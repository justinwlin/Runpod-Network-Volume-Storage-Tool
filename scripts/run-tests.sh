#!/bin/bash

# Simple test runner for Runpod Network Storage examples
# Usage: ./scripts/run-tests.sh [creds|quick|full]

set -e

# Colors for output (optional, will work without)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the repository root (parent of scripts directory)
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to repository root to ensure paths work correctly
cd "$REPO_ROOT"

# Get test type from argument
TEST_TYPE=${1:-creds}

echo "=========================================="
echo "Runpod Network Storage Test Runner"
echo "=========================================="

# Check if credentials are set
if [ -z "$RUNPOD_API_KEY" ] || [ -z "$RUNPOD_S3_ACCESS_KEY" ] || [ -z "$RUNPOD_S3_SECRET_KEY" ]; then
    echo "⚠ Environment variables not set"
    echo ""
    echo "Please set up your credentials first:"
    echo "  1. cp examples/.env.example examples/.env"
    echo "  2. Edit examples/.env with your credentials"
    echo "  3. source examples/.env"
    echo "  4. Run this script again"
    echo ""
    echo "Get credentials at: https://www.runpod.io/console/user/settings"
    exit 1
fi

# Check if uv is available, otherwise use python
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
else
    PYTHON_CMD="python"
fi

# Run the appropriate test
case $TEST_TYPE in
    creds|credentials)
        echo "Running credential test..."
        $PYTHON_CMD examples/test_credentials.py
        ;;
    quick)
        echo "Running quick test (100MB)..."
        $PYTHON_CMD examples/test_upload_quick.py
        ;;
    full)
        FILE_SIZE=${TEST_FILE_SIZE_GB:-6}
        echo "Running full test (${FILE_SIZE}GB)..."
        $PYTHON_CMD examples/test_large_file_e2e.py
        ;;
    *)
        echo "Invalid test type: $TEST_TYPE"
        echo ""
        echo "Usage: ./test.sh [creds|quick|full]"
        echo ""
        echo "Options:"
        echo "  creds  - Test credentials (default)"
        echo "  quick  - Quick 100MB upload test"
        echo "  full   - Full 6GB end-to-end test"
        echo ""
        echo "Examples:"
        echo "  ./test.sh           # Test credentials"
        echo "  ./test.sh quick     # Run quick test"
        echo "  ./test.sh full      # Run full test"
        echo ""
        echo "Custom file size:"
        echo "  export TEST_FILE_SIZE_GB=10"
        echo "  ./test.sh full      # Run 10GB test"
        exit 1
        ;;
esac