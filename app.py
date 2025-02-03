from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash
import re
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from location_data import STATES_AND_DISTRICTS, STATES_LIST

# Load environment variables from .env file
load_dotenv()

# Database path
DATABASE_PATH = os.getenv('DATABASE_URL', 'database/users.db')

def init_db():
    """Initialize the database with all required tables"""
    print("Initializing database...")  # Debug log
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                location_lat REAL,
                location_long REAL,
                state TEXT,
                district TEXT,
                bio TEXT,
                occupation TEXT,
                interests TEXT,
                drinking TEXT,
                smoking TEXT,
                religion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Users table created successfully")  # Debug log

        # Create prompts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt1 TEXT,
                prompt2 TEXT,
                prompt3 TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        print("Prompts table created successfully")  # Debug log

        # Create photos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                photo_path TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        print("Photos table created successfully")  # Debug log

        conn.commit()
        conn.close()
        print("Database initialization completed successfully")  # Debug log
        
    except Exception as e:
        print(f"Error initializing database: {e}")  # Debug log
        raise e

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Directory to store uploaded photos
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create database directory if it doesn't exist
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Initialize database when app starts
init_db()

def save_user_data():
    """Save all user data from session to database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # First, insert basic user info and get user_id
        cursor.execute('''
            INSERT INTO users (
                full_name, email, password, age, gender,
                location_lat, location_long, state, district,
                bio, occupation, interests, drinking, smoking, religion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get('full_name'),
            session.get('email'),
            session.get('password'),
            session.get('age'),
            session.get('gender'),
            session.get('location', {}).get('lat'),
            session.get('location', {}).get('long'),
            session.get('location', {}).get('state'),
            session.get('location', {}).get('district'),
            session.get('bio'),
            session.get('occupation'),
            session.get('interests'),
            session.get('lifestyle', {}).get('drinking'),
            session.get('lifestyle', {}).get('smoking'),
            session.get('lifestyle', {}).get('religion')
        ))
        
        user_id = cursor.lastrowid

        # Insert prompts if they exist
        prompts = session.get('prompts', {})
        if prompts:
            cursor.execute('''
                INSERT INTO prompts (user_id, prompt1, prompt2, prompt3)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                prompts.get('prompt1'),
                prompts.get('prompt2'),
                prompts.get('prompt3')
            ))

        # Insert photos if they exist
        photo_paths = session.get('photo_paths', [])
        for i, photo_path in enumerate(photo_paths):
            cursor.execute('''
                INSERT INTO photos (user_id, photo_path, is_primary)
                VALUES (?, ?, ?)
            ''', (user_id, photo_path, i == 0))

        conn.commit()
        conn.close()
        return True

    except sqlite3.IntegrityError as e:
        print(f"Database integrity error: {e}")
        if 'UNIQUE constraint failed: users.email' in str(e):
            raise Exception('Email already exists')
        raise e
    except Exception as e:
        print(f"Error saving data: {e}")
        raise e

@app.route('/')
def index():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation
        if not all([full_name, email, password, confirm_password]):
            flash('All fields are required')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('signup'))
        
        # Store basic info in session
        session['full_name'] = full_name
        session['email'] = email
        session['password'] = password

        # Redirect to first onboarding step
        return redirect(url_for('onboarding_age'))
    
    return render_template('signup.html')

# Split Signup Routes
@app.route('/signup/personal', methods=['GET', 'POST'])
def signup_personal():
    if request.method == 'POST':
        # Collect basic personal information
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate inputs
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email format"}), 400
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400
        if not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
            return jsonify({"error": "Password must contain at least one number, one uppercase letter, and one special symbol"}), 400

        # Store in session
        session['full_name'] = full_name
        session['email'] = email
        session['password'] = password

        return redirect(url_for('signup_location'))
    return render_template('signup/personal.html')

@app.route('/signup/location', methods=['GET', 'POST'])
def signup_location():
    if request.method == 'POST':
        state = request.form.get('state')
        district = request.form.get('district')
        location_lat = request.form.get('location_lat')
        location_long = request.form.get('location_long')

        if not state or not district:
            return jsonify({"error": "State and District must be selected"}), 400

        session['location'] = {
            'state': state,
            'district': district,
            'lat': location_lat,
            'long': location_long
        }

        return redirect(url_for('signup_preferences'))
    return render_template('signup/location.html')

@app.route('/signup/preferences', methods=['GET', 'POST'])
def signup_preferences():
    if not check_previous_step(['full_name', 'email', 'location']):
        flash('Please complete previous steps first')
        return redirect(url_for('signup_personal'))
    
    if request.method == 'POST':
        # Collect preferences
        budget = request.form.get('budget')
        preferred_gender = request.form.get('preferred_gender')
        preferred_budget = request.form.get('preferred_budget')
        preferred_location = request.form.get('preferred_location')
        height = request.form.get('height')
        
        session['preferences'] = {
            'budget': budget,
            'preferred_gender': preferred_gender,
            'preferred_budget': preferred_budget,
            'preferred_location': preferred_location,
            'height': height
        }

        return redirect(url_for('signup_lifestyle'))
    return render_template('signup/preferences.html')

@app.route('/signup/lifestyle', methods=['GET', 'POST'])
def signup_lifestyle():
    if request.method == 'POST':
        # Collect lifestyle information
        interests = request.form.get('interests')
        qualities = request.form.get('qualities')
        drinking = request.form.get('drinking')
        smoking = request.form.get('smoking')
        religion = request.form.get('religion')
        
        session['lifestyle'] = {
            'interests': interests,
            'qualities': qualities,
            'drinking': drinking,
            'smoking': smoking,
            'religion': religion
        }

        return redirect(url_for('signup_photos'))
    return render_template('signup/lifestyle.html')

def validate_session_data():
    """Validate all required session data before final submission"""
    required_fields = {
        'full_name': 'Personal Information',
        'email': 'Personal Information',
        'password': 'Personal Information',
        'location': 'Location',
        'preferences': 'Preferences',
        'lifestyle': 'Lifestyle'
    }
    
    missing_fields = []
    for field, step in required_fields.items():
        if field not in session:
            missing_fields.append(f"{field} from {step}")
    
    return len(missing_fields) == 0, missing_fields

@app.route('/signup/photos', methods=['GET', 'POST'])
def signup_photos():
    is_valid, missing_fields = validate_session_data()
    if not is_valid:
        flash(f"Missing required information: {', '.join(missing_fields)}")
        return redirect(url_for('signup_personal'))
    
    if request.method == 'POST':
        photos = request.files.getlist('photos')
        
        if len(photos) < 1 or len(photos) > 6:
            return jsonify({"error": "Please upload between 1 and 6 photos"}), 400

        try:
            # Store photos
            photo_paths = []
            for photo in photos:
                filename = secure_filename(f"{datetime.now().timestamp()}_{photo.filename}")
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                photo_paths.append(photo_path)

            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Insert user data
            cursor.execute('''
                INSERT INTO users (
                    full_name, email, password, gender, age,
                    location_lat, location_long, state, district,
                    bio, occupation, interests, drinking, smoking, religion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.get('full_name'),
                session.get('email'),
                session.get('password'),
                session.get('gender'),
                session.get('age'),
                session.get('location', {}).get('lat'),
                session.get('location', {}).get('long'),
                session.get('location', {}).get('state'),
                session.get('location', {}).get('district'),
                session.get('bio'),
                session.get('occupation'),
                session.get('interests'),
                session.get('lifestyle', {}).get('drinking'),
                session.get('lifestyle', {}).get('smoking'),
                session.get('lifestyle', {}).get('religion')
            ))
            
            user_id = cursor.lastrowid
            
            # Insert preferences
            cursor.execute('''
                INSERT INTO preferences (
                    user_id, budget, preferred_gender, preferred_budget,
                    preferred_location, height, interests, qualities,
                    drinking, smoking, religion, prompts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                session.get('preferences', {}).get('budget'),
                session.get('preferences', {}).get('preferred_gender'),
                session.get('preferences', {}).get('preferred_budget'),
                session.get('preferences', {}).get('preferred_location'),
                session.get('preferences', {}).get('height'),
                session.get('lifestyle', {}).get('interests'),
                session.get('lifestyle', {}).get('qualities'),
                session.get('lifestyle', {}).get('drinking'),
                session.get('lifestyle', {}).get('smoking'),
                session.get('lifestyle', {}).get('religion'),
                session.get('prompts')
            ))
            
            # Insert photos
            for i, photo_path in enumerate(photo_paths):
                cursor.execute('''
                    INSERT INTO photos (user_id, photo_path, is_primary)
                    VALUES (?, ?, ?)
                ''', (user_id, photo_path, i == 0))  # First photo is primary
            
            conn.commit()
            conn.close()
            
            # Clear session after successful signup
            session.clear()
            return redirect(url_for('signin_page'))
            
        except sqlite3.Error as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"error": f"Error: {str(e)}"}), 500

    return render_template('signup/photos.html')

@app.route('/signin')
def signin_page():
    # Add debug logging
    print("Redirected to signin page")
    # Clear any remaining session data
    session.clear()
    return render_template('signin.html')

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    print(f"Signin attempt for email: {email}")  # Debug log

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, full_name, password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user is None:
            print(f"User not found for email: {email}")  # Debug log
            return jsonify({"error": "User not found"}), 404

        user_id, full_name, stored_password = user
        
        if password == stored_password:  # In production, use proper password hashing
            print(f"Successful login for user: {full_name}")  # Debug log
            return jsonify({
                "message": f"Welcome back, {full_name}!",
                "user_id": user_id
            }), 200
        else:
            print(f"Invalid password for email: {email}")  # Debug log
            return jsonify({"error": "Invalid password"}), 401
            
    except Exception as e:
        print(f"Database error during signin: {e}")  # Debug log
        return jsonify({"error": "An error occurred during sign-in"}), 500
    finally:
        conn.close()

@app.route('/get_states')
def get_states():
    return jsonify(STATES_LIST)

@app.route('/get_districts/<state>')
def get_districts(state):
    districts = STATES_AND_DISTRICTS.get(state, [])
    return jsonify(districts)

@app.route('/users')
def view_users():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            users.*,
            preferences.*,
            GROUP_CONCAT(photos.photo_path) as photo_paths
        FROM users
        LEFT JOIN preferences ON users.id = preferences.user_id
        LEFT JOIN photos ON users.id = photos.user_id
        GROUP BY users.id
    ''')
    
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(users)

# Onboarding Routes
@app.route('/onboarding/age', methods=['GET', 'POST'])
def onboarding_age():
    if not check_previous_step([]):  # Empty list since we're checking only basic info
        flash('Please complete signup first')
        return redirect(url_for('signup'))
        
    if request.method == 'POST':
        age = request.form.get('age')
        if not age or not age.isdigit() or int(age) < 18:
            flash('Invalid age. Must be 18 or older')
            return redirect(url_for('onboarding_age'))
        session['age'] = int(age)
        return redirect(url_for('onboarding_gender'))
    return render_template('onboarding/age.html')

@app.route('/onboarding/gender', methods=['GET', 'POST'])
def onboarding_gender():
    if not check_previous_step(['age']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        gender = request.form.get('gender')
        if not gender:
            flash('Please select a gender')
            return redirect(url_for('onboarding_gender'))
        session['gender'] = gender
        return redirect(url_for('onboarding_location'))
    return render_template('onboarding/gender.html')

@app.route('/onboarding/location', methods=['GET', 'POST'])
def onboarding_location():
    if not check_previous_step(['age', 'gender']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        state = request.form.get('state')
        district = request.form.get('district')
        lat = request.form.get('location_lat')
        long = request.form.get('location_long')
        if not all([state, district]):
            flash('Please select your location')
            return redirect(url_for('onboarding_location'))
        session['location'] = {
            'state': state,
            'district': district,
            'lat': lat,
            'long': long
        }
        return redirect(url_for('onboarding_bio'))
    return render_template('onboarding/location.html')

@app.route('/onboarding/bio', methods=['GET', 'POST'])
def onboarding_bio():
    if not check_previous_step(['age', 'gender', 'location']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        bio = request.form.get('bio')
        if not bio or len(bio) > 500:
            flash('Bio must be between 1 and 500 characters')
            return redirect(url_for('onboarding_bio'))
        session['bio'] = bio
        return redirect(url_for('onboarding_occupation'))
    return render_template('onboarding/bio.html')

@app.route('/onboarding/occupation', methods=['GET', 'POST'])
def onboarding_occupation():
    if not check_previous_step(['age', 'gender', 'location', 'bio']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        occupation = request.form.get('occupation')
        if not occupation:
            flash('Please enter your occupation')
            return redirect(url_for('onboarding_occupation'))
        session['occupation'] = occupation
        return redirect(url_for('onboarding_interests'))
    return render_template('onboarding/occupation.html')

@app.route('/onboarding/interests', methods=['GET', 'POST'])
def onboarding_interests():
    if not check_previous_step(['age', 'gender', 'location', 'bio', 'occupation']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        interests = request.form.get('interests')
        if not interests:
            flash('Please select at least one interest')
            return redirect(url_for('onboarding_interests'))
        session['interests'] = interests
        return redirect(url_for('onboarding_photos'))
    return render_template('onboarding/interests.html')

@app.route('/onboarding/photos', methods=['GET', 'POST'])
def onboarding_photos():
    if not check_previous_step(['age', 'gender', 'location', 'bio', 'occupation', 'interests']):
        return redirect(url_for('onboarding_age'))
    if request.method == 'POST':
        photos = request.files.getlist('photos')
        if not photos or len(photos) > 6:
            flash('Please upload between 1 and 6 photos')
            return redirect(url_for('onboarding_photos'))
        
        photo_paths = []
        for photo in photos:
            if photo and allowed_file(photo.filename):
                filename = secure_filename(f"{datetime.now().timestamp()}_{photo.filename}")
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                photo_paths.append(photo_path)
        
        session['photo_paths'] = photo_paths
        return redirect(url_for('onboarding_prompts'))
    return render_template('onboarding/photos.html')

@app.route('/onboarding/prompts', methods=['GET', 'POST'])
def onboarding_prompts():
    if not check_previous_step(['age', 'gender', 'location', 'bio', 'occupation', 'interests', 'photo_paths']):
        flash('Please complete all previous steps')
        return redirect(url_for('onboarding_age'))
    
    if request.method == 'POST':
        prompts = {
            'prompt1': request.form.get('prompt1'),
            'prompt2': request.form.get('prompt2'),
            'prompt3': request.form.get('prompt3')
        }
        
        # Add debug logging
        print("Received prompts:", prompts)
        
        if not all(prompts.values()):
            flash('Please answer all prompts')
            return redirect(url_for('onboarding_prompts'))
        
        try:
            session['prompts'] = prompts
            print("Session before save:", dict(session))  # Debug log
            
            # Save all collected data to database
            save_user_data()
            
            # Clear session after successful save
            session.clear()
            return redirect(url_for('signin_page'))
            
        except Exception as e:
            print(f"Error during save: {e}")  # Debug log
            flash(f'Error saving data: {str(e)}')
            return redirect(url_for('onboarding_prompts'))
    
    return render_template('onboarding/prompts.html')

def check_previous_step(required_data):
    """Check if required session data exists from previous steps"""
    basic_info = ['full_name', 'email', 'password']  # Basic signup info
    required_data = basic_info + required_data  # Add basic info to required data
    
    for data in required_data:
        if data not in session:
            return False
    return True

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/start-onboarding')
def start_onboarding():
    return redirect(url_for('onboarding_age'))

@app.route('/debug/session')
def debug_session():
    """Debug route to view session data"""
    if app.debug:  # Only available in debug mode
        return jsonify(dict(session))
    return "Not available", 403

if __name__ == '__main__':
    app.run(debug=True)
