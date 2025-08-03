"""
API routes for Runpod Storage server.

Implements all REST endpoints with comprehensive validation and error handling.
"""

import os
import tempfile
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
    DeleteResponse,
    DownloadResponse,
    ListFilesResponse,
    ListVolumesResponse,
    NetworkVolume,
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
    }
)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    api_key_header: str = None,
    api_key_query: str = None
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
        detail="API key required. Use Authorization header, X-API-Key header, or api_key query parameter."
    )


async def get_storage_api(api_key: str = Depends(get_api_key)) -> RunpodStorageAPI:
    """Get authenticated storage API instance."""
    try:
        return RunpodStorageAPI(api_key=api_key)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize storage API: {e}"
        )


@router.get(
    "/volumes",
    response_model=ListVolumesResponse,
    summary="List network volumes",
    description="Retrieve a list of all network volumes associated with your account."
)
async def list_volumes(api: RunpodStorageAPI = Depends(get_storage_api)) -> ListVolumesResponse:
    """List all network volumes."""
    try:
        volumes = api.list_volumes()
        return ListVolumesResponse(
            volumes=[NetworkVolume(**vol) for vol in volumes],
            total_count=len(volumes)
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
    description="Create a new network volume with specified name, size, and datacenter."
)
async def create_volume(
    request: CreateVolumeRequest,
    api: RunpodStorageAPI = Depends(get_storage_api)
) -> NetworkVolume:
    """Create a new network volume."""
    try:
        volume = api.create_volume(
            name=request.name,
            size=request.size,
            datacenter_id=request.datacenter_id
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
    description="Retrieve detailed information about a specific network volume."
)
async def get_volume(
    volume_id: str,
    api: RunpodStorageAPI = Depends(get_storage_api)
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


@router.delete(
    "/volumes/{volume_id}",
    response_model=DeleteResponse,
    summary="Delete volume",
    description="Delete a network volume. This operation is irreversible."
)
async def delete_volume(
    volume_id: str,
    api: RunpodStorageAPI = Depends(get_storage_api)
) -> DeleteResponse:
    """Delete a network volume."""
    try:
        success = api.delete_volume(volume_id)
        if success:
            return DeleteResponse(success=True, message=f"Volume {volume_id} deleted successfully")
        else:
            raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/volumes/{volume_id}/files",
    response_model=ListFilesResponse,
    summary="List files in volume",
    description="List all files in a network volume, optionally filtered by prefix."
)
async def list_files(
    volume_id: str,
    prefix: str = "",
    api: RunpodStorageAPI = Depends(get_storage_api)
) -> ListFilesResponse:
    """List files in a volume."""
    try:
        files = api.list_files(volume_id, prefix)
        return ListFilesResponse(
            files=files,
            total_count=len(files),
            prefix=prefix if prefix else None
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
    description="Upload a file to a network volume. Supports large files via multipart upload."
)
async def upload_file(
    volume_id: str,
    file: UploadFile = File(..., description="File to upload"),
    remote_path: str = Form(None, description="Remote path for the file"),
    chunk_size: int = Form(50 * 1024 * 1024, description="Chunk size for multipart upload"),
    api: RunpodStorageAPI = Depends(get_storage_api)
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
        
        success = api.upload_file(tmp_file_path, volume_id, remote_path, chunk_size)
        
        upload_time = time.time() - start_time
        file_size = len(content)
        speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
        
        return UploadResponse(
            success=success,
            file_path=remote_path,
            size=file_size,
            upload_time=upload_time,
            speed_mbps=speed_mbps
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


@router.get(
    "/volumes/{volume_id}/files/{file_path:path}",
    response_class=FileResponse,
    summary="Download file",
    description="Download a file from a network volume."
)
async def download_file(
    volume_id: str,
    file_path: str,
    api: RunpodStorageAPI = Depends(get_storage_api)
) -> FileResponse:
    """Download a file from a volume."""
    
    # Create temporary file for download
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file_path = tmp_file.name
    
    try:
        success = api.download_file(volume_id, file_path, tmp_file_path)
        
        if success:
            filename = os.path.basename(file_path)
            return FileResponse(
                path=tmp_file_path,
                filename=filename,
                media_type="application/octet-stream"
            )
        else:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/volumes/{volume_id}/files/{file_path:path}",
    response_model=DeleteResponse,
    summary="Delete file",
    description="Delete a file from a network volume."
)
async def delete_file(
    volume_id: str,
    file_path: str,
    api: RunpodStorageAPI = Depends(get_storage_api)
) -> DeleteResponse:
    """Delete a file from a volume."""
    try:
        success = api.delete_file(volume_id, file_path)
        if success:
            return DeleteResponse(success=True, message=f"File {file_path} deleted successfully")
        else:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except VolumeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    except NetworkError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except RunpodStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/datacenters",
    response_model=List[DatacenterInfo],
    summary="List datacenters",
    description="Get information about available Runpod datacenters."
)
async def list_datacenters(api: RunpodStorageAPI = Depends(get_storage_api)) -> List[DatacenterInfo]:
    """List available datacenters."""
    datacenters = api.get_available_datacenters()
    
    datacenter_names = {
        "EUR-IS-1": "Europe - Iceland",
        "EU-RO-1": "Europe - Romania", 
        "EU-CZ-1": "Europe - Czech Republic",
        "US-KS-2": "USA - Kansas"
    }
    
    return [
        DatacenterInfo(
            id=dc_id,
            name=datacenter_names.get(dc_id, dc_id),
            s3_endpoint=endpoint,
            region=dc_id
        )
        for dc_id, endpoint in datacenters.items()
    ]