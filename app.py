import sqlite3
import json
import re
import secrets
import time
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
import requests

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER UNIQUE,
        user_email TEXT,
        therapist_email TEXT,
        amount INTEGER,
        currency TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS therapist_payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_payment_id INTEGER UNIQUE,
        booking_id INTEGER,
        therapist_email TEXT,
        amount INTEGER,
        currency TEXT,
        recipient_code TEXT,
        reference TEXT UNIQUE,
        status TEXT,
        transfer_code TEXT,
        provider_response TEXT,
        created_at TEXT,
        updated_at TEXT
    )
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
    if "online_status" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN online_status TEXT DEFAULT 'offline'")
    if "manual_availability" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN manual_availability INTEGER DEFAULT 0")
    if "created_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
    if "last_login_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    if "last_seen_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT")
    if "payout_bank_code" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_bank_code TEXT")
    if "payout_bank_name" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_bank_name TEXT")
    if "payout_account_number" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_account_number TEXT")
    if "payout_account_name" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_account_name TEXT")
    if "payout_recipient_code" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_recipient_code TEXT")
    if "payout_verified_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_verified_at TEXT")
    if "payout_updated_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN payout_updated_at TEXT")
    if "email_verified" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 1")
    if "email_verification_token" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token TEXT")
    if "email_verification_code" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verification_code TEXT")
    if "email_verification_expires_at" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verification_expires_at TEXT")

    migration_now = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    cursor.execute("""
    UPDATE users
    SET created_at=COALESCE(created_at, ?)
    WHERE created_at IS NULL OR created_at=''
    """, (migration_now,))

    cursor.execute("PRAGMA table_info(bookings)")
    existing_booking_columns = [row[1] for row in cursor.fetchall()]
    if "client_needs" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN client_needs TEXT")
    if "meet_link" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN meet_link TEXT")
    if "booking_group_id" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN booking_group_id TEXT")
    if "sequence_number" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN sequence_number INTEGER DEFAULT 1")
    if "total_sessions" not in existing_booking_columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN total_sessions INTEGER DEFAULT 1")

    cursor.execute("""
    UPDATE bookings
    SET booking_group_id='booking-' || id
    WHERE booking_group_id IS NULL OR booking_group_id=''
    """)
    cursor.execute("""
    UPDATE bookings
    SET sequence_number=COALESCE(sequence_number, 1),
        total_sessions=COALESCE(total_sessions, 1)
    """)

    cursor.execute("PRAGMA table_info(messages)")
    existing_message_columns = [row[1] for row in cursor.fetchall()]
    if "booking_id" not in existing_message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN booking_id INTEGER")
    if "created_at" not in existing_message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")

    cursor.execute("PRAGMA table_info(payments)")
    existing_payment_columns = [row[1] for row in cursor.fetchall()]
    if "archived" not in existing_payment_columns:
        cursor.execute("ALTER TABLE payments ADD COLUMN archived INTEGER DEFAULT 0")
    if "archived_at" not in existing_payment_columns:
        cursor.execute("ALTER TABLE payments ADD COLUMN archived_at TEXT")

    cursor.execute("PRAGMA table_info(session_payments)")
    existing_session_payment_columns = [row[1] for row in cursor.fetchall()]
    if "started_at" not in existing_session_payment_columns:
        cursor.execute("ALTER TABLE session_payments ADD COLUMN started_at TEXT")
    if "ends_at" not in existing_session_payment_columns:
        cursor.execute("ALTER TABLE session_payments ADD COLUMN ends_at TEXT")
    if "duration_minutes" not in existing_session_payment_columns:
        cursor.execute("ALTER TABLE session_payments ADD COLUMN duration_minutes INTEGER")

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_session_payments_booking
    ON session_payments(booking_id)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_payments_user_status
    ON payments(user_email, status)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bookings_user_therapist_status
    ON bookings(user_email, therapist_email, status)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_bookings_group
    ON bookings(booking_group_id, sequence_number)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_messages_booking
    ON messages(booking_id, id)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_therapist_payouts_therapist_status
    ON therapist_payouts(therapist_email, status)
    """)

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

app = Flask(__name__, static_folder=None)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
CORS_ALLOWED_ORIGINS = parse_allowed_origins()
if CORS_ALLOWED_ORIGINS:
    CORS(app, origins=CORS_ALLOWED_ORIGINS)

ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
PASSWORD_HASH_PREFIXES = ('scrypt:', 'pbkdf2:', 'argon2:')
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def env_int(name, default):
    try:
        return int(os.environ.get(name, default) or default)
    except (TypeError, ValueError):
        return default


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


SESSION_HOURS = env_int('SESSION_HOURS', 12)
MAX_LOGIN_ATTEMPTS = env_int('MAX_LOGIN_ATTEMPTS', 5)
LOGIN_LOCK_SECONDS = env_int('LOGIN_LOCK_SECONDS', 5 * 60)
LOGIN_ATTEMPTS = {}
MAX_AUTH_ATTEMPTS_PER_IP = env_int('MAX_AUTH_ATTEMPTS_PER_IP', 30)
AUTH_IP_WINDOW_SECONDS = env_int('AUTH_IP_WINDOW_SECONDS', 60 * 60)
AUTH_IP_ATTEMPTS = {}
MAX_SIGNUP_ATTEMPTS_PER_EMAIL = env_int('MAX_SIGNUP_ATTEMPTS_PER_EMAIL', 8)
SIGNUP_WINDOW_SECONDS = env_int('SIGNUP_WINDOW_SECONDS', 60 * 60)
SIGNUP_ATTEMPTS = {}
EMAIL_VERIFICATION_HOURS = env_int('EMAIL_VERIFICATION_HOURS', 24)
EMAIL_VERIFICATION_REQUIRED = (
    env_flag('EMAIL_VERIFICATION_REQUIRED', False)
    or env_flag('REQUIRE_EMAIL_VERIFICATION', False)
)
ADMIN_ENTRY_PATH = '/admin'
ADMIN_CONSOLE_PATH = '/tm-console-7f3a9c'
LEGACY_ADMIN_ENTRY_PATH = '/tm-gate-7f3a9c'
LEGACY_ADMIN_CONSOLE_PATH = '/admin/console'
PUBLIC_FILES = {
    'index.html',
    'dashboard.html',
    'settings.html',
    'profile.html',
    'match.html',
    'chat.html',
    'therapist.html',
    'styles.css',
    'script.js',
    'dashboard.js',
    'settings.js',
    'profile.js',
    'match.js',
    'chat.js',
    'therapist.js',
    'support.js',
    'mobile-nav.js',
    'admin-login.js',
    'admin.js',
    'logo.png',
}
SESSION_PRICE_KOBO = 1100000
DEFAULT_TOP_UP_KOBO = 500000
MAX_CONSECUTIVE_SESSIONS = 8
WALLET_CREDITED_PAYMENT_STATUSES = ('recorded', 'verified', 'success', 'paid')
WALLET_PENDING_PAYMENT_STATUSES = ('pending_verification',)
SESSION_PAYMENT_STATUSES = ('paid',)
PAYSTACK_API_BASE = "https://api.paystack.co"
PAYSTACK_PUBLIC_KEY_FALLBACK = "pk_test_1fab358fb60e7c6d5fd6898d94c29be6e314cde8"
PAYOUT_RETRY_STATUSES = ('missing_recipient', 'pending_configuration', 'failed')
FALLBACK_NIGERIAN_BANKS = [
    {"name": "Access Bank", "code": "044"},
    {"name": "Citibank Nigeria", "code": "023"},
    {"name": "Ecobank Nigeria", "code": "050"},
    {"name": "Fidelity Bank", "code": "070"},
    {"name": "First Bank of Nigeria", "code": "011"},
    {"name": "First City Monument Bank", "code": "214"},
    {"name": "Guaranty Trust Bank", "code": "058"},
    {"name": "Keystone Bank", "code": "082"},
    {"name": "Kuda Bank", "code": "50211"},
    {"name": "Opay", "code": "999992"},
    {"name": "Polaris Bank", "code": "076"},
    {"name": "Stanbic IBTC Bank", "code": "221"},
    {"name": "Sterling Bank", "code": "232"},
    {"name": "Union Bank of Nigeria", "code": "032"},
    {"name": "United Bank For Africa", "code": "033"},
    {"name": "Wema Bank", "code": "035"},
    {"name": "Zenith Bank", "code": "057"}
]


def now_iso():
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def future_iso(hours):
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat(timespec='seconds') + 'Z'


def normalize_email(email):
    return str(email or '').strip().lower()


def is_valid_email(email):
    return bool(EMAIL_PATTERN.fullmatch(normalize_email(email)))


def get_request_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def prune_attempts(store, key, window_seconds):
    now = time.time()
    attempts = [
        attempt
        for attempt in store.get(key, [])
        if now - attempt < window_seconds
    ]

    if attempts:
        store[key] = attempts
    else:
        store.pop(key, None)

    return attempts


def is_auth_ip_limited():
    attempts = prune_attempts(AUTH_IP_ATTEMPTS, get_request_ip(), AUTH_IP_WINDOW_SECONDS)
    return len(attempts) >= MAX_AUTH_ATTEMPTS_PER_IP


def record_auth_ip_attempt():
    key = get_request_ip()
    attempts = prune_attempts(AUTH_IP_ATTEMPTS, key, AUTH_IP_WINDOW_SECONDS)
    attempts.append(time.time())
    AUTH_IP_ATTEMPTS[key] = attempts


def is_signup_limited(email):
    email_attempts = prune_attempts(
        SIGNUP_ATTEMPTS,
        f"email:{normalize_email(email)}",
        SIGNUP_WINDOW_SECONDS
    )
    return len(email_attempts) >= MAX_SIGNUP_ATTEMPTS_PER_EMAIL


def record_signup_attempt(email):
    if not email:
        return

    key = f"email:{normalize_email(email)}"
    attempts = prune_attempts(SIGNUP_ATTEMPTS, key, SIGNUP_WINDOW_SECONDS)
    attempts.append(time.time())
    SIGNUP_ATTEMPTS[key] = attempts


def smtp_configured():
    return bool(os.environ.get('SMTP_HOST', '').strip() and os.environ.get('SMTP_FROM_EMAIL', '').strip())


def email_verification_enabled():
    return EMAIL_VERIFICATION_REQUIRED and smtp_configured()


def role_requires_email_verification(role):
    return role in ('user', 'therapist') and email_verification_enabled()


def generate_email_verification():
    return {
        "token": secrets.token_urlsafe(32),
        "code": f"{secrets.randbelow(1000000):06d}",
        "expires_at": future_iso(EMAIL_VERIFICATION_HOURS)
    }


def verification_link(token):
    base_url = os.environ.get('APP_BASE_URL', '').strip().rstrip('/')
    if not base_url:
        base_url = request.url_root.rstrip('/')
    return f"{base_url}/verify_email?token={token}"


def send_email(to_email, subject, body):
    smtp_host = os.environ.get('SMTP_HOST', '').strip()
    from_email = os.environ.get('SMTP_FROM_EMAIL', '').strip()
    if not smtp_host or not from_email:
        return False, "SMTP email is not configured"

    smtp_port = int(os.environ.get('SMTP_PORT', '587') or 587)
    smtp_username = os.environ.get('SMTP_USERNAME', '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD', '').strip()
    use_ssl = os.environ.get('SMTP_USE_SSL', '').strip() == '1'
    from_name = os.environ.get('SMTP_FROM_NAME', 'TherapistMatch').strip() or 'TherapistMatch'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = f"{from_name} <{from_email}>"
    message['To'] = to_email
    message.set_content(body)

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10) as server:
                if smtp_username or smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                if smtp_username or smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        return False, str(error)

    return True, ""


def send_verification_email(email, token, code):
    link = verification_link(token)
    body = f"""Welcome to TherapistMatch.

Please verify your email before logging in:

{link}

Your verification code is: {code}

This verification expires in {EMAIL_VERIFICATION_HOURS} hours. If you did not create this account, you can ignore this email.
"""
    return send_email(email, "Verify your TherapistMatch email", body)


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


def booking_duration_from_availability(availability_value):
    return parse_availability_value(availability_value)["duration"] or 60


def therapist_accepts_requested_time(availability_value, manual_availability, online_status, requested_start):
    duration = booking_duration_from_availability(availability_value)

    if manual_availability or online_status == "online":
        return True, duration

    return requested_time_is_available(availability_value, requested_start)


def therapist_has_booking_conflict(cursor, therapist_email, requested_start, duration, exclude_booking_id=None):
    query = """
    SELECT id, date FROM bookings
    WHERE therapist_email=?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """
    params = [therapist_email]

    if exclude_booking_id:
        query += " AND id != ?"
        params.append(exclude_booking_id)

    cursor.execute(query, params)
    for booking_id, existing_date in cursor.fetchall():
        if existing_booking_conflicts(existing_date, requested_start, duration):
            return True, booking_id

    return False, None


def find_duplicate_booking_ids(cursor, user_email=None, therapist_email=None):
    query = """
    SELECT b.id, b.user_email, b.therapist_email, b.date, COALESCE(b.status, 'Pending'), u.availability
    FROM bookings b
    LEFT JOIN users u ON u.email = b.therapist_email
    WHERE COALESCE(b.status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """
    params = []

    if user_email:
        query += " AND b.user_email=?"
        params.append(user_email)

    if therapist_email:
        query += " AND b.therapist_email=?"
        params.append(therapist_email)

    query += " ORDER BY b.user_email, b.therapist_email, b.id ASC"
    cursor.execute(query, params)

    grouped = {}
    for row in cursor.fetchall():
        grouped.setdefault((row[1], row[2]), []).append({
            "id": row[0],
            "date": row[3],
            "status": row[4],
            "availability": row[5],
            "start": parse_booking_datetime(row[3])
        })

    duplicate_ids = []
    for rows in grouped.values():
        kept = []
        rows.sort(key=lambda item: (
            0 if item["status"] == "Accepted" else 1,
            item["start"] or datetime.max,
            item["id"]
        ))

        for row in rows:
            duration = booking_duration_from_availability(row["availability"])
            if not row["start"]:
                exact_duplicate = any(existing["date"] == row["date"] for existing in kept)
                if exact_duplicate:
                    duplicate_ids.append(row["id"])
                else:
                    kept.append(row)
                continue

            overlaps_kept_booking = any(
                existing_booking_conflicts(existing["date"], row["start"], duration)
                for existing in kept
            )

            if overlaps_kept_booking:
                duplicate_ids.append(row["id"])
            else:
                kept.append(row)

    return duplicate_ids


def cancel_duplicate_bookings(cursor, user_email=None, therapist_email=None):
    duplicate_ids = find_duplicate_booking_ids(
        cursor,
        user_email=user_email,
        therapist_email=therapist_email
    )

    if not duplicate_ids:
        return 0

    placeholders = ",".join("?" for _ in duplicate_ids)
    cursor.execute(f"""
    UPDATE bookings
    SET status='Cancelled'
    WHERE id IN ({placeholders})
    """, duplicate_ids)

    return cursor.rowcount


def normalize_amount_kobo(value, default_amount=DEFAULT_TOP_UP_KOBO):
    try:
        amount = int(value)
    except (TypeError, ValueError):
        amount = default_amount

    return max(amount, 0)


def sum_payments_by_status(cursor, email, statuses):
    email = normalize_email(email)
    if not is_valid_email(email) or not statuses:
        return 0

    placeholders = ",".join("?" for _ in statuses)
    cursor.execute(f"""
    SELECT COALESCE(SUM(COALESCE(amount, 0)), 0)
    FROM payments
    WHERE user_email=?
      AND LOWER(COALESCE(status, '')) IN ({placeholders})
    """, (email, *statuses))

    return int(cursor.fetchone()[0] or 0)


def session_debit_total(cursor, email):
    email = normalize_email(email)
    if not is_valid_email(email):
        return 0

    placeholders = ",".join("?" for _ in SESSION_PAYMENT_STATUSES)
    cursor.execute(f"""
    SELECT COALESCE(SUM(COALESCE(amount, 0)), 0)
    FROM session_payments
    WHERE user_email=?
      AND LOWER(COALESCE(status, '')) IN ({placeholders})
    """, (email, *SESSION_PAYMENT_STATUSES))

    return int(cursor.fetchone()[0] or 0)


def wallet_summary_for_user(cursor, email):
    credited = sum_payments_by_status(cursor, email, WALLET_CREDITED_PAYMENT_STATUSES)
    pending = sum_payments_by_status(cursor, email, WALLET_PENDING_PAYMENT_STATUSES)
    debited = session_debit_total(cursor, email)
    balance = max(credited - debited, 0)

    return {
        "balance": balance,
        "pending_balance": pending,
        "credited_total": credited,
        "debited_total": debited,
        "session_price": SESSION_PRICE_KOBO,
        "shortage": max(SESSION_PRICE_KOBO - balance, 0)
    }


def booking_has_session_payment(cursor, booking_id):
    if not booking_id:
        return False

    placeholders = ",".join("?" for _ in SESSION_PAYMENT_STATUSES)
    cursor.execute(f"""
    SELECT id FROM session_payments
    WHERE booking_id=?
      AND LOWER(COALESCE(status, '')) IN ({placeholders})
    LIMIT 1
    """, (booking_id, *SESSION_PAYMENT_STATUSES))

    return cursor.fetchone() is not None


def user_has_confirmed_payment(cursor, email):
    email = normalize_email(email)
    if not is_valid_email(email):
        return False

    return wallet_summary_for_user(cursor, email)["balance"] >= SESSION_PRICE_KOBO


def get_user_roles(cursor, *emails):
    normalized_emails = [normalize_email(email) for email in emails if is_valid_email(email)]
    if not normalized_emails:
        return {}

    placeholders = ",".join("?" for _ in normalized_emails)
    cursor.execute(f"""
    SELECT email, role FROM users
    WHERE email IN ({placeholders})
    """, normalized_emails)

    return {normalize_email(row[0]): row[1] for row in cursor.fetchall()}


def get_accepted_booking_between(cursor, user_email, therapist_email, booking_id=None):
    query = """
    SELECT id, date, meet_link
    FROM bookings
    WHERE user_email=? AND therapist_email=?
      AND COALESCE(status, 'Pending')='Accepted'
    """
    params = [user_email, therapist_email]

    if booking_id:
        query += " AND id=?"
        params.append(booking_id)

    query += " ORDER BY id DESC LIMIT 1"
    cursor.execute(query, params)

    return cursor.fetchone()


def get_chat_access(cursor, sender_email, receiver_email, booking_id=None):
    sender_email = normalize_email(sender_email)
    receiver_email = normalize_email(receiver_email)

    if (
        not is_valid_email(sender_email)
        or not is_valid_email(receiver_email)
        or sender_email == receiver_email
    ):
        return {
            "allowed": False,
            "status": 400,
            "message": "Please use valid account emails"
        }

    booking = get_accepted_booking_between(cursor, sender_email, receiver_email, booking_id)
    if booking:
        user_email = sender_email
        therapist_email = receiver_email
    else:
        booking = get_accepted_booking_between(cursor, receiver_email, sender_email, booking_id)
        user_email = receiver_email
        therapist_email = sender_email

    if not booking:
        roles = get_user_roles(cursor, sender_email, receiver_email)
        role_values = {roles.get(sender_email), roles.get(receiver_email)}
        if None not in role_values and role_values != {'user', 'therapist'}:
            return {
                "allowed": False,
                "status": 403,
                "message": "Chat is only available between clients and therapists"
            }

        return {
            "allowed": False,
            "status": 403,
            "message": "Chat opens after the therapist accepts a booking"
        }

    if not booking_has_session_payment(cursor, booking[0]):
        return {
            "allowed": False,
            "status": 402,
            "message": "Pay for this session before chat or Google Meet can start"
        }

    return {
        "allowed": True,
        "user_email": user_email,
        "therapist_email": therapist_email,
        "booking": booking
    }


def is_google_meet_link(value):
    link = (value or '').strip()
    return not link or link.startswith('https://meet.google.com/')


def normalize_needs(value):
    if isinstance(value, list):
        needs = [str(item).strip() for item in value if str(item).strip()]
    else:
        needs = [item.strip() for item in str(value or "").split(",") if item.strip()]

    return ",".join(needs[:4])


def parse_session_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 1

    return min(max(count, 1), MAX_CONSECUTIVE_SESSIONS)


def get_consecutive_session_starts(requested_start, duration, session_count):
    return [
        requested_start + timedelta(minutes=duration * index)
        for index in range(session_count)
    ]


def is_active_booking_status(status):
    return (status or 'Pending') not in ('Cancelled', 'Rejected')


def normalize_account_number(value):
    return re.sub(r"\D", "", str(value or ""))


def mask_account_number(value):
    account_number = normalize_account_number(value)
    if len(account_number) <= 4:
        return account_number

    return f"{'*' * (len(account_number) - 4)}{account_number[-4:]}"


def paystack_secret_key():
    return os.environ.get('PAYSTACK_SECRET_KEY', '').strip()


def paystack_headers():
    secret_key = paystack_secret_key()
    if not secret_key:
        return None

    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }


def paystack_request(method, path, **kwargs):
    headers = paystack_headers()
    if not headers:
        return False, {"message": "Paystack secret key is not configured"}, 503

    try:
        response = requests.request(
            method,
            f"{PAYSTACK_API_BASE}{path}",
            headers=headers,
            timeout=15,
            **kwargs
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text or "Paystack returned an unreadable response"}

        return response.ok and payload.get("status") is True, payload, response.status_code
    except requests.RequestException:
        return False, {"message": "Paystack is unreachable right now. The request can be retried later."}, 503


def paystack_message(payload, fallback="Paystack could not complete this request"):
    if isinstance(payload, dict):
        return payload.get("message") or fallback
    return fallback


def fetch_paystack_banks():
    ok, payload, _ = paystack_request("GET", "/bank", params={
        "country": "nigeria",
        "currency": "NGN"
    })

    if ok:
        banks = [
            {
                "name": bank.get("name"),
                "code": str(bank.get("code") or "")
            }
            for bank in payload.get("data", [])
            if bank.get("name") and bank.get("code")
        ]
        if banks:
            return sorted(banks, key=lambda bank: bank["name"]), True

    return FALLBACK_NIGERIAN_BANKS, False


def resolve_paystack_account(account_number, bank_code):
    ok, payload, status_code = paystack_request("GET", "/bank/resolve", params={
        "account_number": account_number,
        "bank_code": bank_code
    })

    if not ok:
        return {
            "ok": False,
            "status_code": status_code,
            "message": paystack_message(payload, "Account could not be verified")
        }

    account_data = payload.get("data") or {}
    return {
        "ok": True,
        "account_name": account_data.get("account_name") or "",
        "account_number": account_data.get("account_number") or account_number
    }


def create_paystack_recipient(account_name, account_number, bank_code):
    ok, payload, status_code = paystack_request("POST", "/transferrecipient", json={
        "type": "nuban",
        "name": account_name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    })

    if not ok:
        return {
            "ok": False,
            "status_code": status_code,
            "message": paystack_message(payload, "Transfer recipient could not be created")
        }

    recipient_data = payload.get("data") or {}
    return {
        "ok": True,
        "recipient_code": recipient_data.get("recipient_code") or "",
        "account_name": recipient_data.get("details", {}).get("account_name") or account_name
    }


def initiate_paystack_transfer(amount, recipient_code, reason, reference):
    ok, payload, status_code = paystack_request("POST", "/transfer", json={
        "source": "balance",
        "amount": amount,
        "recipient": recipient_code,
        "reason": reason,
        "reference": reference
    })

    transfer_data = payload.get("data") if isinstance(payload, dict) else {}
    return {
        "ok": ok,
        "status_code": status_code,
        "status": (transfer_data or {}).get("status") or ("pending" if ok else "failed"),
        "transfer_code": (transfer_data or {}).get("transfer_code"),
        "message": paystack_message(payload, "Transfer request recorded"),
        "payload": payload
    }


def get_booking_group_meta(cursor, group_ids):
    normalized_group_ids = [group_id for group_id in set(group_ids) if group_id]
    if not normalized_group_ids:
        return {}

    placeholders = ",".join("?" for _ in normalized_group_ids)
    cursor.execute(f"""
    SELECT id, booking_group_id, COALESCE(status, 'Pending'), date
    FROM bookings
    WHERE booking_group_id IN ({placeholders})
    ORDER BY booking_group_id, date, id
    """, normalized_group_ids)

    grouped = {}
    for row in cursor.fetchall():
        grouped.setdefault(row[1], []).append({
            "id": row[0],
            "status": row[2],
            "date": row[3],
            "paid": booking_has_session_payment(cursor, row[0])
        })

    meta = {}
    for group_id, rows in grouped.items():
        active_rows = [row for row in rows if is_active_booking_status(row["status"])]
        accepted_unpaid_ids = [
            row["id"]
            for row in active_rows
            if row["status"] == "Accepted" and not row["paid"]
        ]
        paid_count = sum(1 for row in active_rows if row["paid"])

        meta[group_id] = {
            "active_count": len(active_rows),
            "paid_count": paid_count,
            "unpaid_count": max(len(active_rows) - paid_count, 0),
            "accepted_unpaid_booking_ids": accepted_unpaid_ids,
            "accepted_unpaid_count": len(accepted_unpaid_ids),
            "accepted_unpaid_total": len(accepted_unpaid_ids) * SESSION_PRICE_KOBO
        }

    return meta


def session_timer_for_booking(cursor, booking_id):
    cursor.execute("""
    SELECT sp.started_at, sp.ends_at, sp.duration_minutes, sp.created_at, u.availability
    FROM session_payments sp
    JOIN bookings b ON b.id = sp.booking_id
    LEFT JOIN users u ON u.email = b.therapist_email AND u.role='therapist'
    WHERE sp.booking_id=?
      AND LOWER(COALESCE(sp.status, '')) IN ('paid')
    LIMIT 1
    """, (booking_id,))
    row = cursor.fetchone()

    if not row:
        return {
            "paid": False,
            "started": False,
            "duration_minutes": None,
            "started_at": None,
            "ends_at": None
        }

    duration = row[2] or booking_duration_from_availability(row[4])
    return {
        "paid": True,
        "started": bool(row[0]),
        "duration_minutes": duration,
        "started_at": row[0],
        "ends_at": row[1],
        "payment_created_at": row[3]
    }


def maybe_start_session_timer(cursor, booking_id):
    timer = session_timer_for_booking(cursor, booking_id)
    if not timer["paid"] or timer["started"]:
        return timer

    cursor.execute("""
    SELECT user_email, therapist_email
    FROM bookings
    WHERE id=?
    """, (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        return timer

    cursor.execute("""
    SELECT DISTINCT sender
    FROM messages
    WHERE booking_id=?
      AND sender IN (?, ?)
    """, (booking_id, booking[0], booking[1]))
    senders = {row[0] for row in cursor.fetchall()}

    if {booking[0], booking[1]}.issubset(senders):
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=timer["duration_minutes"] or 60)
        started_at = start_time.isoformat(timespec='seconds') + 'Z'
        ends_at = end_time.isoformat(timespec='seconds') + 'Z'
        cursor.execute("""
        UPDATE session_payments
        SET started_at=?,
            ends_at=?,
            duration_minutes=COALESCE(duration_minutes, ?)
        WHERE booking_id=?
          AND started_at IS NULL
        """, (started_at, ends_at, timer["duration_minutes"] or 60, booking_id))

        timer.update({
            "started": True,
            "started_at": started_at,
            "ends_at": ends_at
        })

    return timer


def upsert_payout_record(cursor, existing_id, values):
    if existing_id:
        cursor.execute("""
        UPDATE therapist_payouts
        SET amount=?,
            currency=?,
            recipient_code=?,
            reference=?,
            status=?,
            transfer_code=?,
            provider_response=?,
            updated_at=?
        WHERE id=?
        """, (
            values["amount"],
            values["currency"],
            values["recipient_code"],
            values["reference"],
            values["status"],
            values["transfer_code"],
            values["provider_response"],
            now_iso(),
            existing_id
        ))
        return

    cursor.execute("""
    INSERT INTO therapist_payouts (
        session_payment_id, booking_id, therapist_email, amount, currency,
        recipient_code, reference, status, transfer_code, provider_response,
        created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        values["session_payment_id"],
        values["booking_id"],
        values["therapist_email"],
        values["amount"],
        values["currency"],
        values["recipient_code"],
        values["reference"],
        values["status"],
        values["transfer_code"],
        values["provider_response"],
        now_iso(),
        now_iso()
    ))


def process_payouts_for_session_payments(session_payment_ids, retry=False):
    normalized_ids = []
    for payment_id in session_payment_ids:
        try:
            normalized_ids.append(int(payment_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    payouts = []

    placeholders = ",".join("?" for _ in normalized_ids)
    cursor.execute(f"""
    SELECT sp.id, sp.booking_id, sp.therapist_email, sp.amount, sp.currency,
           u.payout_recipient_code, u.payout_account_number, u.payout_bank_name
    FROM session_payments sp
    LEFT JOIN users u ON u.email = sp.therapist_email AND u.role='therapist'
    WHERE sp.id IN ({placeholders})
      AND LOWER(COALESCE(sp.status, ''))='paid'
    """, normalized_ids)

    rows = cursor.fetchall()
    for row in rows:
        cursor.execute("""
        SELECT id, status, reference
        FROM therapist_payouts
        WHERE session_payment_id=?
        """, (row[0],))
        existing = cursor.fetchone()

        if existing and (not retry or existing[1] not in PAYOUT_RETRY_STATUSES):
            payouts.append({
                "session_payment_id": row[0],
                "booking_id": row[1],
                "status": existing[1],
                "reference": existing[2]
            })
            continue

        reference = existing[2] if existing and existing[2] else f"payout_{row[1]}_{uuid4().hex[:10]}"
        recipient_code = row[5] or ""
        provider_response = {}
        transfer_code = None

        if not recipient_code:
            status = "missing_recipient"
            provider_response = {"message": "Therapist payout account is not ready yet"}
        elif not paystack_secret_key():
            status = "pending_configuration"
            provider_response = {"message": "Paystack secret key is not configured"}
        else:
            transfer = initiate_paystack_transfer(
                row[3],
                recipient_code,
                f"TherapistMatch session #{row[1]}",
                reference
            )
            status = transfer["status"]
            transfer_code = transfer["transfer_code"]
            provider_response = transfer["payload"]
            if not transfer["ok"] and status == "failed":
                provider_response = {"message": transfer["message"], "payload": transfer["payload"]}

        values = {
            "session_payment_id": row[0],
            "booking_id": row[1],
            "therapist_email": row[2],
            "amount": row[3],
            "currency": row[4] or "NGN",
            "recipient_code": recipient_code,
            "reference": reference,
            "status": status,
            "transfer_code": transfer_code,
            "provider_response": json.dumps(provider_response)
        }
        upsert_payout_record(cursor, existing[0] if existing else None, values)
        payouts.append({
            "session_payment_id": row[0],
            "booking_id": row[1],
            "status": status,
            "reference": reference
        })

    conn.commit()
    conn.close()
    return payouts


def process_pending_payouts_for_therapist(therapist_email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sp.id
    FROM session_payments sp
    LEFT JOIN therapist_payouts tp ON tp.session_payment_id = sp.id
    WHERE sp.therapist_email=?
      AND LOWER(COALESCE(sp.status, ''))='paid'
      AND (
        tp.id IS NULL
        OR tp.status IN ('missing_recipient', 'pending_configuration', 'failed')
      )
    """, (therapist_email,))
    payment_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    return process_payouts_for_session_payments(payment_ids, retry=True)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}

    email = normalize_email(data.get('email'))
    password = data.get('password')
    role = data.get('role')

    if is_auth_ip_limited():
        return jsonify({"message": "Too many signup or login attempts from this IP address. Please wait and try again later."}), 429

    record_auth_ip_attempt()

    if is_signup_limited(email):
        return jsonify({"message": "Too many signup attempts for this email. Please wait and try again later."}), 429

    if not email or not password or role not in ('user', 'therapist', 'admin'):
        record_signup_attempt(email)
        return jsonify({"message": "Please enter a valid email, password, and role"}), 400

    if not is_valid_email(email):
        record_signup_attempt(email)
        return jsonify({"message": "Please enter a valid email address"}), 400

    password_message = validate_password_strength(password)
    if password_message:
        record_signup_attempt(email)
        return jsonify({"message": password_message}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if role == 'admin':
        admin_signup_code = os.environ.get('ADMIN_SIGNUP_CODE', '').strip()
        submitted_admin_code = str(data.get('admin_code') or '').strip()
        cursor.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
        admin_exists = cursor.fetchone() is not None

        if admin_signup_code and submitted_admin_code != admin_signup_code:
            conn.close()
            record_signup_attempt(email)
            return jsonify({"message": "Admin signup code is required"}), 403

        if admin_exists and not admin_signup_code:
            conn.close()
            record_signup_attempt(email)
            return jsonify({"message": "Admin signup is locked. Ask the current admin to create access."}), 403

    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        record_signup_attempt(email)
        return jsonify({"message": "An account with this email already exists"}), 409

    verification_status = 'draft' if role == 'therapist' else 'verified'
    needs_email_verification = role_requires_email_verification(role)
    email_verification = generate_email_verification() if needs_email_verification else None
    email_verified = 0 if needs_email_verification else 1

    password_hash = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO users (
            email, password, role, verification_status, created_at, last_seen_at,
            email_verified, email_verification_token, email_verification_code,
            email_verification_expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            password_hash,
            role,
            verification_status,
            now_iso(),
            now_iso(),
            email_verified,
            email_verification["token"] if needs_email_verification else None,
            email_verification["code"] if needs_email_verification else None,
            email_verification["expires_at"] if needs_email_verification else None
        )
    )

    token = create_session(cursor, email, role) if email_verified else ""

    conn.commit()
    conn.close()

    email_sent = False
    if needs_email_verification:
        email_sent, _ = send_verification_email(
            email,
            email_verification["token"],
            email_verification["code"]
        )

    record_signup_attempt(email)
    if needs_email_verification:
        message = "Account created. Check your email to verify your account before logging in."
        if not email_sent:
            message = "Account created, but the verification email could not be sent. Ask the site owner to check email settings."
        return jsonify({
            "message": message,
            "role": role,
            "token": token,
            "email_verification_required": True,
            "email_sent": email_sent
        })

    return jsonify({"message": "Account created", "role": role, "token": token, "email_verification_required": False})


@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'GET':
        token = (request.args.get('token') or '').strip()
        if not token:
            return "<h1>Verification failed</h1><p>Missing verification token.</p>", 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT email FROM users
        WHERE email_verification_token=?
          AND COALESCE(email_verified, 0)=0
          AND email_verification_expires_at > ?
        LIMIT 1
        """, (token, now_iso()))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return "<h1>Verification failed</h1><p>This verification link is invalid or expired.</p>", 400

        cursor.execute("""
        UPDATE users
        SET email_verified=1,
            email_verification_token=NULL,
            email_verification_code=NULL,
            email_verification_expires_at=NULL
        WHERE email=?
        """, (row[0],))
        conn.commit()
        conn.close()

        return """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Email Verified - TherapistMatch</title>
          <link rel="stylesheet" href="/styles.css">
        </head>
        <body class="redirect-page">
          <main class="auth-container">
            <h2>Email verified</h2>
            <p>You can now log in to TherapistMatch.</p>
            <a href="/">Go to login</a>
          </main>
        </body>
        </html>
        """

    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    code = str(data.get('code') or '').strip()

    if not is_valid_email(email) or not re.fullmatch(r"\d{6}", code):
        return jsonify({"message": "Enter your email and 6-digit verification code"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id FROM users
    WHERE email=?
      AND email_verification_code=?
      AND COALESCE(email_verified, 0)=0
      AND email_verification_expires_at > ?
    LIMIT 1
    """, (email, code, now_iso()))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"message": "Verification code is invalid or expired"}), 400

    cursor.execute("""
    UPDATE users
    SET email_verified=1,
        email_verification_token=NULL,
        email_verification_code=NULL,
        email_verification_expires_at=NULL
    WHERE id=?
    """, (row[0],))
    conn.commit()
    conn.close()

    return jsonify({"message": "Email verified. You can now log in."})


@app.route('/resend_verification_email', methods=['POST'])
def resend_verification_email():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    if not is_valid_email(email):
        return jsonify({"message": "Enter a valid email address"}), 400

    if not email_verification_enabled():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, COALESCE(email_verified, 1) FROM users WHERE email=? LIMIT 1", (email,))
        row = cursor.fetchone()

        if row and not row[1]:
            cursor.execute("""
            UPDATE users
            SET email_verified=1,
                email_verification_token=NULL,
                email_verification_code=NULL,
                email_verification_expires_at=NULL
            WHERE id=?
            """, (row[0],))
            conn.commit()

        conn.close()
        return jsonify({"message": "Email verification is off right now. You can log in."})

    if is_signup_limited(email):
        return jsonify({"message": "Too many verification email requests. Please wait and try again later."}), 429

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, COALESCE(email_verified, 1), role
    FROM users
    WHERE email=?
    LIMIT 1
    """, (email,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        record_signup_attempt(email)
        return jsonify({"message": "If that account exists, a verification email will be sent."})

    if row[1]:
        conn.close()
        return jsonify({"message": "This email is already verified."})

    email_verification = generate_email_verification()
    cursor.execute("""
    UPDATE users
    SET email_verification_token=?,
        email_verification_code=?,
        email_verification_expires_at=?
    WHERE id=?
    """, (
        email_verification["token"],
        email_verification["code"],
        email_verification["expires_at"],
        row[0]
    ))
    conn.commit()
    conn.close()

    email_sent, _ = send_verification_email(
        email,
        email_verification["token"],
        email_verification["code"]
    )
    record_signup_attempt(email)

    if not email_sent:
        return jsonify({"message": "Email sending is not configured yet. Ask the site owner to enable verification email."}), 503

    return jsonify({"message": "Verification email sent. Please check your inbox."})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = normalize_email(data.get('email'))
    password = data.get('password')
    expected_role = data.get('role')

    if is_auth_ip_limited():
        return jsonify({"message": "Too many signup or login attempts from this IP address. Please wait and try again later."}), 429

    record_auth_ip_attempt()

    if not email or not password:
        return jsonify({"message": "Please enter email and password"}), 400

    if expected_role and expected_role not in ('user', 'therapist', 'admin'):
        return jsonify({"message": "Please use a valid login type"}), 400

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid email address"}), 400

    if is_login_limited(email):
        return jsonify({"message": "Too many login attempts. Please wait a few minutes and try again."}), 429

    conn = get_db_connection()
    cursor = conn.cursor()

    if expected_role:
        cursor.execute("""
        SELECT id, password, role, verified, verification_status, COALESCE(email_verified, 1)
        FROM users
        WHERE email=? AND role=?
        ORDER BY id DESC
        LIMIT 1
        """, (email, expected_role))
    else:
        cursor.execute("""
        SELECT id, password, role, verified, verification_status, COALESCE(email_verified, 1)
        FROM users
        WHERE email=?
        ORDER BY id DESC
        LIMIT 1
        """, (email,))
    user = cursor.fetchone()

    if user and password_matches(user[1], password):
        user_id = user[0]
        stored_password = user[1]
        role = user[2]
        verified = user[3]
        status = user[4] or ('verified' if verified else 'draft')
        email_verified = user[5]

        if expected_role and role != expected_role:
            conn.close()
            record_failed_login(email)
            return jsonify({"message": "Please use the correct login page for this account"}), 403

        if role in ('user', 'therapist') and not email_verified:
            if email_verification_enabled():
                conn.close()
                return jsonify({
                    "message": "Please verify your email before logging in.",
                    "email_verification_required": True
                }), 403

            cursor.execute("""
            UPDATE users
            SET email_verified=1,
                email_verification_token=NULL,
                email_verification_code=NULL,
                email_verification_expires_at=NULL
            WHERE id=?
            """, (user_id,))

        if not is_password_hash(stored_password):
            cursor.execute(
                "UPDATE users SET password=? WHERE id=?",
                (generate_password_hash(password), user_id)
            )

        cursor.execute(
            "UPDATE users SET last_login_at=?, last_seen_at=? WHERE id=?",
            (now_iso(), now_iso(), user_id)
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
    WHERE email=? AND role='user' AND COALESCE(email_verified, 1)=1
    """, (name, dob, gender, location, primary_language, secondary_language, specialties, email))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"message": "Please create and verify an account before updating your profile"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "Profile updated"})
    

@app.route('/get_profile', methods=['POST'])
def get_profile():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, dob, gender, location, primary_language, secondary_language, specialties
    FROM users
    WHERE email=? AND role='user'
    ORDER BY id DESC
    LIMIT 1
    """, (email,))
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
    preferred_datetime = data.get('preferred_datetime') or data.get('date') or ''
    preferred_start = parse_booking_datetime(preferred_datetime) if preferred_datetime else None
    raw_specializations = data.get('specializations') or data.get('specialization') or []
    if isinstance(raw_specializations, str):
        specializations = [raw_specializations] if raw_specializations else []
    else:
        specializations = [item for item in raw_specializations if item]

    if len(specializations) < 1 or len(specializations) > 4:
        return jsonify({"message": "Please select between 1 and 4 specialties"}), 400

    if preferred_datetime and not preferred_start:
        return jsonify({"message": "Please choose a valid appointment date and time"}), 400

    if preferred_start and preferred_start < datetime.now().replace(second=0, microsecond=0):
        return jsonify({"message": "Please choose a future appointment time"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT u.email, u.name, u.location, u.primary_language, u.secondary_language, u.specialization,
           u.experience_years, u.bio, u.hourly_rate, u.profile_photo, u.session_formats, u.availability,
           COALESCE(r.rating_average, 0), COALESCE(r.rating_count, 0), u.manual_availability, u.online_status
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

        manual_availability = therapist[14] or 0
        online_status = therapist[15] or "offline"

        if preferred_start:
            is_available, duration = therapist_accepts_requested_time(
                therapist[11],
                manual_availability,
                online_status,
                preferred_start
            )
            if not is_available:
                continue

            has_conflict, _ = therapist_has_booking_conflict(
                cursor,
                therapist[0],
                preferred_start,
                duration
            )
            if has_conflict:
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
            "rating_count": therapist[13],
            "manual_availability": manual_availability,
            "online_status": online_status,
            "matches_requested_time": bool(preferred_start)
        })

    conn.close()

    return jsonify({"therapists": therapists})


@app.route('/book', methods=['POST'])
def book():
    data = request.get_json() or {}
    user_email = normalize_email(data.get('user_email'))
    therapist_email = normalize_email(data.get('therapist_email'))
    date = data.get('date')
    requested_start = parse_booking_datetime(date)
    client_needs = normalize_needs(data.get('client_needs'))
    session_count = parse_session_count(data.get('session_count'))

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
    SELECT id, availability, manual_availability, online_status FROM users
    WHERE email=? AND role='therapist' AND verified=1
    """, (therapist_email,))
    therapist = cursor.fetchone()
    if not therapist:
        conn.close()
        return jsonify({"message": "This therapist is not available for booking right now"}), 404

    is_available, duration = therapist_accepts_requested_time(
        therapist[1],
        therapist[2] or 0,
        therapist[3] or "offline",
        requested_start
    )

    if not is_available:
        conn.close()
        return jsonify({"message": "This therapist is not available at that day or time. Please choose a time inside their listed availability."}), 400

    session_starts = get_consecutive_session_starts(requested_start, duration, session_count)
    for session_start in session_starts:
        is_available, _ = therapist_accepts_requested_time(
            therapist[1],
            therapist[2] or 0,
            therapist[3] or "offline",
            session_start
        )
        if not is_available:
            conn.close()
            return jsonify({
                "message": "That many sessions no longer fits the therapist's available time. Please choose fewer sessions or another start time.",
                "available_sessions": max(session_starts.index(session_start), 1)
            }), 400

    cursor.execute("""
    SELECT id, date
    FROM bookings
    WHERE user_email=? AND therapist_email=?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """, (user_email, therapist_email))
    for existing_id, existing_date in cursor.fetchall():
        if any(existing_booking_conflicts(existing_date, session_start, duration) for session_start in session_starts):
            conn.close()
            return jsonify({
                "message": f"You already have an active session request with this therapist for that time (booking #{existing_id}).",
                "status": "duplicate"
            }), 409

    for session_start in session_starts:
        has_conflict, _ = therapist_has_booking_conflict(cursor, therapist_email, session_start, duration)
        if has_conflict:
            conn.close()
            return jsonify({
                "message": "This therapist is available then, but one of those session times is already booked. Please choose another time or fewer sessions.",
                "status": "booked"
            }), 409

    booking_group_id = f"group_{uuid4().hex[:12]}"
    booking_ids = []
    for index, session_start in enumerate(session_starts, start=1):
        cursor.execute("""
        INSERT INTO bookings (
            user_email, therapist_email, date, status, client_needs,
            booking_group_id, sequence_number, total_sessions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_email,
            therapist_email,
            session_start.isoformat(timespec='minutes'),
            'Pending',
            client_needs,
            booking_group_id,
            index,
            session_count
        ))
        booking_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()

    session_word = "session request" if session_count == 1 else "session requests"
    return jsonify({
        "message": f"{session_count} {session_word} sent. Your profile has been shared with the therapist.",
        "booking_ids": booking_ids,
        "booking_group_id": booking_group_id,
        "session_count": session_count
    })


@app.route('/therapist_bookings', methods=['POST'])
def therapist_bookings():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid therapist email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    removed_duplicates = cancel_duplicate_bookings(cursor, therapist_email=email)
    if removed_duplicates:
        conn.commit()

    cursor.execute("""
    SELECT b.id, b.user_email, b.date, b.status,
           u.name, u.dob, u.gender, u.location,
           u.primary_language, u.secondary_language, u.specialties, b.client_needs,
           b.meet_link, b.booking_group_id, b.sequence_number, b.total_sessions
    FROM bookings b
    LEFT JOIN users u ON u.id = (
        SELECT ux.id FROM users ux
        WHERE ux.email = b.user_email AND ux.role='user'
        ORDER BY ux.id DESC
        LIMIT 1
    )
    WHERE b.therapist_email=?
      AND COALESCE(b.status, 'Pending') IN ('Pending', 'Accepted')
    ORDER BY b.id DESC
    """, (email,))

    rows = cursor.fetchall()
    paid_bookings = {
        row[0]: booking_has_session_payment(cursor, row[0])
        for row in rows
    }
    group_meta = get_booking_group_meta(cursor, [row[13] for row in rows])
    cursor.execute("""
    SELECT sp.booking_id, COALESCE(tp.status, 'pending')
    FROM session_payments sp
    LEFT JOIN therapist_payouts tp ON tp.session_payment_id = sp.id
    WHERE sp.therapist_email=?
    """, (email,))
    payout_statuses = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    return jsonify({
        "bookings": [
            {
                "id": row[0],
                "user_email": row[1],
                "date": row[2],
                "status": row[3],
                "paid": paid_bookings.get(row[0], False),
                "can_chat": row[3] == 'Accepted' and paid_bookings.get(row[0], False),
                "meet_link": row[12],
                "booking_group_id": row[13],
                "sequence_number": row[14] or 1,
                "total_sessions": row[15] or 1,
                "group_active_count": group_meta.get(row[13], {}).get("active_count", row[15] or 1),
                "group_paid_count": group_meta.get(row[13], {}).get("paid_count", 0),
                "payout_status": payout_statuses.get(row[0]),
                "session_price": SESSION_PRICE_KOBO,
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
    removed_duplicates = cancel_duplicate_bookings(cursor, user_email=email)
    if removed_duplicates:
        conn.commit()
    wallet_summary = wallet_summary_for_user(cursor, email)

    cursor.execute("""
    SELECT b.id, b.therapist_email, b.date, b.status, b.client_needs,
           u.name, u.specialization, u.profile_photo,
           tr.rating, tr.comment, b.meet_link,
           b.booking_group_id, b.sequence_number, b.total_sessions
    FROM bookings b
    LEFT JOIN users u ON u.id = (
        SELECT ux.id FROM users ux
        WHERE ux.email = b.therapist_email AND ux.role='therapist'
        ORDER BY ux.verified DESC, ux.id DESC
        LIMIT 1
    )
    LEFT JOIN therapist_reviews tr
      ON tr.therapist_email = b.therapist_email AND tr.user_email = b.user_email
    WHERE b.user_email=?
      AND COALESCE(b.status, 'Pending') != 'Cancelled'
    ORDER BY b.id DESC
    """, (email,))

    rows = cursor.fetchall()
    paid_bookings = {
        row[0]: booking_has_session_payment(cursor, row[0])
        for row in rows
    }
    group_meta = get_booking_group_meta(cursor, [row[11] for row in rows])
    conn.close()

    return jsonify({
        "bookings": [
            {
                "id": row[0],
                "therapist_email": row[1],
                "date": row[2],
                "status": row[3],
                "client_needs": row[4].split(',') if row[4] else [],
                "paid": paid_bookings.get(row[0], False),
                "can_chat": row[3] == 'Accepted' and paid_bookings.get(row[0], False),
                "meet_link": row[10] if row[3] == 'Accepted' and paid_bookings.get(row[0], False) else None,
                "booking_group_id": row[11],
                "sequence_number": row[12] or 1,
                "total_sessions": row[13] or 1,
                "group_active_count": group_meta.get(row[11], {}).get("active_count", row[13] or 1),
                "group_paid_count": group_meta.get(row[11], {}).get("paid_count", 0),
                "group_unpaid_count": group_meta.get(row[11], {}).get("accepted_unpaid_count", 0),
                "group_unpaid_booking_ids": group_meta.get(row[11], {}).get("accepted_unpaid_booking_ids", []),
                "group_unpaid_total": group_meta.get(row[11], {}).get("accepted_unpaid_total", 0),
                "account_balance": wallet_summary["balance"],
                "pending_balance": wallet_summary["pending_balance"],
                "session_price": SESSION_PRICE_KOBO,
                "shortage": max(SESSION_PRICE_KOBO - wallet_summary["balance"], 0),
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


@app.route('/update_booking_status', methods=['POST'])
def update_booking_status():
    """Update booking status - accept, reject, or cancel bookings"""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    new_status = data.get('status')
    therapist_email = normalize_email(data.get('therapist_email'))
    
    valid_statuses = ['Accepted', 'Rejected', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({"message": "Invalid status"}), 400
    
    if not booking_id or not is_valid_email(therapist_email):
        return jsonify({"message": "Booking ID and therapist email required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT b.id, b.user_email, b.therapist_email, b.date, COALESCE(b.status, 'Pending'), u.availability
    FROM bookings b
    LEFT JOIN users u ON u.email = b.therapist_email
    WHERE b.id=? AND b.therapist_email=?
    """, (booking_id, therapist_email))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return jsonify({"message": "Booking not found or access denied"}), 404

    if booking[4] == 'Cancelled':
        conn.close()
        return jsonify({"message": "This booking has already been cancelled"}), 400

    if booking[4] == 'Rejected' and new_status != 'Cancelled':
        conn.close()
        return jsonify({"message": "Rejected bookings cannot be accepted again"}), 400

    if new_status == 'Accepted':
        booking_start = parse_booking_datetime(booking[3])
        if not booking_start:
            conn.close()
            return jsonify({"message": "This booking has an invalid appointment time. Please reschedule it first."}), 400

        duration = booking_duration_from_availability(booking[5])
        cursor.execute("""
        SELECT id, user_email, date FROM bookings
        WHERE therapist_email=?
          AND id != ?
          AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
        """, (therapist_email, booking_id))
        duplicate_ids = []

        for conflict_id, conflict_user_email, conflict_date in cursor.fetchall():
            if not existing_booking_conflicts(conflict_date, booking_start, duration):
                continue

            if normalize_email(conflict_user_email) == normalize_email(booking[1]):
                duplicate_ids.append(conflict_id)
                continue

            conn.close()
            return jsonify({"message": f"Booking conflicts with booking #{conflict_id}. Please reschedule first."}), 409

        if duplicate_ids:
            placeholders = ",".join("?" for _ in duplicate_ids)
            cursor.execute(f"""
            UPDATE bookings
            SET status='Cancelled'
            WHERE id IN ({placeholders})
            """, duplicate_ids)
    
    cursor.execute("UPDATE bookings SET status=? WHERE id=?", (new_status, booking_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": f"Booking {new_status.lower()} successfully",
        "booking_id": booking_id,
        "status": new_status
    })


@app.route('/reschedule_booking', methods=['POST'])
def reschedule_booking():
    """Allow therapists to move an active appointment to a new time."""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    therapist_email = normalize_email(data.get('therapist_email'))
    date = data.get('date')
    requested_start = parse_booking_datetime(date)

    if not booking_id or not is_valid_email(therapist_email) or not date:
        return jsonify({"message": "Booking ID, therapist email, and new date are required"}), 400

    if not requested_start:
        return jsonify({"message": "Please choose a valid appointment date and time"}), 400

    if requested_start < datetime.now().replace(second=0, microsecond=0):
        return jsonify({"message": "Please choose a future appointment time"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT b.id, b.user_email, COALESCE(b.status, 'Pending'), u.availability
    FROM bookings b
    LEFT JOIN users u ON u.email = b.therapist_email
    WHERE b.id=? AND b.therapist_email=?
    """, (booking_id, therapist_email))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return jsonify({"message": "Booking not found or access denied"}), 404

    if booking[2] in ('Cancelled', 'Rejected'):
        conn.close()
        return jsonify({"message": "Cancelled or rejected bookings cannot be rescheduled"}), 400

    duration = booking_duration_from_availability(booking[3])
    cursor.execute("""
    SELECT id, user_email, date FROM bookings
    WHERE therapist_email=?
      AND id != ?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """, (therapist_email, booking_id))
    duplicate_ids = []

    for conflict_id, conflict_user_email, conflict_date in cursor.fetchall():
        if not existing_booking_conflicts(conflict_date, requested_start, duration):
            continue

        if normalize_email(conflict_user_email) == normalize_email(booking[1]):
            duplicate_ids.append(conflict_id)
            continue

        conn.close()
        return jsonify({"message": f"That time conflicts with booking #{conflict_id}. Please choose another time."}), 409

    if duplicate_ids:
        placeholders = ",".join("?" for _ in duplicate_ids)
        cursor.execute(f"""
        UPDATE bookings
        SET status='Cancelled'
        WHERE id IN ({placeholders})
        """, duplicate_ids)

    cursor.execute("""
    UPDATE bookings
    SET date=?, status='Accepted'
    WHERE id=?
    """, (requested_start.isoformat(timespec='minutes'), booking_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Booking rescheduled successfully"})


@app.route('/reduce_booking_group', methods=['POST'])
def reduce_booking_group():
    data = request.get_json() or {}
    therapist_email = normalize_email(data.get('therapist_email'))
    booking_group_id = (data.get('booking_group_id') or '').strip()

    try:
        keep_count = int(data.get('keep_count'))
    except (TypeError, ValueError):
        keep_count = 0

    if not is_valid_email(therapist_email) or not booking_group_id:
        return jsonify({"message": "Therapist account and booking group are required"}), 400

    if keep_count < 1:
        return jsonify({"message": "Keep at least one session in the request"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, COALESCE(status, 'Pending'), date
    FROM bookings
    WHERE therapist_email=?
      AND booking_group_id=?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    ORDER BY date, id
    """, (therapist_email, booking_group_id))
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return jsonify({"message": "Active booking group not found"}), 404

    if keep_count >= len(rows):
        conn.close()
        return jsonify({"message": "No reduction needed", "cancelled": 0})

    paid_ids = [row[0] for row in rows if booking_has_session_payment(cursor, row[0])]
    if keep_count < len(paid_ids):
        conn.close()
        return jsonify({"message": "Already paid sessions cannot be reduced here"}), 400

    keep_ids = {row[0] for row in rows[:keep_count]}
    cancel_ids = [row[0] for row in rows if row[0] not in keep_ids and row[0] not in paid_ids]

    if not cancel_ids:
        conn.close()
        return jsonify({"message": "No unpaid sessions were available to reduce", "cancelled": 0})

    placeholders = ",".join("?" for _ in cancel_ids)
    cursor.execute(f"""
    UPDATE bookings
    SET status='Cancelled',
        total_sessions=?
    WHERE id IN ({placeholders})
    """, (keep_count, *cancel_ids))
    cursor.execute("""
    UPDATE bookings
    SET total_sessions=?
    WHERE booking_group_id=?
      AND therapist_email=?
      AND COALESCE(status, 'Pending') NOT IN ('Cancelled', 'Rejected')
    """, (keep_count, booking_group_id, therapist_email))

    conn.commit()
    cancelled = len(cancel_ids)
    conn.close()

    return jsonify({
        "message": f"Booking request reduced to {keep_count} session(s)",
        "cancelled": cancelled,
        "keep_count": keep_count
    })


@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    """Allow users to cancel their booking before therapist accepts"""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    user_email = normalize_email(data.get('user_email'))
    
    if not booking_id or not user_email:
        return jsonify({"message": "Booking ID and email required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify the user owns this booking and it's still pending
    cursor.execute("""
        SELECT id FROM bookings 
        WHERE id=? AND user_email=? AND LOWER(COALESCE(status, 'Pending'))='pending'
    """, (booking_id, user_email))
    
    if not cursor.fetchone():
        conn.close()
        return jsonify({"message": "Booking not found or cannot be cancelled (already accepted or cancelled)"}), 404
    
    cursor.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Booking cancelled successfully"})


@app.route('/delete_user_booking', methods=['POST'])
def delete_user_booking():
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    user_email = normalize_email(data.get('user_email'))

    if not booking_id or not is_valid_email(user_email):
        return jsonify({"message": "Booking ID and email required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM bookings
    WHERE id=? AND user_email=?
      AND COALESCE(status, 'Pending') IN ('Rejected', 'Cancelled')
    """, (booking_id, user_email))

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"message": "Only rejected or cancelled bookings can be deleted"}), 404

    return jsonify({"message": "Booking deleted"})


@app.route('/set_online_status', methods=['POST'])
def set_online_status():
    """Allow therapists to set their online/offline status"""
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    online_status = data.get('online_status')
    manual_availability = data.get('manual_availability')
    
    if not email:
        return jsonify({"message": "Email required"}), 400
    
    valid_statuses = ['online', 'offline']
    if online_status not in valid_statuses:
        return jsonify({"message": "Invalid status. Use 'online' or 'offline'"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user is a therapist
    cursor.execute("SELECT role FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    if not row or row[0] != 'therapist':
        conn.close()
        return jsonify({"message": "Only therapists can set online status"}), 403
    
    # Update both online_status and manual_availability
    manual_avail = 1 if manual_availability else 0
    cursor.execute("""
        UPDATE users 
        SET online_status=?, manual_availability=? 
        WHERE email=?
    """, (online_status, manual_avail, email))
    
    conn.commit()
    conn.close()
    
    status_text = "available for all bookings" if manual_availability else "available during scheduled hours"
    return jsonify({"message": f"Status set to {online_status}. You are now {status_text}."})


@app.route('/get_notifications', methods=['POST'])
def get_notifications():
    """Get notification counts for sidebar badges"""
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    role = data.get('role')
    
    if not email:
        return jsonify({"message": "Email required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    notifications = {"bookings": 0, "support": 0}
    
    if role == 'therapist':
        # Count pending bookings for therapist
        cursor.execute("""
            SELECT COUNT(*) FROM bookings 
            WHERE therapist_email=? AND (status='Pending' OR status IS NULL)
        """, (email,))
        notifications["bookings"] = cursor.fetchone()[0] or 0
    elif role == 'user':
        # Count user's pending bookings
        cursor.execute("""
            SELECT COUNT(*) FROM bookings 
            WHERE user_email=? AND (status='Pending' OR status IS NULL)
        """, (email,))
        notifications["bookings"] = cursor.fetchone()[0] or 0
    
    # Count unread support messages for admin
    if role == 'admin':
        cursor.execute("""
            SELECT COUNT(*) FROM customer_care 
            WHERE status='open' OR status IS NULL
        """)
        notifications["support"] = cursor.fetchone()[0] or 0
    
    conn.close()
    return jsonify(notifications)


@app.route('/remove_duplicate_bookings', methods=['POST'])
def remove_duplicate_bookings():
    """Cancel overlapping duplicate bookings so they stop showing in booking lists."""
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    requested_role = data.get('role')
    
    if not email:
        return jsonify({"message": "Email required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()

    if requested_role in ('user', 'therapist'):
        cursor.execute("""
        SELECT role FROM users WHERE email=? AND role=?
        LIMIT 1
        """, (email, requested_role))
    else:
        cursor.execute("""
        SELECT role FROM users
        WHERE email=? AND role IN ('user', 'therapist')
        ORDER BY id DESC
        LIMIT 1
        """, (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"message": "Account not found"}), 404

    role = user[0]
    removed_count = cancel_duplicate_bookings(
        cursor,
        user_email=email if role == 'user' else None,
        therapist_email=email if role == 'therapist' else None
    )

    if not removed_count:
        conn.close()
        return jsonify({"message": "No duplicate bookings found", "removed": 0})

    conn.commit()
    conn.close()
    
    return jsonify({"message": f"Cancelled {removed_count} duplicate booking(s)", "removed": removed_count})



@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json() or {}
    sender = normalize_email(data.get('sender'))
    receiver = normalize_email(data.get('receiver'))
    booking_id = data.get('booking_id')
    message = (data.get('message') or '').strip()

    if not message:
        return jsonify({"message": "Please type a message"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    access = get_chat_access(cursor, sender, receiver, booking_id)

    if not access.get("allowed"):
        conn.close()
        return jsonify({"message": access["message"]}), access["status"]

    active_booking_id = access["booking"][0]
    cursor.execute("""
    INSERT INTO messages (sender, receiver, message, booking_id, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (sender, receiver, message, active_booking_id, now_iso()))
    timer = maybe_start_session_timer(cursor, active_booking_id)

    conn.commit()
    conn.close()

    return jsonify({"message": "Message sent", "timer": timer})


@app.route('/get_messages', methods=['POST'])
def get_messages():
    data = request.get_json() or {}
    user1 = normalize_email(data.get('user1'))
    user2 = normalize_email(data.get('user2'))
    booking_id = data.get('booking_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    access = get_chat_access(cursor, user1, user2, booking_id)

    if not access.get("allowed"):
        conn.close()
        return jsonify({"message": access["message"], "messages": []}), access["status"]

    active_booking_id = access["booking"][0]
    timer = maybe_start_session_timer(cursor, active_booking_id)
    cursor.execute("""
    SELECT sender, receiver, message, created_at FROM messages
    WHERE booking_id=?
      AND (
        (sender=? AND receiver=?)
        OR (sender=? AND receiver=?)
      )
    ORDER BY id ASC
    """, (
        active_booking_id,
        user1,
        user2,
        user2,
        user1
    ))

    messages = cursor.fetchall()
    conn.commit()
    conn.close()

    return jsonify({
        "timer": timer,
        "messages": [
            {
                "sender": row[0],
                "receiver": row[1],
                "message": row[2],
                "created_at": row[3]
            }
            for row in messages
        ]
    })


@app.route('/chat_threads', methods=['POST'])
def chat_threads():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    role = data.get('role')

    if not is_valid_email(email) or role not in ('user', 'therapist'):
        return jsonify({"message": "Valid account details required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    removed_duplicates = cancel_duplicate_bookings(
        cursor,
        user_email=email if role == 'user' else None,
        therapist_email=email if role == 'therapist' else None
    )
    if removed_duplicates:
        conn.commit()

    if role == 'user':
        wallet_summary = wallet_summary_for_user(cursor, email)
        cursor.execute("""
        SELECT b.id, b.therapist_email, b.date, b.meet_link,
               u.name, u.specialization, u.profile_photo
        FROM bookings b
        LEFT JOIN users u ON u.id = (
            SELECT ux.id FROM users ux
            WHERE ux.email = b.therapist_email AND ux.role='therapist'
            ORDER BY ux.verified DESC, ux.id DESC
            LIMIT 1
        )
        WHERE b.user_email=?
          AND COALESCE(b.status, 'Pending')='Accepted'
        ORDER BY b.id DESC
        """, (email,))
        rows = cursor.fetchall()
        paid_bookings = {
            row[0]: booking_has_session_payment(cursor, row[0])
            for row in rows
        }
        timers = {
            row[0]: session_timer_for_booking(cursor, row[0])
            for row in rows
        }
        conn.close()

        return jsonify({
            "balance": wallet_summary["balance"],
            "pending_balance": wallet_summary["pending_balance"],
            "session_price": SESSION_PRICE_KOBO,
            "threads": [
                {
                    "booking_id": row[0],
                    "receiver_email": row[1],
                    "display_name": row[4] or row[1],
                    "subtitle": row[5] or "Therapist",
                    "date": row[2],
                    "meet_link": row[3] if paid_bookings.get(row[0], False) else None,
                    "paid": paid_bookings.get(row[0], False),
                    "can_chat": paid_bookings.get(row[0], False),
                    "session_price": SESSION_PRICE_KOBO,
                    "shortage": max(SESSION_PRICE_KOBO - wallet_summary["balance"], 0),
                    "timer": timers.get(row[0]),
                    "profile_photo": row[6]
                }
                for row in rows
            ]
        })

    cursor.execute("""
    SELECT b.id, b.user_email, b.date, b.meet_link,
           u.name, u.gender, u.location
    FROM bookings b
    LEFT JOIN users u ON u.id = (
        SELECT ux.id FROM users ux
        WHERE ux.email = b.user_email AND ux.role='user'
        ORDER BY ux.id DESC
        LIMIT 1
    )
    WHERE b.therapist_email=?
      AND COALESCE(b.status, 'Pending')='Accepted'
    ORDER BY b.id DESC
    """, (email,))
    rows = cursor.fetchall()
    paid_bookings = {
        row[0]: booking_has_session_payment(cursor, row[0])
        for row in rows
    }
    timers = {
        row[0]: session_timer_for_booking(cursor, row[0])
        for row in rows
    }
    conn.close()

    return jsonify({
        "threads": [
            {
                "booking_id": row[0],
                "receiver_email": row[1],
                "display_name": row[4] or row[1],
                "subtitle": ", ".join(item for item in [row[5], row[6]] if item) or "Client",
                "date": row[2],
                "meet_link": row[3] if paid_bookings.get(row[0], False) else None,
                "paid": paid_bookings.get(row[0], False),
                "can_chat": paid_bookings.get(row[0], False),
                "session_price": SESSION_PRICE_KOBO,
                "timer": timers.get(row[0])
            }
            for row in rows
        ]
    })


@app.route('/set_meet_link', methods=['POST'])
def set_meet_link():
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    therapist_email = normalize_email(data.get('therapist_email'))
    meet_link = (data.get('meet_link') or '').strip()

    if not booking_id or not is_valid_email(therapist_email):
        return jsonify({"message": "Booking ID and therapist email required"}), 400

    if not is_google_meet_link(meet_link):
        return jsonify({"message": "Please paste a valid Google Meet link"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE bookings
    SET meet_link=?
    WHERE id=? AND therapist_email=?
      AND COALESCE(status, 'Pending')='Accepted'
    """, (meet_link, booking_id, therapist_email))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"message": "Accepted booking not found"}), 404

    return jsonify({"message": "Google Meet link saved", "meet_link": meet_link})

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
           verification_status, rejection_reason, online_status, manual_availability,
           payout_bank_code, payout_bank_name, payout_account_number,
           payout_account_name, payout_recipient_code, payout_verified_at,
           payout_updated_at
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
            "rejection_reason": therapist[20],
            "online_status": therapist[21] or "offline",
            "manual_availability": therapist[22] or 0,
            "payout_bank_code": therapist[23],
            "payout_bank_name": therapist[24],
            "payout_account_number_masked": mask_account_number(therapist[25]),
            "payout_account_name": therapist[26],
            "payout_recipient_ready": bool(therapist[27]),
            "payout_verified_at": therapist[28],
            "payout_updated_at": therapist[29]
        }
        return jsonify({"therapist": profile})

    return jsonify({"message": "Therapist not found"}), 404


@app.route('/paystack_banks', methods=['GET'])
def paystack_banks():
    banks, verified_source = fetch_paystack_banks()
    return jsonify({
        "banks": banks,
        "paystack_configured": bool(paystack_secret_key()),
        "verified_source": verified_source
    })


@app.route('/payment_config', methods=['GET'])
def payment_config():
    return jsonify({
        "paystack_public_key": os.environ.get('PAYSTACK_PUBLIC_KEY', PAYSTACK_PUBLIC_KEY_FALLBACK).strip()
    })


@app.route('/save_payout_account', methods=['POST'])
def save_payout_account():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    bank_code = str(data.get('bank_code') or '').strip()
    bank_name = (data.get('bank_name') or '').strip()
    account_number = normalize_account_number(data.get('account_number'))

    if not is_valid_email(email):
        return jsonify({"message": "Please use a valid therapist email"}), 400

    if not bank_code or not account_number:
        return jsonify({"message": "Choose a bank and enter the account number"}), 400

    if len(account_number) != 10:
        return jsonify({"message": "Nigerian payout account number must be 10 digits"}), 400

    banks, _ = fetch_paystack_banks()
    bank_lookup = {bank["code"]: bank["name"] for bank in banks}
    bank_name = bank_name or bank_lookup.get(bank_code) or "Selected bank"
    account_name = (data.get('account_name') or '').strip()
    recipient_code = ""
    verified_at = None
    message = "Payout account saved. Paystack verification is pending."

    if paystack_secret_key():
        resolved = resolve_paystack_account(account_number, bank_code)
        if resolved["ok"]:
            account_name = resolved["account_name"]
            recipient = create_paystack_recipient(account_name, account_number, bank_code)
            if recipient["ok"] and recipient["recipient_code"]:
                recipient_code = recipient["recipient_code"]
                account_name = recipient.get("account_name") or account_name
                verified_at = now_iso()
                message = "Payout account verified. Therapist payouts can now be sent through Paystack."
            else:
                message = f"Payout account saved, but recipient setup is pending: {recipient['message']}"
        else:
            message = f"Payout account saved, but Paystack could not verify it yet: {resolved['message']}"
    else:
        message = "Payout account saved. Add PAYSTACK_SECRET_KEY before live therapist payouts."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE users
    SET payout_bank_code=?,
        payout_bank_name=?,
        payout_account_number=?,
        payout_account_name=?,
        payout_recipient_code=?,
        payout_verified_at=?,
        payout_updated_at=?
    WHERE email=? AND role='therapist'
    """, (
        bank_code,
        bank_name,
        account_number,
        account_name,
        recipient_code,
        verified_at,
        now_iso(),
        email
    ))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"message": "Therapist account not found"}), 404

    payouts = process_pending_payouts_for_therapist(email) if recipient_code else []
    return jsonify({
        "message": message,
        "bank_code": bank_code,
        "bank_name": bank_name,
        "account_name": account_name,
        "account_number_masked": mask_account_number(account_number),
        "recipient_ready": bool(recipient_code),
        "payouts": payouts
    })

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


@app.route('/get_people', methods=['GET'])
def get_people():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT u.email, u.role,
           u.verified, u.verification_status, u.created_at, u.last_login_at, u.last_seen_at,
           COALESCE(client_bookings.total, 0), COALESCE(therapist_bookings.total, 0),
           COALESCE(payments.total, 0), COALESCE(support.total, 0),
           COALESCE(u.email_verified, 1)
    FROM users u
    LEFT JOIN (
        SELECT user_email, COUNT(*) AS total
        FROM bookings
        GROUP BY user_email
    ) client_bookings ON client_bookings.user_email = u.email
    LEFT JOIN (
        SELECT therapist_email, COUNT(*) AS total
        FROM bookings
        GROUP BY therapist_email
    ) therapist_bookings ON therapist_bookings.therapist_email = u.email
    LEFT JOIN (
        SELECT user_email, COUNT(*) AS total
        FROM payments
        GROUP BY user_email
    ) payments ON payments.user_email = u.email
    LEFT JOIN (
        SELECT sender_email, COUNT(*) AS total
        FROM customer_care
        GROUP BY sender_email
    ) support ON support.sender_email = u.email
    WHERE u.role IN ('user', 'therapist')
    ORDER BY COALESCE(u.last_seen_at, u.created_at, '') DESC, u.id DESC
    """)

    people = cursor.fetchall()
    conn.close()

    return jsonify({
        "people": [
            {
                "email": row[0],
                "role": row[1],
                "verified": row[2],
                "verification_status": row[3],
                "created_at": row[4],
                "last_login_at": row[5],
                "last_seen_at": row[6],
                "client_bookings": row[7],
                "therapist_bookings": row[8],
                "payments": row[9],
                "support_messages": row[10],
                "email_verified": bool(row[11])
            }
            for row in people
        ]
    })


@app.route('/admin_delete_account', methods=['POST'])
def admin_delete_account():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid account email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE email=?", (email,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return jsonify({"message": "Account not found"}), 404

    if account[0] not in ('user', 'therapist'):
        conn.close()
        return jsonify({"message": "Only user and therapist accounts can be kicked out here"}), 403

    delete_account_data(cursor, email)

    conn.commit()
    conn.close()

    return jsonify({"message": f"{email} has been kicked out"})


def delete_account_data(cursor, email):
    cursor.execute("DELETE FROM sessions WHERE user_email=?", (email,))
    cursor.execute("""
    UPDATE bookings
    SET status='Cancelled'
    WHERE user_email=? OR therapist_email=?
    """, (email, email))
    cursor.execute("DELETE FROM messages WHERE sender=? OR receiver=?", (email, email))
    cursor.execute("DELETE FROM customer_care WHERE sender_email=?", (email,))
    cursor.execute("DELETE FROM therapist_reviews WHERE user_email=? OR therapist_email=?", (email, email))
    cursor.execute("DELETE FROM users WHERE email=? AND role IN ('user', 'therapist')", (email,))


@app.route('/admin_bulk_delete_accounts', methods=['POST'])
def admin_bulk_delete_accounts():
    auth_error = require_admin()
    if auth_error:
        return auth_error

    data = request.get_json() or {}
    emails = data.get('emails') or []

    if not isinstance(emails, list):
        return jsonify({"message": "Choose accounts to kick out"}), 400

    normalized_emails = []
    for email in emails:
        normalized = normalize_email(email)
        if normalized and normalized not in normalized_emails:
            normalized_emails.append(normalized)

    if not normalized_emails:
        return jsonify({"message": "Choose accounts to kick out"}), 400

    if len(normalized_emails) > 100:
        return jsonify({"message": "You can kick out up to 100 accounts at a time"}), 400

    invalid_emails = [email for email in normalized_emails if not is_valid_email(email)]
    if invalid_emails:
        return jsonify({"message": "One or more selected emails are invalid"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in normalized_emails)
    cursor.execute(f"""
    SELECT email, role
    FROM users
    WHERE email IN ({placeholders})
    """, normalized_emails)
    accounts = cursor.fetchall()
    account_lookup = {row[0]: row[1] for row in accounts}

    deleted = []
    skipped = []
    for email in normalized_emails:
        role = account_lookup.get(email)
        if role not in ('user', 'therapist'):
            skipped.append(email)
            continue
        delete_account_data(cursor, email)
        deleted.append(email)

    conn.commit()
    conn.close()

    return jsonify({
        "message": f"Kicked out {len(deleted)} account{'s' if len(deleted) != 1 else ''}."
                   + (f" Skipped {len(skipped)}." if skipped else ""),
        "deleted": deleted,
        "skipped": skipped
    })


@app.route('/pay', methods=['POST'])
def pay():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    amount = normalize_amount_kobo(data.get('amount'), DEFAULT_TOP_UP_KOBO)
    reference = data.get('reference') or f"manual_{uuid4().hex[:12]}"

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid payment email"}), 400

    if amount <= 0:
        return jsonify({"message": "Please enter a valid top-up amount"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payments (user_email, amount, currency, provider, reference, status, created_at, verified_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (email, amount, data.get('currency', 'NGN'), data.get('provider', 'manual'), reference, 'recorded', now_iso(), now_iso()))

    wallet_summary = wallet_summary_for_user(cursor, email)
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Account top-up recorded",
        "reference": reference,
        "balance": wallet_summary["balance"],
        "pending_balance": wallet_summary["pending_balance"],
        "session_price": SESSION_PRICE_KOBO,
        "shortage": wallet_summary["shortage"]
    })


@app.route('/wallet_summary', methods=['POST'])
def wallet_summary():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))

    if not is_valid_email(email):
        return jsonify({"message": "Please enter a valid account email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    summary = wallet_summary_for_user(cursor, email)

    cursor.execute("""
    SELECT b.id, b.therapist_email, b.date, u.name
    FROM bookings b
    LEFT JOIN users u ON u.id = (
        SELECT ux.id FROM users ux
        WHERE ux.email = b.therapist_email AND ux.role='therapist'
        ORDER BY ux.verified DESC, ux.id DESC
        LIMIT 1
    )
    LEFT JOIN session_payments sp
      ON sp.booking_id = b.id AND LOWER(COALESCE(sp.status, ''))='paid'
    WHERE b.user_email=?
      AND COALESCE(b.status, 'Pending')='Accepted'
      AND sp.id IS NULL
    ORDER BY b.id DESC
    """, (email,))
    unpaid_rows = cursor.fetchall()
    conn.close()

    return jsonify({
        **summary,
        "can_pay_session": summary["balance"] >= SESSION_PRICE_KOBO,
        "unpaid_sessions": [
            {
                "booking_id": row[0],
                "therapist_email": row[1],
                "therapist_name": row[3] or row[1],
                "date": row[2]
            }
            for row in unpaid_rows
        ]
    })


def pay_for_accepted_sessions(user_email, booking_ids, currency='NGN'):
    requested_ids = []
    for booking_id in booking_ids:
        try:
            numeric_id = int(booking_id)
        except (TypeError, ValueError):
            continue
        if numeric_id not in requested_ids:
            requested_ids.append(numeric_id)

    if not is_valid_email(user_email) or not requested_ids:
        return {"message": "Accepted session bookings are required"}, 400

    if len(requested_ids) > MAX_CONSECUTIVE_SESSIONS:
        return {"message": f"You can pay for up to {MAX_CONSECUTIVE_SESSIONS} sessions at once"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in requested_ids)
    cursor.execute(f"""
    SELECT b.id, b.user_email, b.therapist_email, COALESCE(b.status, 'Pending'), u.availability
    FROM bookings b
    LEFT JOIN users u ON u.email = b.therapist_email AND u.role='therapist'
    WHERE b.id IN ({placeholders}) AND b.user_email=?
    ORDER BY b.date, b.id
    """, (*requested_ids, user_email))
    rows = cursor.fetchall()
    rows_by_id = {row[0]: row for row in rows}

    missing_ids = [booking_id for booking_id in requested_ids if booking_id not in rows_by_id]
    if missing_ids:
        conn.close()
        return {"message": "One or more session bookings could not be found"}, 404

    invalid_rows = [row for row in rows if row[3] != 'Accepted']
    if invalid_rows:
        conn.close()
        return {"message": "Therapist must accept every selected session before payment"}, 400

    unpaid_rows = [row for row in rows if not booking_has_session_payment(cursor, row[0])]
    summary = wallet_summary_for_user(cursor, user_email)

    if not unpaid_rows:
        conn.close()
        return {
            "message": "Selected sessions are already paid",
            "balance": summary["balance"],
            "session_price": SESSION_PRICE_KOBO,
            "shortage": summary["shortage"],
            "paid_booking_ids": requested_ids
        }, 200

    total_amount = len(unpaid_rows) * SESSION_PRICE_KOBO
    if summary["balance"] < total_amount:
        conn.close()
        return {
            "message": "Insufficient account balance. Please top up before paying for these sessions.",
            "balance": summary["balance"],
            "session_price": SESSION_PRICE_KOBO,
            "shortage": total_amount - summary["balance"],
            "total_amount": total_amount,
            "session_count": len(unpaid_rows)
        }, 402

    session_payment_ids = []
    paid_booking_ids = []
    try:
        for row in unpaid_rows:
            duration = booking_duration_from_availability(row[4])
            cursor.execute("""
            INSERT INTO session_payments (
                booking_id, user_email, therapist_email, amount, currency,
                status, created_at, duration_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row[0],
                row[1],
                row[2],
                SESSION_PRICE_KOBO,
                currency or 'NGN',
                'paid',
                now_iso(),
                duration
            ))
            session_payment_ids.append(cursor.lastrowid)
            paid_booking_ids.append(row[0])
    except sqlite3.IntegrityError:
        conn.rollback()
        summary = wallet_summary_for_user(cursor, user_email)
        conn.close()
        return {
            "message": "One of these sessions was already paid. Please refresh and try again.",
            "balance": summary["balance"],
            "session_price": SESSION_PRICE_KOBO,
            "shortage": summary["shortage"]
        }, 409

    summary = wallet_summary_for_user(cursor, user_email)
    conn.commit()
    conn.close()

    payouts = process_payouts_for_session_payments(session_payment_ids)
    count = len(paid_booking_ids)
    session_word = "session" if count == 1 else "sessions"

    return {
        "message": f"{count} {session_word} paid. Chat and Google Meet are now unlocked.",
        "paid_booking_ids": paid_booking_ids,
        "balance": summary["balance"],
        "session_price": SESSION_PRICE_KOBO,
        "shortage": summary["shortage"],
        "total_amount": total_amount,
        "session_count": count,
        "payouts": payouts
    }, 200


@app.route('/pay_for_session', methods=['POST'])
def pay_for_session():
    data = request.get_json() or {}
    user_email = normalize_email(data.get('user_email') or data.get('email'))
    booking_id = data.get('booking_id')

    payload, status_code = pay_for_accepted_sessions(
        user_email,
        [booking_id],
        data.get('currency', 'NGN')
    )
    if "paid_booking_ids" in payload:
        payload["booking_id"] = payload["paid_booking_ids"][0] if payload["paid_booking_ids"] else booking_id

    return jsonify(payload), status_code


@app.route('/pay_for_sessions', methods=['POST'])
def pay_for_sessions():
    data = request.get_json() or {}
    user_email = normalize_email(data.get('user_email') or data.get('email'))
    booking_ids = data.get('booking_ids') or []

    if not isinstance(booking_ids, list):
        booking_ids = [booking_ids]

    payload, status_code = pay_for_accepted_sessions(
        user_email,
        booking_ids,
        data.get('currency', 'NGN')
    )
    return jsonify(payload), status_code

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json() or {}
    reference = data.get('reference')
    email = normalize_email(data.get('email'))
    amount = normalize_amount_kobo(data.get('amount'), DEFAULT_TOP_UP_KOBO)

    if not reference:
        return jsonify({"message": "Missing payment reference"}), 400

    if email and not is_valid_email(email):
        return jsonify({"message": "Please enter a valid payment email"}), 400

    if amount <= 0:
        return jsonify({"message": "Please enter a valid payment amount"}), 400

    paystack_secret_key = os.environ.get('PAYSTACK_SECRET_KEY', '').strip()
    status = 'pending_verification'
    message = 'Payment recorded for admin review'

    if paystack_secret_key:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {paystack_secret_key}"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
            paystack_data = result.get('data', {})

            if paystack_data.get('status') == "success":
                status = 'verified'
                message = 'Account top-up verified'
                email = email or normalize_email(paystack_data.get('customer', {}).get('email'))
                amount = normalize_amount_kobo(paystack_data.get('amount'), amount)
            else:
                status = 'failed'
                message = 'Payment failed'
        except requests.RequestException:
            status = 'pending_verification'
            message = 'Payment recorded for admin review'
    else:
        message = 'Payment recorded for admin review. Paystack verification is not configured yet.'

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

    summary = wallet_summary_for_user(cursor, email) if is_valid_email(email) else None
    conn.commit()
    conn.close()

    response_status = 200 if status == 'verified' else 202 if status == 'pending_verification' else 400
    payload = {"message": message, "status": status}
    if summary:
        payload.update({
            "balance": summary["balance"],
            "pending_balance": summary["pending_balance"],
            "session_price": SESSION_PRICE_KOBO,
            "shortage": summary["shortage"]
        })

    return jsonify(payload), response_status


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
    LEFT JOIN users u ON u.id = (
        SELECT ux.id FROM users ux
        WHERE ux.email = p.user_email
        ORDER BY CASE ux.role WHEN 'user' THEN 0 WHEN 'therapist' THEN 1 ELSE 2 END, ux.id DESC
        LIMIT 1
    )
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
@app.route('/login')
def home():
    return send_from_directory(app.root_path, 'index.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"})


@app.route('/dashboard.html')
@app.route('/dashboard')
@app.route('/user')
def dashboard():
    return send_from_directory(app.root_path, 'dashboard.html')

@app.route('/settings.html')
def settings():
    return send_from_directory(app.root_path, 'settings.html')

@app.route('/admin.html')
def admin():
    abort(404)

@app.route('/admin-login.html')
def admin_login_page():
    abort(404)

@app.route('/admin-login')
def admin_login_shortcut():
    abort(404)

@app.route(ADMIN_ENTRY_PATH)
@app.route(LEGACY_ADMIN_ENTRY_PATH)
def admin_entry():
    return send_from_directory(app.root_path, 'admin-login.html')

@app.route(ADMIN_CONSOLE_PATH)
@app.route(LEGACY_ADMIN_CONSOLE_PATH)
def admin_console():
    return send_from_directory(app.root_path, 'admin.html')

@app.route('/therapist.html')
@app.route('/therapist')
def therapist():
    return send_from_directory(app.root_path, 'therapist.html')


@app.route('/<path:filename>')
def public_file(filename):
    if filename in PUBLIC_FILES:
        return send_from_directory(app.root_path, filename)
    abort(404)


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
