"""
Discovery system exceptions.

This module defines custom exceptions for the device discovery system.
"""

from ..core.exceptions import EdgeFleetError


class DiscoveryError(EdgeFleetError):
    """Base exception for discovery-related errors."""
    pass


class DiscoveryTimeoutError(DiscoveryError):
    """Raised when a discovery operation times out."""
    pass


class RateLimitExceededError(DiscoveryError):
    """Raised when rate limits are exceeded."""
    pass


class DeviceNotFoundError(DiscoveryError):
    """Raised when a requested device is not found."""
    pass


class ProtocolNotAvailableError(DiscoveryError):
    """Raised when a discovery protocol is not available."""
    pass


class NetworkError(DiscoveryError):
    """Raised when network-related errors occur during discovery."""
    pass


class InvalidDeviceError(DiscoveryError):
    """Raised when device data is invalid or malformed."""
    pass


class CacheError(DiscoveryError):
    """Raised when cache operations fail."""
    pass
