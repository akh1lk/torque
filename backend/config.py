# SAM2 Interactive Backend Configuration

# Server settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# SAM2 Model settings
SAM2_MODEL = "sam2.1_l.pt"  # Options: sam2_t.pt, sam2_s.pt, sam2_b.pt, sam2_l.pt
SAM2_CONF_THRESHOLD = 0.25
SAM2_IMAGE_SIZE = 1024

# File storage settings
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
SESSION_CLEANUP_HOURS = 24  # Auto-cleanup sessions after 24 hours

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

# Performance settings
MAX_CONCURRENT_SESSIONS = 5
FRAME_EXTRACTION_QUALITY = 95  # JPEG quality for extracted frames
