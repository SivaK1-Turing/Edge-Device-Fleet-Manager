"""
Domain services for device repository.

Domain services contain business logic that doesn't naturally fit within entities
or value objects, often involving multiple aggregates or external dependencies.
"""

import re
from typing import List, Optional, Set
from datetime import datetime, timezone

from .entities import DeviceAggregate, DeviceEntity, DeviceType, DeviceStatus
from .value_objects import DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities
from ...core.exceptions import ValidationError


class DeviceValidationService:
    """Service for validating device data and business rules."""
    
    @staticmethod
    def validate_device_name(name: str) -> None:
        """Validate device name according to business rules."""
        if not name or not name.strip():
            raise ValidationError("Device name is required")
        
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError("Device name must be at least 2 characters long")
        
        if len(name) > 200:
            raise ValidationError("Device name cannot exceed 200 characters")
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            raise ValidationError("Device name contains invalid characters. Only letters, numbers, spaces, hyphens, underscores, and dots are allowed")
        
        # Check for reserved names
        reserved_names = {'admin', 'root', 'system', 'null', 'undefined'}
        if name.lower() in reserved_names:
            raise ValidationError(f"'{name}' is a reserved name and cannot be used")
    
    @staticmethod
    def validate_serial_number(serial_number: str) -> None:
        """Validate device serial number."""
        if not serial_number or not serial_number.strip():
            raise ValidationError("Serial number is required")
        
        serial_number = serial_number.strip()
        
        if len(serial_number) < 3:
            raise ValidationError("Serial number must be at least 3 characters long")
        
        if len(serial_number) > 100:
            raise ValidationError("Serial number cannot exceed 100 characters")
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9\-_]+$', serial_number):
            raise ValidationError("Serial number contains invalid characters. Only letters, numbers, hyphens, and underscores are allowed")
    
    @staticmethod
    def validate_device_type_compatibility(device_type: DeviceType, capabilities: DeviceCapabilities) -> None:
        """Validate that device capabilities are compatible with device type."""
        if device_type == DeviceType.SENSOR:
            if not capabilities.has_sensors:
                raise ValidationError("Sensor devices must have at least one sensor capability")
        
        elif device_type == DeviceType.ACTUATOR:
            if not capabilities.has_actuators:
                raise ValidationError("Actuator devices must have at least one actuator capability")
        
        elif device_type == DeviceType.GATEWAY:
            required_protocols = {'mqtt', 'http', 'https'}
            device_protocols = {p.lower() for p in capabilities.supported_protocols}
            if not required_protocols.intersection(device_protocols):
                raise ValidationError("Gateway devices must support at least one of: MQTT, HTTP, HTTPS")
        
        elif device_type == DeviceType.CAMERA:
            if 'video' not in [s.lower() for s in capabilities.sensors]:
                raise ValidationError("Camera devices must have video sensor capability")


class DeviceRegistrationService:
    """Service for device registration business logic."""
    
    def __init__(self, validation_service: DeviceValidationService):
        self.validation_service = validation_service
    
    def validate_registration_data(
        self,
        name: str,
        device_type: DeviceType,
        identifier: DeviceIdentifier,
        capabilities: Optional[DeviceCapabilities] = None
    ) -> None:
        """Validate all data required for device registration."""
        # Validate name
        self.validation_service.validate_device_name(name)
        
        # Validate serial number
        self.validation_service.validate_serial_number(identifier.serial_number)
        
        # Validate type compatibility with capabilities
        if capabilities:
            self.validation_service.validate_device_type_compatibility(device_type, capabilities)
    
    def create_device_aggregate(
        self,
        name: str,
        device_type: DeviceType,
        identifier: DeviceIdentifier,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        location: Optional[DeviceLocation] = None,
        capabilities: Optional[DeviceCapabilities] = None,
    ) -> DeviceAggregate:
        """Create a new device aggregate with validation."""
        # Validate registration data
        self.validate_registration_data(name, device_type, identifier, capabilities)
        
        # Generate device ID
        device_id = DeviceId.generate()
        
        # Create aggregate
        return DeviceAggregate.create(
            device_id=device_id,
            name=name.strip(),
            device_type=device_type,
            identifier=identifier,
            manufacturer=manufacturer,
            model=model,
            location=location,
            capabilities=capabilities,
        )
    
    def check_duplicate_identifier(
        self,
        identifier: DeviceIdentifier,
        existing_devices: List[DeviceEntity]
    ) -> Optional[DeviceEntity]:
        """Check if a device with the same identifier already exists."""
        for device in existing_devices:
            if device.identifier.serial_number == identifier.serial_number:
                return device
            
            # Check MAC address if both devices have it
            if (device.identifier.mac_address and identifier.mac_address and
                device.identifier.mac_address.lower() == identifier.mac_address.lower()):
                return device
        
        return None


class DeviceLifecycleService:
    """Service for managing device lifecycle operations."""
    
    def __init__(self, validation_service: DeviceValidationService):
        self.validation_service = validation_service
    
    def can_deactivate_device(self, device: DeviceEntity) -> tuple[bool, Optional[str]]:
        """Check if a device can be deactivated."""
        if device.status == DeviceStatus.DECOMMISSIONED:
            return False, "Cannot deactivate a decommissioned device"
        
        if device.status == DeviceStatus.INACTIVE:
            return False, "Device is already inactive"
        
        return True, None
    
    def can_activate_device(self, device: DeviceEntity) -> tuple[bool, Optional[str]]:
        """Check if a device can be activated."""
        if device.status == DeviceStatus.DECOMMISSIONED:
            return False, "Cannot activate a decommissioned device"
        
        if device.status == DeviceStatus.ACTIVE:
            return False, "Device is already active"
        
        return True, None
    
    def can_set_maintenance_mode(self, device: DeviceEntity) -> tuple[bool, Optional[str]]:
        """Check if a device can be set to maintenance mode."""
        if device.status == DeviceStatus.DECOMMISSIONED:
            return False, "Cannot set maintenance mode on decommissioned device"
        
        if device.status == DeviceStatus.MAINTENANCE:
            return False, "Device is already in maintenance mode"
        
        return True, None
    
    def can_decommission_device(self, device: DeviceEntity) -> tuple[bool, Optional[str]]:
        """Check if a device can be decommissioned."""
        if device.status == DeviceStatus.DECOMMISSIONED:
            return False, "Device is already decommissioned"
        
        return True, None
    
    def get_stale_devices(
        self,
        devices: List[DeviceEntity],
        stale_threshold_seconds: int = 86400  # 24 hours
    ) -> List[DeviceEntity]:
        """Get devices that haven't been seen recently."""
        now = datetime.now(timezone.utc)
        stale_devices = []
        
        for device in devices:
            if not device.last_seen:
                # Device has never been seen - consider stale
                stale_devices.append(device)
            else:
                age_seconds = (now - device.last_seen).total_seconds()
                if age_seconds > stale_threshold_seconds:
                    stale_devices.append(device)
        
        return stale_devices
    
    def get_devices_by_status(
        self,
        devices: List[DeviceEntity],
        status: DeviceStatus
    ) -> List[DeviceEntity]:
        """Get devices with specific status."""
        return [device for device in devices if device.status == status]
    
    def get_devices_by_type(
        self,
        devices: List[DeviceEntity],
        device_type: DeviceType
    ) -> List[DeviceEntity]:
        """Get devices of specific type."""
        return [device for device in devices if device.device_type == device_type]
    
    def get_devices_by_manufacturer(
        self,
        devices: List[DeviceEntity],
        manufacturer: str
    ) -> List[DeviceEntity]:
        """Get devices from specific manufacturer."""
        manufacturer_lower = manufacturer.lower()
        return [
            device for device in devices 
            if device.manufacturer and device.manufacturer.lower() == manufacturer_lower
        ]
    
    def get_devices_with_capabilities(
        self,
        devices: List[DeviceEntity],
        required_protocols: Optional[Set[str]] = None,
        required_sensors: Optional[Set[str]] = None,
        required_actuators: Optional[Set[str]] = None
    ) -> List[DeviceEntity]:
        """Get devices with specific capabilities."""
        matching_devices = []
        
        for device in devices:
            if not device.capabilities:
                continue
            
            # Check protocols
            if required_protocols:
                device_protocols = {p.lower() for p in device.capabilities.supported_protocols}
                if not required_protocols.issubset(device_protocols):
                    continue
            
            # Check sensors
            if required_sensors:
                device_sensors = {s.lower() for s in device.capabilities.sensors}
                if not required_sensors.issubset(device_sensors):
                    continue
            
            # Check actuators
            if required_actuators:
                device_actuators = {a.lower() for a in device.capabilities.actuators}
                if not required_actuators.issubset(device_actuators):
                    continue
            
            matching_devices.append(device)
        
        return matching_devices
    
    def calculate_device_health_score(self, device: DeviceEntity) -> float:
        """Calculate a health score for the device (0.0 to 1.0)."""
        score = 1.0
        
        # Reduce score based on status
        if device.status == DeviceStatus.INACTIVE:
            score *= 0.5
        elif device.status == DeviceStatus.MAINTENANCE:
            score *= 0.7
        elif device.status == DeviceStatus.DECOMMISSIONED:
            score = 0.0
        
        # Reduce score based on last seen
        if device.last_seen:
            now = datetime.now(timezone.utc)
            age_hours = (now - device.last_seen).total_seconds() / 3600
            
            if age_hours > 24:  # More than 24 hours
                score *= 0.3
            elif age_hours > 12:  # More than 12 hours
                score *= 0.6
            elif age_hours > 6:  # More than 6 hours
                score *= 0.8
        else:
            # Never seen
            score *= 0.2
        
        return max(0.0, min(1.0, score))
