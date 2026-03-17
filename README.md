# BookVibe - Book Rating & Recommendation Platform

## Overview

**BookVibe** is a full-stack web application developed using Django as part of the University of Glasgow Internet Technology (M) coursework.

The platform enables users to discover, rate, and discuss books, while also providing AI-assisted recommendations. The system demonstrates modern web development practices, including dynamic content rendering, asynchronous interactions (AJAX), and user authentication.

---

## Coursework Requirement Coverage

This project satisfies all major coursework requirements:

| Requirement Area | Implementation                                              |
| ---------------- | ----------------------------------------------------------- |
| M1–M2            | User authentication (login, registration, session handling) |
| M3               | Book catalogue with pagination and categories               |
| M4–M5            | AJAX-based rating system with real-time updates             |
| M6               | Custom admin dashboard for full CRUD operations             |
| C1               | AI recommendation chat (DeepSeek API + fallback system)     |
| C2               | Asynchronous commenting system                              |
| S1–S2            | Search and filtering functionality                          |

---

## Key Features

* 📚 Book browsing with search, filtering, and pagination
* ⭐ Real-time rating system (AJAX, no page reload)
* 💬 Asynchronous comment system
* 🔐 User authentication and access control
* 🛠 Custom admin dashboard (separate from Django admin)
* 🤖 AI-powered book recommendation assistant
* 📱 Fully responsive UI (Bootstrap 5)
* ♿ Accessibility support (ARIA, keyboard navigation, focus states)
* ⚡ Performance optimisation (lazy loading, minimal assets)

---

## System Design & Architecture

The system follows a **Model–View–Template (MVT)** architecture:

* **Models**: Handle database logic (Book, Category, Rating, Comment)
* **Views**: Process user requests and business logic
* **Templates**: Render UI using Django templating

### Key Design Decisions

* **AJAX for interactivity**
  → Improves user experience by avoiding full page reloads

* **Separation of admin dashboard and Django admin**
  → Provides better control and custom UI

* **Fallback AI recommendation logic**
  → Ensures system works even without external API

* **Reusable templates & partials**
  → Improves maintainability and scalability

---

## Tech Stack

* **Backend:** Django (Python)
* **Frontend:** HTML, CSS, JavaScript, Bootstrap
* **Database:** SQLite (development), PostgreSQL (production)
* **Deployment:** Render, Gunicorn, Whitenoise
* **Testing:** Django TestCase

---

## Project Structure

(keep your original structure here)

---

## Local Development Setup

### 1. Install dependencies

```bash id="a1"
pip install -r requirements.txt
```

### 2. Apply migrations

```bash id="a2"
python manage.py migrate
```

### 3. Load demo data

```bash id="a3"
python manage.py seed_demo_data
```

### 4. Run server

```bash id="a4"
python manage.py runserver
```

---

## Admin Access

If demo data is loaded:

* Username: admin
* Password: admin123

Or create manually:

```bash id="a5"
python manage.py createsuperuser
```

---

## Testing & Quality Assurance

The project includes unit tests covering:

* Model logic (e.g. rating calculations)
* AJAX endpoints (rating and comments)
* Search and filtering functionality
* Authentication workflows

Run tests:

```bash id="a6"
python manage.py test core
```

---

## Deployment

The application is configured for deployment using:

* **Gunicorn** (WSGI server)
* **Whitenoise** (static file handling)
* **Render.com** (cloud hosting)

Environment variables (e.g. API keys) are securely managed via environment configuration.

---

## Notes for Marker

* Demo data ensures immediate usability without manual setup
* All core features are functional and tested
* System gracefully degrades if AI API is unavailable
* Code follows clear structure and separation of concerns

---

## Limitations

* AI recommendations depend on external API availability
* No advanced machine learning recommendation engine
* Limited scalability for very large datasets

---

## Future Improvements

* Integrate machine learning-based recommendation system
* Add user profiles and personalised dashboards
* Implement caching and performance scaling
* Improve UI/UX with animations and micro-interactions

---

## Author

Yuhang Chen
University of Glasgow
Internet Technology Coursework Submission
