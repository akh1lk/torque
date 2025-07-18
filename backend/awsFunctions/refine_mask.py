import argparse
from aws_utils import (
    s3_download_file, s3_upload_file, patch_status,
    throwFNF, load_points_json, JobPaths, print_job_summary
)
from sam2_service import Sam2Service

"""
Runs on EC2 to regenerate preview mask whenever user updates points.
"""

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

    paths = JobPaths(job_id)
    
    print_job_summary(job_id, "REFINE MASK",
                     workspace=paths.workspace,
                     preview_dir=paths.preview,
                     config_dir=paths.config)

    # Load 1st frame image
    throwFNF(paths.first_frame)

    # download latest updated prompts @ config/initial_points.json
    s3_url_pts = f"s3://{bucket}/{job_id}/config/initial_points.json"
    s3_download_file(s3_url_pts, paths.points_json)
    points, labels = load_points_json(paths.points_json)

    # generate mask npz + merged mask png as preview/img_masks.npz
    svc = Sam2Service()
    masks_path = svc.img_mask(
        image_path=paths.first_frame,
        output_dir=paths.preview,
        points=points,
        labels=labels
    )

    # to preview/first_frame_outlined.png
    overlay_path = svc.overlay_outline(
        image_path=paths.first_frame,
        mask_path=masks_path,
        out_dir=paths.preview
    )

    # upload to s3
    s3_base = f"s3://{bucket}/{job_id}/preview/"
    s3_upload_file(overlay_path, s3_base + 'first_frame_outlined.png')

    # patch status w/ fastapi
    patch_status(fastapi_url, fastapi_token, job_id, 'preview_mask_ready')
    print(f"[✔] Refined mask for job {job_id}")

if __name__ == '__main__':
    main()