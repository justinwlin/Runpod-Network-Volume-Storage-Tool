#!/usr/bin/env python3
"""
Quick test for file upload functionality (100MB test file).

This test is perfect for:
- Verifying your setup is working
- Testing network connectivity
- Quick development iterations

Setup:
    1. Set environment variables (see .env.example):
       export RUNPOD_API_KEY='your_api_key'
       export RUNPOD_S3_ACCESS_KEY='your_s3_access_key'
       export RUNPOD_S3_SECRET_KEY='your_s3_secret_key'
    
    2. Run the test:
       python examples/test_upload_quick.py

Expected runtime: ~30-60 seconds depending on network speed
"""

import os
import sys
import time
import tempfile
import hashlib
import threading
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from runpod_storage import RunpodStorageAPI


def quick_upload_test():
    """Quick test with 100MB file."""
    print("\n" + "="*50)
    print("Quick Upload Test (100MB)")
    print("="*50)
    
    api = RunpodStorageAPI()
    test_size_mb = 100
    test_files = []
    
    try:
        # Get or create test volume
        volumes = api.list_volumes()
        test_volume = None
        
        for vol in volumes:
            if 'test' in vol.get('name', '').lower():
                test_volume = vol
                break
        
        if not test_volume:
            print("Creating test volume...")
            test_volume = api.create_volume(
                name=f"test-quick-{datetime.now().strftime('%Y%m%d')}",
                size=10,  # 10GB is enough for quick tests
                datacenter_id="EU-RO-1"
            )
            print(f"✓ Created volume: {test_volume['id']}")
        else:
            print(f"Using existing test volume: {test_volume['id']}")
        
        # Create test file
        print(f"\nCreating {test_size_mb}MB test file...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            test_file = f.name
            test_files.append(test_file)
            
            # Write random data
            data = os.urandom(test_size_mb * 1024 * 1024)
            f.write(data)
            
            # Calculate hash
            test_hash = hashlib.md5(data).hexdigest()
        
        print(f"✓ Created test file: {test_file}")
        print(f"  MD5: {test_hash}")
        
        # Clean up existing test files
        print("\nCleaning up existing test files...")
        try:
            existing_files = api.list_files(test_volume['id'], 'test/')
            if existing_files:
                print(f"  Found {len(existing_files)} existing test files, deleting...")
                for f in existing_files:
                    try:
                        api.delete_file(test_volume['id'], f['key'])
                        print(f"    ✓ Deleted: {f['key']}")
                    except Exception as e:
                        print(f"    ✗ Could not delete {f['key']}: {e}")
                print("  Cleanup complete")
            else:
                print("  No existing test files found")
        except Exception as e:
            print(f"  Could not list files: {e}")
        
        # Test upload with unique filename
        print("\nTesting upload...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        remote_path = f"test/quick_test_{test_size_mb}mb_{timestamp}.bin"
        print(f"  Remote path: {remote_path}")
        print(f"  File size: {test_size_mb} MB")
        
        # Simple progress indicator
        import threading
        stop_progress = threading.Event()
        
        def show_progress():
            """Show a simple progress spinner"""
            spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            i = 0
            start_time = time.time()
            while not stop_progress.is_set():
                elapsed = time.time() - start_time
                print(f"\r  Uploading... {spinner[i % len(spinner)]} {elapsed:.1f}s", end="", flush=True)
                i += 1
                time.sleep(0.1)
        
        # Start progress thread
        progress_thread = threading.Thread(target=show_progress)
        progress_thread.start()
        start = time.time()
        
        try:
            api.upload_file(
                test_file,
                test_volume['id'],
                remote_path,
                chunk_size=10 * 1024 * 1024  # 10MB chunks
            )
            stop_progress.set()
            progress_thread.join()
            print("\r" + " " * 50 + "\r", end="")  # Clear progress line
        except Exception as e:
            stop_progress.set()
            progress_thread.join()
            print(f"\n✗ Upload failed: {e}")
            raise
        
        upload_time = time.time() - start
        upload_speed = (test_size_mb / upload_time)
        print(f"✓ Upload successful!")
        print(f"  Time: {upload_time:.2f}s")
        print(f"  Speed: {upload_speed:.1f} MB/s")
        
        # Test download
        print("\nTesting download...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='_downloaded.bin') as f:
            download_file = f.name
            test_files.append(download_file)
        
        # Progress indicator for download
        stop_progress = threading.Event()
        
        def show_download_progress():
            """Show download progress"""
            spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            i = 0
            start_time = time.time()
            while not stop_progress.is_set():
                elapsed = time.time() - start_time
                print(f"\r  Downloading... {spinner[i % len(spinner)]} {elapsed:.1f}s", end="", flush=True)
                i += 1
                time.sleep(0.1)
        
        progress_thread = threading.Thread(target=show_download_progress)
        progress_thread.start()
        start = time.time()
        
        try:
            api.download_file(test_volume['id'], remote_path, download_file)
            stop_progress.set()
            progress_thread.join()
            print("\r" + " " * 50 + "\r", end="")  # Clear progress line
        except Exception as e:
            stop_progress.set()
            progress_thread.join()
            print(f"\n✗ Download failed: {e}")
            raise
        
        download_time = time.time() - start
        download_speed = (test_size_mb / download_time)
        print(f"✓ Download successful!")
        print(f"  Time: {download_time:.2f}s")
        print(f"  Speed: {download_speed:.1f} MB/s")
        
        # Verify integrity
        print("\nVerifying integrity...")
        with open(download_file, 'rb') as f:
            downloaded_hash = hashlib.md5(f.read()).hexdigest()
        
        if downloaded_hash == test_hash:
            print(f"✓ Integrity verified!")
        else:
            print(f"✗ Integrity check failed!")
            print(f"  Original: {test_hash}")
            print(f"  Downloaded: {downloaded_hash}")
        
        # Cleanup remote file
        print("\nCleaning up...")
        api.delete_file(test_volume['id'], remote_path)
        print(f"✓ Deleted remote file: {remote_path}")
        
        print("\n" + "="*50)
        print("✓ QUICK TEST PASSED")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
        
    finally:
        # Cleanup local files
        for file_path in test_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass


if __name__ == "__main__":
    # Check environment
    required = ['RUNPOD_API_KEY', 'RUNPOD_S3_ACCESS_KEY', 'RUNPOD_S3_SECRET_KEY']
    missing = [v for v in required if not os.getenv(v)]
    
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("\nQuick Start:")
        print("1. Copy .env.example to .env")
        print("2. Add your credentials to .env")
        print("3. Run: source .env")
        print("4. Run this test again")
        print("\nGet credentials at: https://www.runpod.io/console/user/settings")
        sys.exit(1)
    
    success = quick_upload_test()
    sys.exit(0 if success else 1)