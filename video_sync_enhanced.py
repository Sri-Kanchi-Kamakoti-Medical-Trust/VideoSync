#!/usr/bin/env python3
"""
Enhanced Surgical Video Sync with Upload Functionality
Extended version with cloud storage and upload capabilities
"""

import os
import hashlib
import shutil
import logging
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_sync_enhanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedVideoSyncManager:
    """Enhanced video sync manager with upload capabilities"""
    
    def __init__(self, config_file: str = 'video_sync_config.json'):
        """Initialize the enhanced video sync manager"""
        self.config = self.load_config(config_file)
        self.source_dir = Path(self.config['source_directory'])
        self.destination_dir = Path(self.config['destination_directory'])
        self.hash_mapping_file = Path(self.config['hash_mapping_file'])
        self.supported_formats = self.config.get('supported_formats', ['.mp4', '.avi', '.mov', '.mkv'])
        
        # Upload settings
        self.upload_enabled = self.config.get('upload_settings', {}).get('enabled', False)
        self.upload_destination = self.config.get('upload_settings', {}).get('upload_destination', '')
        
        # Ensure directories exist
        self.destination_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing hash mappings
        self.hash_mappings = self.load_hash_mappings()
        
        # Initialize upload statistics
        self.upload_stats = {'uploaded': 0, 'failed': 0, 'skipped': 0}
    
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found. Using default configuration.")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            raise
    
    def get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            "source_directory": "./source_videos",
            "destination_directory": "./anonymized_videos",
            "hash_mapping_file": "hash_mappings.json",
            "supported_formats": [".mp4", ".avi", ".mov", ".mkv"],
            "hash_algorithm": "sha256",
            "salt": "surgical_video_salt_2025",
            "upload_settings": {
                "enabled": False,
                "upload_destination": "",
                "backup_original": True,
                "verify_upload": True,
                "max_retries": 3,
                "retry_delay": 60
            },
            "retention_settings": {
                "keep_source_files": True,
                "archive_after_days": 30,
                "cleanup_orphaned": True
            }
        }
    
    def load_hash_mappings(self) -> Dict[str, str]:
        """Load existing hash mappings from file"""
        if self.hash_mapping_file.exists():
            try:
                with open(self.hash_mapping_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid hash mapping file. Starting with empty mappings.")
        return {}
    
    def save_hash_mappings(self):
        """Save hash mappings to file"""
        with open(self.hash_mapping_file, 'w') as f:
            json.dump(self.hash_mappings, f, indent=2)
    
    def generate_anonymous_name(self, original_filename: str) -> str:
        """Generate anonymous filename using hash function"""
        file_ext = Path(original_filename).suffix
        hash_input = f"{original_filename}{self.config['salt']}"
        
        hash_algorithm = self.config.get('hash_algorithm', 'sha256')
        if hash_algorithm == 'md5':
            hash_obj = hashlib.md5(hash_input.encode())
        elif hash_algorithm == 'sha1':
            hash_obj = hashlib.sha1(hash_input.encode())
        elif hash_algorithm == 'sha256':
            hash_obj = hashlib.sha256(hash_input.encode())
        else:
            logger.warning(f"Unknown hash algorithm {hash_algorithm}, using SHA256")
            hash_obj = hashlib.sha256(hash_input.encode())
        
        anonymous_name = f"video_{hash_obj.hexdigest()[:16]}{file_ext}"
        return anonymous_name
    
    def get_video_files(self, directory: Path) -> List[Path]:
        """Get all video files from directory"""
        video_files = []
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                video_files.append(file_path)
        return video_files
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate hash of file contents for verification"""
        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def upload_file(self, file_path: Path, remote_path: str) -> bool:
        """Upload file to remote destination (placeholder for actual implementation)"""
        try:
            # This is a placeholder - implement actual upload logic based on your needs
            # Examples: AWS S3, Azure Blob Storage, SFTP, etc.
            
            upload_settings = self.config.get('upload_settings', {})
            max_retries = upload_settings.get('max_retries', 3)
            retry_delay = upload_settings.get('retry_delay', 60)
            
            for attempt in range(max_retries):
                try:
                    # Simulate upload process
                    logger.info(f"Uploading {file_path.name} to {remote_path} (attempt {attempt + 1})")
                    
                    # Example upload implementation (replace with actual code):
                    # For AWS S3:
                    # s3_client.upload_file(str(file_path), bucket_name, remote_path)
                    
                    # For SFTP:
                    # sftp_client.put(str(file_path), remote_path)
                    
                    # For Azure Blob:
                    # blob_client.upload_blob(open(file_path, 'rb'))
                    
                    # Simulate success
                    time.sleep(1)  # Simulate upload time
                    
                    # Verify upload if enabled
                    if upload_settings.get('verify_upload', True):
                        if self.verify_upload(file_path, remote_path):
                            logger.info(f"Successfully uploaded and verified: {file_path.name}")
                            return True
                        else:
                            logger.warning(f"Upload verification failed for: {file_path.name}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                continue
                    else:
                        logger.info(f"Successfully uploaded: {file_path.name}")
                        return True
                        
                except Exception as e:
                    logger.error(f"Upload attempt {attempt + 1} failed for {file_path.name}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        raise
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path.name}: {e}")
            return False
    
    def verify_upload(self, local_path: Path, remote_path: str) -> bool:
        """Verify that uploaded file matches local file"""
        try:
            # This is a placeholder for actual verification logic
            # In real implementation, you would:
            # 1. Calculate local file hash
            # 2. Download/check remote file hash
            # 3. Compare hashes or file sizes
            
            local_hash = self.calculate_file_hash(local_path)
            
            # Simulate remote verification
            # remote_hash = get_remote_file_hash(remote_path)
            # return local_hash == remote_hash
            
            logger.info(f"Verification simulated for {local_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Verification failed for {local_path.name}: {e}")
            return False
    
    def sync_and_anonymize_video(self, source_path: Path) -> Optional[Path]:
        """Sync, anonymize, and optionally upload a video file"""
        try:
            # Generate anonymous filename
            anonymous_filename = self.generate_anonymous_name(source_path.name)
            destination_path = self.destination_dir / anonymous_filename
            
            # Check if file already exists in destination
            if destination_path.exists():
                logger.info(f"Anonymized file already exists: {anonymous_filename}")
                
                # Check if upload is needed
                if self.upload_enabled and not self.is_uploaded(source_path):
                    self.handle_upload(destination_path, anonymous_filename)
                
                return destination_path
            
            # Copy file with new anonymous name
            logger.info(f"Processing: {source_path.name} -> {anonymous_filename}")
            shutil.copy2(source_path, destination_path)
            
            # Calculate file hash for integrity
            file_hash = self.calculate_file_hash(source_path)
            
            # Update hash mappings
            mapping_data = {
                'original_name': source_path.name,
                'anonymous_name': anonymous_filename,
                'processed_date': datetime.now().isoformat(),
                'file_size': source_path.stat().st_size,
                'file_hash': file_hash,
                'uploaded': False,
                'upload_date': None
            }
            
            self.hash_mappings[str(source_path)] = mapping_data
            
            # Handle upload if enabled
            if self.upload_enabled:
                upload_success = self.handle_upload(destination_path, anonymous_filename)
                if upload_success:
                    self.hash_mappings[str(source_path)]['uploaded'] = True
                    self.hash_mappings[str(source_path)]['upload_date'] = datetime.now().isoformat()
            
            logger.info(f"Successfully processed: {source_path.name}")
            return destination_path
            
        except Exception as e:
            logger.error(f"Error processing {source_path}: {e}")
            return None
    
    def handle_upload(self, file_path: Path, filename: str) -> bool:
        """Handle file upload with error handling"""
        try:
            remote_path = f"{self.upload_destination}/{filename}"
            success = self.upload_file(file_path, remote_path)
            
            if success:
                self.upload_stats['uploaded'] += 1
                logger.info(f"Upload successful: {filename}")
            else:
                self.upload_stats['failed'] += 1
                logger.error(f"Upload failed: {filename}")
            
            return success
            
        except Exception as e:
            self.upload_stats['failed'] += 1
            logger.error(f"Upload error for {filename}: {e}")
            return False
    
    def is_uploaded(self, source_path: Path) -> bool:
        """Check if file has been uploaded"""
        mapping = self.hash_mappings.get(str(source_path))
        return mapping and mapping.get('uploaded', False)
    
    def run_sync(self) -> Dict[str, int]:
        """Run the complete sync, anonymization, and upload process"""
        logger.info("Starting enhanced video sync process")
        
        # Check if source directory exists
        if not self.source_dir.exists():
            logger.error(f"Source directory does not exist: {self.source_dir}")
            return {'processed': 0, 'skipped': 0, 'errors': 0, 'uploaded': 0}
        
        # Get all video files from source directory
        video_files = self.get_video_files(self.source_dir)
        logger.info(f"Found {len(video_files)} video files in source directory")
        
        stats = {'processed': 0, 'skipped': 0, 'errors': 0}
        
        for video_path in video_files:
            if str(video_path) in self.hash_mappings:
                logger.info(f"Skipping already processed file: {video_path.name}")
                stats['skipped'] += 1
                
                # Check if upload is needed for existing files
                if self.upload_enabled and not self.is_uploaded(video_path):
                    anonymous_name = self.hash_mappings[str(video_path)]['anonymous_name']
                    destination_path = self.destination_dir / anonymous_name
                    if destination_path.exists():
                        self.handle_upload(destination_path, anonymous_name)
                
                continue
            
            result = self.sync_and_anonymize_video(video_path)
            if result:
                stats['processed'] += 1
            else:
                stats['errors'] += 1
        
        # Save updated hash mappings
        self.save_hash_mappings()
        
        # Add upload statistics to results
        stats.update(self.upload_stats)
        
        logger.info(f"Enhanced sync completed. Processed: {stats['processed']}, "
                   f"Skipped: {stats['skipped']}, Errors: {stats['errors']}, "
                   f"Uploaded: {stats['uploaded']}")
        
        return stats
    
    def cleanup_old_files(self, days: int = 30):
        """Clean up files older than specified days"""
        logger.info(f"Cleaning up files older than {days} days")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleanup_count = 0
        
        for source_path_str, mapping in list(self.hash_mappings.items()):
            processed_date = datetime.fromisoformat(mapping['processed_date'])
            
            if processed_date < cutoff_date:
                # Check retention settings
                retention_settings = self.config.get('retention_settings', {})
                
                if not retention_settings.get('keep_source_files', True):
                    source_path = Path(source_path_str)
                    if source_path.exists():
                        source_path.unlink()
                        logger.info(f"Removed old source file: {source_path.name}")
                        cleanup_count += 1
        
        logger.info(f"Cleaned up {cleanup_count} old files")
        return cleanup_count


def main():
    """Main function for enhanced cronjob execution"""
    parser = argparse.ArgumentParser(description='Enhanced Surgical Video Sync with Upload')
    parser.add_argument('--config', default='video_sync_config.json',
                       help='Configuration file path')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up orphaned files')
    parser.add_argument('--cleanup-old', type=int, metavar='DAYS',
                       help='Clean up files older than specified days')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--upload-only', action='store_true',
                       help='Only upload already processed files')
    
    args = parser.parse_args()
    
    try:
        # Initialize enhanced video sync manager
        sync_manager = EnhancedVideoSyncManager(args.config)
        
        if args.cleanup:
            sync_manager.cleanup_orphaned_files()
        
        if args.cleanup_old:
            sync_manager.cleanup_old_files(args.cleanup_old)
        
        if args.upload_only:
            # Upload only mode - upload existing anonymized files
            logger.info("Running in upload-only mode")
            for source_path_str, mapping in sync_manager.hash_mappings.items():
                if not mapping.get('uploaded', False):
                    anonymous_name = mapping['anonymous_name']
                    destination_path = sync_manager.destination_dir / anonymous_name
                    if destination_path.exists():
                        sync_manager.handle_upload(destination_path, anonymous_name)
        elif not args.dry_run:
            # Run the full sync process
            stats = sync_manager.run_sync()
            logger.info(f"Job completed successfully. Statistics: {stats}")
        else:
            logger.info("Dry run mode - no files will be processed")
            video_files = sync_manager.get_video_files(sync_manager.source_dir)
            logger.info(f"Would process {len(video_files)} video files")
    
    except Exception as e:
        logger.error(f"Enhanced cronjob failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
