"""
Smart Worker Daemon for Single EC2 Instance

runs the complete torque pipeline with intelligent shutdown:
- processes all jobs in sqs queue
- handles the full pipeline: init → refine_mask → sam2 → colmap → brush → cleanup  
- auto-shutdown after 2 hours OR when no jobs remain
- integrates with existing ec2 setup and pipeline scripts
"""
import time
import subprocess
import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import signal
import sys


class SmartWorker:
    """intelligent single-instance worker with auto-shutdown"""
    
    def __init__(self):
        # aws clients
        self.sqs = boto3.client('sqs')
        self.ec2 = boto3.client('ec2')
        
        # config from environment
        self.queue_url = os.getenv('TORQUE_SQS_QUEUE_URL')
        self.fastapi_url = os.getenv('FASTAPI_URL', 'https://torque-api.railway.app')
        self.fastapi_token = os.getenv('FASTAPI_TOKEN')
        self.bucket = os.getenv('TORQUE_S3_BUCKET', 'torque-jobs')
        
        # runtime limits
        self.max_runtime_hours = 2
        self.idle_shutdown_minutes = 5
        self.start_time = time.time()
        
        # instance info
        self.instance_id = self._get_instance_id()
        
        # job processing state
        self.current_job_id = None
        self.jobs_processed = 0
        self.last_job_time = time.time()
        
        # shutdown handling
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"smart worker initialized:")
        print(f"  instance: {self.instance_id}")
        print(f"  queue: {self.queue_url}")
        print(f"  max runtime: {self.max_runtime_hours} hours")
        print(f"  idle shutdown: {self.idle_shutdown_minutes} minutes")
    
    def _get_instance_id(self) -> str:
        """get ec2 instance id from metadata"""
        try:
            import requests
            response = requests.get(
                'http://169.254.169.254/latest/meta-data/instance-id',
                timeout=2
            )
            return response.text
        except:
            return "unknown-instance"
    
    def _signal_handler(self, signum, frame):
        """handle shutdown signals gracefully"""
        print(f"received signal {signum}, requesting shutdown...")
        self.shutdown_requested = True
    
    def run(self):
        """main worker loop with intelligent shutdown"""
        print("starting smart worker loop...")
        
        try:
            while not self.shutdown_requested:
                # check shutdown conditions
                if self._should_shutdown():
                    break
                
                # get next job from queue
                job_message = self._receive_job()
                
                if job_message:
                    # process the job
                    success = self._process_complete_job(job_message)
                    
                    if success:
                        self.jobs_processed += 1
                        self.last_job_time = time.time()
                        print(f"completed job {self.current_job_id} (total: {self.jobs_processed})")
                    else:
                        print(f"job {self.current_job_id} failed")
                    
                    self.current_job_id = None
                else:
                    # no jobs available - short sleep
                    print("no jobs available, waiting...")
                    time.sleep(30)
            
            print(f"worker loop ended - processed {self.jobs_processed} jobs")
            
        except Exception as e:
            print(f"worker loop error: {e}")
        finally:
            self._shutdown_instance()
    
    def _should_shutdown(self) -> bool:
        """check if worker should shutdown"""
        current_time = time.time()
        runtime_hours = (current_time - self.start_time) / 3600
        idle_minutes = (current_time - self.last_job_time) / 60
        
        # check max runtime
        if runtime_hours >= self.max_runtime_hours:
            print(f"shutdown: max runtime reached ({runtime_hours:.1f} hours)")
            return True
        
        # check idle time (only after processing at least one job)
        if self.jobs_processed > 0 and idle_minutes >= self.idle_shutdown_minutes:
            print(f"shutdown: idle for {idle_minutes:.1f} minutes")
            return True
        
        return False
    
    def _receive_job(self) -> Optional[Dict[str, Any]]:
        """receive next job from sqs queue"""
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # long polling
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return None
            
            message = messages[0]
            job_data = json.loads(message['Body'])
            
            return {
                'job': job_data,
                'receipt_handle': message['ReceiptHandle'],
                'message_id': message['MessageId']
            }
            
        except Exception as e:
            print(f"error receiving job: {e}")
            return None
    
    def _process_complete_job(self, job_message: Dict[str, Any]) -> bool:
        """process complete torque pipeline for a job"""
        job = job_message['job']
        receipt_handle = job_message['receipt_handle']
        
        self.current_job_id = job['job_id']
        job_id = self.current_job_id
        video_url = job['video_url']
        user_id = job['user_id']
        
        print(f"\\nprocessing job {job_id} for user {user_id}")
        print(f"video: {video_url}")
        
        try:
            # update job status to processing
            self._patch_job_status(job_id, "processing", {
                "worker_instance_id": self.instance_id,
                "started_at": datetime.now().isoformat()
            })
            
            # step 1: init_job
            print(f"step 1/6: init_job for {job_id}")
            if not self._run_pipeline_step("init_job", job_id, video_url):
                raise Exception("init_job failed")
            
            self._patch_job_status(job_id, "processing", {"stage_status": {"init_done": True}})
            
            # step 2: refine_mask (interactive - skip for now or use defaults)
            print(f"step 2/6: refine_mask for {job_id} (using defaults)")
            # for automated processing, we'll skip interactive refinement
            # or could implement auto-refinement based on initial sam2 results
            
            # step 3: run_sam2  
            print(f"step 3/6: run_sam2 for {job_id}")
            if not self._run_pipeline_step("run_sam2", job_id):
                raise Exception("run_sam2 failed")
            
            self._patch_job_status(job_id, "processing", {"stage_status": {"sam2_done": True}})
            
            # step 4: run_colmap
            print(f"step 4/6: run_colmap for {job_id}")
            if not self._run_pipeline_step("run_colmap", job_id):
                raise Exception("run_colmap failed")
            
            self._patch_job_status(job_id, "processing", {"stage_status": {"colmap_done": True}})
            
            # step 5: run_brush
            print(f"step 5/6: run_brush for {job_id}")
            if not self._run_pipeline_step("run_brush", job_id):
                raise Exception("run_brush failed")
            
            self._patch_job_status(job_id, "processing", {"stage_status": {"brush_done": True}})
            
            # step 6: cleanup_job
            print(f"step 6/6: cleanup_job for {job_id}")
            if not self._run_pipeline_step("cleanup_job", job_id):
                print("warning: cleanup_job failed, but job completed")
            
            # mark job as completed
            self._patch_job_status(job_id, "completed", {
                "completed_at": datetime.now().isoformat(),
                "worker_instance_id": self.instance_id
            })
            
            # acknowledge job completion in sqs
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            
            print(f"job {job_id} completed successfully!")
            return True
            
        except Exception as e:
            print(f"job {job_id} failed: {e}")
            
            # mark job as failed
            self._patch_job_status(job_id, "failed", {
                "error_message": str(e),
                "failed_at": datetime.now().isoformat(),
                "worker_instance_id": self.instance_id
            })
            
            # don't acknowledge - let job retry or go to dlq
            return False
    
    def _run_pipeline_step(self, step_name: str, job_id: str, video_url: str = None) -> bool:
        """run a specific pipeline step script"""
        try:
            # construct command based on step
            if step_name == "init_job":
                cmd = [
                    'python3', 'init_job.py',
                    '--job_id', job_id,
                    '--video_url', video_url,
                    '--bucket', self.bucket,
                    '--fastapi_url', self.fastapi_url,
                    '--fastapi_token', self.fastapi_token
                ]
            elif step_name == "run_sam2":
                cmd = [
                    'python3', 'run_sam2.py',
                    '--job_id', job_id,
                    '--bucket', self.bucket,
                    '--fastapi_url', self.fastapi_url,
                    '--fastapi_token', self.fastapi_token
                ]
            elif step_name == "run_colmap":
                cmd = [
                    'python3', 'run_colmap.py',
                    '--job_id', job_id,
                    '--bucket', self.bucket,
                    '--fastapi_url', self.fastapi_url,
                    '--fastapi_token', self.fastapi_token
                ]
            elif step_name == "run_brush":
                cmd = [
                    'python3', 'run_brush.py',
                    '--job_id', job_id,
                    '--bucket', self.bucket,
                    '--fastapi_url', self.fastapi_url,
                    '--fastapi_token', self.fastapi_token
                ]
            elif step_name == "cleanup_job":
                cmd = [
                    'python3', 'cleanup_job.py',
                    '--job_id', job_id,
                    '--bucket', self.bucket
                ]
            else:
                raise ValueError(f"unknown pipeline step: {step_name}")
            
            # run the command
            print(f"running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout per step
            )
            
            print(f"{step_name} completed successfully")
            if result.stdout:
                print(f"stdout: {result.stdout[-500:]}")  # last 500 chars
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"{step_name} failed with exit code {e.returncode}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            print(f"{step_name} timed out after 1 hour")
            return False
        except Exception as e:
            print(f"{step_name} error: {e}")
            return False
    
    def _patch_job_status(self, job_id: str, status: str, additional_data: Dict[str, Any] = None):
        """update job status via fastapi"""
        try:
            import requests
            
            data = {"status": status}
            if additional_data:
                data.update(additional_data)
            
            headers = {
                "Authorization": f"Bearer {self.fastapi_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.patch(
                f"{self.fastapi_url}/jobs/{job_id}/status",
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"updated job {job_id} status to {status}")
            else:
                print(f"failed to update job status: {response.status_code}")
                
        except Exception as e:
            print(f"error updating job status: {e}")
    
    def _shutdown_instance(self):
        """shutdown the ec2 instance"""
        print(f"\\nshutting down instance {self.instance_id}")
        print(f"session summary:")
        print(f"  runtime: {(time.time() - self.start_time) / 3600:.1f} hours")
        print(f"  jobs processed: {self.jobs_processed}")
        
        try:
            # give time for final status updates
            time.sleep(5)
            
            # shutdown instance
            self.ec2.stop_instances(InstanceIds=[self.instance_id])
            print("instance shutdown initiated")
            
        except Exception as e:
            print(f"error shutting down instance: {e}")
            # fallback to system shutdown
            os.system("sudo shutdown -h now")


def main():
    """main entry point"""
    print("torque smart worker starting...")
    
    # check required environment variables
    required_vars = ['TORQUE_SQS_QUEUE_URL', 'FASTAPI_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"error: missing environment variables: {missing_vars}")
        sys.exit(1)
    
    # start worker
    worker = SmartWorker()
    worker.run()


if __name__ == "__main__":
    main()