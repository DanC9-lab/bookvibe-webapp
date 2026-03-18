from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Book, Category, Comment, Rating


class BookModelTests(TestCase):
    """Core model business logic should remain stable."""

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.category = Category.objects.create(name='Testing')
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            description='A test book.',
            category=self.category,
        )

    def test_average_rating_no_ratings(self):
        self.assertEqual(self.book.average_rating(), 0.0)

    def test_average_rating_single_rating(self):
        Rating.objects.create(book=self.book, user=self.user1, rating=4)
        self.assertEqual(self.book.average_rating(), 4.0)

    def test_average_rating_multiple_ratings(self):
        Rating.objects.create(book=self.book, user=self.user1, rating=3)
        Rating.objects.create(book=self.book, user=self.user2, rating=5)
        self.assertEqual(self.book.average_rating(), 4.0)

    def test_book_str(self):
        self.assertEqual(str(self.book), 'Test Book by Test Author')


class RatingModelTests(TestCase):
    """A user should only keep one rating per book."""

    def setUp(self):
        self.user = User.objects.create_user(username='rater', password='testpass123')
        self.category = Category.objects.create(name='Fiction')
        self.book = Book.objects.create(title='Rated Book', author='Author', description='Desc', category=self.category)

    def test_unique_rating_per_user_per_book(self):
        Rating.objects.create(book=self.book, user=self.user, rating=5)
        with self.assertRaises(Exception):
            Rating.objects.create(book=self.book, user=self.user, rating=3)


class BookDetailViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='viewer1', password='testpass123')
        self.user2 = User.objects.create_user(username='viewer2', password='testpass123')
        self.category = Category.objects.create(name='Detail Testing')
        self.book = Book.objects.create(title='Detail Book', author='Detail Author', description='Detail desc.', category=self.category)

    def test_detail_view_status_code(self):
        response = self.client.get(reverse('core:book_detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_avg_rating_no_ratings(self):
        response = self.client.get(reverse('core:book_detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.context['avg_rating'], 0.0)

    def test_detail_view_avg_rating_with_ratings(self):
        Rating.objects.create(book=self.book, user=self.user1, rating=3)
        Rating.objects.create(book=self.book, user=self.user2, rating=5)
        response = self.client.get(reverse('core:book_detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.context['avg_rating'], 4.0)

    def test_detail_view_uses_correct_template(self):
        response = self.client.get(reverse('core:book_detail', kwargs={'pk': self.book.pk}))
        self.assertTemplateUsed(response, 'core/book_detail.html')

    def test_detail_view_supplies_estimated_read_minutes(self):
        response = self.client.get(reverse('core:book_detail', kwargs={'pk': self.book.pk}))
        self.assertIn('estimated_read_minutes', response.context)
        self.assertGreaterEqual(response.context['estimated_read_minutes'], 1)


class AjaxRatingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ajaxuser', password='testpass123')
        self.category = Category.objects.create(name='Ajax Fiction')
        self.book = Book.objects.create(title='Ajax Book', author='Author', description='Desc', category=self.category)
        self.url = reverse('core:submit_rating_ajax', kwargs={'pk': self.book.pk})

    def test_unauthenticated_user_redirected(self):
        response = self.client.post(self.url, {'rating': 5})
        self.assertEqual(response.status_code, 302)

    def test_authenticated_rating_success(self):
        self.client.login(username='ajaxuser', password='testpass123')
        response = self.client.post(self.url, {'rating': '4'})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['user_rating'], 4)
        self.assertAlmostEqual(data['new_average_rating'], 4.0)
        self.assertEqual(data['new_rating_count'], 1)

    def test_invalid_rating_rejected(self):
        self.client.login(username='ajaxuser', password='testpass123')
        response = self.client.post(self.url, {'rating': '8'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_rating_update_on_resubmission(self):
        self.client.login(username='ajaxuser', password='testpass123')
        self.client.post(self.url, {'rating': '3'})
        self.client.post(self.url, {'rating': '5'})
        self.assertEqual(self.book.ratings.count(), 1)
        self.assertEqual(self.book.ratings.first().rating, 5)


class AjaxCommentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='commenter', password='testpass123')
        self.category = Category.objects.create(name='Comment Testing')
        self.book = Book.objects.create(title='Comment Book', author='Author', description='Desc', category=self.category)
        self.url = reverse('core:submit_comment_ajax', kwargs={'pk': self.book.pk})

    def test_unauthenticated_user_redirected(self):
        response = self.client.post(self.url, {'content': 'Hello'})
        self.assertEqual(response.status_code, 302)

    def test_authenticated_comment_success(self):
        self.client.login(username='commenter', password='testpass123')
        response = self.client.post(self.url, {'content': 'Great book!'})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('Great book!', data['comment_html'])
        self.assertEqual(data['comment_count'], 1)

    def test_empty_comment_rejected(self):
        self.client.login(username='commenter', password='testpass123')
        response = self.client.post(self.url, {'content': ''})
        data = response.json()
        self.assertFalse(data['success'])


class BookListViewTests(TestCase):
    def setUp(self):
        self.cat1 = Category.objects.create(name='Classic')
        self.cat2 = Category.objects.create(name='Mystery')
        self.book1 = Book.objects.create(
            title='Pride and Prejudice', author='Jane Austen', description='A classic novel.', category=self.cat1
        )
        self.book2 = Book.objects.create(
            title='Sherlock Holmes', author='Arthur Conan Doyle', description='A mystery novel.', category=self.cat2
        )

    def test_book_list_status_code(self):
        response = self.client.get(reverse('core:book_list'))
        self.assertEqual(response.status_code, 200)

    def test_search_filter(self):
        response = self.client.get(reverse('core:book_list'), {'q': 'Pride'})
        self.assertContains(response, 'Pride and Prejudice')
        self.assertNotContains(response, 'Sherlock Holmes')

    def test_category_filter(self):
        response = self.client.get(reverse('core:book_list'), {'category': self.cat2.pk})
        self.assertContains(response, 'Sherlock Holmes')
        self.assertNotContains(response, 'Pride and Prejudice')

    def test_filtered_homepage_hides_editorial_sections(self):
        response = self.client.get(reverse('core:book_list'), {'q': 'Pride'})
        self.assertNotContains(response, 'Community spotlight')
        self.assertNotContains(response, 'Editor and community picks')

    def test_homepage_supplies_showcase_and_filter_context(self):
        response = self.client.get(reverse('core:book_list'))
        self.assertIn('category_showcase', response.context)
        self.assertIn('featured_books', response.context)
        self.assertIn('latest_comments', response.context)
        self.assertEqual(response.context['selected_sort'], 'top')

    def test_discussion_sort_uses_distinct_comment_count(self):
        reader = User.objects.create_user(username='disc_reader', password='pass1234')
        second_reader = User.objects.create_user(username='disc_reader2', password='pass1234')
        Comment.objects.create(book=self.book1, user=reader, content='First comment')
        Comment.objects.create(book=self.book1, user=second_reader, content='Second comment')
        Rating.objects.create(book=self.book1, user=reader, rating=5)
        Rating.objects.create(book=self.book1, user=second_reader, rating=4)

        response = self.client.get(reverse('core:book_list'), {'sort': 'discussion'})
        discussed_book = next(book for book in response.context['books'] if book.pk == self.book1.pk)
        self.assertEqual(discussed_book.comment_count, 2)
        self.assertEqual(discussed_book.rating_count, 2)


class RegistrationViewTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())


class DashboardPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='norm', password='pass1234')
        self.staff = User.objects.create_user(username='admin', password='pass1234', is_staff=True)

    def test_anon_redirected(self):
        self.assertEqual(self.client.get(reverse('core:dashboard')).status_code, 302)

    def test_normal_user_forbidden(self):
        self.client.login(username='norm', password='pass1234')
        self.assertEqual(self.client.get(reverse('core:dashboard')).status_code, 403)

    def test_staff_allowed(self):
        self.client.login(username='admin', password='pass1234')
        self.assertEqual(self.client.get(reverse('core:dashboard')).status_code, 200)


class AiFallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reader', password='pass1234')
        category = Category.objects.create(name='Fantasy')
        self.book = Book.objects.create(
            title='The Name of the Wind',
            author='Patrick Rothfuss',
            description='A lyrical fantasy story.',
            category=category,
        )
        Rating.objects.create(book=self.book, user=self.user, rating=5)
        self.url = reverse('core:get_ai_response')

    def test_requires_login(self):
        response = self.client.post(self.url, {'message': 'Recommend fantasy'})
        self.assertEqual(response.status_code, 302)

    def test_returns_local_recommendation_without_api_key(self):
        self.client.login(username='reader', password='pass1234')
        response = self.client.post(self.url, {'message': 'Recommend a fantasy book'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('The Name of the Wind', response.json()['response'])


class AuthenticationFlowTests(TestCase):
    def test_login_page_preserves_next_parameter(self):
        response = self.client.get(reverse('login'), {'next': reverse('core:chat')})
        self.assertContains(response, 'name="next"')
        self.assertContains(response, reverse('core:chat'))


class DashboardCrudTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staffuser', password='pass1234', is_staff=True)
        self.category = Category.objects.create(name='Original Category')
        self.book = Book.objects.create(
            title='Original Title',
            author='Original Author',
            description='Original description',
            category=self.category,
        )
        self.client.login(username='staffuser', password='pass1234')

    def test_staff_can_add_book(self):
        response = self.client.post(reverse('core:add_book'), {
            'title': 'New Book',
            'author': 'New Author',
            'description': 'Fresh description',
            'category': self.category.pk,
            'cover_url': 'https://example.com/cover.jpg',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Book.objects.filter(title='New Book').exists())

    def test_staff_can_edit_book(self):
        response = self.client.post(reverse('core:edit_book', kwargs={'pk': self.book.pk}), {
            'title': 'Updated Title',
            'author': self.book.author,
            'description': self.book.description,
            'category': self.category.pk,
            'cover_url': '',
        })
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, 'Updated Title')

    def test_staff_can_add_and_edit_category(self):
        add_response = self.client.post(reverse('core:add_category'), {'name': 'Added Category'})
        self.assertEqual(add_response.status_code, 302)
        added = Category.objects.get(name='Added Category')

        edit_response = self.client.post(reverse('core:edit_category', kwargs={'pk': added.pk}), {'name': 'Renamed Category'})
        self.assertEqual(edit_response.status_code, 302)
        added.refresh_from_db()
        self.assertEqual(added.name, 'Renamed Category')

    def test_delete_category_blocked_when_books_exist(self):
        response = self.client.post(reverse('core:delete_category', kwargs={'pk': self.category.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_staff_can_delete_book(self):
        response = self.client.post(reverse('core:delete_book', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_delete_book_rejects_get_requests(self):
        self.book = Book.objects.create(title='Second Book', author='Author', description='Desc', category=self.category)
        response = self.client.get(reverse('core:delete_book', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())
