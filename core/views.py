import os
import logging
import requests

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView
from django.db.models import Avg, Count, Q

from .forms import BookForm, CategoryForm, CommentForm, RatingForm, RegistrationForm
from .models import Book, Category, Comment, Rating

logger = logging.getLogger(__name__)


# =========================================================
# Utility: Admin Check
# =========================================================
def is_admin(user):
    return user.is_superuser or user.is_staff


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


# =========================================================
# Book List View
# =========================================================
class BookListView(ListView):
    model = Book
    template_name = 'core/book_list.html'
    context_object_name = 'books'
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('category')
            .annotate(
                avg_rating=Avg('ratings__rating'),
                rating_count=Count('ratings')
            )
        )

        category_id = self.request.GET.get('category')
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', 'top')

        if category_id:
            queryset = queryset.filter(category__id=category_id)

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(author__icontains=query)
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

        categories = Category.objects.annotate(
            book_count=Count('books')
        ).order_by('name')

        filtered = any(
            self.request.GET.get(param)
            for param in ('category', 'q', 'sort')
        )

        spotlight_book = (
            Book.objects.select_related('category')
            .annotate(
                avg_rating=Avg('ratings__rating'),
                rating_count=Count('ratings')
            )
            .order_by('-avg_rating', '-rating_count', 'title')
            .first()
        )

        editor_picks = (
            Book.objects.select_related('category')
            .annotate(
                avg_rating=Avg('ratings__rating'),
                rating_count=Count('ratings')
            )
            .order_by('-rating_count', '-avg_rating', 'title')[:3]
        )

        context.update({
            'categories': categories,
            'total_books': Book.objects.count(),
            'total_categories': Category.objects.count(),
            'community_ratings': Rating.objects.count(),
            'community_comments': Comment.objects.count(),
            'spotlight_book': None if filtered else spotlight_book,
            'editor_picks': [] if filtered else editor_picks,
            'is_filtered': filtered,
        })

        return context


# =========================================================
# Book Detail View
# =========================================================
class BookDetailView(View):
    def get(self, request, pk):
        book = get_object_or_404(
            Book.objects.select_related('category')
            .prefetch_related('comments__user', 'ratings__user'),
            pk=pk,
        )

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
            .order_by('-avg_rating', '-rating_count')[:4]
        )

        context = {
            'book': book,
            'avg_rating': avg_rating,
            'rating_count': rating_count,
            'comments': book.comments.all(),
            'rating_form': RatingForm(initial={'rating': user_rating.rating if user_rating else None}),
            'comment_form': CommentForm(),
            'recommendations': recommendations,
            'user_rating': user_rating,
        }

        return render(request, 'core/book_detail.html', context)


# =========================================================
# Authentication
# =========================================================
class RegistrationView(View):
    def get(self, request):
        return render(request, 'registration/register.html', {'form': RegistrationForm()})

    def post(self, request):
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('core:book_list')

        return render(request, 'registration/register.html', {'form': form})


# =========================================================
# Static Pages
# =========================================================
class ContactView(TemplateView):
    template_name = 'core/contact.html'


class FAQView(TemplateView):
    template_name = 'core/faq.html'


# =========================================================
# Admin Dashboard
# =========================================================
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


# =========================================================
# CRUD
# =========================================================
class AddBookView(AdminRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'core/add_book.html'
    success_url = reverse_lazy('core:dashboard')


class EditBookView(AdminRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'core/edit_book.html'
    success_url = reverse_lazy('core:dashboard')


@login_required
def delete_book(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden()

    get_object_or_404(Book, pk=pk).delete()
    return redirect('core:dashboard')


class AddCategoryView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/add_category.html'
    success_url = reverse_lazy('core:dashboard')


class EditCategoryView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/edit_category.html'
    success_url = reverse_lazy('core:dashboard')


@login_required
def delete_category(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden()

    get_object_or_404(Category, pk=pk).delete()
    return redirect('core:dashboard')


# =========================================================
# AI Chat
# =========================================================
class ChatView(LoginRequiredMixin, TemplateView):
    template_name = 'core/chat.html'


@login_required
def get_ai_response(request):
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
                        {"role": "system", "content": "You recommend books."},
                        {"role": "user", "content": user_message},
                    ],
                },
                timeout=15,
            )
            response.raise_for_status()
            return JsonResponse({
                'response': response.json()['choices'][0]['message']['content']
            })

        except Exception as e:
            logger.warning(f"AI API failed: {e}")

    queryset = Book.objects.annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings')
    ).order_by('-avg_rating', '-rating_count')[:3]

    bullets = '\n'.join(
        f'• {b.title} ({(b.avg_rating or 0):.1f}/5)'
        for b in queryset
    )

    return JsonResponse({
        'response': f"Recommended:\n{bullets}"
    })


# =========================================================
# AJAX
# =========================================================
@login_required
@require_POST
def submit_rating_ajax(request, pk):
    book = get_object_or_404(Book, pk=pk)

    try:
        value = int(request.POST.get("value") or request.POST.get("rating"))
        if value < 1 or value > 5:
            raise ValueError
    except:
        return JsonResponse({"success": False}, status=400)

    Rating.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={"rating": value}
    )

    avg = Rating.objects.filter(book=book).aggregate(avg=Avg("rating"))["avg"]

    return JsonResponse({
        "success": True,
        "new_average_rating": round(avg or 0, 1),
        "new_rating_count": Rating.objects.filter(book=book).count()
    })


@login_required
@require_POST
def submit_comment_ajax(request, pk):
    book = get_object_or_404(Book, pk=pk)
    content = request.POST.get("content")

    if not content or not content.strip():
        return JsonResponse({"success": False}, status=400)

    comment = Comment.objects.create(
        user=request.user,
        book=book,
        content=content
    )

    html = render_to_string(
        "core/partials/comment.html",
        {"comment": comment},
        request=request
    )

    return JsonResponse({
        "success": True,
        "comment_html": html,
        "comment_count": Comment.objects.filter(book=book).count()
    })