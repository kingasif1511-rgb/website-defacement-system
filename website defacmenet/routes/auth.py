from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import random
from database.models import db, User
from services.alerts import send_otp_email

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """
    Decorator to protect routes requiring user login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to protect routes requiring administrator privileges.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Simple Validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already registered.', 'danger')
            return render_template('register.html')
            
        # First user is admin, others are standard users
        is_first_user = User.query.count() == 0
        role = 'admin' if is_first_user else 'user'
        
        # Generate 6-digit verification OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Hash password and save user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=role,
            is_verified=False,
            otp=otp_code,
            otp_created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Send OTP email (simulated in sandbox, live via SMTP otherwise)
            send_otp_email(email, otp_code)
            
            flash('Account created! A 6-digit verification code has been sent to your email.', 'warning')
            return redirect(url_for('auth.verify_otp', email=email))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('Username/email and password are required.', 'danger')
            return render_template('login.html')
            
        # Query user
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Check verification status
            if not user.is_verified:
                flash('Account email is not verified yet. Please enter the OTP code sent to your email.', 'warning')
                return redirect(url_for('auth.verify_otp', email=user.email))
                
            # Start session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard.home'))
        else:
            flash('Invalid username/email or password.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'user_id' in session:
        return redirect(url_for('dashboard.home'))
        
    email = request.args.get('email', '').strip()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        otp_input = request.form.get('otp', '').strip()
        
        if not email or not otp_input:
            flash('Email and OTP code are required.', 'danger')
            return render_template('verify_otp.html', email=email)
            
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid request parameters.', 'danger')
            return redirect(url_for('auth.register'))
            
        if user.is_verified:
            flash('Account is already verified. Please log in.', 'info')
            return redirect(url_for('auth.login'))
            
        # Verify OTP code and expiration (10 minutes)
        if user.otp != otp_input:
            flash('Invalid OTP code. Please check your inputs.', 'danger')
            return render_template('verify_otp.html', email=email)
            
        expiration_time = user.otp_created_at + timedelta(minutes=10)
        if datetime.utcnow() > expiration_time:
            # Code expired, generate a new one
            new_otp = str(random.randint(100000, 999999))
            user.otp = new_otp
            user.otp_created_at = datetime.utcnow()
            db.session.commit()
            send_otp_email(email, new_otp)
            flash('OTP expired. A new verification code has been dispatched.', 'danger')
            return render_template('verify_otp.html', email=email)
            
        # Success! Activate User
        user.is_verified = True
        user.otp = None
        user.otp_created_at = None
        db.session.commit()
        
        flash('Account verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('verify_otp.html', email=email)

@auth_bp.route('/resend-otp')
def resend_otp():
    email = request.args.get('email', '').strip()
    if not email:
        flash('Email address is required.', 'danger')
        return redirect(url_for('auth.register'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.register'))
        
    if user.is_verified:
        flash('User already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))
        
    new_otp = str(random.randint(100000, 999999))
    user.otp = new_otp
    user.otp_created_at = datetime.utcnow()
    db.session.commit()
    
    send_otp_email(email, new_otp)
    flash('A new verification code has been dispatched.', 'success')
    return redirect(url_for('auth.verify_otp', email=email))
