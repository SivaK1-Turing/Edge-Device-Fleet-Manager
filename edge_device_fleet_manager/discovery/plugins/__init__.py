"""
Discovery Plugin System

This module provides a hot-reloadable plugin architecture for device discovery.
Plugins can be dynamically loaded, configured, and managed at runtime without
requiring system restarts.

Key Features:
- Hot-reloadable plugin loading
- Plugin lifecycle management
- Configuration management per plugin
- Plugin status monitoring
- Dependency resolution
- Error isolation and recovery
"""

from .base import (
    DiscoveryPlugin,
    PluginConfig,
    PluginStatus,
    PluginMetadata,
    PluginError
)

from .manager import (
    PluginManager,
    PluginRegistry,
    PluginLoader,
    PluginWatcher
)

from .decorators import (
    discovery_plugin,
    plugin_config,
    plugin_dependency,
    plugin_hook
)

__all__ = [
    # Base plugin system
    "DiscoveryPlugin",
    "PluginConfig", 
    "PluginStatus",
    "PluginMetadata",
    "PluginError",
    
    # Plugin management
    "PluginManager",
    "PluginRegistry",
    "PluginLoader",
    "PluginWatcher",
    
    # Plugin decorators
    "discovery_plugin",
    "plugin_config",
    "plugin_dependency", 
    "plugin_hook"
]
