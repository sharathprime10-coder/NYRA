from PIL import Image
import sys

try:
    img_path = r"c:\Users\Sharath Chandra S\OneDrive\Desktop\app_chatbot\frontend\public\nyra_logo.jpg"
    img = Image.open(img_path)

    width, height = img.size
    print(f"Original size: {width}x{height}")

    # Calculate square dimension
    size = min(width, height)

    # Calculate crop coordinates
    # Center horizontally
    left = (width - size) / 2
    right = (width + size) / 2

    # We'll take the top 'size' pixels vertically, or center it if height > width
    if height > width:
        # Portait
        top = (height - size) / 2
        bottom = (height + size) / 2
    else:
        # Landscape - subject is often vertically centered or slightly top-heavy, so taking the middle
        # Since height == size, top = 0, bottom = height
        top = 0
        bottom = size

    img_cropped = img.crop((left, top, right, bottom))
    
    # Save it
    img_cropped.save(img_path)
    print(f"Cropped size: {img_cropped.size}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
