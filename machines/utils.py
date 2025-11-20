from PIL import Image
from pillow_heif import register_heif_opener
import io
import os
from django.core.files.uploadedfile import InMemoryUploadedFile

# Register HEIF opener with Pillow
register_heif_opener()

def convert_heic_to_jpg(uploaded_file):
    """
    Convert HEIC/HEIF image to JPG format while preserving the filename
    Returns a new InMemoryUploadedFile with .jpg extension
    """
    try:
        # Open the HEIC image
        image = Image.open(uploaded_file)
        
        # Convert to RGB (HEIC might be in different color mode)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create a BytesIO object to hold the converted image
        output = io.BytesIO()
        
        # Save as JPEG
        image.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        # Get original filename and change extension to .jpg
        original_name = uploaded_file.name
        name_without_ext = os.path.splitext(original_name)[0]
        new_filename = f"{name_without_ext}.jpg"
        
        # Create a new InMemoryUploadedFile
        converted_file = InMemoryUploadedFile(
            output,
            'ImageField',
            new_filename,
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
        
        return converted_file
    
    except Exception as e:
        print(f"Error converting HEIC to JPG: {e}")
        return None