"""
Health Monitor

Comprehensive health monitoring system for tracking the operational status
and health of all Edge Device Fleet Manager components and services.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of components that can be monitored."""
    
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    EXTERNAL_API = "external_api"
    STORAGE = "storage"
    NETWORK = "network"
    DEVICE = "device"


@dataclass
class HealthCheck:
    """Represents a health check configuration."""
    
    name: str
    component_type: ComponentType
    check_function: Callable
    interval_seconds: int = 30
    timeout_seconds: int = 10
    retries: int = 3
    enabled: bool = True
    critical: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.interval_seconds < 1:
            raise ValueError("Interval must be at least 1 second")
        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be at least 1 second")
        if self.retries < 0:
            raise ValueError("Retries cannot be negative")


@dataclass
class HealthResult:
    """Represents the result of a health check."""
    
    check_name: str
    status: HealthStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'check_name': self.check_name,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms,
            'message': self.message,
            'details': self.details,
            'error': self.error
        }


class HealthMonitor:
    """
    Comprehensive health monitoring system.
    
    Monitors the health of various system components, services, and dependencies
    to provide real-time operational status and early warning of issues.
    """
    
    def __init__(self, metrics_collector=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize health monitor.
        
        Args:
            metrics_collector: Optional metrics collector for health metrics
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.metrics_collector = metrics_collector
        self.health_checks = {}  # Dict[str, HealthCheck]
        self.check_results = {}  # Dict[str, List[HealthResult]]
        self.check_tasks = {}  # Dict[str, asyncio.Task]
        self.overall_status = HealthStatus.UNKNOWN
        self.monitoring_enabled = False
        
        # Configuration
        self.max_result_history = self.config.get('max_result_history', 100)
        self.status_update_interval = self.config.get('status_update_interval', 10)
        self.alert_on_status_change = self.config.get('alert_on_status_change', True)
        
        self.logger = get_logger(f"{__name__}.HealthMonitor")
        
        # Initialize built-in health checks
        self._initialize_builtin_checks()
    
    def _initialize_builtin_checks(self):
        """Initialize built-in health checks."""
        # System health checks
        self.register_health_check(HealthCheck(
            name="system_memory",
            component_type=ComponentType.SERVICE,
            check_function=self._check_system_memory,
            interval_seconds=30,
            critical=True
        ))
        
        self.register_health_check(HealthCheck(
            name="system_disk_space",
            component_type=ComponentType.STORAGE,
            check_function=self._check_disk_space,
            interval_seconds=60,
            critical=True
        ))
        
        # Application health checks
        self.register_health_check(HealthCheck(
            name="application_startup",
            component_type=ComponentType.SERVICE,
            check_function=self._check_application_startup,
            interval_seconds=60,
            critical=True
        ))
    
    def register_health_check(self, health_check: HealthCheck):
        """
        Register a new health check.
        
        Args:
            health_check: HealthCheck configuration
        """
        self.health_checks[health_check.name] = health_check
        self.check_results[health_check.name] = []
        
        self.logger.info(f"Registered health check: {health_check.name}")
        
        # Start monitoring if already enabled
        if self.monitoring_enabled:
            self._start_health_check(health_check.name)
    
    def unregister_health_check(self, check_name: str):
        """
        Unregister a health check.
        
        Args:
            check_name: Name of the health check to remove
        """
        if check_name in self.health_checks:
            # Stop the check task
            if check_name in self.check_tasks:
                self.check_tasks[check_name].cancel()
                del self.check_tasks[check_name]
            
            # Remove from registry
            del self.health_checks[check_name]
            del self.check_results[check_name]
            
            self.logger.info(f"Unregistered health check: {check_name}")
    
    def start_monitoring(self):
        """Start health monitoring for all registered checks."""
        if self.monitoring_enabled:
            self.logger.warning("Health monitoring is already enabled")
            return
        
        self.monitoring_enabled = True
        
        # Start all health checks
        for check_name in self.health_checks:
            self._start_health_check(check_name)
        
        # Start overall status monitoring
        asyncio.create_task(self._monitor_overall_status())
        
        self.logger.info("Health monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop health monitoring."""
        if not self.monitoring_enabled:
            return
        
        self.monitoring_enabled = False
        
        # Cancel all check tasks
        for task in self.check_tasks.values():
            task.cancel()
        
        self.check_tasks.clear()
        
        self.logger.info("Health monitoring stopped")
    
    def _start_health_check(self, check_name: str):
        """Start monitoring for a specific health check."""
        if check_name not in self.health_checks:
            return
        
        health_check = self.health_checks[check_name]
        
        if not health_check.enabled:
            return
        
        # Cancel existing task if running
        if check_name in self.check_tasks:
            self.check_tasks[check_name].cancel()
        
        # Start new monitoring task
        self.check_tasks[check_name] = asyncio.create_task(
            self._health_check_loop(health_check)
        )
    
    async def _health_check_loop(self, health_check: HealthCheck):
        """Main loop for a health check."""
        while self.monitoring_enabled and health_check.enabled:
            try:
                result = await self._execute_health_check(health_check)
                self._store_result(result)
                
                # Record metrics if collector available
                if self.metrics_collector:
                    self._record_health_metrics(result)
                
                await asyncio.sleep(health_check.interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop for {health_check.name}: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _execute_health_check(self, health_check: HealthCheck) -> HealthResult:
        """Execute a single health check."""
        start_time = time.time()
        
        for attempt in range(health_check.retries + 1):
            try:
                # Execute the check function with timeout
                if asyncio.iscoroutinefunction(health_check.check_function):
                    result = await asyncio.wait_for(
                        health_check.check_function(),
                        timeout=health_check.timeout_seconds
                    )
                else:
                    result = health_check.check_function()
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Parse result
                if isinstance(result, bool):
                    status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                    message = "Check passed" if result else "Check failed"
                    details = {}
                elif isinstance(result, dict):
                    status = HealthStatus(result.get('status', 'unknown'))
                    message = result.get('message')
                    details = result.get('details', {})
                else:
                    status = HealthStatus.HEALTHY
                    message = str(result)
                    details = {}
                
                return HealthResult(
                    check_name=health_check.name,
                    status=status,
                    duration_ms=duration_ms,
                    message=message,
                    details=details
                )
                
            except asyncio.TimeoutError:
                if attempt < health_check.retries:
                    continue
                
                duration_ms = (time.time() - start_time) * 1000
                return HealthResult(
                    check_name=health_check.name,
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    message="Health check timed out",
                    error=f"Timeout after {health_check.timeout_seconds} seconds"
                )
                
            except Exception as e:
                if attempt < health_check.retries:
                    continue
                
                duration_ms = (time.time() - start_time) * 1000
                return HealthResult(
                    check_name=health_check.name,
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                    message="Health check failed with exception",
                    error=str(e)
                )
    
    def _store_result(self, result: HealthResult):
        """Store health check result."""
        check_name = result.check_name
        
        if check_name not in self.check_results:
            self.check_results[check_name] = []
        
        self.check_results[check_name].append(result)
        
        # Limit history size
        if len(self.check_results[check_name]) > self.max_result_history:
            self.check_results[check_name] = self.check_results[check_name][-self.max_result_history:]
    
    def _record_health_metrics(self, result: HealthResult):
        """Record health metrics."""
        if not self.metrics_collector:
            return
        
        # Record check duration
        self.metrics_collector.record_histogram(
            'health_check_duration_ms',
            result.duration_ms,
            labels={'check_name': result.check_name}
        )
        
        # Record check status
        status_value = 1 if result.status == HealthStatus.HEALTHY else 0
        self.metrics_collector.record_gauge(
            'health_check_status',
            status_value,
            labels={'check_name': result.check_name, 'status': result.status.value}
        )
        
        # Record check execution
        self.metrics_collector.record_counter(
            'health_check_executions_total',
            1,
            labels={'check_name': result.check_name, 'status': result.status.value}
        )
    
    async def _monitor_overall_status(self):
        """Monitor and update overall system status."""
        while self.monitoring_enabled:
            try:
                new_status = self._calculate_overall_status()
                
                if new_status != self.overall_status:
                    old_status = self.overall_status
                    self.overall_status = new_status
                    
                    self.logger.info(f"Overall health status changed: {old_status.value} -> {new_status.value}")
                    
                    # Record status change metric
                    if self.metrics_collector:
                        self.metrics_collector.record_counter(
                            'health_status_changes_total',
                            1,
                            labels={'from_status': old_status.value, 'to_status': new_status.value}
                        )
                
                await asyncio.sleep(self.status_update_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring overall status: {e}")
                await asyncio.sleep(5)
    
    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health status."""
        if not self.check_results:
            return HealthStatus.UNKNOWN
        
        critical_unhealthy = 0
        non_critical_unhealthy = 0
        degraded_count = 0
        total_checks = 0
        
        for check_name, results in self.check_results.items():
            if not results:
                continue
            
            latest_result = results[-1]
            health_check = self.health_checks.get(check_name)
            
            if not health_check:
                continue
            
            total_checks += 1
            
            if latest_result.status == HealthStatus.UNHEALTHY:
                if health_check.critical:
                    critical_unhealthy += 1
                else:
                    non_critical_unhealthy += 1
            elif latest_result.status == HealthStatus.DEGRADED:
                degraded_count += 1
        
        # Determine overall status
        if critical_unhealthy > 0:
            return HealthStatus.UNHEALTHY
        elif non_critical_unhealthy > total_checks * 0.5:  # More than 50% non-critical unhealthy
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0 or non_critical_unhealthy > 0:
            return HealthStatus.DEGRADED
        elif total_checks > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'overall_status': self.overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'monitoring_enabled': self.monitoring_enabled,
            'total_checks': len(self.health_checks),
            'active_checks': len([c for c in self.health_checks.values() if c.enabled]),
            'check_results': {
                name: results[-1].to_dict() if results else None
                for name, results in self.check_results.items()
            }
        }
    
    def get_check_history(self, check_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history for a specific health check."""
        if check_name not in self.check_results:
            return []
        
        results = self.check_results[check_name][-limit:]
        return [result.to_dict() for result in results]
    
    # Built-in health check functions
    async def _check_system_memory(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                return {
                    'status': 'unhealthy',
                    'message': f'High memory usage: {memory.percent:.1f}%',
                    'details': {'memory_percent': memory.percent, 'available_gb': memory.available / (1024**3)}
                }
            elif memory.percent > 80:
                return {
                    'status': 'degraded',
                    'message': f'Elevated memory usage: {memory.percent:.1f}%',
                    'details': {'memory_percent': memory.percent, 'available_gb': memory.available / (1024**3)}
                }
            else:
                return {
                    'status': 'healthy',
                    'message': f'Memory usage normal: {memory.percent:.1f}%',
                    'details': {'memory_percent': memory.percent, 'available_gb': memory.available / (1024**3)}
                }
        except ImportError:
            return {
                'status': 'unknown',
                'message': 'psutil not available for memory monitoring'
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 95:
                return {
                    'status': 'unhealthy',
                    'message': f'Critical disk usage: {usage_percent:.1f}%',
                    'details': {'disk_percent': usage_percent, 'free_gb': disk.free / (1024**3)}
                }
            elif usage_percent > 85:
                return {
                    'status': 'degraded',
                    'message': f'High disk usage: {usage_percent:.1f}%',
                    'details': {'disk_percent': usage_percent, 'free_gb': disk.free / (1024**3)}
                }
            else:
                return {
                    'status': 'healthy',
                    'message': f'Disk usage normal: {usage_percent:.1f}%',
                    'details': {'disk_percent': usage_percent, 'free_gb': disk.free / (1024**3)}
                }
        except (ImportError, OSError):
            return {
                'status': 'unknown',
                'message': 'Unable to check disk space'
            }
    
    async def _check_application_startup(self) -> Dict[str, Any]:
        """Check if application started successfully."""
        # This is a placeholder - would check actual application state
        return {
            'status': 'healthy',
            'message': 'Application running normally',
            'details': {'uptime_seconds': time.time()}
        }
    
    async def shutdown(self):
        """Shutdown the health monitor."""
        self.stop_monitoring()
        self.logger.info("Health monitor shutdown complete")
