"""
API routes for Runpod Storage server.

Implements all REST endpoints with comprehensive validation and error handling.
"""

import os
import tempfile
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.api import RunpodStorageAPI
from ..core.exceptions import (
    AuthenticationError,
    NetworkError,
    RunpodStorageError,
    VolumeNotFoundError,
)
from ..core.models import (
    CreateVolumeRequest,
    DatacenterInfo,
    DeleteFileRequest,
    DeleteResponse,
    DownloadFileRequest,
    ListFilesRequest,
    ListFilesResponse,
    ListVolumesResponse,
    NetworkVolume,
    NetworkVolumeUpdateRequest,
    UploadResponse,
)

# Security
security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="",
    tags=["Storage"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Authorization failed"},
        500: {"description": "Internal server error"},
    },
)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    api_key_header: str = None,
    api_key_query: str = None,
) -> str:
    """Extract API key from various sources."""

    # Try Bearer token first
    if credentials and credentials.credentials:
        return credentials.credentials

    # Try X-API-Key header
    if api_key_header:
        return api_key_header

    # Try query parameter
    if api_key_query:
        return api_key_query

    # Try environment variable (for development)
    env_key = os.getenv("RUNPOD_API_KEY")
    if env_key:
        return env_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required. Use Authorization header, X-API-Key header, or api_key query parameter.",
    )


async def get_storage_api(api_key: str = Depends(get_api_key)) -> RunpodStorageAPI:
    """Get authenticated storage API instance for volume operations only."""
    try:
        return RunpodStorageAPI(api_key=api_key, auto_setup_s3=False)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize storage API: {e}",
        )


@router.get(
    "/volumes",
    response_model=ListVolumesResponse,
    summary="List network volumes",
    description="Retrieve a list of all network volumes associated with your account.",
)
async def list_volumes(
    api: RunpodStorageAPI = Depends(get_storage_api),
) -> ListVolumesResponse:
    """List all network volumes."""
    try:
        volumes = api.list_volumes()
        return ListVolumesResponse(
            volumes=[NetworkVolume(**vol) for vol in volumes], total_count=len(volumes)
        )
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/volumes",
    response_model=NetworkVolume,
    status_code=status.HTTP_201_CREATED,
    summary="Create network volume",
    description="Create a new network volume with specified name, size, and datacenter.",
)
async def create_volume(
    request: CreateVolumeRequest, api: RunpodStorageAPI = Depends(get_storage_api)
) -> NetworkVolume:
    """Create a new network volume."""
    try:
        volume = api.create_volume(
            name=request.name, size=request.size, datacenter_id=request.datacenter_id
        )
        return NetworkVolume(**volume)
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/volumes/{volume_id}",
    response_model=NetworkVolume,
    summary="Get volume details",
    description="Retrieve detailed information about a specific network volume.",
)
async def get_volume(
    volume_id: str, api: RunpodStorageAPI = Depends(get_storage_api)
) -> NetworkVolume:
    """Get volume details."""
    try:
        volume = api.get_volume(volume_id)
        return NetworkVolume(**volume)
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/volumes/{volume_id}",
    response_model=NetworkVolume,
    summary="Update volume",
    description="Update a network volume's name and/or size. Size can only be increased.",
)
async def update_volume(
    volume_id: str,
    request: NetworkVolumeUpdateRequest,
    api: RunpodStorageAPI = Depends(get_storage_api),
) -> NetworkVolume:
    """Update a network volume."""
    try:
        volume = api.update_volume(
            volume_id=volume_id, name=request.name, size=request.size
        )
        return NetworkVolume(**volume)
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/volumes/{volume_id}",
    response_model=DeleteResponse,
    summary="Delete volume",
    description="Delete a network volume. This operation is irreversible.",
)
async def delete_volume(
    volume_id: str, api: RunpodStorageAPI = Depends(get_storage_api)
) -> DeleteResponse:
    """Delete a network volume."""
    try:
        success = api.delete_volume(volume_id)
        if success:
            return DeleteResponse(
                success=True, message=f"Volume {volume_id} deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/volumes/{volume_id}/files/list",
    response_model=ListFilesResponse,
    summary="List files in volume",
    description="List all files in a network volume, optionally filtered by prefix. Requires S3 credentials in request body.",
)
async def list_files(
    volume_id: str, request: ListFilesRequest, api_key: str = Depends(get_api_key)
) -> ListFilesResponse:
    """List files in a volume."""
    try:
        # Create API instance with provided S3 credentials
        api = RunpodStorageAPI(
            api_key=api_key,
            s3_access_key=request.s3_credentials.s3_access_key,
            s3_secret_key=request.s3_credentials.s3_secret_key,
        )

        files = api.list_files(volume_id, request.prefix or "")
        return ListFilesResponse(
            files=files,
            total_count=len(files),
            prefix=request.prefix if request.prefix else None,
        )
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/volumes/{volume_id}/files",
    response_model=UploadResponse,
    summary="Upload file",
    description="Upload a file to a network volume. Supports large files via multipart upload. Requires S3 credentials in form data.",
)
async def upload_file(
    volume_id: str,
    file: UploadFile = File(..., description="File to upload"),
    remote_path: str = Form(None, description="Remote path for the file"),
    chunk_size: int = Form(
        50 * 1024 * 1024, description="Chunk size for multipart upload"
    ),
    s3_access_key: str = Form(..., description="S3 access key"),
    s3_secret_key: str = Form(..., description="S3 secret key"),
    api_key: str = Depends(get_api_key),
) -> UploadResponse:
    """Upload a file to a volume."""

    # Use filename if remote_path not provided
    if not remote_path:
        remote_path = file.filename or "uploaded_file"

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        import time

        start_time = time.time()

        # Create API instance with provided S3 credentials
        api = RunpodStorageAPI(
            api_key=api_key, s3_access_key=s3_access_key, s3_secret_key=s3_secret_key
        )

        success = api.upload_file(tmp_file_path, volume_id, remote_path, chunk_size)

        upload_time = time.time() - start_time
        file_size = len(content)
        speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0

        return UploadResponse(
            success=success,
            file_path=remote_path,
            size=file_size,
            upload_time=upload_time,
            speed_mbps=speed_mbps,
        )

    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file_path)
        except:
            pass


@router.post(
    "/volumes/{volume_id}/files/download",
    response_class=FileResponse,
    summary="Download file",
    description="Download a file from a network volume. Requires S3 credentials in request body.",
)
async def download_file(
    volume_id: str, request: DownloadFileRequest, api_key: str = Depends(get_api_key)
) -> FileResponse:
    """Download a file from a volume."""

    # Create temporary file for download
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file_path = tmp_file.name

    try:
        # Create API instance with provided S3 credentials
        api = RunpodStorageAPI(
            api_key=api_key,
            s3_access_key=request.s3_credentials.s3_access_key,
            s3_secret_key=request.s3_credentials.s3_secret_key,
        )

        success = api.download_file(volume_id, request.remote_path, tmp_file_path)

        if success:
            filename = os.path.basename(request.remote_path)
            return FileResponse(
                path=tmp_file_path,
                filename=filename,
                media_type="application/octet-stream",
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"File {request.remote_path} not found"
            )

    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/volumes/{volume_id}/files/delete",
    response_model=DeleteResponse,
    summary="Delete file",
    description="Delete a file from a network volume. Requires S3 credentials in request body.",
)
async def delete_file(
    volume_id: str, request: DeleteFileRequest, api_key: str = Depends(get_api_key)
) -> DeleteResponse:
    """Delete a file from a volume."""
    try:
        # Create API instance with provided S3 credentials
        api = RunpodStorageAPI(
            api_key=api_key,
            s3_access_key=request.s3_credentials.s3_access_key,
            s3_secret_key=request.s3_credentials.s3_secret_key,
        )

        success = api.delete_file(volume_id, request.remote_path)
        if success:
            return DeleteResponse(
                success=True, message=f"File {request.remote_path} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"File {request.remote_path} not found"
            )
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/datacenters",
    response_model=List[DatacenterInfo],
    summary="List available datacenters",
    description="Get information about available Runpod datacenters for volume creation.",
)
async def list_datacenters(
    api: RunpodStorageAPI = Depends(get_storage_api),
) -> List[DatacenterInfo]:
    """List available datacenters."""
    datacenters = api.get_available_datacenters()

    datacenter_names = {
        "EUR-IS-1": "Europe - Iceland",
        "EU-RO-1": "Europe - Romania",
        "EU-CZ-1": "Europe - Czech Republic",
        "US-KS-2": "USA - Kansas",
    }

    return [
        DatacenterInfo(
            id=dc_id,
            name=datacenter_names.get(dc_id, dc_id),
            s3_endpoint=endpoint,
            region=dc_id,
        )
        for dc_id, endpoint in datacenters.items()
    ]
