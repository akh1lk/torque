# Torque - Image-to-3D Asset Reconstruction

**Transform 2D captures into interactive 3D assets using Gaussian Splatting & SAM2**

Torque: A pipeline for converting 2D images of a real-world asset into high-quality 3D models for VFX hobbyists to use in games, AR, and other digital media (TikTok, Instagram, etc!)

<table>
<tr>
<td width="50%">
<img src="demo/bottle_image.jpg" alt="Input 2D Image" />
<p align="center"><em>Input: Multi-view 2D captures</em></p>
</td>
<td width="50%">
<img src="demo/bottle_3d_reconstruction.png" alt="3D Asset Result" />
<p align="center"><em>Output: Interactive 3D asset</em></p>
</td>
</tr>
</table>

## Architecture

- **Frontend:** Next.js 13 + React Three Fiber for 3D visualization  
- **Backend:** FastAPI handling video and image processing  
- **Processing:** SAM2 → COLMAP → Gaussian Splatting on AWS EC2  
- **Storage:** AWS S3 for managing assets and exports  

## Processing Pipeline

1. **Upload**: Users upload image sequences through the web interface
2. **User-Interactive Masking**: Users define object boundaries via Meta's SAM2 Image Segmentation Model
3. **RGBA Generation**: Transparent background images are created via segmentation masks
4. **Performance**: Used C++ to Parallelize OpenCV & RGBA operations via OpenMP and SIMD
5. **COLMAP**: Structure-from-Motion reconstruction generates camera poses and sparse point cloud (SfM model for points)
6. **Gaussian Splatting**: 3D reconstruction creates interactive models (powered by Brush engine)
7. **Export**: Clean 3D assets ready for games, AR, and digital content
  
## File Structure

### Frontend (Next.js)
```
app/                    # Next.js 13 app router pages
components/            # Reusable UI components
contexts/             # React context providers
public/               # Static assets
```

### Backend (FastAPI hosted separately)
```
api/                  # FastAPI server and endpoints
backend/awsFunctions/ # EC2 processing scripts
  ├── init_job.py          # Initial job setup and preview generation
  ├── refine_mask.py       # Mask refinement based on user brush input
  ├── run_sam2.py          # SAM2 video processing and RGBA generation
  └── sam2_service.py      # SAM2 service wrapper
```

### Config
```
requirements.txt      # Python dependencies
package.json         # Node.js dependencies
vercel.json          # Deployment configuration
```

## Environment Requirements

- Node.js + pnpm package manager
- Python 3.x with venv
- AWS creds for S3 and EC2 access OR CUDA-compatible GPU for SAM2 and Gaussian Splatting processing
