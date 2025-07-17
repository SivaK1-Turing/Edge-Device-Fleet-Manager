"""
Robust Persistence & Migrations Package

This package provides comprehensive database persistence capabilities for the
Edge Device Fleet Manager, including:

- SQLAlchemy Core/ORM hybrid models
- Alembic-based migration system
- Repository pattern for data access
- Connection pooling and health monitoring
- Data validation and serialization
- Transaction management and error handling

Key Features:
- Async/await support throughout
- Custom indexes and foreign key constraints
- Automatic schema migrations
- Connection failover and retry logic
- Comprehensive logging and monitoring
- Type-safe data models with Pydantic integration
"""

from .models import *
from .repositories import *
from .migrations import *
from .connection import *

__all__ = [
    # Models
    "Device",
    "TelemetryEvent", 
    "Analytics",
    "User",
    "DeviceGroup",
    "Alert",
    "AuditLog",
    
    # Repositories
    "DeviceRepository",
    "TelemetryRepository",
    "AnalyticsRepository",
    "UserRepository",
    "DeviceGroupRepository",
    "AlertRepository",
    "AuditLogRepository",
    
    # Migration system
    "MigrationManager",
    "DatabaseMigrator",
    
    # Connection management
    "DatabaseManager",
    "ConnectionPool",
    "HealthChecker",
    
    # Schemas
    "DeviceSchema",
    "TelemetryEventSchema",
    "AnalyticsSchema",
    "UserSchema",
    "DeviceGroupSchema",
    "AlertSchema",
    "AuditLogSchema",
]
