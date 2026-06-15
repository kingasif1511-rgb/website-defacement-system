import os
import logging
from flask import Flask, session
from flask_wtf.csrf import CSRFProtect
from config import Config
from database.models import db, User, Website, Baseline, ScanResult, Alert, SystemLog
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from services.scheduler import init_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable Logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Initialize CSRF Protection
    csrf = CSRFProtect(app)
    
    # Initialize Database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    
    # Configure context processors for templates
    @app.context_processor
    def inject_user():
        return dict(
            current_user_id=session.get('user_id'),
            current_username=session.get('username'),
            current_role=session.get('role')
        )
        
    # Create screenshots upload folder if missing
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize DB tables and Background Scheduler
    with app.app_context():
        db.create_all()
        # Initialize scheduler
        init_scheduler(app)
        
    return app

app = create_app()

if __name__ == '__main__':
    # Run server locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
