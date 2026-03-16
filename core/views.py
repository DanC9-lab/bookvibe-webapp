import os
import requests

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import BookForm, CategoryForm, CommentForm, RatingForm, RegistrationForm
from .management.commands.seed_demo_data import CATEGORY_LIBRARY
from .models import Book, Category, Comment, Rating


def is_admin(user):
    """Returns True when the user has admin privileges."""
    return user.is_superuser or user.is_staff


class AdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to admin users only."""

    def test_func(self):
        return is_admin(self.request.user)


class BookListView(ListView):
    """Displays the book catalogue with search, filter and sorting."""

    model = Book
    template_name = 'core/book_list.html'
    context_object_name = 'books'
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('category')
            .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
        )

        category_id = self.request.GET.get('category')
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', 'top')

        if category_id:
            queryset = queryset.filter(category__id=category_id)
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(author__icontains=query))

        if sort == 'latest':
            queryset = queryset.order_by('-created_at', 'title')
        elif sort == 'title':
            queryset = queryset.order_by('title')
        elif sort == 'discussion':
            queryset = queryset.annotate(comment_count=Count('comments')).order_by('-comment_count', '-avg_rating', 'title')
        else:
            queryset = queryset.order_by('-avg_rating', '-rating_count', 'title')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.annotate(book_count=Count('books')).order_by('name')
        category_map = {category.name: category for category in categories}
        category_showcase = []
        for category_item in CATEGORY_LIBRARY:
            category = category_map.get(category_item['name'])
            if not category:
                continue
            category_showcase.append({
                'id': category.id,
                'name': category_item['name'],
                'description': category_item['description'],
                'sample_books': [title for title, _, _ in category_item['books']],
                'book_count': category.book_count,
            })
        featured_books = (
            Book.objects.select_related('category')
            .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
            .order_by('-avg_rating', '-rating_count', '-created_at')[:3]
        )
        top_rated = (
            Book.objects.select_related('category')
            .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
            .order_by('-avg_rating', '-rating_count', 'title')[:5]
        )
        latest_comments = Comment.objects.select_related('user', 'book').order_by('-created_at')[:4]
        spotlight_book = top_rated[0] if top_rated else None
        selected_category = self.request.GET.get('category', '')
        search_query = self.request.GET.get('q', '')
        context.update(
            {
                'categories': categories,
                'selected_category': selected_category,
                'search_query': search_query,
                'selected_sort': self.request.GET.get('sort', 'top'),
                'is_filtered': bool(selected_category or search_query),
                'total_books': Book.objects.count(),
                'total_categories': Category.objects.count(),
                'community_ratings': Rating.objects.count(),
                'community_comments': Comment.objects.count(),
                'featured_books': featured_books,
                'top_rated_books': top_rated,
                'spotlight_book': spotlight_book,
                'latest_comments': latest_comments,
                'quick_category_links': category_showcase[:6],
                'category_showcase': category_showcase,
            }
        )
        return context


class BookDetailView(View):
    """Displays a single book's detail page with rating, comments and recommendations."""

    def get(self, request, pk):
        book = get_object_or_404(
            Book.objects.select_related('category').prefetch_related('comments__user', 'ratings__user'),
            pk=pk,
        )
        comments = book.comments.all()
        ratings = list(book.ratings.all())
        avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else 0.0
        rating_count = len(ratings)
        user_rating = None
        if request.user.is_authenticated:
            user_rating = book.ratings.filter(user=request.user).first()
        recommendations = (
            Book.objects.select_related('category')
            .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
            .filter(category=book.category)
            .exclude(pk=book.pk)
            .order_by('-avg_rating', '-rating_count', 'title')[:4]
        )
        description_words = len((book.description or '').split())
        estimated_read_minutes = max(1, round(description_words / 180))
        context = {
            'book': book,
            'avg_rating': avg_rating,
            'rating_count': rating_count,
            'comments': comments,
            'rating_form': RatingForm(initial={'rating': user_rating.rating if user_rating else None}),
            'comment_form': CommentForm(),
            'recommendations': recommendations,
            'user_rating': user_rating,
            'estimated_read_minutes': estimated_read_minutes,
        }
        return render(request, 'core/book_detail.html', context)


class RegistrationView(View):
    """Handles user registration and logs the user in on success."""

    def get(self, request):
        return render(request, 'registration/register.html', {'form': RegistrationForm()})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect('core:book_list')
        return render(request, 'registration/register.html', {'form': form})


class ContactView(TemplateView):
    template_name = 'core/contact.html'


class FAQView(TemplateView):
    template_name = 'core/faq.html'


@login_required
def submit_rating_ajax(request, pk):
    """AJAX endpoint for submitting or updating a book rating."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': 'Invalid request'}, status=400)

    book = get_object_or_404(Book, pk=pk)
    form = RatingForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    rating_obj, _ = Rating.objects.update_or_create(
        book=book,
        user=request.user,
        defaults={'rating': form.cleaned_data['rating']},
    )
    updated_book = Book.objects.annotate(avg_rating=Avg('ratings__rating')).get(pk=pk)
    stars = '★' * rating_obj.rating + '☆' * (5 - rating_obj.rating)
    return JsonResponse(
        {
            'success': True,
            'new_average_rating': round(updated_book.avg_rating or 0, 1),
            'new_rating_count': updated_book.ratings.count(),
            'user_rating': rating_obj.rating,
            'user_rating_stars': stars,
        }
    )


@login_required
def submit_comment_ajax(request, pk):
    """AJAX endpoint for posting a new comment."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': 'Invalid request'}, status=400)

    book = get_object_or_404(Book, pk=pk)
    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    comment = form.save(commit=False)
    comment.book = book
    comment.user = request.user
    comment.save()
    comment_html = render_to_string('core/partials/comment.html', {'comment': comment})
    return JsonResponse({'success': True, 'comment_html': comment_html, 'comment_count': book.comments.count()})


class ChatView(LoginRequiredMixin, TemplateView):
    """Renders the AI chat page."""

    template_name = 'core/chat.html'


@login_required
def get_ai_response(request):
    """Returns an AI response, with a local recommendation fallback when no API key is set."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    user_message = (request.POST.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if api_key:
        try:
            response = requests.post(
                'https://api.deepseek.com/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a warm, concise book recommendation assistant for a public reading website.',
                        },
                        {'role': 'user', 'content': user_message},
                    ],
                },
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return JsonResponse({'response': data['choices'][0]['message']['content']})
        except Exception:
            pass

    lowered = user_message.lower()
    books = list(Book.objects.select_related('category').annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings')))
    if not books:
        return JsonResponse({'response': 'I do not have any books in the catalogue yet. Add a few in the admin panel and I can recommend them.'})

    if 'fantasy' in lowered:
        matches = [b for b in books if b.category and 'fantasy' in b.category.name.lower()]
    elif 'classic' in lowered:
        matches = [b for b in books if b.category and 'classic' in b.category.name.lower()]
    elif 'sci' in lowered or 'science' in lowered:
        matches = [b for b in books if b.category and 'sci' in b.category.name.lower()]
    elif 'best' in lowered or 'top' in lowered or 'popular' in lowered:
        matches = sorted(books, key=lambda b: ((b.avg_rating or 0), b.rating_count), reverse=True)[:3]
    elif 'short' in lowered or 'easy' in lowered:
        matches = [b for b in books if len(b.description) < 220][:3]
    elif 'motivation' in lowered or 'habit' in lowered or 'self' in lowered:
        matches = [b for b in books if b.category and 'self' in b.category.name.lower()][:3]
    else:
        matches = sorted(books, key=lambda b: ((b.avg_rating or 0), b.rating_count, b.created_at.timestamp()), reverse=True)[:3]

    if not matches:
        matches = books[:3]

    bullets = '\n'.join(
        f'• {book.title} by {book.author} — {(book.category.name if book.category else "General")}, rated {(book.avg_rating or 0):.1f}/5 from {book.rating_count} review(s)'
        for book in matches[:3]
    )
    response_text = (
        'Here are a few good picks from BookVibe:\n'
        f'{bullets}\n\n'
        'Tell me a genre, mood, or author you like and I can narrow it down.'
    )
    return JsonResponse({'response': response_text})


class DashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Custom admin dashboard showing books and categories."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.select_related('category').annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings')).all()
        categories = Category.objects.annotate(book_count=Count('books')).all()
        context.update(
            {
                'books': books,
                'categories': categories,
                'dashboard_stats': {
                    'books': Book.objects.count(),
                    'categories': Category.objects.count(),
                    'ratings': Rating.objects.count(),
                    'comments': Comment.objects.count(),
                },
            }
        )
        return context


class AddBookView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/add_book.html', {'form': BookForm()})

    def post(self, request):
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Book added successfully.')
            return redirect('core:dashboard')
        return render(request, 'core/add_book.html', {'form': form})


class EditBookView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        return render(request, 'core/edit_book.html', {'form': BookForm(instance=book), 'book': book})

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Book updated successfully.')
            return redirect('core:dashboard')
        return render(request, 'core/edit_book.html', {'form': form, 'book': book})


@login_required
@user_passes_test(is_admin)
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.delete()
        messages.success(request, 'Book deleted successfully.')
    return redirect('core:dashboard')


class AddCategoryView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/add_category.html', {'form': CategoryForm()})

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('core:dashboard')
        return render(request, 'core/add_category.html', {'form': form})


class EditCategoryView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return render(request, 'core/edit_category.html', {'form': CategoryForm(instance=category), 'category': category})

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('core:dashboard')
        return render(request, 'core/edit_category.html', {'form': form, 'category': category})


@login_required
@user_passes_test(is_admin)
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully.')
    return redirect('core:dashboard')
