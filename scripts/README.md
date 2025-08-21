# Test Scripts

This directory contains helper scripts for testing the Runpod Network Storage tool.

## Available Scripts

### `run-tests.sh` - Local Test Runner
Main test runner for local development and testing. Works on any machine with Python installed.

**Usage:**
```bash
# First time setup
cp examples/.env.example examples/.env
# Edit examples/.env with your credentials
source examples/.env

# Run tests
./scripts/run-tests.sh           # Test credentials (default)
./scripts/run-tests.sh quick     # Quick 100MB test
./scripts/run-tests.sh full      # Full 6GB test

# Custom file size
export TEST_FILE_SIZE_GB=10
./scripts/run-tests.sh full      # 10GB test
```

**What it does:**
- Checks that credentials are properly configured
- Runs the appropriate test based on your selection
- Automatically uses `uv` if available, otherwise uses `python`

### `setup-pod-environment.sh` - Runpod Pod Setup
Automated setup script for running tests on Runpod pods with maximum network speeds.

**When to use:**
- You're SSH'd into a Runpod pod
- You want the fastest possible upload/download speeds (50-200 MB/s)
- You need a quick one-liner setup

**Usage:**
```bash
# One-liner to download and run
curl -sSL https://raw.githubusercontent.com/justinwlin/Runpod-Network-Volume-Storage-Tool/main/scripts/setup-pod-environment.sh | bash

# Or if you already have the repo
./scripts/setup-pod-environment.sh
```

**What it does:**
1. Installs required dependencies (git, python)
2. Clones or updates the repository
3. Installs Python packages
4. Provides instructions for setting credentials
5. Points you to use `run-tests.sh` for actual testing

## Quick Start Guide

### Testing Locally
```bash
# 1. Set up credentials
cp examples/.env.example examples/.env
nano examples/.env  # Add your credentials
source examples/.env

# 2. Test your setup
./scripts/run-tests.sh

# 3. Run performance tests
./scripts/run-tests.sh quick  # 100MB
./scripts/run-tests.sh full   # 6GB
```

### Testing on Runpod Pod (Fastest)
```bash
# 1. SSH into your Runpod pod

# 2. Run the setup script
curl -sSL https://raw.githubusercontent.com/justinwlin/Runpod-Network-Volume-Storage-Tool/main/scripts/setup-pod-environment.sh | bash

# 3. Navigate to the cloned repo
cd Runpod-Network-Volume-Storage-Tool

# 4. Set credentials
export RUNPOD_API_KEY='your_key'
export RUNPOD_S3_ACCESS_KEY='your_s3_key'
export RUNPOD_S3_SECRET_KEY='your_s3_secret'

# 5. Run tests
./scripts/run-tests.sh quick  # Fast 100MB test
./scripts/run-tests.sh full   # Full 6GB test
```

## Test Types

| Test Type | Command | Duration | Purpose |
|-----------|---------|----------|---------|
| Credentials | `./scripts/run-tests.sh` | ~10 seconds | Verify setup is correct |
| Quick | `./scripts/run-tests.sh quick` | ~1 minute | Fast functionality test |
| Full | `./scripts/run-tests.sh full` | 10-30 minutes | Production workload test |

## Expected Performance

| Environment | Upload Speed | 100MB Time | 6GB Time |
|-------------|-------------|------------|----------|
| Home Internet | 1-10 MB/s | 10-100s | 10-100 min |
| Cloud VM | 10-50 MB/s | 2-10s | 2-10 min |
| Runpod Pod | 50-200 MB/s | 0.5-2s | 30s-2 min |

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/run-tests.sh
chmod +x scripts/setup-pod-environment.sh
```

### Missing Credentials
The scripts will guide you to:
1. Copy `examples/.env.example` to `examples/.env`
2. Add your credentials
3. Source the file: `source examples/.env`

### Python Not Found
- The scripts automatically detect and use `uv` or `python`
- On Runpod pods, Python is pre-installed
- On local machines, install Python 3.8+

## Getting Credentials

Get your credentials from: https://www.runpod.io/console/user/settings

You need:
- API Key (starts with `rpa_`)
- S3 Access Key (starts with `user_`)
- S3 Secret Key (starts with `rps_`)