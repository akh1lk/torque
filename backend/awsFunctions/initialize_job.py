import os
import sys
import argparse
import subprocess
from urllib.parse import urlparse
import cv2
import numpy as np

import boto3
import requests
from sam2_service import Sam2Service

# helpers

def run(cmd, **kw):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)

def s3_download_dir(s3_pref: str, local_dir: str):
    """
    Downloads a s3 directory to a local directory.
    """ 
    run(["aws", "s3", "cp", s3_pref, local_dir, "--recursive"])

def s3_upload_dir(local_dir: str, s3_pref: str):
    """
    Uploads a local directory to a s3 directory.
    """ 
    run(["aws", "s3", "cp", s3_pref, local_dir, "--recursive"])

def patch_status(fastapi_url: str, token: str, job_id: str):
    """
    PATCH status to FastAPI /jobs/{job_id} endpoint.
    """
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.patch(f"{fastapi_url}/jobs/{job_id}", json={"status": "init_done"}, headers=headers)
    resp.raise_for_status()

# actual job initialization

def init_job(job_id: str, bucket: str, fastapi_url: str, token: str):
    base = os.path.expanduser(f"~/torque/jobs/{job_id}")  # Fixed string formatting
    images_dir = os.path.join(base, "images")
    preview_dir = os.path.join(base, "preview")

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(preview_dir, exist_ok=True)

    # Download images from S3
    s3_images = f"s3://{bucket}/{job_id}/images/"
    s3_download_dir(s3_images, images_dir)

    # Convert images to a propagatable format for SAM2
    mp4_path = os.path.join(base, f"images/{job_id}_video.mp4")
    run(["ffmpeg", "-y",
        "-framerate", "12",
        "-i", os.path.join(images_dir, "%04d.png"),
        "-c:v", "libx264",  # Fixed typo: was "libx124"
        "-pix_fmt", "yuv420p",
        mp4_path])
    
    # Get first frame from images folder (not from video)
    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort()  # Ensure consistent ordering
    
    if not image_files:
        raise ValueError(f"No image files found in {images_dir}")
    
    first_image_path = os.path.join(images_dir, image_files[0])
    first_frame = os.path.join(preview_dir, "first_frame.png")
    
    # Copy first image to preview directory
    run(["cp", first_image_path, first_frame])

    # Initialize Sam2Service and run segmentation on first frame
    sam2_service = Sam2Service()
    print("▶ Running SAM2 on first frame for initial mask")
    
    # Use Sam2Service.img_mask and save masks.npz to preview directory
    mask_result = sam2_service.img_mask(first_frame, output_dir=preview_dir)
    
    # Create overlay preview using overlay_outline
    init_mask_path = os.path.join(preview_dir, "masks.npz")
    preview_overlay = sam2_service.overlay_outline(
        image_path=first_frame,
        mask_path=init_mask_path,
        out_dir=preview_dir,
    )
    
    print(f"✅ Created preview overlay: {preview_overlay}")

    # Upload preview to S3
    s3_preview = f"s3://{bucket}/{job_id}/preview/"
    s3_upload_dir(preview_dir, s3_preview)

    patch_status(fastapi_url, token, job_id)
    print("Job initialized successfully")

def main():
    parser = argparse.ArgumentParser(description="Initialize a SAM2 job")

    parser.add_argument("--job_id", required=True, help="Job ID")
    parser.add_argument("--bucket", default="torque-jobs", help="S3 bucket name")
    parser.add_argument("--fastapi_url", required=True, help="FastAPI Base URL (no trailing slash)")
    parser.add_argument("--fastapi_token", required=True, help="FastAPI Auth Token")  # Fixed argument name

    args = parser.parse_args()
    
    init_job(
        job_id=args.job_id,
        bucket=args.bucket,
        fastapi_url=args.fastapi_url,
        token=args.fastapi_token
    )

if __name__ == "__main__":
    main()