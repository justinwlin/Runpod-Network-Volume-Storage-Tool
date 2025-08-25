# Runpod Network Volume Storage Tool

A command-line tool for managing Runpod network storage volumes and files. Built to work with Runpod's S3-compatible API for easy file transfers and volume management.

## Table of Contents
- [Getting Started](#getting-started)
- [Installation](#installation)
- [Configuration](#configuration)
- [Using the Interactive Mode](#using-the-interactive-mode)
- [File Browser Guide](#file-browser-guide)
- [Command Line Usage](#command-line-usage)
- [Python SDK Usage](#python-sdk-usage)
- [API Server](#api-server)
- [Troubleshooting](#troubleshooting)

## Getting Started

This tool provides three ways to interact with Runpod network storage:
1. **Interactive CLI** - Menu-driven interface with file browser
2. **Command Line** - Direct commands for automation
3. **Python SDK** - Programmatic access for scripts

### Prerequisites

You'll need API keys from [Runpod Console](https://console.runpod.io/user/settings):
- **Runpod API Key** - For volume management
- **S3 API Keys** - For file operations (access key + secret key)

## Installation

```bash
# Clone the repository
git clone https://github.com/justinwlin/Runpod-Network-Volume-Storage-Tool.git
cd Runpod-Network-Volume-Storage-Tool

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Configuration

Set your API credentials as environment variables:

```bash
# Required for volume operations
export RUNPOD_API_KEY="your_runpod_api_key"

# Required for file operations
export RUNPOD_S3_ACCESS_KEY="your_s3_access_key"
export RUNPOD_S3_SECRET_KEY="your_s3_secret_key"
```

The tool will prompt for credentials if not set.

## Using the Interactive Mode

The interactive mode is the easiest way to get started:

```bash
uv run runpod-storage interactive
```

You'll see a menu with these options:

```
Runpod Storage Manager
1. List volumes
2. Create volume
3. Update volume
4. Delete volume
5. List files
6. Upload file/directory
7. Download file/directory
8. Browse volume files
9. Exit
```

### Common Workflows

#### Creating a Volume
1. Select option 2 (Create volume)
2. Enter a name for your volume
3. Specify size in GB (10-4000)
4. Choose a datacenter location

#### Uploading Files
1. Select option 6 (Upload file/directory)
2. Enter the local file/directory path
3. Select the target volume
4. For directories, choose whether to delete remote files not present locally

#### Downloading Files
1. Select option 7 (Download file/directory)
2. Choose from three download modes:
   - **Browse & Select** (default) - Navigate and select files interactively
   - **Direct File** - Download a specific file by path
   - **Direct Directory** - Download an entire directory by path

## File Browser Guide

The file browser (option 8 or option 7 → Browse & Select) provides an intuitive way to navigate and manage files.

### Navigation Mode

When you start, you're in navigation mode:

```
📂 File Browser - Volume: your-volume-id
Path: /
Mode: NAVIGATION (Press 's' to enter SELECT mode)

Contents
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ #  ┃ Type ┃ Name          ┃    Size ┃ Modified         ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 1  │ 📁   │ workspace/    │      -- │ --               │
│ 2  │ 📁   │ data/         │      -- │ --               │
│ 3  │ 📄   │ config.json   │  1.2 KB │ 2025-08-13 10:30 │
│ 4  │ 📄   │ readme.txt    │   856 B │ 2025-08-13 09:15 │
└────┴──────┴───────────────┴─────────┴──────────────────┘

Commands:
  1     - Enter directory 1
  d 3   - Quick download item 3
  d 1 3 - Download multiple items
  s     - Switch to SELECT mode
  u     - Go up one level
  q     - Quit
```

**Quick Commands in Navigation Mode:**
- Type a number (e.g., `1`) to enter that directory
- Type `d` followed by numbers to download items (e.g., `d 3` or `d 1 3 4`)
- Type `s` to switch to selection mode for more complex operations
- Type `u` to go up one directory level

### Selection Mode

Press `s` to enter selection mode for batch operations:

```
Mode: SELECT (Press 'n' to return to NAVIGATION mode)
Selected: 2 item(s)

Commands:
  n     - Return to NAVIGATION mode
  a 3   - Add item 3 to selection
  r 3   - Remove item 3 from selection
  aa    - Add all items
  ra    - Clear selection
  d     - Download selected items
  q     - Quit
```

Selection mode is useful when you want to:
- Select files from different directories
- Download multiple files/directories as a single zip
- Have more control over what gets downloaded

### Download Options

When downloading, you'll be prompted:
1. **Download as zip?** - Recommended for cloud storage (default: Yes)
2. **Zip filename** - Name for the downloaded zip file

## Command Line Usage

For automation and scripting, use direct commands:

### Volume Management

```bash
# List all volumes
uv run runpod-storage list-volumes

# Create a volume
uv run runpod-storage create-volume --name "my-storage" --size 50 --datacenter EU-RO-1

# Delete a volume (use with caution)
uv run runpod-storage delete-volume volume-id
```

### File Operations

```bash
# Upload a file
uv run runpod-storage upload /path/to/file.txt volume-id

# Upload a directory
uv run runpod-storage upload /path/to/directory volume-id

# Download a file
uv run runpod-storage download volume-id remote/file.txt

# List files in a volume
uv run runpod-storage list-files volume-id
```

## Python SDK Usage

### Quick Start

```python
from runpod_storage import RunpodStorageAPI

# Initialize with environment variables
api = RunpodStorageAPI()

# Or provide credentials directly
api = RunpodStorageAPI(
    api_key="your_runpod_api_key",
    s3_access_key="your_s3_access_key",
    s3_secret_key="your_s3_secret_key"
)
```

### Volume Management

```python
from runpod_storage import RunpodStorageAPI

api = RunpodStorageAPI()

# List all volumes
volumes = api.list_volumes()
for vol in volumes:
    print(f"Volume: {vol['id']} ({vol['name']}) - {vol['size']} GB in {vol['dataCenterId']}")

# Create a new volume
volume = api.create_volume(
    name="ml-datasets",
    size=100,  # GB
    datacenter="EU-RO-1"  # or "US-KS-2", "EU-CZ-1", "EUR-IS-1"
)
print(f"Created volume: {volume['id']}")

# Get specific volume details
volume_info = api.get_volume(volume['id'])
print(f"Volume {volume_info['name']} has {volume_info['size']} GB")

# Update volume (rename and/or expand)
updated = api.update_volume(
    volume['id'],
    name="ml-datasets-v2",  # New name (optional)
    size=200  # Expand to 200 GB (optional, must be larger than current)
)
print(f"Updated: {updated['name']} - {updated['size']} GB")

# Delete volume (use with caution!)
# api.delete_volume(volume['id'])
```

### File Upload Operations

```python
from runpod_storage import RunpodStorageAPI
import os

api = RunpodStorageAPI()
volume_id = "your-volume-id"

# Upload a single file - automatically detects optimal chunk size!
api.upload_file("data.csv", volume_id, "datasets/data.csv")
# Auto-detects: < 1GB: 10MB chunks, 1-10GB: 50MB, 10-50GB: 100MB, >50GB: 200MB

# Upload with progress tracking (still auto-detects chunk size)
def upload_progress(bytes_uploaded, total_bytes, speed_mbps):
    percent = (bytes_uploaded / total_bytes) * 100
    print(f"Upload: {percent:.1f}% - {speed_mbps:.1f} MB/s")

api.upload_file(
    "large_model.bin",
    volume_id,
    "models/large_model.bin",
    progress_callback=upload_progress
)

# Override with custom chunk size if needed (optional)
api.upload_file(
    "huge_dataset.tar",
    volume_id,
    "datasets/huge_dataset.tar",
    chunk_size=200 * 1024 * 1024  # Manual: 200MB chunks
)

# Upload entire directory with progress tracking
def progress_callback(current, total, filename):
    percent = (current / total) * 100
    print(f"[{current}/{total}] {percent:.1f}% - Uploading: {filename}")

api.upload_directory(
    "my_project/",
    volume_id,
    "projects/my_project/",
    exclude_patterns=["*.log", "*.tmp", ".git/*", "__pycache__/*"],
    delete=True,  # Remove remote files not in local directory
    progress_callback=progress_callback
)

# Upload with automatic exclusions
api.upload_directory(
    "ml_code/",
    volume_id,
    "code/",
    exclude_patterns=[
        "*.pyc",           # Compiled Python files
        "__pycache__/*",   # Python cache directories
        ".git/*",          # Git repository data
        ".DS_Store",       # macOS system files
        "*.log",           # Log files
        "node_modules/*",  # Node.js dependencies
        "*.tmp",           # Temporary files
        ".venv/*",         # Virtual environment
    ]
)
```

### File Download Operations

```python
from runpod_storage import RunpodStorageAPI
from pathlib import Path

api = RunpodStorageAPI()
volume_id = "your-volume-id"

# Download a single file
api.download_file(volume_id, "models/model.pkl", "local_model.pkl")

# Download entire directory
api.download_directory(
    volume_id,
    "projects/my_project/",  # Remote directory
    "downloaded_project/",    # Local destination
)

# Download with progress tracking
def download_progress(current, total, filename):
    percent = (current / total) * 100
    print(f"[{current}/{total}] {percent:.1f}% - Downloaded: {filename}")

api.download_directory(
    volume_id,
    "datasets/",
    "local_datasets/",
    progress_callback=download_progress
)

# List and selectively download files
files = api.list_files(volume_id, "models/")
for file_info in files:
    if file_info['size'] < 100 * 1024 * 1024:  # Only files under 100MB
        local_path = Path("downloads") / Path(file_info['key']).name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        api.download_file(volume_id, file_info['key'], str(local_path))
        print(f"Downloaded: {file_info['key']}")
```

### File Listing and Management

```python
from runpod_storage import RunpodStorageAPI
from datetime import datetime

api = RunpodStorageAPI()
volume_id = "your-volume-id"

# List all files in volume
all_files = api.list_files(volume_id)
print(f"Total files: {len(all_files)}")

# List files in specific directory
project_files = api.list_files(volume_id, "projects/my_project/")
for file_info in project_files:
    size_mb = file_info['size'] / (1024 * 1024)
    modified = file_info['last_modified'].strftime("%Y-%m-%d %H:%M")
    print(f"{file_info['key']} - {size_mb:.2f} MB - Modified: {modified}")

# Find large files
large_files = [f for f in all_files if f['size'] > 100 * 1024 * 1024]
print(f"Files over 100MB: {len(large_files)}")

# Find recently modified files
from datetime import datetime, timedelta
recent_date = datetime.now() - timedelta(days=7)
recent_files = [
    f for f in all_files 
    if f['last_modified'].replace(tzinfo=None) > recent_date
]
print(f"Files modified in last 7 days: {len(recent_files)}")

# Delete specific files
api.delete_file(volume_id, "temp/old_file.tmp")

# Delete multiple files matching pattern
for file_info in all_files:
    if file_info['key'].endswith('.tmp'):
        api.delete_file(volume_id, file_info['key'])
        print(f"Deleted: {file_info['key']}")
```

## Handling Large Files

### Overview

The tool supports large file uploads with intelligent automatic optimization:

**Automatic Chunk Size Detection** - No configuration needed! The tool automatically selects the optimal chunk size based on your file size:
- **< 1 GB**: 10 MB chunks (fast for small files)
- **1-10 GB**: 50 MB chunks (balanced performance)
- **10-50 GB**: 100 MB chunks (efficient for large files)
- **> 50 GB**: 200 MB chunks (optimized for huge files)

This means you can simply call `upload_file()` without worrying about chunk sizes - the tool automatically optimizes for best performance. Of course, you can still override with a custom chunk_size if needed for specific network conditions.

**Resume Support** - Uploads are resumable by default! If your upload is interrupted:
- The tool automatically saves progress for multipart uploads
- On retry, it detects the incomplete upload and resumes from the last successful chunk
- File integrity is verified using MD5 hashing
- No need to re-upload parts that already succeeded

### Interactive Mode (Easiest for Large Files)

The interactive mode handles large files automatically:

```bash
uv run runpod-storage interactive
```

1. Select option 6 (Upload file/directory)
2. Enter the path to your large file
3. The system will:
   - Automatically detect file size
   - Use multipart upload for files over 5GB
   - Show progress during upload
   - Resume if interrupted (unless --no-resume is used)

**Example session:**
```
Runpod Storage Manager
Choose action: 6

Local file/directory path: /path/to/large_dataset.tar.gz
Select volume: 1

Uploading file [cyan]/path/to/large_dataset.tar.gz[/cyan] to [green]volume-id/large_dataset.tar.gz[/green]
File size: 25.3 GB - Using multipart upload
[████████████████████░░░░░░░░░░] 65% - 16.4 GB / 25.3 GB
Upload speed: 45.2 MB/s - ETA: 3m 20s
```

### Command Line Upload

For automation and scripts, use the CLI with chunk size options:

```bash
# Basic large file upload (auto-detects optimal settings)
uv run runpod-storage upload /path/to/50gb_file.bin volume-id

# Specify custom chunk size (for very large files)
uv run runpod-storage upload /path/to/huge_file.bin volume-id \
  --chunk-size 104857600  # 100MB chunks

# Upload with resume capability (enabled by default)
# If interrupted, just run the same command again to resume
uv run runpod-storage upload /path/to/large_file.tar volume-id

# Disable resume if you want a fresh upload (ignore previous progress)
uv run runpod-storage upload /path/to/large_file.tar volume-id --no-resume

# Upload large directory as compressed archive
tar czf - /path/to/large_directory | \
  uv run runpod-storage upload - volume-id --remote-path archive.tar.gz
```

### Programmatic Upload (Python SDK)

For maximum control over large file uploads:

```python
from runpod_storage import RunpodStorageAPI
import os
import time
from pathlib import Path

api = RunpodStorageAPI()
volume_id = "your-volume-id"

# Simple large file upload - chunk size auto-detected!
def upload_large_file(local_path, volume_id, remote_path):
    """Upload large file with automatic optimization"""
    file_size = os.path.getsize(local_path)
    file_size_gb = file_size / (1024**3)
    
    print(f"Uploading {file_size_gb:.2f} GB file: {local_path}")
    
    # NEW: Auto-detects optimal chunk size based on file size
    # No need to manually specify chunk_size anymore!
    api.upload_file(
        local_path,
        volume_id,
        remote_path
        # chunk_size is automatically optimized:
        # < 1 GB: 10 MB chunks
        # 1-10 GB: 50 MB chunks  
        # 10-50 GB: 100 MB chunks
        # > 50 GB: 200 MB chunks
    )
    
    print(f"✓ Upload completed!")

# Advanced upload with real-time progress tracking
def upload_with_progress(local_path, volume_id, remote_path):
    """Upload large file with detailed progress tracking"""
    from runpod_storage import RunpodStorageAPI
    
    api = RunpodStorageAPI()
    
    def progress_callback(bytes_uploaded, total_bytes, speed_mbps):
        """Display upload progress with bar"""
        percent = (bytes_uploaded / total_bytes) * 100
        uploaded_gb = bytes_uploaded / (1024**3)
        total_gb = total_bytes / (1024**3)
        
        # Calculate ETA
        if speed_mbps > 0:
            remaining_bytes = total_bytes - bytes_uploaded
            remaining_seconds = (remaining_bytes / (1024**2)) / speed_mbps
            eta_str = f" - ETA: {int(remaining_seconds//60)}m {int(remaining_seconds%60)}s"
        else:
            eta_str = ""
        
        # Create progress bar
        bar_width = 40
        filled = int(bar_width * percent / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        print(f"\r[{bar}] {percent:.1f}% - {uploaded_gb:.2f}/{total_gb:.2f} GB - {speed_mbps:.1f} MB/s{eta_str}", 
              end="", flush=True)
        
        if bytes_uploaded >= total_bytes:
            print("\n✓ Upload complete!")
    
    # Upload with automatic chunk size detection and progress
    api.upload_file(
        local_path,
        volume_id,
        remote_path,
        progress_callback=progress_callback
    )

# Batch upload large files
def upload_large_dataset(dataset_dir, volume_id):
    """Upload multiple large files efficiently"""
    dataset_path = Path(dataset_dir)
    large_files = [f for f in dataset_path.glob("*.tar.gz") if f.stat().st_size > 1024**3]
    
    print(f"Found {len(large_files)} large files to upload")
    
    for i, file_path in enumerate(large_files, 1):
        file_size_gb = file_path.stat().st_size / (1024**3)
        print(f"\n[{i}/{len(large_files)}] Uploading {file_path.name} ({file_size_gb:.1f} GB)")
        
        remote_path = f"datasets/{file_path.name}"
        upload_large_file(str(file_path), volume_id, remote_path)

# Resume interrupted upload
def resume_upload(local_path, volume_id, remote_path):
    """Resume an interrupted upload - enabled by default!"""
    # The SDK automatically handles resume:
    # 1. Checks for existing incomplete uploads
    # 2. Verifies file integrity with MD5 hash
    # 3. Resumes from last successful chunk
    api.upload_file(
        local_path,
        volume_id,
        remote_path,
        # enable_resume=True is the default
    )
    print("✓ Upload completed (resumed if interrupted)")

# Force fresh upload (ignore previous progress)
def fresh_upload(local_path, volume_id, remote_path):
    """Start a new upload, ignoring any previous progress"""
    api.upload_file(
        local_path,
        volume_id,
        remote_path,
        enable_resume=False  # Disable resume
    )
    print("✓ Fresh upload completed")
```

### Optimizing Large Transfers

#### Best Practices

1. **Automatic Chunk Size (Recommended):**
   - Let the SDK auto-detect optimal chunk size - no configuration needed!
   - The tool intelligently selects chunk size based on file size
   - Override only if you have specific network requirements
   
   **Default chunk sizes by file size:**
   - **< 1 GB**: 10 MB chunks
   - **1-10 GB**: 50 MB chunks  
   - **10-50 GB**: 100 MB chunks
   - **> 50 GB**: 200 MB chunks

2. **Network Optimization:**
   ```bash
   # Test your upload speed first
   uv run runpod-storage upload test-file.bin volume-id --benchmark
   
   # Choose nearest datacenter for better speed
   # US users: US-KS-2
   # EU users: EU-RO-1, EU-CZ-1, or EUR-IS-1
   ```

3. **Compression Before Upload:**
   ```bash
   # Compress before uploading (can reduce size by 50-90%)
   tar czf dataset.tar.gz dataset/
   uv run runpod-storage upload dataset.tar.gz volume-id
   
   # Or use higher compression
   tar cJf dataset.tar.xz dataset/  # xz compression (slower but smaller)
   7z a -mx=9 dataset.7z dataset/   # 7zip maximum compression
   ```

4. **Parallel Uploads for Multiple Files:**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   import threading
   
   api = RunpodStorageAPI()
   upload_lock = threading.Lock()
   
   def upload_file_thread(file_path, volume_id, remote_path):
       """Thread-safe file upload"""
       try:
           api.upload_file(file_path, volume_id, remote_path)
           with upload_lock:
               print(f"✓ Uploaded: {file_path}")
       except Exception as e:
           with upload_lock:
               print(f"✗ Failed: {file_path} - {e}")
   
   # Upload multiple large files in parallel
   files_to_upload = [
       ("file1.bin", "data/file1.bin"),
       ("file2.bin", "data/file2.bin"),
       ("file3.bin", "data/file3.bin"),
   ]
   
   with ThreadPoolExecutor(max_workers=3) as executor:
       futures = []
       for local_path, remote_path in files_to_upload:
           future = executor.submit(upload_file_thread, local_path, volume_id, remote_path)
           futures.append(future)
       
       # Wait for all uploads to complete
       for future in futures:
           future.result()
   ```

#### Monitoring Transfers

```python
# Monitor upload with detailed statistics
import psutil
import threading

def monitor_upload(local_path, volume_id, remote_path):
    """Monitor system resources during upload"""
    stop_monitoring = threading.Event()
    
    def monitor_thread():
        while not stop_monitoring.is_set():
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            network = psutil.net_io_counters()
            upload_speed = network.bytes_sent / (1024**2)  # MB
            
            print(f"\rCPU: {cpu}% | RAM: {memory}% | Uploaded: {upload_speed:.1f} MB", end="")
    
    # Start monitoring
    monitor = threading.Thread(target=monitor_thread)
    monitor.start()
    
    try:
        # Perform upload
        api.upload_file(local_path, volume_id, remote_path, chunk_size=100*1024*1024)
        print("\n✓ Upload complete!")
    finally:
        stop_monitoring.set()
        monitor.join()
```

#### Handling Failures

```python
# Robust upload with retry and resume
def reliable_large_upload(local_path, volume_id, remote_path, max_retries=3):
    """Upload large file with automatic retry and resume"""
    import time
    
    for attempt in range(max_retries):
        try:
            print(f"Upload attempt {attempt + 1}/{max_retries}")
            
            api.upload_file(
                local_path,
                volume_id,
                remote_path,
                chunk_size=100 * 1024 * 1024
            )
            
            print("✓ Upload successful!")
            return True
            
        except Exception as e:
            print(f"✗ Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("✗ Upload failed after all retries")
                return False
    
    return False

# Usage
success = reliable_large_upload(
    "/path/to/50gb_dataset.tar.gz",
    "volume-id",
    "datasets/training_data.tar.gz"
)
```

### Troubleshooting Large Uploads

**Upload fails midway:**
- The tool supports resume by default for multipart uploads
- Simply run the same upload command again to resume from where it left off
- Use `--no-resume` flag (CLI) or `enable_resume=False` (SDK) to start fresh

**"Request timeout" errors:**
- Increase chunk size for better efficiency
- Check your internet connection stability
- Consider uploading during off-peak hours

**Cleaning up abandoned uploads:**
```python
# Clean up incomplete uploads older than 24 hours
from runpod_storage import RunpodStorageAPI

api = RunpodStorageAPI()
volume_id = "your-volume-id"

# Remove abandoned multipart uploads
cleaned = api.cleanup_abandoned_uploads(volume_id, max_age_hours=24)
print(f"Cleaned up {cleaned} abandoned uploads")

# You can also clean up more aggressively (e.g., uploads older than 1 hour)
cleaned = api.cleanup_abandoned_uploads(volume_id, max_age_hours=1)
```

**"Insufficient storage" errors:**
- Check volume size: `uv run runpod-storage list-volumes`
- Expand volume if needed: `api.update_volume(volume_id, size=new_size)`
- Delete unnecessary files first

**Slow upload speeds:**
- Choose the datacenter closest to you
- Compress files before uploading
- Use wired connection instead of WiFi
- Upload during off-peak hours for better bandwidth

## API Server

Run your own REST API server that proxies to Runpod's API:

```bash
# Start the server
uv run runpod-storage-server --host 0.0.0.0 --port 8000

# Access the interactive API documentation
# FastAPI Docs (Swagger UI): http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Interactive API Documentation

Once the server is running, visit **http://localhost:8000/docs** for the interactive FastAPI documentation where you can:
- Explore all available endpoints
- Test API calls directly from your browser
- View request/response schemas
- See required headers and parameters

The API server acts as a thin wrapper around Runpod's API, requiring:
- **All endpoints**: `runpod-api-key` header
- **File operations**: Additional `s3-access-key` and `s3-secret-key` headers

### Docker Deployment

```bash
# Build and run with Docker
docker build -t runpod-storage .
docker run -p 8000:8000 \
  -e RUNPOD_API_KEY=your_key \
  -e RUNPOD_S3_ACCESS_KEY=your_s3_key \
  -e RUNPOD_S3_SECRET_KEY=your_s3_secret \
  runpod-storage
```

## Available Datacenters

| Datacenter | Location | Endpoint |
|------------|----------|----------|
| EUR-IS-1 | Iceland | https://s3api-eur-is-1.runpod.io/ |
| EU-RO-1 | Romania | https://s3api-eu-ro-1.runpod.io/ |
| EU-CZ-1 | Czech Republic | https://s3api-eu-cz-1.runpod.io/ |
| US-KS-2 | Kansas, USA | https://s3api-us-ks-2.runpod.io/ |

## Troubleshooting

### Authentication Issues

**"Invalid API key" error:**
- Verify your API key is correct
- Check that environment variables are set
- Try passing the key directly: `--api-key your_key`

**"S3 credentials required" error:**
- File operations need S3 credentials in addition to the API key
- Set both `RUNPOD_S3_ACCESS_KEY` and `RUNPOD_S3_SECRET_KEY`

### Volume Operations

**"Cannot decrease volume size" error:**
- Volumes can only be expanded, not shrunk
- Create a new smaller volume if needed

**Volume not found:**
- Verify the volume ID is correct
- Check that the volume exists in your account
- Use `list-volumes` to see available volumes

### File Transfer Issues

**Slow uploads/downloads:**
- Consider using zip downloads for multiple files
- Check your internet connection speed
- Choose a datacenter closer to your location

**"Path not found" errors:**
- Use the file browser to verify the correct path
- Remember paths are case-sensitive
- Don't include leading slashes for relative paths

### File Browser Issues

**Can't see files:**
- Make sure you're in the correct directory
- Check that files have been uploaded to the volume
- Verify S3 credentials have proper permissions

**Download fails:**
- Ensure you have write permissions in the download directory
- Check available disk space
- Try downloading as zip if individual files fail

## Examples

### Backing Up a Project

```python
from runpod_storage import RunpodStorageAPI
import datetime

api = RunpodStorageAPI()

# Create a backup volume if it doesn't exist
volumes = api.list_volumes()
backup_volume = None
for v in volumes:
    if v['name'] == 'project-backups':
        backup_volume = v
        break

if not backup_volume:
    backup_volume = api.create_volume('project-backups', 100, 'EU-RO-1')

# Upload with timestamp
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
api.upload_directory(
    'my_project/',
    backup_volume['id'],
    f'backups/{timestamp}/',
    exclude_patterns=['*.tmp', '*.log', '__pycache__/*', '.git/*']
)
print(f"Backup completed: backups/{timestamp}/")
```

### Batch Download Files

Using the interactive file browser:
1. Run `uv run runpod-storage interactive`
2. Select option 7 (Download file/directory)
3. Choose option 1 (Browse & Select)
4. Navigate to your files
5. Press `s` to enter selection mode
6. Use `a 1`, `a 2`, etc. to select files
7. Press `d` to download all as a zip

Or use quick download in navigation mode:
- Type `d 1 3 5 7` to download items 1, 3, 5, and 7 as a single zip

## Support

For issues or questions:
- Check the [GitHub repository](https://github.com/justinwlin/Runpod-Network-Volume-Storage-Tool)
- Review Runpod's [S3 API documentation](https://docs.runpod.io/serverless/storage/s3-api)
- Ensure your API keys have the necessary permissions

## License

MIT License - See LICENSE file for details

## Notes

This tool was created for personal use to work with Runpod's network storage API. Feel free to submit pull requests for bug fixes or improvements.