#!/usr/bin/env python3
"""
Comprehensive integration test for Feature 5: Robust Persistence & Migrations.

This script tests the complete persistence system including:
- SQLAlchemy models with validation and relationships
- Repository pattern with async operations
- Database connection management and pooling
- Migration system with Alembic integration
- Health monitoring and error handling
- End-to-end persistence workflows
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
    TelemetryEvent, TelemetryType, TelemetryData
)
from edge_device_fleet_manager.persistence.models.analytics import (
    Analytics, AnalyticsType, AnalyticsMetric
)
from edge_device_fleet_manager.persistence.models.user import (
    User, UserRole, UserStatus
)
from edge_device_fleet_manager.persistence.models.alert import (
    Alert, AlertSeverity, AlertStatus
)
from edge_device_fleet_manager.persistence.models.audit_log import (
    AuditLog, AuditAction, AuditResource
)
from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
from edge_device_fleet_manager.persistence.connection.health import HealthChecker
from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
from edge_device_fleet_manager.persistence.migrations.manager import MigrationManager


async def test_model_creation_and_validation():
    """Test model creation and validation."""
    print("🔍 Testing Model Creation and Validation...")
    
    # Test Device model
    device = Device(
        name="Test Device",
        device_type=DeviceType.SENSOR,
        status=DeviceStatus.ONLINE,
        ip_address="192.168.1.100",
        health_score=0.85,
        battery_level=75.0
    )
    
    assert device.name == "Test Device"
    assert device.device_type == DeviceType.SENSOR
    assert device.status == DeviceStatus.ONLINE
    assert device.is_online is True
    assert device.is_healthy is True
    assert device.id is not None
    
    # Test validation
    try:
        device.health_score = 1.5  # Should fail
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Health score must be between 0.0 and 1.0" in str(e)
    
    # Test TelemetryEvent model
    telemetry = TelemetryEvent(
        device_id=device.id,
        event_type=TelemetryType.SENSOR_DATA,
        event_name="temperature_reading",
        numeric_value=25.5,
        units="celsius",
        data={"sensor_id": "temp_01", "location": "room_1"}
    )
    
    assert telemetry.device_id == device.id
    assert telemetry.event_type == TelemetryType.SENSOR_DATA
    assert telemetry.extract_numeric_value() == 25.5
    assert telemetry.get_data_field("sensor_id") == "temp_01"
    
    # Test Analytics model
    analytics = Analytics(
        analytics_type=AnalyticsType.DEVICE_METRICS,
        metric_name="average_temperature",
        metric_type=AnalyticsMetric.AVERAGE,
        period_start=datetime.now(timezone.utc) - timedelta(hours=1),
        period_end=datetime.now(timezone.utc),
        granularity="hourly",
        scope="device",
        numeric_value=25.5,
        avg_value=25.5,
        min_value=20.0,
        max_value=30.0
    )
    
    assert analytics.get_primary_value() == 25.5
    assert analytics.has_statistical_data is True
    
    # Test User model
    user = User(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.OPERATOR
    )
    
    user.set_password("testpassword123")
    assert user.check_password("testpassword123") is True
    assert user.check_password("wrongpassword") is False
    assert user.has_permission("devices.read") is True
    assert user.has_permission("users.delete") is False
    
    # Test Alert model
    alert = Alert(
        title="High Temperature Alert",
        description="Temperature exceeded threshold",
        alert_type="temperature_threshold",
        severity=AlertSeverity.HIGH,
        device_id=device.id
    )
    
    assert alert.is_open is True
    assert alert.is_critical is False
    
    user_id = str(uuid.uuid4())
    alert.acknowledge(user_id)
    assert alert.status == AlertStatus.ACKNOWLEDGED
    assert alert.acknowledged_by_user_id == user_id
    
    # Test AuditLog model
    audit_log = AuditLog.create_log(
        action=AuditAction.CREATE,
        resource_type=AuditResource.DEVICE,
        user_id=user.id,
        resource_id=str(device.id),
        description="Created new device"
    )
    
    assert audit_log.action == AuditAction.CREATE
    assert audit_log.resource_type == AuditResource.DEVICE
    assert audit_log.success is True
    
    print("✅ Model creation and validation tests passed")
    return True


async def test_database_configuration():
    """Test database configuration system."""
    print("🔍 Testing Database Configuration...")
    
    # Test default configuration
    config = DatabaseConfig()
    assert config.database_url is not None
    assert config.pool_size > 0
    assert config.max_overflow >= 0
    
    # Test configuration validation
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
    
    # Test configuration methods
    assert config.is_sqlite() or config.is_postgresql() or config.is_mysql()
    db_type = config.get_database_type()
    assert db_type in ['sqlite', 'postgresql', 'mysql']
    
    config_dict = config.to_dict()
    assert 'database_url' in config_dict
    assert 'pool_size' in config_dict
    
    print("✅ Database configuration tests passed")
    return True


async def test_database_connection_management():
    """Test database connection management."""
    print("🔍 Testing Database Connection Management...")
    
    # Create test configuration
    config = DatabaseConfig(
        database_url="sqlite+aiosqlite:///:memory:",
        pool_size=2,
        max_overflow=5,
        enable_health_checks=True,
        health_check_interval=1
    )
    
    # Test database manager
    manager = DatabaseManager(config)
    
    assert manager.config == config
    assert manager._is_initialized is False
    
    # Initialize manager
    await manager.initialize()
    assert manager._is_initialized is True
    assert manager.engine is not None
    assert manager.session_factory is not None
    
    # Test connection check
    is_healthy = await manager.check_connection()
    assert is_healthy is True
    
    # Test session management
    async with manager.get_session() as session:
        assert session is not None
        # Test basic query
        result = await manager.execute_query("SELECT 1")
        assert result is not None
    
    # Test transaction management
    async with manager.get_transaction() as session:
        assert session is not None
    
    # Test connection info
    info = await manager.get_connection_info()
    assert info['is_initialized'] is True
    assert 'connection_count' in info
    
    # Test statistics
    stats = await manager.get_statistics()
    assert 'connections' in stats
    assert 'configuration' in stats
    
    # Test health checker
    if manager.health_checker:
        health_status = await manager.health_checker.get_status()
        assert 'is_healthy' in health_status
        assert 'metrics' in health_status
    
    # Shutdown manager
    await manager.shutdown()
    assert manager._is_initialized is False
    
    print("✅ Database connection management tests passed")
    return True


async def test_health_monitoring():
    """Test database health monitoring."""
    print("🔍 Testing Health Monitoring...")
    
    # Create mock engine for testing
    from unittest.mock import AsyncMock, MagicMock
    
    mock_engine = MagicMock()
    mock_engine.begin = AsyncMock()
    
    # Create health checker
    health_checker = HealthChecker(
        mock_engine,
        check_interval=1,
        timeout=5,
        failure_threshold=2
    )
    
    assert health_checker.is_healthy() is True
    assert health_checker._is_running is False
    
    # Test health check metrics
    status = await health_checker.get_status()
    assert status['is_healthy'] is True
    assert status['is_monitoring'] is False
    assert 'metrics' in status
    
    # Test statistics
    stats = await health_checker.get_statistics()
    assert 'success_rate' in stats
    assert 'failure_rate' in stats
    
    # Test callback system
    callback_called = False
    callback_args = None
    
    async def test_callback(is_healthy, metrics):
        nonlocal callback_called, callback_args
        callback_called = True
        callback_args = (is_healthy, metrics)
    
    health_checker.add_callback(test_callback)
    
    # Test health summary
    summary = health_checker.get_health_summary()
    assert "Status:" in summary
    assert "HEALTHY" in summary
    
    print("✅ Health monitoring tests passed")
    return True


async def test_repository_operations():
    """Test repository pattern operations."""
    print("🔍 Testing Repository Operations...")
    
    # Create in-memory database for testing
    config = DatabaseConfig(database_url="sqlite+aiosqlite:///:memory:")
    manager = DatabaseManager(config)
    await manager.initialize()
    
    # Create tables (simplified for testing)
    from edge_device_fleet_manager.persistence.models.base import Base
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Test device repository
    async with manager.get_session() as session:
        device_repo = DeviceRepository(session)
        
        # Test create
        device_data = {
            "name": "Test Device",
            "device_type": DeviceType.SENSOR,
            "status": DeviceStatus.ONLINE,
            "ip_address": "192.168.1.100"
        }
        
        device = await device_repo.create(device_data)
        assert device.name == "Test Device"
        assert device.id is not None
        
        # Test get
        retrieved_device = await device_repo.get(device.id)
        assert retrieved_device is not None
        assert retrieved_device.name == "Test Device"
        
        # Test update
        updated_device = await device_repo.update(
            device.id,
            {"name": "Updated Device", "health_score": 0.9}
        )
        assert updated_device.name == "Updated Device"
        assert updated_device.health_score == 0.9
        
        # Test count
        count = await device_repo.count()
        assert count == 1
        
        # Test exists
        exists = await device_repo.exists(device.id)
        assert exists is True
        
        # Test get_multi
        devices = await device_repo.get_multi(limit=10)
        assert len(devices) == 1
        
        # Test device-specific methods
        device_by_ip = await device_repo.get_by_ip_address("192.168.1.100")
        assert device_by_ip is not None
        assert device_by_ip.id == device.id
        
        online_devices = await device_repo.get_online_devices()
        assert len(online_devices) == 1
        
        # Test bulk operations
        bulk_data = [
            {"name": f"Bulk Device {i}", "device_type": DeviceType.SENSOR}
            for i in range(3)
        ]
        bulk_devices = await device_repo.bulk_create(bulk_data)
        assert len(bulk_devices) == 3
        
        # Test search
        search_results = await device_repo.search_devices("Bulk")
        assert len(search_results) == 3
        
        # Test statistics
        stats = await device_repo.get_statistics()
        assert stats['total_devices'] == 4  # 1 original + 3 bulk
        assert 'status_distribution' in stats
        
        # Commit the session
        await session.commit()
    
    await manager.shutdown()
    
    print("✅ Repository operations tests passed")
    return True


async def test_migration_system():
    """Test migration system functionality."""
    print("🔍 Testing Migration System...")
    
    # Create temporary database for migration testing
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        database_url = f"sqlite:///{db_path}"
        
        # Test migration manager
        migration_manager = MigrationManager(database_url)
        
        assert migration_manager.database_url == database_url
        assert migration_manager.engine is not None
        
        # Test schema validation (on empty database)
        is_valid, issues = migration_manager.validate_schema()
        assert is_valid is False  # Empty database should have issues
        assert len(issues) > 0
        
        # Test table creation
        migration_manager.create_tables()
        
        # Test schema validation after table creation
        is_valid, issues = migration_manager.validate_schema()
        assert is_valid is True  # Should be valid now
        assert len(issues) == 0
        
        # Test migration status
        status = migration_manager.get_migration_status()
        assert 'current_revision' in status
        assert 'schema_valid' in status
        assert status['schema_valid'] is True
        
        # Test connection check
        connection_ok = await migration_manager.check_connection()
        assert connection_ok is True
        
    finally:
        # Clean up temporary database
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    print("✅ Migration system tests passed")
    return True


async def test_end_to_end_workflow():
    """Test end-to-end persistence workflow."""
    print("🔍 Testing End-to-End Workflow...")
    
    # Create complete persistence stack
    config = DatabaseConfig(
        database_url="sqlite+aiosqlite:///:memory:",
        enable_health_checks=False  # Disable for testing
    )
    
    manager = DatabaseManager(config)
    await manager.initialize()
    
    # Create schema
    from edge_device_fleet_manager.persistence.models.base import Base
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Complete workflow: Create user, device, telemetry, analytics, alert, audit
    async with manager.get_transaction() as session:
        device_repo = DeviceRepository(session)
        
        # 1. Create a device
        device = await device_repo.create({
            "name": "Workflow Test Device",
            "device_type": DeviceType.SENSOR,
            "status": DeviceStatus.ONLINE,
            "ip_address": "192.168.1.200",
            "health_score": 0.95
        })
        
        # 2. Create telemetry events
        telemetry_events = []
        for i in range(5):
            telemetry = TelemetryEvent(
                device_id=device.id,
                event_type=TelemetryType.SENSOR_DATA,
                event_name="temperature_reading",
                numeric_value=20.0 + i,
                units="celsius"
            )
            session.add(telemetry)
            telemetry_events.append(telemetry)
        
        await session.flush()
        
        # 3. Create analytics based on telemetry
        analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="average_temperature",
            metric_type=AnalyticsMetric.AVERAGE,
            period_start=datetime.now(timezone.utc) - timedelta(hours=1),
            period_end=datetime.now(timezone.utc),
            granularity="hourly",
            scope="device",
            device_id=device.id,
            avg_value=22.0,
            min_value=20.0,
            max_value=24.0,
            sample_count=5
        )
        session.add(analytics)
        
        # 4. Create an alert
        alert = Alert(
            title="Temperature Monitoring Alert",
            description="Regular temperature monitoring alert",
            alert_type="monitoring",
            severity=AlertSeverity.INFO,
            device_id=device.id
        )
        session.add(alert)
        
        # 5. Create audit log
        audit_log = AuditLog.create_log(
            action=AuditAction.CREATE,
            resource_type=AuditResource.DEVICE,
            resource_id=str(device.id),
            description="Created device in workflow test"
        )
        session.add(audit_log)
        
        await session.flush()
    
    # Verify the complete workflow
    async with manager.get_session() as session:
        device_repo = DeviceRepository(session)
        
        # Verify device exists
        device = await device_repo.get_by_ip_address("192.168.1.200")
        assert device is not None
        assert device.name == "Workflow Test Device"
        
        # Verify statistics
        stats = await device_repo.get_statistics()
        assert stats['total_devices'] >= 1
    
    await manager.shutdown()
    
    print("✅ End-to-end workflow tests passed")
    return True


async def run_all_tests():
    """Run all persistence system tests."""
    print("🚀 Starting Feature 5: Robust Persistence & Migrations Tests")
    print("=" * 70)
    
    tests = [
        test_model_creation_and_validation,
        test_database_configuration,
        test_database_connection_management,
        test_health_monitoring,
        test_repository_operations,
        test_migration_system,
        test_end_to_end_workflow,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            start_time = time.time()
            result = await test()
            duration = time.time() - start_time
            
            if result:
                passed += 1
                print(f"  ⏱️  Completed in {duration:.3f}s")
            else:
                failed += 1
                print(f"  ❌ Test failed")
        
        except Exception as e:
            failed += 1
            print(f"  ❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 70)
    print(f"🎯 Summary: {passed}/{len(tests)} tests passed")
    
    if failed == 0:
        print("🎉 All persistence tests passed! Feature 5 is working correctly.")
        return True
    else:
        print(f"❌ {failed} tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
