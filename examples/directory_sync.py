#!/usr/bin/env python3
"""
Example: Directory Sync with Runpod Storage

This example demonstrates how to use the directory sync functionality
to upload and download entire directory structures with progress tracking.
"""

import os
from pathlib import Path
from runpod_storage import RunpodStorageAPI

def upload_directory_example():
    """Upload a directory with progress tracking and smart exclusions."""
    # Initialize the API
    api = RunpodStorageAPI()
    
    # Create a test directory structure
    test_dir = Path("test_project")
    test_dir.mkdir(exist_ok=True)
    
    # Create some test files
    (test_dir / "src").mkdir(exist_ok=True)
    (test_dir / "src" / "main.py").write_text("print('Hello, World!')")
    (test_dir / "src" / "__pycache__").mkdir(exist_ok=True)
    (test_dir / "src" / "__pycache__" / "main.cpython-39.pyc").write_text("bytecode")
    (test_dir / "README.md").write_text("# Test Project\nThis is a test project.")
    (test_dir / "config.json").write_text('{"name": "test", "version": "1.0.0"}')
    (test_dir / ".DS_Store").write_text("system file")
    (test_dir / "logs").mkdir(exist_ok=True)
    (test_dir / "logs" / "app.log").write_text("Log entries...")
    
    print("📁 Created test directory structure:")
    for file_path in test_dir.rglob('*'):
        if file_path.is_file():
            print(f"  📄 {file_path}")
    
    # Get your volume ID (replace with actual volume ID)
    volumes = api.list_volumes()
    if not volumes:
        print("❌ No volumes found. Please create a volume first.")
        return
    
    volume_id = volumes[0]['id']
    print(f"\n🎯 Uploading to volume: {volume_id}")
    
    # Define progress callback
    def upload_progress(current, total, filename):
        percent = (current / total) * 100
        print(f"  ⬆️  [{current:3d}/{total:3d}] ({percent:5.1f}%) {filename}")
    
    # Upload directory with smart exclusions
    print("\n🚀 Starting directory upload...")
    try:
        api.upload_directory(
            str(test_dir),              # Local directory
            volume_id,                  # Target volume
            "examples/test_project",    # Remote directory
            exclude_patterns=[          # Files to exclude
                "*.log",                # Log files
                "*.DS_Store",           # macOS system files
                "__pycache__/*",        # Python cache
                "*.pyc",                # Python bytecode
                ".git/*",               # Git repository
                "node_modules/*",       # Node.js dependencies
                "*.tmp"                 # Temporary files
            ],
            delete=True,                # Remove remote files not in local
            progress_callback=upload_progress
        )
        print("✅ Directory upload completed successfully!")
        
        # List uploaded files
        print("\n📋 Uploaded files:")
        files = api.list_files(volume_id, "examples/test_project")
        for file_info in files:
            size_mb = file_info['size'] / (1024 * 1024)
            print(f"  📄 {file_info['key']} ({size_mb:.2f} MB)")
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\n🧹 Cleaned up local test directory")


def download_directory_example():
    """Download a directory with progress tracking."""
    api = RunpodStorageAPI()
    
    # Get your volume ID
    volumes = api.list_volumes()
    if not volumes:
        print("❌ No volumes found.")
        return
    
    volume_id = volumes[0]['id']
    print(f"🎯 Downloading from volume: {volume_id}")
    
    # Define progress callback
    def download_progress(current, total, filename):
        percent = (current / total) * 100
        print(f"  ⬇️  [{current:3d}/{total:3d}] ({percent:5.1f}%) {filename}")
    
    # Download directory
    print("\n🚀 Starting directory download...")
    try:
        api.download_directory(
            volume_id,
            "examples/test_project",    # Remote directory
            "downloaded_project",       # Local destination
            progress_callback=download_progress
        )
        print("✅ Directory download completed successfully!")
        
        # Show downloaded structure
        print("\n📁 Downloaded directory structure:")
        download_path = Path("downloaded_project")
        for file_path in download_path.rglob('*'):
            if file_path.is_file():
                print(f"  📄 {file_path}")
                
    except Exception as e:
        print(f"❌ Download failed: {e}")


def sync_with_deletion_example():
    """Example of syncing with deletion of remote files."""
    api = RunpodStorageAPI()
    
    # Get volume
    volumes = api.list_volumes()
    if not volumes:
        print("❌ No volumes found.")
        return
    
    volume_id = volumes[0]['id']
    
    # Create modified local directory
    test_dir = Path("modified_project")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "new_file.txt").write_text("This is a new file")
    (test_dir / "updated_readme.md").write_text("# Updated Project\nThis project has been updated.")
    
    print("🔄 Syncing with deletion enabled...")
    print("This will:")
    print("  ✅ Upload new local files")
    print("  ✅ Update existing files")
    print("  🗑️  Delete remote files not present locally")
    
    def sync_progress(current, total, filename):
        print(f"  🔄 [{current}/{total}] Syncing: {filename}")
    
    try:
        api.upload_directory(
            str(test_dir),
            volume_id,
            "examples/test_project",
            delete=True,  # This will delete remote files not in local directory
            progress_callback=sync_progress
        )
        print("✅ Sync completed!")
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("🚀 Runpod Storage Directory Sync Examples")
    print("=" * 50)
    
    # Make sure you have set your API keys
    if not os.getenv("RUNPOD_API_KEY"):
        print("❌ Please set RUNPOD_API_KEY environment variable")
        exit(1)
    
    if not (os.getenv("RUNPOD_S3_ACCESS_KEY") and os.getenv("RUNPOD_S3_SECRET_KEY")):
        print("❌ Please set RUNPOD_S3_ACCESS_KEY and RUNPOD_S3_SECRET_KEY environment variables")
        exit(1)
    
    print("\n1️⃣  Example 1: Upload Directory with Smart Exclusions")
    print("-" * 50)
    upload_directory_example()
    
    print("\n2️⃣  Example 2: Download Directory with Progress")
    print("-" * 50)
    download_directory_example()
    
    print("\n3️⃣  Example 3: Sync with Deletion")
    print("-" * 50)
    sync_with_deletion_example()
    
    print("\n🎉 All examples completed!")