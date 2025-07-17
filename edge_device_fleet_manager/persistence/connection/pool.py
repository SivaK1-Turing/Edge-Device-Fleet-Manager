"""
Connection Pool

Advanced connection pooling implementation with monitoring,
load balancing, and connection lifecycle management.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import QueuePool, StaticPool, NullPool

from ...core.logging import get_logger

logger = get_logger(__name__)


class ConnectionPool:
    """
    Advanced connection pool with monitoring and management capabilities.
    
    Provides connection pooling with health monitoring, load balancing,
    and comprehensive connection lifecycle management.
    """
    
    def __init__(self, engine: AsyncEngine, pool_config: Optional[Dict[str, Any]] = None):
        """
        Initialize connection pool.
        
        Args:
            engine: Async SQLAlchemy engine
            pool_config: Pool configuration options
        """
        self.engine = engine
        self.pool_config = pool_config or {}
        self._active_connections = 0
        self._total_connections_created = 0
        self._connection_errors = 0
        self._last_error_time = None
        self._pool_statistics = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_failed': 0,
            'peak_connections': 0,
            'total_requests': 0,
            'average_wait_time': 0.0
        }
        self._wait_times = []
        self.logger = get_logger(f"{__name__}.ConnectionPool")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get database connection from pool with monitoring.
        
        Yields:
            Database connection
        """
        start_time = time.time()
        connection = None
        
        try:
            self._pool_statistics['total_requests'] += 1
            
            # Get connection from engine
            connection = self.engine.connect()
            await connection.start()
            
            self._active_connections += 1
            self._total_connections_created += 1
            self._pool_statistics['connections_created'] += 1
            
            # Update peak connections
            if self._active_connections > self._pool_statistics['peak_connections']:
                self._pool_statistics['peak_connections'] = self._active_connections
            
            # Calculate wait time
            wait_time = time.time() - start_time
            self._wait_times.append(wait_time)
            if len(self._wait_times) > 100:  # Keep last 100 measurements
                self._wait_times.pop(0)
            
            self._pool_statistics['average_wait_time'] = sum(self._wait_times) / len(self._wait_times)
            
            self.logger.debug(f"Connection acquired (active: {self._active_connections})")
            
            yield connection
            
        except Exception as e:
            self._connection_errors += 1
            self._last_error_time = datetime.now(timezone.utc)
            self._pool_statistics['connections_failed'] += 1
            
            self.logger.error(f"Connection error: {e}")
            raise
            
        finally:
            if connection:
                try:
                    await connection.close()
                    self._active_connections = max(0, self._active_connections - 1)
                    self._pool_statistics['connections_closed'] += 1
                    
                    self.logger.debug(f"Connection released (active: {self._active_connections})")
                    
                except Exception as e:
                    self.logger.error(f"Error closing connection: {e}")
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get database session from pool.
        
        Yields:
            AsyncSession instance
        """
        async with self.get_connection() as connection:
            session = AsyncSession(bind=connection)
            try:
                yield session
            finally:
                await session.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current pool status.
        
        Returns:
            Pool status dictionary
        """
        pool_info = {}
        
        # Get pool information from engine if available
        if hasattr(self.engine, 'pool'):
            pool = self.engine.pool
            pool_info = {
                'pool_size': getattr(pool, 'size', lambda: 'N/A')(),
                'checked_in': getattr(pool, 'checkedin', lambda: 'N/A')(),
                'checked_out': getattr(pool, 'checkedout', lambda: 'N/A')(),
                'overflow': getattr(pool, 'overflow', lambda: 'N/A')(),
                'invalid': getattr(pool, 'invalid', lambda: 'N/A')(),
            }
        
        return {
            'active_connections': self._active_connections,
            'total_connections_created': self._total_connections_created,
            'connection_errors': self._connection_errors,
            'last_error_time': self._last_error_time.isoformat() if self._last_error_time else None,
            'pool_info': pool_info,
            'statistics': self._pool_statistics.copy()
        }
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """
        Get detailed pool statistics.
        
        Returns:
            Pool statistics dictionary
        """
        stats = self._pool_statistics.copy()
        
        # Calculate additional metrics
        if stats['total_requests'] > 0:
            stats['error_rate'] = (stats['connections_failed'] / stats['total_requests']) * 100
            stats['success_rate'] = 100 - stats['error_rate']
        else:
            stats['error_rate'] = 0
            stats['success_rate'] = 100
        
        # Connection efficiency
        if stats['connections_created'] > 0:
            stats['connection_reuse_ratio'] = (
                (stats['total_requests'] - stats['connections_created']) / 
                stats['total_requests'] * 100
            )
        else:
            stats['connection_reuse_ratio'] = 0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset pool statistics."""
        self._pool_statistics = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_failed': 0,
            'peak_connections': 0,
            'total_requests': 0,
            'average_wait_time': 0.0
        }
        self._wait_times = []
        self._connection_errors = 0
        self._last_error_time = None
        
        self.logger.info("Pool statistics reset")
    
    async def health_check(self) -> bool:
        """
        Perform health check on the connection pool.
        
        Returns:
            True if pool is healthy
        """
        try:
            async with self.get_connection() as connection:
                # Simple query to test connection
                result = await connection.execute("SELECT 1")
                await result.fetchone()
                return True
                
        except Exception as e:
            self.logger.error(f"Pool health check failed: {e}")
            return False
    
    async def warm_up_pool(self, target_connections: int = 3) -> int:
        """
        Warm up the connection pool by creating initial connections.
        
        Args:
            target_connections: Number of connections to create
            
        Returns:
            Number of connections successfully created
        """
        created_connections = 0
        
        self.logger.info(f"Warming up pool with {target_connections} connections")
        
        # Create connections concurrently
        tasks = []
        for i in range(target_connections):
            task = asyncio.create_task(self._create_warmup_connection())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result is True:
                created_connections += 1
            elif isinstance(result, Exception):
                self.logger.warning(f"Failed to create warmup connection: {result}")
        
        self.logger.info(f"Pool warmed up with {created_connections}/{target_connections} connections")
        return created_connections
    
    async def _create_warmup_connection(self) -> bool:
        """Create a single warmup connection."""
        try:
            async with self.get_connection():
                # Connection created and immediately released
                pass
            return True
        except Exception:
            return False
    
    def configure_pool_events(self, callbacks: Dict[str, Callable]) -> None:
        """
        Configure pool event callbacks.
        
        Args:
            callbacks: Dictionary of event callbacks
        """
        # This would set up SQLAlchemy pool events
        # For now, just store the callbacks
        self._event_callbacks = callbacks
        self.logger.info("Pool event callbacks configured")
    
    async def drain_pool(self, timeout: float = 30.0) -> bool:
        """
        Drain the connection pool gracefully.
        
        Args:
            timeout: Maximum time to wait for connections to close
            
        Returns:
            True if pool drained successfully
        """
        start_time = time.time()
        
        self.logger.info("Draining connection pool")
        
        while self._active_connections > 0:
            if time.time() - start_time > timeout:
                self.logger.warning(f"Pool drain timeout with {self._active_connections} active connections")
                return False
            
            await asyncio.sleep(0.1)
        
        self.logger.info("Connection pool drained successfully")
        return True
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get detailed connection information.
        
        Returns:
            Connection information dictionary
        """
        return {
            'engine_url': str(self.engine.url),
            'pool_class': type(self.engine.pool).__name__ if hasattr(self.engine, 'pool') else 'Unknown',
            'active_connections': self._active_connections,
            'total_created': self._total_connections_created,
            'error_count': self._connection_errors,
            'last_error': self._last_error_time.isoformat() if self._last_error_time else None,
            'pool_config': self.pool_config
        }
    
    def __repr__(self) -> str:
        """String representation of the connection pool."""
        return (
            f"ConnectionPool(active={self._active_connections}, "
            f"total_created={self._total_connections_created}, "
            f"errors={self._connection_errors})"
        )
