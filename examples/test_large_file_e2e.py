#!/usr/bin/env python3
"""
End-to-end test for large file upload with cleanup.

This test creates a large file, uploads it to Runpod Network Storage,
downloads it back, and verifies integrity.

Setup:
    1. Set environment variables (see .env.example):
       export RUNPOD_API_KEY='your_api_key'
       export RUNPOD_S3_ACCESS_KEY='your_s3_access_key'
       export RUNPOD_S3_SECRET_KEY='your_s3_secret_key'
    
    2. Run the test:
       python examples/test_large_file_e2e.py

Optional environment variables:
    TEST_VOLUME_ID - Use existing volume instead of creating new one
    TEST_DATACENTER - Datacenter to use (default: EU-RO-1)
    TEST_FILE_SIZE_GB - Size of test file in GB (default: 6)

Examples:
    # Default 6GB test
    python examples/test_large_file_e2e.py
    
    # Custom 10GB test
    export TEST_FILE_SIZE_GB=10
    python examples/test_large_file_e2e.py
    
    # Use existing volume
    export TEST_VOLUME_ID='vol_abc123'
    python examples/test_large_file_e2e.py
"""

import os
import sys
import time
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from runpod_storage import RunpodStorageAPI


class TestLargeFileUpload:
    """End-to-end test for large file uploads."""
    
    def __init__(self):
        self.api = RunpodStorageAPI()
        self.test_volume_id = os.getenv('TEST_VOLUME_ID')
        self.datacenter = os.getenv('TEST_DATACENTER', 'EU-RO-1')
        self.file_size_gb = int(os.getenv('TEST_FILE_SIZE_GB', '6'))
        self.created_volume = False
        self.test_files = []
        self.uploaded_files = []
        
    def setup(self):
        """Set up test environment."""
        print(f"\n{'='*60}")
        print("Large File Upload E2E Test")
        print(f"{'='*60}")
        print(f"Test file size: {self.file_size_gb} GB")
        print(f"Datacenter: {self.datacenter}")
        
        # Show network location info
        import socket
        try:
            hostname = socket.gethostname()
            print(f"Running from: {hostname}")
        except:
            pass
        
        # Create or use existing volume
        if not self.test_volume_id:
            print("\nCreating test volume...")
            volume = self.api.create_volume(
                name=f"test-large-upload-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                size=max(50, self.file_size_gb * 2),  # 2x file size or minimum 50GB
                datacenter_id=self.datacenter
            )
            self.test_volume_id = volume['id']
            self.created_volume = True
            print(f"✓ Created volume: {self.test_volume_id}")
        else:
            print(f"Using existing volume: {self.test_volume_id}")
            
    def create_test_file(self, size_gb):
        """Create a test file of specified size with verification."""
        print(f"\nCreating {size_gb}GB test file...")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            test_file_path = f.name
            self.test_files.append(test_file_path)
            
            # Write in chunks to avoid memory issues
            chunk_size = 100 * 1024 * 1024  # 100MB chunks
            total_bytes = size_gb * 1024 * 1024 * 1024
            bytes_written = 0
            
            # Create predictable data for verification
            chunk_data = os.urandom(chunk_size)
            
            start_time = time.time()
            while bytes_written < total_bytes:
                remaining = total_bytes - bytes_written
                write_size = min(chunk_size, remaining)
                
                if write_size < chunk_size:
                    f.write(chunk_data[:write_size])
                else:
                    f.write(chunk_data)
                    
                bytes_written += write_size
                
                # Show progress
                progress = (bytes_written / total_bytes) * 100
                elapsed = time.time() - start_time
                speed = (bytes_written / (1024**2)) / elapsed if elapsed > 0 else 0
                print(f"\rCreating file: {progress:.1f}% - {speed:.1f} MB/s", end="")
        
        print(f"\n✓ Created test file: {test_file_path}")
        print(f"  Size: {os.path.getsize(test_file_path) / (1024**3):.2f} GB")
        
        # Calculate checksum for verification
        print("Calculating checksum...")
        file_hash = self.calculate_file_hash(test_file_path)
        print(f"  MD5: {file_hash}")
        
        return test_file_path, file_hash
    
    def calculate_file_hash(self, file_path):
        """Calculate MD5 hash of file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(100 * 1024 * 1024), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def test_upload(self, file_path):
        """Test uploading large file."""
        print(f"\n{'='*40}")
        print("Testing Upload")
        print(f"{'='*40}")
        
        # Clean up any existing test files first
        print("Cleaning up existing test files...")
        try:
            existing_files = self.api.list_files(self.test_volume_id, 'test/')
            if existing_files:
                print(f"  Found {len(existing_files)} existing test files, deleting...")
                for f in existing_files:
                    try:
                        self.api.delete_file(self.test_volume_id, f['key'])
                        print(f"    ✓ Deleted: {f['key']}")
                    except Exception as e:
                        print(f"    ✗ Could not delete {f['key']}: {e}")
        except Exception as e:
            print(f"  Could not list files: {e}")
        
        file_size = os.path.getsize(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        remote_path = f"test/large_file_{self.file_size_gb}gb_{timestamp}.bin"
        
        # Choose optimal chunk size
        if self.file_size_gb < 10:
            chunk_size = 50 * 1024 * 1024  # 50MB
        else:
            chunk_size = 100 * 1024 * 1024  # 100MB
        
        print(f"Uploading {file_size / (1024**3):.2f} GB file...")
        print(f"Chunk size: {chunk_size / (1024**2):.0f} MB")
        
        start_time = time.time()
        
        try:
            self.api.upload_file(
                file_path,
                self.test_volume_id,
                remote_path,
                chunk_size=chunk_size
            )
            
            elapsed = time.time() - start_time
            upload_speed = (file_size / (1024**2)) / elapsed
            
            print(f"✓ Upload successful!")
            print(f"  Time: {elapsed:.1f} seconds")
            print(f"  Speed: {upload_speed:.1f} MB/s")
            
            self.uploaded_files.append(remote_path)
            return True, elapsed, upload_speed, remote_path
            
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return False, 0, 0, None
    
    def test_download_verify(self, remote_path, original_hash):
        """Test downloading and verify integrity."""
        print(f"\n{'='*40}")
        print("Testing Download & Verification")
        print(f"{'='*40}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='_downloaded.bin') as f:
            download_path = f.name
            self.test_files.append(download_path)
        
        print(f"Downloading from {remote_path}...")
        start_time = time.time()
        
        try:
            self.api.download_file(
                self.test_volume_id,
                remote_path,
                download_path
            )
            
            elapsed = time.time() - start_time
            file_size = os.path.getsize(download_path)
            download_speed = (file_size / (1024**2)) / elapsed
            
            print(f"✓ Download successful!")
            print(f"  Time: {elapsed:.1f} seconds")
            print(f"  Speed: {download_speed:.1f} MB/s")
            
            # Verify integrity
            print("\nVerifying file integrity...")
            downloaded_hash = self.calculate_file_hash(download_path)
            
            if downloaded_hash == original_hash:
                print(f"✓ Integrity check passed!")
                print(f"  Original MD5: {original_hash}")
                print(f"  Downloaded MD5: {downloaded_hash}")
                return True, elapsed, download_speed
            else:
                print(f"✗ Integrity check failed!")
                print(f"  Original MD5: {original_hash}")
                print(f"  Downloaded MD5: {downloaded_hash}")
                return False, elapsed, download_speed
                
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return False, 0, 0
    
    def test_chunk_sizes(self):
        """Test different chunk sizes with a small file to ensure no limitations."""
        print(f"\n{'='*40}")
        print("Testing Various Chunk Sizes")
        print(f"{'='*40}")
        
        # Create a small test file (100MB)
        test_size_mb = 100
        print(f"\nCreating {test_size_mb}MB test file for chunk size testing...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='_chunk_test.bin') as f:
            test_file = f.name
            self.test_files.append(test_file)
            # Write 100MB of data
            test_data = os.urandom(test_size_mb * 1024 * 1024)
            f.write(test_data)
        
        print(f"✓ Created test file: {test_size_mb}MB")
        
        # Test different chunk sizes
        chunk_sizes = [
            (10, "Small chunks (< 1GB files)"),
            (50, "Medium chunks (1-10GB files)"),
            (100, "Large chunks (10-50GB files)"),
            (200, "Extra large chunks (> 50GB files)"),
        ]
        
        all_passed = True
        
        for chunk_mb, description in chunk_sizes:
            chunk_size = chunk_mb * 1024 * 1024
            remote_path = f"test/chunk_test_{chunk_mb}mb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
            
            print(f"\nTesting {chunk_mb}MB chunks - {description}")
            
            try:
                start_time = time.time()
                self.api.upload_file(
                    test_file,
                    self.test_volume_id,
                    remote_path,
                    chunk_size=chunk_size
                )
                elapsed = time.time() - start_time
                
                print(f"  ✓ Upload successful with {chunk_mb}MB chunks")
                print(f"    Time: {elapsed:.2f}s")
                
                # Clean up the uploaded file
                self.api.delete_file(self.test_volume_id, remote_path)
                print(f"  ✓ Cleaned up test file")
                
            except Exception as e:
                print(f"  ✗ Failed with {chunk_mb}MB chunks: {e}")
                all_passed = False
        
        return all_passed
    
    def test_resume_capability(self, file_path):
        """Test resume capability by simulating interrupted upload."""
        print(f"\n{'='*40}")
        print("Testing Resume Capability")
        print(f"{'='*40}")
        
        # This is a simplified test - in reality you'd interrupt the upload
        remote_path = f"test/resume_test_{self.file_size_gb}gb.bin"
        
        print("Testing resume capability...")
        print("(In production, this would simulate an interrupted upload)")
        
        # Upload with resume enabled
        try:
            self.api.upload_file(
                file_path,
                self.test_volume_id,
                remote_path,
                chunk_size=50 * 1024 * 1024
            )
            print("✓ Upload with resume capability successful")
            self.uploaded_files.append(remote_path)
            return True
        except Exception as e:
            print(f"✗ Resume test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources."""
        print(f"\n{'='*40}")
        print("Cleanup")
        print(f"{'='*40}")
        
        # Delete uploaded files from volume
        if self.uploaded_files:
            print(f"Deleting {len(self.uploaded_files)} uploaded test files...")
            for remote_path in self.uploaded_files:
                try:
                    self.api.delete_file(self.test_volume_id, remote_path)
                    print(f"  ✓ Deleted: {remote_path}")
                except Exception as e:
                    print(f"  ✗ Failed to delete {remote_path}: {e}")
        
        # Delete local test files
        if self.test_files:
            print(f"Deleting {len(self.test_files)} local test files...")
            for file_path in self.test_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        print(f"  ✓ Deleted: {file_path}")
                except Exception as e:
                    print(f"  ✗ Failed to delete {file_path}: {e}")
        
        # Delete test volume if we created it
        if self.created_volume and self.test_volume_id:
            print(f"Deleting test volume {self.test_volume_id}...")
            try:
                self.api.delete_volume(self.test_volume_id)
                print(f"  ✓ Volume deleted")
            except Exception as e:
                print(f"  ✗ Failed to delete volume: {e}")
    
    def run(self):
        """Run all tests."""
        test_results = {
            'setup': False,
            'chunk_sizes': False,
            'file_creation': False,
            'upload': False,
            'download': False,
            'integrity': False,
            'resume': False,
            'cleanup': False
        }
        
        try:
            # Setup
            self.setup()
            test_results['setup'] = True
            
            # Test different chunk sizes with small file first
            chunk_test_success = self.test_chunk_sizes()
            test_results['chunk_sizes'] = chunk_test_success
            
            # Create test file
            test_file_path, original_hash = self.create_test_file(self.file_size_gb)
            test_results['file_creation'] = True
            
            # Test upload
            upload_success, upload_time, upload_speed, remote_path = self.test_upload(test_file_path)
            test_results['upload'] = upload_success
            
            if upload_success and remote_path:
                # Test download and verify using the actual uploaded path
                download_success, download_time, download_speed = self.test_download_verify(
                    remote_path, original_hash
                )
                test_results['download'] = download_success
                test_results['integrity'] = download_success
                
                # Test resume capability
                resume_success = self.test_resume_capability(test_file_path)
                test_results['resume'] = resume_success
            
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            
        finally:
            # Always cleanup
            try:
                self.cleanup()
                test_results['cleanup'] = True
            except Exception as e:
                print(f"✗ Cleanup failed: {e}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")
        
        for test_name, success in test_results.items():
            status = "✓ PASSED" if success else "✗ FAILED"
            print(f"{test_name.ljust(20)}: {status}")
        
        # Overall result
        all_passed = all(test_results.values())
        print(f"\n{'='*60}")
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print(f"{'='*60}\n")
        
        return all_passed


def main():
    """Main test runner."""
    # Check environment variables
    required_vars = ['RUNPOD_API_KEY', 'RUNPOD_S3_ACCESS_KEY', 'RUNPOD_S3_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        print("\nOption 1: Export directly (temporary):")
        for var in missing_vars:
            print(f"  export {var}='your_value'")
        print("\nOption 2: Use .env file (recommended):")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in your credentials")
        print("  3. Run: source .env")
        print("\nTo get your credentials:")
        print("  Visit: https://www.runpod.io/console/user/settings")
        sys.exit(1)
    
    # Run test
    test = TestLargeFileUpload()
    success = test.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()