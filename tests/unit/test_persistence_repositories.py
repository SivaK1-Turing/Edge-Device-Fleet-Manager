"""
Unit tests for persistence repositories.

Tests the repository pattern implementation including CRUD operations,
query optimization, transaction management, and business logic.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from edge_device_fleet_manager.persistence.repositories.base import (
    BaseRepository, RepositoryError
)
from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
from edge_device_fleet_manager.persistence.models.device import (
    Device, DeviceStatus, DeviceType
)


class TestBaseRepository:
    """Test BaseRepository functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_model(self):
        """Create mock model class."""
        model = MagicMock()
        model.__name__ = "TestModel"
        model.id = MagicMock()
        model.is_deleted = MagicMock()
        return model
    
    @pytest.fixture
    def repository(self, mock_session, mock_model):
        """Create repository instance."""
        return BaseRepository(mock_session, mock_model)
    
    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_session, mock_model):
        """Test successful record creation."""
        # Setup
        create_data = {"name": "Test Item", "value": 42}
        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()
        mock_model.return_value = mock_instance
        
        # Execute
        result = await repository.create(create_data)
        
        # Verify
        mock_model.assert_called_once_with(**create_data)
        mock_session.add.assert_called_once_with(mock_instance)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_instance)
        assert result == mock_instance
    
    @pytest.mark.asyncio
    async def test_create_with_schema(self, repository, mock_session, mock_model):
        """Test record creation with schema object."""
        # Setup
        mock_schema = MagicMock()
        mock_schema.dict.return_value = {"name": "Test Item", "value": 42}
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        
        # Execute
        result = await repository.create(mock_schema)
        
        # Verify
        mock_schema.dict.assert_called_once()
        mock_model.assert_called_once_with(name="Test Item", value=42)
        assert result == mock_instance
    
    @pytest.mark.asyncio
    async def test_create_with_kwargs(self, repository, mock_session, mock_model):
        """Test record creation with additional kwargs."""
        # Setup
        create_data = {"name": "Test Item"}
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        
        # Execute
        result = await repository.create(create_data, extra_field="extra_value")
        
        # Verify
        mock_model.assert_called_once_with(name="Test Item", extra_field="extra_value")
        assert result == mock_instance
    
    @pytest.mark.asyncio
    async def test_create_integrity_error(self, repository, mock_session, mock_model):
        """Test creation with integrity error."""
        from sqlalchemy.exc import IntegrityError
        
        # Setup
        mock_session.flush.side_effect = IntegrityError("", "", "")
        
        # Execute & Verify
        with pytest.raises(RepositoryError, match="Failed to create"):
            await repository.create({"name": "Test"})
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_success(self, repository, mock_session, mock_model):
        """Test successful record retrieval."""
        # Setup
        record_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_instance = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get(record_id)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_instance
    
    @pytest.mark.asyncio
    async def test_get_not_found(self, repository, mock_session):
        """Test record retrieval when not found."""
        # Setup
        record_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get(record_id)
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_multi_with_pagination(self, repository, mock_session):
        """Test multiple record retrieval with pagination."""
        # Setup
        mock_result = MagicMock()
        mock_instances = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.scalars.return_value.all.return_value = mock_instances
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get_multi(skip=10, limit=20)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_instances
    
    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, repository, mock_session, mock_model):
        """Test multiple record retrieval with filters."""
        # Setup
        mock_result = MagicMock()
        mock_instances = [MagicMock()]
        mock_result.scalars.return_value.all.return_value = mock_instances
        mock_session.execute.return_value = mock_result
        
        # Mock model attributes for filtering
        mock_model.status = MagicMock()
        mock_model.name = MagicMock()
        
        # Execute
        result = await repository.get_multi(status="active", name="test")
        
        # Verify
        assert result == mock_instances
    
    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session):
        """Test successful record update."""
        # Setup
        record_id = uuid.uuid4()
        mock_instance = MagicMock()
        mock_instance.updated_at = None
        
        # Mock get method
        repository.get = AsyncMock(return_value=mock_instance)
        
        update_data = {"name": "Updated Name", "value": 100}
        
        # Execute
        result = await repository.update(record_id, update_data)
        
        # Verify
        repository.get.assert_called_once_with(record_id)
        assert mock_instance.name == "Updated Name"
        assert mock_instance.value == 100
        assert mock_instance.updated_at is not None
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_instance)
        assert result == mock_instance
    
    @pytest.mark.asyncio
    async def test_update_not_found(self, repository):
        """Test update when record not found."""
        # Setup
        record_id = uuid.uuid4()
        repository.get = AsyncMock(return_value=None)
        
        # Execute
        result = await repository.update(record_id, {"name": "Updated"})
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_soft_delete(self, repository, mock_session):
        """Test soft delete."""
        # Setup
        record_id = uuid.uuid4()
        mock_instance = MagicMock()
        mock_instance.soft_delete = MagicMock()
        repository.get = AsyncMock(return_value=mock_instance)
        
        # Execute
        result = await repository.delete(record_id, soft_delete=True)
        
        # Verify
        repository.get.assert_called_once_with(record_id)
        mock_instance.soft_delete.assert_called_once()
        mock_session.flush.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_hard_delete(self, repository, mock_session):
        """Test hard delete."""
        # Setup
        record_id = uuid.uuid4()
        mock_instance = MagicMock()
        repository.get = AsyncMock(return_value=mock_instance)
        
        # Execute
        result = await repository.delete(record_id, soft_delete=False)
        
        # Verify
        repository.get.assert_called_once_with(record_id)
        mock_session.delete.assert_called_once_with(mock_instance)
        mock_session.flush.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository):
        """Test delete when record not found."""
        # Setup
        record_id = uuid.uuid4()
        repository.get = AsyncMock(return_value=None)
        
        # Execute
        result = await repository.delete(record_id)
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session):
        """Test record counting."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.count()
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        """Test exists check when record exists."""
        # Setup
        record_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.exists(record_id)
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """Test exists check when record doesn't exist."""
        # Setup
        record_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.exists(record_id)
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_bulk_create(self, repository, mock_session, mock_model):
        """Test bulk record creation."""
        # Setup
        objects_data = [
            {"name": "Item 1", "value": 1},
            {"name": "Item 2", "value": 2},
            {"name": "Item 3", "value": 3}
        ]
        
        mock_instances = [MagicMock() for _ in objects_data]
        mock_model.side_effect = mock_instances
        
        # Execute
        result = await repository.bulk_create(objects_data)
        
        # Verify
        assert len(mock_model.call_args_list) == 3
        mock_session.add_all.assert_called_once_with(mock_instances)
        mock_session.flush.assert_called_once()
        assert len(mock_session.refresh.call_args_list) == 3
        assert result == mock_instances
    
    @pytest.mark.asyncio
    async def test_bulk_update(self, repository, mock_session):
        """Test bulk record update."""
        # Setup
        updates = [
            {"id": uuid.uuid4(), "name": "Updated 1"},
            {"id": uuid.uuid4(), "name": "Updated 2"}
        ]
        
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.bulk_update(updates)
        
        # Verify
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_search(self, repository, mock_session, mock_model):
        """Test text search functionality."""
        # Setup
        mock_result = MagicMock()
        mock_instances = [MagicMock(), MagicMock()]
        mock_result.scalars.return_value.all.return_value = mock_instances
        mock_session.execute.return_value = mock_result
        
        # Mock model attributes for search
        mock_model.name = MagicMock()
        mock_model.description = MagicMock()
        mock_model.is_deleted = MagicMock()
        
        # Execute
        result = await repository.search("test", ["name", "description"])
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_instances


class TestDeviceRepository:
    """Test DeviceRepository specific functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session
    
    @pytest.fixture
    def device_repository(self, mock_session):
        """Create device repository instance."""
        return DeviceRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_by_ip_address(self, device_repository, mock_session):
        """Test getting device by IP address."""
        # Setup
        ip_address = "192.168.1.100"
        mock_device = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await device_repository.get_by_ip_address(ip_address)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_device
    
    @pytest.mark.asyncio
    async def test_get_by_mac_address(self, device_repository, mock_session):
        """Test getting device by MAC address."""
        # Setup
        mac_address = "00:11:22:33:44:55"
        mock_device = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await device_repository.get_by_mac_address(mac_address)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_device
    
    @pytest.mark.asyncio
    async def test_get_by_status(self, device_repository, mock_session):
        """Test getting devices by status."""
        # Setup
        status = DeviceStatus.ONLINE
        mock_devices = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await device_repository.get_by_status(status)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_devices
    
    @pytest.mark.asyncio
    async def test_get_stale_devices(self, device_repository, mock_session):
        """Test getting stale devices."""
        # Setup
        mock_devices = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await device_repository.get_stale_devices(stale_threshold_minutes=30)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_devices
    
    @pytest.mark.asyncio
    async def test_get_unhealthy_devices(self, device_repository, mock_session):
        """Test getting unhealthy devices."""
        # Setup
        mock_devices = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await device_repository.get_unhealthy_devices(health_threshold=0.5)
        
        # Verify
        mock_session.execute.assert_called_once()
        assert result == mock_devices
    
    @pytest.mark.asyncio
    async def test_get_device_statistics(self, device_repository, mock_session):
        """Test getting device statistics."""
        # Setup
        # Mock total count
        total_result = MagicMock()
        total_result.scalar.return_value = 100
        
        # Mock status distribution
        status_result = MagicMock()
        status_result.all.return_value = [
            (DeviceStatus.ONLINE, 80),
            (DeviceStatus.OFFLINE, 20)
        ]
        
        # Mock type distribution
        type_result = MagicMock()
        type_result.all.return_value = [
            (DeviceType.SENSOR, 60),
            (DeviceType.GATEWAY, 40)
        ]
        
        # Mock health statistics
        health_result = MagicMock()
        health_result.first.return_value = (0.85, 0.2, 1.0)
        
        mock_session.execute.side_effect = [
            total_result, status_result, type_result, health_result
        ]
        
        # Execute
        result = await device_repository.get_device_statistics()
        
        # Verify
        assert result['total_devices'] == 100
        assert result['status_distribution']['online'] == 80
        assert result['status_distribution']['offline'] == 20
        assert result['type_distribution']['sensor'] == 60
        assert result['type_distribution']['gateway'] == 40
        assert result['health_statistics']['average_health'] == 0.85
        assert result['health_statistics']['min_health'] == 0.2
        assert result['health_statistics']['max_health'] == 1.0
    
    @pytest.mark.asyncio
    async def test_update_last_seen(self, device_repository):
        """Test updating device last seen timestamp."""
        # Setup
        device_id = uuid.uuid4()
        mock_device = MagicMock()
        mock_device.update_last_seen = MagicMock()
        device_repository.get = AsyncMock(return_value=mock_device)
        
        # Execute
        result = await device_repository.update_last_seen(device_id)
        
        # Verify
        device_repository.get.assert_called_once_with(device_id)
        mock_device.update_last_seen.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_last_seen_not_found(self, device_repository):
        """Test updating last seen for non-existent device."""
        # Setup
        device_id = uuid.uuid4()
        device_repository.get = AsyncMock(return_value=None)
        
        # Execute
        result = await device_repository.update_last_seen(device_id)
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_mark_devices_offline(self, device_repository):
        """Test marking multiple devices offline."""
        # Setup
        device_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        device_repository.bulk_update = AsyncMock(return_value=3)
        
        # Execute
        result = await device_repository.mark_devices_offline(device_ids)
        
        # Verify
        device_repository.bulk_update.assert_called_once()
        call_args = device_repository.bulk_update.call_args[0][0]
        assert len(call_args) == 3
        assert all(update['status'] == DeviceStatus.OFFLINE for update in call_args)
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_search_devices(self, device_repository):
        """Test device search functionality."""
        # Setup
        search_term = "sensor"
        mock_devices = [MagicMock(), MagicMock()]
        device_repository.search = AsyncMock(return_value=mock_devices)
        
        # Execute
        result = await device_repository.search_devices(search_term)
        
        # Verify
        device_repository.search.assert_called_once_with(
            search_term,
            ['name', 'hostname', 'location', 'manufacturer', 'model'],
            0,
            100
        )
        assert result == mock_devices


class TestDatabaseConnection:
    """Test database connection management."""

    @pytest.fixture
    def mock_config(self):
        """Create mock database configuration."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        return DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            pool_size=5,
            max_overflow=10
        )

    @pytest.mark.asyncio
    async def test_database_manager_initialization(self, mock_config):
        """Test database manager initialization."""
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager

        manager = DatabaseManager(mock_config)

        assert manager.config == mock_config
        assert manager.engine is None
        assert manager.session_factory is None
        assert manager._is_initialized is False

    def test_database_config_validation(self):
        """Test database configuration validation."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig

        # Test valid configuration
        config = DatabaseConfig(
            database_url="postgresql://user:pass@localhost/db",
            pool_size=5,
            max_overflow=10
        )

        errors = config.validate()
        assert len(errors) == 0

        # Test invalid configuration
        invalid_config = DatabaseConfig(
            database_url="",
            pool_size=-1,
            max_overflow=-5
        )

        errors = invalid_config.validate()
        assert len(errors) > 0
        assert any("Database URL is required" in error for error in errors)
        assert any("Pool size must be positive" in error for error in errors)
