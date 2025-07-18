#!/usr/bin/env python3
"""
Comprehensive Fixed Test Suite for Feature 5: Robust Persistence & Migrations

This test suite addresses all the issues found in the pytest runs and provides
a complete validation of the persistence layer functionality.
"""

import asyncio
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.persistence.models.device import (
    Device, DeviceStatus, DeviceType
)
from edge_device_fleet_manager.persistence.models.telemetry import (
    TelemetryEvent, TelemetryType
)
from edge_device_fleet_manager.persistence.models.analytics import (
    Analytics, AnalyticsType, AnalyticsMetric
)
from edge_device_fleet_manager.persistence.models.user import (
    User, UserRole, UserStatus
)
from edge_device_fleet_manager.persistence.models.device_group import DeviceGroup
from edge_device_fleet_manager.persistence.models.alert import (
    Alert, AlertSeverity, AlertStatus
)
from edge_device_fleet_manager.persistence.models.audit_log import (
    AuditLog, AuditAction, AuditResource
)
from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✅ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"  ❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Results: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"❌ {self.failed} tests failed:")
            for error in self.errors:
                print(f"   - {error}")
        return self.failed == 0


async def test_model_creation_fixed():
    """Test model creation with proper initialization."""
    print("🔍 Testing Model Creation (Fixed)...")
    results = TestResults()
    
    try:
        # Test Device model with manual ID setting
        device = Device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE,
            ip_address="192.168.1.100",
            health_score=0.85
        )
        # Manually set required fields that would normally be set by SQLAlchemy
        device.id = uuid.uuid4()
        device.created_at = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)
        
        assert device.name == "Test Device"
        assert device.device_type == DeviceType.SENSOR
        assert device.status == DeviceStatus.ONLINE
        assert device.is_online is True
        assert device.is_healthy is True
        results.add_pass("Device creation")
        
    except Exception as e:
        results.add_fail("Device creation", str(e))
    
    try:
        # Test TelemetryEvent with proper timestamp
        telemetry = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="temperature_reading",
            numeric_value=25.5,
            units="celsius"
        )
        # Set required fields manually
        telemetry.id = uuid.uuid4()
        telemetry.timestamp = datetime.now(timezone.utc)
        telemetry.received_at = datetime.now(timezone.utc)
        telemetry.created_at = datetime.now(timezone.utc)
        telemetry.updated_at = datetime.now(timezone.utc)
        
        assert telemetry.device_id is not None
        assert telemetry.event_type == TelemetryType.SENSOR_DATA
        assert telemetry.timestamp is not None
        assert telemetry.received_at is not None
        results.add_pass("TelemetryEvent creation")
        
    except Exception as e:
        results.add_fail("TelemetryEvent creation", str(e))
    
    try:
        # Test Analytics model
        analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="average_temperature",
            metric_type=AnalyticsMetric.AVERAGE,
            period_start=datetime.now(timezone.utc) - timedelta(hours=1),
            period_end=datetime.now(timezone.utc),
            granularity="hourly",
            scope="device",
            numeric_value=25.5
        )
        analytics.id = uuid.uuid4()
        analytics.created_at = datetime.now(timezone.utc)
        analytics.updated_at = datetime.now(timezone.utc)
        
        assert analytics.analytics_type == AnalyticsType.DEVICE_METRICS
        assert analytics.get_primary_value() == 25.5
        results.add_pass("Analytics creation")
        
    except Exception as e:
        results.add_fail("Analytics creation", str(e))
    
    try:
        # Test User model
        user = User(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role=UserRole.OPERATOR
        )
        user.id = uuid.uuid4()
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.has_permission("devices.read") is True
        results.add_pass("User creation")
        
    except Exception as e:
        results.add_fail("User creation", str(e))
    
    try:
        # Test DeviceGroup model
        group = DeviceGroup(
            name="Test Group",
            description="A test device group",
            group_type="sensor_group"
        )
        group.id = uuid.uuid4()
        group.created_at = datetime.now(timezone.utc)
        group.updated_at = datetime.now(timezone.utc)
        
        assert group.name == "Test Group"
        assert group.is_root_group is True
        results.add_pass("DeviceGroup creation")
        
    except Exception as e:
        results.add_fail("DeviceGroup creation", str(e))
    
    try:
        # Test Alert model
        alert = Alert(
            title="Test Alert",
            description="A test alert",
            alert_type="system_error",
            severity=AlertSeverity.HIGH,
            device_id=uuid.uuid4()
        )
        alert.id = uuid.uuid4()
        alert.created_at = datetime.now(timezone.utc)
        alert.updated_at = datetime.now(timezone.utc)
        alert.first_occurred = datetime.now(timezone.utc)
        
        assert alert.title == "Test Alert"
        assert alert.is_open is True
        results.add_pass("Alert creation")
        
    except Exception as e:
        results.add_fail("Alert creation", str(e))
    
    try:
        # Test AuditLog model
        audit_log = AuditLog.create_log(
            action=AuditAction.CREATE,
            resource_type=AuditResource.DEVICE,
            resource_id="device-123",
            description="Created new device"
        )
        
        assert audit_log.action == AuditAction.CREATE
        assert audit_log.resource_type == AuditResource.DEVICE
        assert audit_log.success is True
        results.add_pass("AuditLog creation")
        
    except Exception as e:
        results.add_fail("AuditLog creation", str(e))
    
    return results.summary()


async def test_model_validation_fixed():
    """Test model validation with proper error handling."""
    print("🔍 Testing Model Validation (Fixed)...")
    results = TestResults()
    
    try:
        # Test Device validation
        device = Device(name="Test Device")
        device.id = uuid.uuid4()
        device.created_at = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)
        
        # Test health score validation
        try:
            device.health_score = 1.5  # Should fail
            results.add_fail("Device health score validation", "Should have raised ValueError")
        except ValueError:
            results.add_pass("Device health score validation")
        
        # Test battery level validation
        try:
            device.battery_level = 150.0  # Should fail
            results.add_fail("Device battery level validation", "Should have raised ValueError")
        except ValueError:
            results.add_pass("Device battery level validation")
        
    except Exception as e:
        results.add_fail("Device validation setup", str(e))
    
    try:
        # Test TelemetryEvent validation
        telemetry = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="test_event"
        )
        telemetry.id = uuid.uuid4()
        telemetry.timestamp = datetime.now(timezone.utc)
        telemetry.received_at = datetime.now(timezone.utc)
        telemetry.created_at = datetime.now(timezone.utc)
        telemetry.updated_at = datetime.now(timezone.utc)
        
        # Test quality score validation
        try:
            telemetry.quality_score = 1.5  # Should fail
            results.add_fail("Telemetry quality score validation", "Should have raised ValueError")
        except ValueError:
            results.add_pass("Telemetry quality score validation")
        
    except Exception as e:
        results.add_fail("Telemetry validation setup", str(e))
    
    return results.summary()


async def test_model_business_logic_fixed():
    """Test model business logic methods."""
    print("🔍 Testing Model Business Logic (Fixed)...")
    results = TestResults()
    
    try:
        # Test Device business methods
        device = Device(
            name="Test Device",
            status=DeviceStatus.OFFLINE,
            latitude=40.7128,
            longitude=-74.0060
        )
        device.id = uuid.uuid4()
        device.created_at = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)
        device.last_seen = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        # Test update_last_seen
        old_time = device.last_seen
        device.update_last_seen()
        assert device.last_seen > old_time
        results.add_pass("Device update_last_seen")
        
        # Test update_heartbeat
        device.update_heartbeat()
        assert device.last_heartbeat is not None
        assert device.status == DeviceStatus.ONLINE
        results.add_pass("Device update_heartbeat")
        
        # Test distance calculation
        device2 = Device(
            name="Device 2",
            latitude=34.0522,
            longitude=-118.2437
        )
        device2.id = uuid.uuid4()
        device2.created_at = datetime.now(timezone.utc)
        device2.updated_at = datetime.now(timezone.utc)
        
        distance = device.calculate_distance_to(device2)
        assert distance is not None
        assert distance > 3000
        results.add_pass("Device distance calculation")
        
    except Exception as e:
        results.add_fail("Device business logic", str(e))
    
    try:
        # Test TelemetryEvent business methods
        telemetry = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="test_event",
            numeric_value=42.0,
            data={"temperature": 25.5, "humidity": 60.0}
        )
        telemetry.id = uuid.uuid4()
        telemetry.timestamp = datetime.now(timezone.utc)
        telemetry.received_at = datetime.now(timezone.utc)
        telemetry.created_at = datetime.now(timezone.utc)
        telemetry.updated_at = datetime.now(timezone.utc)
        
        # Test mark_processed
        telemetry.mark_processed(duration_ms=150)
        assert telemetry.processed is True
        assert telemetry.processed_at is not None
        results.add_pass("TelemetryEvent mark_processed")
        
        # Test data field methods
        assert telemetry.get_data_field("temperature") == 25.5
        assert telemetry.get_data_field("nonexistent", "default") == "default"
        results.add_pass("TelemetryEvent data field methods")
        
    except Exception as e:
        results.add_fail("TelemetryEvent business logic", str(e))
    
    return results.summary()


async def test_database_operations_fixed():
    """Test database operations with real database."""
    print("🔍 Testing Database Operations (Fixed)...")
    results = TestResults()
    
    try:
        # Create in-memory database
        config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            enable_health_checks=False
        )
        manager = DatabaseManager(config)
        await manager.initialize()
        
        # Create tables
        from edge_device_fleet_manager.persistence.models.base import Base
        async with manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        results.add_pass("Database setup")
        
        # Test repository operations
        async with manager.get_transaction() as session:
            device_repo = DeviceRepository(session)
            
            # Create device
            device_data = {
                "name": "Test Device",
                "device_type": DeviceType.SENSOR,
                "status": DeviceStatus.ONLINE,
                "ip_address": "192.168.1.100"
            }
            
            device = await device_repo.create(device_data)
            assert device.name == "Test Device"
            results.add_pass("Device repository create")
            
            # Get device
            retrieved_device = await device_repo.get(device.id)
            assert retrieved_device is not None
            assert retrieved_device.name == "Test Device"
            results.add_pass("Device repository get")
            
            # Update device
            updated_device = await device_repo.update(
                device.id,
                {"name": "Updated Device", "health_score": 0.9}
            )
            assert updated_device.name == "Updated Device"
            results.add_pass("Device repository update")
            
            # Count devices
            count = await device_repo.count()
            assert count == 1
            results.add_pass("Device repository count")
            
            # Test device-specific methods
            device_by_ip = await device_repo.get_by_ip_address("192.168.1.100")
            assert device_by_ip is not None
            results.add_pass("Device repository get_by_ip_address")
            
            online_devices = await device_repo.get_online_devices()
            assert len(online_devices) == 1
            results.add_pass("Device repository get_online_devices")
        
        await manager.shutdown()
        results.add_pass("Database cleanup")
        
    except Exception as e:
        results.add_fail("Database operations", str(e))
    
    return results.summary()


async def test_configuration_comprehensive():
    """Test comprehensive configuration functionality."""
    print("🔍 Testing Configuration (Comprehensive)...")
    results = TestResults()
    
    try:
        # Test default configuration
        config = DatabaseConfig()
        assert config.database_url is not None
        assert config.pool_size > 0
        results.add_pass("Default configuration")
        
        # Test custom configuration
        custom_config = DatabaseConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            pool_size=5,
            max_overflow=10,
            enable_health_checks=True
        )
        assert custom_config.pool_size == 5
        results.add_pass("Custom configuration")
        
        # Test validation
        errors = custom_config.validate()
        assert len(errors) == 0
        results.add_pass("Configuration validation")
        
        # Test invalid configuration
        invalid_config = DatabaseConfig(
            database_url="",
            pool_size=-1,
            max_overflow=-5
        )
        errors = invalid_config.validate()
        assert len(errors) > 0
        results.add_pass("Invalid configuration detection")
        
        # Test configuration methods
        assert custom_config.is_sqlite() is True
        assert custom_config.get_database_type() == "sqlite"
        results.add_pass("Configuration utility methods")
        
        # Test configuration serialization
        config_dict = custom_config.to_dict()
        assert 'database_url' in config_dict
        assert 'pool_size' in config_dict
        results.add_pass("Configuration serialization")
        
    except Exception as e:
        results.add_fail("Configuration tests", str(e))
    
    return results.summary()


async def run_all_fixed_tests():
    """Run all fixed tests."""
    print("🚀 Starting Comprehensive Fixed Test Suite for Feature 5")
    print("=" * 70)
    
    tests = [
        ("Model Creation", test_model_creation_fixed),
        ("Model Validation", test_model_validation_fixed),
        ("Model Business Logic", test_model_business_logic_fixed),
        ("Database Operations", test_database_operations_fixed),
        ("Configuration", test_configuration_comprehensive),
    ]
    
    overall_success = True
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            start_time = time.time()
            success = await test_func()
            duration = time.time() - start_time
            
            if success:
                print(f"✅ {test_name} PASSED ({duration:.3f}s)")
            else:
                print(f"❌ {test_name} FAILED ({duration:.3f}s)")
                overall_success = False
        
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            overall_success = False
    
    print("\n" + "=" * 70)
    if overall_success:
        print("🎉 ALL FIXED TESTS PASSED! Feature 5 is working correctly.")
        print("\n💡 Working commands for Feature 5:")
        print("   python test_persistence_comprehensive_fixed.py")
        print("   python test_persistence_feature5_simple.py")
        print("   python test_persistence_working.py")
        print("   python benchmark_persistence_performance.py")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(run_all_fixed_tests())
    sys.exit(0 if success else 1)
