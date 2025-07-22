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