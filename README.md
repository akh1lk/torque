# Torque

Torque is a 3D scanning web application that converts videos into interactive 3D models using Neural Gaussian Splatting. Users can upload videos, define object boundaries through an intuitive brush interface, and generate 3D models with transparent backgrounds.

## Architecture

- **Frontend**: Next.js 13 with React Three Fiber for 3D visualization
- **Backend**: FastAPI for video processing pipeline
- **Processing**: AWS EC2 instances running SAM2 → COLMAP → Gaussian Splatting pipeline
- **Storage**: S3 buckets for asset management

## Key Features

- Video upload and frame extraction
- Interactive brush masking interface with SAM2 integration
- 3D reconstruction pipeline (SAM2 → COLMAP → Gaussian Splatting)
- Real-time 3D model preview
- RGBA image generation with transparent backgrounds
- Authentication and user management
- Dashboard for scan management

## File Structure

### Frontend (Next.js)
```
app/                    # Next.js 13 app router pages
components/            # Reusable UI components
contexts/             # React context providers
public/               # Static assets
```

### Backend (FastAPI)
```
api/                  # FastAPI server and endpoints
backend/awsFunctions/ # EC2 processing scripts
  ├── init_job.py          # Initial job setup and preview generation
  ├── refine_mask.py       # Mask refinement based on user brush input
  ├── run_sam2.py          # SAM2 video processing and RGBA generation
  └── sam2_service.py      # SAM2 service wrapper
```

### Configuration
```
requirements.txt      # Python dependencies
package.json         # Node.js dependencies
vercel.json          # Deployment configuration
```

## Processing Pipeline

1. **Upload**: Users upload videos through the web interface
2. **Frame Extraction**: Videos are processed into sequential frames (0001.png, 0002.png, etc.)
3. **Brush Masking**: Users define object boundaries using interactive brush tools
4. **SAM2 Segmentation**: Segment Anything Model 2 propagates masks across all frames
5. **RGBA Generation**: Transparent background images are created using SAM2 masks
6. **COLMAP**: Structure-from-Motion reconstruction generates camera poses and sparse point cloud
7. **Gaussian Splatting**: Neural rendering creates interactive 3D models

## Environment Requirements

- Node.js with pnpm package manager
- Python 3.x with virtual environment
- AWS credentials for S3 and EC2 access
- CUDA-compatible GPU for SAM2 and Gaussian Splatting processing