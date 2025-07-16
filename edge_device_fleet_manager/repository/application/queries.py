"""
Query definitions for CQRS pattern.

Queries represent read operations and data retrieval requests.
They are immutable and contain all parameters needed to fetch data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from ..domain.value_objects import DeviceId
from ..domain.entities import DeviceType, DeviceStatus


class Query(ABC):
    """Base class for all queries."""

    def __init__(self, query_id: UUID, timestamp: datetime,
                 user_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.query_id = query_id
        self.timestamp = timestamp
        self.user_id = user_id
        self.correlation_id = correlation_id
    
    @property
    @abstractmethod
    def query_type(self) -> str:
        """Get the query type identifier."""
        pass


class GetDeviceQuery(Query):
    """Query to get a single device by ID."""

    def __init__(self, query_id: UUID, timestamp: datetime, device_id: DeviceId,
                 include_metrics: bool = False, include_configuration: bool = False, **kwargs):
        super().__init__(query_id, timestamp, **kwargs)
        self.device_id = device_id
        self.include_metrics = include_metrics
        self.include_configuration = include_configuration
    
    @property
    def query_type(self) -> str:
        return "get_device"


@dataclass(frozen=True)
class GetDeviceBySerialNumberQuery(Query):
    """Query to get a device by serial number."""
    
    serial_number: str
    include_metrics: bool = False
    include_configuration: bool = False
    
    @property
    def query_type(self) -> str:
        return "get_device_by_serial_number"


class ListDevicesQuery(Query):
    """Query to list devices with pagination."""

    def __init__(self, query_id: UUID, timestamp: datetime, page: int = 1,
                 page_size: int = 50, sort_by: str = "name", sort_order: str = "asc",
                 include_metrics: bool = False, include_configuration: bool = False, **kwargs):
        super().__init__(query_id, timestamp, **kwargs)
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.include_metrics = include_metrics
        self.include_configuration = include_configuration
    
    @property
    def query_type(self) -> str:
        return "list_devices"


class SearchDevicesQuery(Query):
    """Query to search devices with filters."""

    def __init__(self, query_id: UUID, timestamp: datetime,
                 search_term: Optional[str] = None,
                 device_types: Optional[List[DeviceType]] = None,
                 statuses: Optional[List[DeviceStatus]] = None,
                 manufacturers: Optional[List[str]] = None,
                 models: Optional[List[str]] = None,
                 location_filters: Optional[Dict[str, Any]] = None,
                 capability_filters: Optional[Dict[str, Any]] = None,
                 created_after: Optional[datetime] = None,
                 created_before: Optional[datetime] = None,
                 last_seen_after: Optional[datetime] = None,
                 last_seen_before: Optional[datetime] = None,
                 page: int = 1, page_size: int = 50,
                 sort_by: str = "name", sort_order: str = "asc", **kwargs):
        super().__init__(query_id, timestamp, **kwargs)
        self.search_term = search_term
        self.device_types = device_types
        self.statuses = statuses
        self.manufacturers = manufacturers
        self.models = models
        self.location_filters = location_filters
        self.capability_filters = capability_filters
        self.created_after = created_after
        self.created_before = created_before
        self.last_seen_after = last_seen_after
        self.last_seen_before = last_seen_before
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order
    
    @property
    def query_type(self) -> str:
        return "search_devices"


@dataclass(frozen=True)
class GetDevicesByTypeQuery(Query):
    """Query to get devices by type."""
    
    device_type: DeviceType
    status_filter: Optional[DeviceStatus] = None
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_devices_by_type"


@dataclass(frozen=True)
class GetDevicesByStatusQuery(Query):
    """Query to get devices by status."""
    
    status: DeviceStatus
    device_type_filter: Optional[DeviceType] = None
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_devices_by_status"


@dataclass(frozen=True)
class GetStaleDevicesQuery(Query):
    """Query to get devices that haven't been seen recently."""
    
    stale_threshold_hours: int = 24
    device_type_filter: Optional[DeviceType] = None
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_stale_devices"


@dataclass(frozen=True)
class GetDeviceMetricsQuery(Query):
    """Query to get device metrics."""
    
    device_id: DeviceId
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    metric_types: Optional[List[str]] = None
    limit: int = 100
    
    @property
    def query_type(self) -> str:
        return "get_device_metrics"


@dataclass(frozen=True)
class GetDeviceConfigurationQuery(Query):
    """Query to get device configuration."""
    
    device_id: DeviceId
    configuration_keys: Optional[List[str]] = None
    
    @property
    def query_type(self) -> str:
        return "get_device_configuration"


@dataclass(frozen=True)
class GetDevicesWithCapabilitiesQuery(Query):
    """Query to get devices with specific capabilities."""
    
    required_protocols: Optional[Set[str]] = None
    required_sensors: Optional[Set[str]] = None
    required_actuators: Optional[Set[str]] = None
    connectivity_types: Optional[Set[str]] = None
    power_source: Optional[str] = None
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_devices_with_capabilities"


@dataclass(frozen=True)
class GetDevicesByLocationQuery(Query):
    """Query to get devices by location criteria."""
    
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    address_contains: Optional[str] = None
    within_radius_km: Optional[float] = None
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_devices_by_location"


@dataclass(frozen=True)
class GetDeviceStatisticsQuery(Query):
    """Query to get device statistics."""
    
    group_by: List[str] = None  # e.g., ["device_type", "status", "manufacturer"]
    include_metrics_summary: bool = False
    
    @property
    def query_type(self) -> str:
        return "get_device_statistics"


@dataclass(frozen=True)
class GetDeviceHealthQuery(Query):
    """Query to get device health information."""
    
    device_id: Optional[DeviceId] = None
    health_threshold: float = 0.7
    include_unhealthy_only: bool = False
    page: int = 1
    page_size: int = 50
    
    @property
    def query_type(self) -> str:
        return "get_device_health"


# Query validation utilities
class QueryValidator:
    """Validates queries before processing."""
    
    @staticmethod
    def validate_pagination(page: int, page_size: int) -> List[str]:
        """Validate pagination parameters."""
        errors = []
        
        if page < 1:
            errors.append("Page number must be at least 1")
        
        if page_size < 1:
            errors.append("Page size must be at least 1")
        elif page_size > 1000:
            errors.append("Page size cannot exceed 1000")
        
        return errors
    
    @staticmethod
    def validate_sort_parameters(sort_by: str, sort_order: str) -> List[str]:
        """Validate sort parameters."""
        errors = []
        
        valid_sort_fields = {
            "name", "device_type", "status", "manufacturer", "model",
            "created_at", "updated_at", "last_seen"
        }
        
        if sort_by not in valid_sort_fields:
            errors.append(f"Invalid sort field: {sort_by}. Valid fields: {', '.join(valid_sort_fields)}")
        
        if sort_order not in ["asc", "desc"]:
            errors.append("Sort order must be 'asc' or 'desc'")
        
        return errors
    
    @staticmethod
    def validate_date_range(from_date: Optional[datetime], to_date: Optional[datetime]) -> List[str]:
        """Validate date range parameters."""
        errors = []
        
        if from_date and to_date and from_date > to_date:
            errors.append("From date cannot be after to date")
        
        if to_date and to_date > datetime.now():
            errors.append("To date cannot be in the future")
        
        return errors
    
    @staticmethod
    def validate_location_query(query: GetDevicesByLocationQuery) -> List[str]:
        """Validate location query parameters."""
        errors = []
        
        # Validate radius search parameters
        if query.within_radius_km is not None:
            if query.center_latitude is None or query.center_longitude is None:
                errors.append("Center coordinates required for radius search")
            
            if query.within_radius_km <= 0:
                errors.append("Radius must be positive")
            elif query.within_radius_km > 10000:  # 10,000 km max
                errors.append("Radius cannot exceed 10,000 km")
        
        # Validate coordinates
        if query.center_latitude is not None:
            if not (-90 <= query.center_latitude <= 90):
                errors.append("Latitude must be between -90 and 90 degrees")
        
        if query.center_longitude is not None:
            if not (-180 <= query.center_longitude <= 180):
                errors.append("Longitude must be between -180 and 180 degrees")
        
        return errors


# Query result types
@dataclass(frozen=True)
class QueryResult:
    """Base result of query execution."""
    
    success: bool
    query_id: UUID
    error_message: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    
    @classmethod
    def failure_result(
        cls,
        query_id: UUID,
        error_message: str,
        validation_errors: Optional[List[str]] = None
    ) -> 'QueryResult':
        """Create a failed query result."""
        return cls(
            success=False,
            query_id=query_id,
            error_message=error_message,
            validation_errors=validation_errors
        )


@dataclass(frozen=True)
class PaginatedQueryResult(QueryResult):
    """Result with pagination information."""
    
    page: int = 1
    page_size: int = 50
    total_count: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False
    
    @classmethod
    def create(
        cls,
        query_id: UUID,
        page: int,
        page_size: int,
        total_count: int,
        **kwargs
    ) -> 'PaginatedQueryResult':
        """Create paginated result with calculated pagination info."""
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return cls(
            success=True,
            query_id=query_id,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            **kwargs
        )
