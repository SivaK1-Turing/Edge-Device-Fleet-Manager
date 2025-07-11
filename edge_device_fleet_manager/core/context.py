"""
ContextVar-based context manager for propagating shared objects 
across sync and async Click commands.
"""

import asyncio
import uuid
from contextvars import ContextVar, copy_context
from typing import Any, Dict, Optional, TypeVar, Union
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .config import Config
from .exceptions import EdgeFleetError

T = TypeVar('T')

# Context variables for shared objects
_config_context: ContextVar[Optional[Config]] = ContextVar('config', default=None)
_correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_db_session_context: ContextVar[Optional[Union[Session, AsyncSession]]] = ContextVar('db_session', default=None)
_mqtt_client_context: ContextVar[Optional[Any]] = ContextVar('mqtt_client', default=None)
_redis_client_context: ContextVar[Optional[Any]] = ContextVar('redis_client', default=None)
_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('user', default=None)
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request', default=None)


class AppContext:
    """Application context manager for shared objects."""
    
    def __init__(self) -> None:
        self._context_data: Dict[str, Any] = {}
    
    @property
    def config(self) -> Optional[Config]:
        """Get the current configuration."""
        return _config_context.get()
    
    @config.setter
    def config(self, value: Config) -> None:
        """Set the current configuration."""
        _config_context.set(value)
    
    @property
    def correlation_id(self) -> Optional[str]:
        """Get the current correlation ID."""
        return _correlation_id_context.get()
    
    @correlation_id.setter
    def correlation_id(self, value: str) -> None:
        """Set the current correlation ID."""
        _correlation_id_context.set(value)
    
    @property
    def db_session(self) -> Optional[Union[Session, AsyncSession]]:
        """Get the current database session."""
        return _db_session_context.get()
    
    @db_session.setter
    def db_session(self, value: Union[Session, AsyncSession]) -> None:
        """Set the current database session."""
        _db_session_context.set(value)
    
    @property
    def mqtt_client(self) -> Optional[Any]:
        """Get the current MQTT client."""
        return _mqtt_client_context.get()
    
    @mqtt_client.setter
    def mqtt_client(self, value: Any) -> None:
        """Set the current MQTT client."""
        _mqtt_client_context.set(value)
    
    @property
    def redis_client(self) -> Optional[Any]:
        """Get the current Redis client."""
        return _redis_client_context.get()
    
    @redis_client.setter
    def redis_client(self, value: Any) -> None:
        """Set the current Redis client."""
        _redis_client_context.set(value)
    
    @property
    def user(self) -> Optional[Dict[str, Any]]:
        """Get the current user context."""
        return _user_context.get()
    
    @user.setter
    def user(self, value: Dict[str, Any]) -> None:
        """Set the current user context."""
        _user_context.set(value)
    
    @property
    def request(self) -> Optional[Dict[str, Any]]:
        """Get the current request context."""
        return _request_context.get()
    
    @request.setter
    def request(self, value: Dict[str, Any]) -> None:
        """Set the current request context."""
        _request_context.set(value)
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        correlation_id = str(uuid.uuid4())
        self.correlation_id = correlation_id
        return correlation_id
    
    def get_context_data(self) -> Dict[str, Any]:
        """Get all context data as a dictionary."""
        return {
            'config': self.config,
            'correlation_id': self.correlation_id,
            'db_session': self.db_session,
            'mqtt_client': self.mqtt_client,
            'redis_client': self.redis_client,
            'user': self.user,
            'request': self.request,
        }
    
    def clear(self) -> None:
        """Clear all context data."""
        _config_context.set(None)
        _correlation_id_context.set(None)
        _db_session_context.set(None)
        _mqtt_client_context.set(None)
        _redis_client_context.set(None)
        _user_context.set(None)
        _request_context.set(None)


# Global context instance
app_context = AppContext()


@contextmanager
def context_manager(
    config: Optional[Config] = None,
    correlation_id: Optional[str] = None,
    db_session: Optional[Union[Session, AsyncSession]] = None,
    mqtt_client: Optional[Any] = None,
    redis_client: Optional[Any] = None,
    user: Optional[Dict[str, Any]] = None,
    request: Optional[Dict[str, Any]] = None,
):
    """Synchronous context manager for setting up application context."""
    # Store previous values
    prev_config = app_context.config
    prev_correlation_id = app_context.correlation_id
    prev_db_session = app_context.db_session
    prev_mqtt_client = app_context.mqtt_client
    prev_redis_client = app_context.redis_client
    prev_user = app_context.user
    prev_request = app_context.request
    
    try:
        # Set new values
        if config is not None:
            app_context.config = config
        if correlation_id is not None:
            app_context.correlation_id = correlation_id
        elif app_context.correlation_id is None:
            app_context.generate_correlation_id()
        if db_session is not None:
            app_context.db_session = db_session
        if mqtt_client is not None:
            app_context.mqtt_client = mqtt_client
        if redis_client is not None:
            app_context.redis_client = redis_client
        if user is not None:
            app_context.user = user
        if request is not None:
            app_context.request = request
        
        yield app_context
        
    finally:
        # Restore previous values
        app_context.config = prev_config
        app_context.correlation_id = prev_correlation_id
        app_context.db_session = prev_db_session
        app_context.mqtt_client = prev_mqtt_client
        app_context.redis_client = prev_redis_client
        app_context.user = prev_user
        app_context.request = prev_request


@asynccontextmanager
async def async_context_manager(
    config: Optional[Config] = None,
    correlation_id: Optional[str] = None,
    db_session: Optional[Union[Session, AsyncSession]] = None,
    mqtt_client: Optional[Any] = None,
    redis_client: Optional[Any] = None,
    user: Optional[Dict[str, Any]] = None,
    request: Optional[Dict[str, Any]] = None,
):
    """Asynchronous context manager for setting up application context."""
    # Store previous values
    prev_config = app_context.config
    prev_correlation_id = app_context.correlation_id
    prev_db_session = app_context.db_session
    prev_mqtt_client = app_context.mqtt_client
    prev_redis_client = app_context.redis_client
    prev_user = app_context.user
    prev_request = app_context.request
    
    try:
        # Set new values
        if config is not None:
            app_context.config = config
        if correlation_id is not None:
            app_context.correlation_id = correlation_id
        elif app_context.correlation_id is None:
            app_context.generate_correlation_id()
        if db_session is not None:
            app_context.db_session = db_session
        if mqtt_client is not None:
            app_context.mqtt_client = mqtt_client
        if redis_client is not None:
            app_context.redis_client = redis_client
        if user is not None:
            app_context.user = user
        if request is not None:
            app_context.request = request
        
        yield app_context
        
    finally:
        # Restore previous values
        app_context.config = prev_config
        app_context.correlation_id = prev_correlation_id
        app_context.db_session = prev_db_session
        app_context.mqtt_client = prev_mqtt_client
        app_context.redis_client = prev_redis_client
        app_context.user = prev_user
        app_context.request = prev_request


def run_in_context(func, *args, **kwargs):
    """Run a function in a copied context."""
    ctx = copy_context()
    return ctx.run(func, *args, **kwargs)


async def run_in_context_async(func, *args, **kwargs):
    """Run an async function in a copied context."""
    ctx = copy_context()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ctx.run, func, *args, **kwargs)


def get_current_context() -> AppContext:
    """Get the current application context."""
    return app_context


def require_config() -> Config:
    """Get the current configuration, raising an error if not set."""
    config = app_context.config
    if config is None:
        raise EdgeFleetError(
            "Configuration not available in current context",
            error_code="CONFIG_NOT_AVAILABLE"
        )
    return config


def require_correlation_id() -> str:
    """Get the current correlation ID, raising an error if not set."""
    correlation_id = app_context.correlation_id
    if correlation_id is None:
        raise EdgeFleetError(
            "Correlation ID not available in current context",
            error_code="CORRELATION_ID_NOT_AVAILABLE"
        )
    return correlation_id


def require_db_session() -> Union[Session, AsyncSession]:
    """Get the current database session, raising an error if not set."""
    db_session = app_context.db_session
    if db_session is None:
        raise EdgeFleetError(
            "Database session not available in current context",
            error_code="DB_SESSION_NOT_AVAILABLE"
        )
    return db_session
