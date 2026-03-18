
from django.urls import path
from .views import *

urlpatterns = [
    path('book/<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('book/<int:pk>/ajax/comment/', ajax_add_comment, name='ajax_add_comment'),
    path('book/<int:pk>/ajax/rating/', ajax_add_rating, name='ajax_add_rating'),
]
