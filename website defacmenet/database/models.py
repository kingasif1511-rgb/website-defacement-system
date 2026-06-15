from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    otp = db.Column(db.String(6))
    otp_created_at = db.Column(db.DateTime)
    
    # Relationships
    websites = db.relationship('Website', backref='owner', lazy=True, cascade="all, delete-orphan")
    baselines_updated = db.relationship('Baseline', backref='updater', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Website(db.Model):
    __tablename__ = 'websites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    check_interval_mins = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    baseline = db.relationship('Baseline', backref='website', uselist=False, cascade="all, delete-orphan")
    scan_results = db.relationship('ScanResult', backref='website', lazy=True, cascade="all, delete-orphan")
    alerts = db.relationship('Alert', backref='website', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'url': self.url,
            'name': self.name,
            'is_active': self.is_active,
            'check_interval_mins': self.check_interval_mins,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Baseline(db.Model):
    __tablename__ = 'baselines'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), unique=True, nullable=False)
    html_hash = db.Column(db.String(64), nullable=False)  # SHA-256
    original_html = db.Column(db.Text, nullable=False)
    text_content = db.Column(db.Text)
    screenshot_path = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'html_hash': self.html_hash,
            'original_html_len': len(self.original_html) if self.original_html else 0,
            'screenshot_path': self.screenshot_path,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }


class ScanResult(db.Model):
    __tablename__ = 'scan_results'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'safe', 'defaced', 'error'
    html_hash = db.Column(db.String(64), nullable=False)
    scanned_html = db.Column(db.Text)
    diff_report = db.Column(db.Text)  # Unified diff text or summary JSON
    screenshot_path = db.Column(db.String(500))
    severity = db.Column(db.String(20))  # 'Low', 'Medium', 'High', 'Critical'
    duration_ms = db.Column(db.Integer)  # Time taken in milliseconds
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    alerts = db.relationship('Alert', backref='scan_result', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'status': self.status,
            'html_hash': self.html_hash,
            'screenshot_path': self.screenshot_path,
            'severity': self.severity,
            'duration_ms': self.duration_ms,
            'scanned_at': self.scanned_at.isoformat() if self.scanned_at else None
        }


class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    scan_result_id = db.Column(db.Integer, db.ForeignKey('scan_results.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'Low', 'Medium', 'High', 'Critical'
    is_resolved = db.Column(db.Boolean, default=False)
    notified_email = db.Column(db.Boolean, default=False)
    notified_telegram = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'scan_result_id': self.scan_result_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'is_resolved': self.is_resolved,
            'notified_email': self.notified_email,
            'notified_telegram': self.notified_telegram,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'Scheduler', 'Security', 'Alert', 'Scraper'
    level = db.Column(db.String(20), nullable=False)     # 'INFO', 'WARNING', 'ERROR'
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'level': self.level,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
