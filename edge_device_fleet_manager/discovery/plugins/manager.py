"""
Plugin Manager for Discovery System

This module provides comprehensive plugin management including:
- Dynamic plugin loading and unloading
- Plugin lifecycle management
- Configuration management
- Dependency resolution
- Hot-reloading capabilities
- Plugin registry and discovery
"""

import asyncio
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Type, Any, Callable
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
import inspect

from ...core.logging import get_logger
from .base import DiscoveryPlugin, PluginConfig, PluginStatus, PluginMetadata, PluginError


class PluginRegistry:
    """Registry for managing plugin metadata and instances."""
    
    def __init__(self):
        self._plugins: Dict[str, DiscoveryPlugin] = {}
        self._plugin_classes: Dict[str, Type[DiscoveryPlugin]] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def register_plugin_class(self, plugin_class: Type[DiscoveryPlugin], metadata: PluginMetadata) -> None:
        """Register a plugin class with metadata."""
        async with self._lock:
            name = metadata.name
            self._plugin_classes[name] = plugin_class
            self._metadata[name] = metadata
            self._dependencies[name] = set(metadata.dependencies)
            
            # Update dependents
            for dep in metadata.dependencies:
                if dep not in self._dependents:
                    self._dependents[dep] = set()
                self._dependents[dep].add(name)
            
            self.logger.info("Registered plugin class", plugin=name, version=metadata.version)
    
    async def create_plugin_instance(self, name: str, config: PluginConfig) -> DiscoveryPlugin:
        """Create a plugin instance from registered class."""
        async with self._lock:
            if name not in self._plugin_classes:
                raise PluginError(name, "Plugin class not registered")
            
            plugin_class = self._plugin_classes[name]
            plugin = plugin_class(config)
            plugin.metadata = self._metadata[name]
            
            self._plugins[name] = plugin
            return plugin
    
    async def get_plugin(self, name: str) -> Optional[DiscoveryPlugin]:
        """Get plugin instance by name."""
        async with self._lock:
            return self._plugins.get(name)
    
    async def get_all_plugins(self) -> Dict[str, DiscoveryPlugin]:
        """Get all plugin instances."""
        async with self._lock:
            return self._plugins.copy()
    
    async def remove_plugin(self, name: str) -> bool:
        """Remove plugin from registry."""
        async with self._lock:
            if name in self._plugins:
                del self._plugins[name]
                return True
            return False
    
    async def get_plugin_metadata(self, name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata."""
        async with self._lock:
            return self._metadata.get(name)
    
    async def get_dependencies(self, name: str) -> Set[str]:
        """Get plugin dependencies."""
        async with self._lock:
            return self._dependencies.get(name, set()).copy()
    
    async def get_dependents(self, name: str) -> Set[str]:
        """Get plugins that depend on this plugin."""
        async with self._lock:
            return self._dependents.get(name, set()).copy()
    
    async def resolve_load_order(self, plugins: List[str]) -> List[str]:
        """Resolve plugin load order based on dependencies."""
        async with self._lock:
            visited = set()
            temp_visited = set()
            result = []
            
            def visit(plugin_name: str):
                if plugin_name in temp_visited:
                    raise PluginError(plugin_name, "Circular dependency detected")
                if plugin_name in visited:
                    return
                
                temp_visited.add(plugin_name)
                
                # Visit dependencies first
                for dep in self._dependencies.get(plugin_name, set()):
                    if dep in plugins:  # Only consider plugins we're loading
                        visit(dep)
                
                temp_visited.remove(plugin_name)
                visited.add(plugin_name)
                result.append(plugin_name)
            
            for plugin_name in plugins:
                if plugin_name not in visited:
                    visit(plugin_name)
            
            return result


class PluginLoader:
    """Dynamic plugin loader with hot-reload support."""
    
    def __init__(self, plugin_directories: List[str]):
        self.plugin_directories = [Path(d) for d in plugin_directories]
        self.logger = get_logger(__name__)
        self._loaded_modules: Dict[str, Any] = {}
    
    async def discover_plugins(self) -> List[Type[DiscoveryPlugin]]:
        """Discover plugin classes in plugin directories."""
        plugin_classes = []
        
        for plugin_dir in self.plugin_directories:
            if not plugin_dir.exists():
                self.logger.warning("Plugin directory does not exist", path=str(plugin_dir))
                continue
            
            # Add plugin directory to Python path
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))
            
            # Scan for Python files
            for py_file in plugin_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                
                try:
                    classes = await self._load_plugin_file(py_file)
                    plugin_classes.extend(classes)
                except Exception as e:
                    self.logger.error(
                        "Failed to load plugin file",
                        file=str(py_file),
                        error=str(e),
                        exc_info=e
                    )
        
        return plugin_classes
    
    async def _load_plugin_file(self, file_path: Path) -> List[Type[DiscoveryPlugin]]:
        """Load plugin classes from a Python file."""
        module_name = f"plugin_{file_path.stem}_{id(file_path)}"
        
        # Load module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            raise PluginError(module_name, f"Cannot load module from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        self._loaded_modules[str(file_path)] = module
        
        spec.loader.exec_module(module)
        
        # Find plugin classes
        plugin_classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, DiscoveryPlugin) and 
                obj is not DiscoveryPlugin and 
                hasattr(obj, '__plugin_metadata__')):
                plugin_classes.append(obj)
        
        return plugin_classes
    
    async def reload_plugin_file(self, file_path: Path) -> List[Type[DiscoveryPlugin]]:
        """Reload a plugin file."""
        module_path = str(file_path)
        
        if module_path in self._loaded_modules:
            # Reload existing module
            module = self._loaded_modules[module_path]
            importlib.reload(module)
        
        return await self._load_plugin_file(file_path)


class PluginWatcher(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """File system watcher for plugin hot-reloading."""
    
    def __init__(self, plugin_manager: 'PluginManager'):
        self.plugin_manager = plugin_manager
        self.logger = get_logger(__name__)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.py'):
            self.logger.info("Plugin file modified", file=event.src_path)
            asyncio.create_task(self.plugin_manager.reload_plugin_file(Path(event.src_path)))
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.py'):
            self.logger.info("New plugin file created", file=event.src_path)
            asyncio.create_task(self.plugin_manager.discover_new_plugins())


class PluginManager:
    """
    Comprehensive plugin manager for the discovery system.
    
    Provides:
    - Dynamic plugin loading and unloading
    - Hot-reload capabilities
    - Dependency management
    - Configuration management
    - Plugin lifecycle management
    """
    
    def __init__(self, plugin_directories: List[str], enable_hot_reload: bool = True):
        self.registry = PluginRegistry()
        self.loader = PluginLoader(plugin_directories)
        self.plugin_directories = plugin_directories
        self.enable_hot_reload = enable_hot_reload
        self.logger = get_logger(__name__)
        
        # File system watcher for hot-reload
        self._observer: Optional[Observer] = None
        self._watcher: Optional[PluginWatcher] = None
        
        # Plugin configurations
        self._configs: Dict[str, PluginConfig] = {}
        
        # Event hooks
        self._hooks: Dict[str, List[Callable]] = {}
    
    async def initialize(self) -> None:
        """Initialize the plugin manager."""
        self.logger.info("Initializing plugin manager")
        
        # Discover and register plugins
        await self.discover_plugins()
        
        # Start file system watcher if hot-reload is enabled
        if self.enable_hot_reload and WATCHDOG_AVAILABLE:
            await self._start_file_watcher()
        elif self.enable_hot_reload and not WATCHDOG_AVAILABLE:
            self.logger.warning("Hot-reload requested but watchdog not available")
        
        self.logger.info("Plugin manager initialized")
    
    async def discover_plugins(self) -> None:
        """Discover and register all plugins."""
        plugin_classes = await self.loader.discover_plugins()
        
        for plugin_class in plugin_classes:
            metadata = getattr(plugin_class, '__plugin_metadata__', None)
            if metadata:
                await self.registry.register_plugin_class(plugin_class, metadata)
    
    async def discover_new_plugins(self) -> None:
        """Discover and register new plugins (for hot-reload)."""
        await self.discover_plugins()
        await self.trigger_hook("plugins_discovered")
    
    async def load_plugin(self, name: str, config: Optional[PluginConfig] = None) -> DiscoveryPlugin:
        """Load a plugin by name."""
        if not config:
            config = self._configs.get(name, PluginConfig(plugin_name=name))
        
        plugin = await self.registry.create_plugin_instance(name, config)
        await plugin.load()
        
        await self.trigger_hook("plugin_loaded", plugin)
        return plugin
    
    async def load_plugins(self, plugin_names: List[str]) -> Dict[str, DiscoveryPlugin]:
        """Load multiple plugins with dependency resolution."""
        # Resolve load order
        load_order = await self.registry.resolve_load_order(plugin_names)
        
        loaded_plugins = {}
        for name in load_order:
            try:
                plugin = await self.load_plugin(name)
                loaded_plugins[name] = plugin
                self.logger.info("Plugin loaded", plugin=name)
            except Exception as e:
                self.logger.error("Failed to load plugin", plugin=name, error=str(e), exc_info=e)
                # Continue loading other plugins
        
        return loaded_plugins
    
    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        plugin = await self.registry.get_plugin(name)
        if not plugin:
            return False
        
        # Check for dependents
        dependents = await self.registry.get_dependents(name)
        active_dependents = []
        
        for dependent in dependents:
            dep_plugin = await self.registry.get_plugin(dependent)
            if dep_plugin and dep_plugin.status == PluginStatus.ACTIVE:
                active_dependents.append(dependent)
        
        if active_dependents:
            raise PluginError(
                name,
                f"Cannot unload plugin with active dependents: {', '.join(active_dependents)}"
            )
        
        await plugin.unload()
        await self.registry.remove_plugin(name)
        
        await self.trigger_hook("plugin_unloaded", name)
        return True
    
    async def reload_plugin(self, name: str) -> Optional[DiscoveryPlugin]:
        """Reload a plugin."""
        plugin = await self.registry.get_plugin(name)
        if plugin:
            await plugin.reload()
            await self.trigger_hook("plugin_reloaded", plugin)
            return plugin
        return None
    
    async def reload_plugin_file(self, file_path: Path) -> None:
        """Reload plugins from a specific file."""
        try:
            plugin_classes = await self.loader.reload_plugin_file(file_path)
            
            for plugin_class in plugin_classes:
                metadata = getattr(plugin_class, '__plugin_metadata__', None)
                if metadata:
                    # Re-register plugin class
                    await self.registry.register_plugin_class(plugin_class, metadata)
                    
                    # Reload plugin instance if it exists
                    plugin = await self.registry.get_plugin(metadata.name)
                    if plugin:
                        await plugin.reload()
            
            self.logger.info("Plugin file reloaded", file=str(file_path))
            
        except Exception as e:
            self.logger.error(
                "Failed to reload plugin file",
                file=str(file_path),
                error=str(e),
                exc_info=e
            )
    
    async def get_plugin(self, name: str) -> Optional[DiscoveryPlugin]:
        """Get a plugin by name."""
        return await self.registry.get_plugin(name)
    
    async def get_all_plugins(self) -> Dict[str, DiscoveryPlugin]:
        """Get all loaded plugins."""
        return await self.registry.get_all_plugins()
    
    async def get_active_plugins(self) -> Dict[str, DiscoveryPlugin]:
        """Get all active plugins."""
        all_plugins = await self.registry.get_all_plugins()
        return {
            name: plugin for name, plugin in all_plugins.items()
            if plugin.status == PluginStatus.ACTIVE
        }
    
    def set_plugin_config(self, name: str, config: PluginConfig) -> None:
        """Set plugin configuration."""
        self._configs[name] = config
    
    def get_plugin_config(self, name: str) -> Optional[PluginConfig]:
        """Get plugin configuration."""
        return self._configs.get(name)
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """Register a hook for plugin manager events."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    async def trigger_hook(self, event: str, *args, **kwargs) -> None:
        """Trigger plugin manager hooks."""
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
    
    async def _start_file_watcher(self) -> None:
        """Start file system watcher for hot-reload."""
        if self._observer:
            return
        
        self._watcher = PluginWatcher(self)
        self._observer = Observer()
        
        for plugin_dir in self.plugin_directories:
            if Path(plugin_dir).exists():
                self._observer.schedule(self._watcher, str(plugin_dir), recursive=True)
        
        self._observer.start()
        self.logger.info("Plugin file watcher started")
    
    async def stop(self) -> None:
        """Stop the plugin manager."""
        # Stop file watcher
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        # Unload all plugins
        plugins = await self.registry.get_all_plugins()
        for name in plugins:
            try:
                await self.unload_plugin(name)
            except Exception as e:
                self.logger.error("Failed to unload plugin during shutdown", plugin=name, error=str(e))
        
        self.logger.info("Plugin manager stopped")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get plugin manager statistics."""
        plugins = await self.registry.get_all_plugins()
        return {
            "running": self._observer is not None,
            "jobs_scheduled": 0,  # Placeholder for compatibility
            "plugins_loaded": len(self.registry._plugins),
            "plugins_registered": len(plugins),
            "plugin_directories": self.plugin_directories,
            "hot_reload_enabled": self.enable_hot_reload
        }
