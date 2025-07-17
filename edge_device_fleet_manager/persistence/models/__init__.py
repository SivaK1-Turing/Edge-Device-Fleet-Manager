"""
Database Models Package

SQLAlchemy Core/ORM hybrid models for the Edge Device Fleet Manager.
Provides comprehensive data models with custom indexes, foreign key constraints,
and optimized queries for high-performance operations.
"""

from .base import Base, BaseModel, TimestampMixin, SoftDeleteMixin
from .device import Device, DeviceStatus, DeviceType
from .telemetry import TelemetryEvent, TelemetryType, TelemetryData
from .analytics import Analytics, AnalyticsType, AnalyticsMetric
from .user import User, UserRole, UserStatus
from .device_group import DeviceGroup, DeviceGroupMembership
from .alert import Alert, AlertSeverity, AlertStatus, AlertRule
from .audit_log import AuditLog, AuditAction, AuditResource

__all__ = [
    # Base classes
    "Base",
    "BaseModel", 
    "TimestampMixin",
    "SoftDeleteMixin",
    
    # Device models
    "Device",
    "DeviceStatus",
    "DeviceType",
    
    # Telemetry models
    "TelemetryEvent",
    "TelemetryType",
    "TelemetryData",
    
    # Analytics models
    "Analytics",
    "AnalyticsType",
    "AnalyticsMetric",
    
    # User models
    "User",
    "UserRole",
    "UserStatus",
    
    # Device group models
    "DeviceGroup",
    "DeviceGroupMembership",
    
    # Alert models
    "Alert",
    "AlertSeverity",
    "AlertStatus", 
    "AlertRule",
    
    # Audit log models
    "AuditLog",
    "AuditAction",
    "AuditResource",
]
