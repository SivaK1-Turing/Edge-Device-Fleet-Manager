"""
Watchdog-powered plugin loader with hot-reload capability for Click commands.
"""

import asyncio
import importlib
import importlib.util
import inspect
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

import click
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config, PluginConfig
from .context import app_context
from .logging import get_logger
from .exceptions import PluginError

logger = get_logger(__name__)


class PluginMetadata:
    """Metadata for a plugin."""
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        dependencies: Optional[List[str]] = None,
        commands: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []
        self.commands = commands or []


class Plugin:
    """Base class for plugins."""
    
    metadata: PluginMetadata
    
    def __init__(self) -> None:
        if not hasattr(self, 'metadata'):
            self.metadata = PluginMetadata(
                name=self.__class__.__name__,
                description=f"Plugin: {self.__class__.__name__}"
            )
    
    def initialize(self, config: Config) -> None:
        """Initialize the plugin with configuration."""
        pass
    
    def cleanup(self) -> None:
        """Cleanup resources when plugin is unloaded."""
        pass
    
    def get_commands(self) -> List[click.Command]:
        """Get Click commands provided by this plugin."""
        commands = []
        
        # Find all methods decorated with @click.command
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '__click_params__'):
                commands.append(method)
        
        return commands


class PluginLoadResult:
    """Result of loading a plugin."""
    
    def __init__(
        self,
        success: bool,
        plugin: Optional[Plugin] = None,
        error: Optional[Exception] = None,
        load_time: float = 0.0,
    ) -> None:
        self.success = success
        self.plugin = plugin
        self.error = error
        self.load_time = load_time


class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reload."""
    
    def __init__(self, plugin_loader: 'PluginLoader') -> None:
        self.plugin_loader = plugin_loader
        self.last_reload_time: Dict[str, float] = {}
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.py'):
            return
        
        # Debounce rapid file changes
        now = time.time()
        if event.src_path in self.last_reload_time:
            if now - self.last_reload_time[event.src_path] < self.plugin_loader.config.reload_delay:
                return
        
        self.last_reload_time[event.src_path] = now
        
        logger.info(
            "Plugin file modified, reloading",
            file_path=event.src_path
        )
        
        # Schedule reload
        asyncio.create_task(self.plugin_loader.reload_plugin_from_file(event.src_path))
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.py'):
            return
        
        logger.info(
            "New plugin file detected",
            file_path=event.src_path
        )
        
        # Schedule load
        asyncio.create_task(self.plugin_loader.load_plugin_from_file(event.src_path))
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.py'):
            return
        
        logger.info(
            "Plugin file deleted",
            file_path=event.src_path
        )
        
        # Schedule unload
        asyncio.create_task(self.plugin_loader.unload_plugin_from_file(event.src_path))


class PluginLoader:
    """Plugin loader with hot-reload capability."""
    
    def __init__(self, config: PluginConfig) -> None:
        self.config = config
        self.plugins_dir = Path(config.plugins_dir)
        self.loaded_plugins: Dict[str, Plugin] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.plugin_files: Dict[str, str] = {}  # file_path -> plugin_name
        self.observer: Optional[Observer] = None
        self.cli_group: Optional[click.Group] = None
        
        # Ensure plugins directory exists
        self.plugins_dir.mkdir(exist_ok=True)
    
    def set_cli_group(self, cli_group: click.Group) -> None:
        """Set the CLI group to register commands with."""
        self.cli_group = cli_group
    
    async def start(self) -> None:
        """Start the plugin loader."""
        logger.info("Starting plugin loader", plugins_dir=str(self.plugins_dir))
        
        # Load all existing plugins
        await self.load_all_plugins()
        
        # Start file watcher if auto-reload is enabled
        if self.config.auto_reload:
            await self.start_file_watcher()
    
    async def stop(self) -> None:
        """Stop the plugin loader."""
        logger.info("Stopping plugin loader")
        
        # Stop file watcher
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        # Unload all plugins
        await self.unload_all_plugins()
    
    async def start_file_watcher(self) -> None:
        """Start the file system watcher for hot-reload."""
        if self.observer is not None:
            return
        
        self.observer = Observer()
        handler = PluginFileHandler(self)
        self.observer.schedule(handler, str(self.plugins_dir), recursive=True)
        self.observer.start()
        
        logger.info("Plugin file watcher started")
    
    async def load_all_plugins(self) -> List[PluginLoadResult]:
        """Load all plugins from the plugins directory."""
        results = []
        
        for plugin_file in self.plugins_dir.rglob("*.py"):
            if plugin_file.name.startswith("__"):
                continue
            
            result = await self.load_plugin_from_file(str(plugin_file))
            results.append(result)
        
        logger.info(
            "Loaded plugins",
            total=len(results),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success)
        )
        
        return results
    
    async def load_plugin_from_file(self, file_path: str) -> PluginLoadResult:
        """Load a plugin from a file."""
        start_time = time.time()
        
        try:
            # Get plugin name from file path
            plugin_path = Path(file_path)
            relative_path = plugin_path.relative_to(self.plugins_dir)
            plugin_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
            
            # Check if plugin is already loaded
            if plugin_name in self.loaded_plugins:
                await self.unload_plugin(plugin_name)
            
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if spec is None or spec.loader is None:
                raise PluginError(f"Could not load spec for plugin: {plugin_name}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute the module with timeout
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, spec.loader.exec_module, module
                ),
                timeout=self.config.load_timeout
            )
            
            # Find plugin classes
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj is not Plugin):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                raise PluginError(f"No plugin classes found in: {plugin_name}")
            
            if len(plugin_classes) > 1:
                logger.warning(
                    "Multiple plugin classes found, using first one",
                    plugin_name=plugin_name,
                    classes=[cls.__name__ for cls in plugin_classes]
                )
            
            # Instantiate the plugin
            plugin_class = plugin_classes[0]
            plugin = plugin_class()
            
            # Initialize the plugin
            config = app_context.config
            if config:
                plugin.initialize(config)
            
            # Register the plugin
            self.loaded_plugins[plugin_name] = plugin
            self.plugin_modules[plugin_name] = module
            self.plugin_files[file_path] = plugin_name
            
            # Register commands with CLI
            if self.cli_group:
                commands = plugin.get_commands()
                for command in commands:
                    self.cli_group.add_command(command)
            
            load_time = time.time() - start_time
            
            logger.info(
                "Plugin loaded successfully",
                plugin_name=plugin_name,
                plugin_class=plugin_class.__name__,
                load_time=load_time,
                commands_count=len(plugin.get_commands())
            )
            
            return PluginLoadResult(
                success=True,
                plugin=plugin,
                load_time=load_time
            )
            
        except Exception as e:
            load_time = time.time() - start_time
            
            logger.error(
                "Failed to load plugin",
                file_path=file_path,
                error=str(e),
                load_time=load_time,
                exc_info=e
            )
            
            return PluginLoadResult(
                success=False,
                error=e,
                load_time=load_time
            )
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        try:
            plugin = self.loaded_plugins.get(plugin_name)
            if plugin:
                # Remove commands from CLI
                if self.cli_group:
                    commands = plugin.get_commands()
                    for command in commands:
                        if command.name in self.cli_group.commands:
                            del self.cli_group.commands[command.name]
                
                # Cleanup plugin
                plugin.cleanup()
                
                # Remove from registry
                del self.loaded_plugins[plugin_name]
                
                # Remove module from cache
                if plugin_name in self.plugin_modules:
                    module = self.plugin_modules[plugin_name]
                    if hasattr(module, '__file__') and module.__file__ in sys.modules:
                        del sys.modules[module.__file__]
                    del self.plugin_modules[plugin_name]
                
                logger.info("Plugin unloaded", plugin_name=plugin_name)
                return True
            
        except Exception as e:
            logger.error(
                "Failed to unload plugin",
                plugin_name=plugin_name,
                error=str(e),
                exc_info=e
            )
        
        return False

    async def unload_all_plugins(self) -> None:
        """Unload all plugins."""
        plugin_names = list(self.loaded_plugins.keys())
        for plugin_name in plugin_names:
            await self.unload_plugin(plugin_name)

    async def reload_plugin_from_file(self, file_path: str) -> PluginLoadResult:
        """Reload a plugin from a file."""
        plugin_name = self.plugin_files.get(file_path)
        if plugin_name:
            await self.unload_plugin(plugin_name)

        return await self.load_plugin_from_file(file_path)

    async def unload_plugin_from_file(self, file_path: str) -> bool:
        """Unload a plugin from a file."""
        plugin_name = self.plugin_files.get(file_path)
        if plugin_name:
            result = await self.unload_plugin(plugin_name)
            if result:
                del self.plugin_files[file_path]
            return result
        return False

    def get_loaded_plugins(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return self.loaded_plugins.copy()

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a specific plugin by name."""
        return self.loaded_plugins.get(name)

    def is_plugin_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded."""
        return name in self.loaded_plugins


# Global plugin loader instance
_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> Optional[PluginLoader]:
    """Get the global plugin loader instance."""
    return _plugin_loader


def set_plugin_loader(loader: PluginLoader) -> None:
    """Set the global plugin loader instance."""
    global _plugin_loader
    _plugin_loader = loader


async def initialize_plugin_system(config: PluginConfig, cli_group: click.Group) -> PluginLoader:
    """Initialize the plugin system."""
    loader = PluginLoader(config)
    loader.set_cli_group(cli_group)
    set_plugin_loader(loader)
    await loader.start()
    return loader


async def shutdown_plugin_system() -> None:
    """Shutdown the plugin system."""
    loader = get_plugin_loader()
    if loader:
        await loader.stop()
