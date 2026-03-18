import logging
import os

import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import BookForm, CategoryForm, CommentForm, RatingForm, RegistrationForm
from .models import Book, Category, Comment, Rating

# Initialize logger for debugging and error tracking
logger = logging.getLogger(__name__)


def is_admin(user):
    """Returns True when the user has admin privileges."""
    return user.is_superuser or user.is_staff


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts access to admin users only."""

    def test_func(self):
        return is_admin(self.request.user)


def _build_book_analytics_queryset():
    """Reusable queryset with related category data and rating aggregates."""
    return Book.objects.select_related('category').annotate(
        avg_rating=Avg('ratings__rating'),   # Calculate average rating per book
        rating_count=Count('ratings'),       # Count total number of ratings
    )


def _estimate_read_minutes(book):
    """Lightweight reading-time estimate for the detail page."""
    # Combine text fields for rough word count estimation
    text = ' '.join(
        part.strip()
        for part in [book.title or '', book.author or '', book.description or '']
        if part
    )
    # Assume average reading speed = 200 words per minute
    return max(1, round(len(text.split()) / 200))


class BookListView(ListView):
    """
    Displays the book catalogue with search, filtering and sorting options.
    """

    model = Book
    template_name = 'core/book_list.html'
    context_object_name = 'books'
    paginate_by = 9  # Limit number of books per page

    def get_queryset(self):
        # Base queryset with analytics (ratings)
        queryset = _build_book_analytics_queryset()

        # Extract query parameters from request
        category_id = self.request.GET.get('category')
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', 'top')

        # Filter by category if provided
        if category_id:
            queryset = queryset.filter(category__id=category_id)

        # Search by title or author
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(author__icontains=query)
            )

        # Sorting logic
        if sort == 'latest':
            queryset = queryset.order_by('-created_at', 'title')
        elif sort == 'title':
            queryset = queryset.order_by('title')
        elif sort == 'discussion':
            queryset = queryset.annotate(
                comment_count=Count('comments')  # Count comments per book
            ).order_by('-comment_count', '-avg_rating', 'title')
        else:
            # Default sorting: highest rating + most reviews
            queryset = queryset.order_by('-avg_rating', '-rating_count', 'title')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get categories with number of books in each
        categories = Category.objects.annotate(book_count=Count('books')).order_by('name')

        # Check if any filter is applied
        filtered = any(
            self.request.GET.get(param)
            for param in ('category', 'q', 'sort')
        )

        # Top-rated book for hero section
        spotlight_book = (
            _build_book_analytics_queryset()
            .order_by('-avg_rating', '-rating_count', 'title')
            .first()
        )

        # Editor picks: most reviewed books
        editor_picks = (
            _build_book_analytics_queryset()
            .order_by('-rating_count', '-avg_rating', 'title')[:3]
        )

        # ⭐ Category showcase (top 3 sample books per category)
        category_showcase = []
        for category in categories:
            sample_books = list(
                Book.objects.filter(category=category)
                .values_list('title', flat=True)[:3]
            )
            category_showcase.append({
                'id': category.id,
                'name': category.name,
                'description': getattr(category, 'description', ''),
                'book_count': category.book_count,
                'sample_books': sample_books,
            })

        # ⭐ Latest user comments (recent activity)
        latest_comments = Comment.objects.select_related('user', 'book').order_by('-id')[:5]

        # Update template context
        context.update({
            'categories': categories,

            # 🔥 Platform statistics
            'total_books': Book.objects.count(),
            'total_categories': Category.objects.count(),
            'community_ratings': Rating.objects.count(),
            'community_comments': Comment.objects.count(),

            # ⭐ Hero + sections (only shown when not filtered)
            'spotlight_book': None if filtered else spotlight_book,
            'quick_category_links': categories[:6] if not filtered else [],

            # ⭐ Featured sections
            'category_showcase': [] if filtered else category_showcase,
            'featured_books': [] if filtered else editor_picks,
            'latest_comments': [] if filtered else latest_comments,

            'is_filtered': filtered,
        })

        return context


class BookDetailView(View):
    """
    Displays an individual book page with ratings, comments,
    and simple category-based recommendations.
    """

    def get(self, request, pk):
        # Retrieve book with related category, comments and ratings
        book = get_object_or_404(
            Book.objects.select_related('category').prefetch_related('comments__user', 'ratings__user'),
            pk=pk,
        )

        comments = book.comments.all()
        ratings = list(book.ratings.all())

        # Calculate average rating manually
        avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else 0.0
        rating_count = len(ratings)

        # Get current user's rating if exists
        user_rating = None
        if request.user.is_authenticated:
            user_rating = book.ratings.filter(user=request.user).first()

        # Recommend similar books from same category
        recommendations = (
            _build_book_analytics_queryset()
            .filter(category=book.category)
            .exclude(pk=book.pk)
            .order_by('-avg_rating', '-rating_count')[:4]
        )

        # Estimate reading time
        estimated_read_minutes = _estimate_read_minutes(book)

        # Convert rating into circular progress degrees
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
        # Display registration form
        return render(request, 'registration/register.html', {'form': RegistrationForm()})

    def post(self, request):
        # Handle form submission
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect('core:book_list')

        return render(request, 'registration/register.html', {'form': form})


class ContactView(TemplateView):
    """Static contact page."""
    template_name = 'core/contact.html'


class FAQView(TemplateView):
    """Static FAQ page."""
    template_name = 'core/faq.html'


class DashboardView(AdminRequiredMixin, TemplateView):
    """Admin dashboard with site statistics."""
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Dashboard statistics and data tables
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
    """Admin view to add a new book."""
    model = Book
    form_class = BookForm
    template_name = 'core/add_book.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Book added successfully.')
        return super().form_valid(form)


class EditBookView(AdminRequiredMixin, UpdateView):
    """Admin view to edit an existing book."""
    model = Book
    form_class = BookForm
    template_name = 'core/edit_book.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Book updated successfully.')
        return super().form_valid(form)


class AddCategoryView(AdminRequiredMixin, CreateView):
    """Admin view to add a new category."""
    model = Category
    form_class = CategoryForm
    template_name = 'core/add_category.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Category added successfully.')
        return super().form_valid(form)


class EditCategoryView(AdminRequiredMixin, UpdateView):
    """Admin view to edit an existing category."""
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
    # Ensure request method is POST for security
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid request method.')

    # Retrieve and delete the selected book
    book = get_object_or_404(Book, pk=pk)
    book.delete()

    # Display success message and redirect to dashboard
    messages.success(request, 'Book deleted successfully.')
    return redirect('core:dashboard')


@login_required
@user_passes_test(is_admin)
def delete_category(request, pk):
    # Ensure request method is POST
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid request method.')

    # Retrieve category and count related books
    category = get_object_or_404(Category, pk=pk)
    linked_books = category.books.count()

    # Prevent deletion if category still has books assigned
    if linked_books:
        messages.warning(
            request,
            f'Cannot delete category while it is assigned to {linked_books} book(s). Reassign those books first.'
        )
        return redirect('core:dashboard')

    # Delete category if safe
    category.delete()
    messages.success(request, 'Category deleted successfully.')
    return redirect('core:dashboard')


@login_required
def submit_rating_ajax(request, pk):
    """Handles rating submission via AJAX."""

    # Only allow POST requests
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    # Get book instance
    book = get_object_or_404(Book, pk=pk)
    form = RatingForm(request.POST)

    # Validate form
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # Create or update user's rating
    rating_obj, _ = Rating.objects.update_or_create(
        book=book,
        user=request.user,
        defaults={'rating': form.cleaned_data['rating']},
    )

    # Recalculate updated average rating
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

    # Only allow POST requests
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)

    # Get book instance
    book = get_object_or_404(Book, pk=pk)
    form = CommentForm(request.POST)

    # Validate form
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # Create comment object but do not save yet
    comment = form.save(commit=False)
    comment.book = book
    comment.user = request.user
    comment.save()

    # Render comment HTML for dynamic insertion (AJAX)
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

    # Only allow POST requests
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    # Get and clean user input
    user_message = (request.POST.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    lowered = user_message.lower()
    api_key = os.environ.get('DEEPSEEK_API_KEY')

    # Try calling external AI API
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

            # Return AI-generated response
            return JsonResponse({'response': data['choices'][0]['message']['content']})

        except Exception as exc:
            # Fallback if API fails
            logger.warning('AI API request failed, falling back to local recommendations: %s', exc)

    # Local recommendation system
    books = list(
        Book.objects.select_related('category').annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings'),
        )
    )

    if not books:
        return JsonResponse({'response': 'I do not have any books in the catalogue yet.'})

    results = books

    # Genre filtering based on user input
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

    # Filter for shorter/easier reads
    if 'short' in lowered or 'easy' in lowered:
        results = [b for b in results if len(b.description or '') < 250]

    # Sorting logic
    if 'popular' in lowered:
        results = sorted(results, key=lambda b: b.rating_count, reverse=True)
    else:
        results = sorted(
            results,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True,
        )

    # Fallback if no filtered results
    if not results:
        results = sorted(
            books,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True,
        )

    # Limit to top 3 results
    results = results[:3]

    # Format response text
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