import csv
import requests
from io import StringIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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

def download_image_to_temp(url):
    """Download image from Google Drive URL and save to temporary file"""
    temp_file = None
    try:
        file_id = extract_google_drive_id(url)
        if not file_id:
            print(f"Could not extract file ID from URL: {url}")
            return None
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        print(f"Downloading image from: {download_url}")
        
        session = requests.Session()
        response = session.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Try to get the image directly
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            # If we get HTML, try the view URL
            view_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            response = session.get(view_url, stream=True, timeout=30)
            response.raise_for_status()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(response.content)
        temp_file.close()
        
        # Verify the file exists and has content
        if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 1000:
            print(f"Image saved to: {temp_file.name}")
            return temp_file.name
        else:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None
        
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass
        return None

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

def create_pdf(data_rows, output_filename="Transfer Application.pdf"):
    """Create PDF with table and images"""
    
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
    temp_files = []  # Keep track of temporary files
    
    print(f"Processing {len(data_rows)} rows of data...")
    
    for idx, row in enumerate(data_rows):
        if len(row) < 15:
            continue
            
        # Extract image URL from column 14
        image_url = row[14].strip() if len(row) > 14 and row[14].strip() else None
        if image_url:
            print(f"Row {idx}: Found image URL")
            # Download image to temp file
            temp_file_path = download_image_to_temp(image_url)
            if temp_file_path:
                temp_files.append(temp_file_path)
                print(f"Row {idx}: Image downloaded successfully")
            else:
                temp_files.append(None)
                print(f"Row {idx}: Failed to download image")
        else:
            temp_files.append(None)
        
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
    
    print(f"Created {len(table_data)} table rows, {len([f for f in temp_files if f])} images downloaded")
    
    # Create PDF with minimal margins
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
    
    # Build story - only add elements that have content
    story = []
    
    # Add title and subtitle
    story.append(Paragraph("Rationalization of Teachers | Intra-circle Transfer", title_style))
    story.append(Paragraph("Transfer Application Receiving Status", subtitle_style))
    story.append(Spacer(1, 3*mm))
    
    # Create table if there's data
    if table_data:
        # Calculate column widths (proportional)
        col_widths = [
            85*mm,  # Teacher Name - School Name
            22*mm,  # Enrollment
            30*mm,  # Total Teacher - HT
            40*mm,  # Preference 1
            40*mm,  # Preference 2
            40*mm   # Preference 3
        ]
        
        # Convert table data to Paragraphs for better wrapping
        table_content = []
        for row in table_data:
            para_row = []
            for cell in row:
                para_row.append(Paragraph(cell, styles['Normal']))
            table_content.append(para_row)
        
        # Create header paragraphs
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
        
        # Style the table
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
    
    # Add images on separate pages - only if images exist
    valid_images = [f for f in temp_files if f and os.path.exists(f)]
    
    if valid_images:
        # Add a page break before first image if there's table data
        if table_data:
            story.append(PageBreak())
        
        # Get page dimensions
        page_width, page_height = landscape(A4)
        
        for idx, temp_file_path in enumerate(valid_images):
            try:
                # Get image dimensions using PIL
                pil_img = PILImage.open(temp_file_path)
                img_width, img_height = pil_img.size
                pil_img.close()
                
                # Calculate available space (leave room for header and caption)
                available_width = page_width - 12*mm
                available_height = page_height - 25*mm
                
                # Calculate scaling to fit within available space
                width_scale = available_width / img_width
                height_scale = available_height / img_height
                scale = min(width_scale, height_scale)
                
                # Ensure image doesn't exceed page bounds
                if scale > 1.0:
                    scale = 1.0
                
                # Calculate final dimensions
                final_width = img_width * scale
                final_height = img_height * scale
                
                print(f"Image {idx+1}: Original ({img_width}x{img_height}), Scaled ({final_width:.2f}x{final_height:.2f}), Scale: {scale:.2f}")
                
                # Create image with calculated dimensions
                img = Image(temp_file_path, width=final_width, height=final_height)
                img.hAlign = 'CENTER'
                
                # Add image header
                story.append(Paragraph(f"Application Image - Entry {idx + 1}", 
                                     ParagraphStyle('ImageHeader', parent=styles['Heading2'], 
                                                  alignment=TA_CENTER, fontSize=11, spaceAfter=5)))
                
                story.append(Spacer(1, 2*mm))
                story.append(img)
                
                # Add caption at bottom
                story.append(Spacer(1, 3*mm))
                caption_style = ParagraphStyle(
                    'ImageCaption',
                    parent=styles['Normal'],
                    alignment=TA_CENTER,
                    fontSize=8,
                    textColor=colors.grey
                )
                story.append(Paragraph(f"Image {idx + 1} of {len(valid_images)}", caption_style))
                
                # Add page break after each image except the last one
                if idx < len(valid_images) - 1:
                    story.append(PageBreak())
                    
            except Exception as e:
                print(f"Error adding image {idx + 1}: {e}")
                story.append(Paragraph(f"Error loading image: {str(e)}", styles['Normal']))
    
    # Build PDF
    try:
        doc.build(story)
        print(f"PDF created successfully: {output_filename}")
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise
    finally:
        # Clean up temporary files after PDF is built
        print("Cleaning up temporary files...")
        for temp_file_path in temp_files:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    print(f"Deleted: {temp_file_path}")
                except Exception as e:
                    print(f"Error deleting {temp_file_path}: {e}")

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
