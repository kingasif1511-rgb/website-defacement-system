import os
import tempfile
from flask import Blueprint, render_template, redirect, url_for, session, flash, send_file, current_app
from database.models import db, Website, Baseline, ScanResult, Alert, SystemLog
from routes.auth import login_required, admin_required
from services.pdf_generator import generate_scan_pdf

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    return redirect(url_for('dashboard.home'))

@dashboard_bp.route('/dashboard')
@login_required
def home():
    # Fetch website stats
    if session.get('role') == 'admin':
        websites = Website.query.all()
        recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
        system_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(5).all()
    else:
        websites = Website.query.filter_by(user_id=session['user_id']).all()
        recent_alerts = Alert.query.join(Website).filter(Website.user_id == session['user_id']).order_by(Alert.created_at.desc()).limit(5).all()
        system_logs = []

    total_count = len(websites)
    safe_count = 0
    defaced_count = 0
    inactive_count = 0
    
    # Process site list states
    site_list_data = []
    for site in websites:
        # Get latest scan result
        latest_scan = ScanResult.query.filter_by(website_id=site.id).order_by(ScanResult.scanned_at.desc()).first()
        
        status = "No Scans"
        severity = None
        scanned_at = None
        
        if latest_scan:
            status = latest_scan.status
            severity = latest_scan.severity
            scanned_at = latest_scan.scanned_at
            
        if not site.is_active:
            inactive_count += 1
        elif status == 'safe':
            safe_count += 1
        elif status == 'defaced':
            defaced_count += 1
            
        site_list_data.append({
            'id': site.id,
            'name': site.name,
            'url': site.url,
            'is_active': site.is_active,
            'status': status,
            'severity': severity,
            'scanned_at': scanned_at.strftime('%Y-%m-%d %H:%M:%S') if scanned_at else 'N/A'
        })

    # Prepare chart metrics
    severity_distribution = {'Low': 0, 'Medium': 0, 'High': 0, 'Critical': 0}
    for alert in Alert.query.filter_by(is_resolved=False).all():
        if alert.severity in severity_distribution:
            severity_distribution[alert.severity] += 1

    return render_template(
        'dashboard.html',
        total_count=total_count,
        safe_count=safe_count,
        defaced_count=defaced_count,
        inactive_count=inactive_count,
        site_list_data=site_list_data,
        recent_alerts=recent_alerts,
        system_logs=system_logs,
        severity_chart_data=list(severity_distribution.values())
    )

@dashboard_bp.route('/websites/<int:website_id>')
@login_required
def website_detail(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        flash('Website not found.', 'danger')
        return redirect(url_for('dashboard.home'))
        
    # Access control
    if session.get('role') != 'admin' and website.user_id != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.home'))
        
    baseline = website.baseline
    scan_history = ScanResult.query.filter_by(website_id=website_id).order_by(ScanResult.scanned_at.desc()).limit(15).all()
    latest_scan = scan_history[0] if scan_history else None
    
    return render_template(
        'website_detail.html',
        website=website,
        baseline=baseline,
        latest_scan=latest_scan,
        scan_history=scan_history
    )

@dashboard_bp.route('/alerts')
@login_required
def alerts_log():
    # Admins see everything, users see their own alerts
    if session.get('role') == 'admin':
        alerts = Alert.query.order_by(Alert.created_at.desc()).all()
        system_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).all()
    else:
        alerts = Alert.query.join(Website).filter(Website.user_id == session['user_id']).order_by(Alert.created_at.desc()).all()
        system_logs = []
        
    return render_template(
        'alerts.html',
        alerts=alerts,
        system_logs=system_logs
    )

@dashboard_bp.route('/scan-results/<int:result_id>/pdf')
@login_required
def download_pdf(result_id):
    scan_result = db.session.get(ScanResult, result_id)
    if not scan_result:
        flash('Scan result not found.', 'danger')
        return redirect(url_for('dashboard.home'))
        
    website = db.session.get(Website, scan_result.website_id)
    # Access control
    if session.get('role') != 'admin' and website.user_id != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard.home'))
        
    try:
        # Create temp folder inside workspace directory for reports
        reports_dir = os.path.join(current_app.config['BASE_DIR'], 'temp_reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        pdf_path = os.path.join(reports_dir, f"report_{result_id}.pdf")
        generate_scan_pdf(website, scan_result, pdf_path)
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"defacement_report_{website.name.replace(' ', '_')}_{scan_result.id}.pdf"
        )
    except Exception as e:
        flash(f"Failed to generate report: {str(e)}", 'danger')
        return redirect(url_for('dashboard.website_detail', website_id=website.id))
