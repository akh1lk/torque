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
from datetime import datetime
import os
import json
from supabase import create_client, Client
import asyncio

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

# config
UPLOAD_BUCKET = os.getenv('TORQUE_UPLOAD_BUCKET', 'torque-jobs')
SQS_QUEUE_URL = os.getenv('TORQUE_SQS_QUEUE_URL')
WORKER_TOKEN = os.getenv('FASTAPI_WORKER_TOKEN', 'secure-worker-token')

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
            'processing_options': request.processing_options
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
                ExpiresIn=3600  # 1 hour to upload
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