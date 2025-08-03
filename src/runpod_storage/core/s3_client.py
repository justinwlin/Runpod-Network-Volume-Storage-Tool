"""S3-compatible client for Runpod network volume file operations."""

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

        self.region = region
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
        chunk_size: int = 50 * 1024 * 1024,  # 50MB
    ) -> bool:
        """Upload a file to network volume.

        Args:
            local_path: Local file path
            volume_id: Network volume ID
            remote_path: Remote file path in volume
            chunk_size: Size of chunks for multipart upload

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

        # Use simple upload for small files, multipart for large files
        if file_size < chunk_size:
            return self._simple_upload(str(local_path), volume_id, remote_path)
        else:
            return self._multipart_upload(
                str(local_path), volume_id, remote_path, chunk_size
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
        self, local_path: str, volume_id: str, remote_path: str, chunk_size: int
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
    ) -> None:
        self.file_path = file_path
        self.bucket = bucket
        self.key = key
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.part_size = part_size
        self.max_retries = max_retries

        self.progress_lock = Lock()
        self.parts_completed = 0

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
                elapsed = time.time() - start_time
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
        """Execute the multipart upload."""
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

        resp = self.call_with_524_retry(
            "create_multipart_upload",
            lambda: self.s3.create_multipart_upload(Bucket=self.bucket, Key=self.key),
        )
        self.upload_id = resp["UploadId"]
        logger.info(f"Initiated multipart upload: UploadId={self.upload_id}")

        parts: List[dict] = []
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for part_num in range(1, total_parts + 1):
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
                        )
                    ] = part_num

                for fut in as_completed(futures):
                    part = fut.result()
                    parts.append(part)

            def fetch_parts():
                paginator = self.s3.get_paginator("list_parts")
                found = []
                for page in paginator.paginate(
                    Bucket=self.bucket, Key=self.key, UploadId=self.upload_id
                ):
                    found.extend(page.get("Parts", []))
                return found

            seen = self.call_with_524_retry("list_parts", fetch_parts)
            logger.info(f"Verified {len(seen)} of {total_parts} parts uploaded")

            if len(seen) != total_parts:
                raise RuntimeError(f"Expected {total_parts} parts but saw {len(seen)}")

            parts_sorted = sorted(parts, key=lambda x: x["PartNumber"])
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
                logger.info(f"UploadId {self.upload_id} left open for resumption")
            raise

        elapsed = time.time() - start_time
        speed = self.human_mb_per_s(file_size, elapsed)
        duration = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))
        logger.info(f"Upload Speed {speed:.2f} MB/s, Duration {duration}")
