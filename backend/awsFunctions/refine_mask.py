import os
import sys
import argparse
import subprocess
from urllib.parse import urlparse
import cv2
import numpy as np
import json

import boto3
import requests
from sam2_service import Sam2Service

"""
Runs on EC2 to regenerate preview mask whenever user updates points.
"""

def run(cmd, **kw):
    print("▶", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)

def s3_download_file(s3_pref: str, local_path: str):
    """
    Downloads a s3 directory to a local directory.
    """ 
    run(["aws", "s3", "cp", s3_pref, local_path, "--recursive"])

def s3_upload_file(local_path: str, s3_pref: str):
    """
    Uploads a local directory to a s3 directory.
    """ 
    run(["aws", "s3", "cp", s3_pref, local_path, "--recursive"])

def patch_status(fastapi_url: str, token: str, job_id: str):
    """
    PATCH status to FastAPI /jobs/{job_id} endpoint.
    """
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.patch(f"{fastapi_url}/jobs/{job_id}", json={"status": "init_done"}, headers=headers)
    resp.raise_for_status()

def throwFNF(fpath: str, msg: str = ""):
    if not os.path.exists(fpath):
        raise FileNotFoundError(fpath)

# this file expects init_job.py to alr be run

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--job_id', required=True)
    p.add_argument('--bucket', required=True)
    p.add_argument('--fastapi_url', required=True)
    p.add_argument('--fastapi_token', required=True)

    args = p.parse_args()
    job_id = args.job_id
    bucket = args.bucket
    fastapi_url = args.fastapi_url
    fastapi_token = args.fastapi_token

    root = os.path.expanduser(f"~/torque/jobs/{job_id}")
    preview_dir = os.path.join(root, 'preview')
    config_dir = os.path.join(root, 'config')
    points_json = os.path.join(config_dir, 'initial_points.json')

    # Load 1st frame image
    first_frame = os.path.join(preview_dir, 'first_frame.png')
    throwFNF(first_frame)

    # download latest updated prompts @ config/initial_points.json
    s3_url_pts = f"s3://{bucket}/{job_id}/config/initial_points.json"
    s3_download_file(s3_url_pts, points_json)
    with open(points_json) as f:
        data = json.load(f)
    points = data.get('points', [])
    labels = data.get('labels', [1] * len(points))

    # generate mask npz + merged mask png as preview/img_masks.npz
    svc = Sam2Service()
    masks_path = svc.img_mask(
        image_path=first_frame,
        output_dir=preview_dir,
        points=points,
        labels=labels
    )

    # to preview/first_frame_outlined.png
    overlay_path = svc.overlay_outline(
        image_path=first_frame,
        mask_path=masks_path,
        out_dir=preview_dir
    )

    # upload to s3
    s3_base = f"s3://{bucket}/{job_id}/preview"
    s3_upload_file(overlay_path, s3_base + 'first_frame_outlined.png')

    # patch status w/ fastapi
    patch_status(fastapi_url, fastapi_token, job_id, 'preview_mask_ready')
    print(f"[✔] Refined mask for job {job_id}")

if __name__ == '__main__':
    main()