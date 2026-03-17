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

    # -------------------------------
    # Try external AI (unchanged)
    # -------------------------------
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
        except Exception:
            pass

    # -------------------------------
    # Advanced local AI (NEW PART)
    # -------------------------------

    books = list(
        Book.objects
        .select_related('category')
        .annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings')
        )
    )

    if not books:
        return JsonResponse({
            'response': 'I do not have any books in the catalogue yet.'
        })

    results = books

    # -------- Genre filtering --------
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

    # -------- Length / difficulty --------
    if 'short' in lowered or 'easy' in lowered:
        results = [b for b in results if len(b.description or '') < 250]

    # -------- Ranking --------
    if 'popular' in lowered:
        results = sorted(results, key=lambda b: b.rating_count, reverse=True)

    elif 'high rating' in lowered or 'best' in lowered or 'top' in lowered:
        results = sorted(results, key=lambda b: ((b.avg_rating or 0), b.rating_count), reverse=True)

    else:
        results = sorted(
            results,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True
        )

    # -------- Fallback --------
    if not results:
        results = sorted(
            books,
            key=lambda b: ((b.avg_rating or 0), b.rating_count),
            reverse=True
        )

results = results[:3]

# -------- Format response --------
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