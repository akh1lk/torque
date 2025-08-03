# FastAPI Deployment Guide for Torque

## Overview

This guide covers deploying the production FastAPI server with:
- Supabase auth integration
- S3 image uploads  
- SQS job queue
- Database schema setup

## 1. Supabase Setup

### Create Project
1. Go to [supabase.com](https://supabase.com) → New Project
2. Copy your project URL and keys

### Run Database Schema
1. Go to Supabase Dashboard → SQL Editor
2. Copy and run the entire `supabase_schema.sql` file
3. This creates all tables, RLS policies, and triggers

### Configure Auth
1. Go to Authentication → Settings
2. Enable email auth (or social providers)
3. Set JWT expiry to reasonable time (24 hours)

### Storage Setup
1. Go to Storage → Create Buckets:
   - `torque-uploads` (private)
   - `torque-jobs` (private) 
   - `torque-results` (public for final assets)

2. Set up Storage Policies:
```sql
-- Users can upload to their job folders
CREATE POLICY "Users can upload job images" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'torque-jobs' AND 
    (storage.foldername(name))[1] = 'jobs' AND
    auth.uid()::text = (storage.foldername(name))[3]
  );

-- Users can download their results  
CREATE POLICY "Users can download results" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'torque-results' AND
    auth.uid()::text = (storage.foldername(name))[2]
  );
```

## 2. AWS Setup

### IAM User for FastAPI
Create IAM user with this policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject", 
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::torque-jobs/*",
        "arn:aws:s3:::torque-uploads/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:torque-processing-queue"
    }
  ]
}
```

### SQS Queue Setup
```bash
# Create queue (if not already done)
aws sqs create-queue --queue-name torque-processing-queue \
  --attributes '{
    "VisibilityTimeoutSeconds": "1800",
    "MessageRetentionPeriod": "1209600", 
    "ReceiveMessageWaitTimeSeconds": "20"
  }'

# Get queue URL
aws sqs get-queue-url --queue-name torque-processing-queue
```

## 3. Railway Deployment

### Environment Variables
Set these in Railway dashboard:
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...  # anon key
SUPABASE_SERVICE_KEY=eyJ...  # service role key

# AWS  
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# App Config
TORQUE_UPLOAD_BUCKET=torque-jobs
TORQUE_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../torque-processing-queue
FASTAPI_WORKER_TOKEN=your-secure-random-token-here
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### Deploy
1. Connect Railway to your GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn production_fastapi:app --host 0.0.0.0 --port $PORT`
4. Deploy!

## 4. Testing the API

### Create User (via Supabase Auth)
```bash
# Users can sign up directly via frontend using Supabase client
# Or create via API (implement signup endpoint)
```

### Test Job Flow
```bash
# 1. Create job
curl -X POST https://your-api.railway.app/jobs \
  -H "Authorization: Bearer your-supabase-jwt" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Bottle Scan"}'

# Response: {"job_id": "uuid-here", "status": "uploading", ...}

# 2. Get upload URLs
curl "https://your-api.railway.app/jobs/uuid-here/upload-urls?filenames=image1.jpg,image2.jpg" \
  -H "Authorization: Bearer your-supabase-jwt"

# Response: {"upload_urls": [{"presigned_post": {"url": "...", "fields": {...}}}]}

# 3. Upload directly to S3 (using presigned POST)
# Frontend does this step with each file

# 4. Confirm uploads complete
curl -X POST https://your-api.railway.app/jobs/uuid-here/upload-complete \
  -H "Authorization: Bearer your-supabase-jwt" \
  -H "Content-Type: application/json" \
  -d '[{"s3_key": "jobs/uuid/images/0001.jpg", "original_filename": "image1.jpg"}]'

# 5. Submit for processing
curl -X POST https://your-api.railway.app/jobs/uuid-here/submit \
  -H "Authorization: Bearer your-supabase-jwt"

# 6. Check status
curl https://your-api.railway.app/jobs/uuid-here \
  -H "Authorization: Bearer your-supabase-jwt"
```

## 5. EC2 Worker Integration

### Update Worker Environment
On your EC2 instance, add:
```bash
export FASTAPI_URL="https://your-api.railway.app"
export FASTAPI_TOKEN="your-secure-random-token-here"
```

### Update Worker Scripts
Modify your existing pipeline scripts to call the new endpoints:
- `PATCH /jobs/{job_id}/status` for progress updates
- `POST /jobs/{job_id}/results` when complete

## 6. Frontend Integration

### Supabase Client Setup
```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://your-project.supabase.co'
const supabaseAnonKey = 'your-anon-key'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Auth Hook
```typescript
// hooks/useAuth.ts
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setToken(session?.access_token ?? null)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ?? null)
        setToken(session?.access_token ?? null)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  return { user, token }
}
```

### API Client
```typescript
// lib/api.ts
export class TorqueAPI {
  constructor(private baseURL: string, private token: string) {}

  async createJob(name: string) {
    const response = await fetch(`${this.baseURL}/jobs`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name })
    })
    return response.json()
  }

  async getUploadUrls(jobId: string, filenames: string[]) {
    const filenamesStr = filenames.join(',')
    const response = await fetch(
      `${this.baseURL}/jobs/${jobId}/upload-urls?filenames=${encodeURIComponent(filenamesStr)}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    )
    return response.json()
  }

  async uploadToS3(presignedPost: any, file: File) {
    const formData = new FormData()
    
    // Add all the required fields from presigned post
    Object.entries(presignedPost.fields).forEach(([key, value]) => {
      formData.append(key, value as string)
    })
    
    // Add the file last
    formData.append('file', file)

    const response = await fetch(presignedPost.url, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error('S3 upload failed')
    }
    
    return response
  }

  async uploadImages(jobId: string, files: File[]) {
    // 1. Get presigned URLs
    const filenames = files.map(f => f.name)
    const { upload_urls } = await this.getUploadUrls(jobId, filenames)

    // 2. Upload each file directly to S3
    const uploadPromises = files.map(async (file, index) => {
      const uploadInfo = upload_urls[index]
      await this.uploadToS3(uploadInfo.presigned_post, file)
      
      return {
        s3_key: uploadInfo.s3_key,
        original_filename: uploadInfo.original_filename,
        file_size: file.size
      }
    })

    const uploadedFiles = await Promise.all(uploadPromises)

    // 3. Confirm uploads complete
    const response = await fetch(`${this.baseURL}/jobs/${jobId}/upload-complete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(uploadedFiles)
    })

    return response.json()
  }

  async submitJob(jobId: string) {
    const response = await fetch(`${this.baseURL}/jobs/${jobId}/submit`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    })
    return response.json()
  }

  async getJobStatus(jobId: string) {
    const response = await fetch(`${this.baseURL}/jobs/${jobId}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    })
    return response.json()
  }
}
```

## 7. Workflow Summary

1. **User Signs Up**: Via Supabase auth (magic link, email/password)
2. **Create Job**: `POST /jobs` with scan name
3. **Upload Images**: `POST /jobs/{id}/upload` with multiple files
4. **Refine Masks** (optional): `POST /jobs/{id}/refine` with brush data
5. **Submit Job**: `POST /jobs/{id}/submit` → goes to SQS queue
6. **EC2 Processing**: Worker picks up job, runs pipeline, updates status
7. **Download Results**: `GET /jobs/{id}/download/{type}` for final files

## 8. Monitoring

### Check Queue Status
```bash
curl https://your-api.railway.app/admin/queue/stats
```

### Database Monitoring
- Supabase Dashboard → Database → Tables
- Check job statuses, processing metrics
- Monitor storage usage

### Logs
- Railway: Dashboard → Deployments → Logs
- EC2: `journalctl -u torque-worker -f`

This setup gives you a production-ready API that scales with your needs!