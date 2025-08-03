"""Runpod API client for network volume operations."""

import os
import logging
from typing import Dict, List, Optional, Any
import requests


logger = logging.getLogger(__name__)


class RunpodClient:
    """Client for Runpod REST API operations."""
    
    BASE_URL = "https://rest.runpod.io/v1"
    
    # Available datacenters with S3 endpoints
    DATACENTERS = {
        "EUR-IS-1": "https://s3api-eur-is-1.runpod.io/",
        "EU-RO-1": "https://s3api-eu-ro-1.runpod.io/",
        "EU-CZ-1": "https://s3api-eu-cz-1.runpod.io/",
        "US-KS-2": "https://s3api-us-ks-2.runpod.io/",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Runpod client.
        
        Args:
            api_key: Runpod API key. If not provided, will try to get from RUNPOD_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Runpod API key required. Set RUNPOD_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Runpod API."""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Response content: {e.response.text}")
            raise
    
    def list_network_volumes(self) -> List[Dict[str, Any]]:
        """List all network volumes."""
        try:
            # The API endpoint might be /networkvolumes or similar
            # Let's try the most likely endpoint first
            response = self._make_request("GET", "/networkvolumes")
            return response if isinstance(response, list) else response.get("networkVolumes", [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Try alternative endpoint
                try:
                    response = self._make_request("GET", "/network-volumes")
                    return response if isinstance(response, list) else response.get("networkVolumes", [])
                except:
                    pass
            raise
    
    def create_network_volume(
        self, 
        name: str, 
        size: int, 
        datacenter_id: str
    ) -> Dict[str, Any]:
        """Create a new network volume.
        
        Args:
            name: Name for the network volume
            size: Size in GB (minimum 1, maximum 4000)
            datacenter_id: Datacenter ID (e.g., 'EU-RO-1')
            
        Returns:
            Created network volume data
        """
        if datacenter_id not in self.DATACENTERS:
            raise ValueError(f"Invalid datacenter. Must be one of: {list(self.DATACENTERS.keys())}")
        
        if not (10 <= size <= 4000):
            raise ValueError("Size must be between 10 and 4000 GB")
        
        data = {
            "name": name,
            "size": size,
            "dataCenterId": datacenter_id
        }
        
        return self._make_request("POST", "/networkvolumes", json=data)
    
    def get_network_volume(self, volume_id: str) -> Dict[str, Any]:
        """Get details of a specific network volume."""
        return self._make_request("GET", f"/networkvolumes/{volume_id}")
    
    def delete_network_volume(self, volume_id: str) -> bool:
        """Delete a network volume."""
        try:
            url = f"{self.BASE_URL}/networkvolumes/{volume_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    def get_s3_endpoint(self, datacenter_id: str) -> str:
        """Get S3 endpoint URL for a datacenter."""
        if datacenter_id not in self.DATACENTERS:
            raise ValueError(f"No S3 endpoint for datacenter {datacenter_id}")
        return self.DATACENTERS[datacenter_id]
    
    @classmethod
    def get_available_datacenters(cls) -> Dict[str, str]:
        """Get available datacenters and their S3 endpoints."""
        return cls.DATACENTERS.copy()