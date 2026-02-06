print("=== APP.PY STARTING ===")

import sys
print(f"Python version: {sys.version}")

try:
    from flask import Flask, render_template, request, jsonify, session, redirect, url_for
    print("Flask imported")
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    print("Flask-Login imported")
    from flask_mail import Mail, Message
    print("Flask-Mail imported")
    import resend
    print("Resend imported")
    from authlib.integrations.flask_client import OAuth
    print("Authlib imported")
    import sqlite3
    import json
    import random
    import uuid
    from datetime import datetime, date, timedelta
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

# Trust proxy headers for HTTPS (Railway runs behind a proxy)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Flask-Mail setup
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@uptriv.app')
mail = Mail(app)

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY')

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

# Learning resources for knowledge gaps
LEARNING_RESOURCES = {
    'news': {
        'current_events': [
            {'type': 'read', 'title': 'AP News Daily', 'url': 'https://apnews.com', 'desc': 'Unbiased daily news coverage'},
            {'type': 'watch', 'title': 'TLDR News (YouTube)', 'url': 'https://youtube.com/@TLDRNews', 'desc': '10-min explainers on current events'},
            {'type': 'listen', 'title': 'The Daily (NYT Podcast)', 'desc': '20-min deep dives on top stories'},
        ],
        'politics': [
            {'type': 'read', 'title': 'The Economist', 'url': 'https://economist.com', 'desc': 'In-depth political analysis'},
            {'type': 'watch', 'title': 'Vox (YouTube)', 'url': 'https://youtube.com/@Vox', 'desc': 'Visual explainers on policy & politics'},
            {'type': 'listen', 'title': 'Pod Save America', 'desc': 'US politics from Obama staffers'},
        ],
        'world_affairs': [
            {'type': 'read', 'title': 'Foreign Affairs', 'url': 'https://foreignaffairs.com', 'desc': 'Global politics & international relations'},
            {'type': 'watch', 'title': 'CaspianReport (YouTube)', 'url': 'https://youtube.com/@CaspianReport', 'desc': 'Geopolitics explained'},
            {'type': 'listen', 'title': 'Global News Podcast (BBC)', 'desc': 'Twice-daily world news roundup'},
        ],
        'famous_people': [
            {'type': 'read', 'title': 'Biography.com', 'url': 'https://biography.com', 'desc': 'Notable figures past & present'},
            {'type': 'watch', 'title': 'Biographics (YouTube)', 'url': 'https://youtube.com/@Biographics', 'desc': 'Video biographies of famous people'},
            {'type': 'listen', 'title': 'Revisionist History', 'desc': 'Malcolm Gladwell on overlooked stories'},
        ],
    },
    'history': {
        'ancient': [
            {'type': 'read', 'title': 'SPQR by Mary Beard', 'desc': 'Definitive history of ancient Rome'},
            {'type': 'watch', 'title': 'Historia Civilis (YouTube)', 'url': 'https://youtube.com/@HistoriaCivilis', 'desc': 'Animated ancient history'},
            {'type': 'listen', 'title': 'The History of Rome Podcast', 'desc': '179 episodes covering Rome\'s history'},
        ],
        'medieval': [
            {'type': 'read', 'title': 'The Time Traveler\'s Guide to Medieval England', 'desc': 'Immersive medieval history'},
            {'type': 'watch', 'title': 'Kings and Generals (YouTube)', 'url': 'https://youtube.com/@KingsandGenerals', 'desc': 'Medieval battles & kingdoms'},
            {'type': 'stream', 'title': 'The Last Kingdom (Netflix)', 'desc': 'Saxon England drama series'},
        ],
        'modern': [
            {'type': 'read', 'title': 'The Guns of August by Barbara Tuchman', 'desc': 'WWI origins, Pulitzer winner'},
            {'type': 'watch', 'title': 'The Great War (YouTube)', 'url': 'https://youtube.com/@TheGreatWar', 'desc': 'Week-by-week WWI coverage'},
            {'type': 'listen', 'title': 'Hardcore History', 'desc': 'Dan Carlin\'s epic history deep dives'},
        ],
        'wars': [
            {'type': 'read', 'title': 'A World at Arms by Gerhard Weinberg', 'desc': 'Comprehensive WWII history'},
            {'type': 'watch', 'title': 'World War Two (YouTube)', 'url': 'https://youtube.com/@WorldWarTwo', 'desc': 'WWII week by week'},
            {'type': 'stream', 'title': 'Band of Brothers (Max)', 'desc': 'WWII miniseries masterpiece'},
        ],
        'presidents': [
            {'type': 'read', 'title': 'Team of Rivals by Doris Kearns Goodwin', 'desc': 'Lincoln\'s political genius'},
            {'type': 'watch', 'title': 'American Experience: The Presidents (PBS)', 'desc': 'Documentary series on US presidents'},
            {'type': 'listen', 'title': 'Presidential Podcast (Washington Post)', 'desc': 'Story of each president'},
        ],
        'world_history': [
            {'type': 'read', 'title': 'Sapiens by Yuval Noah Harari', 'desc': 'Human history overview'},
            {'type': 'watch', 'title': 'Crash Course World History (YouTube)', 'url': 'https://youtube.com/@crashcourse', 'desc': 'Fast-paced world history'},
            {'type': 'listen', 'title': 'Stuff You Missed in History Class', 'desc': 'Overlooked historical stories'},
        ],
    },
    'science': {
        'space': [
            {'type': 'read', 'title': 'Cosmos by Carl Sagan', 'desc': 'Classic introduction to astronomy'},
            {'type': 'watch', 'title': 'PBS Space Time (YouTube)', 'url': 'https://youtube.com/@pbsspacetime', 'desc': 'Deep dives into astrophysics'},
            {'type': 'stream', 'title': 'Cosmos: A Spacetime Odyssey (Disney+)', 'desc': 'Neil deGrasse Tyson\'s visual journey'},
        ],
        'astronomy': [
            {'type': 'read', 'title': 'Astrophysics for People in a Hurry', 'desc': 'Neil deGrasse Tyson\'s quick guide'},
            {'type': 'watch', 'title': 'Scott Manley (YouTube)', 'url': 'https://youtube.com/@scottmanley', 'desc': 'Space exploration & rockets'},
            {'type': 'listen', 'title': 'StarTalk Radio', 'desc': 'Neil deGrasse Tyson\'s science podcast'},
        ],
        'biology': [
            {'type': 'read', 'title': 'The Gene by Siddhartha Mukherjee', 'desc': 'History of genetics'},
            {'type': 'watch', 'title': 'Kurzgesagt (YouTube)', 'url': 'https://youtube.com/@kurzgesagt', 'desc': 'Animated science explainers'},
            {'type': 'stream', 'title': 'Planet Earth (Netflix)', 'desc': 'David Attenborough nature series'},
        ],
        'physics': [
            {'type': 'read', 'title': 'A Brief History of Time by Stephen Hawking', 'desc': 'Physics for everyone'},
            {'type': 'watch', 'title': 'Veritasium (YouTube)', 'url': 'https://youtube.com/@veritasium', 'desc': 'Fascinating physics videos'},
            {'type': 'listen', 'title': 'Radiolab', 'desc': 'Science storytelling at its best'},
        ],
        'chemistry': [
            {'type': 'read', 'title': 'The Disappearing Spoon by Sam Kean', 'desc': 'Stories behind the periodic table'},
            {'type': 'watch', 'title': 'Periodic Videos (YouTube)', 'url': 'https://youtube.com/@periodicvideos', 'desc': 'Every element explained'},
            {'type': 'stream', 'title': 'Breaking Bad (Netflix)', 'desc': 'Chemistry-themed drama (fiction!)'},
        ],
        'earth_science': [
            {'type': 'read', 'title': 'A Short History of Nearly Everything', 'desc': 'Bill Bryson\'s science adventure'},
            {'type': 'watch', 'title': 'MinuteEarth (YouTube)', 'url': 'https://youtube.com/@MinuteEarth', 'desc': 'Quick earth science lessons'},
            {'type': 'stream', 'title': 'Our Planet (Netflix)', 'desc': 'Earth\'s ecosystems documentary'},
        ],
    },
    'entertainment': {
        'movies': [
            {'type': 'read', 'title': 'IMDb Top 250', 'url': 'https://imdb.com/chart/top', 'desc': 'Must-see films ranked'},
            {'type': 'watch', 'title': 'Lessons from the Screenplay (YouTube)', 'url': 'https://youtube.com/@LessonsFromTheScreenplay', 'desc': 'Film analysis & storytelling'},
            {'type': 'listen', 'title': 'The Rewatchables (Ringer)', 'desc': 'Deep dives on classic movies'},
        ],
        'tv': [
            {'type': 'read', 'title': 'TV Guide\'s Greatest Shows', 'desc': 'Classic & modern TV essentials'},
            {'type': 'watch', 'title': 'Nerdwriter1 (YouTube)', 'url': 'https://youtube.com/@Nerdwriter1', 'desc': 'Video essays on TV & culture'},
            {'type': 'listen', 'title': 'TV Avalanche', 'desc': 'Weekly TV discussion podcast'},
        ],
        'music': [
            {'type': 'read', 'title': 'Rolling Stone\'s 500 Greatest Albums', 'desc': 'Essential music history'},
            {'type': 'watch', 'title': 'Polyphonic (YouTube)', 'url': 'https://youtube.com/@Polyphonic', 'desc': 'Music history & analysis'},
            {'type': 'listen', 'title': 'Song Exploder', 'desc': 'Artists break down their songs'},
        ],
        'literature': [
            {'type': 'read', 'title': 'Penguin Classics Collection', 'desc': 'Essential world literature'},
            {'type': 'watch', 'title': 'Crash Course Literature (YouTube)', 'url': 'https://youtube.com/@crashcourse', 'desc': 'Quick lit lessons'},
            {'type': 'listen', 'title': 'LeVar Burton Reads', 'desc': 'Short fiction read aloud'},
        ],
        'arts': [
            {'type': 'read', 'title': 'The Story of Art by E.H. Gombrich', 'desc': 'Classic art history intro'},
            {'type': 'watch', 'title': 'Great Art Explained (YouTube)', 'url': 'https://youtube.com/@GreatArtExplained', 'desc': '15-min masterpiece deep dives'},
            {'type': 'stream', 'title': 'Abstract: The Art of Design (Netflix)', 'desc': 'Profiles of top designers'},
        ],
        'games': [
            {'type': 'read', 'title': 'Blood, Sweat, and Pixels', 'desc': 'Behind-the-scenes game development'},
            {'type': 'watch', 'title': 'NoClip Documentaries (YouTube)', 'url': 'https://youtube.com/@noclip', 'desc': 'Video game documentaries'},
            {'type': 'stream', 'title': 'High Score (Netflix)', 'desc': 'History of video games docuseries'},
        ],
    },
    'sports': {
        'football': [
            {'type': 'read', 'title': 'The Blind Side by Michael Lewis', 'desc': 'Football & human interest'},
            {'type': 'watch', 'title': 'NFL Films (YouTube)', 'url': 'https://youtube.com/@NFL', 'desc': 'Classic NFL moments'},
            {'type': 'stream', 'title': 'Quarterback (Netflix)', 'desc': 'Behind-the-scenes NFL docuseries'},
        ],
        'basketball': [
            {'type': 'read', 'title': 'The Book of Basketball by Bill Simmons', 'desc': 'NBA history & legends'},
            {'type': 'stream', 'title': 'The Last Dance (Netflix)', 'desc': 'Michael Jordan documentary'},
            {'type': 'listen', 'title': 'The Bill Simmons Podcast', 'desc': 'NBA talk & sports culture'},
        ],
        'baseball': [
            {'type': 'read', 'title': 'Moneyball by Michael Lewis', 'desc': 'Baseball analytics revolution'},
            {'type': 'stream', 'title': 'Ken Burns: Baseball (PBS)', 'desc': 'Epic baseball documentary'},
            {'type': 'listen', 'title': 'Effectively Wild', 'desc': 'Daily baseball analysis'},
        ],
        'soccer': [
            {'type': 'read', 'title': 'Inverting the Pyramid by Jonathan Wilson', 'desc': 'Soccer tactics history'},
            {'type': 'watch', 'title': 'TIFO Football (YouTube)', 'url': 'https://youtube.com/@TifoFootball', 'desc': 'Tactical analysis & history'},
            {'type': 'stream', 'title': 'Sunderland \'Til I Die (Netflix)', 'desc': 'English football club docuseries'},
        ],
        'olympics': [
            {'type': 'read', 'title': 'The Boys in the Boat', 'desc': '1936 Olympic rowing story'},
            {'type': 'watch', 'title': 'Olympic Channel (YouTube)', 'url': 'https://youtube.com/@olympics', 'desc': 'Historic Olympic moments'},
            {'type': 'stream', 'title': 'Icarus (Netflix)', 'desc': 'Olympic doping scandal documentary'},
        ],
        'misc': [
            {'type': 'read', 'title': 'Sports Illustrated Vault', 'url': 'https://vault.si.com', 'desc': 'Classic sports journalism'},
            {'type': 'stream', 'title': '30 for 30 (ESPN+)', 'desc': 'Award-winning sports docs'},
            {'type': 'listen', 'title': 'The Athletic Football Show', 'desc': 'Multi-sport analysis'},
        ],
        'hockey': [
            {'type': 'read', 'title': 'The Game by Ken Dryden', 'desc': 'Hockey memoir classic'},
            {'type': 'watch', 'title': 'NHL Vault (YouTube)', 'url': 'https://youtube.com/@NHL', 'desc': 'Classic hockey highlights'},
            {'type': 'listen', 'title': 'Spittin\' Chiclets', 'desc': 'Hockey culture podcast'},
        ],
        'tennis': [
            {'type': 'read', 'title': 'Open by Andre Agassi', 'desc': 'Tennis autobiography'},
            {'type': 'stream', 'title': 'Break Point (Netflix)', 'desc': 'Behind-the-scenes tennis doc'},
            {'type': 'listen', 'title': 'No Challenges Remaining', 'desc': 'Tennis analysis podcast'},
        ],
        'golf': [
            {'type': 'read', 'title': 'The Match by Mark Frost', 'desc': 'Golf history classic'},
            {'type': 'watch', 'title': 'PGA Tour (YouTube)', 'url': 'https://youtube.com/@PGATOUR', 'desc': 'Golf highlights & history'},
            {'type': 'stream', 'title': 'Full Swing (Netflix)', 'desc': 'PGA Tour docuseries'},
        ],
    },
    'geography': {
        'countries': [
            {'type': 'read', 'title': 'Prisoners of Geography by Tim Marshall', 'desc': 'How maps explain the world'},
            {'type': 'watch', 'title': 'Geography Now (YouTube)', 'url': 'https://youtube.com/@GeographyNow', 'desc': 'Every country explained'},
            {'type': 'listen', 'title': 'Throughline (NPR)', 'desc': 'History behind current events'},
        ],
        'capitals': [
            {'type': 'read', 'title': 'Sporcle Geography Quizzes', 'url': 'https://sporcle.com/games/category/geography', 'desc': 'Practice world capitals'},
            {'type': 'watch', 'title': 'Seterra Geography Games', 'url': 'https://seterra.com', 'desc': 'Interactive map quizzes'},
            {'type': 'listen', 'title': 'Radiolab: Cities', 'desc': 'Stories of urban life'},
        ],
        'landmarks': [
            {'type': 'read', 'title': '1,000 Places to See Before You Die', 'desc': 'World landmarks guide'},
            {'type': 'stream', 'title': 'Rick Steves\' Europe (PBS)', 'desc': 'Travel & landmark tours'},
            {'type': 'listen', 'title': 'Atlas Obscura Podcast', 'desc': 'Hidden wonders of the world'},
        ],
        'maps': [
            {'type': 'read', 'title': 'The Map Book by Peter Barber', 'desc': 'Beautiful cartography history'},
            {'type': 'watch', 'title': 'Map Men (YouTube)', 'url': 'https://youtube.com/@JayForeman', 'desc': 'Fun cartography videos'},
            {'type': 'listen', 'title': '99% Invisible', 'desc': 'Design stories including maps'},
        ],
        'flags': [
            {'type': 'read', 'title': 'Flag Stories', 'url': 'https://flagstories.co', 'desc': 'Meaning behind flags'},
            {'type': 'watch', 'title': 'Geography Now (YouTube)', 'url': 'https://youtube.com/@GeographyNow', 'desc': 'Flag facts in country episodes'},
            {'type': 'listen', 'title': 'Vexillology Podcast', 'desc': 'All about flags'},
        ],
        'continents': [
            {'type': 'read', 'title': 'National Geographic Atlas', 'desc': 'Comprehensive world atlas'},
            {'type': 'watch', 'title': 'Atlas Pro (YouTube)', 'url': 'https://youtube.com/@AtlasPro1', 'desc': 'Geography & earth science'},
            {'type': 'stream', 'title': 'Seven Worlds, One Planet (BBC)', 'desc': 'Each continent explored'},
        ],
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
        {'q': 'Which country left the European Union in 2020?', 'a': 'United Kingdom', 'options': ['United Kingdom', 'Greece', 'Poland', 'Hungary'], 'sub': 'world_affairs'},
        {'q': 'Who became the first female Vice President of the United States?', 'a': 'Kamala Harris', 'options': ['Kamala Harris', 'Hillary Clinton', 'Nancy Pelosi', 'Elizabeth Warren'], 'sub': 'politics'},
        {'q': 'What pandemic caused global lockdowns starting in 2020?', 'a': 'COVID-19', 'options': ['COVID-19', 'SARS', 'H1N1', 'Ebola'], 'sub': 'current_events'},
        {'q': 'Which streaming service launched Disney+ in 2019?', 'a': 'Disney', 'options': ['Disney', 'Warner Bros', 'Universal', 'Paramount'], 'sub': 'current_events'},
        {'q': 'What ship blocked the Suez Canal for six days in 2021?', 'a': 'Ever Given', 'options': ['Ever Given', 'Ever Forward', 'Maersk Line', 'Costa Concordia'], 'sub': 'current_events'},
        {'q': 'Who is the CEO of Tesla?', 'a': 'Elon Musk', 'options': ['Elon Musk', 'Tim Cook', 'Satya Nadella', 'Jeff Bezos'], 'sub': 'famous_people'},
        {'q': 'Which country hosted the 2022 FIFA World Cup?', 'a': 'Qatar', 'options': ['Qatar', 'Russia', 'Brazil', 'UAE'], 'sub': 'current_events'},
        {'q': 'What cryptocurrency experienced a major crash in 2022?', 'a': 'Bitcoin', 'options': ['Bitcoin', 'Dogecoin', 'Ethereum', 'Litecoin'], 'sub': 'current_events'},
        {'q': 'Who is the founder of Amazon?', 'a': 'Jeff Bezos', 'options': ['Jeff Bezos', 'Elon Musk', 'Bill Gates', 'Mark Zuckerberg'], 'sub': 'famous_people'},
        {'q': 'Which social media app is known for short-form videos and is owned by ByteDance?', 'a': 'TikTok', 'options': ['TikTok', 'Instagram Reels', 'YouTube Shorts', 'Snapchat'], 'sub': 'current_events'},
        {'q': 'What organization did the US rejoin on President Biden\'s first day in office?', 'a': 'Paris Climate Agreement', 'options': ['Paris Climate Agreement', 'NATO', 'United Nations', 'WHO'], 'sub': 'politics'},
        {'q': 'Which European country experienced a major energy crisis in 2022 due to Russian gas cuts?', 'a': 'Germany', 'options': ['Germany', 'France', 'Spain', 'Italy'], 'sub': 'world_affairs'},
        {'q': 'Who is the current President of France?', 'a': 'Emmanuel Macron', 'options': ['Emmanuel Macron', 'François Hollande', 'Nicolas Sarkozy', 'Marine Le Pen'], 'sub': 'politics'},
        {'q': 'What company did Microsoft acquire for $69 billion in 2023?', 'a': 'Activision Blizzard', 'options': ['Activision Blizzard', 'Electronic Arts', 'Take-Two', 'Ubisoft'], 'sub': 'current_events'},
        {'q': 'Which vaccine was the first COVID-19 vaccine authorized in the US?', 'a': 'Pfizer-BioNTech', 'options': ['Pfizer-BioNTech', 'Moderna', 'Johnson & Johnson', 'AstraZeneca'], 'sub': 'current_events'},
        {'q': 'What is the name of the UK\'s royal family?', 'a': 'Windsor', 'options': ['Windsor', 'Tudor', 'Stuart', 'York'], 'sub': 'famous_people'},
        {'q': 'Which tech giant was fined billions by the EU for antitrust violations?', 'a': 'Google', 'options': ['Google', 'Apple', 'Amazon', 'Facebook'], 'sub': 'current_events'},
        {'q': 'Who succeeded Angela Merkel as Chancellor of Germany?', 'a': 'Olaf Scholz', 'options': ['Olaf Scholz', 'Friedrich Merz', 'Annalena Baerbock', 'Armin Laschet'], 'sub': 'politics'},
        {'q': 'What messaging app is owned by Meta (Facebook)?', 'a': 'WhatsApp', 'options': ['WhatsApp', 'Telegram', 'Signal', 'WeChat'], 'sub': 'current_events'},
        {'q': 'Which country\'s parliament was stormed on January 6, 2021?', 'a': 'United States', 'options': ['United States', 'Brazil', 'France', 'Germany'], 'sub': 'politics'},
        {'q': 'Who is the richest person in the world as of 2024?', 'a': 'Elon Musk', 'options': ['Elon Musk', 'Jeff Bezos', 'Bernard Arnault', 'Bill Gates'], 'sub': 'famous_people'},
        {'q': 'What company makes the iPhone?', 'a': 'Apple', 'options': ['Apple', 'Samsung', 'Google', 'Microsoft'], 'sub': 'current_events'},
        {'q': 'Which prince stepped back from royal duties in 2020?', 'a': 'Prince Harry', 'options': ['Prince Harry', 'Prince William', 'Prince Andrew', 'Prince Charles'], 'sub': 'famous_people'},
        {'q': 'What is the name of SpaceX\'s reusable rocket?', 'a': 'Falcon 9', 'options': ['Falcon 9', 'Atlas V', 'Delta IV', 'New Shepard'], 'sub': 'current_events'},
        {'q': 'Which country experienced massive protests in 2019 over an extradition bill?', 'a': 'Hong Kong', 'options': ['Hong Kong', 'Taiwan', 'Thailand', 'Myanmar'], 'sub': 'world_affairs'},
        {'q': 'Who is the CEO of Microsoft?', 'a': 'Satya Nadella', 'options': ['Satya Nadella', 'Bill Gates', 'Steve Ballmer', 'Sundar Pichai'], 'sub': 'famous_people'},
        {'q': 'What major infrastructure bill did Biden sign in 2021?', 'a': 'Infrastructure Investment and Jobs Act', 'options': ['Infrastructure Investment and Jobs Act', 'Build Back Better', 'American Rescue Plan', 'CHIPS Act'], 'sub': 'politics'},
        {'q': 'Which country\'s military took power in a 2021 coup?', 'a': 'Myanmar', 'options': ['Myanmar', 'Thailand', 'Afghanistan', 'Sudan'], 'sub': 'world_affairs'},
        {'q': 'What search engine is the most used in the world?', 'a': 'Google', 'options': ['Google', 'Bing', 'Yahoo', 'DuckDuckGo'], 'sub': 'current_events'},
        {'q': 'Who founded Facebook?', 'a': 'Mark Zuckerberg', 'options': ['Mark Zuckerberg', 'Jack Dorsey', 'Evan Spiegel', 'Kevin Systrom'], 'sub': 'famous_people'},
        {'q': 'What telescope launched by NASA in 2021 is the successor to Hubble?', 'a': 'James Webb Space Telescope', 'options': ['James Webb Space Telescope', 'Kepler', 'Chandra', 'Spitzer'], 'sub': 'current_events'},
        {'q': 'Which country did the Taliban retake control of in 2021?', 'a': 'Afghanistan', 'options': ['Afghanistan', 'Iraq', 'Syria', 'Pakistan'], 'sub': 'world_affairs'},
        {'q': 'What is Netflix\'s primary business?', 'a': 'Streaming video', 'options': ['Streaming video', 'DVD rental', 'Video games', 'Social media'], 'sub': 'current_events'},
        {'q': 'Who was the Queen of England until 2022?', 'a': 'Elizabeth II', 'options': ['Elizabeth II', 'Victoria', 'Elizabeth I', 'Mary'], 'sub': 'famous_people'},
        {'q': 'What major climate conference was held in Glasgow in 2021?', 'a': 'COP26', 'options': ['COP26', 'COP25', 'Paris Summit', 'Kyoto Protocol'], 'sub': 'world_affairs'},
        {'q': 'Which tech company created the Pixel smartphone?', 'a': 'Google', 'options': ['Google', 'Apple', 'Samsung', 'OnePlus'], 'sub': 'current_events'},
        {'q': 'Who is the Prime Minister of Canada?', 'a': 'Justin Trudeau', 'options': ['Justin Trudeau', 'Stephen Harper', 'Pierre Poilievre', 'Jean Chrétien'], 'sub': 'politics'},
        {'q': 'What cryptocurrency was created by the pseudonymous Satoshi Nakamoto?', 'a': 'Bitcoin', 'options': ['Bitcoin', 'Ethereum', 'Litecoin', 'Ripple'], 'sub': 'current_events'},
        {'q': 'Which company owns Instagram?', 'a': 'Meta', 'options': ['Meta', 'Google', 'Twitter', 'Snapchat'], 'sub': 'current_events'},
        {'q': 'What virus caused a global pandemic starting in Wuhan, China?', 'a': 'SARS-CoV-2', 'options': ['SARS-CoV-2', 'MERS', 'H5N1', 'Zika'], 'sub': 'current_events'},
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
        {'q': 'Who was the first man to walk on the moon?', 'a': 'Neil Armstrong', 'options': ['Neil Armstrong', 'Buzz Aldrin', 'John Glenn', 'Yuri Gagarin'], 'sub': 'modern'},
        {'q': 'What year did the Titanic sink?', 'a': '1912', 'options': ['1912', '1905', '1920', '1898'], 'sub': 'modern'},
        {'q': 'Who was the leader of Nazi Germany?', 'a': 'Adolf Hitler', 'options': ['Adolf Hitler', 'Benito Mussolini', 'Joseph Stalin', 'Francisco Franco'], 'sub': 'wars'},
        {'q': 'The French Revolution began in what year?', 'a': '1789', 'options': ['1789', '1776', '1804', '1815'], 'sub': 'world_history'},
        {'q': 'Who discovered America in 1492?', 'a': 'Christopher Columbus', 'options': ['Christopher Columbus', 'Amerigo Vespucci', 'Leif Erikson', 'Ferdinand Magellan'], 'sub': 'world_history'},
        {'q': 'What ancient wonder was located in Alexandria, Egypt?', 'a': 'Lighthouse', 'options': ['Lighthouse', 'Hanging Gardens', 'Colossus', 'Temple of Artemis'], 'sub': 'ancient'},
        {'q': 'Who was the first Roman Emperor?', 'a': 'Augustus', 'options': ['Augustus', 'Julius Caesar', 'Nero', 'Caligula'], 'sub': 'ancient'},
        {'q': 'The Industrial Revolution began in which country?', 'a': 'England', 'options': ['England', 'Germany', 'France', 'USA'], 'sub': 'modern'},
        {'q': 'Who wrote the Declaration of Independence?', 'a': 'Thomas Jefferson', 'options': ['Thomas Jefferson', 'Benjamin Franklin', 'John Adams', 'George Washington'], 'sub': 'presidents'},
        {'q': 'What empire was ruled by Genghis Khan?', 'a': 'Mongol Empire', 'options': ['Mongol Empire', 'Ottoman Empire', 'Roman Empire', 'Persian Empire'], 'sub': 'medieval'},
        {'q': 'The assassination of Archduke Franz Ferdinand triggered which war?', 'a': 'World War I', 'options': ['World War I', 'World War II', 'Napoleonic Wars', 'Franco-Prussian War'], 'sub': 'wars'},
        {'q': 'What year did the American Civil War begin?', 'a': '1861', 'options': ['1861', '1865', '1850', '1870'], 'sub': 'wars'},
        {'q': 'Who was the last Pharaoh of ancient Egypt?', 'a': 'Cleopatra', 'options': ['Cleopatra', 'Nefertiti', 'Hatshepsut', 'Tutankhamun'], 'sub': 'ancient'},
        {'q': 'What document did King John sign in 1215?', 'a': 'Magna Carta', 'options': ['Magna Carta', 'Bill of Rights', 'Constitution', 'Declaration'], 'sub': 'medieval'},
        {'q': 'Who painted the ceiling of the Sistine Chapel?', 'a': 'Michelangelo', 'options': ['Michelangelo', 'Leonardo da Vinci', 'Raphael', 'Donatello'], 'sub': 'medieval'},
        {'q': 'What was the Manhattan Project?', 'a': 'Development of atomic bomb', 'options': ['Development of atomic bomb', 'Space program', 'Spy network', 'Economic plan'], 'sub': 'wars'},
        {'q': 'Who was the first female Prime Minister of the UK?', 'a': 'Margaret Thatcher', 'options': ['Margaret Thatcher', 'Theresa May', 'Elizabeth I', 'Queen Victoria'], 'sub': 'modern'},
        {'q': 'What ancient city was destroyed by Mount Vesuvius in 79 AD?', 'a': 'Pompeii', 'options': ['Pompeii', 'Rome', 'Athens', 'Carthage'], 'sub': 'ancient'},
        {'q': 'Who was known as the "Sun King" of France?', 'a': 'Louis XIV', 'options': ['Louis XIV', 'Louis XVI', 'Napoleon', 'Charlemagne'], 'sub': 'world_history'},
        {'q': 'What year did the Soviet Union collapse?', 'a': '1991', 'options': ['1991', '1989', '1985', '1993'], 'sub': 'modern'},
        {'q': 'Who led India to independence from British rule?', 'a': 'Mahatma Gandhi', 'options': ['Mahatma Gandhi', 'Jawaharlal Nehru', 'Subhas Chandra Bose', 'Muhammad Ali Jinnah'], 'sub': 'world_history'},
        {'q': 'What was the primary cause of the Irish Potato Famine?', 'a': 'Potato blight', 'options': ['Potato blight', 'Drought', 'War', 'Flooding'], 'sub': 'world_history'},
        {'q': 'Who was the U.S. President during the Cuban Missile Crisis?', 'a': 'John F. Kennedy', 'options': ['John F. Kennedy', 'Dwight Eisenhower', 'Lyndon Johnson', 'Richard Nixon'], 'sub': 'presidents'},
        {'q': 'What ancient Greek city-state was known for its military prowess?', 'a': 'Sparta', 'options': ['Sparta', 'Athens', 'Corinth', 'Thebes'], 'sub': 'ancient'},
        {'q': 'Who invented the printing press?', 'a': 'Johannes Gutenberg', 'options': ['Johannes Gutenberg', 'Leonardo da Vinci', 'Benjamin Franklin', 'Thomas Edison'], 'sub': 'medieval'},
        {'q': 'What war was fought between the North and South of the United States?', 'a': 'Civil War', 'options': ['Civil War', 'Revolutionary War', 'War of 1812', 'Mexican-American War'], 'sub': 'wars'},
        {'q': 'Who was the first woman to fly solo across the Atlantic?', 'a': 'Amelia Earhart', 'options': ['Amelia Earhart', 'Harriet Quimby', 'Bessie Coleman', 'Jacqueline Cochran'], 'sub': 'modern'},
        {'q': 'What empire built Machu Picchu?', 'a': 'Inca', 'options': ['Inca', 'Aztec', 'Maya', 'Olmec'], 'sub': 'ancient'},
        {'q': 'Who was the U.S. President during the Great Depression\'s start?', 'a': 'Herbert Hoover', 'options': ['Herbert Hoover', 'Franklin D. Roosevelt', 'Calvin Coolidge', 'Warren Harding'], 'sub': 'presidents'},
        {'q': 'What event started the Great Depression in 1929?', 'a': 'Stock market crash', 'options': ['Stock market crash', 'Bank failures', 'Drought', 'War'], 'sub': 'modern'},
        {'q': 'Who unified Germany in 1871?', 'a': 'Otto von Bismarck', 'options': ['Otto von Bismarck', 'Kaiser Wilhelm I', 'Frederick the Great', 'Adolf Hitler'], 'sub': 'world_history'},
        {'q': 'What was the Black Death?', 'a': 'Bubonic plague', 'options': ['Bubonic plague', 'Cholera', 'Smallpox', 'Typhus'], 'sub': 'medieval'},
        {'q': 'Who was the longest-reigning British monarch before Elizabeth II?', 'a': 'Queen Victoria', 'options': ['Queen Victoria', 'George III', 'Henry VIII', 'Elizabeth I'], 'sub': 'world_history'},
        {'q': 'What year did the United States declare independence?', 'a': '1776', 'options': ['1776', '1789', '1783', '1774'], 'sub': 'presidents'},
        {'q': 'Who was the first President to be impeached?', 'a': 'Andrew Johnson', 'options': ['Andrew Johnson', 'Bill Clinton', 'Richard Nixon', 'Donald Trump'], 'sub': 'presidents'},
        {'q': 'What battle marked Napoleon\'s final defeat?', 'a': 'Waterloo', 'options': ['Waterloo', 'Trafalgar', 'Austerlitz', 'Borodino'], 'sub': 'wars'},
        {'q': 'Who was the leader of the Soviet Union during World War II?', 'a': 'Joseph Stalin', 'options': ['Joseph Stalin', 'Vladimir Lenin', 'Nikita Khrushchev', 'Leon Trotsky'], 'sub': 'wars'},
        {'q': 'What ancient trade route connected China to the Mediterranean?', 'a': 'Silk Road', 'options': ['Silk Road', 'Spice Route', 'Amber Road', 'Tea Road'], 'sub': 'ancient'},
        {'q': 'Who was the first explorer to circumnavigate the globe?', 'a': 'Ferdinand Magellan', 'options': ['Ferdinand Magellan', 'Christopher Columbus', 'Vasco da Gama', 'Francis Drake'], 'sub': 'world_history'},
        {'q': 'What was the primary purpose of the Lewis and Clark expedition?', 'a': 'Explore western territories', 'options': ['Explore western territories', 'Find gold', 'Establish trade', 'Map the coast'], 'sub': 'presidents'},
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
        {'q': 'What is the chemical formula for water?', 'a': 'H2O', 'options': ['H2O', 'CO2', 'NaCl', 'O2'], 'sub': 'chemistry'},
        {'q': 'What planet is known as the Red Planet?', 'a': 'Mars', 'options': ['Mars', 'Venus', 'Jupiter', 'Saturn'], 'sub': 'space'},
        {'q': 'What is the powerhouse of the cell?', 'a': 'Mitochondria', 'options': ['Mitochondria', 'Nucleus', 'Ribosome', 'Golgi body'], 'sub': 'biology'},
        {'q': 'What is the boiling point of water in Celsius?', 'a': '100°C', 'options': ['100°C', '90°C', '110°C', '212°C'], 'sub': 'physics'},
        {'q': 'How many chromosomes do humans have?', 'a': '46', 'options': ['46', '23', '48', '44'], 'sub': 'biology'},
        {'q': 'What element has the atomic number 1?', 'a': 'Hydrogen', 'options': ['Hydrogen', 'Helium', 'Oxygen', 'Carbon'], 'sub': 'chemistry'},
        {'q': 'What is the largest mammal on Earth?', 'a': 'Blue whale', 'options': ['Blue whale', 'Elephant', 'Giraffe', 'Hippopotamus'], 'sub': 'animals'},
        {'q': 'What is the center of an atom called?', 'a': 'Nucleus', 'options': ['Nucleus', 'Electron', 'Proton', 'Neutron'], 'sub': 'chemistry'},
        {'q': 'What gas makes up most of Earth\'s atmosphere?', 'a': 'Nitrogen', 'options': ['Nitrogen', 'Oxygen', 'Carbon dioxide', 'Argon'], 'sub': 'earth_science'},
        {'q': 'What is the smallest unit of life?', 'a': 'Cell', 'options': ['Cell', 'Atom', 'Molecule', 'Organ'], 'sub': 'biology'},
        {'q': 'What planet has the most moons?', 'a': 'Saturn', 'options': ['Saturn', 'Jupiter', 'Uranus', 'Neptune'], 'sub': 'space'},
        {'q': 'What type of rock is formed from cooled lava?', 'a': 'Igneous', 'options': ['Igneous', 'Sedimentary', 'Metamorphic', 'ite'], 'sub': 'earth_science'},
        {'q': 'What is the main gas in the Sun?', 'a': 'Hydrogen', 'options': ['Hydrogen', 'Helium', 'Oxygen', 'Nitrogen'], 'sub': 'space'},
        {'q': 'What vitamin is produced when skin is exposed to sunlight?', 'a': 'Vitamin D', 'options': ['Vitamin D', 'Vitamin C', 'Vitamin A', 'Vitamin B'], 'sub': 'human_body'},
        {'q': 'What is the study of earthquakes called?', 'a': 'Seismology', 'options': ['Seismology', 'Geology', 'Volcanology', 'Meteorology'], 'sub': 'earth_science'},
        {'q': 'How many legs does a spider have?', 'a': '8', 'options': ['8', '6', '10', '4'], 'sub': 'animals'},
        {'q': 'What is the chemical symbol for iron?', 'a': 'Fe', 'options': ['Fe', 'Ir', 'In', 'I'], 'sub': 'chemistry'},
        {'q': 'What organ pumps blood through the body?', 'a': 'Heart', 'options': ['Heart', 'Lungs', 'Liver', 'Brain'], 'sub': 'human_body'},
        {'q': 'What is the freezing point of water in Fahrenheit?', 'a': '32°F', 'options': ['32°F', '0°F', '100°F', '212°F'], 'sub': 'physics'},
        {'q': 'What type of animal is a dolphin?', 'a': 'Mammal', 'options': ['Mammal', 'Fish', 'Reptile', 'Amphibian'], 'sub': 'animals'},
        {'q': 'What planet is known for its rings?', 'a': 'Saturn', 'options': ['Saturn', 'Jupiter', 'Uranus', 'Neptune'], 'sub': 'space'},
        {'q': 'What is the most abundant element in the universe?', 'a': 'Hydrogen', 'options': ['Hydrogen', 'Helium', 'Oxygen', 'Carbon'], 'sub': 'chemistry'},
        {'q': 'What part of the plant conducts photosynthesis?', 'a': 'Leaves', 'options': ['Leaves', 'Roots', 'Stem', 'Flowers'], 'sub': 'biology'},
        {'q': 'What is the speed of sound in air at sea level?', 'a': '343 m/s', 'options': ['343 m/s', '300 m/s', '400 m/s', '500 m/s'], 'sub': 'physics'},
        {'q': 'What blood type is the universal donor?', 'a': 'O negative', 'options': ['O negative', 'AB positive', 'A positive', 'B negative'], 'sub': 'human_body'},
        {'q': 'What is the largest organ inside the human body?', 'a': 'Liver', 'options': ['Liver', 'Heart', 'Brain', 'Lungs'], 'sub': 'human_body'},
        {'q': 'What force opposes motion between surfaces?', 'a': 'Friction', 'options': ['Friction', 'Gravity', 'Magnetism', 'Tension'], 'sub': 'physics'},
        {'q': 'How many planets are in our solar system?', 'a': '8', 'options': ['8', '9', '7', '10'], 'sub': 'space'},
        {'q': 'What is table salt\'s chemical name?', 'a': 'Sodium chloride', 'options': ['Sodium chloride', 'Potassium chloride', 'Calcium chloride', 'Sodium bicarbonate'], 'sub': 'chemistry'},
        {'q': 'What is the largest species of big cat?', 'a': 'Tiger', 'options': ['Tiger', 'Lion', 'Leopard', 'Jaguar'], 'sub': 'animals'},
        {'q': 'What phenomenon causes the Northern Lights?', 'a': 'Solar particles', 'options': ['Solar particles', 'Moon reflection', 'Volcanic ash', 'Meteor showers'], 'sub': 'space'},
        {'q': 'What is the pH of pure water?', 'a': '7', 'options': ['7', '0', '14', '1'], 'sub': 'chemistry'},
        {'q': 'What carries oxygen in red blood cells?', 'a': 'Hemoglobin', 'options': ['Hemoglobin', 'Plasma', 'Platelets', 'White blood cells'], 'sub': 'human_body'},
        {'q': 'What is the study of weather called?', 'a': 'Meteorology', 'options': ['Meteorology', 'Climatology', 'Geology', 'Astronomy'], 'sub': 'earth_science'},
        {'q': 'What is the largest land animal?', 'a': 'African elephant', 'options': ['African elephant', 'Rhinoceros', 'Hippopotamus', 'Giraffe'], 'sub': 'animals'},
        {'q': 'What is absolute zero in Celsius?', 'a': '-273.15°C', 'options': ['-273.15°C', '-100°C', '0°C', '-459.67°C'], 'sub': 'physics'},
        {'q': 'What organelle contains genetic material?', 'a': 'Nucleus', 'options': ['Nucleus', 'Mitochondria', 'Ribosome', 'Cytoplasm'], 'sub': 'biology'},
        {'q': 'What scale is commonly used to measure the magnitude of earthquakes?', 'a': 'Richter scale', 'options': ['Richter scale', 'Mercalli scale', 'Beaufort scale', 'Mohs scale'], 'sub': 'earth_science'},
        {'q': 'What planet rotates on its side?', 'a': 'Uranus', 'options': ['Uranus', 'Neptune', 'Venus', 'Pluto'], 'sub': 'space'},
        {'q': 'What is the human body\'s largest muscle?', 'a': 'Gluteus maximus', 'options': ['Gluteus maximus', 'Quadriceps', 'Latissimus dorsi', 'Biceps'], 'sub': 'human_body'},
    ],
    'entertainment': [
        {'q': 'Which film won the Academy Award for Best Picture in 2024?', 'a': 'Oppenheimer', 'options': ['Oppenheimer', 'Barbie', 'Killers of the Flower Moon', 'Poor Things'], 'sub': 'movies'},
        {'q': 'Who sang "Bohemian Rhapsody"?', 'a': 'Queen', 'options': ['Queen', 'The Beatles', 'Led Zeppelin', 'Pink Floyd'], 'sub': 'music'},
        {'q': 'What TV series features a chemistry teacher turned drug manufacturer?', 'a': 'Breaking Bad', 'options': ['Breaking Bad', 'The Wire', 'Ozark', 'Narcos'], 'sub': 'tv'},
        {'q': 'Who wrote the Harry Potter book series?', 'a': 'J.K. Rowling', 'options': ['J.K. Rowling', 'Stephen King', 'George R.R. Martin', 'Suzanne Collins'], 'sub': 'literature'},
        {'q': 'Which artist released the album "1989"?', 'a': 'Taylor Swift', 'options': ['Taylor Swift', 'Beyoncé', 'Adele', 'Lady Gaga'], 'sub': 'music'},
        {'q': 'In what year was the first iPhone released?', 'a': '2007', 'options': ['2007', '2005', '2008', '2010'], 'sub': 'tech'},
        {'q': 'Which movie features the quote "I\'ll be back"?', 'a': 'The Terminator', 'options': ['The Terminator', 'Predator', 'Total Recall', 'Commando'], 'sub': 'movies'},
        {'q': 'Who played Iron Man in the Marvel Cinematic Universe?', 'a': 'Robert Downey Jr.', 'options': ['Robert Downey Jr.', 'Chris Evans', 'Chris Hemsworth', 'Mark Ruffalo'], 'sub': 'movies'},
        {'q': 'Which band performed "Smells Like Teen Spirit"?', 'a': 'Nirvana', 'options': ['Nirvana', 'Pearl Jam', 'Soundgarden', 'Alice in Chains'], 'sub': 'music'},
        {'q': 'What streaming service produced "Stranger Things"?', 'a': 'Netflix', 'options': ['Netflix', 'Hulu', 'Amazon Prime', 'Disney+'], 'sub': 'tv'},
        {'q': 'Who directed the movie "Titanic"?', 'a': 'James Cameron', 'options': ['James Cameron', 'Steven Spielberg', 'Martin Scorsese', 'Christopher Nolan'], 'sub': 'movies'},
        {'q': 'What band was Freddie Mercury the lead singer of?', 'a': 'Queen', 'options': ['Queen', 'The Rolling Stones', 'Led Zeppelin', 'The Who'], 'sub': 'music'},
        {'q': 'Which TV show features dragons and the Iron Throne?', 'a': 'Game of Thrones', 'options': ['Game of Thrones', 'Lord of the Rings', 'The Witcher', 'Vikings'], 'sub': 'tv'},
        {'q': 'Who wrote "Romeo and Juliet"?', 'a': 'William Shakespeare', 'options': ['William Shakespeare', 'Charles Dickens', 'Jane Austen', 'Mark Twain'], 'sub': 'literature'},
        {'q': 'What movie features a shark terrorizing a beach town?', 'a': 'Jaws', 'options': ['Jaws', 'The Meg', 'Deep Blue Sea', 'Sharknado'], 'sub': 'movies'},
        {'q': 'Who is known as the "King of Pop"?', 'a': 'Michael Jackson', 'options': ['Michael Jackson', 'Elvis Presley', 'Prince', 'Stevie Wonder'], 'sub': 'music'},
        {'q': 'What sitcom featured six friends living in New York City?', 'a': 'Friends', 'options': ['Friends', 'Seinfeld', 'How I Met Your Mother', 'The Big Bang Theory'], 'sub': 'tv'},
        {'q': 'Who wrote "1984"?', 'a': 'George Orwell', 'options': ['George Orwell', 'Aldous Huxley', 'Ray Bradbury', 'H.G. Wells'], 'sub': 'literature'},
        {'q': 'Which film won the first Academy Award for Best Picture?', 'a': 'Wings', 'options': ['Wings', 'The Jazz Singer', 'Sunrise', 'The Broadway Melody'], 'sub': 'movies'},
        {'q': 'What band sang "Hotel California"?', 'a': 'Eagles', 'options': ['Eagles', 'Fleetwood Mac', 'The Doors', 'Creedence Clearwater Revival'], 'sub': 'music'},
        {'q': 'What animated show features a family named Griffin in Quahog, Rhode Island?', 'a': 'Family Guy', 'options': ['Family Guy', 'The Simpsons', 'American Dad', 'South Park'], 'sub': 'tv'},
        {'q': 'Who wrote "Pride and Prejudice"?', 'a': 'Jane Austen', 'options': ['Jane Austen', 'Charlotte Brontë', 'Emily Brontë', 'Virginia Woolf'], 'sub': 'literature'},
        {'q': 'What animated film features a lion cub named Simba?', 'a': 'The Lion King', 'options': ['The Lion King', 'Madagascar', 'The Jungle Book', 'Tarzan'], 'sub': 'movies'},
        {'q': 'Who sang "Like a Virgin"?', 'a': 'Madonna', 'options': ['Madonna', 'Cyndi Lauper', 'Whitney Houston', 'Janet Jackson'], 'sub': 'music'},
        {'q': 'What TV series is set in the 1960s at a fictional advertising agency on Madison Avenue?', 'a': 'Mad Men', 'options': ['Mad Men', 'Boardwalk Empire', 'The Crown', 'Downton Abbey'], 'sub': 'tv'},
        {'q': 'Who wrote "The Great Gatsby"?', 'a': 'F. Scott Fitzgerald', 'options': ['F. Scott Fitzgerald', 'Ernest Hemingway', 'John Steinbeck', 'William Faulkner'], 'sub': 'literature'},
        {'q': 'What superhero is also known as the "Dark Knight"?', 'a': 'Batman', 'options': ['Batman', 'Superman', 'Spider-Man', 'Iron Man'], 'sub': 'movies'},
        {'q': 'Who is the lead singer of U2?', 'a': 'Bono', 'options': ['Bono', 'The Edge', 'Sting', 'Chris Martin'], 'sub': 'music'},
        {'q': 'What TV show follows the Bluth family?', 'a': 'Arrested Development', 'options': ['Arrested Development', 'Modern Family', 'Schitt\'s Creek', 'The Office'], 'sub': 'tv'},
        {'q': 'Who wrote "To Kill a Mockingbird"?', 'a': 'Harper Lee', 'options': ['Harper Lee', 'John Steinbeck', 'Mark Twain', 'Ernest Hemingway'], 'sub': 'literature'},
        {'q': 'What movie trilogy features Frodo and the One Ring?', 'a': 'Lord of the Rings', 'options': ['Lord of the Rings', 'The Hobbit', 'Harry Potter', 'Narnia'], 'sub': 'movies'},
        {'q': 'Who sang "Thriller"?', 'a': 'Michael Jackson', 'options': ['Michael Jackson', 'Prince', 'Stevie Wonder', 'James Brown'], 'sub': 'music'},
        {'q': 'What TV series follows the Shelby crime family in post-WWI Birmingham, England?', 'a': 'Peaky Blinders', 'options': ['Peaky Blinders', 'Boardwalk Empire', 'Vikings', 'Downton Abbey'], 'sub': 'tv'},
        {'q': 'Who wrote "The Catcher in the Rye"?', 'a': 'J.D. Salinger', 'options': ['J.D. Salinger', 'Jack Kerouac', 'F. Scott Fitzgerald', 'Ernest Hemingway'], 'sub': 'literature'},
        {'q': 'What movie features a DeLorean time machine?', 'a': 'Back to the Future', 'options': ['Back to the Future', 'The Terminator', 'Bill & Ted', 'Hot Tub Time Machine'], 'sub': 'movies'},
        {'q': 'Who is the lead singer of Coldplay?', 'a': 'Chris Martin', 'options': ['Chris Martin', 'Thom Yorke', 'Brandon Flowers', 'Matt Bellamy'], 'sub': 'music'},
        {'q': 'What TV show features the Dunder Mifflin Paper Company?', 'a': 'The Office', 'options': ['The Office', 'Parks and Recreation', 'Brooklyn Nine-Nine', 'Superstore'], 'sub': 'tv'},
        {'q': 'Who wrote "Moby-Dick"?', 'a': 'Herman Melville', 'options': ['Herman Melville', 'Mark Twain', 'Nathaniel Hawthorne', 'Edgar Allan Poe'], 'sub': 'literature'},
        {'q': 'What movie features the character Jack Sparrow?', 'a': 'Pirates of the Caribbean', 'options': ['Pirates of the Caribbean', 'The Princess Bride', 'Master and Commander', 'Cutthroat Island'], 'sub': 'movies'},
        {'q': 'Who sang "Rolling in the Deep"?', 'a': 'Adele', 'options': ['Adele', 'Amy Winehouse', 'Beyoncé', 'Rihanna'], 'sub': 'music'},
        {'q': 'What TV show is set in the fictional town of Hawkins, Indiana?', 'a': 'Stranger Things', 'options': ['Stranger Things', 'Supernatural', 'The X-Files', 'Twin Peaks'], 'sub': 'tv'},
        {'q': 'Who wrote "The Hunger Games"?', 'a': 'Suzanne Collins', 'options': ['Suzanne Collins', 'Veronica Roth', 'James Dashner', 'Stephenie Meyer'], 'sub': 'literature'},
        {'q': 'What movie features the quote "Here\'s looking at you, kid"?', 'a': 'Casablanca', 'options': ['Casablanca', 'Gone with the Wind', 'Citizen Kane', 'The Maltese Falcon'], 'sub': 'movies'},
        {'q': 'Who is the lead singer of The Rolling Stones?', 'a': 'Mick Jagger', 'options': ['Mick Jagger', 'Keith Richards', 'Roger Daltrey', 'Robert Plant'], 'sub': 'music'},
        {'q': 'What comedy series features the Parks Department employees of Pawnee, Indiana?', 'a': 'Parks and Recreation', 'options': ['Parks and Recreation', 'The Office', 'Brooklyn Nine-Nine', 'Superstore'], 'sub': 'tv'},
        {'q': 'Who wrote "Lord of the Flies"?', 'a': 'William Golding', 'options': ['William Golding', 'George Orwell', 'Aldous Huxley', 'Ray Bradbury'], 'sub': 'literature'},
        {'q': 'What Disney movie features a wooden puppet who wants to be a real boy?', 'a': 'Pinocchio', 'options': ['Pinocchio', 'Dumbo', 'Bambi', 'Fantasia'], 'sub': 'movies'},
        {'q': 'Who sang "Purple Rain"?', 'a': 'Prince', 'options': ['Prince', 'Michael Jackson', 'Stevie Wonder', 'James Brown'], 'sub': 'music'},
        {'q': 'What TV show features FBI agents Mulder and Scully?', 'a': 'The X-Files', 'options': ['The X-Files', 'Criminal Minds', 'Fringe', 'Supernatural'], 'sub': 'tv'},
        {'q': 'Who wrote "Brave New World"?', 'a': 'Aldous Huxley', 'options': ['Aldous Huxley', 'George Orwell', 'Ray Bradbury', 'H.G. Wells'], 'sub': 'literature'},
    ],
    'sports': [
        {'q': 'Which country has won the most FIFA World Cup titles?', 'a': 'Brazil', 'options': ['Brazil', 'Germany', 'Italy', 'Argentina'], 'sub': 'soccer'},
        {'q': 'How many players are on a basketball team on the court at once?', 'a': '5', 'options': ['5', '6', '7', '4'], 'sub': 'basketball'},
        {'q': 'Who holds the record for most home runs in MLB history?', 'a': 'Barry Bonds', 'options': ['Barry Bonds', 'Hank Aaron', 'Babe Ruth', 'Alex Rodriguez'], 'sub': 'baseball'},
        {'q': 'Which NFL team has won the most Super Bowls?', 'a': 'New England Patriots', 'options': ['New England Patriots', 'Pittsburgh Steelers', 'Dallas Cowboys', 'San Francisco 49ers'], 'sub': 'football'},
        {'q': 'In which city were the 2020 Summer Olympics held (delayed to 2021)?', 'a': 'Tokyo', 'options': ['Tokyo', 'Paris', 'London', 'Rio de Janeiro'], 'sub': 'olympics'},
        {'q': 'Who is the all-time leading scorer in NBA history?', 'a': 'LeBron James', 'options': ['LeBron James', 'Kareem Abdul-Jabbar', 'Michael Jordan', 'Kobe Bryant'], 'sub': 'basketball'},
        {'q': 'What is the only Grand Slam tennis tournament played on grass?', 'a': 'Wimbledon', 'options': ['Wimbledon', 'US Open', 'French Open', 'Australian Open'], 'sub': 'tennis'},
        {'q': 'In which city were the first modern Olympic Games held in 1896?', 'a': 'Athens', 'options': ['Athens', 'Paris', 'London', 'Rome'], 'sub': 'olympics'},
        {'q': 'What sport is played at Augusta National?', 'a': 'Golf', 'options': ['Golf', 'Tennis', 'Polo', 'Cricket'], 'sub': 'golf'},
        {'q': 'Who won Super Bowl LVIII in 2024?', 'a': 'Kansas City Chiefs', 'options': ['Kansas City Chiefs', 'San Francisco 49ers', 'Philadelphia Eagles', 'Baltimore Ravens'], 'sub': 'football'},
        {'q': 'What is the national sport of Canada?', 'a': 'Lacrosse', 'options': ['Lacrosse', 'Ice Hockey', 'Curling', 'Baseball'], 'sub': 'misc'},
        {'q': 'How many points is a touchdown worth in American football?', 'a': '6', 'options': ['6', '7', '3', '4'], 'sub': 'football'},
        {'q': 'Who is known as "The Great One" in hockey?', 'a': 'Wayne Gretzky', 'options': ['Wayne Gretzky', 'Mario Lemieux', 'Bobby Orr', 'Gordie Howe'], 'sub': 'hockey'},
        {'q': 'Which country won the first FIFA World Cup in 1930?', 'a': 'Uruguay', 'options': ['Uruguay', 'Brazil', 'Argentina', 'Italy'], 'sub': 'soccer'},
        {'q': 'How long is a marathon in miles?', 'a': '26.2', 'options': ['26.2', '24', '25', '30'], 'sub': 'misc'},
        {'q': 'Who holds the record for most career NBA championships as a player?', 'a': 'Bill Russell', 'options': ['Bill Russell', 'Michael Jordan', 'LeBron James', 'Magic Johnson'], 'sub': 'basketball'},
        {'q': 'What sport uses a shuttlecock?', 'a': 'Badminton', 'options': ['Badminton', 'Tennis', 'Squash', 'Racquetball'], 'sub': 'misc'},
        {'q': 'Which country has won the most Cricket World Cups?', 'a': 'Australia', 'options': ['Australia', 'India', 'West Indies', 'England'], 'sub': 'misc'},
        {'q': 'Who won the 2023 NBA Finals?', 'a': 'Denver Nuggets', 'options': ['Denver Nuggets', 'Miami Heat', 'Boston Celtics', 'Golden State Warriors'], 'sub': 'basketball'},
        {'q': 'What is the maximum score in a single frame of bowling?', 'a': '30', 'options': ['30', '10', '20', '50'], 'sub': 'misc'},
        {'q': 'Who holds the record for most Grand Slam tennis titles (men)?', 'a': 'Novak Djokovic', 'options': ['Novak Djokovic', 'Rafael Nadal', 'Roger Federer', 'Pete Sampras'], 'sub': 'tennis'},
        {'q': 'What is the diameter of a basketball hoop in inches?', 'a': '18', 'options': ['18', '20', '16', '24'], 'sub': 'basketball'},
        {'q': 'Which boxer was known as "The Greatest"?', 'a': 'Muhammad Ali', 'options': ['Muhammad Ali', 'Mike Tyson', 'Joe Frazier', 'George Foreman'], 'sub': 'misc'},
        {'q': 'How many holes are played in a standard round of golf?', 'a': '18', 'options': ['18', '9', '12', '21'], 'sub': 'golf'},
        {'q': 'Which team has won the most MLB World Series?', 'a': 'New York Yankees', 'options': ['New York Yankees', 'St. Louis Cardinals', 'Boston Red Sox', 'Los Angeles Dodgers'], 'sub': 'baseball'},
        {'q': 'What is the term for three strikes in a row in bowling?', 'a': 'Turkey', 'options': ['Turkey', 'Hat trick', 'Triple', 'Strike out'], 'sub': 'misc'},
        {'q': 'What NBA team did Michael Jordan win 6 championships with?', 'a': 'Chicago Bulls', 'options': ['Chicago Bulls', 'Los Angeles Lakers', 'Boston Celtics', 'Detroit Pistons'], 'sub': 'basketball'},
        {'q': 'What country is sumo wrestling from?', 'a': 'Japan', 'options': ['Japan', 'China', 'Korea', 'Mongolia'], 'sub': 'misc'},
        {'q': 'How many periods are in an NHL hockey game?', 'a': '3', 'options': ['3', '4', '2', '5'], 'sub': 'hockey'},
        {'q': 'Who holds the record for most career goals in NHL history?', 'a': 'Wayne Gretzky', 'options': ['Wayne Gretzky', 'Gordie Howe', 'Alex Ovechkin', 'Jaromir Jagr'], 'sub': 'hockey'},
        {'q': 'What is the term for a score of one under par in golf?', 'a': 'Birdie', 'options': ['Birdie', 'Eagle', 'Bogey', 'Par'], 'sub': 'golf'},
        {'q': 'Which country has won the most Olympic gold medals all-time?', 'a': 'United States', 'options': ['United States', 'Soviet Union', 'China', 'Great Britain'], 'sub': 'olympics'},
        {'q': 'How many players are on a baseball team on the field?', 'a': '9', 'options': ['9', '10', '8', '11'], 'sub': 'baseball'},
        {'q': 'What tennis tournament is played on clay courts?', 'a': 'French Open', 'options': ['French Open', 'US Open', 'Wimbledon', 'Australian Open'], 'sub': 'tennis'},
        {'q': 'Who is the fastest man in the world based on the 100m record?', 'a': 'Usain Bolt', 'options': ['Usain Bolt', 'Carl Lewis', 'Tyson Gay', 'Yohan Blake'], 'sub': 'olympics'},
        {'q': 'What is a perfect score in a game of ten-pin bowling?', 'a': '300', 'options': ['300', '200', '400', '150'], 'sub': 'misc'},
        {'q': 'Which team won the first Super Bowl?', 'a': 'Green Bay Packers', 'options': ['Green Bay Packers', 'Kansas City Chiefs', 'Dallas Cowboys', 'Miami Dolphins'], 'sub': 'football'},
        {'q': 'How many sets does a player need to win a men\'s Grand Slam tennis match?', 'a': '3', 'options': ['3', '2', '4', '5'], 'sub': 'tennis'},
        {'q': 'What sport is known as "the beautiful game"?', 'a': 'Soccer', 'options': ['Soccer', 'Basketball', 'Cricket', 'Rugby'], 'sub': 'soccer'},
        {'q': 'Which golfer has won the most major championships?', 'a': 'Jack Nicklaus', 'options': ['Jack Nicklaus', 'Tiger Woods', 'Arnold Palmer', 'Gary Player'], 'sub': 'golf'},
        {'q': 'What is the name of the trophy awarded to NHL champions?', 'a': 'Stanley Cup', 'options': ['Stanley Cup', 'Presidents Trophy', 'Conn Smythe', 'Hart Trophy'], 'sub': 'hockey'},
        {'q': 'How many players are on a soccer team on the field?', 'a': '11', 'options': ['11', '10', '9', '12'], 'sub': 'soccer'},
        {'q': 'Who holds the record for most career passing yards in the NFL?', 'a': 'Tom Brady', 'options': ['Tom Brady', 'Drew Brees', 'Peyton Manning', 'Brett Favre'], 'sub': 'football'},
        {'q': 'In pool, what color is the 8-ball?', 'a': 'Black', 'options': ['Black', 'White', 'Red', 'Blue'], 'sub': 'misc'},
        {'q': 'Which country invented basketball?', 'a': 'United States', 'options': ['United States', 'Canada', 'England', 'France'], 'sub': 'basketball'},
        {'q': 'How many rings are on the Olympic flag?', 'a': '5', 'options': ['5', '6', '4', '7'], 'sub': 'olympics'},
        {'q': 'What is the distance of a free throw line from the basket?', 'a': '15 feet', 'options': ['15 feet', '12 feet', '18 feet', '10 feet'], 'sub': 'basketball'},
        {'q': 'Which country won the 2022 FIFA World Cup?', 'a': 'Argentina', 'options': ['Argentina', 'France', 'Brazil', 'Croatia'], 'sub': 'soccer'},
        {'q': 'What is the term for three goals in a hockey game by one player?', 'a': 'Hat trick', 'options': ['Hat trick', 'Triple', 'Trifecta', 'Three-peat'], 'sub': 'hockey'},
        {'q': 'Who is the all-time leading scorer in FIFA World Cup history?', 'a': 'Miroslav Klose', 'options': ['Miroslav Klose', 'Ronaldo', 'Pelé', 'Gerd Müller'], 'sub': 'soccer'},
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
        {'q': 'What is the largest country by land area?', 'a': 'Russia', 'options': ['Russia', 'Canada', 'China', 'USA'], 'sub': 'countries'},
        {'q': 'What is the capital of Japan?', 'a': 'Tokyo', 'options': ['Tokyo', 'Kyoto', 'Osaka', 'Yokohama'], 'sub': 'capitals'},
        {'q': 'Which continent has the most countries?', 'a': 'Africa', 'options': ['Africa', 'Europe', 'Asia', 'South America'], 'sub': 'continents'},
        {'q': 'What river flows through Paris?', 'a': 'Seine', 'options': ['Seine', 'Thames', 'Rhine', 'Danube'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Canada?', 'a': 'Ottawa', 'options': ['Ottawa', 'Toronto', 'Vancouver', 'Montreal'], 'sub': 'capitals'},
        {'q': 'What is the tallest mountain in the world?', 'a': 'Mount Everest', 'options': ['Mount Everest', 'K2', 'Kangchenjunga', 'Mont Blanc'], 'sub': 'landmarks'},
        {'q': 'Which country has the most time zones?', 'a': 'France', 'options': ['France', 'Russia', 'USA', 'China'], 'sub': 'countries'},
        {'q': 'What is the capital of Germany?', 'a': 'Berlin', 'options': ['Berlin', 'Munich', 'Hamburg', 'Frankfurt'], 'sub': 'capitals'},
        {'q': 'What is the largest island in the world?', 'a': 'Greenland', 'options': ['Greenland', 'Madagascar', 'Borneo', 'New Guinea'], 'sub': 'maps'},
        {'q': 'Which African country has Cairo as its capital?', 'a': 'Egypt', 'options': ['Egypt', 'Sudan', 'Libya', 'Morocco'], 'sub': 'capitals'},
        {'q': 'What mountain range separates Europe from Asia?', 'a': 'Ural Mountains', 'options': ['Ural Mountains', 'Alps', 'Himalayas', 'Caucasus'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Italy?', 'a': 'Rome', 'options': ['Rome', 'Milan', 'Venice', 'Florence'], 'sub': 'capitals'},
        {'q': 'Which country is home to the Great Barrier Reef?', 'a': 'Australia', 'options': ['Australia', 'Indonesia', 'Philippines', 'Fiji'], 'sub': 'landmarks'},
        {'q': 'What is the driest continent on Earth?', 'a': 'Antarctica', 'options': ['Antarctica', 'Africa', 'Australia', 'Asia'], 'sub': 'continents'},
        {'q': 'What is the capital of Spain?', 'a': 'Madrid', 'options': ['Madrid', 'Barcelona', 'Seville', 'Valencia'], 'sub': 'capitals'},
        {'q': 'Which strait connects the Mediterranean Sea to the Atlantic Ocean?', 'a': 'Strait of Gibraltar', 'options': ['Strait of Gibraltar', 'Strait of Hormuz', 'Bosphorus', 'Suez Canal'], 'sub': 'maps'},
        {'q': 'What country has the longest coastline?', 'a': 'Canada', 'options': ['Canada', 'Australia', 'Russia', 'Indonesia'], 'sub': 'countries'},
        {'q': 'What is the capital of South Korea?', 'a': 'Seoul', 'options': ['Seoul', 'Busan', 'Incheon', 'Pyongyang'], 'sub': 'capitals'},
        {'q': 'On which continent would you find the Amazon River?', 'a': 'South America', 'options': ['South America', 'Africa', 'Asia', 'Australia'], 'sub': 'maps'},
        {'q': 'Which country is completely surrounded by South Africa?', 'a': 'Lesotho', 'options': ['Lesotho', 'Swaziland', 'Botswana', 'Zimbabwe'], 'sub': 'countries'},
        {'q': 'What is the capital of Argentina?', 'a': 'Buenos Aires', 'options': ['Buenos Aires', 'Córdoba', 'Rosario', 'Mendoza'], 'sub': 'capitals'},
        {'q': 'What ocean lies between Africa and Australia?', 'a': 'Indian Ocean', 'options': ['Indian Ocean', 'Pacific Ocean', 'Atlantic Ocean', 'Southern Ocean'], 'sub': 'maps'},
        {'q': 'What is the smallest US state by area?', 'a': 'Rhode Island', 'options': ['Rhode Island', 'Delaware', 'Connecticut', 'New Jersey'], 'sub': 'countries'},
        {'q': 'What is the capital of Egypt?', 'a': 'Cairo', 'options': ['Cairo', 'Alexandria', 'Giza', 'Luxor'], 'sub': 'capitals'},
        {'q': 'Which European country has the most UNESCO World Heritage Sites?', 'a': 'Italy', 'options': ['Italy', 'Spain', 'France', 'Germany'], 'sub': 'countries'},
        {'q': 'What is the longest mountain range in the world?', 'a': 'Andes', 'options': ['Andes', 'Rocky Mountains', 'Himalayas', 'Alps'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Turkey?', 'a': 'Ankara', 'options': ['Ankara', 'Istanbul', 'Izmir', 'Antalya'], 'sub': 'capitals'},
        {'q': 'What sea is bordered by Europe to the north and Africa to the south?', 'a': 'Mediterranean Sea', 'options': ['Mediterranean Sea', 'Red Sea', 'Black Sea', 'Caspian Sea'], 'sub': 'maps'},
        {'q': 'What country has the most islands?', 'a': 'Sweden', 'options': ['Sweden', 'Finland', 'Indonesia', 'Philippines'], 'sub': 'countries'},
        {'q': 'What is the capital of India?', 'a': 'New Delhi', 'options': ['New Delhi', 'Mumbai', 'Kolkata', 'Chennai'], 'sub': 'capitals'},
        {'q': 'What is the deepest ocean trench?', 'a': 'Mariana Trench', 'options': ['Mariana Trench', 'Puerto Rico Trench', 'Java Trench', 'Philippine Trench'], 'sub': 'landmarks'},
        {'q': 'Which two countries share the longest border?', 'a': 'Canada and USA', 'options': ['Canada and USA', 'Russia and China', 'Argentina and Chile', 'India and China'], 'sub': 'countries'},
        {'q': 'What is the capital of Russia?', 'a': 'Moscow', 'options': ['Moscow', 'St. Petersburg', 'Novosibirsk', 'Yekaterinburg'], 'sub': 'capitals'},
        {'q': 'What is the largest desert in the world?', 'a': 'Antarctic Desert', 'options': ['Antarctic Desert', 'Sahara', 'Arabian', 'Gobi'], 'sub': 'landmarks'},
        {'q': 'Which country is known as the "Land of Fire and Ice"?', 'a': 'Iceland', 'options': ['Iceland', 'Norway', 'Greenland', 'Finland'], 'sub': 'countries'},
        {'q': 'What is the capital of China?', 'a': 'Beijing', 'options': ['Beijing', 'Shanghai', 'Hong Kong', 'Guangzhou'], 'sub': 'capitals'},
        {'q': 'What river runs through London?', 'a': 'Thames', 'options': ['Thames', 'Seine', 'Danube', 'Rhine'], 'sub': 'landmarks'},
        {'q': 'How many continents are there?', 'a': '7', 'options': ['7', '6', '5', '8'], 'sub': 'continents'},
        {'q': 'What is the capital of Mexico?', 'a': 'Mexico City', 'options': ['Mexico City', 'Guadalajara', 'Cancún', 'Monterrey'], 'sub': 'capitals'},
        {'q': 'Which country has the most active volcanoes?', 'a': 'Indonesia', 'options': ['Indonesia', 'Japan', 'USA', 'Philippines'], 'sub': 'countries'},
    ]
}

# Hard mode questions - more challenging for experienced players
HARD_QUESTIONS = {
    'news': [
        {'q': 'Which country withdrew from the International Criminal Court in 2023 citing bias?', 'a': 'Russia', 'options': ['Russia', 'China', 'Israel', 'Turkey'], 'sub': 'world_affairs'},
        {'q': 'What percentage of global GDP does the G7 represent approximately?', 'a': '45%', 'options': ['45%', '30%', '60%', '75%'], 'sub': 'world_affairs'},
        {'q': 'Which tech company faced a landmark antitrust ruling in 2024 over app store practices?', 'a': 'Apple', 'options': ['Apple', 'Google', 'Amazon', 'Meta'], 'sub': 'current_events'},
        {'q': 'What was the inflation rate peak in the US during 2022?', 'a': '9.1%', 'options': ['9.1%', '7.5%', '11.2%', '6.8%'], 'sub': 'current_events'},
        {'q': 'Which African nation joined BRICS in 2024?', 'a': 'Ethiopia', 'options': ['Ethiopia', 'Nigeria', 'Kenya', 'Ghana'], 'sub': 'world_affairs'},
        {'q': 'Who became the first female president of the European Central Bank?', 'a': 'Christine Lagarde', 'options': ['Christine Lagarde', 'Janet Yellen', 'Ursula von der Leyen', 'Kristalina Georgieva'], 'sub': 'politics'},
        {'q': 'What cryptocurrency exchange collapsed in November 2022?', 'a': 'FTX', 'options': ['FTX', 'Celsius', 'BlockFi', 'Voyager'], 'sub': 'current_events'},
        {'q': 'Which country has the highest nominal GDP per capita as of 2024?', 'a': 'Luxembourg', 'options': ['Luxembourg', 'Switzerland', 'Norway', 'Singapore'], 'sub': 'world_affairs'},
        {'q': 'What is the name of the US legislation that allocated $280B for semiconductor manufacturing?', 'a': 'CHIPS Act', 'options': ['CHIPS Act', 'Build Back Better', 'Infrastructure Act', 'Tech America Act'], 'sub': 'politics'},
        {'q': 'Which social media platform reached 100 million users fastest in history?', 'a': 'Threads', 'options': ['Threads', 'ChatGPT', 'TikTok', 'Instagram'], 'sub': 'current_events'},
        {'q': 'What is the name of the EU\'s comprehensive AI regulation passed in 2024?', 'a': 'AI Act', 'options': ['AI Act', 'Digital Services Act', 'GDPR 2.0', 'Tech Regulation Act'], 'sub': 'politics'},
        {'q': 'Which country\'s currency lost over 80% of its value in 2023?', 'a': 'Argentina', 'options': ['Argentina', 'Turkey', 'Venezuela', 'Lebanon'], 'sub': 'world_affairs'},
        {'q': 'What was the name of the cargo ship that collapsed the Francis Scott Key Bridge?', 'a': 'Dali', 'options': ['Dali', 'Ever Given', 'Ever Forward', 'Maersk Alabama'], 'sub': 'current_events'},
        {'q': 'Which country became NATO\'s 31st member in 2023?', 'a': 'Finland', 'options': ['Finland', 'Sweden', 'Ukraine', 'Georgia'], 'sub': 'world_affairs'},
        {'q': 'What is the Federal Reserve\'s target inflation rate?', 'a': '2%', 'options': ['2%', '3%', '1%', '4%'], 'sub': 'current_events'},
        {'q': 'Who is the CEO of OpenAI as of 2024?', 'a': 'Sam Altman', 'options': ['Sam Altman', 'Elon Musk', 'Satya Nadella', 'Dario Amodei'], 'sub': 'current_events'},
        {'q': 'What percentage of the world\'s population uses the internet?', 'a': '~65%', 'options': ['~65%', '~45%', '~80%', '~90%'], 'sub': 'current_events'},
        {'q': 'Which country has the world\'s largest sovereign wealth fund?', 'a': 'Norway', 'options': ['Norway', 'UAE', 'Saudi Arabia', 'China'], 'sub': 'world_affairs'},
        {'q': 'What is the name of China\'s Belt and Road Initiative\'s main financing bank?', 'a': 'AIIB', 'options': ['AIIB', 'World Bank', 'IMF', 'ADB'], 'sub': 'world_affairs'},
        {'q': 'What was the largest corporate bankruptcy in US history by assets?', 'a': 'Lehman Brothers', 'options': ['Lehman Brothers', 'Enron', 'WorldCom', 'Washington Mutual'], 'sub': 'current_events'},
        {'q': 'What is the unemployment rate threshold the Fed considers "full employment"?', 'a': '4-5%', 'options': ['4-5%', '2-3%', '6-7%', '0-1%'], 'sub': 'current_events'},
        {'q': 'Which former Soviet state experienced a military coup attempt in 2023?', 'a': 'Russia', 'options': ['Russia', 'Belarus', 'Kazakhstan', 'Armenia'], 'sub': 'world_affairs'},
        {'q': 'What is the name of the leader of Wagner Group who led that coup attempt?', 'a': 'Yevgeny Prigozhin', 'options': ['Yevgeny Prigozhin', 'Sergei Shoigu', 'Ramzan Kadyrov', 'Alexander Lukashenko'], 'sub': 'world_affairs'},
        {'q': 'Which tech company laid off the highest percentage of workers in 2023?', 'a': 'Meta', 'options': ['Meta', 'Google', 'Amazon', 'Microsoft'], 'sub': 'current_events'},
        {'q': 'What is the current US national debt approximately?', 'a': '$34 trillion', 'options': ['$34 trillion', '$20 trillion', '$50 trillion', '$15 trillion'], 'sub': 'politics'},
        {'q': 'Which Middle Eastern country normalized relations with Israel in 2020 via the Abraham Accords?', 'a': 'UAE', 'options': ['UAE', 'Saudi Arabia', 'Qatar', 'Kuwait'], 'sub': 'world_affairs'},
        {'q': 'What was the name of the SVB executive who sold stock before the bank\'s collapse?', 'a': 'Greg Becker', 'options': ['Greg Becker', 'Jamie Dimon', 'Lloyd Blankfein', 'Brian Moynihan'], 'sub': 'current_events'},
        {'q': 'Which European country elected its first far-right government since WWII in 2022?', 'a': 'Italy', 'options': ['Italy', 'France', 'Germany', 'Spain'], 'sub': 'politics'},
        {'q': 'What is the name of the Chinese spy balloon shot down over the US in 2023?', 'a': 'No official name given', 'options': ['No official name given', 'Dragon Eye', 'Sky Watch', 'Wind Rider'], 'sub': 'current_events'},
        {'q': 'Which central bank was first to cut interest rates in 2024 among major economies?', 'a': 'Swiss National Bank', 'options': ['Swiss National Bank', 'Federal Reserve', 'ECB', 'Bank of England'], 'sub': 'world_affairs'},
        {'q': 'What percentage of global CO2 emissions does China produce?', 'a': '~30%', 'options': ['~30%', '~15%', '~45%', '~50%'], 'sub': 'world_affairs'},
        {'q': 'Which streaming service had the most subscribers globally in 2024?', 'a': 'Netflix', 'options': ['Netflix', 'Amazon Prime', 'Disney+', 'YouTube Premium'], 'sub': 'current_events'},
        {'q': 'What was the name of the Russian opposition leader who died in prison in 2024?', 'a': 'Alexei Navalny', 'options': ['Alexei Navalny', 'Boris Nemtsov', 'Mikhail Khodorkovsky', 'Gary Kasparov'], 'sub': 'world_affairs'},
        {'q': 'Which country produces the most lithium globally?', 'a': 'Australia', 'options': ['Australia', 'Chile', 'China', 'Argentina'], 'sub': 'world_affairs'},
        {'q': 'What is the name of Apple\'s mixed reality headset?', 'a': 'Vision Pro', 'options': ['Vision Pro', 'Apple Glass', 'iVision', 'Reality One'], 'sub': 'current_events'},
        {'q': 'Which country has the fastest 5G speeds on average?', 'a': 'South Korea', 'options': ['South Korea', 'USA', 'China', 'Japan'], 'sub': 'current_events'},
        {'q': 'What percentage of US electricity comes from renewable sources?', 'a': '~22%', 'options': ['~22%', '~10%', '~35%', '~50%'], 'sub': 'current_events'},
        {'q': 'Which billionaire lost the most wealth in 2022?', 'a': 'Elon Musk', 'options': ['Elon Musk', 'Mark Zuckerberg', 'Jeff Bezos', 'Bernard Arnault'], 'sub': 'current_events'},
        {'q': 'What is the name of the EU\'s digital markets regulation targeting big tech?', 'a': 'Digital Markets Act', 'options': ['Digital Markets Act', 'Tech Antitrust Act', 'Platform Regulation', 'Digital Services Act'], 'sub': 'politics'},
        {'q': 'Which Asian country had the highest GDP growth in 2023?', 'a': 'India', 'options': ['India', 'China', 'Vietnam', 'Indonesia'], 'sub': 'world_affairs'},
        {'q': 'What is the current population of Earth approximately?', 'a': '8 billion', 'options': ['8 billion', '7 billion', '9 billion', '6 billion'], 'sub': 'world_affairs'},
        {'q': 'Which country is building the largest offshore wind farm?', 'a': 'United Kingdom', 'options': ['United Kingdom', 'Denmark', 'Germany', 'China'], 'sub': 'current_events'},
        {'q': 'What percentage of global oil production does OPEC control?', 'a': '~40%', 'options': ['~40%', '~60%', '~25%', '~80%'], 'sub': 'world_affairs'},
        {'q': 'Which tech company\'s stock rose the most in 2023?', 'a': 'Nvidia', 'options': ['Nvidia', 'Apple', 'Microsoft', 'Tesla'], 'sub': 'current_events'},
        {'q': 'What is the name of the largest AI language model released by Google?', 'a': 'Gemini', 'options': ['Gemini', 'Bard', 'PaLM', 'Lambda'], 'sub': 'current_events'},
        {'q': 'Which European country generates the highest percentage of electricity from nuclear?', 'a': 'France', 'options': ['France', 'Sweden', 'Finland', 'Belgium'], 'sub': 'world_affairs'},
        {'q': 'What was the peak price of Bitcoin in 2021?', 'a': '~$69,000', 'options': ['~$69,000', '~$50,000', '~$100,000', '~$40,000'], 'sub': 'current_events'},
        {'q': 'Which country has the most billionaires per capita?', 'a': 'Monaco', 'options': ['Monaco', 'Switzerland', 'USA', 'Singapore'], 'sub': 'world_affairs'},
        {'q': 'What is the name of Saudi Arabia\'s planned $500B megacity?', 'a': 'NEOM', 'options': ['NEOM', 'The Line', 'Vision City', 'Future Arabia'], 'sub': 'world_affairs'},
    ],
    'history': [
        {'q': 'The Treaty of Westphalia in 1648 established what key concept in international relations?', 'a': 'National sovereignty', 'options': ['National sovereignty', 'Free trade', 'Human rights', 'Colonial boundaries'], 'sub': 'world_history'},
        {'q': 'Which empire was ruled by Suleiman the Magnificent?', 'a': 'Ottoman Empire', 'options': ['Ottoman Empire', 'Mughal Empire', 'Persian Empire', 'Byzantine Empire'], 'sub': 'medieval'},
        {'q': 'The Zimmermann Telegram, which helped bring the US into WWI, proposed an alliance with which country?', 'a': 'Mexico', 'options': ['Mexico', 'Japan', 'Spain', 'Brazil'], 'sub': 'wars'},
        {'q': 'The Magna Carta was signed in which year?', 'a': '1215', 'options': ['1215', '1066', '1348', '1453'], 'sub': 'medieval'},
        {'q': 'Which ancient civilization developed the concept of zero as a number?', 'a': 'Maya', 'options': ['Maya', 'Romans', 'Greeks', 'Egyptians'], 'sub': 'ancient'},
        {'q': 'The Hundred Years\' War was fought primarily between which two countries?', 'a': 'England and France', 'options': ['England and France', 'Spain and Portugal', 'Germany and Italy', 'Austria and Prussia'], 'sub': 'wars'},
        {'q': 'Which US president established the National Park Service?', 'a': 'Woodrow Wilson', 'options': ['Woodrow Wilson', 'Theodore Roosevelt', 'William Taft', 'Calvin Coolidge'], 'sub': 'presidents'},
        {'q': 'The Partition of India in 1947 created which two nations?', 'a': 'India and Pakistan', 'options': ['India and Pakistan', 'India and Bangladesh', 'India and Sri Lanka', 'India and Myanmar'], 'sub': 'modern'},
        {'q': 'What year was the Battle of Hastings?', 'a': '1066', 'options': ['1066', '1215', '1415', '1346'], 'sub': 'medieval'},
        {'q': 'Who was the first Holy Roman Emperor?', 'a': 'Charlemagne', 'options': ['Charlemagne', 'Otto I', 'Frederick I', 'Charles V'], 'sub': 'medieval'},
        {'q': 'The Thirty Years\' War primarily devastated which region?', 'a': 'Central Europe (Germany)', 'options': ['Central Europe (Germany)', 'France', 'England', 'Spain'], 'sub': 'wars'},
        {'q': 'What was the code name for the D-Day invasion?', 'a': 'Operation Overlord', 'options': ['Operation Overlord', 'Operation Torch', 'Operation Market Garden', 'Operation Barbarossa'], 'sub': 'wars'},
        {'q': 'Which US president purchased Louisiana from France?', 'a': 'Thomas Jefferson', 'options': ['Thomas Jefferson', 'James Madison', 'James Monroe', 'John Adams'], 'sub': 'presidents'},
        {'q': 'The Boxer Rebellion occurred in which country?', 'a': 'China', 'options': ['China', 'Japan', 'Korea', 'Philippines'], 'sub': 'world_history'},
        {'q': 'What year did Constantinople fall to the Ottoman Turks?', 'a': '1453', 'options': ['1453', '1389', '1492', '1517'], 'sub': 'medieval'},
        {'q': 'Who was the last Tsar of Russia?', 'a': 'Nicholas II', 'options': ['Nicholas II', 'Alexander III', 'Nicholas I', 'Alexander II'], 'sub': 'modern'},
        {'q': 'The Meiji Restoration occurred in which country?', 'a': 'Japan', 'options': ['Japan', 'China', 'Korea', 'Vietnam'], 'sub': 'world_history'},
        {'q': 'What treaty ended World War I?', 'a': 'Treaty of Versailles', 'options': ['Treaty of Versailles', 'Treaty of Paris', 'Treaty of Ghent', 'Treaty of Westphalia'], 'sub': 'wars'},
        {'q': 'Which pharaoh built the Great Pyramid of Giza?', 'a': 'Khufu', 'options': ['Khufu', 'Tutankhamun', 'Ramesses II', 'Cleopatra'], 'sub': 'ancient'},
        {'q': 'The Opium Wars were fought between China and which country?', 'a': 'Britain', 'options': ['Britain', 'France', 'USA', 'Japan'], 'sub': 'world_history'},
        {'q': 'Who was the first woman to win a Nobel Prize twice?', 'a': 'Marie Curie', 'options': ['Marie Curie', 'Irene Joliot-Curie', 'Dorothy Hodgkin', 'Ada Lovelace'], 'sub': 'modern'},
        {'q': 'What was the name of the US policy to contain Soviet expansion?', 'a': 'Containment', 'options': ['Containment', 'Domino Theory', 'Marshall Plan', 'Truman Doctrine'], 'sub': 'modern'},
        {'q': 'The Peloponnesian War was fought between Athens and which city-state?', 'a': 'Sparta', 'options': ['Sparta', 'Corinth', 'Thebes', 'Macedonia'], 'sub': 'ancient'},
        {'q': 'Which US president signed the Civil Rights Act of 1964?', 'a': 'Lyndon B. Johnson', 'options': ['Lyndon B. Johnson', 'John F. Kennedy', 'Dwight Eisenhower', 'Richard Nixon'], 'sub': 'presidents'},
        {'q': 'The Haitian Revolution was the only successful slave revolt that led to what?', 'a': 'An independent nation', 'options': ['An independent nation', 'A new colony', 'A civil war', 'A territory'], 'sub': 'world_history'},
        {'q': 'Who was the British monarch during the American Revolution?', 'a': 'George III', 'options': ['George III', 'George II', 'George IV', 'William IV'], 'sub': 'world_history'},
        {'q': 'The Khmer Rouge ruled which country?', 'a': 'Cambodia', 'options': ['Cambodia', 'Vietnam', 'Laos', 'Thailand'], 'sub': 'modern'},
        {'q': 'What was the name of the ship that brought the first enslaved Africans to English North America?', 'a': 'White Lion', 'options': ['White Lion', 'Mayflower', 'San Juan Bautista', 'Amistad'], 'sub': 'world_history'},
        {'q': 'The War of the Roses was a civil war in which country?', 'a': 'England', 'options': ['England', 'France', 'Spain', 'Germany'], 'sub': 'medieval'},
        {'q': 'Who was the first US president to be assassinated?', 'a': 'Abraham Lincoln', 'options': ['Abraham Lincoln', 'James Garfield', 'William McKinley', 'John F. Kennedy'], 'sub': 'presidents'},
        {'q': 'The Suez Crisis of 1956 involved which three countries attacking Egypt?', 'a': 'Britain, France, Israel', 'options': ['Britain, France, Israel', 'USA, Britain, France', 'USSR, Egypt, Syria', 'Britain, USA, Israel'], 'sub': 'modern'},
        {'q': 'What ancient wonder was located in Babylon?', 'a': 'Hanging Gardens', 'options': ['Hanging Gardens', 'Lighthouse', 'Colossus', 'Mausoleum'], 'sub': 'ancient'},
        {'q': 'The Scramble for Africa occurred primarily in which century?', 'a': '19th century', 'options': ['19th century', '18th century', '20th century', '17th century'], 'sub': 'world_history'},
        {'q': 'Who was the youngest US president at inauguration?', 'a': 'Theodore Roosevelt', 'options': ['Theodore Roosevelt', 'John F. Kennedy', 'Bill Clinton', 'Barack Obama'], 'sub': 'presidents'},
        {'q': 'The Treaty of Tordesillas divided the New World between which two countries?', 'a': 'Spain and Portugal', 'options': ['Spain and Portugal', 'England and France', 'Spain and England', 'Portugal and Netherlands'], 'sub': 'world_history'},
        {'q': 'What was the primary religion of the Byzantine Empire?', 'a': 'Eastern Orthodox Christianity', 'options': ['Eastern Orthodox Christianity', 'Roman Catholicism', 'Islam', 'Judaism'], 'sub': 'medieval'},
        {'q': 'The Long March was a military retreat by which group?', 'a': 'Chinese Communist Party', 'options': ['Chinese Communist Party', 'Kuomintang', 'Japanese Army', 'Viet Cong'], 'sub': 'modern'},
        {'q': 'Who was the US president during the War of 1812?', 'a': 'James Madison', 'options': ['James Madison', 'Thomas Jefferson', 'James Monroe', 'John Adams'], 'sub': 'presidents'},
        {'q': 'The Reconquista was the Christian reconquest of which peninsula?', 'a': 'Iberian Peninsula', 'options': ['Iberian Peninsula', 'Italian Peninsula', 'Balkan Peninsula', 'Scandinavian Peninsula'], 'sub': 'medieval'},
        {'q': 'What year did the United States enter World War I?', 'a': '1917', 'options': ['1917', '1914', '1915', '1916'], 'sub': 'wars'},
        {'q': 'The Sepoy Mutiny of 1857 occurred in which country?', 'a': 'India', 'options': ['India', 'China', 'Egypt', 'South Africa'], 'sub': 'world_history'},
        {'q': 'Who founded the Mongol Empire?', 'a': 'Genghis Khan', 'options': ['Genghis Khan', 'Kublai Khan', 'Tamerlane', 'Attila'], 'sub': 'medieval'},
        {'q': 'The Bay of Pigs invasion was an attempt to overthrow which leader?', 'a': 'Fidel Castro', 'options': ['Fidel Castro', 'Che Guevara', 'Hugo Chavez', 'Daniel Ortega'], 'sub': 'modern'},
        {'q': 'What was the name of the first permanent English settlement in America?', 'a': 'Jamestown', 'options': ['Jamestown', 'Plymouth', 'Roanoke', 'Boston'], 'sub': 'world_history'},
        {'q': 'The Russo-Japanese War ended with what treaty?', 'a': 'Treaty of Portsmouth', 'options': ['Treaty of Portsmouth', 'Treaty of Shimonoseki', 'Treaty of Kanagawa', 'Treaty of Versailles'], 'sub': 'wars'},
        {'q': 'Who was the first US president to resign from office?', 'a': 'Richard Nixon', 'options': ['Richard Nixon', 'Andrew Johnson', 'Bill Clinton', 'Donald Trump'], 'sub': 'presidents'},
        {'q': 'The Dreyfus Affair was a political scandal in which country?', 'a': 'France', 'options': ['France', 'Germany', 'Britain', 'Russia'], 'sub': 'modern'},
        {'q': 'What was the primary cause of the Taiping Rebellion?', 'a': 'Religious and political reform', 'options': ['Religious and political reform', 'Foreign invasion', 'Famine', 'Tax revolt'], 'sub': 'world_history'},
        {'q': 'The Nuremberg Trials prosecuted leaders of which regime?', 'a': 'Nazi Germany', 'options': ['Nazi Germany', 'Imperial Japan', 'Fascist Italy', 'Soviet Union'], 'sub': 'wars'},
    ],
    'science': [
        {'q': 'What is the half-life of Carbon-14, used in radiocarbon dating?', 'a': '5,730 years', 'options': ['5,730 years', '1,200 years', '12,000 years', '50,000 years'], 'sub': 'chemistry'},
        {'q': 'Which planet has the strongest magnetic field in our solar system?', 'a': 'Jupiter', 'options': ['Jupiter', 'Earth', 'Saturn', 'Neptune'], 'sub': 'space'},
        {'q': 'What is the name of the process by which cells divide to produce gametes?', 'a': 'Meiosis', 'options': ['Meiosis', 'Mitosis', 'Binary fission', 'Cytokinesis'], 'sub': 'biology'},
        {'q': 'What is the Chandrasekhar limit approximately equal to?', 'a': '1.4 solar masses', 'options': ['1.4 solar masses', '3.0 solar masses', '0.5 solar masses', '10 solar masses'], 'sub': 'space'},
        {'q': 'Which element has the highest electronegativity?', 'a': 'Fluorine', 'options': ['Fluorine', 'Oxygen', 'Chlorine', 'Nitrogen'], 'sub': 'chemistry'},
        {'q': 'What type of bond holds the two strands of DNA together?', 'a': 'Hydrogen bonds', 'options': ['Hydrogen bonds', 'Covalent bonds', 'Ionic bonds', 'Metallic bonds'], 'sub': 'biology'},
        {'q': 'What is the term for the bending of light as it passes through different media?', 'a': 'Refraction', 'options': ['Refraction', 'Reflection', 'Diffraction', 'Dispersion'], 'sub': 'physics'},
        {'q': 'Which layer of Earth\'s atmosphere contains the ozone layer?', 'a': 'Stratosphere', 'options': ['Stratosphere', 'Troposphere', 'Mesosphere', 'Thermosphere'], 'sub': 'earth_science'},
        {'q': 'What particle is exchanged in the strong nuclear force?', 'a': 'Gluon', 'options': ['Gluon', 'Photon', 'W boson', 'Graviton'], 'sub': 'physics'},
        {'q': 'What is the approximate age of the Earth?', 'a': '4.5 billion years', 'options': ['4.5 billion years', '6,000 years', '1 billion years', '10 billion years'], 'sub': 'earth_science'},
        {'q': 'What is the Heisenberg Uncertainty Principle about?', 'a': 'Position and momentum measurement limits', 'options': ['Position and momentum measurement limits', 'Speed of light', 'Atomic decay', 'Wave-particle duality'], 'sub': 'physics'},
        {'q': 'Which organelle is responsible for protein synthesis?', 'a': 'Ribosome', 'options': ['Ribosome', 'Mitochondria', 'Golgi apparatus', 'Lysosome'], 'sub': 'biology'},
        {'q': 'What is the Schwarzschild radius related to?', 'a': 'Black holes', 'options': ['Black holes', 'Neutron stars', 'White dwarfs', 'Pulsars'], 'sub': 'space'},
        {'q': 'What is the most abundant protein in the human body?', 'a': 'Collagen', 'options': ['Collagen', 'Hemoglobin', 'Keratin', 'Actin'], 'sub': 'biology'},
        {'q': 'What is Avogadro\'s number approximately?', 'a': '6.02 x 10^23', 'options': ['6.02 x 10^23', '3.14 x 10^23', '9.8 x 10^23', '1.6 x 10^23'], 'sub': 'chemistry'},
        {'q': 'Which planet has the Great Red Spot?', 'a': 'Jupiter', 'options': ['Jupiter', 'Saturn', 'Neptune', 'Mars'], 'sub': 'space'},
        {'q': 'What is the process called when a solid turns directly into a gas?', 'a': 'Sublimation', 'options': ['Sublimation', 'Evaporation', 'Condensation', 'Deposition'], 'sub': 'chemistry'},
        {'q': 'What type of wave is sound?', 'a': 'Longitudinal', 'options': ['Longitudinal', 'Transverse', 'Electromagnetic', 'Surface'], 'sub': 'physics'},
        {'q': 'What is the main component of natural gas?', 'a': 'Methane', 'options': ['Methane', 'Propane', 'Butane', 'Ethane'], 'sub': 'chemistry'},
        {'q': 'Which blood type is the universal recipient?', 'a': 'AB positive', 'options': ['AB positive', 'O negative', 'A positive', 'B negative'], 'sub': 'biology'},
        {'q': 'What is the escape velocity from Earth?', 'a': '11.2 km/s', 'options': ['11.2 km/s', '7.9 km/s', '15.0 km/s', '25.0 km/s'], 'sub': 'space'},
        {'q': 'What is the name of the effect where light changes wavelength due to motion?', 'a': 'Doppler effect', 'options': ['Doppler effect', 'Photoelectric effect', 'Compton effect', 'Zeeman effect'], 'sub': 'physics'},
        {'q': 'Which element has the atomic number 79?', 'a': 'Gold', 'options': ['Gold', 'Silver', 'Platinum', 'Mercury'], 'sub': 'chemistry'},
        {'q': 'What causes the Northern and Southern Lights?', 'a': 'Solar wind particles', 'options': ['Solar wind particles', 'Moonlight reflection', 'Volcanic gases', 'Ocean currents'], 'sub': 'earth_science'},
        {'q': 'What is the name of the closest star to our solar system?', 'a': 'Proxima Centauri', 'options': ['Proxima Centauri', 'Alpha Centauri A', 'Sirius', 'Barnard\'s Star'], 'sub': 'space'},
        {'q': 'What is the SI unit of electrical resistance?', 'a': 'Ohm', 'options': ['Ohm', 'Volt', 'Ampere', 'Watt'], 'sub': 'physics'},
        {'q': 'Which vitamin is synthesized by gut bacteria?', 'a': 'Vitamin K', 'options': ['Vitamin K', 'Vitamin C', 'Vitamin A', 'Vitamin E'], 'sub': 'biology'},
        {'q': 'What is the most reactive group of elements?', 'a': 'Alkali metals', 'options': ['Alkali metals', 'Halogens', 'Noble gases', 'Transition metals'], 'sub': 'chemistry'},
        {'q': 'What type of rock is marble?', 'a': 'Metamorphic', 'options': ['Metamorphic', 'Igneous', 'Sedimentary', 'Volcanic'], 'sub': 'earth_science'},
        {'q': 'What is the name of the boundary between Earth\'s crust and mantle?', 'a': 'Mohorovičić discontinuity', 'options': ['Mohorovičić discontinuity', 'Gutenberg discontinuity', 'Lehmann discontinuity', 'Conrad discontinuity'], 'sub': 'earth_science'},
        {'q': 'Which particle has no electric charge?', 'a': 'Neutron', 'options': ['Neutron', 'Proton', 'Electron', 'Positron'], 'sub': 'physics'},
        {'q': 'What is the name of the sugar found in DNA?', 'a': 'Deoxyribose', 'options': ['Deoxyribose', 'Ribose', 'Glucose', 'Fructose'], 'sub': 'biology'},
        {'q': 'What phenomenon explains why the sky is blue?', 'a': 'Rayleigh scattering', 'options': ['Rayleigh scattering', 'Mie scattering', 'Raman scattering', 'Tyndall effect'], 'sub': 'physics'},
        {'q': 'What is the critical temperature of water?', 'a': '374°C', 'options': ['374°C', '100°C', '212°C', '500°C'], 'sub': 'chemistry'},
        {'q': 'Which moon of Saturn has a thick atmosphere?', 'a': 'Titan', 'options': ['Titan', 'Enceladus', 'Mimas', 'Rhea'], 'sub': 'space'},
        {'q': 'What is the name of the process by which plants lose water through leaves?', 'a': 'Transpiration', 'options': ['Transpiration', 'Evaporation', 'Respiration', 'Perspiration'], 'sub': 'biology'},
        {'q': 'What is Planck\'s constant used to calculate?', 'a': 'Energy of photons', 'options': ['Energy of photons', 'Mass of electrons', 'Speed of light', 'Gravitational force'], 'sub': 'physics'},
        {'q': 'Which element is the best conductor of electricity?', 'a': 'Silver', 'options': ['Silver', 'Copper', 'Gold', 'Aluminum'], 'sub': 'chemistry'},
        {'q': 'What is the name of the supercontinent that existed 335 million years ago?', 'a': 'Pangaea', 'options': ['Pangaea', 'Gondwana', 'Laurasia', 'Rodinia'], 'sub': 'earth_science'},
        {'q': 'What is the function of telomerase?', 'a': 'Extends telomeres during cell division', 'options': ['Extends telomeres during cell division', 'Repairs DNA damage', 'Synthesizes proteins', 'Transports RNA'], 'sub': 'biology'},
        {'q': 'What is the name of the effect where electrons are emitted from a surface when light hits it?', 'a': 'Photoelectric effect', 'options': ['Photoelectric effect', 'Compton effect', 'Doppler effect', 'Hall effect'], 'sub': 'physics'},
        {'q': 'Which noble gas is used in neon signs?', 'a': 'Neon', 'options': ['Neon', 'Argon', 'Helium', 'Krypton'], 'sub': 'chemistry'},
        {'q': 'What is the name of the Mars rover that landed in 2021?', 'a': 'Perseverance', 'options': ['Perseverance', 'Curiosity', 'Opportunity', 'Spirit'], 'sub': 'space'},
        {'q': 'What is the name of the enzyme that unzips DNA?', 'a': 'Helicase', 'options': ['Helicase', 'Polymerase', 'Ligase', 'Primase'], 'sub': 'biology'},
        {'q': 'What is the term for a material that does not conduct electricity?', 'a': 'Insulator', 'options': ['Insulator', 'Conductor', 'Semiconductor', 'Superconductor'], 'sub': 'physics'},
        {'q': 'What is the name of the boundary where tectonic plates move apart?', 'a': 'Divergent boundary', 'options': ['Divergent boundary', 'Convergent boundary', 'Transform boundary', 'Subduction zone'], 'sub': 'earth_science'},
        {'q': 'Which planet rotates backwards compared to most others?', 'a': 'Venus', 'options': ['Venus', 'Mercury', 'Uranus', 'Neptune'], 'sub': 'space'},
        {'q': 'What is the name of the smallest unit of an element?', 'a': 'Atom', 'options': ['Atom', 'Molecule', 'Ion', 'Electron'], 'sub': 'chemistry'},
        {'q': 'What percentage of the human brain is water?', 'a': '~75%', 'options': ['~75%', '~50%', '~90%', '~60%'], 'sub': 'biology'},
    ],
    'entertainment': [
        {'q': 'Which film holds the record for most Academy Award wins?', 'a': 'Ben-Hur, Titanic, and LOTR: ROTK', 'options': ['Ben-Hur, Titanic, and LOTR: ROTK', 'Gone with the Wind', 'West Side Story', 'The Godfather'], 'sub': 'movies'},
        {'q': 'Who composed the opera "The Marriage of Figaro"?', 'a': 'Mozart', 'options': ['Mozart', 'Beethoven', 'Verdi', 'Wagner'], 'sub': 'music'},
        {'q': 'Which TV series has won the most Emmy Awards overall?', 'a': 'Saturday Night Live', 'options': ['Saturday Night Live', 'Game of Thrones', 'The Simpsons', 'Frasier'], 'sub': 'tv'},
        {'q': 'Who wrote "One Hundred Years of Solitude"?', 'a': 'Gabriel García Márquez', 'options': ['Gabriel García Márquez', 'Jorge Luis Borges', 'Pablo Neruda', 'Isabel Allende'], 'sub': 'literature'},
        {'q': 'What band has sold the most albums worldwide?', 'a': 'The Beatles', 'options': ['The Beatles', 'Led Zeppelin', 'Pink Floyd', 'Eagles'], 'sub': 'music'},
        {'q': 'Which director has the most Best Director Oscar nominations?', 'a': 'Martin Scorsese', 'options': ['Martin Scorsese', 'Steven Spielberg', 'William Wyler', 'John Ford'], 'sub': 'movies'},
        {'q': 'What was the first music video played on MTV?', 'a': 'Video Killed the Radio Star', 'options': ['Video Killed the Radio Star', 'Thriller', 'Take On Me', 'Sweet Dreams'], 'sub': 'music'},
        {'q': 'Which author has sold the most books of all time?', 'a': 'Agatha Christie', 'options': ['Agatha Christie', 'William Shakespeare', 'J.K. Rowling', 'Stephen King'], 'sub': 'literature'},
        {'q': 'What streaming service produced "The Crown"?', 'a': 'Netflix', 'options': ['Netflix', 'Amazon Prime', 'HBO Max', 'Apple TV+'], 'sub': 'tv'},
        {'q': 'Which album spent the most weeks at #1 on the Billboard 200?', 'a': 'Thriller', 'options': ['Thriller', '21', 'The Bodyguard Soundtrack', 'Purple Rain'], 'sub': 'music'},
        {'q': 'Who directed "2001: A Space Odyssey"?', 'a': 'Stanley Kubrick', 'options': ['Stanley Kubrick', 'Steven Spielberg', 'Ridley Scott', 'George Lucas'], 'sub': 'movies'},
        {'q': 'Which composer wrote "The Four Seasons"?', 'a': 'Vivaldi', 'options': ['Vivaldi', 'Bach', 'Mozart', 'Handel'], 'sub': 'music'},
        {'q': 'What TV show has the most watched series finale?', 'a': 'M*A*S*H', 'options': ['M*A*S*H', 'Cheers', 'Seinfeld', 'Friends'], 'sub': 'tv'},
        {'q': 'Who wrote "War and Peace"?', 'a': 'Leo Tolstoy', 'options': ['Leo Tolstoy', 'Fyodor Dostoevsky', 'Anton Chekhov', 'Ivan Turgenev'], 'sub': 'literature'},
        {'q': 'Which film won the first Academy Award for Best Animated Feature?', 'a': 'Shrek', 'options': ['Shrek', 'Monsters, Inc.', 'Toy Story', 'Finding Nemo'], 'sub': 'movies'},
        {'q': 'Who painted "Starry Night"?', 'a': 'Vincent van Gogh', 'options': ['Vincent van Gogh', 'Claude Monet', 'Pablo Picasso', 'Salvador Dalí'], 'sub': 'arts'},
        {'q': 'Which band performed the longest concert in history?', 'a': 'The Flaming Lips', 'options': ['The Flaming Lips', 'Phish', 'Grateful Dead', 'Bruce Springsteen'], 'sub': 'music'},
        {'q': 'Who created the TV series "The Twilight Zone"?', 'a': 'Rod Serling', 'options': ['Rod Serling', 'Steven Spielberg', 'Alfred Hitchcock', 'Gene Roddenberry'], 'sub': 'tv'},
        {'q': 'Which novel begins with "Call me Ishmael"?', 'a': 'Moby-Dick', 'options': ['Moby-Dick', 'The Old Man and the Sea', 'Treasure Island', 'Robinson Crusoe'], 'sub': 'literature'},
        {'q': 'What was Marilyn Monroe\'s birth name?', 'a': 'Norma Jeane Mortenson', 'options': ['Norma Jeane Mortenson', 'Mary Jane Baker', 'Patricia Anne Smith', 'Betty Jean Davis'], 'sub': 'movies'},
        {'q': 'Which symphony is known as Beethoven\'s "Choral"?', 'a': 'Symphony No. 9', 'options': ['Symphony No. 9', 'Symphony No. 5', 'Symphony No. 6', 'Symphony No. 3'], 'sub': 'music'},
        {'q': 'What TV show holds the record for most expensive episode?', 'a': 'The Rings of Power', 'options': ['The Rings of Power', 'Game of Thrones', 'The Crown', 'Stranger Things'], 'sub': 'tv'},
        {'q': 'Who wrote "The Canterbury Tales"?', 'a': 'Geoffrey Chaucer', 'options': ['Geoffrey Chaucer', 'William Shakespeare', 'John Milton', 'Edmund Spenser'], 'sub': 'literature'},
        {'q': 'Which film has the highest box office gross of all time (unadjusted)?', 'a': 'Avatar', 'options': ['Avatar', 'Avengers: Endgame', 'Titanic', 'Star Wars: The Force Awakens'], 'sub': 'movies'},
        {'q': 'What instrument did Miles Davis play?', 'a': 'Trumpet', 'options': ['Trumpet', 'Saxophone', 'Piano', 'Bass'], 'sub': 'music'},
        {'q': 'Which show won the first Emmy for Outstanding Drama Series?', 'a': 'The U.S. Steel Hour', 'options': ['The U.S. Steel Hour', 'I Love Lucy', 'Playhouse 90', 'Studio One'], 'sub': 'tv'},
        {'q': 'Who wrote "Don Quixote"?', 'a': 'Miguel de Cervantes', 'options': ['Miguel de Cervantes', 'Gabriel García Márquez', 'Jorge Luis Borges', 'Pablo Neruda'], 'sub': 'literature'},
        {'q': 'Which actor has won the most Academy Awards?', 'a': 'Katharine Hepburn', 'options': ['Katharine Hepburn', 'Meryl Streep', 'Jack Nicholson', 'Daniel Day-Lewis'], 'sub': 'movies'},
        {'q': 'Who composed the music for "Star Wars"?', 'a': 'John Williams', 'options': ['John Williams', 'Hans Zimmer', 'Jerry Goldsmith', 'James Horner'], 'sub': 'music'},
        {'q': 'What was the first TV show to air a same-sex wedding?', 'a': 'Roseanne', 'options': ['Roseanne', 'Friends', 'Will & Grace', 'Ellen'], 'sub': 'tv'},
        {'q': 'Who wrote "Ulysses"?', 'a': 'James Joyce', 'options': ['James Joyce', 'Samuel Beckett', 'Oscar Wilde', 'W.B. Yeats'], 'sub': 'literature'},
        {'q': 'Which Pixar film was the first to be rated PG?', 'a': 'The Incredibles', 'options': ['The Incredibles', 'Up', 'Brave', 'Ratatouille'], 'sub': 'movies'},
        {'q': 'What is considered the first rock and roll song?', 'a': 'Rocket 88', 'options': ['Rocket 88', 'Rock Around the Clock', 'Johnny B. Goode', 'Tutti Frutti'], 'sub': 'music'},
        {'q': 'Which TV drama has the highest IMDB rating?', 'a': 'Breaking Bad', 'options': ['Breaking Bad', 'The Wire', 'The Sopranos', 'Game of Thrones'], 'sub': 'tv'},
        {'q': 'Who wrote "Crime and Punishment"?', 'a': 'Fyodor Dostoevsky', 'options': ['Fyodor Dostoevsky', 'Leo Tolstoy', 'Anton Chekhov', 'Nikolai Gogol'], 'sub': 'literature'},
        {'q': 'Which movie had the longest continuous shot (11 minutes)?', 'a': 'Touch of Evil', 'options': ['Touch of Evil', 'Birdman', '1917', 'Children of Men'], 'sub': 'movies'},
        {'q': 'Who was the first musician to have a diamond-certified album?', 'a': 'Michael Jackson', 'options': ['Michael Jackson', 'The Beatles', 'Elvis Presley', 'Eagles'], 'sub': 'music'},
        {'q': 'What was HBO\'s first original drama series?', 'a': 'Oz', 'options': ['Oz', 'The Sopranos', 'Six Feet Under', 'The Wire'], 'sub': 'tv'},
        {'q': 'Who wrote "Frankenstein"?', 'a': 'Mary Shelley', 'options': ['Mary Shelley', 'Bram Stoker', 'Edgar Allan Poe', 'H.G. Wells'], 'sub': 'literature'},
        {'q': 'Which director has made the most films?', 'a': 'Takashi Miike', 'options': ['Takashi Miike', 'Steven Spielberg', 'Woody Allen', 'Clint Eastwood'], 'sub': 'movies'},
        {'q': 'What symphony orchestra is the oldest in the United States?', 'a': 'New York Philharmonic', 'options': ['New York Philharmonic', 'Boston Symphony', 'Chicago Symphony', 'Philadelphia Orchestra'], 'sub': 'music'},
        {'q': 'Which TV show introduced the "bottle episode" concept?', 'a': 'Star Trek', 'options': ['Star Trek', 'The Twilight Zone', 'M*A*S*H', 'Cheers'], 'sub': 'tv'},
        {'q': 'Who wrote "The Divine Comedy"?', 'a': 'Dante Alighieri', 'options': ['Dante Alighieri', 'Giovanni Boccaccio', 'Petrarch', 'Virgil'], 'sub': 'literature'},
        {'q': 'Which silent film star was known as "The Little Tramp"?', 'a': 'Charlie Chaplin', 'options': ['Charlie Chaplin', 'Buster Keaton', 'Harold Lloyd', 'Fatty Arbuckle'], 'sub': 'movies'},
        {'q': 'What was the first album to be certified platinum?', 'a': 'Eagles - Their Greatest Hits', 'options': ['Eagles - Their Greatest Hits', 'Fleetwood Mac - Rumours', 'Boston - Boston', 'Led Zeppelin IV'], 'sub': 'music'},
        {'q': 'Which TV network aired the first regularly scheduled news broadcast?', 'a': 'CBS', 'options': ['CBS', 'NBC', 'ABC', 'DuMont'], 'sub': 'tv'},
        {'q': 'Who wrote "The Odyssey"?', 'a': 'Homer', 'options': ['Homer', 'Sophocles', 'Euripides', 'Virgil'], 'sub': 'literature'},
        {'q': 'What was the first feature film made entirely with CGI?', 'a': 'Toy Story', 'options': ['Toy Story', 'Shrek', 'A Bug\'s Life', 'Antz'], 'sub': 'movies'},
        {'q': 'Which female artist has won the most Grammy Awards?', 'a': 'Beyoncé', 'options': ['Beyoncé', 'Alison Krauss', 'Adele', 'Taylor Swift'], 'sub': 'music'},
    ],
    'sports': [
        {'q': 'Which country has won the most FIFA World Cup titles in women\'s football?', 'a': 'United States', 'options': ['United States', 'Germany', 'Brazil', 'Japan'], 'sub': 'soccer'},
        {'q': 'Who was the first African American head coach to win a Super Bowl?', 'a': 'Tony Dungy', 'options': ['Tony Dungy', 'Mike Tomlin', 'Lovie Smith', 'Herm Edwards'], 'sub': 'football'},
        {'q': 'Which boxer retired undefeated with a 50-0 record?', 'a': 'Floyd Mayweather Jr.', 'options': ['Floyd Mayweather Jr.', 'Rocky Marciano', 'Muhammad Ali', 'Mike Tyson'], 'sub': 'misc'},
        {'q': 'What year did the "Miracle on Ice" occur at the Winter Olympics?', 'a': '1980', 'options': ['1980', '1984', '1976', '1972'], 'sub': 'olympics'},
        {'q': 'Who holds the record for most goals in a single Premier League season?', 'a': 'Erling Haaland', 'options': ['Erling Haaland', 'Mohamed Salah', 'Alan Shearer', 'Cristiano Ronaldo'], 'sub': 'soccer'},
        {'q': 'What is the only country to have competed in every Summer Olympic Games?', 'a': 'Greece', 'options': ['Greece', 'United States', 'Great Britain', 'France'], 'sub': 'olympics'},
        {'q': 'Who was the youngest player to score in a FIFA World Cup final?', 'a': 'Pelé', 'options': ['Pelé', 'Kylian Mbappé', 'Michael Owen', 'Diego Maradona'], 'sub': 'soccer'},
        {'q': 'Which NBA player has the most career triple-doubles?', 'a': 'Russell Westbrook', 'options': ['Russell Westbrook', 'Oscar Robertson', 'Magic Johnson', 'LeBron James'], 'sub': 'basketball'},
        {'q': 'What is the only major sports league to have had a team relocate to a different country?', 'a': 'MLB', 'options': ['MLB', 'NBA', 'NFL', 'NHL'], 'sub': 'misc'},
        {'q': 'Who holds the record for most career grand slams in MLB?', 'a': 'Lou Gehrig', 'options': ['Lou Gehrig', 'Alex Rodriguez', 'Manny Ramirez', 'Eddie Murray'], 'sub': 'baseball'},
        {'q': 'Which golfer has the most career PGA Tour wins?', 'a': 'Sam Snead', 'options': ['Sam Snead', 'Tiger Woods', 'Jack Nicklaus', 'Arnold Palmer'], 'sub': 'golf'},
        {'q': 'What is the longest winning streak in NBA history?', 'a': '33 games', 'options': ['33 games', '27 games', '24 games', '28 games'], 'sub': 'basketball'},
        {'q': 'Who was the first African American to win a Grand Slam title?', 'a': 'Althea Gibson', 'options': ['Althea Gibson', 'Arthur Ashe', 'Serena Williams', 'Venus Williams'], 'sub': 'tennis'},
        {'q': 'Which country has won the most Rugby World Cups?', 'a': 'South Africa/New Zealand', 'options': ['South Africa/New Zealand', 'Australia', 'England', 'France'], 'sub': 'misc'},
        {'q': 'What is the fastest recorded tennis serve?', 'a': '163.7 mph', 'options': ['163.7 mph', '155.0 mph', '170.0 mph', '145.0 mph'], 'sub': 'tennis'},
        {'q': 'Who has scored the most goals in a single calendar year?', 'a': 'Lionel Messi', 'options': ['Lionel Messi', 'Cristiano Ronaldo', 'Gerd Müller', 'Pelé'], 'sub': 'soccer'},
        {'q': 'Which NHL team has won the most Stanley Cups?', 'a': 'Montreal Canadiens', 'options': ['Montreal Canadiens', 'Toronto Maple Leafs', 'Detroit Red Wings', 'Boston Bruins'], 'sub': 'hockey'},
        {'q': 'What was the "Rumble in the Jungle"?', 'a': 'Ali vs Foreman boxing match', 'options': ['Ali vs Foreman boxing match', 'Ali vs Frazier', 'Tyson vs Holyfield', 'Foreman vs Frazier'], 'sub': 'misc'},
        {'q': 'Who holds the record for most consecutive games played in MLB?', 'a': 'Cal Ripken Jr.', 'options': ['Cal Ripken Jr.', 'Lou Gehrig', 'Pete Rose', 'Ty Cobb'], 'sub': 'baseball'},
        {'q': 'Which country invented the sport of golf?', 'a': 'Scotland', 'options': ['Scotland', 'England', 'Netherlands', 'France'], 'sub': 'golf'},
        {'q': 'What is the longest touchdown in NFL history?', 'a': '109 yards', 'options': ['109 yards', '108 yards', '107 yards', '105 yards'], 'sub': 'football'},
        {'q': 'Who was the first player to be drafted #1 overall straight from high school in NBA?', 'a': 'Kwame Brown', 'options': ['Kwame Brown', 'LeBron James', 'Kobe Bryant', 'Kevin Garnett'], 'sub': 'basketball'},
        {'q': 'Which cyclist won the most Tour de France titles before being stripped?', 'a': 'Lance Armstrong', 'options': ['Lance Armstrong', 'Miguel Indurain', 'Bernard Hinault', 'Eddy Merckx'], 'sub': 'misc'},
        {'q': 'What is the diameter of a golf hole in inches?', 'a': '4.25 inches', 'options': ['4.25 inches', '4.5 inches', '4.0 inches', '3.75 inches'], 'sub': 'golf'},
        {'q': 'Who was the first quarterback to throw for 5,000 yards in an NFL season?', 'a': 'Dan Marino', 'options': ['Dan Marino', 'Drew Brees', 'Peyton Manning', 'Tom Brady'], 'sub': 'football'},
        {'q': 'Which swimmer has the most individual Olympic gold medals?', 'a': 'Michael Phelps', 'options': ['Michael Phelps', 'Mark Spitz', 'Ryan Lochte', 'Ian Thorpe'], 'sub': 'olympics'},
        {'q': 'What is the weight of an official NBA basketball?', 'a': '22 ounces', 'options': ['22 ounces', '20 ounces', '24 ounces', '18 ounces'], 'sub': 'basketball'},
        {'q': 'Who has the most career assists in NHL history?', 'a': 'Wayne Gretzky', 'options': ['Wayne Gretzky', 'Ron Francis', 'Mark Messier', 'Ray Bourque'], 'sub': 'hockey'},
        {'q': 'What is the name of the annual soccer match between Real Madrid and Barcelona?', 'a': 'El Clásico', 'options': ['El Clásico', 'The Derby', 'La Final', 'El Grande'], 'sub': 'soccer'},
        {'q': 'What is the oldest tennis tournament in the world?', 'a': 'Wimbledon', 'options': ['Wimbledon', 'US Open', 'French Open', 'Australian Open'], 'sub': 'tennis'},
        {'q': 'Who holds the record for most home runs in a single MLB season?', 'a': 'Barry Bonds', 'options': ['Barry Bonds', 'Mark McGwire', 'Sammy Sosa', 'Roger Maris'], 'sub': 'baseball'},
        {'q': 'Which Formula 1 driver has the most World Championships?', 'a': 'Michael Schumacher/Lewis Hamilton', 'options': ['Michael Schumacher/Lewis Hamilton', 'Juan Manuel Fangio', 'Alain Prost', 'Sebastian Vettel'], 'sub': 'misc'},
        {'q': 'What is the length of an Olympic swimming pool in meters?', 'a': '50 meters', 'options': ['50 meters', '100 meters', '25 meters', '75 meters'], 'sub': 'olympics'},
        {'q': 'Who was the first player to score 100 points in an NBA game?', 'a': 'Wilt Chamberlain', 'options': ['Wilt Chamberlain', 'Michael Jordan', 'Kobe Bryant', 'LeBron James'], 'sub': 'basketball'},
        {'q': 'Which horse won the Triple Crown most recently before Justify?', 'a': 'American Pharoah', 'options': ['American Pharoah', 'Secretariat', 'Seattle Slew', 'Affirmed'], 'sub': 'misc'},
        {'q': 'Who holds the record for most goals in a single NHL season?', 'a': 'Wayne Gretzky', 'options': ['Wayne Gretzky', 'Brett Hull', 'Mario Lemieux', 'Alexander Mogilny'], 'sub': 'hockey'},
        {'q': 'Who holds the women\'s 100m world record?', 'a': 'Florence Griffith-Joyner', 'options': ['Florence Griffith-Joyner', 'Shelly-Ann Fraser-Pryce', 'Elaine Thompson', 'Marion Jones'], 'sub': 'olympics'},
        {'q': 'Which NFL team went undefeated in the regular season and won Super Bowl?', 'a': '1972 Miami Dolphins', 'options': ['1972 Miami Dolphins', '2007 New England Patriots', '1985 Chicago Bears', '1998 Denver Broncos'], 'sub': 'football'},
        {'q': 'What is the highest possible break in snooker?', 'a': '147', 'options': ['147', '155', '180', '200'], 'sub': 'misc'},
        {'q': 'Who has won the most Ballon d\'Or awards?', 'a': 'Lionel Messi', 'options': ['Lionel Messi', 'Cristiano Ronaldo', 'Michel Platini', 'Johan Cruyff'], 'sub': 'soccer'},
        {'q': 'What is the marathon world record (men\'s)?', 'a': '2:00:35', 'options': ['2:00:35', '2:01:09', '2:02:57', '2:03:23'], 'sub': 'misc'},
        {'q': 'Which pitcher has the most career strikeouts in MLB?', 'a': 'Nolan Ryan', 'options': ['Nolan Ryan', 'Randy Johnson', 'Roger Clemens', 'Steve Carlton'], 'sub': 'baseball'},
        {'q': 'Who was the youngest world heavyweight boxing champion?', 'a': 'Mike Tyson', 'options': ['Mike Tyson', 'Muhammad Ali', 'Floyd Patterson', 'Leon Spinks'], 'sub': 'misc'},
        {'q': 'What is the oldest trophy in international sports?', 'a': "America's Cup", 'options': ["America's Cup", 'Wimbledon', 'Stanley Cup', 'Ryder Cup'], 'sub': 'misc'},
        {'q': 'Who holds the record for most career rebounds in NBA history?', 'a': 'Wilt Chamberlain', 'options': ['Wilt Chamberlain', 'Bill Russell', 'Kareem Abdul-Jabbar', 'Karl Malone'], 'sub': 'basketball'},
        {'q': 'Which tennis player has won the most Grand Slam singles titles (women)?', 'a': 'Margaret Court', 'options': ['Margaret Court', 'Serena Williams', 'Steffi Graf', 'Chris Evert'], 'sub': 'tennis'},
        {'q': 'What is the highest score ever recorded in an NBA game by one team?', 'a': '186 points', 'options': ['186 points', '173 points', '162 points', '150 points'], 'sub': 'basketball'},
        {'q': 'Who was the first woman to run a sub-4 minute mile?', 'a': 'No woman has', 'options': ['No woman has', 'Sifan Hassan', 'Faith Kipyegon', 'Svetlana Masterkova'], 'sub': 'olympics'},
    ],
    'geography': [
        {'q': 'What is the deepest point in the world\'s oceans?', 'a': 'Challenger Deep', 'options': ['Challenger Deep', 'Puerto Rico Trench', 'Java Trench', 'Philippine Trench'], 'sub': 'landmarks'},
        {'q': 'Which African country has the largest economy by GDP?', 'a': 'Nigeria', 'options': ['Nigeria', 'South Africa', 'Egypt', 'Kenya'], 'sub': 'countries'},
        {'q': 'What is the only country that borders both France and Portugal?', 'a': 'Spain', 'options': ['Spain', 'Andorra', 'Morocco', 'Belgium'], 'sub': 'countries'},
        {'q': 'Lake Baikal, the world\'s deepest lake, is located in which country?', 'a': 'Russia', 'options': ['Russia', 'Kazakhstan', 'Mongolia', 'China'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Myanmar?', 'a': 'Naypyidaw', 'options': ['Naypyidaw', 'Yangon', 'Mandalay', 'Bagan'], 'sub': 'capitals'},
        {'q': 'What channel separates England from France?', 'a': 'English Channel', 'options': ['English Channel', 'Strait of Dover', 'Irish Sea', 'North Sea'], 'sub': 'maps'},
        {'q': 'How many time zones does Russia span?', 'a': '11', 'options': ['11', '9', '7', '13'], 'sub': 'countries'},
        {'q': 'What is the smallest country in mainland Africa by area?', 'a': 'Gambia', 'options': ['Gambia', 'Eswatini', 'Lesotho', 'Djibouti'], 'sub': 'countries'},
        {'q': 'Which desert is the largest hot desert in the world?', 'a': 'Sahara', 'options': ['Sahara', 'Arabian', 'Gobi', 'Kalahari'], 'sub': 'landmarks'},
        {'q': 'What is the highest waterfall in the world by total height?', 'a': 'Angel Falls', 'options': ['Angel Falls', 'Niagara Falls', 'Victoria Falls', 'Iguazu Falls'], 'sub': 'landmarks'},
        {'q': 'Which European country has the longest coastline?', 'a': 'Norway', 'options': ['Norway', 'Greece', 'Italy', 'United Kingdom'], 'sub': 'countries'},
        {'q': 'What is the largest landlocked country by area?', 'a': 'Kazakhstan', 'options': ['Kazakhstan', 'Mongolia', 'Chad', 'Niger'], 'sub': 'countries'},
        {'q': 'Which river forms part of the border between the US and Mexico?', 'a': 'Rio Grande', 'options': ['Rio Grande', 'Colorado River', 'Pecos River', 'Gila River'], 'sub': 'maps'},
        {'q': 'What is the capital of Kazakhstan?', 'a': 'Astana', 'options': ['Astana', 'Almaty', 'Shymkent', 'Karaganda'], 'sub': 'capitals'},
        {'q': 'Which country has the most languages spoken within its borders?', 'a': 'Papua New Guinea', 'options': ['Papua New Guinea', 'Indonesia', 'Nigeria', 'India'], 'sub': 'countries'},
        {'q': 'What is the driest desert in the world?', 'a': 'Atacama Desert', 'options': ['Atacama Desert', 'Sahara Desert', 'Gobi Desert', 'Namib Desert'], 'sub': 'landmarks'},
        {'q': 'Which sea is the saltiest in the world?', 'a': 'Dead Sea', 'options': ['Dead Sea', 'Red Sea', 'Mediterranean Sea', 'Black Sea'], 'sub': 'maps'},
        {'q': 'What is the capital of Sri Lanka?', 'a': 'Sri Jayawardenepura Kotte', 'options': ['Sri Jayawardenepura Kotte', 'Colombo', 'Kandy', 'Galle'], 'sub': 'capitals'},
        {'q': 'Which European country is divided into 26 cantons?', 'a': 'Switzerland', 'options': ['Switzerland', 'Austria', 'Belgium', 'Netherlands'], 'sub': 'countries'},
        {'q': 'What percentage of the Netherlands is below sea level?', 'a': '26%', 'options': ['26%', '50%', '10%', '75%'], 'sub': 'countries'},
        {'q': 'Which African country was never colonized?', 'a': 'Ethiopia', 'options': ['Ethiopia', 'Liberia', 'Egypt', 'Morocco'], 'sub': 'countries'},
        {'q': 'What is the largest lake in Africa?', 'a': 'Lake Victoria', 'options': ['Lake Victoria', 'Lake Tanganyika', 'Lake Malawi', 'Lake Chad'], 'sub': 'landmarks'},
        {'q': 'What is the only continent without an active volcano?', 'a': 'Australia', 'options': ['Australia', 'Antarctica', 'Europe', 'Africa'], 'sub': 'countries'},
        {'q': 'What is the capital of Bhutan?', 'a': 'Thimphu', 'options': ['Thimphu', 'Paro', 'Punakha', 'Phuntsholing'], 'sub': 'capitals'},
        {'q': 'Which is the only country through which both the Equator and Tropic of Capricorn pass?', 'a': 'Brazil', 'options': ['Brazil', 'Indonesia', 'Kenya', 'Ecuador'], 'sub': 'maps'},
        {'q': 'What is the smallest country in Asia by area?', 'a': 'Maldives', 'options': ['Maldives', 'Singapore', 'Bahrain', 'Brunei'], 'sub': 'countries'},
        {'q': 'Which mountain range separates France from Spain?', 'a': 'Pyrenees', 'options': ['Pyrenees', 'Alps', 'Carpathians', 'Apennines'], 'sub': 'landmarks'},
        {'q': 'What is the capital of Mongolia?', 'a': 'Ulaanbaatar', 'options': ['Ulaanbaatar', 'Darkhan', 'Erdenet', 'Choibalsan'], 'sub': 'capitals'},
        {'q': 'Which country spans the most time zones?', 'a': 'France', 'options': ['France', 'Russia', 'United States', 'China'], 'sub': 'countries'},
        {'q': 'What is the deepest lake in the United States?', 'a': 'Crater Lake', 'options': ['Crater Lake', 'Lake Tahoe', 'Lake Superior', 'Lake Chelan'], 'sub': 'landmarks'},
        {'q': 'Which European country has the lowest population density?', 'a': 'Iceland', 'options': ['Iceland', 'Norway', 'Finland', 'Sweden'], 'sub': 'countries'},
        {'q': 'What is the capital of Malta?', 'a': 'Valletta', 'options': ['Valletta', 'Mdina', 'Sliema', 'St. Julian\'s'], 'sub': 'capitals'},
        {'q': 'Which country is the world\'s largest producer of coffee?', 'a': 'Brazil', 'options': ['Brazil', 'Colombia', 'Vietnam', 'Ethiopia'], 'sub': 'countries'},
        {'q': 'What is the highest peak in Africa?', 'a': 'Mount Kilimanjaro', 'options': ['Mount Kilimanjaro', 'Mount Kenya', 'Mount Stanley', 'Ras Dashen'], 'sub': 'landmarks'},
        {'q': 'Which country has the most neighbor countries?', 'a': 'China/Russia', 'options': ['China/Russia', 'Brazil', 'Germany', 'France'], 'sub': 'countries'},
        {'q': 'What is the capital of Liechtenstein?', 'a': 'Vaduz', 'options': ['Vaduz', 'Schaan', 'Balzers', 'Triesen'], 'sub': 'capitals'},
        {'q': 'Which strait connects the Black Sea to the Mediterranean?', 'a': 'Bosphorus and Dardanelles', 'options': ['Bosphorus and Dardanelles', 'Strait of Gibraltar', 'Suez Canal', 'Strait of Messina'], 'sub': 'maps'},
        {'q': 'What is the largest island in the Mediterranean Sea?', 'a': 'Sicily', 'options': ['Sicily', 'Sardinia', 'Cyprus', 'Corsica'], 'sub': 'maps'},
        {'q': 'Which country has the highest average elevation?', 'a': 'Bhutan', 'options': ['Bhutan', 'Nepal', 'Switzerland', 'Lesotho'], 'sub': 'countries'},
        {'q': 'What is the capital of Ecuador?', 'a': 'Quito', 'options': ['Quito', 'Guayaquil', 'Cuenca', 'Ambato'], 'sub': 'capitals'},
        {'q': 'Which body of water separates Iran from Arabia?', 'a': 'Persian Gulf', 'options': ['Persian Gulf', 'Red Sea', 'Arabian Sea', 'Gulf of Oman'], 'sub': 'maps'},
        {'q': 'What is the only capital city that borders two countries?', 'a': 'Bratislava', 'options': ['Bratislava', 'Vienna', 'Luxembourg City', 'Bern'], 'sub': 'capitals'},
        {'q': 'What is the largest country in Africa by area?', 'a': 'Algeria', 'options': ['Algeria', 'Democratic Republic of Congo', 'Sudan', 'Libya'], 'sub': 'countries'},
        {'q': 'What is the world\'s largest coral reef system?', 'a': 'Great Barrier Reef', 'options': ['Great Barrier Reef', 'Belize Barrier Reef', 'Red Sea Coral Reef', 'Maldives Coral Reef'], 'sub': 'landmarks'},
        {'q': 'Which European capital is built on 14 islands?', 'a': 'Stockholm', 'options': ['Stockholm', 'Copenhagen', 'Amsterdam', 'Venice'], 'sub': 'capitals'},
        {'q': 'What is the largest country in South America by area?', 'a': 'Brazil', 'options': ['Brazil', 'Argentina', 'Peru', 'Colombia'], 'sub': 'countries'},
        {'q': 'Which river flows through the most countries?', 'a': 'Danube', 'options': ['Danube', 'Nile', 'Rhine', 'Mekong'], 'sub': 'maps'},
        {'q': 'What is the capital of Papua New Guinea?', 'a': 'Port Moresby', 'options': ['Port Moresby', 'Lae', 'Mount Hagen', 'Madang'], 'sub': 'capitals'},
        {'q': 'What sea lies between Japan and the Korean Peninsula?', 'a': 'Sea of Japan', 'options': ['Sea of Japan', 'Yellow Sea', 'South China Sea', 'Philippine Sea'], 'sub': 'maps'},
    ]
}

# Onboarding quiz questions - 50 questions for building user knowledge profile
# Medium difficulty - not too easy, not too hard
ONBOARDING_QUESTIONS = [
    # News/Current Events (8 questions)
    {'q': 'What country most recently joined the European Union?', 'a': 'Croatia', 'options': ['Croatia', 'Romania', 'Bulgaria', 'Montenegro'], 'category': 'news', 'sub': 'world_affairs'},
    {'q': 'What ride-sharing company went public in 2019 in one of the largest tech IPOs?', 'a': 'Uber', 'options': ['Uber', 'Lyft', 'DoorDash', 'Airbnb'], 'category': 'news', 'sub': 'current_events'},
    {'q': 'What social media platform did Mark Zuckerberg rename to "Meta" in 2021?', 'a': 'Facebook', 'options': ['Facebook', 'Instagram', 'WhatsApp', 'Twitter'], 'category': 'news', 'sub': 'current_events'},
    {'q': 'Which country hosted the G20 summit in 2023?', 'a': 'India', 'options': ['India', 'Indonesia', 'Brazil', 'Japan'], 'category': 'news', 'sub': 'world_affairs'},
    {'q': 'Which streaming service released the show "Squid Game"?', 'a': 'Netflix', 'options': ['Netflix', 'Amazon Prime', 'Disney+', 'HBO Max'], 'category': 'news', 'sub': 'current_events'},
    {'q': 'Who became the UK Prime Minister after Boris Johnson?', 'a': 'Liz Truss', 'options': ['Liz Truss', 'Rishi Sunak', 'Keir Starmer', 'Jeremy Hunt'], 'category': 'news', 'sub': 'politics'},
    {'q': 'What electric vehicle company became the most valuable car company in 2020?', 'a': 'Tesla', 'options': ['Tesla', 'Rivian', 'NIO', 'BYD'], 'category': 'news', 'sub': 'current_events'},
    {'q': 'Which company launched the James Webb Space Telescope?', 'a': 'NASA', 'options': ['NASA', 'SpaceX', 'ESA', 'Blue Origin'], 'category': 'news', 'sub': 'current_events'},

    # History (9 questions)
    {'q': 'Who was the first person to reach the South Pole?', 'a': 'Roald Amundsen', 'options': ['Roald Amundsen', 'Robert Scott', 'Ernest Shackleton', 'Richard Byrd'], 'category': 'history', 'sub': 'modern'},
    {'q': 'Who was the first woman to win a Nobel Prize?', 'a': 'Marie Curie', 'options': ['Marie Curie', 'Mother Teresa', 'Jane Addams', 'Irene Joliot-Curie'], 'category': 'history', 'sub': 'modern'},
    {'q': 'What was the longest war in United States history?', 'a': 'War in Afghanistan', 'options': ['War in Afghanistan', 'Vietnam War', 'Civil War', 'War of 1812'], 'category': 'history', 'sub': 'wars'},
    {'q': 'Who was the first president of South Africa after apartheid?', 'a': 'Nelson Mandela', 'options': ['Nelson Mandela', 'Desmond Tutu', 'F.W. de Klerk', 'Thabo Mbeki'], 'category': 'history', 'sub': 'modern'},
    {'q': 'What was the name of the first satellite launched into space?', 'a': 'Sputnik', 'options': ['Sputnik', 'Explorer 1', 'Vostok', 'Gemini'], 'category': 'history', 'sub': 'modern'},
    {'q': 'What medieval code of conduct governed the behavior of knights?', 'a': 'Chivalry', 'options': ['Chivalry', 'Feudalism', 'Vassalage', 'Heraldry'], 'category': 'history', 'sub': 'medieval'},
    {'q': 'What was the codename for the Allied invasion of Normandy in 1944?', 'a': 'D-Day', 'options': ['D-Day', 'Operation Torch', 'Operation Overlord', 'Battle of the Bulge'], 'category': 'history', 'sub': 'wars'},
    {'q': 'Which president delivered the Gettysburg Address?', 'a': 'Abraham Lincoln', 'options': ['Abraham Lincoln', 'George Washington', 'Thomas Jefferson', 'Ulysses S. Grant'], 'category': 'history', 'sub': 'presidents'},
    {'q': 'The Great Fire of London occurred in which century?', 'a': '17th century', 'options': ['17th century', '18th century', '16th century', '19th century'], 'category': 'history', 'sub': 'world_history'},

    # Science (9 questions)
    {'q': 'What is the chemical symbol for sodium?', 'a': 'Na', 'options': ['Na', 'So', 'Sd', 'N'], 'category': 'science', 'sub': 'chemistry'},
    {'q': 'How many chambers does the human heart have?', 'a': '4', 'options': ['4', '2', '3', '6'], 'category': 'science', 'sub': 'biology'},
    {'q': 'Light travels fastest through which medium?', 'a': 'Vacuum', 'options': ['Vacuum', 'Air', 'Water', 'Glass'], 'category': 'science', 'sub': 'physics'},
    {'q': 'What gas do humans exhale that plants need for photosynthesis?', 'a': 'Carbon dioxide', 'options': ['Carbon dioxide', 'Oxygen', 'Nitrogen', 'Hydrogen'], 'category': 'science', 'sub': 'biology'},
    {'q': 'What process do plants use to convert sunlight into energy?', 'a': 'Photosynthesis', 'options': ['Photosynthesis', 'Respiration', 'Fermentation', 'Osmosis'], 'category': 'science', 'sub': 'biology'},
    {'q': 'What is the hottest planet in our solar system?', 'a': 'Venus', 'options': ['Venus', 'Mercury', 'Mars', 'Jupiter'], 'category': 'science', 'sub': 'astronomy'},
    {'q': 'What unit is used to measure electrical current?', 'a': 'Ampere', 'options': ['Ampere', 'Volt', 'Watt', 'Ohm'], 'category': 'science', 'sub': 'physics'},
    {'q': 'DNA stands for what?', 'a': 'Deoxyribonucleic acid', 'options': ['Deoxyribonucleic acid', 'Dinitrogen acid', 'Dual nucleic acid', 'Dynamic nucleic acid'], 'category': 'science', 'sub': 'biology'},
    {'q': 'What type of animal is a whale?', 'a': 'Mammal', 'options': ['Mammal', 'Fish', 'Reptile', 'Amphibian'], 'category': 'science', 'sub': 'biology'},

    # Entertainment (8 questions)
    {'q': 'Who directed the movie "Inception"?', 'a': 'Christopher Nolan', 'options': ['Christopher Nolan', 'Steven Spielberg', 'Martin Scorsese', 'Denis Villeneuve'], 'category': 'entertainment', 'sub': 'movies'},
    {'q': 'Which band released the album "Abbey Road"?', 'a': 'The Beatles', 'options': ['The Beatles', 'The Rolling Stones', 'Led Zeppelin', 'Pink Floyd'], 'category': 'entertainment', 'sub': 'music'},
    {'q': 'What fictional country is Black Panther from?', 'a': 'Wakanda', 'options': ['Wakanda', 'Zamunda', 'Latveria', 'Genosha'], 'category': 'entertainment', 'sub': 'movies'},
    {'q': 'Who played the Joker in "The Dark Knight"?', 'a': 'Heath Ledger', 'options': ['Heath Ledger', 'Joaquin Phoenix', 'Jared Leto', 'Jack Nicholson'], 'category': 'entertainment', 'sub': 'movies'},
    {'q': 'What animated TV show has been on air since 1989 featuring a yellow-skinned family?', 'a': 'The Simpsons', 'options': ['The Simpsons', 'Family Guy', 'South Park', 'Bob\'s Burgers'], 'category': 'entertainment', 'sub': 'tv'},
    {'q': 'Who wrote "The Lord of the Rings" trilogy?', 'a': 'J.R.R. Tolkien', 'options': ['J.R.R. Tolkien', 'C.S. Lewis', 'George R.R. Martin', 'Terry Pratchett'], 'category': 'entertainment', 'sub': 'literature'},
    {'q': 'Who painted the Mona Lisa?', 'a': 'Leonardo da Vinci', 'options': ['Leonardo da Vinci', 'Michelangelo', 'Raphael', 'Pablo Picasso'], 'category': 'entertainment', 'sub': 'arts'},
    {'q': 'What video game franchise features a character named Master Chief?', 'a': 'Halo', 'options': ['Halo', 'Call of Duty', 'Gears of War', 'Destiny'], 'category': 'entertainment', 'sub': 'games'},

    # Sports (8 questions)
    {'q': 'What is the standard height of a basketball hoop?', 'a': '10 feet', 'options': ['10 feet', '8 feet', '12 feet', '9 feet'], 'category': 'sports', 'sub': 'basketball'},
    {'q': 'What color card results in a player being ejected from a soccer match?', 'a': 'Red', 'options': ['Red', 'Yellow', 'Blue', 'Black'], 'category': 'sports', 'sub': 'soccer'},
    {'q': 'In tennis, what is a score of zero called?', 'a': 'Love', 'options': ['Love', 'Nil', 'Zero', 'Duck'], 'category': 'sports', 'sub': 'tennis'},
    {'q': 'What sport is played at Wimbledon?', 'a': 'Tennis', 'options': ['Tennis', 'Golf', 'Cricket', 'Rugby'], 'category': 'sports', 'sub': 'tennis'},
    {'q': 'In which sport did Michael Jordan become famous?', 'a': 'Basketball', 'options': ['Basketball', 'Baseball', 'Football', 'Golf'], 'category': 'sports', 'sub': 'basketball'},
    {'q': 'What is the national sport of Japan?', 'a': 'Sumo wrestling', 'options': ['Sumo wrestling', 'Judo', 'Karate', 'Baseball'], 'category': 'sports', 'sub': 'misc'},
    {'q': 'How many innings are in a standard baseball game?', 'a': '9', 'options': ['9', '7', '6', '12'], 'category': 'sports', 'sub': 'baseball'},
    {'q': 'How many quarters are in an American football game?', 'a': '4', 'options': ['4', '2', '3', '6'], 'category': 'sports', 'sub': 'football'},

    # Geography (8 questions)
    {'q': 'What is the official language of Brazil?', 'a': 'Portuguese', 'options': ['Portuguese', 'Spanish', 'English', 'French'], 'category': 'geography', 'sub': 'countries'},
    {'q': 'What is the tallest building in the world as of 2024?', 'a': 'Burj Khalifa', 'options': ['Burj Khalifa', 'Shanghai Tower', 'One World Trade Center', 'Taipei 101'], 'category': 'geography', 'sub': 'landmarks'},
    {'q': 'In which country would you find the city of Mumbai?', 'a': 'India', 'options': ['India', 'Pakistan', 'Bangladesh', 'Nepal'], 'category': 'geography', 'sub': 'countries'},
    {'q': 'Which mountain is the tallest in North America?', 'a': 'Denali', 'options': ['Denali', 'Mount Whitney', 'Mount Rainier', 'Mount Logan'], 'category': 'geography', 'sub': 'landmarks'},
    {'q': 'What is the most populous country in Africa?', 'a': 'Nigeria', 'options': ['Nigeria', 'Ethiopia', 'Egypt', 'South Africa'], 'category': 'geography', 'sub': 'countries'},
    {'q': 'What waterfall on the border of Zambia and Zimbabwe is one of the largest in the world?', 'a': 'Victoria Falls', 'options': ['Victoria Falls', 'Niagara Falls', 'Iguazu Falls', 'Angel Falls'], 'category': 'geography', 'sub': 'landmarks'},
    {'q': 'What currency is used in Japan?', 'a': 'Yen', 'options': ['Yen', 'Yuan', 'Won', 'Ringgit'], 'category': 'geography', 'sub': 'countries'},
    {'q': 'What European country is shaped like a boot?', 'a': 'Italy', 'options': ['Italy', 'Greece', 'Spain', 'Portugal'], 'category': 'geography', 'sub': 'countries'},
]


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email=None, google_id=None, profile_picture=None):
        self.id = id
        self.username = username
        self.email = email
        self.google_id = google_id
        self.profile_picture = profile_picture


def get_placeholder():
    """Return the correct placeholder for the current database."""
    return '%s' if USE_POSTGRES else '?'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT * FROM users WHERE id = {ph}', (user_id,))
    user_row = cur.fetchone()
    conn.close()

    if user_row:
        return User(
            id=user_row['id'],
            username=user_row['username'],
            email=user_row.get('email') if hasattr(user_row, 'get') else user_row['email'],
            google_id=user_row.get('google_id') if hasattr(user_row, 'get') else user_row['google_id'],
            profile_picture=user_row.get('profile_picture') if hasattr(user_row, 'get') else user_row['profile_picture']
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
                email TEXT,
                google_id TEXT UNIQUE,
                anonymous_id TEXT UNIQUE,
                profile_picture TEXT,
                difficulty TEXT DEFAULT 'easy',
                onboarding_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add columns if they don't exist (for existing databases)
        for col_sql in [
            'ALTER TABLE users ADD COLUMN anonymous_id TEXT UNIQUE',
            'ALTER TABLE users ADD COLUMN difficulty TEXT DEFAULT \'easy\'',
            'ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0'
        ]:
            try:
                cur.execute(col_sql)
                conn.commit()
            except Exception:
                conn.rollback()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                game_date TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                user_answer TEXT,
                correct INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                difficulty TEXT DEFAULT 'easy',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add difficulty column to game_results if it doesn't exist
        try:
            cur.execute("ALTER TABLE game_results ADD COLUMN difficulty TEXT DEFAULT 'easy'")
            conn.commit()
        except Exception:
            conn.rollback()

        # Change game_date from DATE to TEXT to support onboarding prefix
        try:
            cur.execute("ALTER TABLE game_results ALTER COLUMN game_date TYPE TEXT")
            conn.commit()
        except Exception:
            conn.rollback()

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

        cur.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id SERIAL PRIMARY KEY,
                inviter_id INTEGER NOT NULL REFERENCES users(id),
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS dismissed_recommendations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                dismissed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite schema
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                google_id TEXT UNIQUE,
                anonymous_id TEXT UNIQUE,
                profile_picture TEXT,
                difficulty TEXT DEFAULT 'easy',
                onboarding_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_date TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                question TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                user_answer TEXT,
                correct INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                difficulty TEXT DEFAULT 'easy',
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

        cur.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inviter_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (inviter_id) REFERENCES users(id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS dismissed_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                dismissed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # SQLite migrations for existing databases
        for col_sql in [
            'ALTER TABLE game_results ADD COLUMN difficulty TEXT DEFAULT \'easy\''
        ]:
            try:
                cur.execute(col_sql)
                conn.commit()
            except Exception:
                pass  # Column already exists

    # Create visits table for analytics
    if USE_POSTGRES:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id SERIAL PRIMARY KEY,
                path TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                user_id INTEGER REFERENCES users(id),
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                user_id INTEGER,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

    # Create indexes for better query performance
    # These speed up the most common queries significantly
    index_statements = [
        'CREATE INDEX IF NOT EXISTS idx_results_user_date ON game_results(user_id, game_date)',
        'CREATE INDEX IF NOT EXISTS idx_results_question ON game_results(question)',
        'CREATE INDEX IF NOT EXISTS idx_results_category ON game_results(category)',
        'CREATE INDEX IF NOT EXISTS idx_results_game_date ON game_results(game_date)',
        'CREATE INDEX IF NOT EXISTS idx_daily_questions_date_user ON daily_questions(game_date, user_id)',
        'CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester_id)',
        'CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee_id)',
        'CREATE INDEX IF NOT EXISTS idx_visits_path ON visits(path)',
        'CREATE INDEX IF NOT EXISTS idx_visits_visited_at ON visits(visited_at)',
    ]

    for stmt in index_statements:
        try:
            cur.execute(stmt)
        except Exception as e:
            print(f"Index creation note: {e}")

    conn.commit()
    conn.close()


def get_or_create_user_by_google(google_id, email, name, picture):
    """Get or create user from Google OAuth data."""
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Check if user exists by google_id
    cur.execute(f'SELECT * FROM users WHERE google_id = {ph}', (google_id,))
    user = cur.fetchone()

    if user:
        # Update profile picture if changed, and fix full name to first name only
        current_username = dict(user).get('username', '')
        # If username contains a space, it's likely a full name - update to first name only
        if ' ' in current_username:
            cur.execute(f'UPDATE users SET profile_picture = {ph}, username = {ph} WHERE google_id = {ph}',
                       (picture, name, google_id))
        else:
            cur.execute(f'UPDATE users SET profile_picture = {ph} WHERE google_id = {ph}', (picture, google_id))
        conn.commit()
        # Re-fetch to get updated data
        cur.execute(f'SELECT * FROM users WHERE google_id = {ph}', (google_id,))
        user = cur.fetchone()
    else:
        # Check if email already exists (user previously created without OAuth)
        cur.execute(f'SELECT * FROM users WHERE email = {ph}', (email,))
        existing = cur.fetchone()

        if existing:
            # Link Google account to existing user
            cur.execute(f'UPDATE users SET google_id = {ph}, profile_picture = {ph} WHERE email = {ph}',
                       (google_id, picture, email))
            conn.commit()
            cur.execute(f'SELECT * FROM users WHERE email = {ph}', (email,))
            user = cur.fetchone()
        else:
            # Create new user
            cur.execute(f'''
                INSERT INTO users (username, email, google_id, profile_picture)
                VALUES ({ph}, {ph}, {ph}, {ph})
            ''', (name, email, google_id, picture))
            conn.commit()
            cur.execute(f'SELECT * FROM users WHERE google_id = {ph}', (google_id,))
            user = cur.fetchone()

    conn.close()
    return dict(user)


def get_user_difficulty(user_id):
    """Get user's difficulty setting."""
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT difficulty FROM users WHERE id = {ph}', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result['difficulty'] if result and result['difficulty'] else 'easy'


def get_recently_used_questions(difficulty, days=None):
    """Get all previously used questions to avoid repeats across ALL modes.
    If days is None, checks all history. Otherwise limits to N days."""
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Query questions from daily_questions table
    # We look for any user's cached questions since they're the same for all users at same difficulty
    if days is not None:
        today = get_user_today()
        recent_dates = [(today - timedelta(days=i)).isoformat() for i in range(0, days + 1)]
        placeholders = ','.join([ph] * len(recent_dates))
        cur.execute(f'''
            SELECT DISTINCT questions_json FROM daily_questions
            WHERE game_date IN ({placeholders})
        ''', tuple(recent_dates))
    else:
        cur.execute('SELECT DISTINCT questions_json FROM daily_questions')

    results = cur.fetchall()
    conn.close()

    # Extract question texts from the JSON - track ALL difficulties to prevent cross-mode duplicates
    used_questions = set()
    for row in results:
        try:
            questions = json.loads(row['questions_json'])
            for q in questions:
                used_questions.add(q.get('q'))
        except:
            pass

    return used_questions


def get_daily_questions_for_user(user_id):
    """Get today's questions - same for all users at same difficulty (like Wordle/Connections)."""
    today = get_user_today().isoformat()
    difficulty = get_user_difficulty(user_id)

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    # Check if user already has today's questions cached FOR THIS DIFFICULTY
    cur.execute(f'SELECT questions_json FROM daily_questions WHERE game_date = {placeholder} AND user_id = {placeholder}', (today, user_id))
    result = cur.fetchone()

    if result:
        cached_questions = json.loads(result['questions_json'])
        # Only use cache if it matches the current difficulty
        if cached_questions and cached_questions[0].get('difficulty') == difficulty:
            conn.close()
            return cached_questions
        # Otherwise, delete the old cache and generate new questions
        cur.execute(f'DELETE FROM daily_questions WHERE game_date = {placeholder} AND user_id = {placeholder}', (today, user_id))
        conn.commit()

    # Check if ANY user has today's questions for this difficulty (global cache)
    # This ensures all users at same difficulty get the same questions
    cur.execute(f'''
        SELECT questions_json FROM daily_questions
        WHERE game_date = {placeholder}
        LIMIT 10
    ''', (today,))
    existing_today = cur.fetchall()

    for row in existing_today:
        try:
            cached_questions = json.loads(row['questions_json'])
            # Check if this cache is for the same difficulty
            if cached_questions and cached_questions[0].get('difficulty') == difficulty:
                # Use the same questions as other users at this difficulty
                cur.execute(
                    f'INSERT INTO daily_questions (game_date, user_id, questions_json) VALUES ({placeholder}, {placeholder}, {placeholder})',
                    (today, user_id, json.dumps(cached_questions))
                )
                conn.commit()
                conn.close()
                return cached_questions
        except:
            pass

    # Get recently used questions to avoid repeats
    recently_used = get_recently_used_questions(difficulty)

    # Generate questions using date + difficulty as seed
    # Use an isolated Random instance to avoid thread-safety issues with the global random state
    seed = int(hashlib.md5(f"{today}-{difficulty}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    # Choose question bank based on difficulty
    question_bank = HARD_QUESTIONS if difficulty == 'hard' else QUESTIONS

    questions = []
    for cat_key in ['news', 'history', 'science', 'entertainment', 'sports', 'geography']:
        category_questions = question_bank[cat_key]

        # Filter out recently used questions
        available = [q for q in category_questions if q['q'] not in recently_used]

        # If all questions were recently used, allow repeats from oldest first
        if not available:
            available = category_questions

        # Use seeded random to pick, then fallback if it's still a recent repeat
        rng.shuffle(available)
        q = available[0]
        for candidate in available:
            if candidate['q'] not in recently_used:
                q = candidate
                break

        questions.append({
            'category': cat_key,
            'category_name': CATEGORIES[cat_key]['name'],
            'color': CATEGORIES[cat_key]['color'],
            'difficulty': difficulty,
            **q
        })

    rng.shuffle(questions)

    # Cache for this user
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
        SELECT category, subcategory, correct, time_taken, COALESCE(difficulty, 'easy') as difficulty
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
    # Per-difficulty tracking
    diff_cat_stats = {cat: {'easy_correct': 0, 'easy_total': 0, 'hard_correct': 0, 'hard_total': 0} for cat in CATEGORIES}
    overall_diff = {'easy_correct': 0, 'easy_total': 0, 'hard_correct': 0, 'hard_total': 0}

    for r in results:
        cat = r['category']
        sub = r['subcategory']
        correct = r['correct']
        difficulty = r['difficulty'] if r['difficulty'] in ('easy', 'hard') else 'easy'

        cat_stats[cat]['total'] += 1
        cat_stats[cat]['correct'] += correct

        # Track per-difficulty
        if difficulty == 'hard':
            diff_cat_stats[cat]['hard_total'] += 1
            diff_cat_stats[cat]['hard_correct'] += correct
            overall_diff['hard_total'] += 1
            overall_diff['hard_correct'] += correct
        else:
            diff_cat_stats[cat]['easy_total'] += 1
            diff_cat_stats[cat]['easy_correct'] += correct
            overall_diff['easy_total'] += 1
            overall_diff['easy_correct'] += correct

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
        # Merge difficulty stats into category stats
        ds = diff_cat_stats[cat]
        cat_stats[cat]['easy_correct'] = ds['easy_correct']
        cat_stats[cat]['easy_total'] = ds['easy_total']
        cat_stats[cat]['easy_percentage'] = round(ds['easy_correct'] / ds['easy_total'] * 100) if ds['easy_total'] > 0 else 0
        cat_stats[cat]['hard_correct'] = ds['hard_correct']
        cat_stats[cat]['hard_total'] = ds['hard_total']
        cat_stats[cat]['hard_percentage'] = round(ds['hard_correct'] / ds['hard_total'] * 100) if ds['hard_total'] > 0 else 0

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

    overall_easy_pct = round(overall_diff['easy_correct'] / overall_diff['easy_total'] * 100) if overall_diff['easy_total'] > 0 else 0
    overall_hard_pct = round(overall_diff['hard_correct'] / overall_diff['hard_total'] * 100) if overall_diff['hard_total'] > 0 else 0

    return {
        'total_games': total_questions // 6,
        'total_questions': total_questions,
        'categories': cat_stats,
        'subcategories': sub_stats,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'overall_percentage': overall,
        'overall_easy_percentage': overall_easy_pct,
        'overall_easy_total': overall_diff['easy_total'],
        'overall_hard_percentage': overall_hard_pct,
        'overall_hard_total': overall_diff['hard_total']
    }


def generate_player_summary(stats, dismissed_titles=None):
    """Generate a personalized player summary with analysis and recommendations."""
    if stats['total_questions'] < 6:
        return None  # Not enough data

    if dismissed_titles is None:
        dismissed_titles = set()

    total_questions = stats['total_questions']
    overall = stats['overall_percentage']
    categories = stats['categories']
    weaknesses = stats['weaknesses']
    strengths = stats['strengths']
    subcategories = stats['subcategories']

    # Determine player archetype based on performance
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]['percentage'], reverse=True)
    best_cat = sorted_cats[0] if sorted_cats else None
    worst_cat = sorted_cats[-1] if sorted_cats else None

    # Generate synopsis
    if overall >= 80:
        skill_level = "trivia master"
        skill_desc = "You have exceptional knowledge across the board."
    elif overall >= 65:
        skill_level = "trivia enthusiast"
        skill_desc = "You have solid knowledge with room to grow."
    elif overall >= 50:
        skill_level = "curious learner"
        skill_desc = "You're building a good foundation of knowledge."
    else:
        skill_level = "trivia rookie"
        skill_desc = "You're just getting started on your knowledge journey."

    # Build strength description
    strength_text = ""
    if best_cat and best_cat[1]['percentage'] >= 60 and best_cat[1]['total'] >= 3:
        cat_name = CATEGORIES[best_cat[0]]['name']
        strength_text = f"Your strongest area is {cat_name} ({best_cat[1]['percentage']}%)."
        if strengths:
            top_subs = [s['name'] for s in strengths[:2]]
            if top_subs:
                strength_text += f" You particularly excel at {' and '.join(top_subs)}."

    # Build weakness description
    weakness_text = ""
    if worst_cat and worst_cat[1]['percentage'] < 60 and worst_cat[1]['total'] >= 3:
        cat_name = CATEGORIES[worst_cat[0]]['name']
        weakness_text = f"{cat_name} is your biggest opportunity for growth ({worst_cat[1]['percentage']}%)."

    # Get recommendations based on weak subcategories
    recommendations = []
    seen_resources = set()

    # Get weak areas (subcategories below 50% with at least 3 attempts)
    weak_subs = []
    for sub_name, sub_stats in subcategories.items():
        if sub_stats['total'] >= 3 and sub_stats['percentage'] < 50:
            weak_subs.append((sub_name, sub_stats))

    # Sort by percentage (worst first)
    weak_subs.sort(key=lambda x: x[1]['percentage'])

    # Get resources for weak areas
    for sub_name, sub_stats in weak_subs[:4]:  # Top 4 weakest
        cat = sub_stats['category']
        if cat in LEARNING_RESOURCES:
            cat_resources = LEARNING_RESOURCES[cat]
            # Try exact subcategory match first
            if sub_name in cat_resources:
                for resource in cat_resources[sub_name]:
                    resource_key = resource['title']
                    if resource_key not in seen_resources and resource_key not in dismissed_titles:
                        seen_resources.add(resource_key)
                        recommendations.append({
                            'topic': sub_name.replace('_', ' ').title(),
                            'category': cat,
                            **resource
                        })
                        if len(recommendations) >= 6:
                            break
        if len(recommendations) >= 6:
            break

    # If not enough recommendations, add from weak categories
    if len(recommendations) < 4:
        for cat_key, cat_stats in sorted_cats[-3:]:  # 3 worst categories
            if cat_stats['total'] >= 3 and cat_stats['percentage'] < 60:
                if cat_key in LEARNING_RESOURCES:
                    # Get first available subcategory resources
                    for sub_key, resources in LEARNING_RESOURCES[cat_key].items():
                        for resource in resources:
                            resource_key = resource['title']
                            if resource_key not in seen_resources and resource_key not in dismissed_titles:
                                seen_resources.add(resource_key)
                                recommendations.append({
                                    'topic': CATEGORIES[cat_key]['name'],
                                    'category': cat_key,
                                    **resource
                                })
                                break
                        if len(recommendations) >= 6:
                            break
            if len(recommendations) >= 6:
                break

    # Interest-based recommendations from strong subcategories (>= 70% with >= 3 attempts)
    interest_recs = []
    seen_interest = set()
    strong_subs = []
    for sub_name, sub_stats in subcategories.items():
        if sub_stats['total'] >= 3 and sub_stats['percentage'] >= 70:
            strong_subs.append((sub_name, sub_stats))
    strong_subs.sort(key=lambda x: x[1]['percentage'], reverse=True)

    for sub_name, sub_stats in strong_subs[:6]:
        cat = sub_stats['category']
        if cat in LEARNING_RESOURCES:
            cat_resources = LEARNING_RESOURCES[cat]
            if sub_name in cat_resources:
                for resource in cat_resources[sub_name]:
                    resource_key = resource['title']
                    if resource_key not in seen_interest and resource_key not in seen_resources and resource_key not in dismissed_titles:
                        seen_interest.add(resource_key)
                        interest_recs.append({
                            'topic': sub_name.replace('_', ' ').title(),
                            'category': cat,
                            **resource
                        })
                        break
        if len(interest_recs) >= 6:
            break

    # If not enough, add from strong categories
    if len(interest_recs) < 4:
        for cat_key, cat_stats in sorted_cats[:3]:  # 3 best categories
            if cat_stats['total'] >= 3 and cat_stats['percentage'] >= 60:
                if cat_key in LEARNING_RESOURCES:
                    for sub_key, resources in LEARNING_RESOURCES[cat_key].items():
                        for resource in resources:
                            resource_key = resource['title']
                            if resource_key not in seen_interest and resource_key not in seen_resources and resource_key not in dismissed_titles:
                                seen_interest.add(resource_key)
                                interest_recs.append({
                                    'topic': CATEGORIES[cat_key]['name'],
                                    'category': cat_key,
                                    **resource
                                })
                                break
                        if len(interest_recs) >= 6:
                            break
            if len(interest_recs) >= 6:
                break

    return {
        'skill_level': skill_level,
        'skill_desc': skill_desc,
        'strength_text': strength_text,
        'weakness_text': weakness_text,
        'total_questions': total_questions,
        'overall': overall,
        'recommendations': recommendations[:6],
        'interest_recs': interest_recs[:6]
    }


def get_user_today():
    """Get today's date adjusted for US Eastern timezone."""
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)
    # Offset for US Eastern (UTC-5, or UTC-4 during DST)
    # Simple approach: subtract 5 hours from UTC
    eastern_offset = timedelta(hours=-5)
    eastern_now = utc_now + eastern_offset
    return eastern_now.date()

def has_played_today(user_id, difficulty=None):
    """Check if user has already played today, optionally at a specific difficulty."""
    today = get_user_today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    if difficulty:
        cur.execute(
            f'SELECT COUNT(*) as count FROM game_results WHERE user_id = {placeholder} AND game_date = {placeholder} AND difficulty = {placeholder}',
            (user_id, today, difficulty)
        )
    else:
        cur.execute(
            f'SELECT COUNT(*) as count FROM game_results WHERE user_id = {placeholder} AND game_date = {placeholder}',
            (user_id, today)
        )
    result = cur.fetchone()
    conn.close()
    return result['count'] > 0


def get_played_difficulties_today(user_id):
    """Get list of difficulties user has played today."""
    today = get_user_today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'
    # Fetch all results for user and filter in Python to avoid SQL type issues
    cur.execute(
        f'SELECT game_date, COALESCE(difficulty, \'easy\') as difficulty FROM game_results WHERE user_id = {placeholder}',
        (user_id,)
    )
    results = cur.fetchall()
    conn.close()

    # Filter to today's games in Python
    difficulties = set()
    for r in results:
        game_date = str(r['game_date'])
        # Handle both DATE objects and strings
        if game_date == today or game_date.startswith(today):
            difficulties.add(r['difficulty'] or 'easy')
    return list(difficulties)


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
            full_name = user_info.get('name', user_info['email'].split('@')[0])
            first_name = user_info.get('given_name', full_name.split()[0] if full_name else 'User')
            user_data = get_or_create_user_by_google(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=first_name,
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

            # Check for invite token and create friendship
            invite_token = session.pop('invite_token', None)
            if invite_token:
                process_invite(invite_token, user.id, user_info['email'])

            return redirect(url_for('play'))
    except Exception as e:
        print(f"OAuth error: {e}")
        return redirect(url_for('index'))

    return redirect(url_for('index'))


def process_invite(token, new_user_id, email):
    """Process an invite after user signs up."""
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Get the invite
    cur.execute(f"SELECT * FROM invites WHERE token = {ph} AND status = 'pending'", (token,))
    invite = cur.fetchone()

    if invite:
        inviter_id = invite['inviter_id'] if hasattr(invite, '__getitem__') and isinstance(invite, dict) else invite[1]

        # Mark invite as accepted
        cur.execute(f"UPDATE invites SET status = 'accepted' WHERE token = {ph}", (token,))

        # Create automatic friendship (already accepted)
        try:
            cur.execute(f'''
                INSERT INTO friendships (requester_id, addressee_id, status)
                VALUES ({ph}, {ph}, 'accepted')
            ''', (inviter_id, new_user_id))
        except:
            pass  # Friendship might already exist

        conn.commit()

    conn.close()


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
                'profile_picture': current_user.profile_picture,
                'google_id': current_user.google_id
            }
        })
    return jsonify({'authenticated': False})


@app.route('/api/update-username', methods=['POST'])
def update_username():
    """Update username for anonymous users."""
    data = request.get_json() or {}
    new_username = data.get('username', '').strip()

    if not new_username or len(new_username) < 2:
        return jsonify({'error': 'Username must be at least 2 characters'}), 400

    if len(new_username) > 30:
        return jsonify({'error': 'Username must be 30 characters or less'}), 400

    # Get user from session or anonymous_id
    user_id = None
    if current_user.is_authenticated:
        # Don't allow Google users to change username here
        if current_user.google_id:
            return jsonify({'error': 'Google users cannot change username'}), 400
        user_id = current_user.id
    else:
        anonymous_id = data.get('anonymous_id') or request.cookies.get('uptriv_anonymous_id')
        if anonymous_id:
            conn = get_db()
            cur = conn.cursor()
            ph = get_placeholder()
            cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
            user = cur.fetchone()
            conn.close()
            if user:
                user_id = user['id']

    if not user_id:
        return jsonify({'error': 'User not found'}), 400

    # Check if username is taken
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    cur.execute(f'SELECT id FROM users WHERE LOWER(username) = {ph} AND id != {ph}', (new_username.lower(), user_id))
    existing = cur.fetchone()

    if existing:
        conn.close()
        return jsonify({'error': 'Username already taken'}), 400

    # Update username
    cur.execute(f'UPDATE users SET username = {ph} WHERE id = {ph}', (new_username, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'username': new_username})


@app.route('/api/anonymous-session', methods=['POST'])
def get_or_create_anonymous_session():
    """Get or create an anonymous user session for cookie-based play."""
    import uuid

    data = request.get_json() or {}
    anonymous_id = data.get('anonymous_id')

    try:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()

        if anonymous_id:
            # Check if this anonymous user exists
            cur.execute(f'SELECT * FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
            user = cur.fetchone()
            if user:
                # Record a visit so this user appears in admin active users
                ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if ip and ',' in ip:
                    ip = ip.split(',')[0].strip()
                cur.execute(f'''
                    INSERT INTO visits (path, ip_address, user_agent, user_id)
                    VALUES ({ph}, {ph}, {ph}, {ph})
                ''', ('/play', ip, request.user_agent.string[:500], user['id']))
                conn.commit()
                conn.close()
                resp = jsonify({
                    'success': True,
                    'anonymous_id': anonymous_id,
                    'user_id': user['id'],
                    'username': user['username']
                })
                resp.set_cookie('uptriv_anonymous_id', anonymous_id, max_age=365*24*60*60, samesite='Lax')
                return resp

        # Create new anonymous user
        new_anonymous_id = str(uuid.uuid4())
        # Generate a fun random username
        adjectives = ['Swift', 'Clever', 'Bright', 'Quick', 'Sharp', 'Keen', 'Bold', 'Wise']
        nouns = ['Owl', 'Fox', 'Eagle', 'Wolf', 'Hawk', 'Bear', 'Tiger', 'Lion']
        import random
        username = f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(100, 999)}"

        cur.execute(
            f'INSERT INTO users (username, anonymous_id) VALUES ({ph}, {ph})',
            (username, new_anonymous_id)
        )
        conn.commit()

        # Get the new user's ID
        cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (new_anonymous_id,))
        new_user = cur.fetchone()

        # Record a visit so this user appears in admin active users
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        cur.execute(f'''
            INSERT INTO visits (path, ip_address, user_agent, user_id)
            VALUES ({ph}, {ph}, {ph}, {ph})
        ''', ('/play', ip, request.user_agent.string[:500], new_user['id']))
        conn.commit()
        conn.close()

        resp = jsonify({
            'success': True,
            'anonymous_id': new_anonymous_id,
            'user_id': new_user['id'],
            'username': username
        })
        resp.set_cookie('uptriv_anonymous_id', new_anonymous_id, max_age=365*24*60*60, samesite='Lax')
        return resp
    except Exception as e:
        print(f"Error creating anonymous session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/set-difficulty', methods=['POST'])
def set_difficulty():
    """Set user's difficulty mode (easy/hard)."""
    user_id, username = get_user_from_request()

    if not user_id:
        return jsonify({'error': 'No user session'}), 401

    data = request.get_json() or {}
    difficulty = data.get('difficulty', 'easy')

    if difficulty not in ['easy', 'hard']:
        return jsonify({'error': 'Invalid difficulty. Must be "easy" or "hard"'}), 400

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    cur.execute(f'UPDATE users SET difficulty = {ph} WHERE id = {ph}', (difficulty, user_id))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'difficulty': difficulty,
        'message': f'Difficulty set to {difficulty} mode'
    })


@app.route('/api/get-difficulty')
def get_difficulty():
    """Get user's current difficulty setting."""
    user_id = None

    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        anonymous_id = request.args.get('anonymous_id')
        if anonymous_id:
            conn = get_db()
            cur = conn.cursor()
            ph = get_placeholder()
            cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
            user = cur.fetchone()
            conn.close()
            if user:
                user_id = user['id']

    if not user_id:
        return jsonify({'difficulty': 'easy'})

    difficulty = get_user_difficulty(user_id)
    return jsonify({'difficulty': difficulty})


# ============ ONBOARDING QUIZ ROUTES ============

@app.route('/api/onboarding-status')
def onboarding_status():
    """Get user's onboarding quiz progress."""
    user_id = None

    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        anonymous_id = request.args.get('anonymous_id')
        if anonymous_id:
            conn = get_db()
            cur = conn.cursor()
            ph = get_placeholder()
            cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
            user = cur.fetchone()
            conn.close()
            if user:
                user_id = user['id']

    if not user_id:
        return jsonify({'completed': 0, 'total': 50, 'is_complete': False})

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT onboarding_completed FROM users WHERE id = {ph}', (user_id,))
    result = cur.fetchone()
    conn.close()

    completed = result['onboarding_completed'] if result else 0
    return jsonify({
        'completed': completed,
        'total': 50,
        'is_complete': completed >= 50,
        'next_set': (completed // 10) + 1 if completed < 50 else None,
        'questions_in_set': min(10, 50 - completed)
    })


@app.route('/api/start-onboarding', methods=['POST'])
def start_onboarding():
    """Get the next set of 10 onboarding questions."""
    user_id, username = get_user_from_request()

    if not user_id:
        return jsonify({'error': 'No user session'}), 401

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT onboarding_completed FROM users WHERE id = {ph}', (user_id,))
    result = cur.fetchone()
    completed = result['onboarding_completed'] if result else 0
    conn.close()

    if completed >= 50:
        return jsonify({'error': 'Onboarding already complete', 'is_complete': True}), 400

    # Get next 10 questions (or remaining if less than 10)
    start_index = completed
    end_index = min(completed + 10, 50)
    questions = ONBOARDING_QUESTIONS[start_index:end_index]

    # Format questions for frontend
    safe_questions = []
    for i, q in enumerate(questions):
        safe_questions.append({
            'index': start_index + i,
            'category': q['category'],
            'category_name': CATEGORIES[q['category']]['name'],
            'color': CATEGORIES[q['category']]['color'],
            'question': q['q'],
            'options': q['options'],
            'subcategory': q['sub']
        })

    return jsonify({
        'success': True,
        'questions': safe_questions,
        'set_number': (completed // 10) + 1,
        'total_sets': 5,
        'completed_so_far': completed
    })


@app.route('/api/submit-onboarding-answer', methods=['POST'])
def submit_onboarding_answer():
    """Submit an answer for an onboarding question."""
    user_id, username = get_user_from_request()

    if not user_id:
        return jsonify({'error': 'No user session'}), 401

    data = request.get_json() or {}
    question_index = data.get('question_index')
    user_answer = data.get('answer')
    time_taken = data.get('time_taken', 10)

    if question_index is None or question_index >= len(ONBOARDING_QUESTIONS):
        return jsonify({'error': 'Invalid question index'}), 400

    question = ONBOARDING_QUESTIONS[question_index]
    correct = user_answer == question['a']

    # Store result in game_results with special game_date for onboarding
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Use a special date format for onboarding results: 'onboarding-YYYY-MM-DD'
    today = get_user_today().isoformat()
    onboarding_date = f"onboarding-{today}"

    cur.execute(f'''
        INSERT INTO game_results (user_id, game_date, category, subcategory, question, correct_answer, user_answer, correct, time_taken)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ''', (user_id, onboarding_date, question['category'], question['sub'], question['q'], question['a'], user_answer, 1 if correct else 0, time_taken))

    # Update onboarding_completed count
    cur.execute(f'UPDATE users SET onboarding_completed = onboarding_completed + 1 WHERE id = {ph}', (user_id,))

    conn.commit()

    # Get updated count
    cur.execute(f'SELECT onboarding_completed FROM users WHERE id = {ph}', (user_id,))
    result = cur.fetchone()
    new_completed = result['onboarding_completed'] if result else 0
    conn.close()

    return jsonify({
        'success': True,
        'correct': correct,
        'correct_answer': question['a'],
        'completed': new_completed,
        'set_complete': new_completed % 10 == 0,
        'onboarding_complete': new_completed >= 50
    })


@app.route('/api/onboarding-results')
def onboarding_results():
    """Get summary of onboarding quiz results."""
    try:
        user_id = None

        if current_user.is_authenticated:
            user_id = current_user.id
        else:
            anonymous_id = request.args.get('anonymous_id')
            if anonymous_id:
                conn = get_db()
                cur = conn.cursor()
                ph = get_placeholder()
                cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
                user = cur.fetchone()
                conn.close()
                if user:
                    user_id = user['id']

        if not user_id:
            return jsonify({'success': False, 'error': 'No user session'})

        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()

        # Get all results and filter in Python to avoid SQL type issues
        cur.execute(f'''
            SELECT game_date, category, correct
            FROM game_results
            WHERE user_id = {ph}
        ''', (user_id,))
        all_results = cur.fetchall()
        conn.close()

        # Filter to onboarding results in Python
        results = [r for r in all_results if str(r['game_date']).startswith('onboarding')]

        if not results:
            return jsonify({'success': False, 'error': 'No onboarding results found'})

        # Calculate stats by category
        category_stats = {}
        total_correct = 0
        total_questions = len(results)

        for r in results:
            cat = r['category']
            if cat not in category_stats:
                category_stats[cat] = {'correct': 0, 'total': 0}
            category_stats[cat]['total'] += 1
            if r['correct']:
                category_stats[cat]['correct'] += 1
                total_correct += 1

        # Calculate percentages
        for cat in category_stats:
            stats = category_stats[cat]
            stats['percentage'] = round((stats['correct'] / stats['total']) * 100) if stats['total'] > 0 else 0

        overall_percentage = round((total_correct / total_questions) * 100) if total_questions > 0 else 0

        return jsonify({
            'success': True,
            'overall': {
                'correct': total_correct,
                'total': total_questions,
                'completed': total_questions,
                'percentage': overall_percentage
            },
            'categories': category_stats,
            'recommended_difficulty': 'hard' if overall_percentage >= 80 else 'easy'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/check-hard-mode-eligibility')
def check_hard_mode_eligibility():
    """Check if user's performance qualifies them for hard mode (top 20%)."""
    user_id = None

    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        anonymous_id = request.args.get('anonymous_id')
        if anonymous_id:
            conn = get_db()
            cur = conn.cursor()
            ph = get_placeholder()
            cur.execute(f'SELECT id, difficulty FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
            user = cur.fetchone()
            conn.close()
            if user:
                user_id = user['id']
                # Don't show prompt if already on hard mode
                if user['difficulty'] == 'hard':
                    return jsonify({'eligible': False, 'reason': 'already_hard'})

    if not user_id:
        return jsonify({'eligible': False, 'reason': 'no_session'})

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Check current difficulty
    cur.execute(f'SELECT difficulty FROM users WHERE id = {ph}', (user_id,))
    user_data = cur.fetchone()
    if user_data and user_data['difficulty'] == 'hard':
        conn.close()
        return jsonify({'eligible': False, 'reason': 'already_hard'})

    # Calculate user's overall correct percentage (excluding onboarding)
    cur.execute(f'''
        SELECT COUNT(*) as total, SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct_count
        FROM game_results
        WHERE user_id = {ph} AND game_date NOT LIKE 'onboarding-%'
    ''', (user_id,))
    user_stats = cur.fetchone()

    if not user_stats or user_stats['total'] < 6:
        conn.close()
        return jsonify({'eligible': False, 'reason': 'not_enough_games'})

    user_percentage = (user_stats['correct_count'] / user_stats['total']) * 100 if user_stats['total'] > 0 else 0

    # Get all users' percentages to find top 20% threshold
    cur.execute('''
        SELECT user_id,
               COUNT(*) as total,
               SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct_count
        FROM game_results
        WHERE game_date NOT LIKE 'onboarding-%'
        GROUP BY user_id
        HAVING COUNT(*) >= 6
    ''')
    all_users = cur.fetchall()
    conn.close()

    if len(all_users) < 5:
        # Not enough users to determine top 20%, use absolute threshold
        eligible = user_percentage >= 80
        return jsonify({
            'eligible': eligible,
            'user_percentage': round(user_percentage, 1),
            'threshold': 80,
            'reason': 'absolute_threshold' if eligible else 'below_threshold'
        })

    # Calculate percentages for all users
    all_percentages = []
    for u in all_users:
        pct = (u['correct_count'] / u['total']) * 100 if u['total'] > 0 else 0
        all_percentages.append(pct)

    all_percentages.sort(reverse=True)

    # Find top 20% threshold
    top_20_index = max(0, int(len(all_percentages) * 0.2) - 1)
    threshold = all_percentages[top_20_index]

    eligible = user_percentage >= threshold

    return jsonify({
        'eligible': eligible,
        'user_percentage': round(user_percentage, 1),
        'threshold': round(threshold, 1),
        'percentile': round(100 - (all_percentages.index(min(all_percentages, key=lambda x: abs(x - user_percentage))) / len(all_percentages) * 100), 1),
        'reason': 'top_20' if eligible else 'below_threshold'
    })


# ============ VISIT TRACKING ============

# Admin email(s) allowed to access admin page
ADMIN_EMAILS = ['kaplanae@gmail.com']

def track_visit():
    """Track page visit for analytics."""
    # Skip API calls and static files
    if request.path.startswith('/api/') or request.path.startswith('/static/'):
        return

    try:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()

        user_id = current_user.id if current_user.is_authenticated else None

        # Also try to resolve anonymous users to their user_id
        if not user_id:
            anonymous_id = request.cookies.get('uptriv_anonymous_id')
            if anonymous_id:
                cur.execute(f'SELECT id FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
                row = cur.fetchone()
                if row:
                    user_id = row['id'] if isinstance(row, dict) else row[0]

        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        cur.execute(f'''
            INSERT INTO visits (path, ip_address, user_agent, user_id)
            VALUES ({ph}, {ph}, {ph}, {ph})
        ''', (request.path, ip, request.user_agent.string[:500], user_id))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Visit tracking error: {e}")


@app.before_request
def before_request():
    """Run before each request."""
    track_visit()


# ============ PAGE ROUTES ============

@app.route('/')
def index():
    return render_template('index.html', categories=CATEGORIES)


@app.route('/play')
def play():
    return render_template('play.html', categories=CATEGORIES)


@app.route('/onboarding')
def onboarding():
    return render_template('onboarding.html', categories=CATEGORIES)


@app.route('/profile')
def profile():
    # Redirect to the new Profile page (formerly History)
    return redirect(url_for('history'))


@app.route('/profile/<username>')
def user_profile(username):
    # Redirect to the new Profile page with username
    return redirect(url_for('history_user', username=username))


@app.route('/history')
def history():
    return render_template('history.html', categories=CATEGORIES, view_username=None)


@app.route('/history/<username>')
def history_user(username):
    return render_template('history.html', categories=CATEGORIES, view_username=username)


@app.route('/friends')
@login_required
def friends_page():
    return render_template('friends.html', categories=CATEGORIES)


@app.route('/leaderboard')
@login_required
def leaderboard_page():
    return render_template('leaderboard.html', categories=CATEGORIES)


@app.route('/admin')
@login_required
def admin_page():
    """Admin dashboard with site analytics."""
    # Check if user is admin
    if not current_user.email or current_user.email not in ADMIN_EMAILS:
        return redirect(url_for('index'))

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Get visit stats
    today = get_user_today().isoformat()

    # Today's visits
    cur.execute(f"SELECT COUNT(*) as count FROM visits WHERE DATE(visited_at) = {ph}", (today,))
    today_visits = cur.fetchone()['count']

    # Today's unique IPs
    cur.execute(f"SELECT COUNT(DISTINCT ip_address) as count FROM visits WHERE DATE(visited_at) = {ph}", (today,))
    today_unique = cur.fetchone()['count']

    # Total visits all time
    cur.execute("SELECT COUNT(*) as count FROM visits")
    total_visits = cur.fetchone()['count']

    # Total unique IPs all time
    cur.execute("SELECT COUNT(DISTINCT ip_address) as count FROM visits")
    total_unique = cur.fetchone()['count']

    # Total registered users
    cur.execute("SELECT COUNT(*) as count FROM users")
    total_users = cur.fetchone()['count']

    # Users with Google auth
    cur.execute("SELECT COUNT(*) as count FROM users WHERE google_id IS NOT NULL")
    google_users = cur.fetchone()['count']

    # Total games played
    cur.execute("SELECT COUNT(DISTINCT user_id || game_date || COALESCE(difficulty, 'easy')) as count FROM game_results")
    total_games = cur.fetchone()['count']

    # Visits by page (top 10)
    cur.execute('''
        SELECT path, COUNT(*) as count
        FROM visits
        GROUP BY path
        ORDER BY count DESC
        LIMIT 10
    ''')
    page_visits = [dict(row) for row in cur.fetchall()]

    # Daily visits for last 7 days
    cur.execute('''
        SELECT DATE(visited_at) as date, COUNT(*) as visits, COUNT(DISTINCT ip_address) as unique_visitors
        FROM visits
        GROUP BY DATE(visited_at)
        ORDER BY date DESC
        LIMIT 7
    ''')
    daily_stats = [dict(row) for row in cur.fetchall()]

    # Recent logins (users who visited today)
    cur.execute(f'''
        SELECT DISTINCT u.username, u.email, u.profile_picture,
            u.google_id, u.anonymous_id, u.created_at
        FROM visits v
        JOIN users u ON v.user_id = u.id
        WHERE DATE(v.visited_at) = {ph}
        ORDER BY u.username
    ''', (today,))
    today_logins = [dict(row) for row in cur.fetchall()]

    conn.close()

    return render_template('admin.html',
        today_visits=today_visits,
        today_unique=today_unique,
        total_visits=total_visits,
        total_unique=total_unique,
        total_users=total_users,
        google_users=google_users,
        total_games=total_games,
        page_visits=page_visits,
        daily_stats=daily_stats,
        today_logins=today_logins
    )


@app.route('/admin/flush-questions', methods=['POST'])
@login_required
def flush_daily_questions():
    """Admin-only: clear today's cached questions AND game results to allow replay."""
    if not current_user.email or current_user.email not in ADMIN_EMAILS:
        return redirect(url_for('index'))

    data = request.get_json() or {}
    difficulty = data.get('difficulty', 'all')

    today = get_user_today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    questions_deleted = 0
    results_deleted = 0

    if difficulty == 'all':
        # Clear all cached question sets for today
        cur.execute(f'DELETE FROM daily_questions WHERE game_date = {ph}', (today,))
        questions_deleted = cur.rowcount
        # Clear all game results for today (so everyone can replay)
        cur.execute(f'DELETE FROM game_results WHERE game_date = {ph}', (today,))
        results_deleted = cur.rowcount
    else:
        # Delete cached questions matching the specified difficulty
        cur.execute(f'SELECT id, questions_json FROM daily_questions WHERE game_date = {ph}', (today,))
        rows = cur.fetchall()
        ids_to_delete = []
        for row in rows:
            try:
                questions = json.loads(row['questions_json'])
                if questions and questions[0].get('difficulty') == difficulty:
                    ids_to_delete.append(row['id'])
            except:
                pass
        for row_id in ids_to_delete:
            cur.execute(f'DELETE FROM daily_questions WHERE id = {ph}', (row_id,))
        questions_deleted = len(ids_to_delete)

        # Clear game results for today at this difficulty (so everyone can replay it)
        cur.execute(f'DELETE FROM game_results WHERE game_date = {ph} AND COALESCE(difficulty, \'easy\') = {ph}', (today, difficulty))
        results_deleted = cur.rowcount

    conn.commit()
    conn.close()
    return jsonify({
        'success': True,
        'questions_flushed': questions_deleted,
        'results_cleared': results_deleted,
        'date': today,
        'difficulty': difficulty
    })


@app.route('/admin/preview-questions', methods=['POST'])
@login_required
def preview_questions():
    """Admin-only: generate questions for a future date without caching anything."""
    if not current_user.email or current_user.email not in ADMIN_EMAILS:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    date_str = data.get('date')

    if date_str:
        try:
            preview_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    else:
        preview_date = get_user_today() + timedelta(days=1)

    # Get all previously used questions to avoid repeats
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT questions_json FROM daily_questions')
    recently_used = set()
    for row in cur.fetchall():
        try:
            questions = json.loads(row['questions_json'])
            for q in questions:
                recently_used.add(q.get('q'))
        except:
            pass
    conn.close()

    result = {}
    for difficulty in ['easy', 'hard']:
        seed = int(hashlib.md5(f"{preview_date.isoformat()}-{difficulty}".encode()).hexdigest(), 16)
        rng = random.Random(seed)
        question_bank = HARD_QUESTIONS if difficulty == 'hard' else QUESTIONS

        questions = []
        for cat_key in ['news', 'history', 'science', 'entertainment', 'sports', 'geography']:
            category_questions = question_bank[cat_key]
            available = [q for q in category_questions if q['q'] not in recently_used]
            if not available:
                available = category_questions
            rng.shuffle(available)
            q = available[0]
            for candidate in available:
                if candidate['q'] not in recently_used:
                    q = candidate
                    break
            questions.append({
                'category': cat_key,
                'category_name': CATEGORIES[cat_key]['name'],
                'color': CATEGORIES[cat_key]['color'],
                'difficulty': difficulty,
                **q
            })
        rng.shuffle(questions)
        label = 'normal' if difficulty == 'easy' else 'expert'
        result[label] = questions

    return jsonify({
        'success': True,
        'date': preview_date.isoformat(),
        'questions': result
    })


# ============ GAME API ROUTES ============

@app.route('/api/debug-time')
def debug_time():
    """Debug endpoint to check server time."""
    from datetime import timezone as tz
    utc_now = datetime.now(tz.utc)
    eastern_offset = timedelta(hours=-5)
    eastern_now = utc_now + eastern_offset
    return jsonify({
        'utc_now': utc_now.isoformat(),
        'eastern_now': eastern_now.isoformat(),
        'get_user_today': get_user_today().isoformat(),
        'server_date_today': date.today().isoformat()
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint with performance metrics for monitoring."""
    import time
    start = time.time()

    try:
        conn = get_db()
        cur = conn.cursor()

        # Count users
        cur.execute('SELECT COUNT(*) as count FROM users')
        user_count = cur.fetchone()['count']

        # Count game results
        cur.execute('SELECT COUNT(*) as count FROM game_results')
        result_count = cur.fetchone()['count']

        # Count today's games
        today = get_user_today().isoformat()
        ph = get_placeholder()
        cur.execute(f"SELECT COUNT(DISTINCT user_id) as count FROM game_results WHERE game_date = {ph}", (today,))
        today_players = cur.fetchone()['count']

        conn.close()

        db_time = time.time() - start

        # Determine status based on metrics
        status = 'healthy'
        warnings = []

        if db_time > 1.0:
            status = 'degraded'
            warnings.append('Database queries slow (>1s)')
        elif db_time > 0.5:
            warnings.append('Database queries slightly slow (>500ms)')

        if result_count > 100000 and db_time > 0.3:
            warnings.append('Large dataset - consider adding caching')

        return jsonify({
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'total_users': user_count,
                'total_game_results': result_count,
                'players_today': today_players,
                'db_query_time_ms': round(db_time * 1000, 2)
            },
            'warnings': warnings if warnings else None,
            'database': 'postgresql' if USE_POSTGRES else 'sqlite'
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/reset-today', methods=['POST'])
@login_required
def reset_today():
    """Reset today's game for testing/timezone issues."""
    today = get_user_today().isoformat()
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Delete today's questions and results
    cur.execute(f'DELETE FROM daily_questions WHERE user_id = {ph} AND game_date = {ph}', (current_user.id, today))
    cur.execute(f'DELETE FROM game_results WHERE user_id = {ph} AND game_date = {ph}', (current_user.id, today))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Reset game for {today}'})


def get_user_from_request():
    """Get user from either session (Google login) or anonymous_id."""
    if current_user.is_authenticated:
        return current_user.id, current_user.username

    # Check for anonymous user
    data = request.get_json() or {}
    anonymous_id = data.get('anonymous_id')

    if anonymous_id:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'SELECT id, username FROM users WHERE anonymous_id = {ph}', (anonymous_id,))
        user = cur.fetchone()
        conn.close()
        if user:
            return user['id'], user['username']

    return None, None


@app.route('/api/start-game', methods=['POST'])
def start_game():
    try:
        user_id, username = get_user_from_request()

        if not user_id:
            return jsonify({'error': 'No user session. Please refresh the page.', 'require_session': True}), 401

        # Get user's current difficulty and what they've played today
        current_difficulty = get_user_difficulty(user_id)
        played_today = get_played_difficulties_today(user_id)

        # Check if they've already played at their current difficulty
        if current_difficulty in played_today:
            # If they played easy but not hard, they can still play hard
            can_play_hard = 'easy' in played_today and 'hard' not in played_today

            # Customize message based on what they've played
            if 'easy' in played_today and 'hard' in played_today:
                message = "You've completed both Easy and Hard mode today! Come back tomorrow for new questions."
            elif current_difficulty == 'hard' and 'hard' in played_today:
                message = "You've already played Hard mode today! Come back tomorrow for new questions."
            else:
                message = "You've already played Easy mode today! Try Hard mode for an extra challenge, or come back tomorrow."

            return jsonify({
                'error': 'already_played',
                'message': message,
                'played_difficulties': played_today,
                'can_play_hard': can_play_hard
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
            'user': {'id': user_id, 'username': username},
            'game_date': get_user_today().isoformat()
        })
    except Exception as e:
        import traceback
        print(f"Error in start_game: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    user_id, username = get_user_from_request()

    if not user_id:
        return jsonify({'error': 'No user session'}), 401

    question_index = data.get('question_index')
    answer = data.get('answer')
    time_taken = data.get('time_taken', 10)

    questions = get_daily_questions_for_user(user_id)

    if question_index < 0 or question_index >= len(questions):
        return jsonify({'error': 'Invalid question'}), 400

    q = questions[question_index]
    correct = answer == q['a']
    difficulty = q.get('difficulty', 'easy')

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    # Save the answer with difficulty
    cur.execute(f'''
        INSERT INTO game_results (user_id, game_date, category, subcategory, question, correct_answer, user_answer, correct, time_taken, difficulty)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    ''', (user_id, get_user_today().isoformat(), q['category'], q['sub'], q['q'], q['a'], answer, 1 if correct else 0, time_taken, difficulty))
    conn.commit()

    # Get stats for this question (how many got it right)
    cur.execute(f'''
        SELECT COUNT(*) as total, SUM(correct) as correct_count
        FROM game_results
        WHERE question = {placeholder}
    ''', (q['q'],))
    stats = cur.fetchone()
    conn.close()

    total_answers = stats['total'] or 1
    correct_count = stats['correct_count'] or 0
    percent_correct = round((correct_count / total_answers) * 100)

    return jsonify({
        'correct': correct,
        'correct_answer': q['a'],
        'percent_correct': percent_correct,
        'total_answers': total_answers
    })


@app.route('/api/dismiss-recommendation', methods=['POST'])
def dismiss_recommendation():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401

    data = request.get_json()
    title = data.get('title', '').strip() if data else ''
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    user_id = current_user.id
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Insert dismissed title (allow duplicates silently)
    cur.execute(
        f'INSERT INTO dismissed_recommendations (user_id, title) VALUES ({ph}, {ph})',
        (user_id, title)
    )
    conn.commit()

    # Fetch all dismissed titles for this user
    cur.execute(f'SELECT title FROM dismissed_recommendations WHERE user_id = {ph}', (user_id,))
    dismissed_titles = {row['title'] for row in cur.fetchall()}
    conn.close()

    # Return refreshed recommendations
    stats = calculate_user_stats(user_id)
    summary = generate_player_summary(stats, dismissed_titles=dismissed_titles)

    return jsonify({
        'success': True,
        'player_summary': summary
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

    # Fetch dismissed titles if user is logged in
    dismissed_titles = set()
    if current_user.is_authenticated and user_id == current_user.id:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'SELECT title FROM dismissed_recommendations WHERE user_id = {ph}', (user_id,))
        dismissed_titles = {row['title'] for row in cur.fetchall()}
        conn.close()

    stats = calculate_user_stats(user_id)
    stats['categories_meta'] = CATEGORIES

    # Add player summary with recommendations
    stats['player_summary'] = generate_player_summary(stats, dismissed_titles=dismissed_titles)

    return jsonify(stats)


@app.route('/api/get-history', methods=['GET'])
def get_history():
    try:
        username = request.args.get('username')
        anonymous_id = request.args.get('anonymous_id')
        user_id = None
        auth_method = None

        conn = get_db()
        cur = conn.cursor()
        placeholder = '%s' if USE_POSTGRES else '?'

        # Try to find user by various methods
        if current_user.is_authenticated:
            user_id = current_user.id
            auth_method = 'google_session'
        elif username:
            cur.execute(f'SELECT id FROM users WHERE username = {placeholder}', (username,))
            user = cur.fetchone()
            if user:
                user_id = user['id']
                auth_method = 'username'

        # Also try anonymous_id if we still don't have a user
        if not user_id and anonymous_id:
            cur.execute(f'SELECT id FROM users WHERE anonymous_id = {placeholder}', (anonymous_id,))
            user = cur.fetchone()
            if user:
                user_id = user['id']
                auth_method = 'anonymous_id'

        if not user_id:
            conn.close()
            return jsonify({'error': 'User not found', 'games': []})

        # Simple query without the LIKE filter to test
        cur.execute(f'''
            SELECT game_date, category, subcategory, question, correct_answer, user_answer, correct, time_taken, COALESCE(difficulty, 'easy') as difficulty
            FROM game_results
            WHERE user_id = {placeholder}
            ORDER BY created_at DESC
        ''', (user_id,))
        all_results = cur.fetchall()

        # Filter out onboarding in Python instead of SQL
        results = [r for r in all_results if not str(r['game_date']).startswith('onboarding')]

        # Get percentage stats for all questions this user has answered
        questions_list = list(set(r['question'] for r in results))
        question_stats = {}
        for q in questions_list:
            cur.execute(f'''
                SELECT COUNT(*) as total, SUM(correct) as correct_count
                FROM game_results WHERE question = {placeholder}
            ''', (q,))
            stats = cur.fetchone()
            total = stats['total'] or 1
            correct_count = stats['correct_count'] or 0
            question_stats[q] = round((correct_count / total) * 100)

        conn.close()

        # Group by date AND difficulty (so easy and hard on same day are separate rows)
        games = {}
        for r in results:
            game_date = r['game_date'] if isinstance(r['game_date'], str) else r['game_date'].isoformat()
            difficulty = r['difficulty'] or 'easy'
            game_key = f"{game_date}_{difficulty}"

            if game_key not in games:
                games[game_key] = {
                    'date': game_date,
                    'difficulty': difficulty,
                    'questions': [],
                    'score': 0,
                    'total': 0
                }
            games[game_key]['questions'].append({
                'category': r['category'],
                'category_name': CATEGORIES.get(r['category'], {}).get('name', r['category']),
                'color': CATEGORIES.get(r['category'], {}).get('color', '#888'),
                'question': r['question'],
                'correct_answer': r['correct_answer'],
                'user_answer': r['user_answer'] or '(No answer)',
                'correct': r['correct'],
                'time_taken': round(r['time_taken'], 1),
                'percent_correct': question_stats.get(r['question'], 0)
            })
            games[game_key]['total'] += 1
            if r['correct']:
                games[game_key]['score'] += 1

        # Sort by date desc, then hard before easy
        games_list = sorted(games.values(), key=lambda x: (x['date'], x['difficulty']), reverse=True)
        return jsonify({
            'games': games_list,
            'debug': {
                'user_id': user_id,
                'auth_method': auth_method,
                'total_results': len(all_results),
                'filtered_results': len(results),
                'total_games': len(games_list)
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'games': []}), 500


@app.route('/api/get-share-text', methods=['GET'])
def get_share_text():
    username = request.args.get('username')
    game_date = request.args.get('date')
    difficulty = request.args.get('difficulty', 'easy')

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

    # Filter by difficulty
    cur.execute(f'''
        SELECT category, correct
        FROM game_results
        WHERE user_id = {placeholder} AND game_date = {placeholder} AND difficulty = {placeholder}
        ORDER BY created_at ASC
    ''', (user_id, game_date, difficulty))
    results = cur.fetchall()
    conn.close()

    if not results:
        return jsonify({'error': 'No results found for that date and difficulty'})

    score = sum(1 for r in results if r['correct'])
    total = len(results)

    # Build share grid - green for correct, red for incorrect
    squares = []
    for r in results:
        if r['correct']:
            squares.append('🟩')
        else:
            squares.append('🟥')

    date_obj = datetime.strptime(game_date, '%Y-%m-%d')
    date_str = date_obj.strftime('%b %d, %Y')

    # Include difficulty in share text
    difficulty_label = "🔥 Expert" if difficulty == 'hard' else "🎯 Normal"

    share_text = f"UpTriv {difficulty_label}\n{date_str}\n{score}/{total} " + "".join(squares) + "\nwww.uptriv.com"

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
    if len(query) < 1:
        return jsonify({'users': []})

    conn = get_db()
    cur = conn.cursor()
    placeholder = '%s' if USE_POSTGRES else '?'

    # Exact match only (case-insensitive) - for privacy
    cur.execute(f'''
        SELECT id, username, profile_picture
        FROM users
        WHERE LOWER(username) = {placeholder}
        AND id != {placeholder}
        AND google_id IS NOT NULL
        LIMIT 1
    ''', (query.lower(), current_user.id))

    users = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({'users': users})


@app.route('/api/friends/request', methods=['POST'])
@login_required
def api_send_friend_request():
    data = request.get_json()
    friend_id = data.get('addressee_id') or data.get('user_id')

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


@app.route('/api/friends/invite', methods=['POST'])
@login_required
def api_invite_friend():
    """Send an email invite to a friend."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400

    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    # Check if user already exists with this email
    cur.execute(f'SELECT id FROM users WHERE email = {ph}', (email,))
    existing_user = cur.fetchone()

    if existing_user:
        # User exists - just send a friend request instead
        conn.close()
        return jsonify({'error': 'User already exists. Send a friend request instead.', 'user_exists': True}), 400

    # Check if invite already sent
    cur.execute(f"SELECT id FROM invites WHERE inviter_id = {ph} AND email = {ph} AND status = 'pending'",
               (current_user.id, email))
    existing_invite = cur.fetchone()

    if existing_invite:
        conn.close()
        return jsonify({'error': 'Invite already sent to this email'}), 400

    # Create invite token
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=7)

    cur.execute(f'''
        INSERT INTO invites (inviter_id, email, token, expires_at)
        VALUES ({ph}, {ph}, {ph}, {ph})
    ''', (current_user.id, email, token, expires_at))

    conn.commit()
    conn.close()

    # Generate invite link
    invite_url = url_for('accept_invite', token=token, _external=True)

    # Try to send email, but always return the link as fallback
    email_sent = False
    if resend.api_key:
        try:
            resend.emails.send({
                "from": "UpTriv <noreply@uptriv.com>",
                "to": [email],
                "subject": f"{current_user.username} invited you to UpTriv!",
                "html": f'''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #667eea;">You're Invited to UpTriv!</h1>
                    <p><strong>{current_user.username}</strong> wants you to join them on UpTriv - a daily brain training trivia game.</p>
                    <p>Challenge yourself with 6 questions across different categories:</p>
                    <ul>
                        <li>World & U.S. News</li>
                        <li>History</li>
                        <li>Science & Nature</li>
                        <li>Entertainment</li>
                        <li>Sports</li>
                        <li>Geography</li>
                    </ul>
                    <p>
                        <a href="{invite_url}" style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                            Join UpTriv
                        </a>
                    </p>
                    <p style="color: #666; font-size: 14px;">This invite expires in 7 days.</p>
                </div>
                '''
            })
            email_sent = True
        except Exception as e:
            print(f"Resend email error: {e}")

    if email_sent:
        return jsonify({'success': True, 'message': f'Invite sent to {email}', 'invite_url': invite_url})
    else:
        return jsonify({'success': True, 'message': 'Invite created! Share this link with your friend:', 'invite_url': invite_url})


@app.route('/invite/<token>')
def accept_invite(token):
    """Handle invite link - redirect to sign up."""
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()

    cur.execute(f"SELECT * FROM invites WHERE token = {ph} AND status = 'pending'", (token,))
    invite = cur.fetchone()

    if not invite:
        conn.close()
        return redirect(url_for('index'))

    # Check if expired
    expires_at = invite['expires_at'] if hasattr(invite, '__getitem__') else invite[6]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if datetime.now() > expires_at:
        conn.close()
        return redirect(url_for('index'))

    # Store invite token in session for after OAuth
    session['invite_token'] = token
    conn.close()

    # Redirect to Google sign in
    return redirect(url_for('google_login'))


# ============ LEADERBOARD API ============

@app.route('/api/leaderboard', methods=['GET'])
@login_required
def api_leaderboard():
    friends = get_friends(current_user.id)

    # Include current user in leaderboard
    all_users = [{'id': current_user.id, 'username': current_user.username,
                  'profile_picture': current_user.profile_picture, 'is_self': True}]

    for friend in friends:
        if friend['id'] == current_user.id:
            continue
        friend['is_self'] = False
        all_users.append(friend)

    # Calculate stats for all users — split by difficulty
    leaderboard_normal = []
    leaderboard_expert = []
    category_leaderboards_normal = {cat: [] for cat in CATEGORIES}
    category_leaderboards_expert = {cat: [] for cat in CATEGORIES}

    for user in all_users:
        stats = calculate_user_stats(user['id'])
        user_info = {
            'id': user['id'],
            'username': user['username'],
            'profile_picture': user.get('profile_picture'),
            'is_self': user.get('is_self', False)
        }

        # Normal (easy) overall
        if stats.get('overall_easy_total', 0) > 0:
            leaderboard_normal.append({
                'user': user_info,
                'percentage': stats['overall_easy_percentage'],
                'total': stats['overall_easy_total'],
                'correct': sum(stats['categories'][c].get('easy_correct', 0) for c in stats['categories'])
            })

        # Expert (hard) overall
        if stats.get('overall_hard_total', 0) > 0:
            leaderboard_expert.append({
                'user': user_info,
                'percentage': stats['overall_hard_percentage'],
                'total': stats['overall_hard_total'],
                'correct': sum(stats['categories'][c].get('hard_correct', 0) for c in stats['categories'])
            })

        # Category-specific leaderboards per difficulty
        for cat in CATEGORIES:
            cat_stats = stats['categories'][cat]
            if cat_stats.get('easy_total', 0) > 0:
                category_leaderboards_normal[cat].append({
                    'user': user_info,
                    'percentage': cat_stats['easy_percentage'],
                    'correct': cat_stats['easy_correct'],
                    'total': cat_stats['easy_total']
                })
            if cat_stats.get('hard_total', 0) > 0:
                category_leaderboards_expert[cat].append({
                    'user': user_info,
                    'percentage': cat_stats['hard_percentage'],
                    'correct': cat_stats['hard_correct'],
                    'total': cat_stats['hard_total']
                })

    # Sort and rank helper
    def sort_and_rank(lb):
        lb.sort(key=lambda x: (-x['percentage'], -x['total']))
        for i, entry in enumerate(lb):
            entry['rank'] = i + 1

    sort_and_rank(leaderboard_normal)
    sort_and_rank(leaderboard_expert)
    for cat in CATEGORIES:
        sort_and_rank(category_leaderboards_normal[cat])
        sort_and_rank(category_leaderboards_expert[cat])

    # Add fake users to fill leaderboard if less than 10 real users
    fake_users_normal = [
        {'name': 'Alex', 'pct': 82, 'games': 9},
        {'name': 'Jordan', 'pct': 78, 'games': 8},
        {'name': 'Taylor', 'pct': 75, 'games': 9},
        {'name': 'Morgan', 'pct': 72, 'games': 7},
        {'name': 'Casey', 'pct': 69, 'games': 6},
        {'name': 'Riley', 'pct': 66, 'games': 8},
        {'name': 'Quinn', 'pct': 63, 'games': 5},
        {'name': 'Avery', 'pct': 60, 'games': 7},
        {'name': 'Jamie', 'pct': 57, 'games': 4},
        {'name': 'Drew', 'pct': 54, 'games': 3},
    ]
    fake_users_expert = [
        {'name': 'Alex', 'pct': 50, 'games': 7},
        {'name': 'Jordan', 'pct': 46, 'games': 6},
        {'name': 'Taylor', 'pct': 43, 'games': 7},
        {'name': 'Morgan', 'pct': 40, 'games': 5},
        {'name': 'Casey', 'pct': 37, 'games': 4},
        {'name': 'Riley', 'pct': 34, 'games': 6},
        {'name': 'Quinn', 'pct': 31, 'games': 3},
        {'name': 'Avery', 'pct': 28, 'games': 5},
        {'name': 'Jamie', 'pct': 25, 'games': 2},
        {'name': 'Drew', 'pct': 22, 'games': 2},
    ]

    # Category-specific fake data with varied percentages
    fake_category_normal = {
        'news': [{'name': 'Alex', 'pct': 85, 'games': 8}, {'name': 'Morgan', 'pct': 79, 'games': 7}, {'name': 'Taylor', 'pct': 74, 'games': 9}, {'name': 'Casey', 'pct': 68, 'games': 6}, {'name': 'Riley', 'pct': 62, 'games': 5}],
        'history': [{'name': 'Jordan', 'pct': 81, 'games': 9}, {'name': 'Quinn', 'pct': 76, 'games': 7}, {'name': 'Alex', 'pct': 70, 'games': 8}, {'name': 'Avery', 'pct': 65, 'games': 6}, {'name': 'Drew', 'pct': 58, 'games': 4}],
        'science': [{'name': 'Taylor', 'pct': 84, 'games': 9}, {'name': 'Casey', 'pct': 77, 'games': 8}, {'name': 'Jordan', 'pct': 71, 'games': 7}, {'name': 'Jamie', 'pct': 64, 'games': 5}, {'name': 'Morgan', 'pct': 59, 'games': 6}],
        'entertainment': [{'name': 'Riley', 'pct': 86, 'games': 8}, {'name': 'Avery', 'pct': 80, 'games': 9}, {'name': 'Quinn', 'pct': 73, 'games': 7}, {'name': 'Alex', 'pct': 67, 'games': 6}, {'name': 'Taylor', 'pct': 61, 'games': 5}],
        'sports': [{'name': 'Morgan', 'pct': 83, 'games': 9}, {'name': 'Drew', 'pct': 78, 'games': 7}, {'name': 'Riley', 'pct': 72, 'games': 8}, {'name': 'Jordan', 'pct': 66, 'games': 6}, {'name': 'Casey', 'pct': 60, 'games': 5}],
        'geography': [{'name': 'Quinn', 'pct': 82, 'games': 8}, {'name': 'Jamie', 'pct': 75, 'games': 7}, {'name': 'Avery', 'pct': 69, 'games': 9}, {'name': 'Drew', 'pct': 63, 'games': 5}, {'name': 'Alex', 'pct': 57, 'games': 6}],
    }
    fake_category_expert = {
        'news': [{'name': 'Alex', 'pct': 52, 'games': 6}, {'name': 'Morgan', 'pct': 46, 'games': 5}, {'name': 'Taylor', 'pct': 41, 'games': 7}, {'name': 'Casey', 'pct': 35, 'games': 4}, {'name': 'Riley', 'pct': 30, 'games': 3}],
        'history': [{'name': 'Jordan', 'pct': 48, 'games': 7}, {'name': 'Quinn', 'pct': 43, 'games': 5}, {'name': 'Alex', 'pct': 38, 'games': 6}, {'name': 'Avery', 'pct': 32, 'games': 4}, {'name': 'Drew', 'pct': 26, 'games': 3}],
        'science': [{'name': 'Taylor', 'pct': 51, 'games': 7}, {'name': 'Casey', 'pct': 44, 'games': 6}, {'name': 'Jordan', 'pct': 39, 'games': 5}, {'name': 'Jamie', 'pct': 33, 'games': 3}, {'name': 'Morgan', 'pct': 27, 'games': 4}],
        'entertainment': [{'name': 'Riley', 'pct': 53, 'games': 6}, {'name': 'Avery', 'pct': 47, 'games': 7}, {'name': 'Quinn', 'pct': 40, 'games': 5}, {'name': 'Alex', 'pct': 34, 'games': 4}, {'name': 'Taylor', 'pct': 29, 'games': 3}],
        'sports': [{'name': 'Morgan', 'pct': 50, 'games': 7}, {'name': 'Drew', 'pct': 45, 'games': 5}, {'name': 'Riley', 'pct': 39, 'games': 6}, {'name': 'Jordan', 'pct': 33, 'games': 4}, {'name': 'Casey', 'pct': 28, 'games': 3}],
        'geography': [{'name': 'Quinn', 'pct': 49, 'games': 6}, {'name': 'Jamie', 'pct': 42, 'games': 5}, {'name': 'Avery', 'pct': 36, 'games': 7}, {'name': 'Drew', 'pct': 30, 'games': 3}, {'name': 'Alex', 'pct': 25, 'games': 4}],
    }

    def add_fakes(lb, fakes, questions_per_game=6):
        if len(lb) < 10:
            for i, fake in enumerate(fakes):
                if len(lb) >= 10:
                    break
                total = fake['games'] * questions_per_game
                correct = int(total * fake['pct'] / 100)
                lb.append({
                    'user': {'id': -1 - i, 'username': fake['name'], 'profile_picture': None, 'is_self': False, 'is_fake': True},
                    'percentage': fake['pct'], 'total': total, 'correct': correct
                })
            sort_and_rank(lb)

    add_fakes(leaderboard_normal, fake_users_normal)
    add_fakes(leaderboard_expert, fake_users_expert)
    for cat in CATEGORIES:
        if cat in fake_category_normal:
            add_fakes(category_leaderboards_normal[cat], fake_category_normal[cat], 1)
        if cat in fake_category_expert:
            add_fakes(category_leaderboards_expert[cat], fake_category_expert[cat], 1)

    return jsonify({
        'normal': {
            'overall': leaderboard_normal,
            'categories': category_leaderboards_normal
        },
        'expert': {
            'overall': leaderboard_expert,
            'categories': category_leaderboards_expert
        }
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
