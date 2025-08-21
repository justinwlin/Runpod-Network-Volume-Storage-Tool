#!/bin/bash

# Test runner script for Runpod Storage upload tests

set -e

echo "=========================================="
echo "Runpod Storage Upload Tests"
echo "=========================================="

# Check for required environment variables
required_vars=("RUNPOD_API_KEY" "RUNPOD_S3_ACCESS_KEY" "RUNPOD_S3_SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please set these variables first:"
    for var in "${missing_vars[@]}"; do
        echo "  export $var=your_value"
    done
    exit 1
fi

# Parse arguments
TEST_TYPE=${1:-quick}
TEST_SIZE_GB=${2:-6}

echo ""
echo "Configuration:"
echo "  Test type: $TEST_TYPE"
if [ "$TEST_TYPE" = "full" ]; then
    echo "  Test file size: ${TEST_SIZE_GB}GB"
fi
echo "  Datacenter: ${TEST_DATACENTER:-EU-RO-1}"
echo ""

# Run appropriate test
if [ "$TEST_TYPE" = "quick" ]; then
    echo "Running quick test (100MB file)..."
    echo "=========================================="
    python3 examples/test_upload_quick.py
elif [ "$TEST_TYPE" = "full" ]; then
    echo "Running full E2E test (${TEST_SIZE_GB}GB file)..."
    echo "=========================================="
    export TEST_FILE_SIZE_GB=$TEST_SIZE_GB
    python3 examples/test_large_file_e2e.py
else
    echo "❌ Unknown test type: $TEST_TYPE"
    echo ""
    echo "Usage: ./run_tests.sh [quick|full] [size_gb]"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh quick         # Run quick 100MB test"
    echo "  ./run_tests.sh full          # Run full 6GB test"
    echo "  ./run_tests.sh full 10       # Run full test with 10GB file"
    exit 1
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi