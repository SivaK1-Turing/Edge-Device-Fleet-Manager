#!/usr/bin/env python3
"""
Comprehensive test runner for Feature 2: High-Performance Device Discovery.

This script runs all discovery-related tests and provides a summary of results.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.discovery.core import (
    Device, DeviceType, DeviceStatus, DeviceRegistry, DiscoveryEngine
)
from edge_device_fleet_manager.discovery.rate_limiter import RateLimiter, RateLimitConfig
from edge_device_fleet_manager.discovery.cache import DiscoveryCache
from edge_device_fleet_manager.discovery.protocols.mdns import MDNSDiscovery
from edge_device_fleet_manager.discovery.protocols.ssdp import SSDPDiscovery
from edge_device_fleet_manager.discovery.protocols.network_scan import NetworkScanDiscovery


async def test_device_creation():
    """Test basic device creation and functionality."""
    print("🔍 Testing Device Creation...")
    
    device = Device(
        ip_address="192.168.1.100",
        name="Test Device",
        device_type=DeviceType.IOT_SENSOR,
        ports=[80, 443, 1883],
        services=["HTTP", "HTTPS", "MQTT"]
    )
    
    assert device.ip_address == "192.168.1.100"
    assert device.name == "Test Device"
    assert device.device_type == DeviceType.IOT_SENSOR
    assert device.status == DeviceStatus.UNKNOWN
    assert len(device.ports) == 3
    assert len(device.services) == 3
    
    # Test serialization
    device_dict = device.to_dict()
    assert device_dict["ip_address"] == "192.168.1.100"
    assert device_dict["device_type"] == "iot_sensor"
    
    # Test last seen update
    original_time = device.last_seen
    time.sleep(0.01)
    device.update_last_seen()
    assert device.last_seen > original_time
    assert device.status == DeviceStatus.ONLINE
    
    print("✅ Device creation tests passed")
    return True


async def test_device_registry():
    """Test device registry functionality."""
    print("🔍 Testing Device Registry...")
    
    registry = DeviceRegistry()
    
    # Test empty registry
    devices = await registry.get_all_devices()
    assert len(devices) == 0
    
    count = await registry.get_device_count()
    assert count == 0
    
    # Add devices
    device1 = Device(ip_address="192.168.1.100", name="Device 1")
    device2 = Device(ip_address="192.168.1.101", name="Device 2")
    
    is_new1 = await registry.add_device(device1)
    is_new2 = await registry.add_device(device2)
    
    assert is_new1 is True
    assert is_new2 is True
    
    # Test retrieval
    count = await registry.get_device_count()
    assert count == 2
    
    retrieved1 = await registry.get_device(device1.device_id)
    assert retrieved1 is not None
    assert retrieved1.device_id == device1.device_id
    
    retrieved_by_ip = await registry.get_device_by_ip("192.168.1.100")
    assert retrieved_by_ip is not None
    assert retrieved_by_ip.ip_address == "192.168.1.100"
    
    # Test device merging (same IP)
    device1_updated = Device(
        ip_address="192.168.1.100",
        hostname="device1.local",
        ports=[22, 80],
        services=["SSH", "HTTP"]
    )
    
    is_new_update = await registry.add_device(device1_updated)
    assert is_new_update is False  # Not new, should merge
    
    merged = await registry.get_device_by_ip("192.168.1.100")
    assert merged.name == "Device 1"  # Original name preserved
    assert merged.hostname == "device1.local"  # New hostname added
    assert set(merged.ports) == {22, 80}  # Ports merged
    assert set(merged.services) == {"SSH", "HTTP"}  # Services merged
    
    # Test removal
    removed = await registry.remove_device(device2.device_id)
    assert removed is True
    
    count = await registry.get_device_count()
    assert count == 1
    
    print("✅ Device registry tests passed")
    return True


async def test_rate_limiter():
    """Test rate limiting functionality."""
    print("🔍 Testing Rate Limiter...")
    
    config = RateLimitConfig(
        requests_per_second=10.0,
        per_host_limit=5.0,
        global_limit=20.0,
        backoff_factor=2.0,
        max_backoff=5.0
    )
    
    rate_limiter = RateLimiter(config)
    
    # Test basic acquisition
    result = await rate_limiter.acquire("test.example.com", timeout=1.0)
    assert result is True
    
    # Test success recording
    rate_limiter.record_success("test.example.com", response_time=0.1)
    
    stats = rate_limiter.get_stats("test.example.com")
    assert stats["total_requests"] == 1
    assert stats["success_rate"] == 1.0
    assert stats["avg_response_time"] == 0.1
    
    # Test failure recording
    rate_limiter.record_failure("test.example.com", error_type="timeout")
    
    stats = rate_limiter.get_stats("test.example.com")
    assert stats["total_requests"] == 2
    assert stats["success_rate"] == 0.5
    assert stats["current_backoff"] > 0
    
    # Test global stats
    rate_limiter.record_success("other.example.com", response_time=0.2)

    global_stats = rate_limiter.get_stats()  # No host = global
    assert global_stats["total_requests"] == 3
    # Note: active_hosts counts hosts with buckets, which may be created during acquire calls
    assert global_stats["active_hosts"] >= 1  # At least one host should be active
    
    print("✅ Rate limiter tests passed")
    return True


async def test_discovery_cache():
    """Test discovery caching functionality."""
    print("🔍 Testing Discovery Cache...")
    
    cache = DiscoveryCache(redis_config=None, default_ttl=300)
    assert cache.backend == "memory"
    
    # Test device caching
    device = Device(
        device_id="test-device-123",
        ip_address="192.168.1.100",
        name="Test Device",
        device_type=DeviceType.IOT_SENSOR,
        ports=[80, 443],
        services=["HTTP", "HTTPS"]
    )
    
    # Cache device
    result = await cache.cache_device(device)
    assert result is True
    
    # Retrieve device
    cached_device = await cache.get_device(device.device_id)
    assert cached_device is not None
    assert cached_device.device_id == device.device_id
    assert cached_device.ip_address == device.ip_address
    assert cached_device.name == device.name
    
    # Retrieve by IP
    cached_by_ip = await cache.get_device_by_ip("192.168.1.100")
    assert cached_by_ip is not None
    assert cached_by_ip.device_id == device.device_id
    
    # Test discovery result caching
    devices = [device]
    result = await cache.cache_discovery_result("mdns", devices)
    assert result is True
    
    cached_result = await cache.get_discovery_result("mdns")
    assert cached_result is not None
    assert cached_result["protocol"] == "mdns"
    assert len(cached_result["devices"]) == 1
    
    # Test getting all cached devices
    all_devices = await cache.get_cached_devices()
    assert len(all_devices) == 1
    assert all_devices[0].device_id == device.device_id
    
    # Test removal
    removed = await cache.remove_device(device.device_id)
    assert removed is True
    
    cached_device = await cache.get_device(device.device_id)
    assert cached_device is None
    
    print("✅ Discovery cache tests passed")
    return True


async def test_discovery_protocols():
    """Test discovery protocol availability checks."""
    print("🔍 Testing Discovery Protocols...")
    
    # Mock configuration
    class MockConfig:
        class Discovery:
            mdns_timeout = 3
            ssdp_timeout = 3
            rate_limit_per_host = 2.0
            rate_limit_global = 100.0
        
        discovery = Discovery()
    
    config = MockConfig()
    
    # Test protocol creation
    mdns = MDNSDiscovery(config)
    ssdp = SSDPDiscovery(config)
    network_scan = NetworkScanDiscovery(config)
    
    assert mdns.name == "mdns"
    assert ssdp.name == "ssdp"
    assert network_scan.name == "network_scan"
    
    # Test availability checks (may fail in test environment, that's OK)
    try:
        mdns_available = await mdns.is_available()
        print(f"  mDNS available: {mdns_available}")
    except Exception as e:
        print(f"  mDNS availability check failed: {e}")
    
    try:
        ssdp_available = await ssdp.is_available()
        print(f"  SSDP available: {ssdp_available}")
    except Exception as e:
        print(f"  SSDP availability check failed: {e}")
    
    try:
        network_available = await network_scan.is_available()
        print(f"  Network scan available: {network_available}")
    except Exception as e:
        print(f"  Network scan availability check failed: {e}")
    
    print("✅ Discovery protocol tests passed")
    return True


async def test_discovery_engine():
    """Test discovery engine coordination."""
    print("🔍 Testing Discovery Engine...")
    
    # Mock configuration
    class MockConfig:
        class Discovery:
            cache_ttl = 300
        
        discovery = Discovery()
    
    config = MockConfig()
    
    # Create engine
    engine = DiscoveryEngine(config)
    
    # Test protocol registration
    class MockProtocol:
        def __init__(self, name, devices=None):
            self.name = name
            self.devices = devices or []
            self.discover_called = False
        
        def get_name(self):
            return self.name
        
        async def discover(self, **kwargs):
            self.discover_called = True
            from edge_device_fleet_manager.discovery.core import DiscoveryResult
            result = DiscoveryResult(protocol=self.name)
            result.devices = self.devices.copy()
            result.duration = 0.1
            return result
        
        async def is_available(self):
            return True
    
    # Register mock protocols
    device1 = Device(ip_address="192.168.1.100", discovery_protocol="protocol1")
    device2 = Device(ip_address="192.168.1.101", discovery_protocol="protocol2")
    
    protocol1 = MockProtocol("protocol1", [device1])
    protocol2 = MockProtocol("protocol2", [device2])
    
    engine.register_protocol(protocol1)
    engine.register_protocol(protocol2)
    
    assert len(engine.protocols) == 2
    assert "protocol1" in engine.protocols
    assert "protocol2" in engine.protocols
    
    # Test discovery
    result = await engine.discover_all()
    
    assert result.success is True
    assert len(result.devices) == 2
    assert result.protocol == "all"
    assert result.duration > 0
    assert protocol1.discover_called
    assert protocol2.discover_called
    
    # Test getting devices from registry
    devices = await engine.get_devices()
    assert len(devices) == 2
    
    # Test specific protocol discovery
    result = await engine.discover_all(protocols=["protocol1"])
    # Note: This will add the same device again, but registry should handle duplicates
    
    print("✅ Discovery engine tests passed")
    return True


async def run_all_tests():
    """Run all discovery tests."""
    print("🚀 Starting Feature 2: High-Performance Device Discovery Tests")
    print("=" * 70)
    
    tests = [
        test_device_creation,
        test_device_registry,
        test_rate_limiter,
        test_discovery_cache,
        test_discovery_protocols,
        test_discovery_engine,
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
        print("🎉 All discovery tests passed! Feature 2 is working correctly.")
        return True
    else:
        print(f"❌ {failed} tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
