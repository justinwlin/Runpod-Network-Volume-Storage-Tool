# Runpod Storage API Credentials

## Overview

Runpod Storage uses **two separate APIs** with different authentication methods:

## 1. 🔧 Volume Management API

**Purpose**: Create, update, delete network volumes
**Base URL**: `https://rest.runpod.io/v1`

### Authentication
- **API Key**: `RUNPOD_API_KEY` (starts with `rpa_`)
- **Header**: `Authorization: Bearer rpa_your_api_key_here`

### Get Your API Key
1. Go to [Runpod Console](https://console.runpod.io/user/settings)
2. Find "API Keys" section
3. Create or copy your API key (starts with `rpa_`)

### OpenAPI Spec
✅ Available: `docs/api/runpod-storage-complete.yaml`

---

## 2. 📁 File Operations API (S3-Compatible)

**Purpose**: Upload, download, list, delete files
**Endpoints**: `https://s3api-{datacenter}.runpod.io/`

### Authentication
- **Access Key**: `RUNPOD_S3_ACCESS_KEY` (starts with `user_`)
- **Secret Key**: `RUNPOD_S3_SECRET_KEY` (starts with `rps_`)
- **Protocol**: AWS S3 authentication (AWS4-HMAC-SHA256)

### Get Your S3 Credentials
1. Go to [Runpod Console](https://console.runpod.io/user/settings)
2. Find "S3 API Keys" section
3. Create new S3 API key
4. Save both access key and secret key

### Datacenters & Endpoints
| Datacenter | Endpoint |
|------------|----------|
| EUR-IS-1 | `https://s3api-eur-is-1.runpod.io/` |
| EU-RO-1  | `https://s3api-eu-ro-1.runpod.io/` |
| EU-CZ-1  | `https://s3api-eu-cz-1.runpod.io/` |
| US-KS-2  | `https://s3api-us-ks-2.runpod.io/` |

### OpenAPI Spec
❌ Not available - Use standard AWS S3 OpenAPI specifications

---

## 🔐 Environment Variables

Set both sets of credentials:

```bash
# Volume Management API
export RUNPOD_API_KEY="rpa_your_api_key_here"

# File Operations API  
export RUNPOD_S3_ACCESS_KEY="user_your_access_key_here"
export RUNPOD_S3_SECRET_KEY="rps_your_secret_key_here"
```

## 📚 Usage Examples

### Volume Management (REST API)
```bash
curl -H "Authorization: Bearer rpa_your_api_key" \
     https://rest.runpod.io/v1/networkvolumes
```

### File Operations (S3 API)
```bash
# Using AWS CLI
aws s3 ls --endpoint-url https://s3api-eu-ro-1.runpod.io/ \
          --region EU-RO-1 \
          s3://your-volume-id/

# Using boto3
import boto3

s3 = boto3.client(
    's3',
    aws_access_key_id='user_your_access_key',
    aws_secret_access_key='rps_your_secret_key',
    region_name='EU-RO-1',
    endpoint_url='https://s3api-eu-ro-1.runpod.io/'
)
```

## ⚠️ Important Notes

1. **Separate Credentials**: Volume and file operations require different API keys
2. **Region Matching**: S3 operations must use the correct datacenter endpoint
3. **Volume as Bucket**: In S3 operations, volume ID acts as the S3 bucket name
4. **Security**: Never commit credentials to code - use environment variables
5. **Key Prefixes**: 
   - API keys start with `rpa_`
   - S3 access keys start with `user_`  
   - S3 secret keys start with `rps_`

## 🛠️ SDK Usage

Our Python SDK handles both APIs automatically:

```python
from runpod_storage import RunpodStorageAPI

# Automatically uses both RUNPOD_API_KEY and S3 credentials
api = RunpodStorageAPI()

# Volume management (uses REST API)
volume = api.create_volume("my-volume", 50, "EU-RO-1")

# File operations (uses S3 API)
api.upload_file("local.txt", volume['id'], "remote.txt")
```