# SAM2 Interactive Video Segmentation Backend

An interactive backend for video object segmentation using Meta's SAM2 (Segment Anything Model 2). This backend provides a REST API for interactive video segmentation with the following workflow:

1. **Upload Video** - User uploads a video file
2. **Frame Selection** - User selects points on the first frame (or any frame)
3. **Initial Segmentation** - SAM2 generates initial mask based on user points
4. **Mask Propagation** - Masks are propagated through the video sequence
5. **Refinement** - User can refine masks on specific frames and re-propagate
6. **Export** - Generate final segmented video

## Features

- 🎯 **Interactive Point Selection** - Add positive/negative points for precise segmentation
- 🔄 **Mask Propagation** - Automatic mask tracking through video frames
- ✏️ **Mask Refinement** - Refine masks on any frame and re-propagate
- 📹 **Video Export** - Export segmented videos with overlays
- 🌐 **REST API** - Complete HTTP API for frontend integration
- 🧹 **Session Management** - Handle multiple concurrent video sessions

## Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Download SAM2 Model** (if not already available)
```bash
# The model will be automatically downloaded on first use
# Or manually download from: https://github.com/facebookresearch/segment-anything-2
```

## Quick Start

### 1. Start the Server
```bash
python main.py
```
The server will start at `http://localhost:8000`

### 2. Test with CLI Tool
```bash
# Basic video info
python run_sam2.py --video test.mp4

# Add annotation and propagate
python run_sam2.py --video test.mp4 --frame 0 \
  --points "[[920,470],[909,138]]" --labels "[1,1]" \
  --propagate-end 100 --export
```

### 3. Test with HTTP API
```bash
python test_workflow.py
```

## API Endpoints

### Upload Video
```http
POST /upload-video
Content-Type: multipart/form-data

Returns: Session info with session_id
```

### Get Frame
```http
GET /frame/{session_id}/{frame_idx}

Returns: JPEG image of the specified frame
```

### Annotate Frame
```http
POST /annotate-frame/{session_id}
Content-Type: application/json

{
  "frame_idx": 0,
  "points": [
    {"x": 920, "y": 470, "label": 1},
    {"x": 900, "y": 450, "label": 0}
  ]
}
```

### Propagate Masks
```http
POST /propagate/{session_id}
Content-Type: application/json

{
  "session_id": "uuid",
  "start_frame": 0,
  "end_frame": 100
}
```

### Get Mask Overlay
```http
GET /overlay/{session_id}/{frame_idx}

Returns: JPEG image with mask overlay
```

### Export Video
```http
GET /export/{session_id}

Returns: MP4 video file with segmentation
```

## Interactive Workflow

### 1. Basic Segmentation
```python
import requests

# Upload video
files = {"file": open("video.mp4", "rb")}
response = requests.post("http://localhost:8000/upload-video", files=files)
session = response.json()

# Add points to first frame
annotation = {
    "frame_idx": 0,
    "points": [
        {"x": 920, "y": 470, "label": 1},  # Positive point
        {"x": 900, "y": 450, "label": 1}   # Another positive point
    ]
}
requests.post(f"http://localhost:8000/annotate-frame/{session['session_id']}", 
              json=annotation)

# Propagate through video
propagation = {
    "session_id": session["session_id"],
    "start_frame": 0,
    "end_frame": 100
}
requests.post(f"http://localhost:8000/propagate/{session['session_id']}", 
              json=propagation)
```

### 2. Mask Refinement
```python
# If you're not satisfied with frame 50, add refinement points
refinement = {
    "frame_idx": 50,
    "points": [
        {"x": 800, "y": 600, "label": 0}  # Negative point to exclude area
    ]
}
requests.post(f"http://localhost:8000/refine-mask/{session['session_id']}", 
              json=refinement)

# Re-propagate from frame 50 onwards
propagation = {
    "session_id": session["session_id"],
    "start_frame": 50,
    "end_frame": 100
}
requests.post(f"http://localhost:8000/propagate/{session['session_id']}", 
              json=propagation)
```

## Configuration

Edit `config.py` to customize:

- **Model Selection**: Choose between sam2_t.pt, sam2_s.pt, sam2_b.pt, sam2_l.pt
- **Performance**: Max concurrent sessions, image quality
- **Storage**: Upload limits, cleanup intervals
- **CORS**: Allowed origins for frontend integration

## File Structure

```
backend/
├── main.py              # FastAPI server
├── sam2_manager.py      # SAM2 video processing logic
├── run_sam2.py          # CLI tool for testing
├── test_workflow.py     # HTTP API test script
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── uploads/             # Uploaded videos (auto-created)
└── outputs/             # Session outputs (auto-created)
    └── {session_id}/
        ├── frames/      # Extracted video frames
        ├── masks/       # Generated masks
        ├── overlays/    # Frame+mask overlays
        └── output_video.mp4
```

## Usage Tips

1. **Point Selection**: 
   - Use positive points (label=1) inside the object
   - Use negative points (label=0) to exclude unwanted areas
   - Start with 2-3 positive points for best results

2. **Performance**:
   - Use sam2_t.pt for faster processing
   - Use sam2_l.pt for better accuracy
   - Process shorter segments for better interactivity

3. **Refinement Strategy**:
   - Check key frames first (beginning, middle, end)
   - Add refinements only where needed
   - Re-propagate from the refined frame forward

## Integration with Frontend

This backend is designed to work with your frontend. Key integration points:

1. **File Upload**: Use the `/upload-video` endpoint
2. **Frame Display**: Fetch frames with `/frame/{session_id}/{frame_idx}`
3. **Point Collection**: Send user clicks to `/annotate-frame/{session_id}`
4. **Real-time Preview**: Display overlays from `/overlay/{session_id}/{frame_idx}`
5. **Export**: Download results from `/export/{session_id}`

## Troubleshooting

- **CUDA Issues**: Install PyTorch with CUDA support for GPU acceleration
- **Memory Errors**: Reduce video resolution or process shorter segments
- **Model Download**: Ensure internet connection for automatic model download
- **CORS Errors**: Check `config.py` ALLOWED_ORIGINS setting
