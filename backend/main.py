from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import json
import cv2
import numpy as np
from pathlib import Path
import shutil
from sam2_manager import SAM2VideoManager

app = FastAPI(title="Torque SAM2 Interactive Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for sessions (in production, use Redis or database)
sessions: Dict[str, SAM2VideoManager] = {}

# Directory for storing uploaded videos and outputs
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class Point(BaseModel):
    x: int
    y: int
    label: int  # 1 for positive, 0 for negative

class FrameAnnotation(BaseModel):
    frame_idx: int
    points: List[Point]

class PropagationRequest(BaseModel):
    session_id: str
    start_frame: int
    end_frame: Optional[int] = None

class SessionResponse(BaseModel):
    session_id: str
    video_path: str
    total_frames: int
    fps: float
    width: int
    height: int

@app.post("/upload-video", response_model=SessionResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video and create a new SAM2 session"""
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Unsupported video format")
    
    # Create session ID and save video
    session_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{session_id}_{file.filename}"
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Initialize SAM2 manager
    try:
        sam_manager = SAM2VideoManager(str(video_path))
        sessions[session_id] = sam_manager
        
        # Get video info
        video_info = sam_manager.get_video_info()
        
        return SessionResponse(
            session_id=session_id,
            video_path=str(video_path),
            **video_info
        )
    except Exception as e:
        # Clean up on error
        if video_path.exists():
            video_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to initialize SAM2: {str(e)}")

@app.get("/frame/{session_id}/{frame_idx}")
async def get_frame(session_id: str, frame_idx: int):
    """Get a specific frame from the video"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        frame_path = sessions[session_id].get_frame(frame_idx)
        return FileResponse(frame_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/annotate-frame/{session_id}")
async def annotate_frame(session_id: str, annotation: FrameAnnotation):
    """Add point annotations to a specific frame"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Convert points to the format expected by SAM2
        points = [[p.x, p.y] for p in annotation.points]
        labels = [p.label for p in annotation.points]
        
        mask_path = sessions[session_id].add_frame_annotation(
            annotation.frame_idx, points, labels
        )
        
        return {
            "success": True,
            "mask_path": mask_path,
            "frame_idx": annotation.frame_idx
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/propagate/{session_id}")
async def propagate_masks(session_id: str, request: PropagationRequest):
    """Propagate masks through the video"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        result = sessions[session_id].propagate_masks(
            start_frame=request.start_frame,
            end_frame=request.end_frame
        )
        
        return {
            "success": True,
            "propagated_frames": result["propagated_frames"],
            "output_video": result["output_video"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mask/{session_id}/{frame_idx}")
async def get_mask(session_id: str, frame_idx: int):
    """Get the mask for a specific frame"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        mask_path = sessions[session_id].get_mask(frame_idx)
        return FileResponse(mask_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Mask not found")

@app.get("/overlay/{session_id}/{frame_idx}")
async def get_overlay(session_id: str, frame_idx: int):
    """Get frame with mask overlay"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        overlay_path = sessions[session_id].get_overlay(frame_idx)
        return FileResponse(overlay_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up a session and its associated files"""
    if session_id in sessions:
        sessions[session_id].cleanup()
        del sessions[session_id]
        return {"success": True, "message": "Session deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "sessions": [
            {
                "session_id": sid,
                "video_info": sessions[sid].get_video_info()
            }
            for sid in sessions.keys()
        ]
    }

@app.post("/refine-mask/{session_id}")
async def refine_mask(session_id: str, annotation: FrameAnnotation):
    """Refine an existing mask with additional points"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        points = [[p.x, p.y] for p in annotation.points]
        labels = [p.label for p in annotation.points]
        
        mask_path = sessions[session_id].refine_mask(
            annotation.frame_idx, points, labels
        )
        
        return {
            "success": True,
            "mask_path": mask_path,
            "frame_idx": annotation.frame_idx
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/{session_id}")
async def export_results(session_id: str):
    """Export the final segmented video"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        export_path = sessions[session_id].export_video()
        return FileResponse(
            export_path,
            media_type='video/mp4',
            filename=f"segmented_{session_id}.mp4"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
