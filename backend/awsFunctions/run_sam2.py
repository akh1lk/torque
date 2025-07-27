"""
run_sam2.py

EC2 worker script to:
1. Download job inputs (configs/initial_points.json) from S3
2. Propagate SAM2 over the video to generate per-frame masks (NPZ + PNGs)
3. Composite RGBA frames using the masks
4. Upload masks and RGBA outputs back to S3
5. Notify FastAPI of job completion
"""
import argparse
import os
from aws_utils import (
    patch_status, load_points_json, JobPaths, print_job_summary
)
from sam2_service import Sam2Service

# main execution

def main():
    parser = argparse.ArgumentParser(description="Run SAM2 on a video propogation + RGBA composite for a job.")
    parser.add_argument("--job_id", required=True, help="Job ID")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--fastapi_url", required=True, help="FastAPI URL")
    parser.add_argument("--fastapi_token", required=True, help="FastAPI auth token")
    
    args = parser.parse_args()

    job_id = args.job_id
    bucket = args.bucket
    fastapi_url = args.fastapi_url
    token = args.fastapi_token

    paths = JobPaths(job_id)
    paths.ensure_dirs("rgba")
    
    print_job_summary(job_id, "RUN SAM2",
                     workspace=paths.workspace,
                     images_dir=paths.images,
                     rgba_dir=paths.rgba,
                     config_dir=paths.config)

    # local video check
    if not os.path.exists(paths.video):
        raise FileNotFoundError(f"Expected video @ {paths.video}")
    
    # prepare prompts: read initial mask or pts (after refine mask, latest are local)
    points, labels = load_points_json(paths.points_json)

    # Initialize SAM2 service
    svc = Sam2Service()

    # Run SAM2 to get masks
    masks_path = svc.video_mask(
        video_path=paths.video,
        job_id=job_id,
        points=points,
        labels=labels
    )

    # use masks to create rgba images
    results = svc.batch_create_rgba_masks(
        job_id=job_id,
        upload_to_s3=True,
        s3_bucket=bucket,
        s3_prefix=f"{job_id}/rgba",
    )
    
    print(f"RGBA processing complete: {results['processed']} images, {results['uploaded']} uploaded")
        
    # Notify FastAPI of job completion
    patch_status(fastapi_url, token, job_id, "sam2_done")
    print(f"SUCCESS: SAM2 completed for job {job_id}")

if __name__ == "__main__":
    main()