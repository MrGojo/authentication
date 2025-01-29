from flask import Flask, request, render_template, redirect, url_for
import re
import sqlite3
import os
import jwt
import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Directory to store uploaded photos
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database path
DATABASE_PATH = os.getenv('DATABASE_URL', 'database/users.db')

# Secret key for JWT
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_secret_key_here')

# Initialize the database
def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
         CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        gender TEXT NOT NULL,
        age INTEGER NOT NULL,
        location_lat REAL,
        location_long REAL,
        state TEXT NOT NULL,
        district TEXT NOT NULL
        )
    ''')

    # Preferences Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget INTEGER,
            preferred_gender TEXT,
            preferred_budget INTEGER,
            preferred_location TEXT,
            height REAL,
            interests TEXT,
            qualities TEXT,
            drinking TEXT,
            smoking TEXT,
            religion TEXT,
            prompt TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Photos Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# Route to serve the Sign-Up page
@app.route('/')
def signup_page():
    return render_template('signup.html')

# Route to handle the Sign-Up form submission
@app.route('/signup', methods=['POST'])
def signup():
    # Collect form data
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    gender = request.form.get('gender')
    age = request.form.get('age')
    location_lat = request.form.get('location_lat')
    location_long = request.form.get('location_long')
    state = request.form.get('state')
    district = request.form.get('district')
    budget = request.form.get('budget')
    preferred_gender = request.form.get('preferred_gender')
    preferred_budget = request.form.get('preferred_budget')
    preferred_location = request.form.get('preferred_location')
    height = request.form.get('height')
    interests = request.form.get('interests')
    qualities = request.form.get('qualities')
    drinking = request.form.get('drinking')
    smoking = request.form.get('smoking')
    religion = request.form.get('religion')
    prompt = request.form.get('prompt')
    photos = request.files.getlist('photos')

    # Validate inputs
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format", 400
    if password != confirm_password:
        return "Passwords do not match", 400
    if not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        return "Password must contain at least one number, one uppercase letter, and one special symbol", 400
    if not state or not district:
        return "State and District must be selected", 400
    if len(photos) < 1 or len(photos) > 6:
        return "Please upload between 1 and 6 photos", 400

    # Generate JWT
    payload = {
        'email': email,
        'full_name': full_name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)  # Token expiration: 30 days
    }
    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    try:
        # Save user data
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (full_name, email, password, gender, age, location_lat, location_long, state, district)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, email, jwt_token, gender, age, location_lat, location_long, state, district))
        user_id = cursor.lastrowid  # Get the inserted user's ID

        # Save preferences
        cursor.execute('''
            INSERT INTO preferences (user_id, budget, preferred_gender, preferred_budget, preferred_location, height, interests, qualities, drinking, smoking, religion, prompt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, budget, preferred_gender, preferred_budget, preferred_location, height, interests, qualities, drinking, smoking, religion, prompt))

        # Save photos
        for photo in photos:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            cursor.execute('INSERT INTO photos (user_id, photo_path) VALUES (?, ?)', (user_id, photo_path))

        conn.commit()
        conn.close()
        return redirect(url_for('signin_page'))
    except sqlite3.IntegrityError:
        return "User with this email already exists", 400

# Route to serve the Sign-In page
@app.route('/signin')
def signin_page():
    return render_template('signin.html')

# Route to handle the Sign-In form submission
@app.route('/signin', methods=['POST'])
def signin():
    email = request.form.get('email')
    password = request.form.get('password')  # Optional for validation

    # Fetch JWT from the database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, password FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    # If user not found
    if user is None:
        return "User not found", 404

    user_id, stored_jwt = user

    # Validate JWT
    try:
        decoded_jwt = jwt.decode(stored_jwt, SECRET_KEY, algorithms=['HS256'])
        return f"Welcome back, {decoded_jwt['full_name']}!", 200
    except jwt.ExpiredSignatureError:
        return "Token has expired. Please sign in again.", 401
    except jwt.InvalidTokenError:
        return "Invalid token. Authentication failed.", 401

if __name__ == '__main__':
    app.run(debug=True)
