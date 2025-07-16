"""
Infrastructure layer for device repository.

This module contains infrastructure concerns including repositories, event store,
database access, and external service integrations.
"""

from .event_store import (
    EventStore,
    InMemoryEventStore,
    SqlEventStore,
    EventStoreError,
)

from .repositories import (
    DeviceRepository,
    DeviceGroupRepository,
    InMemoryDeviceRepository,
    SqlDeviceRepository,
)

from .database import (
    DatabaseSession,
    create_database_engine,
    Base,
)

from .unit_of_work import (
    UnitOfWork,
    SqlUnitOfWork,
)

__all__ = [
    # Event Store
    "EventStore",
    "InMemoryEventStore", 
    "SqlEventStore",
    "EventStoreError",
    
    # Repositories
    "DeviceRepository",
    "DeviceGroupRepository",
    "InMemoryDeviceRepository",
    "SqlDeviceRepository",
    
    # Database
    "DatabaseSession",
    "create_database_engine",
    "Base",
    
    # Unit of Work
    "UnitOfWork",
    "SqlUnitOfWork",
]
