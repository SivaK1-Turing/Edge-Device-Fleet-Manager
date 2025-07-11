"""
Pytest configuration and fixtures for Edge Device Fleet Manager tests.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from click.testing import CliRunner

from edge_device_fleet_manager.core.config import Config, ConfigLoader
from edge_device_fleet_manager.core.context import AppContext, app_context
from edge_device_fleet_manager.core.plugins import PluginLoader
from edge_device_fleet_manager.cli.main import cli


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config_dir(temp_dir: Path) -> Path:
    """Create a temporary config directory with test configuration files."""
    config_dir = temp_dir / "configs"
    config_dir.mkdir()
    
    # Create default config
    default_config = {
        "app_name": "Edge Device Fleet Manager Test",
        "debug": True,
        "environment": "test",
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False
        },
        "mqtt": {
            "broker_host": "localhost",
            "broker_port": 1883
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 15  # Use different DB for tests
        },
        "logging": {
            "level": "DEBUG",
            "format": "json",
            "debug_sampling_rate": 1.0
        },
        "plugins": {
            "plugins_dir": str(temp_dir / "plugins"),
            "auto_reload": False
        }
    }
    
    import yaml
    with open(config_dir / "default.yaml", "w") as f:
        yaml.dump(default_config, f)
    
    return config_dir


@pytest.fixture
def plugins_dir(temp_dir: Path) -> Path:
    """Create a temporary plugins directory."""
    plugins_dir = temp_dir / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


@pytest_asyncio.fixture
async def test_config(config_dir: Path) -> Config:
    """Create a test configuration."""
    loader = ConfigLoader(config_dir)
    config = await loader.load_config()
    return config


@pytest.fixture
def mock_secrets_manager():
    """Mock AWS Secrets Manager."""
    mock = MagicMock()
    mock.get_secret_value.return_value = {
        "SecretString": '{"test_secret": "encrypted_value"}'
    }
    return mock


@pytest.fixture
def app_context_fixture(test_config: Config) -> AppContext:
    """Set up application context for tests."""
    app_context.config = test_config
    app_context.generate_correlation_id()
    yield app_context
    app_context.clear()


@pytest_asyncio.fixture
async def plugin_loader(test_config: Config, plugins_dir: Path) -> AsyncGenerator[PluginLoader, None]:
    """Create a plugin loader for tests."""
    loader = PluginLoader(test_config.plugins)
    await loader.start()
    yield loader
    await loader.stop()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_plugin_code() -> str:
    """Sample plugin code for testing."""
    return '''
import click
from edge_device_fleet_manager.core.plugins import Plugin, PluginMetadata

class TestPlugin(Plugin):
    metadata = PluginMetadata(
        name="test",
        version="1.0.0",
        description="Test plugin"
    )
    
    @click.command()
    def test_command(self):
        """Test command."""
        click.echo("Test command executed")
'''


@pytest.fixture
def broken_plugin_code() -> str:
    """Broken plugin code for testing error handling."""
    return '''
import click
from edge_device_fleet_manager.core.plugins import Plugin

class BrokenPlugin(Plugin):
    def __init__(self):
        super().__init__()
        raise SyntaxError("This plugin is intentionally broken")
    
    @click.command()
    def broken_command(self):
        click.echo("This should not work")
'''


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for AWS services."""
    mock_client = MagicMock()
    
    # Mock Secrets Manager responses
    mock_client.get_secret_value.return_value = {
        "SecretString": '{"encryption_key": "test_key_value"}'
    }
    
    mock_client.create_secret.return_value = {
        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret",
        "Name": "test-secret"
    }
    
    mock_client.update_secret.return_value = {
        "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret",
        "Name": "test-secret"
    }
    
    mock_client.describe_secret.return_value = {
        "Name": "test-secret",
        "LastChangedDate": "2024-01-01T00:00:00Z"
    }
    
    return mock_client


@pytest.fixture
def mock_watchdog_observer():
    """Mock watchdog Observer for file system events."""
    mock_observer = MagicMock()
    mock_observer.start.return_value = None
    mock_observer.stop.return_value = None
    mock_observer.join.return_value = None
    return mock_observer


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "type": "string",
        "pattern": "^[a-zA-Z0-9][a-zA-Z0-9\\-_]*[a-zA-Z0-9]$",
        "minLength": 3,
        "maxLength": 64
    }
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Reset configuration
    from edge_device_fleet_manager.core.config import _config, _config_loader
    globals()['_config'] = None
    globals()['_config_loader'] = None
    
    # Reset plugin loader
    from edge_device_fleet_manager.core.plugins import _plugin_loader
    globals()['_plugin_loader'] = None
    
    # Reset context
    app_context.clear()
    
    yield
    
    # Cleanup after test
    app_context.clear()


@pytest.fixture
def env_vars():
    """Set up environment variables for testing."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "DATABASE__URL": "sqlite:///:memory:",
        "LOGGING__LEVEL": "DEBUG",
        "PLUGINS__AUTO_RELOAD": "false"
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Async test utilities
@pytest_asyncio.fixture
async def async_mock():
    """Create an async mock for testing."""
    return AsyncMock()


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.asyncio = pytest.mark.asyncio
