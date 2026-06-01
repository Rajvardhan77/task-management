import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_db_connection
from datetime import datetime

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your_secret_key_here'  # Replace with a secure, random secret key

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()
        if user_data:
            return User(id=user_data['id'], username=user_data['username'], email=user_data['email'])
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Custom filter to format datetime
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%B %d, %Y %I:%M %p'):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(format)

@app.route('/')
def index():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        # Fetch posts with author name
        query = """
            SELECT posts.id, posts.title, posts.content, posts.created_at, users.username as author 
            FROM posts 
            JOIN users ON posts.author_id = users.id 
            ORDER BY posts.created_at DESC
        """
        cursor.execute(query)
        posts = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('index.html', posts=posts)
    except Exception as e:
        return f"An error occurred while fetching posts: {e}"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('signup.html')
            
        hashed_password = generate_password_hash(password)
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("Username or email already exists.", "danger")
                cursor.close()
                connection.close()
                return render_template('signup.html')
                
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Signup error: {e}", "danger")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username_or_email = request.form['username_or_email'].strip()
        password = request.form['password']
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM users WHERE username = %s OR email = %s",
                (username_or_email, username_or_email)
            )
            user_data = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User(id=user_data['id'], username=user_data['username'], email=user_data['email'])
                login_user(user)
                flash("Logged in successfully!", "success")
                return redirect(url_for('index'))
            else:
                flash("Invalid credentials.", "danger")
        except Exception as e:
            flash(f"Login error: {e}", "danger")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        if not title or not content:
            flash("Title and content cannot be empty.", "danger")
            return render_template('create_post.html')
            
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO posts (title, content, author_id) VALUES (%s, %s, %s)",
                (title, content, current_user.id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash("Post published successfully!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error publishing post: {e}", "danger")
            
    return render_template('create_post.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get post details
        query_post = """
            SELECT posts.id, posts.title, posts.content, posts.created_at, posts.author_id, users.username as author 
            FROM posts 
            JOIN users ON posts.author_id = users.id 
            WHERE posts.id = %s
        """
        cursor.execute(query_post, (post_id,))
        post = cursor.fetchone()
        
        if not post:
            cursor.close()
            connection.close()
            return "Post not found", 404
            
        # Get comments
        query_comments = """
            SELECT comments.id, comments.content, comments.created_at, users.username as author 
            FROM comments 
            JOIN users ON comments.user_id = users.id 
            WHERE comments.post_id = %s 
            ORDER BY comments.created_at ASC
        """
        cursor.execute(query_comments, (post_id,))
        comments = cursor.fetchall()
        
        cursor.close()
        connection.close()
        return render_template('post_detail.html', post=post, comments=comments)
    except Exception as e:
        return f"Error loading post: {e}"

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        
        if not post:
            cursor.close()
            connection.close()
            return "Post not found", 404
            
        if post['author_id'] != current_user.id:
            cursor.close()
            connection.close()
            flash("You are not authorized to edit this post.", "danger")
            return redirect(url_for('post_detail', post_id=post_id))
            
        if request.method == 'POST':
            title = request.form['title'].strip()
            content = request.form['content'].strip()
            
            if not title or not content:
                flash("Title and content cannot be empty.", "danger")
                cursor.close()
                connection.close()
                return render_template('edit_post.html', post=post)
                
            cursor.execute(
                "UPDATE posts SET title = %s, content = %s WHERE id = %s",
                (title, content, post_id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash("Post updated successfully!", "success")
            return redirect(url_for('post_detail', post_id=post_id))
            
        cursor.close()
        connection.close()
        return render_template('edit_post.html', post=post)
    except Exception as e:
        return f"Error editing post: {e}"

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
        post = cursor.fetchone()
        
        if not post:
            cursor.close()
            connection.close()
            return "Post not found", 404
            
        if post['author_id'] != current_user.id:
            cursor.close()
            connection.close()
            flash("You are not authorized to delete this post.", "danger")
            return redirect(url_for('post_detail', post_id=post_id))
            
        cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash("Post deleted successfully!", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error deleting post: {e}", "danger")
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form['content'].strip()
    
    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for('post_detail', post_id=post_id))
        
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)",
            (post_id, current_user.id, content)
        )
        connection.commit()
        cursor.close()
        connection.close()
        flash("Comment added successfully!", "success")
    except Exception as e:
        flash(f"Error adding comment: {e}", "danger")
        
    return redirect(url_for('post_detail', post_id=post_id))

if __name__ == "__main__":
    app.run(debug=True)
