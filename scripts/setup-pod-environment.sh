#!/bin/bash

# Script to quickly set up and run tests on a Runpod pod
# Run this ON your Runpod pod for maximum network speeds
#
# One-liner to run this script:
#   curl -sSL https://raw.githubusercontent.com/justinwlin/Runpod-Network-Volume-Storage-Tool/main/scripts/setup-pod-environment.sh | bash

echo "=========================================="
echo "Runpod Storage Test - Pod Setup"
echo "=========================================="
echo ""

# Check if we're in a pod environment
if [ -f /workspace/.pod_ready ]; then
    echo "✓ Running on Runpod pod"
else
    echo "⚠ This appears to be a local environment"
    echo "  For best performance, run this on a Runpod pod"
    echo ""
fi

# Install required tools if not present
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    apt-get update && apt-get install -y git curl
fi

# Clone or update the repository
if [ -d "Runpod-Network-Volume-Storage-Tool" ]; then
    echo "Repository already exists, updating..."
    cd Runpod-Network-Volume-Storage-Tool
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/justinwlin/Runpod-Network-Volume-Storage-Tool.git
    cd Runpod-Network-Volume-Storage-Tool
fi

# Install Python dependencies
echo "Installing dependencies..."
if command -v uv &> /dev/null; then
    uv sync
elif command -v pip &> /dev/null; then
    pip install -e .
else
    echo "Installing pip..."
    apt-get install -y python3-pip
    pip install -e .
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Set your credentials (get them from https://www.runpod.io/console/user/settings):"
echo ""
echo "   export RUNPOD_API_KEY='your_api_key'"
echo "   export RUNPOD_S3_ACCESS_KEY='your_s3_access_key'"
echo "   export RUNPOD_S3_SECRET_KEY='your_s3_secret_key'"
echo ""
echo "2. Run tests:"
echo ""
echo "   ./scripts/run-tests.sh           # Test credentials"
echo "   ./scripts/run-tests.sh quick     # Quick 100MB test"
echo "   ./scripts/run-tests.sh full      # Full 6GB test"
echo ""
echo "3. Custom file size test:"
echo ""
echo "   export TEST_FILE_SIZE_GB=10"
echo "   ./scripts/run-tests.sh full      # Run 10GB test"
echo ""
echo "Expected speeds on Runpod pod: 50-200 MB/s"
echo ""