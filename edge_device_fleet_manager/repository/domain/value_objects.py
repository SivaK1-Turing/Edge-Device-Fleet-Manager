"""
Domain value objects for device repository.

Value objects are immutable objects that represent concepts in the domain
and are defined by their attributes rather than identity.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from ...core.exceptions import ValidationError


@dataclass(frozen=True)
class DeviceId:
    """Device identifier value object."""
    
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValidationError("DeviceId must be a valid UUID")
    
    @classmethod
    def generate(cls) -> 'DeviceId':
        """Generate a new device ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'DeviceId':
        """Create DeviceId from string."""
        try:
            return cls(UUID(value))
        except ValueError as e:
            raise ValidationError(f"Invalid device ID format: {value}") from e
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class DeviceIdentifier:
    """Device hardware identifier value object."""
    
    serial_number: str
    mac_address: Optional[str] = None
    hardware_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.serial_number or not self.serial_number.strip():
            raise ValidationError("Serial number is required")
        
        if len(self.serial_number) > 100:
            raise ValidationError("Serial number too long (max 100 characters)")
        
        if self.mac_address and not self._is_valid_mac_address(self.mac_address):
            raise ValidationError(f"Invalid MAC address format: {self.mac_address}")
    
    @staticmethod
    def _is_valid_mac_address(mac: str) -> bool:
        """Validate MAC address format."""
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    def __str__(self) -> str:
        parts = [f"SN:{self.serial_number}"]
        if self.mac_address:
            parts.append(f"MAC:{self.mac_address}")
        if self.hardware_id:
            parts.append(f"HW:{self.hardware_id}")
        return " | ".join(parts)


@dataclass(frozen=True)
class DeviceLocation:
    """Device physical location value object."""
    
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    altitude: Optional[Decimal] = None
    address: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    
    def __post_init__(self):
        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValidationError("Latitude must be between -90 and 90 degrees")
        
        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValidationError("Longitude must be between -180 and 180 degrees")
        
        if self.address and len(self.address) > 500:
            raise ValidationError("Address too long (max 500 characters)")
    
    @property
    def has_coordinates(self) -> bool:
        """Check if location has GPS coordinates."""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def has_physical_location(self) -> bool:
        """Check if location has physical address information."""
        return any([self.address, self.building, self.floor, self.room])
    
    def __str__(self) -> str:
        parts = []
        
        if self.has_coordinates:
            parts.append(f"GPS: {self.latitude}, {self.longitude}")
            if self.altitude:
                parts[-1] += f", {self.altitude}m"
        
        if self.address:
            parts.append(f"Address: {self.address}")
        
        if self.building:
            location_parts = [self.building]
            if self.floor:
                location_parts.append(f"Floor {self.floor}")
            if self.room:
                location_parts.append(f"Room {self.room}")
            parts.append(" - ".join(location_parts))
        
        return " | ".join(parts) if parts else "No location specified"


@dataclass(frozen=True)
class DeviceCapabilities:
    """Device capabilities and features value object."""
    
    supported_protocols: List[str]
    sensors: List[str] = None
    actuators: List[str] = None
    connectivity: List[str] = None
    power_source: Optional[str] = None
    operating_system: Optional[str] = None
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    memory_mb: Optional[int] = None
    storage_mb: Optional[int] = None
    cpu_cores: Optional[int] = None
    
    def __post_init__(self):
        if not self.supported_protocols:
            raise ValidationError("At least one supported protocol is required")
        
        # Set default empty lists
        object.__setattr__(self, 'sensors', self.sensors or [])
        object.__setattr__(self, 'actuators', self.actuators or [])
        object.__setattr__(self, 'connectivity', self.connectivity or [])
        
        # Validate numeric values
        if self.memory_mb is not None and self.memory_mb < 0:
            raise ValidationError("Memory size cannot be negative")
        
        if self.storage_mb is not None and self.storage_mb < 0:
            raise ValidationError("Storage size cannot be negative")
        
        if self.cpu_cores is not None and self.cpu_cores < 1:
            raise ValidationError("CPU cores must be at least 1")
    
    @property
    def has_sensors(self) -> bool:
        """Check if device has sensors."""
        return len(self.sensors) > 0
    
    @property
    def has_actuators(self) -> bool:
        """Check if device has actuators."""
        return len(self.actuators) > 0
    
    @property
    def is_battery_powered(self) -> bool:
        """Check if device is battery powered."""
        return self.power_source and 'battery' in self.power_source.lower()
    
    def supports_protocol(self, protocol: str) -> bool:
        """Check if device supports a specific protocol."""
        return protocol.lower() in [p.lower() for p in self.supported_protocols]
    
    def __str__(self) -> str:
        parts = [f"Protocols: {', '.join(self.supported_protocols)}"]
        
        if self.sensors:
            parts.append(f"Sensors: {', '.join(self.sensors)}")
        
        if self.actuators:
            parts.append(f"Actuators: {', '.join(self.actuators)}")
        
        if self.connectivity:
            parts.append(f"Connectivity: {', '.join(self.connectivity)}")
        
        if self.power_source:
            parts.append(f"Power: {self.power_source}")
        
        return " | ".join(parts)


@dataclass(frozen=True)
class DeviceMetrics:
    """Device metrics and telemetry value object."""
    
    timestamp: datetime
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    temperature_celsius: Optional[float] = None
    battery_level_percent: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None
    uptime_seconds: Optional[int] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.timestamp:
            raise ValidationError("Timestamp is required for metrics")
        
        # Validate percentage values
        for field_name, value in [
            ('cpu_usage_percent', self.cpu_usage_percent),
            ('memory_usage_percent', self.memory_usage_percent),
            ('disk_usage_percent', self.disk_usage_percent),
            ('battery_level_percent', self.battery_level_percent),
        ]:
            if value is not None and not (0 <= value <= 100):
                raise ValidationError(f"{field_name} must be between 0 and 100")
        
        # Validate network bytes
        for field_name, value in [
            ('network_bytes_sent', self.network_bytes_sent),
            ('network_bytes_received', self.network_bytes_received),
        ]:
            if value is not None and value < 0:
                raise ValidationError(f"{field_name} cannot be negative")
        
        if self.uptime_seconds is not None and self.uptime_seconds < 0:
            raise ValidationError("Uptime cannot be negative")
        
        # Set default empty dict for custom metrics
        if self.custom_metrics is None:
            object.__setattr__(self, 'custom_metrics', {})
    
    @classmethod
    def create_now(cls, **kwargs) -> 'DeviceMetrics':
        """Create metrics with current timestamp."""
        return cls(timestamp=datetime.now(timezone.utc), **kwargs)
    
    @property
    def age_seconds(self) -> float:
        """Get age of metrics in seconds."""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()
    
    @property
    def is_recent(self, max_age_seconds: int = 300) -> bool:
        """Check if metrics are recent (within max_age_seconds)."""
        return self.age_seconds <= max_age_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_percent': self.memory_usage_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'temperature_celsius': self.temperature_celsius,
            'battery_level_percent': self.battery_level_percent,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_received': self.network_bytes_received,
            'uptime_seconds': self.uptime_seconds,
        }
        
        if self.custom_metrics:
            result['custom_metrics'] = self.custom_metrics
        
        return {k: v for k, v in result.items() if v is not None}
    
    def __str__(self) -> str:
        parts = [f"Timestamp: {self.timestamp.isoformat()}"]
        
        if self.cpu_usage_percent is not None:
            parts.append(f"CPU: {self.cpu_usage_percent:.1f}%")
        
        if self.memory_usage_percent is not None:
            parts.append(f"Memory: {self.memory_usage_percent:.1f}%")
        
        if self.temperature_celsius is not None:
            parts.append(f"Temp: {self.temperature_celsius:.1f}°C")
        
        if self.battery_level_percent is not None:
            parts.append(f"Battery: {self.battery_level_percent:.1f}%")
        
        return " | ".join(parts)
