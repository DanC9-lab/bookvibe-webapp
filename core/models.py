from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """
    Represents a book category (e.g., Classic, Mystery, Adventure).
    Each category has a unique name used for filtering books on the list page.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Name of the category")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Book(models.Model):
    """
    Represents a single book in the library.
    Linked to a Category via ForeignKey, and has related Rating and Comment objects.
    """
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.ImageField(upload_to='book_covers/', null=True, blank=True, help_text="Book cover image")
    cover_url = models.URLField(blank=True, default="", help_text="Remote cover image URL")
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="books")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def display_cover_url(self):
        if self.cover:
            return self.cover.url
        return self.cover_url

    def average_rating(self):
        """
        Calculates the average rating for the book.
        Returns 0.0 if there are no ratings yet.
        """
        ratings = self.ratings.all()
        if not ratings:
            return 0.0
        return sum(r.rating for r in ratings) / len(ratings)


class Rating(models.Model):
    """
    Represents a user's rating for a book (1-5 stars).
    The unique_together constraint ensures each user can only rate a book once.
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ratings")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('book', 'user')

    def __str__(self):
        return f"{self.user.username}'s {self.rating}-star rating for {self.book.title}"


class Comment(models.Model):
    """
    Represents a user's comment on a book page.
    Ordered by creation date (newest first) for display purposes.
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.book.title}"

    class Meta:
        ordering = ['-created_at']
