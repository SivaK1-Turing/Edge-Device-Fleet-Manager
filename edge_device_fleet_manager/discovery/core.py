"""
Core discovery system architecture.

This module defines the fundamental classes and interfaces for the device discovery system,
including device models, registry, and the main discovery engine.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any, AsyncIterator, Callable
from uuid import uuid4

from ..core.logging import get_logger

logger = get_logger(__name__)


class DeviceType(Enum):
    """Types of discoverable devices."""
    UNKNOWN = "unknown"
    IOT_SENSOR = "iot_sensor"
    IOT_GATEWAY = "iot_gateway"
    CAMERA = "camera"
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    PRINTER = "printer"
    MEDIA_SERVER = "media_server"
    SMART_HOME = "smart_home"
    INDUSTRIAL = "industrial"


class DeviceStatus(Enum):
    """Device availability status."""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"


@dataclass
class Device:
    """Represents a discovered device."""
    
    # Core identification
    device_id: str = field(default_factory=lambda: str(uuid4()))
    name: Optional[str] = None
    device_type: DeviceType = DeviceType.UNKNOWN
    
    # Network information
    ip_address: str = ""
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    
    # Discovery metadata
    discovery_protocol: str = ""
    discovery_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: DeviceStatus = DeviceStatus.UNKNOWN
    
    # Device details
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    services: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = datetime.now(timezone.utc)
        self.status = DeviceStatus.ONLINE
    
    def is_stale(self, ttl_seconds: int = 300) -> bool:
        """Check if device information is stale."""
        age = (datetime.now(timezone.utc) - self.last_seen).total_seconds()
        return age > ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary representation."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "hostname": self.hostname,
            "ports": self.ports,
            "discovery_protocol": self.discovery_protocol,
            "discovery_time": self.discovery_time.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "status": self.status.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "services": self.services,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


@dataclass
class DiscoveryResult:
    """Result of a discovery operation."""
    
    devices: List[Device] = field(default_factory=list)
    protocol: str = ""
    duration: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_device(self, device: Device) -> None:
        """Add a device to the result."""
        self.devices.append(device)
    
    def get_device_count(self) -> int:
        """Get the number of discovered devices."""
        return len(self.devices)


class DiscoveryProtocol(ABC):
    """Abstract base class for discovery protocols."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"{__name__}.{name}")
    
    @abstractmethod
    async def discover(self, **kwargs) -> DiscoveryResult:
        """Perform device discovery using this protocol."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this protocol is available on the system."""
        pass
    
    def get_name(self) -> str:
        """Get the protocol name."""
        return self.name


class DeviceRegistry:
    """Registry for managing discovered devices."""
    
    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._ip_to_device: Dict[str, str] = {}  # IP -> device_id mapping
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def add_device(self, device: Device) -> bool:
        """Add or update a device in the registry."""
        async with self._lock:
            # Check if device already exists by IP
            existing_id = self._ip_to_device.get(device.ip_address)
            if existing_id and existing_id in self._devices:
                # Update existing device
                existing_device = self._devices[existing_id]
                existing_device.update_last_seen()
                
                # Merge information
                if device.name and not existing_device.name:
                    existing_device.name = device.name
                if device.hostname and not existing_device.hostname:
                    existing_device.hostname = device.hostname
                if device.mac_address and not existing_device.mac_address:
                    existing_device.mac_address = device.mac_address
                
                # Merge services and ports
                existing_device.services = list(set(existing_device.services + device.services))
                existing_device.ports = list(set(existing_device.ports + device.ports))
                
                # Update capabilities and metadata
                existing_device.capabilities.update(device.capabilities)
                existing_device.metadata.update(device.metadata)
                
                self.logger.debug("Updated existing device", device_id=existing_id, ip=device.ip_address)
                return False  # Not a new device
            else:
                # Add new device
                self._devices[device.device_id] = device
                self._ip_to_device[device.ip_address] = device.device_id
                
                self.logger.info("Added new device", device_id=device.device_id, ip=device.ip_address)
                return True  # New device added
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device by ID."""
        async with self._lock:
            return self._devices.get(device_id)
    
    async def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """Get a device by IP address."""
        async with self._lock:
            device_id = self._ip_to_device.get(ip_address)
            if device_id:
                return self._devices.get(device_id)
            return None
    
    async def get_all_devices(self) -> List[Device]:
        """Get all devices in the registry."""
        async with self._lock:
            return list(self._devices.values())
    
    async def remove_device(self, device_id: str) -> bool:
        """Remove a device from the registry."""
        async with self._lock:
            device = self._devices.get(device_id)
            if device:
                del self._devices[device_id]
                if device.ip_address in self._ip_to_device:
                    del self._ip_to_device[device.ip_address]
                self.logger.info("Removed device", device_id=device_id)
                return True
            return False
    
    async def cleanup_stale_devices(self, ttl_seconds: int = 300) -> int:
        """Remove stale devices from the registry."""
        async with self._lock:
            stale_devices = [
                device_id for device_id, device in self._devices.items()
                if device.is_stale(ttl_seconds)
            ]
            
            for device_id in stale_devices:
                device = self._devices[device_id]
                del self._devices[device_id]
                if device.ip_address in self._ip_to_device:
                    del self._ip_to_device[device.ip_address]
            
            if stale_devices:
                self.logger.info("Cleaned up stale devices", count=len(stale_devices))
            
            return len(stale_devices)
    
    async def get_device_count(self) -> int:
        """Get the total number of devices."""
        async with self._lock:
            return len(self._devices)


class DiscoveryEngine:
    """Main discovery engine that coordinates multiple protocols."""
    
    def __init__(self, config, registry: Optional[DeviceRegistry] = None):
        self.config = config
        self.registry = registry or DeviceRegistry()
        self.protocols: Dict[str, DiscoveryProtocol] = {}
        self.logger = get_logger(__name__)
        self._running = False
        self._discovery_tasks: Set[asyncio.Task] = set()
    
    def register_protocol(self, protocol: DiscoveryProtocol) -> None:
        """Register a discovery protocol."""
        self.protocols[protocol.get_name()] = protocol
        self.logger.info("Registered discovery protocol", protocol=protocol.get_name())
    
    async def discover_all(self, protocols: Optional[List[str]] = None) -> DiscoveryResult:
        """Run discovery using all or specified protocols."""
        start_time = time.time()
        result = DiscoveryResult(protocol="all")
        
        # Use all protocols if none specified
        if protocols is None:
            protocols = list(self.protocols.keys())
        
        # Run discovery protocols concurrently
        tasks = []
        for protocol_name in protocols:
            if protocol_name in self.protocols:
                protocol = self.protocols[protocol_name]
                task = asyncio.create_task(protocol.discover())
                tasks.append((protocol_name, task))
        
        # Collect results
        for protocol_name, task in tasks:
            try:
                protocol_result = await task
                result.devices.extend(protocol_result.devices)
                
                # Add devices to registry
                for device in protocol_result.devices:
                    await self.registry.add_device(device)
                
                self.logger.info(
                    "Protocol discovery completed",
                    protocol=protocol_name,
                    devices_found=len(protocol_result.devices),
                    duration=protocol_result.duration
                )
                
            except Exception as e:
                self.logger.error(
                    "Protocol discovery failed",
                    protocol=protocol_name,
                    error=str(e),
                    exc_info=e
                )
        
        result.duration = time.time() - start_time
        result.metadata["total_protocols"] = len(protocols)
        result.metadata["successful_protocols"] = len([t for _, t in tasks if not t.exception()])
        
        self.logger.info(
            "Discovery completed",
            total_devices=len(result.devices),
            duration=result.duration,
            protocols=len(protocols)
        )
        
        return result
    
    async def get_devices(self) -> List[Device]:
        """Get all discovered devices."""
        return await self.registry.get_all_devices()
    
    async def cleanup_stale_devices(self) -> int:
        """Clean up stale devices."""
        return await self.registry.cleanup_stale_devices(self.config.discovery.cache_ttl)
