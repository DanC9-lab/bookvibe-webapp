from __future__ import annotations

import requests

from dataclasses import dataclass

import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Book, Category, Comment, Rating
class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        # Prevent duplicate data insertion:
        # If the database already contains books, skip seeding
        if Book.objects.exists():
            self.stdout.write("Seed skipped: data already exists.")
            return

        self.stdout.write("Seeding database...")

        # ---------------------------
        # Create categories
        # ---------------------------
        fiction = Category.objects.create(name="Fiction")
        non_fiction = Category.objects.create(name="Non-fiction")
        sci_fi = Category.objects.create(name="Sci-Fi")

        # ---------------------------
        # Create demo user
        # ---------------------------
        user, _ = User.objects.get_or_create(
            username="demo_user",
            defaults={"email": "demo@example.com"}
        )

        # ---------------------------
        # Create books
        # ---------------------------
        books = [
            ("1984", "George Orwell", fiction),
            ("To Kill a Mockingbird", "Harper Lee", fiction),
            ("The Great Gatsby", "F. Scott Fitzgerald", fiction),
            ("Dune", "Frank Herbert", sci_fi),
            ("Foundation", "Isaac Asimov", sci_fi),
            ("Sapiens", "Yuval Noah Harari", non_fiction),
            ("Educated", "Tara Westover", non_fiction),
        ]

        created_books = []

        for title, author, category in books:
            book = Book.objects.create(
                title=title,
                author=author,
                description=f"A book titled '{title}' by {author}.",
                category=category
            )
            created_books.append(book)

        # ---------------------------
        # Add ratings and comments
        # ---------------------------
        for book in created_books:
            Rating.objects.create(
                user=user,
                book=book,
                score=4
            )

            Comment.objects.create(
                user=user,
                book=book,
                content=f"I enjoyed reading {book.title}."
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully."))

CATEGORY_LIBRARY = [
    {
        'name': 'Fiction',
        'description': 'Contemporary and literary fiction driven by memorable voices, relationships, and atmosphere.',
        'books': [
            ('1984', 'George Orwell', 'A chilling literary classic about surveillance, truth, and personal freedom in a controlled society.'),
            ('To Kill a Mockingbird', 'Harper Lee', 'A compassionate novel of justice, childhood, and moral courage in the American South.'),
            ('The Kite Runner', 'Khaled Hosseini', 'A deeply emotional story of friendship, guilt, and redemption across decades of change.'),
            ('Atonement', 'Ian McEwan', 'A beautifully crafted novel about memory, regret, and the lasting consequences of one accusation.'),
        ],
    },
    {
        'name': 'Classics',
        'description': 'Enduring works that continue to shape reading culture across generations.',
        'books': [
            ('Pride and Prejudice', 'Jane Austen', 'A witty and elegant classic about love, family expectations, and self-awareness.'),
            ('Jane Eyre', 'Charlotte Bronte', 'A deeply felt romantic classic about dignity, desire, and independence.'),
            ('Wuthering Heights', 'Emily Bronte', 'A dark and passionate gothic novel of obsession, revenge, and the Yorkshire moors.'),
            ('The Great Gatsby', 'F. Scott Fitzgerald', 'A glittering, tragic portrait of wealth, longing, and the American dream.'),
            ('Moby-Dick', 'Herman Melville', 'A vast sea-bound epic of obsession, fate, and the unknowable world.'),
        ],
    },
    {
        'name': 'Mystery & Thriller',
        'description': 'Unsolved puzzles, hidden motives, dark secrets, and page-turning suspense.',
        'books': [
            ('And Then There Were None', 'Agatha Christie', 'A masterful closed-circle mystery where tension rises with every chapter.'),
            ('The Girl with the Dragon Tattoo', 'Stieg Larsson', 'A dark investigative thriller with sharp social commentary and unforgettable protagonists.'),
            ('Gone Girl', 'Gillian Flynn', 'A razor-sharp psychological thriller built on deception, media spectacle, and shifting loyalties.'),
            ('The Hound of the Baskervilles', 'Arthur Conan Doyle', 'A legendary Sherlock Holmes mystery wrapped in mist, fear, and folklore.'),
        ],
    },
    {
        'name': 'Science Fiction',
        'description': 'Speculative fiction shaped by technology, future worlds, and big ideas.',
        'books': [
            ('Dune', 'Frank Herbert', 'An epic science-fiction saga of power, ecology, prophecy, and survival.'),
            ('The Three-Body Problem', 'Liu Cixin', 'A visionary first-contact story that scales from cultural upheaval to cosmic stakes.'),
            ('Neuromancer', 'William Gibson', 'A foundational cyberpunk novel of hackers, AI, and life in a digital underworld.'),
            ('Foundation', 'Isaac Asimov', 'A grand future history about science, empire, and the attempt to preserve civilisation.'),
            ('Fahrenheit 451', 'Ray Bradbury', 'A lyrical dystopian novel about censorship, conformity, and the saving power of books.'),
        ],
    },
    {
        'name': 'Fantasy',
        'description': 'Immersive worlds of myth, magic, quests, and wonder.',
        'books': [
            ('The Hobbit', 'J.R.R. Tolkien', 'A warm and adventurous fantasy journey full of courage, wonder, and discovery.'),
            ('Harry Potter and the Philosopher\'s Stone', 'J.K. Rowling', 'A beloved school-of-magic story that opens the door to an enchanting world.'),
            ('A Game of Thrones', 'George R.R. Martin', 'A sweeping political fantasy of rival houses, ancient threats, and uneasy power.'),
            ('The Name of the Wind', 'Patrick Rothfuss', 'A lyrical coming-of-age fantasy centred on talent, storytelling, and ambition.'),
            ('The Last Unicorn', 'Peter S. Beagle', 'A wistful and elegant fantasy about loss, transformation, and wonder.'),
        ],
    },
    {
        'name': 'Romance',
        'description': 'Love stories shaped by chemistry, emotional depth, and unforgettable connections.',
        'books': [
            ('Normal People', 'Sally Rooney', 'A contemporary relationship novel about intimacy, vulnerability, and growth.'),
            ('The Notebook', 'Nicholas Sparks', 'A heartfelt romance about devotion, memory, and enduring love.'),
            ('Me Before You', 'Jojo Moyes', 'An emotional love story about care, change, and difficult choices.'),
            ('Call Me by Your Name', 'Andre Aciman', 'A sensuous and reflective novel of desire, summer, and first love.'),
        ],
    },
    {
        'name': 'History & Biography',
        'description': 'Real lives, defining moments, and narratives that shaped the modern world.',
        'books': [
            ('Steve Jobs', 'Walter Isaacson', 'A richly reported biography of one of the most influential figures in modern technology.'),
            ('Sapiens', 'Yuval Noah Harari', 'A sweeping narrative history of humankind, ideas, and civilisations.'),
            ('The Diary of a Young Girl', 'Anne Frank', 'An essential wartime diary of hope, fear, and extraordinary human resilience.'),
            ('Alexander Hamilton', 'Ron Chernow', 'A major biography tracing ambition, politics, and the making of the United States.'),
        ],
    },
    {
        'name': 'Philosophy & Psychology',
        'description': 'Books about meaning, behaviour, identity, and the life of the mind.',
        'books': [
            ('Sophie\'s World', 'Jostein Gaarder', 'An accessible and imaginative introduction to the history of philosophy.'),
            ('Man\'s Search for Meaning', 'Viktor E. Frankl', 'A profound reflection on suffering, purpose, and the human search for meaning.'),
            ('Thinking, Fast and Slow', 'Daniel Kahneman', 'A landmark guide to judgement, bias, and the two systems that shape human thought.'),
            ('Meditations', 'Marcus Aurelius', 'A stoic classic on discipline, perspective, and inner steadiness.'),
        ],
    },
    {
        'name': 'Business & Economics',
        'description': 'Strategy, leadership, money, decision-making, and the forces that shape markets.',
        'books': [
            ('The Lean Startup', 'Eric Ries', 'A practical framework for building products through testing, feedback, and iteration.'),
            ('Principles', 'Ray Dalio', 'A personal and managerial playbook focused on systems, reflection, and decision-making.'),
            ('The Intelligent Investor', 'Benjamin Graham', 'A foundational investing book centred on discipline, value, and long-term thinking.'),
            ('The Psychology of Money', 'Morgan Housel', 'A clear and engaging look at how behaviour shapes financial outcomes.'),
        ],
    },
    {
        'name': 'Science & Technology',
        'description': 'Scientific ideas and technical thinking explained with clarity and curiosity.',
        'books': [
            ('A Brief History of Time', 'Stephen Hawking', 'A lucid introduction to cosmology, black holes, and the nature of the universe.'),
            ('Clean Code', 'Robert C. Martin', 'A foundational software book about readable, maintainable, and disciplined coding.'),
            ('The Selfish Gene', 'Richard Dawkins', 'A compelling classic on evolution, genes, and the logic of natural selection.'),
            ('The Innovators', 'Walter Isaacson', 'A broad history of the people and ideas behind the digital revolution.'),
        ],
    },
    {
        'name': 'Self-Help',
        'description': 'Practical books for habits, productivity, resilience, and personal growth.',
        'books': [
            ('Atomic Habits', 'James Clear', 'A highly practical guide to building sustainable routines through small improvements.'),
            ('The 7 Habits of Highly Effective People', 'Stephen R. Covey', 'A classic self-development book on values, effectiveness, and long-term growth.'),
            ('Deep Work', 'Cal Newport', 'A persuasive case for focused attention and meaningful concentration in a distracted age.'),
            ('The Power of Now', 'Eckhart Tolle', 'A reflective guide to mindfulness, presence, and stepping back from mental noise.'),
        ],
    },
    {
        'name': 'Young Adult & Graphic Stories',
        'description': 'Coming-of-age fiction and visually driven storytelling full of momentum and heart.',
        'books': [
            ('The Little Prince', 'Antoine de Saint-Exupery', 'A poetic fable about imagination, friendship, and what truly matters.'),
            ('The Fault in Our Stars', 'John Green', 'A tender young-adult novel about love, humour, and mortality.'),
            ('Persepolis', 'Marjane Satrapi', 'A powerful graphic memoir of youth, revolution, and identity.'),
            ('Maus', 'Art Spiegelman', 'A groundbreaking graphic work about memory, trauma, and survival during the Holocaust.'),
        ],
    },
]


COMMENT_BANK = [
    'A book that rewards close reading and stays with you long after the final page.',
    'Excellent pacing and a strong sense of atmosphere from beginning to end.',
    'Easy to recommend when someone wants a reliable, highly rated place to start.',
    'One of those titles that sparks good discussion as soon as people finish it.',
]


@dataclass
class CoverLookupResult:
    cover_url: str = ''
    first_publish_year: Optional[int] = None


class OpenLibraryCoverClient:
    search_endpoint = 'https://openlibrary.org/search.json'
    cover_endpoint = 'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg'

    def __init__(self):
        import requests
       self.session = requests.Session()
        self.cache: dict[tuple[str, str], CoverLookupResult] = {}

    def find_cover(self, title: str, author: str) -> CoverLookupResult:
        cache_key = (title.lower().strip(), author.lower().strip())
        if cache_key in self.cache:
            return self.cache[cache_key]

        result = CoverLookupResult()
        try:
            response = self.session.get(
                self.search_endpoint,
                params={'title': title, 'author': author, 'limit': 12},
                timeout=4,
            )
            response.raise_for_status()
            docs = response.json().get('docs', [])
        except requests.RequestException:
            self.cache[cache_key] = result
            return result

        matching_docs = []
        title_tokens = {token.lower() for token in title.replace(':', ' ').replace(',', ' ').split() if token}
        author_lower = author.lower()
        for doc in docs:
            doc_title = str(doc.get('title', '')).lower()
            doc_author_names = ' '.join(doc.get('author_name', [])).lower()
            if not doc.get('cover_i'):
                continue
            if author_lower and author_lower not in doc_author_names:
                continue
            if title_tokens and not all(token in doc_title for token in list(title_tokens)[:3]):
                continue
            matching_docs.append(doc)

        if not matching_docs:
            matching_docs = [doc for doc in docs if doc.get('cover_i')][:1]

        if matching_docs:
            chosen = sorted(
                matching_docs,
                key=lambda item: item.get('first_publish_year') or 99999,
            )[0]
            result = CoverLookupResult(
                cover_url=self.cover_endpoint.format(cover_id=chosen['cover_i']),
                first_publish_year=chosen.get('first_publish_year'),
            )

        self.cache[cache_key] = result
        return result


class Command(BaseCommand):
    help = 'Seed BookVibe with reader-facing categories, books, ratings, comments, and online cover images.'

    def handle(self, *args, **options):
        cover_client = OpenLibraryCoverClient()
        created_books = []

        for category_payload in CATEGORY_LIBRARY:
            category, _ = Category.objects.get_or_create(name=category_payload['name'])

            for title, author, description in category_payload['books']:
                book, _ = Book.objects.get_or_create(
                    title=title,
                    defaults={
                        'author': author,
                        'description': description,
                        'category': category,
                    },
                )
                cover_result = CoverLookupResult(cover_url=book.cover_url)
                if not book.cover and not book.cover_url:
                    cover_result = cover_client.find_cover(title, author)
                updated_fields = []
                if book.author != author:
                    book.author = author
                    updated_fields.append('author')
                if book.description != description:
                    book.description = description
                    updated_fields.append('description')
                if book.category_id != category.id:
                    book.category = category
                    updated_fields.append('category')
                if cover_result.cover_url and book.cover_url != cover_result.cover_url:
                    book.cover_url = cover_result.cover_url
                    updated_fields.append('cover_url')
                if updated_fields:
                    book.save(update_fields=updated_fields)
                created_books.append(book)

        reader_specs = [
            ('alice_reads', 'alice@bookvibe.test'),
            ('benjamin_turns_pages', 'ben@bookvibe.test'),
            ('clara_booknotes', 'clara@bookvibe.test'),
        ]
        readers = []
        for username, email in reader_specs:
            user, _ = User.objects.get_or_create(username=username, defaults={'email': email})
            if not user.has_usable_password():
                user.set_password('BookVibeReader123!')
                user.save()
            readers.append(user)

        admin_user, _ = User.objects.get_or_create(
            username='bookvibe_admin',
            defaults={'email': 'admin@bookvibe.test', 'is_staff': True, 'is_superuser': True},
        )
        if not admin_user.has_usable_password():
            admin_user.set_password('BookVibeAdmin123!')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        for index, book in enumerate(created_books):
            for reader_index, reader in enumerate(readers):
                rating_value = 5 if (index + reader_index) % 4 else 4
                Rating.objects.update_or_create(book=book, user=reader, defaults={'rating': rating_value})

            Comment.objects.get_or_create(
                book=book,
                user=readers[index % len(readers)],
                content=COMMENT_BANK[index % len(COMMENT_BANK)],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded {len(CATEGORY_LIBRARY)} categories and {len(created_books)} books for BookVibe.'
            )
        )
