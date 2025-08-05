# Delhi High Court Case Scraper

**Implementation of Task**

A web scraping application written in Flask that fetches case information automatically from the official Delhi High Court website. This task showcases skills in web automation, API, error handling, and creating intuitive interfaces for complicated web scraping processes.

## Task Overview

**Challenge**: Create a system to extract case data programmatically from the Delhi High Court website, which offers a number of technical hurdles:
- Interactive form submissions needing specific case types and years
- CAPTCHA defense blocking robot access
- Multi-step navigation to access real PDF documents
- Compose DOM structure necessitating accurate element targeting

**Solution**: A full-stack web application employing browser automation to address the entire user experience, from form submission to document retrieval.

## Technical Implementation

### Architecture Decisions

**HTTP Request Automation over Browser**: Preferred Playwright over conventional scraping libraries (BeautifulSoup, Scrapy) since the website loads dynamic content. Form interactions and transition between pages on the court website demand a complete browser context to be effective.

**Full-Stack Web Interface with Flask**: Used a simple web UI instead of a CLI utility to showcase full-stack feature and improve user experience for the non-technical crowd.

**Modular Design**: Split concerns into independent functions (CAPTCHA processing, form interaction, data extraction) to support testability and maintainability.

### Technical Features of Note

#### 1. Smart CAPTCHA Solution
```python
def handle_captcha(page):
    """Dual-mode CAPTCHA solving with fallback strategy"""
```
- **Manual Mode**: Solves CAPTCHA images and asks for user input automatically
- **Automated Mode**: Utilizes 2captcha API to solve CAPTCHA automatically
- **Graceful Fallback**: Operates even without CAPTCHA

#### 2. Multi-Step PDF Extraction
```python
```
def get_actual_pdf_url(page, intermediate_url):
    """Navigate through intermediate pages to extract direct PDF links"""
```
The court website has a two-step PDF access process. My solution:
- Identifies intermediate PDF links in search results
- Traverses intermediate pages keeping session state
- Extracts final PDF URLs and resolves relative paths to absolute URLs
- Inserts proper error handling and page state management

#### 3. Centralized Selector Management
```python
SELECTORS: Dict[str, str] = {"}}}
"case_type_dropdown": "#case_type",
"case_number_input": "#case_number",
#. more selectors
```
- Groups all CSS selectors into one configuration
- Supports maintenance ease if website structure is altered
- Integrates a validator for selectors

#### 4. Strong Error Handling
- Network timeout handling with customizable delay
- Checking availability of elements prior to interaction
- Through form validation with informative error messages
- Degrading gracefully in case of absent optional elements

### Technical Stack

- **Backend**: Flask (web framework for Python)
- **Automation**: Playwright (browser automation)
- **Environment**: python-dotenv for configuration management
- **CAPTCHA**: Integration with 2captcha API
- **Frontend**: HTML templates styled with Bootstrap

## Implementation Highlights

### 1. Smart Form Interaction
```python
def scrape_case_details(case_number: str, case_type: str, filing_year: str):
    # Manages dropdown choices, text input, form submission
    page.select_option(SELECTORS["case_type_dropdown"], value=case_type)
    page.fill(SELECTORS["case_number_input"], case_number)
    page.select_option(SELECTORS["case_year_dropdown"], value=filing_year")
```

### 2. Fallback Data Extraction
```python
def safe_text(page, selector: str, fallback: str = "Not available") -> str:
    """Defensive programming for unstable DOM elements"""
```

### 3. Environment-Based Config Management
Applied adequate configuration management for various deployment environments:
- Development and production configurations
- API key management for out-of-house services
- Base URL configuration flexibility

## Problem-Solving Strategy

### Challenge 1: Court Website Structure Analysis
- Manually inspected the court website form structure and data flow
- Discovered the multi-step PDF access pattern using browser developer tools
- Reverse-engineered the precise selectors necessary for robust automation

### Challenge 2: CAPTCHA Handling Strategy
- Research done on several CAPTCHA solving strategies
- Used manual as well as automated solutions to provide flexibility
- Included proper error handling in case of CAPTCHA failure

### Challenge 3: Reliability and Maintenance
- Created selector testing features for maintenance over time
- Implemented robust logging and error reporting
- Applied defensive programming methods for volatile web elements

## Installation and Usage

### Quick Start
```bash
# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install dependencies
pip install flask playwright requests python-dotenv
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run application
python app.py
```

### Environment Configuration
```env
FLASK_SECRET=your-secret-key
BASE_URL=https://delhihighcourt.nic.in
CAPTCHA_SOLVER=manual  # or 2captcha
TWOCAPTCHA_KEY=your-api-key-if-using-2captcha
```

### Testing Selectors
```bash
python app.py --test-selectors
```

## Project Outcomes

### Demonstrated Skills
- **Web Scraping**: Complex multi-step automation with dynamic content
- **API Integration**: Third-party service integration (2captcha)
- **Error Handling**: Edge case management across the board
- **User Experience**: Clean design for technical functionality
- **Code Organization**: Modular, maintainable code
- **Configuration Management**: Environment-based configuration
- **Documentation**: Clear technical documentation

### Challenges Overcome
1. **Dynamic Content**: Correctly processed JavaScript-heavy forms
2. **Anti-Bot Measures**: Used CAPTCHA solving without causing blocks
3. **Complex Navigation**: Automated retrieval of multi-page documents
4. **Reliability**: Implemented robust error handling for flaky website elements
5. **User Experience**: Made advanced automation available via web interface

## Technical Decisions Justified

**Why Playwright instead of Selenium?**: more consistent element interaction, and updated async/await support.

**Why Flask instead of FastAPI?**: Easier setup for this scale, improved template engine support, and easier session handling.

**Why Manual CAPTCHA Option?**: Offers backup when automated services don't work, shows comprehension of user experience implications.

**Why Centralized Selectors?**: Demonstrates thought on maintainability and the nature of web scraping production systems.

## Future Enhancements

If it were a production system, I would add:
- Storage of scraped case data in a database
- Bulk case processing with queue handling
- Rate limiting to be courteous to the court website
- Caching layer to reduce redundant requests
- API endpoints for accessing programs
- Docker containerization for deployment
- Monitoring and alerting for website changes

## Code Quality

- **Type Hints**: Employed across for improved code documentation
- **Error Handling**: Exhaustive exception handling
- **Logging**: Ordered logging to facilitate debugging and monitoring
- **Configuration**: Environment-driven settings management
- **Testing**: Integrated selector validation tools
- **Documentation**: Inline comments describing intricate logic

This solution attests to the capability to address practical web scraping challenges while developing maintainable, user-centric software solutions.