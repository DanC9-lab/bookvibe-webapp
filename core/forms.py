from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Book, Category, Comment, Rating


class RegistrationForm(UserCreationForm):
    """Custom registration form with a required email field."""

    email = forms.EmailField(required=True, help_text='Required. Used for account recovery.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': field.label})
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'


class RatingForm(forms.ModelForm):
    """Form for submitting a 1-5 star book rating."""

    class Meta:
        model = Rating
        fields = ['rating']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(5, 0, -1)]),
        }


class CommentForm(forms.ModelForm):
    """Form for submitting a comment on a book page."""

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Share your thoughts, recommendations, or favourite moment from this book...',
                    'class': 'form-control',
                }
            ),
        }


class BookForm(forms.ModelForm):
    """Form for administrators to add or edit books."""

    class Meta:
        model = Book
        fields = ['title', 'author', 'cover', 'cover_url', 'description', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Book title'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author name'}),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'cover_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Optional remote cover image URL'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Add a concise but engaging description.'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }


class CategoryForm(forms.ModelForm):
    """Form for administrators to add or edit categories."""

    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
        }
