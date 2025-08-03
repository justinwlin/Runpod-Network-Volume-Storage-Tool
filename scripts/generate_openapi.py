#!/usr/bin/env python3
"""Generate OpenAPI specification from FastAPI routes.

This script generates the OpenAPI JSON specification directly from the FastAPI app.
It should be run whenever the API routes or models are modified to keep the
documentation in sync with the implementation.

Usage:
    python scripts/generate_openapi.py
    uv run python scripts/generate_openapi.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from runpod_storage.server.main import create_app

    # Create app and generate OpenAPI schema
    app = create_app()
    schema = app.openapi()

    # Ensure docs/api directory exists
    docs_dir = Path(__file__).parent.parent / "docs" / "api"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON spec
    openapi_file = docs_dir / "openapi.json"
    with open(openapi_file, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"✅ Generated OpenAPI spec: {openapi_file}")
    print(f"📊 Found {len(schema.get('paths', {}))} endpoints")

    # List endpoints for verification
    for path, methods in schema.get("paths", {}).items():
        for method in methods.keys():
            if method != "parameters":  # Skip OpenAPI parameters
                print(f"   {method.upper()} {path}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure dependencies are installed: uv sync")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error generating OpenAPI: {e}")
    sys.exit(1)
