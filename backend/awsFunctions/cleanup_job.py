"""
cleanup_job.py
if 3D model uploaded to S3, delete entire job directory.
"""
import argparse
import os
import shutil
import subprocess
from aws_utils import JobPaths


def check_s3_model_exists(bucket: str, job_id: str) -> bool:
    """Check if 3D model exists in S3."""
    s3_path = f"s3://{bucket}/{job_id}/gaussian_splat/"
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", s3_path], 
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0 and ".ply" in result.stdout
    except Exception:
        return False


def cleanup_completed_job(job_id: str, bucket: str) -> bool:
    """Remove job directory if model uploaded to S3."""
    paths = JobPaths(job_id)
    
    if not os.path.exists(paths.workspace):
        print(f"Job directory doesn't exist: {job_id}")
        return False
    
    if check_s3_model_exists(bucket, job_id):
        try:
            shutil.rmtree(paths.workspace)
            print(f"Cleaned up job {job_id} (model safe in S3)")
            return True
        except Exception as e:
            print(f"✗ Failed to remove {job_id}: {e}")
            return False
    else:
        print(f"Skipping {job_id} (no S3 model found)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Clean up completed jobs")
    parser.add_argument("--job_id", help="Specific job to clean")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--all", action="store_true", help="Clean all completed jobs")
    
    args = parser.parse_args()
    
    if args.job_id:
        cleanup_completed_job(args.job_id, args.bucket)
    elif args.all:
        jobs_dir = os.path.expanduser("~/torque/jobs")
        if os.path.exists(jobs_dir):
            for job_id in os.listdir(jobs_dir):
                if os.path.isdir(os.path.join(jobs_dir, job_id)):
                    cleanup_completed_job(job_id, args.bucket)
    else:
        parser.error("Use --job_id or --all")


if __name__ == "__main__":
    main()