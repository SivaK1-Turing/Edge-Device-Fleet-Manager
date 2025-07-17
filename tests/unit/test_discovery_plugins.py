"""
Unit tests for discovery plugin system.

Tests the plugin architecture including:
- Plugin base classes and lifecycle
- Plugin manager functionality
- Plugin loading and unloading
- Hot-reload capabilities
- Plugin decorators
- Configuration management
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from edge_device_fleet_manager.discovery.plugins.base import (
    DiscoveryPlugin, PluginConfig, PluginStatus, PluginMetadata, PluginError
)
from edge_device_fleet_manager.discovery.plugins.manager import (
    PluginManager, PluginRegistry, PluginLoader
)
from edge_device_fleet_manager.discovery.plugins.decorators import (
    discovery_plugin, plugin_config, plugin_dependency, plugin_hook
)
from edge_device_fleet_manager.discovery.core import DiscoveryResult, Device, DeviceStatus


class TestPluginConfig:
    """Test plugin configuration."""
    
    def test_plugin_config_creation(self):
        """Test plugin configuration creation."""
        config = PluginConfig(
            plugin_name="test_plugin",
            enabled=True,
            priority=100,
            timeout=30.0
        )
        
        assert config.plugin_name == "test_plugin"
        assert config.enabled is True
        assert config.priority == 100
        assert config.timeout == 30.0
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert isinstance(config.config_data, dict)
    
    def test_config_get_set(self):
        """Test configuration get/set methods."""
        config = PluginConfig(plugin_name="test")
        
        # Test get with default
        assert config.get("nonexistent", "default") == "default"
        assert config.get("nonexistent") is None
        
        # Test set and get
        config.set("key1", "value1")
        assert config.get("key1") == "value1"
        
        # Test update
        config.update({"key2": "value2", "key3": "value3"})
        assert config.get("key2") == "value2"
        assert config.get("key3") == "value3"


class TestPluginMetadata:
    """Test plugin metadata."""
    
    def test_metadata_creation(self):
        """Test plugin metadata creation."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            dependencies=["dep1", "dep2"],
            supported_protocols=["http", "https"]
        )
        
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Test plugin"
        assert metadata.author == "Test Author"
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.supported_protocols == ["http", "https"]
        assert metadata.min_python_version == "3.8"
        assert metadata.plugin_api_version == "1.0"


class MockDiscoveryPlugin(DiscoveryPlugin):
    """Mock discovery plugin for testing."""
    
    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.initialize_called = False
        self.discover_called = False
        self.cleanup_called = False
        self.discover_result = DiscoveryResult(protocol="mock", success=True)
    
    async def initialize(self):
        """Mock initialize."""
        self.initialize_called = True
    
    async def discover(self, **kwargs):
        """Mock discover."""
        self.discover_called = True
        return self.discover_result
    
    async def cleanup(self):
        """Mock cleanup."""
        self.cleanup_called = True


class TestDiscoveryPlugin:
    """Test discovery plugin base class."""
    
    @pytest.fixture
    def plugin_config(self):
        """Create plugin configuration."""
        return PluginConfig(plugin_name="test_plugin")
    
    @pytest.fixture
    def plugin(self, plugin_config):
        """Create mock plugin."""
        return MockDiscoveryPlugin(plugin_config)
    
    def test_plugin_creation(self, plugin):
        """Test plugin creation."""
        assert plugin.config.plugin_name == "test_plugin"
        assert plugin.status == PluginStatus.UNLOADED
        assert plugin.metadata is None
        assert plugin.last_error is None
        assert plugin.load_time is None
        assert plugin.discovery_count == 0
        assert plugin.error_count == 0
    
    async def test_plugin_validation(self, plugin):
        """Test plugin configuration validation."""
        # Valid configuration
        errors = await plugin.validate_config()
        assert len(errors) == 0
        
        # Invalid configuration
        plugin.config.plugin_name = ""
        plugin.config.timeout = -1
        plugin.config.retry_count = -1
        plugin.config.retry_delay = -1
        
        errors = await plugin.validate_config()
        assert len(errors) == 4
        assert any("Plugin name is required" in error for error in errors)
        assert any("Timeout must be positive" in error for error in errors)
        assert any("Retry count cannot be negative" in error for error in errors)
        assert any("Retry delay cannot be negative" in error for error in errors)
    
    async def test_plugin_lifecycle(self, plugin):
        """Test plugin lifecycle management."""
        # Initial state
        assert plugin.status == PluginStatus.UNLOADED
        assert not await plugin.is_available()
        
        # Load plugin
        await plugin.load()
        assert plugin.status == PluginStatus.LOADED
        assert plugin.initialize_called
        assert plugin.load_time is not None
        
        # Activate plugin
        await plugin.activate()
        assert plugin.status == PluginStatus.ACTIVE
        assert await plugin.is_available()
        
        # Deactivate plugin
        await plugin.deactivate()
        assert plugin.status == PluginStatus.INACTIVE
        assert not await plugin.is_available()
        
        # Unload plugin
        await plugin.unload()
        assert plugin.status == PluginStatus.UNLOADED
        assert plugin.cleanup_called
    
    async def test_plugin_reload(self, plugin):
        """Test plugin reload."""
        # Load and activate
        await plugin.load()
        await plugin.activate()
        
        # Reset call flags
        plugin.initialize_called = False
        plugin.cleanup_called = False
        
        # Reload
        await plugin.reload()
        
        assert plugin.status == PluginStatus.ACTIVE
        assert plugin.cleanup_called
        assert plugin.initialize_called
    
    async def test_plugin_error_handling(self, plugin_config):
        """Test plugin error handling."""
        
        class FailingPlugin(DiscoveryPlugin):
            async def initialize(self):
                raise Exception("Initialization failed")
            
            async def discover(self, **kwargs):
                return DiscoveryResult(protocol="test")
            
            async def cleanup(self):
                pass
        
        plugin = FailingPlugin(plugin_config)
        
        # Load should fail
        with pytest.raises(PluginError):
            await plugin.load()
        
        assert plugin.status == PluginStatus.ERROR
        assert plugin.last_error is not None
        assert plugin.error_count == 1
    
    async def test_plugin_hooks(self, plugin):
        """Test plugin hook system."""
        hook_called = False
        hook_args = None
        
        def test_hook(*args, **kwargs):
            nonlocal hook_called, hook_args
            hook_called = True
            hook_args = (args, kwargs)
        
        # Register hook
        plugin.register_hook("test_event", test_hook)
        
        # Trigger hook
        await plugin.trigger_hook("test_event", "arg1", key="value")
        
        assert hook_called
        assert hook_args == (("arg1",), {"key": "value"})
    
    async def test_plugin_statistics(self, plugin):
        """Test plugin statistics."""
        await plugin.load()
        await plugin.activate()
        
        stats = await plugin.get_statistics()
        
        assert stats["plugin_name"] == "test_plugin"
        assert stats["status"] == "active"
        assert stats["discovery_count"] == 0
        assert stats["error_count"] == 0
        assert stats["load_time"] is not None
        assert stats["config"]["enabled"] is True
        assert stats["config"]["priority"] == 100


class TestPluginRegistry:
    """Test plugin registry."""
    
    @pytest.fixture
    def registry(self):
        """Create plugin registry."""
        return PluginRegistry()
    
    @pytest.fixture
    def plugin_metadata(self):
        """Create plugin metadata."""
        return PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            dependencies=["dep1"]
        )
    
    async def test_register_plugin_class(self, registry, plugin_metadata):
        """Test plugin class registration."""
        await registry.register_plugin_class(MockDiscoveryPlugin, plugin_metadata)
        
        # Check registration
        metadata = await registry.get_plugin_metadata("test_plugin")
        assert metadata == plugin_metadata
        
        dependencies = await registry.get_dependencies("test_plugin")
        assert dependencies == {"dep1"}
    
    async def test_create_plugin_instance(self, registry, plugin_metadata):
        """Test plugin instance creation."""
        await registry.register_plugin_class(MockDiscoveryPlugin, plugin_metadata)
        
        config = PluginConfig(plugin_name="test_plugin")
        plugin = await registry.create_plugin_instance("test_plugin", config)
        
        assert isinstance(plugin, MockDiscoveryPlugin)
        assert plugin.config == config
        assert plugin.metadata == plugin_metadata
    
    async def test_dependency_resolution(self, registry):
        """Test dependency resolution."""
        # Register plugins with dependencies
        metadata1 = PluginMetadata(name="plugin1", version="1.0", description="", author="", dependencies=[])
        metadata2 = PluginMetadata(name="plugin2", version="1.0", description="", author="", dependencies=["plugin1"])
        metadata3 = PluginMetadata(name="plugin3", version="1.0", description="", author="", dependencies=["plugin2"])
        
        await registry.register_plugin_class(MockDiscoveryPlugin, metadata1)
        await registry.register_plugin_class(MockDiscoveryPlugin, metadata2)
        await registry.register_plugin_class(MockDiscoveryPlugin, metadata3)
        
        # Test load order resolution
        load_order = await registry.resolve_load_order(["plugin3", "plugin1", "plugin2"])
        assert load_order == ["plugin1", "plugin2", "plugin3"]
    
    async def test_circular_dependency_detection(self, registry):
        """Test circular dependency detection."""
        # Create circular dependency
        metadata1 = PluginMetadata(name="plugin1", version="1.0", description="", author="", dependencies=["plugin2"])
        metadata2 = PluginMetadata(name="plugin2", version="1.0", description="", author="", dependencies=["plugin1"])
        
        await registry.register_plugin_class(MockDiscoveryPlugin, metadata1)
        await registry.register_plugin_class(MockDiscoveryPlugin, metadata2)
        
        # Should raise error for circular dependency
        with pytest.raises(PluginError, match="Circular dependency detected"):
            await registry.resolve_load_order(["plugin1", "plugin2"])


class TestPluginManager:
    """Test plugin manager."""
    
    @pytest.fixture
    def plugin_manager(self, tmp_path):
        """Create plugin manager with temporary directory."""
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        return PluginManager([str(plugin_dir)], enable_hot_reload=False)
    
    async def test_plugin_manager_initialization(self, plugin_manager):
        """Test plugin manager initialization."""
        await plugin_manager.initialize()
        
        # Should be initialized without errors
        stats = await plugin_manager.get_statistics()
        assert stats["running"] is False  # Not started yet
        assert stats["jobs_scheduled"] == 0
    
    async def test_plugin_loading(self, plugin_manager):
        """Test plugin loading."""
        await plugin_manager.initialize()
        
        # Register a plugin class manually for testing
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author"
        )
        await plugin_manager.registry.register_plugin_class(MockDiscoveryPlugin, metadata)
        
        # Load plugin
        plugin = await plugin_manager.load_plugin("test_plugin")
        
        assert isinstance(plugin, MockDiscoveryPlugin)
        assert plugin.status == PluginStatus.LOADED
        
        # Get plugin
        retrieved_plugin = await plugin_manager.get_plugin("test_plugin")
        assert retrieved_plugin == plugin
    
    async def test_plugin_configuration(self, plugin_manager):
        """Test plugin configuration management."""
        config = PluginConfig(
            plugin_name="test_plugin",
            enabled=True,
            priority=50
        )
        
        plugin_manager.set_plugin_config("test_plugin", config)
        retrieved_config = plugin_manager.get_plugin_config("test_plugin")
        
        assert retrieved_config == config
    
    async def test_plugin_manager_shutdown(self, plugin_manager):
        """Test plugin manager shutdown."""
        await plugin_manager.initialize()
        
        # Register and load a plugin
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author"
        )
        await plugin_manager.registry.register_plugin_class(MockDiscoveryPlugin, metadata)
        plugin = await plugin_manager.load_plugin("test_plugin")
        
        # Stop plugin manager
        await plugin_manager.stop()
        
        # Plugin should be unloaded
        assert plugin.status == PluginStatus.UNLOADED


class TestPluginDecorators:
    """Test plugin decorators."""
    
    def test_discovery_plugin_decorator(self):
        """Test discovery plugin decorator."""
        
        @discovery_plugin(
            name="decorated_plugin",
            version="1.0.0",
            description="Decorated plugin",
            author="Test Author",
            supported_protocols=["test"]
        )
        class DecoratedPlugin(DiscoveryPlugin):
            async def initialize(self):
                pass
            
            async def discover(self, **kwargs):
                return DiscoveryResult(protocol="test")
            
            async def cleanup(self):
                pass
        
        # Check metadata was attached
        assert hasattr(DecoratedPlugin, '__plugin_metadata__')
        metadata = DecoratedPlugin.__plugin_metadata__
        
        assert metadata.name == "decorated_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Decorated plugin"
        assert metadata.author == "Test Author"
        assert metadata.supported_protocols == ["test"]
    
    def test_plugin_config_decorator(self):
        """Test plugin config decorator."""
        
        @plugin_config(
            required_keys=["api_key"],
            optional_keys={"timeout": 30}
        )
        class ConfiguredPlugin(DiscoveryPlugin):
            async def initialize(self):
                pass
            
            async def discover(self, **kwargs):
                return DiscoveryResult(protocol="test")
            
            async def cleanup(self):
                pass
        
        # Check config requirements were attached
        assert hasattr(ConfiguredPlugin, '__config_requirements__')
        requirements = ConfiguredPlugin.__config_requirements__
        
        assert requirements["required_keys"] == ["api_key"]
        assert requirements["optional_keys"] == {"timeout": 30}
    
    def test_plugin_dependency_decorator(self):
        """Test plugin dependency decorator."""
        
        @plugin_dependency("base_plugin", "auth_plugin")
        class DependentPlugin(DiscoveryPlugin):
            async def initialize(self):
                pass
            
            async def discover(self, **kwargs):
                return DiscoveryResult(protocol="test")
            
            async def cleanup(self):
                pass
        
        # Check dependencies were stored
        assert hasattr(DependentPlugin, '__pending_dependencies__')
        assert DependentPlugin.__pending_dependencies__ == ["base_plugin", "auth_plugin"]
    
    def test_plugin_hook_decorator(self):
        """Test plugin hook decorator."""
        
        class HookedPlugin(DiscoveryPlugin):
            async def initialize(self):
                pass
            
            async def discover(self, **kwargs):
                return DiscoveryResult(protocol="test")
            
            async def cleanup(self):
                pass
            
            @plugin_hook("device_discovered")
            async def on_device_discovered(self, device):
                pass
        
        # Check hook was marked
        assert hasattr(HookedPlugin.on_device_discovered, '__plugin_hook__')
        assert HookedPlugin.on_device_discovered.__plugin_hook__ == "device_discovered"


class TestPluginIntegration:
    """Test plugin system integration."""
    
    @pytest.fixture
    def plugin_manager(self, tmp_path):
        """Create plugin manager for integration tests."""
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        return PluginManager([str(plugin_dir)], enable_hot_reload=False)
    
    async def test_end_to_end_plugin_workflow(self, plugin_manager):
        """Test complete plugin workflow."""
        await plugin_manager.initialize()
        
        # Create and register plugin
        @discovery_plugin(
            name="integration_plugin",
            version="1.0.0",
            description="Integration test plugin",
            author="Test Author"
        )
        class IntegrationPlugin(DiscoveryPlugin):
            async def initialize(self):
                self.initialized = True
            
            async def discover(self, **kwargs):
                device = Device(
                    ip_address="192.168.1.100",
                    discovery_protocol="integration",
                    name="Test Device",
                    status=DeviceStatus.ONLINE
                )
                result = DiscoveryResult(protocol="integration", success=True)
                result.add_device(device)
                return result
            
            async def cleanup(self):
                self.cleaned_up = True
        
        # Register plugin class
        metadata = IntegrationPlugin.__plugin_metadata__
        await plugin_manager.registry.register_plugin_class(IntegrationPlugin, metadata)
        
        # Load and activate plugin
        plugin = await plugin_manager.load_plugin("integration_plugin")
        await plugin.activate()
        
        # Test discovery
        result = await plugin.discover()
        assert result.success
        assert len(result.devices) == 1
        assert result.devices[0].name == "Test Device"
        
        # Test statistics
        stats = await plugin.get_statistics()
        assert stats["plugin_name"] == "integration_plugin"
        assert stats["status"] == "active"
        
        # Cleanup
        await plugin_manager.stop()
        assert plugin.status == PluginStatus.UNLOADED
