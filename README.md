# 📚 BookVibe – Campus Book Recommendation Platform

## 📖 Overview

BookVibe is a Django-based web application designed to help users browse, rate, and discuss books.
It includes dynamic AJAX features and an AI-powered recommendation system.

---

## 🚀 Features

* 📚 Browse and search books
* ⭐ Rating system (AJAX, no page reload)
* 💬 Comment system (AJAX, real-time updates)
* 🤖 AI-powered book recommendations
* 🔐 User authentication (login/register)
* 🛠 Admin dashboard for content management

---

## 🛠 Tech Stack

* Backend: Django (Python)
* Frontend: HTML, CSS, Bootstrap, JavaScript
* Database: SQLite (local) / PostgreSQL (Render)
* API: External AI service (via HTTP requests)

---

## ⚙️ Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Apply migrations

```bash
python manage.py migrate
```

### 3. Seed demo data (IMPORTANT)

```bash
python manage.py seed_demo_data
```

👉 This will populate the database with sample books (50+ records).

### 4. Run the development server

```bash
python manage.py runserver
```

👉 Open: http://127.0.0.1:8000/

---

## 🔄 AJAX Functionality

The application uses AJAX to enhance user experience:

* Rating submissions update instantly without page reload
* Comments appear immediately after posting
* Backend returns JSON responses:

  * `new_average_rating`
  * `new_rating_count`
  * `comment_html`
  * `comment_count`

---

## 🗄 Database Design

Main models:

* **Book**
* **Category**
* **Rating** (One rating per user per book)
* **Comment**

Relationships:

* Book → Category (ForeignKey)
* Rating → Book + User
* Comment → Book + User

---

## 🌐 Deployment

The application is deployed on **Render**.

### Build Command

```bash
python manage.py migrate && python manage.py seed_demo_data
```

### Notes

* Uses PostgreSQL in production
* Static files served via WhiteNoise

---

## 🧪 Testing

Run tests using:

```bash
python manage.py test
```

All tests pass, including:

* AJAX rating submission
* AJAX comment submission
* Database updates and counts

---

## ⚠️ Notes

* Each user can rate a book only once (update_or_create logic)
* Empty comments are rejected
* AJAX endpoints return JSON (not HTML pages)

---

## 📁 Project Structure

```
core/               # Main app (models, views, logic)
project_config/     # Django settings
templates/          # HTML templates
static/             # CSS, JS
manage.py
requirements.txt
build.sh
```

---

## 👨‍💻 Author

Yuhang Chen
University of Glasgow

---

## ✅ Submission Notes

* Virtual environment (`venv/`) removed
* `.git/` removed
* Database not included (use seed script instead)
* Project fully reproducible using instructions above

---
