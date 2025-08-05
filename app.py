# app.py
import os
import sys
import time
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from playwright.sync_api import sync_playwright
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io


load_dotenv()
FLASK_SECRET = os.getenv("FLASK_SECRET", "dev-fallback")
BASE_URL = os.getenv("BASE_URL", "https://delhihighcourt.nic.in")
# Set tesseract path if needed (Windows users typically need this)
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

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
        browser = p.chromium.launch(headless=True, slow_mo=800)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/app/get-case-type-status", timeout=30000)
            page.wait_for_load_state("networkidle")

            # Fill out the search form first
            page.select_option(SELECTORS["case_type_dropdown"], value=case_type)
            page.fill(SELECTORS["case_number_input"], case_number)
            page.select_option(SELECTORS["case_year_dropdown"], value=filing_year)

            # Handle CAPTCHA if it shows up (this will also submit the form)
            if not handle_captcha(page):
                raise Exception("CAPTCHA not solved")

            # Wait for results to load
            page.wait_for_load_state("networkidle")
            time.sleep(2) # Give results time to load completely

            return extract_case_data(page, case_number, case_type, filing_year)
        finally:
            browser.close()


def preprocess_captcha_image(image_bytes):
    """
    Preprocess CAPTCHA image to improve OCR accuracy
    """
    # Open image from bytes
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Resize image to make text larger (improves OCR)
    width, height = image.size
    image = image.resize((width * 3, height * 3), Image.LANCZOS)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Apply threshold to make it binary (black and white)
    threshold = 128
    image = image.point(lambda x: 0 if x < threshold else 255, '1')
    
    # Apply slight blur to smooth edges
    image = image.filter(ImageFilter.MedianFilter(size=3))
    
    return image


def solve_captcha_with_ocr(page, img_locator, inp_locator, max_attempts=3):
    """
    Solve CAPTCHA using pytesseract OCR with image preprocessing
    """
    for attempt in range(max_attempts):
        try:
            print(f"CAPTCHA solving attempt {attempt + 1}/{max_attempts}")
            
            # Get CAPTCHA image as bytes
            img_bytes = img_locator.screenshot()
            
            # Preprocess image for better OCR
            processed_image = preprocess_captcha_image(img_bytes)
            
            # Configure tesseract for better CAPTCHA recognition
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            
            # Extract text using OCR
            captcha_text = pytesseract.image_to_string(processed_image, config=custom_config).strip()
            
            # Clean the extracted text (remove spaces, special characters)
            captcha_text = ''.join(char for char in captcha_text if char.isalnum())
            
            print(f"Extracted CAPTCHA text: '{captcha_text}'")
            
            if len(captcha_text) >= 4:  # Most CAPTCHAs are at least 4 characters
                # Fill the CAPTCHA input
                inp_locator.fill(captcha_text)
                
                # Click the search button to submit the form with CAPTCHA
                search_button = page.locator(SELECTORS["submit_button"])
                if search_button.count() > 0:
                    search_button.click()
                    time.sleep(3)  # Wait for validation
                    
                    # Check if CAPTCHA was accepted by looking for results or if CAPTCHA input disappeared
                    if inp_locator.count() == 0 or page.locator(SELECTORS["results_table"]).count() > 0:
                        print("CAPTCHA solved successfully!")
                        return True
                    else:
                        print(f"CAPTCHA attempt {attempt + 1} failed, trying again...")
                else:
                    print("Search button not found")
                    return False
            else:
                print(f"Extracted text too short: '{captcha_text}', trying again...")
                
        except Exception as e:
            print(f"Error in CAPTCHA attempt {attempt + 1}: {str(e)}")
            
        # Wait before next attempt
        if attempt < max_attempts - 1:
            time.sleep(2)
    
    print("Failed to solve CAPTCHA after all attempts")
    return False


def handle_captcha(page):
    """Try to solve CAPTCHA if present using OCR, return True if successful or no CAPTCHA"""
    img = page.locator(SELECTORS["captcha_img"])
    inp = page.locator(SELECTORS["captcha_input"])
    
    if img.count() == 0 or inp.count() == 0:
        print("No CAPTCHA found")
        return True  # no captcha
    
    print("CAPTCHA detected, attempting to solve with OCR...")
    return solve_captcha_with_ocr(page, img, inp)


def extract_case_data(page, case_number, case_type, filing_year):
    """Extract case info from results page"""
    import re
    
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
        
        # Navigate back to the original results page
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
