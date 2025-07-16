"""
Domain entities for device repository.

Entities are objects that have identity and lifecycle, representing core business concepts
in the device management domain.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .value_objects import (
    DeviceId, DeviceIdentifier, DeviceLocation, 
    DeviceCapabilities, DeviceMetrics
)
from .events import (
    DomainEvent, DeviceRegisteredEvent, DeviceUpdatedEvent, 
    DeviceDeactivatedEvent, DeviceActivatedEvent, DeviceConfigurationChangedEvent,
    DeviceMetricsRecordedEvent, DeviceLocationChangedEvent, DeviceCapabilitiesUpdatedEvent
)
from ...core.exceptions import ValidationError


class DeviceStatus(Enum):
    """Device status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class DeviceType(Enum):
    """Device type enumeration."""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CONTROLLER = "controller"
    CAMERA = "camera"
    DISPLAY = "display"
    ROUTER = "router"
    SWITCH = "switch"
    OTHER = "other"


@dataclass
class DeviceConfiguration:
    """Device configuration entity."""
    
    device_id: DeviceId
    configuration: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_configuration(self, key: str, value: Any, changed_by: Optional[str] = None) -> DomainEvent:
        """Update a configuration value."""
        previous_value = self.configuration.get(key)
        self.configuration[key] = value
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
        
        return DeviceConfigurationChangedEvent(
            aggregate_id=self.device_id,
            configuration_key=key,
            new_value=value,
            previous_value=previous_value,
            changed_by=changed_by,
            version=self.version
        )
    
    def remove_configuration(self, key: str, changed_by: Optional[str] = None) -> Optional[DomainEvent]:
        """Remove a configuration value."""
        if key in self.configuration:
            previous_value = self.configuration.pop(key)
            self.version += 1
            self.updated_at = datetime.now(timezone.utc)
            
            return DeviceConfigurationChangedEvent(
                aggregate_id=self.device_id,
                configuration_key=key,
                new_value=None,
                previous_value=previous_value,
                changed_by=changed_by,
                version=self.version
            )
        return None
    
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.configuration.get(key, default)


@dataclass
class DeviceEntity:
    """Core device entity."""
    
    device_id: DeviceId
    name: str
    device_type: DeviceType
    identifier: DeviceIdentifier
    status: DeviceStatus = DeviceStatus.ACTIVE
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    location: Optional[DeviceLocation] = None
    capabilities: Optional[DeviceCapabilities] = None
    configuration: Optional[DeviceConfiguration] = None
    last_seen: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValidationError("Device name is required")
        
        if len(self.name) > 200:
            raise ValidationError("Device name too long (max 200 characters)")
        
        if self.configuration is None:
            self.configuration = DeviceConfiguration(device_id=self.device_id)
    
    def update_name(self, new_name: str) -> DomainEvent:
        """Update device name."""
        if not new_name or not new_name.strip():
            raise ValidationError("Device name cannot be empty")
        
        if len(new_name) > 200:
            raise ValidationError("Device name too long (max 200 characters)")
        
        previous_name = self.name
        self.name = new_name.strip()
        self._update_version()
        
        return DeviceUpdatedEvent(
            aggregate_id=self.device_id,
            updated_fields={'name': new_name},
            previous_values={'name': previous_name},
            version=self.version
        )
    
    def update_location(self, new_location: DeviceLocation) -> DomainEvent:
        """Update device location."""
        previous_location = self.location
        self.location = new_location
        self._update_version()
        
        return DeviceLocationChangedEvent(
            aggregate_id=self.device_id,
            new_location=new_location,
            previous_location=previous_location,
            version=self.version
        )
    
    def update_capabilities(self, new_capabilities: DeviceCapabilities) -> DomainEvent:
        """Update device capabilities."""
        previous_capabilities = self.capabilities
        self.capabilities = new_capabilities
        self._update_version()
        
        return DeviceCapabilitiesUpdatedEvent(
            aggregate_id=self.device_id,
            new_capabilities=new_capabilities,
            previous_capabilities=previous_capabilities,
            version=self.version
        )
    
    def deactivate(self, reason: str, deactivated_by: Optional[str] = None) -> DomainEvent:
        """Deactivate the device."""
        if self.status == DeviceStatus.DECOMMISSIONED:
            raise ValidationError("Cannot deactivate a decommissioned device")
        
        self.status = DeviceStatus.INACTIVE
        self._update_version()
        
        return DeviceDeactivatedEvent(
            aggregate_id=self.device_id,
            reason=reason,
            deactivated_by=deactivated_by,
            version=self.version
        )
    
    def activate(self, activated_by: Optional[str] = None) -> DomainEvent:
        """Activate the device."""
        if self.status == DeviceStatus.DECOMMISSIONED:
            raise ValidationError("Cannot activate a decommissioned device")
        
        self.status = DeviceStatus.ACTIVE
        self._update_version()
        
        return DeviceActivatedEvent(
            aggregate_id=self.device_id,
            activated_by=activated_by,
            version=self.version
        )
    
    def set_maintenance_mode(self) -> DomainEvent:
        """Set device to maintenance mode."""
        if self.status == DeviceStatus.DECOMMISSIONED:
            raise ValidationError("Cannot set maintenance mode on decommissioned device")
        
        previous_status = self.status.value
        self.status = DeviceStatus.MAINTENANCE
        self._update_version()
        
        return DeviceUpdatedEvent(
            aggregate_id=self.device_id,
            updated_fields={'status': self.status.value},
            previous_values={'status': previous_status},
            version=self.version
        )
    
    def record_metrics(self, metrics: DeviceMetrics) -> DomainEvent:
        """Record device metrics."""
        self.last_seen = metrics.timestamp
        self._update_version()
        
        return DeviceMetricsRecordedEvent(
            aggregate_id=self.device_id,
            metrics=metrics,
            version=self.version
        )
    
    def update_last_seen(self, timestamp: Optional[datetime] = None) -> None:
        """Update last seen timestamp."""
        self.last_seen = timestamp or datetime.now(timezone.utc)
        self._update_version()
    
    def is_online(self, timeout_seconds: int = 300) -> bool:
        """Check if device is considered online."""
        if not self.last_seen:
            return False
        
        age = (datetime.now(timezone.utc) - self.last_seen).total_seconds()
        return age <= timeout_seconds
    
    def _update_version(self) -> None:
        """Update entity version and timestamp."""
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class DeviceGroup:
    """Device group entity for organizing devices."""
    
    group_id: DeviceId
    name: str
    description: Optional[str] = None
    device_ids: List[DeviceId] = field(default_factory=list)
    parent_group_id: Optional[DeviceId] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValidationError("Group name is required")
        
        if len(self.name) > 200:
            raise ValidationError("Group name too long (max 200 characters)")
    
    def add_device(self, device_id: DeviceId) -> None:
        """Add a device to the group."""
        if device_id not in self.device_ids:
            self.device_ids.append(device_id)
            self._update_version()
    
    def remove_device(self, device_id: DeviceId) -> bool:
        """Remove a device from the group."""
        if device_id in self.device_ids:
            self.device_ids.remove(device_id)
            self._update_version()
            return True
        return False
    
    def update_name(self, new_name: str) -> None:
        """Update group name."""
        if not new_name or not new_name.strip():
            raise ValidationError("Group name cannot be empty")
        
        if len(new_name) > 200:
            raise ValidationError("Group name too long (max 200 characters)")
        
        self.name = new_name.strip()
        self._update_version()
    
    def update_description(self, new_description: Optional[str]) -> None:
        """Update group description."""
        self.description = new_description
        self._update_version()
    
    def get_device_count(self) -> int:
        """Get number of devices in group."""
        return len(self.device_ids)
    
    def _update_version(self) -> None:
        """Update entity version and timestamp."""
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)


class DeviceAggregate:
    """Device aggregate root that encapsulates device entity and related behavior."""

    def __init__(self, device: DeviceEntity):
        self._device = device
        self._uncommitted_events: List[DomainEvent] = []
        self._metrics_history: List[DeviceMetrics] = []

    @property
    def device_id(self) -> DeviceId:
        """Get device ID."""
        return self._device.device_id

    @property
    def device(self) -> DeviceEntity:
        """Get device entity."""
        return self._device

    @property
    def version(self) -> int:
        """Get aggregate version."""
        return self._device.version

    @classmethod
    def create(
        cls,
        device_id: DeviceId,
        name: str,
        device_type: DeviceType,
        identifier: DeviceIdentifier,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        location: Optional[DeviceLocation] = None,
        capabilities: Optional[DeviceCapabilities] = None,
    ) -> 'DeviceAggregate':
        """Create a new device aggregate."""
        device = DeviceEntity(
            device_id=device_id,
            name=name,
            device_type=device_type,
            identifier=identifier,
            manufacturer=manufacturer,
            model=model,
            location=location,
            capabilities=capabilities,
        )

        aggregate = cls(device)

        # Raise domain event for device registration
        event = DeviceRegisteredEvent(
            aggregate_id=device_id,
            device_name=name,
            device_type=device_type.value,
            identifier=identifier,
            manufacturer=manufacturer,
            model=model,
            location=location,
            capabilities=capabilities,
            version=device.version
        )

        aggregate._add_event(event)
        return aggregate

    def update_name(self, new_name: str) -> None:
        """Update device name."""
        event = self._device.update_name(new_name)
        self._add_event(event)

    def update_location(self, new_location: DeviceLocation) -> None:
        """Update device location."""
        event = self._device.update_location(new_location)
        self._add_event(event)

    def update_capabilities(self, new_capabilities: DeviceCapabilities) -> None:
        """Update device capabilities."""
        event = self._device.update_capabilities(new_capabilities)
        self._add_event(event)

    def deactivate(self, reason: str, deactivated_by: Optional[str] = None) -> None:
        """Deactivate the device."""
        event = self._device.deactivate(reason, deactivated_by)
        self._add_event(event)

    def activate(self, activated_by: Optional[str] = None) -> None:
        """Activate the device."""
        event = self._device.activate(activated_by)
        self._add_event(event)

    def set_maintenance_mode(self) -> None:
        """Set device to maintenance mode."""
        event = self._device.set_maintenance_mode()
        self._add_event(event)

    def record_metrics(self, metrics: DeviceMetrics) -> None:
        """Record device metrics."""
        event = self._device.record_metrics(metrics)
        self._metrics_history.append(metrics)

        # Keep only recent metrics (last 100 entries)
        if len(self._metrics_history) > 100:
            self._metrics_history = self._metrics_history[-100:]

        self._add_event(event)

    def update_configuration(self, key: str, value: Any, changed_by: Optional[str] = None) -> None:
        """Update device configuration."""
        if self._device.configuration:
            event = self._device.configuration.update_configuration(key, value, changed_by)
            self._add_event(event)

    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get device configuration value."""
        if self._device.configuration:
            return self._device.configuration.get_configuration(key, default)
        return default

    def get_recent_metrics(self, count: int = 10) -> List[DeviceMetrics]:
        """Get recent metrics."""
        return self._metrics_history[-count:] if self._metrics_history else []

    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get uncommitted domain events."""
        return self._uncommitted_events.copy()

    def mark_events_as_committed(self) -> None:
        """Mark all events as committed."""
        self._uncommitted_events.clear()

    def _add_event(self, event: DomainEvent) -> None:
        """Add domain event to uncommitted events."""
        self._uncommitted_events.append(event)
