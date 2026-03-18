
from django.views.generic import DetailView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from .models import Book, Comment, Rating

class BookDetailView(DetailView):
    model = Book
    template_name = 'core/book_detail.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object

        context['comments'] = Comment.objects.filter(book=book).order_by('-created_at')
        context['avg_rating'] = Rating.objects.filter(book=book).aggregate(avg=Avg('score'))['avg'] or 0

        # Simple "similar books" (same category if exists)
        if hasattr(book, 'category'):
            context['similar_books'] = Book.objects.filter(category=book.category).exclude(id=book.id)[:4]
        else:
            context['similar_books'] = []

        return context


def ajax_add_comment(request, pk):
    if request.method == "POST":
        book = get_object_or_404(Book, pk=pk)
        text = request.POST.get('text')
        if text:
            comment = Comment.objects.create(book=book, text=text)
            return JsonResponse({
                "text": comment.text,
            })
    return JsonResponse({"error": "Invalid"}, status=400)


def ajax_add_rating(request, pk):
    if request.method == "POST":
        book = get_object_or_404(Book, pk=pk)
        score = int(request.POST.get('score', 0))
        if 1 <= score <= 5:
            Rating.objects.create(book=book, score=score)
            avg = Rating.objects.filter(book=book).aggregate(avg=Avg('score'))['avg'] or 0
            return JsonResponse({"avg": round(avg,1)})
    return JsonResponse({"error": "Invalid"}, status=400)
