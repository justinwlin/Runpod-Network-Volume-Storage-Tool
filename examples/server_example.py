#!/usr/bin/env python3
"""
Example of using the Runpod Storage API server programmatically.

This script demonstrates how to interact with the REST API server
using HTTP requests instead of the Python SDK.
"""

import os
import tempfile
from typing import Any, Dict

import requests


class RunpodStorageClient:
    """Simple HTTP client for Runpod Storage API server."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to the API server."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        return self._request("GET", "/health")

    def list_volumes(self) -> Dict[str, Any]:
        """List all volumes."""
        return self._request("GET", "/api/v1/volumes")

    def create_volume(self, name: str, size: int, datacenter_id: str) -> Dict[str, Any]:
        """Create a new volume."""
        data = {"name": name, "size": size, "datacenter_id": datacenter_id}
        return self._request("POST", "/api/v1/volumes", json=data)

    def get_volume(self, volume_id: str) -> Dict[str, Any]:
        """Get volume details."""
        return self._request("GET", f"/api/v1/volumes/{volume_id}")

    def list_files(self, volume_id: str, prefix: str = "") -> Dict[str, Any]:
        """List files in volume."""
        params = {"prefix": prefix} if prefix else {}
        return self._request("GET", f"/api/v1/volumes/{volume_id}/files", params=params)

    def upload_file(
        self, volume_id: str, file_path: str, remote_path: str = None
    ) -> Dict[str, Any]:
        """Upload a file to volume."""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {}
            if remote_path:
                data["remote_path"] = remote_path

            response = self.session.post(
                f"{self.base_url}/api/v1/volumes/{volume_id}/files",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    def download_file(self, volume_id: str, file_path: str, local_path: str):
        """Download a file from volume."""
        response = self.session.get(
            f"{self.base_url}/api/v1/volumes/{volume_id}/files/{file_path}"
        )
        response.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(response.content)

    def delete_file(self, volume_id: str, file_path: str) -> Dict[str, Any]:
        """Delete a file from volume."""
        return self._request("DELETE", f"/api/v1/volumes/{volume_id}/files/{file_path}")

    def list_datacenters(self) -> Dict[str, Any]:
        """List available datacenters."""
        return self._request("GET", "/api/v1/datacenters")


def main():
    """Demonstrate API server usage."""

    print("🌐 Runpod Storage API Server Example")
    print("=" * 50)

    # Initialize client
    client = RunpodStorageClient()

    # Check if server is running
    try:
        health = client.health_check()
        print(f"✅ Server is healthy: {health['status']} (version {health['version']})")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("   Start the server with: runpod-storage-server")
        return
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed - check your API key")
            return
        raise

    # List datacenters
    print("\n📍 Available datacenters:")
    try:
        datacenters = client.list_datacenters()
        for dc in datacenters:
            print(f"   • {dc['id']}: {dc['name']} ({dc['s3_endpoint']})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # List volumes
    print("\n📦 Listing volumes:")
    try:
        volumes_response = client.list_volumes()
        volumes = volumes_response["volumes"]
        print(f"   Found {volumes_response['total_count']} volumes:")
        for volume in volumes:
            print(f"   • {volume['name']} ({volume['id']}) - {volume['size']}GB")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Use first volume for file operations demo
    if volumes:
        volume_id = volumes[0]["id"]
        print(f"\n📁 File operations demo using volume: {volume_id}")

        # Check if S3 credentials are available
        if not os.getenv("RUNPOD_S3_ACCESS_KEY") or not os.getenv(
            "RUNPOD_S3_SECRET_KEY"
        ):
            print("   ⚠️  S3 credentials not set - file operations may fail")
            print(
                "   Set RUNPOD_S3_ACCESS_KEY and RUNPOD_S3_SECRET_KEY to test file operations"
            )

        try:
            # Create test file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(
                    "Hello from API server example!\nTimestamp: " + str(os.time.time())
                )
                test_file = f.name

            # Upload file
            print("   📤 Uploading test file...")
            upload_result = client.upload_file(
                volume_id, test_file, "api-demo/test.txt"
            )
            print(
                f"   ✅ Upload completed: {upload_result['file_path']} ({upload_result['size']} bytes)"
            )

            # List files
            print("   📋 Listing files...")
            files_response = client.list_files(volume_id)
            files = files_response["files"]
            print(f"   Found {files_response['total_count']} files:")
            for file_info in files:
                print(f"     • {file_info['key']} ({file_info['size']} bytes)")

            # Download file
            download_path = "downloaded-api-test.txt"
            print(f"   📥 Downloading file to {download_path}...")
            client.download_file(volume_id, "api-demo/test.txt", download_path)
            print("   ✅ Download completed")

            # Verify download
            with open(download_path) as f:
                content = f.read()
                print(f"   📄 Downloaded content preview: {content[:50]}...")

            # Clean up
            print("   🧹 Cleaning up...")
            client.delete_file(volume_id, "api-demo/test.txt")
            os.unlink(test_file)
            os.unlink(download_path)
            print("   ✅ Cleanup completed")

        except Exception as e:
            print(f"   ❌ File operations error: {e}")
            # Clean up on error
            try:
                os.unlink(test_file)
                os.unlink(download_path)
            except:
                pass

    else:
        print("\n   ℹ️  No volumes found - create one first:")
        print("   curl -X POST http://localhost:8000/api/v1/volumes \\")
        print("     -H 'Authorization: Bearer your-api-key' \\")
        print("     -H 'Content-Type: application/json' \\")
        print(
            '     -d \'{"name": "test-volume", "size": 10, "datacenter_id": "EU-RO-1"}\''
        )

    print("\n" + "=" * 50)
    print("🎉 API Server Demo Completed!")
    print("\n💡 Tips:")
    print("• Visit http://localhost:8000/docs for interactive API documentation")
    print("• Use curl or any HTTP client to interact with the API")
    print("• The server supports multiple authentication methods")


if __name__ == "__main__":
    main()
