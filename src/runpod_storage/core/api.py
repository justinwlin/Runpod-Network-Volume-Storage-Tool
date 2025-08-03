"""Programmatic API for Runpod storage operations."""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .client import RunpodClient
from .s3_client import RunpodS3Client
from .exceptions import VolumeNotFoundError, AuthenticationError


logger = logging.getLogger(__name__)


class RunpodStorageAPI:
    """High-level API for Runpod storage operations."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        auto_setup_s3: bool = True
    ):
        """Initialize the Runpod Storage API.
        
        Args:
            api_key: Runpod API key (or from RUNPOD_API_KEY env var)
            s3_access_key: S3 access key (or from RUNPOD_S3_ACCESS_KEY env var)
            s3_secret_key: S3 secret key (or from RUNPOD_S3_SECRET_KEY env var)
            auto_setup_s3: Whether to automatically set up S3 clients
        """
        self.client = RunpodClient(api_key)
        self.s3_clients = {}  # Cache S3 clients by datacenter
        self.s3_access_key = s3_access_key or os.getenv("RUNPOD_S3_ACCESS_KEY")
        self.s3_secret_key = s3_secret_key or os.getenv("RUNPOD_S3_SECRET_KEY")
        self.auto_setup_s3 = auto_setup_s3
    
    def _get_s3_client(self, datacenter_id: str) -> RunpodS3Client:
        """Get or create S3 client for a datacenter."""
        if datacenter_id not in self.s3_clients:
            if not self.s3_access_key or not self.s3_secret_key:
                if self.auto_setup_s3:
                    raise ValueError(
                        "S3 credentials required for file operations. "
                        "Set RUNPOD_S3_ACCESS_KEY and RUNPOD_S3_SECRET_KEY environment variables "
                        "or pass them to the constructor."
                    )
                else:
                    return None
            
            endpoint_url = self.client.get_s3_endpoint(datacenter_id)
            self.s3_clients[datacenter_id] = RunpodS3Client(
                access_key=self.s3_access_key,
                secret_key=self.s3_secret_key,
                region=datacenter_id,
                endpoint_url=endpoint_url
            )
        
        return self.s3_clients[datacenter_id]
    
    # Volume Management
    def list_volumes(self) -> List[Dict[str, Any]]:
        """List all network volumes."""
        return self.client.list_network_volumes()
    
    def create_volume(
        self, 
        name: str, 
        size: int, 
        datacenter_id: str = "EU-RO-1"
    ) -> Dict[str, Any]:
        """Create a new network volume.
        
        Args:
            name: Volume name
            size: Size in GB (1-4000)
            datacenter_id: Datacenter ID
            
        Returns:
            Created volume information
        """
        return self.client.create_network_volume(name, size, datacenter_id)
    
    def get_volume(self, volume_id: str) -> Dict[str, Any]:
        """Get volume details."""
        try:
            return self.client.get_network_volume(volume_id)
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise VolumeNotFoundError(volume_id)
            raise
    
    def delete_volume(self, volume_id: str) -> bool:
        """Delete a volume."""
        return self.client.delete_network_volume(volume_id)
    
    # File Operations
    def list_files(
        self, 
        volume_id: str, 
        prefix: str = ""
    ) -> List[Dict[str, Any]]:
        """List files in a volume.
        
        Args:
            volume_id: Volume ID
            prefix: Optional path prefix
            
        Returns:
            List of file information
        """
        volume = self.get_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        s3_client = self._get_s3_client(datacenter_id)
        return s3_client.list_files(volume_id, prefix)
    
    def upload_file(
        self,
        local_path: Union[str, Path],
        volume_id: str,
        remote_path: Optional[str] = None,
        chunk_size: int = 50 * 1024 * 1024
    ) -> bool:
        """Upload a file to a volume.
        
        Args:
            local_path: Local file path
            volume_id: Volume ID
            remote_path: Remote path (default: filename)
            chunk_size: Chunk size for large files
            
        Returns:
            True if successful
        """
        local_path = Path(local_path)
        if remote_path is None:
            remote_path = local_path.name
        
        volume = self.get_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        s3_client = self._get_s3_client(datacenter_id)
        
        return s3_client.upload_file(
            str(local_path), volume_id, remote_path, chunk_size
        )
    
    def download_file(
        self,
        volume_id: str,
        remote_path: str,
        local_path: Optional[Union[str, Path]] = None
    ) -> bool:
        """Download a file from a volume.
        
        Args:
            volume_id: Volume ID
            remote_path: Remote file path
            local_path: Local path to save (default: filename)
            
        Returns:
            True if successful
        """
        if local_path is None:
            local_path = Path(remote_path).name
        
        volume = self.get_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        s3_client = self._get_s3_client(datacenter_id)
        
        return s3_client.download_file(volume_id, remote_path, str(local_path))
    
    def delete_file(self, volume_id: str, remote_path: str) -> bool:
        """Delete a file from a volume."""
        volume = self.get_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        s3_client = self._get_s3_client(datacenter_id)
        return s3_client.delete_file(volume_id, remote_path)
    
    # Utility methods
    def get_available_datacenters(self) -> Dict[str, str]:
        """Get available datacenters."""
        return self.client.get_available_datacenters()
    
    def volume_exists(self, volume_id: str) -> bool:
        """Check if a volume exists."""
        try:
            self.get_volume(volume_id)
            return True
        except:
            return False
    
    def file_exists(self, volume_id: str, remote_path: str) -> bool:
        """Check if a file exists in a volume."""
        try:
            files = self.list_files(volume_id, remote_path)
            return any(f["key"] == remote_path for f in files)
        except:
            return False


# Convenience functions for quick usage
def list_volumes(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Quick function to list volumes."""
    api = RunpodStorageAPI(api_key)
    return api.list_volumes()


def create_volume(
    name: str,
    size: int,
    datacenter_id: str = "EU-RO-1",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Quick function to create a volume."""
    api = RunpodStorageAPI(api_key)
    return api.create_volume(name, size, datacenter_id)


def upload_file(
    local_path: Union[str, Path],
    volume_id: str,
    remote_path: Optional[str] = None,
    api_key: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None
) -> bool:
    """Quick function to upload a file."""
    api = RunpodStorageAPI(api_key, s3_access_key, s3_secret_key)
    return api.upload_file(local_path, volume_id, remote_path)


def download_file(
    volume_id: str,
    remote_path: str,
    local_path: Optional[Union[str, Path]] = None,
    api_key: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None
) -> bool:
    """Quick function to download a file."""
    api = RunpodStorageAPI(api_key, s3_access_key, s3_secret_key)
    return api.download_file(volume_id, remote_path, local_path)