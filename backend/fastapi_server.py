"""
FastAPI Backend for Torque 3D Scanning Pipeline

provides rest api for:
- job submission and status tracking
- user authentication  
- file upload handling
- integration with sqs queue system
- supabase database operations
"""
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import boto3
import uuid
import time
from datetime import datetime, timedelta
import os
import json
import hashlib

from sqs_queue_system import SQSJobQueue, JobManager, TorqueJob


# pydantic models

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class JobSubmissionRequest(BaseModel):
    video_url: Optional[str] = None  # for direct s3 urls
    initial_points: Optional[List[List[int]]] = None  # sam2 prompts
    processing_options: Optional[Dict[str, Any]] = {}


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    progress: Dict[str, bool]
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class QueueStatsResponse(BaseModel):
    pending_jobs: int
    in_progress_jobs: int
    estimated_wait_minutes: int


# app initialization

app = FastAPI(
    title="Torque 3D Scanning API",
    description="Neural Gaussian Splatting pipeline with distributed processing",
    version="1.0.0"
)

# cors for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://torque.app"],  # add your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# security
security = HTTPBearer()

# global services
sqs_queue = SQSJobQueue()
job_manager = JobManager(sqs_queue)
s3_client = boto3.client('s3')

# config from env vars
UPLOAD_BUCKET = os.getenv('TORQUE_UPLOAD_BUCKET', 'torque-uploads')
RESULTS_BUCKET = os.getenv('TORQUE_RESULTS_BUCKET', 'torque-results')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


# auth functions

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """verify jwt token and return user_id"""
    token = credentials.credentials
    
    # simple token verification (replace with proper jwt in production)
    if token == "dev-token":
        return "dev-user"
    
    # todo: implement proper jwt verification with supabase
    raise HTTPException(status_code=401, detail="invalid token")


def hash_password(password: str) -> str:
    """simple password hashing (replace with bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()


# api endpoints

@app.get("/")
async def root():
    """health check endpoint"""
    return {
        "service": "torque-3d-scanning-api",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/queue/stats")
async def get_queue_stats() -> QueueStatsResponse:
    """get current queue statistics"""
    stats = sqs_queue.get_queue_stats()
    estimate = job_manager.estimate_completion_time()
    
    return QueueStatsResponse(
        pending_jobs=stats['pending_jobs'],
        in_progress_jobs=stats['in_progress_jobs'],
        estimated_wait_minutes=estimate['estimated_wait_minutes']
    )


# authentication endpoints

@app.post("/auth/register")
async def register_user(user_data: UserCreateRequest):
    """register new user account"""
    try:
        # todo: integrate with supabase auth
        # for now, return mock response
        user_id = f"user_{int(time.time())}"
        
        return {
            "user_id": user_id,
            "email": user_data.email,
            "message": "user registered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"registration failed: {e}")


@app.post("/auth/login")
async def login_user(login_data: UserLoginRequest):
    """authenticate user and return jwt token"""
    try:
        # todo: implement proper auth with supabase
        # for now, return mock token
        
        if login_data.email == "test@torque.app":
            return {
                "access_token": "dev-token",
                "token_type": "bearer",
                "user_id": "dev-user",
                "expires_in": 3600
            }
        
        raise HTTPException(status_code=401, detail="invalid credentials")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"login failed: {e}")


# file upload endpoints

@app.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    """upload video file to s3 for processing"""
    try:
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="file must be a video")
        
        # generate unique filename
        file_id = f"{user_id}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'mp4'
        s3_key = f"uploads/{file_id}.{file_extension}"
        
        # upload to s3
        s3_client.upload_fileobj(
            file.file,
            UPLOAD_BUCKET,
            s3_key,
            ExtraArgs={
                'ContentType': file.content_type,
                'Metadata': {
                    'user_id': user_id,
                    'original_filename': file.filename,
                    'upload_timestamp': datetime.utcnow().isoformat()
                }
            }
        )
        
        video_url = f"s3://{UPLOAD_BUCKET}/{s3_key}"
        
        return {
            "video_url": video_url,
            "file_size": file.size,
            "content_type": file.content_type,
            "upload_complete": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"upload failed: {e}")


# job management endpoints

@app.post("/jobs/submit")
async def submit_job(
    job_request: JobSubmissionRequest,
    user_id: str = Depends(verify_token)
) -> Dict[str, Any]:
    """submit new 3d scanning job for processing"""
    try:
        if not job_request.video_url:
            raise HTTPException(status_code=400, detail="video_url is required")
        
        # create job
        job = job_manager.create_job(
            user_id=user_id,
            video_url=job_request.video_url
        )
        
        # store initial points if provided
        if job_request.initial_points:
            # todo: save to s3 or database
            pass
        
        # submit to queue
        if job_manager.submit_for_processing(job):
            # todo: save job to supabase database
            
            return {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at,
                "estimated_completion": job_manager.estimate_completion_time()['estimated_completion']
            }
        else:
            raise HTTPException(status_code=500, detail="failed to submit job to queue")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"job submission failed: {e}")


@app.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    user_id: str = Depends(verify_token)
) -> JobStatusResponse:
    """get current status of a processing job"""
    try:
        # todo: fetch from supabase database
        # for now, return mock status
        
        return JobStatusResponse(
            job_id=job_id,
            status="processing",
            created_at=datetime.utcnow().isoformat(),
            progress={
                "init_done": True,
                "sam2_done": True,
                "colmap_done": False,
                "brush_done": False
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get job status: {e}")


@app.get("/jobs/user/{user_id}")
async def get_user_jobs(
    user_id: str,
    authenticated_user: str = Depends(verify_token),
    limit: int = 10,
    offset: int = 0
) -> List[JobStatusResponse]:
    """get all jobs for a user"""
    try:
        # verify user can access these jobs
        if user_id != authenticated_user:
            raise HTTPException(status_code=403, detail="access denied")
        
        # todo: fetch from supabase database
        # for now, return mock jobs
        
        return [
            JobStatusResponse(
                job_id=f"job_{i}",
                status="completed" if i % 2 == 0 else "processing",
                created_at=(datetime.utcnow() - timedelta(hours=i)).isoformat(),
                progress={
                    "init_done": True,
                    "sam2_done": True,
                    "colmap_done": True,
                    "brush_done": i % 2 == 0
                }
            )
            for i in range(limit)
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get user jobs: {e}")


@app.patch("/jobs/{job_id}/status")
async def update_job_status(
    job_id: str,
    status_update: Dict[str, Any],
    worker_token: str = Depends(verify_token)  # workers use special tokens
):
    """update job status (called by ec2 workers)"""
    try:
        # todo: verify worker token
        # todo: update job status in supabase database
        
        print(f"job {job_id} status update: {status_update}")
        
        return {"status": "updated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to update job status: {e}")


# results endpoints

@app.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    user_id: str = Depends(verify_token)
):
    """get final results for completed job"""
    try:
        # todo: verify user owns this job
        # todo: fetch results from s3 and database
        
        return {
            "job_id": job_id,
            "status": "completed",
            "results": {
                "splat_file": f"s3://{RESULTS_BUCKET}/{job_id}/final.splat",
                "preview_video": f"s3://{RESULTS_BUCKET}/{job_id}/preview.mp4",
                "point_cloud": f"s3://{RESULTS_BUCKET}/{job_id}/points.ply",
                "processing_stats": {
                    "total_time_minutes": 12.5,
                    "frames_processed": 120,
                    "optimization_used": "cpp"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get job results: {e}")


@app.get("/jobs/{job_id}/download/{file_type}")
async def download_result_file(
    job_id: str,
    file_type: str,  # splat, ply, mp4, etc
    user_id: str = Depends(verify_token)
):
    """generate signed url for downloading result files"""
    try:
        # todo: verify user owns this job
        # todo: verify file exists
        
        s3_key = f"{job_id}/final.{file_type}"
        
        # generate presigned url for download
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': RESULTS_BUCKET, 'Key': s3_key},
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            "download_url": download_url,
            "expires_in": 3600,
            "file_type": file_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to generate download url: {e}")


# admin endpoints (for monitoring)

@app.get("/admin/queue/stats")
async def get_detailed_queue_stats(admin_token: str = Depends(verify_token)):
    """detailed queue statistics for admin dashboard"""
    try:
        # todo: verify admin permissions
        
        stats = sqs_queue.get_queue_stats()
        estimate = job_manager.estimate_completion_time()
        
        return {
            "queue_stats": stats,
            "completion_estimate": estimate,
            "system_health": {
                "sqs_healthy": True,
                "s3_healthy": True,  # todo: implement health checks
                "database_healthy": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to get admin stats: {e}")


# websocket for real-time updates (optional)

@app.websocket("/ws/jobs/{job_id}")
async def job_status_websocket(websocket, job_id: str):
    """websocket for real-time job status updates"""
    await websocket.accept()
    
    try:
        while True:
            # todo: implement real-time status updates
            # could use redis pub/sub or database change streams
            
            status_update = {
                "job_id": job_id,
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send_json(status_update)
            await asyncio.sleep(5)  # update every 5 seconds
            
    except Exception as e:
        print(f"websocket error for job {job_id}: {e}")
    finally:
        await websocket.close()


# startup/shutdown events

@app.on_event("startup")
async def startup_event():
    """initialize services on startup"""
    print("torque fastapi server starting up...")
    print(f"sqs queue: {sqs_queue.queue_name}")
    print(f"upload bucket: {UPLOAD_BUCKET}")
    print(f"results bucket: {RESULTS_BUCKET}")


@app.on_event("shutdown") 
async def shutdown_event():
    """cleanup on shutdown"""
    print("torque fastapi server shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # for development
        log_level="info"
    )