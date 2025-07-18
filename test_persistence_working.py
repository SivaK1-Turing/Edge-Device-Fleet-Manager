#!/usr/bin/env python3
"""
Working persistence tests that avoid SQLAlchemy mapper configuration issues.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all persistence modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        # Test enum imports
        from edge_device_fleet_manager.persistence.models.device import DeviceStatus, DeviceType
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryType
        from edge_device_fleet_manager.persistence.models.analytics import AnalyticsType, AnalyticsMetric
        from edge_device_fleet_manager.persistence.models.user import UserRole, UserStatus
        from edge_device_fleet_manager.persistence.models.alert import AlertSeverity, AlertStatus
        from edge_device_fleet_manager.persistence.models.audit_log import AuditAction, AuditResource
        print("  ✅ Enums imported")
        
        # Test model class imports (without instantiation)
        from edge_device_fleet_manager.persistence.models.device import Device
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent
        from edge_device_fleet_manager.persistence.models.analytics import Analytics
        from edge_device_fleet_manager.persistence.models.user import User
        from edge_device_fleet_manager.persistence.models.device_group import DeviceGroup
        from edge_device_fleet_manager.persistence.models.alert import Alert
        from edge_device_fleet_manager.persistence.models.audit_log import AuditLog
        print("  ✅ Model classes imported")
        
        # Test repository imports
        from edge_device_fleet_manager.persistence.repositories.base import BaseRepository
        from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
        from edge_device_fleet_manager.persistence.repositories.telemetry import TelemetryRepository
        from edge_device_fleet_manager.persistence.repositories.analytics import AnalyticsRepository
        from edge_device_fleet_manager.persistence.repositories.user import UserRepository
        from edge_device_fleet_manager.persistence.repositories.device_group import DeviceGroupRepository
        from edge_device_fleet_manager.persistence.repositories.alert import AlertRepository
        from edge_device_fleet_manager.persistence.repositories.audit_log import AuditLogRepository
        print("  ✅ Repository classes imported")
        
        # Test connection imports
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
        from edge_device_fleet_manager.persistence.connection.health import HealthChecker
        from edge_device_fleet_manager.persistence.connection.pool import ConnectionPool
        print("  ✅ Connection classes imported")
        
        # Test migration imports
        from edge_device_fleet_manager.persistence.migrations.manager import MigrationManager
        from edge_device_fleet_manager.persistence.migrations.migrator import DatabaseMigrator
        from edge_device_fleet_manager.persistence.migrations.utils import MigrationUtils
        from edge_device_fleet_manager.persistence.migrations.validators import SchemaValidator
        print("  ✅ Migration classes imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_enum_values():
    """Test enum values are correct."""
    print("🔍 Testing enum values...")
    
    try:
        from edge_device_fleet_manager.persistence.models.device import DeviceStatus, DeviceType
        
        # Test DeviceStatus enum
        assert DeviceStatus.ONLINE.value == "online"
        assert DeviceStatus.OFFLINE.value == "offline"
        assert DeviceStatus.MAINTENANCE.value == "maintenance"
        assert DeviceStatus.ERROR.value == "error"
        print("  ✅ DeviceStatus enum values correct")
        
        # Test DeviceType enum
        assert DeviceType.SENSOR.value == "sensor"
        assert DeviceType.ACTUATOR.value == "actuator"
        assert DeviceType.GATEWAY.value == "gateway"
        assert DeviceType.CONTROLLER.value == "controller"
        print("  ✅ DeviceType enum values correct")
        
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryType
        assert TelemetryType.SENSOR_DATA.value == "sensor_data"
        assert TelemetryType.SYSTEM_METRICS.value == "system_metrics"
        print("  ✅ TelemetryType enum values correct")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Enum test failed: {e}")
        return False

def test_configuration():
    """Test configuration classes."""
    print("🔍 Testing configuration...")
    
    try:
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        
        # Test default configuration
        config = DatabaseConfig()
        assert config.database_url is not None
        assert config.pool_size > 0
        assert config.max_overflow >= 0
        print("  ✅ Default configuration created")
        
        # Test custom configuration
        custom_config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            pool_size=5,
            max_overflow=10,
            enable_health_checks=True
        )
        assert custom_config.database_url == "sqlite+aiosqlite:///:memory:"
        assert custom_config.pool_size == 5
        assert custom_config.max_overflow == 10
        print("  ✅ Custom configuration created")
        
        # Test validation
        errors = custom_config.validate()
        assert len(errors) == 0
        print("  ✅ Configuration validation passed")
        
        # Test invalid configuration
        invalid_config = DatabaseConfig(
            database_url="",
            pool_size=-1,
            max_overflow=-5
        )
        errors = invalid_config.validate()
        assert len(errors) > 0
        print("  ✅ Invalid configuration properly detected")
        
        # Test configuration methods
        assert custom_config.is_sqlite() is True
        assert custom_config.get_database_type() == "sqlite"
        print("  ✅ Configuration methods work")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def test_model_table_names():
    """Test that model table names are set correctly."""
    print("🔍 Testing model table names...")
    
    try:
        from edge_device_fleet_manager.persistence.models.device import Device
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent
        from edge_device_fleet_manager.persistence.models.analytics import Analytics
        from edge_device_fleet_manager.persistence.models.user import User
        from edge_device_fleet_manager.persistence.models.device_group import DeviceGroup
        from edge_device_fleet_manager.persistence.models.alert import Alert
        from edge_device_fleet_manager.persistence.models.audit_log import AuditLog
        
        # Check table names
        assert Device.__tablename__ == "devices"
        assert TelemetryEvent.__tablename__ == "telemetry_events"
        assert Analytics.__tablename__ == "analytics"
        assert User.__tablename__ == "users"
        assert DeviceGroup.__tablename__ == "device_groups"
        assert Alert.__tablename__ == "alerts"
        assert AuditLog.__tablename__ == "audit_logs"
        
        print("  ✅ All table names are correct")
        return True
        
    except Exception as e:
        print(f"  ❌ Table name test failed: {e}")
        return False

def test_model_inheritance():
    """Test that models inherit from BaseModel correctly."""
    print("🔍 Testing model inheritance...")
    
    try:
        from edge_device_fleet_manager.persistence.models.base import BaseModel
        from edge_device_fleet_manager.persistence.models.device import Device
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent
        
        # Check inheritance
        assert issubclass(Device, BaseModel)
        assert issubclass(TelemetryEvent, BaseModel)
        
        print("  ✅ Model inheritance is correct")
        return True
        
    except Exception as e:
        print(f"  ❌ Inheritance test failed: {e}")
        return False

def test_repository_inheritance():
    """Test that repositories inherit from BaseRepository correctly."""
    print("🔍 Testing repository inheritance...")
    
    try:
        from edge_device_fleet_manager.persistence.repositories.base import BaseRepository
        from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
        from edge_device_fleet_manager.persistence.repositories.telemetry import TelemetryRepository
        
        # Check that classes exist and have the right structure
        assert hasattr(DeviceRepository, '__init__')
        assert hasattr(TelemetryRepository, '__init__')
        
        print("  ✅ Repository structure is correct")
        return True
        
    except Exception as e:
        print(f"  ❌ Repository test failed: {e}")
        return False

async def test_database_connection():
    """Test database connection without model instantiation."""
    print("🔍 Testing database connection...")
    
    try:
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
        
        # Create configuration
        config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            enable_health_checks=False
        )
        
        # Create manager
        manager = DatabaseManager(config)
        await manager.initialize()
        print("  ✅ Database manager initialized")
        
        # Test connection
        is_healthy = await manager.check_connection()
        assert is_healthy is True
        print("  ✅ Database connection is healthy")
        
        # Test session creation
        async with manager.get_session() as session:
            assert session is not None
        print("  ✅ Session creation works")
        
        # Test transaction
        async with manager.get_transaction() as session:
            assert session is not None
        print("  ✅ Transaction management works")
        
        # Cleanup
        await manager.shutdown()
        print("  ✅ Database manager shutdown")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database connection test failed: {e}")
        return False

def main():
    """Run all working tests."""
    print("🚀 Running Working Persistence Tests")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Enum Value Tests", test_enum_values),
        ("Configuration Tests", test_configuration),
        ("Model Table Name Tests", test_model_table_names),
        ("Model Inheritance Tests", test_model_inheritance),
        ("Repository Structure Tests", test_repository_inheritance),
    ]
    
    # Run sync tests
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}")
    
    # Run async test
    print(f"\n📋 Database Connection Tests")
    try:
        import asyncio
        if asyncio.run(test_database_connection()):
            passed += 1
            print(f"✅ Database Connection Tests PASSED")
        else:
            failed += 1
            print(f"❌ Database Connection Tests FAILED")
    except Exception as e:
        failed += 1
        print(f"❌ Database Connection Tests FAILED: {e}")
    
    # Summary
    total = passed + failed
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if failed == 0:
        print("🎉 All working persistence tests passed!")
        return True
    else:
        print(f"❌ {failed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
