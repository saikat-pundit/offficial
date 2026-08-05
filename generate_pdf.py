import csv
import requests
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import landscape, A4, portrait
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
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
        
        content_type = response.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type and file_id:
            view_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            response = session.get(view_url, stream=True, timeout=30)
            response.raise_for_status()
        
        return response.content
        
    except Exception as e:
        print(f"Error downloading file from {url}: {e}")
        return None

def detect_file_type(content):
    """Detect if content is PDF or image"""
    if content and content[:4] == b'%PDF':
        return 'pdf'
    
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
    
    cols = {
        'teacher': 1, 'school': 0, 'enroll': 2, 'total': 3, 'ht': 4,
        'p1': 5, 'e1': 6, 't1': 7, 'p2': 8, 'e2': 9, 't2': 10,
        'p3': 11, 'e3': 12, 't3': 13
    }
    
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
            
        table_row = []
        
        teacher = row[cols['teacher']].strip() if cols['teacher'] < len(row) else ''
        school = row[cols['school']].strip() if cols['school'] < len(row) else ''
        table_row.append(wrap_text(f"{teacher} - {school}", 25))
        
        table_row.append(row[cols['enroll']].strip() if cols['enroll'] < len(row) else '')
        
        total = row[cols['total']].strip() if cols['total'] < len(row) else ''
        ht = row[cols['ht']].strip() if cols['ht'] < len(row) else ''
        table_row.append(wrap_text(f"{total} - {ht}", 15))
        
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
    
    story.append(Paragraph("Rationalization of Teachers | Intra-circle Transfer", title_style))
    story.append(Paragraph("Transfer Application Receiving Status", subtitle_style))
    story.append(Spacer(1, 3*mm))
    
    if table_data:
        col_widths = [
            85*mm, 22*mm, 30*mm, 40*mm, 40*mm, 40*mm
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

def convert_image_to_single_page_pdf(image_content, output_filename):
    """Convert image to single page PDF - STRICTLY ONE PAGE"""
    try:
        # Open image
        img = PILImage.open(io.BytesIO(image_content))
        
        # Convert to RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get original dimensions
        img_width, img_height = img.size
        
        # Get page dimensions (Portrait A4)
        page_width, page_height = portrait(A4)
        
        # Calculate maximum available space with margins
        margin_mm = 15
        max_width = page_width - (2 * margin_mm * mm)
        max_height = page_height - (2 * margin_mm * mm)
        
        # Calculate scale to fit image within page
        scale_x = max_width / img_width
        scale_y = max_height / img_height
        
        # Use the smaller scale to ensure it fits completely
        scale = min(scale_x, scale_y)
        
        # If image is smaller than page, don't upscale
        if scale > 1.0:
            scale = 1.0
        
        # Calculate final dimensions
        final_width = img_width * scale
        final_height = img_height * scale
        
        print(f"  Image: {img_width}x{img_height}")
        print(f"  Page: {page_width:.2f}x{page_height:.2f}")
        print(f"  Max available: {max_width:.2f}x{max_height:.2f}")
        print(f"  Scale: {scale:.4f}")
        print(f"  Final: {final_width:.2f}x{final_height:.2f}")
        
        # Save image to temp file
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        img.save(temp_img.name, 'JPEG', quality=95)
        temp_img.close()
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=portrait(A4),
            rightMargin=margin_mm*mm,
            leftMargin=margin_mm*mm,
            topMargin=margin_mm*mm,
            bottomMargin=margin_mm*mm
        )
        
        story = []
        
        # Add image with exact dimensions
        reportlab_img = Image(temp_img.name, width=final_width, height=final_height)
        reportlab_img.hAlign = 'CENTER'
        
        story.append(reportlab_img)
        
        doc.build(story)
        
        # Clean up
        if os.path.exists(temp_img.name):
            os.unlink(temp_img.name)
        
        print(f"Image converted to single page PDF: {output_filename}")
        return True
        
    except Exception as e:
        print(f"Error converting image to PDF: {e}")
        return False

def convert_pdf_to_single_page(pdf_content, output_filename):
    """Convert multi-page PDF to single page by extracting first page"""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        
        if len(pdf_reader.pages) == 0:
            print("PDF has no pages")
            return False
        
        # If single page, just save it
        if len(pdf_reader.pages) == 1:
            with open(output_filename, 'wb') as f:
                f.write(pdf_content)
            print(f"Single page PDF saved directly")
            return True
        
        # Extract first page only
        print(f"PDF has {len(pdf_reader.pages)} pages, extracting first page only")
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf_reader.pages[0])
        
        with open(output_filename, 'wb') as f:
            pdf_writer.write(f)
        
        print(f"First page extracted to: {output_filename}")
        return True
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False

def get_image_from_pdf_page(pdf_content, output_filename):
    """Extract first page as image and convert to single page PDF"""
    try:
        # Try to extract as image from PDF
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_content, first_page=1, last_page=1)
        
        if images:
            # Convert first page to RGB
            img = images[0]
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as temporary image
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_img.name, 'JPEG', quality=95)
            temp_img.close()
            
            # Convert image to PDF
            return convert_image_to_single_page_pdf(open(temp_img.name, 'rb').read(), output_filename)
        
        return False
    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
        return False

def create_pdf(data_rows, output_filename="Transfer Application.pdf"):
    """Create PDF with table and images - ONE IMAGE PER PAGE"""
    
    # Step 1: Create table PDF (Page 1)
    table_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    table_pdf.close()
    create_table_pdf(data_rows, table_pdf.name)
    
    # Step 2: Download and convert each file to single page PDF
    image_pdfs = []
    
    for idx, row in enumerate(data_rows):
        if len(row) < 15:
            continue
            
        image_url = row[14].strip() if len(row) > 14 and row[14].strip() else None
        if not image_url:
            continue
            
        print(f"\n{'='*50}")
        print(f"Processing entry {idx + 1}")
        print(f"{'='*50}")
        
        # Download file
        content = download_file_from_url(image_url)
        if not content:
            print(f"Failed to download file")
            continue
        
        # Detect file type
        file_type = detect_file_type(content)
        print(f"File type: {file_type}")
        
        # Create temp PDF file
        pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf_file.close()
        
        success = False
        
        if file_type == 'pdf':
            # Try to convert PDF to single page
            success = convert_pdf_to_single_page(content, pdf_file.name)
            
            # If that fails, try to extract as image
            if not success:
                print("Attempting to extract PDF as image...")
                success = get_image_from_pdf_page(content, pdf_file.name)
        
        else:
            # Convert image to single page PDF
            success = convert_image_to_single_page_pdf(content, pdf_file.name)
        
        if success:
            image_pdfs.append(pdf_file.name)
            print(f"✅ Successfully converted to single page PDF")
        else:
            print(f"❌ Failed to convert file")
            if os.path.exists(pdf_file.name):
                os.unlink(pdf_file.name)
    
    # Step 3: Merge all PDFs
    if image_pdfs:
        print(f"\n{'='*50}")
        print(f"Merging {len(image_pdfs)} image pages with table")
        print(f"{'='*50}")
        
        merger = PdfMerger()
        
        # Add table PDF
        merger.append(table_pdf.name)
        print(f"Added: Table page")
        
        # Add image PDFs
        for i, pdf_file in enumerate(image_pdfs, 1):
            try:
                merger.append(pdf_file)
                print(f"Added: Image {i}")
            except Exception as e:
                print(f"Error adding image {i}: {e}")
        
        # Save merged PDF
        merger.write(output_filename)
        merger.close()
        
        print(f"\n{'='*50}")
        print(f"✅ PDF created successfully: {output_filename}")
        print(f"Total pages: {1 + len(image_pdfs)} (1 table + {len(image_pdfs)} images)")
        print(f"{'='*50}")
        
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
