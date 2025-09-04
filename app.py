import os
import logging
import pandas as pd
import xlrd
from datetime import datetime, timedelta
import re
import yaml
import qrcode
from PIL import Image, ImageDraw
import io
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile
from dateutil import parser as date_parser

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load configuration files
def load_config():
    """Load column mapping and date format configuration"""
    try:
        with open('config.yml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("config.yml not found, using default configuration")
        return get_default_config()

def load_layout():
    """Load layout configuration for PDF positioning"""
    try:
        with open('layout.yml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("layout.yml not found, using default layout")
        return get_default_layout()

def get_default_config():
    """Default configuration if config.yml is missing"""
    return {
        'columns': {
            'confirmation': ["Conf", "Conf #", "Confirmation", "Conf:", "Confirmation #"],
            'arrival': ["Arrive", "Arrival", "Check-In", "Check In", "Arrival Date"],
            'departure': ["Departs", "Departure", "Check-Out", "Check Out", "Departure Date"]
        },
        'date_format_in': ["%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"],
        'date_format_out': "%m/%d/%Y",
        'confirmation_regex': r"Conf[:#]?\s*(\d+)"
    }

def get_default_layout():
    """Default layout configuration if layout.yml is missing"""
    return {
        'page': {
            'dpi': 72,
            'panels': {
                'top': {'origin': [50, 100]},
                'bottom': {'origin': [50, 400]}
            }
        },
        'fields': {
            'confirmation': {'offset': [100, 50], 'font_size': 14},
            'date': {'offset': [100, 80], 'font_size': 14},
            'nights': {'offset': [100, 110], 'font_size': 14}
        },
        'qr': {
            'content_template': 'CONF={confirmation};ARR={arrival};NIGHTS={nights}',
            'size_px': 100,
            'offset': [300, 50],
            'border': 2
        }
    }

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_table(filepath):
    """Load CSV or XLS file into pandas DataFrame"""
    try:
        file_ext = filepath.rsplit('.', 1)[1].lower()
        
        if file_ext == 'csv':
            # Try different encodings for CSV
            for encoding in ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']:
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    logging.info(f"Successfully loaded CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV file with any supported encoding")
                
        elif file_ext in ['xls', 'xlsx']:
            # Try different header row positions for Excel files
            df = None
            engine = 'xlrd' if file_ext == 'xls' else 'openpyxl'
            
            # First, read the raw data to find the header row
            raw_df = pd.read_excel(filepath, engine=engine, header=None)
            logging.info(f"Raw Excel data shape: {raw_df.shape}")
            
            # Look for the header row by finding rows with meaningful header text
            header_row = 0
            for i in range(len(raw_df)):  # Check all rows
                row_data = raw_df.iloc[i].astype(str).str.strip()
                non_empty_vals = [val for val in row_data if val and val != 'nan' and val != 'NaN' and val != '']
                
                # If this row has multiple non-empty values, check if it's headers
                if len(non_empty_vals) >= 5:  # Need at least 5 columns for headers
                    row_text = ' '.join(non_empty_vals).lower()
                    header_keywords = ['guest', 'name', 'status', 'arrive', 'depart', 'room', 'rate', 'type']
                    
                    keyword_matches = sum(1 for keyword in header_keywords if keyword in row_text)
                    
                    if keyword_matches >= 3:  # Need at least 3 header keywords
                        header_row = i
                        logging.info(f"Found header row at index {i}: {non_empty_vals[:10]}")
                        break
            
            # Load with the detected header row
            df = pd.read_excel(filepath, engine=engine, header=header_row)
            
            # If we still have unnamed columns, try to use the data from a different row as headers
            if all(col.startswith('Unnamed:') for col in df.columns if isinstance(col, str)):
                logging.info("All columns are unnamed, trying alternative approaches")
                
                # Look for a row that could serve as headers
                for i in range(min(5, len(df))):
                    potential_headers = df.iloc[i].astype(str).str.strip()
                    if len(potential_headers.dropna()) >= 3:
                        # Use this row as headers and drop it from data
                        df.columns = potential_headers
                        df = df.drop(df.index[i]).reset_index(drop=True)
                        logging.info(f"Used row {i} as headers")
                        break
            
            logging.info(f"Successfully loaded {file_ext.upper()} file")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
            
        # Clean column names - strip whitespace and normalize
        df.columns = df.columns.astype(str).str.strip()
        
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        
        # Remove completely empty rows
        df = df.dropna(axis=0, how='all').reset_index(drop=True)
        
        # Special processing for Visual Matrix format
        if file_ext in ['xls', 'xlsx'] and any('Guest' in str(col) for col in df.columns):
            df = process_visual_matrix_format(df)
        
        logging.info(f"Final processed data: {len(df)} rows with columns: {list(df.columns)}")
        return df
        
    except Exception as e:
        logging.error(f"Error loading file {filepath}: {str(e)}")
        raise

def process_visual_matrix_format(df):
    """Process Visual Matrix specific format where confirmation numbers are on separate rows"""
    try:
        processed_rows = []
        
        for i, row in df.iterrows():
            # Check if this is a guest data row (has guest name)
            guest_name_col = None
            for col in df.columns:
                if 'Guest' in str(col) or 'Name' in str(col):
                    guest_name_col = col
                    break
            
            if guest_name_col and pd.notna(row[guest_name_col]) and ',' in str(row[guest_name_col]):
                # This is a guest row, look for confirmation number in the next row
                guest_data = row.copy()
                
                # Look ahead for confirmation number in next few rows
                conf_num = None
                for look_ahead in range(1, 4):  # Check next 3 rows
                    if i + look_ahead < len(df):
                        next_row = df.iloc[i + look_ahead]
                        # Convert all values to strings and look for Conf:
                        row_values = [str(val).strip() for val in next_row if pd.notna(val)]
                        
                        for j, val in enumerate(row_values):
                            if val == 'Conf:' and j + 1 < len(row_values):
                                # Next value should be the confirmation number
                                potential_conf = row_values[j + 1].strip()
                                # Remove any non-alphanumeric characters for validation
                                clean_conf = ''.join(c for c in potential_conf if c.isalnum() or c in '-')
                                if clean_conf and len(clean_conf) >= 3:  # Must be at least 3 chars
                                    conf_num = clean_conf
                                    logging.info(f"Found confirmation number: {conf_num}")
                                    break
                        
                        if conf_num:
                            break
                
                # Add confirmation number to guest data
                if conf_num:
                    guest_data['Confirmation'] = conf_num
                else:
                    guest_data['Confirmation'] = 'Not Found'
                
                processed_rows.append(guest_data)
        
        if processed_rows:
            result_df = pd.DataFrame(processed_rows)
            logging.info(f"Processed Visual Matrix format: {len(result_df)} guest records")
            return result_df
        else:
            logging.warning("No guest records found in Visual Matrix format")
            return df
            
    except Exception as e:
        logging.error(f"Error processing Visual Matrix format: {e}")
        return df

def auto_map_columns(df, config):
    """Automatically map DataFrame columns to required fields"""
    columns = df.columns.tolist()
    mapping = {}
    
    for field, possible_names in config['columns'].items():
        for col_name in columns:
            if any(possible.lower() in col_name.lower() for possible in possible_names):
                mapping[field] = col_name
                logging.info(f"Auto-mapped '{field}' to column '{col_name}'")
                break
    
    return mapping

def parse_date(date_str, date_formats):
    """Parse date string using multiple format attempts"""
    if pd.isna(date_str) or date_str == '':
        return None
        
    # Convert to string if not already
    date_str = str(date_str).strip()
    
    # Try configured formats first
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try dateutil parser as fallback
    try:
        return date_parser.parse(date_str)
    except:
        return None

def compute_nights(arrival, departure):
    """Compute number of nights between arrival and departure"""
    if not arrival or not departure:
        return None
    
    try:
        if isinstance(arrival, str):
            arrival = parse_date(arrival, load_config()['date_format_in'])
        if isinstance(departure, str):
            departure = parse_date(departure, load_config()['date_format_in'])
            
        if not arrival or not departure:
            return None
            
        nights = (departure - arrival).days
        return nights if nights > 0 else None
        
    except Exception as e:
        logging.error(f"Error computing nights: {e}")
        return None

def validate_rows(df, column_mapping, config):
    """Validate DataFrame rows and return errors/warnings"""
    errors = []
    valid_rows = []
    
    conf_col = column_mapping.get('confirmation')
    arrival_col = column_mapping.get('arrival')
    departure_col = column_mapping.get('departure')
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Validate confirmation number
        conf_num = None
        if conf_col and not pd.isna(row[conf_col]):
            conf_num = str(row[conf_col]).strip()
            if not conf_num:
                # Try regex fallback
                full_row_text = ' '.join([str(val) for val in row.values if not pd.isna(val)])
                match = re.search(config.get('confirmation_regex', r"Conf[:#]?\s*(\d+)"), full_row_text)
                if match:
                    conf_num = match.group(1)
                else:
                    row_errors.append("Missing or invalid confirmation number")
        else:
            row_errors.append("Missing confirmation number column")
        
        # Validate and parse dates
        arrival_date = None
        departure_date = None
        nights = None
        
        if arrival_col and not pd.isna(row[arrival_col]):
            arrival_date = parse_date(row[arrival_col], config['date_format_in'])
            if not arrival_date:
                row_errors.append("Invalid arrival date format")
        else:
            row_errors.append("Missing arrival date")
            
        if departure_col and not pd.isna(row[departure_col]):
            departure_date = parse_date(row[departure_col], config['date_format_in'])
            if not departure_date:
                row_errors.append("Invalid departure date format")
        else:
            row_errors.append("Missing departure date")
        
        if arrival_date and departure_date:
            nights = compute_nights(arrival_date, departure_date)
            if nights is None or nights <= 0:
                row_errors.append("Invalid stay duration (must be positive)")
        
        row_data = {
            'index': idx,
            'confirmation': conf_num,
            'arrival': arrival_date.strftime(config['date_format_out']) if arrival_date else '',
            'departure': departure_date.strftime(config['date_format_out']) if departure_date else '',
            'nights': nights,
            'errors': row_errors,
            'valid': len(row_errors) == 0,
            'raw_data': row.to_dict()
        }
        
        if row_errors:
            errors.append(row_data)
        else:
            valid_rows.append(row_data)
    
    return valid_rows, errors

def generate_qr_code(content, size=100):
    """Generate QR code image"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(content)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((size, size))
    
    return qr_img

def create_overlay_pdf(data_rows, layout_config):
    """Create PDF overlay with text and QR codes for parking passes"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    page_width, page_height = letter
    rows_per_page = 2  # Two passes per page
    
    for page_num, start_idx in enumerate(range(0, len(data_rows), rows_per_page)):
        if page_num > 0:
            c.showPage()
        
        page_rows = data_rows[start_idx:start_idx + rows_per_page]
        
        for panel_idx, row_data in enumerate(page_rows):
            panel_name = 'top' if panel_idx == 0 else 'bottom'
            panel_config = layout_config['page']['panels'][panel_name]
            origin_x, origin_y = panel_config['origin']
            
            # Convert from top-left to bottom-left coordinate system for ReportLab
            origin_y = page_height - origin_y
            
            # Draw confirmation number (fill in the blank after "Confirmation #")
            conf_config = layout_config['fields']['confirmation']
            conf_x = origin_x + conf_config['offset'][0]
            conf_y = origin_y - conf_config['offset'][1]
            c.setFont("Helvetica", conf_config['font_size'])
            c.drawString(conf_x, conf_y, str(row_data['confirmation']))
            
            # Draw date (fill in the blank after "Date")
            date_config = layout_config['fields']['date']
            date_x = origin_x + date_config['offset'][0]
            date_y = origin_y - date_config['offset'][1]
            c.setFont("Helvetica", date_config['font_size'])
            c.drawString(date_x, date_y, str(row_data['arrival']))
            
            # Draw nights (fill in the blank after "Days Staying")
            nights_config = layout_config['fields']['nights']
            nights_x = origin_x + nights_config['offset'][0]
            nights_y = origin_y - nights_config['offset'][1]
            c.setFont("Helvetica", nights_config['font_size'])
            c.drawString(nights_x, nights_y, str(row_data['nights']))
            
            # Generate and draw QR code
            qr_config = layout_config['qr']
            qr_content = qr_config['content_template'].format(
                confirmation=row_data['confirmation'],
                arrival=row_data['arrival'],
                nights=row_data['nights']
            )
            
            qr_img = generate_qr_code(qr_content, qr_config['size_px'])
            
            # Draw PIL image directly (ReportLab supports PIL images)
            qr_x = origin_x + qr_config['offset'][0]
            qr_y = origin_y - qr_config['offset'][1] - qr_config['size_px']
            
            c.drawImage(qr_img, qr_x, qr_y, 
                       width=qr_config['size_px'], 
                       height=qr_config['size_px'])
    
    c.save()
    buffer.seek(0)
    return buffer

def merge_pdf_overlay(template_path, overlay_buffer, output_path):
    """Merge overlay PDF with template PDF"""
    try:
        # Ensure template_path is a string
        if not isinstance(template_path, str):
            raise ValueError(f"Template path must be a string, got {type(template_path)}")
            
        # Check if template file exists
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        # Reset buffer position to beginning
        overlay_buffer.seek(0)
        
        # Create temporary file for overlay
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_overlay_file:
            temp_overlay_file.write(overlay_buffer.read())
            temp_overlay_path = temp_overlay_file.name
        
        try:
            # Read both PDFs
            template_reader = pypdf.PdfReader(template_path)
            overlay_reader = pypdf.PdfReader(temp_overlay_path)
            writer = pypdf.PdfWriter()
            
            if len(template_reader.pages) == 0:
                raise ValueError("Template PDF has no pages")
                
            template_page = template_reader.pages[0]
            
            # Merge each overlay page with the template
            for overlay_page in overlay_reader.pages:
                # Create a copy of the template page
                merged_page = template_page
                # Merge the overlay on top
                merged_page.merge_page(overlay_page)
                writer.add_page(merged_page)
            
            # Write the final PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logging.info(f"Successfully created merged PDF: {output_path}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_overlay_path):
                os.unlink(temp_overlay_path)
        
    except Exception as e:
        logging.error(f"Error merging PDFs: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        raise

# Flask routes
@app.route('/')
def index():
    """Main upload and processing page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and initial processing"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Load and process the file
            df = load_table(filepath)
            config = load_config()
            column_mapping = auto_map_columns(df, config)
            
            # Store in session for further processing
            session['current_file'] = filename
            session['column_mapping'] = column_mapping
            session['columns'] = df.columns.tolist()
            
            flash(f'File uploaded successfully. Found {len(df)} rows.', 'success')
            return redirect(url_for('column_mapping'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload CSV, XLS, or XLSX files.', 'error')
        return redirect(url_for('index'))

@app.route('/column-mapping')
def column_mapping():
    """Column mapping interface"""
    if 'current_file' not in session:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))
    
    try:
        # Load the file to get data preview
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], session['current_file'])
        df = load_table(filepath)
        
        # Get preview data (first 3 non-empty rows for each column)
        column_previews = {}
        for col in df.columns:
            # Get first 3 non-null, non-empty values
            non_empty_values = df[col].dropna().astype(str).str.strip()
            non_empty_values = non_empty_values[non_empty_values != ''].head(3).tolist()
            column_previews[col] = non_empty_values
        
        return render_template('index.html', 
                             show_mapping=True,
                             columns=session.get('columns', []),
                             current_mapping=session.get('column_mapping', {}),
                             column_previews=column_previews)
    except Exception as e:
        flash(f'Error loading file for preview: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/process-data', methods=['POST'])
def process_data():
    """Process data with user-confirmed column mapping"""
    if 'current_file' not in session:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))
    
    # Get user's column mapping
    column_mapping = {
        'confirmation': request.form.get('confirmation_col'),
        'arrival': request.form.get('arrival_col'),
        'departure': request.form.get('departure_col')
    }
    
    # Remove None values
    column_mapping = {k: v for k, v in column_mapping.items() if v}
    
    if len(column_mapping) < 3:
        flash('Please map all required columns (Confirmation, Arrival, Departure)', 'error')
        return redirect(url_for('column_mapping'))
    
    try:
        # Load file and process data
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], session['current_file'])
        df = load_table(filepath)
        config = load_config()
        
        valid_rows, errors = validate_rows(df, column_mapping, config)
        
        # Store processed data in session
        session['valid_rows'] = valid_rows
        session['errors'] = errors
        session['column_mapping'] = column_mapping
        
        flash(f'Data processed: {len(valid_rows)} valid rows, {len(errors)} errors', 'info')
        return redirect(url_for('preview_data'))
        
    except Exception as e:
        flash(f'Error processing data: {str(e)}', 'error')
        return redirect(url_for('column_mapping'))

@app.route('/preview')
def preview_data():
    """Preview processed data before PDF generation"""
    if 'valid_rows' not in session:
        flash('No processed data available', 'error')
        return redirect(url_for('index'))
    
    return render_template('preview.html', 
                         valid_rows=session.get('valid_rows', []),
                         errors=session.get('errors', []))

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate parking pass PDF"""
    if 'valid_rows' not in session:
        flash('No processed data available', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get selected rows (if any specific selection was made)
        selected_indices = request.form.getlist('selected_rows')
        valid_rows = session['valid_rows']
        
        if selected_indices:
            # Filter to selected rows only
            selected_indices = [int(idx) for idx in selected_indices]
            valid_rows = [row for i, row in enumerate(valid_rows) if i in selected_indices]
        
        if not valid_rows:
            flash('No rows selected for PDF generation', 'error')
            return redirect(url_for('preview_data'))
        
        # Load layout configuration
        layout_config = load_layout()
        
        # Generate final PDF
        output_filename = f"Parking_Passes_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        template_path = os.path.join('static', 'parking_pass_template.pdf')
        
        # Log debug info
        logging.info(f"Template path: {template_path}")
        logging.info(f"Template exists: {os.path.exists(template_path)}")
        logging.info(f"Output path: {output_path}")
        
        # Try creating PDF directly without overlay for now
        try:
            logging.info("Creating overlay PDF...")
            overlay_buffer = create_overlay_pdf(valid_rows, layout_config)
            logging.info(f"Overlay created successfully, type: {type(overlay_buffer)}")
            
            # For debugging, save just the overlay first
            with open(output_path.replace('.pdf', '_overlay_only.pdf'), 'wb') as f:
                overlay_buffer.seek(0)
                f.write(overlay_buffer.read())
            logging.info("Overlay PDF saved for debugging")
            
            # Now try merging with template
            logging.info("Starting template merge...")
            merge_pdf_overlay(template_path, overlay_buffer, output_path)
            logging.info("Template merge completed")
            
        except Exception as e:
            logging.error(f"Error in PDF creation: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        flash(f'PDF generated successfully: {len(valid_rows)} passes created', 'success')
        
        # Return the PDF file for download
        return send_file(output_path, as_attachment=True, download_name=output_filename)
        
    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('preview_data'))

@app.route('/reset')
def reset_session():
    """Reset session and start over"""
    session.clear()
    flash('Session reset. You can upload a new file.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
