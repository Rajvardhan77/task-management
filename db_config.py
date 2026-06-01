import mysql.connector
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Helper to parse datetime from sqlite
def parse_datetime(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            pass
    return val

class UnifiedCursorWrapper:
    def __init__(self, cursor, is_sqlite, dictionary=False):
        self.cursor = cursor
        self.is_sqlite = is_sqlite
        self.dictionary = dictionary

    def execute(self, query, params=None):
        if self.is_sqlite:
            query = query.replace('%s', '?')
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not self.dictionary:
            return rows

        res = []
        for row in rows:
            d = dict(row) if self.is_sqlite else row
            
            # Map submission_time to submitted_at, and parse datetime if SQLite
            if 'submission_time' in d:
                val = d['submission_time']
                if self.is_sqlite and val:
                    val = parse_datetime(val)
                d['submission_time'] = val
                d['submitted_at'] = val
            elif 'submitted_at' in d:
                val = d['submitted_at']
                if self.is_sqlite and val:
                    val = parse_datetime(val)
                d['submitted_at'] = val

            res.append(d)
        return res

    def close(self):
        self.cursor.close()

    def __getattr__(self, name):
        return getattr(self.cursor, name)

class UnifiedConnectionWrapper:
    def __init__(self, conn, is_sqlite):
        self.conn = conn
        self.is_sqlite = is_sqlite

    def cursor(self, dictionary=False):
        if self.is_sqlite:
            self.conn.row_factory = sqlite3.Row
            return UnifiedCursorWrapper(self.conn.cursor(), is_sqlite=True, dictionary=dictionary)
        else:
            return UnifiedCursorWrapper(self.conn.cursor(dictionary=dictionary), is_sqlite=False, dictionary=dictionary)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __getattr__(self, name):
        return getattr(self.conn, name)

def get_db_connection():
    try:
        # Try connecting to MySQL with a short timeout (e.g. 3s) so local startup is fast
        conn = mysql.connector.connect(
            host="245124737102.mysql.pythonanywhere-services.com",
            user="245124737102",
            password="R@jvardhan25",
            database="245124737102$default",
            connection_timeout=3
        )
        print("Connected to remote MySQL database.")
        
        # Ensure tables exist on MySQL
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                author_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                post_id INT NOT NULL,
                user_id INT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
        
        return UnifiedConnectionWrapper(conn, is_sqlite=False)
    except Exception as e:
        print(f"Could not connect to remote MySQL database: {e}")
        print("Falling back to local SQLite database.")
        
        # Use /tmp folder if running on Vercel serverless environment (since root directory is read-only)
        if 'VERCEL' in os.environ or 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            db_path = "/tmp/blog.db"
            print("Detected Vercel runtime. Using /tmp/blog.db for write support.")
        else:
            db_path = os.path.join(os.path.dirname(__file__), "blog.db")
            print(f"Using local path: {db_path}")
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        
        # Check if database is empty and auto-seed if so
        cursor.execute("SELECT COUNT(*) FROM posts")
        if cursor.fetchone()[0] == 0:
            print("Auto-seeding default articles and users...")
            
            # 1. Users
            users = [
                ("alex_dev", "alex@example.com", generate_password_hash("password123")),
                ("sarah_ux", "sarah@example.com", generate_password_hash("password123")),
                ("code_master", "master@example.com", generate_password_hash("password123"))
            ]
            cursor.executemany("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", users)
            conn.commit()
            
            # Get user IDs mapping
            cursor.execute("SELECT id, username FROM users")
            user_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # 2. Posts
            now = datetime.now()
            posts = [
                (
                    "The Rise of Agentic AI Workflows",
                    "Artificial Intelligence is shifting from simple prompt-response interactions to fully agentic workflows. Instead of just answering questions, modern AI agents can call APIs, run terminal commands, verify their code execution, and correct their own errors. This shift enables developers to build self-correcting systems that automate complex software engineering pipelines. To prepare for this future, developers should focus on creating clean modular codebases that can be easily parsed and tested by autonomous software agents.",
                    user_map["alex_dev"],
                    (now - timedelta(days=2)).isoformat()
                ),
                (
                    "Sleek Aesthetics in Modern Web Design",
                    "First impressions are everything on the modern web. Gone are the days of plain white interfaces and generic borders. The current design zeitgeist prioritizes vibrant gradient accents, glassmorphic card layouts (semi-transparent backgrounds with backdrop blur), and micro-animations. Applying custom CSS variables allows developers to build robust, cohesive light and dark themes. Remember: premium design is not just how it looks, but how it behaves. Adding smooth scale transitions on hover and subtle box-shadow expansions makes the user experience feel tactile and alive.",
                    user_map["sarah_ux"],
                    (now - timedelta(days=1)).isoformat()
                ),
                (
                    "Why We Still Love SQLite for Local Development",
                    "When building local prototypes or small-scale web applications, SQLite remains one of the best tools in a developer's toolkit. It requires zero configuration, has no daemon process to maintain, and stores the entire database in a single file. Modern wrappers make it simple to switch between SQLite during development and robust databases like MySQL or PostgreSQL in production. In fact, by writing compliant ANSI SQL and utilizing adapters, you can prototype offline with SQLite and deploy online to the cloud with zero code modifications.",
                    user_map["code_master"],
                    (now - timedelta(hours=6)).isoformat()
                )
            ]
            cursor.executemany("INSERT INTO posts (title, content, author_id, created_at) VALUES (?, ?, ?, ?)", posts)
            conn.commit()
            
            # Get post IDs mapping
            cursor.execute("SELECT id, title FROM posts")
            post_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # 3. Comments
            comments = [
                (
                    post_map["The Rise of Agentic AI Workflows"],
                    user_map["sarah_ux"],
                    "Fascinating writeup! I love the concept of AI self-correction. How do you see this impacting UI/UX design tools?",
                    (now - timedelta(days=1, hours=12)).isoformat()
                ),
                (
                    post_map["The Rise of Agentic AI Workflows"],
                    user_map["code_master"],
                    "Completely agree. Writing test-driven code (TDD) will become even more vital as AI developers write more code.",
                    (now - timedelta(days=1, hours=4)).isoformat()
                ),
                (
                    post_map["Sleek Aesthetics in Modern Web Design"],
                    user_map["alex_dev"],
                    "Glassmorphism looks incredible when done right, but the performance cost of backdrop-blur can sometimes be high on low-end mobile devices.",
                    (now - timedelta(hours=18)).isoformat()
                ),
                (
                    post_map["Why We Still Love SQLite for Local Development"],
                    user_map["alex_dev"],
                    "Totally! The single-file storage format makes creating database backups as simple as copying a file.",
                    (now - timedelta(hours=3)).isoformat()
                )
            ]
            cursor.executemany("INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)", comments)
            conn.commit()
            
        cursor.close()
        return UnifiedConnectionWrapper(conn, is_sqlite=True)
