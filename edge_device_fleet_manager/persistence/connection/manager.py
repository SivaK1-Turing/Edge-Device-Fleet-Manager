"""
Database Manager

Comprehensive database management with connection pooling, health monitoring,
transaction management, and failover capabilities.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
)
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import text, event

from ...core.logging import get_logger
from .config import DatabaseConfig
from .health import HealthChecker

logger = get_logger(__name__)


class DatabaseManager:
    """
    Comprehensive database manager with connection pooling and health monitoring.
    
    Provides high-level database management including connection pooling,
    health checks, transaction management, and failover capabilities.
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize database manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self.health_checker: Optional[HealthChecker] = None
        self._is_initialized = False
        self._connection_count = 0
        self._transaction_count = 0
        self._error_count = 0
        
        logger.info(f"Database manager initialized for {config.database_url}")
    
    async def initialize(self) -> None:
        """Initialize database engine and connection pool."""
        try:
            if self._is_initialized:
                logger.warning("Database manager already initialized")
                return
            
            # Create async engine with connection pooling
            engine_kwargs = {
                'echo': self.config.echo_sql,
                'echo_pool': self.config.echo_pool,
                'pool_size': self.config.pool_size,
                'max_overflow': self.config.max_overflow,
                'pool_timeout': self.config.pool_timeout,
                'pool_recycle': self.config.pool_recycle,
                'pool_pre_ping': self.config.pool_pre_ping,
            }
            
            # Use NullPool for SQLite, QueuePool for others
            if self.config.database_url.startswith('sqlite'):
                engine_kwargs['poolclass'] = NullPool
                # Remove pool-specific settings for SQLite
                for key in ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle']:
                    engine_kwargs.pop(key, None)
            else:
                engine_kwargs['poolclass'] = QueuePool
            
            self.engine = create_async_engine(
                self.config.database_url,
                **engine_kwargs
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=self.config.autoflush,
                autocommit=False
            )
            
            # Initialize health checker
            self.health_checker = HealthChecker(
                self.engine,
                check_interval=self.config.health_check_interval,
                timeout=self.config.health_check_timeout
            )
            
            # Set up event listeners
            self._setup_event_listeners()
            
            # Start health monitoring if enabled
            if self.config.enable_health_checks:
                await self.health_checker.start()
            
            self._is_initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown database manager and cleanup resources."""
        try:
            if not self._is_initialized:
                return
            
            # Stop health checker
            if self.health_checker:
                await self.health_checker.stop()
            
            # Close engine
            if self.engine:
                await self.engine.dispose()
            
            self._is_initialized = False
            logger.info("Database manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during database manager shutdown: {e}")
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring."""
        if not self.engine:
            return
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections."""
            self._connection_count += 1
            logger.debug(f"New database connection established (total: {self._connection_count})")
        
        @event.listens_for(self.engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Handle database connection closures."""
            self._connection_count = max(0, self._connection_count - 1)
            logger.debug(f"Database connection closed (remaining: {self._connection_count})")
        
        @event.listens_for(self.engine.sync_engine, "handle_error")
        def on_error(exception_context):
            """Handle database errors."""
            self._error_count += 1
            logger.error(f"Database error occurred: {exception_context.original_exception}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.
        
        Yields:
            AsyncSession instance
        """
        if not self._is_initialized:
            raise RuntimeError("Database manager not initialized")
        
        if not self.session_factory:
            raise RuntimeError("Session factory not available")
        
        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error, rolling back: {e}")
            raise
        finally:
            await session.close()
    
    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic transaction management.
        
        Yields:
            AsyncSession instance with transaction
        """
        async with self.get_session() as session:
            try:
                self._transaction_count += 1
                yield session
                await session.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                await session.rollback()
                logger.error(f"Transaction failed, rolling back: {e}")
                raise
            finally:
                self._transaction_count = max(0, self._transaction_count - 1)
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            Query result
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(text(query), parameters or {})
                return result
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            True if connection is healthy
        """
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
                
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information.
        
        Returns:
            Dictionary with connection details
        """
        try:
            info = {
                'database_url': self.config.database_url,
                'is_initialized': self._is_initialized,
                'connection_count': self._connection_count,
                'transaction_count': self._transaction_count,
                'error_count': self._error_count,
                'pool_size': self.config.pool_size,
                'max_overflow': self.config.max_overflow,
                'health_checks_enabled': self.config.enable_health_checks
            }
            
            # Add engine-specific info if available
            if self.engine and hasattr(self.engine, 'pool'):
                pool = self.engine.pool
                try:
                    info.update({
                        'pool_checked_in': getattr(pool, 'checkedin', lambda: 'N/A')(),
                        'pool_checked_out': getattr(pool, 'checkedout', lambda: 'N/A')(),
                        'pool_overflow': getattr(pool, 'overflow', lambda: 'N/A')(),
                        'pool_invalid': getattr(pool, 'invalid', lambda: 'N/A')()
                    })
                except Exception as e:
                    info['pool_info_error'] = str(e)
            
            # Add health check info if available
            if self.health_checker:
                health_info = await self.health_checker.get_status()
                info['health_status'] = health_info
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return {'error': str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            stats = {
                'connections': {
                    'total_created': self._connection_count,
                    'currently_active': self._transaction_count,
                    'errors': self._error_count
                },
                'configuration': {
                    'pool_size': self.config.pool_size,
                    'max_overflow': self.config.max_overflow,
                    'pool_timeout': self.config.pool_timeout,
                    'pool_recycle': self.config.pool_recycle
                },
                'health': {
                    'checks_enabled': self.config.enable_health_checks,
                    'last_check': None,
                    'status': 'unknown'
                }
            }
            
            # Add health check statistics
            if self.health_checker:
                health_stats = await self.health_checker.get_statistics()
                stats['health'].update(health_stats)
            
            # Add pool statistics if available
            if self.engine and hasattr(self.engine, 'pool'):
                pool = self.engine.pool
                stats['pool'] = {
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                    'size': pool.size()
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'error': str(e)}
    
    async def test_connection_with_retry(self, max_retries: int = 3, 
                                       retry_delay: float = 1.0) -> bool:
        """
        Test database connection with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if connection successful
        """
        for attempt in range(max_retries + 1):
            try:
                if await self.check_connection():
                    if attempt > 0:
                        logger.info(f"Connection successful after {attempt} retries")
                    return True
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        logger.error(f"Connection failed after {max_retries} retries")
        return False
    
    async def recreate_engine(self) -> None:
        """Recreate database engine (useful for connection recovery)."""
        try:
            logger.info("Recreating database engine")
            
            # Store current configuration
            old_engine = self.engine
            
            # Create new engine
            await self.initialize()
            
            # Dispose old engine
            if old_engine:
                await old_engine.dispose()
            
            logger.info("Database engine recreated successfully")
            
        except Exception as e:
            logger.error(f"Failed to recreate database engine: {e}")
            raise
    
    def is_healthy(self) -> bool:
        """
        Check if database manager is in a healthy state.
        
        Returns:
            True if healthy
        """
        if not self._is_initialized:
            return False
        
        if self.health_checker:
            return self.health_checker.is_healthy()
        
        # Fallback check
        return self.engine is not None and self.session_factory is not None
