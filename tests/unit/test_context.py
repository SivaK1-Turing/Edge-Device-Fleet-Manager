"""
Unit tests for the ContextVar-based context management system.
"""

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from edge_device_fleet_manager.core.context import (
    AppContext,
    app_context,
    async_context_manager,
    context_manager,
    get_current_context,
    require_config,
    require_correlation_id,
    require_db_session,
    run_in_context,
    run_in_context_async,
)
from edge_device_fleet_manager.core.exceptions import EdgeFleetError


@pytest.mark.unit
class TestAppContext:
    """Test cases for the AppContext class."""
    
    def test_app_context_initialization(self):
        """Test AppContext initialization."""
        context = AppContext()
        
        assert context.config is None
        assert context.correlation_id is None
        assert context.db_session is None
        assert context.mqtt_client is None
        assert context.redis_client is None
        assert context.user is None
        assert context.request is None
    
    def test_config_property(self, test_config):
        """Test config property getter and setter."""
        context = AppContext()
        
        # Test setter
        context.config = test_config
        assert context.config is test_config
        
        # Test getter
        retrieved_config = context.config
        assert retrieved_config is test_config
    
    def test_correlation_id_property(self):
        """Test correlation_id property getter and setter."""
        context = AppContext()
        test_id = "test-correlation-id"
        
        # Test setter
        context.correlation_id = test_id
        assert context.correlation_id == test_id
        
        # Test getter
        retrieved_id = context.correlation_id
        assert retrieved_id == test_id
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        context = AppContext()
        
        correlation_id = context.generate_correlation_id()
        
        # Should be a valid UUID string
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID length
        
        # Should be set in context
        assert context.correlation_id == correlation_id
        
        # Should be a valid UUID
        uuid.UUID(correlation_id)  # Will raise ValueError if invalid
    
    def test_db_session_property(self):
        """Test db_session property getter and setter."""
        context = AppContext()
        mock_session = MagicMock()
        
        # Test setter
        context.db_session = mock_session
        assert context.db_session is mock_session
        
        # Test getter
        retrieved_session = context.db_session
        assert retrieved_session is mock_session
    
    def test_mqtt_client_property(self):
        """Test mqtt_client property getter and setter."""
        context = AppContext()
        mock_client = MagicMock()
        
        # Test setter
        context.mqtt_client = mock_client
        assert context.mqtt_client is mock_client
        
        # Test getter
        retrieved_client = context.mqtt_client
        assert retrieved_client is mock_client
    
    def test_redis_client_property(self):
        """Test redis_client property getter and setter."""
        context = AppContext()
        mock_client = MagicMock()
        
        # Test setter
        context.redis_client = mock_client
        assert context.redis_client is mock_client
        
        # Test getter
        retrieved_client = context.redis_client
        assert retrieved_client is mock_client
    
    def test_user_property(self):
        """Test user property getter and setter."""
        context = AppContext()
        test_user = {"id": "123", "username": "testuser", "role": "admin"}
        
        # Test setter
        context.user = test_user
        assert context.user == test_user
        
        # Test getter
        retrieved_user = context.user
        assert retrieved_user == test_user
    
    def test_request_property(self):
        """Test request property getter and setter."""
        context = AppContext()
        test_request = {
            "method": "GET",
            "path": "/api/devices",
            "remote_addr": "192.168.1.100",
            "user_agent": "test-agent"
        }
        
        # Test setter
        context.request = test_request
        assert context.request == test_request
        
        # Test getter
        retrieved_request = context.request
        assert retrieved_request == test_request
    
    def test_get_context_data(self, test_config):
        """Test getting all context data as a dictionary."""
        context = AppContext()
        mock_session = MagicMock()
        mock_mqtt = MagicMock()
        mock_redis = MagicMock()
        test_user = {"id": "123", "username": "testuser"}
        test_request = {"method": "GET", "path": "/test"}
        
        # Set all context data
        context.config = test_config
        context.correlation_id = "test-id"
        context.db_session = mock_session
        context.mqtt_client = mock_mqtt
        context.redis_client = mock_redis
        context.user = test_user
        context.request = test_request
        
        # Get context data
        data = context.get_context_data()
        
        assert data["config"] is test_config
        assert data["correlation_id"] == "test-id"
        assert data["db_session"] is mock_session
        assert data["mqtt_client"] is mock_mqtt
        assert data["redis_client"] is mock_redis
        assert data["user"] == test_user
        assert data["request"] == test_request
    
    def test_clear_context(self, test_config):
        """Test clearing all context data."""
        context = AppContext()
        
        # Set some context data
        context.config = test_config
        context.correlation_id = "test-id"
        context.db_session = MagicMock()
        
        # Clear context
        context.clear()
        
        # Verify all data is cleared
        assert context.config is None
        assert context.correlation_id is None
        assert context.db_session is None
        assert context.mqtt_client is None
        assert context.redis_client is None
        assert context.user is None
        assert context.request is None


@pytest.mark.unit
class TestContextManagers:
    """Test cases for context managers."""
    
    def test_sync_context_manager(self, test_config):
        """Test synchronous context manager."""
        # Clear any existing context
        app_context.clear()
        
        mock_session = MagicMock()
        test_user = {"id": "123", "username": "testuser"}
        
        with context_manager(
            config=test_config,
            correlation_id="test-id",
            db_session=mock_session,
            user=test_user
        ) as ctx:
            # Verify context is set
            assert ctx.config is test_config
            assert ctx.correlation_id == "test-id"
            assert ctx.db_session is mock_session
            assert ctx.user == test_user
            
            # Verify global context is also set
            assert app_context.config is test_config
            assert app_context.correlation_id == "test-id"
            assert app_context.db_session is mock_session
            assert app_context.user == test_user
        
        # Verify context is restored after exiting
        assert app_context.config is None
        assert app_context.correlation_id is None
        assert app_context.db_session is None
        assert app_context.user is None
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self, test_config):
        """Test asynchronous context manager."""
        # Clear any existing context
        app_context.clear()
        
        mock_session = MagicMock()
        test_request = {"method": "POST", "path": "/api/test"}
        
        async with async_context_manager(
            config=test_config,
            correlation_id="async-test-id",
            db_session=mock_session,
            request=test_request
        ) as ctx:
            # Verify context is set
            assert ctx.config is test_config
            assert ctx.correlation_id == "async-test-id"
            assert ctx.db_session is mock_session
            assert ctx.request == test_request
            
            # Verify global context is also set
            assert app_context.config is test_config
            assert app_context.correlation_id == "async-test-id"
            assert app_context.db_session is mock_session
            assert app_context.request == test_request
        
        # Verify context is restored after exiting
        assert app_context.config is None
        assert app_context.correlation_id is None
        assert app_context.db_session is None
        assert app_context.request is None
    
    def test_context_manager_auto_correlation_id(self, test_config):
        """Test context manager auto-generates correlation ID if not provided."""
        app_context.clear()
        
        with context_manager(config=test_config) as ctx:
            # Should auto-generate correlation ID
            assert ctx.correlation_id is not None
            assert len(ctx.correlation_id) == 36  # UUID length
            
            # Should be a valid UUID
            uuid.UUID(ctx.correlation_id)
    
    def test_context_manager_preserves_existing_correlation_id(self, test_config):
        """Test context manager preserves existing correlation ID."""
        app_context.clear()
        app_context.correlation_id = "existing-id"
        
        with context_manager(config=test_config) as ctx:
            # Should preserve existing correlation ID
            assert ctx.correlation_id == "existing-id"
    
    def test_nested_context_managers(self, test_config):
        """Test nested context managers."""
        app_context.clear()
        
        mock_session1 = MagicMock()
        mock_session2 = MagicMock()
        
        with context_manager(config=test_config, db_session=mock_session1):
            assert app_context.db_session is mock_session1
            
            with context_manager(db_session=mock_session2):
                # Inner context should override
                assert app_context.db_session is mock_session2
                assert app_context.config is test_config  # Should preserve
            
            # Should restore outer context
            assert app_context.db_session is mock_session1
            assert app_context.config is test_config
        
        # Should restore original state
        assert app_context.db_session is None
        assert app_context.config is None


@pytest.mark.unit
class TestContextUtilities:
    """Test cases for context utility functions."""
    
    def test_get_current_context(self, test_config):
        """Test getting current context."""
        app_context.clear()
        app_context.config = test_config
        app_context.correlation_id = "test-id"
        
        current_context = get_current_context()
        
        assert current_context is app_context
        assert current_context.config is test_config
        assert current_context.correlation_id == "test-id"
    
    def test_require_config_success(self, test_config):
        """Test require_config when config is available."""
        app_context.clear()
        app_context.config = test_config
        
        config = require_config()
        assert config is test_config
    
    def test_require_config_failure(self):
        """Test require_config when config is not available."""
        app_context.clear()
        
        with pytest.raises(EdgeFleetError) as exc_info:
            require_config()
        
        assert exc_info.value.error_code == "CONFIG_NOT_AVAILABLE"
        assert "Configuration not available" in str(exc_info.value)
    
    def test_require_correlation_id_success(self):
        """Test require_correlation_id when correlation ID is available."""
        app_context.clear()
        app_context.correlation_id = "test-correlation-id"
        
        correlation_id = require_correlation_id()
        assert correlation_id == "test-correlation-id"
    
    def test_require_correlation_id_failure(self):
        """Test require_correlation_id when correlation ID is not available."""
        app_context.clear()
        
        with pytest.raises(EdgeFleetError) as exc_info:
            require_correlation_id()
        
        assert exc_info.value.error_code == "CORRELATION_ID_NOT_AVAILABLE"
        assert "Correlation ID not available" in str(exc_info.value)
    
    def test_require_db_session_success(self):
        """Test require_db_session when session is available."""
        app_context.clear()
        mock_session = MagicMock()
        app_context.db_session = mock_session
        
        session = require_db_session()
        assert session is mock_session
    
    def test_require_db_session_failure(self):
        """Test require_db_session when session is not available."""
        app_context.clear()
        
        with pytest.raises(EdgeFleetError) as exc_info:
            require_db_session()
        
        assert exc_info.value.error_code == "DB_SESSION_NOT_AVAILABLE"
        assert "Database session not available" in str(exc_info.value)
    
    def test_run_in_context(self, test_config):
        """Test running function in copied context."""
        app_context.clear()
        app_context.config = test_config
        
        def test_function():
            return app_context.config
        
        # Run in copied context
        result = run_in_context(test_function)
        assert result is test_config
    
    @pytest.mark.asyncio
    async def test_run_in_context_async(self, test_config):
        """Test running async function in copied context."""
        app_context.clear()
        app_context.config = test_config
        
        def test_function():
            return app_context.config
        
        # Run in copied context
        result = await run_in_context_async(test_function)
        assert result is test_config
