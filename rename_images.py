#!/usr/bin/env python3
"""
rename_images.py

Renames all images in /images folder to chronological format (0001.png, 0002.png, etc.)
and saves them to /images_new folder.
"""
import os
import shutil
from pathlib import Path

def rename_images():
    """Rename images to chronological format."""
    # Paths
    current_dir = Path(__file__).parent
    images_dir = current_dir / "images"
    output_dir = current_dir / "images_new"
    
    # Check if images directory exists
    if not images_dir.exists():
        print(f"❌ Error: {images_dir} directory not found")
        return False
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    image_files = []
    
    for file in images_dir.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            image_files.append(file)
    
    if not image_files:
        print(f"❌ No image files found in {images_dir}")
        return False
    
    # Sort by modification time (chronological)
    image_files.sort(key=lambda x: x.stat().st_mtime)
    
    # Create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    print(f"📁 Found {len(image_files)} images")
    print(f"📁 Creating renamed images in: {output_dir}")
    print()
    
    # Rename and copy files
    for i, image_file in enumerate(image_files, start=1):
        # New name format: 0001.png, 0002.png, etc.
        new_name = f"{i:04d}.png"
        new_path = output_dir / new_name
        
        # Copy file with new name
        shutil.copy2(image_file, new_path)
        
        print(f"✅ {image_file.name} → {new_name}")
    
    print()
    print(f"🎉 Successfully renamed {len(image_files)} images!")
    print(f"📁 Output directory: {output_dir}")
    print()
    print("Next steps:")
    print(f"  aws s3 cp {output_dir}/ s3://torque-jobs/test123/images/ --recursive")
    
    return True

if __name__ == "__main__":
    rename_images()