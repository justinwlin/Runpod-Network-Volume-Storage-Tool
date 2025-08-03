#!/usr/bin/env python3
"""Generate OpenAPI specification from FastAPI routes."""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from runpod_storage.server.main import create_app
    
    # Create app and generate OpenAPI schema
    app = create_app()
    schema = app.openapi()
    
    # Ensure docs/api directory exists
    docs_dir = Path("docs/api")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Write JSON
    with open(docs_dir / "openapi.json", "w") as f:
        json.dump(schema, f, indent=2)
    
    print("✅ Generated OpenAPI JSON spec from FastAPI app")
    print("📄 File: docs/api/openapi.json")
    print(f"📊 Found {len(schema.get('paths', {}))} endpoints")
    
    # List endpoints
    for path, methods in schema.get('paths', {}).items():
        for method in methods.keys():
            if method != 'parameters':  # Skip OpenAPI parameters
                print(f"  {method.upper()} {path}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Try installing dependencies first")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error generating OpenAPI: {e}")
    sys.exit(1)