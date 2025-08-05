# app.py
import os
import sys
import time
from datetime import datetime
from typing import Dict
import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from playwright.sync_api import sync_playwright


load_dotenv()
FLASK_SECRET = os.getenv("FLASK_SECRET", "dev-fallback")
BASE_URL = os.getenv("BASE_URL", "https://delhihighcourt.nic.in")
CAPTCHA_SOLVER = os.getenv("CAPTCHA_SOLVER", "manual")  # manual | 2captcha
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "")

app = Flask(__name__)
app.secret_key = FLASK_SECRET


# Keep all selectors in one place - makes updates easier when site changes
SELECTORS: Dict[str, str] = {
    "case_type_dropdown": "#case_type",
    "case_number_input": "#case_number",
    "case_year_dropdown": "#case_year",
    "submit_button": "#search",
    "results_table": "#caseTable",
    "parties_cell": "#caseTable > tbody > tr > td:nth-child(3)",           # fallback text search ready
    "dates_cell": "#caseTable > tbody > tr > td:nth-child(4)",
    "pdf_link": "#caseTable > tbody > tr:nth-child(1) > td:nth-child(2) > a",
    "captcha_img": "#captcha-code",
    "captcha_input": "#captchaInput",


}

def row_based_selector(row, nth):
    """Grab text from nth cell in a row, handles missing cells gracefully"""    
    try:
        return row.locator("td").nth(nth).inner_text(timeout=1000).strip()
    except Exception:
        return "Not available"

def first_pdf_link(row):
    """Extract PDF href from row, convert relative URLs to absolute"""
    link = row.locator('a[href*=".pdf"]').first
    href = link.get_attribute("href") if link.count() else None
    if href and href.startswith("/"):
        href = BASE_URL + href
    return href


def safe_text(page, selector: str, fallback: str = "Not available") -> str:
    """Get text from element, return fallback if element doesn't exist or times out"""
    try:
        el = page.locator(selector).first
        return el.inner_text(timeout=2000).strip()
    except Exception:
        return fallback


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    # Basic form validation
    case_number = request.form.get("case_number", "").strip()
    case_type = request.form.get("case_type", "").strip()
    filing_year = request.form.get("filing_year", "").strip()

    errors = []
    if not case_number:
        errors.append("Case number is required")
    if not case_type:
        errors.append("Case type is required")
    if not filing_year:
        errors.append("Filing year is required")

    # Validate year range - court doesn't have cases before 1951
    try:
        year = int(filing_year)
        current_year = datetime.now().year
        if year < 1951 or year > current_year:
            errors.append(f"Filing year must be between 1951 and {current_year}")
    except ValueError:
        errors.append("Filing year must be a valid number")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("index"))

    # Do the actual scraping
    try:
        results = scrape_case_details(case_number, case_type, filing_year)
        flash("Search completed", "success" if results["found"] else "warning")
    except Exception as ex:
        flash(f"Search error: {ex}", "error")
        # Return basic error response so page doesn't break
        results = dict(
            case_number=case_number,
            case_type=case_type,
            filing_year=filing_year,
            status="Technical failure",
            found=False,
        )

    return render_template("index.html", results=results)


def scrape_case_details(case_number: str, case_type: str, filing_year: str):
    with sync_playwright() as p:
        # Keep browser visible for debugging, add delay to avoid getting blocked
        browser = p.chromium.launch(headless=False, slow_mo=800)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/app/get-case-type-status", timeout=30000)
            page.wait_for_load_state("networkidle")

            # Handle CAPTCHA if it shows up 
            if not handle_captcha(page):
                raise Exception("CAPTCHA not solved")

            # Fill out the search form
            page.select_option(SELECTORS["case_type_dropdown"], value=case_type)
            page.fill(SELECTORS["case_number_input"], case_number)
            page.select_option(SELECTORS["case_year_dropdown"], value=filing_year)

            # Submit and wait for results
            page.click(SELECTORS["submit_button"])
            page.wait_for_load_state("networkidle")
            time.sleep(2) # Give results time to load completely

            return extract_case_data(page, case_number, case_type, filing_year)
        finally:
            browser.close()


def handle_captcha(page):
    """Try to solve CAPTCHA if present, return True if successful or no CAPTCHA"""
    img = page.locator(SELECTORS["captcha_img"])
    inp = page.locator(SELECTORS["captcha_input"])
    if img.count() == 0 or inp.count() == 0:
        return True  # no captcha

    if CAPTCHA_SOLVER == "2captcha" and TWOCAPTCHA_KEY:
        return solve_with_2captcha(page, img)
    else:
        return solve_manually(page, img, inp)


def solve_manually(page, img, inp):
    """Save CAPTCHA image and ask user to solve it"""
    import platform, subprocess
    from pathlib import Path
    img_path = Path('C:/Users/DELL/OneDrive/Desktop/delhi-hc-scraper/captcha_images/captcha_img.png')
    os.makedirs("captcha_images", exist_ok=True)
    img.screenshot(path=img_path)
    
    # Try to open image automatically for user
    system = platform.system()
    if system == "Windows":
        os.startfile(img_path)
    elif system == "Darwin":
        subprocess.run(["open", img_path])
    else:
        subprocess.run(["xdg-open", img_path])
    
    solution = input("Enter CAPTCHA text (or 'skip'): ").strip()
    if not solution or solution.lower() == "skip":
        return False
    inp.fill(solution)
    inp.press("Enter")
    time.sleep(2)
    return True


def solve_with_2captcha(page, img_locator):
    """Use 2captcha service to solve CAPTCHA automatically"""
    if not TWOCAPTCHA_KEY:
        print("[WARN] 2Captcha key missing – skipping")
        return False

    # Upload CAPTCHA image to 2captcha
    img_bytes = img_locator.screenshot()
    files = {"file": ("captcha.png", img_bytes, "image/png")}
    data = {"key": TWOCAPTCHA_KEY, "method": "post"}
    upload = requests.post("http://2captcha.com/in.php", files=files, data=data)
    if "OK|" not in upload.text:
        print("[2Captcha] upload failed:", upload.text)
        return False
    captcha_id = upload.text.split("|")[1]

    # Poll for solution - usually takes 10-30 seconds
    for _ in range(24):  # max 2 minutes
        time.sleep(5)
        res = requests.get(
            "http://2captcha.com/res.php",
            params={"key": TWOCAPTCHA_KEY, "action": "get", "id": captcha_id},
        )
        if "OK|" in res.text:
            solution = res.text.split("|")[1]
            page.locator(SELECTORS["captcha_input"]).fill(solution)
            page.locator(SELECTORS["captcha_input"]).press("Enter")
            time.sleep(2)
            return True
    print("[2Captcha] timeout")
    return False


def extract_case_data(page, case_number, case_type, filing_year):
    """Extract case info from results page"""
    import re
    captcha_dir = "captcha_images"
    for f in os.listdir(captcha_dir):
        os.remove(os.path.join(captcha_dir, f))
    table = page.locator(SELECTORS["results_table"])
    
    # Get first result row
    row = table.locator("tbody tr").first

    # Extract basic info from table cells
    parties = safe_text(row, "td:nth-child(3)")
    dates = safe_text(row, "td:nth-child(4)")


    # Parse dates information
    next_date = "Not available"
    last_date = "Not available"
    court_no = "Not available"
    
    # Use regex to extract structured information
    date_match = re.search(
        r'NEXT DATE:\s*(.*?)\s*Last Date:\s*(.*?)\s*COURT NO:\s*(.*)',
        dates
    )
    
    if date_match:
        next_date = date_match.group(1).strip() or "NA"
        last_date = date_match.group(2).strip() or "Not available"
        court_no = date_match.group(3).strip() or "Not available"

    # Handle PDF link - court site uses intermediate pages, so need to follow the chain
    pdf_link_element = page.locator("#caseTable > tbody > tr > td:nth-child(2) > a:nth-child(5)")
    pdf_url = None
        
    if pdf_link_element.count() > 0:
        intermediate_url = pdf_link_element.get_attribute("href")
        print(f"Found intermediate PDF link: {intermediate_url}")
        
        # Navigate to get actual PDF URL
        pdf_url = get_actual_pdf_url(page, intermediate_url)
    else:
        print("No PDF link found")

    return dict(
        case_number=case_number,
        case_type=case_type,
        filing_year=filing_year,
        parties=parties,
        next_hearing_date=next_date,
        last_hearing_date=last_date,
        court_no=court_no,
        pdf_url=pdf_url,
        status="Case details extracted",
        found=True,
    )

def get_actual_pdf_url(page, intermediate_url):
    """Navigate through intermediate page to get direct PDF link"""
    
    try:
        # Convert relative URL to absolute
        if intermediate_url and intermediate_url.startswith("/"):
            intermediate_url = "https://delhihighcourt.nic.in" + intermediate_url
        elif intermediate_url and not intermediate_url.startswith("http"):
            intermediate_url = "https://delhihighcourt.nic.in/" + intermediate_url
        
        print(f"Navigating to intermediate page: {intermediate_url}")
        
        # Remember where we are so we can come back
        current_url = page.url
        
        # Go to intermediate page
        page.goto(intermediate_url, timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Find the actual PDF link on this page
        print("Looking for actual PDF link...")
        actual_pdf_element = page.locator("#caseTable > tbody > tr:nth-child(1) > td:nth-child(2) > a")
        
        # Make sure we have absolute URL
        actual_pdf_url = None
        if actual_pdf_element.count() > 0:
            actual_pdf_url = actual_pdf_element.get_attribute("href")
            
            # Convert relative URL to absolute if needed
            if actual_pdf_url and actual_pdf_url.startswith("/"):
                actual_pdf_url = "https://delhihighcourt.nic.in" + actual_pdf_url
            elif actual_pdf_url and not actual_pdf_url.startswith("http"):
                actual_pdf_url = "https://delhihighcourt.nic.in/" + actual_pdf_url
            
            print(f"Found actual PDF URL: {actual_pdf_url}")
        else:
            print("No actual PDF link found on intermediate page")
        
        # Navigate back to the original results page (optional)
        try:
            page.goto(current_url, timeout=10000)
            page.wait_for_load_state("networkidle")
        except:
            print("Could not navigate back to results page, continuing...")
        
        return actual_pdf_url
        
    except Exception as e:
        print(f"Error getting actual PDF URL: {str(e)}")
        return None

# Quick selector test for debugging when site structure changes
if __name__ == "__main__":
    if "--test-selectors" in sys.argv:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/app/get-case-type-status")
            for name, sel in SELECTORS.items():
                found = page.locator(sel).count()
                print(f"{name:20} -> {'✅' if found else '❌'}")
            browser.close()
        sys.exit(0)

    app.run(debug=True, host="127.0.0.1", port=5000)