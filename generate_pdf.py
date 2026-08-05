# Add images on separate pages - only if images exist
valid_images = [f for f in temp_files if f and os.path.exists(f)]

if valid_images:
    # Add a page break before first image if there's table data
    if table_data:
        story.append(PageBreak())
    
    # Get page dimensions
    page_width, page_height = landscape(A4)
    
    for idx, temp_file_path in enumerate(valid_images):
        # Start each image on a new page
        if idx > 0:
            story.append(PageBreak())
        
        try:
            # ... rest of image processing ...
