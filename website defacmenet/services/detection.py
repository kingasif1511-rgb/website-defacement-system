import hashlib
import difflib
import re
from bs4 import BeautifulSoup

def generate_sha256(text_content):
    """
    Generates SHA-256 hash of text or HTML content.
    """
    if not text_content:
        return ""
    return hashlib.sha256(text_content.encode('utf-8', errors='ignore')).hexdigest()

def detect_defacement(baseline_html, current_html):
    """
    Compares baseline HTML with current HTML.
    Returns:
        is_defaced (bool): True if changes exceed the acceptable threshold.
        severity (str): 'Low', 'Medium', 'High', 'Critical'
        diff_report (str): Detailed text diff report.
        changes_summary (dict): Quantitative and qualitative analysis of changes.
    """
    if not baseline_html or not current_html:
        return False, "Low", "Missing content for comparison", {}
        
    baseline_hash = generate_sha256(baseline_html)
    current_hash = generate_sha256(current_html)
    
    # If hashes match exactly, website is safe
    if baseline_hash == current_hash:
        return False, "Safe", "No changes detected", {
            "similarity_ratio": 1.0,
            "added_lines": 0,
            "removed_lines": 0,
            "script_injected": False,
            "keywords_found": []
        }
        
    # Standardize HTML into lines for diffing
    baseline_lines = baseline_html.splitlines()
    current_lines = current_html.splitlines()
    
    # Compute unified diff
    diff = list(difflib.unified_diff(
        baseline_lines, 
        current_lines, 
        fromfile='Baseline', 
        tofile='CurrentScan', 
        lineterm=''
    ))
    diff_report = "\n".join(diff)
    
    # Analyze differences
    added_lines_count = 0
    removed_lines_count = 0
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            added_lines_count += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines_count += 1
            
    # Calculate similarity ratio
    matcher = difflib.SequenceMatcher(None, baseline_lines, current_lines)
    similarity = matcher.ratio()
    pct_changed = (1 - similarity) * 100
    
    # Look for signature defacement keywords in the current HTML
    defacement_keywords = ["hacked", "pwned", "defaced", "hackers", "hacked by", "security breach", "ownz", "deface", "exploit"]
    found_keywords = []
    current_lower = current_html.lower()
    for kw in defacement_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', current_lower):
            found_keywords.append(kw)
            
    # Script Injections Check (Check for new script tags not present in baseline)
    baseline_soup = BeautifulSoup(baseline_html, 'html.parser')
    current_soup = BeautifulSoup(current_html, 'html.parser')
    
    baseline_scripts = [str(s) for s in baseline_soup.find_all('script')]
    current_scripts = [str(s) for s in current_soup.find_all('script')]
    
    new_scripts = [s for s in current_scripts if s not in baseline_scripts]
    script_injected = len(new_scripts) > 0
    
    # Title Check
    baseline_title = baseline_soup.title.string.strip() if baseline_soup.title else ""
    current_title = current_soup.title.string.strip() if current_soup.title else ""
    title_changed = baseline_title != current_title
    
    # Determine severity levels:
    # Critical: Keywords found OR complete rewrite (similarity < 0.3) OR script injections with high text changes.
    # High: Script injections OR title changed OR similarity < 0.7 (more than 30% page changed).
    # Medium: 5% to 30% lines changed.
    # Low: less than 5% change.
    
    severity = "Low"
    is_defaced = False
    
    # If there are changes, we classify them
    if similarity < 0.999:  # Threshold for any change
        is_defaced = True
        
        if len(found_keywords) > 0 or similarity < 0.3:
            severity = "Critical"
        elif script_injected or title_changed or similarity < 0.7:
            severity = "High"
        elif similarity < 0.95:
            severity = "Medium"
        else:
            severity = "Low"
            
    changes_summary = {
        "similarity_ratio": round(similarity, 4),
        "pct_changed": round(pct_changed, 2),
        "added_lines": added_lines_count,
        "removed_lines": removed_lines_count,
        "script_injected": script_injected,
        "new_scripts_count": len(new_scripts),
        "title_changed": title_changed,
        "keywords_found": found_keywords,
        "baseline_title": baseline_title,
        "current_title": current_title
    }
    
    return is_defaced, severity, diff_report, changes_summary
