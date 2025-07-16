"""
Domain layer for device repository.

This module contains the core domain model including entities, value objects,
domain events, and domain services following Domain-Driven Design principles.
"""

from .entities import (
    DeviceAggregate,
    DeviceEntity,
    DeviceGroup,
    DeviceConfiguration,
)

from .value_objects import (
    DeviceId,
    DeviceIdentifier,
    DeviceLocation,
    DeviceCapabilities,
    DeviceMetrics,
)

from .events import (
    DomainEvent,
    DeviceRegisteredEvent,
    DeviceUpdatedEvent,
    DeviceDeactivatedEvent,
    DeviceConfigurationChangedEvent,
    DeviceMetricsRecordedEvent,
)

from .services import (
    DeviceRegistrationService,
    DeviceValidationService,
    DeviceLifecycleService,
)

__all__ = [
    # Entities
    "DeviceAggregate",
    "DeviceEntity",
    "DeviceGroup", 
    "DeviceConfiguration",
    
    # Value Objects
    "DeviceId",
    "DeviceIdentifier",
    "DeviceLocation",
    "DeviceCapabilities",
    "DeviceMetrics",
    
    # Events
    "DomainEvent",
    "DeviceRegisteredEvent",
    "DeviceUpdatedEvent",
    "DeviceDeactivatedEvent",
    "DeviceConfigurationChangedEvent",
    "DeviceMetricsRecordedEvent",
    
    # Services
    "DeviceRegistrationService",
    "DeviceValidationService",
    "DeviceLifecycleService",
]
