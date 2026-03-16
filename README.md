# BookVibe - Book Rating & Recommendation Platform

**BookVibe** is a user-friendly book discovery, rating, and discussion platform built with Python and Django. Users can browse books by category, rate books from 1–5 stars, post comments, and chat with an AI assistant for personalised book recommendations.

This project was developed as part of the Internet Technology (M) course at the University of Glasgow.

## Key Features

*   **User Authentication** – Secure registration, login, and logout (M1, M2).
*   **Book Catalogue** – Browse a paginated list of books with cover images, ratings, and categories (M3).
*   **Star Ratings** – Rate books 1–5 stars; average ratings update in real time via AJAX (M4, M5).
*   **Comments** – Post comments on book pages, submitted asynchronously (C2).
*   **Search & Filter** – Search by title/author and filter by category (S1, S2).
*   **AI Chat** – Get personalised book recommendations from DeepSeek AI (C1).
*   **Custom Admin Dashboard** – Add, edit, and delete books and categories through a dedicated dashboard (M6).
*   **Responsive Design** – Built with Bootstrap 5, fully responsive across mobile, tablet, and desktop.
*   **Accessibility** – Skip-to-content link, visible focus indicators, ARIA live regions, and accessible form error handling.
*   **Sustainability** – Lazy-loaded images, external CSS/JS, no unused dependencies.

## Tech Stack

*   **Backend:** Python 3.9+, Django 4.2+
*   **Frontend:** HTML5, CSS3, JavaScript (vanilla), Bootstrap 5
*   **Database:** PostgreSQL (production) / SQLite3 (development)
*   **Deployment:** Gunicorn, Whitenoise, Render.com
*   **Testing:** Django TestCase

## Project Structure

```
bookvibe/
├── manage.py
├── requirements.txt
├── build.sh                    # Render deployment script
├── project_config/             # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                       # Main application
│   ├── models.py               # Book, Category, Rating, Comment
│   ├── views.py                # All views (public + admin dashboard)
│   ├── urls.py                 # URL routing
│   ├── forms.py                # Django forms
│   ├── admin.py                # Django admin registration
│   └── tests.py                # Unit tests
├── templates/
│   ├── base.html               # Base layout (template inheritance)
│   ├── core/                   # App templates
│   │   ├── book_list.html
│   │   ├── book_detail.html
│   │   ├── chat.html
│   │   ├── contact.html
│   │   ├── faq.html
│   │   ├── dashboard.html
│   │   ├── add_book.html / edit_book.html
│   │   ├── add_category.html / edit_category.html
│   │   └── partials/comment.html
│   └── registration/
│       ├── login.html
│       └── register.html
└── static/
    ├── css/style.css           # All custom styles
    └── js/main.js              # All custom JavaScript
```

## Local Development Setup

### Prerequisites

*   Python 3.9+
*   `pip` (Python package installer)

### 1. Create and Activate a Virtual Environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply Migrations

```bash
python manage.py migrate
```

### 4. (Optional) Seed Demo Data

```bash
python manage.py seed_demo_data
```

This loads sample categories, books, ratings, comments, a demo reader, and a demo admin for fast demos.

### 5. Create a Superuser

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at **http://127.0.0.1:8000/**.

*   Book List: `http://127.0.0.1:8000/`
*   Admin Dashboard: `http://127.0.0.1:8000/dashboard/` (requires staff/superuser)
*   Django Admin: `http://127.0.0.1:8000/admin/`

### 7. (Optional) Set Up AI Chat

To enable live AI chat responses, set the `DEEPSEEK_API_KEY` environment variable. If it is not set, BookVibe falls back to local catalogue recommendations so the chat demo still works:

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

## Running Tests

```bash
python manage.py test core
```

The test suite covers: model business logic (average rating calculation), AJAX rating endpoint, AJAX comment endpoint, book list search/filter, registration flow, and view template rendering.
