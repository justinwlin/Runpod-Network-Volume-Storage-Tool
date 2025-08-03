"""
Exception classes for Runpod Storage.

Provides a comprehensive hierarchy of exceptions for different error scenarios.
"""

from typing import Any, Dict, Optional


class RunpodStorageError(Exception):
    """Base exception for all Runpod Storage errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class AuthenticationError(RunpodStorageError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AuthorizationError(RunpodStorageError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization failed") -> None:
        super().__init__(message)


class VolumeNotFoundError(RunpodStorageError):
    """Raised when a volume is not found."""

    def __init__(self, volume_id: str) -> None:
        super().__init__(f"Volume not found: {volume_id}", {"volume_id": volume_id})
        self.volume_id = volume_id


class VolumeError(RunpodStorageError):
    """Raised for volume-related errors."""

    def __init__(self, message: str, volume_id: Optional[str] = None) -> None:
        details = {"volume_id": volume_id} if volume_id else {}
        super().__init__(message, details)
        self.volume_id = volume_id


class FileNotFoundError(RunpodStorageError):
    """Raised when a file is not found."""

    def __init__(self, file_path: str, volume_id: Optional[str] = None) -> None:
        details = {"file_path": file_path, "volume_id": volume_id}
        super().__init__(f"File not found: {file_path}", details)
        self.file_path = file_path
        self.volume_id = volume_id


class InsufficientStorageError(RunpodStorageError):
    """Raised when there's insufficient storage space."""

    def __init__(self, message: str = "Insufficient storage space") -> None:
        super().__init__(message)


class NetworkError(RunpodStorageError):
    """Raised for network-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        details = {"status_code": status_code} if status_code else {}
        super().__init__(message, details)
        self.status_code = status_code


class ValidationError(RunpodStorageError):
    """Raised for input validation errors."""

    def __init__(self, field: str, value: Any, message: str) -> None:
        details = {"field": field, "value": value}
        super().__init__(f"Validation error for {field}: {message}", details)
        self.field = field
        self.value = value


class ConfigurationError(RunpodStorageError):
    """Raised for configuration-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class UploadError(RunpodStorageError):
    """Raised for upload-related errors."""

    def __init__(self, message: str, file_path: Optional[str] = None) -> None:
        details = {"file_path": file_path} if file_path else {}
        super().__init__(message, details)
        self.file_path = file_path


class DownloadError(RunpodStorageError):
    """Raised for download-related errors."""

    def __init__(self, message: str, file_path: Optional[str] = None) -> None:
        details = {"file_path": file_path} if file_path else {}
        super().__init__(message, details)
        self.file_path = file_path