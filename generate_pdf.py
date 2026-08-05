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

def download_csv_from_gist(url):
    """Download CSV data from gist URL"""
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_csv_data(csv_content):
    """Parse CSV content and return headers and data rows"""
    csv_reader = csv.reader(StringIO(csv_content))
    rows = list(csv_reader)
    if not rows:
        raise ValueError("CSV file is empty")
    return rows[0], rows[1:]  # headers, data rows

def extract_google_drive_id(url):
    """Extract file ID from Google Drive URL"""
    pattern = r'id=([^&]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def download_image_from_google_drive(url):
    """Download image from Google Drive URL"""
    try:
        file_id = extract_google_drive_id(url)
        if not file_id:
            # Try alternative URL format
            if 'drive.google.com' in url and 'uc' in url:
                # Already in correct format
                pass
            else:
                # Try to extract from any Google Drive URL
                pattern = r'/d/([^/]+)'
                match = re.search(pattern, url)
                if match:
                    file_id = match.group(1)
                    url = f'https://drive.google.com/uc?export=download&id={file_id}'
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(response.content)
            return tmp_file.name
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
    image_urls = []
    
    for row in data_rows:
        # Skip rows that don't have enough columns or are empty
        if len(row) < 15:
            continue
            
        # Extract image URL from column 14 (index 14) if exists
        if len(row) > 14 and row[14].strip():
            image_urls.append(row[14].strip())
        else:
            image_urls.append(None)
            
        table_row = [
            f"{row[cols['teacher']].strip() if cols['teacher'] < len(row) else ''} -\n{row[cols['school']].strip() if cols['school'] < len(row) else ''}",
            row[cols['enroll']].strip() if cols['enroll'] < len(row) else '',
            f"{row[cols['total']].strip() if cols['total'] < len(row) else ''} -\n{row[cols['ht']].strip() if cols['ht'] < len(row) else ''}",
            f"{row[cols['p1']].strip() if cols['p1'] < len(row) else ''} -\n{row[cols['e1']].strip() if cols['e1'] < len(row) else ''} -\n{row[cols['t1']].strip() if cols['t1'] < len(row) else ''}",
            f"{row[cols['p2']].strip() if cols['p2'] < len(row) else ''} -\n{row[cols['e2']].strip() if cols['e2'] < len(row) else ''} -\n{row[cols['t2']].strip() if cols['t2'] < len(row) else ''}",
            f"{row[cols['p3']].strip() if cols['p3'] < len(row) else ''} -\n{row[cols['e3']].strip() if cols['e3'] < len(row) else ''} -\n{row[cols['t3']].strip() if cols['t3'] < len(row) else ''}"
        ]
        table_data.append(table_row)
    
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
    
    # Create table
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
        ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Left align first column
        
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        
        # Row height
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    
    # Add images on separate pages
    for idx, url in enumerate(image_urls):
        if url:
            story.append(PageBreak())
            
            # Add page header for images
            story.append(Paragraph(f"Application Image - Entry {idx + 1}", 
                                 ParagraphStyle('ImageHeader', parent=styles['Heading2'], 
                                              alignment=TA_CENTER, fontSize=12, spaceAfter=10)))
            
            # Download and add image
            image_path = download_image_from_google_drive(url)
            if image_path:
                try:
                    img = Image(image_path)
                    # Scale image to fit page
                    max_width = landscape(A4)[0] - 20*mm
                    max_height = landscape(A4)[1] - 30*mm
                    img.drawWidth = max_width
                    img.drawHeight = max_height
                    img.hAlign = 'CENTER'
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"Error loading image: {e}", styles['Normal']))
                finally:
                    # Clean up temporary file
                    if os.path.exists(image_path):
                        os.unlink(image_path)
            else:
                story.append(Paragraph("Failed to download image", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {output_filename}")

def main():
    csv_url = "https://gist.githubusercontent.com/saikat-pundit/ad6a030b5bf7d6ecaa1eaa3176526d82/raw/Rationalisation.csv"
    
    try:
        # Download CSV
        print("Downloading CSV data...")
        csv_content = download_csv_from_gist(csv_url)
        
        # Parse CSV
        print("Parsing CSV data...")
        headers, data_rows = parse_csv_data(csv_content)
        
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
