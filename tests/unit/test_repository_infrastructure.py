"""
Unit tests for repository infrastructure layer.

Tests event store, repositories, database, and unit of work.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from edge_device_fleet_manager.repository.infrastructure.event_store import (
    InMemoryEventStore, EventStoreError
)
from edge_device_fleet_manager.repository.infrastructure.repositories import (
    InMemoryDeviceRepository
)
from edge_device_fleet_manager.repository.infrastructure.unit_of_work import (
    InMemoryUnitOfWork
)
from edge_device_fleet_manager.repository.infrastructure.database import (
    create_test_database, DatabaseMigration
)
from edge_device_fleet_manager.repository.domain.entities import (
    DeviceAggregate, DeviceType, DeviceStatus
)
from edge_device_fleet_manager.repository.domain.value_objects import (
    DeviceId, DeviceIdentifier, DeviceMetrics
)
from edge_device_fleet_manager.repository.domain.events import (
    DeviceRegisteredEvent, DeviceMetricsRecordedEvent
)


class TestInMemoryEventStore:
    """Test in-memory event store."""
    
    @pytest.fixture
    def event_store(self):
        """Create event store."""
        return InMemoryEventStore()
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        event1 = DeviceRegisteredEvent(
            aggregate_id=device_id,
            device_name="Test Device",
            device_type="sensor",
            identifier=identifier,
            version=1
        )
        
        metrics = DeviceMetrics.create_now(cpu_usage_percent=50.0)
        event2 = DeviceMetricsRecordedEvent(
            aggregate_id=device_id,
            metrics=metrics,
            version=2
        )
        
        return device_id, [event1, event2]
    
    async def test_save_and_get_events(self, event_store, sample_events):
        """Test saving and retrieving events."""
        device_id, events = sample_events
        
        # Save events
        await event_store.save_events(device_id, events, 0)
        
        # Get events
        retrieved_events = await event_store.get_events(device_id)
        
        assert len(retrieved_events) == 2
        assert retrieved_events[0].event_type == "device.registered"
        assert retrieved_events[1].event_type == "device.metrics.recorded"
    
    async def test_get_events_from_version(self, event_store, sample_events):
        """Test getting events from specific version."""
        device_id, events = sample_events
        
        # Save events
        await event_store.save_events(device_id, events, 0)
        
        # Get events from version 1
        retrieved_events = await event_store.get_events(device_id, from_version=1)
        
        assert len(retrieved_events) == 1
        assert retrieved_events[0].event_type == "device.metrics.recorded"
    
    async def test_concurrency_conflict(self, event_store, sample_events):
        """Test concurrency conflict detection."""
        device_id, events = sample_events
        
        # Save initial events
        await event_store.save_events(device_id, events[:1], 0)
        
        # Try to save with wrong expected version
        with pytest.raises(EventStoreError, match="Concurrency conflict"):
            await event_store.save_events(device_id, events[1:], 0)  # Should be 1
    
    async def test_get_all_events(self, event_store, sample_events):
        """Test getting all events."""
        device_id, events = sample_events
        
        # Save events
        await event_store.save_events(device_id, events, 0)
        
        # Get all events
        all_events = await event_store.get_all_events()
        
        assert len(all_events) == 2
    
    async def test_get_events_by_type(self, event_store, sample_events):
        """Test getting events by type."""
        device_id, events = sample_events
        
        # Save events
        await event_store.save_events(device_id, events, 0)
        
        # Get events by type
        metrics_events = await event_store.get_events_by_type("device.metrics.recorded")
        
        assert len(metrics_events) == 1
        assert metrics_events[0].event_type == "device.metrics.recorded"
    
    def test_clear(self, event_store):
        """Test clearing event store."""
        event_store.clear()
        
        # Event store should be empty
        assert len(event_store._events) == 0
        assert len(event_store._all_events) == 0


class TestInMemoryDeviceRepository:
    """Test in-memory device repository."""
    
    @pytest.fixture
    def repository(self):
        """Create device repository."""
        return InMemoryDeviceRepository()
    
    @pytest.fixture
    def sample_aggregate(self):
        """Create sample device aggregate."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        return DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
    
    async def test_save_and_get_device(self, repository, sample_aggregate):
        """Test saving and retrieving device."""
        # Save device
        await repository.save(sample_aggregate)
        
        # Get device by ID
        retrieved = await repository.get_by_id(sample_aggregate.device_id)
        
        assert retrieved is not None
        assert retrieved.device_id == sample_aggregate.device_id
        assert retrieved.device.name == "Test Device"
    
    async def test_get_by_serial_number(self, repository, sample_aggregate):
        """Test getting device by serial number."""
        # Save device
        await repository.save(sample_aggregate)
        
        # Get device by serial number
        retrieved = await repository.get_by_serial_number("SN123456")
        
        assert retrieved is not None
        assert retrieved.device.identifier.serial_number == "SN123456"
    
    async def test_get_all_devices(self, repository):
        """Test getting all devices."""
        # Create multiple devices
        devices = []
        for i in range(3):
            device_id = DeviceId.generate()
            identifier = DeviceIdentifier(serial_number=f"SN{i}")
            
            aggregate = DeviceAggregate.create(
                device_id=device_id,
                name=f"Device {i}",
                device_type=DeviceType.SENSOR,
                identifier=identifier
            )
            devices.append(aggregate)
            await repository.save(aggregate)
        
        # Get all devices
        all_devices = await repository.get_all()
        
        assert len(all_devices) == 3
    
    async def test_find_by_criteria(self, repository):
        """Test finding devices by criteria."""
        # Create devices with different types
        sensor_device = DeviceAggregate.create(
            device_id=DeviceId.generate(),
            name="Sensor Device",
            device_type=DeviceType.SENSOR,
            identifier=DeviceIdentifier(serial_number="SN001")
        )
        
        actuator_device = DeviceAggregate.create(
            device_id=DeviceId.generate(),
            name="Actuator Device",
            device_type=DeviceType.ACTUATOR,
            identifier=DeviceIdentifier(serial_number="SN002")
        )
        
        await repository.save(sensor_device)
        await repository.save(actuator_device)
        
        # Find sensors
        sensors = await repository.find_by_criteria({"device_type": "sensor"})
        assert len(sensors) == 1
        assert sensors[0].device.name == "Sensor Device"
        
        # Find actuators
        actuators = await repository.find_by_criteria({"device_type": "actuator"})
        assert len(actuators) == 1
        assert actuators[0].device.name == "Actuator Device"
    
    async def test_delete_device(self, repository, sample_aggregate):
        """Test deleting device."""
        # Save device
        await repository.save(sample_aggregate)
        
        # Delete device
        deleted = await repository.delete(sample_aggregate.device_id)
        assert deleted is True
        
        # Device should not exist
        retrieved = await repository.get_by_id(sample_aggregate.device_id)
        assert retrieved is None
        
        # Delete non-existent device
        deleted = await repository.delete(DeviceId.generate())
        assert deleted is False
    
    def test_clear(self, repository, sample_aggregate):
        """Test clearing repository."""
        # Save device
        asyncio.run(repository.save(sample_aggregate))
        
        # Clear repository
        repository.clear()
        
        # Repository should be empty
        all_devices = asyncio.run(repository.get_all())
        assert len(all_devices) == 0


class TestInMemoryUnitOfWork:
    """Test in-memory unit of work."""
    
    @pytest.fixture
    def unit_of_work(self):
        """Create unit of work."""
        return InMemoryUnitOfWork()
    
    @pytest.fixture
    def sample_aggregate(self):
        """Create sample device aggregate."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        return DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
    
    async def test_unit_of_work_context_manager(self, unit_of_work):
        """Test unit of work as context manager."""
        async with unit_of_work as uow:
            assert uow is unit_of_work
            assert uow.devices is not None
            assert uow.event_store is not None
    
    async def test_unit_of_work_commit(self, unit_of_work, sample_aggregate):
        """Test unit of work commit."""
        async with unit_of_work as uow:
            # Save device
            await uow.devices.save(sample_aggregate)
            uow.track_aggregate(sample_aggregate)
            
            # Commit
            await uow.commit()
            
            # Events should be saved
            events = await uow.event_store.get_events(sample_aggregate.device_id)
            assert len(events) > 0
    
    async def test_unit_of_work_rollback(self, unit_of_work, sample_aggregate):
        """Test unit of work rollback."""
        async with unit_of_work as uow:
            # Save device
            await uow.devices.save(sample_aggregate)
            uow.track_aggregate(sample_aggregate)
            
            # Rollback
            await uow.rollback()
            
            # Aggregates should be cleared
            assert len(uow._aggregates) == 0
    
    async def test_collect_new_events(self, unit_of_work, sample_aggregate):
        """Test collecting new events."""
        async with unit_of_work as uow:
            # Track aggregate with events
            uow.track_aggregate(sample_aggregate)
            
            # Collect events
            events = await uow.collect_new_events()
            
            assert len(events) > 0
            assert events[0].event_type == "device.registered"
    
    def test_clear(self, unit_of_work):
        """Test clearing unit of work."""
        unit_of_work.clear()
        
        # Should be empty
        assert len(unit_of_work._aggregates) == 0


class TestDatabaseSession:
    """Test database session management."""
    
    def test_create_test_database(self):
        """Test creating test database."""
        db_session = create_test_database()
        
        assert db_session is not None
        assert db_session.engine is not None
        assert db_session.session_factory is not None
    
    def test_database_migration(self):
        """Test database migration utilities."""
        db_session = create_test_database()
        migration = DatabaseMigration(db_session.engine)
        
        # Schema should exist (created by create_test_database)
        assert migration.check_schema_exists() is True
        
        # Get schema version
        version = migration.get_schema_version()
        assert version is not None
    
    def test_session_context_manager(self):
        """Test session context manager."""
        db_session = create_test_database()
        
        with db_session.get_session() as session:
            # Should be able to execute queries
            result = session.execute("SELECT 1")
            assert result.fetchone()[0] == 1
    
    def test_create_and_drop_tables(self):
        """Test creating and dropping tables."""
        db_session = create_test_database()
        
        # Tables should exist
        migration = DatabaseMigration(db_session.engine)
        assert migration.check_schema_exists() is True
        
        # Drop tables
        db_session.drop_tables()
        
        # Tables should not exist
        assert migration.check_schema_exists() is False
        
        # Recreate tables
        db_session.create_tables()
        
        # Tables should exist again
        assert migration.check_schema_exists() is True


class TestEventStoreIntegration:
    """Test event store integration scenarios."""
    
    @pytest.fixture
    def event_store(self):
        """Create event store."""
        return InMemoryEventStore()
    
    async def test_event_replay_scenario(self, event_store):
        """Test event replay scenario."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        # Create initial registration event
        registration_event = DeviceRegisteredEvent(
            aggregate_id=device_id,
            device_name="Test Device",
            device_type="sensor",
            identifier=identifier,
            version=1
        )
        
        # Save registration event
        await event_store.save_events(device_id, [registration_event], 0)
        
        # Add metrics events over time
        for i in range(5):
            metrics = DeviceMetrics.create_now(cpu_usage_percent=float(i * 10))
            metrics_event = DeviceMetricsRecordedEvent(
                aggregate_id=device_id,
                metrics=metrics,
                version=i + 2
            )
            await event_store.save_events(device_id, [metrics_event], i + 1)
        
        # Replay all events
        all_events = await event_store.get_events(device_id)
        
        assert len(all_events) == 6  # 1 registration + 5 metrics
        assert all_events[0].event_type == "device.registered"
        
        # Replay from specific version
        recent_events = await event_store.get_events(device_id, from_version=3)
        assert len(recent_events) == 3
    
    async def test_multiple_aggregates(self, event_store):
        """Test multiple aggregates in event store."""
        # Create multiple devices
        devices = []
        for i in range(3):
            device_id = DeviceId.generate()
            identifier = DeviceIdentifier(serial_number=f"SN{i}")
            
            event = DeviceRegisteredEvent(
                aggregate_id=device_id,
                device_name=f"Device {i}",
                device_type="sensor",
                identifier=identifier,
                version=1
            )
            
            await event_store.save_events(device_id, [event], 0)
            devices.append(device_id)
        
        # Get all events
        all_events = await event_store.get_all_events()
        assert len(all_events) == 3
        
        # Get events for specific device
        device_events = await event_store.get_events(devices[0])
        assert len(device_events) == 1
        assert device_events[0].aggregate_id == devices[0]
    
    async def test_event_ordering(self, event_store):
        """Test event ordering and timestamps."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        # Create events with different timestamps
        events = []
        for i in range(3):
            event = DeviceRegisteredEvent(
                aggregate_id=device_id,
                device_name=f"Device {i}",
                device_type="sensor",
                identifier=identifier,
                version=i + 1,
                occurred_at=datetime.now(timezone.utc)
            )
            events.append(event)
            
            # Save one by one to ensure ordering
            await event_store.save_events(device_id, [event], i)
        
        # Get events and verify ordering
        retrieved_events = await event_store.get_events(device_id)
        
        assert len(retrieved_events) == 3
        for i in range(2):
            assert retrieved_events[i].occurred_at <= retrieved_events[i + 1].occurred_at
