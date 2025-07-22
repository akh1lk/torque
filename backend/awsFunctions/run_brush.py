"""
run_brush.py

EC2 worker script to:
1. Assess correct dirs for RGBA + COLMAP + new outputs.
2. Run Brush (3D Gaussian Splatting) training with transparent inputs
2.5 Routinely upload pngs of said object to S3 for preview.
3. Generate final 3D model files
4. Upload trained model to S3
5. Notify FastAPI of completion
"""
import argparse
import os
import shutil
from aws_utils import (
    run, patch_status, ensure_dir, s3_upload_dir,
    JobPaths, print_job_summary
)


def setup_brush_data(paths: JobPaths):
    """
    Set up Brush w/ symlinks for /rgba + /colmap/sparse/0
    """
    brush_data_dir = os.path.join(paths.workspace, "brush_data")
    brush_images_link = os.path.join(brush_data_dir, "images")
    brush_sparse_dir = os.path.join(brush_data_dir, "sparse")
    brush_sparse_link = os.path.join(brush_sparse_dir, "0")
    
    print("Setting up Brush data structure with symlinks")
    print(f"RGBA images: {paths.rgba}")
    print(f"COLMAP data: {paths.colmap}")
    print(f"Brush data dir: {brush_data_dir}")
    
    # Validate source directories exist
    if not os.path.exists(paths.rgba):
        raise FileNotFoundError(f"RGBA directory not found: {paths.rgba}")
    
    colmap_sparse_source = os.path.join(paths.colmap, "sparse", "0")
    if not os.path.exists(colmap_sparse_source):
        raise FileNotFoundError(f"COLMAP sparse directory not found: {colmap_sparse_source}")
    
    # check brush_data good
    ensure_dir(brush_data_dir)
    ensure_dir(brush_sparse_dir)
    
    # remove existing symlinks if they exist
    if os.path.exists(brush_images_link):
        os.unlink(brush_images_link)
    if os.path.exists(brush_sparse_link):
        os.unlink(brush_sparse_link)
    
    # symlinks
    os.symlink(paths.rgba, brush_images_link)
    os.symlink(colmap_sparse_source, brush_sparse_link)
    
    print("Brush data structure created with symlinks")
    return brush_data_dir