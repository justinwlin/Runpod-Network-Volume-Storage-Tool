#!/usr/bin/env python3
"""
Basic usage examples for Runpod Storage.

This script demonstrates the most common operations:
- Listing volumes
- Creating volumes
- Uploading and downloading files
- Error handling
"""

import os
import tempfile
from pathlib import Path

from runpod_storage import (
    RunpodStorageAPI,
    VolumeNotFoundError,
    AuthenticationError,
    InsufficientStorageError
)


def main():
    """Demonstrate basic Runpod Storage operations."""
    
    # Initialize API (requires RUNPOD_API_KEY environment variable)
    try:
        api = RunpodStorageAPI()
        print("✅ Successfully initialized Runpod Storage API")
    except AuthenticationError:
        print("❌ Authentication failed. Please set RUNPOD_API_KEY environment variable")
        return
    
    print("\n" + "="*50)
    print("BASIC RUNPOD STORAGE OPERATIONS")
    print("="*50)
    
    # 1. List existing volumes
    print("\n1. Listing existing volumes...")
    try:
        volumes = api.list_volumes()
        print(f"   Found {len(volumes)} volumes:")
        for volume in volumes:
            print(f"   • {volume['name']} ({volume['id']}) - {volume['size']}GB in {volume['dataCenterId']}")
    except Exception as e:
        print(f"   ❌ Error listing volumes: {e}")
        return
    
    # 2. Create a new volume (if needed)
    print("\n2. Creating a new volume...")
    test_volume_name = "demo-volume"
    
    # Check if demo volume already exists
    existing_volume = None
    for volume in volumes:
        if volume['name'] == test_volume_name:
            existing_volume = volume
            break
    
    if existing_volume:
        print(f"   ℹ️  Volume '{test_volume_name}' already exists, using existing one")
        volume_id = existing_volume['id']
    else:
        try:
            print(f"   Creating volume '{test_volume_name}' (10GB in EU-RO-1)...")
            new_volume = api.create_volume(test_volume_name, 10, "EU-RO-1")
            volume_id = new_volume['id']
            print(f"   ✅ Created volume: {volume_id}")
        except Exception as e:
            print(f"   ❌ Error creating volume: {e}")
            return
    
    # 3. File operations (requires S3 credentials)
    if not os.getenv("RUNPOD_S3_ACCESS_KEY") or not os.getenv("RUNPOD_S3_SECRET_KEY"):
        print("\n3. File operations...")
        print("   ⚠️  S3 credentials not found, skipping file operations")
        print("   To enable file operations, set RUNPOD_S3_ACCESS_KEY and RUNPOD_S3_SECRET_KEY")
    else:
        demonstrate_file_operations(api, volume_id)
    
    # 4. Error handling demonstration
    print("\n4. Demonstrating error handling...")
    demonstrate_error_handling(api)
    
    print("\n" + "="*50)
    print("DEMO COMPLETED SUCCESSFULLY! 🎉")
    print("="*50)
    print("\nNext steps:")
    print("• Explore the CLI: runpod-storage interactive")
    print("• Check the documentation: https://runpod.github.io/runpod-storage")
    print("• Try the API server: runpod-storage-server")


def demonstrate_file_operations(api: RunpodStorageAPI, volume_id: str):
    """Demonstrate file upload/download operations."""
    
    print("\n3. File operations...")
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_content = "Hello from Runpod Storage!\nThis is a demonstration file.\n"
        f.write(test_content)
        test_file_path = f.name
    
    try:
        # Upload file
        remote_path = "demo/test-file.txt"
        print(f"   Uploading file to {remote_path}...")
        success = api.upload_file(test_file_path, volume_id, remote_path)
        if success:
            print("   ✅ File uploaded successfully")
        else:
            print("   ❌ File upload failed")
            return
        
        # List files
        print(f"   Listing files in volume...")
        files = api.list_files(volume_id)
        print(f"   Found {len(files)} files:")
        for file_info in files:
            size_kb = file_info['size'] / 1024
            print(f"     • {file_info['key']} ({size_kb:.1f} KB)")
        
        # Download file
        download_path = "downloaded-demo-file.txt"
        print(f"   Downloading file to {download_path}...")
        success = api.download_file(volume_id, remote_path, download_path)
        if success:
            print("   ✅ File downloaded successfully")
            
            # Verify content
            with open(download_path, 'r') as f:
                downloaded_content = f.read()
            
            if downloaded_content == test_content:
                print("   ✅ File content verified - download successful!")
            else:
                print("   ⚠️  Downloaded content doesn't match original")
        else:
            print("   ❌ File download failed")
        
        # Clean up
        print("   Cleaning up...")
        api.delete_file(volume_id, remote_path)
        os.unlink(test_file_path)
        if Path(download_path).exists():
            os.unlink(download_path)
        print("   ✅ Cleanup completed")
        
    except Exception as e:
        print(f"   ❌ Error during file operations: {e}")
        # Clean up on error
        try:
            os.unlink(test_file_path)
        except:
            pass
        try:
            if Path(download_path).exists():
                os.unlink(download_path)
        except:
            pass


def demonstrate_error_handling(api: RunpodStorageAPI):
    """Demonstrate proper error handling."""
    
    print("   Testing error handling scenarios...")
    
    # Test 1: Non-existent volume
    try:
        api.get_volume("non-existent-volume-id")
        print("   ⚠️  Expected VolumeNotFoundError but didn't get one")
    except VolumeNotFoundError:
        print("   ✅ VolumeNotFoundError handled correctly")
    except Exception as e:
        print(f"   ⚠️  Unexpected error type: {type(e).__name__}: {e}")
    
    # Test 2: Invalid volume name (if we had validation)
    try:
        # This might not actually fail depending on API validation
        result = api.create_volume("", 10, "EU-RO-1")
        print("   ⚠️  Empty volume name was accepted (API allows this)")
    except Exception as e:
        print(f"   ✅ Invalid volume name rejected: {type(e).__name__}")
    
    print("   ✅ Error handling demonstration completed")


if __name__ == "__main__":
    main()