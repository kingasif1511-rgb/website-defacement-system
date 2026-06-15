import os

class Config:
    # Flask Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cyber-defacement-monitor-secure-key-9988')
    
    # Database Configuration (SQLite database stored in the workspace directory)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///defacement_monitor.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Directory paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'screenshots')
    
    # Scheduler Config
    SCAN_INTERVAL_MINUTES = 5
    
    # Alert Sandbox Mode (If True, notifications are logged instead of hitting live APIs)
    ALERT_SANDBOX = True
    
    # SMTP Email Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER', 'your_email@gmail.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your_app_password')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'no-reply@defacement-monitor.com')
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'YOUR_TELEGRAM_CHAT_ID')
