"""
URL configuration for BookVibe project.
Includes routes for the core app, authentication views, and admin panel.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import RegistrationView

urlpatterns = [
    # Django's built-in admin site
    path('admin/', admin.site.urls),

    # Core app URLs (books, chat, ratings, comments, custom admin dashboard)
    path('', include('core.urls')),

    # Django built-in authentication URLs (login, logout)
    path('accounts/', include('django.contrib.auth.urls')),

    # Custom registration view
    path('accounts/register/', RegistrationView.as_view(), name='register'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
