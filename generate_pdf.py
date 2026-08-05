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

def download_image_from_google_drive(url):
    """Download image from Google Drive URL and return as PIL Image"""
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
        
        # Convert to PIL Image
        image_data = response.content
        pil_image = PILImage.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        return pil_image
        
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
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
    image_data = []
    
    print(f"Processing {len(data_rows)} rows of data...")
    
    for idx, row in enumerate(data_rows):
        if len(row) < 15:
            continue
            
        # Extract image URL from column 14
        image_url = row[14].strip() if len(row) > 14 and row[14].strip() else None
        if image_url:
            print(f"Row {idx}: Found image URL")
            # Download image now and store PIL image
            pil_img = download_image_from_google_drive(image_url)
            if pil_img:
                image_data.append(pil_img)
                print(f"Row {idx}: Image downloaded successfully")
            else:
                image_data.append(None)
                print(f"Row {idx}: Failed to download image")
        else:
            image_data.append(None)
        
        # Build table row
        table_row = []
        
        # Teacher Name - School Name
        teacher = row[cols['teacher']].strip() if cols['teacher'] < len(row) else ''
        school = row[cols['school']].strip() if cols['school'] < len(row) else ''
        table_row.append(f"{teacher} - {school}")
        
        # Enrollment
        table_row.append(row[cols['enroll']].strip() if cols['enroll'] < len(row) else '')
        
        # Total Teacher - HT
        total = row[cols['total']].strip() if cols['total'] < len(row) else ''
        ht = row[cols['ht']].strip() if cols['ht'] < len(row) else ''
        table_row.append(f"{total} - {ht}")
        
        # Preferences
        p1 = row[cols['p1']].strip() if cols['p1'] < len(row) else ''
        e1 = row[cols['e1']].strip() if cols['e1'] < len(row) else ''
        t1 = row[cols['t1']].strip() if cols['t1'] < len(row) else ''
        table_row.append(f"{p1} - {e1} - {t1}")
        
        p2 = row[cols['p2']].strip() if cols['p2'] < len(row) else ''
        e2 = row[cols['e2']].strip() if cols['e2'] < len(row) else ''
        t2 = row[cols['t2']].strip() if cols['t2'] < len(row) else ''
        table_row.append(f"{p2} - {e2} - {t2}")
        
        p3 = row[cols['p3']].strip() if cols['p3'] < len(row) else ''
        e3 = row[cols['e3']].strip() if cols['e3'] < len(row) else ''
        t3 = row[cols['t3']].strip() if cols['t3'] < len(row) else ''
        table_row.append(f"{p3} - {e3} - {t3}")
        
        table_data.append(table_row)
    
    print(f"Created {len(table_data)} table rows, {len([img for img in image_data if img])} images downloaded")
    
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
    
    # Create table
    if table_data:
        # Calculate column widths
        col_widths = [
            90*mm,  # Teacher Name - School Name
            25*mm,  # Enrollment
            35*mm,  # Total Teacher - HT
            45*mm,  # Preference 1
            45*mm,  # Preference 2
            45*mm   # Preference 3
        ]
        
        table = Table([headers] + table_data, colWidths=col_widths, repeatRows=1)
        
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
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data available", styles['Normal']))
    
    # Add images on separate pages
    for idx, pil_img in enumerate(image_data):
        if pil_img:
            story.append(PageBreak())
            
            # Add image header
            story.append(Paragraph(f"Application Image - Entry {idx + 1}", 
                                 ParagraphStyle('ImageHeader', parent=styles['Heading2'], 
                                              alignment=TA_CENTER, fontSize=12, spaceAfter=10)))
            
            # Create temporary file for the image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            pil_img.save(temp_file.name, 'JPEG', quality=95)
            temp_file.close()
            
            try:
                # Add image to PDF
                img = Image(temp_file.name)
                
                # Calculate available space
                page_width = landscape(A4)[0]
                page_height = landscape(A4)[1]
                max_width = page_width - 20*mm
                max_height = page_height - 30*mm
                
                # Get original dimensions
                img_width = img.drawWidth
                img_height = img.drawHeight
                
                # Calculate scaling to fit page while maintaining aspect ratio
                width_scale = max_width / img_width
                height_scale = max_height / img_height
                scale = min(width_scale, height_scale)
                
                # Apply scaling
                img.drawWidth = img_width * scale
                img.drawHeight = img_height * scale
                img.hAlign = 'CENTER'
                
                story.append(img)
                story.append(Spacer(1, 5*mm))
                
                # Add image caption
                caption_style = ParagraphStyle(
                    'ImageCaption',
                    parent=styles['Normal'],
                    alignment=TA_CENTER,
                    fontSize=8,
                    textColor=colors.grey
                )
                story.append(Paragraph(f"Image {idx + 1} of {len([img for img in image_data if img])}", caption_style))
                
            except Exception as e:
                print(f"Error adding image {idx + 1}: {e}")
                story.append(Paragraph(f"Error loading image: {str(e)}", styles['Normal']))
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                except:
                    pass
    
    # Build PDF
    try:
        doc.build(story)
        print(f"PDF created successfully: {output_filename}")
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise

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
