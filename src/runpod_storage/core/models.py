"""
Pydantic models for Runpod Storage API.

These models provide comprehensive validation and serialization for all API operations.
Follows OpenAPI 3.0 specification for maximum compatibility.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class DatacenterID(str, Enum):
    """Available Runpod datacenters."""

    EUR_IS_1 = "EUR-IS-1"
    EU_RO_1 = "EU-RO-1"
    EU_CZ_1 = "EU-CZ-1"
    US_KS_2 = "US-KS-2"


class VolumeStatus(str, Enum):
    """Volume status enumeration."""

    CREATING = "creating"
    AVAILABLE = "available"
    DELETING = "deleting"
    ERROR = "error"


# Request Models
class CreateVolumeRequest(BaseModel):
    """Request model for creating a network volume."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Name for the network volume",
        example="my-storage-volume",
    )
    size: int = Field(
        ...,
        ge=10,
        le=4000,
        description="Size in GB (minimum 10GB, maximum 4000GB)",
        example=50,
    )
    datacenter_id: DatacenterID = Field(
        ...,
        description="Datacenter where the volume will be created",
        example=DatacenterID.EU_RO_1,
    )

    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate volume name."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v


class NetworkVolumeUpdateRequest(BaseModel):
    """Request model for updating a network volume."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        description="New name for the network volume",
        example="renamed-storage",
    )
    size: Optional[int] = Field(
        None,
        ge=10,
        le=4000,
        description="New size in GB (must be larger than current size)",
        example=100,
    )

    @validator("name")
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate volume name."""
        if v is not None and not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    @validator("size")
    def validate_at_least_one_field(
        cls, v: Optional[int], values: dict
    ) -> Optional[int]:
        """Ensure at least one field is provided."""
        if v is None and values.get("name") is None:
            raise ValueError("Must specify at least name or size to update")
        return v


class S3Credentials(BaseModel):
    """S3 credentials for file operations."""

    s3_access_key: str = Field(
        ...,
        description="S3 access key (starts with 'user_')",
        example="user_your_access_key_here",
    )
    s3_secret_key: str = Field(
        ...,
        description="S3 secret key (starts with 'rps_')",
        example="rps_your_secret_key_here",
    )


class UploadFileRequest(BaseModel):
    """Request model for file upload."""

    remote_path: Optional[str] = Field(
        None,
        description="Remote path for the file (defaults to filename)",
        example="data/my-file.txt",
    )
    chunk_size: int = Field(
        50 * 1024 * 1024,
        ge=1024 * 1024,
        le=500 * 1024 * 1024,
        description="Chunk size for multipart upload in bytes",
        example=50 * 1024 * 1024,
    )
    s3_credentials: S3Credentials = Field(
        ..., description="S3 credentials for file operations"
    )


class DownloadFileRequest(BaseModel):
    """Request model for file download."""

    remote_path: str = Field(
        ...,
        min_length=1,
        description="Remote path of the file to download",
        example="data/my-file.txt",
    )
    local_path: Optional[str] = Field(
        None,
        description="Local path to save the file (defaults to filename)",
        example="./downloads/my-file.txt",
    )
    s3_credentials: S3Credentials = Field(
        ..., description="S3 credentials for file operations"
    )


class ListFilesRequest(BaseModel):
    """Request model for listing files."""

    prefix: Optional[str] = Field(
        None, description="Prefix filter for file paths", example="data/"
    )
    s3_credentials: S3Credentials = Field(
        ..., description="S3 credentials for file operations"
    )


class DeleteFileRequest(BaseModel):
    """Request model for file deletion."""

    remote_path: str = Field(
        ...,
        min_length=1,
        description="Remote path of the file to delete",
        example="data/my-file.txt",
    )
    s3_credentials: S3Credentials = Field(
        ..., description="S3 credentials for file operations"
    )


# Response Models
class NetworkVolume(BaseModel):
    """Network volume information."""

    id: str = Field(..., description="Unique volume identifier", example="abc123def456")
    name: str = Field(..., description="Volume name", example="my-storage-volume")
    size: int = Field(..., description="Size in GB", example=50)
    datacenter_id: Optional[DatacenterID] = Field(
        None, description="Datacenter location", alias="dataCenterId"
    )
    status: Optional[VolumeStatus] = Field(None, description="Volume status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        populate_by_name = True  # Allow both field name and alias


class FileInfo(BaseModel):
    """File information."""

    key: str = Field(..., description="File path/key", example="data/my-file.txt")
    size: int = Field(..., description="File size in bytes", example=1024000)
    last_modified: datetime = Field(..., description="Last modification timestamp")
    etag: str = Field(
        ..., description="Entity tag for the file", example="abc123def456"
    )
    content_type: Optional[str] = Field(
        None, description="MIME content type", example="text/plain"
    )


class ListFilesResponse(BaseModel):
    """Response for listing files."""

    files: List[FileInfo] = Field(..., description="List of files in the volume")
    total_count: int = Field(..., description="Total number of files", example=42)
    prefix: Optional[str] = Field(
        None, description="Prefix filter used", example="data/"
    )


class UploadResponse(BaseModel):
    """Response for file upload."""

    success: bool = Field(..., description="Upload success status")
    file_path: str = Field(
        ..., description="Remote file path", example="data/my-file.txt"
    )
    size: int = Field(..., description="Uploaded file size in bytes", example=1024000)
    upload_time: float = Field(..., description="Upload time in seconds", example=12.34)
    speed_mbps: float = Field(..., description="Upload speed in MB/s", example=4.2)


class DownloadResponse(BaseModel):
    """Response for file download."""

    success: bool = Field(..., description="Download success status")
    local_path: str = Field(..., description="Local file path", example="./my-file.txt")
    size: int = Field(..., description="Downloaded file size in bytes", example=1024000)
    download_time: float = Field(
        ..., description="Download time in seconds", example=8.76
    )
    speed_mbps: float = Field(..., description="Download speed in MB/s", example=6.1)


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    success: bool = Field(..., description="Delete success status")
    message: str = Field(
        ..., description="Status message", example="Successfully deleted"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type", example="ValidationError")
    message: str = Field(..., description="Error message", example="Invalid input")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status", example="healthy")
    version: str = Field(..., description="API version", example="1.0.0")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )


class DatacenterInfo(BaseModel):
    """Datacenter information."""

    id: DatacenterID = Field(..., description="Datacenter identifier")
    name: str = Field(
        ..., description="Human-readable name", example="Europe - Romania"
    )
    s3_endpoint: str = Field(..., description="S3 API endpoint URL")
    region: str = Field(..., description="AWS-compatible region name")


class ApiKeyInfo(BaseModel):
    """API key information (for documentation)."""

    description: str = Field(
        ...,
        description="How to obtain and use API keys",
        example="Get your API key from https://console.runpod.io/user/settings",
    )
    environment_variable: str = Field(
        ..., description="Environment variable name", example="RUNPOD_API_KEY"
    )
    cli_flag: str = Field(..., description="CLI flag for API key", example="--api-key")


# Utility Models
class PaginationParams(BaseModel):
    """Pagination parameters."""

    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of items to return"
    )
    offset: int = Field(0, ge=0, description="Number of items to skip")


class ListVolumesResponse(BaseModel):
    """Response for listing volumes."""

    volumes: List[NetworkVolume] = Field(..., description="List of network volumes")
    total_count: int = Field(..., description="Total number of volumes")


# Configuration Models
class S3Config(BaseModel):
    """S3 configuration model."""

    access_key: str = Field(..., description="S3 access key")
    secret_key: str = Field(..., description="S3 secret key")
    region: str = Field(..., description="S3 region")
    endpoint_url: str = Field(..., description="S3 endpoint URL")


class RunpodConfig(BaseModel):
    """Runpod configuration model."""

    api_key: str = Field(..., description="Runpod API key")
    base_url: str = Field(
        "https://rest.runpod.io/v1", description="Runpod API base URL"
    )
    timeout: int = Field(30, ge=1, le=300, description="Request timeout in seconds")
