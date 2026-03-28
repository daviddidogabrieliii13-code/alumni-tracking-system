from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import event
import enum
import hashlib
import hmac

db = SQLAlchemy()

class UserRole(enum.Enum):
    ALUMNI = 'alumni'
    ADMIN = 'admin'
    DIRECTOR = 'director'
    REGISTRAR = 'registrar'
    OSA = 'osa'

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.ALUMNI, nullable=False)
    otp_code_hash = db.Column(db.String(256))
    otp_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    approval_status = db.Column(db.String(20), default='approved', nullable=False)
    approval_requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approval_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    profile = db.relationship('AlumniProfile', backref='user', uselist=False)
    logs = db.relationship('SystemLog', backref='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_otp(self, otp):
        self.otp_code_hash = hashlib.sha256(otp.encode()).hexdigest()
    
    def verify_otp(self, otp):
        if not otp or not self.otp_code_hash:
            return False
        provided_hash = hashlib.sha256(otp.encode()).hexdigest()
        return hmac.compare_digest(provided_hash, self.otp_code_hash)

class AlumniProfile(db.Model):
    __tablename__ = 'alumni_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    civil_status = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    facebook_link = db.Column(db.String(500))
    linkedin_link = db.Column(db.String(500))
    
    # Educational Background  
    student_id = db.Column(db.String(50), unique=True)
    degree = db.Column(db.String(200), nullable=False)
    year_graduated = db.Column(db.Integer)
    honors = db.Column(db.Text)
    activities = db.Column(db.Text)

    # Family Information
    father_name = db.Column(db.String(120))
    father_contact = db.Column(db.String(30))
    mother_name = db.Column(db.String(120))
    mother_contact = db.Column(db.String(30))
    guardian_name = db.Column(db.String(120))
    guardian_contact = db.Column(db.String(30))

    # Enrollment Information
    enrollment_status = db.Column(db.String(100))
    enrolled_program = db.Column(db.String(200))
    enrollment_date = db.Column(db.Date)
    expected_completion_date = db.Column(db.Date)
    
    # Employment Information
    employment_status = db.Column(db.String(50), default='student')
    current_employer = db.Column(db.String(200))
    job_position = db.Column(db.String(200))
    employment_duration = db.Column(db.String(50))
    salary_range = db.Column(db.String(100))
    work_location = db.Column(db.String(200))
    job_description = db.Column(db.Text)
    
    # Skills & Additional
    skills = db.Column(db.Text)
    certifications = db.Column(db.Text)
    volunteer_work = db.Column(db.Text)
    
    # Status
    profile_photo = db.Column(db.String(500))
    profile_completed = db.Column(db.Boolean, default=False)
    survey_completed = db.Column(db.Boolean, default=False)  # Added for app.py
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    surveys = db.relationship('TracerSurvey', backref='alumni_profile', cascade='all, delete-orphan')

class TracerSurvey(db.Model):
    __tablename__ = 'survey_response'  # Match app.py expectations
    
    id = db.Column(db.Integer, primary_key=True)
    alumni_id = db.Column(db.Integer, db.ForeignKey('alumni_profile.id'), nullable=False)
    
    # Educational Experience
    education_quality = db.Column(db.Integer)  # 1-5
    curriculum_relevance = db.Column(db.Integer)
    facilities_rating = db.Column(db.Integer)
    instructor_quality = db.Column(db.Integer)
    research_opportunities = db.Column(db.Integer)
    
    # Competency Assessment
    competency_technical = db.Column(db.Integer)
    competency_soft = db.Column(db.Integer)
    competency_problem = db.Column(db.Integer)
    competency_communication = db.Column(db.Integer)
    competency_leadership = db.Column(db.Integer)
    
    # Employment Status
    is_employed = db.Column(db.Boolean)
    job_related = db.Column(db.Boolean)
    job_searching = db.Column(db.Boolean)
    employment_sector = db.Column(db.String(100))
    
    # Overall Satisfaction
    overall_satisfaction = db.Column(db.Integer)
    recommend_rating = db.Column(db.Integer)
    suggestions = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Missing models used in app.py
class Job(db.Model):
    __tablename__ = 'job'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    location = db.Column(db.String(200))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    job_type = db.Column(db.String(50))
    category = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.Index('ix_job_active_posted', 'is_active', 'posted_date'),)

class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(100))
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    venue = db.Column(db.String(200))
    organizer = db.Column(db.String(200))
    contact_email = db.Column(db.String(120))
    is_published = db.Column(db.Boolean, default=False)
    
    __table_args__ = (db.Index('ix_event_date_published', 'event_date', 'is_published'),)

class EventRSVP(db.Model):
    __tablename__ = 'event_rsvp'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # attend / maybe / not_attend
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('rsvps', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('event_rsvps', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_rsvp_event_user'),
        db.Index('ix_event_rsvp_status', 'status'),
    )

class PasswordReset(db.Model):
    __tablename__ = 'password_reset'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False, index=True)
    used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemLog(db.Model):
    __tablename__ = 'system_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    device = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'report'
    
    id = db.Column(db.Integer, primary_key=True)
    generated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    report_type = db.Column(db.String(50))
    parameters = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500))

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    notification_type = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Auto-update timestamps (optional listener removed to avoid SQLAlchemy version issues)


