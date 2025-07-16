"""
Application services for device repository.

Application services orchestrate domain operations and provide
a high-level interface for external systems.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from .commands import (
    RegisterDeviceCommand, UpdateDeviceCommand, DeactivateDeviceCommand,
    ActivateDeviceCommand, UpdateLocationCommand, UpdateCapabilitiesCommand,
    UpdateConfigurationCommand, RecordMetricsCommand, CommandResult
)
from .queries import (
    GetDeviceQuery, ListDevicesQuery, SearchDevicesQuery,
    GetDevicesByTypeQuery, GetDevicesByStatusQuery, QueryResult
)
from .handlers import DeviceCommandHandler, DeviceQueryHandler
from .dto import DeviceDto, DeviceListDto, DeviceSearchResultDto
from ..domain.entities import DeviceType, DeviceStatus
from ..domain.value_objects import DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities, DeviceMetrics
from ...core.exceptions import ValidationError, RepositoryError


class DeviceApplicationService:
    """Application service for device operations."""
    
    def __init__(self, command_handler: DeviceCommandHandler, query_handler: DeviceQueryHandler):
        self.command_handler = command_handler
        self.query_handler = query_handler
    
    # Command operations
    async def register_device(
        self,
        name: str,
        device_type: DeviceType,
        serial_number: str,
        mac_address: Optional[str] = None,
        hardware_id: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        location: Optional[DeviceLocation] = None,
        capabilities: Optional[DeviceCapabilities] = None,
        initial_configuration: Optional[dict] = None,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Register a new device."""
        identifier = DeviceIdentifier(
            serial_number=serial_number,
            mac_address=mac_address,
            hardware_id=hardware_id
        )
        
        command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            name=name,
            device_type=device_type,
            identifier=identifier,
            manufacturer=manufacturer,
            model=model,
            location=location,
            capabilities=capabilities,
            initial_configuration=initial_configuration
        )
        
        return await self.command_handler.handle(command)
    
    async def update_device(
        self,
        device_id: DeviceId,
        name: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Update device information."""
        command = UpdateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            name=name,
            manufacturer=manufacturer,
            model=model
        )
        
        return await self.command_handler.handle(command)
    
    async def deactivate_device(
        self,
        device_id: DeviceId,
        reason: str,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Deactivate a device."""
        command = DeactivateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            reason=reason
        )
        
        return await self.command_handler.handle(command)
    
    async def activate_device(
        self,
        device_id: DeviceId,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Activate a device."""
        command = ActivateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id
        )
        
        return await self.command_handler.handle(command)
    
    async def update_device_location(
        self,
        device_id: DeviceId,
        location: DeviceLocation,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Update device location."""
        command = UpdateLocationCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            location=location
        )
        
        return await self.command_handler.handle(command)
    
    async def update_device_capabilities(
        self,
        device_id: DeviceId,
        capabilities: DeviceCapabilities,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Update device capabilities."""
        command = UpdateCapabilitiesCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            capabilities=capabilities
        )
        
        return await self.command_handler.handle(command)
    
    async def update_device_configuration(
        self,
        device_id: DeviceId,
        configuration_key: str,
        configuration_value: any,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Update device configuration."""
        command = UpdateConfigurationCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            configuration_key=configuration_key,
            configuration_value=configuration_value
        )
        
        return await self.command_handler.handle(command)
    
    async def record_device_metrics(
        self,
        device_id: DeviceId,
        metrics: DeviceMetrics,
        user_id: Optional[str] = None
    ) -> CommandResult:
        """Record device metrics."""
        command = RecordMetricsCommand(
            command_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            metrics=metrics
        )
        
        return await self.command_handler.handle(command)
    
    # Query operations
    async def get_device(
        self,
        device_id: DeviceId,
        include_metrics: bool = False,
        include_configuration: bool = False,
        user_id: Optional[str] = None
    ) -> QueryResult:
        """Get a device by ID."""
        query = GetDeviceQuery(
            query_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_id=device_id,
            include_metrics=include_metrics,
            include_configuration=include_configuration
        )
        
        return await self.query_handler.handle(query)
    
    async def list_devices(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "name",
        sort_order: str = "asc",
        include_metrics: bool = False,
        include_configuration: bool = False,
        user_id: Optional[str] = None
    ) -> QueryResult:
        """List devices with pagination."""
        query = ListDevicesQuery(
            query_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            include_metrics=include_metrics,
            include_configuration=include_configuration
        )
        
        return await self.query_handler.handle(query)
    
    async def search_devices(
        self,
        search_term: Optional[str] = None,
        device_types: Optional[List[DeviceType]] = None,
        statuses: Optional[List[DeviceStatus]] = None,
        manufacturers: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "name",
        sort_order: str = "asc",
        user_id: Optional[str] = None
    ) -> QueryResult:
        """Search devices with filters."""
        query = SearchDevicesQuery(
            query_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            search_term=search_term,
            device_types=device_types,
            statuses=statuses,
            manufacturers=manufacturers,
            models=models,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return await self.query_handler.handle(query)
    
    async def get_devices_by_type(
        self,
        device_type: DeviceType,
        status_filter: Optional[DeviceStatus] = None,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None
    ) -> QueryResult:
        """Get devices by type."""
        query = GetDevicesByTypeQuery(
            query_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            device_type=device_type,
            status_filter=status_filter,
            page=page,
            page_size=page_size
        )
        
        return await self.query_handler.handle(query)
    
    async def get_devices_by_status(
        self,
        status: DeviceStatus,
        device_type_filter: Optional[DeviceType] = None,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None
    ) -> QueryResult:
        """Get devices by status."""
        query = GetDevicesByStatusQuery(
            query_id=uuid4(),
            timestamp=datetime.now(),
            user_id=user_id,
            status=status,
            device_type_filter=device_type_filter,
            page=page,
            page_size=page_size
        )
        
        return await self.query_handler.handle(query)


class DeviceQueryService:
    """Specialized service for device queries and read operations."""
    
    def __init__(self, query_handler: DeviceQueryHandler):
        self.query_handler = query_handler
    
    async def get_device_summary(self, device_id: DeviceId) -> Optional[dict]:
        """Get device summary information."""
        result = await self.get_device(device_id, include_metrics=True)
        
        if not result.success or not hasattr(result, 'device'):
            return None
        
        device = result.device
        return {
            'device_id': str(device.device_id),
            'name': device.name,
            'type': device.device_type.value,
            'status': device.status.value,
            'manufacturer': device.manufacturer,
            'model': device.model,
            'health_score': device.health_score,
            'is_online': device.is_online,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'location_summary': self._get_location_summary(device.location),
            'capabilities_summary': self._get_capabilities_summary(device.capabilities),
        }
    
    async def get_device_statistics(self) -> dict:
        """Get overall device statistics."""
        # This would typically be implemented with specialized queries
        # For now, we'll use the list query to get basic stats
        result = await self.list_devices(page_size=1000)  # Get a large sample
        
        if not result.success or not hasattr(result, 'device_list'):
            return {}
        
        devices = result.device_list.devices
        
        # Calculate statistics
        total_devices = len(devices)
        devices_by_type = {}
        devices_by_status = {}
        online_count = 0
        
        for device in devices:
            # Count by type
            type_key = device.device_type.value
            devices_by_type[type_key] = devices_by_type.get(type_key, 0) + 1
            
            # Count by status
            status_key = device.status.value
            devices_by_status[status_key] = devices_by_status.get(status_key, 0) + 1
            
            # Count online devices
            if device.is_online:
                online_count += 1
        
        return {
            'total_devices': total_devices,
            'devices_by_type': devices_by_type,
            'devices_by_status': devices_by_status,
            'online_devices': online_count,
            'offline_devices': total_devices - online_count,
            'last_updated': datetime.now().isoformat(),
        }
    
    def _get_location_summary(self, location) -> Optional[str]:
        """Get location summary string."""
        if not location:
            return None
        
        parts = []
        if location.building:
            parts.append(location.building)
        if location.floor:
            parts.append(f"Floor {location.floor}")
        if location.room:
            parts.append(f"Room {location.room}")
        
        if parts:
            return " - ".join(parts)
        elif location.address:
            return location.address
        elif location.has_coordinates:
            return f"GPS: {location.latitude}, {location.longitude}"
        
        return None
    
    def _get_capabilities_summary(self, capabilities) -> Optional[dict]:
        """Get capabilities summary."""
        if not capabilities:
            return None
        
        return {
            'protocols': len(capabilities.supported_protocols),
            'sensors': len(capabilities.sensors),
            'actuators': len(capabilities.actuators),
            'connectivity': len(capabilities.connectivity),
            'has_battery': capabilities.power_source and 'battery' in capabilities.power_source.lower(),
        }
