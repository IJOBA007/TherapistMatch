import sqlite3
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)
DATABASE_PATH = os.path.join(DATA_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')


def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def parse_allowed_origins():
    origins = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
    if not origins:
        return None
    if origins == '*':
        return '*'
    return [origin.strip() for origin in origins.split(',') if origin.strip()]


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        role TEXT,
        name TEXT,
        age INTEGER,
        gender TEXT,
        location TEXT,
        language TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        therapist_email TEXT,
        date TEXT,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        amount INTEGER,
        currency TEXT,
        provider TEXT,
        reference TEXT,
        status TEXT,
        created_at TEXT,
        verified_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_care (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_email TEXT,
        sender_role TEXT,
        message TEXT,
        admin_reply TEXT,
        status TEXT,
        created_at TEXT,
        replied_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_email TEXT,
        role TEXT,
        created_at TEXT,
        expires_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS therapist_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        therapist_email TEXT,
        rating INTEGER,
        comment TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_therapist_reviews_user_therapist
    ON therapist_reviews(user_email, therapist_email)
    """)

    conn.commit()

    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "dob" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN dob TEXT")
    if "primary_language" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN primary_language TEXT")
    if "secondary_language" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN secondary_language TEXT")
    if "specialties" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN specialties TEXT")
    if "license_number" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN license_number TEXT")
    if "license_state" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN license_state TEXT")
    if "license_expiry" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN license_expiry TEXT")
    if "specialization" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN specialization TEXT")
    if "experience_years" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN experience_years INTEGER")
    if "bio" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
    if "hourly_rate" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN hourly_rate TEXT")
    if "education" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN education TEXT")
    if "certifications" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN certifications TEXT")
    if "availability" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN availability TEXT")
    if "session_formats" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN session_formats TEXT")
    if "profile_photo" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    if "credential_document" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN credential_document TEXT")
    if "verification_status" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN verification_status TEXT DEFAULT 'draft'")
    if "rejection_reason" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN rejection_reason TEXT")

    cursor.execute("PRAGMA table_info(bookings)")
    existing_booking_columns = [row[1] for row in cursor.fetchall()]
    if "client_needs" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN client_needs TEXT")

    cursor.execute("PRAGMA table_info(payments)")
    existing_payment_columns = [row[1] for row in cursor.fetchall()]
    if "archived" not in existing_payment_columns:
        cursor.execute("ALTER TABLE payments ADD COLUMN archived INTEGER DEFAULT 0")
    if "archived_at" not in existing_payment_columns:
        cursor.execute("ALTER TABLE payments ADD COLUMN archived_at TEXT")

    cursor.execute("""
    UPDATE users
    SET verification_status='verified'
    WHERE role='therapist' AND verified=1
      AND (verification_status IS NULL OR verification_status='' OR verification_status='draft')
    """)
    cursor.execute("""
    UPDATE users
    SET verification_status='pending'
    WHERE role='therapist' AND verified=0
      AND license_number IS NOT NULL AND license_number != ''
      AND (verification_status IS NULL OR verification_status='' OR verification_status='draft')
    """)
    cursor.execute("""
    UPDATE users
    SET verification_status='draft'
    WHERE role='therapist' AND verified=0
      AND (license_number IS NULL OR license_number = '')
      AND (verification_status IS NULL OR verification_status='')
    """)

    conn.commit()
    conn.close()

init_db()

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
CORS_ALLOWED_ORIGINS = parse_allowed_origins()
if CORS_ALLOWED_ORIGINS:
    CORS(app, origins=CORS_ALLOWED_ORIGINS)

ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
PASSWORD_HASH_PREFIXES = ('scrypt:', 'pbkdf2:', 'argon2:')
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SESSION_HOURS = 12
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 5 * 60
LOGIN_ATTEMPTS = {}


def now_iso():
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def future_iso(hours):
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat(timespec='seconds') + 'Z'


def normalize_email(email):
    return str(email or '').strip().lower()


def is_valid_email(email):
    return bool(EMAIL_PATTERN.fullmatch(normalize_email(email)))


def validate_password_strength(password):
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must include at least one letter and one number."
    return ""


def is_login_limited(email):
    key = normalize_email(email)
    attempt = LOGIN_ATTEMPTS.get(key)
    if not attempt:
        return False

    if time.time() - attempt["last_attempt"] > LOGIN_LOCK_SECONDS:
        LOGIN_ATTEMPTS.pop(key, None)
        return False

    return attempt["count"] >= MAX_LOGIN_ATTEMPTS


def record_failed_login(email):
    key = normalize_email(email)
    now = time.time()
    attempt = LOGIN_ATTEMPTS.get(key)

    if not attempt or now - attempt["last_attempt"] > LOGIN_LOCK_SECONDS:
        LOGIN_ATTEMPTS[key] = {"count": 1, "last_attempt": now}
        return

    attempt["count"] += 1
    attempt["last_attempt"] = now


def clear_failed_login(email):
    LOGIN_ATTEMPTS.pop(normalize_email(email), None)


def create_session(cursor, email, role):
    token = secrets.token_urlsafe(32)
    cursor.execute("""
    INSERT INTO sessions (token, user_email, role, created_at, expires_at)
    VALUES (?, ?, ?, ?, ?)
    """, (token, normalize_email(email), role, now_iso(), future_iso(SESSION_HOURS)))
    return token


def get_authenticated_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT user_email, role FROM sessions
    WHERE token=? AND expires_at > ?
    """, (token, now_iso()))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {"email": row[0], "role": row[1]}


def require_admin():
    user = get_authenticated_user()
    if not user or user.get("role") != "admin":
        return jsonify({"message": "Admin login required"}), 401
    return None


def is_password_hash(password_value):
    return bool(password_value) and password_value.startswith(PASSWORD_HASH_PREFIXES)


def password_matches(stored_password, submitted_password):
    if not stored_password or not submitted_password:
        return False

    if is_password_hash(stored_password):
        return check_password_hash(stored_password, submitted_password)

    return stored_password == submitted_password


def save_uploaded_file(field_name, email):
    uploaded_file = request.files.get(field_name)
    if not uploaded_file or not uploaded_file.filename:
        return None

    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f"{field_name} must be a PDF, PNG, JPG, JPEG, or WEBP file")

    safe_email = secure_filename(email.replace('@', '_at_').replace('.', '_'))
    filename = f"{safe_email}_{field_name}_{uuid4().hex[:10]}.{extension}"
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    return f"/uploads/{filename}"


def parse_booking_datetime(value):
    if not value:
        return None

    normalized = str(value).strip()
    if normalized.endswith('Z'):
        normalized = normalized[:-1]

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo:
        parsed = parsed.replace(tzinfo=None)

    return parsed.replace(second=0, microsecond=0)


def minutes_from_time(value):
    if not value or ':' not in value:
        return None

    try:
        hour_value, minute_value = value.split(':', 1)
        return int(hour_value) * 60 + int(minute_value[:2])
    except (TypeError, ValueError):
        return None


def parse_availability_value(value):
    if not value:
        return {"duration": 60, "slots": [], "legacy": ""}

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict) and isinstance(parsed.get("slots"), list):
            return {
                "duration": int(parsed.get("duration") or 60),
                "slots": [
                    {
                        "day": slot.get("day"),
                        "start": slot.get("start") or "",
                        "end": slot.get("end") or ""
                    }
                    for slot in parsed.get("slots", [])
                    if isinstance(slot, dict) and slot.get("day")
                ],
                "legacy": ""
            }
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    parts = str(value).split("|")
    if len(parts) >= 2:
        days = [day.strip() for day in parts[0].split(",") if day.strip()]
        time_range = [item.strip() for item in parts[1].split("-", 1)]
        duration_match = re.search(r"(\d+)", parts[2] if len(parts) > 2 else "")

        if days and len(time_range) == 2 and time_range[0] and time_range[1]:
            return {
                "duration": int(duration_match.group(1)) if duration_match else 60,
                "slots": [{"day": day, "start": time_range[0], "end": time_range[1]} for day in days],
                "legacy": ""
            }

    return {"duration": 60, "slots": [], "legacy": str(value)}


def requested_time_is_available(availability_value, requested_start):
    availability = parse_availability_value(availability_value)

    if availability["legacy"]:
        return True, availability["duration"]

    if not availability["slots"]:
        return False, availability["duration"]

    requested_day = requested_start.strftime("%A")
    requested_minute = requested_start.hour * 60 + requested_start.minute
    duration = availability["duration"] or 60

    for slot in availability["slots"]:
        if slot["day"] != requested_day:
            continue

        slot_start = minutes_from_time(slot["start"])
        slot_end = minutes_from_time(slot["end"])
        if slot_start is None or slot_end is None:
            continue

        if slot_start <= requested_minute and requested_minute + duration <= slot_end:
            return True, duration

    return False, duration


def existing_booking_conflicts(existing_date, requested_start, duration):
    existing_start = parse_booking_datetime(existing_date)
    if not existing_start:
        return False

    existing_end = existing_start + timedelta(minutes=duration)
    requested_end = requested_start + timedelta(minutes=duration)
    return requested_start < existing_end and existing_start < requested_end


def normalize_needs(value):
    if isinstance(value, list):
        needs = [str(item).strip() for item in value if str(item).strip()]
    else:
        needs = [item.strip() for item in str(value or "").split(",") if item.strip()]

    return ",".join(needs[:4])

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}

    email = normalize_email(data.get('email'))
    password = data.get('password')
    role = data.get('role')

    if not email or not password or role not in ('user', 'therapist', 'admin'):
        return jsonify({"message": "Please enter a valid email, password, and role"}), 400

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid email address"}), 400

    password_message = validate_password_strength(password)
    if password_message:
        return jsonify({"message": password_message}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if role == 'admin':
        admin_signup_code = os.environ.get('ADMIN_SIGNUP_CODE', '').strip()
        cursor.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
        admin_exists = cursor.fetchone() is not None

        if admin_signup_code and data.get('admin_code') != admin_signup_code:
            conn.close()
            return jsonify({"message": "Admin signup code is required"}), 403

        if admin_exists and not admin_signup_code:
            conn.close()
            return jsonify({"message": "Admin signup is locked. Ask the current admin to create access."}), 403

    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"message": "An account with this email already exists"}), 409

    verification_status = 'draft' if role == 'therapist' else 'verified'

    password_hash = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (email, password, role, verification_status) VALUES (?, ?, ?, ?)",
        (email, password_hash, role, verification_status)
    )
    token = create_session(cursor, email, role)

    conn.commit()
    conn.close()

    return jsonify({"message": "Account created", "role": role, "token": token})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = normalize_email(data.get('email'))
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Please enter email and password"}), 400

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid email address"}), 400

    if is_login_limited(email):
        return jsonify({"message": "Too many login attempts. Please wait a few minutes and try again."}), 429

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password, role, verified, verification_status FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if user and password_matches(user[1], password):
        user_id = user[0]
        stored_password = user[1]
        role = user[2]
        verified = user[3]
        status = user[4] or ('verified' if verified else 'draft')

        if not is_password_hash(stored_password):
            cursor.execute(
                "UPDATE users SET password=? WHERE id=?",
                (generate_password_hash(password), user_id)
            )

        token = create_session(cursor, email, role)
        conn.commit()
        clear_failed_login(email)

        conn.close()

        return jsonify({"message": "Login successful", "role": role, "verified": verified, "status": status, "token": token})

    conn.close()
    record_failed_login(email)
    return jsonify({"message": "Invalid credentials"}), 401



@app.route('/update_profile', methods=['POST'])
def update_profile():
    data = request.get_json()

    email = normalize_email(data.get('email'))
    name = data.get('name')
    dob = data.get('dob')
    gender = data.get('gender')
    location = data.get('location')
    primary_language = data.get('primary_language')
    secondary_language = data.get('secondary_language')
    specialties = ','.join(data.get('specialties', []))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users SET name=?, dob=?, gender=?, location=?, primary_language=?, secondary_language=?, specialties=?
    WHERE email=?
    """, (name, dob, gender, location, primary_language, secondary_language, specialties, email))

    if cursor.rowcount == 0:
        cursor.execute("""
        INSERT INTO users (email, name, dob, gender, location, primary_language, secondary_language, specialties, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, name, dob, gender, location, primary_language, secondary_language, specialties, 'user'))

    conn.commit()
    conn.close()

    return jsonify({"message": "Profile updated"})
    

@app.route('/get_profile', methods=['POST'])
def get_profile():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, dob, gender, location, primary_language, secondary_language, specialties FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    conn.close()

    if user:
        profile = {
            "name": user[0],
            "dob": user[1],
            "gender": user[2],
            "location": user[3],
            "primary_language": user[4],
            "secondary_language": user[5],
            "specialties": user[6].split(',') if user[6] else []
        }
        return jsonify({"profile": profile})

    return jsonify({"message": "Profile not found"}), 404

@app.route('/match', methods=['POST'])
def match():
    data = request.get_json() or {}

    primary_language = data.get('primary_language') or data.get('language')
    raw_specializations = data.get('specializations') or data.get('specialization') or []
    if isinstance(raw_specializations, str):
        specializations = [raw_specializations] if raw_specializations else []
    else:
        specializations = [item for item in raw_specializations if item]

    if len(specializations) < 1 or len(specializations) > 4:
        return jsonify({"message": "Please select between 1 and 4 specialties"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT u.email, u.name, u.location, u.primary_language, u.secondary_language, u.specialization,
           u.experience_years, u.bio, u.hourly_rate, u.profile_photo, u.session_formats, u.availability,
           COALESCE(r.rating_average, 0), COALESCE(r.rating_count, 0)
    FROM users u
    LEFT JOIN (
        SELECT therapist_email, ROUND(AVG(rating), 1) AS rating_average, COUNT(*) AS rating_count
        FROM therapist_reviews
        GROUP BY therapist_email
    ) r ON r.therapist_email = u.email
    WHERE u.role='therapist' AND u.verified=1
    """
    params = []

    if primary_language:
        query += " AND (u.primary_language=? OR u.secondary_language=?)"
        params.extend([primary_language, primary_language])

    cursor.execute(query, params)

    rows = cursor.fetchall()
    conn.close()

    therapists = []
    selected_specialties = set(specializations)
    for therapist in rows:
        therapist_specialties = [
            item.strip()
            for item in (therapist[5] or '').split(',')
            if item.strip()
        ]

        if selected_specialties and not selected_specialties.intersection(therapist_specialties):
            continue

        therapists.append({
            "email": therapist[0],
            "name": therapist[1],
            "location": therapist[2],
            "primary_language": therapist[3],
            "secondary_language": therapist[4],
            "specialization": therapist[5],
            "experience_years": therapist[6],
            "bio": therapist[7],
            "hourly_rate": therapist[8],
            "profile_photo": therapist[9],
            "session_formats": therapist[10].split(',') if therapist[10] else [],
            "availability": therapist[11],
            "rating_average": therapist[12],
            "rating_count": therapist[13]
        })

    return jsonify({"therapists": therapists})


@app.route('/book', methods=['POST'])
def book():
    data = request.get_json() or {}
    user_email = normalize_email(data.get('user_email'))
    therapist_email = normalize_email(data.get('therapist_email'))
    date = data.get('date')
    requested_start = parse_booking_datetime(date)
    client_needs = normalize_needs(data.get('client_needs'))

    if not user_email or not therapist_email or not date:
        return jsonify({"message": "Missing booking details"}), 400

    if not is_valid_email(user_email) or not is_valid_email(therapist_email):
        return jsonify({"message": "Please use valid account emails for booking"}), 400

    if not requested_start:
        return jsonify({"message": "Please choose a valid appointment date and time"}), 400

    if requested_start < datetime.now().replace(second=0, microsecond=0):
        return jsonify({"message": "Please choose a future appointment time"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, dob, gender, location, primary_language, secondary_language, specialties
    FROM users
    WHERE email=? AND role='user'
    """, (user_email,))
    user_profile = cursor.fetchone()

    if not user_profile or not all(user_profile[index] for index in range(5)):
        conn.close()
        return jsonify({"message": "Please complete your profile in Settings before booking. Your profile is shared with the therapist before the session begins."}), 400

    cursor.execute("""
    SELECT id, availability FROM users
    WHERE email=? AND role='therapist' AND verified=1
    """, (therapist_email,))
    therapist = cursor.fetchone()
    if not therapist:
        conn.close()
        return jsonify({"message": "This therapist is not available for booking right now"}), 404

    is_available, duration = requested_time_is_available(therapist[1], requested_start)
    if not is_available:
        conn.close()
        return jsonify({"message": "This therapist is not available at that day or time. Please choose a time inside their listed availability."}), 400

    cursor.execute("""
    SELECT date FROM bookings
    WHERE therapist_email=?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """, (therapist_email,))
    existing_bookings = cursor.fetchall()

    for existing_booking in existing_bookings:
        if existing_booking_conflicts(existing_booking[0], requested_start, duration):
            conn.close()
            return jsonify({
                "message": "This therapist is available then, but that time is already booked. Please choose another time.",
                "status": "booked"
            }), 409

    cursor.execute("""
    INSERT INTO bookings (user_email, therapist_email, date, status, client_needs)
    VALUES (?, ?, ?, ?, ?)
    """, (user_email, therapist_email, requested_start.isoformat(timespec='minutes'), 'Pending', client_needs))

    conn.commit()
    conn.close()

    return jsonify({"message": "Session request sent. Your profile has been shared with the therapist."})


@app.route('/therapist_bookings', methods=['POST'])
def therapist_bookings():
    data = request.get_json()
    email = normalize_email(data.get('email'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT b.id, b.user_email, b.date, b.status,
           u.name, u.dob, u.gender, u.location,
           u.primary_language, u.secondary_language, u.specialties, b.client_needs
    FROM bookings b
    LEFT JOIN users u ON b.user_email = u.email
    WHERE b.therapist_email=?
    ORDER BY b.id DESC
    """, (email,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "bookings": [
            {
                "id": row[0],
                "user_email": row[1],
                "date": row[2],
                "status": row[3],
                "user_profile": {
                    "name": row[4],
                    "dob": row[5],
                    "gender": row[6],
                    "location": row[7],
                    "primary_language": row[8],
                    "secondary_language": row[9],
                    "specialties": (row[11] or row[10] or '').split(',') if (row[11] or row[10]) else []
                }
            }
            for row in rows
        ]
    })


@app.route('/user_bookings', methods=['POST'])
def user_bookings():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT b.id, b.therapist_email, b.date, b.status, b.client_needs,
           u.name, u.specialization, u.profile_photo,
           tr.rating, tr.comment
    FROM bookings b
    LEFT JOIN users u ON b.therapist_email = u.email
    LEFT JOIN therapist_reviews tr
      ON tr.therapist_email = b.therapist_email AND tr.user_email = b.user_email
    WHERE b.user_email=?
    ORDER BY b.id DESC
    """, (email,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "bookings": [
            {
                "id": row[0],
                "therapist_email": row[1],
                "date": row[2],
                "status": row[3],
                "client_needs": row[4].split(',') if row[4] else [],
                "therapist": {
                    "name": row[5],
                    "specialization": row[6],
                    "profile_photo": row[7]
                },
                "review": {
                    "rating": row[8],
                    "comment": row[9]
                } if row[8] else None
            }
            for row in rows
        ]
    })


@app.route('/rate_therapist', methods=['POST'])
def rate_therapist():
    data = request.get_json() or {}
    user_email = normalize_email(data.get('user_email'))
    therapist_email = normalize_email(data.get('therapist_email'))
    comment = (data.get('comment') or '').strip()

    try:
        rating = int(data.get('rating'))
    except (TypeError, ValueError):
        rating = 0

    if not is_valid_email(user_email) or not is_valid_email(therapist_email):
        return jsonify({"message": "Please use valid account emails"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"message": "Please choose a rating from 1 to 5"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id FROM bookings
    WHERE user_email=? AND therapist_email=?
    LIMIT 1
    """, (user_email, therapist_email))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"message": "You can only rate a therapist after booking them"}), 403

    cursor.execute("""
    SELECT id FROM therapist_reviews
    WHERE user_email=? AND therapist_email=?
    """, (user_email, therapist_email))
    existing_review = cursor.fetchone()

    if existing_review:
        cursor.execute("""
        UPDATE therapist_reviews
        SET rating=?, comment=?, updated_at=?
        WHERE id=?
        """, (rating, comment, now_iso(), existing_review[0]))
    else:
        cursor.execute("""
        INSERT INTO therapist_reviews (user_email, therapist_email, rating, comment, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_email, therapist_email, rating, comment, now_iso(), now_iso()))

    conn.commit()
    conn.close()

    return jsonify({"message": "Therapist rating saved"})



@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO messages (sender, receiver, message)
    VALUES (?, ?, ?)
    """, (
        data.get('sender'),
        data.get('receiver'),
        data.get('message')
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Message sent"})

@app.route('/get_messages', methods=['POST'])
def get_messages():
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT sender, message FROM messages
    WHERE (sender=? AND receiver=?)
    OR (sender=? AND receiver=?)
    """, (
        data.get('user1'),
        data.get('user2'),
        data.get('user2'),
        data.get('user1')
    ))

    messages = cursor.fetchall()
    conn.close()

    return jsonify({"messages": messages})

# Therapist credential submission
@app.route('/submit_credentials', methods=['POST'])
def submit_credentials():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    email = data.get('email')

    if not email:
        return jsonify({"message": "Missing therapist email"}), 400

    name = data.get('name')
    location = data.get('location')
    primary_language = data.get('primary_language')
    secondary_language = data.get('secondary_language')
    license_number = data.get('license_number')
    license_state = data.get('license_state')
    license_expiry = data.get('license_expiry')
    if request.form:
        specialization = ','.join(request.form.getlist('specialization'))
    else:
        raw_specialization = data.get('specialization', '')
        specialization = ','.join(raw_specialization) if isinstance(raw_specialization, list) else raw_specialization
    selected_specialties = [item.strip() for item in specialization.split(',') if item.strip()]
    if len(selected_specialties) < 1 or len(selected_specialties) > 4:
        return jsonify({"message": "Please select between 1 and 4 specialties"}), 400
    experience_years = data.get('experience_years')
    bio = data.get('bio')
    hourly_rate = data.get('hourly_rate')
    education = data.get('education')
    certifications = data.get('certifications')
    availability = data.get('availability')

    if request.form:
        session_formats = ','.join(request.form.getlist('session_formats'))
    else:
        raw_formats = data.get('session_formats', '')
        session_formats = ','.join(raw_formats) if isinstance(raw_formats, list) else raw_formats

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT verified, profile_photo, credential_document
    FROM users
    WHERE email=? AND role='therapist'
    """, (email,))
    therapist = cursor.fetchone()

    if not therapist:
        conn.close()
        return jsonify({"message": "Therapist account not found"}), 404

    try:
        profile_photo = save_uploaded_file('profile_photo', email) or therapist[1]
        credential_document = save_uploaded_file('credential_document', email) or therapist[2]
    except ValueError as error:
        conn.close()
        return jsonify({"message": str(error)}), 400

    is_verified = therapist[0] == 1
    verification_status = 'verified' if is_verified else 'pending'
    verified = 1 if is_verified else 0

    cursor.execute("""
    UPDATE users SET 
        name=?, location=?, primary_language=?, secondary_language=?,
        license_number=?, license_state=?, license_expiry=?,
        specialization=?, experience_years=?, bio=?,
        hourly_rate=?, education=?, certifications=?,
        availability=?, session_formats=?, profile_photo=?, credential_document=?,
        verified=?, verification_status=?, rejection_reason=NULL
    WHERE email=?
    """, (name, location, primary_language, secondary_language,
          license_number, license_state, license_expiry,
          specialization, experience_years, bio,
          hourly_rate, education, certifications,
          availability, session_formats, profile_photo, credential_document,
          verified, verification_status, email))

    conn.commit()
    conn.close()

    if is_verified:
        return jsonify({"message": "Therapist profile updated"})

    return jsonify({"message": "Credentials submitted for verification"})

# Get therapist profile (public)
@app.route('/get_therapist_profile', methods=['POST'])
def get_therapist_profile():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT email, name, location, primary_language, secondary_language,
           license_number, license_state, license_expiry,
           specialization, experience_years, bio, hourly_rate,
           education, certifications, availability, session_formats,
           profile_photo, credential_document, verified,
           verification_status, rejection_reason
    FROM users WHERE email=? AND role='therapist'
    """, (email,))
    
    therapist = cursor.fetchone()
    conn.close()

    if therapist:
        profile = {
            "email": therapist[0],
            "name": therapist[1],
            "location": therapist[2],
            "primary_language": therapist[3],
            "secondary_language": therapist[4],
            "license_number": therapist[5],
            "license_state": therapist[6],
            "license_expiry": therapist[7],
            "specialization": therapist[8],
            "experience_years": therapist[9],
            "bio": therapist[10],
            "hourly_rate": therapist[11],
            "education": therapist[12],
            "certifications": therapist[13],
            "availability": therapist[14],
            "session_formats": therapist[15].split(',') if therapist[15] else [],
            "profile_photo": therapist[16],
            "credential_document": therapist[17],
            "verified": therapist[18],
            "verification_status": therapist[19] or ('verified' if therapist[18] else 'draft'),
            "rejection_reason": therapist[20]
        }
        return jsonify({"therapist": profile})

    return jsonify({"message": "Therapist not found"}), 404

# Admin verify therapist
@app.route('/verify_therapist', methods=['POST'])
def verify_therapist():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    verify = data.get('verify')  # 1 to verify, 0 to reject
    rejection_reason = data.get('rejection_reason') or 'Application needs more information.'

    conn = get_db_connection()
    cursor = conn.cursor()

    verification_status = 'verified' if verify else 'rejected'

    cursor.execute("""
    UPDATE users
    SET verified=?, verification_status=?, rejection_reason=?
    WHERE email=? AND role='therapist'
    """, (verify, verification_status, None if verify else rejection_reason, email))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"message": "Therapist not found"}), 404

    if verify:
        return jsonify({"message": "Therapist verified successfully"})

    return jsonify({"message": "Therapist verification rejected"})

# Get all unverified therapists (for admin)
@app.route('/get_unverified_therapists', methods=['GET'])
def get_unverified_therapists():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT email, name, location, primary_language, secondary_language,
           license_number, license_state, license_expiry,
           specialization, experience_years, bio, hourly_rate,
           education, certifications, availability, session_formats,
           profile_photo, credential_document, verification_status
    FROM users
    WHERE role='therapist' AND verified=0
      AND license_number IS NOT NULL AND license_number != ''
      AND COALESCE(verification_status, 'pending') = 'pending'
    """)
    
    therapists = cursor.fetchall()
    conn.close()

    therapist_list = []
    for t in therapists:
        therapist_list.append({
            "email": t[0],
            "name": t[1],
            "location": t[2],
            "primary_language": t[3],
            "secondary_language": t[4],
            "license_number": t[5],
            "license_state": t[6],
            "license_expiry": t[7],
            "specialization": t[8],
            "experience_years": t[9],
            "bio": t[10],
            "hourly_rate": t[11],
            "education": t[12],
            "certifications": t[13],
            "availability": t[14],
            "session_formats": t[15].split(',') if t[15] else [],
            "profile_photo": t[16],
            "credential_document": t[17],
            "verification_status": t[18]
        })

    return jsonify({"therapists": therapist_list})

@app.route('/pay', methods=['POST'])
def pay():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    amount = data.get('amount', 500000)
    reference = data.get('reference') or f"manual_{uuid4().hex[:12]}"

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid payment email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payments (user_email, amount, currency, provider, reference, status, created_at, verified_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (email, amount, data.get('currency', 'NGN'), data.get('provider', 'manual'), reference, 'recorded', now_iso(), now_iso()))

    conn.commit()
    conn.close()

    return jsonify({"message": "Payment recorded", "reference": reference})

import requests

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json() or {}
    reference = data.get('reference')
    email = normalize_email(data.get('email'))
    amount = data.get('amount', 500000)

    if not reference:
        return jsonify({"message": "Missing payment reference"}), 400

    if email and not is_valid_email(email):
        return jsonify({"message": "Please enter a valid payment email"}), 400

    paystack_secret_key = os.environ.get('PAYSTACK_SECRET_KEY', '').strip()
    if not paystack_secret_key:
        return jsonify({
            "message": "Paystack secret key is not configured",
            "status": "configuration_error"
        }), 500

    url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {
        "Authorization": f"Bearer {paystack_secret_key}"
    }

    status = 'pending_verification'
    message = 'Payment recorded for admin review'

    try:
        response = requests.get(url, headers=headers, timeout=10)
        result = response.json()
        paystack_data = result.get('data', {})

        if paystack_data.get('status') == "success":
            status = 'verified'
            message = 'Payment verified'
            email = email or normalize_email(paystack_data.get('customer', {}).get('email'))
            amount = paystack_data.get('amount', amount)
        else:
            status = 'failed'
            message = 'Payment failed'
    except requests.RequestException:
        status = 'pending_verification'

    conn = get_db_connection()
    cursor = conn.cursor()
    email = email if is_valid_email(email) else None
    cursor.execute("SELECT id FROM payments WHERE reference=?", (reference,))
    existing_payment = cursor.fetchone()

    if existing_payment:
        cursor.execute("""
        UPDATE payments
        SET user_email=COALESCE(?, user_email),
            amount=COALESCE(?, amount),
            status=?,
            verified_at=?
        WHERE reference=?
        """, (email, amount, status, now_iso(), reference))
    else:
        cursor.execute("""
        INSERT INTO payments (user_email, amount, currency, provider, reference, status, created_at, verified_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (email, amount, data.get('currency', 'NGN'), 'paystack', reference, status, now_iso(), now_iso()))

    conn.commit()
    conn.close()

    response_status = 200 if status in ('verified', 'pending_verification') else 400
    return jsonify({"message": message, "status": status}), response_status


@app.route('/get_payments', methods=['GET'])
def get_payments():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    search = (request.args.get('search') or '').strip()
    include_archived = request.args.get('include_archived') == '1' or bool(search)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT p.user_email, p.amount, p.currency, p.provider, p.reference,
           p.status, p.created_at, p.verified_at, COALESCE(u.role, 'user'),
           COALESCE(p.archived, 0), p.archived_at
    FROM payments p
    LEFT JOIN users u ON p.user_email = u.email
    """
    filters = []
    params = []

    if not include_archived:
        filters.append("COALESCE(p.archived, 0)=0")

    if search:
        filters.append("""
        (
            p.user_email LIKE ?
            OR p.reference LIKE ?
            OR p.provider LIKE ?
            OR p.status LIKE ?
            OR COALESCE(u.role, 'user') LIKE ?
        )
        """)
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term, search_term])

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY p.id DESC"
    cursor.execute(query, params)
    payments = cursor.fetchall()
    conn.close()

    return jsonify({
        "payments": [
            {
                "user_email": payment[0],
                "amount": payment[1],
                "currency": payment[2],
                "provider": payment[3],
                "reference": payment[4],
                "status": payment[5],
                "created_at": payment[6],
                "verified_at": payment[7],
                "payer_role": payment[8],
                "archived": bool(payment[9]),
                "archived_at": payment[10]
            }
            for payment in payments
        ]
    })


@app.route('/archive_payment', methods=['POST'])
def archive_payment():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    reference = (data.get('reference') or '').strip()
    archived = 1 if data.get('archived', True) else 0

    if not reference:
        return jsonify({"message": "Missing payment reference"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE payments
    SET archived=?, archived_at=?
    WHERE reference=?
    """, (archived, now_iso() if archived else None, reference))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"message": "Payment not found"}), 404

    return jsonify({"message": "Payment removed from the dashboard. You can still find it with search."})


@app.route('/customer_care', methods=['POST'])
def customer_care():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    role = data.get('role', 'user')
    message = data.get('message', '').strip()

    if not is_valid_email(email) or not message:
        return jsonify({"message": "Please enter a customer care message"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO customer_care (sender_email, sender_role, message, admin_reply, status, created_at, replied_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (email, role, message, None, 'open', now_iso(), None))

    conn.commit()
    conn.close()

    return jsonify({"message": "Customer care message sent"})


@app.route('/get_customer_care', methods=['POST'])
def get_customer_care():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get('email'))

    if not email:
        auth_error = require_admin()
        if auth_error:
            return auth_error

    conn = get_db_connection()
    cursor = conn.cursor()

    if email:
        cursor.execute("""
        SELECT id, sender_email, sender_role, message, admin_reply, status, created_at, replied_at
        FROM customer_care
        WHERE sender_email=?
        ORDER BY id DESC
        """, (email,))
    else:
        cursor.execute("""
        SELECT id, sender_email, sender_role, message, admin_reply, status, created_at, replied_at
        FROM customer_care
        ORDER BY id DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "messages": [
            {
                "id": row[0],
                "sender_email": row[1],
                "sender_role": row[2],
                "message": row[3],
                "admin_reply": row[4],
                "status": row[5],
                "created_at": row[6],
                "replied_at": row[7]
            }
            for row in rows
        ]
    })


@app.route('/reply_customer_care', methods=['POST'])
def reply_customer_care():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    message_id = data.get('id')
    reply = data.get('reply', '').strip()

    if not message_id or not reply:
        return jsonify({"message": "Missing reply details"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE customer_care
    SET admin_reply=?, status='answered', replied_at=?
    WHERE id=?
    """, (reply, now_iso(), message_id))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"message": "Customer care message not found"}), 404

    return jsonify({"message": "Reply sent"})

from flask_socketio import SocketIO, send

socketio = SocketIO(app, cors_allowed_origins=CORS_ALLOWED_ORIGINS)

@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)


@app.route('/unverified', methods=['GET'])
def unverified():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM users WHERE role='therapist' AND verified=0")
    therapists = cursor.fetchall()

    conn.close()

    return jsonify({"therapists": therapists})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/profile.html')
def profile():
    return send_from_directory(app.root_path, 'profile.html')

@app.route('/')
def home():
    return send_from_directory(app.root_path, 'index.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"})


@app.route('/dashboard.html')
def dashboard():
    return send_from_directory(app.root_path, 'dashboard.html')

@app.route('/settings.html')
def settings():
    return send_from_directory(app.root_path, 'settings.html')

@app.route('/admin.html')
def admin():
    return send_from_directory(app.root_path, 'admin.html')

@app.route('/therapist.html')
def therapist():
    return send_from_directory(app.root_path, 'therapist.html')

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG') == '1'
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )
