"""
Data Transfer Objects (DTOs) for the application layer.

DTOs provide a stable interface for data exchange between layers
and external systems, decoupling internal domain models from external APIs.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..domain.entities import DeviceType, DeviceStatus


@dataclass(frozen=True)
class DeviceIdentifierDto:
    """DTO for device identifier."""
    
    serial_number: str
    mac_address: Optional[str] = None
    hardware_id: Optional[str] = None


@dataclass(frozen=True)
class DeviceLocationDto:
    """DTO for device location."""
    
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    altitude: Optional[Decimal] = None
    address: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    
    @property
    def has_coordinates(self) -> bool:
        """Check if location has GPS coordinates."""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def has_physical_location(self) -> bool:
        """Check if location has physical address information."""
        return any([self.address, self.building, self.floor, self.room])


@dataclass(frozen=True)
class DeviceCapabilitiesDto:
    """DTO for device capabilities."""
    
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
        # Set default empty lists
        if self.sensors is None:
            object.__setattr__(self, 'sensors', [])
        if self.actuators is None:
            object.__setattr__(self, 'actuators', [])
        if self.connectivity is None:
            object.__setattr__(self, 'connectivity', [])


@dataclass(frozen=True)
class DeviceMetricsDto:
    """DTO for device metrics."""
    
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
        if self.custom_metrics is None:
            object.__setattr__(self, 'custom_metrics', {})


@dataclass(frozen=True)
class DeviceConfigurationDto:
    """DTO for device configuration."""
    
    configuration: Dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DeviceDto:
    """DTO for complete device information."""
    
    device_id: UUID
    name: str
    device_type: DeviceType
    status: DeviceStatus
    identifier: DeviceIdentifierDto
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    location: Optional[DeviceLocationDto] = None
    capabilities: Optional[DeviceCapabilitiesDto] = None
    configuration: Optional[DeviceConfigurationDto] = None
    last_seen: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    version: int = 1
    
    # Computed properties
    health_score: Optional[float] = None
    is_online: Optional[bool] = None
    recent_metrics: Optional[List[DeviceMetricsDto]] = None
    
    @classmethod
    def from_aggregate(cls, aggregate, include_metrics: bool = False, include_configuration: bool = False):
        """Create DTO from domain aggregate."""
        device = aggregate.device
        
        # Convert identifier
        identifier_dto = DeviceIdentifierDto(
            serial_number=device.identifier.serial_number,
            mac_address=device.identifier.mac_address,
            hardware_id=device.identifier.hardware_id,
        )
        
        # Convert location
        location_dto = None
        if device.location:
            location_dto = DeviceLocationDto(
                latitude=device.location.latitude,
                longitude=device.location.longitude,
                altitude=device.location.altitude,
                address=device.location.address,
                building=device.location.building,
                floor=device.location.floor,
                room=device.location.room,
            )
        
        # Convert capabilities
        capabilities_dto = None
        if device.capabilities:
            capabilities_dto = DeviceCapabilitiesDto(
                supported_protocols=device.capabilities.supported_protocols,
                sensors=device.capabilities.sensors,
                actuators=device.capabilities.actuators,
                connectivity=device.capabilities.connectivity,
                power_source=device.capabilities.power_source,
                operating_system=device.capabilities.operating_system,
                firmware_version=device.capabilities.firmware_version,
                hardware_version=device.capabilities.hardware_version,
                memory_mb=device.capabilities.memory_mb,
                storage_mb=device.capabilities.storage_mb,
                cpu_cores=device.capabilities.cpu_cores,
            )
        
        # Convert configuration
        configuration_dto = None
        if include_configuration and device.configuration:
            configuration_dto = DeviceConfigurationDto(
                configuration=device.configuration.configuration,
                version=device.configuration.version,
                created_at=device.configuration.created_at,
                updated_at=device.configuration.updated_at,
            )
        
        # Convert recent metrics
        recent_metrics_dto = None
        if include_metrics:
            recent_metrics = aggregate.get_recent_metrics(5)
            recent_metrics_dto = [
                DeviceMetricsDto(
                    timestamp=metrics.timestamp,
                    cpu_usage_percent=metrics.cpu_usage_percent,
                    memory_usage_percent=metrics.memory_usage_percent,
                    disk_usage_percent=metrics.disk_usage_percent,
                    temperature_celsius=metrics.temperature_celsius,
                    battery_level_percent=metrics.battery_level_percent,
                    network_bytes_sent=metrics.network_bytes_sent,
                    network_bytes_received=metrics.network_bytes_received,
                    uptime_seconds=metrics.uptime_seconds,
                    custom_metrics=metrics.custom_metrics,
                )
                for metrics in recent_metrics
            ]
        
        # Calculate health score
        from ..domain.services import DeviceLifecycleService
        lifecycle_service = DeviceLifecycleService(None)
        health_score = lifecycle_service.calculate_device_health_score(device)
        
        return cls(
            device_id=device.device_id.value,
            name=device.name,
            device_type=device.device_type,
            status=device.status,
            identifier=identifier_dto,
            manufacturer=device.manufacturer,
            model=device.model,
            location=location_dto,
            capabilities=capabilities_dto,
            configuration=configuration_dto,
            last_seen=device.last_seen,
            created_at=device.created_at,
            updated_at=device.updated_at,
            version=device.version,
            health_score=health_score,
            is_online=device.is_online(),
            recent_metrics=recent_metrics_dto,
        )


@dataclass(frozen=True)
class DeviceListDto:
    """DTO for device list with pagination."""
    
    devices: List[DeviceDto]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass(frozen=True)
class DeviceSearchResultDto:
    """DTO for device search results."""
    
    devices: List[DeviceDto]
    search_term: Optional[str]
    filters_applied: Dict[str, Any]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass(frozen=True)
class DeviceStatisticsDto:
    """DTO for device statistics."""
    
    total_devices: int
    devices_by_type: Dict[str, int]
    devices_by_status: Dict[str, int]
    devices_by_manufacturer: Dict[str, int]
    online_devices: int
    offline_devices: int
    stale_devices: int
    average_health_score: float
    last_updated: datetime


@dataclass(frozen=True)
class DeviceHealthDto:
    """DTO for device health information."""
    
    device_id: UUID
    device_name: str
    health_score: float
    status: DeviceStatus
    last_seen: Optional[datetime]
    issues: List[str]
    recommendations: List[str]


@dataclass(frozen=True)
class DeviceGroupDto:
    """DTO for device group."""
    
    group_id: UUID
    name: str
    description: Optional[str]
    device_count: int
    parent_group_id: Optional[UUID]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int


@dataclass(frozen=True)
class BulkOperationResultDto:
    """DTO for bulk operation results."""
    
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    execution_time_seconds: float


@dataclass(frozen=True)
class DeviceImportResultDto:
    """DTO for device import results."""
    
    total_devices: int
    imported: int
    updated: int
    skipped: int
    failed: int
    errors: List[Dict[str, Any]]
    warnings: List[str]
    source: str
    import_time: datetime
    execution_time_seconds: float


# Utility functions for DTO conversion
class DtoConverter:
    """Utility class for converting between domain objects and DTOs."""
    
    @staticmethod
    def device_aggregate_to_dto(
        aggregate,
        include_metrics: bool = False,
        include_configuration: bool = False
    ) -> DeviceDto:
        """Convert device aggregate to DTO."""
        return DeviceDto.from_aggregate(aggregate, include_metrics, include_configuration)
    
    @staticmethod
    def device_aggregates_to_list_dto(
        aggregates: List,
        page: int,
        page_size: int,
        total_count: int,
        include_metrics: bool = False,
        include_configuration: bool = False
    ) -> DeviceListDto:
        """Convert list of device aggregates to list DTO."""
        devices = [
            DtoConverter.device_aggregate_to_dto(aggregate, include_metrics, include_configuration)
            for aggregate in aggregates
        ]
        
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return DeviceListDto(
            devices=devices,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )
