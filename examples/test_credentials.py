#!/usr/bin/env python3
"""
Test script to verify your Runpod credentials are working correctly.

This is the first test you should run to ensure your setup is correct.

Usage:
    1. Set your environment variables:
       export RUNPOD_API_KEY='your_api_key'
       export RUNPOD_S3_ACCESS_KEY='your_s3_access_key'
       export RUNPOD_S3_SECRET_KEY='your_s3_secret_key'
    
    2. Run the test:
       python examples/test_credentials.py

What this tests:
    - API key is valid
    - S3 credentials are valid
    - Can list volumes
    - Can upload/download small test file
    - Can delete files
"""

import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from runpod_storage import RunpodStorageAPI

def test_credentials():
    """Test that credentials are properly configured and working."""
    print("\nTesting Runpod credentials...")
    print("=" * 50)
    
    # Check environment variables first
    required_vars = ['RUNPOD_API_KEY', 'RUNPOD_S3_ACCESS_KEY', 'RUNPOD_S3_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Missing environment variables: {', '.join(missing_vars)}")
        print("\nSetup Instructions:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("\n2. Edit .env and add your credentials")
        print("\n3. Load the environment variables:")
        print("   source .env")
        print("\n4. Run this test again")
        print("\nGet your credentials at:")
        print("  https://www.runpod.io/console/user/settings")
        return False
    
    try:
        # Initialize API
        api = RunpodStorageAPI()
        print("✓ API initialized")
        
        # List volumes
        volumes = api.list_volumes()
        print(f"✓ Found {len(volumes)} volumes")
        
        if not volumes:
            print("\n⚠ No volumes found. Creating a test volume...")
            volume = api.create_volume(
                name="test-credentials",
                size=1,  # 1GB is enough for testing
                datacenter_id="EU-RO-1"
            )
            volumes = [volume]
            print(f"✓ Created test volume: {volume['id']}")
        
        # Test file operations on first volume
        volume_id = volumes[0]['id']
        volume_name = volumes[0].get('name', 'unnamed')
        print(f"\nTesting file operations on volume: {volume_name} ({volume_id})")
        
        # List files
        files = api.list_files(volume_id)
        print(f"✓ Listed {len(files)} files")
        
        # Create tiny test file
        test_content = b"Test data for credential verification"
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(test_content)
            test_file = f.name
        
        try:
            # Upload
            print("\nTesting upload...")
            api.upload_file(test_file, volume_id, "test/credential_test.txt")
            print("✓ Upload successful")
            
            # Download
            print("Testing download...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='_downloaded.txt') as f:
                download_file = f.name
            
            api.download_file(volume_id, "test/credential_test.txt", download_file)
            print("✓ Download successful")
            
            # Verify content
            with open(download_file, 'rb') as f:
                content = f.read()
            
            if content == test_content:
                print("✓ Content verified")
            else:
                print("✗ Content mismatch")
                return False
            
            # Cleanup remote file
            api.delete_file(volume_id, "test/credential_test.txt")
            print("✓ Cleanup successful")
            
            # Cleanup local files
            os.unlink(test_file)
            os.unlink(download_file)
            
        except Exception as e:
            print(f"✗ File operation failed: {e}")
            # Try to clean up
            try:
                if os.path.exists(test_file):
                    os.unlink(test_file)
                if 'download_file' in locals() and os.path.exists(download_file):
                    os.unlink(download_file)
            except:
                pass
            return False
        
        print("\n" + "=" * 50)
        print("✓ ALL CREDENTIAL TESTS PASSED")
        print("=" * 50)
        print("\nYour credentials are working correctly!")
        print("You can now run the other tests:")
        print("  python examples/test_upload_quick.py    # Quick 100MB test")
        print("  python examples/test_large_file_e2e.py  # Full 6GB test")
        return True
        
    except Exception as e:
        print(f"\n✗ Credential test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check that your credentials are correct")
        print("2. Ensure you have network connectivity")
        print("3. Verify your Runpod account is active")
        print("\nGet help at: https://discord.gg/runpod")
        return False

if __name__ == "__main__":
    success = test_credentials()
    sys.exit(0 if success else 1)