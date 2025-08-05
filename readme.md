# Delhi High Court Case Scraper

A web application that automates case lookup from the Delhi High Court website using web scraping with automatic CAPTCHA solving capabilities.

## Features

- **Automated Case Search**: Search for cases by case number, type, and filing year
- **Automatic CAPTCHA Solving**: Uses pytesseract OCR to automatically solve CAPTCHAs
- **Comprehensive Case Details**: Extracts parties, hearing dates, court numbers, and PDF links
- **User-Friendly Interface**: Clean Bootstrap-based web interface with loading indicators
- **PDF Document Access**: Direct links to case documents when available

## Technologies Used

- **Backend**: Python Flask
- **Web Scraping**: Playwright (Chromium browser automation)
- **CAPTCHA Solving**: pytesseract + Pillow (OCR with image preprocessing)
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Template Engine**: Jinja2

## Installation

### Prerequisites

1. **Python 3.7+**
2. **Tesseract OCR** (for CAPTCHA solving)
   - **Windows**: Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd delhi-hc-scraper
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

5. **Create `.env` file**:
   ```bash
   FLASK_SECRET=your-secret-key-here
   BASE_URL=https://delhihighcourt.nic.in
   TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe  # Windows only, if needed
   ```

## Dependencies

Create a `requirements.txt` file with:

```
flask
playwright
python-dotenv
pytesseract
pillow
requests
```

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

3. **Search for a case**:
   - Enter the case number (e.g., 123)
   - Select case type (e.g., W.P.(C), CRL.A., etc.)
   - Choose filing year (1951-2025)
   - Click "Search Case"

4. **Wait for results**:
   - The application will automatically handle any CAPTCHAs
   - Loading screen shows progress
   - Results display case details, hearing dates, and PDF links

## Project Structure

```
delhi-hc-scraper/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Web interface template
├── .env                  # Environment variables (create this)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### Environment Variables

- `FLASK_SECRET`: Secret key for Flask sessions
- `BASE_URL`: Delhi High Court base URL (default: https://delhihighcourt.nic.in)
- `TESSERACT_PATH`: Path to tesseract executable (Windows users may need this)

### CAPTCHA Settings

The application automatically handles CAPTCHAs using:
- Image preprocessing (grayscale, resize, contrast enhancement)
- OCR with custom tesseract configuration
- Up to 3 retry attempts per CAPTCHA
- Automatic form submission after solving

## How It Works

1. **User submits search form** → Flask receives request
2. **Playwright launches browser** → Navigates to court website
3. **Form filling** → Enters case details into search form
4. **CAPTCHA detection** → Checks for CAPTCHA presence
5. **OCR processing** → Screenshots and processes CAPTCHA image
6. **Automatic solving** → Fills CAPTCHA and submits form
7. **Data extraction** → Scrapes case details from results
8. **Response** → Returns formatted case information

## Supported Case Types

The application supports all Delhi High Court case types including:
- W.P.(C) - Writ Petition (Civil)
- CRL.A. - Criminal Appeal
- CS(OS) - Civil Suit (Original Side)
- FAO - First Appeal from Order
- MAT. - Motor Accident Tribunal
- And many more...

## Limitations

- **Rate Limiting**: Built-in delays to avoid being blocked
- **CAPTCHA Accuracy**: OCR success depends on CAPTCHA complexity
- **Browser Dependency**: Requires Chromium browser for automation
- **Network Dependent**: Requires stable internet connection

## Troubleshooting

### Common Issues

1. **Tesseract not found**:
   - Install Tesseract OCR
   - Set `TESSERACT_PATH` in `.env` file (Windows)

2. **Browser launch fails**:
   - Run `playwright install chromium`
   - Check system permissions

3. **CAPTCHA solving fails**:
   - CAPTCHAs may be too complex for OCR
   - Network issues during image processing
   - Try running again (automatic retry included)

4. **No results found**:
   - Verify case number, type, and year are correct
   - Case might not exist in the database
   - Check Delhi High Court website availability

### Debug Mode

Run with debugging enabled:
```bash
python app.py --debug
```

Test selectors (useful when website changes):
```bash
python app.py --test-selectors
```

## Legal Disclaimer

This tool is for educational and research purposes only. Users are responsible for:
- Complying with the Delhi High Court website's terms of service
- Using the tool ethically and responsibly
- Verifying information through official channels
- Respecting rate limits and server resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes. Please respect the Delhi High Court's terms of service and use responsibly.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review error logs in the console
3. Ensure all dependencies are properly installed
4. Verify environment configuration

---

**Note**: This application automates interaction with a government website. Always ensure your usage complies with applicable laws and the website's terms of service.
