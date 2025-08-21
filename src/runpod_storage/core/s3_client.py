"""S3-compatible client for Runpod network volume file operations."""

import hashlib
import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)

logger = logging.getLogger(__name__)


class RunpodS3Client:
    """S3-compatible client for Runpod network volumes."""
    
    @staticmethod
    def normalize_region(region: str) -> str:
        """Normalize region/datacenter identifier to uppercase format."""
        if not region:
            return region
        
        # Convert to uppercase and strip whitespace
        normalized = region.strip().upper()
        
        # Handle common variations
        variations = {
            "US-KS-1": "US-KS-2",  # In case someone uses the old identifier
            "US-OR-1": "US-KS-2",  # Another potential confusion
        }
        
        return variations.get(normalized, normalized)

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "EU-RO-1",
        endpoint_url: str = "https://s3api-eu-ro-1.runpod.io/",
        max_retries: int = 5,
    ):
        """Initialize S3 client for Runpod.

        Args:
            access_key: S3 API access key (from Runpod console)
            secret_key: S3 API secret key (from Runpod console)
            region: Datacenter region
            endpoint_url: S3 endpoint URL for the datacenter
            max_retries: Maximum number of retries for operations
        """
        self.access_key = access_key or os.getenv("RUNPOD_S3_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("RUNPOD_S3_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "S3 API credentials required. Set RUNPOD_S3_ACCESS_KEY and "
                "RUNPOD_S3_SECRET_KEY environment variables or pass as parameters."
            )

        self.region = self.normalize_region(region)
        self.endpoint_url = endpoint_url
        self.max_retries = max_retries

        self.session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

        self.config = Config(
            region_name=self.region,
            retries={"max_attempts": self.max_retries, "mode": "standard"},
        )

        self.s3 = self.session.client(
            "s3", config=self.config, endpoint_url=self.endpoint_url
        )

    def list_volumes(self) -> List[str]:
        """List all available network volumes (S3 buckets)."""
        try:
            response = self.s3.list_buckets()
            return [bucket["Name"] for bucket in response.get("Buckets", [])]
        except Exception as e:
            logger.error(f"Failed to list volumes: {e}")
            raise

    def list_files(self, volume_id: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in a network volume.

        Args:
            volume_id: Network volume ID
            prefix: Optional prefix to filter files

        Returns:
            List of file information dictionaries
        """
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            files = []

            for page in paginator.paginate(Bucket=volume_id, Prefix=prefix):
                for obj in page.get("Contents", []):
                    files.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"].strip('"'),
                        }
                    )

            return files
        except Exception as e:
            logger.error(f"Failed to list files in volume {volume_id}: {e}")
            raise

    def upload_file(
        self,
        local_path: str,
        volume_id: str,
        remote_path: str,
        chunk_size: Optional[int] = None,
        enable_resume: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """Upload a file to network volume with automatic chunk size optimization.

        Args:
            local_path: Local file path
            volume_id: Network volume ID
            remote_path: Remote file path in volume
            chunk_size: Size of chunks for multipart upload (auto-detected if None)
            enable_resume: Enable resume capability for interrupted uploads
            progress_callback: Optional callback for progress updates.
                Called with (bytes_uploaded, total_bytes, speed_mbps)

        Returns:
            True if successful
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        if local_path.is_dir():
            raise ValueError(
                f"Path is a directory. Use upload_directory() for directory uploads: {local_path}"
            )

        file_size = local_path.stat().st_size
        
        # Auto-detect optimal chunk size if not specified
        if chunk_size is None:
            file_size_gb = file_size / (1024**3)
            
            if file_size_gb < 1:
                chunk_size = 10 * 1024 * 1024      # 10MB for < 1GB
            elif file_size_gb < 10:
                chunk_size = 50 * 1024 * 1024      # 50MB for 1-10GB
            elif file_size_gb < 50:
                chunk_size = 100 * 1024 * 1024     # 100MB for 10-50GB
            else:
                chunk_size = 200 * 1024 * 1024     # 200MB for > 50GB
            
            logger.debug(f"Auto-detected chunk size: {chunk_size / (1024*1024):.0f}MB for {file_size_gb:.1f}GB file")

        # Use simple upload for small files, multipart for large files
        if file_size < chunk_size:
            # For simple upload, call progress callback once at completion
            result = self._simple_upload(str(local_path), volume_id, remote_path)
            if result and progress_callback:
                progress_callback(file_size, file_size, 0)
            return result
        else:
            return self._multipart_upload(
                str(local_path), volume_id, remote_path, chunk_size, enable_resume, progress_callback
            )

    def upload_directory(
        self,
        local_dir: str,
        volume_id: str,
        remote_dir: str = "",
        exclude_patterns: List[str] = None,
        delete: bool = False,
        progress_callback=None,
    ) -> bool:
        """Upload a directory to network volume (sync functionality).

        Args:
            local_dir: Local directory path
            volume_id: Network volume ID
            remote_dir: Remote directory path in volume (default: root)
            exclude_patterns: List of glob patterns to exclude
            delete: Delete remote files not present locally
            progress_callback: Callback function for progress updates

        Returns:
            True if successful
        """
        import fnmatch
        from concurrent.futures import ThreadPoolExecutor, as_completed

        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        if not local_dir.is_dir():
            raise ValueError(f"Path is not a directory: {local_dir}")

        exclude_patterns = exclude_patterns or []

        # Get all local files
        local_files = []
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)

                # Check exclude patterns
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(str(relative_path), pattern):
                        excluded = True
                        break

                if not excluded:
                    remote_file_path = str(Path(remote_dir) / relative_path).replace(
                        "\\", "/"
                    )
                    local_files.append((str(file_path), remote_file_path))

        # Get existing remote files if delete is enabled
        remote_files = set()
        if delete:
            try:
                existing_files = self.list_files(volume_id, remote_dir)
                remote_files = {f["key"] for f in existing_files}
            except Exception as e:
                logger.warning(f"Could not list remote files for deletion: {e}")

        total_files = len(local_files)
        uploaded_files = 0
        failed_files = []

        logger.info(f"Starting directory upload: {total_files} files")

        # Upload files with threading
        def upload_single_file(file_info):
            local_file, remote_file = file_info
            try:
                self.upload_file(local_file, volume_id, remote_file)
                return True, remote_file
            except Exception as e:
                logger.error(f"Failed to upload {local_file}: {e}")
                return False, remote_file

        # Use ThreadPoolExecutor for concurrent uploads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(upload_single_file, file_info): file_info
                for file_info in local_files
            }

            for future in as_completed(futures):
                success, remote_file = future.result()
                uploaded_files += 1

                if success:
                    remote_files.discard(remote_file)  # Remove from deletion list
                    if progress_callback:
                        progress_callback(uploaded_files, total_files, remote_file)
                    logger.info(
                        f"Uploaded ({uploaded_files}/{total_files}): {remote_file}"
                    )
                else:
                    failed_files.append(remote_file)

        # Delete remote files not present locally
        if delete and remote_files:
            logger.info(
                f"Deleting {len(remote_files)} remote files not present locally"
            )
            for remote_file in remote_files:
                try:
                    self.delete_file(volume_id, remote_file)
                    logger.info(f"Deleted: {remote_file}")
                except Exception as e:
                    logger.error(f"Failed to delete {remote_file}: {e}")

        if failed_files:
            logger.error(f"Failed to upload {len(failed_files)} files: {failed_files}")
            return False

        logger.info(f"Directory upload completed: {uploaded_files} files uploaded")
        return True

    def download_directory(
        self, volume_id: str, remote_dir: str, local_dir: str, progress_callback=None
    ) -> bool:
        """Download a directory from network volume.

        Args:
            volume_id: Network volume ID
            remote_dir: Remote directory path in volume
            local_dir: Local directory path to download to
            progress_callback: Callback function for progress updates

        Returns:
            True if successful
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Get all remote files
        try:
            remote_files = self.list_files(volume_id, remote_dir)
        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            raise

        total_files = len(remote_files)
        downloaded_files = 0
        failed_files = []

        logger.info(f"Starting directory download: {total_files} files")

        def download_single_file(file_info):
            remote_file = file_info["key"]
            # Remove the remote_dir prefix if present
            if remote_dir and remote_file.startswith(remote_dir):
                relative_path = remote_file[len(remote_dir) :].lstrip("/")
            else:
                relative_path = remote_file

            local_file = local_dir / relative_path

            try:
                self.download_file(volume_id, remote_file, str(local_file))
                return True, remote_file
            except Exception as e:
                logger.error(f"Failed to download {remote_file}: {e}")
                return False, remote_file

        # Use ThreadPoolExecutor for concurrent downloads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(download_single_file, file_info): file_info
                for file_info in remote_files
            }

            for future in as_completed(futures):
                success, remote_file = future.result()
                downloaded_files += 1

                if success:
                    if progress_callback:
                        progress_callback(downloaded_files, total_files, remote_file)
                    logger.info(
                        f"Downloaded ({downloaded_files}/{total_files}): {remote_file}"
                    )
                else:
                    failed_files.append(remote_file)

        if failed_files:
            logger.error(
                f"Failed to download {len(failed_files)} files: {failed_files}"
            )
            return False

        logger.info(
            f"Directory download completed: {downloaded_files} files downloaded"
        )
        return True

    def download_file(self, volume_id: str, remote_path: str, local_path: str) -> bool:
        """Download a file from network volume.

        Args:
            volume_id: Network volume ID
            remote_path: Remote file path in volume
            local_path: Local file path to save to

        Returns:
            True if successful
        """
        try:
            # Create local directory if it doesn't exist
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading {remote_path} to {local_path}")
            self.s3.download_file(volume_id, remote_path, str(local_path))
            logger.info("Download completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def delete_file(self, volume_id: str, remote_path: str) -> bool:
        """Delete a file from network volume."""
        try:
            self.s3.delete_object(Bucket=volume_id, Key=remote_path)
            logger.info(f"Deleted {remote_path} from volume {volume_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise

    def cleanup_abandoned_uploads(self, volume_id: str, max_age_hours: int = 24) -> int:
        """Clean up abandoned multipart uploads for a volume.
        
        Args:
            volume_id: Network volume ID
            max_age_hours: Maximum age in hours for uploads to keep
            
        Returns:
            Number of uploads cleaned up
        """
        try:
            import datetime
            
            cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            paginator = self.s3.get_paginator("list_multipart_uploads")
            for page in paginator.paginate(Bucket=volume_id):
                for upload in page.get("Uploads", []):
                    initiated = upload["Initiated"]
                    if initiated < cutoff_time:
                        upload_id = upload["UploadId"]
                        key = upload["Key"]
                        try:
                            self.s3.abort_multipart_upload(
                                Bucket=volume_id,
                                Key=key,
                                UploadId=upload_id
                            )
                            logger.info(f"Cleaned up abandoned upload: {key} ({upload_id})")
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to clean up upload {upload_id}: {e}")
                            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} abandoned uploads from {volume_id}")
            return cleaned_count
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            return 0

    def _simple_upload(self, local_path: str, volume_id: str, remote_path: str) -> bool:
        """Upload a file using simple upload."""
        try:
            logger.info(f"Uploading {local_path} to {remote_path}")
            self.s3.upload_file(local_path, volume_id, remote_path)
            logger.info("Upload completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    def _multipart_upload(
        self, local_path: str, volume_id: str, remote_path: str, chunk_size: int, 
        enable_resume: bool = True, progress_callback: Optional[callable] = None
    ) -> bool:
        """Upload a large file using multipart upload with the robust implementation."""
        try:
            uploader = LargeMultipartUploader(
                file_path=local_path,
                bucket=volume_id,
                key=remote_path,
                region=self.region,
                access_key=self.access_key,
                secret_key=self.secret_key,
                endpoint=self.endpoint_url,
                part_size=chunk_size,
                max_retries=self.max_retries,
                enable_resume=enable_resume,
                progress_callback=progress_callback,
            )
            uploader.upload()
            return True
        except Exception as e:
            logger.error(f"Multipart upload failed: {e}")
            raise


class LargeMultipartUploader:
    """Upload a large file using robust multipart uploads."""

    def __init__(
        self,
        *,
        file_path: str,
        bucket: str,
        key: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint: str,
        part_size: int = 50 * 1024 * 1024,
        max_retries: int = 5,
        enable_resume: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> None:
        self.file_path = file_path
        self.bucket = bucket
        self.key = key
        self.region = RunpodS3Client.normalize_region(region)
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.part_size = part_size
        self.max_retries = max_retries
        self.enable_resume = enable_resume
        self.progress_callback = progress_callback

        self.progress_lock = Lock()
        self.parts_completed = 0
        self.upload_start_time = None

        self.session = boto3.session.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        self.botocore_cfg = Config(
            region_name=self.region,
            retries={"max_attempts": self.max_retries, "mode": "standard"},
        )
        self.s3 = self.session.client(
            "s3", config=self.botocore_cfg, endpoint_url=self.endpoint
        )
        self.upload_id: Optional[str] = None
        self.file_hash: Optional[str] = None
        self.existing_parts: Dict[int, str] = {}  # part_number -> etag

    @staticmethod
    def human_mb_per_s(num_bytes: int, seconds: float) -> float:
        """Return MB/s as float, avoiding divide-by-zero."""
        return (num_bytes / (1024 * 1024)) / seconds if seconds > 0 else float("inf")

    @staticmethod
    def is_insufficient_storage_error(exc: Exception) -> bool:
        """Return True if the exception wraps a 507 Insufficient Storage response."""
        if isinstance(exc, ClientError):
            meta = exc.response.get("ResponseMetadata", {})
            return meta.get("HTTPStatusCode") == 507
        return False

    @staticmethod
    def is_524_error(exc: Exception) -> bool:
        """Return True if the exception wraps a 524 timeout response."""
        if isinstance(exc, ClientError):
            meta = exc.response.get("ResponseMetadata", {})
            return meta.get("HTTPStatusCode") == 524
        return False

    @staticmethod
    def is_no_such_upload_error(exc: Exception) -> bool:
        """Return True if the exception reports a missing multipart upload."""
        if isinstance(exc, ClientError):
            err = exc.response.get("Error", {})
            return err.get("Code") == "NoSuchUpload"
        return False

    def calculate_file_hash(self) -> str:
        """Calculate MD5 hash of the file for resume verification."""
        if self.file_hash is not None:
            return self.file_hash
            
        logger.info("Calculating file hash for resume verification...")
        hash_md5 = hashlib.md5()
        with open(self.file_path, "rb") as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        
        self.file_hash = hash_md5.hexdigest()
        logger.info(f"File hash calculated: {self.file_hash}")
        return self.file_hash

    def find_existing_upload(self) -> Optional[str]:
        """Find existing multipart upload for this file that can be resumed."""
        try:
            file_hash = self.calculate_file_hash()
            logger.info(f"Looking for existing uploads for key: {self.key}")
            
            # List all multipart uploads for this key
            paginator = self.s3.get_paginator("list_multipart_uploads")
            upload_count = 0
            
            # Try without prefix first, then filter manually
            for page in paginator.paginate(Bucket=self.bucket):
                uploads = page.get("Uploads", [])
                upload_count += len(uploads)
                logger.info(f"Found {len(uploads)} uploads in this page")
                
                for upload in uploads:
                    upload_key = upload["Key"]
                    logger.info(f"Checking upload: {upload_key} == {self.key}?")
                    
                    # Handle both with and without leading slash
                    if (upload_key == self.key or 
                        upload_key == f"/{self.key}" or 
                        upload_key.lstrip("/") == self.key.lstrip("/")):
                        upload_id = upload["UploadId"]
                        logger.info(f"Found matching key upload: {upload_id}")
                        
                        # Check if this upload has metadata that matches our file
                        if self.verify_upload_compatibility(upload_id, file_hash):
                            logger.info(f"Found resumable upload: {upload_id}")
                            return upload_id
                        else:
                            logger.info(f"Upload {upload_id} not compatible")
            
            logger.info(f"Total uploads found: {upload_count}, none resumable")
                            
        except Exception as e:
            logger.warning(f"Error finding existing uploads: {e}")
            
        return None

    def verify_upload_compatibility(self, upload_id: str, file_hash: str) -> bool:
        """Verify if an existing upload is compatible with current file."""
        try:
            logger.info(f"Verifying compatibility for upload {upload_id}")
            
            # Get existing parts
            parts = self.list_existing_parts(upload_id)
            logger.info(f"Found {len(parts)} existing parts")
            
            if not parts:
                logger.info("No parts found, not compatible")
                return False
            
            # Get the current file size and calculate expected total parts
            actual_file_size = os.path.getsize(self.file_path)
            expected_total_parts = (actual_file_size + self.part_size - 1) // self.part_size
            
            logger.info(f"Current file size: {actual_file_size} bytes")
            logger.info(f"Expected total parts for this file: {expected_total_parts}")
            logger.info(f"Existing uploaded parts: {len(parts)}")
            
            # Check if part size is consistent
            for part in parts:
                part_size = part.get("Size", 0)
                part_number = part["PartNumber"]
                
                # For all parts except the last one, size should match part_size
                if part_number < expected_total_parts:
                    if part_size != self.part_size:
                        logger.info(f"Part {part_number} size mismatch: expected {self.part_size}, got {part_size}")
                        return False
                else:
                    # For the last part, calculate expected size
                    expected_last_part_size = actual_file_size - ((expected_total_parts - 1) * self.part_size)
                    if part_size != expected_last_part_size:
                        logger.info(f"Last part {part_number} size mismatch: expected {expected_last_part_size}, got {part_size}")
                        return False
                
                logger.info(f"Part {part_number}: {part_size} bytes ✓")
            
            # Verify that we don't have more parts than expected
            max_part_number = max(part["PartNumber"] for part in parts)
            if max_part_number > expected_total_parts:
                logger.info(f"Upload has more parts ({max_part_number}) than expected ({expected_total_parts})")
                return False
            
            logger.info("Upload appears compatible - part sizes and file size match")
            return True
                
        except Exception as e:
            logger.warning(f"Error verifying upload compatibility: {e}")
            
        return False

    def list_existing_parts(self, upload_id: str) -> List[Dict]:
        """List parts that have already been uploaded."""
        try:
            paginator = self.s3.get_paginator("list_parts")
            parts = []
            for page in paginator.paginate(
                Bucket=self.bucket, Key=self.key, UploadId=upload_id
            ):
                parts.extend(page.get("Parts", []))
            return parts
        except Exception as e:
            logger.warning(f"Error listing existing parts: {e}")
            return []

    def load_existing_parts(self, upload_id: str) -> None:
        """Load information about parts that have already been uploaded."""
        existing_parts = self.list_existing_parts(upload_id)
        self.existing_parts = {}
        
        for part in existing_parts:
            part_number = part["PartNumber"]
            etag = part["ETag"]
            self.existing_parts[part_number] = etag
            
        logger.info(f"Found {len(self.existing_parts)} existing parts to resume from")

    def is_part_uploaded(self, part_number: int) -> bool:
        """Check if a specific part has already been uploaded."""
        return part_number in self.existing_parts

    def get_existing_part_etag(self, part_number: int) -> Optional[str]:
        """Get the ETag of an existing part."""
        return self.existing_parts.get(part_number)


    def call_with_524_retry(self, description: str, func):
        """Call ``func`` retrying on HTTP 524 or timeout errors."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except ClientError as exc:
                if self.is_524_error(exc):
                    logger.warning(
                        f"{description}: received 524 response (attempt {attempt})"
                    )
                    if attempt == self.max_retries:
                        logger.error(f"{description}: exceeded max_retries for 524")
                        raise
                    backoff = 2**attempt
                    logger.info(f"{description}: retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                raise
            except (ReadTimeoutError, ConnectTimeoutError) as exc:
                logger.warning(
                    f"{description}: request timed out (attempt {attempt}): {exc}"
                )
                if attempt == self.max_retries:
                    logger.error(f"{description}: exceeded max_retries for timeout")
                    raise
                backoff = 2**attempt
                logger.info(f"{description}: retrying in {backoff}s...")
                time.sleep(backoff)

    def complete_with_timeout_retry(
        self,
        *,
        parts_sorted: list,
        initial_timeout: int,
        expected_size: int,
    ):
        """Complete the multipart upload, doubling timeout on client timeouts."""
        if self.upload_id is None:
            raise RuntimeError("upload_id not set")

        timeout = initial_timeout
        cfg = self.botocore_cfg
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            cfg = cfg.merge(Config(read_timeout=timeout, connect_timeout=timeout))
            client = self.session.client("s3", config=cfg, endpoint_url=self.endpoint)
            try:
                client.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=self.key,
                    UploadId=self.upload_id,
                    MultipartUpload={"Parts": parts_sorted},
                )
                self.s3 = client
                self.botocore_cfg = cfg
                return
            except (ReadTimeoutError, ConnectTimeoutError) as exc:
                last_exc = exc
                no_such_upload = False
                logger.warning(
                    f"complete_multipart_upload timed out after {timeout}s: {exc}"
                )
            except (ClientError, BotoCoreError) as exc:
                last_exc = exc
                no_such_upload = self.is_no_such_upload_error(exc)
                logger.warning(
                    f"complete_multipart_upload failed (attempt {attempt}): {exc}"
                )

            if no_such_upload:
                logger.info("Upload session missing; checking object state immediately")
            else:
                logger.info(
                    f"Waiting {timeout}s before checking object state to see if merge has completed"
                )
                time.sleep(timeout)

            try:
                head = self.call_with_524_retry(
                    "head_object",
                    lambda: client.head_object(Bucket=self.bucket, Key=self.key),
                )
                uploaded_size = head.get("ContentLength")
                if uploaded_size == expected_size:
                    logger.info(
                        "HeadObject confirms multipart upload merge has completed"
                    )
                    self.s3 = client
                    self.botocore_cfg = cfg
                    return
                logger.info(
                    "HeadObject size mismatch after timeout; will retry complete_multipart_upload"
                )
            except Exception as head_exc:
                logger.info(f"head_object failed after error: {head_exc}")

            if attempt == self.max_retries:
                raise (
                    last_exc
                    if last_exc
                    else RuntimeError(
                        "Exceeded max_retries without completing multipart upload"
                    )
                )

            timeout *= 2
            logger.info(f"Increasing timeout to {timeout}s and retrying")

    def upload_part(
        self,
        *,
        part_number: int,
        offset: int,
        bytes_to_read: int,
        total_parts: int,
        start_time: float,
        file_size: int,
    ) -> dict:
        """Upload a single part with exponential-backoff retries."""
        if self.upload_id is None:
            raise RuntimeError("upload_id not set")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Part {part_number}: reading bytes {offset}–{offset+bytes_to_read} (attempt {attempt})"
                )
                with open(self.file_path, "rb") as f:
                    f.seek(offset)
                    data = f.read(bytes_to_read)
                resp = self.s3.upload_part(
                    Bucket=self.bucket,
                    Key=self.key,
                    PartNumber=part_number,
                    UploadId=self.upload_id,
                    Body=data,
                )
                etag = resp["ETag"]
                with self.progress_lock:
                    self.parts_completed += 1
                    progress = 100.0 * self.parts_completed / total_parts
                    
                # Calculate progress metrics
                elapsed = time.time() - start_time
                bytes_uploaded = self.parts_completed * self.part_size
                # Handle last part which might be smaller
                if self.parts_completed == total_parts:
                    bytes_uploaded = file_size
                total_bytes = file_size
                speed_mbps = (bytes_uploaded / (1024**2)) / elapsed if elapsed > 0 else 0
                
                # Call progress callback if provided
                if self.progress_callback:
                    try:
                        self.progress_callback(bytes_uploaded, total_bytes, speed_mbps)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                
                progress_fraction = part_number / total_parts
                if progress_fraction > 0:
                    remaining = max(0, elapsed * (1 / progress_fraction - 1))
                    eta = time.strftime("%Hh %Mm %Ss", time.gmtime(remaining))
                else:
                    eta = "?"
                logger.info(
                    f"Part {part_number}: uploaded, progress: {progress:.1f}%, est time remaining: {eta}"
                )
                return {"PartNumber": part_number, "ETag": etag}
            except (BotoCoreError, ClientError) as exc:
                if self.is_insufficient_storage_error(exc):
                    logger.error(
                        f"Part {part_number}: received 507 Insufficient Storage; aborting"
                    )
                    raise RuntimeError("Server reported insufficient storage") from exc
                if self.is_524_error(exc):
                    logger.warning(
                        f"Part {part_number}: received 524 response (attempt {attempt})"
                    )
                else:
                    logger.warning(
                        f"Part {part_number}: attempt {attempt} failed: {exc}"
                    )
                if attempt == self.max_retries:
                    logger.error(
                        f"Part {part_number}: exceeded max_retries ({self.max_retries})"
                    )
                    raise
                backoff = 2**attempt
                logger.info(f"Part {part_number}: retrying in {backoff}s...")
                time.sleep(backoff)

    def upload(self) -> None:
        """Execute the multipart upload with resume capability."""
        logger.info(
            f"Uploading to region: {self.region}; bucket: {self.bucket}; key: {self.key}"
        )

        file_size = os.path.getsize(self.file_path)
        total_parts = math.ceil(file_size / self.part_size)
        logger.info(
            f"File size: {file_size} bytes; will upload in {total_parts} parts of up to {self.part_size} bytes each"
        )

        start_time = time.time()

        file_gb = file_size / float(1024**3)
        completion_timeout = max(60, int(math.ceil(file_gb) * 5))

        # Try to find and resume existing upload if enabled
        existing_upload_id = None
        if self.enable_resume:
            existing_upload_id = self.find_existing_upload()
        
        if existing_upload_id:
            logger.info(f"Resuming existing upload: {existing_upload_id}")
            self.upload_id = existing_upload_id
            self.load_existing_parts(existing_upload_id)
            # Update parts completed for progress tracking
            self.parts_completed = len(self.existing_parts)
            logger.info(f"Resuming from part {self.parts_completed + 1} of {total_parts}")
        else:
            # Create new multipart upload
            resp = self.call_with_524_retry(
                "create_multipart_upload",
                lambda: self.s3.create_multipart_upload(Bucket=self.bucket, Key=self.key),
            )
            self.upload_id = resp["UploadId"]
            logger.info(f"Initiated new multipart upload: UploadId={self.upload_id}")

        # Track parts uploaded in this session (not including existing ones)
        new_parts: List[dict] = []
        
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                
                # Only upload parts that haven't been uploaded yet
                for part_num in range(1, total_parts + 1):
                    if self.is_part_uploaded(part_num):
                        logger.info(f"Part {part_num}: already uploaded, skipping")
                        continue
                        
                    offset = (part_num - 1) * self.part_size
                    chunk_size = min(self.part_size, file_size - offset)
                    futures[
                        executor.submit(
                            self.upload_part,
                            part_number=part_num,
                            offset=offset,
                            bytes_to_read=chunk_size,
                            total_parts=total_parts,
                            start_time=start_time,
                            file_size=file_size,
                        )
                    ] = part_num

                # Wait for new parts to complete
                for fut in as_completed(futures):
                    part = fut.result()
                    new_parts.append(part)

            # Combine existing and new parts for completion
            all_parts = []
            
            # Add existing parts
            for part_number, etag in self.existing_parts.items():
                all_parts.append({"PartNumber": part_number, "ETag": etag})
            
            # Add newly uploaded parts
            all_parts.extend(new_parts)
            
            # Verify all parts are present
            parts_by_number = {p["PartNumber"]: p for p in all_parts}
            logger.info(f"Total parts available: {sorted(parts_by_number.keys())}")
            logger.info(f"Existing parts: {sorted(self.existing_parts.keys())}")
            logger.info(f"New parts: {sorted([p['PartNumber'] for p in new_parts])}")
            
            if len(parts_by_number) != total_parts:
                missing_parts = set(range(1, total_parts + 1)) - set(parts_by_number.keys())
                logger.error(f"Parts incomplete: {len(parts_by_number)} of {total_parts}. Missing: {sorted(missing_parts)}")
                raise RuntimeError(
                    f"Expected {total_parts} parts but have {len(parts_by_number)}. "
                    f"Missing parts: {sorted(missing_parts)}"
                )

            parts_sorted = sorted(all_parts, key=lambda x: x["PartNumber"])
            logger.info("Sending complete_multipart_upload request")
            self.complete_with_timeout_retry(
                parts_sorted=parts_sorted,
                initial_timeout=completion_timeout,
                expected_size=file_size,
            )

            head = self.call_with_524_retry(
                "head_object",
                lambda: self.s3.head_object(Bucket=self.bucket, Key=self.key),
            )
            uploaded_size = head.get("ContentLength")
            if uploaded_size != file_size:
                logger.error(
                    f"Size mismatch: remote object is {uploaded_size} bytes, "
                    f"but local file is {file_size} bytes"
                )
                raise RuntimeError(
                    "Multipart upload verification failed: size mismatch"
                )
            logger.info(
                f"Verified upload: remote object size {uploaded_size} bytes matches local file size"
            )
        except Exception as exc:
            logger.error(f"Upload interrupted: {exc}")
            if self.upload_id:
                completed_parts = len(self.existing_parts) + len(new_parts)
                logger.info(
                    f"UploadId {self.upload_id} left open for resumption. "
                    f"Progress: {completed_parts}/{total_parts} parts uploaded"
                )
            raise

        elapsed = time.time() - start_time
        speed = self.human_mb_per_s(file_size, elapsed)
        duration = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))
        logger.info(f"Upload Speed {speed:.2f} MB/s, Duration {duration}")
