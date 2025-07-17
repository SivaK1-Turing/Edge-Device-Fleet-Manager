"""
Database Health Checker

Comprehensive health monitoring for database connections with
automatic recovery, metrics collection, and alerting capabilities.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ...core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthMetrics:
    """Health check metrics."""
    
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    last_check_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    average_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    uptime_percentage: float = 100.0
    response_times: List[float] = field(default_factory=list)
    
    def update_success(self, response_time_ms: float) -> None:
        """Update metrics for successful check."""
        self.total_checks += 1
        self.successful_checks += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_check_time = datetime.now(timezone.utc)
        self.last_success_time = self.last_check_time
        
        # Update response time metrics
        self.response_times.append(response_time_ms)
        if len(self.response_times) > 100:  # Keep last 100 measurements
            self.response_times.pop(0)
        
        self.average_response_time_ms = sum(self.response_times) / len(self.response_times)
        self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)
        self.min_response_time_ms = min(self.min_response_time_ms, response_time_ms)
        
        # Update uptime percentage
        if self.total_checks > 0:
            self.uptime_percentage = (self.successful_checks / self.total_checks) * 100
    
    def update_failure(self) -> None:
        """Update metrics for failed check."""
        self.total_checks += 1
        self.failed_checks += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_check_time = datetime.now(timezone.utc)
        self.last_failure_time = self.last_check_time
        
        # Update uptime percentage
        if self.total_checks > 0:
            self.uptime_percentage = (self.successful_checks / self.total_checks) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_checks': self.total_checks,
            'successful_checks': self.successful_checks,
            'failed_checks': self.failed_checks,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'average_response_time_ms': self.average_response_time_ms,
            'max_response_time_ms': self.max_response_time_ms,
            'min_response_time_ms': self.min_response_time_ms if self.min_response_time_ms != float('inf') else 0,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'uptime_percentage': self.uptime_percentage
        }


class HealthChecker:
    """
    Database health checker with monitoring and recovery capabilities.
    
    Provides continuous health monitoring, metrics collection,
    and automatic recovery mechanisms for database connections.
    """
    
    def __init__(self, engine: AsyncEngine, check_interval: int = 60, 
                 timeout: int = 10, failure_threshold: int = 3):
        """
        Initialize health checker.
        
        Args:
            engine: Database engine to monitor
            check_interval: Interval between health checks in seconds
            timeout: Timeout for health checks in seconds
            failure_threshold: Number of consecutive failures before marking unhealthy
        """
        self.engine = engine
        self.check_interval = check_interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        
        self.metrics = HealthMetrics()
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
        self._is_healthy = True
        self._callbacks: List[Callable[[bool, Dict[str, Any]], None]] = []
        
        logger.info(f"Health checker initialized with {check_interval}s interval")
    
    async def start(self) -> None:
        """Start health monitoring."""
        if self._is_running:
            logger.warning("Health checker already running")
            return
        
        self._is_running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health checker started")
    
    async def stop(self) -> None:
        """Stop health monitoring."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health checker stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def perform_health_check(self) -> bool:
        """
        Perform a single health check.
        
        Returns:
            True if healthy, False otherwise
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Perform health check with timeout
            await asyncio.wait_for(
                self._execute_health_query(),
                timeout=self.timeout
            )
            
            # Calculate response time
            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update metrics
            self.metrics.update_success(response_time_ms)
            
            # Update health status
            was_healthy = self._is_healthy
            self._is_healthy = True
            
            # Notify callbacks if status changed
            if not was_healthy:
                logger.info("Database health restored")
                await self._notify_callbacks(True, self.metrics.to_dict())
            
            logger.debug(f"Health check passed ({response_time_ms:.2f}ms)")
            return True
            
        except Exception as e:
            # Update metrics
            self.metrics.update_failure()
            
            # Update health status
            was_healthy = self._is_healthy
            if self.metrics.consecutive_failures >= self.failure_threshold:
                self._is_healthy = False
                
                # Notify callbacks if status changed
                if was_healthy:
                    logger.error(f"Database marked unhealthy after {self.failure_threshold} failures")
                    await self._notify_callbacks(False, self.metrics.to_dict())
            
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def _execute_health_query(self) -> None:
        """Execute health check query."""
        async with self.engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
    
    def is_healthy(self) -> bool:
        """
        Check if database is currently healthy.
        
        Returns:
            True if healthy
        """
        return self._is_healthy
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Dictionary with health status and metrics
        """
        return {
            'is_healthy': self._is_healthy,
            'is_monitoring': self._is_running,
            'check_interval': self.check_interval,
            'timeout': self.timeout,
            'failure_threshold': self.failure_threshold,
            'metrics': self.metrics.to_dict()
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed health statistics.
        
        Returns:
            Dictionary with health statistics
        """
        stats = await self.get_status()
        
        # Add additional statistics
        if self.metrics.total_checks > 0:
            stats['success_rate'] = (self.metrics.successful_checks / self.metrics.total_checks) * 100
            stats['failure_rate'] = (self.metrics.failed_checks / self.metrics.total_checks) * 100
        else:
            stats['success_rate'] = 0
            stats['failure_rate'] = 0
        
        # Add time since last check
        if self.metrics.last_check_time:
            time_since_last = datetime.now(timezone.utc) - self.metrics.last_check_time
            stats['seconds_since_last_check'] = time_since_last.total_seconds()
        
        return stats
    
    def add_callback(self, callback: Callable[[bool, Dict[str, Any]], None]) -> None:
        """
        Add callback for health status changes.
        
        Args:
            callback: Function to call when health status changes
                     Receives (is_healthy, metrics) as arguments
        """
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[bool, Dict[str, Any]], None]) -> None:
        """
        Remove health status change callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def _notify_callbacks(self, is_healthy: bool, metrics: Dict[str, Any]) -> None:
        """Notify all registered callbacks of health status change."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(is_healthy, metrics)
                else:
                    callback(is_healthy, metrics)
            except Exception as e:
                logger.error(f"Error in health status callback: {e}")
    
    async def force_check(self) -> bool:
        """
        Force an immediate health check.
        
        Returns:
            True if healthy
        """
        return await self.perform_health_check()
    
    def reset_metrics(self) -> None:
        """Reset all health metrics."""
        self.metrics = HealthMetrics()
        logger.info("Health metrics reset")
    
    async def wait_for_healthy(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for database to become healthy.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if became healthy within timeout
        """
        start_time = datetime.now(timezone.utc)
        
        while True:
            if self.is_healthy():
                return True
            
            if timeout:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= timeout:
                    return False
            
            await asyncio.sleep(1)
    
    def get_health_summary(self) -> str:
        """
        Get human-readable health summary.
        
        Returns:
            Health summary string
        """
        status = "HEALTHY" if self._is_healthy else "UNHEALTHY"
        
        if self.metrics.total_checks == 0:
            return f"Status: {status} (No checks performed yet)"
        
        return (
            f"Status: {status} | "
            f"Uptime: {self.metrics.uptime_percentage:.1f}% | "
            f"Checks: {self.metrics.total_checks} | "
            f"Avg Response: {self.metrics.average_response_time_ms:.1f}ms | "
            f"Consecutive Failures: {self.metrics.consecutive_failures}"
        )
