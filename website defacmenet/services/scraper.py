import os
import time
import requests
import re
from bs4 import BeautifulSoup
from flask import current_app

# Selenium imports (optional screenshot capability)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class ScrapeResult:
    def __init__(self, success, html="", text="", screenshot_path=None, error_message=""):
        self.success = success
        self.html = html
        self.text = text
        self.screenshot_path = screenshot_path
        self.error_message = error_message

def clean_html(html_content):
    """
    Cleans HTML content by removing dynamic components that frequently change 
    and cause false positive defacement detections (e.g. CSRF tokens, timestamps, nonces).
    """
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Remove common CSRF tokens / hidden input tokens
    for token_input in soup.find_all('input', {'name': re.compile(r'(csrf|token|nonce|session)', re.I)}):
        token_input['value'] = 'DYNAMIC_TOKEN_CLEANED'
        
    # 2. Clean style nonces if any
    for tag in soup.find_all(attrs={"nonce": True}):
        tag['nonce'] = 'DYNAMIC_NONCE_CLEANED'
        
    # 3. Strip custom timestamps / calendars (often in footer) if they match specific classes/ids
    for dynamic_el in soup.find_all(class_=re.compile(r'(time|clock|date|current-time)', re.I)):
        dynamic_el.string = 'DYNAMIC_TIME_CLEANED'
        
    return str(soup)

def extract_text(html_content):
    """
    Extracts visible text content from HTML for granular analysis.
    """
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    # Get text
    text = soup.get_text()
    # Break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    return "\n".join(chunk for chunk in chunks if chunk)

def fetch_website_content(url, capture_screenshot=False, website_id=None):
    """
    Fetches website content using requests. Optionally runs selenium in headless mode
    to capture a full page screenshot.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    html_content = ""
    error_msg = ""
    success = False
    screenshot_file = None
    
    # Try fetching content using requests
    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        html_content = clean_html(response.text)
        success = True
    except requests.RequestException as e:
        error_msg = f"HTTP Request failed: {str(e)}"
        return ScrapeResult(success=False, error_message=error_msg)
        
    # Capture Screenshot if requested
    if capture_screenshot and success:
        screenshot_file = capture_page_screenshot(url, website_id)
        
    text_content = extract_text(html_content)
    return ScrapeResult(
        success=True, 
        html=html_content, 
        text=text_content, 
        screenshot_path=screenshot_file
    )

def capture_page_screenshot(url, website_id):
    """
    Helper function to render the page in Headless Chrome and save a screenshot.
    Gracefully falls back to None if Selenium is not available or fails to launch.
    """
    if not SELENIUM_AVAILABLE:
        print("Selenium is not installed. Skipping screenshot.")
        return None
        
    try:
        # Create output directory for screenshots
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'screenshots')
        os.makedirs(static_dir, exist_ok=True)
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,1024")
        
        # Disable logging in driver
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Set up chrome driver manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.set_page_load_timeout(20)
        driver.get(url)
        time.sleep(2)  # Wait for scripts to execute and page to settle
        
        filename = f"site_{website_id or 'temp'}_{int(time.time())}.png"
        filepath = os.path.join(static_dir, filename)
        
        driver.save_screenshot(filepath)
        driver.quit()
        
        # Return relative URL path for serving in Flask
        return f"/static/screenshots/{filename}"
        
    except Exception as e:
        print(f"Warning: Screenshot capture failed: {str(e)}")
        # Log to app context if available
        try:
            current_app.logger.warning(f"Screenshot failed for {url}: {str(e)}")
        except Exception:
            pass
        return None
