#!/usr/bin/env python3
"""
Surgical Video Sync and Anonymization Cronjob with Azure Blob Storage
This script performs two main functions:
1. Sync and upload new surgical videos from a source directory to Azure Blob Storage
2. Anonymize video names using hash functions for privacy protection
"""

import os
import re
import hashlib
import shutil
import logging
import json
import time
from datetime import datetime
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Tuple
import argparse
import platform

# Import case sheet detection functions
from detect_case_sheet import compute_laplacian_variance_from_video, detect_case_sheet, clip_video

# Azure Blob Storage imports
try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    from azure.core.exceptions import AzureError, ResourceNotFoundError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log Azure availability
if not AZURE_AVAILABLE:
    logger.warning("Azure Storage Blob library not installed. Install with: pip install azure-storage-blob")

class VideoSyncManager:
    """Manages surgical video synchronization and anonymization with Azure Blob Storage"""
    
    def __init__(self, config_file: str = 'video_sync_config.json'):
        """Initialize the video sync manager with configuration"""
        self.config = self.load_config(config_file)
        self.source_dir = self._normalize_path(self.config['source_directory'])
        self.destination_dir = self._normalize_path(self.config['destination_directory'])
        self.hash_mapping_file = self._normalize_path(self.config['hash_mapping_file'])
        self.supported_formats = self.config.get('supported_formats', ['.mp4', '.avi', '.mov', '.mkv'])
        
        # Ensure directories exist
        self._ensure_directory_exists(self.destination_dir)
        
        # Load existing hash mappings
        self.hash_mappings = self.load_hash_mappings()
        
        # Initialize Azure Blob Storage client
        self.blob_service_client = None
        self.container_client = None
        self.azure_enabled = False
        self._initialize_azure_client()
    
    def _normalize_path(self, path_str: str) -> Path:
        """Normalize path string to handle UNC paths properly"""
        if not path_str:
            return Path('.')
        
        # Handle UNC paths on Windows
        if platform.system() == 'Windows' and path_str.startswith(('\\\\', '//')):
            # Convert forward slashes to backslashes for UNC paths
            path_str = path_str.replace('/', '\\')
            
            # For UNC paths, we need to use os.path operations initially
            # then convert to Path for consistency
            if os.path.exists(path_str):
                return Path(path_str)
            else:
                # Create Path object even if path doesn't exist yet
                return Path(path_str)
        
        return Path(path_str)
    
    def _ensure_directory_exists(self, directory: Path) -> bool:
        """Ensure directory exists, handling UNC paths"""
        try:
            if platform.system() == 'Windows' and self._is_unc_path(directory):
                # For UNC paths, use os.makedirs which handles network paths better
                os.makedirs(str(directory), exist_ok=True)
            else:
                directory.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False
    
    def _is_unc_path(self, path: Path) -> bool:
        """Check if path is a UNC path"""
        path_str = str(path)
        return platform.system() == 'Windows' and path_str.startswith('\\\\')
    
    def _safe_path_exists(self, path: Path) -> bool:
        """Safely check if path exists, handling network timeouts"""
        try:
            if self._is_unc_path(path):
                # For UNC paths, use os.path.exists which may be more reliable
                return os.path.exists(str(path))
            return path.exists()
        except (OSError, TimeoutError) as e:
            logger.warning(f"Error checking path existence {path}: {e}")
            return False
    
    def _safe_path_stat(self, path: Path) -> Optional[os.stat_result]:
        """Safely get path stats, handling network issues"""
        try:
            if self._is_unc_path(path):
                return os.stat(str(path))
            return path.stat()
        except (OSError, TimeoutError) as e:
            logger.warning(f"Error getting path stats {path}: {e}")
            return None

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
            "case_sheet_detection": {
                "enabled": True,
                "threshold": 12,
                "window_size": 15,
                "temp_frames_dir": "./temp_frames",
                "max_frames": 1000
            },
            "azure_blob_settings": {
                "enabled": False,
                "connection_string": "",
                "container_name": "surgical-videos-anonymized",
                "blob_prefix": "videos/",
                "verify_upload": True,
                "max_retries": 3,
                "retry_delay": 30
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
        # Extract file extension
        file_ext = Path(original_filename).suffix

        #extract 6 digit MRD for anonymization
        # If MRD is present, extract it
        mrd_match = re.search(r'\b\d{6}\b', original_filename)
        if mrd_match:
            mrd = mrd_match.group(0)
            logger.info(f"Extracted MRD: {mrd} from filename: {original_filename}")
        else:
            mrd = None
            logger.info(f"No MRD found in filename: {original_filename}")

        # If MRD is found, use it else use the original filename
        if mrd:
            hash_input = f"{mrd}{self.config['salt']}"
        else:
            hash_input = f"{original_filename}{self.config['salt']}"
        
        # Generate hash based on configured algorithm
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
        
        # Create anonymous filename
        anonymous_name = f"video_{hash_obj.hexdigest()[:16]}{file_ext}"
        return anonymous_name
    
    def get_video_files(self, directory: Path) -> List[Path]:
        """Get all video files from directory, handling UNC paths"""
        video_files = []
        try:
            if self._is_unc_path(directory):
                # For UNC paths, use os.walk which may be more reliable
                for root, dirs, files in os.walk(str(directory)):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in self.supported_formats:
                            video_files.append(file_path)
            else:
                for file_path in directory.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                        video_files.append(file_path)
        except (OSError, PermissionError) as e:
            logger.error(f"Error accessing directory {directory}: {e}")
        
        return video_files
    
    def is_video_processed(self, video_path: Path) -> bool:
        """Check if video has already been processed"""
        # Normalize path for comparison
        normalized_path = str(self._normalize_path(str(video_path)))
        return normalized_path in self.hash_mappings
    
    def sync_and_anonymize_video(self, source_path: Path) -> Optional[Path]:
        """Sync and anonymize a single video file, then upload to Azure Blob Storage"""
        try:
            # Normalize source path
            source_path = self._normalize_path(str(source_path))
            
            # Check if source file exists
            if not self._safe_path_exists(source_path):
                logger.error(f"Source file does not exist: {source_path}")
                return None
            
            # Calculate relative path from source directory
            try:
                relative_path = source_path.relative_to(self.source_dir)
            except ValueError:
                # If relative_to fails (common with UNC paths), use alternative method
                source_parts = Path(str(source_path)).parts
                source_dir_parts = Path(str(self.source_dir)).parts
                
                # Find common prefix and create relative path
                if len(source_parts) > len(source_dir_parts):
                    relative_parts = source_parts[len(source_dir_parts):]
                    relative_path = Path(*relative_parts)
                else:
                    relative_path = Path(source_path.name)
            
            relative_dir = relative_path.parent
            
            # Generate anonymous filename
            anonymous_filename = self.generate_anonymous_name(source_path.name)
            
            # Create destination path maintaining folder structure
            destination_dir = self.destination_dir / relative_dir
            destination_path = destination_dir / anonymous_filename
            
            # Ensure destination subdirectory exists
            if not self._ensure_directory_exists(destination_dir):
                logger.error(f"Failed to create destination directory: {destination_dir}")
                return None
            
            # Check if file already exists in destination
            if self._safe_path_exists(destination_path):
                logger.info(f"Anonymized file already exists: {relative_dir / anonymous_filename}")
                
                # Check if upload to Azure is needed
                if self.azure_enabled and not self.is_blob_uploaded(anonymous_filename, relative_dir):
                    upload_success = self.upload_to_azure_blob(destination_path, anonymous_filename, relative_dir)
                    if upload_success:
                        # Update mapping to reflect upload status
                        normalized_source_path = str(source_path)
                        if normalized_source_path in self.hash_mappings:
                            self.hash_mappings[normalized_source_path]['azure_uploaded'] = True
                            self.hash_mappings[normalized_source_path]['azure_upload_date'] = datetime.now().isoformat()
                
                return destination_path
            
            # Case sheet detection for anonymization clipping
            clip_start_time = None
            case_sheet_settings = self.config.get('case_sheet_detection', {})
            
            if case_sheet_settings.get('enabled', True):
                logger.info(f"Performing case sheet detection for: {source_path.name}")
                
                try:
                    # Extract frames from video
                    variances = compute_laplacian_variance_from_video(
                        source_path,
                        max_frames=case_sheet_settings.get('max_frames', 1000)
                    )

                    # Detect case sheet using imported function
                    window_start, window_end = detect_case_sheet(variances)

                    if window_end is not None:
                        clip_start_time = window_end  # Start after case sheet ends
                        logger.info(f"Case sheet detected - will clip video from {clip_start_time} seconds")
                    else:
                        logger.info("No case sheet detected - no clipping needed")
  
                except Exception as e:
                    logger.warning(f"Case sheet detection failed for {source_path.name}: {e}")
                    
            
            # Process video (clip if needed, otherwise copy)
            if clip_start_time is not None:
                logger.info(f"Clipping and processing: {relative_path} -> {relative_dir / anonymous_filename}")
                success = clip_video(source_path, destination_path, clip_start_time)
                if not success:
                    logger.warning(f"Clipping failed for {source_path.name}, falling back to full copy")
                    self._safe_copy_file(source_path, destination_path)
            else:
                logger.info(f"Processing: {relative_path} -> {relative_dir / anonymous_filename}")
                self._safe_copy_file(source_path, destination_path)
            
            # Get file size safely
            file_stat = self._safe_path_stat(source_path)
            file_size = file_stat.st_size if file_stat else 0
            
            # Update hash mappings
            mapping_data = {
                'original_name': source_path.name,
                'anonymous_name': anonymous_filename,
                'relative_path': str(relative_path),
                'relative_dir': str(relative_dir),
                'processed_date': datetime.now().isoformat(),
                'file_size': file_size,
                'clipped_start_time': clip_start_time,
                'anonymization_method': 'clipped' if clip_start_time is not None else 'copied',
                'azure_uploaded': False,
                'azure_upload_date': None
            }
            
            # Upload to Azure Blob Storage if enabled
            if self.azure_enabled:
                upload_success = self.upload_to_azure_blob(destination_path, anonymous_filename, relative_dir)
                if upload_success:
                    mapping_data['azure_uploaded'] = True
                    mapping_data['azure_upload_date'] = datetime.now().isoformat()
                    logger.info(f"Successfully uploaded {relative_dir / anonymous_filename} to Azure Blob Storage")
                else:
                    logger.warning(f"Failed to upload {relative_dir / anonymous_filename} to Azure Blob Storage")
            
            self.hash_mappings[str(source_path)] = mapping_data
            
            logger.info(f"Successfully processed: {relative_path}")
            return destination_path
            
        except Exception as e:
            logger.error(f"Error processing {source_path}: {e}")
            return None
    
    def _safe_copy_file(self, source: Path, destination: Path) -> bool:
        """Safely copy file, handling UNC paths and network issues"""
        try:
            if self._is_unc_path(source) or self._is_unc_path(destination):
                # For UNC paths, use shutil.copy2 with string paths
                shutil.copy2(str(source), str(destination))
            else:
                shutil.copy2(source, destination)
            return True
        except (OSError, PermissionError, TimeoutError) as e:
            logger.error(f"Error copying file from {source} to {destination}: {e}")
            return False
    
    def run_sync(self) -> Dict[str, int]:
        """Run the complete sync and anonymization process with Azure upload"""
        logger.info("Starting video sync and anonymization process with Azure Blob Storage")
        
        # Check if source directory exists
        if not self._safe_path_exists(self.source_dir):
            logger.error(f"Source directory does not exist or is not accessible: {self.source_dir}")
            return {'processed': 0, 'skipped': 0, 'errors': 0, 'azure_uploaded': 0, 'azure_failed': 0}
        
        # Get all video files from source directory
        video_files = self.get_video_files(self.source_dir)
        logger.info(f"Found {len(video_files)} video files in source directory")
        
        if self.azure_enabled:
            logger.info("Azure Blob Storage is enabled and configured")
        else:
            logger.warning("Azure Blob Storage is not available or not configured")
        
        stats = {'processed': 0, 'skipped': 0, 'errors': 0, 'azure_uploaded': 0, 'azure_failed': 0}
        
        for video_path in video_files:
            if self.is_video_processed(video_path):
                logger.info(f"Skipping already processed file: {video_path.name}")
                stats['skipped'] += 1
                continue

            result = self.sync_and_anonymize_video(video_path)
            if result:
                stats['processed'] += 1
                # Check if Azure upload was successful
                mapping = self.hash_mappings.get(str(video_path), {})
                if mapping.get('azure_uploaded', False):
                    stats['azure_uploaded'] += 1
                else:
                    stats['azure_failed'] += 1
            else:
                stats['errors'] += 1
        
        # Save updated hash mappings
        self.save_hash_mappings()
        
        logger.info(f"Sync completed. Processed: {stats['processed']}, "
                   f"Skipped: {stats['skipped']}, Errors: {stats['errors']}, "
                   f"Azure Uploaded: {stats['azure_uploaded']}, Azure Failed: {stats['azure_failed']}")
        
        return stats
    
    def get_original_filename(self, anonymous_filename: str) -> Optional[str]:
        """Retrieve original filename from anonymous filename"""
        for mapping in self.hash_mappings.values():
            if mapping['anonymous_name'] == anonymous_filename:
                return mapping['original_name']
        return None
    
    def cleanup_orphaned_files(self):
        """Remove anonymized files whose source files no longer exist"""
        logger.info("Checking for orphaned anonymized files")
        
        orphaned_count = 0
        for source_path_str, mapping in list(self.hash_mappings.items()):
            source_path = self._normalize_path(source_path_str)
            if not self._safe_path_exists(source_path):
                # Build the anonymized file path with folder structure
                relative_dir = Path(mapping.get('relative_dir', '.'))
                anonymous_filename = mapping['anonymous_name']
                
                if str(relative_dir) != '.':
                    anonymous_path = self.destination_dir / relative_dir / anonymous_filename
                else:
                    anonymous_path = self.destination_dir / anonymous_filename
                
                if self._safe_path_exists(anonymous_path):
                    try:
                        anonymous_path.unlink()
                        logger.info(f"Removed orphaned file: {relative_dir / anonymous_filename}")
                        orphaned_count += 1
                    except (OSError, PermissionError) as e:
                        logger.error(f"Failed to remove orphaned file {anonymous_path}: {e}")
                
                # Remove from mappings
                del self.hash_mappings[source_path_str]
        
        if orphaned_count > 0:
            self.save_hash_mappings()
            logger.info(f"Cleaned up {orphaned_count} orphaned files")
        else:
            logger.info("No orphaned files found")
    
    def _initialize_azure_client(self):
        """Initialize Azure Blob Storage client"""
        try:
            if not AZURE_AVAILABLE:
                logger.warning("Azure Blob Storage not available. Upload functionality disabled.")
                return
            
            azure_settings = self.config.get('azure_blob_settings', {})
            if not azure_settings.get('enabled', False):
                logger.info("Azure Blob Storage disabled in configuration")
                return
            
            connection_string = azure_settings.get('connection_string')
            if not connection_string:
                logger.error("Azure connection string not provided in configuration")
                return
            
            container_name = azure_settings.get('container_name', 'surgical-videos')
            
            # Initialize Azure Blob Service Client
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            self.container_client = self.blob_service_client.get_container_client(container_name)
            
            # Ensure container exists
            try:
                self.container_client.get_container_properties()
                logger.info(f"Connected to Azure Blob container: {container_name}")
            except ResourceNotFoundError:
                logger.info(f"Container {container_name} does not exist. Creating...")
                self.container_client.create_container()
                logger.info(f"Created Azure Blob container: {container_name}")
            
            self.azure_enabled = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage client: {e}")
            self.azure_enabled = False
    
    def upload_to_azure_blob(self, file_path: Path, blob_name: str, relative_dir: Path = None) -> bool:
        """Upload file to Azure Blob Storage maintaining folder structure"""
        if not self.azure_enabled:
            logger.warning("Azure Blob Storage not enabled, skipping upload")
            return False
        
        try:
            azure_settings = self.config.get('azure_blob_settings', {})
            blob_prefix = azure_settings.get('blob_prefix', 'videos/')
            
            # Build full blob path maintaining folder structure
            if relative_dir and str(relative_dir) != '.':
                # Convert Windows path separators to forward slashes for blob storage
                relative_dir_str = str(relative_dir).replace('\\', '/')
                full_blob_name = f"{blob_prefix}{relative_dir_str}/{blob_name}"
            else:
                full_blob_name = f"{blob_prefix}{blob_name}"
            
            logger.info(f"Uploading {file_path.name} to Azure Blob: {full_blob_name}")
            
            # Upload file with retry logic and custom block size
            max_retries = azure_settings.get('max_retries', 3)
            retry_delay = azure_settings.get('retry_delay', 30)
            
            for attempt in range(max_retries):
                try:
                    with open(file_path, 'rb') as data:
                        blob_client = self.container_client.get_blob_client(full_blob_name)
                        blob_client.upload_blob(
                            data, 
                            overwrite=True,
                            max_concurrency=4,
                            blob_type="BlockBlob",
                        )
                    
                    logger.info(f"Successfully uploaded {file_path.name} to Azure Blob Storage")
                    
                    # Verify upload if enabled
                    if azure_settings.get('verify_upload', True):
                        if self.verify_azure_blob_upload(file_path, full_blob_name):
                            return True
                        else:
                            logger.warning(f"Upload verification failed for {file_path.name}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                continue
                    else:
                        return True
                        
                except AzureError as e:
                    logger.error(f"Azure upload attempt {attempt + 1} failed for {file_path.name}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        raise
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path.name} to Azure Blob Storage: {e}")
            return False
    
    def verify_azure_blob_upload(self, local_file_path: Path, blob_name: str) -> bool:
        """Verify that uploaded blob matches local file"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_properties = blob_client.get_blob_properties()
            
            # Compare file sizes
            local_size = local_file_path.stat().st_size
            blob_size = blob_properties.size
            
            if local_size != blob_size:
                logger.error(f"Size mismatch: local={local_size}, blob={blob_size}")
                return False
            
            logger.info(f"Upload verification successful for {local_file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Upload verification failed for {local_file_path.name}: {e}")
            return False
    
    def list_azure_blobs(self, prefix: str = None) -> List[str]:
        """List blobs in Azure container"""
        if not self.azure_enabled:
            return []
        
        try:
            blob_list = []
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                blob_list.append(blob.name)
            return blob_list
            
        except Exception as e:
            logger.error(f"Failed to list Azure blobs: {e}")
            return []
    
    def is_blob_uploaded(self, blob_name: str, relative_dir: Path = None) -> bool:
        """Check if blob already exists in Azure Storage"""
        if not self.azure_enabled:
            return False
        
        try:
            azure_settings = self.config.get('azure_blob_settings', {})
            blob_prefix = azure_settings.get('blob_prefix', 'videos/')
            
            # Build full blob path maintaining folder structure
            if relative_dir and str(relative_dir) != '.':
                relative_dir_str = str(relative_dir).replace('\\', '/')
                full_blob_name = f"{blob_prefix}{relative_dir_str}/{blob_name}"
            else:
                full_blob_name = f"{blob_prefix}{blob_name}"
            
            blob_client = self.container_client.get_blob_client(full_blob_name)
            blob_client.get_blob_properties()
            return True
            
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking blob existence: {e}")
            return False

        
def main():
    """Main function for cronjob execution"""
    parser = argparse.ArgumentParser(description='Surgical Video Sync and Anonymization with Azure Blob Storage')
    parser.add_argument('--config', default='video_sync_config.json',
                       help='Configuration file path')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up orphaned files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--azure-only', action='store_true',
                       help='Only upload to Azure Blob Storage (skip local processing)')
    parser.add_argument('--list-blobs', action='store_true',
                       help='List blobs in Azure container')
    
    args = parser.parse_args()
    
    try:
        # Initialize video sync manager
        sync_manager = VideoSyncManager(args.config)
        
        if args.list_blobs:
            if sync_manager.azure_enabled:
                azure_settings = sync_manager.config.get('azure_blob_settings', {})
                blob_prefix = azure_settings.get('blob_prefix', 'videos/')
                blobs = sync_manager.list_azure_blobs(blob_prefix)
                logger.info(f"Found {len(blobs)} blobs in Azure container:")
                for blob in blobs:
                    logger.info(f"  - {blob}")
            else:
                logger.error("Azure Blob Storage is not enabled or configured")
            return
        
        if args.cleanup:
            sync_manager.cleanup_orphaned_files()
        
        if args.azure_only:
            # Azure-only upload mode
            if not sync_manager.azure_enabled:
                logger.error("Azure Blob Storage is not enabled or configured")
                return
            
            logger.info("Running in Azure-only upload mode")
            stats = {'azure_uploaded': 0, 'azure_failed': 0, 'skipped': 0}
            
            for source_path_str, mapping in sync_manager.hash_mappings.items():
                if not mapping.get('azure_uploaded', False):
                    anonymous_filename = mapping.get('anonymous_name')
                    relative_dir = Path(mapping.get('relative_dir', '.'))
                    
                    if anonymous_filename:
                        if str(relative_dir) != '.':
                            destination_path = sync_manager.destination_dir / relative_dir / anonymous_filename
                        else:
                            destination_path = sync_manager.destination_dir / anonymous_filename
                        
                        if sync_manager._safe_path_exists(destination_path):
                            if not sync_manager.is_blob_uploaded(anonymous_filename, relative_dir):
                                upload_success = sync_manager.upload_to_azure_blob(destination_path, anonymous_filename, relative_dir)
                                if upload_success:
                                    sync_manager.hash_mappings[source_path_str]['azure_uploaded'] = True
                                    sync_manager.hash_mappings[source_path_str]['azure_upload_date'] = datetime.now().isoformat()
                                    stats['azure_uploaded'] += 1
                                else:
                                    stats['azure_failed'] += 1
                            else:
                                logger.info(f"Blob already exists: {anonymous_filename}")
                                stats['skipped'] += 1
                        else:
                            logger.warning(f"Local file not found: {destination_path}")
                            stats['azure_failed'] += 1
            
            sync_manager.save_hash_mappings()
            logger.info(f"Azure upload completed. Uploaded: {stats['azure_uploaded']}, "
                       f"Failed: {stats['azure_failed']}, Skipped: {stats['skipped']}")
            
        elif not args.dry_run:
            # Run the sync process
            stats = sync_manager.run_sync()
            
            # Log summary
            logger.info(f"Job completed successfully. Statistics: {stats}")
        else:
            logger.info("Dry run mode - no files will be processed")
            video_files = sync_manager.get_video_files(sync_manager.source_dir)
            logger.info(f"Would process {len(video_files)} video files")
            
            if sync_manager.azure_enabled:
                logger.info("Azure Blob Storage is configured and would be used for uploads")
            else:
                logger.info("Azure Blob Storage is not configured")
    
    except Exception as e:
        logger.error(f"Cronjob failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
