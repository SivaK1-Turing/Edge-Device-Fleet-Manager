"""
Structured JSON logging with DEBUG sampling, correlation IDs, and Sentry integration.
"""

import asyncio
import json
import logging
import random
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import sentry_sdk
import structlog
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .config import Config, LoggingConfig
from .context import app_context
from .exceptions import EdgeFleetError


class CorrelationIDProcessor:
    """Processor to add correlation ID to log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = app_context.correlation_id
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        return event_dict


class SamplingProcessor:
    """Processor to sample DEBUG logs based on configuration."""
    
    def __init__(self, debug_sampling_rate: float = 0.05) -> None:
        self.debug_sampling_rate = debug_sampling_rate
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Only sample DEBUG level logs
        if method_name == "debug":
            if random.random() > self.debug_sampling_rate:
                # Skip this log entry
                raise structlog.DropEvent
        return event_dict


class TimestampProcessor:
    """Processor to add ISO timestamp to log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return event_dict


class LevelProcessor:
    """Processor to add log level to log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        event_dict["level"] = method_name.upper()
        return event_dict


class ContextProcessor:
    """Processor to add application context to log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Add user context if available
        user = app_context.user
        if user:
            event_dict["user"] = {
                "id": user.get("id"),
                "username": user.get("username"),
                "role": user.get("role")
            }
        
        # Add request context if available
        request = app_context.request
        if request:
            event_dict["request"] = {
                "method": request.get("method"),
                "path": request.get("path"),
                "remote_addr": request.get("remote_addr"),
                "user_agent": request.get("user_agent")
            }
        
        return event_dict


class ExceptionProcessor:
    """Processor to format exceptions in log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        exc_info = event_dict.pop("exc_info", None)
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            
            event_dict["exception"] = {
                "type": exc_info[0].__name__ if exc_info[0] else None,
                "message": str(exc_info[1]) if exc_info[1] else None,
                "traceback": traceback.format_exception(*exc_info) if exc_info[0] else None
            }
        
        return event_dict


class AsyncSentryHandler(logging.Handler):
    """Async handler for sending errors to Sentry."""
    
    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[logging.LogRecord] = asyncio.Queue()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
    
    def start(self) -> None:
        """Start the async handler."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._process_queue())
    
    def stop(self) -> None:
        """Stop the async handler."""
        self._running = False
        if self._task:
            self._task.cancel()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        if self._running:
            try:
                self._queue.put_nowait(record)
            except asyncio.QueueFull:
                # Drop the record if queue is full
                pass
    
    async def _process_queue(self) -> None:
        """Process the queue of log records."""
        while self._running:
            try:
                record = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._send_to_sentry(record)
            except asyncio.TimeoutError:
                continue
            except Exception:
                # Don't let logging errors crash the application
                pass
    
    async def _send_to_sentry(self, record: logging.LogRecord) -> None:
        """Send a log record to Sentry."""
        if record.levelno >= logging.ERROR:
            # Extract exception info if available
            exc_info = getattr(record, 'exc_info', None)
            
            # Create Sentry event
            with sentry_sdk.push_scope() as scope:
                # Add correlation ID
                correlation_id = app_context.correlation_id
                if correlation_id:
                    scope.set_tag("correlation_id", correlation_id)
                
                # Add user context
                user = app_context.user
                if user:
                    scope.set_user({
                        "id": user.get("id"),
                        "username": user.get("username"),
                        "role": user.get("role")
                    })
                
                # Add request context
                request = app_context.request
                if request:
                    scope.set_context("request", {
                        "method": request.get("method"),
                        "path": request.get("path"),
                        "remote_addr": request.get("remote_addr"),
                        "user_agent": request.get("user_agent")
                    })
                
                # Send to Sentry
                if exc_info:
                    sentry_sdk.capture_exception(exc_info)
                else:
                    sentry_sdk.capture_message(record.getMessage(), level=record.levelname.lower())


def setup_logging(config: Config) -> None:
    """Setup structured logging with the given configuration."""
    logging_config = config.logging
    
    # Setup Sentry if DSN is provided
    if logging_config.sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        
        sentry_sdk.init(
            dsn=logging_config.sentry_dsn,
            environment=logging_config.sentry_environment,
            traces_sample_rate=logging_config.sentry_traces_sample_rate,
            integrations=[
                sentry_logging,
                AsyncioIntegration(auto_enabling_integrations=False),
                SqlalchemyIntegration(),
            ],
            attach_stacktrace=True,
            send_default_pii=False,
        )
    
    # Configure structlog processors
    processors = [
        TimestampProcessor(),
        LevelProcessor(),
        CorrelationIDProcessor(),
        ContextProcessor(),
        SamplingProcessor(logging_config.debug_sampling_rate),
        ExceptionProcessor(),
    ]
    
    if logging_config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, logging_config.level.upper())
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, logging_config.level.upper()),
    )
    
    # Add async Sentry handler if Sentry is configured
    if logging_config.sentry_dsn:
        async_handler = AsyncSentryHandler()
        async_handler.start()
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(async_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given name."""
    return structlog.get_logger(name)


def log_exception(
    logger: structlog.BoundLogger,
    exception: Exception,
    message: str = "An error occurred",
    **kwargs: Any
) -> None:
    """Log an exception with structured data."""
    logger.error(
        message,
        exc_info=exception,
        error_type=type(exception).__name__,
        error_message=str(exception),
        **kwargs
    )


def log_performance(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        operation=operation,
        duration_ms=duration_ms,
        **kwargs
    )


def log_audit(
    logger: structlog.BoundLogger,
    action: str,
    resource: str,
    result: str = "success",
    **kwargs: Any
) -> None:
    """Log audit events."""
    logger.info(
        "Audit event",
        action=action,
        resource=resource,
        result=result,
        **kwargs
    )


# Global logger instance
logger = get_logger(__name__)
