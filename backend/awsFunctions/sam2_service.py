import os
import cv2
import numpy as np
import boto3
from ultralytics import SAM
from ultralytics.models.sam import SAM2VideoPredictor
from typing import Optional, List, Tuple

class Sam2Service:
    
    def __init__(self):
        # Model paths
        sam2_model_path = os.path.expanduser("~/torque/models/sam2.1_b.pt")

        # Image + Video SAM
        self.sam_img = SAM(sam2_model_path)
        self.sam_video = SAM2VideoPredictor(overrides=dict(
            conf=0.25,
            task="segment",
            mode="predict",
            imgsz=1024,
            model=sam2_model_path
            )
        )
        self.s3 = boto3.client('s3')
    
    # Mask ARRAY generators

    def img_mask(self, image_path: str, output_dir: str = None, points: Optional[List[List[int]]] = None, labels: Optional[List[int]] = None) -> np.ndarray:
        """
        predict with SAM single-frame
        """
        # SAM2 image predictor usage - correct format
        if points and labels:
            result = self.sam_img(image_path, points=points, labels=labels)
        else:
            result = self.sam_img(image_path)
        # Handle SAM2 result format - it returns a list of Results objects
        if isinstance(result, list) and len(result) > 0:
            result = result[0]  # Take the first (and usually only) result
        
        if not hasattr(result, 'masks') or result.masks is None:
            raise ValueError(f"SAM2 returned no masks for {image_path}")
            
        masks_arr = result.masks.data.cpu().numpy()  # (N,H,W)
        
        # Save masks as npz if output_dir is provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            # Convert to binary masks (0s and 1s) for consistency with video_mask
            binary_masks = (masks_arr > 0).astype(np.uint8)
            np.savez_compressed(os.path.join(output_dir, "img_masks.npz"), binary_masks)
            print(f"Saved masks to: {output_dir}/img_masks.npz")
        
        output_path = os.path.join(f"{output_dir}/img_masks.npz")
        if not (points and labels):
            merged = np.any(masks_arr, axis=0).astype(np.uint8) * 255
            return merged
        return output_path
    
    def video_mask(self, video_path: str,job_id: str, points: Optional[List[List[int]]] = None, labels: Optional[List[int]] = None) -> np.ndarray:
        """
        predict with SAM2 video
        """
        # SAM2 video predictor usage - format points and labels correctly
        if points and labels:
            results = self.sam_video(video_path, points=points, labels=labels)
        else:
            results = self.sam_video(video_path)

        output_dir = os.path.expanduser(f"~/torque/jobs/{job_id}")
        masks_dir = os.path.join(output_dir, "masks")
        os.makedirs(masks_dir, exist_ok=True)
        
        all_masks = []
        for i, result in enumerate(results):
            if result.masks is not None:
                masks = result.masks.data.cpu().numpy() # (N, H, W)
                
                merged_mask = np.any(masks, axis=0).astype(np.uint8)  # (H, W)
                all_masks.append(merged_mask)

        # Save full 3D mask array: (num_frames, H, W)
        mask_array = np.stack(all_masks)
        output_path = os.path.join(masks_dir, "video_masks.npz")
        np.savez_compressed(output_path, mask_array)

        print(f"Done. Saved masks to: {output_path}")
        return output_path

    # Mask ARRAY -> IMAGE

    def overlay_outline(self, image_path: str, mask_path: str, out_dir: str, color: Tuple[int, int, int] = (255,0,0), thickness: float = 0.2, alpha: float = 0.3):
        """
        Overlay mask outline(s) on an image and save to output directory.
        Use Case: Finetuning mask outline on 1st image.
        Should support 1 or more masks.
        """
        # Load mask from file
        mask_data = np.load(mask_path)
        
        # Extract mask array from npz file (usually stored as 'arr_0')
        if isinstance(mask_data, np.lib.npyio.NpzFile):
            # Get the first (and likely only) array from the npz file
            key = list(mask_data.keys())[0]  # Usually 'arr_0'
            masks = mask_data[key]
        else:
            masks = mask_data
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        overlay = image.copy()
        
        # Handle different mask formats
        if masks.ndim == 2:
            # If 2D array (single mask), convert to 3D for uniform processing
            masks = masks[np.newaxis, ...]
        
        # Process each mask
        for i, mask in enumerate(masks):
            # Mask contains 0 and 1 values, convert to 0-255 for contour detection
            mask_binary = (mask * 255).astype(np.uint8)
            
            # edge map
            contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # translucent fill (use original mask for boolean indexing)
            colored = np.zeros_like(image)
            colored[mask > 0] = color
            cv2.addWeighted(colored, alpha, overlay, 1 - alpha, 0, overlay)
            
            # draw outline - convert thickness to int for cv2.drawContours
            thickness_int = max(1, int(thickness * 10)) 
            cv2.drawContours(overlay, contours, -1, color, thickness_int)
        
        # Create output directory if it doesn't exist
        os.makedirs(out_dir, exist_ok=True)
        
        # Generate output filename
        image_filename = os.path.basename(image_path)
        name, ext = os.path.splitext(image_filename)
        output_filename = f"{name}_outlined{ext}"
        output_path = os.path.join(out_dir, output_filename)
        
        # Save the overlaid image
        cv2.imwrite(output_path, overlay)
        print(f"Saved outlined image to: {output_path}")
        
        return output_path
    
    def create_rgba_mask(self, image_path: str, mask: np.ndarray, output_path: str):
        """
        Create an RGBA PNG using a single mask as the alpha channel.
        
        Args:
            image_path: Path to the input image
            mask: 2D numpy array mask (H, W) with 0s and 1s
            output_path: Path where the RGBA PNG will be saved
        
        Returns:
            str: Path to the saved RGBA PNG file
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Ensure mask dimensions match image dimensions
        img_height, img_width = image_rgb.shape[:2]
        if mask.shape != (img_height, img_width):
            # Resize mask to match image dimensions
            mask = cv2.resize(mask.astype(np.float32), (img_width, img_height), interpolation=cv2.INTER_NEAREST)
        
        # Convert mask to 0-255 range for alpha channel
        alpha_channel = (mask > 0).astype(np.uint8) * 255
        
        # Create RGBA image by adding alpha channel
        rgba_image = np.dstack((image_rgb, alpha_channel))
        
        # Output directory is already created by batch function - no need to create for each image
    
        # Save as PNG
        from PIL import Image
        pil_image = Image.fromarray(rgba_image, 'RGBA')
        pil_image.save(output_path, 'PNG')
        
        print(f"Saved RGBA image to: {output_path}")
        
        return output_path
    
    def batch_create_rgba_masks(self, job_id: str, upload_to_s3: bool = True, s3_bucket: str = None, s3_prefix: str = None):
        """
        Create RGBA masks for all images in a job directory using video_masks.npz.
        Each mask in the array corresponds to each image in sequential order.
        
        Returns:
            dict: Summary of processing results
        """
        # Define paths
        images_dir = os.path.expanduser(f"~/torque/jobs/{job_id}/images")
        output_dir = os.path.expanduser(f"~/torque/jobs/{job_id}/rgba")
        video_masks_path = os.path.expanduser(f"~/torque/jobs/{job_id}/masks/video_masks.npz")
        
        # Validate inputs
        if not os.path.exists(images_dir):
            raise ValueError(f"Images directory not found: {images_dir}")
        if not os.path.exists(video_masks_path):
            raise ValueError(f"Video masks file not found: {video_masks_path}")
        
        if upload_to_s3 and not s3_bucket:
            raise ValueError("s3_bucket is required when upload_to_s3=True")
        
        # Load video masks array (num_frames, H, W)
        mask_data = np.load(video_masks_path)
        if isinstance(mask_data, np.lib.npyio.NpzFile):
            key = list(mask_data.keys())[0]  # Usually 'arr_0'
            video_masks = mask_data[key]
        else:
            video_masks = mask_data
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get all image files (already sorted by init_job as 0001.png, 0002.png, etc.)
        image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')) and not f.endswith('_video.mp4')]
        image_files.sort()  # Sequential ordering maintained
        
        print(f"Processing {len(image_files)} images for job {job_id}")
        print(f"Video masks shape: {video_masks.shape}")
        
        # validate len(masks) == len(images)
        if len(image_files) != video_masks.shape[0]:
            raise ValueError(f"Mismatch: {len(image_files)} images but {video_masks.shape[0]} masks")
        
        results = {
            'processed': 0,
            'errors': 0,
            'uploaded': 0,
            'output_files': []
        }
        
        for i, image_filename in enumerate(image_files):
            try:
                # Paths - maintain sequential naming convention
                image_path = os.path.join(images_dir, image_filename)
                name, _ = os.path.splitext(image_filename)
                output_filename = f"{name}.png"  # Keep same numbering: 0001.png -> 0001.png
                output_path = os.path.join(output_dir, output_filename)
                
                # Get the corresponding mask for this image
                mask_for_image = video_masks[i]  # Shape: (H, W)
                
                # Create RGBA mask using the specific mask for this image
                self.create_rgba_mask(image_path, mask_for_image, output_path)
                results['processed'] += 1
                results['output_files'].append(output_path)
                
                # Upload to S3 if requested
                if upload_to_s3:
                    try:
                        s3_key = f"{s3_prefix}/{output_filename}" if s3_prefix else output_filename
                        self.s3.upload_file(output_path, s3_bucket, s3_key)
                        print(f"Uploaded to S3: s3://{s3_bucket}/{s3_key}")
                        results['uploaded'] += 1
                    except Exception as e:
                        print(f"ERROR: S3 upload failed for {output_filename}: {e}")
                
            except Exception as e:
                print(f"ERROR: Error processing {image_filename}: {e}")
                results['errors'] += 1
                continue
        
        print(f"Batch processing complete:")
        print(f"   Processed: {results['processed']}/{len(image_files)}")
        print(f"   Errors: {results['errors']}")
        print(f"   Uploaded: {results['uploaded']}")
        print(f"   Output directory: {output_dir}")
        
        return results