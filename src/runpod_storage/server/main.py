"""
FastAPI server for Runpod Storage API.

Provides a complete REST API for Runpod storage operations with OpenAPI documentation.
"""


import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..core.models import HealthCheckResponse
from .routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Runpod Storage API",
        description="""
        Professional REST API for Runpod network storage management.

        This API provides comprehensive access to Runpod storage operations including:
        - Network volume management (create, list, delete)
        - File operations (upload, download, list, delete)
        - Robust error handling and validation
        - OpenAPI 3.0 compliant documentation

        ## Authentication

        All endpoints require authentication via API key. You can authenticate in several ways:

        1. **Bearer Token Header**: `Authorization: Bearer your-api-key`
        2. **API Key Header**: `X-API-Key: your-api-key`
        3. **Query Parameter**: `?api_key=your-api-key`

        Get your API key from [Runpod Console](https://console.runpod.io/user/settings).

        ## Rate Limiting

        API requests are subject to rate limiting. See response headers for current limits.

        ## SDKs and Tools

        - **Python SDK**: `pip install runpod-storage`
        - **CLI Tool**: `runpod-storage --help`
        - **Docker Image**: `docker run runpod/storage-api`
        """,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "Runpod Storage Team",
            "email": "support@runpod.io",
            "url": "https://github.com/runpod/runpod-storage",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "https://storage-api.runpod.io",
                "description": "Production server",
            },
            {"url": "http://localhost:8000", "description": "Development server"},
        ],
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/v1")

    @app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
    async def health_check() -> HealthCheckResponse:
        """Health check endpoint."""
        return HealthCheckResponse(status="healthy", version=__version__)

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Runpod Storage API",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
            "openapi": "/openapi.json",
        }

    return app


def main() -> None:
    """Main entry point for the server."""
    import argparse

    parser = argparse.ArgumentParser(description="Runpod Storage API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")

    args = parser.parse_args()

    app = create_app()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()
