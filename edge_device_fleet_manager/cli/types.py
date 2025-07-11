"""
Custom Click parameter types with validation, caching, and autocompletion.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import httpx
import jsonschema
from jsonschema import ValidationError

from ..core.context import app_context, get_logger
from ..core.exceptions import ValidationError as EdgeValidationError

logger = get_logger(__name__)


class CachedSchema:
    """Cached JSON schema with TTL."""
    
    def __init__(self, schema: Dict[str, Any], ttl: int = 3600) -> None:
        self.schema = schema
        self.cached_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if the cached schema is expired."""
        return time.time() - self.cached_at > self.ttl
    
    def validate(self, value: Any) -> None:
        """Validate a value against the cached schema."""
        jsonschema.validate(value, self.schema)


class DeviceIDType(click.ParamType):
    """
    Custom Click parameter type for device IDs with remote schema validation,
    local caching, and shell autocompletion.
    """
    
    name = "device_id"
    
    def __init__(
        self,
        schema_url: Optional[str] = None,
        schema_file: Optional[str] = None,
        cache_ttl: int = 3600,
        pattern: Optional[str] = None,
        min_length: int = 1,
        max_length: int = 255,
    ) -> None:
        self.schema_url = schema_url
        self.schema_file = schema_file
        self.cache_ttl = cache_ttl
        self.pattern = re.compile(pattern) if pattern else None
        self.min_length = min_length
        self.max_length = max_length
        
        # Cache for schemas and device IDs
        self._schema_cache: Optional[CachedSchema] = None
        self._device_ids_cache: Dict[str, float] = {}
        self._device_ids_cache_ttl = 300  # 5 minutes
    
    def convert(
        self, 
        value: Any, 
        param: Optional[click.Parameter], 
        ctx: Optional[click.Context]
    ) -> str:
        """Convert and validate the device ID."""
        if value is None:
            return value
        
        device_id = str(value).strip()
        
        # Basic validation
        if len(device_id) < self.min_length:
            self.fail(
                f"Device ID must be at least {self.min_length} characters long",
                param,
                ctx
            )
        
        if len(device_id) > self.max_length:
            self.fail(
                f"Device ID must be at most {self.max_length} characters long",
                param,
                ctx
            )
        
        # Pattern validation
        if self.pattern and not self.pattern.match(device_id):
            self.fail(
                f"Device ID does not match required pattern: {self.pattern.pattern}",
                param,
                ctx
            )
        
        # Schema validation
        try:
            self._validate_with_schema(device_id)
        except ValidationError as e:
            self.fail(f"Device ID validation failed: {e.message}", param, ctx)
        except Exception as e:
            logger.warning(
                "Schema validation failed",
                device_id=device_id,
                error=str(e)
            )
            # Continue without schema validation if it fails
        
        return device_id
    
    def _validate_with_schema(self, device_id: str) -> None:
        """Validate device ID against JSON schema."""
        schema = self._get_schema()
        if schema:
            schema.validate(device_id)
    
    def _get_schema(self) -> Optional[CachedSchema]:
        """Get the validation schema, loading from cache or remote source."""
        # Check if cached schema is still valid
        if self._schema_cache and not self._schema_cache.is_expired():
            return self._schema_cache
        
        # Try to load from file first
        if self.schema_file:
            try:
                schema_path = Path(self.schema_file)
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_data = json.load(f)
                    self._schema_cache = CachedSchema(schema_data, self.cache_ttl)
                    return self._schema_cache
            except Exception as e:
                logger.warning(
                    "Failed to load schema from file",
                    schema_file=self.schema_file,
                    error=str(e)
                )
        
        # Try to load from URL
        if self.schema_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(self.schema_url)
                    response.raise_for_status()
                    schema_data = response.json()
                
                self._schema_cache = CachedSchema(schema_data, self.cache_ttl)
                
                # Cache to file for offline use
                if self.schema_file:
                    try:
                        schema_path = Path(self.schema_file)
                        schema_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(schema_path, 'w', encoding='utf-8') as f:
                            json.dump(schema_data, f, indent=2)
                    except Exception as e:
                        logger.warning(
                            "Failed to cache schema to file",
                            schema_file=self.schema_file,
                            error=str(e)
                        )
                
                return self._schema_cache
                
            except Exception as e:
                logger.warning(
                    "Failed to load schema from URL",
                    schema_url=self.schema_url,
                    error=str(e)
                )
        
        return None
    
    def shell_complete(
        self, 
        ctx: click.Context, 
        param: click.Parameter, 
        incomplete: str
    ) -> List[click.shell_completion.CompletionItem]:
        """Provide shell autocompletion for device IDs."""
        try:
            device_ids = self._get_device_ids()
            
            # Filter device IDs that start with the incomplete text
            matches = [
                device_id for device_id in device_ids
                if device_id.startswith(incomplete)
            ]
            
            return [
                click.shell_completion.CompletionItem(device_id)
                for device_id in matches[:20]  # Limit to 20 suggestions
            ]
            
        except Exception as e:
            logger.warning(
                "Failed to provide autocompletion",
                incomplete=incomplete,
                error=str(e)
            )
            return []
    
    def _get_device_ids(self) -> List[str]:
        """Get list of known device IDs for autocompletion."""
        # Check cache first
        now = time.time()
        if hasattr(self, '_cached_device_ids'):
            cache_time = getattr(self, '_cached_device_ids_time', 0)
            if now - cache_time < self._device_ids_cache_ttl:
                return getattr(self, '_cached_device_ids', [])
        
        device_ids = []
        
        try:
            # Try to get device IDs from the repository
            # This would typically query the database or API
            # For now, we'll return a sample list
            device_ids = [
                "device-001",
                "device-002", 
                "device-003",
                "sensor-temp-01",
                "sensor-humidity-01",
                "gateway-main",
                "gateway-backup"
            ]
            
            # Cache the results
            self._cached_device_ids = device_ids
            self._cached_device_ids_time = now
            
        except Exception as e:
            logger.warning(
                "Failed to fetch device IDs for autocompletion",
                error=str(e)
            )
        
        return device_ids


class IPAddressType(click.ParamType):
    """Custom Click parameter type for IP addresses."""
    
    name = "ip_address"
    
    def __init__(self, allow_ipv6: bool = True) -> None:
        self.allow_ipv6 = allow_ipv6
    
    def convert(
        self, 
        value: Any, 
        param: Optional[click.Parameter], 
        ctx: Optional[click.Context]
    ) -> str:
        """Convert and validate the IP address."""
        if value is None:
            return value
        
        ip_str = str(value).strip()
        
        # IPv4 pattern
        ipv4_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        
        # IPv6 pattern (simplified)
        ipv6_pattern = re.compile(
            r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
            r'^::1$|^::$'
        )
        
        if ipv4_pattern.match(ip_str):
            return ip_str
        
        if self.allow_ipv6 and ipv6_pattern.match(ip_str):
            return ip_str
        
        self.fail(f"Invalid IP address: {ip_str}", param, ctx)


class SubnetType(click.ParamType):
    """Custom Click parameter type for network subnets."""
    
    name = "subnet"
    
    def convert(
        self, 
        value: Any, 
        param: Optional[click.Parameter], 
        ctx: Optional[click.Context]
    ) -> str:
        """Convert and validate the subnet."""
        if value is None:
            return value
        
        subnet_str = str(value).strip()
        
        # CIDR notation pattern
        cidr_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
            r'/(?:[0-9]|[1-2][0-9]|3[0-2])$'
        )
        
        if cidr_pattern.match(subnet_str):
            return subnet_str
        
        self.fail(f"Invalid subnet (use CIDR notation): {subnet_str}", param, ctx)


# Pre-configured type instances
DEVICE_ID = DeviceIDType(
    schema_url="https://api.edgefleet.dev/schemas/device-id.json",
    schema_file="schemas/device-id.json",
    pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*[a-zA-Z0-9]$',
    min_length=3,
    max_length=64
)

IP_ADDRESS = IPAddressType()
SUBNET = SubnetType()
