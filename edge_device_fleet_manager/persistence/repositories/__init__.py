"""
Repository Pattern Implementation

Provides data access layer with repository pattern for clean separation
of concerns, async support, and comprehensive query capabilities.

Key Features:
- Generic repository base class
- Async/await support throughout
- Transaction management
- Query optimization
- Caching integration
- Audit trail support
- Bulk operations
- Pagination and filtering
"""

from .base import BaseRepository, RepositoryError
from .device import DeviceRepository
from .telemetry import TelemetryRepository
from .analytics import AnalyticsRepository
from .user import UserRepository
from .device_group import DeviceGroupRepository
from .alert import AlertRepository
from .audit_log import AuditLogRepository

__all__ = [
    # Base classes
    "BaseRepository",
    "RepositoryError",
    
    # Specific repositories
    "DeviceRepository",
    "TelemetryRepository",
    "AnalyticsRepository",
    "UserRepository",
    "DeviceGroupRepository",
    "AlertRepository",
    "AuditLogRepository",
]
