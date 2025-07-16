"""
Domain-Driven Device Repository.

This module provides a comprehensive domain-driven repository system for managing
IoT edge devices with event sourcing, CQRS patterns, and rich domain modeling.
"""

from .domain import (
    # Entities
    DeviceAggregate,
    DeviceEntity,
    DeviceGroup,
    DeviceConfiguration,
    
    # Value Objects
    DeviceId,
    DeviceIdentifier,
    DeviceLocation,
    DeviceCapabilities,
    DeviceMetrics,
    
    # Domain Events
    DeviceRegisteredEvent,
    DeviceUpdatedEvent,
    DeviceDeactivatedEvent,
    DeviceConfigurationChangedEvent,
    DeviceMetricsRecordedEvent,
    
    # Domain Services
    DeviceRegistrationService,
    DeviceValidationService,
    DeviceLifecycleService,
)

from .infrastructure import (
    # Repositories
    DeviceRepository,
    DeviceGroupRepository,
    EventStore,
    
    # Unit of Work
    UnitOfWork,
    
    # Database
    DatabaseSession,
    create_database_engine,
)

from .application import (
    # Commands
    RegisterDeviceCommand,
    UpdateDeviceCommand,
    DeactivateDeviceCommand,
    UpdateConfigurationCommand,
    RecordMetricsCommand,
    
    # Queries
    GetDeviceQuery,
    ListDevicesQuery,
    SearchDevicesQuery,
    GetDeviceMetricsQuery,
    
    # Command Handlers
    DeviceCommandHandler,
    
    # Query Handlers
    DeviceQueryHandler,
    
    # Application Services
    DeviceApplicationService,
)

__all__ = [
    # Domain - Entities
    "DeviceAggregate",
    "DeviceEntity", 
    "DeviceGroup",
    "DeviceConfiguration",
    
    # Domain - Value Objects
    "DeviceId",
    "DeviceIdentifier",
    "DeviceLocation",
    "DeviceCapabilities",
    "DeviceMetrics",
    
    # Domain - Events
    "DeviceRegisteredEvent",
    "DeviceUpdatedEvent",
    "DeviceDeactivatedEvent",
    "DeviceConfigurationChangedEvent",
    "DeviceMetricsRecordedEvent",
    
    # Domain - Services
    "DeviceRegistrationService",
    "DeviceValidationService",
    "DeviceLifecycleService",
    
    # Infrastructure
    "DeviceRepository",
    "DeviceGroupRepository",
    "EventStore",
    "UnitOfWork",
    "DatabaseSession",
    "create_database_engine",
    
    # Application
    "RegisterDeviceCommand",
    "UpdateDeviceCommand",
    "DeactivateDeviceCommand",
    "UpdateConfigurationCommand",
    "RecordMetricsCommand",
    "GetDeviceQuery",
    "ListDevicesQuery",
    "SearchDevicesQuery",
    "GetDeviceMetricsQuery",
    "DeviceCommandHandler",
    "DeviceQueryHandler",
    "DeviceApplicationService",
]
