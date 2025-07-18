#!/usr/bin/env python3
"""
run_colmap.py

EC2 worker script to:
1. Use RGBA images from SAM2 output
2. Run COLMAP pipeline (feature extraction, matching, reconstruction)
3. Generate sparse reconstruction (cameras.bin, images.bin, points3D.bin)
4. Keep results locally for Gaussian Splatting pipeline
5. Notify FastAPI of completion
"""