"""
Discovery Configuration Management

This module provides comprehensive configuration management for the discovery system,
including protocol-specific settings, network configuration, timing parameters,
and plugin configurations.

Key Features:
- Hierarchical configuration structure
- Environment variable support
- Configuration validation
- Hot-reload capabilities
- Protocol-specific configurations
- Security settings management
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import os
from pathlib import Path

from abc import ABC, abstractmethod


@dataclass
class NetworkConfig:
    """Network configuration for discovery."""
    
    # IP ranges to scan
    ip_ranges: List[str] = field(default_factory=lambda: ["192.168.1.0/24"])
    
    # Network interface to use
    interface: Optional[str] = None
    
    # DNS servers for resolution
    dns_servers: List[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])
    
    # Network timeouts
    connect_timeout: float = 5.0
    read_timeout: float = 10.0
    
    # Concurrent connection limits
    max_concurrent_connections: int = 50
    max_connections_per_host: int = 5
    
    # Port scanning configuration
    common_ports: List[int] = field(default_factory=lambda: [
        22, 23, 53, 80, 135, 139, 443, 445, 993, 995, 1723, 3389, 5900, 8080
    ])
    
    # Network discovery options
    ping_enabled: bool = True
    arp_scan_enabled: bool = True
    port_scan_enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate network configuration."""
        errors = []
        
        if not self.ip_ranges:
            errors.append("At least one IP range must be specified")
        
        if self.connect_timeout <= 0:
            errors.append("Connect timeout must be positive")
        
        if self.read_timeout <= 0:
            errors.append("Read timeout must be positive")
        
        if self.max_concurrent_connections <= 0:
            errors.append("Max concurrent connections must be positive")
        
        return errors


@dataclass
class TimingConfig:
    """Timing configuration for discovery operations."""
    
    # Discovery intervals
    discovery_interval: int = 300  # 5 minutes
    quick_scan_interval: int = 60   # 1 minute
    deep_scan_interval: int = 3600  # 1 hour
    
    # Timeout settings
    protocol_timeout: float = 30.0
    total_timeout: float = 300.0
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    
    # Adaptive timing
    adaptive_timing_enabled: bool = True
    min_interval: int = 30
    max_interval: int = 7200
    
    # Jitter to avoid thundering herd
    jitter_enabled: bool = True
    jitter_max_percent: float = 10.0
    
    def validate(self) -> List[str]:
        """Validate timing configuration."""
        errors = []
        
        if self.discovery_interval <= 0:
            errors.append("Discovery interval must be positive")
        
        if self.protocol_timeout <= 0:
            errors.append("Protocol timeout must be positive")
        
        if self.total_timeout <= 0:
            errors.append("Total timeout must be positive")
        
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.adaptive_timing_enabled:
            if self.min_interval <= 0:
                errors.append("Min interval must be positive")
            if self.max_interval <= self.min_interval:
                errors.append("Max interval must be greater than min interval")
        
        return errors


@dataclass
class ProtocolConfig:
    """Configuration for a specific discovery protocol."""
    
    # Basic settings
    enabled: bool = True
    priority: int = 100
    timeout: float = 30.0
    
    # Protocol-specific settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Security settings
    credentials: Dict[str, str] = field(default_factory=dict)
    
    # Advanced options
    max_concurrent: int = 10
    retry_count: int = 3
    retry_delay: float = 1.0
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a protocol-specific setting."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a protocol-specific setting."""
        self.settings[key] = value
    
    def get_credential(self, key: str) -> Optional[str]:
        """Get a credential value."""
        return self.credentials.get(key)
    
    def set_credential(self, key: str, value: str) -> None:
        """Set a credential value."""
        self.credentials[key] = value
    
    def validate(self) -> List[str]:
        """Validate protocol configuration."""
        errors = []
        
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        
        if self.priority < 0:
            errors.append("Priority cannot be negative")
        
        if self.max_concurrent <= 0:
            errors.append("Max concurrent must be positive")
        
        if self.retry_count < 0:
            errors.append("Retry count cannot be negative")
        
        return errors


@dataclass
class PluginConfig:
    """Configuration for discovery plugins."""
    
    # Plugin directories
    plugin_directories: List[str] = field(default_factory=lambda: ["plugins"])
    
    # Hot-reload settings
    hot_reload_enabled: bool = True
    reload_check_interval: float = 5.0
    
    # Plugin loading
    auto_load_plugins: bool = True
    plugin_load_timeout: float = 30.0
    
    # Plugin-specific configurations
    plugin_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Security settings
    allow_external_plugins: bool = False
    plugin_signature_verification: bool = False
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin."""
        return self.plugin_configs.get(plugin_name, {})
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific plugin."""
        self.plugin_configs[plugin_name] = config
    
    def validate(self) -> List[str]:
        """Validate plugin configuration."""
        errors = []
        
        if not self.plugin_directories:
            errors.append("At least one plugin directory must be specified")
        
        if self.reload_check_interval <= 0:
            errors.append("Reload check interval must be positive")
        
        if self.plugin_load_timeout <= 0:
            errors.append("Plugin load timeout must be positive")
        
        return errors


@dataclass
class SecurityConfig:
    """Security configuration for discovery operations."""
    
    # Authentication
    enable_authentication: bool = False
    auth_methods: List[str] = field(default_factory=lambda: ["basic", "digest"])
    
    # Encryption
    enable_encryption: bool = False
    tls_verify_certificates: bool = True
    tls_ca_bundle: Optional[str] = None
    
    # Access control
    allowed_networks: List[str] = field(default_factory=list)
    blocked_networks: List[str] = field(default_factory=list)
    
    # Rate limiting
    rate_limit_enabled: bool = True
    max_requests_per_second: float = 10.0
    max_requests_per_minute: float = 100.0
    
    # Credential management
    credential_store: str = "memory"  # memory, file, keyring
    credential_encryption: bool = True
    
    def validate(self) -> List[str]:
        """Validate security configuration."""
        errors = []
        
        if self.enable_authentication and not self.auth_methods:
            errors.append("Authentication methods must be specified when authentication is enabled")
        
        if self.rate_limit_enabled:
            if self.max_requests_per_second <= 0:
                errors.append("Max requests per second must be positive")
            if self.max_requests_per_minute <= 0:
                errors.append("Max requests per minute must be positive")
        
        return errors


class BaseConfig(ABC):
    """Base configuration class."""

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        pass


@dataclass
class DiscoveryConfig(BaseConfig):
    """
    Main configuration class for the discovery system.
    
    Provides hierarchical configuration management with validation,
    environment variable support, and hot-reload capabilities.
    """
    
    # Core settings
    enabled: bool = True
    log_level: str = "INFO"
    
    # Component configurations
    network: NetworkConfig = field(default_factory=NetworkConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Protocol configurations
    protocols: Dict[str, ProtocolConfig] = field(default_factory=dict)
    
    # Event system
    event_bus_enabled: bool = True
    event_history_size: int = 1000
    
    # Scheduling
    scheduler_enabled: bool = True
    max_concurrent_jobs: int = 5
    
    # Integration settings
    repository_integration: bool = True
    auto_register_devices: bool = True
    
    def __post_init__(self):
        """Initialize default protocol configurations."""
        
        # Initialize default protocol configurations if not present
        default_protocols = {
            "mdns": ProtocolConfig(
                enabled=True,
                priority=90,
                timeout=10.0,
                settings={
                    "service_types": ["_http._tcp", "_https._tcp", "_ssh._tcp"],
                    "browse_timeout": 5.0
                }
            ),
            "ssdp": ProtocolConfig(
                enabled=True,
                priority=80,
                timeout=15.0,
                settings={
                    "search_targets": ["upnp:rootdevice", "ssdp:all"],
                    "mx_delay": 3
                }
            ),
            "snmp": ProtocolConfig(
                enabled=False,  # Disabled by default due to security concerns
                priority=70,
                timeout=10.0,
                settings={
                    "community": "public",
                    "version": 2,
                    "port": 161,
                    "include_interfaces": True
                }
            ),
            "network_scan": ProtocolConfig(
                enabled=True,
                priority=60,
                timeout=30.0,
                settings={
                    "ping_enabled": True,
                    "port_scan_enabled": True,
                    "service_detection": True
                }
            )
        }
        
        # Add default configurations for protocols not already configured
        for protocol_name, default_config in default_protocols.items():
            if protocol_name not in self.protocols:
                self.protocols[protocol_name] = default_config
    
    def get_protocol_config(self, protocol_name: str) -> Optional[ProtocolConfig]:
        """Get configuration for a specific protocol."""
        return self.protocols.get(protocol_name)
    
    def set_protocol_config(self, protocol_name: str, config: ProtocolConfig) -> None:
        """Set configuration for a specific protocol."""
        self.protocols[protocol_name] = config
    
    def is_protocol_enabled(self, protocol_name: str) -> bool:
        """Check if a protocol is enabled."""
        config = self.get_protocol_config(protocol_name)
        return config is not None and config.enabled
    
    def get_enabled_protocols(self) -> List[str]:
        """Get list of enabled protocols."""
        return [
            name for name, config in self.protocols.items()
            if config.enabled
        ]
    
    def validate(self) -> List[str]:
        """Validate the entire configuration."""
        errors = []
        
        # Validate component configurations
        errors.extend(self.network.validate())
        errors.extend(self.timing.validate())
        errors.extend(self.plugins.validate())
        errors.extend(self.security.validate())
        
        # Validate protocol configurations
        for protocol_name, protocol_config in self.protocols.items():
            protocol_errors = protocol_config.validate()
            for error in protocol_errors:
                errors.append(f"Protocol '{protocol_name}': {error}")
        
        # Cross-validation
        if self.scheduler_enabled and self.max_concurrent_jobs <= 0:
            errors.append("Max concurrent jobs must be positive when scheduler is enabled")
        
        if self.event_bus_enabled and self.event_history_size <= 0:
            errors.append("Event history size must be positive when event bus is enabled")
        
        return errors
    
    @classmethod
    def from_env(cls) -> 'DiscoveryConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Core settings
        config.enabled = os.getenv('DISCOVERY_ENABLED', 'true').lower() == 'true'
        config.log_level = os.getenv('DISCOVERY_LOG_LEVEL', 'INFO')
        
        # Network settings
        if ip_ranges := os.getenv('DISCOVERY_IP_RANGES'):
            config.network.ip_ranges = ip_ranges.split(',')
        
        config.network.max_concurrent_connections = int(
            os.getenv('DISCOVERY_MAX_CONCURRENT', '50')
        )
        
        # Timing settings
        config.timing.discovery_interval = int(
            os.getenv('DISCOVERY_INTERVAL', '300')
        )
        
        config.timing.protocol_timeout = float(
            os.getenv('DISCOVERY_PROTOCOL_TIMEOUT', '30.0')
        )
        
        # Plugin settings
        if plugin_dirs := os.getenv('DISCOVERY_PLUGIN_DIRS'):
            config.plugins.plugin_directories = plugin_dirs.split(',')
        
        config.plugins.hot_reload_enabled = (
            os.getenv('DISCOVERY_HOT_RELOAD', 'true').lower() == 'true'
        )
        
        # Protocol-specific settings
        for protocol_name in ['mdns', 'ssdp', 'snmp', 'network_scan']:
            enabled_key = f'DISCOVERY_{protocol_name.upper()}_ENABLED'
            if enabled_env := os.getenv(enabled_key):
                if protocol_name in config.protocols:
                    config.protocols[protocol_name].enabled = enabled_env.lower() == 'true'
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enabled": self.enabled,
            "log_level": self.log_level,
            "network": {
                "ip_ranges": self.network.ip_ranges,
                "interface": self.network.interface,
                "dns_servers": self.network.dns_servers,
                "connect_timeout": self.network.connect_timeout,
                "read_timeout": self.network.read_timeout,
                "max_concurrent_connections": self.network.max_concurrent_connections,
                "common_ports": self.network.common_ports,
                "ping_enabled": self.network.ping_enabled,
                "arp_scan_enabled": self.network.arp_scan_enabled,
                "port_scan_enabled": self.network.port_scan_enabled
            },
            "timing": {
                "discovery_interval": self.timing.discovery_interval,
                "protocol_timeout": self.timing.protocol_timeout,
                "total_timeout": self.timing.total_timeout,
                "max_retries": self.timing.max_retries,
                "adaptive_timing_enabled": self.timing.adaptive_timing_enabled
            },
            "protocols": {
                name: {
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "timeout": config.timeout,
                    "settings": config.settings,
                    "max_concurrent": config.max_concurrent
                }
                for name, config in self.protocols.items()
            },
            "plugins": {
                "plugin_directories": self.plugins.plugin_directories,
                "hot_reload_enabled": self.plugins.hot_reload_enabled,
                "auto_load_plugins": self.plugins.auto_load_plugins
            },
            "event_bus_enabled": self.event_bus_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "repository_integration": self.repository_integration
        }
