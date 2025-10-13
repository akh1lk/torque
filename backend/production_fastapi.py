"""
FastAPI Server for Torque 3D Scanning Pipeline

handles:
- supabase auth integration
- image upload to s3
- job creation and management  
- sqs job queue integration
- status updates from ec2 workers
"""
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
import boto3
import uuid
import time
from datetime import datetime, timedelta
import os
import json
from supabase import create_client, Client
import asyncio
import logging

# pydantic models
class JobCreateRequest(BaseModel):
    name: Optional[str] = "Untitled Scan"
    processing_options: Optional[Dict[str, Any]] = {}

class JobStatusUpdate(BaseModel):
    status: Optional[str] = None
    stage_status: Optional[Dict[str, bool]] = None
    worker_instance_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None

class MaskRefinementRequest(BaseModel):
    refinement_data: Dict[str, Any]  # brush strokes, points, etc

class StageUpdateRequest(BaseModel):
    stage_name: str  # sam2, colmap, brush, cleanup
    status: str  # started, completed, failed
    processing_stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class DashboardStatsResponse(BaseModel):
    total_scans: int
    complete_scans: int
    processing_scans: int
    failed_scans: int
    total_storage_mb: float
    recent_activity: List[Dict[str, Any]]

# app initialization
app = FastAPI(
    title="Torque 3D Scanning API",
    description="Transform 2D captures into 3D assets",
    version="1.0.0"
)

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://trytorque3d.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# auth
security = HTTPBearer()

# clients and config
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY') 
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')  # for worker updates

if not all([supabase_url, supabase_key, supabase_service_key]):
    raise ValueError("Missing Supabase environment variables")

supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin: Client = create_client(supabase_url, supabase_service_key)  # for bypassing RLS

# aws clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
ec2_client = boto3.client('ec2')

# config
UPLOAD_BUCKET = os.getenv('TORQUE_UPLOAD_BUCKET', 'torque-jobs')
SQS_QUEUE_URL = os.getenv('TORQUE_SQS_QUEUE_URL')
WORKER_TOKEN = os.getenv('FASTAPI_WORKER_TOKEN', 'secure-worker-token')
MAX_JOB_DURATION_MINUTES = 30
EC2_INSTANCE_TYPE = 'g4dn.xlarge'

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# auth helpers
async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """verify supabase jwt token and return user_id"""
    try:
        token = credentials.credentials
        
        # verify with supabase
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user.user.id
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

async def verify_worker_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """verify worker token for status updates"""
    token = credentials.credentials
    if token != WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid worker token")
    return True

def get_s3_key(job_id: str, folder: str, filename: str) -> str:
    """generate s3 key for job files"""
    return f"jobs/{job_id}/{folder}/{filename}"

async def shutdown_worker_instance(instance_id: str) -> bool:
    """shutdown ec2 worker instance after job completion"""
    try:
        if not instance_id:
            return False
            
        logger.info(f"Shutting down EC2 instance: {instance_id}")
        
        # terminate the instance
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        
        logger.info(f"Successfully initiated shutdown for instance: {instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to shutdown instance {instance_id}: {e}")
        return False

# api endpoints

@app.get("/")
async def root():
    return {
        "service": "torque-3d-scanning-api",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/auth/user")
async def get_current_user(user_id: str = Depends(verify_user_token)):
    """get current user profile"""
    try:
        response = supabase.table('user_profiles').select('*').eq('id', user_id).single().execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {e}")

# job management endpoints

@app.post("/jobs")
async def create_job(
    request: JobCreateRequest,
    user_id: str = Depends(verify_user_token)
):
    """create new job for image upload"""
    try:
        # create job in supabase (let supabase generate UUID)
        job_data = {
            'user_id': user_id,
            'name': request.name,
            'status': 'uploading',
            'processing_options': request.processing_options,
            'stage_status': {
                'upload_done': False,
                'mask_refined': False,
                'sam2_done': False,
                'colmap_done': False,
                'brush_done': False,
                'cleanup_done': False
            },
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('jobs').insert(job_data).execute()
        
        job_id = response.data[0]['id']
        
        # update with s3 URLs now that we have the UUID
        supabase.table('jobs').update({
            's3_images_url': f's3://{UPLOAD_BUCKET}/jobs/{job_id}/images/',
            's3_results_url': f's3://{UPLOAD_BUCKET}/jobs/{job_id}/results/'
        }).eq('id', job_id).execute()
        
        return {
            'job_id': job_id,
            'status': 'uploading',
            'upload_url': f'/jobs/{job_id}/upload',
            'created_at': response.data[0]['created_at']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {e}")

@app.get("/jobs/{job_id}/upload-urls")
async def get_upload_urls(
    job_id: str,
    filenames: str,  # comma-separated list: "image1.jpg,image2.jpg"
    user_id: str = Depends(verify_user_token)
):
    """generate presigned urls for direct s3 upload"""
    try:
        # verify job ownership
        job_response = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', user_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        # check job status (must be 'uploading')
        job = job_response.data
        if job['status'] != 'uploading':
            raise HTTPException(status_code=400, detail="Job is not in uploading state")
        
        # parse filenames
        filename_list = [f.strip() for f in filenames.split(',') if f.strip()]
        if len(filename_list) > 50:  # reasonable limit
            raise HTTPException(status_code=400, detail="Too many files (max 50)")
        
        presigned_urls = []
        
        for i, filename in enumerate(filename_list):
            # validate filename
            if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp']):
                raise HTTPException(status_code=400, detail=f"Invalid file type: {filename}")
            
            # generate s3 key with sequential naming
            file_extension = filename.split('.')[-1].lower()
            s3_filename = f"{i+1:04d}.{file_extension}"  # 0001.jpg, 0002.jpg, etc
            s3_key = get_s3_key(job_id, 'images', s3_filename)
            
            # generate presigned post
            presigned_post = s3_client.generate_presigned_post(
                Bucket=UPLOAD_BUCKET,
                Key=s3_key,
                Fields={
                    'Content-Type': f'image/{file_extension}',
                    'x-amz-meta-job-id': job_id,
                    'x-amz-meta-user-id': user_id,
                    'x-amz-meta-original-filename': filename,
                    'x-amz-meta-upload-order': str(i+1)
                },
                Conditions=[
                    {'Content-Type': f'image/{file_extension}'},
                    ['content-length-range', 100, 50 * 1024 * 1024],  # 100 bytes to 50MB
                    {'x-amz-meta-job-id': job_id},
                    {'x-amz-meta-user-id': user_id}
                ],
                # 1 hour to upload
                ExpiresIn=3600  
            )
            
            presigned_urls.append({
                'original_filename': filename,
                's3_filename': s3_filename,
                's3_key': s3_key,
                'upload_order': i+1,
                'presigned_post': presigned_post
            })
        
        return {
            'job_id': job_id,
            'upload_urls': presigned_urls,
            'expires_in': 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URLs: {e}")
    

@app.post("/jobs/{job_id}/upload-complete")
async def confirm_upload_complete(
    job_id: str,
    uploaded_files: List[Dict[str, Any]],  # [{"s3_key": "...", "original_filename": "...", "file_size": 123}]
    user_id: str = Depends(verify_user_token)
):
    """confirm that files have been uploaded to s3"""
    try:
        # verify job ownership
        job_response = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', user_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_response.data
        if job['status'] != 'uploading':
            raise HTTPException(status_code=400, detail="Job is not in uploading state")
        
        # verify files exist in s3 and record in database
        confirmed_files = []
        
        for file_info in uploaded_files:
            s3_key = file_info['s3_key']
            
            # verify file exists in s3
            try:
                head_response = s3_client.head_object(Bucket=UPLOAD_BUCKET, Key=s3_key)
                actual_size = head_response['ContentLength']
                
                # get metadata
                metadata = head_response.get('Metadata', {})
                upload_order = int(metadata.get('upload-order', 0))
                
            except s3_client.exceptions.NoSuchKey:
                raise HTTPException(status_code=400, detail=f"File not found in S3: {s3_key}")
            
            confirmed_files.append({
                'original_filename': file_info['original_filename'],
                's3_key': s3_key,
                'file_size': actual_size,
                'upload_order': upload_order
            })
        
        # update job status and record upload completion
        stage_status = job.get('stage_status', {})
        stage_status['upload_done'] = True
        
        supabase.table('jobs').update({
            'image_count': len(confirmed_files),
            'stage_status': stage_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        
        return {
            'job_id': job_id,
            'confirmed_count': len(confirmed_files),
            'files': confirmed_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload confirmation failed: {e}")

@app.post("/jobs/{job_id}/refine")
async def submit_mask_refinement(
    job_id: str,
    request: MaskRefinementRequest,
    user_id: str = Depends(verify_user_token)
):
    """submit mask refinement data"""
    try:
        # verify job ownership
        job_response = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', user_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # store refinement data
        refinement_data = {
            'job_id': job_id,
            'refinement_data': request.refinement_data
        }
        
        response = supabase.table('mask_refinements').insert(refinement_data).execute()
        
        # update job status
        job = job_response.data
        stage_status = job.get('stage_status', {})
        stage_status['mask_refined'] = True
        
        supabase.table('jobs').update({
            'stage_status': stage_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        
        return {
            'job_id': job_id,
            'refinement_id': response.data[0]['id'],
            'status': 'refinement_saved'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {e}")

@app.post("/jobs/{job_id}/submit")
async def submit_job_for_processing(
    job_id: str,
    user_id: str = Depends(verify_user_token)
):
    """submit job to sqs queue for processing"""
    try:
        # verify job ownership and readiness
        job_response = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', user_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_response.data
        stage_status = job['stage_status']
        
        if not stage_status.get('upload_done'):
            raise HTTPException(status_code=400, detail="Images not uploaded")
        
        # Optionally require mask refinement for better results
        # if not stage_status.get('mask_refined'):
        #     raise HTTPException(status_code=400, detail="Mask refinement not completed")
        
        # create sqs message
        sqs_message = {
            'job_id': job_id,
            'user_id': user_id,
            's3_bucket': UPLOAD_BUCKET,
            's3_prefix': job['s3_prefix'],
            'image_count': job['image_count'],
            'processing_options': job['processing_options']
        }
        
        # send to sqs
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(sqs_message),
            MessageAttributes={
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'user_id': {'StringValue': user_id, 'DataType': 'String'}
            }
        )
        
        # update job status
        supabase.table('jobs').update({
            'status': 'pending'
        }).eq('id', job_id).execute()
        
        return {
            'job_id': job_id,
            'status': 'pending',
            'message_id': response['MessageId'],
            'queue_position': 'unknown'  # could query sqs for approximate position
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job submission failed: {e}")

@app.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user_id: str = Depends(verify_user_token)
):
    """get job status and details"""
    try:
        # get job with related data
        job_response = supabase.table('jobs').select('''
            *,
            mask_refinements(*),
            job_results(*)
        ''').eq('id', job_id).eq('user_id', user_id).single().execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job_response.data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job: {e}")

@app.get("/jobs")
async def get_user_jobs(
    user_id: str = Depends(verify_user_token),
    limit: int = 10,
    offset: int = 0
):
    """get user's jobs with pagination"""
    try:
        response = supabase.table('jobs').select('*').eq('user_id', user_id) \
            .order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            'jobs': response.data,
            'count': len(response.data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {e}")


@app.post("/jobs/{job_id}/timeout")
async def handle_job_timeout(
    job_id: str,
    worker_verified: bool = Depends(verify_worker_token)
):
    """handle job timeout and cleanup"""
    try:
        # get job
        job_response = supabase_admin.table('jobs').select('*').eq('id', job_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_response.data
        
        # update job status to failed due to timeout
        supabase_admin.table('jobs').update({
            'status': 'failed',
            'error_message': f'Job timed out after {MAX_JOB_DURATION_MINUTES} minutes',
            'completed_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('id', job_id).execute()
        
        # shutdown worker instance on timeout
        worker_instance_id = job.get('worker_instance_id')
        if worker_instance_id:
            logger.warning(f"Job {job_id} timed out, shutting down instance {worker_instance_id}")
            await shutdown_worker_instance(worker_instance_id)
        
        logger.warning(f"Job {job_id} timed out after {MAX_JOB_DURATION_MINUTES} minutes")
        
        return {
            'status': 'timeout_handled',
            'job_id': job_id,
            'message': f'Job marked as failed due to timeout'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle timeout for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to handle timeout: {e}")

# worker endpoints (called by ec2)

@app.patch("/jobs/{job_id}/status")
async def update_job_status(
    job_id: str,
    update: JobStatusUpdate,
    worker_verified: bool = Depends(verify_worker_token)
):
    """update job status from ec2 worker (enhanced for AWS function stages)"""
    try:
        # get current job to access stage status
        current_job = supabase_admin.table('jobs').select('*').eq('id', job_id).single().execute()
        if not current_job.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = current_job.data
        current_stages = job.get('stage_status', {})
        
        # prepare update data
        update_data = {'updated_at': datetime.now().isoformat()}
        
        # handle AWS function stage progression
        if update.stage_status:
            current_stages.update(update.stage_status)
            update_data['stage_status'] = current_stages
            
            # auto-advance job status based on completed stages
            if not update.status:  # only auto-advance if status not explicitly set
                if current_stages.get('cleanup_done'):
                    update_data['status'] = 'completed'
                    update_data['completed_at'] = datetime.now().isoformat()
                elif current_stages.get('brush_done'):
                    update_data['status'] = 'cleanup_processing'
                elif current_stages.get('colmap_done'):
                    update_data['status'] = 'brush_processing'
                elif current_stages.get('sam2_done'):
                    update_data['status'] = 'colmap_processing'
                elif current_stages.get('upload_done'):
                    update_data['status'] = 'sam2_processing'
        
        if update.status:
            update_data['status'] = update.status
        
        if update.worker_instance_id:
            update_data['worker_instance_id'] = update.worker_instance_id
        
        if update.started_at:
            update_data['started_at'] = update.started_at
        
        if update.completed_at:
            update_data['completed_at'] = update.completed_at
        
        if update.error_message:
            update_data['error_message'] = update.error_message
        
        # update using admin client to bypass RLS
        response = supabase_admin.table('jobs').update(update_data).eq('id', job_id).execute()
        
        # handle auto-shutdown for completed or failed jobs
        final_status = update_data.get('status', job.get('status'))
        worker_instance_id = job.get('worker_instance_id') or update.worker_instance_id
        
        if final_status in ['completed', 'failed'] and worker_instance_id:
            logger.info(f"Job {job_id} finished with status {final_status}, initiating shutdown")
            await shutdown_worker_instance(worker_instance_id)
        
        # store processing stats if provided
        if update.processing_stats:
            metrics_data = {
                'job_id': job_id,
                'stage': update.processing_stats.get('stage', 'unknown'),
                'processing_time_ms': update.processing_stats.get('processing_time_ms'),
                'throughput_mpix_per_sec': update.processing_stats.get('throughput_mpix_per_sec'),
                'optimization_used': update.processing_stats.get('optimization_used', 'python'),
                'worker_instance_id': update.worker_instance_id
            }
            
            supabase_admin.table('processing_metrics').insert(metrics_data).execute()
        
        return {'status': 'updated', 'job_id': job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update job status: {e}")

@app.post("/jobs/{job_id}/results")
async def store_job_results(
    job_id: str,
    results: Dict[str, Any],
    worker_verified: bool = Depends(verify_worker_token)
):
    """store final job results"""
    try:
        # store results metadata
        results_data = {
            'job_id': job_id,
            'splat_file_s3_key': results.get('splat_file'),
            'preview_video_s3_key': results.get('preview_video'),
            'point_cloud_s3_key': results.get('point_cloud'),
            'file_sizes': results.get('file_sizes', {}),
            'processing_stats': results.get('processing_stats', {}),
            'quality_metrics': results.get('quality_metrics', {})
        }
        
        response = supabase_admin.table('job_results').insert(results_data).execute()
        
        # update job to completed
        supabase_admin.table('jobs').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'results_metadata': results
        }).eq('id', job_id).execute()
        
        return {'status': 'results_stored', 'result_id': response.data[0]['id']}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store results: {e}")

# dashboard endpoints

@app.get("/dashboard/stats")
async def get_dashboard_stats(
    user_id: str = Depends(verify_user_token)
) -> DashboardStatsResponse:
    """get dashboard statistics for user"""
    try:
        # get all user jobs with results
        jobs_response = supabase.table('jobs').select('''
            *,
            job_results(file_sizes)
        ''').eq('user_id', user_id).execute()
        
        jobs = jobs_response.data
        
        # calculate stats
        total_scans = len(jobs)
        complete_scans = len([j for j in jobs if j['status'] == 'completed'])
        processing_scans = len([j for j in jobs if j['status'] in ['pending', 'sam2_processing', 'colmap_processing', 'brush_processing', 'cleanup_processing']])
        failed_scans = len([j for j in jobs if j['status'] == 'failed'])
        
        # calculate total storage usage
        total_storage_mb = 0.0
        for job in jobs:
            if job.get('job_results') and len(job['job_results']) > 0:
                file_sizes = job['job_results'][0].get('file_sizes', {})
                total_storage_mb += file_sizes.get('splat_file_mb', 0)
                total_storage_mb += file_sizes.get('point_cloud_mb', 0)
                total_storage_mb += file_sizes.get('preview_video_mb', 0)
        
        # get recent activity (last 10 jobs)
        recent_jobs = sorted(jobs, key=lambda x: x['created_at'], reverse=True)[:10]
        recent_activity = []
        
        for job in recent_jobs:
            activity = {
                'job_id': job['id'],
                'name': job['name'],
                'status': job['status'],
                'created_at': job['created_at'],
                'completed_at': job.get('completed_at')
            }
            
            # add processing time if available
            if job.get('started_at') and job.get('completed_at'):
                start_time = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                processing_time_seconds = (end_time - start_time).total_seconds()
                activity['processing_time_seconds'] = processing_time_seconds
                
            recent_activity.append(activity)
        
        return DashboardStatsResponse(
            total_scans=total_scans,
            complete_scans=complete_scans,
            processing_scans=processing_scans,
            failed_scans=failed_scans,
            total_storage_mb=round(total_storage_mb, 2),
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard stats for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {e}")

@app.get("/jobs/{job_id}/preview")
async def get_job_preview(
    job_id: str,
    user_id: str = Depends(verify_user_token)
):
    """get 3D model preview data and thumbnails"""
    try:
        # verify job ownership
        job_response = supabase.table('jobs').select('''
            *,
            job_results(*)
        ''').eq('id', job_id).eq('user_id', user_id).single().execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_response.data
        
        if job['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Job not completed yet")
        
        if not job.get('job_results') or len(job['job_results']) == 0:
            raise HTTPException(status_code=404, detail="Results not found")
        
        results = job['job_results'][0]
        
        # generate preview URLs for 3D viewer
        preview_data = {
            'job_id': job_id,
            'name': job['name'],
            'status': job['status'],
            'created_at': job['created_at'],
            'completed_at': job.get('completed_at'),
            'image_count': job.get('image_count', 0),
            'file_sizes': results.get('file_sizes', {}),
            'quality_metrics': results.get('quality_metrics', {}),
            'processing_stats': results.get('processing_stats', {})
        }
        
        # generate presigned URLs for file access
        if results.get('splat_file_s3_key'):
            preview_data['splat_url'] = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': UPLOAD_BUCKET, 'Key': results['splat_file_s3_key']},
                ExpiresIn=3600
            )
        
        if results.get('preview_video_s3_key'):
            preview_data['preview_video_url'] = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': UPLOAD_BUCKET, 'Key': results['preview_video_s3_key']},
                ExpiresIn=3600
            )
        
        if results.get('point_cloud_s3_key'):
            preview_data['point_cloud_url'] = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': UPLOAD_BUCKET, 'Key': results['point_cloud_s3_key']},
                ExpiresIn=3600
            )
        
        # generate thumbnail URL if available
        thumbnail_key = f"jobs/{job_id}/results/thumbnail.jpg"
        try:
            s3_client.head_object(Bucket=UPLOAD_BUCKET, Key=thumbnail_key)
            preview_data['thumbnail_url'] = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': UPLOAD_BUCKET, 'Key': thumbnail_key},
                ExpiresIn=3600
            )
        except s3_client.exceptions.NoSuchKey:
            # thumbnail doesn't exist, that's okay
            pass
        
        return preview_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preview for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job preview: {e}")

# download endpoints

@app.get("/jobs/{job_id}/download/{file_type}")
async def get_download_url(
    job_id: str,
    file_type: str,  # 'splat', 'ply', 'preview', etc
    user_id: str = Depends(verify_user_token)
):
    """generate presigned download url"""
    try:
        # verify job ownership
        job_response = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', user_id).single().execute()
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # get results
        results_response = supabase.table('job_results').select('*').eq('job_id', job_id).single().execute()
        if not results_response.data:
            raise HTTPException(status_code=404, detail="Results not found")
        
        results = results_response.data
        
        # map file type to s3 key
        file_mapping = {
            'splat': results.get('splat_file_s3_key'),
            'ply': results.get('point_cloud_s3_key'), 
            'preview': results.get('preview_video_s3_key')
        }
        
        s3_key = file_mapping.get(file_type)
        if not s3_key:
            raise HTTPException(status_code=404, detail=f"File type {file_type} not found")
        
        # generate presigned url
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': UPLOAD_BUCKET, 'Key': s3_key},
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            'download_url': download_url,
            'file_type': file_type,
            'expires_in': 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("production_fastapi:app", host="0.0.0.0", port=8000, reload=True)