import os
import secrets
import sqlite3
import smtplib
import time
import hmac
import hashlib
import re
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

from flask import Flask, abort, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename

from config import Config
from models import (
    db,
    User,
    AlumniProfile,
    TracerSurvey,
    Job,
    Event,
    EventRSVP,
    PasswordReset,
    SystemLog,
    Notification,
    Report,
    UserRole,
)


app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "database.db").replace("\\", "/")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{db_path}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

upload_folder = os.path.join(app.root_path, "static", "uploads")
os.makedirs(upload_folder, exist_ok=True)
app.config["UPLOAD_FOLDER"] = upload_folder
profile_photo_folder = os.path.join(upload_folder, "profile_photos")
os.makedirs(profile_photo_folder, exist_ok=True)
app.config["PROFILE_PHOTO_FOLDER"] = profile_photo_folder

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "warning"
login_manager.init_app(app)

app.config.setdefault("OTP_EXPIRY_SECONDS", 300)
app.config.setdefault("SHOW_OTP_IN_UI", True)
app.config.setdefault("OTP_MODE", "totp")
app.config.setdefault("OTP_TIMESTEP_SECONDS", 30)
try:
    app.config["OTP_EXPIRY_SECONDS"] = int(
        os.environ.get("OTP_EXPIRY_SECONDS", app.config["OTP_EXPIRY_SECONDS"])
    )
except (TypeError, ValueError):
    app.config["OTP_EXPIRY_SECONDS"] = 300

try:
    app.config["OTP_TIMESTEP_SECONDS"] = int(
        os.environ.get("OTP_TIMESTEP_SECONDS", app.config["OTP_TIMESTEP_SECONDS"])
    )
except (TypeError, ValueError):
    app.config["OTP_TIMESTEP_SECONDS"] = 30

otp_mode_env = str(os.environ.get("OTP_MODE", app.config["OTP_MODE"])).strip().lower()
if otp_mode_env in {"totp", "hotp"}:
    app.config["OTP_MODE"] = otp_mode_env
else:
    app.config["OTP_MODE"] = "totp"

show_otp_env = os.environ.get("SHOW_OTP_IN_UI")
if show_otp_env is not None:
    app.config["SHOW_OTP_IN_UI"] = show_otp_env.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

ROLE_PORTALS = {
    "alumni": {"label": "Alumni", "dashboard_template": "alumni_dashboard.html"},
    "admin": {"label": "Admin", "dashboard_template": "admin_dashboard.html"},
    "director": {"label": "Director", "dashboard_template": "director_dashboard.html"},
    "registrar": {"label": "Registrar", "dashboard_template": "registrar_dashboard.html"},
    "osa": {"label": "OSA", "dashboard_template": "osa_dashboard.html"},
}

ROLE_ALIASES = {
    "administrator": "admin",
    "admin portal": "admin",
    "director portal": "director",
    "registrar portal": "registrar",
    "office of student affairs": "osa",
    "student affairs": "osa",
    "osa portal": "osa",
}

DEGREE_OPTIONS = [
    "Bachelor of Elementary Education",
    "Bachelor of Secondary Education - English",
    "Bachelor of Secondary Education - Math",
    "Bachelor of Secondary Education - Social Studies",
    "Bachelor of Science in Industrial Technology - Drafting Technology",
    "Bachelor of Science in Industrial Technology - Automotive Technology",
    "Bachelor of Science in Industrial Technology - Electrical Technology",
    "Bachelor of Science in Industrial Technology - Electronics Technology",
    "Bachelor of Science in Industrial Technology - Welding Technology",
    "Bachelor of Science in Hospitality Management (BSHM)",
    "Bachelor of Science in Information Systems (BSIS)",
    "Bachelor of Science in Information Technology (BSIT)",
    "Bachelor of Technical-Vocational Education (BTVE)",
]

OTP_PURPOSE_LOGIN = "login"
OTP_PURPOSE_REGISTRATION = "registration"
OTP_SESSION_KEY = "otp_context"
ACTIVE_USER_ID_KEY = "active_user_id"
ACTIVE_ROLE_KEY = "active_user_role"
POST_LOGIN_NEXT_KEY = "post_login_next"
APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_REQUIRED_ROLES = {"admin", "director", "registrar", "osa"}
RSVP_ATTEND = "attend"
RSVP_MAYBE = "maybe"
RSVP_NOT_ATTEND = "not_attend"
RSVP_STATUSES = {RSVP_ATTEND, RSVP_MAYBE, RSVP_NOT_ATTEND}

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PROFILE_PHOTO_WEB_PREFIX = "uploads/profile_photos/"
DEFAULT_AVATAR_FILE = "img/default-avatar.svg"
CAMPUS_LOGO_FILE = "img/Pototan.jpg"
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^[0-9+\-()\s]{7,24}$")


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@login_manager.unauthorized_handler
def handle_unauthorized():
    next_target = request.path
    if request.query_string:
        next_target = f"{request.path}?{request.query_string.decode('utf-8', errors='ignore')}"

    flash("Please sign in to continue.", "warning")
    role_slug = infer_portal_role_from_endpoint()
    if role_slug:
        return redirect(url_for("role_login", role=role_slug, next=next_target))
    return redirect(url_for("index"))


def normalize_role(role):
    if role is None:
        return None
    if isinstance(role, UserRole):
        return role.value
    value = str(role).strip()
    if value.startswith("UserRole."):
        value = value.split(".", 1)[1]
    normalized = value.lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    if normalized in ROLE_ALIASES:
        return ROLE_ALIASES[normalized]
    return normalized


def clean_text(value):
    return (value or "").strip()


def to_role_slug(value, default=None):
    normalized = normalize_role(value)
    if normalized in ROLE_PORTALS:
        return normalized
    if normalized in ROLE_ALIASES:
        alias = ROLE_ALIASES[normalized]
        if alias in ROLE_PORTALS:
            return alias
    if normalized:
        compact = normalized.replace(" ", "")
        if compact in ROLE_PORTALS:
            return compact
    return default


def to_role_enum(value, default=UserRole.ALUMNI):
    role_slug = to_role_slug(value, normalize_role(default) if default else "alumni")
    if role_slug not in ROLE_PORTALS:
        role_slug = "alumni"
    return UserRole[role_slug.upper()]


def require_role_slug(value):
    role_slug = normalize_role(value)
    if role_slug not in ROLE_PORTALS:
        abort(404)
    return role_slug


def role_requires_approval(role_slug):
    return role_slug in APPROVAL_REQUIRED_ROLES


def normalize_approval_status(value):
    normalized = clean_text(value).lower()
    if normalized in {APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED}:
        return normalized
    return APPROVAL_APPROVED


def user_approval_status(user):
    return normalize_approval_status(getattr(user, "approval_status", APPROVAL_APPROVED))


def is_user_approved(user):
    return user_approval_status(user) == APPROVAL_APPROVED


def infer_portal_role_from_endpoint():
    endpoint = request.endpoint or ""
    path = request.path or ""

    if path.startswith("/portal/"):
        segments = [seg for seg in path.split("/") if seg]
        if len(segments) >= 2:
            inferred = to_role_slug(segments[1])
            if inferred:
                return inferred

    if endpoint.startswith("admin_") or path.startswith("/admin"):
        return "admin"
    if endpoint in {"admin", "analytics"} or path.startswith("/analytics"):
        return "admin"
    if endpoint.startswith("alumni_module") or endpoint in {
        "profile",
        "my_profile",
        "survey",
        "my_survey",
        "dashboard_overview",
    }:
        return "alumni"
    return None


def role_template(role_slug, page):
    return f"portals/{role_slug}/{page}.html"


def role_dashboard_url(role_slug):
    return url_for("role_dashboard", role=role_slug)


def role_login_url(role_slug):
    return url_for("role_login", role=role_slug)


def role_register_url(role_slug):
    return url_for("role_register", role=role_slug)


def set_active_session(user):
    resolved_role = to_role_slug(user.role, default="alumni")
    session[ACTIVE_USER_ID_KEY] = user.id
    session[ACTIVE_ROLE_KEY] = resolved_role


def clear_active_session():
    session.pop(ACTIVE_USER_ID_KEY, None)
    session.pop(ACTIVE_ROLE_KEY, None)
    session.pop(POST_LOGIN_NEXT_KEY, None)


def clear_otp_context():
    session.pop(OTP_SESSION_KEY, None)
    session.pop("otp_email", None)
    session.pop("otp_demo", None)


def parse_utc_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_hotp(secret_bytes, counter, digits=6):
    counter_bytes = int(counter).to_bytes(8, "big")
    digest = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    code = truncated % (10 ** digits)
    return f"{code:0{digits}d}"


def generate_totp(secret_bytes, timestep=30, digits=6):
    step = max(15, int(timestep or 30))
    counter = int(time.time() // step)
    code = generate_hotp(secret_bytes, counter, digits=digits)
    return code, counter


def send_otp(email, otp, role_slug="alumni"):
    resolved_role = to_role_slug(role_slug, default="alumni")
    portal_name = ROLE_PORTALS.get(resolved_role, ROLE_PORTALS["alumni"]).get(
        "label", "Alumni"
    )
    smtp_server = clean_text(os.environ.get("MAIL_SERVER", app.config.get("MAIL_SERVER")))
    smtp_username = clean_text(
        os.environ.get("MAIL_USERNAME", app.config.get("MAIL_USERNAME"))
    )
    smtp_password = os.environ.get("MAIL_PASSWORD", app.config.get("MAIL_PASSWORD"))
    smtp_port = app.config.get("MAIL_PORT", 587)
    try:
        smtp_port = int(os.environ.get("MAIL_PORT", smtp_port))
    except (TypeError, ValueError):
        smtp_port = 587

    use_tls_env = os.environ.get("MAIL_USE_TLS")
    if use_tls_env is None:
        use_tls = bool(app.config.get("MAIL_USE_TLS", True))
    else:
        use_tls = use_tls_env.strip().lower() in {"1", "true", "yes", "on"}

    if smtp_server and smtp_username and smtp_password:
        minutes = max(1, app.config.get("OTP_EXPIRY_SECONDS", 300) // 60)
        message = EmailMessage()
        message["Subject"] = f"WVSU {portal_name} Portal OTP Verification"
        message["From"] = smtp_username
        message["To"] = email
        message.set_content(
            (
                f"Your one-time password for the WVSU {portal_name} Portal is "
                f"{otp}. It expires in about {minutes} minutes."
            )
        )
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as smtp:
                if use_tls:
                    smtp.starttls()
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)
            return
        except Exception as exc:
            print(f"Failed to send OTP email to {email}: {exc}")

    print(f"OTP for {email} ({portal_name} portal): {otp}")


def issue_otp(user, purpose, role_slug):
    otp_mode = clean_text(os.environ.get("OTP_MODE", app.config.get("OTP_MODE", "totp"))).lower()
    if otp_mode not in {"totp", "hotp"}:
        otp_mode = "totp"

    otp_secret = secrets.token_bytes(20)
    otp_counter = None
    if otp_mode == "hotp":
        otp_counter = secrets.randbelow(10_000_000_000)
        otp_code = generate_hotp(otp_secret, otp_counter)
    else:
        otp_code, otp_counter = generate_totp(
            otp_secret,
            timestep=app.config.get("OTP_TIMESTEP_SECONDS", 30),
        )

    user.set_otp(otp_code)
    expires_at = datetime.utcnow() + timedelta(seconds=app.config["OTP_EXPIRY_SECONDS"])
    session[OTP_SESSION_KEY] = {
        "email": user.email,
        "role": role_slug,
        "purpose": purpose,
        "otp_mode": otp_mode,
        "otp_counter": otp_counter,
        "expires_at": expires_at.isoformat(),
        "request_id": secrets.token_urlsafe(8),
    }
    session["otp_email"] = user.email
    if app.config.get("SHOW_OTP_IN_UI"):
        session["otp_demo"] = otp_code
    else:
        session.pop("otp_demo", None)
    send_otp(user.email, otp_code, role_slug=role_slug)
    return otp_code


def get_otp_context(email=None, role_slug=None, purpose=None):
    context = session.get(OTP_SESSION_KEY)
    if not isinstance(context, dict):
        return None
    if email and context.get("email") != email:
        return None
    if role_slug and context.get("role") != role_slug:
        return None
    if purpose and context.get("purpose") != purpose:
        return None
    return context


def is_otp_context_expired(context):
    expires_at = parse_utc_iso(context.get("expires_at")) if context else None
    if not expires_at:
        return True
    return datetime.utcnow() > expires_at


def get_otp_seconds_remaining(context):
    expires_at = parse_utc_iso(context.get("expires_at")) if context else None
    if not expires_at:
        return 0
    remaining = int((expires_at - datetime.utcnow()).total_seconds())
    return max(0, remaining)


def validate_active_session():
    if not current_user.is_authenticated:
        return None

    role_slug = to_role_slug(current_user.role, default="alumni")
    stored_user_id = session.get(ACTIVE_USER_ID_KEY)
    stored_role = session.get(ACTIVE_ROLE_KEY)

    if stored_user_id is None or stored_role is None:
        set_active_session(current_user)
        return None

    try:
        stored_user_id = int(stored_user_id)
    except (TypeError, ValueError):
        stored_user_id = None

    if stored_user_id != current_user.id or stored_role != role_slug:
        logout_user()
        clear_active_session()
        clear_otp_context()
        flash("Session validation failed. Please sign in again.", "warning")
        return redirect(role_login_url(role_slug))

    return None


def block_switch_account(target_role=None):
    if current_user.is_authenticated:
        role_slug = to_role_slug(current_user.role, default="alumni")
        if target_role and role_slug == target_role:
            return redirect(role_dashboard_url(role_slug))
        flash("Please log out before signing in to another account.", "warning")
        return redirect(role_dashboard_url(role_slug))
    return None


def role_label(role_slug):
    return ROLE_PORTALS[role_slug]["label"]


def resolve_requested_role(default=None):
    role_input = request.form.get("role") if request.method == "POST" else None
    if not role_input:
        role_input = request.args.get("role")
    return to_role_slug(role_input, default=default)


@app.context_processor
def inject_role():
    role_value = None
    current_dashboard_url = None
    if current_user.is_authenticated:
        role_value = to_role_slug(current_user.role, default="alumni")
        current_dashboard_url = role_dashboard_url(role_value)
    return {
        "current_role": role_value,
        "current_dashboard_url": current_dashboard_url,
        "role_portals": ROLE_PORTALS,
        "campus_logo_static_path": url_for("static", filename=CAMPUS_LOGO_FILE),
    }


@app.template_global()
def profile_photo_url(profile):
    return profile_photo_url_for(profile)


@app.template_global()
def profile_initials(profile):
    return profile_initials_for(profile)


@app.template_global()
def role_display_name(role_value):
    role_slug = to_role_slug(role_value, default="alumni")
    return role_label(role_slug)


@app.before_request
def enforce_session_validation():
    if request.endpoint == "static":
        return None
    return validate_active_session()


def role_required(*roles):
    allowed = {role.lower() for role in roles}

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            role_value = to_role_slug(current_user.role, default="alumni")
            if role_value not in allowed:
                flash("You do not have access to that page.", "danger")
                return redirect(role_dashboard_url(role_value))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime_local(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def is_valid_email(value):
    return bool(EMAIL_PATTERN.fullmatch(clean_text(value)))


def is_valid_phone(value):
    phone_value = clean_text(value)
    if not phone_value:
        return True
    if not PHONE_PATTERN.fullmatch(phone_value):
        return False
    digits_only = "".join(ch for ch in phone_value if ch.isdigit())
    return 7 <= len(digits_only) <= 15


def detect_image_type(header_bytes):
    if not header_bytes:
        return None
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header_bytes[:4] == b"RIFF" and header_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def normalize_static_path(path):
    return clean_text(path).replace("\\", "/").lstrip("/")


def is_profile_photo_path(path):
    normalized = normalize_static_path(path)
    return normalized.startswith(PROFILE_PHOTO_WEB_PREFIX)


def delete_profile_photo_file(path):
    normalized = normalize_static_path(path)
    if not is_profile_photo_path(normalized):
        return

    static_root = os.path.abspath(os.path.join(app.root_path, "static"))
    photo_root = os.path.abspath(app.config["PROFILE_PHOTO_FOLDER"])
    absolute_path = os.path.abspath(
        os.path.join(static_root, normalized.replace("/", os.sep))
    )

    try:
        within_photo_root = os.path.commonpath([photo_root, absolute_path]) == photo_root
    except ValueError:
        within_photo_root = False

    if within_photo_root and os.path.exists(absolute_path):
        os.remove(absolute_path)


def save_profile_photo_upload(file_storage):
    if not file_storage or not clean_text(getattr(file_storage, "filename", "")):
        return None, None

    safe_filename = secure_filename(file_storage.filename)
    if "." not in safe_filename:
        return None, "Please upload a valid image file."

    extension = safe_filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        return None, f"Unsupported file type. Allowed: {allowed}."

    header_bytes = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    detected_type = detect_image_type(header_bytes)
    if not detected_type:
        return None, "Uploaded file is not a valid image."

    normalized_extension = "jpg" if extension == "jpeg" else extension
    if detected_type != normalized_extension:
        return None, "Image file content does not match the file extension."

    generated_name = f"{secrets.token_hex(16)}.{normalized_extension}"
    relative_path = f"{PROFILE_PHOTO_WEB_PREFIX}{generated_name}"
    absolute_path = os.path.abspath(
        os.path.join(app.root_path, "static", relative_path.replace("/", os.sep))
    )
    photo_root = os.path.abspath(app.config["PROFILE_PHOTO_FOLDER"])

    try:
        within_photo_root = os.path.commonpath([photo_root, absolute_path]) == photo_root
    except ValueError:
        within_photo_root = False

    if not within_photo_root:
        return None, "Unable to safely store uploaded image."

    file_storage.save(absolute_path)
    return relative_path, None


def profile_photo_url_for(profile):
    photo_path = normalize_static_path(getattr(profile, "profile_photo", None))
    if photo_path and is_profile_photo_path(photo_path):
        return url_for("static", filename=photo_path)
    return url_for("static", filename=DEFAULT_AVATAR_FILE)


def profile_initials_for(profile):
    first_name = clean_text(getattr(profile, "first_name", ""))
    last_name = clean_text(getattr(profile, "last_name", ""))
    initials = "".join(part[0].upper() for part in [first_name, last_name] if part)
    return initials or "AL"


def calculate_section_completion(values):
    if not values:
        return 0
    filled_values = sum(1 for value in values if value)
    return int(round((filled_values / len(values)) * 100))


def get_or_create_alumni_profile():
    profile = current_user.profile
    if profile:
        return profile
    profile = AlumniProfile(
        user=current_user,
        first_name="",
        last_name="",
        degree="",
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def set_user_approval_defaults(user, role_slug):
    user.approval_requested_at = datetime.utcnow()
    if role_requires_approval(role_slug):
        user.approval_status = APPROVAL_PENDING
        user.approved_at = None
        user.approved_by_user_id = None
    else:
        user.approval_status = APPROVAL_APPROVED
        user.approved_at = datetime.utcnow()


def sync_user_activation_state(user):
    role_slug = to_role_slug(user.role, default="alumni")
    approved = is_user_approved(user)
    if role_requires_approval(role_slug):
        user.is_active = bool(user.otp_verified and approved)
        return
    user.is_active = bool(user.otp_verified)


def calculate_employment_rate(total_alumni, employed_count):
    if total_alumni == 0:
        return 0
    return round((employed_count / total_alumni) * 100)


def get_basic_stats():
    total_alumni = AlumniProfile.query.count()
    employed_count = AlumniProfile.query.filter(
        AlumniProfile.employment_status.in_(["employed", "self-employed"])
    ).count()
    survey_responses = TracerSurvey.query.count()
    active_jobs = Job.query.filter(Job.is_active.is_(True)).count()
    return {
        "total_alumni": total_alumni,
        "employed_count": employed_count,
        "survey_responses": survey_responses,
        "active_jobs": active_jobs,
    }


def calculate_profile_completed(profile):
    required_fields = [
        profile.first_name,
        profile.last_name,
        profile.degree,
        profile.year_graduated,
    ]
    return all(required_fields)


def calculate_completion_percentage(profile):
    fields = [
        profile.first_name,
        profile.last_name,
        profile.middle_name,
        profile.civil_status,
        profile.gender,
        profile.date_of_birth,
        profile.phone,
        profile.address,
        profile.city,
        profile.province,
        profile.degree,
        profile.year_graduated,
        profile.student_id,
        profile.employment_status,
        profile.current_employer,
        profile.job_position,
        profile.work_location,
        profile.skills,
        profile.father_name,
        profile.mother_name,
        profile.guardian_name,
        profile.enrollment_status,
        profile.enrolled_program,
        profile.enrollment_date,
        profile.expected_completion_date,
    ]
    filled = sum(1 for field in fields if field)
    if not fields:
        return 0
    return int(round((filled / len(fields)) * 100))


def format_salary_range(min_salary, max_salary):
    if min_salary and max_salary:
        return f"PHP {min_salary:,} - {max_salary:,}"
    if min_salary:
        return f"PHP {min_salary:,}+"
    if max_salary:
        return f"Up to PHP {max_salary:,}"
    return None


def safe_commit(error_message="Unable to save changes. Please try again."):
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        flash(error_message, "danger")
        return False


def get_auth_template_context(role_slug):
    return {
        "role_slug": role_slug,
        "role_label": role_label(role_slug),
        "role_login_url": role_login_url(role_slug),
        "role_register_url": role_register_url(role_slug),
        "legacy_login_url": url_for("login", role=role_slug),
        "legacy_register_url": url_for("register", role=role_slug),
        "portal_login_url": role_login_url(role_slug),
        "portal_register_url": role_register_url(role_slug),
        "otp_expiry_seconds": app.config["OTP_EXPIRY_SECONDS"],
        "year_options": range(datetime.utcnow().year + 1, 1969, -1),
        "degree_options": degree_options_for(),
    }


def degree_options_for(selected=None):
    selected_value = clean_text(selected)
    options = list(DEGREE_OPTIONS)
    if selected_value and selected_value not in options:
        options.insert(0, selected_value)
    return options


def render_dashboard_for_role(role_slug):
    stats = get_basic_stats()
    employment_rate = calculate_employment_rate(
        stats["total_alumni"], stats["employed_count"]
    )
    survey_rate = calculate_employment_rate(
        stats["total_alumni"], stats["survey_responses"]
    )

    if role_slug == "admin":
        pending_accounts = User.query.filter(
            User.approval_status == APPROVAL_PENDING,
            User.role.in_(
                [UserRole.ADMIN, UserRole.DIRECTOR, UserRole.REGISTRAR, UserRole.OSA]
            ),
        ).count()
        total_rsvps = EventRSVP.query.filter(EventRSVP.status == RSVP_ATTEND).count()
        return render_template(
            "admin_dashboard.html",
            total_alumni=stats["total_alumni"],
            total_surveys=TracerSurvey.query.count(),
            total_jobs=Job.query.count(),
            total_events=Event.query.count(),
            employment_rate=employment_rate,
            pending_accounts=pending_accounts,
            total_rsvps=total_rsvps,
        )

    if role_slug == "director":
        return render_template(
            "director_dashboard.html",
            employment_rate=employment_rate,
            survey_rate=survey_rate,
        )

    if role_slug == "registrar":
        pending_verifications = AlumniProfile.query.filter(
            AlumniProfile.profile_completed.is_(False)
        ).count()
        verified_alumni = AlumniProfile.query.filter(
            AlumniProfile.profile_completed.is_(True)
        ).count()
        return render_template(
            "registrar_dashboard.html",
            pending_verifications=pending_verifications,
            verified_alumni=verified_alumni,
        )

    if role_slug == "osa":
        upcoming_events = Event.query.filter(
            Event.event_date >= datetime.utcnow(), Event.is_published.is_(True)
        ).count()
        rsvp_count = (
            db.session.query(func.count(EventRSVP.id))
            .join(Event, EventRSVP.event_id == Event.id)
            .filter(
                Event.event_date >= datetime.utcnow(),
                EventRSVP.status == RSVP_ATTEND,
            )
            .scalar()
            or 0
        )
        return render_template(
            "osa_dashboard.html",
            upcoming_events=upcoming_events,
            rsvp_count=rsvp_count,
        )

    return render_template(
        "alumni_dashboard.html",
        total_alumni=stats["total_alumni"],
        active_jobs=Job.query.filter(Job.is_active.is_(True)).count(),
    )


def handle_portal_registration(role_slug):
    template_name = role_template(role_slug, "register")
    template_context = get_auth_template_context(role_slug)

    blocked = block_switch_account(role_slug)
    if blocked:
        return blocked

    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password or not confirm_password:
            flash("Please complete all required fields.", "danger")
            return render_template(template_name, **template_context)

        if not is_valid_email(email):
            flash("Please provide a valid email address.", "danger")
            return render_template(template_name, **template_context)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template(template_name, **template_context)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            existing_role = to_role_slug(existing_user.role, default="alumni")
            flash(
                f"Email already registered under the {role_label(existing_role)} Portal. Please sign in there.",
                "warning",
            )
            return redirect(role_login_url(existing_role))

        user = User(email=email, role=to_role_enum(role_slug))
        user.set_password(password)
        user.otp_verified = False
        user.is_active = False
        set_user_approval_defaults(user, role_slug)

        db.session.add(user)
        if role_slug == "alumni":
            first_name = clean_text(request.form.get("first_name"))
            last_name = clean_text(request.form.get("last_name"))
            degree = clean_text(request.form.get("degree"))
            year_graduated = parse_int(request.form.get("year_graduated"))

            if not all([first_name, last_name, degree, year_graduated]):
                flash("Please complete all required alumni profile fields.", "danger")
                db.session.rollback()
                clear_otp_context()
                return render_template(template_name, **template_context)

            profile = AlumniProfile(
                user=user,
                first_name=first_name,
                last_name=last_name,
                degree=degree,
                year_graduated=year_graduated,
            )
            db.session.add(profile)

        issue_otp(user, OTP_PURPOSE_REGISTRATION, role_slug)

        if not safe_commit("Registration failed. Please try again."):
            clear_otp_context()
            return render_template(template_name, **template_context)

        flash("OTP sent. Please verify to complete registration.", "success")
        return redirect(
            url_for(
                "verify_otp",
                email=email,
                role=role_slug,
                purpose=OTP_PURPOSE_REGISTRATION,
            )
        )

    return render_template(template_name, **template_context)


def handle_portal_login(role_slug):
    template_name = role_template(role_slug, "login")
    template_context = get_auth_template_context(role_slug)

    blocked = block_switch_account(role_slug)
    if blocked:
        return blocked

    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template(template_name, **template_context)

        user_role = to_role_slug(user.role)
        if not user_role:
            flash("Account role is invalid. Please contact support.", "danger")
            return render_template(template_name, **template_context)
        if user_role != role_slug:
            flash(
                f"This account belongs to the {role_label(user_role)} Portal. Use the correct portal login.",
                "danger",
            )
            return redirect(role_login_url(user_role))

        if role_requires_approval(user_role):
            approval_status = user_approval_status(user)
            if approval_status == APPROVAL_PENDING and user.otp_verified:
                flash(
                    "Your account is pending admin approval. Please wait for confirmation.",
                    "warning",
                )
                return render_template(template_name, **template_context)
            if approval_status == APPROVAL_REJECTED:
                flash(
                    "Your account request was not approved. Please contact an administrator.",
                    "danger",
                )
                return render_template(template_name, **template_context)

        sync_user_activation_state(user)
        if not user.is_active and user.otp_verified:
            flash("Account is inactive. Please contact support.", "danger")
            return render_template(template_name, **template_context)

        otp_purpose = (
            OTP_PURPOSE_REGISTRATION
            if not user.otp_verified
            else OTP_PURPOSE_LOGIN
        )
        issue_otp(user, otp_purpose, role_slug)
        next_target = clean_text(request.form.get("next")) or request.args.get("next")
        session[POST_LOGIN_NEXT_KEY] = (
            next_target
            if otp_purpose == OTP_PURPOSE_LOGIN
            else None
        )

        if not safe_commit("Unable to generate OTP right now. Please try again."):
            clear_otp_context()
            return render_template(template_name, **template_context)

        message = (
            "OTP sent. Verify to activate your account."
            if otp_purpose == OTP_PURPOSE_REGISTRATION
            else "OTP sent. Verify to complete sign in."
        )
        flash(message, "success")
        return redirect(
            url_for(
                "verify_otp",
                email=email,
                role=role_slug,
                purpose=otp_purpose,
            )
        )

    return render_template(template_name, **template_context)


def seed_users():
    def ensure_user(email, role, password):
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, role=role)
            user.set_password(password)
            user.otp_verified = True
            user.approval_status = APPROVAL_APPROVED
            user.approval_requested_at = datetime.utcnow()
            user.approved_at = datetime.utcnow()
            user.is_active = True
            db.session.add(user)
            db.session.flush()
        else:
            try:
                user.role = role
            except:
                role_str = str(role).lower().strip()
                user.role = UserRole[role_str.upper()] if hasattr(UserRole, role_str.upper()) else UserRole.ALUMNI
            user.otp_verified = True
            user.approval_status = APPROVAL_APPROVED
            user.approved_at = datetime.utcnow()
            user.is_active = True
        return user

    ensure_user("admin@wvsu.edu.ph", UserRole.ADMIN, "admin123")
    ensure_user("director@wvsu.edu.ph", UserRole.DIRECTOR, "admin123")
    ensure_user("registrar@wvsu.edu.ph", UserRole.REGISTRAR, "admin123")
    ensure_user("osa@wvsu.edu.ph", UserRole.OSA, "admin123")
    db.session.commit()


def fix_invalid_roles():
    fixed = 0
    for user in User.query.all():
        resolved_slug = to_role_slug(user.role)
        if not resolved_slug:
            normalized_enum = UserRole.ALUMNI
        else:
            normalized_enum = UserRole[resolved_slug.upper()]

        if user.role != normalized_enum:
            user.role = normalized_enum
            fixed += 1

    if fixed:
        db.session.commit()
        print(f"Fixed {fixed} roles")


def ensure_user_approval_integrity():
    users = User.query.all()
    touched = 0
    for user in users:
        changed = False
        role_slug = to_role_slug(user.role, default="alumni")
        raw_status = clean_text(getattr(user, "approval_status", "")).lower()
        if raw_status not in {APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED}:
            raw_status = APPROVAL_APPROVED
            if user.approval_status != raw_status:
                user.approval_status = raw_status
                changed = True
        status = raw_status

        if role_requires_approval(role_slug):
            # Backward-compatible migration for existing privileged accounts.
            pass
        else:
            if status != APPROVAL_APPROVED:
                user.approval_status = APPROVAL_APPROVED
                status = APPROVAL_APPROVED
                changed = True

        if not user.approval_requested_at:
            user.approval_requested_at = user.created_at or datetime.utcnow()
            changed = True

        if status == APPROVAL_APPROVED and not user.approved_at:
            user.approved_at = datetime.utcnow()
            changed = True

        current_active = bool(user.is_active)
        sync_user_activation_state(user)
        if bool(user.is_active) != current_active:
            changed = True

        if changed:
            touched += 1

    if touched:
        db.session.commit()
        print(f"Normalized approval data for {touched} users")


def ensure_sqlite_schema():
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if db_uri.startswith("sqlite:///"):
        db_file = db_uri.replace("sqlite:///", "")
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            def add_missing_columns(table_name, column_defs):
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                existing_columns = {row[1] for row in cursor.fetchall()}
                for column_name, ddl in column_defs.items():
                    if column_name not in existing_columns:
                        cursor.execute(
                            f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {ddl}'
                        )

            try:
                add_missing_columns(
                    "user",
                    {
                        "role": "TEXT DEFAULT 'alumni'",
                        "otp_code_hash": "TEXT",
                        "otp_verified": "INTEGER DEFAULT 0",
                        "is_active": "INTEGER DEFAULT 0",
                        "approval_status": "TEXT DEFAULT 'approved'",
                        "approval_requested_at": "DATETIME",
                        "approved_at": "DATETIME",
                        "approved_by_user_id": "INTEGER",
                        "approval_notes": "TEXT",
                        "created_at": "DATETIME",
                        "last_login": "DATETIME",
                    },
                )
                add_missing_columns(
                    "alumni_profile",
                    {
                        "civil_status": "TEXT",
                        "father_name": "TEXT",
                        "father_contact": "TEXT",
                        "mother_name": "TEXT",
                        "mother_contact": "TEXT",
                        "guardian_name": "TEXT",
                        "guardian_contact": "TEXT",
                        "enrollment_status": "TEXT",
                        "enrolled_program": "TEXT",
                        "enrollment_date": "DATE",
                        "expected_completion_date": "DATE",
                    },
                )
                conn.commit()
            finally:
                conn.close()


@app.route("/")
def index():
    stats = get_basic_stats()
    return render_template("index.html", **stats)


@app.route("/about")
def about():
    stats = get_basic_stats()
    employment_rate = calculate_employment_rate(
        stats["total_alumni"], stats["employed_count"]
    )
    return render_template(
        "about.html",
        total_alumni=stats["total_alumni"],
        employment_rate=employment_rate,
        survey_responses=stats["survey_responses"],
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Thank you for reaching out. We will respond soon.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/portal/<role>")
def portal_entry(role):
    role_slug = require_role_slug(role)
    if current_user.is_authenticated:
        current_role = to_role_slug(current_user.role, default="alumni")
        if current_role == role_slug:
            return redirect(role_dashboard_url(current_role))
        flash("Please log out before switching to another portal.", "warning")
        return redirect(role_dashboard_url(current_role))
    return redirect(role_login_url(role_slug))


@app.route("/portal/<role>/register", methods=["GET", "POST"])
def role_register(role):
    role_slug = require_role_slug(role)
    return handle_portal_registration(role_slug)


@app.route("/register", methods=["GET", "POST"])
def register():
    role_slug = resolve_requested_role()
    if not role_slug:
        flash("Please choose a portal before registration.", "warning")
        return redirect(url_for("index"))
    return handle_portal_registration(role_slug)


@app.route("/portal/<role>/login", methods=["GET", "POST"])
def role_login(role):
    role_slug = require_role_slug(role)
    return handle_portal_login(role_slug)


@app.route("/login", methods=["GET", "POST"])
def login():
    role_slug = resolve_requested_role()
    if not role_slug:
        flash("Please choose a portal before signing in.", "warning")
        return redirect(url_for("index"))
    return handle_portal_login(role_slug)


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    blocked = block_switch_account()
    if blocked:
        return blocked

    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        otp = clean_text(request.form.get("otp"))
        role_slug = to_role_slug(request.form.get("role"))
        if not role_slug:
            flash("Invalid portal context. Please request a new OTP.", "danger")
            return redirect(url_for("index"))
        purpose = clean_text(request.form.get("purpose")).lower() or OTP_PURPOSE_LOGIN
        if purpose not in {OTP_PURPOSE_LOGIN, OTP_PURPOSE_REGISTRATION}:
            purpose = OTP_PURPOSE_LOGIN

        otp_context = get_otp_context(
            email=email,
            role_slug=role_slug,
            purpose=purpose,
        )
        if not otp_context:
            flash("OTP session not found. Please request a new OTP.", "warning")
            if purpose == OTP_PURPOSE_REGISTRATION:
                return redirect(role_register_url(role_slug))
            return redirect(role_login_url(role_slug))

        if is_otp_context_expired(otp_context):
            flash("OTP expired. Please request a new OTP.", "warning")
            clear_otp_context()
            return redirect(
                url_for(
                    "resend_otp",
                    email=email,
                    role=role_slug,
                    purpose=purpose,
                )
            )

        user = User.query.filter_by(email=email).first()
        if not user:
            clear_otp_context()
            flash("Account not found. Please register again.", "danger")
            return redirect(role_register_url(role_slug))

        account_role = to_role_slug(user.role)
        if not account_role:
            clear_otp_context()
            flash("Account role is invalid. Please contact support.", "danger")
            return redirect(url_for("index"))
        if account_role != role_slug:
            clear_otp_context()
            flash(
                f"Role mismatch detected. Please continue in the {role_label(account_role)} Portal.",
                "danger",
            )
            return redirect(role_login_url(account_role))

        if not user.verify_otp(otp):
            flash("Invalid OTP. Please try again.", "danger")
            return redirect(
                url_for(
                    "verify_otp",
                    email=email,
                    role=role_slug,
                    purpose=purpose,
                )
            )

        if purpose == OTP_PURPOSE_REGISTRATION:
            user.otp_verified = True
            user.otp_code_hash = None
            sync_user_activation_state(user)
            if not safe_commit("Unable to verify OTP right now."):
                return redirect(
                    url_for(
                        "verify_otp",
                        email=email,
                        role=role_slug,
                        purpose=purpose,
                    )
                )

            clear_otp_context()
            if role_requires_approval(role_slug):
                approval_status = user_approval_status(user)
                if approval_status == APPROVAL_PENDING:
                    flash(
                        "OTP verified. Your account is pending admin approval before login.",
                        "warning",
                    )
                elif approval_status == APPROVAL_REJECTED:
                    flash(
                        "OTP verified, but this account is not approved. Contact an administrator.",
                        "danger",
                    )
                else:
                    flash("OTP verified. You can now sign in.", "success")
            else:
                flash("OTP verified. You can now sign in.", "success")
            return redirect(role_login_url(role_slug))

        if role_requires_approval(role_slug):
            approval_status = user_approval_status(user)
            if approval_status == APPROVAL_PENDING:
                clear_otp_context()
                flash(
                    "Your account is pending admin approval. Login is disabled until approval.",
                    "warning",
                )
                return redirect(role_login_url(role_slug))
            if approval_status == APPROVAL_REJECTED:
                clear_otp_context()
                flash(
                    "This account request was rejected. Please contact an administrator.",
                    "danger",
                )
                return redirect(role_login_url(role_slug))

        sync_user_activation_state(user)
        if not user.is_active:
            clear_otp_context()
            flash("Account is not active yet. Please contact support.", "danger")
            return redirect(role_login_url(role_slug))

        login_user(user)
        set_active_session(user)
        user.last_login = datetime.utcnow()
        user.otp_code_hash = None
        if not safe_commit("Unable to complete sign in. Please try again."):
            logout_user()
            clear_active_session()
            return redirect(role_login_url(role_slug))

        clear_otp_context()
        next_page = session.pop(POST_LOGIN_NEXT_KEY, None)
        flash("Sign in successful.", "success")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(role_dashboard_url(role_slug))

    email = clean_text(request.args.get("email") or session.get("otp_email")).lower()
    context_role = to_role_slug(request.args.get("role"))
    context_purpose = clean_text(request.args.get("purpose")).lower()
    if context_purpose not in {OTP_PURPOSE_LOGIN, OTP_PURPOSE_REGISTRATION}:
        context_purpose = None

    otp_context = get_otp_context(
        email=email or None,
        role_slug=context_role if request.args.get("role") else None,
        purpose=context_purpose,
    )
    if not otp_context:
        otp_context = get_otp_context()
        if otp_context:
            email = otp_context.get("email", "")
            context_role = to_role_slug(otp_context.get("role"), default=context_role)
            context_purpose = otp_context.get("purpose", OTP_PURPOSE_LOGIN)

    if not otp_context:
        flash("Please request an OTP first.", "warning")
        if context_purpose == OTP_PURPOSE_LOGIN and context_role:
            return redirect(role_login_url(context_role))
        if context_role:
            return redirect(role_register_url(context_role))
        return redirect(url_for("index"))

    if is_otp_context_expired(otp_context):
        flash("OTP expired. Please request a new OTP.", "warning")
        email = otp_context.get("email", email)
        context_role = to_role_slug(otp_context.get("role"), default=context_role)
        context_purpose = otp_context.get("purpose", OTP_PURPOSE_LOGIN)
        clear_otp_context()
        if not context_role:
            return redirect(url_for("index"))
        return redirect(
            url_for(
                "resend_otp",
                email=email,
                role=context_role,
                purpose=context_purpose,
            )
        )

    email = otp_context.get("email", email)
    context_role = to_role_slug(otp_context.get("role"), default=context_role)
    if not context_role:
        clear_otp_context()
        flash("OTP context is invalid. Please request a new OTP.", "danger")
        return redirect(url_for("index"))
    context_purpose = otp_context.get("purpose", OTP_PURPOSE_LOGIN)

    return render_template(
        "verify_otp.html",
        email=email,
        role_slug=context_role,
        role_label=role_label(context_role),
        purpose=context_purpose,
        otp=session.get("otp_demo"),
        expires_in=get_otp_seconds_remaining(otp_context),
        login_url=role_login_url(context_role),
        register_url=role_register_url(context_role),
    )


@app.route("/resend-otp")
def resend_otp():
    blocked = block_switch_account()
    if blocked:
        return blocked

    email = clean_text(request.args.get("email") or session.get("otp_email")).lower()
    requested_role = clean_text(request.args.get("role"))
    requested_purpose = clean_text(request.args.get("purpose")).lower()
    if requested_purpose not in {OTP_PURPOSE_LOGIN, OTP_PURPOSE_REGISTRATION}:
        requested_purpose = None

    existing_context = get_otp_context(email=email or None)
    role_slug = to_role_slug(
        requested_role or (existing_context.get("role") if existing_context else None),
    )
    purpose = requested_purpose or (
        existing_context.get("purpose") if existing_context else OTP_PURPOSE_REGISTRATION
    )
    if purpose not in {OTP_PURPOSE_LOGIN, OTP_PURPOSE_REGISTRATION}:
        purpose = OTP_PURPOSE_REGISTRATION

    if not email:
        flash("Email is required to resend OTP.", "danger")
        if role_slug:
            return redirect(role_register_url(role_slug))
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if not user:
        clear_otp_context()
        flash("Account not found. Please register again.", "danger")
        if role_slug:
            return redirect(role_register_url(role_slug))
        return redirect(url_for("index"))

    account_role = to_role_slug(user.role, default="alumni")
    if not role_slug:
        role_slug = account_role
    if account_role != role_slug:
        clear_otp_context()
        flash(
            f"Role mismatch detected. Continue in the {role_label(account_role)} Portal.",
            "danger",
        )
        return redirect(role_login_url(account_role))

    if purpose == OTP_PURPOSE_REGISTRATION and user.otp_verified:
        clear_otp_context()
        flash("Account already verified. Please sign in.", "info")
        return redirect(role_login_url(role_slug))

    if purpose == OTP_PURPOSE_LOGIN and role_requires_approval(role_slug):
        approval_status = user_approval_status(user)
        if approval_status == APPROVAL_PENDING:
            clear_otp_context()
            flash(
                "Your account is pending admin approval. Login OTP cannot be issued yet.",
                "warning",
            )
            return redirect(role_login_url(role_slug))
        if approval_status == APPROVAL_REJECTED:
            clear_otp_context()
            flash(
                "This account request was rejected. Please contact an administrator.",
                "danger",
            )
            return redirect(role_login_url(role_slug))

    issue_otp(user, purpose, role_slug)
    if not safe_commit("Unable to resend OTP right now. Please try again."):
        clear_otp_context()
        return redirect(role_login_url(role_slug))

    flash("OTP resent. Please check your email or console.", "success")
    return redirect(
        url_for(
            "verify_otp",
            email=email,
            role=role_slug,
            purpose=purpose,
        )
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    clear_active_session()
    clear_otp_context()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/portal/<role>/dashboard")
@login_required
def role_dashboard(role):
    role_slug = require_role_slug(role)
    current_role = to_role_slug(current_user.role, default="alumni")
    if current_role != role_slug:
        flash("You cannot access another role portal.", "danger")
        return redirect(role_dashboard_url(current_role))
    return render_dashboard_for_role(role_slug)


@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(role_dashboard_url(to_role_slug(current_user.role, default="alumni")))


@app.route("/dashboard/overview")
@role_required("alumni")
def dashboard_overview():
    profile = current_user.profile
    if not profile:
        flash("Please complete your profile to access the dashboard.", "warning")
        return redirect(url_for("profile"))

    completion_percentage = calculate_completion_percentage(profile)
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.utcnow(), Event.is_published.is_(True)
    ).order_by(Event.event_date.asc()).limit(4).all()
    recent_jobs = Job.query.filter(Job.is_active.is_(True)).order_by(
        Job.posted_date.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        profile=profile,
        completion_percentage=completion_percentage,
        upcoming_events=upcoming_events,
        recent_jobs=recent_jobs,
    )


@app.route("/admin")
@role_required("admin")
def admin():
    total_users = User.query.count()
    total_alumni = AlumniProfile.query.count()
    total_surveys = TracerSurvey.query.count()
    total_jobs = Job.query.count()
    recent_alumni = AlumniProfile.query.order_by(
        AlumniProfile.created_at.desc()
    ).limit(5).all()
    recent_surveys = (
        db.session.query(TracerSurvey, AlumniProfile)
        .join(AlumniProfile, TracerSurvey.alumni_id == AlumniProfile.id)
        .order_by(TracerSurvey.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "admin.html",
        total_users=total_users,
        total_alumni=total_alumni,
        total_surveys=total_surveys,
        total_jobs=total_jobs,
        recent_alumni=recent_alumni,
        recent_surveys=recent_surveys,
    )


@app.route("/analytics")
@role_required("admin", "director")
def analytics():
    total_alumni = AlumniProfile.query.count()
    employment_rows = (
        db.session.query(
            AlumniProfile.employment_status, func.count(AlumniProfile.id)
        )
        .group_by(AlumniProfile.employment_status)
        .all()
    )
    employment_counts = {status: count for status, count in employment_rows if status}
    employed = employment_counts.get("employed", 0)
    unemployed = employment_counts.get("unemployed", 0)
    self_employed = employment_counts.get("self-employed", 0)
    student = employment_counts.get("student", 0)

    total_jobs = Job.query.count()
    survey_responses = TracerSurvey.query.count()
    employment_rate = calculate_employment_rate(total_alumni, employed + self_employed)
    survey_rate = calculate_employment_rate(total_alumni, survey_responses)

    year_counts = (
        db.session.query(AlumniProfile.year_graduated, func.count(AlumniProfile.id))
        .filter(AlumniProfile.year_graduated.is_not(None))
        .group_by(AlumniProfile.year_graduated)
        .order_by(AlumniProfile.year_graduated)
        .all()
    )
    years = [year for year, _ in year_counts]
    graduates_by_year = [count for _, count in year_counts]

    degree_counts = (
        db.session.query(AlumniProfile.degree, func.count(AlumniProfile.id))
        .filter(AlumniProfile.degree.is_not(None))
        .group_by(AlumniProfile.degree)
        .order_by(func.count(AlumniProfile.id).desc())
        .all()
    )
    degrees = [degree for degree, _ in degree_counts]
    degrees_count = [count for _, count in degree_counts]

    avg_education = db.session.query(func.avg(TracerSurvey.education_quality)).scalar()
    avg_curriculum = db.session.query(func.avg(TracerSurvey.curriculum_relevance)).scalar()
    avg_facilities = db.session.query(func.avg(TracerSurvey.facilities_rating)).scalar()
    avg_satisfaction = db.session.query(func.avg(TracerSurvey.overall_satisfaction)).scalar()
    avg_recommend = db.session.query(func.avg(TracerSurvey.recommend_rating)).scalar()

    def normalize_avg(value):
        return round(value, 2) if value else 0

    return render_template(
        "analytics.html",
        total_alumni=total_alumni,
        employment_rate=employment_rate,
        survey_rate=survey_rate,
        total_jobs=total_jobs,
        employed=employed,
        unemployed=unemployed,
        self_employed=self_employed,
        student=student,
        years=years,
        graduates_by_year=graduates_by_year,
        degrees=degrees,
        degrees_count=degrees_count,
        avg_education=normalize_avg(avg_education),
        avg_curriculum=normalize_avg(avg_curriculum),
        avg_facilities=normalize_avg(avg_facilities),
        avg_satisfaction=normalize_avg(avg_satisfaction),
        avg_recommend=normalize_avg(avg_recommend),
    )


@app.route("/admin/account-approvals")
@role_required("admin")
def admin_account_approvals():
    status_filter = clean_text(request.args.get("status")).lower()
    if status_filter not in {APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED}:
        status_filter = ""

    query = User.query.filter(User.role != UserRole.ALUMNI)
    if status_filter:
        query = query.filter(User.approval_status == status_filter)

    accounts = query.order_by(
        (User.approval_status == APPROVAL_PENDING).desc(),
        User.approval_requested_at.desc(),
        User.created_at.desc(),
    ).all()
    pending_count = User.query.filter(
        User.role != UserRole.ALUMNI,
        User.approval_status == APPROVAL_PENDING,
    ).count()

    return render_template(
        "admin_account_approvals.html",
        accounts=accounts,
        status_filter=status_filter,
        pending_count=pending_count,
    )


@app.route("/admin/account-approvals/<int:user_id>/approve", methods=["POST"])
@role_required("admin")
def admin_approve_account(user_id):
    user = User.query.get_or_404(user_id)
    role_slug = to_role_slug(user.role, default="alumni")
    if role_slug == "alumni":
        flash("Alumni accounts do not require admin approval.", "info")
        return redirect(url_for("admin_account_approvals"))

    user.approval_status = APPROVAL_APPROVED
    user.approved_at = datetime.utcnow()
    user.approved_by_user_id = current_user.id
    notes = clean_text(request.form.get("approval_notes")) or None
    if notes:
        user.approval_notes = notes
    sync_user_activation_state(user)

    if safe_commit("Unable to approve account right now."):
        flash(f"{role_label(role_slug)} account approved.", "success")
    return redirect(url_for("admin_account_approvals"))


@app.route("/admin/account-approvals/<int:user_id>/reject", methods=["POST"])
@role_required("admin")
def admin_reject_account(user_id):
    user = User.query.get_or_404(user_id)
    role_slug = to_role_slug(user.role, default="alumni")
    if role_slug == "alumni":
        flash("Alumni accounts do not require admin approval.", "info")
        return redirect(url_for("admin_account_approvals"))

    user.approval_status = APPROVAL_REJECTED
    user.approved_at = datetime.utcnow()
    user.approved_by_user_id = current_user.id
    notes = clean_text(request.form.get("approval_notes")) or None
    user.approval_notes = notes or "Rejected by administrator."
    user.is_active = False

    if safe_commit("Unable to reject account right now."):
        flash(f"{role_label(role_slug)} account rejected.", "warning")
    return redirect(url_for("admin_account_approvals"))


@app.route("/admin/events/rsvp-analytics")
@role_required("admin", "osa")
def admin_event_rsvp_analytics():
    events_list = Event.query.order_by(Event.event_date.desc()).all()
    event_ids = [event.id for event in events_list]

    rows = []
    if event_ids:
        rows = (
            db.session.query(EventRSVP.event_id, EventRSVP.status, func.count(EventRSVP.id))
            .filter(EventRSVP.event_id.in_(event_ids))
            .group_by(EventRSVP.event_id, EventRSVP.status)
            .all()
        )

    rsvp_counts = {
        event_id: {RSVP_ATTEND: 0, RSVP_MAYBE: 0, RSVP_NOT_ATTEND: 0}
        for event_id in event_ids
    }
    for event_id, status, count in rows:
        if event_id in rsvp_counts and status in RSVP_STATUSES:
            rsvp_counts[event_id][status] = count

    selected_event_id = request.args.get("event_id", type=int)
    selected_event = None
    attendees = []
    if selected_event_id:
        selected_event = Event.query.get(selected_event_id)
        if selected_event:
            attendees = (
                db.session.query(EventRSVP, User, AlumniProfile)
                .join(User, EventRSVP.user_id == User.id)
                .outerjoin(AlumniProfile, AlumniProfile.user_id == User.id)
                .filter(EventRSVP.event_id == selected_event_id)
                .order_by(EventRSVP.updated_at.desc())
                .all()
            )

    return render_template(
        "admin_event_rsvp_analytics.html",
        events=events_list,
        rsvp_counts=rsvp_counts,
        selected_event=selected_event,
        attendees=attendees,
    )


@app.route("/admin/system-reset", methods=["GET", "POST"])
@role_required("admin")
def admin_system_reset():
    default_admin_email = "admin@wvsu.edu.ph"

    if request.method == "POST":
        confirmation_phrase = clean_text(request.form.get("confirmation_phrase"))
        keep_default_admin = request.form.get("keep_default_admin") == "1"
        current_admin_email = clean_text(getattr(current_user, "email", "")).lower()

        if confirmation_phrase != "RESET SYSTEM":
            flash("Confirmation phrase mismatch. System reset cancelled.", "danger")
            return redirect(url_for("admin_system_reset"))

        try:
            db.session.query(EventRSVP).delete(synchronize_session=False)
            db.session.query(TracerSurvey).delete(synchronize_session=False)
            db.session.query(AlumniProfile).delete(synchronize_session=False)
            db.session.query(Job).delete(synchronize_session=False)
            db.session.query(Event).delete(synchronize_session=False)
            db.session.query(PasswordReset).delete(synchronize_session=False)
            db.session.query(Notification).delete(synchronize_session=False)
            db.session.query(SystemLog).delete(synchronize_session=False)
            db.session.query(Report).delete(synchronize_session=False)

            if keep_default_admin:
                db.session.query(User).filter(User.email != default_admin_email).delete(
                    synchronize_session=False
                )
            else:
                db.session.query(User).delete(synchronize_session=False)

            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("System reset failed. No changes were finalized.", "danger")
            return redirect(url_for("admin_system_reset"))

        if keep_default_admin:
            default_admin = User.query.filter_by(email=default_admin_email).first()
            if not default_admin:
                default_admin = User(email=default_admin_email, role=UserRole.ADMIN)
                default_admin.set_password("admin123")
                db.session.add(default_admin)
            default_admin.role = UserRole.ADMIN
            default_admin.otp_verified = True
            default_admin.approval_status = APPROVAL_APPROVED
            default_admin.approval_requested_at = datetime.utcnow()
            default_admin.approved_at = datetime.utcnow()
            default_admin.approved_by_user_id = None
            default_admin.approval_notes = "Default admin retained after reset."
            default_admin.is_active = True
            db.session.commit()

        if keep_default_admin:
            flash(
                "System reset complete. Default admin account was retained.",
                "success",
            )
        else:
            flash("System reset complete. All accounts and records were cleared.", "success")

        current_admin_retained = keep_default_admin and current_admin_email == default_admin_email
        if not current_admin_retained:
            logout_user()
            clear_active_session()
            clear_otp_context()
            flash("You were signed out after reset. Please sign in again.", "info")
            return redirect(url_for("index"))

        return redirect(url_for("admin_system_reset"))

    return render_template("admin_system_reset.html", default_admin_email=default_admin_email)


@app.route("/alumni")
def alumni_directory():
    search = request.args.get("search", "").strip()
    degree_filter = request.args.get("degree", "").strip()
    year_filter = request.args.get("year", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = app.config.get("ITEMS_PER_PAGE", 10)

    query = AlumniProfile.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                AlumniProfile.first_name.ilike(like),
                AlumniProfile.last_name.ilike(like),
                AlumniProfile.degree.ilike(like),
                AlumniProfile.current_employer.ilike(like),
            )
        )

    if degree_filter:
        query = query.filter(AlumniProfile.degree == degree_filter)

    if year_filter:
        query = query.filter(AlumniProfile.year_graduated == parse_int(year_filter))

    alumni = query.order_by(AlumniProfile.last_name.asc()).paginate(
        page=page, per_page=per_page
    )

    degrees = [
        row[0]
        for row in db.session.query(AlumniProfile.degree)
        .filter(AlumniProfile.degree.is_not(None))
        .distinct()
        .order_by(AlumniProfile.degree.asc())
        .all()
    ]
    years = [
        row[0]
        for row in db.session.query(AlumniProfile.year_graduated)
        .filter(AlumniProfile.year_graduated.is_not(None))
        .distinct()
        .order_by(AlumniProfile.year_graduated.desc())
        .all()
    ]

    return render_template(
        "alumni.html",
        alumni=alumni,
        search=search,
        degree_filter=degree_filter,
        year_filter=year_filter,
        degrees=degrees,
        years=years,
    )


@app.route("/jobs")
def jobs():
    search = request.args.get("search", "").strip()
    job_type = request.args.get("job_type", "").strip()
    location = request.args.get("location", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = app.config.get("ITEMS_PER_PAGE", 10)

    query = Job.query.filter(Job.is_active.is_(True))

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Job.title.ilike(like), Job.company.ilike(like)))
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    jobs_page = query.order_by(Job.posted_date.desc()).paginate(
        page=page, per_page=per_page
    )

    for job in jobs_page.items:
        job.salary_display = format_salary_range(job.salary_min, job.salary_max)

    return render_template(
        "jobs.html",
        jobs=jobs_page,
        search=search,
        job_type=job_type,
        location=location,
    )


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    job.salary_display = format_salary_range(job.salary_min, job.salary_max)
    return render_template("job_detail.html", job=job)


@app.route("/events")
def events():
    event_type = request.args.get("type", "").strip()
    now = datetime.utcnow()
    query = Event.query.filter(Event.is_published.is_(True), Event.event_date >= now)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    events_list = query.order_by(Event.event_date.asc()).all()
    event_ids = [event.id for event in events_list]

    rsvp_rows = []
    if event_ids:
        rsvp_rows = (
            db.session.query(EventRSVP.event_id, EventRSVP.status, func.count(EventRSVP.id))
            .filter(EventRSVP.event_id.in_(event_ids))
            .group_by(EventRSVP.event_id, EventRSVP.status)
            .all()
        )

    rsvp_counts = {
        event_id: {RSVP_ATTEND: 0, RSVP_MAYBE: 0, RSVP_NOT_ATTEND: 0}
        for event_id in event_ids
    }
    for event_id, status, count in rsvp_rows:
        if event_id in rsvp_counts and status in RSVP_STATUSES:
            rsvp_counts[event_id][status] = count

    user_rsvp_map = {}
    if (
        current_user.is_authenticated
        and to_role_slug(current_user.role, default=None) == "alumni"
        and event_ids
    ):
        user_rows = EventRSVP.query.filter(
            EventRSVP.user_id == current_user.id,
            EventRSVP.event_id.in_(event_ids),
        ).all()
        user_rsvp_map = {row.event_id: row.status for row in user_rows}

    return render_template(
        "events.html",
        events=events_list,
        event_type=event_type,
        rsvp_counts=rsvp_counts,
        user_rsvp_map=user_rsvp_map,
    )


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    role_value = to_role_slug(getattr(current_user, "role", None), default=None)
    if not event.is_published and role_value != "admin":
        flash("Event not available.", "warning")
        return redirect(url_for("events"))
    rsvp_rows = (
        db.session.query(EventRSVP.status, func.count(EventRSVP.id))
        .filter(EventRSVP.event_id == event.id)
        .group_by(EventRSVP.status)
        .all()
    )
    rsvp_counts = {RSVP_ATTEND: 0, RSVP_MAYBE: 0, RSVP_NOT_ATTEND: 0}
    for status, count in rsvp_rows:
        if status in RSVP_STATUSES:
            rsvp_counts[status] = count

    user_rsvp = None
    if current_user.is_authenticated and role_value == "alumni":
        record = EventRSVP.query.filter_by(event_id=event.id, user_id=current_user.id).first()
        user_rsvp = record.status if record else None

    return render_template(
        "event_detail.html",
        event=event,
        rsvp_counts=rsvp_counts,
        user_rsvp=user_rsvp,
    )


@app.route("/events/<int:event_id>/rsvp", methods=["POST"])
@role_required("alumni")
def event_rsvp(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.is_published:
        flash("This event is not available for RSVP.", "warning")
        return redirect(url_for("events"))

    status = clean_text(request.form.get("status")).lower()
    if status not in RSVP_STATUSES:
        flash("Please select a valid RSVP response.", "danger")
        return redirect(url_for("event_detail", event_id=event.id))

    existing = EventRSVP.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if existing:
        existing.status = status
    else:
        db.session.add(EventRSVP(event_id=event.id, user_id=current_user.id, status=status))

    if safe_commit("Unable to save RSVP right now. Please try again."):
        flash("Your RSVP response has been saved.", "success")
    return redirect(url_for("event_detail", event_id=event.id))


@app.route("/alumni-module")
@role_required("alumni")
def alumni_module():
    return redirect(url_for("alumni_module_dashboard"))


@app.route("/alumni-module/dashboard")
@role_required("alumni")
def alumni_module_dashboard():
    profile = get_or_create_alumni_profile()

    personal_completion = calculate_section_completion(
        [
            profile.first_name,
            profile.last_name,
            current_user.email,
            profile.gender,
            profile.phone,
            profile.date_of_birth,
            profile.address,
            profile.city,
            profile.province,
        ]
    )
    education_completion = calculate_section_completion(
        [
            profile.degree,
            profile.student_id,
            profile.year_graduated,
            profile.honors,
            profile.activities,
        ]
    )
    family_completion = calculate_section_completion(
        [
            profile.civil_status,
            profile.father_name,
            profile.father_contact,
            profile.mother_name,
            profile.mother_contact,
            profile.guardian_name,
            profile.guardian_contact,
        ]
    )
    enrollment_completion = calculate_section_completion(
        [
            profile.enrollment_status,
            profile.enrolled_program,
            profile.enrollment_date,
            profile.expected_completion_date,
            profile.current_employer,
            profile.job_position,
            profile.work_location,
        ]
    )
    overall_completion = int(
        round(
            (
                personal_completion
                + education_completion
                + family_completion
                + enrollment_completion
            )
            / 4
        )
    )

    return render_template(
        "alumni_module_dashboard.html",
        profile=profile,
        overall_completion=overall_completion,
        personal_completion=personal_completion,
        education_completion=education_completion,
        family_completion=family_completion,
        enrollment_completion=enrollment_completion,
    )


@app.route("/alumni-module/form", methods=["GET", "POST"])
@role_required("alumni")
def alumni_module_form():
    profile = get_or_create_alumni_profile()
    year_options = range(datetime.utcnow().year + 1, 1969, -1)

    if request.method == "POST":
        current_year = datetime.utcnow().year
        errors = []

        email = clean_text(request.form.get("email")).lower()
        first_name = clean_text(request.form.get("first_name"))
        last_name = clean_text(request.form.get("last_name"))
        middle_name = clean_text(request.form.get("middle_name")) or None
        civil_status = clean_text(request.form.get("civil_status")) or None
        gender = clean_text(request.form.get("gender")) or None
        date_of_birth_raw = clean_text(request.form.get("date_of_birth"))
        date_of_birth = parse_date(date_of_birth_raw)
        phone = clean_text(request.form.get("phone")) or None
        address = clean_text(request.form.get("address")) or None
        city = clean_text(request.form.get("city")) or None
        province = clean_text(request.form.get("province")) or None
        facebook_link = clean_text(request.form.get("facebook_link")) or None
        linkedin_link = clean_text(request.form.get("linkedin_link")) or None

        degree = clean_text(request.form.get("degree"))
        student_id = clean_text(request.form.get("student_id")) or None
        year_graduated_raw = clean_text(request.form.get("year_graduated"))
        year_graduated = parse_int(year_graduated_raw)
        honors = clean_text(request.form.get("honors")) or None
        activities = clean_text(request.form.get("activities")) or None

        father_name = clean_text(request.form.get("father_name")) or None
        father_contact = clean_text(request.form.get("father_contact")) or None
        mother_name = clean_text(request.form.get("mother_name")) or None
        mother_contact = clean_text(request.form.get("mother_contact")) or None
        guardian_name = clean_text(request.form.get("guardian_name")) or None
        guardian_contact = clean_text(request.form.get("guardian_contact")) or None

        employment_status = clean_text(request.form.get("employment_status")) or "student"
        enrollment_status = clean_text(request.form.get("enrollment_status")) or None
        enrolled_program = clean_text(request.form.get("enrolled_program")) or None
        enrollment_date_raw = clean_text(request.form.get("enrollment_date"))
        enrollment_date = parse_date(enrollment_date_raw)
        expected_completion_date_raw = clean_text(
            request.form.get("expected_completion_date")
        )
        expected_completion_date = parse_date(expected_completion_date_raw)
        current_employer = clean_text(request.form.get("current_employer")) or None
        job_position = clean_text(request.form.get("job_position")) or None
        work_location = clean_text(request.form.get("work_location")) or None
        skills = clean_text(request.form.get("skills")) or None
        certifications = clean_text(request.form.get("certifications")) or None
        volunteer_work = clean_text(request.form.get("volunteer_work")) or None
        job_description = clean_text(request.form.get("job_description")) or None

        if not first_name or not last_name:
            errors.append("First name and last name are required.")
        if not degree or degree == "__other__":
            errors.append("Please provide a valid degree/course.")
        if year_graduated is None:
            errors.append("Year graduated is required.")
        elif not (1970 <= year_graduated <= current_year + 1):
            errors.append(
                f"Year graduated must be between 1970 and {current_year + 1}."
            )
        if not email:
            errors.append("Email address is required.")
        elif not is_valid_email(email):
            errors.append("Please provide a valid email address.")
        else:
            with db.session.no_autoflush:
                duplicate_user = User.query.filter(
                    User.email == email,
                    User.id != current_user.id,
                ).first()
            if duplicate_user:
                errors.append("This email is already in use by another account.")

        if date_of_birth_raw and not date_of_birth:
            errors.append("Date of birth must use a valid date.")
        elif date_of_birth and date_of_birth > datetime.utcnow().date():
            errors.append("Date of birth cannot be in the future.")

        if enrollment_date_raw and not enrollment_date:
            errors.append("Enrollment date must use a valid date.")
        if expected_completion_date_raw and not expected_completion_date:
            errors.append("Expected completion date must use a valid date.")
        if (
            enrollment_date
            and expected_completion_date
            and expected_completion_date < enrollment_date
        ):
            errors.append(
                "Expected completion date cannot be earlier than enrollment date."
            )

        phone_fields = [
            ("Phone number", phone),
            ("Father contact number", father_contact),
            ("Mother contact number", mother_contact),
            ("Guardian contact number", guardian_contact),
        ]
        for label, value in phone_fields:
            if value and not is_valid_phone(value):
                errors.append(f"{label} is not in a valid format.")

        if student_id:
            with db.session.no_autoflush:
                duplicate_student_id = AlumniProfile.query.filter(
                    AlumniProfile.student_id == student_id,
                    AlumniProfile.id != profile.id,
                ).first()
            if duplicate_student_id:
                errors.append("Student ID is already assigned to another alumni profile.")

        profile.first_name = first_name
        profile.last_name = last_name
        profile.middle_name = middle_name
        profile.civil_status = civil_status
        profile.gender = gender
        profile.date_of_birth = date_of_birth
        profile.phone = phone
        profile.address = address
        profile.city = city
        profile.province = province
        profile.facebook_link = facebook_link
        profile.linkedin_link = linkedin_link
        profile.degree = degree
        profile.student_id = student_id
        profile.year_graduated = year_graduated
        profile.honors = honors
        profile.activities = activities
        profile.father_name = father_name
        profile.father_contact = father_contact
        profile.mother_name = mother_name
        profile.mother_contact = mother_contact
        profile.guardian_name = guardian_name
        profile.guardian_contact = guardian_contact
        profile.employment_status = employment_status
        profile.enrollment_status = enrollment_status
        profile.enrolled_program = enrolled_program
        profile.enrollment_date = enrollment_date
        profile.expected_completion_date = expected_completion_date
        profile.current_employer = current_employer
        profile.job_position = job_position
        profile.work_location = work_location
        profile.skills = skills
        profile.certifications = certifications
        profile.volunteer_work = volunteer_work
        profile.job_description = job_description

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "alumni_module_form.html",
                profile=profile,
                account_email=email,
                degree_options=degree_options_for(profile.degree),
                year_options=year_options,
            )

        remove_photo = request.form.get("remove_profile_photo") == "1"
        uploaded_photo = request.files.get("profile_photo")
        photos_to_delete = []

        if remove_photo and profile.profile_photo:
            photos_to_delete.append(profile.profile_photo)
            profile.profile_photo = None

        if uploaded_photo and clean_text(uploaded_photo.filename):
            previous_photo = profile.profile_photo
            saved_photo, photo_error = save_profile_photo_upload(uploaded_photo)
            if photo_error:
                flash(photo_error, "danger")
                return render_template(
                    "alumni_module_form.html",
                    profile=profile,
                    account_email=email,
                    degree_options=degree_options_for(profile.degree),
                    year_options=year_options,
                )
            if previous_photo and previous_photo != saved_photo:
                photos_to_delete.append(previous_photo)
            profile.profile_photo = saved_photo

        current_user.email = email
        profile.profile_completed = calculate_profile_completed(profile)

        if safe_commit("Unable to save alumni module details right now."):
            for path in set(photos_to_delete):
                delete_profile_photo_file(path)
            flash("Alumni module details saved successfully.", "success")
            return redirect(url_for("alumni_module_form"))

    return render_template(
        "alumni_module_form.html",
        profile=profile,
        account_email=current_user.email,
        degree_options=degree_options_for(profile.degree),
        year_options=year_options,
    )


@app.route("/alumni-module/profile")
@role_required("alumni")
def alumni_module_profile():
    profile = current_user.profile
    if not profile:
        flash("Please complete the alumni form first.", "warning")
        return redirect(url_for("alumni_module_form"))
    return render_template("alumni_module_profile.html", profile=profile)


@app.route("/alumni-module/photo/delete", methods=["POST"])
@role_required("alumni")
def alumni_module_delete_photo():
    profile = current_user.profile
    if not profile:
        flash("No profile record found.", "warning")
        return redirect(url_for("alumni_module_form"))

    if profile.profile_photo:
        old_photo_path = profile.profile_photo
        profile.profile_photo = None
        if safe_commit("Unable to remove profile photo right now."):
            delete_profile_photo_file(old_photo_path)
            flash("Profile photo removed.", "success")
    else:
        flash("No profile photo to remove.", "info")

    return redirect(url_for("alumni_module_form"))


@app.route("/profile", methods=["GET", "POST"])
@role_required("alumni")
def profile():
    profile = current_user.profile
    year_options = range(datetime.utcnow().year + 1, 1969, -1)
    if not profile:
        profile = AlumniProfile(
            user=current_user,
            first_name="",
            last_name="",
            degree="",
        )
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        profile.first_name = request.form.get("first_name", "").strip()
        profile.last_name = request.form.get("last_name", "").strip()
        profile.middle_name = request.form.get("middle_name", "").strip() or None
        profile.gender = request.form.get("gender", "").strip() or None
        profile.date_of_birth = parse_date(request.form.get("date_of_birth"))
        profile.phone = request.form.get("phone", "").strip() or None
        profile.address = request.form.get("address", "").strip() or None
        profile.city = request.form.get("city", "").strip() or None
        profile.province = request.form.get("province", "").strip() or None
        profile.facebook_link = request.form.get("facebook_link", "").strip() or None
        profile.linkedin_link = request.form.get("linkedin_link", "").strip() or None
        profile.degree = request.form.get("degree", "").strip()
        profile.student_id = request.form.get("student_id", "").strip() or None
        profile.year_graduated = parse_int(request.form.get("year_graduated"))
        profile.honors = request.form.get("honors", "").strip() or None
        profile.activities = request.form.get("activities", "").strip() or None
        profile.employment_status = request.form.get("employment_status", "").strip() or "student"
        profile.current_employer = request.form.get("current_employer", "").strip() or None
        profile.job_position = request.form.get("job_position", "").strip() or None
        profile.employment_duration = (
            request.form.get("employment_duration", "").strip() or None
        )
        profile.salary_range = request.form.get("salary_range", "").strip() or None
        profile.work_location = request.form.get("work_location", "").strip() or None
        profile.job_description = request.form.get("job_description", "").strip() or None
        profile.skills = request.form.get("skills", "").strip() or None
        profile.certifications = request.form.get("certifications", "").strip() or None
        profile.volunteer_work = request.form.get("volunteer_work", "").strip() or None

        validation_errors = []
        raw_dob = clean_text(request.form.get("date_of_birth"))
        if raw_dob and not profile.date_of_birth:
            validation_errors.append("Date of birth must use a valid date.")
        elif profile.date_of_birth and profile.date_of_birth > datetime.utcnow().date():
            validation_errors.append("Date of birth cannot be in the future.")
        if profile.phone and not is_valid_phone(profile.phone):
            validation_errors.append("Phone number is not in a valid format.")
        if validation_errors:
            for message in validation_errors:
                flash(message, "danger")
            return render_template(
                "profile.html",
                profile=profile,
                degree_options=degree_options_for(profile.degree),
                year_options=year_options,
            )

        if not profile.first_name or not profile.last_name or not profile.degree:
            flash("First name, last name, and degree are required.", "danger")
            return render_template(
                "profile.html",
                profile=profile,
                degree_options=degree_options_for(profile.degree),
                year_options=year_options,
            )

        profile.profile_completed = calculate_profile_completed(profile)
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        profile=profile,
        degree_options=degree_options_for(profile.degree),
        year_options=year_options,
    )


@app.route("/my-profile")
@role_required("alumni")
def my_profile():
    profile = current_user.profile
    if not profile:
        flash("Please complete your profile first.", "warning")
        return redirect(url_for("profile"))
    return render_template("my_profile.html", profile=profile)


@app.route("/my-survey")
@role_required("alumni")
def my_survey():
    profile = current_user.profile
    if not profile:
        flash("Please complete your profile first.", "warning")
        return redirect(url_for("profile"))
    survey = (
        TracerSurvey.query.filter_by(alumni_id=profile.id)
        .order_by(TracerSurvey.created_at.desc())
        .first()
    )
    return render_template("my_survey.html", survey=survey)


@app.route("/survey", methods=["GET", "POST"])
@role_required("alumni")
def survey():
    profile = current_user.profile
    if not profile:
        flash("Please complete your profile before taking the survey.", "warning")
        return redirect(url_for("profile"))

    if request.method == "POST":
        required_fields = app.config.get("SURVEY_REQUIRED_FIELDS", [])
        missing = [field for field in required_fields if not request.form.get(field)]
        if missing:
            flash("Please complete the required survey fields.", "danger")
            return render_template("survey.html")

        survey_record = (
            TracerSurvey.query.filter_by(alumni_id=profile.id)
            .order_by(TracerSurvey.created_at.desc())
            .first()
        )

        if not survey_record:
            survey_record = TracerSurvey(alumni_id=profile.id)
            db.session.add(survey_record)

        survey_record.education_quality = parse_int(
            request.form.get("education_quality")
        )
        survey_record.curriculum_relevance = parse_int(
            request.form.get("curriculum_relevance")
        )
        survey_record.facilities_rating = parse_int(
            request.form.get("facilities_rating")
        )
        survey_record.instructor_quality = parse_int(
            request.form.get("instructor_quality")
        )
        survey_record.research_opportunities = parse_int(
            request.form.get("research_opportunities")
        )
        survey_record.competency_technical = parse_int(
            request.form.get("competency_technical")
        )
        survey_record.competency_soft = parse_int(
            request.form.get("competency_soft")
        )
        survey_record.competency_problem = parse_int(
            request.form.get("competency_problem")
        )
        survey_record.competency_communication = parse_int(
            request.form.get("competency_communication")
        )
        survey_record.competency_leadership = parse_int(
            request.form.get("competency_leadership")
        )
        survey_record.is_employed = request.form.get("is_employed") == "yes"
        survey_record.job_related = request.form.get("job_related") == "yes"
        survey_record.job_searching = request.form.get("job_searching") == "yes"
        survey_record.employment_sector = (
            request.form.get("employment_sector", "").strip() or None
        )
        survey_record.overall_satisfaction = parse_int(
            request.form.get("overall_satisfaction")
        )
        survey_record.recommend_rating = parse_int(
            request.form.get("recommend_rating")
        )
        survey_record.suggestions = request.form.get("suggestions", "").strip() or None

        profile.survey_completed = True
        db.session.commit()
        flash("Survey submitted successfully.", "success")
        return redirect(url_for("my_survey"))

    return render_template("survey.html")


@app.route("/admin/alumni")
@role_required("admin", "registrar")
def admin_alumni():
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = app.config.get("ITEMS_PER_PAGE", 10)

    query = AlumniProfile.query
    if search:
        like = f"%{search}%"
        query = query.join(User).filter(
            or_(
                AlumniProfile.first_name.ilike(like),
                AlumniProfile.last_name.ilike(like),
                AlumniProfile.degree.ilike(like),
                User.email.ilike(like),
            )
        )

    alumni = query.order_by(AlumniProfile.created_at.desc()).paginate(
        page=page, per_page=per_page
    )

    return render_template("admin_alumni.html", alumni=alumni, search=search)


@app.route("/admin/alumni/edit/<int:alumni_id>", methods=["GET", "POST"])
@role_required("admin", "registrar")
def admin_edit_alumni(alumni_id):
    profile = AlumniProfile.query.get_or_404(alumni_id)

    if request.method == "POST":
        for field in [
            "first_name",
            "last_name",
            "middle_name",
            "gender",
            "phone",
            "address",
            "city",
            "province",
            "degree",
            "employment_status",
            "current_employer",
            "job_position",
            "salary_range",
            "skills",
        ]:
            if field in request.form:
                setattr(profile, field, request.form.get(field) or None)

        if "year_graduated" in request.form:
            profile.year_graduated = parse_int(request.form.get("year_graduated"))

        profile.profile_completed = calculate_profile_completed(profile)
        db.session.commit()
        flash("Alumni profile updated.", "success")
        return redirect(url_for("admin_alumni"))

    return render_template(
        "admin_edit_alumni.html",
        profile=profile,
        degree_options=degree_options_for(profile.degree),
        year_options=range(datetime.utcnow().year + 1, 1969, -1),
    )


@app.route("/admin/alumni/delete/<int:alumni_id>", methods=["POST"])
@role_required("admin")
def admin_delete_alumni(alumni_id):
    profile = AlumniProfile.query.get_or_404(alumni_id)
    user = profile.user
    db.session.delete(profile)
    if user and to_role_slug(user.role, default="alumni") == "alumni":
        db.session.delete(user)
    db.session.commit()
    flash("Alumni deleted.", "success")
    return redirect(url_for("admin_alumni"))


@app.route("/admin/surveys")
@role_required("admin", "director")
def admin_surveys():
    surveys_data = (
        db.session.query(TracerSurvey, AlumniProfile)
        .join(AlumniProfile, TracerSurvey.alumni_id == AlumniProfile.id)
        .order_by(TracerSurvey.created_at.desc())
        .all()
    )
    return render_template("admin_surveys.html", surveys_data=surveys_data)


@app.route("/admin/surveys/delete/<int:survey_id>", methods=["POST"])
@role_required("admin")
def admin_delete_survey(survey_id):
    survey_record = TracerSurvey.query.get_or_404(survey_id)
    db.session.delete(survey_record)
    db.session.commit()
    flash("Survey deleted.", "success")
    return redirect(url_for("admin_surveys"))


@app.route("/admin/jobs")
@role_required("admin")
def admin_jobs():
    jobs_list = Job.query.order_by(Job.posted_date.desc()).all()
    return render_template("admin_jobs.html", jobs=jobs_list)


@app.route("/admin/jobs/add", methods=["GET", "POST"])
@role_required("admin")
def admin_add_job():
    if request.method == "POST":
        title = clean_text(request.form.get("title"))
        company = clean_text(request.form.get("company"))
        if not title or not company:
            flash("Job title and company are required.", "danger")
            return render_template("admin_edit_job.html", job=None)

        job = Job(
            title=title,
            company=company,
            description=request.form.get("description", "").strip() or None,
            requirements=request.form.get("requirements", "").strip() or None,
            location=request.form.get("location", "").strip() or None,
            job_type=request.form.get("job_type", "").strip() or "full-time",
            category=request.form.get("category", "").strip() or None,
            salary_min=parse_int(request.form.get("salary_min")),
            salary_max=parse_int(request.form.get("salary_max")),
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        flash("Job created.", "success")
        return redirect(url_for("admin_jobs"))
    return render_template("admin_edit_job.html", job=None)


@app.route("/admin/jobs/edit/<int:job_id>", methods=["GET", "POST"])
@role_required("admin")
def admin_edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == "POST":
        job.title = clean_text(request.form.get("title"))
        job.company = clean_text(request.form.get("company"))
        if not job.title or not job.company:
            flash("Job title and company are required.", "danger")
            return render_template("admin_edit_job.html", job=job)

        job.description = request.form.get("description", "").strip() or None
        job.requirements = request.form.get("requirements", "").strip() or None
        job.location = request.form.get("location", "").strip() or None
        job.job_type = request.form.get("job_type", "").strip() or job.job_type
        job.category = request.form.get("category", "").strip() or None
        job.salary_min = parse_int(request.form.get("salary_min"))
        job.salary_max = parse_int(request.form.get("salary_max"))
        db.session.commit()
        flash("Job updated.", "success")
        return redirect(url_for("admin_jobs"))
    return render_template("admin_edit_job.html", job=job)


@app.route("/admin/jobs/delete/<int:job_id>", methods=["POST"])
@role_required("admin")
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash("Job deleted.", "success")
    return redirect(url_for("admin_jobs"))


@app.route("/admin/events")
@role_required("admin", "osa")
def admin_events():
    events_list = Event.query.order_by(Event.event_date.desc()).all()
    event_ids = [event.id for event in events_list]
    rsvp_rows = []
    if event_ids:
        rsvp_rows = (
            db.session.query(EventRSVP.event_id, EventRSVP.status, func.count(EventRSVP.id))
            .filter(EventRSVP.event_id.in_(event_ids))
            .group_by(EventRSVP.event_id, EventRSVP.status)
            .all()
        )

    rsvp_counts = {
        event_id: {RSVP_ATTEND: 0, RSVP_MAYBE: 0, RSVP_NOT_ATTEND: 0}
        for event_id in event_ids
    }
    for event_id, status, count in rsvp_rows:
        if event_id in rsvp_counts and status in RSVP_STATUSES:
            rsvp_counts[event_id][status] = count

    return render_template("admin_events.html", events=events_list, rsvp_counts=rsvp_counts)


@app.route("/admin/events/add", methods=["GET", "POST"])
@role_required("admin", "osa")
def admin_add_event():
    if request.method == "POST":
        title = clean_text(request.form.get("title"))
        event_date = parse_datetime_local(request.form.get("event_date"))
        if not title or not event_date:
            flash("Event title and date are required.", "danger")
            return render_template("admin_edit_event.html", event=None)

        event = Event(
            title=title,
            description=request.form.get("description", "").strip() or None,
            event_type=request.form.get("event_type", "").strip() or None,
            event_date=event_date,
            location=request.form.get("location", "").strip() or None,
            venue=request.form.get("venue", "").strip() or None,
            organizer=request.form.get("organizer", "").strip() or None,
            contact_email=request.form.get("contact_email", "").strip() or None,
            is_published=True,
        )
        db.session.add(event)
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("admin_events"))
    return render_template("admin_edit_event.html", event=None)


@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
@role_required("admin", "osa")
def admin_edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == "POST":
        event.title = clean_text(request.form.get("title"))
        parsed_event_date = parse_datetime_local(request.form.get("event_date"))
        if not event.title or not parsed_event_date:
            flash("Event title and date are required.", "danger")
            return render_template("admin_edit_event.html", event=event)

        event.description = request.form.get("description", "").strip() or None
        event.event_type = request.form.get("event_type", "").strip() or None
        event.event_date = parsed_event_date
        event.location = request.form.get("location", "").strip() or None
        event.venue = request.form.get("venue", "").strip() or None
        event.organizer = request.form.get("organizer", "").strip() or None
        event.contact_email = request.form.get("contact_email", "").strip() or None
        event.is_published = True
        db.session.commit()
        flash("Event updated.", "success")
        return redirect(url_for("admin_events"))
    return render_template("admin_edit_event.html", event=event)


@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@role_required("admin", "osa")
def admin_delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "success")
    return redirect(url_for("admin_events"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            reset_record = PasswordReset(
                user_id=user.id,
                token=token,
                used=False,
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            db.session.add(reset_record)
            db.session.commit()
            reset_link = url_for("reset_password", token=token, _external=True)
            print(f"Password reset link for {email}: {reset_link}")
            return render_template("forgot_password.html", reset_link=reset_link, success_message="Reset link generated!")
        
        flash("Email not found.", "warning")
    
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset_record = PasswordReset.query.filter_by(token=token, used=False).first()
    if not reset_record or reset_record.expires_at < datetime.utcnow():
        flash("Reset link is invalid or expired.", "danger")
        return redirect(url_for("forgot_password"))

    target_user = db.session.get(User, reset_record.user_id)
    if not target_user:
        flash("Account not found.", "danger")
        return redirect(url_for("forgot_password"))
    target_role = to_role_slug(target_user.role, default="alumni")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token, role_slug=target_role)

        target_user.set_password(password)
        target_user.is_active = True
        reset_record.used = True
        db.session.commit()
        flash("Password reset successfully. Please login.", "success")
        return redirect(role_login_url(target_role))

    return render_template("reset_password.html", token=token, role_slug=target_role)


@app.errorhandler(403)
def forbidden(_error):
    return (
        render_template("error.html", error_code=403, message="Access forbidden."),
        403,
    )


@app.errorhandler(404)
def page_not_found(_error):
    return (
        render_template("error.html", error_code=404, message="Page not found."),
        404,
    )


@app.errorhandler(500)
def server_error(_error):
    return (
        render_template(
            "error.html", error_code=500, message="Unexpected server error."
        ),
        500,
    )

# ... all your other functions ...

def init_app():
    with app.app_context():
        db.create_all()
        ensure_sqlite_schema()
        fix_invalid_roles()
        seed_users()
        ensure_user_approval_integrity()

if __name__ == "__main__":
    init_app()
    app.run(debug=True, host="0.0.0.0", port=5000)

