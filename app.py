print("=== APP.PY STARTING ===")

import sys
print(f"Python version: {sys.version}")

try:
    from flask import Flask, render_template, request, jsonify, session, redirect, url_for
    print("Flask imported")
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    print("Flask-Login imported")
    from authlib.integrations.flask_client import OAuth
    print("Authlib imported")
    import sqlite3
    import json
    import random
    from datetime import datetime, date
    import hashlib
    import os
    from dotenv import load_dotenv
    print("All imports successful")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    raise

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'uptriv-dev-secret-key-change-in-production')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# OAuth setup
oauth = OAuth(app)
google = None

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

print(f"GOOGLE_CLIENT_ID set: {bool(GOOGLE_CLIENT_ID)}")
print(f"GOOGLE_CLIENT_SECRET set: {bool(GOOGLE_CLIENT_SECRET)}")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    print("Google OAuth registered successfully")
else:
    print("WARNING: Google OAuth not configured - missing credentials")

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    # PostgreSQL for production
    USE_POSTGRES = True
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    # SQLite for local development
    USE_POSTGRES = False
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uptriv.db')

# Categories and their subcategories
CATEGORIES = {
    'news': {
        'name': 'World & U.S. News',
        'icon': 'globe',
        'color': '#FF6B6B',
        'subcategories': ['current_events', 'politics', 'famous_people', 'world_affairs']
    },
    'history': {
        'name': 'History',
        'icon': 'landmark',
        'color': '#4ECDC4',
        'subcategories': ['ancient', 'medieval', 'modern', 'wars', 'presidents', 'world_history']
    },
    'science': {
        'name': 'Science & Nature',
        'icon': 'flask',
        'color': '#45B7D1',
        'subcategories': ['space', 'animals', 'human_body', 'physics', 'chemistry', 'earth_science']
    },
    'entertainment': {
        'name': 'Entertainment',
        'icon': 'film',
        'color': '#96CEB4',
        'subcategories': ['movies', 'tv', 'music_pre1990', 'music_post1990', 'celebrities', 'literature']
    },
    'sports': {
        'name': 'Sports',
        'icon': 'trophy',
        'color': '#FFEAA7',
        'subcategories': ['football', 'basketball', 'baseball', 'soccer', 'olympics', 'records']
    },
    'geography': {
        'name': 'Geography',
        'icon': 'map',
        'color': '#DDA0DD',
        'subcategories': ['countries', 'capitals', 'landmarks', 'maps', 'flags', 'continents']
    }
}

# Question bank with subcategories
QUESTIONS = {
    'news': [
        {'q': 'Which country hosted the 2024 Summer Olympics?', 'a': 'France', 'options': ['France', 'Japan', 'USA', 'UK'], 'sub': 'current_events'},
        {'q': 'Who is the current Secretary-General of the United Nations?', 'a': 'António Guterres', 'options': ['António Guterres', 'Ban Ki-moon', 'Kofi Annan', 'Javier Solana'], 'sub': 'world_affairs'},
        {'q': 'Which tech company became the first to reach a $3 trillion market cap?', 'a': 'Apple', 'options': ['Apple', 'Microsoft', 'Amazon', 'Google'], 'sub': 'current_events'},
        {'q': 'What social media platform was formerly known as Twitter?', 'a': 'X', 'options': ['X', 'Threads', 'Bluesky', 'Mastodon'], 'sub': 'current_events'},
        {'q': 'Who won the 2024 U.S. Presidential Election?', 'a': 'Donald Trump', 'options': ['Donald Trump', 'Joe Biden', 'Kamala Harris', 'Ron DeSantis'], 'sub': 'politics'},
        {'q': 'Which billionaire acquired Twitter in 2022?', 'a': 'Elon Musk', 'options': ['Elon Musk', 'Jeff Bezos', 'Mark Zuckerberg', 'Bill Gates'], 'sub': 'famous_people'},
        {'q': 'What country did Russia invade in February 2022?', 'a': 'Ukraine', 'options': ['Ukraine', 'Georgia', 'Poland', 'Belarus'], 'sub': 'world_affairs'},
        {'q': 'Who is the current Prime Minister of the United Kingdom?', 'a': 'Keir Starmer', 'options': ['Keir Starmer', 'Rishi Sunak', 'Boris Johnson', 'Liz Truss'], 'sub': 'politics'},
        {'q': 'Which AI chatbot launched by OpenAI went viral in late 2022?', 'a': 'ChatGPT', 'options': ['ChatGPT', 'Bard', 'Claude', 'Copilot'], 'sub': 'current_events'},
        {'q': 'What major bank collapsed in March 2023?', 'a': 'Silicon Valley Bank', 'options': ['Silicon Valley Bank', 'Wells Fargo', 'Chase', 'Bank of America'], 'sub': 'current_events'},
    ],
    'history': [
        {'q': 'In what year did World War II end?', 'a': '1945', 'options': ['1945', '1944', '1946', '1943'], 'sub': 'wars'},
        {'q': 'Who was the first President of the United States?', 'a': 'George Washington', 'options': ['George Washington', 'John Adams', 'Thomas Jefferson', 'Benjamin Franklin'], 'sub': 'presidents'},
        {'q': 'The Great Wall of China was primarily built to protect against invasions from which direction?', 'a': 'North', 'options': ['North', 'South', 'East', 'West'], 'sub': 'ancient'},
        {'q': 'What year did the Berlin Wall fall?', 'a': '1989', 'options': ['1989', '1991', '1987', '1990'], 'sub': 'modern'},
        {'q': 'Which ancient civilization built the pyramids of Giza?', 'a': 'Egyptians', 'options': ['Egyptians', 'Romans', 'Greeks', 'Persians'], 'sub': 'ancient'},
        {'q': 'Who was the British Prime Minister during most of World War II?', 'a': 'Winston Churchill', 'options': ['Winston Churchill', 'Neville Chamberlain', 'Clement Attlee', 'Anthony Eden'], 'sub': 'wars'},
        {'q': 'The Renaissance began in which country?', 'a': 'Italy', 'options': ['Italy', 'France', 'England', 'Spain'], 'sub': 'medieval'},
        {'q': 'What was the name of the ship on which the Pilgrims sailed to America in 1620?', 'a': 'Mayflower', 'options': ['Mayflower', 'Santa Maria', 'Endeavour', 'Beagle'], 'sub': 'world_history'},
        {'q': 'Which U.S. President issued the Emancipation Proclamation?', 'a': 'Abraham Lincoln', 'options': ['Abraham Lincoln', 'Ulysses S. Grant', 'Andrew Johnson', 'James Buchanan'], 'sub': 'presidents'},
        {'q': 'The Cold War was primarily between which two superpowers?', 'a': 'USA and USSR', 'options': ['USA and USSR', 'USA and China', 'UK and USSR', 'USA and Germany'], 'sub': 'modern'},
    ],
    'science': [
        {'q': 'What is the closest planet to the Sun?', 'a': 'Mercury', 'options': ['Mercury', 'Venus', 'Mars', 'Earth'], 'sub': 'space'},
        {'q': 'What is the largest organ in the human body?', 'a': 'Skin', 'options': ['Skin', 'Liver', 'Heart', 'Brain'], 'sub': 'human_body'},
        {'q': 'What is the chemical symbol for gold?', 'a': 'Au', 'options': ['Au', 'Ag', 'Fe', 'Go'], 'sub': 'chemistry'},
        {'q': 'What is the fastest land animal?', 'a': 'Cheetah', 'options': ['Cheetah', 'Lion', 'Gazelle', 'Horse'], 'sub': 'animals'},
        {'q': 'What force keeps planets in orbit around the Sun?', 'a': 'Gravity', 'options': ['Gravity', 'Magnetism', 'Friction', 'Inertia'], 'sub': 'physics'},
        {'q': 'What is the largest planet in our solar system?', 'a': 'Jupiter', 'options': ['Jupiter', 'Saturn', 'Neptune', 'Uranus'], 'sub': 'space'},
        {'q': 'How many bones are in the adult human body?', 'a': '206', 'options': ['206', '208', '204', '212'], 'sub': 'human_body'},
        {'q': 'What is the hardest natural substance on Earth?', 'a': 'Diamond', 'options': ['Diamond', 'Titanium', 'Platinum', 'Quartz'], 'sub': 'earth_science'},
        {'q': 'What gas do plants absorb from the atmosphere?', 'a': 'Carbon dioxide', 'options': ['Carbon dioxide', 'Oxygen', 'Nitrogen', 'Hydrogen'], 'sub': 'earth_science'},
        {'q': 'What is the speed of light in a vacuum (approximately)?', 'a': '300,000 km/s', 'options': ['300,000 km/s', '150,000 km/s', '500,000 km/s', '1,000,000 km/s'], 'sub': 'physics'},
    ],
    'entertainment': [
        {'q': 'Which film won the Academy Award for Best Picture in 2024?', 'a': 'Oppenheimer', 'options': ['Oppenheimer', 'Barbie', 'Killers of the Flower Moon', 'Poor Things'], 'sub': 'movies'},
        {'q': 'Who sang "Bohemian Rhapsody"?', 'a': 'Queen', 'options': ['Queen', 'The Beatles', 'Led Zeppelin', 'Pink Floyd'], 'sub': 'music_pre1990'},
        {'q': 'What TV series features a chemistry teacher turned drug manufacturer?', 'a': 'Breaking Bad', 'options': ['Breaking Bad', 'The Wire', 'Ozark', 'Narcos'], 'sub': 'tv'},
        {'q': 'Who wrote the Harry Potter book series?', 'a': 'J.K. Rowling', 'options': ['J.K. Rowling', 'Stephen King', 'George R.R. Martin', 'Suzanne Collins'], 'sub': 'literature'},
        {'q': 'Which artist released the album "1989"?', 'a': 'Taylor Swift', 'options': ['Taylor Swift', 'Beyoncé', 'Adele', 'Lady Gaga'], 'sub': 'music_post1990'},
        {'q': 'In what year was the first iPhone released?', 'a': '2007', 'options': ['2007', '2005', '2008', '2010'], 'sub': 'celebrities'},
        {'q': 'Which movie features the quote "I\'ll be back"?', 'a': 'The Terminator', 'options': ['The Terminator', 'Predator', 'Total Recall', 'Commando'], 'sub': 'movies'},
        {'q': 'Who played Iron Man in the Marvel Cinematic Universe?', 'a': 'Robert Downey Jr.', 'options': ['Robert Downey Jr.', 'Chris Evans', 'Chris Hemsworth', 'Mark Ruffalo'], 'sub': 'movies'},
        {'q': 'Which band performed "Smells Like Teen Spirit"?', 'a': 'Nirvana', 'options': ['Nirvana', 'Pearl Jam', 'Soundgarden', 'Alice in Chains'], 'sub': 'music_post1990'},
        {'q': 'What streaming service produced "Stranger Things"?', 'a': 'Netflix', 'options': ['Netflix', 'Hulu', 'Amazon Prime', 'Disney+'], 'sub': 'tv'},
    ],
    'sports': [
        {'q': 'Which country has won the most FIFA World Cup titles?', 'a': 'Brazil', 'options': ['Brazil', 'Germany', 'Italy', 'Argentina'], 'sub': 'soccer'},
        {'q': 'How many players are on a basketball team on the court at once?', 'a': '5', 'options': ['5', '6', '7', '4'], 'sub': 'basketball'},
        {'q': 'Who holds the record for most home runs in MLB history?', 'a': 'Barry Bonds', 'options': ['Barry Bonds', 'Hank Aaron', 'Babe Ruth', 'Alex Rodriguez'], 'sub': 'baseball'},
        {'q': 'Which NFL team has won the most Super Bowls?', 'a': 'New England Patriots', 'options': ['New England Patriots', 'Pittsburgh Steelers', 'Dallas Cowboys', 'San Francisco 49ers'], 'sub': 'football'},
        {'q': 'In which city were the 2020 Summer Olympics held (delayed to 2021)?', 'a': 'Tokyo', 'options': ['Tokyo', 'Paris', 'London', 'Rio de Janeiro'], 'sub': 'olympics'},
        {'q': 'Who is the all-time leading scorer in NBA history?', 'a': 'LeBron James', 'options': ['LeBron James', 'Kareem Abdul-Jabbar', 'Michael Jordan', 'Kobe Bryant'], 'sub': 'basketball'},
        {'q': 'What is the only Grand Slam tennis tournament played on grass?', 'a': 'Wimbledon', 'options': ['Wimbledon', 'US Open', 'French Open', 'Australian Open'], 'sub': 'records'},
        {'q': 'Which athlete has won the most Olympic gold medals?', 'a': 'Michael Phelps', 'options': ['Michael Phelps', 'Usain Bolt', 'Carl Lewis', 'Mark Spitz'], 'sub': 'olympics'},
        {'q': 'What sport is played at Augusta National?', 'a': 'Golf', 'options': ['Golf', 'Tennis', 'Polo', 'Cricket'], 'sub': 'records'},
        {'q': 'Who won Super Bowl LVIII in 2024?', 'a': 'Kansas City Chiefs', 'options': ['Kansas City Chiefs', 'San Francisco 49ers', 'Philadelphia Eagles', 'Baltimore Ravens'], 'sub': 'football'},
    ],
    'geography': [
        {'q': 'What is the capital of Australia?', 'a': 'Canberra', 'options': ['Canberra', 'Sydney', 'Melbourne', 'Brisbane'], 'sub': 'capitals'},
        {'q': 'Which country has the largest population in the world?', 'a': 'India', 'options': ['India', 'China', 'USA', 'Indonesia'], 'sub': 'countries'},
        {'q': 'What is the longest river in the world?', 'a': 'Nile', 'options': ['Nile', 'Amazon', 'Mississippi', 'Yangtze'], 'sub': 'landmarks'},
        {'q': 'Which continent is the Sahara Desert located on?', 'a': 'Africa', 'options': ['Africa', 'Asia', 'Australia', 'South America'], 'sub': 'continents'},
        {'q': 'What is the smallest country in the world by area?', 'a': 'Vatican City', 'options': ['Vatican City', 'Monaco', 'San Marino', 'Liechtenstein'], 'sub': 'countries'},
        {'q': 'Which country\'s flag features a maple leaf?', 'a': 'Canada', 'options': ['Canada', 'USA', 'Japan', 'South Korea'], 'sub': 'flags'},
        {'q': 'Mount Everest is located on the border of which two countries?', 'a': 'Nepal and China', 'options': ['Nepal and China', 'India and China', 'Nepal and India', 'Pakistan and China'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Brazil?', 'a': 'Brasília', 'options': ['Brasília', 'Rio de Janeiro', 'São Paulo', 'Salvador'], 'sub': 'capitals'},
        {'q': 'Which ocean is the largest?', 'a': 'Pacific', 'options': ['Pacific', 'Atlantic', 'Indian', 'Arctic'], 'sub': 'maps'},
        {'q': 'What country is known as the Land of the Rising Sun?', 'a': 'Japan', 'options': ['Japan', 'China', 'South Korea', 'Thailand'], 'sub': 'countries'},
    ]
}


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email=None, google_id=None, profile_picture=None):
        self.id = id
        self.username = username
        self.email = email
        self.google_id = google_id
        self.profile_picture = profile_picture


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_row = cur.fetchone()
    conn.close()

    if user_row:
        return User(
            id=user_row['id'],
            username=user_row['username'],
            email=user_row['email'] if 'email' in user_row.keys() else None,
            google_id=user_row['google_id'] if 'google_id' in user_row.keys() else None,
            profile_picture=user_row['profile_picture'] if 'profile_picture' in user_row.keys() else None
        )
    return None


def get_db():
    if USE_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = RealDictCursor
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL schema
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                google_id TEXT UNIQUE,
                profile_picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                game_date DATE NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                user_answer TEXT,
                correct INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_questions (
                id SERIAL PRIMARY KEY,
                game_date DATE NOT NULL,
                user_id INTEGER,
                questions_json TEXT NOT NULL,
                UNIQUE(game_date, user_id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                id SERIAL PRIMARY KEY,
                requester_id INTEGER NOT NULL REFERENCES users(id),
                addressee_id INTEGER NOT NULL REFERENCES users(id),
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(requester_id, addressee_id)
            )
        ''')
    else:
        # SQLite schema
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                google_id TEXT UNIQUE,
                profile_picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_date DATE NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                user_answer TEXT,
                correct INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS daily_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date DATE NOT NULL,
                user_id INTEGER,
                questions_json TEXT NOT NULL,
                UNIQUE(game_date, user_id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                addressee_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (requester_id) REFERENCES users(id),
                FOREIGN KEY (addressee_id) REFERENCES users(id),
                UNIQUE(requester_id, addressee_id)
            )
        ''')

    conn.commit()
    conn.close()


def get_or_create_user_by_google(google_id, email, name, picture):
    """Get or create user from Google OAuth data."""
    conn = get_db()
    cur = conn.cursor()

    # Check if user exists by google_id
    cur.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
    user = cur.fetchone()

    if user:
        # Update profile picture if changed
        cur.execute('UPDATE users SET profile_picture = ? WHERE google_id = ?', (picture, google_id))
        conn.commit()
    else:
        # Check if email already exists (user previously created without OAuth)
        cur.execute('SELECT * FROM users WHERE email = ?', (email,))
        existing = cur.fetchone()

        if existing:
            # Link Google account to existing user
            cur.execute('UPDATE users SET google_id = ?, profile_picture = ? WHERE email = ?',
                       (google_id, picture, email))
            conn.commit()
            cur.execute('SELECT * FROM users WHERE email = ?', (email,))
            user = cur.fetchone()
        else:
            # Create new user
            cur.execute('''
                INSERT INTO users (username, email, google_id, profile_picture)
                VALUES (?, ?, ?, ?)
            ''', (name, email, google_id, picture))
            conn.commit()
            cur.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
            user = cur.fetchone()

    conn.close()
    return dict(user)


def get_daily_questions_for_user(user_id):
    """Get or generate questions for today for a specific user, excluding questions they've already seen."""
    today = date.today().isoformat()
    conn = get_db()
    cur = conn.cursor()

    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'SELECT questions_json FROM daily_questions WHERE game_date = {placeholder} AND user_id = {placeholder}', (today, user_id))
    result = cur.fetchone()

    if result:
        conn.close()
        return json.loads(result['questions_json'])

    cur.execute(f'SELECT DISTINCT question FROM game_results WHERE user_id = {placeholder}', (user_id,))
    seen_questions = set(row['question'] for row in cur.fetchall())

    seed = int(hashlib.md5(f"{today}-{user_id}".encode()).hexdigest(), 16)
    random.seed(seed)

    questions = []
    for cat_key in ['news', 'history', 'science', 'entertainment', 'sports', 'geography']:
        available = [q for q in QUESTIONS[cat_key] if q['q'] not in seen_questions]
        if not available:
            available = QUESTIONS[cat_key]

        q = random.choice(available)
        questions.append({
            'category': cat_key,
            'category_name': CATEGORIES[cat_key]['name'],
            'color': CATEGORIES[cat_key]['color'],
            **q
        })

    random.shuffle(questions)

    cur.execute(
        f'INSERT INTO daily_questions (game_date, user_id, questions_json) VALUES ({placeholder}, {placeholder}, {placeholder})',
        (today, user_id, json.dumps(questions))
    )
    conn.commit()
    conn.close()

    return questions


def calculate_user_stats(user_id):
    """Calculate comprehensive stats for a user."""
    conn = get_db()
    cur = conn.cursor()

    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        SELECT category, subcategory, correct, time_taken
        FROM game_results
        WHERE user_id = {placeholder}
    ''', (user_id,))
    results = cur.fetchall()
    conn.close()

    if not results:
        return {
            'total_games': 0,
            'categories': {cat: {'correct': 0, 'total': 0, 'percentage': 0} for cat in CATEGORIES},
            'subcategories': {},
            'strengths': [],
            'weaknesses': [],
            'overall_percentage': 0
        }

    cat_stats = {cat: {'correct': 0, 'total': 0} for cat in CATEGORIES}
    sub_stats = {}

    for r in results:
        cat = r['category']
        sub = r['subcategory']
        correct = r['correct']

        cat_stats[cat]['total'] += 1
        cat_stats[cat]['correct'] += correct

        if sub not in sub_stats:
            sub_stats[sub] = {'correct': 0, 'total': 0, 'category': cat}
        sub_stats[sub]['total'] += 1
        sub_stats[sub]['correct'] += correct

    for cat in cat_stats:
        total = cat_stats[cat]['total']
        if total > 0:
            cat_stats[cat]['percentage'] = round(cat_stats[cat]['correct'] / total * 100)
        else:
            cat_stats[cat]['percentage'] = 0

    for sub in sub_stats:
        total = sub_stats[sub]['total']
        if total > 0:
            sub_stats[sub]['percentage'] = round(sub_stats[sub]['correct'] / total * 100)
        else:
            sub_stats[sub]['percentage'] = 0

    qualified_subs = {k: v for k, v in sub_stats.items() if v['total'] >= 3}
    strengths = []
    weaknesses = []

    if qualified_subs:
        sorted_subs = sorted(qualified_subs.items(), key=lambda x: x[1]['percentage'], reverse=True)
        for sub, stats in sorted_subs[:3]:
            if stats['percentage'] >= 70:
                strengths.append({
                    'name': sub.replace('_', ' ').title(),
                    'percentage': stats['percentage'],
                    'category': stats['category']
                })
        for sub, stats in sorted_subs[-3:]:
            if stats['percentage'] < 50:
                weaknesses.append({
                    'name': sub.replace('_', ' ').title(),
                    'percentage': stats['percentage'],
                    'category': stats['category']
                })

    total_correct = sum(cat_stats[c]['correct'] for c in cat_stats)
    total_questions = sum(cat_stats[c]['total'] for c in cat_stats)
    overall = round(total_correct / total_questions * 100) if total_questions > 0 else 0

    return {
        'total_games': total_questions // 6,
        'total_questions': total_questions,
        'categories': cat_stats,
        'subcategories': sub_stats,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'overall_percentage': overall
    }


def has_played_today(user_id):
    """Check if user has already played today."""
    today = date.today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'
    cur.execute(
        f'SELECT COUNT(*) as count FROM game_results WHERE user_id = {placeholder} AND game_date = {placeholder}',
        (user_id, today)
    )
    result = cur.fetchone()
    conn.close()
    return result['count'] > 0


def get_friends(user_id):
    """Get list of user's friends."""
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        SELECT u.id, u.username, u.profile_picture, f.status, f.created_at
        FROM friendships f
        JOIN users u ON (
            CASE
                WHEN f.requester_id = {placeholder} THEN f.addressee_id = u.id
                ELSE f.requester_id = u.id
            END
        )
        WHERE (f.requester_id = {placeholder} OR f.addressee_id = {placeholder})
        AND f.status = 'accepted'
    ''', (user_id, user_id, user_id))

    friends = [dict(row) for row in cur.fetchall()]
    conn.close()
    return friends


def get_pending_requests(user_id):
    """Get pending friend requests for user."""
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        SELECT u.id, u.username, u.profile_picture, f.id as request_id, f.created_at
        FROM friendships f
        JOIN users u ON f.requester_id = u.id
        WHERE f.addressee_id = {placeholder} AND f.status = 'pending'
    ''', (user_id,))

    requests = [dict(row) for row in cur.fetchall()]
    conn.close()
    return requests


# ============ AUTH ROUTES ============

@app.route('/auth/google')
def google_login():
    """Redirect to Google for OAuth."""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            user_data = get_or_create_user_by_google(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=user_info.get('name', user_info['email'].split('@')[0]),
                picture=user_info.get('picture', '')
            )

            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data.get('email'),
                google_id=user_data.get('google_id'),
                profile_picture=user_data.get('profile_picture')
            )
            login_user(user)

            return redirect(url_for('play'))
    except Exception as e:
        print(f"OAuth error: {e}")
        return redirect(url_for('index'))

    return redirect(url_for('index'))


@app.route('/auth/logout')
def logout():
    """Log out user."""
    logout_user()
    session.clear()
    return redirect(url_for('index'))


@app.route('/login')
def login_page():
    """Login page."""
    return render_template('login.html')


@app.route('/api/me')
def get_current_user():
    """Get current logged in user info."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'profile_picture': current_user.profile_picture
            }
        })
    return jsonify({'authenticated': False})


# ============ PAGE ROUTES ============

@app.route('/')
def index():
    return render_template('index.html', categories=CATEGORIES)


@app.route('/play')
def play():
    return render_template('play.html', categories=CATEGORIES)


@app.route('/profile')
def profile():
    return render_template('profile.html', categories=CATEGORIES)


@app.route('/profile/<username>')
def user_profile(username):
    return render_template('profile.html', categories=CATEGORIES, view_username=username)


@app.route('/history')
def history():
    return render_template('history.html', categories=CATEGORIES)


@app.route('/friends')
@login_required
def friends_page():
    return render_template('friends.html', categories=CATEGORIES)


@app.route('/leaderboard')
@login_required
def leaderboard_page():
    return render_template('leaderboard.html', categories=CATEGORIES)


# ============ GAME API ROUTES ============

@app.route('/api/start-game', methods=['POST'])
def start_game():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Please sign in to play', 'require_login': True}), 401

    user_id = current_user.id

    if has_played_today(user_id):
        return jsonify({
            'error': 'already_played',
            'message': 'You already played today! Come back tomorrow for new questions.'
        }), 400

    questions = get_daily_questions_for_user(user_id)

    safe_questions = []
    for q in questions:
        safe_questions.append({
            'category': q['category'],
            'category_name': q['category_name'],
            'color': q['color'],
            'question': q['q'],
            'options': q['options'],
            'subcategory': q['sub']
        })

    return jsonify({
        'success': True,
        'questions': safe_questions,
        'user': {'id': user_id, 'username': current_user.username}
    })


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    user_id = current_user.id

    question_index = data.get('question_index')
    answer = data.get('answer')
    time_taken = data.get('time_taken', 10)

    questions = get_daily_questions_for_user(user_id)

    if question_index < 0 or question_index >= len(questions):
        return jsonify({'error': 'Invalid question'}), 400

    q = questions[question_index]
    correct = answer == q['a']

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'
    cur.execute(f'''
        INSERT INTO game_results (user_id, game_date, category, subcategory, question, correct_answer, user_answer, correct, time_taken)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    ''', (user_id, date.today().isoformat(), q['category'], q['sub'], q['q'], q['a'], answer, 1 if correct else 0, time_taken))
    conn.commit()
    conn.close()

    return jsonify({
        'correct': correct,
        'correct_answer': q['a']
    })


@app.route('/api/get-stats', methods=['GET'])
def get_stats():
    user_id = None
    username = request.args.get('username')

    if username:
        conn = get_db()
        cur = conn.cursor()
        placeholder = '%s' if USE_POSTGRES else '?'
        cur.execute(f'SELECT id FROM users WHERE username = {placeholder}', (username,))
        user = cur.fetchone()
        conn.close()
        if user:
            user_id = user['id']
    elif current_user.is_authenticated:
        user_id = current_user.id

    if not user_id:
        return jsonify({'error': 'No user specified'}), 400

    stats = calculate_user_stats(user_id)
    stats['categories_meta'] = CATEGORIES

    return jsonify(stats)


@app.route('/api/get-history', methods=['GET'])
def get_history():
    username = request.args.get('username')

    if not username and current_user.is_authenticated:
        username = current_user.username

    if not username:
        return jsonify({'error': 'Username required'}), 400

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'SELECT id FROM users WHERE username = {placeholder}', (username,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found', 'games': []})

    user_id = user['id']

    cur.execute(f'''
        SELECT game_date, category, subcategory, question, correct_answer, user_answer, correct, time_taken
        FROM game_results
        WHERE user_id = {placeholder}
        ORDER BY game_date DESC, created_at ASC
    ''', (user_id,))
    results = cur.fetchall()
    conn.close()

    games = {}
    for r in results:
        game_date = r['game_date'] if isinstance(r['game_date'], str) else r['game_date'].isoformat()
        if game_date not in games:
            games[game_date] = {'date': game_date, 'questions': [], 'score': 0, 'total': 0}
        games[game_date]['questions'].append({
            'category': r['category'],
            'category_name': CATEGORIES.get(r['category'], {}).get('name', r['category']),
            'color': CATEGORIES.get(r['category'], {}).get('color', '#888'),
            'question': r['question'],
            'correct_answer': r['correct_answer'],
            'user_answer': r['user_answer'] or '(No answer)',
            'correct': r['correct'],
            'time_taken': round(r['time_taken'], 1)
        })
        games[game_date]['total'] += 1
        if r['correct']:
            games[game_date]['score'] += 1

    games_list = sorted(games.values(), key=lambda x: x['date'], reverse=True)
    return jsonify({'games': games_list})


@app.route('/api/get-share-text', methods=['GET'])
def get_share_text():
    username = request.args.get('username')
    game_date = request.args.get('date')

    if not username or not game_date:
        return jsonify({'error': 'Username and date required'}), 400

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'SELECT id FROM users WHERE username = {placeholder}', (username,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'})

    user_id = user['id']

    cur.execute(f'''
        SELECT category, correct
        FROM game_results
        WHERE user_id = {placeholder} AND game_date = {placeholder}
        ORDER BY created_at ASC
    ''', (user_id, game_date))
    results = cur.fetchall()
    conn.close()

    if not results:
        return jsonify({'error': 'No results found for that date'})

    score = sum(1 for r in results if r['correct'])
    total = len(results)

    cat_emojis = {
        'news': '🌍', 'history': '📜', 'science': '🔬',
        'entertainment': '🎬', 'sports': '🏆', 'geography': '🗺️'
    }

    lines = []
    for r in results:
        emoji = cat_emojis.get(r['category'], '❓')
        result = '🟩' if r['correct'] else '🟥'
        lines.append(f"{emoji}{result}")

    date_obj = datetime.strptime(game_date, '%Y-%m-%d')
    date_str = date_obj.strftime('%b %d, %Y')

    share_text = f"UpTriv {date_str}\n{score}/{total}\n\n" + " ".join(lines) + "\n\nuptriv.com"

    return jsonify({'share_text': share_text, 'score': score, 'total': total})


# ============ FRIENDS API ROUTES ============

@app.route('/api/friends', methods=['GET'])
@login_required
def api_get_friends():
    friends = get_friends(current_user.id)

    # Add stats for each friend
    for friend in friends:
        stats = calculate_user_stats(friend['id'])
        friend['stats'] = {
            'overall_percentage': stats['overall_percentage'],
            'total_games': stats['total_games']
        }

    return jsonify({'friends': friends})


@app.route('/api/friends/pending', methods=['GET'])
@login_required
def api_get_pending():
    requests = get_pending_requests(current_user.id)
    return jsonify({'requests': requests})


@app.route('/api/friends/search', methods=['GET'])
@login_required
def api_search_users():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'users': []})

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        SELECT id, username, profile_picture
        FROM users
        WHERE username LIKE {placeholder} AND id != {placeholder}
        LIMIT 10
    ''', (f'%{query}%', current_user.id))

    users = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({'users': users})


@app.route('/api/friends/request', methods=['POST'])
@login_required
def api_send_friend_request():
    data = request.get_json()
    friend_id = data.get('user_id')

    if not friend_id or friend_id == current_user.id:
        return jsonify({'error': 'Invalid user'}), 400

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    # Check if friendship already exists
    cur.execute(f'''
        SELECT id, status FROM friendships
        WHERE (requester_id = {placeholder} AND addressee_id = {placeholder})
        OR (requester_id = {placeholder} AND addressee_id = {placeholder})
    ''', (current_user.id, friend_id, friend_id, current_user.id))

    existing = cur.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Friend request already exists'}), 400

    cur.execute(f'''
        INSERT INTO friendships (requester_id, addressee_id, status)
        VALUES ({placeholder}, {placeholder}, 'pending')
    ''', (current_user.id, friend_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Friend request sent'})


@app.route('/api/friends/accept/<int:request_id>', methods=['POST'])
@login_required
def api_accept_friend(request_id):
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        UPDATE friendships
        SET status = 'accepted'
        WHERE id = {placeholder} AND addressee_id = {placeholder} AND status = 'pending'
    ''', (request_id, current_user.id))

    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Request not found'}), 404

    return jsonify({'success': True})


@app.route('/api/friends/reject/<int:request_id>', methods=['POST'])
@login_required
def api_reject_friend(request_id):
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        DELETE FROM friendships
        WHERE id = {placeholder} AND addressee_id = {placeholder} AND status = 'pending'
    ''', (request_id, current_user.id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/friends/<int:friend_id>', methods=['DELETE'])
@login_required
def api_remove_friend(friend_id):
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    cur.execute(f'''
        DELETE FROM friendships
        WHERE ((requester_id = {placeholder} AND addressee_id = {placeholder})
        OR (requester_id = {placeholder} AND addressee_id = {placeholder}))
        AND status = 'accepted'
    ''', (current_user.id, friend_id, friend_id, current_user.id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


# ============ LEADERBOARD API ============

@app.route('/api/leaderboard', methods=['GET'])
@login_required
def api_leaderboard():
    friends = get_friends(current_user.id)

    # Include current user in leaderboard
    all_users = [{'id': current_user.id, 'username': current_user.username,
                  'profile_picture': current_user.profile_picture, 'is_self': True}]

    for friend in friends:
        friend['is_self'] = False
        all_users.append(friend)

    # Calculate stats for all users
    leaderboard = []
    category_leaderboards = {cat: [] for cat in CATEGORIES}

    for user in all_users:
        stats = calculate_user_stats(user['id'])

        if stats['total_games'] > 0:
            leaderboard.append({
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'profile_picture': user.get('profile_picture'),
                    'is_self': user.get('is_self', False)
                },
                'percentage': stats['overall_percentage'],
                'games_played': stats['total_games'],
                'total_correct': sum(stats['categories'][c]['correct'] for c in stats['categories']),
                'total_questions': stats['total_questions']
            })

            # Category-specific leaderboards
            for cat in CATEGORIES:
                cat_stats = stats['categories'][cat]
                if cat_stats['total'] > 0:
                    category_leaderboards[cat].append({
                        'user': {
                            'id': user['id'],
                            'username': user['username'],
                            'profile_picture': user.get('profile_picture'),
                            'is_self': user.get('is_self', False)
                        },
                        'percentage': cat_stats['percentage'],
                        'correct': cat_stats['correct'],
                        'total': cat_stats['total']
                    })

    # Sort leaderboards
    leaderboard.sort(key=lambda x: (-x['percentage'], -x['games_played']))

    for cat in category_leaderboards:
        category_leaderboards[cat].sort(key=lambda x: (-x['percentage'], -x['total']))

    # Add ranks
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1

    for cat in category_leaderboards:
        for i, entry in enumerate(category_leaderboards[cat]):
            entry['rank'] = i + 1

    return jsonify({
        'overall': leaderboard,
        'categories': category_leaderboards
    })


# ============ MAIN ============

# Initialize database on app load (works with gunicorn)
try:
    print("Starting database initialization...")
    print(f"USE_POSTGRES: {USE_POSTGRES}")
    print(f"DATABASE_URL set: {bool(DATABASE_URL)}")
    init_db()
    print("Database initialized successfully!")
except Exception as e:
    print(f"ERROR initializing database: {e}")
    import traceback
    traceback.print_exc()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, port=port, host='0.0.0.0')
