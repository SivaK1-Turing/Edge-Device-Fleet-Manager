"""
Domain events for device repository.

Domain events represent important business events that occur within the domain
and are used for event sourcing and inter-bounded context communication.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from .value_objects import DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities, DeviceMetrics


class DomainEvent(ABC):
    """Base class for all domain events."""

    def __init__(self, aggregate_id: DeviceId, version: int = 1,
                 event_id: UUID = None, occurred_at: datetime = None):
        self.aggregate_id = aggregate_id
        self.version = version
        self.event_id = event_id or uuid4()
        self.occurred_at = occurred_at or datetime.now(timezone.utc)
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type identifier."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': str(self.event_id),
            'event_type': self.event_type,
            'aggregate_id': str(self.aggregate_id),
            'occurred_at': self.occurred_at.isoformat(),
            'version': self.version,
            'data': self._get_event_data()
        }
    
    @abstractmethod
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data for serialization."""
        pass


class DeviceRegisteredEvent(DomainEvent):
    """Event raised when a new device is registered."""

    def __init__(self, aggregate_id: DeviceId, device_name: str, device_type: str,
                 identifier: DeviceIdentifier, manufacturer: Optional[str] = None,
                 model: Optional[str] = None, location: Optional[DeviceLocation] = None,
                 capabilities: Optional[DeviceCapabilities] = None, **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.device_name = device_name
        self.device_type = device_type
        self.identifier = identifier
        self.manufacturer = manufacturer
        self.model = model
        self.location = location
        self.capabilities = capabilities
    
    @property
    def event_type(self) -> str:
        return "device.registered"
    
    def _get_event_data(self) -> Dict[str, Any]:
        data = {
            'device_name': self.device_name,
            'device_type': self.device_type,
            'identifier': {
                'serial_number': self.identifier.serial_number,
                'mac_address': self.identifier.mac_address,
                'hardware_id': self.identifier.hardware_id,
            },
            'manufacturer': self.manufacturer,
            'model': self.model,
        }
        
        if self.location:
            data['location'] = {
                'latitude': str(self.location.latitude) if self.location.latitude else None,
                'longitude': str(self.location.longitude) if self.location.longitude else None,
                'altitude': str(self.location.altitude) if self.location.altitude else None,
                'address': self.location.address,
                'building': self.location.building,
                'floor': self.location.floor,
                'room': self.location.room,
            }
        
        if self.capabilities:
            data['capabilities'] = {
                'supported_protocols': self.capabilities.supported_protocols,
                'sensors': self.capabilities.sensors,
                'actuators': self.capabilities.actuators,
                'connectivity': self.capabilities.connectivity,
                'power_source': self.capabilities.power_source,
                'operating_system': self.capabilities.operating_system,
                'firmware_version': self.capabilities.firmware_version,
                'hardware_version': self.capabilities.hardware_version,
                'memory_mb': self.capabilities.memory_mb,
                'storage_mb': self.capabilities.storage_mb,
                'cpu_cores': self.capabilities.cpu_cores,
            }
        
        return data


class DeviceUpdatedEvent(DomainEvent):
    """Event raised when device information is updated."""

    def __init__(self, aggregate_id: DeviceId, updated_fields: Dict[str, Any],
                 previous_values: Dict[str, Any], **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.updated_fields = updated_fields
        self.previous_values = previous_values
    
    @property
    def event_type(self) -> str:
        return "device.updated"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'updated_fields': self.updated_fields,
            'previous_values': self.previous_values,
        }


class DeviceDeactivatedEvent(DomainEvent):
    """Event raised when a device is deactivated."""

    def __init__(self, aggregate_id: DeviceId, reason: str,
                 deactivated_by: Optional[str] = None, **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.reason = reason
        self.deactivated_by = deactivated_by
    
    @property
    def event_type(self) -> str:
        return "device.deactivated"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'reason': self.reason,
            'deactivated_by': self.deactivated_by,
        }


class DeviceActivatedEvent(DomainEvent):
    """Event raised when a device is activated."""

    def __init__(self, aggregate_id: DeviceId, activated_by: Optional[str] = None, **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.activated_by = activated_by
    
    @property
    def event_type(self) -> str:
        return "device.activated"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'activated_by': self.activated_by,
        }


class DeviceConfigurationChangedEvent(DomainEvent):
    """Event raised when device configuration is changed."""

    def __init__(self, aggregate_id: DeviceId, configuration_key: str, new_value: Any,
                 previous_value: Any, changed_by: Optional[str] = None, **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.configuration_key = configuration_key
        self.new_value = new_value
        self.previous_value = previous_value
        self.changed_by = changed_by
    
    @property
    def event_type(self) -> str:
        return "device.configuration.changed"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'configuration_key': self.configuration_key,
            'new_value': self.new_value,
            'previous_value': self.previous_value,
            'changed_by': self.changed_by,
        }


class DeviceMetricsRecordedEvent(DomainEvent):
    """Event raised when device metrics are recorded."""

    def __init__(self, aggregate_id: DeviceId, metrics: DeviceMetrics, **kwargs):
        super().__init__(aggregate_id, **kwargs)
        self.metrics = metrics
    
    @property
    def event_type(self) -> str:
        return "device.metrics.recorded"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'metrics': self.metrics.to_dict(),
        }


@dataclass(frozen=True)
class DeviceLocationChangedEvent(DomainEvent):
    """Event raised when device location is changed."""
    
    new_location: DeviceLocation
    previous_location: Optional[DeviceLocation] = None
    
    @property
    def event_type(self) -> str:
        return "device.location.changed"
    
    def _get_event_data(self) -> Dict[str, Any]:
        data = {
            'new_location': {
                'latitude': str(self.new_location.latitude) if self.new_location.latitude else None,
                'longitude': str(self.new_location.longitude) if self.new_location.longitude else None,
                'altitude': str(self.new_location.altitude) if self.new_location.altitude else None,
                'address': self.new_location.address,
                'building': self.new_location.building,
                'floor': self.new_location.floor,
                'room': self.new_location.room,
            }
        }
        
        if self.previous_location:
            data['previous_location'] = {
                'latitude': str(self.previous_location.latitude) if self.previous_location.latitude else None,
                'longitude': str(self.previous_location.longitude) if self.previous_location.longitude else None,
                'altitude': str(self.previous_location.altitude) if self.previous_location.altitude else None,
                'address': self.previous_location.address,
                'building': self.previous_location.building,
                'floor': self.previous_location.floor,
                'room': self.previous_location.room,
            }
        
        return data


@dataclass(frozen=True)
class DeviceCapabilitiesUpdatedEvent(DomainEvent):
    """Event raised when device capabilities are updated."""
    
    new_capabilities: DeviceCapabilities
    previous_capabilities: Optional[DeviceCapabilities] = None
    
    @property
    def event_type(self) -> str:
        return "device.capabilities.updated"
    
    def _get_event_data(self) -> Dict[str, Any]:
        data = {
            'new_capabilities': {
                'supported_protocols': self.new_capabilities.supported_protocols,
                'sensors': self.new_capabilities.sensors,
                'actuators': self.new_capabilities.actuators,
                'connectivity': self.new_capabilities.connectivity,
                'power_source': self.new_capabilities.power_source,
                'operating_system': self.new_capabilities.operating_system,
                'firmware_version': self.new_capabilities.firmware_version,
                'hardware_version': self.new_capabilities.hardware_version,
                'memory_mb': self.new_capabilities.memory_mb,
                'storage_mb': self.new_capabilities.storage_mb,
                'cpu_cores': self.new_capabilities.cpu_cores,
            }
        }
        
        if self.previous_capabilities:
            data['previous_capabilities'] = {
                'supported_protocols': self.previous_capabilities.supported_protocols,
                'sensors': self.previous_capabilities.sensors,
                'actuators': self.previous_capabilities.actuators,
                'connectivity': self.previous_capabilities.connectivity,
                'power_source': self.previous_capabilities.power_source,
                'operating_system': self.previous_capabilities.operating_system,
                'firmware_version': self.previous_capabilities.firmware_version,
                'hardware_version': self.previous_capabilities.hardware_version,
                'memory_mb': self.previous_capabilities.memory_mb,
                'storage_mb': self.previous_capabilities.storage_mb,
                'cpu_cores': self.previous_capabilities.cpu_cores,
            }
        
        return data
