"""
Base plugin system for discovery protocols.

This module defines the core plugin architecture including base classes,
configuration management, and plugin lifecycle hooks.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
from uuid import uuid4

from ...core.logging import get_logger
from ..core import DiscoveryResult, Device


class PluginStatus(Enum):
    """Plugin status enumeration."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADING = "unloading"
    CANCELLED = "cancelled"


@dataclass
class PluginMetadata:
    """Plugin metadata information."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    supported_protocols: List[str] = field(default_factory=list)
    min_python_version: str = "3.8"
    plugin_api_version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    license: Optional[str] = None


@dataclass
class PluginConfig:
    """Plugin configuration container."""
    plugin_name: str
    enabled: bool = True
    priority: int = 100
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    config_data: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config_data[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        self.config_data.update(config_dict)


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    
    def __init__(self, plugin_name: str, message: str, cause: Optional[Exception] = None):
        self.plugin_name = plugin_name
        self.cause = cause
        super().__init__(f"Plugin '{plugin_name}': {message}")


class DiscoveryPlugin(ABC):
    """
    Base class for all discovery plugins.
    
    Discovery plugins extend the core discovery system with additional
    protocols, device types, or discovery methods. They can be loaded
    dynamically and configured at runtime.
    """
    
    def __init__(self, config: PluginConfig):
        self.config = config
        self.status = PluginStatus.UNLOADED
        self.logger = get_logger(f"{__name__}.{config.plugin_name}")
        self.metadata: Optional[PluginMetadata] = None
        self.last_error: Optional[Exception] = None
        self.load_time: Optional[datetime] = None
        self.discovery_count = 0
        self.error_count = 0
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the plugin.
        
        This method is called when the plugin is first loaded.
        Use this to set up resources, validate configuration, etc.
        """
        pass
    
    @abstractmethod
    async def discover(self, **kwargs) -> DiscoveryResult:
        """
        Perform device discovery.
        
        Args:
            **kwargs: Discovery parameters
            
        Returns:
            DiscoveryResult: Discovery results
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up plugin resources.
        
        This method is called when the plugin is being unloaded.
        Use this to close connections, release resources, etc.
        """
        pass
    
    async def validate_config(self) -> List[str]:
        """
        Validate plugin configuration.
        
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic validation
        if not self.config.plugin_name:
            errors.append("Plugin name is required")
        
        if self.config.timeout <= 0:
            errors.append("Timeout must be positive")
        
        if self.config.retry_count < 0:
            errors.append("Retry count cannot be negative")
        
        if self.config.retry_delay < 0:
            errors.append("Retry delay cannot be negative")
        
        return errors
    
    async def is_available(self) -> bool:
        """
        Check if the plugin is available for use.
        
        Returns:
            bool: True if plugin is available
        """
        return self.status == PluginStatus.ACTIVE
    
    async def get_supported_protocols(self) -> List[str]:
        """
        Get list of supported discovery protocols.
        
        Returns:
            List[str]: Supported protocol names
        """
        if self.metadata:
            return self.metadata.supported_protocols
        return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get plugin statistics.
        
        Returns:
            Dict[str, Any]: Plugin statistics
        """
        return {
            "plugin_name": self.config.plugin_name,
            "status": self.status.value,
            "discovery_count": self.discovery_count,
            "error_count": self.error_count,
            "load_time": self.load_time.isoformat() if self.load_time else None,
            "last_error": str(self.last_error) if self.last_error else None,
            "config": {
                "enabled": self.config.enabled,
                "priority": self.config.priority,
                "timeout": self.config.timeout
            }
        }
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """
        Register a hook for plugin events.
        
        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    async def trigger_hook(self, event: str, *args, **kwargs) -> None:
        """
        Trigger plugin hooks for an event.
        
        Args:
            event: Event name
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        "Hook callback failed",
                        event=event,
                        error=str(e),
                        exc_info=e
                    )
    
    async def _set_status(self, status: PluginStatus, error: Optional[Exception] = None) -> None:
        """Set plugin status with optional error."""
        async with self._lock:
            self.status = status
            if error:
                self.last_error = error
                self.error_count += 1
            
            await self.trigger_hook("status_changed", status, error)
    
    async def load(self) -> None:
        """Load the plugin."""
        try:
            await self._set_status(PluginStatus.LOADING)
            
            # Validate configuration
            errors = await self.validate_config()
            if errors:
                raise PluginError(
                    self.config.plugin_name,
                    f"Configuration validation failed: {', '.join(errors)}"
                )
            
            # Initialize plugin
            await self.initialize()
            
            self.load_time = datetime.now(timezone.utc)
            await self._set_status(PluginStatus.LOADED)
            
            self.logger.info("Plugin loaded successfully")
            
        except Exception as e:
            await self._set_status(PluginStatus.ERROR, e)
            raise PluginError(self.config.plugin_name, f"Failed to load: {str(e)}", e)
    
    async def activate(self) -> None:
        """Activate the plugin."""
        if self.status != PluginStatus.LOADED:
            raise PluginError(self.config.plugin_name, "Plugin must be loaded before activation")
        
        try:
            await self._set_status(PluginStatus.ACTIVE)
            await self.trigger_hook("activated")
            self.logger.info("Plugin activated")
            
        except Exception as e:
            await self._set_status(PluginStatus.ERROR, e)
            raise PluginError(self.config.plugin_name, f"Failed to activate: {str(e)}", e)
    
    async def deactivate(self) -> None:
        """Deactivate the plugin."""
        if self.status == PluginStatus.ACTIVE:
            try:
                await self._set_status(PluginStatus.INACTIVE)
                await self.trigger_hook("deactivated")
                self.logger.info("Plugin deactivated")
                
            except Exception as e:
                await self._set_status(PluginStatus.ERROR, e)
                raise PluginError(self.config.plugin_name, f"Failed to deactivate: {str(e)}", e)
    
    async def unload(self) -> None:
        """Unload the plugin."""
        try:
            await self._set_status(PluginStatus.UNLOADING)
            
            # Clean up resources
            await self.cleanup()
            
            await self._set_status(PluginStatus.UNLOADED)
            await self.trigger_hook("unloaded")
            
            self.logger.info("Plugin unloaded successfully")
            
        except Exception as e:
            await self._set_status(PluginStatus.ERROR, e)
            raise PluginError(self.config.plugin_name, f"Failed to unload: {str(e)}", e)
    
    async def reload(self) -> None:
        """Reload the plugin."""
        self.logger.info("Reloading plugin")
        
        # Deactivate if active
        if self.status == PluginStatus.ACTIVE:
            await self.deactivate()
        
        # Unload if loaded
        if self.status in [PluginStatus.LOADED, PluginStatus.INACTIVE]:
            await self.unload()
        
        # Reload
        await self.load()
        await self.activate()
    
    def __str__(self) -> str:
        """String representation of the plugin."""
        return f"DiscoveryPlugin(name={self.config.plugin_name}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the plugin."""
        return (
            f"DiscoveryPlugin("
            f"name={self.config.plugin_name}, "
            f"status={self.status.value}, "
            f"priority={self.config.priority}, "
            f"enabled={self.config.enabled}"
            f")"
        )
