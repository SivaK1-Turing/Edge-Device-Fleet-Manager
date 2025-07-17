"""
Unit tests for discovery configuration system.

Tests the configuration management including:
- Configuration classes and validation
- Environment variable support
- Protocol-specific configurations
- Security settings
- Configuration serialization
"""

import os
import pytest
from unittest.mock import patch

from edge_device_fleet_manager.discovery.config import (
    NetworkConfig, TimingConfig, ProtocolConfig, PluginConfig,
    SecurityConfig, DiscoveryConfig
)


class TestNetworkConfig:
    """Test network configuration."""
    
    def test_network_config_creation(self):
        """Test network configuration creation."""
        config = NetworkConfig(
            ip_ranges=["192.168.1.0/24", "10.0.0.0/16"],
            interface="eth0",
            dns_servers=["8.8.8.8", "1.1.1.1"],
            connect_timeout=10.0,
            max_concurrent_connections=100
        )
        
        assert config.ip_ranges == ["192.168.1.0/24", "10.0.0.0/16"]
        assert config.interface == "eth0"
        assert config.dns_servers == ["8.8.8.8", "1.1.1.1"]
        assert config.connect_timeout == 10.0
        assert config.max_concurrent_connections == 100
    
    def test_network_config_defaults(self):
        """Test network configuration defaults."""
        config = NetworkConfig()
        
        assert config.ip_ranges == ["192.168.1.0/24"]
        assert config.interface is None
        assert config.dns_servers == ["8.8.8.8", "1.1.1.1"]
        assert config.connect_timeout == 5.0
        assert config.read_timeout == 10.0
        assert config.max_concurrent_connections == 50
        assert config.ping_enabled is True
        assert config.arp_scan_enabled is True
        assert config.port_scan_enabled is True
        assert len(config.common_ports) > 0
    
    def test_network_config_validation(self):
        """Test network configuration validation."""
        # Valid configuration
        config = NetworkConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = NetworkConfig(
            ip_ranges=[],
            connect_timeout=-1,
            read_timeout=-1,
            max_concurrent_connections=-1
        )
        
        errors = config.validate()
        assert len(errors) == 4
        assert any("IP range must be specified" in error for error in errors)
        assert any("Connect timeout must be positive" in error for error in errors)
        assert any("Read timeout must be positive" in error for error in errors)
        assert any("Max concurrent connections must be positive" in error for error in errors)


class TestTimingConfig:
    """Test timing configuration."""
    
    def test_timing_config_creation(self):
        """Test timing configuration creation."""
        config = TimingConfig(
            discovery_interval=600,
            protocol_timeout=60.0,
            max_retries=5,
            adaptive_timing_enabled=True
        )
        
        assert config.discovery_interval == 600
        assert config.protocol_timeout == 60.0
        assert config.max_retries == 5
        assert config.adaptive_timing_enabled is True
    
    def test_timing_config_defaults(self):
        """Test timing configuration defaults."""
        config = TimingConfig()
        
        assert config.discovery_interval == 300
        assert config.quick_scan_interval == 60
        assert config.deep_scan_interval == 3600
        assert config.protocol_timeout == 30.0
        assert config.total_timeout == 300.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff_factor == 2.0
        assert config.adaptive_timing_enabled is True
        assert config.jitter_enabled is True
    
    def test_timing_config_validation(self):
        """Test timing configuration validation."""
        # Valid configuration
        config = TimingConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = TimingConfig(
            discovery_interval=-1,
            protocol_timeout=-1,
            total_timeout=-1,
            max_retries=-1,
            adaptive_timing_enabled=True,
            min_interval=-1,
            max_interval=10  # Less than min_interval default
        )
        
        errors = config.validate()
        assert len(errors) >= 5
        assert any("interval must be positive" in error.lower() for error in errors)
        assert any("timeout must be positive" in error.lower() for error in errors)
        assert any("retries cannot be negative" in error.lower() for error in errors)


class TestProtocolConfig:
    """Test protocol configuration."""
    
    def test_protocol_config_creation(self):
        """Test protocol configuration creation."""
        config = ProtocolConfig(
            enabled=True,
            priority=90,
            timeout=45.0,
            settings={"key1": "value1"},
            credentials={"username": "user", "password": "pass"}
        )
        
        assert config.enabled is True
        assert config.priority == 90
        assert config.timeout == 45.0
        assert config.settings == {"key1": "value1"}
        assert config.credentials == {"username": "user", "password": "pass"}
    
    def test_protocol_config_defaults(self):
        """Test protocol configuration defaults."""
        config = ProtocolConfig()
        
        assert config.enabled is True
        assert config.priority == 100
        assert config.timeout == 30.0
        assert config.settings == {}
        assert config.credentials == {}
        assert config.max_concurrent == 10
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
    
    def test_protocol_config_settings(self):
        """Test protocol configuration settings management."""
        config = ProtocolConfig()
        
        # Test setting and getting
        config.set_setting("timeout", 60)
        assert config.get_setting("timeout") == 60
        
        # Test default value
        assert config.get_setting("nonexistent", "default") == "default"
        assert config.get_setting("nonexistent") is None
    
    def test_protocol_config_credentials(self):
        """Test protocol configuration credentials management."""
        config = ProtocolConfig()
        
        # Test setting and getting credentials
        config.set_credential("api_key", "secret123")
        assert config.get_credential("api_key") == "secret123"
        
        # Test non-existent credential
        assert config.get_credential("nonexistent") is None
    
    def test_protocol_config_validation(self):
        """Test protocol configuration validation."""
        # Valid configuration
        config = ProtocolConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = ProtocolConfig(
            timeout=-1,
            priority=-1,
            max_concurrent=-1,
            retry_count=-1
        )
        
        errors = config.validate()
        assert len(errors) == 4
        assert any("Timeout must be positive" in error for error in errors)
        assert any("Priority cannot be negative" in error for error in errors)
        assert any("Max concurrent must be positive" in error for error in errors)
        assert any("Retry count cannot be negative" in error for error in errors)


class TestPluginConfig:
    """Test plugin configuration."""
    
    def test_plugin_config_creation(self):
        """Test plugin configuration creation."""
        config = PluginConfig(
            plugin_directories=["plugins", "custom_plugins"],
            hot_reload_enabled=True,
            auto_load_plugins=True
        )
        
        assert config.plugin_directories == ["plugins", "custom_plugins"]
        assert config.hot_reload_enabled is True
        assert config.auto_load_plugins is True
    
    def test_plugin_config_defaults(self):
        """Test plugin configuration defaults."""
        config = PluginConfig()
        
        assert config.plugin_directories == ["plugins"]
        assert config.hot_reload_enabled is True
        assert config.reload_check_interval == 5.0
        assert config.auto_load_plugins is True
        assert config.plugin_load_timeout == 30.0
        assert config.plugin_configs == {}
        assert config.allow_external_plugins is False
        assert config.plugin_signature_verification is False
    
    def test_plugin_config_management(self):
        """Test plugin configuration management."""
        config = PluginConfig()
        
        # Test setting and getting plugin config
        plugin_config = {"setting1": "value1", "setting2": 42}
        config.set_plugin_config("test_plugin", plugin_config)
        
        retrieved_config = config.get_plugin_config("test_plugin")
        assert retrieved_config == plugin_config
        
        # Test non-existent plugin config
        empty_config = config.get_plugin_config("nonexistent")
        assert empty_config == {}
    
    def test_plugin_config_validation(self):
        """Test plugin configuration validation."""
        # Valid configuration
        config = PluginConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = PluginConfig(
            plugin_directories=[],
            reload_check_interval=-1,
            plugin_load_timeout=-1
        )
        
        errors = config.validate()
        assert len(errors) == 3
        assert any("plugin directory must be specified" in error.lower() for error in errors)
        assert any("reload check interval must be positive" in error.lower() for error in errors)
        assert any("plugin load timeout must be positive" in error.lower() for error in errors)


class TestSecurityConfig:
    """Test security configuration."""
    
    def test_security_config_creation(self):
        """Test security configuration creation."""
        config = SecurityConfig(
            enable_authentication=True,
            auth_methods=["basic", "digest", "oauth"],
            enable_encryption=True,
            rate_limit_enabled=True
        )
        
        assert config.enable_authentication is True
        assert config.auth_methods == ["basic", "digest", "oauth"]
        assert config.enable_encryption is True
        assert config.rate_limit_enabled is True
    
    def test_security_config_defaults(self):
        """Test security configuration defaults."""
        config = SecurityConfig()
        
        assert config.enable_authentication is False
        assert config.auth_methods == ["basic", "digest"]
        assert config.enable_encryption is False
        assert config.tls_verify_certificates is True
        assert config.tls_ca_bundle is None
        assert config.allowed_networks == []
        assert config.blocked_networks == []
        assert config.rate_limit_enabled is True
        assert config.max_requests_per_second == 10.0
        assert config.max_requests_per_minute == 100.0
        assert config.credential_store == "memory"
        assert config.credential_encryption is True
    
    def test_security_config_validation(self):
        """Test security configuration validation."""
        # Valid configuration
        config = SecurityConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration - authentication enabled but no methods
        config = SecurityConfig(
            enable_authentication=True,
            auth_methods=[],
            rate_limit_enabled=True,
            max_requests_per_second=-1,
            max_requests_per_minute=-1
        )
        
        errors = config.validate()
        assert len(errors) == 3
        assert any("authentication methods must be specified" in error.lower() for error in errors)
        assert any("max requests per second must be positive" in error.lower() for error in errors)
        assert any("max requests per minute must be positive" in error.lower() for error in errors)


class TestDiscoveryConfig:
    """Test main discovery configuration."""
    
    def test_discovery_config_creation(self):
        """Test discovery configuration creation."""
        network_config = NetworkConfig(ip_ranges=["10.0.0.0/8"])
        timing_config = TimingConfig(discovery_interval=600)
        
        config = DiscoveryConfig(
            enabled=True,
            log_level="DEBUG",
            network=network_config,
            timing=timing_config
        )
        
        assert config.enabled is True
        assert config.log_level == "DEBUG"
        assert config.network == network_config
        assert config.timing == timing_config
    
    def test_discovery_config_defaults(self):
        """Test discovery configuration defaults."""
        config = DiscoveryConfig()
        
        assert config.enabled is True
        assert config.log_level == "INFO"
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.timing, TimingConfig)
        assert isinstance(config.plugins, PluginConfig)
        assert isinstance(config.security, SecurityConfig)
        assert config.event_bus_enabled is True
        assert config.event_history_size == 1000
        assert config.scheduler_enabled is True
        assert config.max_concurrent_jobs == 5
        assert config.repository_integration is True
        assert config.auto_register_devices is True
    
    def test_discovery_config_protocol_defaults(self):
        """Test discovery configuration protocol defaults."""
        config = DiscoveryConfig()
        
        # Check default protocols are configured
        assert "mdns" in config.protocols
        assert "ssdp" in config.protocols
        assert "snmp" in config.protocols
        assert "network_scan" in config.protocols
        
        # Check protocol settings
        mdns_config = config.get_protocol_config("mdns")
        assert mdns_config is not None
        assert mdns_config.enabled is True
        assert mdns_config.priority == 90
        
        snmp_config = config.get_protocol_config("snmp")
        assert snmp_config is not None
        assert snmp_config.enabled is False  # Disabled by default for security
    
    def test_protocol_management(self):
        """Test protocol configuration management."""
        config = DiscoveryConfig()
        
        # Test getting protocol config
        mdns_config = config.get_protocol_config("mdns")
        assert mdns_config is not None
        assert mdns_config.enabled is True
        
        # Test setting protocol config
        new_config = ProtocolConfig(enabled=False, priority=50)
        config.set_protocol_config("custom_protocol", new_config)
        
        retrieved_config = config.get_protocol_config("custom_protocol")
        assert retrieved_config == new_config
        
        # Test protocol enabled check
        assert config.is_protocol_enabled("mdns") is True
        assert config.is_protocol_enabled("custom_protocol") is False
        
        # Test getting enabled protocols
        enabled_protocols = config.get_enabled_protocols()
        assert "mdns" in enabled_protocols
        assert "ssdp" in enabled_protocols
        assert "network_scan" in enabled_protocols
        assert "snmp" not in enabled_protocols  # Disabled by default
        assert "custom_protocol" not in enabled_protocols
    
    def test_discovery_config_validation(self):
        """Test discovery configuration validation."""
        # Valid configuration
        config = DiscoveryConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = DiscoveryConfig(
            scheduler_enabled=True,
            max_concurrent_jobs=-1,
            event_bus_enabled=True,
            event_history_size=-1
        )
        
        # Add invalid protocol config
        invalid_protocol = ProtocolConfig(timeout=-1)
        config.set_protocol_config("invalid_protocol", invalid_protocol)
        
        errors = config.validate()
        assert len(errors) >= 3
        assert any("max concurrent jobs must be positive" in error.lower() for error in errors)
        assert any("event history size must be positive" in error.lower() for error in errors)
        assert any("protocol 'invalid_protocol'" in error.lower() for error in errors)
    
    def test_config_from_environment(self):
        """Test configuration creation from environment variables."""
        env_vars = {
            'DISCOVERY_ENABLED': 'false',
            'DISCOVERY_LOG_LEVEL': 'DEBUG',
            'DISCOVERY_IP_RANGES': '192.168.1.0/24,10.0.0.0/16',
            'DISCOVERY_MAX_CONCURRENT': '100',
            'DISCOVERY_INTERVAL': '600',
            'DISCOVERY_PROTOCOL_TIMEOUT': '60.0',
            'DISCOVERY_PLUGIN_DIRS': 'plugins,custom_plugins',
            'DISCOVERY_HOT_RELOAD': 'false',
            'DISCOVERY_MDNS_ENABLED': 'false',
            'DISCOVERY_SNMP_ENABLED': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = DiscoveryConfig.from_env()
            
            assert config.enabled is False
            assert config.log_level == 'DEBUG'
            assert config.network.ip_ranges == ['192.168.1.0/24', '10.0.0.0/16']
            assert config.network.max_concurrent_connections == 100
            assert config.timing.discovery_interval == 600
            assert config.timing.protocol_timeout == 60.0
            assert config.plugins.plugin_directories == ['plugins', 'custom_plugins']
            assert config.plugins.hot_reload_enabled is False
            assert config.protocols['mdns'].enabled is False
            assert config.protocols['snmp'].enabled is True
    
    def test_config_serialization(self):
        """Test configuration serialization to dictionary."""
        config = DiscoveryConfig()
        config_dict = config.to_dict()
        
        # Check main fields
        assert config_dict['enabled'] is True
        assert config_dict['log_level'] == 'INFO'
        
        # Check nested configurations
        assert 'network' in config_dict
        assert 'timing' in config_dict
        assert 'protocols' in config_dict
        assert 'plugins' in config_dict
        
        # Check network config
        network_dict = config_dict['network']
        assert network_dict['ip_ranges'] == ['192.168.1.0/24']
        assert network_dict['max_concurrent_connections'] == 50
        
        # Check protocol configs
        protocols_dict = config_dict['protocols']
        assert 'mdns' in protocols_dict
        assert protocols_dict['mdns']['enabled'] is True
        assert protocols_dict['mdns']['priority'] == 90
    
    def test_config_inheritance(self):
        """Test configuration inheritance from BaseConfig."""
        config = DiscoveryConfig()
        
        # Should inherit from BaseConfig
        assert hasattr(config, 'validate')
        assert callable(config.validate)
        
        # Test validation works
        errors = config.validate()
        assert isinstance(errors, list)
