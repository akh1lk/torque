import argparse
import os
from aws_utils import (
    run_check, s3_download_dir, s3_upload_dir, patch_status,
    get_image_files, JobPaths, print_job_summary
)
from sam2_service import Sam2Service

# actual job initialization

def init_job(job_id: str, bucket: str, fastapi_url: str, token: str):
    paths = JobPaths(job_id)
    paths.ensure_dirs("images", "preview")
    
    print_job_summary(job_id, "INIT JOB", 
                     workspace=paths.workspace,
                     images_dir=paths.images,
                     preview_dir=paths.preview)

    s3_images = f"s3://{bucket}/{job_id}/images/"
    s3_download_dir(s3_images, paths.images)

    # SAM2 needs video, so imgs -> video
    # Auto-detect input format (jpg or png)
    sample_files = [f for f in os.listdir(paths.images) if f.startswith('0001.')]
    if not sample_files:
        raise FileNotFoundError("No images found starting with '0001.'")
    
    input_ext = sample_files[0].split('.')[-1]  # Get extension (jpg, png, etc.)
    input_pattern = f"%04d.{input_ext}"
    
    print(f"Auto-detected input format: {input_ext}")
    
    run_check(["ffmpeg", "-y",
        "-framerate", "12", 
        "-i", os.path.join(paths.images, input_pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        paths.video])
    
    # first frame for preview / mask modification
    image_files = get_image_files(paths.images)
    
    if not image_files:
        raise ValueError(f"No image files found in {paths.images}")
    
    first_image_path = os.path.join(paths.images, image_files[0])
    
    run_check(["cp", first_image_path, paths.first_frame])

    # init sam2service and segment first frame (NO PROMPTS)
    svc = Sam2Service()
    print("▶ Running SAM2 on first frame for initial mask")
    
    # save masks.npz to preview directory
    mask_result = svc.img_mask(paths.first_frame, output_dir=paths.preview)
    
    # create overlay for visual coolness
    preview_overlay = svc.overlay_outline(
        image_path=paths.first_frame,
        mask_path=paths.img_masks,
        out_dir=paths.preview,
    )
    
    print(f"Created preview overlay: {preview_overlay}")

    # Upload preview to S3
    s3_preview = f"s3://{bucket}/{job_id}/preview/"
    s3_upload_dir(paths.preview, s3_preview)

    patch_status(fastapi_url, token, job_id, "init_done")
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