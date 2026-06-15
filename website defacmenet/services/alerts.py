import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import logging
from config import Config
from database.models import db, Alert, SystemLog, Website, ScanResult

# Setup simple logger
logger = logging.getLogger('AlertSystem')

def log_system_message(category, level, message):
    """
    Utility to record system messages to the DB and standard logger.
    """
    logger.info(f"[{category}] [{level}] {message}")
    try:
        # We need an app context to write to DB, which we handle caller-side or spawn if needed.
        # But to be safe, we check if database connection works.
        sys_log = SystemLog(category=category, level=level, message=message)
        db.session.add(sys_log)
        db.session.commit()
    except Exception as e:
        print(f"Failed to write system log to DB: {str(e)}")

def dispatch_alerts(website, scan_result, changes_summary):
    """
    Core function that records alerts in the database and dispatches notifications
    via SMTP and Telegram based on application settings.
    """
    severity = scan_result.severity
    title = f"DEFACEMENT DETECTED: {website.name} ({severity} Severity)"
    
    # Construct alert message
    message = (
        f"Defacement Scan Alert\n"
        f"----------------------\n"
        f"Website Name: {website.name}\n"
        f"URL: {website.url}\n"
        f"Scan Time: {scan_result.scanned_at}\n"
        f"Severity: {severity}\n"
        f"Similarity Score: {changes_summary.get('similarity_ratio', 0.0) * 100}%\n"
        f"Changes Summary:\n"
        f"  - Lines Added: {changes_summary.get('added_lines', 0)}\n"
        f"  - Lines Removed: {changes_summary.get('removed_lines', 0)}\n"
        f"  - Script Injection Detected: {'YES' if changes_summary.get('script_injected') else 'NO'}\n"
        f"  - Title Changed: {'YES' if changes_summary.get('title_changed') else 'NO'}\n"
    )
    
    if changes_summary.get('keywords_found'):
        message += f"  - Hacking Keywords Found: {', '.join(changes_summary.get('keywords_found'))}\n"
        
    message += (
        f"\nPlease log into the Website Defacement Monitor Dashboard to review the diff report and approve updates."
    )
    
    # 1. Record alert in Database
    new_alert = Alert(
        website_id=website.id,
        scan_result_id=scan_result.id,
        title=title,
        message=message,
        severity=severity
    )
    db.session.add(new_alert)
    db.session.commit()
    
    notified_email = False
    notified_telegram = False
    
    # 2. Dispatch notifications
    if Config.ALERT_SANDBOX:
        log_msg = f"[SANDBOX ALERT] Simulated alert sent for {website.name}. Msg:\n{message}"
        log_system_message("Alert", "INFO", log_msg)
        notified_email = True
        notified_telegram = True
    else:
        # Run Email alert
        if Config.SMTP_USER != 'your_email@gmail.com' and Config.SMTP_USER:
            email_success = send_email_alert(title, message)
            if email_success:
                notified_email = True
                log_system_message("Alert", "INFO", f"Email alert successfully dispatched for {website.name}")
            else:
                log_system_message("Alert", "ERROR", f"Email alert failed to dispatch for {website.name}")
        else:
            log_system_message("Alert", "WARNING", f"SMTP settings are placeholder. Email notification skipped for {website.name}")
            
        # Run Telegram alert
        if Config.TELEGRAM_BOT_TOKEN != 'YOUR_TELEGRAM_BOT_TOKEN' and Config.TELEGRAM_BOT_TOKEN:
            telegram_success = send_telegram_alert(message)
            if telegram_success:
                notified_telegram = True
                log_system_message("Alert", "INFO", f"Telegram alert successfully dispatched for {website.name}")
            else:
                log_system_message("Alert", "ERROR", f"Telegram alert failed to dispatch for {website.name}")
        else:
            log_system_message("Alert", "WARNING", f"Telegram settings are placeholder. Telegram notification skipped for {website.name}")
            
    # Update alert state in DB
    new_alert.notified_email = notified_email
    new_alert.notified_telegram = notified_telegram
    db.session.commit()

def send_email_alert(subject, body_text):
    """
    Sends SMTP email alert. Returns True if success, else False.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_FROM
        msg['To'] = Config.SMTP_USER  # Sends alerts to administrative email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body_text, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.sendmail(Config.SMTP_FROM, Config.SMTP_USER, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {str(e)}")
        return False

def send_telegram_alert(message_text):
    """
    Sends Telegram message via Bot API. Returns True if success, else False.
    """
    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': Config.TELEGRAM_CHAT_ID,
            'text': message_text
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {str(e)}")
        return False

def send_otp_email(email, otp):
    """
    Dispatches OTP verification email to the user.
    """
    subject = "Sentinel Guard - Registration OTP Code"
    body_text = (
        f"Security Notice: Account Registration Verification\n"
        f"-------------------------------------------------\n"
        f"Your verification code is: {otp}\n\n"
        f"This OTP is valid for 10 minutes. If you did not request this account, please ignore this email."
    )
    
    if Config.ALERT_SANDBOX:
        # Log clearly to console and system logs
        print(f"\n[SANDBOX OTP] Verification Code for {email}: {otp}\n")
        log_system_message("Security", "INFO", f"[SANDBOX OTP] Generated verification code for {email}: {otp}")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_FROM
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body_text, 'plain'))
        
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.sendmail(Config.SMTP_FROM, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email: {str(e)}")
        log_system_message("Security", "ERROR", f"Failed to send OTP to {email}: {str(e)}")
        return False
