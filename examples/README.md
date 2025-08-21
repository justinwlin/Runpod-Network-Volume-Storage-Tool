# Runpod Network Storage Examples

This directory contains self-contained examples demonstrating how to use the Runpod Network Storage API programmatically.

## Quick Start

### 1. Set Up Credentials

First, you need to get your Runpod credentials:
1. Visit https://www.runpod.io/console/user/settings
2. Copy your API key and S3 credentials

Then set them up:

```bash
# Copy the example environment file
cp examples/.env.example examples/.env

# Edit .env with your credentials
nano examples/.env  # or use your favorite editor

# Load the environment variables
source examples/.env
```

### 2. Test Your Setup

Run the credential test to verify everything is working:

```bash
python examples/test_credentials.py
```

This test will:
- Verify your API key is valid
- Check S3 credentials work
- Test basic upload/download operations
- Provide helpful troubleshooting if something fails

### 3. Run Tests

Once credentials are verified, you can run the other tests:

```bash
# Quick test (100MB file, ~1 minute)
python examples/test_upload_quick.py

# Full test (6GB file, ~10-30 minutes)
python examples/test_large_file_e2e.py

# Custom size test
export TEST_FILE_SIZE_GB=10
python examples/test_large_file_e2e.py
```

## Available Examples

### test_credentials.py
**Purpose**: Verify your credentials are set up correctly  
**Runtime**: ~10 seconds  
**Use when**: First time setup or troubleshooting authentication issues

### test_upload_quick.py
**Purpose**: Quick test of upload/download functionality  
**Runtime**: ~30-60 seconds  
**File size**: 100MB  
**Use when**: Testing network connectivity or quick development iterations

### test_large_file_e2e.py
**Purpose**: Comprehensive end-to-end test with large files  
**Runtime**: 10-30 minutes (depends on network speed)  
**File size**: 6GB (configurable)  
**Use when**: Testing production workloads or verifying large file handling

Features tested:
- Large file upload with multipart
- Resume capability
- Download and integrity verification
- Automatic cleanup
- Performance metrics

## Running on Runpod Pods

For faster network speeds, you can run these tests directly on a Runpod pod:

```bash
# SSH into your pod, then run this one-liner:
curl -sSL https://raw.githubusercontent.com/justinwlin/Runpod-Network-Volume-Storage-Tool/main/scripts/setup-pod-environment.sh | bash

# Navigate to the cloned repository
cd Runpod-Network-Volume-Storage-Tool

# Set credentials
export RUNPOD_API_KEY='your_key'
export RUNPOD_S3_ACCESS_KEY='your_s3_key'
export RUNPOD_S3_SECRET_KEY='your_s3_secret'

# Run tests using the test runner
./scripts/run-tests.sh           # Test credentials
./scripts/run-tests.sh quick     # Quick 100MB test
./scripts/run-tests.sh full      # Full 6GB test
```

Or run the Python scripts directly:
```bash
python examples/test_upload_quick.py
python examples/test_large_file_e2e.py
```

## Performance Expectations

Network speeds vary based on location and connection:

| Location | Expected Upload Speed | 100MB Test | 6GB Test |
|----------|----------------------|------------|----------|
| Local (Home) | 1-10 MB/s | 10-100s | 10-100min |
| Cloud VM | 10-50 MB/s | 2-10s | 2-10min |
| Runpod Pod | 50-200 MB/s | 0.5-2s | 30s-2min |

## Troubleshooting

### Missing Environment Variables
If you see "Missing environment variables", make sure you:
1. Created the .env file: `cp examples/.env.example examples/.env`
2. Added your credentials to .env
3. Loaded the variables: `source examples/.env`

### Authentication Errors
- Verify your API key starts with `rpa_`
- Check S3 access key starts with `user_`
- Ensure S3 secret key starts with `rps_`
- Confirm your Runpod account is active

### Network Issues
- Check your internet connection
- Try using a different datacenter (EU-RO-1, EU-SE-1, US-OR-1)
- Run tests from a cloud VM or Runpod pod for better speeds

### File Size Issues
- Ensure you have enough disk space for test files
- For large tests, use a system with fast SSD storage
- Consider using smaller test sizes first

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| RUNPOD_API_KEY | Your Runpod API key | Required | rpa_abc123... |
| RUNPOD_S3_ACCESS_KEY | S3 access key | Required | user_xyz789... |
| RUNPOD_S3_SECRET_KEY | S3 secret key | Required | rps_def456... |
| TEST_DATACENTER | Datacenter for tests | EU-RO-1 | US-OR-1 |
| TEST_FILE_SIZE_GB | Size for large file test | 6 | 10 |
| TEST_VOLUME_ID | Use existing volume | None | vol_abc123 |

## Writing Your Own Code

After running these examples, you can use them as templates for your own code:

```python
import os
from runpod_storage import RunpodStorageAPI

# Initialize API (uses environment variables)
api = RunpodStorageAPI()

# List volumes
volumes = api.list_volumes()

# Upload a file
api.upload_file(
    local_path="my_file.zip",
    volume_id="vol_abc123",
    remote_path="backups/my_file.zip",
    chunk_size=50 * 1024 * 1024  # 50MB chunks
)

# Download a file
api.download_file(
    volume_id="vol_abc123",
    remote_path="backups/my_file.zip",
    local_path="downloaded_file.zip"
)
```

## Support

- Documentation: https://github.com/justinwlin/Runpod-Network-Volume-Storage-Tool
- Issues: https://github.com/justinwlin/Runpod-Network-Volume-Storage-Tool/issues
- Discord: https://discord.gg/runpod