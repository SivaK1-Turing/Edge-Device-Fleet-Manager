"""
Event store implementation for event sourcing.

The event store persists domain events and provides event replay capabilities
for rebuilding aggregate state.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Type
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from ..domain.events import DomainEvent
from ..domain.value_objects import DeviceId
from ...core.exceptions import RepositoryError


class EventStoreError(RepositoryError):
    """Exception raised by event store operations."""
    pass


Base = declarative_base()


class StoredEvent(Base):
    """SQLAlchemy model for stored events."""
    
    __tablename__ = 'stored_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(PostgresUUID(as_uuid=True), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    aggregate_version = Column(Integer, nullable=False)
    event_data = Column(Text, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    stored_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<StoredEvent(event_id={self.event_id}, event_type={self.event_type}, aggregate_id={self.aggregate_id})>"


class EventStore(ABC):
    """Abstract base class for event stores."""
    
    @abstractmethod
    async def save_events(self, aggregate_id: DeviceId, events: List[DomainEvent], expected_version: int) -> None:
        """Save events for an aggregate."""
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: DeviceId, from_version: int = 0) -> List[DomainEvent]:
        """Get events for an aggregate from a specific version."""
        pass
    
    @abstractmethod
    async def get_all_events(self, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get all events, optionally from a specific timestamp."""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get events of a specific type."""
        pass


class InMemoryEventStore(EventStore):
    """In-memory event store implementation for testing."""
    
    def __init__(self):
        self._events: Dict[str, List[DomainEvent]] = {}
        self._all_events: List[DomainEvent] = []
    
    async def save_events(self, aggregate_id: DeviceId, events: List[DomainEvent], expected_version: int) -> None:
        """Save events for an aggregate."""
        aggregate_key = str(aggregate_id)
        
        if aggregate_key not in self._events:
            self._events[aggregate_key] = []
        
        current_version = len(self._events[aggregate_key])
        
        if current_version != expected_version:
            raise EventStoreError(
                f"Concurrency conflict: expected version {expected_version}, "
                f"but current version is {current_version}"
            )
        
        # Add events to aggregate stream
        self._events[aggregate_key].extend(events)
        
        # Add events to global stream
        self._all_events.extend(events)
    
    async def get_events(self, aggregate_id: DeviceId, from_version: int = 0) -> List[DomainEvent]:
        """Get events for an aggregate from a specific version."""
        aggregate_key = str(aggregate_id)
        
        if aggregate_key not in self._events:
            return []
        
        return self._events[aggregate_key][from_version:]
    
    async def get_all_events(self, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get all events, optionally from a specific timestamp."""
        if from_timestamp is None:
            return self._all_events.copy()
        
        return [
            event for event in self._all_events
            if event.occurred_at >= from_timestamp
        ]
    
    async def get_events_by_type(self, event_type: str, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get events of a specific type."""
        events = await self.get_all_events(from_timestamp)
        return [event for event in events if event.event_type == event_type]
    
    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()
        self._all_events.clear()


class SqlEventStore(EventStore):
    """SQL-based event store implementation."""
    
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self._event_type_registry: Dict[str, Type[DomainEvent]] = {}
    
    def register_event_type(self, event_class: Type[DomainEvent]) -> None:
        """Register an event type for deserialization."""
        # Create a temporary instance to get the event type
        temp_instance = event_class.__new__(event_class)
        if hasattr(temp_instance, 'event_type'):
            # For events that define event_type as a property
            event_type = temp_instance.__class__.__name__.replace('Event', '').lower()
            self._event_type_registry[event_type] = event_class
        else:
            # Fallback to class name
            event_type = event_class.__name__.replace('Event', '').lower()
            self._event_type_registry[event_type] = event_class
    
    async def save_events(self, aggregate_id: DeviceId, events: List[DomainEvent], expected_version: int) -> None:
        """Save events for an aggregate."""
        session: Session = self.session_factory()
        
        try:
            # Check current version
            current_version = session.query(StoredEvent).filter(
                StoredEvent.aggregate_id == aggregate_id.value
            ).count()
            
            if current_version != expected_version:
                raise EventStoreError(
                    f"Concurrency conflict: expected version {expected_version}, "
                    f"but current version is {current_version}"
                )
            
            # Save events
            for i, event in enumerate(events):
                stored_event = StoredEvent(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    aggregate_id=aggregate_id.value,
                    aggregate_version=expected_version + i + 1,
                    event_data=json.dumps(event.to_dict()),
                    occurred_at=event.occurred_at,
                )
                session.add(stored_event)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            if isinstance(e, EventStoreError):
                raise
            raise EventStoreError(f"Failed to save events: {e}") from e
        finally:
            session.close()
    
    async def get_events(self, aggregate_id: DeviceId, from_version: int = 0) -> List[DomainEvent]:
        """Get events for an aggregate from a specific version."""
        session: Session = self.session_factory()
        
        try:
            stored_events = session.query(StoredEvent).filter(
                StoredEvent.aggregate_id == aggregate_id.value,
                StoredEvent.aggregate_version > from_version
            ).order_by(StoredEvent.aggregate_version).all()
            
            return [self._deserialize_event(stored_event) for stored_event in stored_events]
            
        except Exception as e:
            raise EventStoreError(f"Failed to get events: {e}") from e
        finally:
            session.close()
    
    async def get_all_events(self, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get all events, optionally from a specific timestamp."""
        session: Session = self.session_factory()
        
        try:
            query = session.query(StoredEvent)
            
            if from_timestamp:
                query = query.filter(StoredEvent.occurred_at >= from_timestamp)
            
            stored_events = query.order_by(StoredEvent.stored_at).all()
            
            return [self._deserialize_event(stored_event) for stored_event in stored_events]
            
        except Exception as e:
            raise EventStoreError(f"Failed to get all events: {e}") from e
        finally:
            session.close()
    
    async def get_events_by_type(self, event_type: str, from_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get events of a specific type."""
        session: Session = self.session_factory()
        
        try:
            query = session.query(StoredEvent).filter(StoredEvent.event_type == event_type)
            
            if from_timestamp:
                query = query.filter(StoredEvent.occurred_at >= from_timestamp)
            
            stored_events = query.order_by(StoredEvent.occurred_at).all()
            
            return [self._deserialize_event(stored_event) for stored_event in stored_events]
            
        except Exception as e:
            raise EventStoreError(f"Failed to get events by type: {e}") from e
        finally:
            session.close()
    
    def _deserialize_event(self, stored_event: StoredEvent) -> DomainEvent:
        """Deserialize a stored event back to a domain event."""
        try:
            event_data = json.loads(stored_event.event_data)
            
            # For now, return a generic event representation
            # In a full implementation, you would reconstruct the specific event type
            from ..domain.events import DeviceRegisteredEvent
            from ..domain.value_objects import DeviceId, DeviceIdentifier
            
            # This is a simplified deserialization - in practice you'd have
            # a more sophisticated event reconstruction mechanism
            if stored_event.event_type == "device.registered":
                identifier_data = event_data['data']['identifier']
                identifier = DeviceIdentifier(
                    serial_number=identifier_data['serial_number'],
                    mac_address=identifier_data.get('mac_address'),
                    hardware_id=identifier_data.get('hardware_id'),
                )
                
                return DeviceRegisteredEvent(
                    event_id=stored_event.event_id,
                    aggregate_id=DeviceId(stored_event.aggregate_id),
                    occurred_at=stored_event.occurred_at,
                    version=stored_event.aggregate_version,
                    device_name=event_data['data']['device_name'],
                    device_type=event_data['data']['device_type'],
                    identifier=identifier,
                    manufacturer=event_data['data'].get('manufacturer'),
                    model=event_data['data'].get('model'),
                )
            
            # For other event types, you would add similar reconstruction logic
            # For now, raise an error for unsupported types
            raise EventStoreError(f"Unsupported event type for deserialization: {stored_event.event_type}")
            
        except Exception as e:
            raise EventStoreError(f"Failed to deserialize event {stored_event.event_id}: {e}") from e
