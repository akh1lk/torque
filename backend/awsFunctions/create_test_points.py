#!/usr/bin/env python3
"""
create_test_points.py - Simple center point for testing
"""
import json
import os
import cv2
from aws_utils import JobPaths

def create_center_point(job_id: str):
    paths = JobPaths(job_id)
    paths.ensure_dirs("config")
    
    # Get first image dimensions
    image_files = sorted([f for f in os.listdir(paths.images) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    first_image = os.path.join(paths.images, image_files[0])
    
    image = cv2.imread(first_image)
    height, width = image.shape[:2]
    
    # Single center point
    test_points = {
        "points": [[width // 2, height // 2]],
        "labels": [1]
    }
    
    with open(paths.points_json, 'w') as f:
        json.dump(test_points, f)
    
    print(f"✓ Created center point: ({width//2}, {height//2})")

if __name__ == "__main__":
    import sys
    create_center_point(sys.argv[1])  # job_id