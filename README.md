# Parking Pass Generator

A Flask web application that processes Visual Matrix PMS (Property Management System) arrivals data and generates print-ready parking passes. The system processes CSV/XLS exports containing guest check-in information and creates PDF parking passes with confirmation numbers, check-in dates, length of stay, and QR codes.

## Features

- **Flexible File Upload**: Supports CSV, XLS, and XLSX formats with drag-and-drop functionality
- **Visual Matrix Format Support**: Automatically detects and processes complex Visual Matrix export formats
- **Smart Column Mapping**: Auto-detects confirmation numbers, arrival dates, and departure dates
- **PDF Generation**: Creates professional parking passes using your custom template
- **QR Code Integration**: Generates QR codes with guest information for easy scanning
- **Auto-sizing Text**: Automatically adjusts font size for variable-length confirmation numbers
- **Template Preview**: Debug tool to visualize text positioning on your template
- **Two-passes-per-page Layout**: Efficient printing with two identical passes per page
- **Automatic File Cleanup**: Removes old uploaded files and generated PDFs after 2 days to save disk space

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Self-Hosting Setup

1. **Clone or Download the Project**
   ```bash
   git clone <repository-url>
   # OR download and extract the ZIP file
   cd parking-pass-generator
   ```

2. **Create Virtual Environment** (Recommended)
   ```bash
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   If `requirements.txt` doesn't exist, install manually:
   ```bash
   pip install flask flask-sqlalchemy gunicorn pandas xlrd openpyxl reportlab pypdf pillow qrcode python-dateutil pyyaml email-validator psycopg2-binary werkzeug
   ```

4. **Create Required Directories**
   ```bash
   mkdir -p uploads output static templates
   ```

5. **Add Your Parking Pass Template**
   - Place your PDF template file in the `static/` directory
   - Name it `parking_pass_template.pdf`
   - Ensure it's sized for 8.5×11 inch paper

6. **Set Environment Variables**
   ```bash
   # Create a .env file or set environment variables
   export SESSION_SECRET="your-secret-key-here"
   export FLASK_ENV="development"  # or "production"
   
   # Optional: Database configuration (uses SQLite by default)
   export DATABASE_URL="sqlite:///parking_passes.db"
   ```

7. **Initialize the Application**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

## Usage

### Starting the Application

**Development Mode:**
```bash
python main.py
```
The application will be available at `http://localhost:5000`

**Production Mode:**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

### Using the Application

1. **Upload Visual Matrix Export**
   - Access the web interface at `http://localhost:5000`
   - Upload your CSV/XLS/XLSX file from Visual Matrix
   - The system automatically detects column formats

2. **Preview Template Positioning**
   - Click "Download Template Preview" to see where text will be placed
   - Use the colored guides to verify positioning:
     - Red: Confirmation numbers
     - Green: Arrival dates
     - Purple: Number of nights
     - Orange: QR code area

3. **Column Mapping** (if needed)
   - If auto-detection fails, manually map columns
   - Select which columns contain confirmation numbers, arrival dates, and departure dates

4. **Generate Parking Passes**
   - Review the data preview
   - Click "Generate PDF" to create parking passes
   - Download the resulting PDF with 2 passes per page

## Configuration

### Layout Configuration (`layout.yml`)

Customize text positioning and appearance:

```yaml
# PDF Layout Configuration
page:
  dpi: 72
  width: 612  # 8.5 inches * 72 dpi
  height: 792 # 11 inches * 72 dpi
  
  panels:
    top:
      origin: [0, 0]     # x, y from top-left
      height: 396        # Half page height
    bottom:
      origin: [0, 396]   # x, y from top-left  
      height: 396        # Half page height

fields:
  confirmation:
    offset: [120, 50]   # x, y offset from panel origin
    font_size: 12
    font: "Helvetica"
    color: "black"
    
  date:
    offset: [280, 50]   # x, y offset from panel origin
    font_size: 12
    font: "Helvetica"
    color: "black"
    
  nights:
    offset: [450, 50]   # x, y offset from panel origin
    font_size: 12
    font: "Helvetica"
    color: "black"

qr:
  content_template: "CONF={confirmation};ARR={arrival};NIGHTS={nights}"
  size_px: 80
  offset: [450, 200]   # x, y offset from panel origin
  border: 2
  error_correction: "M"  # L, M, Q, H
```

### Column Mapping Configuration (`config.yml`)

Define how to detect columns in Visual Matrix exports:

```yaml
# Column mapping for Visual Matrix exports
column_mappings:
  confirmation:
    keywords: ['conf', 'confirmation', 'conf #', 'conf#', 'confirm']
    priority: 1
    
  arrival:
    keywords: ['arrive', 'arrival', 'check-in', 'checkin', 'check in']
    priority: 2
    
  departure:
    keywords: ['depart', 'departure', 'departs', 'check-out', 'checkout', 'check out']
    priority: 3

# Date format handling
date_formats:
  input_formats:
    - '%m/%d/%Y'
    - '%Y-%m-%d'
    - '%d/%m/%Y'
    - '%m-%d-%Y'
  
  output_format: '%m/%d/%Y'
```

## File Structure

```
parking-pass-generator/
├── app.py                     # Main Flask application
├── main.py                    # Application entry point
├── config.yml                 # Column mapping configuration
├── layout.yml                 # PDF layout configuration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── static/
│   ├── parking_pass_template.pdf  # Your PDF template
│   ├── app.js                     # Frontend JavaScript
│   └── style.css                  # Custom styles (if any)
├── templates/
│   ├── index.html                 # Main upload page
│   └── preview.html               # Data preview page
├── uploads/                       # Temporary file storage
└── output/                        # Generated PDF storage
```

## Customization

### Adding Your Own Template

1. Create a PDF template sized for 8.5×11 inch paper
2. Leave blank spaces for:
   - Confirmation number
   - Arrival date
   - Number of nights staying
   - QR code area
3. Save as `static/parking_pass_template.pdf`
4. Use the template preview feature to adjust text positioning
5. Modify coordinates in `layout.yml` as needed

### Adjusting Text Positioning

1. Generate a template preview to see current positioning
2. Modify the `offset` values in `layout.yml`
3. Coordinates are in points (72 points = 1 inch)
4. Origin [0,0] is top-left of each panel
5. Test with preview until positioning is correct

## Troubleshooting

### Common Issues

**File Upload Errors:**
- Ensure file is in CSV, XLS, or XLSX format
- Check file size (maximum 16MB)
- Verify Visual Matrix export contains required columns

**PDF Generation Errors:**
- Confirm `parking_pass_template.pdf` exists in `static/` directory
- Check that template is a valid PDF file
- Verify `output/` directory has write permissions

**Text Positioning Issues:**
- Use template preview to visualize positioning
- Adjust coordinates in `layout.yml`
- Test with both short and long confirmation numbers

**Column Detection Issues:**
- Manually map columns if auto-detection fails
- Check that export contains standard Visual Matrix headers
- Verify data starts after header rows

### File Management

The application automatically manages disk space by:
- **Automatic Cleanup**: Removes files older than 2 days from uploads and output directories
- **Periodic Maintenance**: Runs cleanup every 24 hours automatically
- **Startup Cleanup**: Performs initial cleanup when the application starts

**Cleanup Schedule:**
- Upload files (CSV/Excel): Deleted after 2 days
- Generated PDFs: Deleted after 2 days
- Cleanup runs: Every 24 hours + on startup

### Performance Optimization

For production use:
- Use a production WSGI server like Gunicorn
- Configure proper logging
- Monitor disk space (automatic cleanup handles most cases)
- Consider adding user authentication
- Use a proper database (PostgreSQL recommended)

## Dependencies

- **Flask**: Web framework
- **Pandas**: Data processing and Excel file handling
- **ReportLab**: PDF generation
- **Pillow**: Image processing for QR codes
- **qrcode**: QR code generation
- **xlrd**: Legacy Excel file support
- **PyPDF**: PDF manipulation

## License

This project is designed for hotel/property management use. Customize and deploy according to your organization's needs.

## Support

For issues with:
- Visual Matrix export formats
- Template positioning
- PDF generation
- Custom configurations

Check the application logs and use the template preview feature to diagnose positioning issues.