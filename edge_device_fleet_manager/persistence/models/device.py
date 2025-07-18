"""
Device Model

SQLAlchemy model for edge devices with comprehensive attributes,
custom indexes, and foreign key constraints for optimal performance.
"""

import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import INET, MACADDR, UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class DeviceStatus(enum.Enum):
    """Device operational status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    UNKNOWN = "unknown"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"


class DeviceType(enum.Enum):
    """Device type classification."""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CONTROLLER = "controller"
    CAMERA = "camera"
    DISPLAY = "display"
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    UNKNOWN = "unknown"


class Device(BaseModel):
    """
    Edge device model with comprehensive attributes and relationships.
    
    Represents physical or virtual devices in the fleet with detailed
    configuration, status tracking, and relationship management.
    """
    
    __tablename__ = "devices"
    
    # Basic device information
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable device name"
    )
    
    hostname = Column(
        String(255),
        nullable=True,
        comment="Network hostname of the device"
    )
    
    device_type = Column(
        Enum(DeviceType),
        nullable=False,
        default=DeviceType.UNKNOWN,
        comment="Type classification of the device"
    )
    
    status = Column(
        Enum(DeviceStatus),
        nullable=False,
        default=DeviceStatus.UNKNOWN,
        comment="Current operational status"
    )
    
    # Network configuration
    ip_address = Column(
        INET,
        nullable=True,
        comment="Primary IP address of the device"
    )
    
    mac_address = Column(
        MACADDR,
        nullable=True,
        comment="MAC address of the primary network interface"
    )
    
    port = Column(
        Integer,
        nullable=True,
        comment="Primary communication port"
    )
    
    # Hardware information
    manufacturer = Column(
        String(255),
        nullable=True,
        comment="Device manufacturer"
    )
    
    model = Column(
        String(255),
        nullable=True,
        comment="Device model number"
    )
    
    serial_number = Column(
        String(255),
        nullable=True,
        comment="Device serial number"
    )
    
    firmware_version = Column(
        String(100),
        nullable=True,
        comment="Current firmware version"
    )
    
    hardware_version = Column(
        String(100),
        nullable=True,
        comment="Hardware version"
    )
    
    # Location and environment
    location = Column(
        String(500),
        nullable=True,
        comment="Physical location description"
    )
    
    latitude = Column(
        Float,
        nullable=True,
        comment="GPS latitude coordinate"
    )
    
    longitude = Column(
        Float,
        nullable=True,
        comment="GPS longitude coordinate"
    )
    
    altitude = Column(
        Float,
        nullable=True,
        comment="Altitude in meters"
    )
    
    # Operational information
    last_seen = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last communication"
    )
    
    last_heartbeat = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last heartbeat signal"
    )
    
    uptime_seconds = Column(
        Integer,
        nullable=True,
        comment="Device uptime in seconds"
    )
    
    # Configuration and capabilities
    configuration = Column(
        JSON,
        nullable=True,
        comment="Device configuration as JSON"
    )
    
    capabilities = Column(
        JSON,
        nullable=True,
        comment="Device capabilities and features"
    )
    
    tags = Column(
        JSON,
        nullable=True,
        comment="User-defined tags for categorization"
    )
    
    # Security and authentication
    auth_token = Column(
        String(500),
        nullable=True,
        comment="Authentication token for device communication"
    )
    
    certificate_fingerprint = Column(
        String(255),
        nullable=True,
        comment="SSL/TLS certificate fingerprint"
    )
    
    # Monitoring and health
    health_score = Column(
        Float,
        nullable=True,
        comment="Overall health score (0.0 to 1.0)"
    )
    
    battery_level = Column(
        Float,
        nullable=True,
        comment="Battery level percentage (0.0 to 100.0)"
    )
    
    signal_strength = Column(
        Float,
        nullable=True,
        comment="Signal strength in dBm"
    )
    
    # Relationships
    device_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('device_groups.id', name=create_foreign_key_constraint(
            'devices', 'device_group_id', 'device_groups', 'id'
        )),
        nullable=True,
        comment="Reference to device group"
    )
    
    parent_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'devices', 'parent_device_id', 'devices', 'id'
        )),
        nullable=True,
        comment="Reference to parent device (for hierarchical relationships)"
    )
    
    # Relationship definitions
    device_group = relationship(
        "DeviceGroup",
        back_populates="devices",
        lazy="select"
    )
    
    parent_device = relationship(
        "Device",
        remote_side="Device.id",
        back_populates="child_devices",
        lazy="select"
    )
    
    child_devices = relationship(
        "Device",
        back_populates="parent_device",
        lazy="select"
    )
    
    telemetry_events = relationship(
        "TelemetryEvent",
        back_populates="device",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    alerts = relationship(
        "Alert",
        back_populates="device",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        # Unique constraints
        UniqueConstraint('serial_number', name='uniq_devices_serial_number'),
        UniqueConstraint('mac_address', name='uniq_devices_mac_address'),
        
        # Check constraints
        CheckConstraint(
            'health_score >= 0.0 AND health_score <= 1.0',
            name='chk_devices_health_score_range'
        ),
        CheckConstraint(
            'battery_level >= 0.0 AND battery_level <= 100.0',
            name='chk_devices_battery_level_range'
        ),
        CheckConstraint(
            'latitude >= -90.0 AND latitude <= 90.0',
            name='chk_devices_latitude_range'
        ),
        CheckConstraint(
            'longitude >= -180.0 AND longitude <= 180.0',
            name='chk_devices_longitude_range'
        ),
        CheckConstraint(
            'port > 0 AND port <= 65535',
            name='chk_devices_port_range'
        ),
        
        # Indexes for performance
        Index('idx_devices_status', 'status'),
        Index('idx_devices_device_type', 'device_type'),
        Index('idx_devices_ip_address', 'ip_address'),
        Index('idx_devices_last_seen', 'last_seen'),
        Index('idx_devices_location', 'location'),
        Index('idx_devices_device_group_id', 'device_group_id'),
        Index('idx_devices_parent_device_id', 'parent_device_id'),
        Index('idx_devices_manufacturer_model', 'manufacturer', 'model'),
        Index('idx_devices_coordinates', 'latitude', 'longitude'),
        
        # Partial indexes for active devices
        Index(
            'idx_devices_active_status',
            'status',
            postgresql_where="is_deleted = false"
        ),
        Index(
            'idx_devices_active_last_seen',
            'last_seen',
            postgresql_where="is_deleted = false AND status = 'online'"
        ),
        
        # Composite indexes for common queries
        Index('idx_devices_type_status', 'device_type', 'status'),
        Index('idx_devices_group_status', 'device_group_id', 'status'),
    )
    
    # Validation methods
    @validates('health_score')
    def validate_health_score(self, key, value):
        """Validate health score is within valid range."""
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("Health score must be between 0.0 and 1.0")
        return value
    
    @validates('battery_level')
    def validate_battery_level(self, key, value):
        """Validate battery level is within valid range."""
        if value is not None and not (0.0 <= value <= 100.0):
            raise ValueError("Battery level must be between 0.0 and 100.0")
        return value
    
    @validates('port')
    def validate_port(self, key, value):
        """Validate port number is within valid range."""
        if value is not None and not (1 <= value <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return value
    
    # Hybrid properties
    @hybrid_property
    def is_online(self) -> bool:
        """Check if device is currently online."""
        return self.status == DeviceStatus.ONLINE
    
    @hybrid_property
    def is_healthy(self) -> bool:
        """Check if device is considered healthy."""
        return (
            self.status in [DeviceStatus.ONLINE, DeviceStatus.MAINTENANCE] and
            (self.health_score is None or self.health_score >= 0.7)
        )
    
    @hybrid_property
    def has_location(self) -> bool:
        """Check if device has GPS coordinates."""
        return self.latitude is not None and self.longitude is not None
    
    # Business logic methods
    def update_last_seen(self) -> None:
        """Update the last seen timestamp to current time."""
        self.last_seen = datetime.now(timezone.utc)
    
    def update_heartbeat(self) -> None:
        """Update the heartbeat timestamp to current time."""
        self.last_heartbeat = datetime.now(timezone.utc)
        if self.status == DeviceStatus.OFFLINE:
            self.status = DeviceStatus.ONLINE
    
    def set_offline(self) -> None:
        """Mark device as offline."""
        self.status = DeviceStatus.OFFLINE
    
    def calculate_distance_to(self, other_device: 'Device') -> Optional[float]:
        """
        Calculate distance to another device in kilometers.
        
        Args:
            other_device: Another device with GPS coordinates
            
        Returns:
            Distance in kilometers, or None if coordinates are missing
        """
        if not (self.has_location and other_device.has_location):
            return None
        
        from math import radians, sin, cos, sqrt, atan2
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other_device.latitude), radians(other_device.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def __repr__(self) -> str:
        """String representation of the device."""
        return f"<Device(id={self.id}, name='{self.name}', status={self.status.value})>"
