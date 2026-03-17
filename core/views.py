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
    """
    Displays the book catalogue with search, filtering and sorting options.
    """

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
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(author__icontains=query)
            )

        if sort == 'latest':
            queryset = queryset.order_by('-created_at', 'title')

        elif sort == 'title':
            queryset = queryset.order_by('title')

        elif sort == 'discussion':
            queryset = queryset.annotate(
                comment_count=Count('comments')
            ).order_by('-comment_count', '-avg_rating', 'title')

        else:
            queryset = queryset.order_by('-avg_rating', '-rating_count', 'title')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        categories = Category.objects.annotate(book_count=Count('books')).order_by('name')

        context.update({
            'categories': categories,
            'total_books': Book.objects.count(),
            'total_categories': Category.objects.count(),
            'community_ratings': Rating.objects.count(),
            'community_comments': Comment.objects.count(),
        })

        return context


class BookDetailView(View):
    """
    Displays an individual book page with ratings, comments,
    and simple category-based recommendations.
    """

    def get(self, request, pk):

        book = get_object_or_404(
            Book.objects.select_related('category')
            .prefetch_related('comments__user', 'ratings__user'),
            pk=pk
        )

        comments = book.comments.all()
        ratings = list(book.ratings.all())

        avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else 0
        rating_count = len(ratings)

        user_rating = None
        if request.user.is_authenticated:
            user_rating = book.ratings.filter(user=request.user).first()

        recommendations = (
            Book.objects
            .select_related('category')
            .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
            .filter(category=book.category)
            .exclude(pk=book.pk)
            .order_by('-avg_rating', '-rating_count')[:4]
        )

        context = {
            'book': book,
            'avg_rating': avg_rating,
            'rating_count': rating_count,
            'comments': comments,
            'rating_form': RatingForm(initial={'rating': user_rating.rating if user_rating else None}),
            'comment_form': CommentForm(),
            'recommendations': recommendations,
            'user_rating': user_rating,
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

            messages.success(
                request,
                f"Welcome, {user.username}! Your account has been created."
            )

            return redirect('core:book_list')

        return render(request, 'registration/register.html', {'form': form})


class ContactView(TemplateView):
    template_name = 'core/contact.html'


class FAQView(TemplateView):
    template_name = 'core/faq.html'


@login_required
def submit_rating_ajax(request, pk):
    """Handles rating submission via AJAX."""

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    book = get_object_or_404(Book, pk=pk)

    form = RatingForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False}, status=400)

    rating_obj, _ = Rating.objects.update_or_create(
        book=book,
        user=request.user,
        defaults={'rating': form.cleaned_data['rating']}
    )

    updated_book = Book.objects.annotate(avg_rating=Avg('ratings__rating')).get(pk=pk)

    return JsonResponse({
        'success': True,
        'new_average_rating': round(updated_book.avg_rating or 0, 1),
        'new_rating_count': updated_book.ratings.count(),
        'user_rating': rating_obj.rating
    })


@login_required
def submit_comment_ajax(request, pk):
    """Handles comment submission via AJAX."""

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    book = get_object_or_404(Book, pk=pk)

    form = CommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False}, status=400)

    comment = form.save(commit=False)
    comment.book = book
    comment.user = request.user
    comment.save()

    comment_html = render_to_string('core/partials/comment.html', {'comment': comment})

    return JsonResponse({
        'success': True,
        'comment_html': comment_html,
        'comment_count': book.comments.count()
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
    Generates AI responses.

    If an external API key is configured, the system attempts to use the
    DeepSeek API. Otherwise a lightweight local recommendation engine
    suggests books based on keywords and ratings.
    """

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=405)

    user_message = (request.POST.get('message') or '').strip().lower()

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

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
                        {"role": "system", "content": "You are a helpful book recommendation assistant."},
                        {"role": "user", "content": user_message}
                    ],
                },
                timeout=20
            )

            data = response.json()

            return JsonResponse({
                'response': data['choices'][0]['message']['content']
            })

        except Exception:
            pass

    books = list(
        Book.objects
        .select_related('category')
        .annotate(avg_rating=Avg('ratings__rating'), rating_count=Count('ratings'))
    )

    if not books:
        return JsonResponse({
            'response': 'No books available in the catalogue yet.'
        })

    if 'fantasy' in user_message:
        matches = [b for b in books if b.category and 'fantasy' in b.category.name.lower()]

    elif 'classic' in user_message:
        matches = [b for b in books if b.category and 'classic' in b.category.name.lower()]

    elif 'science' in user_message or 'sci' in user_message:
        matches = [b for b in books if b.category and 'sci' in b.category.name.lower()]

    elif 'best' in user_message or 'top' in user_message:
        matches = sorted(books, key=lambda b: ((b.avg_rating or 0), b.rating_count), reverse=True)

    else:
        matches = books[:3]

    bullets = "\n".join(
        f"• {b.title} by {b.author} ({b.category.name if b.category else 'General'})"
        for b in matches[:3]
    )

    return JsonResponse({
        'response': f"Here are some books you might enjoy:\n{bullets}"
    })


class DashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Admin dashboard."""

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update({
            'books': Book.objects.all(),
            'categories': Category.objects.all(),
        })

        return context