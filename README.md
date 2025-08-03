# 🚀 Runpod Storage

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Professional CLI, SDK, and API server for Runpod network storage management.**

Runpod Storage provides a comprehensive suite of tools for managing Runpod network volumes and files with enterprise-grade reliability, performance, and developer experience.

## ✨ Features

- 🎯 **Multi-Interface Access**: CLI, Python SDK, and REST API server
- 🚀 **High Performance**: Robust multipart uploads with retry logic for large files
- 🔒 **Enterprise Security**: Comprehensive authentication and error handling
- 📚 **OpenAPI Compliant**: Full OpenAPI 3.0 specification with auto-generated docs
- 🐳 **Production Ready**: Docker support with health checks and monitoring
- 📖 **Comprehensive Docs**: Extensive documentation with examples and tutorials
- ⚡ **Zero Config**: Works out of the box with sensible defaults

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Tool      │    │   Python SDK    │    │   REST API      │
│   Interactive   │    │   Programmatic  │    │   Server        │
│   Commands      │    │   Access        │    │   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Core SDK      │
                    │   - Runpod API  │
                    │   - S3 Client   │
                    │   - Validation  │
                    │   - Exceptions  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Runpod        │
                    │   Platform      │
                    └─────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/runpod-storage.git
cd runpod-storage

# Install with uv (recommended)
uv sync

# Or install in development mode
uv sync --all-extras
```

### CLI Usage

```bash
# Set your API key
export RUNPOD_API_KEY="your_api_key_here"

# Or pass it directly
runpod-storage --api-key "your_key" list-volumes

# Interactive mode (easiest)
runpod-storage interactive

# Create a volume
runpod-storage create-volume --name "my-storage" --size 50 --datacenter EU-RO-1

# Upload files
runpod-storage upload /path/to/file.txt volume-id

# Download files  
runpod-storage download volume-id remote/file.txt
```

### Python SDK

```python
from runpod_storage import RunpodStorageAPI

# Initialize with API key
api = RunpodStorageAPI(api_key="your_api_key")

# Or use environment variables
api = RunpodStorageAPI()  # Uses RUNPOD_API_KEY

# List volumes
volumes = api.list_volumes()
print(f"Found {len(volumes)} volumes")

# Create a volume
volume = api.create_volume("my-storage", 50, "EU-RO-1")
print(f"Created volume: {volume['id']}")

# Upload a file
api.upload_file("local_file.txt", volume['id'], "remote_file.txt")

# List files
files = api.list_files(volume['id'])
for file_info in files:
    print(f"{file_info['key']} - {file_info['size']} bytes")

# Download a file
api.download_file(volume['id'], "remote_file.txt", "downloaded_file.txt")
```

### REST API Server

```bash
# Start the API server
runpod-storage-server --host 0.0.0.0 --port 8000

# Or with Docker (build locally)
docker build -t runpod-storage .
docker run -p 8000:8000 -e RUNPOD_API_KEY=your_key runpod-storage

# Or with Docker Compose
docker-compose up -d
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📚 Documentation

### 📋 API Reference
- [**OpenAPI Specification**](docs/api/openapi.yaml) - Complete API spec
- **Interactive API Docs** - Start the server and visit `http://localhost:8000/docs`

### 📖 Examples
- [**Basic Usage**](examples/basic_usage.py) - Python SDK examples
- [**Server Integration**](examples/server_example.py) - REST API client examples

## 🌍 Available Datacenters

| Datacenter | Region | S3 Endpoint |
|------------|--------|-------------|
| `EUR-IS-1` | Iceland | `https://s3api-eur-is-1.runpod.io/` |
| `EU-RO-1` | Romania | `https://s3api-eu-ro-1.runpod.io/` |
| `EU-CZ-1` | Czech Republic | `https://s3api-eu-cz-1.runpod.io/` |
| `US-KS-2` | Kansas, USA | `https://s3api-us-ks-2.runpod.io/` |

## 🔐 Authentication

### API Keys

Get your API keys from the [Runpod Console](https://console.runpod.io/user/settings):

1. **Runpod API Key** - For volume management operations
2. **S3 API Keys** - For file operations (access key + secret key)

### Environment Variables

```bash
# Required for volume operations
export RUNPOD_API_KEY="rpa_your_api_key_here"

# Required for file operations  
export RUNPOD_S3_ACCESS_KEY="user_your_s3_access_key"
export RUNPOD_S3_SECRET_KEY="rps_your_s3_secret_key"
```

### Multiple Authentication Methods

```bash
# CLI flag (highest priority)
runpod-storage --api-key "your_key" list-volumes

# Environment variable
export RUNPOD_API_KEY="your_key"
runpod-storage list-volumes

# Configuration file
echo "api_key = your_key" > ~/.runpod/config.toml
```

## 📊 Examples

### Basic File Management

```python
from runpod_storage import RunpodStorageAPI

api = RunpodStorageAPI()

# Create volume and upload multiple files
volume = api.create_volume("data-backup", 100, "EU-RO-1")
volume_id = volume["id"]

files_to_upload = [
    ("local/data.csv", "datasets/data.csv"),
    ("local/model.pkl", "models/model.pkl"),
    ("local/config.json", "config/config.json")
]

for local_path, remote_path in files_to_upload:
    print(f"Uploading {local_path} to {remote_path}...")
    api.upload_file(local_path, volume_id, remote_path)
    print("✓ Upload complete")

# List and download files
print("\nFiles in volume:")
files = api.list_files(volume_id)
for file_info in files:
    print(f"  {file_info['key']} ({file_info['size']} bytes)")
    
    # Download file
    local_name = f"downloaded_{file_info['key'].replace('/', '_')}"
    api.download_file(volume_id, file_info['key'], local_name)
    print(f"  ✓ Downloaded to {local_name}")
```

### Large File Upload with Progress

```python
import time
from runpod_storage import RunpodStorageAPI

api = RunpodStorageAPI()

# Upload large file with custom chunk size
def upload_with_progress(local_path, volume_id, remote_path):
    file_size = os.path.getsize(local_path)
    print(f"Uploading {file_size / (1024**3):.2f} GB file...")
    
    start_time = time.time()
    
    # Use 100MB chunks for large files
    chunk_size = 100 * 1024 * 1024
    api.upload_file(local_path, volume_id, remote_path, chunk_size)
    
    elapsed = time.time() - start_time
    speed = (file_size / (1024**2)) / elapsed  # MB/s
    print(f"✓ Upload completed in {elapsed:.1f}s ({speed:.1f} MB/s)")

upload_with_progress("large_dataset.zip", volume_id, "data/large_dataset.zip")
```

### Error Handling

```python
from runpod_storage import (
    RunpodStorageAPI, 
    VolumeNotFoundError, 
    InsufficientStorageError,
    AuthenticationError
)

api = RunpodStorageAPI()

try:
    # Attempt operations with proper error handling
    volume = api.get_volume("invalid-volume-id")
except VolumeNotFoundError as e:
    print(f"Volume not found: {e.volume_id}")
except AuthenticationError:
    print("Invalid API key - check your credentials")
except InsufficientStorageError:
    print("Not enough storage space available")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 🐳 Docker Deployment

### Simple Deployment

```bash
# Pull and run the API server
docker run -d \
  --name runpod-storage-api \
  -p 8000:8000 \
  -e RUNPOD_API_KEY="your_api_key" \
  -e RUNPOD_S3_ACCESS_KEY="your_s3_key" \
  -e RUNPOD_S3_SECRET_KEY="your_s3_secret" \
  runpod/storage-api
```

### Production Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    image: runpod/storage-api:latest
    ports:
      - "8000:8000"
    environment:
      - RUNPOD_API_KEY=${RUNPOD_API_KEY}
      - RUNPOD_S3_ACCESS_KEY=${RUNPOD_S3_ACCESS_KEY}  
      - RUNPOD_S3_SECRET_KEY=${RUNPOD_S3_SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
    restart: unless-stopped
```

## 🛠️ Development

### Setup Development Environment

```bash
# Install with uv (recommended)
uv sync --all-extras

# Or create virtual environment manually
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/e2e/
```

### Code Quality

```bash
# Format code
uv run black src tests
uv run ruff check --fix src tests

# Type checking
uv run mypy src

# Security scan
uv run bandit -r src/
```

### API Documentation

```bash
# Start the API server to access interactive docs
uv run runpod-storage-server

# Visit http://localhost:8000/docs for interactive documentation
# OpenAPI spec available at: docs/api/openapi.yaml
```

## 🎯 Roadmap

- [ ] GraphQL API support
- [ ] Streaming upload/download for very large files
- [ ] Volume snapshots and backups
- [ ] Advanced file synchronization
- [ ] Web UI for file management
- [ ] Integration with popular data science tools
- [ ] Multi-cloud storage support