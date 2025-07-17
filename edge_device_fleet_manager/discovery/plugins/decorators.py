"""
Plugin decorators for discovery system.

This module provides decorators to simplify plugin development and
configuration management.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .base import DiscoveryPlugin, PluginMetadata


def discovery_plugin(
    name: str,
    version: str,
    description: str,
    author: str,
    dependencies: Optional[List[str]] = None,
    supported_protocols: Optional[List[str]] = None,
    min_python_version: str = "3.8",
    plugin_api_version: str = "1.0",
    tags: Optional[List[str]] = None,
    homepage: Optional[str] = None,
    license: Optional[str] = None
) -> Callable[[Type[DiscoveryPlugin]], Type[DiscoveryPlugin]]:
    """
    Decorator to mark a class as a discovery plugin.
    
    Args:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        dependencies: List of plugin dependencies
        supported_protocols: List of supported protocols
        min_python_version: Minimum Python version required
        plugin_api_version: Plugin API version
        tags: Plugin tags for categorization
        homepage: Plugin homepage URL
        license: Plugin license
    
    Returns:
        Decorated plugin class
    
    Example:
        @discovery_plugin(
            name="custom_discovery",
            version="1.0.0",
            description="Custom device discovery plugin",
            author="Your Name",
            supported_protocols=["custom_protocol"]
        )
        class CustomDiscoveryPlugin(DiscoveryPlugin):
            async def initialize(self):
                pass
            
            async def discover(self, **kwargs):
                # Discovery implementation
                pass
            
            async def cleanup(self):
                pass
    """
    def decorator(cls: Type[DiscoveryPlugin]) -> Type[DiscoveryPlugin]:
        if not issubclass(cls, DiscoveryPlugin):
            raise TypeError(f"Class {cls.__name__} must inherit from DiscoveryPlugin")
        
        metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            dependencies=dependencies or [],
            supported_protocols=supported_protocols or [],
            min_python_version=min_python_version,
            plugin_api_version=plugin_api_version,
            tags=tags or [],
            homepage=homepage,
            license=license
        )
        
        cls.__plugin_metadata__ = metadata
        return cls
    
    return decorator


def plugin_config(
    required_keys: Optional[List[str]] = None,
    optional_keys: Optional[Dict[str, Any]] = None,
    validation_schema: Optional[Dict[str, Any]] = None
) -> Callable[[Type[DiscoveryPlugin]], Type[DiscoveryPlugin]]:
    """
    Decorator to define plugin configuration requirements.
    
    Args:
        required_keys: List of required configuration keys
        optional_keys: Dictionary of optional keys with default values
        validation_schema: JSON schema for configuration validation
    
    Returns:
        Decorated plugin class
    
    Example:
        @plugin_config(
            required_keys=["api_key", "endpoint"],
            optional_keys={"timeout": 30, "retries": 3}
        )
        class MyPlugin(DiscoveryPlugin):
            pass
    """
    def decorator(cls: Type[DiscoveryPlugin]) -> Type[DiscoveryPlugin]:
        original_validate_config = cls.validate_config
        
        @wraps(original_validate_config)
        async def enhanced_validate_config(self) -> List[str]:
            errors = await original_validate_config(self)
            
            # Check required keys
            if required_keys:
                for key in required_keys:
                    if key not in self.config.config_data:
                        errors.append(f"Required configuration key '{key}' is missing")
            
            # Set default values for optional keys
            if optional_keys:
                for key, default_value in optional_keys.items():
                    if key not in self.config.config_data:
                        self.config.config_data[key] = default_value
            
            # TODO: Add JSON schema validation if validation_schema is provided
            
            return errors
        
        cls.validate_config = enhanced_validate_config
        cls.__config_requirements__ = {
            "required_keys": required_keys or [],
            "optional_keys": optional_keys or {},
            "validation_schema": validation_schema
        }
        
        return cls
    
    return decorator


def plugin_dependency(*dependencies: str) -> Callable[[Type[DiscoveryPlugin]], Type[DiscoveryPlugin]]:
    """
    Decorator to declare plugin dependencies.
    
    Args:
        *dependencies: Plugin names this plugin depends on
    
    Returns:
        Decorated plugin class
    
    Example:
        @plugin_dependency("base_network", "authentication")
        class AdvancedPlugin(DiscoveryPlugin):
            pass
    """
    def decorator(cls: Type[DiscoveryPlugin]) -> Type[DiscoveryPlugin]:
        if hasattr(cls, '__plugin_metadata__'):
            cls.__plugin_metadata__.dependencies.extend(dependencies)
        else:
            # Store dependencies for later use when metadata is set
            if not hasattr(cls, '__pending_dependencies__'):
                cls.__pending_dependencies__ = []
            cls.__pending_dependencies__.extend(dependencies)
        
        return cls
    
    return decorator


def plugin_hook(event: str) -> Callable[[Callable], Callable]:
    """
    Decorator to register a method as a plugin hook.
    
    Args:
        event: Event name to hook into
    
    Returns:
        Decorated method
    
    Example:
        class MyPlugin(DiscoveryPlugin):
            @plugin_hook("device_discovered")
            async def on_device_discovered(self, device):
                # Handle device discovery event
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)
        
        wrapper.__plugin_hook__ = event
        return wrapper
    
    return decorator


def protocol_handler(protocol_name: str) -> Callable[[Callable], Callable]:
    """
    Decorator to mark a method as a protocol handler.
    
    Args:
        protocol_name: Name of the protocol this method handles
    
    Returns:
        Decorated method
    
    Example:
        class MultiProtocolPlugin(DiscoveryPlugin):
            @protocol_handler("mdns")
            async def handle_mdns(self, **kwargs):
                # Handle mDNS discovery
                pass
            
            @protocol_handler("ssdp")
            async def handle_ssdp(self, **kwargs):
                # Handle SSDP discovery
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)
        
        wrapper.__protocol_handler__ = protocol_name
        return wrapper
    
    return decorator


def async_timeout(seconds: float) -> Callable[[Callable], Callable]:
    """
    Decorator to add timeout to async plugin methods.
    
    Args:
        seconds: Timeout in seconds
    
    Returns:
        Decorated method
    
    Example:
        class MyPlugin(DiscoveryPlugin):
            @async_timeout(30.0)
            async def discover(self, **kwargs):
                # This method will timeout after 30 seconds
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        
        wrapper.__timeout__ = seconds
        return wrapper
    
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable], Callable]:
    """
    Decorator to add retry logic to plugin methods.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Backoff factor for exponential backoff
        exceptions: Tuple of exceptions to retry on
    
    Returns:
        Decorated method
    
    Example:
        class MyPlugin(DiscoveryPlugin):
            @retry_on_failure(max_retries=3, delay=1.0)
            async def discover(self, **kwargs):
                # This method will retry up to 3 times on failure
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        raise last_exception
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        wrapper.__retry_config__ = {
            "max_retries": max_retries,
            "delay": delay,
            "backoff_factor": backoff_factor,
            "exceptions": exceptions
        }
        return wrapper
    
    return decorator


def cache_result(ttl_seconds: int = 300) -> Callable[[Callable], Callable]:
    """
    Decorator to cache plugin method results.
    
    Args:
        ttl_seconds: Time-to-live for cached results in seconds
    
    Returns:
        Decorated method
    
    Example:
        class MyPlugin(DiscoveryPlugin):
            @cache_result(ttl_seconds=60)
            async def expensive_operation(self):
                # This result will be cached for 60 seconds
                pass
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            import hashlib
            import pickle
            
            # Create cache key from arguments
            key_data = pickle.dumps((args, sorted(kwargs.items())))
            cache_key = hashlib.md5(key_data).hexdigest()
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            # Clean up expired entries
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in cache.items()
                if current_time - timestamp >= ttl_seconds
            ]
            for key in expired_keys:
                del cache[key]
            
            return result
        
        wrapper.__cache_ttl__ = ttl_seconds
        return wrapper
    
    return decorator
