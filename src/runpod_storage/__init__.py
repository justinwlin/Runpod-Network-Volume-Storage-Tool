"""
Runpod Storage - Professional CLI, API, and SDK for Runpod network storage management.

This package provides:
- CLI tool for interactive storage management
- Python SDK for programmatic access
- FastAPI server for REST API access
- Comprehensive error handling and validation
"""

__version__ = "1.0.0"
__author__ = "Runpod Storage Team"
__email__ = "support@runpod.io"

from .core.api import RunpodStorageAPI, list_volumes, create_volume, upload_file, download_file
from .core.client import RunpodClient
from .core.s3_client import RunpodS3Client
from .core.exceptions import (
    RunpodStorageError,
    AuthenticationError,
    VolumeNotFoundError,
    FileNotFoundError as RunpodFileNotFoundError,
    InsufficientStorageError,
    NetworkError,
)

__all__ = [
    # Core classes
    "RunpodStorageAPI",
    "RunpodClient", 
    "RunpodS3Client",
    # Exceptions
    "RunpodStorageError",
    "AuthenticationError", 
    "VolumeNotFoundError",
    "RunpodFileNotFoundError",
    "InsufficientStorageError",
    "NetworkError",
    # Convenience functions
    "list_volumes",
    "create_volume", 
    "upload_file",
    "download_file",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]