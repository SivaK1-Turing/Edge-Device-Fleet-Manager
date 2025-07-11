"""
Three-tier configuration system with YAML defaults, .env overrides, 
and encrypted AWS Secrets Manager entries.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import boto3
import yaml
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigurationError, SecretsManagerError


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///edge_fleet.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


class MQTTConfig(BaseModel):
    """MQTT configuration."""
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "edge_fleet_manager"
    keepalive: int = 60
    qos: int = 1
    topics: List[str] = Field(default_factory=lambda: ["edge/+/telemetry"])


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 50


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    debug_sampling_rate: float = 0.05
    correlation_id_header: str = "X-Correlation-ID"
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1


class SecretsConfig(BaseModel):
    """AWS Secrets Manager configuration."""
    region_name: str = "us-east-1"
    secret_name: str = "edge-fleet-manager/secrets"
    auto_rotation_days: int = 30
    encryption_key_name: str = "edge-fleet-manager/encryption-key"
    kms_key_id: Optional[str] = None


class PluginConfig(BaseModel):
    """Plugin system configuration."""
    plugins_dir: str = "plugins"
    auto_reload: bool = True
    reload_delay: float = 1.0
    max_load_retries: int = 3
    load_timeout: int = 30


class DiscoveryConfig(BaseModel):
    """Device discovery configuration."""
    mdns_timeout: int = 5
    ssdp_timeout: int = 10
    max_retries: int = 10
    retry_backoff_factor: float = 2.0
    retry_jitter: bool = True
    rate_limit_per_host: int = 10
    rate_limit_global: int = 100
    cache_ttl: int = 300


class Config(BaseSettings):
    """Main configuration class with three-tier loading."""
    
    # Application settings
    app_name: str = "Edge Device Fleet Manager"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    
    # Encryption
    encryption_key: Optional[str] = None
    
    # AWS credentials (optional, can use IAM roles)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        
    @validator("logging")
    def validate_logging_level(cls, v: LoggingConfig) -> LoggingConfig:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.level.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v.level}")
        v.level = v.level.upper()
        return v
    
    @validator("discovery")
    def validate_discovery_config(cls, v: DiscoveryConfig) -> DiscoveryConfig:
        """Validate discovery configuration."""
        if v.retry_backoff_factor <= 1.0:
            raise ValueError("retry_backoff_factor must be > 1.0")
        if v.rate_limit_per_host <= 0:
            raise ValueError("rate_limit_per_host must be > 0")
        if v.rate_limit_global <= 0:
            raise ValueError("rate_limit_global must be > 0")
        return v


class SecretsManager:
    """Manages encrypted secrets from AWS Secrets Manager with auto-rotation."""
    
    def __init__(self, config: SecretsConfig) -> None:
        self.config = config
        self._client: Optional[Any] = None
        self._encryption_key: Optional[bytes] = None
        self._secrets_cache: Dict[str, Any] = {}
        self._last_rotation_check: Optional[datetime] = None
    
    @property
    def client(self) -> Any:
        """Get or create AWS Secrets Manager client."""
        if self._client is None:
            self._client = boto3.client(
                "secretsmanager",
                region_name=self.config.region_name
            )
        return self._client
    
    async def get_encryption_key(self) -> bytes:
        """Get or create encryption key from AWS Secrets Manager."""
        if self._encryption_key is not None:
            return self._encryption_key
            
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_secret_value(SecretId=self.config.encryption_key_name)
            )
            key_data = json.loads(response["SecretString"])
            self._encryption_key = key_data["key"].encode()
            return self._encryption_key
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create new encryption key
                key = Fernet.generate_key()
                await self._store_encryption_key(key)
                self._encryption_key = key
                return key
            else:
                raise SecretsManagerError(
                    f"Failed to get encryption key: {e}",
                    error_code="ENCRYPTION_KEY_ERROR"
                )
    
    async def _store_encryption_key(self, key: bytes) -> None:
        """Store encryption key in AWS Secrets Manager."""
        secret_value = json.dumps({"key": key.decode()})
        
        try:
            create_params = {
                "Name": self.config.encryption_key_name,
                "SecretString": secret_value,
                "Description": "Encryption key for Edge Fleet Manager"
            }
            if self.config.kms_key_id:
                create_params["KmsKeyId"] = self.config.kms_key_id

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.create_secret(**create_params)
            )
        except ClientError as e:
            raise SecretsManagerError(
                f"Failed to store encryption key: {e}",
                error_code="ENCRYPTION_KEY_STORE_ERROR"
            )
    
    async def get_secret(self, key: str) -> Optional[str]:
        """Get decrypted secret value."""
        if key in self._secrets_cache:
            return self._secrets_cache[key]
            
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_secret_value(SecretId=self.config.secret_name)
            )
            
            secrets_data = json.loads(response["SecretString"])
            encrypted_value = secrets_data.get(key)
            
            if encrypted_value is None:
                return None
                
            # Decrypt the value
            encryption_key = await self.get_encryption_key()
            fernet = Fernet(encryption_key)
            decrypted_value = fernet.decrypt(encrypted_value.encode()).decode()
            
            # Cache the decrypted value
            self._secrets_cache[key] = decrypted_value
            return decrypted_value
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            else:
                raise SecretsManagerError(
                    f"Failed to get secret {key}: {e}",
                    error_code="SECRET_GET_ERROR"
                )
    
    async def set_secret(self, key: str, value: str) -> None:
        """Set encrypted secret value."""
        try:
            # Get current secrets
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.get_secret_value(SecretId=self.config.secret_name)
                )
                secrets_data = json.loads(response["SecretString"])
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    secrets_data = {}
                else:
                    raise
            
            # Encrypt the new value
            encryption_key = await self.get_encryption_key()
            fernet = Fernet(encryption_key)
            encrypted_value = fernet.encrypt(value.encode()).decode()
            
            # Update secrets
            secrets_data[key] = encrypted_value
            secret_string = json.dumps(secrets_data)
            
            # Store updated secrets
            if "ResourceNotFoundException" in str(secrets_data):
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.create_secret(
                        Name=self.config.secret_name,
                        SecretString=secret_string,
                        Description="Encrypted secrets for Edge Fleet Manager"
                    )
                )
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.update_secret(
                        SecretId=self.config.secret_name,
                        SecretString=secret_string
                    )
                )
            
            # Update cache
            self._secrets_cache[key] = value
            
        except ClientError as e:
            raise SecretsManagerError(
                f"Failed to set secret {key}: {e}",
                error_code="SECRET_SET_ERROR"
            )
    
    async def check_rotation_needed(self) -> bool:
        """Check if key rotation is needed."""
        now = datetime.utcnow()
        
        # Check at most once per hour
        if (self._last_rotation_check and 
            now - self._last_rotation_check < timedelta(hours=1)):
            return False
            
        self._last_rotation_check = now
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.describe_secret(SecretId=self.config.encryption_key_name)
            )
            
            last_changed = response.get("LastChangedDate")
            if last_changed:
                days_since_change = (now - last_changed.replace(tzinfo=None)).days
                return days_since_change >= self.config.auto_rotation_days
                
        except ClientError:
            # If we can't check, assume rotation is needed
            return True
            
        return False
    
    async def rotate_encryption_key(self) -> None:
        """Rotate the encryption key and re-encrypt all secrets."""
        try:
            # Get all current secrets
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_secret_value(SecretId=self.config.secret_name)
            )
            secrets_data = json.loads(response["SecretString"])
            
            # Decrypt with old key
            old_key = await self.get_encryption_key()
            old_fernet = Fernet(old_key)
            
            decrypted_secrets = {}
            for key, encrypted_value in secrets_data.items():
                decrypted_value = old_fernet.decrypt(encrypted_value.encode()).decode()
                decrypted_secrets[key] = decrypted_value
            
            # Generate new key
            new_key = Fernet.generate_key()
            new_fernet = Fernet(new_key)
            
            # Re-encrypt all secrets with new key
            new_secrets_data = {}
            for key, value in decrypted_secrets.items():
                encrypted_value = new_fernet.encrypt(value.encode()).decode()
                new_secrets_data[key] = encrypted_value
            
            # Store new encryption key
            await self._store_encryption_key(new_key)
            
            # Update secrets with new encryption
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.update_secret(
                    SecretId=self.config.secret_name,
                    SecretString=json.dumps(new_secrets_data)
                )
            )
            
            # Update internal state
            self._encryption_key = new_key
            self._secrets_cache.clear()
            
        except ClientError as e:
            raise SecretsManagerError(
                f"Failed to rotate encryption key: {e}",
                error_code="KEY_ROTATION_ERROR"
            )


class ConfigLoader:
    """Three-tier configuration loader: YAML defaults -> .env overrides -> AWS Secrets."""

    def __init__(self, config_dir: Optional[Union[str, Path]] = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else Path("configs")
        self.secrets_manager: Optional[SecretsManager] = None

    async def load_config(self) -> Config:
        """Load configuration from all three tiers."""
        # Tier 1: Load YAML defaults
        yaml_config = self._load_yaml_config()

        # Tier 2: Load .env overrides
        env_config = self._load_env_config()

        # Merge YAML and env configs
        merged_config = {**yaml_config, **env_config}

        # Create initial config object
        config = Config(**merged_config)

        # Tier 3: Load AWS Secrets Manager entries
        await self._load_secrets(config)

        return config

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML files."""
        config_data: Dict[str, Any] = {}

        # Load default config
        default_config_path = self.config_dir / "default.yaml"
        if default_config_path.exists():
            with open(default_config_path, "r", encoding="utf-8") as f:
                default_config = yaml.safe_load(f)
                if default_config:
                    config_data.update(default_config)

        # Load environment-specific config
        env = os.getenv("ENVIRONMENT", "development")
        env_config_path = self.config_dir / f"{env}.yaml"
        if env_config_path.exists():
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f)
                if env_config:
                    config_data.update(env_config)

        return config_data

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        # This is handled by pydantic-settings automatically
        # when we create the Config object
        return {}

    async def _load_secrets(self, config: Config) -> None:
        """Load secrets from AWS Secrets Manager."""
        if not config.secrets:
            return

        self.secrets_manager = SecretsManager(config.secrets)

        # Check if key rotation is needed
        if await self.secrets_manager.check_rotation_needed():
            await self.secrets_manager.rotate_encryption_key()

        # Load specific secrets and update config
        secret_mappings = {
            "database__password": "database.password",
            "mqtt__password": "mqtt.password",
            "redis__password": "redis.password",
            "sentry_dsn": "logging.sentry_dsn",
            "aws_access_key_id": "aws_access_key_id",
            "aws_secret_access_key": "aws_secret_access_key",
        }

        for secret_key, config_path in secret_mappings.items():
            secret_value = await self.secrets_manager.get_secret(secret_key)
            if secret_value:
                self._set_nested_config_value(config, config_path, secret_value)

    def _set_nested_config_value(self, config: Config, path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        parts = path.split(".")
        obj = config

        for part in parts[:-1]:
            obj = getattr(obj, part)

        setattr(obj, parts[-1], value)


# Global configuration instance
_config: Optional[Config] = None
_config_loader: Optional[ConfigLoader] = None


async def get_config(reload: bool = False) -> Config:
    """Get the global configuration instance."""
    global _config, _config_loader

    if _config is None or reload:
        if _config_loader is None:
            _config_loader = ConfigLoader()
        _config = await _config_loader.load_config()

    return _config


def get_config_sync() -> Config:
    """Get configuration synchronously (for non-async contexts)."""
    global _config

    if _config is None:
        # Create a basic config without secrets for sync contexts
        _config = Config()

    return _config
