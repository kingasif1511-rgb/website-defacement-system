Sentinel Guard: Website Defacement Monitoring System
Sentinel Guard is a lightweight, secure, and responsive cybersecurity tool built using Python and Flask. It continuously monitors registered website domains for unauthorized alterations (defacement attacks) by comparing their live state against stored baselines, assessing change severities, generating code delta reports, sending alerts, and compiling PDF security audits.

Key Features
Website Registration & Baseline Setup: Register domains for active monitoring. The system immediately captures a clean baseline HTML signature and page screenshots.
Dynamic HTML Cleaning: Employs filtering algorithms to strip unstable tokens (e.g., anti-CSRF tokens, dynamic script variables, calendars, clocks) from scrapings, preventing false-positive triggers.
Difference Analysis & Code Diff: Features a line-by-line unified delta viewer color-coding additions in green and removals in red, alongside side-by-side screenshot comparisons.
Defacement Detection & Severity Engine: Inspects website changes, looking for injected <script> tags, title changes, or signature hacking terms (hacked, pwned, etc.) and ranks incident severities:
Low: Minor styling or layout adjustments (<5% change).
Medium: Significant text modifications (5-30% change).
High: Script tag injections or header title alterations.
Critical: Signature hacking keywords detected or complete page replacements (>70% change).
Periodic Scan Scheduler: Runs background scanning cycles every 5 minutes using APScheduler.
Incident Alert System: Dispatches SMTP emails and Telegram Bot messages. Includes a configurable Sandbox Mode to simulate alerts locally.
Secure Register with Email OTP: Requires new accounts to verify their emails using a secure, 10-minute expiring 6-digit One-Time Password (OTP) before profile activation.
Report Exporter: Compiles and streams detailed, formatted PDF incident reports using ReportLab.
Admin Security Audits: Logged system logs for monitoring scheduler status, scraping errors, and administrative audit trails.
Technology Stack
Backend: Flask (Python), Flask-SQLAlchemy (ORM), Flask-WTF (CSRF Safety)
Frontend: HTML5, Vanilla CSS (Premium Dark Glassmorphism Theme), JS, Bootstrap 5, Chart.js (Analytics)
Database: SQLite
Background Runner: APScheduler
Report Generator: ReportLab (Pure Python PDF compiler)
Web Scraping: Python Requests & BeautifulSoup4
Headless Screenshotting: Selenium (Chrome Webdriver)
Directory Structure
text

website-defacement-monitoring/
│
├── app.py                      # Server entry point & scheduler setup
├── config.py                   # App secrets, timers, & credential variables
├── requirements.txt            # Python packages
├── README.md                   # System usage guide
├── documentation.md            # Extended developer docs & API reference
│
├── database/
│   └── models.py               # SQLAlchemy models (User, Website, Baseline, ScanResult, Alert, Log)
│
├── services/
│   ├── scraper.py              # Requests scraper & headless Selenium screenshot agent
│   ├── detection.py            # SHA-256 baseline hashing & delta diff calculator
│   ├── scheduler.py            # Background scheduler scan loop
│   ├── alerts.py               # SMTP, Telegram bot, & Sandbox OTP notification dispatchers
│   └── pdf_generator.py        # ReportLab PDF compilation
│
├── routes/
│   ├── auth.py                 # User authentication, registration, & OTP validation
│   ├── dashboard.py            # UI Views rendering & PDF downloader endpoint
│   └── api.py                  # AJAX CRUD endpoints & manual triggers
│
├── templates/
│   ├── base.html               # Global dark glassmorphism layout
│   ├── login.html              # Custom authentication page
│   ├── register.html           # Custom registration page
│   ├── verify_otp.html         # Custom 6-digit verification code form
│   ├── dashboard.html          # Cyber dashboard cards, table, logs & Chart.js severity counts
│   ├── website_detail.html     # Tabbed diff inspector & scan logs archive
│   └── alerts.html             # System audit logs & alert credentials diagnostics
│
├── static/
│   └── screenshots/            # Directory where page screenshots are stored
│
├── verify_setup.py             # Integration test script for scans & diff engines
└── verify_otp_flow.py          # Integration test script for OTP registration flow
Installation & Setup
Prerequisites
Python 3.8+
Google Chrome (Optional: Required if capturing page screenshots is wanted. Runs headlessly).
Steps
Clone and Enter Workspace:

bash

cd website-defacement-monitoring/
Establish Environment & Packages: Create and activate a virtual environment, then install dependencies:

bash

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
Verify Installation (Highly Recommended): We have included automated integration tests. Run them to confirm everything is functional:

bash

python verify_setup.py
python verify_otp_flow.py
Both scripts should report successful executions.

Launch Server:

bash

python app.py
Access the dashboard at http://localhost:5000.

Configuration Variables (config.py)
Set the following parameters in config.py (or load via environment variables):

ALERT_SANDBOX: Set to True (default) to log OTPs and alert notifications to your console/database rather than sending live requests. Set to False in production.
SCAN_INTERVAL_MINUTES: Frequency of background scans (default: 5).
SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD: SMTP credentials for live email verification and alert dispatch.
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID: Telegram credentials for chat bot notifications.
Operational Guide
Admin Creation: Navigate to the site and register. In Sandbox mode, retrieve your 6-digit code from the server console or System Logs table, enter it on the verification screen, and log in.
Monitoring Setup: Click Add Website, input a URL, name, and scan frequency. The system immediately captures the reference baseline state.
Breach Delta Review: When a scan reports DEFACED, open View to inspect line-by-line differences and side-by-side screenshots. Click Export PDF Report to download an audit file.
Remediation:
If the change was an attack, restore the server files and run Scan to return status to Safe.
If the design was updated intentionally, click Approve as New Baseline to save the new HTML signature.
