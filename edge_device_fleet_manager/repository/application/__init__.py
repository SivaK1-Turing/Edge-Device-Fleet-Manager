"""
Application layer for device repository.

This module implements the CQRS pattern with commands, queries, handlers,
and application services that orchestrate domain operations.
"""

from .commands import (
    Command,
    RegisterDeviceCommand,
    UpdateDeviceCommand,
    DeactivateDeviceCommand,
    ActivateDeviceCommand,
    UpdateConfigurationCommand,
    RecordMetricsCommand,
    UpdateLocationCommand,
    UpdateCapabilitiesCommand,
)

from .queries import (
    Query,
    GetDeviceQuery,
    ListDevicesQuery,
    SearchDevicesQuery,
    GetDeviceMetricsQuery,
    GetDevicesByTypeQuery,
    GetDevicesByStatusQuery,
    GetStaleDevicesQuery,
)

from .handlers import (
    CommandHandler,
    QueryHandler,
    DeviceCommandHandler,
    DeviceQueryHandler,
)

from .services import (
    DeviceApplicationService,
    DeviceQueryService,
)

from .dto import (
    DeviceDto,
    DeviceListDto,
    DeviceMetricsDto,
    DeviceSearchResultDto,
)

__all__ = [
    # Commands
    "Command",
    "RegisterDeviceCommand",
    "UpdateDeviceCommand",
    "DeactivateDeviceCommand",
    "ActivateDeviceCommand",
    "UpdateConfigurationCommand",
    "RecordMetricsCommand",
    "UpdateLocationCommand",
    "UpdateCapabilitiesCommand",
    
    # Queries
    "Query",
    "GetDeviceQuery",
    "ListDevicesQuery",
    "SearchDevicesQuery",
    "GetDeviceMetricsQuery",
    "GetDevicesByTypeQuery",
    "GetDevicesByStatusQuery",
    "GetStaleDevicesQuery",
    
    # Handlers
    "CommandHandler",
    "QueryHandler",
    "DeviceCommandHandler",
    "DeviceQueryHandler",
    
    # Services
    "DeviceApplicationService",
    "DeviceQueryService",
    
    # DTOs
    "DeviceDto",
    "DeviceListDto",
    "DeviceMetricsDto",
    "DeviceSearchResultDto",
]
