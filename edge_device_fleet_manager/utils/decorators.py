"""
Utility decorators for Edge Device Fleet Manager.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, TypeVar, Union

from ..core.context import app_context, get_logger
from ..core.exceptions import EdgeFleetError

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def with_correlation_id(func: F) -> F:
    """Decorator to ensure a correlation ID is present in the context."""
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if app_context.correlation_id is None:
            app_context.generate_correlation_id()
        return func(*args, **kwargs)
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        if app_context.correlation_id is None:
            app_context.generate_correlation_id()
        return await func(*args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    else:
        return wrapper  # type: ignore


def log_execution_time(operation_name: Optional[str] = None):
    """Decorator to log execution time of functions."""
    
    def decorator(func: F) -> F:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Function execution completed",
                    operation=op_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    "Function execution failed",
                    operation=op_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    exc_info=e
                )
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Async function execution completed",
                    operation=op_name,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    "Async function execution failed",
                    operation=op_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    exc_info=e
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore
    
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator to retry function execution on failure."""
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(
                            "Function execution failed, retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time,
                            error=str(e)
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            "Function execution failed after all retries",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                            exc_info=e
                        )
            
            raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(
                            "Async function execution failed, retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            wait_time=wait_time,
                            error=str(e)
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            "Async function execution failed after all retries",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                            exc_info=e
                        )
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore
    
    return decorator


def validate_config(func: F) -> F:
    """Decorator to ensure configuration is available."""
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if app_context.config is None:
            raise EdgeFleetError(
                "Configuration not available",
                error_code="CONFIG_NOT_AVAILABLE"
            )
        return func(*args, **kwargs)
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        if app_context.config is None:
            raise EdgeFleetError(
                "Configuration not available",
                error_code="CONFIG_NOT_AVAILABLE"
            )
        return await func(*args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    else:
        return wrapper  # type: ignore


def handle_exceptions(
    default_return: Any = None,
    log_level: str = "error",
    reraise: bool = True
):
    """Decorator to handle exceptions with logging."""
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_method = getattr(logger, log_level.lower())
                log_method(
                    "Exception in function",
                    function=func.__name__,
                    error=str(e),
                    exc_info=e
                )
                
                if reraise:
                    raise
                return default_return
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_method = getattr(logger, log_level.lower())
                log_method(
                    "Exception in async function",
                    function=func.__name__,
                    error=str(e),
                    exc_info=e
                )
                
                if reraise:
                    raise
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore
    
    return decorator
