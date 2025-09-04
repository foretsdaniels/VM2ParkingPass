# Overview

A Flask web application that generates print-ready parking passes from Visual Matrix PMS (Property Management System) arrivals data. The system processes CSV/XLS exports containing guest check-in information and creates PDF parking passes with confirmation numbers, check-in dates, length of stay, and QR codes. Designed to handle inconsistent data formats common in PMS exports.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap-based responsive UI
- **Styling**: Bootstrap 5 with dark theme and Font Awesome icons
- **JavaScript**: Vanilla JS for drag-and-drop file upload functionality
- **User Interface**: Multi-step workflow (upload → column mapping → preview → generate)

## Backend Architecture
- **Framework**: Flask with modular route handling
- **File Processing**: Pandas for CSV/Excel data manipulation with xlrd for legacy XLS support
- **PDF Generation**: ReportLab for creating parking passes from templates
- **Configuration Management**: YAML-based configuration for column mappings, date formats, and layout positioning
- **Data Validation**: Built-in validation for date ranges, confirmation numbers, and stay duration calculations
- **Error Handling**: Comprehensive error reporting with user-friendly flash messages

## Data Processing Pipeline
- **Input Validation**: File type checking and size limits (16MB max)
- **Column Mapping**: Flexible mapping system to handle varying PMS export formats
- **Date Processing**: Multi-format date parsing with configurable input/output formats
- **Business Logic**: Automatic calculation of stay duration from arrival/departure dates
- **Quality Control**: Data filtering and sorting options with error row identification

## PDF Generation System
- **Template-Based**: Uses provided PDF template with precise coordinate positioning
- **Dual Layout**: Generates two identical passes per page for efficiency
- **QR Code Integration**: Configurable QR code content generation
- **Typography**: Configurable font settings through layout configuration

# External Dependencies

## Core Libraries
- **Flask**: Web application framework with session management and file upload handling
- **Pandas**: Data manipulation and analysis for CSV/Excel processing
- **xlrd**: Legacy Excel file format support
- **ReportLab**: PDF generation and manipulation
- **PyPDF**: PDF file operations and template handling
- **Pillow (PIL)**: Image processing for QR code generation
- **qrcode**: QR code generation functionality

## Configuration Files
- **config.yml**: Column mapping definitions and date format specifications
- **layout.yml**: PDF positioning coordinates and typography settings

## File System Dependencies
- **Upload Directory**: Temporary storage for uploaded PMS exports
- **Output Directory**: Generated PDF storage location
- **Template Assets**: PDF template files for pass generation

## Runtime Environment
- **Python 3.x**: Core runtime environment
- **Werkzeug**: WSGI utilities and proxy handling for deployment flexibility