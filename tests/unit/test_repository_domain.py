"""
Unit tests for repository domain layer.

Tests domain entities, value objects, aggregates, and domain services.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from edge_device_fleet_manager.repository.domain.value_objects import (
    DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities, DeviceMetrics
)
from edge_device_fleet_manager.repository.domain.entities import (
    DeviceEntity, DeviceAggregate, DeviceType, DeviceStatus, DeviceConfiguration
)
from edge_device_fleet_manager.repository.domain.events import (
    DeviceRegisteredEvent, DeviceUpdatedEvent, DeviceDeactivatedEvent,
    DeviceMetricsRecordedEvent
)
from edge_device_fleet_manager.repository.domain.services import (
    DeviceValidationService, DeviceRegistrationService, DeviceLifecycleService
)
from edge_device_fleet_manager.core.exceptions import ValidationError


class TestDeviceId:
    """Test DeviceId value object."""
    
    def test_device_id_creation(self):
        """Test device ID creation."""
        device_uuid = uuid4()
        device_id = DeviceId(device_uuid)
        
        assert device_id.value == device_uuid
        assert str(device_id) == str(device_uuid)
    
    def test_device_id_generate(self):
        """Test device ID generation."""
        device_id = DeviceId.generate()
        
        assert device_id.value is not None
        assert isinstance(device_id.value, type(uuid4()))
    
    def test_device_id_from_string(self):
        """Test device ID from string."""
        uuid_str = str(uuid4())
        device_id = DeviceId.from_string(uuid_str)
        
        assert str(device_id) == uuid_str
    
    def test_device_id_invalid_string(self):
        """Test device ID from invalid string."""
        with pytest.raises(ValidationError, match="Invalid device ID format"):
            DeviceId.from_string("invalid-uuid")


class TestDeviceIdentifier:
    """Test DeviceIdentifier value object."""
    
    def test_device_identifier_creation(self):
        """Test device identifier creation."""
        identifier = DeviceIdentifier(
            serial_number="SN123456",
            mac_address="00:11:22:33:44:55",
            hardware_id="HW789"
        )
        
        assert identifier.serial_number == "SN123456"
        assert identifier.mac_address == "00:11:22:33:44:55"
        assert identifier.hardware_id == "HW789"
    
    def test_device_identifier_required_serial(self):
        """Test device identifier requires serial number."""
        with pytest.raises(ValidationError, match="Serial number is required"):
            DeviceIdentifier(serial_number="")
    
    def test_device_identifier_invalid_mac(self):
        """Test device identifier with invalid MAC address."""
        with pytest.raises(ValidationError, match="Invalid MAC address format"):
            DeviceIdentifier(
                serial_number="SN123456",
                mac_address="invalid-mac"
            )
    
    def test_device_identifier_valid_mac_formats(self):
        """Test device identifier with valid MAC address formats."""
        valid_macs = [
            "00:11:22:33:44:55",
            "00-11-22-33-44-55",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff"
        ]
        
        for mac in valid_macs:
            identifier = DeviceIdentifier(
                serial_number="SN123456",
                mac_address=mac
            )
            assert identifier.mac_address == mac


class TestDeviceLocation:
    """Test DeviceLocation value object."""
    
    def test_device_location_creation(self):
        """Test device location creation."""
        location = DeviceLocation(
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            altitude=Decimal("100.5"),
            address="123 Main St, San Francisco, CA",
            building="Building A",
            floor="3",
            room="301"
        )
        
        assert location.latitude == Decimal("37.7749")
        assert location.longitude == Decimal("-122.4194")
        assert location.altitude == Decimal("100.5")
        assert location.address == "123 Main St, San Francisco, CA"
        assert location.building == "Building A"
        assert location.floor == "3"
        assert location.room == "301"
    
    def test_device_location_coordinates_validation(self):
        """Test device location coordinates validation."""
        # Invalid latitude
        with pytest.raises(ValidationError, match="Latitude must be between -90 and 90"):
            DeviceLocation(latitude=Decimal("91"))
        
        # Invalid longitude
        with pytest.raises(ValidationError, match="Longitude must be between -180 and 180"):
            DeviceLocation(longitude=Decimal("181"))
    
    def test_device_location_properties(self):
        """Test device location properties."""
        # Location with coordinates
        location_with_coords = DeviceLocation(
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194")
        )
        assert location_with_coords.has_coordinates is True
        assert location_with_coords.has_physical_location is False
        
        # Location with physical address
        location_with_address = DeviceLocation(
            building="Building A",
            floor="3"
        )
        assert location_with_address.has_coordinates is False
        assert location_with_address.has_physical_location is True


class TestDeviceCapabilities:
    """Test DeviceCapabilities value object."""
    
    def test_device_capabilities_creation(self):
        """Test device capabilities creation."""
        capabilities = DeviceCapabilities(
            supported_protocols=["HTTP", "MQTT", "CoAP"],
            sensors=["temperature", "humidity", "pressure"],
            actuators=["relay", "servo"],
            connectivity=["WiFi", "Ethernet"],
            power_source="battery",
            operating_system="Linux",
            firmware_version="1.2.3",
            memory_mb=512,
            storage_mb=4096,
            cpu_cores=2
        )
        
        assert capabilities.supported_protocols == ["HTTP", "MQTT", "CoAP"]
        assert capabilities.sensors == ["temperature", "humidity", "pressure"]
        assert capabilities.actuators == ["relay", "servo"]
        assert capabilities.connectivity == ["WiFi", "Ethernet"]
        assert capabilities.power_source == "battery"
        assert capabilities.memory_mb == 512
        assert capabilities.cpu_cores == 2
    
    def test_device_capabilities_required_protocols(self):
        """Test device capabilities requires protocols."""
        with pytest.raises(ValidationError, match="At least one supported protocol is required"):
            DeviceCapabilities(supported_protocols=[])
    
    def test_device_capabilities_properties(self):
        """Test device capabilities properties."""
        capabilities = DeviceCapabilities(
            supported_protocols=["HTTP"],
            sensors=["temperature"],
            actuators=["relay"],
            power_source="battery"
        )
        
        assert capabilities.has_sensors is True
        assert capabilities.has_actuators is True
        assert capabilities.is_battery_powered is True
        assert capabilities.supports_protocol("HTTP") is True
        assert capabilities.supports_protocol("MQTT") is False


class TestDeviceMetrics:
    """Test DeviceMetrics value object."""
    
    def test_device_metrics_creation(self):
        """Test device metrics creation."""
        timestamp = datetime.now(timezone.utc)
        metrics = DeviceMetrics(
            timestamp=timestamp,
            cpu_usage_percent=75.5,
            memory_usage_percent=60.2,
            temperature_celsius=45.0,
            battery_level_percent=85.0,
            uptime_seconds=3600
        )
        
        assert metrics.timestamp == timestamp
        assert metrics.cpu_usage_percent == 75.5
        assert metrics.memory_usage_percent == 60.2
        assert metrics.temperature_celsius == 45.0
        assert metrics.battery_level_percent == 85.0
        assert metrics.uptime_seconds == 3600
    
    def test_device_metrics_validation(self):
        """Test device metrics validation."""
        timestamp = datetime.now(timezone.utc)
        
        # Invalid percentage values
        with pytest.raises(ValidationError, match="cpu_usage_percent must be between 0 and 100"):
            DeviceMetrics(timestamp=timestamp, cpu_usage_percent=101)
        
        # Invalid negative values
        with pytest.raises(ValidationError, match="network_bytes_sent cannot be negative"):
            DeviceMetrics(timestamp=timestamp, network_bytes_sent=-1)
    
    def test_device_metrics_create_now(self):
        """Test device metrics create with current timestamp."""
        metrics = DeviceMetrics.create_now(cpu_usage_percent=50.0)
        
        assert metrics.timestamp is not None
        assert metrics.cpu_usage_percent == 50.0
        assert metrics.age_seconds >= 0
    
    def test_device_metrics_to_dict(self):
        """Test device metrics to dictionary conversion."""
        timestamp = datetime.now(timezone.utc)
        metrics = DeviceMetrics(
            timestamp=timestamp,
            cpu_usage_percent=75.5,
            custom_metrics={"sensor1": 123}
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["timestamp"] == timestamp.isoformat()
        assert metrics_dict["cpu_usage_percent"] == 75.5
        assert metrics_dict["custom_metrics"] == {"sensor1": 123}
        assert "memory_usage_percent" not in metrics_dict  # None values excluded


class TestDeviceEntity:
    """Test DeviceEntity."""
    
    @pytest.fixture
    def sample_device(self):
        """Create sample device entity."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        return DeviceEntity(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
    
    def test_device_entity_creation(self, sample_device):
        """Test device entity creation."""
        assert sample_device.name == "Test Device"
        assert sample_device.device_type == DeviceType.SENSOR
        assert sample_device.status == DeviceStatus.ACTIVE
        assert sample_device.identifier.serial_number == "SN123456"
        assert sample_device.version == 1
    
    def test_device_entity_validation(self):
        """Test device entity validation."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        # Empty name
        with pytest.raises(ValidationError, match="Device name is required"):
            DeviceEntity(
                device_id=device_id,
                name="",
                device_type=DeviceType.SENSOR,
                identifier=identifier
            )
        
        # Name too long
        with pytest.raises(ValidationError, match="Device name too long"):
            DeviceEntity(
                device_id=device_id,
                name="x" * 201,
                device_type=DeviceType.SENSOR,
                identifier=identifier
            )
    
    def test_device_entity_update_name(self, sample_device):
        """Test device entity name update."""
        original_version = sample_device.version
        
        event = sample_device.update_name("New Device Name")
        
        assert sample_device.name == "New Device Name"
        assert sample_device.version == original_version + 1
        assert event.event_type == "device.updated"
    
    def test_device_entity_deactivate(self, sample_device):
        """Test device entity deactivation."""
        event = sample_device.deactivate("Maintenance required")
        
        assert sample_device.status == DeviceStatus.INACTIVE
        assert event.event_type == "device.deactivated"
        assert event.reason == "Maintenance required"
    
    def test_device_entity_is_online(self, sample_device):
        """Test device entity online status."""
        # No last seen - not online
        assert sample_device.is_online() is False
        
        # Recent last seen - online
        sample_device.update_last_seen()
        assert sample_device.is_online() is True


class TestDeviceAggregate:
    """Test DeviceAggregate."""
    
    def test_device_aggregate_creation(self):
        """Test device aggregate creation."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        assert aggregate.device_id == device_id
        assert aggregate.device.name == "Test Device"
        assert len(aggregate.get_uncommitted_events()) == 1
        
        # Check registration event
        events = aggregate.get_uncommitted_events()
        assert events[0].event_type == "device.registered"
    
    def test_device_aggregate_record_metrics(self):
        """Test device aggregate metrics recording."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        # Clear initial events
        aggregate.mark_events_as_committed()
        
        # Record metrics
        metrics = DeviceMetrics.create_now(cpu_usage_percent=50.0)
        aggregate.record_metrics(metrics)
        
        # Check metrics event
        events = aggregate.get_uncommitted_events()
        assert len(events) == 1
        assert events[0].event_type == "device.metrics.recorded"
        
        # Check metrics history
        recent_metrics = aggregate.get_recent_metrics(1)
        assert len(recent_metrics) == 1
        assert recent_metrics[0].cpu_usage_percent == 50.0
    
    def test_device_aggregate_configuration(self):
        """Test device aggregate configuration."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        # Update configuration
        aggregate.update_configuration("sampling_rate", 1000)
        
        # Check configuration
        assert aggregate.get_configuration("sampling_rate") == 1000
        assert aggregate.get_configuration("nonexistent", "default") == "default"


class TestDeviceValidationService:
    """Test DeviceValidationService."""
    
    def test_validate_device_name(self):
        """Test device name validation."""
        service = DeviceValidationService()
        
        # Valid names
        service.validate_device_name("Valid Device Name")
        service.validate_device_name("Device-123_v2.0")
        
        # Invalid names
        with pytest.raises(ValidationError, match="Device name is required"):
            service.validate_device_name("")
        
        with pytest.raises(ValidationError, match="must be at least 2 characters"):
            service.validate_device_name("A")
        
        with pytest.raises(ValidationError, match="contains invalid characters"):
            service.validate_device_name("Device@#$%")
        
        with pytest.raises(ValidationError, match="reserved name"):
            service.validate_device_name("admin")
    
    def test_validate_serial_number(self):
        """Test serial number validation."""
        service = DeviceValidationService()
        
        # Valid serial numbers
        service.validate_serial_number("SN123456")
        service.validate_serial_number("ABC-123_DEF")
        
        # Invalid serial numbers
        with pytest.raises(ValidationError, match="Serial number is required"):
            service.validate_serial_number("")
        
        with pytest.raises(ValidationError, match="must be at least 3 characters"):
            service.validate_serial_number("AB")
        
        with pytest.raises(ValidationError, match="contains invalid characters"):
            service.validate_serial_number("SN@123")
    
    def test_validate_device_type_compatibility(self):
        """Test device type compatibility validation."""
        service = DeviceValidationService()
        
        # Valid sensor device
        sensor_capabilities = DeviceCapabilities(
            supported_protocols=["HTTP"],
            sensors=["temperature"]
        )
        service.validate_device_type_compatibility(DeviceType.SENSOR, sensor_capabilities)
        
        # Invalid sensor device (no sensors)
        invalid_sensor_capabilities = DeviceCapabilities(
            supported_protocols=["HTTP"],
            sensors=[]
        )
        with pytest.raises(ValidationError, match="Sensor devices must have at least one sensor"):
            service.validate_device_type_compatibility(DeviceType.SENSOR, invalid_sensor_capabilities)


class TestDeviceLifecycleService:
    """Test DeviceLifecycleService."""
    
    @pytest.fixture
    def lifecycle_service(self):
        """Create lifecycle service."""
        validation_service = DeviceValidationService()
        return DeviceLifecycleService(validation_service)
    
    @pytest.fixture
    def sample_device(self):
        """Create sample device."""
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        return DeviceEntity(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
    
    def test_can_deactivate_device(self, lifecycle_service, sample_device):
        """Test device deactivation check."""
        # Active device can be deactivated
        can_deactivate, reason = lifecycle_service.can_deactivate_device(sample_device)
        assert can_deactivate is True
        assert reason is None
        
        # Decommissioned device cannot be deactivated
        sample_device.status = DeviceStatus.DECOMMISSIONED
        can_deactivate, reason = lifecycle_service.can_deactivate_device(sample_device)
        assert can_deactivate is False
        assert "decommissioned" in reason.lower()
    
    def test_calculate_device_health_score(self, lifecycle_service, sample_device):
        """Test device health score calculation."""
        # Active device with recent activity
        sample_device.update_last_seen()
        health_score = lifecycle_service.calculate_device_health_score(sample_device)
        assert 0.8 <= health_score <= 1.0
        
        # Inactive device
        sample_device.status = DeviceStatus.INACTIVE
        health_score = lifecycle_service.calculate_device_health_score(sample_device)
        assert health_score <= 0.5
        
        # Decommissioned device
        sample_device.status = DeviceStatus.DECOMMISSIONED
        health_score = lifecycle_service.calculate_device_health_score(sample_device)
        assert health_score == 0.0
