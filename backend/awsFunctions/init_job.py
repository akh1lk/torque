import argparse
import os
import cv2
from aws_utils import (
    run_check, s3_download_dir, s3_upload_dir, patch_status,
    get_image_files, JobPaths, print_job_summary
)
from sam2_service import Sam2Service

# actual job initialization

def resize_images_to_max_dimension(images_dir: str, max_dimension: int = 1024):
    """
    Resize all images in directory to max dimension while preserving aspect ratio.
    Processes images in-place to optimize storage and subsequent pipeline stages.
    """
    image_files = get_image_files(images_dir)
    resized_count = 0
    
    for image_file in image_files:
        image_path = os.path.join(images_dir, image_file)
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Warning: Could not load {image_file}, skipping")
            continue
            
        height, width = image.shape[:2]
        
        # Check if resize needed
        if max(height, width) > max_dimension:
            # Calculate new dimensions while preserving aspect ratio
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            # Resize image
            resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Save resized image (overwrite original)
            cv2.imwrite(image_path, resized_image)
            
            print(f"Resized {image_file}: {width}x{height} → {new_width}x{new_height}")
            resized_count += 1
        else:
            print(f"Kept {image_file}: {width}x{height} (already within {max_dimension}px)")
    
    print(f"Resized {resized_count}/{len(image_files)} images to max {max_dimension}px")
    return resized_count

def init_job(job_id: str, bucket: str, fastapi_url: str, token: str):
    paths = JobPaths(job_id)
    paths.ensure_dirs("images", "preview")
    
    print_job_summary(job_id, "INIT JOB", 
                     workspace=paths.workspace,
                     images_dir=paths.images,
                     preview_dir=paths.preview)

    s3_images = f"s3://{bucket}/{job_id}/images/"
    s3_download_dir(s3_images, paths.images)

    # Resize images to 1024px max dimension for pipeline optimization
    resize_images_to_max_dimension(paths.images, max_dimension=1024)

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

    # Upload preview to S3 (exclude NPZ files - internal use only)
    s3_preview = f"s3://{bucket}/{job_id}/preview/"
    run_check(["aws", "s3", "cp", paths.preview, s3_preview, "--recursive", "--exclude", "*.npz"])

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