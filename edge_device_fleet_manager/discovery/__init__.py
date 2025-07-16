"""
High-Performance Device Discovery System.

This module provides comprehensive device discovery capabilities for IoT edge devices
using multiple protocols including mDNS, SSDP, and network scanning with advanced
features like rate limiting, caching, and real-time monitoring.
"""

from .core import (
    Device,
    DeviceRegistry,
    DiscoveryEngine,
    DiscoveryProtocol,
    DiscoveryResult,
    DeviceType,
    DeviceStatus,
)
from .protocols import (
    MDNSDiscovery,
    SSDPDiscovery,
    NetworkScanDiscovery,
)
from .cache import DiscoveryCache
from .rate_limiter import RateLimiter
from .exceptions import (
    DiscoveryError,
    DiscoveryTimeoutError,
    RateLimitExceededError,
    DeviceNotFoundError,
)

__all__ = [
    # Core classes
    "Device",
    "DeviceRegistry", 
    "DiscoveryEngine",
    "DiscoveryProtocol",
    "DiscoveryResult",
    "DeviceType",
    "DeviceStatus",
    
    # Protocol implementations
    "MDNSDiscovery",
    "SSDPDiscovery", 
    "NetworkScanDiscovery",
    
    # Supporting classes
    "DiscoveryCache",
    "RateLimiter",
    
    # Exceptions
    "DiscoveryError",
    "DiscoveryTimeoutError",
    "RateLimitExceededError",
    "DeviceNotFoundError",
]
