"""
Unit tests for discovery caching functionality.

Tests the caching system including MemoryCache, RedisCache, and DiscoveryCache.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from edge_device_fleet_manager.discovery.cache import (
    MemoryCache, RedisCache, DiscoveryCache
)
from edge_device_fleet_manager.discovery.core import Device, DeviceType, DeviceStatus


class TestMemoryCache:
    """Test in-memory cache implementation."""
    
    @pytest.fixture
    def memory_cache(self):
        """Create memory cache."""
        return MemoryCache(default_ttl=300)
    
    async def test_set_and_get(self, memory_cache):
        """Test setting and getting values."""
        # Set value
        result = await memory_cache.set("test_key", "test_value")
        assert result is True
        
        # Get value
        value = await memory_cache.get("test_key")
        assert value == "test_value"
    
    async def test_get_nonexistent(self, memory_cache):
        """Test getting non-existent key."""
        value = await memory_cache.get("nonexistent")
        assert value is None
    
    async def test_ttl_expiration(self, memory_cache):
        """Test TTL expiration."""
        # Set with short TTL
        await memory_cache.set("test_key", "test_value", ttl=1)
        
        # Should exist immediately
        value = await memory_cache.get("test_key")
        assert value == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await memory_cache.get("test_key")
        assert value is None
    
    async def test_delete(self, memory_cache):
        """Test deleting keys."""
        # Set value
        await memory_cache.set("test_key", "test_value")
        
        # Delete existing key
        result = await memory_cache.delete("test_key")
        assert result is True
        
        # Key should be gone
        value = await memory_cache.get("test_key")
        assert value is None
        
        # Delete non-existent key
        result = await memory_cache.delete("nonexistent")
        assert result is False
    
    async def test_exists(self, memory_cache):
        """Test checking key existence."""
        # Non-existent key
        exists = await memory_cache.exists("test_key")
        assert exists is False
        
        # Set key
        await memory_cache.set("test_key", "test_value")
        
        # Should exist
        exists = await memory_cache.exists("test_key")
        assert exists is True
    
    async def test_clear(self, memory_cache):
        """Test clearing all keys."""
        # Set multiple keys
        await memory_cache.set("key1", "value1")
        await memory_cache.set("key2", "value2")
        
        # Clear all
        result = await memory_cache.clear()
        assert result is True
        
        # All keys should be gone
        assert await memory_cache.get("key1") is None
        assert await memory_cache.get("key2") is None
    
    async def test_keys_pattern(self, memory_cache):
        """Test getting keys with pattern."""
        # Set test keys
        await memory_cache.set("test:key1", "value1")
        await memory_cache.set("test:key2", "value2")
        await memory_cache.set("other:key", "value3")
        
        # Get all keys
        all_keys = await memory_cache.keys("*")
        assert len(all_keys) == 3
        
        # Get keys with prefix
        test_keys = await memory_cache.keys("test:*")
        assert len(test_keys) == 2
        assert all(key.startswith("test:") for key in test_keys)


class TestRedisCache:
    """Test Redis cache implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = Mock()
        redis_mock.get = AsyncMock()
        redis_mock.setex = AsyncMock()
        redis_mock.delete = AsyncMock()
        redis_mock.exists = AsyncMock()
        redis_mock.flushdb = AsyncMock()
        redis_mock.keys = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create Redis cache."""
        return RedisCache(mock_redis, default_ttl=300)
    
    async def test_set_and_get(self, redis_cache, mock_redis):
        """Test setting and getting values."""
        # Mock Redis responses
        mock_redis.get.return_value = b"test_value"
        mock_redis.setex.return_value = True
        
        # Set value
        result = await redis_cache.set("test_key", "test_value")
        assert result is True
        mock_redis.setex.assert_called_with("test_key", 300, "test_value")
        
        # Get value
        value = await redis_cache.get("test_key")
        assert value == "test_value"
        mock_redis.get.assert_called_with("test_key")
    
    async def test_get_nonexistent(self, redis_cache, mock_redis):
        """Test getting non-existent key."""
        mock_redis.get.return_value = None
        
        value = await redis_cache.get("nonexistent")
        assert value is None
    
    async def test_delete(self, redis_cache, mock_redis):
        """Test deleting keys."""
        mock_redis.delete.return_value = 1  # 1 key deleted
        
        result = await redis_cache.delete("test_key")
        assert result is True
        mock_redis.delete.assert_called_with("test_key")
    
    async def test_exists(self, redis_cache, mock_redis):
        """Test checking key existence."""
        mock_redis.exists.return_value = 1  # Key exists
        
        exists = await redis_cache.exists("test_key")
        assert exists is True
        mock_redis.exists.assert_called_with("test_key")
    
    async def test_clear(self, redis_cache, mock_redis):
        """Test clearing all keys."""
        mock_redis.flushdb.return_value = True
        
        result = await redis_cache.clear()
        assert result is True
        mock_redis.flushdb.assert_called_once()
    
    async def test_keys(self, redis_cache, mock_redis):
        """Test getting keys with pattern."""
        mock_redis.keys.return_value = [b"key1", b"key2"]
        
        keys = await redis_cache.keys("test:*")
        assert keys == ["key1", "key2"]
        mock_redis.keys.assert_called_with("test:*")
    
    async def test_redis_error_handling(self, redis_cache, mock_redis):
        """Test Redis error handling."""
        # Mock Redis errors
        mock_redis.get.side_effect = Exception("Redis error")
        mock_redis.setex.side_effect = Exception("Redis error")
        
        # Operations should return None/False on error
        value = await redis_cache.get("test_key")
        assert value is None
        
        result = await redis_cache.set("test_key", "test_value")
        assert result is False


class TestDiscoveryCache:
    """Test high-level discovery cache."""
    
    @pytest.fixture
    def mock_redis_config(self):
        """Create mock Redis configuration."""
        config = Mock()
        config.host = "localhost"
        config.port = 6379
        config.db = 0
        config.password = None
        config.socket_timeout = 5
        config.socket_connect_timeout = 5
        config.max_connections = 10
        return config
    
    @pytest.fixture
    def discovery_cache(self):
        """Create discovery cache with memory backend."""
        return DiscoveryCache(redis_config=None, default_ttl=300)
    
    @pytest.fixture
    def sample_device(self):
        """Create sample device."""
        return Device(
            device_id="test-device-123",
            ip_address="192.168.1.100",
            name="Test Device",
            device_type=DeviceType.IOT_SENSOR,
            ports=[80, 443],
            services=["HTTP", "HTTPS"],
            capabilities={"ssl": True}
        )
    
    def test_cache_backend_selection(self):
        """Test cache backend selection."""
        # Without Redis config, should use memory
        cache = DiscoveryCache(redis_config=None)
        assert cache.backend == "memory"
        
        # With Redis available but no config, should use memory
        with patch('edge_device_fleet_manager.discovery.cache.REDIS_AVAILABLE', True):
            cache = DiscoveryCache(redis_config=None)
            assert cache.backend == "memory"
    
    def test_key_generation(self, discovery_cache):
        """Test cache key generation."""
        assert discovery_cache._device_key("test-123") == "device:test-123"
        assert discovery_cache._ip_key("192.168.1.100") == "ip:192.168.1.100"
        assert discovery_cache._discovery_key("mdns") == "discovery:mdns"
    
    async def test_cache_device(self, discovery_cache, sample_device):
        """Test caching a device."""
        result = await discovery_cache.cache_device(sample_device)
        assert result is True
        
        # Should be able to retrieve device
        cached_device = await discovery_cache.get_device(sample_device.device_id)
        assert cached_device is not None
        assert cached_device.device_id == sample_device.device_id
        assert cached_device.ip_address == sample_device.ip_address
        assert cached_device.name == sample_device.name
    
    async def test_get_device_nonexistent(self, discovery_cache):
        """Test getting non-existent device."""
        device = await discovery_cache.get_device("nonexistent")
        assert device is None
    
    async def test_get_device_by_ip(self, discovery_cache, sample_device):
        """Test getting device by IP address."""
        # Cache device
        await discovery_cache.cache_device(sample_device)
        
        # Get by IP
        cached_device = await discovery_cache.get_device_by_ip("192.168.1.100")
        assert cached_device is not None
        assert cached_device.device_id == sample_device.device_id
        
        # Get non-existent IP
        cached_device = await discovery_cache.get_device_by_ip("192.168.1.200")
        assert cached_device is None
    
    async def test_remove_device(self, discovery_cache, sample_device):
        """Test removing device from cache."""
        # Cache device
        await discovery_cache.cache_device(sample_device)
        
        # Remove device
        result = await discovery_cache.remove_device(sample_device.device_id)
        assert result is True
        
        # Should be gone
        cached_device = await discovery_cache.get_device(sample_device.device_id)
        assert cached_device is None
        
        # Remove non-existent device
        result = await discovery_cache.remove_device("nonexistent")
        assert result is True  # Should not fail (returns True even if device doesn't exist)
    
    async def test_cache_discovery_result(self, discovery_cache, sample_device):
        """Test caching discovery results."""
        devices = [sample_device]
        
        result = await discovery_cache.cache_discovery_result("mdns", devices)
        assert result is True
        
        # Get cached result
        cached_result = await discovery_cache.get_discovery_result("mdns")
        assert cached_result is not None
        assert cached_result["protocol"] == "mdns"
        assert len(cached_result["devices"]) == 1
        assert cached_result["devices"][0]["device_id"] == sample_device.device_id
    
    async def test_get_discovery_result_nonexistent(self, discovery_cache):
        """Test getting non-existent discovery result."""
        result = await discovery_cache.get_discovery_result("nonexistent")
        assert result is None
    
    async def test_clear_all(self, discovery_cache, sample_device):
        """Test clearing all cached data."""
        # Cache some data
        await discovery_cache.cache_device(sample_device)
        await discovery_cache.cache_discovery_result("mdns", [sample_device])
        
        # Clear all
        result = await discovery_cache.clear_all()
        assert result is True
        
        # Should be empty
        device = await discovery_cache.get_device(sample_device.device_id)
        assert device is None
        
        discovery_result = await discovery_cache.get_discovery_result("mdns")
        assert discovery_result is None
    
    async def test_get_cached_devices(self, discovery_cache):
        """Test getting all cached devices."""
        # Initially empty
        devices = await discovery_cache.get_cached_devices()
        assert len(devices) == 0
        
        # Cache some devices
        device1 = Device(device_id="device1", ip_address="192.168.1.100")
        device2 = Device(device_id="device2", ip_address="192.168.1.101")
        
        await discovery_cache.cache_device(device1)
        await discovery_cache.cache_device(device2)
        
        # Should get both devices
        devices = await discovery_cache.get_cached_devices()
        assert len(devices) == 2
        device_ids = {d.device_id for d in devices}
        assert device_ids == {"device1", "device2"}
    
    def test_dict_to_device_conversion(self, discovery_cache):
        """Test converting dictionary to Device object."""
        device_dict = {
            "device_id": "test-123",
            "name": "Test Device",
            "device_type": "iot_sensor",
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55",
            "hostname": "test.local",
            "ports": [80, 443],
            "discovery_protocol": "mdns",
            "discovery_time": "2023-01-01T12:00:00+00:00",
            "last_seen": "2023-01-01T12:05:00+00:00",
            "status": "online",
            "manufacturer": "Test Corp",
            "model": "Test Model",
            "firmware_version": "1.0.0",
            "services": ["HTTP", "HTTPS"],
            "capabilities": {"ssl": True},
            "metadata": {"test": "value"}
        }
        
        device = discovery_cache._dict_to_device(device_dict)
        
        assert device.device_id == "test-123"
        assert device.name == "Test Device"
        assert device.device_type == DeviceType.IOT_SENSOR
        assert device.ip_address == "192.168.1.100"
        assert device.mac_address == "00:11:22:33:44:55"
        assert device.hostname == "test.local"
        assert device.ports == [80, 443]
        assert device.discovery_protocol == "mdns"
        assert device.status == DeviceStatus.ONLINE
        assert device.manufacturer == "Test Corp"
        assert device.model == "Test Model"
        assert device.firmware_version == "1.0.0"
        assert device.services == ["HTTP", "HTTPS"]
        assert device.capabilities == {"ssl": True}
        assert device.metadata == {"test": "value"}
        assert isinstance(device.discovery_time, datetime)
        assert isinstance(device.last_seen, datetime)
