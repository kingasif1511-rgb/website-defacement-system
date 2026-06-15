import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database.models import db, Website, Baseline, ScanResult
from services.scraper import fetch_website_content
from services.detection import detect_defacement
from services.alerts import dispatch_alerts, log_system_message

scheduler = BackgroundScheduler()

def scan_single_website(app, website):
    """
    Scans a single website: fetches current HTML, compares with baseline, 
    records results, and dispatches alerts if changes are detected.
    """
    with app.app_context():
        # Re-fetch website to ensure it is in the current session
        website = db.session.get(Website, website.id)
        if not website or not website.is_active:
            return
            
        baseline = website.baseline
        if not baseline:
            # If there's no baseline, we cannot check it
            log_system_message(
                "Scheduler", 
                "WARNING", 
                f"Skipping scan for {website.name} ({website.url}) - No baseline configured."
            )
            return

        log_system_message("Scheduler", "INFO", f"Starting background scan for: {website.name} ({website.url})")
        start_time = time.time()
        
        try:
            # Scrape content (don't capture screenshot every time to save bandwidth/resources, 
            # unless a defacement is detected, in which case we might fetch it or fetch it on warning.
            # To keep it robust, we'll try to capture screenshot if screenshots are enabled in the baseline)
            capture_screenshot = baseline.screenshot_path is not None
            scrape_res = fetch_website_content(
                website.url, 
                capture_screenshot=capture_screenshot, 
                website_id=website.id
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if not scrape_res.success:
                # Scrape failed (website offline or timeout)
                result = ScanResult(
                    website_id=website.id,
                    status='error',
                    html_hash='',
                    scanned_html='',
                    diff_report=scrape_res.error_message,
                    screenshot_path=None,
                    severity='Medium',
                    duration_ms=duration_ms
                )
                db.session.add(result)
                db.session.commit()
                log_system_message("Scheduler", "ERROR", f"Scan failed for {website.name}: {scrape_res.error_message}")
                return
                
            # Perform comparison
            is_defaced, severity, diff_report, summary = detect_defacement(
                baseline.original_html, 
                scrape_res.html
            )
            
            # Save results
            status = 'defaced' if is_defaced else 'safe'
            result = ScanResult(
                website_id=website.id,
                status=status,
                html_hash=summary.get('current_hash', scrape_res.html[:64]), # Use placeholder hash if needed
                scanned_html=scrape_res.html,
                diff_report=diff_report,
                screenshot_path=scrape_res.screenshot_path,
                severity=severity if is_defaced else None,
                duration_ms=duration_ms
            )
            db.session.add(result)
            db.session.commit()
            
            if is_defaced:
                log_system_message(
                    "Scheduler", 
                    "WARNING", 
                    f"Defacement detected on {website.name}! Severity: {severity}. Changed {summary.get('pct_changed', 0)}%"
                )
                # Dispatch alerts
                dispatch_alerts(website, result, summary)
            else:
                log_system_message("Scheduler", "INFO", f"Scan complete for {website.name}. Status: SAFE.")
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log_system_message("Scheduler", "ERROR", f"Exception during scan of {website.name}: {str(e)}")
            try:
                result = ScanResult(
                    website_id=website.id,
                    status='error',
                    html_hash='',
                    scanned_html='',
                    diff_report=f"System exception: {str(e)}",
                    screenshot_path=None,
                    severity='Medium',
                    duration_ms=duration_ms
                )
                db.session.add(result)
                db.session.commit()
            except Exception:
                db.session.rollback()

def scan_all_websites(app):
    """
    Main job loop scheduled to run every 5 minutes.
    """
    with app.app_context():
        active_websites = Website.query.filter_by(is_active=True).all()
        if not active_websites:
            return
            
    for website in active_websites:
        scan_single_website(app, website)

def init_scheduler(app):
    """
    Starts the scheduler process.
    """
    # Check if job already exists to prevent duplicate schedules in dev reloaders
    if not scheduler.get_jobs():
        scheduler.add_job(
            func=scan_all_websites,
            trigger='interval',
            minutes=app.config.get('SCAN_INTERVAL_MINUTES', 5),
            args=[app],
            id='website_monitoring_job',
            name='Scan all active websites periodically'
        )
        scheduler.start()
        log_system_message("Scheduler", "INFO", f"APScheduler initialized. Running scan job every {app.config.get('SCAN_INTERVAL_MINUTES', 5)} minutes.")
