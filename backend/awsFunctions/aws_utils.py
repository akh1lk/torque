"""
aws_utils.py

Shared utilities for AWS EC2 functions in the Torque pipeline.
Contains common imports, helper functions, and utilities used across
init_job.py, refine_mask.py, run_sam2.py, and run_colmap.py.
"""
import os
import sys
import subprocess
import requests
import json
from typing import Optional

# Common imports used across AWS functions
import boto3
import cv2
import numpy as np
from urllib.parse import urlparse

def run(cmd, **kw):
    """
    Execute a shell command and print output.
    """
    print("▶", " ".join(cmd) if isinstance(cmd, list) else cmd)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if result.stdout:
        print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode

def run_check(cmd, **kw):
    """
    Execute a shell command with check=True (raises exception on failure).
    """
    print("▶", " ".join(cmd) if isinstance(cmd, list) else cmd)
    subprocess.run(cmd, check=True, **kw)

def s3_download_dir(s3_pref: str, local_dir: str):
    """
    Downloads a s3 directory to a local directory.
    """
    run_check(["aws", "s3", "cp", s3_pref, local_dir, "--recursive"])

def s3_upload_dir(local_dir: str, s3_pref: str):
    """
    Uploads a local directory to a s3 directory.
    """
    run_check(["aws", "s3", "cp", local_dir, s3_pref, "--recursive"])

def s3_download_file(s3_pref: str, local_path: str):
    """
    Downloads a single s3 file to a local path.
    """
    run_check(["aws", "s3", "cp", s3_pref, local_path])

def s3_upload_file(local_path: str, s3_pref: str):
    """
    Uploads a single local file to s3.
    """
    run_check(["aws", "s3", "cp", local_path, s3_pref])

def patch_status(fastapi_url: str, token: str, job_id: str, status: str):
    """
    PATCH status to FastAPI /jobs/{job_id} endpoint.
    """
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.patch(f"{fastapi_url}/jobs/{job_id}", json={"status": status}, headers=headers)
    resp.raise_for_status()
    print(f"Updated job {job_id} status to: {status}")

def get_job_workspace(job_id: str) -> str:
    """
    Get the standard workspace directory for a job.
    """
    return os.path.expanduser(f"~/torque/jobs/{job_id}")

def ensure_dir(path: str):
    """
    Create directory if it doesn't exist.
    """
    os.makedirs(path, exist_ok=True)

def throwFNF(fpath: str, msg: str = ""):
    """
    Throw FileNotFoundError if file doesn't exist.
    Used in refine_mask.py.
    """
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"{fpath} {msg}")

def load_points_json(points_json_path: str) -> tuple:
    """
    Load points and labels from initial_points.json.
    Returns (points, labels) tuple.
    """
    with open(points_json_path) as f:
        data = json.load(f)
    points = data.get('points', [])
    labels = data.get('labels', [1] * len(points))
    return points, labels

def get_image_files(images_dir: str, exclude_video: bool = True) -> list:
    """
    Get all image files from a directory, optionally excluding video files.
    Returns sorted list of filenames.
    """
    extensions = ('.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff', '.bmp')
    files = [f for f in os.listdir(images_dir) if f.lower().endswith(extensions)]
    
    if exclude_video:
        files = [f for f in files if not f.endswith('_video.mp4')]
    
    return sorted(files)

def validate_job_dirs(job_id: str, required_dirs: list) -> str:
    """
    Validate that required directories exist for a job.
    Returns the job workspace path.
    """
    workspace = get_job_workspace(job_id)
    
    for dir_name in required_dirs:
        dir_path = os.path.join(workspace, dir_name)
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Required directory not found: {dir_path}")
    
    return workspace

class JobPaths:
    """
    Helper class to manage standard job directory paths.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.workspace = get_job_workspace(job_id)
        self.images = os.path.join(self.workspace, "images")
        self.preview = os.path.join(self.workspace, "preview")
        self.config = os.path.join(self.workspace, "config")
        self.masks = os.path.join(self.workspace, "masks")
        self.rgba = os.path.join(self.workspace, "rgba")
        self.colmap = os.path.join(self.workspace, "colmap")
        
        # Common files
        self.video = os.path.join(self.images, f"{job_id}_video.mp4")
        self.first_frame = os.path.join(self.preview, "first_frame.png")
        self.points_json = os.path.join(self.config, "initial_points.json")
        self.video_masks = os.path.join(self.masks, "video_masks.npz")
        self.img_masks = os.path.join(self.preview, "img_masks.npz")
    
    def ensure_dirs(self, *dir_names):
        """
        Ensure specified directories exist.
        """
        for dir_name in dir_names:
            dir_path = getattr(self, dir_name, None)
            if dir_path:
                ensure_dir(dir_path)
            else:
                raise ValueError(f"Unknown directory: {dir_name}")

def print_job_summary(job_id: str, stage: str, **kwargs):
    """
    Print a standardized job processing summary.
    """
    print(f"\n{stage} - Job: {job_id}")
    for key, value in kwargs.items():
        print(f"{key}: {value}")
    print()