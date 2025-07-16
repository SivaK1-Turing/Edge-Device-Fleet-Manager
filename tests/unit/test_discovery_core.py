"""
Unit tests for discovery core functionality.

Tests the core discovery system including Device, DeviceRegistry, 
DiscoveryEngine, and related components.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from edge_device_fleet_manager.discovery.core import (
    Device, DeviceType, DeviceStatus, DeviceRegistry, 
    DiscoveryEngine, DiscoveryResult, DiscoveryProtocol
)


class TestDevice:
    """Test Device class."""
    
    def test_device_creation(self):
        """Test device creation with defaults."""
        device = Device(ip_address="192.168.1.100")
        
        assert device.ip_address == "192.168.1.100"
        assert device.device_type == DeviceType.UNKNOWN
        assert device.status == DeviceStatus.UNKNOWN
        assert device.discovery_protocol == ""
        assert isinstance(device.discovery_time, datetime)
        assert isinstance(device.last_seen, datetime)
        assert device.ports == []
        assert device.services == []
        assert device.capabilities == {}
        assert device.metadata == {}
    
    def test_device_update_last_seen(self):
        """Test updating last seen timestamp."""
        device = Device(ip_address="192.168.1.100")
        original_time = device.last_seen
        
        # Wait a bit and update
        import time
        time.sleep(0.01)
        device.update_last_seen()
        
        assert device.last_seen > original_time
        assert device.status == DeviceStatus.ONLINE
    
    def test_device_is_stale(self):
        """Test stale device detection."""
        device = Device(ip_address="192.168.1.100")
        
        # Fresh device should not be stale
        assert not device.is_stale(ttl_seconds=300)
        
        # Manually set old timestamp
        old_time = datetime.now(timezone.utc).replace(year=2020)
        device.last_seen = old_time
        
        assert device.is_stale(ttl_seconds=300)
    
    def test_device_to_dict(self):
        """Test device serialization."""
        device = Device(
            ip_address="192.168.1.100",
            name="Test Device",
            device_type=DeviceType.IOT_SENSOR,
            ports=[80, 443],
            services=["HTTP", "HTTPS"]
        )
        
        data = device.to_dict()
        
        assert data["ip_address"] == "192.168.1.100"
        assert data["name"] == "Test Device"
        assert data["device_type"] == "iot_sensor"
        assert data["ports"] == [80, 443]
        assert data["services"] == ["HTTP", "HTTPS"]
        assert "discovery_time" in data
        assert "last_seen" in data


class TestDeviceRegistry:
    """Test DeviceRegistry class."""
    
    @pytest.fixture
    def registry(self):
        """Create a device registry."""
        return DeviceRegistry()
    
    @pytest.fixture
    def sample_device(self):
        """Create a sample device."""
        return Device(
            ip_address="192.168.1.100",
            name="Test Device",
            device_type=DeviceType.IOT_SENSOR
        )
    
    async def test_add_device(self, registry, sample_device):
        """Test adding a device."""
        # Add new device
        is_new = await registry.add_device(sample_device)
        assert is_new is True
        
        # Add same device again (should update)
        is_new = await registry.add_device(sample_device)
        assert is_new is False
        
        # Check device count
        count = await registry.get_device_count()
        assert count == 1
    
    async def test_get_device(self, registry, sample_device):
        """Test getting a device by ID."""
        await registry.add_device(sample_device)
        
        # Get existing device
        retrieved = await registry.get_device(sample_device.device_id)
        assert retrieved is not None
        assert retrieved.device_id == sample_device.device_id
        
        # Get non-existent device
        retrieved = await registry.get_device("non-existent")
        assert retrieved is None
    
    async def test_get_device_by_ip(self, registry, sample_device):
        """Test getting a device by IP address."""
        await registry.add_device(sample_device)
        
        # Get existing device
        retrieved = await registry.get_device_by_ip("192.168.1.100")
        assert retrieved is not None
        assert retrieved.ip_address == "192.168.1.100"
        
        # Get non-existent device
        retrieved = await registry.get_device_by_ip("192.168.1.200")
        assert retrieved is None
    
    async def test_get_all_devices(self, registry):
        """Test getting all devices."""
        # Empty registry
        devices = await registry.get_all_devices()
        assert len(devices) == 0
        
        # Add devices
        device1 = Device(ip_address="192.168.1.100")
        device2 = Device(ip_address="192.168.1.101")
        
        await registry.add_device(device1)
        await registry.add_device(device2)
        
        devices = await registry.get_all_devices()
        assert len(devices) == 2
    
    async def test_remove_device(self, registry, sample_device):
        """Test removing a device."""
        await registry.add_device(sample_device)
        
        # Remove existing device
        removed = await registry.remove_device(sample_device.device_id)
        assert removed is True
        
        # Remove non-existent device
        removed = await registry.remove_device("non-existent")
        assert removed is False
        
        # Check device count
        count = await registry.get_device_count()
        assert count == 0
    
    async def test_cleanup_stale_devices(self, registry):
        """Test cleaning up stale devices."""
        # Add fresh device
        fresh_device = Device(ip_address="192.168.1.100")
        await registry.add_device(fresh_device)
        
        # Add stale device
        stale_device = Device(ip_address="192.168.1.101")
        old_time = datetime.now(timezone.utc).replace(year=2020)
        stale_device.last_seen = old_time
        await registry.add_device(stale_device)
        
        # Cleanup with short TTL
        cleaned = await registry.cleanup_stale_devices(ttl_seconds=1)
        assert cleaned == 1
        
        # Check remaining devices
        devices = await registry.get_all_devices()
        assert len(devices) == 1
        assert devices[0].ip_address == "192.168.1.100"
    
    async def test_device_merging(self, registry):
        """Test device information merging."""
        # Add initial device
        device1 = Device(
            ip_address="192.168.1.100",
            name="Device 1",
            ports=[80],
            services=["HTTP"]
        )
        await registry.add_device(device1)
        
        # Add same IP with additional info
        device2 = Device(
            ip_address="192.168.1.100",
            hostname="test.local",
            ports=[443],
            services=["HTTPS"],
            capabilities={"ssl": True}
        )
        await registry.add_device(device2)
        
        # Check merged device
        merged = await registry.get_device_by_ip("192.168.1.100")
        assert merged is not None
        assert merged.name == "Device 1"  # Original name preserved
        assert merged.hostname == "test.local"  # New hostname added
        assert set(merged.ports) == {80, 443}  # Ports merged
        assert set(merged.services) == {"HTTP", "HTTPS"}  # Services merged
        assert merged.capabilities["ssl"] is True  # Capabilities merged


class MockDiscoveryProtocol(DiscoveryProtocol):
    """Mock discovery protocol for testing."""
    
    def __init__(self, name: str, devices: list = None, should_fail: bool = False):
        super().__init__(name)
        self.devices = devices or []
        self.should_fail = should_fail
        self.discover_called = False
    
    async def discover(self, **kwargs) -> DiscoveryResult:
        """Mock discovery implementation."""
        self.discover_called = True
        
        if self.should_fail:
            raise Exception("Mock discovery failure")
        
        result = DiscoveryResult(protocol=self.name)
        result.devices = self.devices.copy()
        result.duration = 0.1
        return result
    
    async def is_available(self) -> bool:
        """Mock availability check."""
        return not self.should_fail


class TestDiscoveryEngine:
    """Test DiscoveryEngine class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.discovery.cache_ttl = 300
        return config
    
    @pytest.fixture
    def engine(self, mock_config):
        """Create discovery engine."""
        return DiscoveryEngine(mock_config)
    
    def test_register_protocol(self, engine):
        """Test protocol registration."""
        protocol = MockDiscoveryProtocol("test")
        engine.register_protocol(protocol)
        
        assert "test" in engine.protocols
        assert engine.protocols["test"] is protocol
    
    async def test_discover_all_success(self, engine):
        """Test successful discovery with multiple protocols."""
        # Create mock devices
        device1 = Device(ip_address="192.168.1.100", discovery_protocol="protocol1")
        device2 = Device(ip_address="192.168.1.101", discovery_protocol="protocol2")
        
        # Register protocols
        protocol1 = MockDiscoveryProtocol("protocol1", [device1])
        protocol2 = MockDiscoveryProtocol("protocol2", [device2])
        
        engine.register_protocol(protocol1)
        engine.register_protocol(protocol2)
        
        # Run discovery
        result = await engine.discover_all()
        
        assert result.success is True
        assert len(result.devices) == 2
        assert result.protocol == "all"
        assert result.duration > 0
        assert protocol1.discover_called
        assert protocol2.discover_called
        
        # Check devices were added to registry
        devices = await engine.get_devices()
        assert len(devices) == 2
    
    async def test_discover_all_with_failure(self, engine):
        """Test discovery with one protocol failing."""
        device1 = Device(ip_address="192.168.1.100", discovery_protocol="protocol1")
        
        # Register protocols (one will fail)
        protocol1 = MockDiscoveryProtocol("protocol1", [device1])
        protocol2 = MockDiscoveryProtocol("protocol2", should_fail=True)
        
        engine.register_protocol(protocol1)
        engine.register_protocol(protocol2)
        
        # Run discovery
        result = await engine.discover_all()
        
        # Should still succeed with partial results
        assert result.success is True
        assert len(result.devices) == 1
        assert result.devices[0].ip_address == "192.168.1.100"
    
    async def test_discover_specific_protocols(self, engine):
        """Test discovery with specific protocols."""
        device1 = Device(ip_address="192.168.1.100", discovery_protocol="protocol1")
        device2 = Device(ip_address="192.168.1.101", discovery_protocol="protocol2")
        
        protocol1 = MockDiscoveryProtocol("protocol1", [device1])
        protocol2 = MockDiscoveryProtocol("protocol2", [device2])
        
        engine.register_protocol(protocol1)
        engine.register_protocol(protocol2)
        
        # Run discovery with only protocol1
        result = await engine.discover_all(protocols=["protocol1"])
        
        assert len(result.devices) == 1
        assert result.devices[0].ip_address == "192.168.1.100"
        assert protocol1.discover_called
        assert not protocol2.discover_called
    
    async def test_cleanup_stale_devices(self, engine, mock_config):
        """Test stale device cleanup."""
        # Add devices to registry
        fresh_device = Device(ip_address="192.168.1.100")
        stale_device = Device(ip_address="192.168.1.101")
        old_time = datetime.now(timezone.utc).replace(year=2020)
        stale_device.last_seen = old_time
        
        await engine.registry.add_device(fresh_device)
        await engine.registry.add_device(stale_device)
        
        # Cleanup
        cleaned = await engine.cleanup_stale_devices()
        assert cleaned == 1
        
        # Check remaining devices
        devices = await engine.get_devices()
        assert len(devices) == 1
        assert devices[0].ip_address == "192.168.1.100"


class TestDiscoveryResult:
    """Test DiscoveryResult class."""
    
    def test_discovery_result_creation(self):
        """Test discovery result creation."""
        result = DiscoveryResult(protocol="test")
        
        assert result.protocol == "test"
        assert result.devices == []
        assert result.duration == 0.0
        assert result.success is True
        assert result.error is None
        assert result.metadata == {}
    
    def test_add_device(self):
        """Test adding devices to result."""
        result = DiscoveryResult(protocol="test")
        device = Device(ip_address="192.168.1.100")
        
        result.add_device(device)
        
        assert len(result.devices) == 1
        assert result.devices[0] is device
        assert result.get_device_count() == 1
    
    def test_get_device_count(self):
        """Test device count."""
        result = DiscoveryResult(protocol="test")
        
        assert result.get_device_count() == 0
        
        result.add_device(Device(ip_address="192.168.1.100"))
        result.add_device(Device(ip_address="192.168.1.101"))
        
        assert result.get_device_count() == 2
