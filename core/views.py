import logging
import os

import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Count, Prefetch, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import BookForm, CategoryForm, CommentForm, RatingForm, RegistrationForm
from .models import Book, Category, Comment, Rating

logger = logging.getLogger(__name__)


def is_admin(user):
    """Returns True when the user has admin privileges."""
    return user.is_superuser or user.is_staff


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts access to admin users only."""

    def test_func(self):
        return is_admin(self.request.user)


CATEGORY_DESCRIPTIONS = {
    'Classic': 'Timeless novels and enduring favourites that continue to shape the reading canon.',
    'Mystery': 'Whodunits, investigations, and suspenseful plots built around clues and revelations.',
    'Fantasy': 'Imaginative worlds, epic quests, and magical stories driven by wonder and adventure.',
    'Science Fiction': 'Speculative futures, new technologies, and big ideas about humanity and change.',
    'Romance': 'Character-led love stories shaped by chemistry, emotion, and personal growth.',
    'History & Biography': 'Real lives, defining moments, and accessible stories rooted in history.',
    'Philosophy & Psychology': 'Books about meaning, behaviour, identity, and the life of the mind.',
    'Business & Economics': 'Practical thinking on markets, leadership, money, and decision-making.',
    'Science & Technology': 'Readable science and technology books that explain complex ideas clearly.',
    'Self-Help': 'Practical books for habits, productivity, resilience, and personal growth.',
    'Young Adult & Graphic Stories': 'Coming-of-age fiction and visual storytelling with momentum and heart.',
}


def _build_book_analytics_queryset():
    """Reusable queryset with related category data and rating aggregates."""
    return Book.objects.select_related('category').annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings', distinct=True),
    )


def _category_description(category_name):
    return CATEGORY_DESCRIPTIONS.get(
        category_name,
        f'Explore standout titles in {category_name.lower()} and discover a strong place to start.',
    )


def _estimate_read_minutes(book):
    """Lightweight reading-time estimate for the detail page."""
    text = ' '.join(
        part.strip()
        for part in [book.title or '', book.author or '', book.description or '']
        if part
    )
    return max(1, round(len(text.split()) / 200))


class BookListView(ListView):
    """
    Displays the book catalogue with search, filtering and sorting options.
    """

    model = Book
    template_name = 'core/book_list.html'
    context_object_name = 'books'
    paginate_by = 9

    def get_queryset(self):
        queryset = _build_book_analytics_queryset()

        category_id = self.request.GET.get('category')
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', 'top')

        if category_id:
            queryset = queryset.filter(category__id=category_id)

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(author__icontains=query)
            )

        if sort == 'latest':
            queryset = queryset.order_by('-created_at', 'title')
        elif sort == 'title':
            queryset = queryset.order_by('title')
        elif sort == 'discussion':
            queryset = queryset.annotate(
                comment_count=Count('comments', distinct=True)
            ).order_by('-comment_count', '-avg_rating', 'title')
        else:
            queryset = queryset.order_by('-avg_rating', '-rating_count', 'title')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        categories = list(
            Category.objects.annotate(book_count=Count('books', distinct=True))
            .prefetch_related(Prefetch('books', queryset=Book.objects.only('id', 'title', 'category_id').order_by('title')))
            .order_by('name')
        )
        search_query = (self.request.GET.get('q') or '').strip()
        selected_category = self.request.GET.get('category', '')
        selected_sort = self.request.GET.get('sort', 'top') or 'top'
        filtered = bool(search_query or selected_category or selected_sort != 'top')

        spotlight_book = (
            _build_book_analytics_queryset()
            .order_by('-avg_rating', '-rating_count', 'title')
            .first()
        )

        editor_picks = list(
            _build_book_analytics_queryset()
            .order_by('-rating_count', '-avg_rating', 'title')[:3]
        )
        featured_books = list(
            _build_book_analytics_queryset()
            .order_by('-avg_rating', '-rating_count', 'title')[:3]
        )
        latest_comments = list(Comment.objects.select_related('user', 'book').order_by('-created_at')[:3])

        category_showcase = categories[:6]
        for category in category_showcase:
            category.description = _category_description(category.name)
            category.sample_books = [book.title for book in list(category.books.all())[:3]]

        context.update({
            'categories': categories,
            'quick_category_links': categories[:6],
            'category_showcase': [] if filtered else category_showcase,
            'featured_books': [] if filtered else featured_books,
            'latest_comments': [] if filtered else latest_comments,
            'search_query': search_query,
            'selected_category': selected_category,
            'selected_sort': selected_sort,
            'total_books': Book.objects.count(),
            'total_categories': Category.objects.count(),
            'community_ratings': Rating.objects.count(),
            'community_comments': Comment.objects.count(),
            'spotlight_book': None if filtered else spotlight_book,
            'editor_picks': [] if filtered else editor_picks,
            'is_filtered': filtered,
        })

        return context


class BookDetailView(View):
    """
    Displays an individual book page with ratings, comments,
    and simple category-based recommendations.
    """

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
            _build_book_analytics_queryset()
            .filter(category=book.category)
            .exclude(pk=book.pk)
            .order_by('-avg_rating', '-rating_count')[:4]
        )

        estimated_read_minutes = _estimate_read_minutes(book)
        score_degrees = round((avg_rating / 5) * 360) if avg_rating else 0

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
            'score_degrees': score_degrees,
        }

        return render(request, 'core/book_detail.html', context)


class RegistrationView(View):
    """Handles user registration."""

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


class DashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dashboard_stats': {
                'books': Book.objects.count(),
                'categories': Category.objects.count(),
                'ratings': Rating.objects.count(),
                'comments': Comment.objects.count(),
            },
            'books': Book.objects.select_related('category').annotate(
                avg_rating=Avg('ratings__rating')
            ).order_by('title'),
            'categories': Category.objects.annotate(book_count=Count('books')).order_by('name'),
        })
        return context


class AddBookView(AdminRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'core/add_book.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Book added successfully.')
        return super().form_valid(form)


class EditBookView(AdminRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'core/edit_book.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Book updated successfully.')
        return super().form_valid(form)


class AddCategoryView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/add_category.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Category added successfully.')
        return super().form_valid(form)


class EditCategoryView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/edit_category.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully.')
        return super().form_valid(form)


@login_required
@user_passes_test(is_admin)
def delete_book(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid request method.')

    book = get_object_or_404(Book, pk=pk)
    book.delete()
    messages.success(request, 'Book deleted successfully.')
    return redirect('core:dashboard')


@login_required
@user_passes_test(is_admin)
def delete_category(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid request method.')

    category = get_object_or_404(Category, pk=pk)
    linked_books = category.books.count()

    if linked_books:
        messages.warning(
            request,
            f'Cannot delete category while it is assigned to {linked_books} book(s). Reassign those books first.'
        )
        return redirect('core:dashboard')

    category.delete()
    messages.success(request, 'Category deleted successfully.')
    return redirect('core:dashboard')


@login_required
def submit_rating_ajax(request, pk):
    """Handles rating submission via AJAX."""

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

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

    return JsonResponse({
        'success': True,
        'new_average_rating': round(updated_book.avg_rating or 0, 1),
        'new_rating_count': updated_book.ratings.count(),
        'user_rating': rating_obj.rating,
    })


@login_required
def submit_comment_ajax(request, pk):
    """Handles comment submission via AJAX."""

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    book = get_object_or_404(Book, pk=pk)
    form = CommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    comment = form.save(commit=False)
    comment.book = book
    comment.user = request.user
    comment.save()

    comment_html = render_to_string(
        'core/partials/comment.html',
        {'comment': comment},
        request=request,
    )

    return JsonResponse({
        'success': True,
        'comment_html': comment_html,
        'comment_count': book.comments.count(),
    })


class ChatView(LoginRequiredMixin, TemplateView):
    """
    Displays the AI chat page.

    The navigation link is visible to all users so the feature can be discovered,
    but authentication is required before accessing the chat interface.
    """

    template_name = 'core/chat.html'


@login_required
def get_ai_response(request):
    """
    Returns an AI response.

    This function first attempts to call the DeepSeek API.
    If unavailable, it falls back to a rule-based recommendation system that:
    - parses user input
    - applies multi-condition filtering
    - ranks books using ratings and popularity
    """

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    user_message = (request.POST.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    lowered = user_message.lower()
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
                            'content': 'You are a helpful book recommendation assistant for a reading website.',
                        },
                        {'role': 'user', 'content': user_message},
                    ],
                },
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return JsonResponse({'response': data['choices'][0]['message']['content']})
        except Exception as exc:
            logger.warning('AI API request failed, falling back to local recommendations: %s', exc)

    books = list(
        Book.objects.select_related('category').annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings'),
        )
    )

    if not books:
        return JsonResponse({'response': 'I do not have any books in the catalogue yet.'})

    results = books

    if 'fantasy' in lowered:
        results = [b for b in results if b.category and 'fantasy' in b.category.name.lower()]
    elif 'classic' in lowered:
        results = [b for b in results if b.category and 'classic' in b.category.name.lower()]
    elif 'science' in lowered or 'sci-fi' in lowered:
        results = [b for b in results if b.category and 'sci' in b.category.name.lower()]
    elif 'romance' in lowered:
        results = [b for b in results if b.category and 'romance' in b.category.name.lower()]
    elif 'mystery' in lowered or 'detective' in lowered:
        results = [b for b in results if b.category and 'mystery' in b.category.name.lower()]

    if 'short' in lowered or 'easy' in lowered:
        results = [b for b in results if len(b.description or '') < 250]

    if 'popular' in lowered:
        results = sorted(results, key=lambda b: b.rating_count, reverse=True)
    else:
        results = sorted(
            results,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True,
        )

    if not results:
        results = sorted(
            books,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True,
        )

    results = results[:3]
    bullets = '\n'.join(
        f'• {book.title} by {book.author} — '
        f'{(book.category.name if book.category else "General")}, '
        f'rated {(book.avg_rating or 0):.1f}/5 from {(book.rating_count or 0)} review(s)'
        for book in results
    )

    response_text = (
        'Here are some books you might enjoy from BookVibe:\n'
        f'{bullets}\n\n'
        'Tell me a genre, mood, or reading style and I can refine the suggestions.'
    )
    return JsonResponse({'response': response_text})
