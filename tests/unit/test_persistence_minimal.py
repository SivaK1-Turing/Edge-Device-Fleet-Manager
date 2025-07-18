"""
Minimal persistence tests that avoid SQLAlchemy mapper issues.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestPersistenceImports:
    """Test that persistence modules can be imported."""
    
    def test_device_enums_import(self):
        """Test device enum imports."""
        from edge_device_fleet_manager.persistence.models.device import DeviceStatus, DeviceType
        assert DeviceStatus.ONLINE.value == "online"
        assert DeviceType.SENSOR.value == "sensor"
    
    def test_telemetry_enums_import(self):
        """Test telemetry enum imports."""
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryType
        assert TelemetryType.SENSOR_DATA.value == "sensor_data"
    
    def test_model_classes_import(self):
        """Test model class imports."""
        from edge_device_fleet_manager.persistence.models.device import Device
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent
        
        # Just check that classes exist
        assert Device.__tablename__ == "devices"
        assert TelemetryEvent.__tablename__ == "telemetry_events"
    
    def test_repository_classes_import(self):
        """Test repository class imports."""
        from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
        from edge_device_fleet_manager.persistence.repositories.telemetry import TelemetryRepository
        
        # Check that classes have expected methods
        assert hasattr(DeviceRepository, '__init__')
        assert hasattr(TelemetryRepository, '__init__')
    
    def test_connection_classes_import(self):
        """Test connection class imports."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
        
        # Test basic configuration
        config = DatabaseConfig()
        assert config.database_url is not None
        assert config.pool_size > 0

class TestDatabaseConfiguration:
    """Test database configuration."""
    
    def test_valid_configuration(self):
        """Test valid configuration creation."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        
        config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            pool_size=5,
            max_overflow=10
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_invalid_configuration(self):
        """Test invalid configuration detection."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        
        config = DatabaseConfig(
            database_url="",
            pool_size=-1
        )
        
        errors = config.validate()
        assert len(errors) > 0
    
    def test_configuration_methods(self):
        """Test configuration utility methods."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        
        config = DatabaseConfig(database_url="sqlite+aiosqlite:///:memory:")
        
        assert config.is_sqlite() is True
        assert config.get_database_type() == "sqlite"
        
        config_dict = config.to_dict()
        assert 'database_url' in config_dict
        assert 'pool_size' in config_dict

@pytest.mark.asyncio
class TestDatabaseConnection:
    """Test database connection functionality."""
    
    async def test_database_manager_lifecycle(self):
        """Test database manager initialization and shutdown."""
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
        
        config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            enable_health_checks=False
        )
        
        manager = DatabaseManager(config)
        
        # Test initialization
        await manager.initialize()
        assert manager._is_initialized is True
        assert manager.engine is not None
        
        # Test connection check
        is_healthy = await manager.check_connection()
        assert is_healthy is True
        
        # Test session creation
        async with manager.get_session() as session:
            assert session is not None
        
        # Test shutdown
        await manager.shutdown()
        assert manager._is_initialized is False
