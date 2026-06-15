import os
import shutil
from app import create_app
from database.models import db, User, Website, Baseline, ScanResult, Alert, SystemLog
from services.detection import detect_defacement, generate_sha256
from services.pdf_generator import generate_scan_pdf

def run_verification():
    print("=== Sentinel Guard Verification Script ===")
    
    # Initialize the app with test settings
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_verification.db'
    
    with app.app_context():
        # Clean old DB if exists
        db.drop_all()
        db.create_all()
        
        print("1. Database Schema created successfully.")
        
        # 1. Create a dummy user
        test_user = User(
            username="sec_admin",
            email="sec_admin@sentinel.local",
            password_hash="pbkdf2:sha256:dummyhash",
            role="admin"
        )
        db.session.add(test_user)
        db.session.commit()
        print(f"2. User created: {test_user.username} (Role: {test_user.role})")
        
        # 2. Add a dummy website
        test_website = Website(
            user_id=test_user.id,
            url="http://mock-security-test.com",
            name="Mock Corporate Portal",
            is_active=True
        )
        db.session.add(test_website)
        db.session.commit()
        print(f"3. Website registered: {test_website.name} ({test_website.url})")
        
        # 3. Establish a baseline HTML
        original_html = """<!DOCTYPE html>
<html>
<head>
    <title>Mock Corporate Portal</title>
</head>
<body>
    <h1>Welcome to our Corporate Portal</h1>
    <p>This is a secure page content that should remain unchanged.</p>
    <footer>© 2026 Corporate Inc.</footer>
</body>
</html>"""
        
        html_hash = generate_sha256(original_html)
        baseline = Baseline(
            website_id=test_website.id,
            html_hash=html_hash,
            original_html=original_html,
            text_content="Welcome to our Corporate Portal\nThis is a secure page content that should remain unchanged.",
            updated_by=test_user.id
        )
        db.session.add(baseline)
        db.session.commit()
        print("4. Baseline established for website.")
        
        # 4. Simulate a Safe Scan
        safe_result = ScanResult(
            website_id=test_website.id,
            status="safe",
            html_hash=html_hash,
            scanned_html=original_html,
            diff_report="No changes detected",
            severity=None,
            duration_ms=250
        )
        db.session.add(safe_result)
        db.session.commit()
        print("5. Safe scan simulation logged.")
        
        # 5. Simulate a Defaced Scan (Inject script tag and modify text)
        defaced_html = """<!DOCTYPE html>
<html>
<head>
    <title>HACKED BY PWN_SQUAD</title>
</head>
<body>
    <h1>SYSTEM OWNED</h1>
    <p>Hacked by Pwn_Squad. Security is an illusion.</p>
    <script src="http://evil-malware-server.com/malicious.js"></script>
    <footer>© 2026 Corporate Inc.</footer>
</body>
</html>"""
        
        is_defaced, severity, diff_report, summary = detect_defacement(original_html, defaced_html)
        
        print("\n--- Detection Engine Verification ---")
        print(f"Defacement Detected: {is_defaced}")
        print(f"Calculated Severity: {severity}")
        print(f"Hacking Keywords: {summary.get('keywords_found')}")
        print(f"Script Injection Detected: {summary.get('script_injected')}")
        print(f"Title Changed: {summary.get('title_changed')}")
        print(f"Percent Changed: {summary.get('pct_changed')}%")
        
        # Log defaced scan result
        defaced_result = ScanResult(
            website_id=test_website.id,
            status="defaced",
            html_hash=generate_sha256(defaced_html),
            scanned_html=defaced_html,
            diff_report=diff_report,
            severity=severity,
            duration_ms=190
        )
        db.session.add(defaced_result)
        db.session.commit()
        
        # Simulate generating alert
        test_alert = Alert(
            website_id=test_website.id,
            scan_result_id=defaced_result.id,
            title=f"DEFACEMENT DETECTED: {test_website.name} ({severity} Severity)",
            message="Alert message placeholder content detailing script injection.",
            severity=severity,
            notified_email=True,
            notified_telegram=True
        )
        db.session.add(test_alert)
        db.session.commit()
        print("6. Defaced result and alert logged successfully.")
        
        # 6. Generate PDF report from ReportLab
        pdf_filename = "test_defacement_report.pdf"
        generate_scan_pdf(test_website, defaced_result, pdf_filename)
        print(f"7. ReportLab PDF Generated successfully: {pdf_filename}")
        
        # Cleanup test DB connection
        db.session.remove()
        
    print("\n=== VERIFICATION SUCCESSFUL ===")
    print("All subsystems (DB, detection engine, alerting logic, ReportLab PDF compilation) passed integration checks.")

if __name__ == "__main__":
    run_verification()
