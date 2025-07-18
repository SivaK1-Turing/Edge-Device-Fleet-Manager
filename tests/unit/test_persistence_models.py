"""
Unit tests for persistence models.

Tests the SQLAlchemy models including validation, relationships,
business logic methods, and database constraints.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

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
from edge_device_fleet_manager.persistence.models.device_group import (
    DeviceGroup
)
from edge_device_fleet_manager.persistence.models.alert import (
    Alert, AlertSeverity, AlertStatus
)
from edge_device_fleet_manager.persistence.models.audit_log import (
    AuditLog, AuditAction, AuditResource
)


class TestDeviceModel:
    """Test Device model functionality."""
    
    def test_device_creation(self):
        """Test device creation with basic attributes."""
        device = Device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE,
            ip_address="192.168.1.100",
            mac_address="00:11:22:33:44:55"
        )
        
        assert device.name == "Test Device"
        assert device.device_type == DeviceType.SENSOR
        assert device.status == DeviceStatus.ONLINE
        assert device.ip_address == "192.168.1.100"
        assert device.mac_address == "00:11:22:33:44:55"
        assert device.id is not None
        assert device.created_at is not None
        assert device.updated_at is not None
    
    def test_device_validation(self):
        """Test device field validation."""
        device = Device(name="Test Device")
        
        # Test health score validation
        with pytest.raises(ValueError, match="Health score must be between 0.0 and 1.0"):
            device.health_score = 1.5
        
        with pytest.raises(ValueError, match="Health score must be between 0.0 and 1.0"):
            device.health_score = -0.1
        
        # Test battery level validation
        with pytest.raises(ValueError, match="Battery level must be between 0.0 and 100.0"):
            device.battery_level = 150.0
        
        with pytest.raises(ValueError, match="Battery level must be between 0.0 and 100.0"):
            device.battery_level = -10.0
        
        # Test port validation
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            device.port = 0
        
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            device.port = 70000
    
    def test_device_hybrid_properties(self):
        """Test device hybrid properties."""
        device = Device(
            name="Test Device",
            status=DeviceStatus.ONLINE,
            health_score=0.8,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        assert device.is_online is True
        assert device.is_healthy is True
        assert device.has_location is True
        
        # Test offline device
        device.status = DeviceStatus.OFFLINE
        assert device.is_online is False
        
        # Test unhealthy device
        device.health_score = 0.5
        assert device.is_healthy is False
        
        # Test device without location
        device.latitude = None
        assert device.has_location is False
    
    def test_device_business_methods(self):
        """Test device business logic methods."""
        device = Device(name="Test Device", status=DeviceStatus.OFFLINE)
        
        # Test update_last_seen
        old_time = device.last_seen
        device.update_last_seen()
        assert device.last_seen > old_time if old_time else True
        
        # Test update_heartbeat
        device.update_heartbeat()
        assert device.last_heartbeat is not None
        assert device.status == DeviceStatus.ONLINE
        
        # Test set_offline
        device.set_offline()
        assert device.status == DeviceStatus.OFFLINE
    
    def test_device_distance_calculation(self):
        """Test distance calculation between devices."""
        device1 = Device(
            name="Device 1",
            latitude=40.7128,  # New York
            longitude=-74.0060
        )
        
        device2 = Device(
            name="Device 2",
            latitude=34.0522,  # Los Angeles
            longitude=-118.2437
        )
        
        distance = device1.calculate_distance_to(device2)
        assert distance is not None
        assert distance > 3000  # Should be roughly 3944 km
        assert distance < 5000
        
        # Test with device without coordinates
        device3 = Device(name="Device 3")
        distance = device1.calculate_distance_to(device3)
        assert distance is None
    
    def test_device_to_dict(self):
        """Test device serialization to dictionary."""
        device = Device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE,
            health_score=0.85
        )
        
        device_dict = device.to_dict()
        
        assert device_dict['name'] == "Test Device"
        assert device_dict['device_type'] == DeviceType.SENSOR
        assert device_dict['status'] == DeviceStatus.ONLINE
        assert device_dict['health_score'] == 0.85
        assert 'id' in device_dict
        assert 'created_at' in device_dict


class TestTelemetryEventModel:
    """Test TelemetryEvent model functionality."""
    
    def test_telemetry_event_creation(self):
        """Test telemetry event creation."""
        device_id = uuid.uuid4()
        
        event = TelemetryEvent(
            device_id=device_id,
            event_type=TelemetryType.SENSOR_DATA,
            event_name="temperature_reading",
            numeric_value=25.5,
            units="celsius"
        )
        
        assert event.device_id == device_id
        assert event.event_type == TelemetryType.SENSOR_DATA
        assert event.event_name == "temperature_reading"
        assert event.numeric_value == 25.5
        assert event.units == "celsius"
        assert event.timestamp is not None
        assert event.received_at is not None
    
    def test_telemetry_validation(self):
        """Test telemetry event validation."""
        event = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="test_event"
        )
        
        # Test quality score validation
        with pytest.raises(ValueError, match="Quality score must be between 0.0 and 1.0"):
            event.quality_score = 1.5
        
        # Test confidence level validation
        with pytest.raises(ValueError, match="Confidence level must be between 0.0 and 1.0"):
            event.confidence_level = -0.1
        
        # Test processing duration validation
        with pytest.raises(ValueError, match="Processing duration must be non-negative"):
            event.processing_duration_ms = -100
    
    def test_telemetry_hybrid_properties(self):
        """Test telemetry event hybrid properties."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=2)
        
        event = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="test_event",
            timestamp=old_time,
            error_code="E001"
        )
        
        assert event.is_recent is False
        assert event.has_error is True
        
        # Test recent event
        event.timestamp = now
        assert event.is_recent is True
        
        # Test processing latency
        event.received_at = now + timedelta(milliseconds=500)
        latency = event.processing_latency_ms
        assert latency == 500
    
    def test_telemetry_business_methods(self):
        """Test telemetry event business methods."""
        event = TelemetryEvent(
            device_id=uuid.uuid4(),
            event_type=TelemetryType.SENSOR_DATA,
            event_name="test_event",
            numeric_value=42.0,
            data={"temperature": 25.5, "humidity": 60.0}
        )
        
        # Test mark_processed
        event.mark_processed(duration_ms=150)
        assert event.processed is True
        assert event.processed_at is not None
        assert event.processing_duration_ms == 150
        
        # Test extract_numeric_value
        assert event.extract_numeric_value() == 42.0
        
        # Test data field methods
        assert event.get_data_field("temperature") == 25.5
        assert event.get_data_field("nonexistent", "default") == "default"
        
        event.set_data_field("pressure", 1013.25)
        assert event.data["pressure"] == 1013.25
        
        # Test to_time_series_point
        ts_point = event.to_time_series_point()
        assert ts_point["value"] == 42.0
        assert ts_point["event_name"] == "test_event"


class TestTelemetryData:
    """Test TelemetryData helper class."""
    
    def test_telemetry_data_properties(self):
        """Test telemetry data property access."""
        data = TelemetryData({
            "temperature": 25.5,
            "humidity": 60.0,
            "cpu_usage": 75.2,
            "voltage": 3.3
        })
        
        assert data.temperature == 25.5
        assert data.humidity == 60.0
        assert data.cpu_usage == 75.2
        assert data.voltage == 3.3
        assert data.pressure is None  # Not in data
    
    def test_telemetry_data_methods(self):
        """Test telemetry data methods."""
        data = TelemetryData({"test_field": "test_value"})
        
        assert data.get("test_field") == "test_value"
        assert data.get("nonexistent", "default") == "default"
        
        data.set("new_field", "new_value")
        assert data.data["new_field"] == "new_value"
        
        data_dict = data.to_dict()
        assert data_dict["test_field"] == "test_value"
        assert data_dict["new_field"] == "new_value"


class TestAnalyticsModel:
    """Test Analytics model functionality."""
    
    def test_analytics_creation(self):
        """Test analytics creation."""
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
        
        assert analytics.analytics_type == AnalyticsType.DEVICE_METRICS
        assert analytics.metric_name == "average_temperature"
        assert analytics.metric_type == AnalyticsMetric.AVERAGE
        assert analytics.granularity == "hourly"
        assert analytics.scope == "device"
        assert analytics.numeric_value == 25.5
    
    def test_analytics_validation(self):
        """Test analytics validation."""
        analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="test_metric",
            metric_type=AnalyticsMetric.COUNT,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            granularity="hourly",
            scope="global"
        )
        
        # Test percentage validation
        with pytest.raises(ValueError, match="Percentage value must be between 0.0 and 100.0"):
            analytics.percentage_value = 150.0
        
        # Test confidence validation
        with pytest.raises(ValueError, match="Confidence level must be between 0.0 and 1.0"):
            analytics.confidence_level = 1.5
        
        # Test quality score validation
        with pytest.raises(ValueError, match="Data quality score must be between 0.0 and 1.0"):
            analytics.data_quality_score = -0.1
    
    def test_analytics_hybrid_properties(self):
        """Test analytics hybrid properties."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="test_metric",
            metric_type=AnalyticsMetric.AVERAGE,
            period_start=start_time,
            period_end=end_time,
            granularity="hourly",
            scope="global",
            min_value=10.0,
            max_value=30.0,
            avg_value=20.0
        )
        
        assert analytics.period_duration_seconds == 3600  # 1 hour
        assert analytics.is_recent is True
        assert analytics.has_statistical_data is True
    
    def test_analytics_business_methods(self):
        """Test analytics business methods."""
        analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="test_metric",
            metric_type=AnalyticsMetric.AVERAGE,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            granularity="hourly",
            scope="global",
            avg_value=25.0,
            detailed_data={"breakdown": {"sensor1": 20.0, "sensor2": 30.0}}
        )
        
        # Test get_primary_value
        assert analytics.get_primary_value() == 25.0
        
        # Test detailed data methods
        assert analytics.get_detailed_field("breakdown") == {"sensor1": 20.0, "sensor2": 30.0}
        assert analytics.get_detailed_field("nonexistent", "default") == "default"
        
        analytics.set_detailed_field("new_field", "new_value")
        assert analytics.detailed_data["new_field"] == "new_value"
        
        # Test calculate_trend
        previous_analytics = Analytics(
            analytics_type=AnalyticsType.DEVICE_METRICS,
            metric_name="test_metric",
            metric_type=AnalyticsMetric.AVERAGE,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            granularity="hourly",
            scope="global",
            avg_value=20.0
        )
        
        trend = analytics.calculate_trend(previous_analytics)
        assert trend == 25.0  # 25% increase
        
        # Test to_chart_data
        chart_data = analytics.to_chart_data()
        assert chart_data["metric"] == "test_metric"
        assert chart_data["value"] == 25.0


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test user creation."""
        user = User(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role=UserRole.OPERATOR
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.role == UserRole.OPERATOR
        assert user.status == UserStatus.PENDING_ACTIVATION
    
    def test_user_validation(self):
        """Test user validation."""
        user = User(username="testuser")
        
        # Test email validation
        with pytest.raises(ValueError, match="Invalid email format"):
            user.email = "invalid-email"
        
        # Test failed login attempts validation
        with pytest.raises(ValueError, match="Failed login attempts must be non-negative"):
            user.failed_login_attempts = -1
    
    def test_user_hybrid_properties(self):
        """Test user hybrid properties."""
        user = User(
            username="testuser",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        
        assert user.full_name == "John Doe"
        assert user.is_active is True
        assert user.is_locked is False
        assert user.has_admin_role is True
        
        # Test locked user
        user.status = UserStatus.LOCKED
        assert user.is_locked is True
        
        # Test user with only first name
        user.last_name = None
        assert user.full_name == "John"
    
    def test_user_password_methods(self):
        """Test user password methods."""
        user = User(username="testuser", email="test@example.com")
        
        # Test set_password
        user.set_password("testpassword123")
        assert user.password_hash is not None
        assert user.salt is not None
        
        # Test check_password
        assert user.check_password("testpassword123") is True
        assert user.check_password("wrongpassword") is False
    
    def test_user_login_methods(self):
        """Test user login tracking methods."""
        user = User(
            username="testuser",
            email="test@example.com",
            failed_login_attempts=2
        )
        
        # Test record_login
        user.record_login("192.168.1.100")
        assert user.last_login is not None
        assert user.last_login_ip == "192.168.1.100"
        assert user.failed_login_attempts == 0
        
        # Test record_failed_login
        user.record_failed_login(max_attempts=3)
        assert user.failed_login_attempts == 1
        
        user.record_failed_login(max_attempts=3)
        user.record_failed_login(max_attempts=3)
        assert user.status == UserStatus.LOCKED
        assert user.locked_until is not None
        
        # Test unlock_account
        user.unlock_account()
        assert user.status == UserStatus.ACTIVE
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_user_permissions(self):
        """Test user permission system."""
        # Test admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN
        )
        
        assert admin_user.has_permission("devices.create") is True
        assert admin_user.has_permission("users.delete") is True
        
        # Test viewer user
        viewer_user = User(
            username="viewer",
            email="viewer@example.com",
            role=UserRole.VIEWER
        )
        
        assert viewer_user.has_permission("devices.read") is True
        assert viewer_user.has_permission("devices.create") is False
        
        # Test super admin
        super_admin = User(
            username="superadmin",
            email="superadmin@example.com",
            role=UserRole.SUPER_ADMIN
        )
        
        assert super_admin.has_permission("anything") is True


class TestDeviceGroupModel:
    """Test DeviceGroup model functionality."""
    
    def test_device_group_creation(self):
        """Test device group creation."""
        group = DeviceGroup(
            name="Test Group",
            description="A test device group",
            group_type="sensor_group"
        )
        
        assert group.name == "Test Group"
        assert group.description == "A test device group"
        assert group.group_type == "sensor_group"
        assert group.device_count == 0
        assert group.active_device_count == 0
        assert group.is_dynamic is False
    
    def test_device_group_validation(self):
        """Test device group validation."""
        group = DeviceGroup(name="Test Group")
        
        # Test device count validation
        with pytest.raises(ValueError, match="Device count must be non-negative"):
            group.device_count = -1
        
        # Test active device count validation
        with pytest.raises(ValueError, match="Active device count must be non-negative"):
            group.active_device_count = -1
        
        group.device_count = 10
        with pytest.raises(ValueError, match="Active device count cannot exceed total device count"):
            group.active_device_count = 15
    
    def test_device_group_hybrid_properties(self):
        """Test device group hybrid properties."""
        group = DeviceGroup(
            name="Test Group",
            device_count=10,
            active_device_count=8
        )
        
        assert group.is_root_group is True
        assert group.has_devices is True
        assert group.activity_ratio == 0.8
        
        # Test group with parent
        group.parent_group_id = uuid.uuid4()
        assert group.is_root_group is False
        
        # Test empty group
        group.device_count = 0
        group.active_device_count = 0
        assert group.has_devices is False
        assert group.activity_ratio is None


class TestAlertModel:
    """Test Alert model functionality."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            title="Test Alert",
            description="A test alert",
            alert_type="system_error",
            severity=AlertSeverity.HIGH,
            device_id=uuid.uuid4()
        )
        
        assert alert.title == "Test Alert"
        assert alert.description == "A test alert"
        assert alert.alert_type == "system_error"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.OPEN
        assert alert.occurrence_count == 1
    
    def test_alert_validation(self):
        """Test alert validation."""
        alert = Alert(title="Test Alert", alert_type="test")
        
        # Test priority validation
        with pytest.raises(ValueError, match="Priority must be between 0 and 100"):
            alert.priority = 150
        
        # Test occurrence count validation
        with pytest.raises(ValueError, match="Occurrence count must be at least 1"):
            alert.occurrence_count = 0
    
    def test_alert_hybrid_properties(self):
        """Test alert hybrid properties."""
        alert = Alert(
            title="Test Alert",
            alert_type="test",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            occurrence_count=3
        )
        
        assert alert.is_open is True
        assert alert.is_critical is True
        assert alert.is_recurring is True
        assert alert.duration_minutes >= 0
        
        # Test resolved alert
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        assert alert.is_open is False
    
    def test_alert_business_methods(self):
        """Test alert business methods."""
        alert = Alert(
            title="Test Alert",
            alert_type="test",
            status=AlertStatus.OPEN
        )
        
        user_id = str(uuid.uuid4())
        
        # Test acknowledge
        alert.acknowledge(user_id)
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None
        assert alert.acknowledged_by_user_id == user_id
        
        # Test assign_to
        alert.assign_to(user_id)
        assert alert.assigned_to_user_id == user_id
        
        # Test start_progress
        alert.start_progress(user_id)
        assert alert.status == AlertStatus.IN_PROGRESS
        
        # Test resolve
        alert.resolve(user_id, "Fixed the issue", "Restarted service")
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
        assert alert.resolved_by_user_id == user_id
        assert alert.resolution_notes == "Fixed the issue"
        assert alert.resolution_action == "Restarted service"
        
        # Test record_occurrence
        old_count = alert.occurrence_count
        alert.record_occurrence()
        assert alert.occurrence_count == old_count + 1
        assert alert.status == AlertStatus.OPEN  # Should reopen


class TestAuditLogModel:
    """Test AuditLog model functionality."""
    
    def test_audit_log_creation(self):
        """Test audit log creation."""
        log = AuditLog(
            action=AuditAction.CREATE,
            resource_type=AuditResource.DEVICE,
            resource_id="device-123",
            user_id=uuid.uuid4(),
            description="Created new device"
        )
        
        assert log.action == AuditAction.CREATE
        assert log.resource_type == AuditResource.DEVICE
        assert log.resource_id == "device-123"
        assert log.description == "Created new device"
        assert log.success is True
        assert log.timestamp is not None
    
    def test_audit_log_validation(self):
        """Test audit log validation."""
        log = AuditLog(
            action=AuditAction.READ,
            resource_type=AuditResource.DEVICE
        )
        
        # Test duration validation
        with pytest.raises(ValueError, match="Duration must be non-negative"):
            log.duration_ms = -100
        
        # Test retention period validation
        with pytest.raises(ValueError, match="Retention period must be positive"):
            log.retention_period_days = 0
    
    def test_audit_log_hybrid_properties(self):
        """Test audit log hybrid properties."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=2)
        
        log = AuditLog(
            action=AuditAction.LOGIN,
            resource_type=AuditResource.USER,
            timestamp=old_time,
            success=False,
            old_values={"status": "active"},
            new_values={"status": "locked"}
        )
        
        assert log.is_recent is False
        assert log.is_security_relevant is True  # Failed login
        assert log.has_changes is True
        
        # Test recent log
        log.timestamp = now
        assert log.is_recent is True
    
    def test_audit_log_business_methods(self):
        """Test audit log business methods."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            resource_type=AuditResource.DEVICE,
            details={"field": "status"},
            old_values={"status": "offline"},
            new_values={"status": "online"}
        )
        
        # Test detail methods
        assert log.get_detail("field") == "status"
        assert log.get_detail("nonexistent", "default") == "default"
        
        log.set_detail("new_field", "new_value")
        assert log.details["new_field"] == "new_value"
        
        # Test value methods
        assert log.get_old_value("status") == "offline"
        assert log.get_new_value("status") == "online"
        
        # Test change tracking
        log.set_change("name", "old_name", "new_name")
        assert log.old_values["name"] == "old_name"
        assert log.new_values["name"] == "new_name"
        
        # Test mark_failed
        log.mark_failed("E001", "Test error")
        assert log.success is False
        assert log.error_code == "E001"
        assert log.error_message == "Test error"
        
        # Test to_summary
        summary = log.to_summary()
        assert summary["action"] == "update"
        assert summary["resource_type"] == "device"
        assert summary["success"] is False
    
    def test_audit_log_create_log(self):
        """Test audit log factory method."""
        user_id = str(uuid.uuid4())
        
        log = AuditLog.create_log(
            action=AuditAction.DELETE,
            resource_type=AuditResource.DEVICE,
            user_id=user_id,
            resource_id="device-456",
            description="Deleted device",
            ip_address="192.168.1.100"
        )
        
        assert log.action == AuditAction.DELETE
        assert log.resource_type == AuditResource.DEVICE
        assert log.user_id == user_id
        assert log.resource_id == "device-456"
        assert log.description == "Deleted device"
        assert log.ip_address == "192.168.1.100"
