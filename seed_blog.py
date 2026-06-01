from api.db_config import get_db_connection
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_database():
    print("Connecting to database...")
    conn = get_db_connection()
    # Use dictionary=False for standard tuple execution
    cursor = conn.cursor(dictionary=False)

    print("Clearing old data...")
    # Disable foreign key check temporarily if MySQL to avoid delete order issues, or delete comments first
    cursor.execute("DELETE FROM comments")
    cursor.execute("DELETE FROM posts")
    cursor.execute("DELETE FROM users")
    conn.commit()

    # 1. Create Mock Users
    print("Inserting mock users...")
    users = [
        ("alex_dev", "alex@example.com", generate_password_hash("password123")),
        ("sarah_ux", "sarah@example.com", generate_password_hash("password123")),
        ("code_master", "master@example.com", generate_password_hash("password123"))
    ]
    for user in users:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            user
        )
    conn.commit()

    # Get user ids
    # Re-obtain cursor with dictionary=True to map username to id
    cursor.close()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users")
    user_map = {row["username"]: row["id"] for row in cursor.fetchall()}
    cursor.close()

    # 2. Create Mock Blog Posts
    print("Inserting mock posts...")
    cursor = conn.cursor(dictionary=False)
    now = datetime.now()
    posts = [
        (
            "The Rise of Agentic AI Workflows",
            "Artificial Intelligence is shifting from simple prompt-response interactions to fully agentic workflows. Instead of just answering questions, modern AI agents can call APIs, run terminal commands, verify their code execution, and correct their own errors. This shift enables developers to build self-correcting systems that automate complex software engineering pipelines. To prepare for this future, developers should focus on creating clean modular codebases that can be easily parsed and tested by autonomous software agents.",
            user_map["alex_dev"],
            (now - timedelta(days=2))
        ),
        (
            "Sleek Aesthetics in Modern Web Design",
            "First impressions are everything on the modern web. Gone are the days of plain white interfaces and generic borders. The current design zeitgeist prioritizes vibrant gradient accents, glassmorphic card layouts (semi-transparent backgrounds with backdrop blur), and micro-animations. Applying custom CSS variables allows developers to build robust, cohesive light and dark themes. Remember: premium design is not just how it looks, but how it behaves. Adding smooth scale transitions on hover and subtle box-shadow expansions makes the user experience feel tactile and alive.",
            user_map["sarah_ux"],
            (now - timedelta(days=1))
        ),
        (
            "Why We Still Love SQLite for Local Development",
            "When building local prototypes or small-scale web applications, SQLite remains one of the best tools in a developer's toolkit. It requires zero configuration, has no daemon process to maintain, and stores the entire database in a single file. Modern wrappers make it simple to switch between SQLite during development and robust databases like MySQL or PostgreSQL in production. In fact, by writing compliant ANSI SQL and utilizing adapters, you can prototype offline with SQLite and deploy online to the cloud with zero code modifications.",
            user_map["code_master"],
            (now - timedelta(hours=6))
        )
    ]
    for post in posts:
        cursor.execute(
            "INSERT INTO posts (title, content, author_id, created_at) VALUES (%s, %s, %s, %s)",
            post
        )
    conn.commit()

    # Get post ids
    cursor.close()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title FROM posts")
    post_map = {row["title"]: row["id"] for row in cursor.fetchall()}
    cursor.close()

    # 3. Create Mock Comments
    print("Inserting mock comments...")
    cursor = conn.cursor(dictionary=False)
    comments = [
        # Comments on Post 1
        (
            post_map["The Rise of Agentic AI Workflows"],
            user_map["sarah_ux"],
            "Fascinating writeup! I love the concept of AI self-correction. How do you see this impacting UI/UX design tools?",
            (now - timedelta(days=1, hours=12))
        ),
        (
            post_map["The Rise of Agentic AI Workflows"],
            user_map["code_master"],
            "Completely agree. Writing test-driven code (TDD) will become even more vital as AI developers write more code.",
            (now - timedelta(days=1, hours=4))
        ),
        # Comments on Post 2
        (
            post_map["Sleek Aesthetics in Modern Web Design"],
            user_map["alex_dev"],
            "Glassmorphism looks incredible when done right, but the performance cost of backdrop-blur can sometimes be high on low-end mobile devices.",
            (now - timedelta(hours=18))
        ),
        # Comments on Post 3
        (
            post_map["Why We Still Love SQLite for Local Development"],
            user_map["alex_dev"],
            "Totally! The single-file storage format makes creating database backups as simple as copying a file.",
            (now - timedelta(hours=3))
        )
    ]
    for comment in comments:
        cursor.execute(
            "INSERT INTO comments (post_id, user_id, content, created_at) VALUES (%s, %s, %s, %s)",
            comment
        )
    conn.commit()

    cursor.close()
    conn.close()
    print("Database successfully seeded!")

if __name__ == "__main__":
    seed_database()
