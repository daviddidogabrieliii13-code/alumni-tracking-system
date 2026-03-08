import re
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import secrets
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='alumni')  # alumni, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    profile = db.relationship('AlumniProfile', backref='user', uselist=False, cascade='all, delete-orphan')

class AlumniProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    profile_photo = db.Column(db.String(200))
    facebook_link = db.Column(db.String(200))
    linkedin_link = db.Column(db.String(200))
    
    # Educational Background
    student_id = db.Column(db.String(50))
    degree = db.Column(db.String(100), nullable=False)
    year_graduated = db.Column(db.Integer)
    honors = db.Column(db.String(200))
    activities = db.Column(db.Text)
    
    # Employment Information
    employment_status = db.Column(db.String(50))  # employed, unemployed, self-employed, student
    current_employer = db.Column(db.String(200))
    job_position = db.Column(db.String(100))
    employment_duration = db.Column(db.String(50))
    salary_range = db.Column(db.String(50))
    work_location = db.Column(db.String(200))
    job_description = db.Column(db.Text)
    
    # Additional
    skills = db.Column(db.Text)
    certifications = db.Column(db.Text)
    volunteer_work = db.Column(db.Text)
    
    # Status
    profile_completed = db.Column(db.Boolean, default=False)
    survey_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alumni_id = db.Column(db.Integer, db.ForeignKey('alumni_profile.id'), nullable=False)
    
    # Relationship
    alumni_profile = db.relationship('AlumniProfile', backref='survey_responses')
    
    # Educational Experience
    education_quality = db.Column(db.Integer)  # 1-5
    curriculum_relevance = db.Column(db.Integer)  # 1-5
    facilities_rating = db.Column(db.Integer)  # 1-5
    instructor_quality = db.Column(db.Integer)  # 1-5
    research_opportunities = db.Column(db.Integer)  # 1-5
    
    # Competency Assessment
    competency_technical = db.Column(db.Integer)  # 1-5
    competency_soft = db.Column(db.Integer)  # 1-5
    competency_problem = db.Column(db.Integer)  # 1-5
    competency_communication = db.Column(db.Integer)  # 1-5
    competency_leadership = db.Column(db.Integer)  # 1-5
    
    # Employment Status
    is_employed = db.Column(db.Boolean)
    job_related = db.Column(db.Boolean)
    job_searching = db.Column(db.Boolean)
    employment_sector = db.Column(db.String(100))
    
    # Overall Satisfaction
    overall_satisfaction = db.Column(db.Integer)  # 1-5
    recommend_rating = db.Column(db.Integer)  # 1-10
    suggestions = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    location = db.Column(db.String(100))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_display = db.Column(db.String(100))
    job_type = db.Column(db.String(50))  # full-time, part-time, contract
    category = db.Column(db.String(100))
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    apply_link = db.Column(db.String(300))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50))  # gathering, career_fair, workshop, reunion
    event_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    venue = db.Column(db.String(200))
    image = db.Column(db.String(200))
    organizer = db.Column(db.String(100))
    contact_email = db.Column(db.String(120))
    registration_required = db.Column(db.Boolean, default=False)
    max_attendees = db.Column(db.Integer)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    notification_type = db.Column(db.String(50))  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='password_resets')
# ==================== HELPERS ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_employment_rate():
    total = AlumniProfile.query.count()
    if total == 0:
        return 0
    employed = AlumniProfile.query.filter(
        AlumniProfile.employment_status.in_(['employed', 'self-employed'])
    ).count()
    return round((employed / total) * 100, 1)

def calculate_survey_response_rate():
    total = AlumniProfile.query.count()
    if total == 0:
        return 0
    completed = SurveyResponse.query.count()
    return round((completed / total) * 100, 1)

def validate_password_strength(password):
    """
    Validates password strength and returns (is_valid, message, strength_score)
    Strength requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long.", 0
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter (A-Z).", 0
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least 1 lowercase letter (a-z).", 0
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least 1 number (0-9).", 0
    
    special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least 1 special character (!@#$%^&*).", 0
    
    # Calculate strength score
    score = 0
    if len(password) >= 12: score += 1
    if len(password) >= 16: score += 1
    if re.search(r'[A-Z].*[A-Z]', password): score += 1  # Multiple uppercase
    if re.search(r'[a-z].*[a-z]', password): score += 1  # Multiple lowercase
    if re.search(r'[0-9].*[0-9]', password): score += 1  # Multiple numbers
    
    strength = "Weak"
    if score >= 3: strength = "Fair"
    if score >= 5: strength = "Good"
    if score >= 7: strength = "Strong"
    
    return True, f"Password strength: {strength}", score

def generate_strong_password(length=16):
    """Generate a strong random password"""
    import random
    import string
    
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one of each
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill rest with random characters
    all_chars = uppercase + lowercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # Shuffle
    random.shuffle(password)
    return ''.join(password)

# ==================== ROUTES ====================

@app.route('/')
def index():
    # Get statistics
    total_alumni = AlumniProfile.query.count()
    employed_count = AlumniProfile.query.filter(
        AlumniProfile.employment_status.in_(['employed', 'self-employed'])
    ).count()
    survey_responses = SurveyResponse.query.count()
    active_jobs = Job.query.filter_by(is_active=True).count()
    
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.utcnow(),
        Event.is_published == True
    ).order_by(Event.event_date).limit(3).all()
    
    return render_template('index.html',
                         total_alumni=total_alumni,
                         employed_count=employed_count,
                         survey_responses=survey_responses,
                         active_jobs=active_jobs,
                         upcoming_events=upcoming_events)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for contacting us! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# ==================== AUTH ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('analytics'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful! Welcome back!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('analytics'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        degree = request.form.get('degree')
        year_graduated = request.form.get('year_graduated')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered! Please login.', 'warning')
            return redirect(url_for('login'))
        
        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role='alumni'
        )
        db.session.add(user)
        db.session.commit()
        
       # Create profile
        profile = AlumniProfile(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        degree=degree,
        year_graduated=int(year_graduated) if year_graduated else None,
        employment_status='student',  # ← COMMA HERE
        profile_completed=True
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration successful! Please login to continue.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))
# ==================== FORGOT PASSWORD ====================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            
            # Delete old reset tokens for this user
            PasswordReset.query.filter_by(user_id=user.id).delete()
            
            reset = PasswordReset(user_id=user.id, token=token)
            db.session.add(reset)
            db.session.commit()
            
            # Show reset link (for testing)
            reset_url = url_for('reset_password', token=token, _external=True)
            flash(f'Password reset link: {reset_url}', 'info')
            flash('Copy the link above to reset your password', 'success')
        else:
            flash('If that email exists, a reset link has been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    reset = PasswordReset.query.filter_by(token=token, used=False).first()
    
    if not reset or reset.expires_at < datetime.utcnow():
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', token=token))
        
        # Update password
        user = User.query.get(reset.user_id)
        user.password_hash = generate_password_hash(password)
        
        # Mark token as used
        reset.used = True
        db.session.commit()
        
        flash('Password has been reset! Please login with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)
# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('analytics'))
    
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    
    # Calculate profile completion
    completed_fields = 0
    total_fields = 20
    if profile.first_name: completed_fields += 1
    if profile.last_name: completed_fields += 1
    if profile.gender: completed_fields += 1
    if profile.phone: completed_fields += 1
    if profile.address: completed_fields += 1
    if profile.degree: completed_fields += 1
    if profile.year_graduated: completed_fields += 1
    if profile.student_id: completed_fields += 1
    if profile.current_employer: completed_fields += 1
    if profile.job_position: completed_fields += 1
    if profile.employment_status: completed_fields += 1
    if profile.salary_range: completed_fields += 1
    if profile.work_location: completed_fields += 1
    if profile.skills: completed_fields += 1
    if profile.certifications: completed_fields += 1
    if profile.facebook_link: completed_fields += 1
    if profile.linkedin_link: completed_fields += 1
    if profile.activities: completed_fields += 1
    if profile.honors: completed_fields += 1
    if profile.volunteer_work: completed_fields += 1
    
    completion_percentage = int((completed_fields / total_fields) * 100)
    
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_date >= datetime.utcnow(),
        Event.is_published == True
    ).order_by(Event.event_date).limit(3).all()
    
    # Get recent jobs
    recent_jobs = Job.query.filter_by(is_active=True).order_by(Job.posted_date.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         profile=profile,
                         completion_percentage=completion_percentage,
                         upcoming_events=upcoming_events,
                         recent_jobs=recent_jobs)

# ==================== PROFILE ====================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        # Personal Information
        profile.first_name = request.form.get('first_name')
        profile.last_name = request.form.get('last_name')
        profile.middle_name = request.form.get('middle_name')
        profile.gender = request.form.get('gender')
        if request.form.get('date_of_birth'):
            profile.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
        profile.phone = request.form.get('phone')
        profile.address = request.form.get('address')
        profile.city = request.form.get('city')
        profile.province = request.form.get('province')
        profile.facebook_link = request.form.get('facebook_link')
        profile.linkedin_link = request.form.get('linkedin_link')
        
        # Educational Background
        profile.student_id = request.form.get('student_id')
        profile.degree = request.form.get('degree')
        profile.year_graduated = int(request.form.get('year_graduated')) if request.form.get('year_graduated') else None
        profile.honors = request.form.get('honors')
        profile.activities = request.form.get('activities')
        
        # Employment Information
        profile.employment_status = request.form.get('employment_status')
        profile.current_employer = request.form.get('current_employer')
        profile.job_position = request.form.get('job_position')
        profile.employment_duration = request.form.get('employment_duration')
        profile.salary_range = request.form.get('salary_range')
        profile.work_location = request.form.get('work_location')
        profile.job_description = request.form.get('job_description')
        
        # Additional
        profile.skills = request.form.get('skills')
        profile.certifications = request.form.get('certifications')
        profile.volunteer_work = request.form.get('volunteer_work')
        
        profile.profile_completed = True
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', profile=profile)

@app.route('/profile/photo', methods=['POST'])
@login_required
def upload_photo():
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file.filename:
            filename = secure_filename(f"profile_{current_user.id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile.profile_photo = filename
            db.session.commit()
            flash('Profile photo uploaded successfully!', 'success')
    
    return redirect(url_for('profile'))

# ==================== SURVEY ====================

@app.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    
    # Check if already completed
    existing_survey = SurveyResponse.query.filter_by(alumni_id=profile.id).first()
    if existing_survey:
        flash('You have already completed the survey. Thank you!', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        survey = SurveyResponse(alumni_id=profile.id)
        
        # Educational Experience
        survey.education_quality = int(request.form.get('education_quality', 0))
        survey.curriculum_relevance = int(request.form.get('curriculum_relevance', 0))
        survey.facilities_rating = int(request.form.get('facilities_rating', 0))
        survey.instructor_quality = int(request.form.get('instructor_quality', 0))
        survey.research_opportunities = int(request.form.get('research_opportunities', 0))
        
        # Competency Assessment
        survey.competency_technical = int(request.form.get('competency_technical', 0))
        survey.competency_soft = int(request.form.get('competency_soft', 0))
        survey.competency_problem = int(request.form.get('competency_problem', 0))
        survey.competency_communication = int(request.form.get('competency_communication', 0))
        survey.competency_leadership = int(request.form.get('competency_leadership', 0))
        
        # Employment Status
        survey.is_employed = request.form.get('is_employed') == 'yes'
        survey.job_related = request.form.get('job_related') == 'yes'
        survey.job_searching = request.form.get('job_searching') == 'yes'
        survey.employment_sector = request.form.get('employment_sector')
        
        # Overall Satisfaction
        survey.overall_satisfaction = int(request.form.get('overall_satisfaction', 0))
        survey.recommend_rating = int(request.form.get('recommend_rating', 0))
        survey.suggestions = request.form.get('suggestions')
        
        db.session.add(survey)
        
        profile.survey_completed = True
        db.session.commit()
        
        flash('Thank you for completing the Graduate Tracer Survey! Your feedback is valuable.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('survey.html', profile=profile)

# ==================== ANALYTICS ====================

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Basic Stats
    total_alumni = AlumniProfile.query.count()
    employment_rate = calculate_employment_rate()
    survey_rate = calculate_survey_response_rate()
    total_jobs = Job.query.count()
    
    # Employment Status Distribution
    employed = AlumniProfile.query.filter_by(employment_status='employed').count()
    unemployed = AlumniProfile.query.filter_by(employment_status='unemployed').count()
    self_employed = AlumniProfile.query.filter_by(employment_status='self-employed').count()
    student = AlumniProfile.query.filter_by(employment_status='student').count()
    
    # Graduate Years
    years = db.session.query(AlumniProfile.year_graduated).distinct().order_by(AlumniProfile.year_graduated).all()
    years = [y[0] for y in years if y[0]]
    graduates_by_year = []
    for year in years:
        count = AlumniProfile.query.filter_by(year_graduated=year).count()
        graduates_by_year.append(count)
    
    # Degrees Distribution
    degrees = db.session.query(AlumniProfile.degree).distinct().all()
    degrees = [d[0] for d in degrees if d[0]]
    degrees_count = []
    for degree in degrees:
        count = AlumniProfile.query.filter_by(degree=degree).count()
        degrees_count.append(count)
    
    # Survey Average Ratings
    surveys = SurveyResponse.query.all()
    avg_education = sum([s.education_quality for s in surveys if s.education_quality]) / max(len([s for s in surveys if s.education_quality]), 1)
    avg_curriculum = sum([s.curriculum_relevance for s in surveys if s.curriculum_relevance]) / max(len([s for s in surveys if s.curriculum_relevance]), 1)
    avg_facilities = sum([s.facilities_rating for s in surveys if s.facilities_rating]) / max(len([s for s in surveys if s.facilities_rating]), 1)
    avg_satisfaction = sum([s.overall_satisfaction for s in surveys if s.overall_satisfaction]) / max(len([s for s in surveys if s.overall_satisfaction]), 1)
    avg_recommend = sum([s.recommend_rating for s in surveys if s.recommend_rating]) / max(len([s for s in surveys if s.recommend_rating]), 1)
    
    return render_template('analytics.html',
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
                         avg_education=round(avg_education, 2),
                         avg_curriculum=round(avg_curriculum, 2),
                         avg_facilities=round(avg_facilities, 2),
                         avg_satisfaction=round(avg_satisfaction, 2),
                         avg_recommend=round(avg_recommend, 2))

# ==================== JOBS ====================

@app.route('/jobs')
def jobs():
    page = request.args.get('page', 1, type=int)
    job_type = request.args.get('job_type', '')
    location = request.args.get('location', '')
    
    query = Job.query.filter_by(is_active=True)
    
    if job_type:
        query = query.filter_by(job_type=job_type)
    if location:
        query = query.filter(Job.location.contains(location))
    
    jobs_list = query.order_by(Job.posted_date.desc()).paginate(page=page, per_page=10)
    
    return render_template('jobs.html', jobs=jobs_list, job_type=job_type, location=location)

@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)

# ==================== EVENTS ====================

@app.route('/events')
def events():
    event_type = request.args.get('type', '')
    
    query = Event.query.filter(
        Event.event_date >= datetime.utcnow(),
        Event.is_published == True
    )
    
    if event_type:
        query = query.filter_by(event_type=event_type)
    
    events_list = query.order_by(Event.event_date).all()
    
    return render_template('events.html', events=events_list, event_type=event_type)

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.html', event=event)

# ==================== ALUMNI DIRECTORY ====================

@app.route('/alumni')
def alumni_directory():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    degree_filter = request.args.get('degree', '')
    year_filter = request.args.get('year', '')
    
    query = AlumniProfile.query.filter(AlumniProfile.profile_completed == True)
    
    if search:
        query = query.filter(
            db.or_(
                AlumniProfile.first_name.ilike(f'%{search}%'),
                AlumniProfile.last_name.ilike(f'%{search}%'),
                AlumniProfile.degree.ilike(f'%{search}%'),
                AlumniProfile.current_employer.ilike(f'%{search}%')
            )
        )
    if degree_filter:
        query = query.filter_by(degree=degree_filter)
    if year_filter:
        query = query.filter_by(year_graduated=int(year_filter))
    
    alumni_list = query.order_by(AlumniProfile.last_name).paginate(page=page, per_page=12)
    
    # Get all degrees for filter
    degrees = db.session.query(AlumniProfile.degree).distinct().all()
    degrees = [d[0] for d in degrees if d[0]]
    
    # Get all years for filter
    years = db.session.query(AlumniProfile.year_graduated).distinct().order_by(AlumniProfile.year_graduated.desc()).all()
    years = [y[0] for y in years if y[0]]
    
    return render_template('alumni.html',
                         alumni=alumni_list,
                         degrees=degrees,
                         years=years,
                         search=search,
                         degree_filter=degree_filter,
                         year_filter=year_filter)

# ==================== ADMIN ====================

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all data for admin panel
    total_users = User.query.count()
    total_alumni = AlumniProfile.query.count()
    total_surveys = SurveyResponse.query.count()
    total_jobs = Job.query.count()
    total_events = Event.query.count()
    
    recent_alumni = AlumniProfile.query.order_by(AlumniProfile.created_at.desc()).limit(10).all()
    recent_surveys = db.session.query(SurveyResponse, AlumniProfile).join(
        AlumniProfile, SurveyResponse.alumni_id == AlumniProfile.id
    ).order_by(SurveyResponse.created_at.desc()).limit(10).all()
    
    return render_template('admin.html',
                         total_users=total_users,
                         total_alumni=total_alumni,
                         total_surveys=total_surveys,
                         total_jobs=total_jobs,
                         total_events=total_events,
                         recent_alumni=recent_alumni,
                         recent_surveys=recent_surveys)

# ==================== ADMIN: ALUMNI MANAGEMENT ====================

@app.route('/admin/alumni')
@login_required
def admin_alumni():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = AlumniProfile.query
    
    if search:
        query = query.filter(
            db.or_(
                AlumniProfile.first_name.ilike(f'%{search}%'),
                AlumniProfile.last_name.ilike(f'%{search}%'),
                AlumniProfile.degree.ilike(f'%{search}%')
            )
        )
    
    alumni_list = query.order_by(AlumniProfile.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin_alumni.html', alumni=alumni_list, search=search)

@app.route('/admin/alumni/<int:alumni_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_alumni(alumni_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    profile = AlumniProfile.query.get_or_404(alumni_id)
    user = User.query.get(profile.user_id)
    
    if request.method == 'POST':
        # Keep existing values if form field is empty
        profile.first_name = request.form.get('first_name') or profile.first_name
        profile.last_name = request.form.get('last_name') or profile.last_name
        profile.middle_name = request.form.get('middle_name') or profile.middle_name
        profile.gender = request.form.get('gender') or profile.gender
        profile.phone = request.form.get('phone') or profile.phone
        profile.address = request.form.get('address') or profile.address
        profile.city = request.form.get('city') or profile.city
        profile.province = request.form.get('province') or profile.province
        profile.degree = request.form.get('degree') or profile.degree
        profile.year_graduated = int(request.form.get('year_graduated')) if request.form.get('year_graduated') else profile.year_graduated
        profile.employment_status = request.form.get('employment_status') or profile.employment_status
        profile.current_employer = request.form.get('current_employer') or profile.current_employer
        profile.job_position = request.form.get('job_position') or profile.job_position
        profile.salary_range = request.form.get('salary_range') or profile.salary_range
        profile.skills = request.form.get('skills') or profile.skills
        
        profile.profile_completed = True
        db.session.commit()
        
        flash('Alumni profile updated successfully!', 'success')
        return redirect(url_for('admin_alumni'))
    
    return render_template('admin_edit_alumni.html', profile=profile, user=user)

@app.route('/admin/alumni/<int:alumni_id>/delete', methods=['POST'])
@login_required
def admin_delete_alumni(alumni_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    profile = AlumniProfile.query.get_or_404(alumni_id)
    user = User.query.get(profile.user_id)
    
    # Delete profile and user
    db.session.delete(profile)
    db.session.delete(user)
    db.session.commit()
    
    flash('Alumni record deleted successfully!', 'success')
    return redirect(url_for('admin_alumni'))

# ==================== ADMIN: JOB MANAGEMENT ====================

@app.route('/admin/jobs')
@login_required
def admin_jobs():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    jobs_list = Job.query.order_by(Job.posted_date.desc()).all()
    return render_template('admin_jobs.html', jobs=jobs_list)

@app.route('/admin/jobs/add', methods=['GET', 'POST'])
@login_required
def admin_add_job():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        job = Job(
            title=request.form.get('title'),
            company=request.form.get('company'),
            description=request.form.get('description'),
            requirements=request.form.get('requirements'),
            location=request.form.get('location'),
            salary_min=int(request.form.get('salary_min')) if request.form.get('salary_min') else None,
            salary_max=int(request.form.get('salary_max')) if request.form.get('salary_max') else None,
            job_type=request.form.get('job_type'),
            category=request.form.get('category')
        )
        db.session.add(job)
        db.session.commit()
        flash('Job added successfully!', 'success')
        return redirect(url_for('admin_jobs'))
    
    return render_template('admin_edit_job.html', job=None)

@app.route('/admin/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_job(job_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    job = Job.query.get_or_404(job_id)
    
    if request.method == 'POST':
        job.title = request.form.get('title')
        job.company = request.form.get('company')
        job.description = request.form.get('description')
        job.requirements = request.form.get('requirements')
        job.location = request.form.get('location')
        job.salary_min = int(request.form.get('salary_min')) if request.form.get('salary_min') else None
        job.salary_max = int(request.form.get('salary_max')) if request.form.get('salary_max') else None
        job.job_type = request.form.get('job_type')
        job.category = request.form.get('category')
        
        db.session.commit()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('admin_jobs'))
    
    return render_template('admin_edit_job.html', job=job)

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def admin_delete_job(job_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('admin_jobs'))

# ==================== ADMIN: EVENT MANAGEMENT ====================

@app.route('/admin/events')
@login_required
def admin_events():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    events_list = Event.query.order_by(Event.event_date.desc()).all()
    return render_template('admin_events.html', events=events_list)

@app.route('/admin/events/add', methods=['GET', 'POST'])
@login_required
def admin_add_event():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        event_date = datetime.strptime(request.form.get('event_date'), '%Y-%m-%dT%H:%M')
        event = Event(
            title=request.form.get('title'),
            description=request.form.get('description'),
            event_type=request.form.get('event_type'),
            event_date=event_date,
            location=request.form.get('location'),
            venue=request.form.get('venue'),
            organizer=request.form.get('organizer'),
            contact_email=request.form.get('contact_email')
        )
        db.session.add(event)
        db.session.commit()
        flash('Event added successfully!', 'success')
        return redirect(url_for('admin_events'))
    
    return render_template('admin_edit_event.html', event=None)

@app.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_event(event_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.event_type = request.form.get('event_type')
        event.event_date = datetime.strptime(request.form.get('event_date'), '%Y-%m-%dT%H:%M')
        event.location = request.form.get('location')
        event.venue = request.form.get('venue')
        event.organizer = request.form.get('organizer')
        event.contact_email = request.form.get('contact_email')
        
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('admin_events'))
    
    return render_template('admin_edit_event.html', event=event)

@app.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
def admin_delete_event(event_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('admin_events'))

# ==================== ADMIN: SURVEY MANAGEMENT ====================

@app.route('/admin/surveys')
@login_required
def admin_surveys():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get surveys with their associated alumni profiles
    surveys_data = db.session.query(SurveyResponse, AlumniProfile).join(
        AlumniProfile, SurveyResponse.alumni_id == AlumniProfile.id
    ).order_by(SurveyResponse.created_at.desc()).all()
    
    return render_template('admin_surveys.html', surveys_data=surveys_data)

@app.route('/admin/surveys/<int:survey_id>/delete', methods=['POST'])
@login_required
def admin_delete_survey(survey_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    survey = SurveyResponse.query.get_or_404(survey_id)
    # Reset survey completed status
    profile = AlumniProfile.query.get(survey.alumni_id)
    if profile:
        profile.survey_completed = False
    
    db.session.delete(survey)
    db.session.commit()
    
    flash('Survey response deleted successfully!', 'success')
    return redirect(url_for('admin_surveys'))

# ==================== ADMIN: PASSWORD RESET ====================

@app.route('/admin/reset-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_reset_password(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('admin_reset_password', user_id=user_id))
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash(f'Password for {user.email} has been reset successfully!', 'success')
        return redirect(url_for('admin_alumni'))
    
    return render_template('admin_reset_password.html', user=user)

# ==================== ALUMNI: LIMITED CONTROLS ====================

@app.route('/my-profile')
@login_required
def my_profile():
    """Alumni can view their own profile"""
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('my_profile.html', profile=profile)

@app.route('/my-survey')
@login_required
def my_survey():
    """Alumni can view their own survey response"""
    profile = AlumniProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    survey = SurveyResponse.query.filter_by(alumni_id=profile.id).first()
    return render_template('my_survey.html', profile=profile, survey=survey)

# ==================== API ROUTES ====================

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_alumni': AlumniProfile.query.count(),
        'employed': AlumniProfile.query.filter(
            AlumniProfile.employment_status.in_(['employed', 'self-employed'])
        ).count(),
        'survey_responses': SurveyResponse.query.count(),
        'active_jobs': Job.query.filter_by(is_active=True).count()
    })

@app.route('/api/employment-distribution')
def api_employment_dist():
    return jsonify({
        'employed': AlumniProfile.query.filter_by(employment_status='employed').count(),
        'unemployed': AlumniProfile.query.filter_by(employment_status='unemployed').count(),
        'self_employed': AlumniProfile.query.filter_by(employment_status='self-employed').count(),
        'student': AlumniProfile.query.filter_by(employment_status='student').count()
    })

@app.route('/api/graduates-by-year')
def api_graduates_year():
    years = db.session.query(AlumniProfile.year_graduated).distinct().order_by(AlumniProfile.year_graduated).all()
    years = [y[0] for y in years if y[0]]
    data = []
    for year in years:
        count = AlumniProfile.query.filter_by(year_graduated=year).count()
        data.append({'year': year, 'count': count})
    return jsonify(data)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def error_404(error):
    return render_template('error.html', error_code=404, message='Page not found'), 404

@app.errorhandler(500)
def error_500(error):
    return render_template('error.html', error_code=500, message='Internal server error'), 500

# ==================== SEED DATA ====================

def seed_data():
    """Seed initial data for the application"""
    
    # Create admin user if not exists
    admin = User.query.filter_by(email='admin@wvsu.edu.ph').first()
    if not admin:
        admin = User(
            email='admin@wvsu.edu.ph',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        
        # Admin profile
        admin_profile = AlumniProfile(
            user_id=admin.id,
            first_name='System',
            last_name='Administrator',
            degree='Computer Science',
            year_graduated=2020,
            employment_status='employed',
            current_employer='WVSU Pototan Campus',
            job_position='System Administrator'
        )
        db.session.add(admin_profile)
        db.session.commit()
    
    # Sample Alumni (if none exist)
    if AlumniProfile.query.count() < 5:
        sample_alumni = [
            {'first_name': 'Juan', 'last_name': 'Dela Cruz', 'degree': 'Bachelor of Science in Information Technology', 'year_graduated': 2019, 'employment_status': 'employed', 'current_employer': 'TechCorp Inc.', 'job_position': 'Software Developer', 'profile_completed': True},
            {'first_name': 'Maria', 'last_name': 'Santos', 'degree': 'Bachelor of Science in Business Administration', 'year_graduated': 2020, 'employment_status': 'employed', 'current_employer': 'Business Solutions Ltd.', 'job_position': 'Marketing Manager', 'profile_completed': True},
            {'first_name': 'Pedro', 'last_name': 'Garcia', 'degree': 'Bachelor of Science in Education', 'year_graduated': 2018, 'employment_status': 'employed', 'current_employer': 'Pototan High School', 'job_position': 'Teacher I', 'profile_completed': True},
            {'first_name': 'Ana', 'last_name': 'Reyes', 'degree': 'Bachelor of Science in Nursing', 'year_graduated': 2021, 'employment_status': 'employed', 'current_employer': 'WVSU Medical Center', 'job_position': 'Staff Nurse', 'profile_completed': True},
            {'first_name': 'Jose', 'last_name': 'Mendoza', 'degree': 'Bachelor of Science in Agriculture', 'year_graduated': 2017, 'employment_status': 'self-employed', 'current_employer': 'Mendoza Farm', 'job_position': 'Farm Owner', 'profile_completed': True},
            {'first_name': 'Lisa', 'last_name': 'Torres', 'degree': 'Bachelor of Science in Information Technology', 'year_graduated': 2022, 'employment_status': 'unemployed', 'current_employer': None, 'job_position': None, 'profile_completed': True},
            {'first_name': 'Mark', 'last_name': 'Aquino', 'degree': 'Bachelor of Science in Computer Science', 'year_graduated': 2023, 'employment_status': 'student', 'current_employer': None, 'job_position': None, 'profile_completed': True},
            {'first_name': 'Sarah', 'last_name': 'Cruz', 'degree': 'Bachelor of Science in Tourism Management', 'year_graduated': 2021, 'employment_status': 'employed', 'current_employer': 'Grand Hotel Iloilo', 'job_position': 'Front Desk Supervisor', 'profile_completed': True},
        ]
        
        for alum_data in sample_alumni:
            # Check if user already exists
            existing = AlumniProfile.query.filter_by(first_name=alum_data['first_name'], last_name=alum_data['last_name']).first()
            if not existing:
                user = User(
                    email=f"{alum_data['first_name'].lower()}.{alum_data['last_name'].lower()}@alumni.wvsu.edu.ph",
                    password_hash=generate_password_hash('password123'),
                    role='alumni'
                )
                db.session.add(user)
                db.session.commit()
                
                profile = AlumniProfile(
                    user_id=user.id,
                    **alum_data
                )
                db.session.add(profile)
        
        db.session.commit()
    
    # Sample Jobs (if none exist)
    if Job.query.count() < 5:
        sample_jobs = [
            {'title': 'Software Developer', 'company': 'Tech Innovators Inc.', 'description': 'We are looking for a skilled software developer to join our team. You will be responsible for developing and maintaining web applications.', 'location': 'Iloilo City', 'salary_min': 25000, 'salary_max': 45000, 'job_type': 'full-time', 'category': 'IT'},
            {'title': 'Marketing Coordinator', 'company': 'Brand Masters Co.', 'description': 'Join our marketing team to help grow our brand presence in the region.', 'location': 'Iloilo City', 'salary_min': 20000, 'salary_max': 30000, 'job_type': 'full-time', 'category': 'Marketing'},
            {'title': 'Teacher - Mathematics', 'company': 'St. Paul College Iloilo', 'description': 'We need a qualified Mathematics teacher for our high school department.', 'location': 'Iloilo City', 'salary_min': 18000, 'salary_max': 25000, 'job_type': 'full-time', 'category': 'Education'},
            {'title': 'Nurse', 'company': 'Medical Center Philippines', 'description': 'Hiring registered nurses for our hospital.', 'location': 'Iloilo City', 'salary_min': 22000, 'salary_max': 35000, 'job_type': 'full-time', 'category': 'Healthcare'},
            {'title': 'Farm Manager', 'company': 'Green Fields Agriculture', 'description': 'Experienced farm manager needed for our vegetable farm operations.', 'location': 'Pototan, Iloilo', 'salary_min': 20000, 'salary_max': 30000, 'job_type': 'full-time', 'category': 'Agriculture'},
            {'title': 'Graphic Designer', 'company': 'Creative Studios', 'description': 'Looking for a creative graphic designer for our design team.', 'location': 'Iloilo City', 'salary_min': 15000, 'salary_max': 25000, 'job_type': 'part-time', 'category': 'Design'},
            {'title': 'IT Support Specialist', 'company': 'System Solutions', 'description': 'Provide technical support and maintenance for company systems.', 'location': 'Iloilo City', 'salary_min': 20000, 'salary_max': 30000, 'job_type': 'full-time', 'category': 'IT'},
        ]
        
        for job_data in sample_jobs:
            job = Job(**job_data)
            db.session.add(job)
        
        db.session.commit()
    
    # Sample Events (if none exist)
    if Event.query.count() < 3:
        sample_events = [
            {'title': 'Alumni Homecoming 2024', 'description': 'Annual alumni gathering and celebration. Join us for a night of nostalgia and reconnection with your batchmates.', 'event_type': 'reunion', 'event_date': datetime.utcnow() + timedelta(days=30), 'location': 'WVSU Pototan Campus', 'venue': 'Grandstand', 'organizer': 'Alumni Association'},
            {'title': 'Career Fair 2024', 'description': 'Annual career fair featuring top employers from the region. Bring your resumes!', 'event_type': 'career_fair', 'event_date': datetime.utcnow() + timedelta(days=45), 'location': 'WVSU Pototan Campus', 'venue': 'Activity Center', 'organizer': 'Career Services'},
            {'title': 'Leadership Workshop', 'description': 'Enhance your leadership skills with this intensive workshop.', 'event_type': 'workshop', 'event_date': datetime.utcnow() + timedelta(days=60), 'location': 'WVSU Pototan Campus', 'venue': 'Conference Hall', 'organizer': 'Student Development'},
            {'title': 'Alumni Golf Tournament', 'description': 'Annual alumni golf tournament for charity.', 'event_type': 'gathering', 'event_date': datetime.utcnow() + timedelta(days=75), 'location': 'Iloilo Golf Club', 'venue': 'Iloilo Golf Club', 'organizer': 'Alumni Association'},
        ]
        
        for event_data in sample_events:
            event = Event(**event_data)
            db.session.add(event)
        
        db.session.commit()

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
