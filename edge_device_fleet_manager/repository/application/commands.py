"""
Command definitions for CQRS pattern.

Commands represent write operations and business intentions.
They are immutable and contain all data needed to perform an operation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..domain.value_objects import DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities, DeviceMetrics
from ..domain.entities import DeviceType


class Command(ABC):
    """Base class for all commands."""

    def __init__(self, command_id: UUID, timestamp: datetime,
                 user_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.command_id = command_id
        self.timestamp = timestamp
        self.user_id = user_id
        self.correlation_id = correlation_id
    
    @property
    @abstractmethod
    def command_type(self) -> str:
        """Get the command type identifier."""
        pass


class RegisterDeviceCommand(Command):
    """Command to register a new device."""

    def __init__(self, command_id: UUID, timestamp: datetime, name: str,
                 device_type: DeviceType, identifier: DeviceIdentifier,
                 manufacturer: Optional[str] = None, model: Optional[str] = None,
                 location: Optional[DeviceLocation] = None,
                 capabilities: Optional[DeviceCapabilities] = None,
                 initial_configuration: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.name = name
        self.device_type = device_type
        self.identifier = identifier
        self.manufacturer = manufacturer
        self.model = model
        self.location = location
        self.capabilities = capabilities
        self.initial_configuration = initial_configuration
    
    @property
    def command_type(self) -> str:
        return "register_device"


class UpdateDeviceCommand(Command):
    """Command to update device information."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 name: Optional[str] = None, manufacturer: Optional[str] = None,
                 model: Optional[str] = None, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.name = name
        self.manufacturer = manufacturer
        self.model = model
    
    @property
    def command_type(self) -> str:
        return "update_device"


class DeactivateDeviceCommand(Command):
    """Command to deactivate a device."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 reason: str, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.reason = reason
    
    @property
    def command_type(self) -> str:
        return "deactivate_device"


class ActivateDeviceCommand(Command):
    """Command to activate a device."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
    
    @property
    def command_type(self) -> str:
        return "activate_device"


@dataclass(frozen=True)
class SetMaintenanceModeCommand(Command):
    """Command to set device to maintenance mode."""
    
    device_id: DeviceId
    
    @property
    def command_type(self) -> str:
        return "set_maintenance_mode"


class UpdateLocationCommand(Command):
    """Command to update device location."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 location: DeviceLocation, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.location = location
    
    @property
    def command_type(self) -> str:
        return "update_location"


class UpdateCapabilitiesCommand(Command):
    """Command to update device capabilities."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 capabilities: DeviceCapabilities, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.capabilities = capabilities
    
    @property
    def command_type(self) -> str:
        return "update_capabilities"


class UpdateConfigurationCommand(Command):
    """Command to update device configuration."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 configuration_key: str, configuration_value: Any, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.configuration_key = configuration_key
        self.configuration_value = configuration_value
    
    @property
    def command_type(self) -> str:
        return "update_configuration"


@dataclass(frozen=True)
class RemoveConfigurationCommand(Command):
    """Command to remove device configuration."""
    
    device_id: DeviceId
    configuration_key: str
    
    @property
    def command_type(self) -> str:
        return "remove_configuration"


class RecordMetricsCommand(Command):
    """Command to record device metrics."""

    def __init__(self, command_id: UUID, timestamp: datetime, device_id: DeviceId,
                 metrics: DeviceMetrics, **kwargs):
        super().__init__(command_id, timestamp, **kwargs)
        self.device_id = device_id
        self.metrics = metrics
    
    @property
    def command_type(self) -> str:
        return "record_metrics"


@dataclass(frozen=True)
class DeleteDeviceCommand(Command):
    """Command to delete a device."""
    
    device_id: DeviceId
    reason: str
    force: bool = False
    
    @property
    def command_type(self) -> str:
        return "delete_device"


@dataclass(frozen=True)
class BulkUpdateDevicesCommand(Command):
    """Command to update multiple devices."""
    
    device_ids: List[DeviceId]
    updates: Dict[str, Any]
    
    @property
    def command_type(self) -> str:
        return "bulk_update_devices"


@dataclass(frozen=True)
class ImportDevicesCommand(Command):
    """Command to import devices from external source."""
    
    devices_data: List[Dict[str, Any]]
    source: str
    overwrite_existing: bool = False
    
    @property
    def command_type(self) -> str:
        return "import_devices"


@dataclass(frozen=True)
class SyncDeviceCommand(Command):
    """Command to synchronize device with external system."""
    
    device_id: DeviceId
    external_system: str
    sync_configuration: bool = True
    sync_metrics: bool = True
    
    @property
    def command_type(self) -> str:
        return "sync_device"


# Command validation utilities
class CommandValidator:
    """Validates commands before processing."""
    
    @staticmethod
    def validate_register_device_command(command: RegisterDeviceCommand) -> List[str]:
        """Validate register device command."""
        errors = []
        
        if not command.name or not command.name.strip():
            errors.append("Device name is required")
        
        if len(command.name) > 200:
            errors.append("Device name cannot exceed 200 characters")
        
        if not command.identifier.serial_number:
            errors.append("Serial number is required")
        
        if command.capabilities and command.device_type == DeviceType.SENSOR:
            if not command.capabilities.has_sensors:
                errors.append("Sensor devices must have sensor capabilities")
        
        return errors
    
    @staticmethod
    def validate_update_device_command(command: UpdateDeviceCommand) -> List[str]:
        """Validate update device command."""
        errors = []
        
        if command.name is not None:
            if not command.name.strip():
                errors.append("Device name cannot be empty")
            elif len(command.name) > 200:
                errors.append("Device name cannot exceed 200 characters")
        
        return errors
    
    @staticmethod
    def validate_deactivate_device_command(command: DeactivateDeviceCommand) -> List[str]:
        """Validate deactivate device command."""
        errors = []
        
        if not command.reason or not command.reason.strip():
            errors.append("Deactivation reason is required")
        
        if len(command.reason) > 500:
            errors.append("Deactivation reason cannot exceed 500 characters")
        
        return errors
    
    @staticmethod
    def validate_update_configuration_command(command: UpdateConfigurationCommand) -> List[str]:
        """Validate update configuration command."""
        errors = []
        
        if not command.configuration_key or not command.configuration_key.strip():
            errors.append("Configuration key is required")
        
        if len(command.configuration_key) > 100:
            errors.append("Configuration key cannot exceed 100 characters")
        
        # Validate configuration value is serializable
        try:
            import json
            json.dumps(command.configuration_value)
        except (TypeError, ValueError):
            errors.append("Configuration value must be JSON serializable")
        
        return errors


# Command result types
@dataclass(frozen=True)
class CommandResult:
    """Result of command execution."""
    
    success: bool
    command_id: UUID
    aggregate_id: Optional[DeviceId] = None
    error_message: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    
    @classmethod
    def success_result(cls, command_id: UUID, aggregate_id: Optional[DeviceId] = None) -> 'CommandResult':
        """Create a successful command result."""
        return cls(
            success=True,
            command_id=command_id,
            aggregate_id=aggregate_id
        )
    
    @classmethod
    def failure_result(
        cls,
        command_id: UUID,
        error_message: str,
        validation_errors: Optional[List[str]] = None
    ) -> 'CommandResult':
        """Create a failed command result."""
        return cls(
            success=False,
            command_id=command_id,
            error_message=error_message,
            validation_errors=validation_errors
        )
    
    @classmethod
    def validation_failure_result(cls, command_id: UUID, validation_errors: List[str]) -> 'CommandResult':
        """Create a validation failure result."""
        return cls(
            success=False,
            command_id=command_id,
            error_message="Command validation failed",
            validation_errors=validation_errors
        )
