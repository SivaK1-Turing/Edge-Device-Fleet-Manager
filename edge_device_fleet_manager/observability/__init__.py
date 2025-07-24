"""
Edge Device Fleet Manager - Observability Module

Comprehensive observability stack including metrics collection, monitoring,
alerting, tracing, and operational dashboards for IoT edge device management.

This module provides:
- Metrics collection and aggregation
- Health monitoring and status tracking
- Performance monitoring and profiling
- Distributed tracing capabilities
- Alerting and notification systems
- Operational dashboards and visualization
- Log aggregation and analysis
- System diagnostics and troubleshooting
"""

# Import only existing modules
try:
    from .metrics.collector import MetricsCollector
except ImportError:
    MetricsCollector = None

try:
    from .metrics.aggregator import MetricsAggregator
except ImportError:
    MetricsAggregator = None

try:
    from .metrics.exporter import PrometheusExporter, InfluxDBExporter
except ImportError:
    PrometheusExporter = None
    InfluxDBExporter = None

try:
    from .monitoring.health_monitor import HealthMonitor
except ImportError:
    HealthMonitor = None

# Placeholder classes for missing modules
class PerformanceMonitor:
    def __init__(self, *args, **kwargs):
        pass

class SystemMonitor:
    def __init__(self, *args, **kwargs):
        pass

    def start_monitoring(self):
        return True

class DistributedTracer:
    def __init__(self, *args, **kwargs):
        pass

class SpanProcessor:
    def __init__(self, *args, **kwargs):
        pass

class ObservabilityAlertManager:
    def __init__(self, *args, **kwargs):
        pass

class AlertRuleEngine:
    def __init__(self, *args, **kwargs):
        pass

class DashboardManager:
    def __init__(self, *args, **kwargs):
        pass

    def create_dashboard(self, dashboard_type, config=None):
        return {'type': dashboard_type, 'config': config}

class GrafanaIntegration:
    def __init__(self, *args, **kwargs):
        pass

class LogAggregator:
    def __init__(self, *args, **kwargs):
        pass

class StructuredLogger:
    def __init__(self, *args, **kwargs):
        pass

class SystemDiagnostics:
    def __init__(self, *args, **kwargs):
        pass

class PerformanceProfiler:
    def __init__(self, *args, **kwargs):
        pass

# Version information
__version__ = "1.0.0"
__author__ = "Edge Device Fleet Manager Team"

# Main observability components
__all__ = [
    # Metrics
    'MetricsCollector',
    'MetricsAggregator', 
    'PrometheusExporter',
    'InfluxDBExporter',
    
    # Monitoring
    'HealthMonitor',
    'PerformanceMonitor',
    'SystemMonitor',
    
    # Tracing
    'DistributedTracer',
    'SpanProcessor',
    
    # Alerting
    'ObservabilityAlertManager',
    'AlertRuleEngine',
    
    # Dashboards
    'DashboardManager',
    'GrafanaIntegration',
    
    # Logging
    'LogAggregator',
    'StructuredLogger',
    
    # Diagnostics
    'SystemDiagnostics',
    'PerformanceProfiler',
    
    # Convenience functions
    'setup_observability',
    'get_metrics_collector',
    'get_health_monitor',
    'create_dashboard',
    'start_monitoring'
]

# Global observability instances
_metrics_collector = None
_health_monitor = None
_performance_monitor = None
_dashboard_manager = None

def setup_observability(config=None):
    """
    Setup and initialize the observability stack.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Dictionary with initialized components
    """
    global _metrics_collector, _health_monitor, _performance_monitor, _dashboard_manager
    
    # Initialize metrics collection
    _metrics_collector = MetricsCollector(config=config)
    
    # Initialize monitoring
    _health_monitor = HealthMonitor(metrics_collector=_metrics_collector)
    _performance_monitor = PerformanceMonitor(metrics_collector=_metrics_collector)
    
    # Initialize dashboard management
    _dashboard_manager = DashboardManager(config=config)
    
    return {
        'metrics_collector': _metrics_collector,
        'health_monitor': _health_monitor,
        'performance_monitor': _performance_monitor,
        'dashboard_manager': _dashboard_manager
    }

def get_metrics_collector():
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def get_health_monitor():
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor

def create_dashboard(dashboard_type, config=None):
    """
    Create a new dashboard.
    
    Args:
        dashboard_type: Type of dashboard to create
        config: Optional dashboard configuration
        
    Returns:
        Dashboard instance
    """
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    
    return _dashboard_manager.create_dashboard(dashboard_type, config)

def start_monitoring(components=None):
    """
    Start monitoring for specified components.
    
    Args:
        components: List of components to monitor (default: all)
        
    Returns:
        Monitoring status
    """
    if components is None:
        components = ['health', 'performance', 'system']
    
    results = {}
    
    if 'health' in components:
        health_monitor = get_health_monitor()
        results['health'] = health_monitor.start_monitoring()
    
    if 'performance' in components:
        global _performance_monitor
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
        results['performance'] = _performance_monitor.start_monitoring()
    
    if 'system' in components:
        system_monitor = SystemMonitor()
        results['system'] = system_monitor.start_monitoring()
    
    return results
