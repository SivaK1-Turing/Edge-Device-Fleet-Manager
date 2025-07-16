"""
Core exceptions for Edge Device Fleet Manager.
"""

from typing import Any, Dict, Optional


class EdgeFleetError(Exception):
    """Base exception for all Edge Fleet Manager errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(EdgeFleetError):
    """Raised when there's an issue with configuration."""
    pass


class PluginError(EdgeFleetError):
    """Raised when there's an issue with plugin loading or execution."""
    pass


class DeviceError(EdgeFleetError):
    """Raised when there's an issue with device operations."""
    pass


class DiscoveryError(EdgeFleetError):
    """Raised when there's an issue with device discovery."""
    pass


class TelemetryError(EdgeFleetError):
    """Raised when there's an issue with telemetry processing."""
    pass


class RepositoryError(EdgeFleetError):
    """Raised when there's an issue with repository operations."""
    pass


class ValidationError(EdgeFleetError):
    """Raised when validation fails."""
    pass


class AuthenticationError(EdgeFleetError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(EdgeFleetError):
    """Raised when authorization fails."""
    pass


class NetworkError(EdgeFleetError):
    """Raised when there's a network-related error."""
    pass


class TimeoutError(EdgeFleetError):
    """Raised when an operation times out."""
    pass


class RateLimitError(EdgeFleetError):
    """Raised when rate limits are exceeded."""
    pass


class EncryptionError(EdgeFleetError):
    """Raised when there's an encryption/decryption error."""
    pass


class SecretsManagerError(EdgeFleetError):
    """Raised when there's an issue with AWS Secrets Manager."""
    pass
