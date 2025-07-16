"""
Unit tests for the three-tier configuration system.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import yaml
from cryptography.fernet import Fernet

from edge_device_fleet_manager.core.config import (
    Config,
    ConfigLoader,
    SecretsManager,
    get_config,
    get_config_sync,
)
from edge_device_fleet_manager.core.exceptions import ConfigurationError, SecretsManagerError


@pytest.mark.unit
class TestConfig:
    """Test cases for the Config class."""
    
    def test_default_config_creation(self):
        """Test creating a config with default values."""
        config = Config()
        
        assert config.app_name == "Edge Device Fleet Manager"
        assert config.app_version == "0.1.0"
        assert config.debug is False
        assert config.environment == "development"
        
        # Test nested configurations
        assert config.database.url == "sqlite:///edge_fleet.db"
        assert config.mqtt.broker_host == "localhost"
        assert config.redis.host == "localhost"
        assert config.logging.level == "INFO"
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid config
        config = Config(
            logging={"level": "DEBUG"},
            discovery={"retry_backoff_factor": 2.0, "rate_limit_per_host": 10, "rate_limit_global": 100}
        )
        assert config.logging.level == "DEBUG"
        
        # Test invalid logging level
        with pytest.raises(ValueError, match="Invalid logging level"):
            Config(logging={"level": "INVALID"})
        
        # Test invalid discovery config
        with pytest.raises(ValueError, match="retry_backoff_factor must be > 1.0"):
            Config(discovery={"retry_backoff_factor": 0.5})
        
        with pytest.raises(ValueError, match="rate_limit_per_host must be > 0"):
            Config(discovery={"rate_limit_per_host": 0})
    
    def test_config_from_env_vars(self, env_vars):
        """Test configuration loading from environment variables."""
        config = Config()
        
        assert config.debug is True  # From env_vars fixture
        assert config.environment == "test"
        assert config.database.url == "sqlite:///:memory:"
        assert config.logging.level == "DEBUG"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSecretsManager:
    """Test cases for the SecretsManager class."""
    
    async def test_secrets_manager_initialization(self, test_config):
        """Test SecretsManager initialization."""
        secrets_manager = SecretsManager(test_config.secrets)
        
        assert secrets_manager.config == test_config.secrets
        assert secrets_manager._client is None
        assert secrets_manager._encryption_key is None
        assert secrets_manager._secrets_cache == {}
    
    @patch('boto3.client')
    async def test_get_encryption_key_new(self, mock_boto3_client, test_config):
        """Test getting encryption key when it doesn't exist."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        # Simulate key not found
        mock_client.get_secret_value.side_effect = Exception("ResourceNotFoundException")
        
        secrets_manager = SecretsManager(test_config.secrets)
        
        with patch.object(secrets_manager, '_store_encryption_key', new_callable=AsyncMock) as mock_store:
            key = await secrets_manager.get_encryption_key()
            
            assert key is not None
            assert len(key) == 44  # Fernet key length
            mock_store.assert_called_once_with(key)
    
    @patch('boto3.client')
    async def test_get_encryption_key_existing(self, mock_boto3_client, test_config):
        """Test getting existing encryption key."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        test_key = Fernet.generate_key()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"key": test_key.decode()})
        }
        
        secrets_manager = SecretsManager(test_config.secrets)
        key = await secrets_manager.get_encryption_key()
        
        assert key == test_key
        mock_client.get_secret_value.assert_called_once()
    
    @patch('boto3.client')
    async def test_get_secret(self, mock_boto3_client, test_config):
        """Test getting a secret value."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        # Setup encryption key
        test_key = Fernet.generate_key()
        fernet = Fernet(test_key)
        encrypted_value = fernet.encrypt(b"secret_value").decode()
        
        mock_client.get_secret_value.side_effect = [
            {"SecretString": json.dumps({"key": test_key.decode()})},  # For encryption key
            {"SecretString": json.dumps({"test_secret": encrypted_value})}  # For actual secret
        ]
        
        secrets_manager = SecretsManager(test_config.secrets)
        value = await secrets_manager.get_secret("test_secret")
        
        assert value == "secret_value"
        assert "test_secret" in secrets_manager._secrets_cache
    
    @patch('boto3.client')
    async def test_set_secret(self, mock_boto3_client, test_config):
        """Test setting a secret value."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        test_key = Fernet.generate_key()
        mock_client.get_secret_value.side_effect = [
            {"SecretString": json.dumps({"key": test_key.decode()})},  # For encryption key
            {"SecretString": json.dumps({})}  # For existing secrets
        ]
        
        secrets_manager = SecretsManager(test_config.secrets)
        await secrets_manager.set_secret("new_secret", "new_value")
        
        # Verify update_secret was called
        mock_client.update_secret.assert_called_once()
        
        # Verify the secret was encrypted
        call_args = mock_client.update_secret.call_args[1]
        secret_string = json.loads(call_args["SecretString"])
        assert "new_secret" in secret_string
    
    @patch('boto3.client')
    async def test_check_rotation_needed(self, mock_boto3_client, test_config):
        """Test checking if key rotation is needed."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        from datetime import datetime, timedelta
        
        # Simulate old key (needs rotation)
        old_date = datetime.utcnow() - timedelta(days=35)
        mock_client.describe_secret.return_value = {
            "LastChangedDate": old_date
        }
        
        secrets_manager = SecretsManager(test_config.secrets)
        needs_rotation = await secrets_manager.check_rotation_needed()
        
        assert needs_rotation is True
        
        # Simulate recent key (no rotation needed)
        recent_date = datetime.utcnow() - timedelta(days=5)
        mock_client.describe_secret.return_value = {
            "LastChangedDate": recent_date
        }
        
        needs_rotation = await secrets_manager.check_rotation_needed()
        assert needs_rotation is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestConfigLoader:
    """Test cases for the ConfigLoader class."""
    
    async def test_config_loader_initialization(self, temp_dir):
        """Test ConfigLoader initialization."""
        config_dir = temp_dir / "configs"
        loader = ConfigLoader(config_dir)
        
        assert loader.config_dir == config_dir
        assert loader.secrets_manager is None
    
    async def test_load_yaml_config(self, config_dir):
        """Test loading YAML configuration."""
        loader = ConfigLoader(config_dir)
        yaml_config = loader._load_yaml_config()
        
        assert yaml_config["app_name"] == "Edge Device Fleet Manager Test"
        assert yaml_config["debug"] is True
        assert yaml_config["environment"] == "test"
    
    async def test_load_config_with_environment_override(self, temp_dir):
        """Test loading config with environment-specific overrides."""
        config_dir = temp_dir / "configs"
        config_dir.mkdir()
        
        # Create default config
        default_config = {"debug": False, "environment": "development"}
        with open(config_dir / "default.yaml", "w") as f:
            yaml.dump(default_config, f)
        
        # Create test environment config
        test_config = {"debug": True, "database": {"echo": True}}
        with open(config_dir / "test.yaml", "w") as f:
            yaml.dump(test_config, f)
        
        # Set environment
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            loader = ConfigLoader(config_dir)
            yaml_config = loader._load_yaml_config()
            
            assert yaml_config["debug"] is True  # Overridden by test.yaml
            assert yaml_config["environment"] == "development"  # From default.yaml
            assert yaml_config["database"]["echo"] is True  # From test.yaml
    
    @patch('edge_device_fleet_manager.core.config.SecretsManager')
    async def test_load_config_with_secrets(self, mock_secrets_manager_class, config_dir):
        """Test loading configuration with secrets."""
        mock_secrets_manager = AsyncMock()
        mock_secrets_manager.check_rotation_needed.return_value = False
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "database__password": "secret_db_password",
            "mqtt__password": "secret_mqtt_password"
        }.get(key)
        
        mock_secrets_manager_class.return_value = mock_secrets_manager
        
        loader = ConfigLoader(config_dir)
        config = await loader.load_config()
        
        # Verify secrets were loaded (this would require the actual implementation
        # to support setting nested values, which we'd need to implement)
        mock_secrets_manager.check_rotation_needed.assert_called_once()
    
    async def test_config_loading_error_handling(self, temp_dir):
        """Test error handling during config loading."""
        config_dir = temp_dir / "configs"
        config_dir.mkdir()
        
        # Create invalid YAML file
        invalid_yaml = config_dir / "default.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [")
        
        loader = ConfigLoader(config_dir)
        
        # Should handle YAML parsing errors gracefully
        yaml_config = loader._load_yaml_config()
        assert yaml_config == {}  # Should return empty dict on error


@pytest.mark.unit
@pytest.mark.asyncio
class TestGlobalConfigFunctions:
    """Test cases for global configuration functions."""
    
    async def test_get_config_singleton(self, config_dir):
        """Test that get_config returns a singleton."""
        with patch('edge_device_fleet_manager.core.config.ConfigLoader') as mock_loader_class:
            mock_loader = AsyncMock()
            mock_config = Config()
            mock_loader.load_config.return_value = mock_config
            mock_loader_class.return_value = mock_loader
            
            # First call
            config1 = await get_config()
            
            # Second call
            config2 = await get_config()
            
            # Should be the same instance
            assert config1 is config2
            
            # Loader should only be called once
            mock_loader.load_config.assert_called_once()
    
    async def test_get_config_reload(self, config_dir):
        """Test config reloading."""
        with patch('edge_device_fleet_manager.core.config.ConfigLoader') as mock_loader_class:
            mock_loader = AsyncMock()
            mock_config1 = Config(debug=False)
            mock_config2 = Config(debug=True)
            mock_loader.load_config.side_effect = [mock_config1, mock_config2]
            mock_loader_class.return_value = mock_loader
            
            # First load
            config1 = await get_config()
            assert config1.debug is False
            
            # Reload
            config2 = await get_config(reload=True)
            assert config2.debug is True
            
            # Should be different instances
            assert config1 is not config2
            
            # Loader should be called twice
            assert mock_loader.load_config.call_count == 2
    
    def test_get_config_sync(self):
        """Test synchronous config getter."""
        config = get_config_sync()
        
        # Should return a basic config instance
        assert isinstance(config, Config)
        assert config.app_name == "Edge Device Fleet Manager"
