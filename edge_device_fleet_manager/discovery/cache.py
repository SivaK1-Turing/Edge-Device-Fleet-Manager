"""
Caching system for discovery results.

This module provides Redis-based caching with TTL, device state persistence,
and cache invalidation strategies for the discovery system.
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .core import Device, DeviceStatus, DeviceType
from .exceptions import CacheError
from ..core.logging import get_logger

logger = get_logger(__name__)


class MemoryCache:
    """In-memory cache implementation as fallback."""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                del self._cache[key]
        return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self.get(key) is not None
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        self._cache.clear()
        return True
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        # Simple pattern matching for memory cache
        if pattern == "*":
            return list(self._cache.keys())
        
        # Basic wildcard support
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._cache.keys() if k.startswith(prefix)]
        
        return [k for k in self._cache.keys() if k == pattern]


class RedisCache:
    """Redis-based cache implementation."""
    
    def __init__(self, redis_client, default_ttl: int = 300):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.logger = get_logger(__name__)
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis cache."""
        try:
            value = await self.redis.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            self.logger.error("Redis get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis cache."""
        try:
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, value)
            return True
        except Exception as e:
            self.logger.error("Redis set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis cache."""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            self.logger.error("Redis delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            self.logger.error("Redis exists failed", key=key, error=str(e))
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            self.logger.error("Redis clear failed", error=str(e))
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode('utf-8') for key in keys]
        except Exception as e:
            self.logger.error("Redis keys failed", pattern=pattern, error=str(e))
            return []


class DiscoveryCache:
    """High-level cache interface for discovery system."""
    
    def __init__(self, redis_config=None, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self.logger = get_logger(__name__)
        
        # Initialize cache backend
        if REDIS_AVAILABLE and redis_config:
            try:
                redis_client = redis.Redis(
                    host=redis_config.host,
                    port=redis_config.port,
                    db=redis_config.db,
                    password=redis_config.password,
                    socket_timeout=redis_config.socket_timeout,
                    socket_connect_timeout=redis_config.socket_connect_timeout,
                    max_connections=redis_config.max_connections,
                    decode_responses=False
                )
                self.cache = RedisCache(redis_client, default_ttl)
                self.backend = "redis"
                self.logger.info("Using Redis cache backend")
            except Exception as e:
                self.logger.warning("Failed to connect to Redis, using memory cache", error=str(e))
                self.cache = MemoryCache(default_ttl)
                self.backend = "memory"
        else:
            self.cache = MemoryCache(default_ttl)
            self.backend = "memory"
            self.logger.info("Using memory cache backend")
    
    def _device_key(self, device_id: str) -> str:
        """Generate cache key for device."""
        return f"device:{device_id}"
    
    def _ip_key(self, ip_address: str) -> str:
        """Generate cache key for IP mapping."""
        return f"ip:{ip_address}"
    
    def _discovery_key(self, protocol: str) -> str:
        """Generate cache key for discovery results."""
        return f"discovery:{protocol}"
    
    async def cache_device(self, device: Device, ttl: Optional[int] = None) -> bool:
        """Cache a device."""
        try:
            device_data = json.dumps(device.to_dict())
            device_key = self._device_key(device.device_id)
            ip_key = self._ip_key(device.ip_address)
            
            # Cache device data
            success1 = await self.cache.set(device_key, device_data, ttl)
            
            # Cache IP to device ID mapping
            success2 = await self.cache.set(ip_key, device.device_id, ttl)
            
            return success1 and success2
        except Exception as e:
            self.logger.error("Failed to cache device", device_id=device.device_id, error=str(e))
            return False
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device from cache."""
        try:
            device_key = self._device_key(device_id)
            device_data = await self.cache.get(device_key)
            
            if device_data:
                data = json.loads(device_data)
                return self._dict_to_device(data)
            
            return None
        except Exception as e:
            self.logger.error("Failed to get device from cache", device_id=device_id, error=str(e))
            return None
    
    async def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """Get a device by IP address from cache."""
        try:
            ip_key = self._ip_key(ip_address)
            device_id = await self.cache.get(ip_key)
            
            if device_id:
                return await self.get_device(device_id)
            
            return None
        except Exception as e:
            self.logger.error("Failed to get device by IP from cache", ip=ip_address, error=str(e))
            return None
    
    async def remove_device(self, device_id: str) -> bool:
        """Remove a device from cache."""
        try:
            # Get device to find IP address
            device = await self.get_device(device_id)
            
            device_key = self._device_key(device_id)
            success1 = await self.cache.delete(device_key)
            
            success2 = True
            if device and device.ip_address:
                ip_key = self._ip_key(device.ip_address)
                success2 = await self.cache.delete(ip_key)
            
            return success1 and success2
        except Exception as e:
            self.logger.error("Failed to remove device from cache", device_id=device_id, error=str(e))
            return False
    
    async def cache_discovery_result(self, protocol: str, devices: List[Device], ttl: Optional[int] = None) -> bool:
        """Cache discovery results."""
        try:
            discovery_key = self._discovery_key(protocol)
            result_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'protocol': protocol,
                'devices': [device.to_dict() for device in devices]
            }
            
            return await self.cache.set(discovery_key, json.dumps(result_data), ttl)
        except Exception as e:
            self.logger.error("Failed to cache discovery result", protocol=protocol, error=str(e))
            return False
    
    async def get_discovery_result(self, protocol: str) -> Optional[Dict]:
        """Get cached discovery results."""
        try:
            discovery_key = self._discovery_key(protocol)
            result_data = await self.cache.get(discovery_key)
            
            if result_data:
                return json.loads(result_data)
            
            return None
        except Exception as e:
            self.logger.error("Failed to get discovery result from cache", protocol=protocol, error=str(e))
            return None
    
    async def clear_all(self) -> bool:
        """Clear all cached data."""
        return await self.cache.clear()
    
    async def get_cached_devices(self) -> List[Device]:
        """Get all cached devices."""
        try:
            device_keys = await self.cache.keys("device:*")
            devices = []
            
            for key in device_keys:
                device_data = await self.cache.get(key)
                if device_data:
                    data = json.loads(device_data)
                    device = self._dict_to_device(data)
                    devices.append(device)
            
            return devices
        except Exception as e:
            self.logger.error("Failed to get cached devices", error=str(e))
            return []
    
    def _dict_to_device(self, data: Dict[str, Any]) -> Device:
        """Convert dictionary to Device object."""
        # Parse datetime fields
        discovery_time = datetime.fromisoformat(data['discovery_time'].replace('Z', '+00:00'))
        last_seen = datetime.fromisoformat(data['last_seen'].replace('Z', '+00:00'))
        
        return Device(
            device_id=data['device_id'],
            name=data.get('name'),
            device_type=DeviceType(data['device_type']),
            ip_address=data['ip_address'],
            mac_address=data.get('mac_address'),
            hostname=data.get('hostname'),
            ports=data.get('ports', []),
            discovery_protocol=data['discovery_protocol'],
            discovery_time=discovery_time,
            last_seen=last_seen,
            status=DeviceStatus(data['status']),
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            firmware_version=data.get('firmware_version'),
            services=data.get('services', []),
            capabilities=data.get('capabilities', {}),
            metadata=data.get('metadata', {})
        )
