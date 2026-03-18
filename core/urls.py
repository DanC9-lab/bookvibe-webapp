"""
URL routing for the core app.
Organises routes into public pages, AJAX endpoints, and admin dashboard.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # --- Public pages ---
    path('', views.BookListView.as_view(), name='book_list'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),

    # --- AJAX endpoints (ratings, comments, AI chat) ---
    path('books/<int:pk>/rate-ajax/', views.submit_rating_ajax, name='submit_rating_ajax'),
    path('books/<int:pk>/comment-ajax/', views.submit_comment_ajax, name='submit_comment_ajax'),
    path('get-ai-response/', views.get_ai_response, name='get_ai_response'),

    # --- Custom admin dashboard (M6) ---
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/book/add/', views.AddBookView.as_view(), name='add_book'),
    path('dashboard/book/<int:pk>/edit/', views.EditBookView.as_view(), name='edit_book'),
    path('dashboard/book/<int:pk>/delete/', views.delete_book, name='delete_book'),
    path('dashboard/category/add/', views.AddCategoryView.as_view(), name='add_category'),
    path('dashboard/category/<int:pk>/edit/', views.EditCategoryView.as_view(), name='edit_category'),
    path('dashboard/category/<int:pk>/delete/', views.delete_category, name='delete_category'),
]
