#!/bin/bash
# Convenience wrapper - redirects to the actual script

# Get the directory where this script is located (repo root)
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Execute the actual script
exec "$REPO_ROOT/scripts/run-tests.sh" "$@"