"""
Unit of Work pattern implementation.

The Unit of Work pattern maintains a list of objects affected by a business transaction
and coordinates writing out changes and resolving concurrency problems.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from contextlib import asynccontextmanager

from sqlalchemy.orm import sessionmaker, Session

from .repositories import DeviceRepository, DeviceGroupRepository, SqlDeviceRepository
from .event_store import EventStore, SqlEventStore
from .database import DatabaseSession
from ..domain.entities import DeviceAggregate
from ..domain.events import DomainEvent
from ...core.exceptions import RepositoryError


class UnitOfWork(ABC):
    """Abstract Unit of Work."""
    
    devices: DeviceRepository
    device_groups: DeviceGroupRepository
    
    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit the unit of work."""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the unit of work."""
        pass
    
    @abstractmethod
    async def collect_new_events(self) -> List[DomainEvent]:
        """Collect new domain events from aggregates."""
        pass


class SqlUnitOfWork(UnitOfWork):
    """SQL-based Unit of Work implementation."""
    
    def __init__(self, session_factory: sessionmaker, event_store: EventStore):
        self.session_factory = session_factory
        self.event_store = event_store
        self._session: Optional[Session] = None
        self._committed = False
        self._aggregates: List[DeviceAggregate] = []
    
    async def __aenter__(self):
        """Enter async context manager."""
        self._session = self.session_factory()
        
        # Initialize repositories with the session
        self.devices = SqlDeviceRepository(self.session_factory, self.event_store)
        # Note: DeviceGroupRepository would be implemented similarly
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            await self.rollback()
        
        if self._session:
            self._session.close()
    
    async def commit(self) -> None:
        """Commit the unit of work."""
        if self._committed:
            raise RepositoryError("Unit of work already committed")
        
        try:
            # Collect and publish domain events
            events = await self.collect_new_events()
            
            # Commit database transaction
            if self._session:
                self._session.commit()
            
            # Mark events as committed on aggregates
            for aggregate in self._aggregates:
                aggregate.mark_events_as_committed()
            
            self._committed = True
            
            # Publish events (in a real implementation, this would be done
            # through an event bus or message queue)
            await self._publish_events(events)
            
        except Exception as e:
            await self.rollback()
            raise RepositoryError(f"Failed to commit unit of work: {e}") from e
    
    async def rollback(self) -> None:
        """Rollback the unit of work."""
        if self._session:
            self._session.rollback()
        
        # Clear collected aggregates
        self._aggregates.clear()
    
    async def collect_new_events(self) -> List[DomainEvent]:
        """Collect new domain events from aggregates."""
        events = []
        for aggregate in self._aggregates:
            events.extend(aggregate.get_uncommitted_events())
        return events
    
    def track_aggregate(self, aggregate: DeviceAggregate) -> None:
        """Track an aggregate for event collection."""
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)
    
    async def _publish_events(self, events: List[DomainEvent]) -> None:
        """Publish domain events."""
        # In a real implementation, this would publish events to an event bus
        # For now, we'll just log them
        for event in events:
            # Log event publication
            pass


class InMemoryUnitOfWork(UnitOfWork):
    """In-memory Unit of Work implementation for testing."""
    
    def __init__(self):
        from .repositories import InMemoryDeviceRepository
        from .event_store import InMemoryEventStore
        
        self.event_store = InMemoryEventStore()
        self.devices = InMemoryDeviceRepository()
        self.device_groups = None  # Would implement InMemoryDeviceGroupRepository
        self._committed = False
        self._aggregates: List[DeviceAggregate] = []
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            await self.rollback()
    
    async def commit(self) -> None:
        """Commit the unit of work."""
        if self._committed:
            raise RepositoryError("Unit of work already committed")
        
        try:
            # Collect and save events
            events = await self.collect_new_events()
            
            # Save events to event store
            for aggregate in self._aggregates:
                aggregate_events = aggregate.get_uncommitted_events()
                if aggregate_events:
                    await self.event_store.save_events(
                        aggregate.device_id,
                        aggregate_events,
                        aggregate.version - len(aggregate_events)
                    )
                    aggregate.mark_events_as_committed()
            
            self._committed = True
            
            # Publish events
            await self._publish_events(events)
            
        except Exception as e:
            await self.rollback()
            raise RepositoryError(f"Failed to commit unit of work: {e}") from e
    
    async def rollback(self) -> None:
        """Rollback the unit of work."""
        # Clear collected aggregates
        self._aggregates.clear()
    
    async def collect_new_events(self) -> List[DomainEvent]:
        """Collect new domain events from aggregates."""
        events = []
        for aggregate in self._aggregates:
            events.extend(aggregate.get_uncommitted_events())
        return events
    
    def track_aggregate(self, aggregate: DeviceAggregate) -> None:
        """Track an aggregate for event collection."""
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)
    
    async def _publish_events(self, events: List[DomainEvent]) -> None:
        """Publish domain events."""
        # In-memory implementation - just log events
        for event in events:
            pass
    
    def clear(self) -> None:
        """Clear all data (for testing)."""
        if hasattr(self.devices, 'clear'):
            self.devices.clear()
        if hasattr(self.event_store, 'clear'):
            self.event_store.clear()
        self._aggregates.clear()


@asynccontextmanager
async def create_unit_of_work(
    database_session: DatabaseSession,
    event_store: Optional[EventStore] = None
):
    """Create a unit of work with proper cleanup."""
    if event_store is None:
        event_store = SqlEventStore(database_session.session_factory)
    
    uow = SqlUnitOfWork(database_session.session_factory, event_store)
    
    async with uow:
        yield uow


class UnitOfWorkFactory:
    """Factory for creating unit of work instances."""
    
    def __init__(self, database_session: DatabaseSession):
        self.database_session = database_session
        self.event_store = SqlEventStore(database_session.session_factory)
    
    def create(self) -> SqlUnitOfWork:
        """Create a new unit of work instance."""
        return SqlUnitOfWork(self.database_session.session_factory, self.event_store)
    
    @asynccontextmanager
    async def get_unit_of_work(self):
        """Get a unit of work with automatic cleanup."""
        uow = self.create()
        async with uow:
            yield uow


# Event handling utilities
class EventHandler(ABC):
    """Abstract event handler."""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        pass


class EventDispatcher:
    """Dispatches domain events to registered handlers."""
    
    def __init__(self):
        self._handlers: dict[str, List[EventHandler]] = {}
    
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def dispatch(self, event: DomainEvent) -> None:
        """Dispatch an event to all registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                # Log error but don't stop other handlers
                # In a real implementation, you might want to use a dead letter queue
                pass
    
    async def dispatch_events(self, events: List[DomainEvent]) -> None:
        """Dispatch multiple events."""
        for event in events:
            await self.dispatch(event)


# Example event handlers
class DeviceRegisteredEventHandler(EventHandler):
    """Handler for device registered events."""
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle device registered event."""
        # Example: Send notification, update read models, etc.
        pass


class DeviceMetricsRecordedEventHandler(EventHandler):
    """Handler for device metrics recorded events."""
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle device metrics recorded event."""
        # Example: Update analytics, trigger alerts, etc.
        pass
