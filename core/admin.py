from django.contrib import admin
from .models import Category, Book, Rating, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the Category model."""
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """Admin configuration for the Book model."""
    list_display = ('title', 'author', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'author')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """Admin configuration for the Rating model."""
    list_display = ('book', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('book__title', 'user__username')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin configuration for the Comment model."""
    list_display = ('book', 'user', 'created_at')
    search_fields = ('book__title', 'user__username', 'content')
    readonly_fields = ('created_at',)
