import csv
import requests
from io import StringIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER
import os
import tempfile
from datetime import datetime
import re
import base64
from urllib.parse import urlparse, parse_qs

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
    return rows[0], rows[1:]  # headers, data rows

def extract_google_drive_id(url):
    """Extract file ID from Google Drive URL"""
    # Try different URL patterns
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

def download_image_from_google_drive(url):
    """Download image from Google Drive URL"""
    temp_file = None
    try:
        # Extract file ID
        file_id = extract_google_drive_id(url)
        if not file_id:
            print(f"Could not extract file ID from URL: {url}")
            return None
        
        # Construct download URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        print(f"Downloading image from: {download_url}")
        
        # Download with session for better handling
        session = requests.Session()
        response = session.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check if we got a valid image
        content_type = response.headers.get('content-type', '')
        if 'html' in content_type.lower():
            # Try alternative download method
            response = session.get(f"https://drive.google.com/uc?export=view&id={file_id}", stream=True, timeout=30)
            response.raise_for_status()
        
        # Create a temporary file with proper extension
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(response.content)
        temp_file.close()
        
        # Verify the file is a valid image
        if os.path.getsize(temp_file.name) < 100:  # Too small to be an image
            os.unlink(temp_file.name)
            return None
            
        print(f"Image downloaded successfully: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass
        return None

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
    image_urls = []
    
    print(f"Processing {len(data_rows)} rows of data...")
    
    for idx, row in enumerate(data_rows):
        # Skip rows that don't have enough columns
        if len(row) < 15:
            print(f"Row {idx}: Skipping - not enough columns ({len(row)})")
            continue
            
        # Extract image URL from column 14 (index 14) if exists
        image_url = row[14].strip() if len(row) > 14 and row[14].strip() else None
        if image_url:
            image_urls.append(image_url)
            print(f"Row {idx}: Found image URL")
        else:
            image_urls.append(None)
        
        # Build table row with safe access
        table_row = []
        
        # Teacher Name - School Name
        teacher = row[cols['teacher']].strip() if cols['teacher'] < len(row) else ''
        school = row[cols['school']].strip() if cols['school'] < len(row) else ''
        table_row.append(f"{teacher} -\n{school}")
        
        # Enrollment
        table_row.append(row[cols['enroll']].strip() if cols['enroll'] < len(row) else '')
        
        # Total Teacher - HT
        total = row[cols['total']].strip() if cols['total'] < len(row) else ''
        ht = row[cols['ht']].strip() if cols['ht'] < len(row) else ''
        table_row.append(f"{total} -\n{ht}")
        
        # Preferences
        for pref in ['p1', 'e1', 't1', 'p2', 'e2', 't2', 'p3', 'e3', 't3']:
            if pref not in cols:
                continue
            col_idx = cols[pref]
            value = row[col_idx].strip() if col_idx < len(row) else ''
            if pref in ['p1', 'p2', 'p3']:
                # This is a preference, need to combine with subsequent columns
                pass
        
        # Manually build preference strings
        p1 = row[cols['p1']].strip() if cols['p1'] < len(row) else ''
        e1 = row[cols['e1']].strip() if cols['e1'] < len(row) else ''
        t1 = row[cols['t1']].strip() if cols['t1'] < len(row) else ''
        table_row.append(f"{p1} -\n{e1} -\n{t1}")
        
        p2 = row[cols['p2']].strip() if cols['p2'] < len(row) else ''
        e2 = row[cols['e2']].strip() if cols['e2'] < len(row) else ''
        t2 = row[cols['t2']].strip() if cols['t2'] < len(row) else ''
        table_row.append(f"{p2} -\n{e2} -\n{t2}")
        
        p3 = row[cols['p3']].strip() if cols['p3'] < len(row) else ''
        e3 = row[cols['e3']].strip() if cols['e3'] < len(row) else ''
        t3 = row[cols['t3']].strip() if cols['t3'] < len(row) else ''
        table_row.append(f"{p3} -\n{e3} -\n{t3}")
        
        table_data.append(table_row)
    
    print(f"Created {len(table_data)} table rows, {len([u for u in image_urls if u])} images to process")
    
    # Create PDF
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=landscape(A4),
        rightMargin=5*mm,
        leftMargin=5*mm,
        topMargin=10*mm,
        bottomMargin=10*mm
    )
    
    styles = getSampleStyleSheet()
    center_style = ParagraphStyle(
        'CenterStyle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        leading=12
    )
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        fontSize=14,
        leading=18,
        spaceAfter=12
    )
    
    # Build story
    story = []
    
    # Add title and subtitle
    story.append(Paragraph("Rationalization of Teachers | Intra-circle Transfer", title_style))
    story.append(Paragraph("Transfer Application Receiving Status", subtitle_style))
    story.append(Spacer(1, 6*mm))
    
    # Create table if there's data
    if table_data:
        table = Table([headers] + table_data, repeatRows=1)
        
        # Style the table
        table.setStyle(TableStyle([
            # Header row style
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Data rows style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data available", styles['Normal']))
    
    # Add images on separate pages
    image_files = []  # Keep track of temporary files for cleanup
    
    for idx, url in enumerate(image_urls):
        if url:
            print(f"Processing image {idx + 1} of {len([u for u in image_urls if u])}...")
            story.append(PageBreak())
            
            # Add page header for images
            story.append(Paragraph(f"Application Image - Entry {idx + 1}", 
                                 ParagraphStyle('ImageHeader', parent=styles['Heading2'], 
                                              alignment=TA_CENTER, fontSize=12, spaceAfter=10)))
            
            # Download and add image
            image_path = download_image_from_google_drive(url)
            if image_path and os.path.exists(image_path):
                try:
                    # Check if it's a valid image file
                    if os.path.getsize(image_path) < 1000:
                        story.append(Paragraph(f"Image file too small (likely invalid)", styles['Normal']))
                        if os.path.exists(image_path):
                            os.unlink(image_path)
                        continue
                    
                    img = Image(image_path)
                    # Scale image to fit page with proper aspect ratio
                    max_width = landscape(A4)[0] - 30*mm
                    max_height = landscape(A4)[1] - 40*mm
                    
                    # Get image dimensions
                    img_width = img.drawWidth
                    img_height = img.drawHeight
                    
                    # Calculate scaling
                    width_scale = max_width / img_width
                    height_scale = max_height / img_height
                    scale = min(width_scale, height_scale, 1.0)
                    
                    img.drawWidth = img_width * scale
                    img.drawHeight = img_height * scale
                    img.hAlign = 'CENTER'
                    story.append(img)
                    
                    # Add filename info
                    story.append(Spacer(1, 5*mm))
                    story.append(Paragraph(f"Image {idx + 1}", 
                                         ParagraphStyle('ImageCaption', parent=styles['Normal'],
                                                      alignment=TA_CENTER, fontSize=8)))
                    
                    # Keep track for cleanup
                    image_files.append(image_path)
                    
                except Exception as e:
                    print(f"Error adding image {idx + 1}: {e}")
                    story.append(Paragraph(f"Error loading image: {str(e)}", styles['Normal']))
                    if os.path.exists(image_path):
                        try:
                            os.unlink(image_path)
                        except:
                            pass
            else:
                story.append(Paragraph("Failed to download image", styles['Normal']))
    
    # Build PDF
    try:
        doc.build(story)
        print(f"PDF created successfully: {output_filename}")
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise
    finally:
        # Clean up temporary files
        for file_path in image_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"Cleaned up: {file_path}")
            except:
                pass

def main():
    csv_url = "https://gist.githubusercontent.com/saikat-pundit/ad6a030b5bf7d6ecaa1eaa3176526d82/raw/Rationalisation.csv"
    
    try:
        # Download CSV
        print("Downloading CSV data...")
        csv_content = download_csv_from_gist(csv_url)
        
        # Parse CSV
        print("Parsing CSV data...")
        headers, data_rows = parse_csv_data(csv_content)
        print(f"Found {len(data_rows)} data rows")
        
        # Create PDF
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
