import csv
import requests
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import landscape, A4, portrait
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger, PdfReader
import os
import tempfile
import re
from PIL import Image as PILImage
import io

def download_csv_from_gist(url):
    """Download CSV data from gist URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error downloading CSV: {e}")
        raise

def parse_csv_data(csv_content):
    """Parse CSV content and return headers and data rows"""
    csv_reader = csv.reader(StringIO(csv_content))
    rows = list(csv_reader)
    if not rows:
        raise ValueError("CSV file is empty")
    return rows[0], rows[1:]

def extract_google_drive_id(url):
    """Extract file ID from Google Drive URL"""
    patterns = [
        r'id=([^&]+)',
        r'/d/([^/]+)',
        r'file/d/([^/]+)',
        r'open\?id=([^&]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_file_from_url(url):
    """Download file from URL and return as bytes"""
    try:
        file_id = extract_google_drive_id(url)
        if file_id:
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        else:
            download_url = url
            
        print(f"Downloading from: {download_url}")
        
        session = requests.Session()
        response = session.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check if it's a PDF or image
        content_type = response.headers.get('content-type', '').lower()
        
        # If it's HTML, try the view URL
        if 'text/html' in content_type and file_id:
            view_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            response = session.get(view_url, stream=True, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
        
        return response.content, content_type
        
    except Exception as e:
        print(f"Error downloading file from {url}: {e}")
        return None, None

def detect_file_type(content):
    """Detect if content is PDF or image (supports PNG, JPEG, GIF, BMP, etc.)"""
    # Check for PDF magic number
    if content and content[:4] == b'%PDF':
        return 'pdf'
    
    # Try to open as image (supports PNG, JPEG, GIF, BMP, WebP, etc.)
    try:
        PILImage.open(io.BytesIO(content))
        return 'image'
    except:
        pass
    
    return 'unknown'

def wrap_text(text, max_length=20):
    """Wrap text to fit in table cells"""
    if not text:
        return ''
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)

def create_table_pdf(data_rows, output_filename):
    """Create PDF with table only (Page 1)"""
    
    # Column mapping
    cols = {
        'teacher': 1, 'school': 0, 'enroll': 2, 'total': 3, 'ht': 4,
        'p1': 5, 'e1': 6, 't1': 7, 'p2': 8, 'e2': 9, 't2': 10,
        'p3': 11, 'e3': 12, 't3': 13
    }
    
    # Prepare table data
    headers = [
        'Teacher Name -\nSchool Name',
        'Enrollment',
        'Total Teacher -\nHT',
        'Preference 1 -\nSch1 Enroll -\nSch1 Teachers',
        'Preference 2 -\nSch2 Enroll -\nSch2 Teachers',
        'Preference 3 -\nSch3 Enroll -\nSch3 Teachers'
    ]
    
    table_data = []
    
    for idx, row in enumerate(data_rows):
        if len(row) < 15:
            continue
            
        # Build table row with wrapped text
        table_row = []
        
        # Teacher Name - School Name
        teacher = row[cols['teacher']].strip() if cols['teacher'] < len(row) else ''
        school = row[cols['school']].strip() if cols['school'] < len(row) else ''
        table_row.append(wrap_text(f"{teacher} - {school}", 25))
        
        # Enrollment
        table_row.append(row[cols['enroll']].strip() if cols['enroll'] < len(row) else '')
        
        # Total Teacher - HT
        total = row[cols['total']].strip() if cols['total'] < len(row) else ''
        ht = row[cols['ht']].strip() if cols['ht'] < len(row) else ''
        table_row.append(wrap_text(f"{total} - {ht}", 15))
        
        # Preferences
        p1 = row[cols['p1']].strip() if cols['p1'] < len(row) else ''
        e1 = row[cols['e1']].strip() if cols['e1'] < len(row) else ''
        t1 = row[cols['t1']].strip() if cols['t1'] < len(row) else ''
        table_row.append(wrap_text(f"{p1} - {e1} - {t1}", 20))
        
        p2 = row[cols['p2']].strip() if cols['p2'] < len(row) else ''
        e2 = row[cols['e2']].strip() if cols['e2'] < len(row) else ''
        t2 = row[cols['t2']].strip() if cols['t2'] < len(row) else ''
        table_row.append(wrap_text(f"{p2} - {e2} - {t2}", 20))
        
        p3 = row[cols['p3']].strip() if cols['p3'] < len(row) else ''
        e3 = row[cols['e3']].strip() if cols['e3'] < len(row) else ''
        t3 = row[cols['t3']].strip() if cols['t3'] < len(row) else ''
        table_row.append(wrap_text(f"{p3} - {e3} - {t3}", 20))
        
        table_data.append(table_row)
    
    # Create PDF
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=landscape(A4),
        rightMargin=5*mm,
        leftMargin=5*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        leading=18,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        fontSize=12,
        leading=16,
        spaceAfter=8
    )
    
    story = []
    
    # Add title and subtitle
    story.append(Paragraph("Rationalization of Teachers | Intra-circle Transfer", title_style))
    story.append(Paragraph("Transfer Application Receiving Status", subtitle_style))
    story.append(Spacer(1, 3*mm))
    
    # Create table
    if table_data:
        col_widths = [
            85*mm,  # Teacher Name - School Name
            22*mm,  # Enrollment
            30*mm,  # Total Teacher - HT
            40*mm,  # Preference 1
            40*mm,  # Preference 2
            40*mm   # Preference 3
        ]
        
        table_content = []
        for row in table_data:
            para_row = []
            for cell in row:
                para_row.append(Paragraph(cell, styles['Normal']))
            table_content.append(para_row)
        
        header_paras = []
        for header in headers:
            header_paras.append(Paragraph(header, ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                alignment=TA_CENTER,
                fontSize=8,
                leading=10,
                textColor=colors.white
            )))
        
        table = Table([header_paras] + table_content, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data available", styles['Normal']))
    
    doc.build(story)
    print(f"Table PDF created: {output_filename}")

def image_to_pdf(image_content, output_filename):
    """Convert any image (PNG, JPEG, etc.) to PDF - strictly one page"""
    try:
        # Open image from bytes
        img = PILImage.open(io.BytesIO(image_content))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get image dimensions
        img_width, img_height = img.size
        
        # Create PDF with proper margins
        page_width, page_height = portrait(A4)
        
        # Calculate available space with generous margins
        margin = 20  # mm
        available_width = page_width - (margin * 2) * mm
        available_height = page_height - (margin * 2) * mm
        
        # Calculate scaling to fit within available space
        width_scale = available_width / img_width
        height_scale = available_height / img_height
        
        # Use the smaller scale to ensure it fits
        scale = min(width_scale, height_scale)
        
        # Apply a safety margin (95% of calculated scale)
        scale = scale * 0.95
        
        # Calculate final dimensions
        final_width = img_width * scale
        final_height = img_height * scale
        
        print(f"  Page: {page_width:.2f}x{page_height:.2f}")
        print(f"  Available: {available_width:.2f}x{available_height:.2f}")
        print(f"  Image: {img_width}x{img_height}")
        print(f"  Scale: {scale:.2f}")
        print(f"  Final: {final_width:.2f}x{final_height:.2f}")
        
        # Create a temporary file for the image
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        img.save(temp_img.name, 'JPEG', quality=95)
        temp_img.close()
        
        # Create PDF with exact dimensions
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=portrait(A4),
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        story = []
        
        # Add image with calculated dimensions
        reportlab_img = Image(temp_img.name, width=final_width, height=final_height)
        reportlab_img.hAlign = 'CENTER'
        reportlab_img.vAlign = 'MIDDLE'
        
        # Center the image vertically with spacers
        story.append(Spacer(1, 10*mm))
        story.append(reportlab_img)
        story.append(Spacer(1, 10*mm))
        
        doc.build(story)
        
        # Clean up temp file
        if os.path.exists(temp_img.name):
            os.unlink(temp_img.name)
            
        print(f"Image converted to PDF: {output_filename}")
        return True
        
    except Exception as e:
        print(f"Error converting image to PDF: {e}")
        return False

def create_pdf(data_rows, output_filename="Transfer Application.pdf"):
    """Create PDF with table and images"""
    
    # Step 1: Create table PDF (Page 1)
    table_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    table_pdf.close()
    create_table_pdf(data_rows, table_pdf.name)
    
    # Step 2: Download and convert images to PDF
    image_pdfs = []
    
    for idx, row in enumerate(data_rows):
        if len(row) < 15:
            continue
            
        # Extract image URL from column 14
        image_url = row[14].strip() if len(row) > 14 and row[14].strip() else None
        if not image_url:
            continue
            
        print(f"\nProcessing image {idx + 1}: {image_url}")
        
        # Download file
        content, content_type = download_file_from_url(image_url)
        if not content:
            print(f"Failed to download file {idx + 1}")
            continue
        
        # Detect file type
        file_type = detect_file_type(content)
        print(f"File type detected: {file_type}")
        
        # Handle any file type (PNG, JPEG, PDF, etc.)
        if file_type == 'pdf':
            # Save PDF directly
            pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            pdf_file.write(content)
            pdf_file.close()
            image_pdfs.append(pdf_file.name)
            print(f"PDF saved directly: {pdf_file.name}")
            
        else:
            # Convert any image (PNG, JPEG, etc.) to PDF
            pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            pdf_file.close()
            if image_to_pdf(content, pdf_file.name):
                image_pdfs.append(pdf_file.name)
                print(f"Image converted to PDF: {pdf_file.name}")
            else:
                print(f"Failed to convert file {idx + 1}")
    
    # Step 3: Merge all PDFs
    if image_pdfs:
        merger = PdfMerger()
        
        # Add table PDF
        merger.append(table_pdf.name)
        
        # Add image PDFs
        for pdf_file in image_pdfs:
            try:
                merger.append(pdf_file)
                print(f"Added: {pdf_file}")
            except Exception as e:
                print(f"Error adding {pdf_file}: {e}")
        
        # Save merged PDF
        merger.write(output_filename)
        merger.close()
        
        print(f"\n✅ PDF created successfully: {output_filename}")
        print(f"Total pages: {1 + len(image_pdfs)} (1 table page + {len(image_pdfs)} image pages)")
        
    else:
        # Just copy table PDF
        import shutil
        shutil.copy2(table_pdf.name, output_filename)
        print(f"\n✅ PDF created successfully (table only): {output_filename}")
    
    # Clean up temporary files
    try:
        if os.path.exists(table_pdf.name):
            os.unlink(table_pdf.name)
        for pdf_file in image_pdfs:
            if os.path.exists(pdf_file):
                os.unlink(pdf_file)
    except:
        pass

def main():
    csv_url = "https://gist.githubusercontent.com/saikat-pundit/ad6a030b5bf7d6ecaa1eaa3176526d82/raw/Rationalisation.csv"
    
    try:
        print("Downloading CSV data...")
        csv_content = download_csv_from_gist(csv_url)
        
        print("Parsing CSV data...")
        headers, data_rows = parse_csv_data(csv_content)
        print(f"Found {len(data_rows)} data rows")
        
        print("Creating PDF...")
        create_pdf(data_rows, "Transfer Application.pdf")
        
        print("PDF generation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
