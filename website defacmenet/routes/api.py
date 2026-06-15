from flask import Blueprint, jsonify, request, session
from database.models import db, Website, Baseline, ScanResult, User
from routes.auth import login_required, admin_required
from services.scraper import fetch_website_content
from services.detection import generate_sha256, detect_defacement
from services.scheduler import scan_single_website
from services.alerts import log_system_message

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/websites', methods=['GET'])
@login_required
def get_websites():
    # Admins see all sites, users see their own registered sites
    if session.get('role') == 'admin':
        websites = Website.query.all()
    else:
        websites = Website.query.filter_by(user_id=session['user_id']).all()
        
    return jsonify([site.to_dict() for site in websites])

@api_bp.route('/websites', methods=['POST'])
@login_required
def register_website():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    name = data.get('name', '').strip()
    check_interval = int(data.get('check_interval_mins', 5))
    
    if not url or not name:
        return jsonify({'error': 'URL and Website Name are required.'}), 400
        
    # Standardize URL protocol
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
        
    # Check if URL already registered
    existing = Website.query.filter_by(url=url).first()
    if existing:
        return jsonify({'error': 'This website URL is already registered.'}), 400
        
    # Create Website Record
    new_site = Website(
        user_id=session['user_id'],
        url=url,
        name=name,
        check_interval_mins=check_interval
    )
    
    try:
        db.session.add(new_site)
        db.session.flush()  # Generate site ID before committing
        
        # Scrape immediately to establish baseline
        # Capture screenshot for the baseline if selenium is active
        scrape_res = fetch_website_content(url, capture_screenshot=True, website_id=new_site.id)
        
        if not scrape_res.success:
            db.session.rollback()
            return jsonify({'error': f'Failed to establish baseline: {scrape_res.error_message}'}), 400
            
        # Create baseline
        html_hash = generate_sha256(scrape_res.html)
        baseline = Baseline(
            website_id=new_site.id,
            html_hash=html_hash,
            original_html=scrape_res.html,
            text_content=scrape_res.text,
            screenshot_path=scrape_res.screenshot_path,
            updated_by=session['user_id']
        )
        db.session.add(baseline)
        db.session.commit()
        
        log_system_message("Security", "INFO", f"Registered website: {name} ({url}) and established baseline.")
        return jsonify({
            'success': True, 
            'message': 'Website registered and baseline established successfully.',
            'website': new_site.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Internal Server Error: {str(e)}'}), 500

@api_bp.route('/websites/<int:website_id>', methods=['DELETE'])
@login_required
def delete_website(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found.'}), 404
        
    # Access control: users can only delete their own websites, admins can delete any
    if session.get('role') != 'admin' and website.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized access.'}), 403
        
    try:
        name = website.name
        url = website.url
        db.session.delete(website)
        db.session.commit()
        log_system_message("Security", "INFO", f"Deleted website: {name} ({url}) by user {session['username']}")
        return jsonify({'success': True, 'message': 'Website deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/websites/<int:website_id>/toggle', methods=['POST'])
@login_required
def toggle_website(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found.'}), 404
        
    if session.get('role') != 'admin' and website.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized access.'}), 403
        
    website.is_active = not website.is_active
    db.session.commit()
    
    state = "enabled" if website.is_active else "disabled"
    log_system_message("Scheduler", "INFO", f"Website {website.name} monitoring has been {state}.")
    return jsonify({
        'success': True, 
        'message': f'Website monitoring {state} successfully.',
        'is_active': website.is_active
    })

@api_bp.route('/websites/<int:website_id>/scan', methods=['POST'])
@login_required
def trigger_scan(website_id):
    # Import app inside method to avoid circular reference
    from flask import current_app
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found.'}), 404
        
    if session.get('role') != 'admin' and website.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized access.'}), 403
        
    # Execute scan synchronously inside the API call so the user gets immediate feedback
    scan_single_website(current_app._get_current_object(), website)
    
    # Get latest result
    latest_result = ScanResult.query.filter_by(website_id=website_id).order_by(ScanResult.scanned_at.desc()).first()
    
    if latest_result:
        return jsonify({
            'success': True,
            'status': latest_result.status,
            'severity': latest_result.severity,
            'scanned_at': latest_result.scanned_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'duration_ms': latest_result.duration_ms,
            'message': 'Scan completed.'
        })
    else:
        return jsonify({'error': 'Scan failed to produce a result.'}), 500

@api_bp.route('/websites/<int:website_id>/baseline', methods=['POST'])
@admin_required
def approve_baseline(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found.'}), 404
        
    # Get latest scan result
    latest_result = ScanResult.query.filter_by(website_id=website_id).order_by(ScanResult.scanned_at.desc()).first()
    if not latest_result or latest_result.status == 'error':
        return jsonify({'error': 'Cannot update baseline: No valid scan results exist.'}), 400
        
    try:
        baseline = website.baseline
        if not baseline:
            # Create a new baseline if it somehow doesn't exist
            baseline = Baseline(website_id=website_id)
            db.session.add(baseline)
            
        # Update baseline values with the latest scan values
        baseline.html_hash = latest_result.html_hash
        baseline.original_html = latest_result.scanned_html
        baseline.screenshot_path = latest_result.screenshot_path
        baseline.updated_by = session['user_id']
        
        # Remove any alerts that were associated with this website since it is now marked as the safe baseline
        alerts = website.alerts
        for alert in alerts:
            alert.is_resolved = True
            
        db.session.commit()
        log_system_message("Security", "INFO", f"Baseline updated for {website.name} by administrator {session['username']}")
        
        return jsonify({
            'success': True,
            'message': 'Baseline updated successfully. All pending alerts marked as resolved.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update baseline: {str(e)}'}), 500
