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
import threading
import time
from aws_utils import (
    run, patch_status, ensure_dir, s3_upload_dir,
    JobPaths, print_job_summary
)


def setup_brush_inputs(paths: JobPaths):
    """
    set up Brush w/ symlinks for /rgba + /colmap/sparse/0
    """
    brush_input_dir = os.path.join(paths.workspace, "brush_input")
    brush_images_link = os.path.join(brush_input_dir, "images")
    brush_sparse_dir = os.path.join(brush_input_dir, "sparse")
    brush_sparse_link = os.path.join(brush_sparse_dir, "0")
    
    print("Setting up Brush data structure with symlinks")
    print(f"RGBA images: {paths.rgba}")
    print(f"COLMAP data: {paths.colmap}")
    print(f"Brush data dir: {brush_input_dir}")
    
    # Validate source directories exist
    if not os.path.exists(paths.rgba):
        raise FileNotFoundError(f"RGBA directory not found: {paths.rgba}")
    
    colmap_sparse_source = os.path.join(paths.colmap, "sparse", "0")
    if not os.path.exists(colmap_sparse_source):
        raise FileNotFoundError(f"COLMAP sparse directory not found: {colmap_sparse_source}")
    
    # check brush_data good
    ensure_dir(brush_input_dir)
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
    return brush_input_dir

def upload_progress_images(progress_dir: str, bucket: str, job_id: str, stop_event: threading.Event):
    """
    Background thread to upload progress images every 5 minutes.
    """
    while not stop_event.is_set():
        try:
            if os.path.exists(progress_dir):
                # Find latest rendered images
                image_files = [f for f in os.listdir(progress_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if image_files:
                    # Upload latest images to S3 progress folder
                    s3_progress_prefix = f"s3://{bucket}/{job_id}/progress/"
                    s3_upload_dir(progress_dir, s3_progress_prefix)
                    print(f"Uploaded {len(image_files)} progress images to S3")
        except Exception as e:
            print(f"Progress upload error: {e}")
        
        # Wait 5 minutes or until stop signal
        stop_event.wait(300)  # 300 seconds = 5 minutes

def run_brush_training(brush_data_dir: str, total_steps: str = "10000", bucket: str = None, job_id: str = None):
    """
    Run Brush Gaussian Splatting training on the prepared dataset.
    """
    print("Starting Brush training...")
    
    # Set up export path for outputs and progress
    export_dir = os.path.join(os.path.dirname(brush_data_dir), "gaussian_splat")
    progress_dir = os.path.join(os.path.dirname(brush_data_dir), "progress")
    ensure_dir(export_dir)
    ensure_dir(progress_dir)
    
    # Start background thread for progress uploads
    stop_upload = threading.Event()
    upload_thread = None
    if bucket and job_id:
        upload_thread = threading.Thread(
            target=upload_progress_images,
            args=(progress_dir, bucket, job_id, stop_upload)
        )
        upload_thread.daemon = True
        upload_thread.start()
        print("Started progress image upload thread")
    
    # Brush training command with correct CLI arguments
    brush_cmd = [
        os.path.expanduser("~/torque/brush_app"),  # Path to brush executable
        brush_data_dir,  # Source path (COLMAP dataset)
        "--total-steps", total_steps,
        "--max-resolution", "1024",
        "--export-every", "5000",  # Export every 5000 steps (will export at 5k and 10k)
        "--export-path", export_dir,
        "--export-name", "export_{iter}.ply",
        "--alpha-loss-weight", "0.1",  # For transparency support
        "--eval-every", "1000",
        "--eval-save-to-disk",  # Save eval images to disk for progress
        "--seed", "42"
    ]
    
    print(f"Running: {' '.join(brush_cmd)}")
    print(f"Export directory: {export_dir}")
    print(f"Progress directory: {progress_dir}")
    
    try:
        # Run Brush training
        result = run(' '.join(brush_cmd))
        
        if result != 0:
            raise RuntimeError(f"Brush training failed with exit code {result}")
        
        print("Brush training completed successfully")
        
    finally:
        # Stop progress upload thread
        if upload_thread:
            stop_upload.set()
            upload_thread.join(timeout=5)
            print("Stopped progress upload thread")
    
    # Check for exported PLY files
    ply_files = [f for f in os.listdir(export_dir) if f.endswith('.ply')]
    if ply_files:
        print(f"Found {len(ply_files)} exported PLY files")
        # Get the final model (highest iteration)
        ply_files.sort()
        final_model = ply_files[-1]
        print(f"Final model: {final_model}")
    else:
        print("WARNING: No PLY files found in export directory")
    
    return export_dir



def cleanup_intermediate_files(paths: JobPaths, output_dir: str):
    """
    Clean up intermediate symlink directories.
    The model files are already in the correct location.
    """
    print("Cleaning up intermediate files...")
    
    # remove brush_input directory (just symlinks)
    brush_input_dir = os.path.join(paths.workspace, "brush_input")
    if os.path.exists(brush_input_dir):
        # remove symlinks and directory
        import shutil
        shutil.rmtree(brush_input_dir)
        print("Removed brush_input symlink directory")
    
    # The output_dir already contains the final models
    if os.path.exists(output_dir):
        print(f"Final models location: {output_dir}")
        return output_dir
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Run Brush 3D Gaussian Splatting training")
    parser.add_argument("--job_id", required=True, help="Job ID")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--fastapi_url", required=True, help="FastAPI URL")
    parser.add_argument("--fastapi_token", required=True, help="FastAPI auth token")
    parser.add_argument("--steps", default="10000", help="Training steps")
    parser.add_argument("--resolution", default="1024", help="Output resolution")
    
    args = parser.parse_args()
    
    paths = JobPaths(args.job_id)
    
    print_job_summary(args.job_id, "RUN BRUSH",
                     rgba_dir=paths.rgba,
                     colmap_dir=paths.colmap,
                     workspace=paths.workspace)
 
    try:
        # Step 1: set up Brush data structure
        brush_data_dir = setup_brush_inputs(paths)
        
        # Step 2: run brush training
        output_dir = run_brush_training(brush_data_dir, args.steps, args.bucket, args.job_id)
        
        # Step 3: clean up + finalize out
        final_model_dir = cleanup_intermediate_files(paths, output_dir)
        
        if final_model_dir:
            # Step 4: upload final model to S3
            print("Uploading final 3D model to S3...")
            s3_model_prefix = f"s3://{args.bucket}/{args.job_id}/gaussian_splat/"
            s3_upload_dir(final_model_dir, s3_model_prefix)
            print(f"Model uploaded to: {s3_model_prefix}")

        # Step 5: update job status
        patch_status(args.fastapi_url, args.fastapi_token, args.job_id, "brush_done")
        print(f"SUCCESS: Brush training completed for job {args.job_id}")
        return 0
        
    except Exception as e:
        print(f"ERROR: Brush training failed: {e}")
        patch_status(args.fastapi_url, args.fastapi_token, args.job_id, "brush_failed")
        return 1

if __name__ == "__main__":
    exit(main())
