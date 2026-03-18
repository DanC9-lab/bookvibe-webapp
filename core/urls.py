"""
URL routing for the core app.

This module defines all routes including:
- Public pages (book list, detail, chat, contact, FAQ)
- AJAX endpoints (ratings, comments, AI responses)
- Admin dashboard (book and category management)
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [

    # =========================================================
    # Public Pages
    # =========================================================

    # Homepage - displays list of books
    path('', views.BookListView.as_view(), name='book_list'),

    # Book detail page
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),

    # AI chat page
    path('chat/', views.ChatView.as_view(), name='chat'),

    # Contact page
    path('contact/', views.ContactView.as_view(), name='contact'),

    # FAQ page
    path('faq/', views.FAQView.as_view(), name='faq'),


    # =========================================================
    # AJAX Endpoints (Ratings, Comments, AI)
    # =========================================================

    # Submit rating via AJAX
    path('books/<int:pk>/rate-ajax/', views.submit_rating_ajax, name='submit_rating_ajax'),

    # Submit comment via AJAX
    path('books/<int:pk>/comment-ajax/', views.submit_comment_ajax, name='submit_comment_ajax'),

    # Get AI response (AJAX endpoint)
    path('get-ai-response/', views.get_ai_response, name='get_ai_response'),


    # =========================================================
    # Admin Dashboard (M6 Feature)
    # =========================================================

    # Dashboard homepage
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Add a new book
    path('dashboard/book/add/', views.AddBookView.as_view(), name='add_book'),

    # Edit an existing book
    path('dashboard/book/<int:pk>/edit/', views.EditBookView.as_view(), name='edit_book'),

    # Delete a book
    path('dashboard/book/<int:pk>/delete/', views.delete_book, name='delete_book'),

    # Add a new category
    path('dashboard/category/add/', views.AddCategoryView.as_view(), name='add_category'),

    # Edit a category
    path('dashboard/category/<int:pk>/edit/', views.EditCategoryView.as_view(), name='edit_category'),

    # Delete a category
    path('dashboard/category/<int:pk>/delete/', views.delete_category, name='delete_category'),
]