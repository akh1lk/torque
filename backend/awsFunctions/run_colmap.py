"""
run_colmap.py

EC2 worker script to:
1. Use RGBA images from SAM2 output
2. Run COLMAP pipeline (feature extraction, matching, reconstruction)
3. Generate sparse reconstruction (cameras.bin, images.bin, points3D.bin)
4. Keep results locally for Gaussian Splatting pipeline
5. Notify FastAPI of completion
"""
import argparse
import os
from aws_utils import (
    run, patch_status, ensure_dir, get_image_files,
    JobPaths, print_job_summary
)

def run_colmap_pipeline(paths: JobPaths, matching_type: str = "Sequential"):
    """
    Runs COLMAP pipeline on RGBA images.
    """
    # create colmap directory (COLMAP creates sparse/0)
    ensure_dir(paths.colmap)
    
    db_path = os.path.join(paths.colmap, "database.db")
    sparse_path = os.path.join(paths.colmap, "sparse")
    
    # Create sparse directory
    ensure_dir(sparse_path)
    
    print(f"Running COLMAP pipeline")
    print(f"RGBA images: {paths.rgba}")
    print(f"Output: {paths.colmap}")
    
    # val RGBA images exist
    if not os.path.exists(paths.rgba):
        print(f"ERROR: RGBA images not found: {paths.rgba}")
        return False
    
    # count images
    rgba_files = get_image_files(paths.rgba, exclude_video=False)
    print(f"Found {len(rgba_files)} RGBA images")
    
    if len(rgba_files) < 3:
        print(f"ERROR: Need at least 3 images, found {len(rgba_files)}")
        return False
    
    # COLMAP pipeline
    commands = [
        ("Creating database", f"colmap database_creator --database_path {db_path}"),
        ("Extracting features", f"colmap feature_extractor --database_path {db_path} --image_path {paths.rgba}"),
        (f"Running {matching_type} matching", {
            "Exhaustive": f"colmap exhaustive_matcher --database_path {db_path}",
            "Sequential": f"colmap sequential_matcher --database_path {db_path}",
            "Spatial": f"colmap spatial_matcher --database_path {db_path}"
        }.get(matching_type, f"colmap sequential_matcher --database_path {db_path}")),
        ("Sparse reconstruction", f"colmap mapper --database_path {db_path} --image_path {paths.rgba} --output_path {sparse_path}")
    ]
    
    for step, cmd in commands:
        print(step)
        if run(cmd) != 0:
            print(f"ERROR: Failed during {step.lower()}")
            return False
   
    # verify output
    result_dir = os.path.join(sparse_path, "0")
    expected_files = ["cameras.bin", "images.bin", "points3D.bin"]
    
    if not os.path.exists(result_dir):
        print(f"ERROR: Output directory not found: {result_dir}")
        return False
    
    missing_files = [f for f in expected_files if not os.path.exists(os.path.join(result_dir, f))]
    if missing_files:
        print(f"ERROR: Missing files: {missing_files}")
        return False
    
    print("SUCCESS: COLMAP completed successfully!")
    print(f"Results: {result_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run COLMAP reconstruction on RGBA images")
    parser.add_argument("--job_id", required=True, help="Job ID")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--fastapi_url", required=True, help="FastAPI URL")
    parser.add_argument("--fastapi_token", required=True, help="FastAPI auth token")
    parser.add_argument("--matching_type", default="Sequential", 
                       choices=["Sequential", "Exhaustive", "Spatial"],
                       help="COLMAP feature matching type")
    
    args = parser.parse_args()
    
    paths = JobPaths(args.job_id)
    
    print_job_summary(args.job_id, "RUN COLMAP",
                     rgba_dir=paths.rgba,
                     colmap_dir=paths.colmap)
    
    # Run COLMAP pipeline
    success = run_colmap_pipeline(paths, args.matching_type)
    
    if success:
        patch_status(args.fastapi_url, args.fastapi_token, args.job_id, "colmap_done")
        print(f"SUCCESS: COLMAP completed for job {args.job_id}")
        return 0
    else:
        patch_status(args.fastapi_url, args.fastapi_token, args.job_id, "colmap_failed")
        print(f"ERROR: COLMAP failed for job {args.job_id}")
        return 1

if __name__ == "__main__":
    exit(main())