"""
Metrics Collector

Comprehensive metrics collection system for gathering, processing, and storing
performance, operational, and business metrics from the Edge Device Fleet Manager.
"""

import asyncio
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timezone
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


@dataclass
class Metric:
    """Represents a single metric measurement."""
    
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary representation."""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'unit': self.unit,
            'description': self.description
        }


@dataclass
class MetricSeries:
    """Represents a time series of metric values."""
    
    name: str
    metric_type: MetricType
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    description: Optional[str] = None
    
    def add_value(self, value: Union[int, float], timestamp: Optional[datetime] = None):
        """Add a value to the time series."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.values.append({
            'value': value,
            'timestamp': timestamp.isoformat()
        })
    
    def get_latest_value(self) -> Optional[Dict[str, Any]]:
        """Get the most recent value."""
        return self.values[-1] if self.values else None
    
    def get_values_in_range(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get values within a time range."""
        result = []
        for value_data in self.values:
            value_time = datetime.fromisoformat(value_data['timestamp'].replace('Z', '+00:00'))
            if start_time <= value_time <= end_time:
                result.append(value_data)
        return result


class MetricsCollector:
    """
    Comprehensive metrics collection system.
    
    Collects, processes, and stores metrics from various sources including
    system performance, application metrics, and business metrics.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.metrics = {}  # Dict[str, MetricSeries]
        self.collectors = {}  # Dict[str, Callable]
        self.exporters = []
        self.collection_interval = self.config.get('collection_interval', 30)  # seconds
        self.max_series_length = self.config.get('max_series_length', 1000)
        self.enabled = True
        self.collection_task = None
        self.lock = threading.RLock()
        
        # Built-in metric counters
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timers = defaultdict(list)
        
        self.logger = get_logger(f"{__name__}.MetricsCollector")
        
        # Initialize built-in metrics
        self._initialize_builtin_metrics()
    
    def _initialize_builtin_metrics(self):
        """Initialize built-in system and application metrics."""
        # System metrics
        self.register_collector('system_cpu_usage', self._collect_cpu_usage)
        self.register_collector('system_memory_usage', self._collect_memory_usage)
        self.register_collector('system_disk_usage', self._collect_disk_usage)
        
        # Application metrics
        self.register_collector('app_request_count', self._collect_request_count)
        self.register_collector('app_response_time', self._collect_response_time)
        self.register_collector('app_error_rate', self._collect_error_rate)
        
        # Device metrics
        self.register_collector('device_count', self._collect_device_count)
        self.register_collector('device_health_score', self._collect_device_health)
        self.register_collector('alert_count', self._collect_alert_count)
    
    def start_collection(self):
        """Start automatic metrics collection."""
        if self.collection_task is None or self.collection_task.done():
            self.collection_task = asyncio.create_task(self._collection_loop())
            self.logger.info("Metrics collection started")
    
    def stop_collection(self):
        """Stop automatic metrics collection."""
        if self.collection_task and not self.collection_task.done():
            self.collection_task.cancel()
            self.logger.info("Metrics collection stopped")
    
    async def _collection_loop(self):
        """Main collection loop."""
        while self.enabled:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def collect_all_metrics(self):
        """Collect all registered metrics."""
        collection_start = time.time()
        
        for name, collector_func in self.collectors.items():
            try:
                if asyncio.iscoroutinefunction(collector_func):
                    await collector_func()
                else:
                    collector_func()
            except Exception as e:
                self.logger.error(f"Error collecting metric {name}: {e}")
        
        # Record collection performance
        collection_duration = time.time() - collection_start
        self.record_gauge('metrics_collection_duration_seconds', collection_duration)
        self.record_counter('metrics_collection_total', 1)
    
    def register_collector(self, name: str, collector_func: Callable):
        """
        Register a metric collector function.
        
        Args:
            name: Name of the metric
            collector_func: Function that collects the metric
        """
        self.collectors[name] = collector_func
        self.logger.debug(f"Registered metric collector: {name}")
    
    def unregister_collector(self, name: str):
        """Unregister a metric collector."""
        if name in self.collectors:
            del self.collectors[name]
            self.logger.debug(f"Unregistered metric collector: {name}")
    
    def record_counter(self, name: str, value: Union[int, float] = 1, 
                      labels: Optional[Dict[str, str]] = None):
        """
        Record a counter metric.
        
        Args:
            name: Metric name
            value: Value to add to counter
            labels: Optional labels
        """
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.counters[key] += value
            
            # Store in time series
            self._store_metric(name, value, MetricType.COUNTER, labels)
    
    def record_gauge(self, name: str, value: Union[int, float],
                    labels: Optional[Dict[str, str]] = None):
        """
        Record a gauge metric.
        
        Args:
            name: Metric name
            value: Current value
            labels: Optional labels
        """
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.gauges[key] = value
            
            # Store in time series
            self._store_metric(name, value, MetricType.GAUGE, labels)
    
    def record_histogram(self, name: str, value: Union[int, float],
                        labels: Optional[Dict[str, str]] = None):
        """
        Record a histogram metric.
        
        Args:
            name: Metric name
            value: Value to record
            labels: Optional labels
        """
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.histograms[key].append(value)
            
            # Limit histogram size
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            
            # Store in time series
            self._store_metric(name, value, MetricType.HISTOGRAM, labels)
    
    def record_timer(self, name: str, duration: float,
                    labels: Optional[Dict[str, str]] = None):
        """
        Record a timer metric.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            labels: Optional labels
        """
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.timers[key].append(duration)
            
            # Limit timer history
            if len(self.timers[key]) > 1000:
                self.timers[key] = self.timers[key][-1000:]
            
            # Store in time series
            self._store_metric(name, duration, MetricType.TIMER, labels)
    
    def _store_metric(self, name: str, value: Union[int, float], 
                     metric_type: MetricType, labels: Optional[Dict[str, str]] = None):
        """Store metric in time series."""
        series_key = self._get_metric_key(name, labels)
        
        if series_key not in self.metrics:
            self.metrics[series_key] = MetricSeries(
                name=name,
                metric_type=metric_type,
                labels=labels or {},
                values=deque(maxlen=self.max_series_length)
            )
        
        self.metrics[series_key].add_value(value)
    
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate a unique key for a metric with labels."""
        if not labels:
            return name
        
        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get the current value of a metric."""
        key = self._get_metric_key(name, labels)
        
        # Try different metric types
        if key in self.gauges:
            return self.gauges[key]
        elif key in self.counters:
            return self.counters[key]
        elif key in self.metrics:
            latest = self.metrics[key].get_latest_value()
            return latest['value'] if latest else None
        
        return None
    
    def get_metric_series(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[MetricSeries]:
        """Get the time series for a metric."""
        key = self._get_metric_key(name, labels)
        return self.metrics.get(key)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metric values."""
        with self.lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {k: list(v) for k, v in self.histograms.items()},
                'timers': {k: list(v) for k, v in self.timers.items()},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        with self.lock:
            return {
                'total_metrics': len(self.metrics),
                'counters': len(self.counters),
                'gauges': len(self.gauges),
                'histograms': len(self.histograms),
                'timers': len(self.timers),
                'collectors': len(self.collectors),
                'collection_enabled': self.enabled,
                'collection_interval': self.collection_interval
            }
    
    # Built-in metric collectors
    def _collect_cpu_usage(self):
        """Collect CPU usage metrics."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            self.record_gauge('system_cpu_usage_percent', cpu_percent)
        except ImportError:
            # Fallback if psutil not available
            self.record_gauge('system_cpu_usage_percent', 0.0)
    
    def _collect_memory_usage(self):
        """Collect memory usage metrics."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            self.record_gauge('system_memory_usage_percent', memory.percent)
            self.record_gauge('system_memory_used_bytes', memory.used)
            self.record_gauge('system_memory_available_bytes', memory.available)
        except ImportError:
            # Fallback if psutil not available
            self.record_gauge('system_memory_usage_percent', 0.0)
    
    def _collect_disk_usage(self):
        """Collect disk usage metrics."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            self.record_gauge('system_disk_usage_percent', (disk.used / disk.total) * 100)
            self.record_gauge('system_disk_used_bytes', disk.used)
            self.record_gauge('system_disk_free_bytes', disk.free)
        except (ImportError, OSError):
            # Fallback if psutil not available or path doesn't exist
            self.record_gauge('system_disk_usage_percent', 0.0)
    
    def _collect_request_count(self):
        """Collect application request count."""
        # This would be populated by the application
        pass
    
    def _collect_response_time(self):
        """Collect application response time."""
        # This would be populated by the application
        pass
    
    def _collect_error_rate(self):
        """Collect application error rate."""
        # This would be populated by the application
        pass
    
    def _collect_device_count(self):
        """Collect device count metrics."""
        # This would integrate with the device manager
        pass
    
    def _collect_device_health(self):
        """Collect device health metrics."""
        # This would integrate with the device manager
        pass
    
    def _collect_alert_count(self):
        """Collect alert count metrics."""
        # This would integrate with the alert manager
        pass
    
    def add_exporter(self, exporter):
        """Add a metrics exporter."""
        self.exporters.append(exporter)
        self.logger.info(f"Added metrics exporter: {type(exporter).__name__}")
    
    async def export_metrics(self):
        """Export metrics to all registered exporters."""
        metrics_data = self.get_all_metrics()
        
        for exporter in self.exporters:
            try:
                if asyncio.iscoroutinefunction(exporter.export):
                    await exporter.export(metrics_data)
                else:
                    exporter.export(metrics_data)
            except Exception as e:
                self.logger.error(f"Error exporting metrics with {type(exporter).__name__}: {e}")
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self.lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.metrics.clear()
        
        self.logger.info("All metrics reset")
    
    async def shutdown(self):
        """Shutdown the metrics collector."""
        self.enabled = False
        self.stop_collection()
        
        # Final export
        await self.export_metrics()
        
        self.logger.info("Metrics collector shutdown complete")
