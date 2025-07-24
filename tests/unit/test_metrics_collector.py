"""
Unit tests for MetricsCollector
"""

import unittest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.observability.metrics.collector import (
    MetricsCollector, Metric, MetricSeries, MetricType
)


class TestMetric(unittest.TestCase):
    """Test Metric class."""
    
    def test_metric_creation(self):
        """Test metric creation."""
        metric = Metric(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            labels={"service": "test"}
        )
        
        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.value, 42.5)
        self.assertEqual(metric.metric_type, MetricType.GAUGE)
        self.assertEqual(metric.labels["service"], "test")
        self.assertIsInstance(metric.timestamp, datetime)
    
    def test_metric_to_dict(self):
        """Test metric dictionary conversion."""
        metric = Metric(
            name="test_metric",
            value=100,
            metric_type=MetricType.COUNTER,
            unit="requests",
            description="Test counter metric"
        )
        
        metric_dict = metric.to_dict()
        
        self.assertEqual(metric_dict["name"], "test_metric")
        self.assertEqual(metric_dict["value"], 100)
        self.assertEqual(metric_dict["type"], "counter")
        self.assertEqual(metric_dict["unit"], "requests")
        self.assertEqual(metric_dict["description"], "Test counter metric")
        self.assertIn("timestamp", metric_dict)


class TestMetricSeries(unittest.TestCase):
    """Test MetricSeries class."""
    
    def test_series_creation(self):
        """Test metric series creation."""
        series = MetricSeries(
            name="test_series",
            metric_type=MetricType.HISTOGRAM,
            labels={"endpoint": "/api/test"}
        )
        
        self.assertEqual(series.name, "test_series")
        self.assertEqual(series.metric_type, MetricType.HISTOGRAM)
        self.assertEqual(series.labels["endpoint"], "/api/test")
        self.assertEqual(len(series.values), 0)
    
    def test_add_value(self):
        """Test adding values to series."""
        series = MetricSeries("test_series", MetricType.GAUGE)
        
        series.add_value(10.5)
        series.add_value(20.0)
        
        self.assertEqual(len(series.values), 2)
        self.assertEqual(series.values[0]["value"], 10.5)
        self.assertEqual(series.values[1]["value"], 20.0)
    
    def test_get_latest_value(self):
        """Test getting latest value."""
        series = MetricSeries("test_series", MetricType.GAUGE)
        
        # No values
        self.assertIsNone(series.get_latest_value())
        
        # Add values
        series.add_value(15.0)
        series.add_value(25.0)
        
        latest = series.get_latest_value()
        self.assertEqual(latest["value"], 25.0)
    
    def test_get_values_in_range(self):
        """Test getting values in time range."""
        series = MetricSeries("test_series", MetricType.GAUGE)
        
        # Add values with specific timestamps
        start_time = datetime.now(timezone.utc)
        series.add_value(10.0, start_time)
        
        middle_time = datetime.now(timezone.utc)
        series.add_value(20.0, middle_time)
        
        end_time = datetime.now(timezone.utc)
        series.add_value(30.0, end_time)
        
        # Get values in range
        values = series.get_values_in_range(start_time, end_time)
        self.assertEqual(len(values), 3)


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector(config={'collection_interval': 1})
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        self.assertIsNotNone(self.collector)
        self.assertEqual(self.collector.collection_interval, 1)
        self.assertTrue(self.collector.enabled)
        self.assertEqual(len(self.collector.counters), 0)
        self.assertEqual(len(self.collector.gauges), 0)
    
    def test_record_counter(self):
        """Test recording counter metrics."""
        self.collector.record_counter("test_counter", 5)
        self.collector.record_counter("test_counter", 3)
        
        value = self.collector.get_metric_value("test_counter")
        self.assertEqual(value, 8)  # 5 + 3
    
    def test_record_gauge(self):
        """Test recording gauge metrics."""
        self.collector.record_gauge("test_gauge", 42.5)
        self.collector.record_gauge("test_gauge", 37.2)
        
        value = self.collector.get_metric_value("test_gauge")
        self.assertEqual(value, 37.2)  # Latest value
    
    def test_record_histogram(self):
        """Test recording histogram metrics."""
        self.collector.record_histogram("test_histogram", 100)
        self.collector.record_histogram("test_histogram", 150)
        self.collector.record_histogram("test_histogram", 200)
        
        key = self.collector._get_metric_key("test_histogram")
        values = self.collector.histograms[key]
        self.assertEqual(len(values), 3)
        self.assertIn(100, values)
        self.assertIn(150, values)
        self.assertIn(200, values)
    
    def test_record_timer(self):
        """Test recording timer metrics."""
        self.collector.record_timer("test_timer", 1.5)
        self.collector.record_timer("test_timer", 2.3)
        
        key = self.collector._get_metric_key("test_timer")
        values = self.collector.timers[key]
        self.assertEqual(len(values), 2)
        self.assertIn(1.5, values)
        self.assertIn(2.3, values)
    
    def test_metric_with_labels(self):
        """Test metrics with labels."""
        labels = {"service": "api", "endpoint": "/users"}
        
        self.collector.record_counter("requests", 1, labels)
        self.collector.record_counter("requests", 2, labels)
        
        value = self.collector.get_metric_value("requests", labels)
        self.assertEqual(value, 3)
        
        # Different labels should be separate
        other_labels = {"service": "api", "endpoint": "/orders"}
        self.collector.record_counter("requests", 5, other_labels)
        
        value_other = self.collector.get_metric_value("requests", other_labels)
        self.assertEqual(value_other, 5)
        
        # Original should be unchanged
        value_original = self.collector.get_metric_value("requests", labels)
        self.assertEqual(value_original, 3)
    
    def test_get_metric_key(self):
        """Test metric key generation."""
        # No labels
        key = self.collector._get_metric_key("test_metric")
        self.assertEqual(key, "test_metric")
        
        # With labels
        labels = {"service": "api", "method": "GET"}
        key = self.collector._get_metric_key("test_metric", labels)
        self.assertEqual(key, "test_metric{method=GET,service=api}")
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        self.collector.record_counter("counter1", 10)
        self.collector.record_gauge("gauge1", 25.5)
        self.collector.record_histogram("hist1", 100)
        self.collector.record_timer("timer1", 1.5)
        
        all_metrics = self.collector.get_all_metrics()
        
        self.assertIn("counters", all_metrics)
        self.assertIn("gauges", all_metrics)
        self.assertIn("histograms", all_metrics)
        self.assertIn("timers", all_metrics)
        self.assertIn("timestamp", all_metrics)
        
        self.assertEqual(all_metrics["counters"]["counter1"], 10)
        self.assertEqual(all_metrics["gauges"]["gauge1"], 25.5)
    
    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        self.collector.record_counter("counter1", 1)
        self.collector.record_counter("counter2", 2)
        self.collector.record_gauge("gauge1", 1.0)
        
        summary = self.collector.get_metrics_summary()
        
        self.assertEqual(summary["counters"], 2)
        self.assertEqual(summary["gauges"], 1)
        self.assertEqual(summary["histograms"], 0)
        self.assertEqual(summary["timers"], 0)
        self.assertTrue(summary["collection_enabled"])
    
    def test_register_collector(self):
        """Test registering metric collectors."""
        def test_collector():
            self.collector.record_gauge("test_metric", 42)
        
        self.collector.register_collector("test", test_collector)
        self.assertIn("test", self.collector.collectors)
        
        # Execute collector
        test_collector()
        value = self.collector.get_metric_value("test_metric")
        self.assertEqual(value, 42)
    
    def test_unregister_collector(self):
        """Test unregistering metric collectors."""
        def test_collector():
            pass
        
        self.collector.register_collector("test", test_collector)
        self.assertIn("test", self.collector.collectors)
        
        self.collector.unregister_collector("test")
        self.assertNotIn("test", self.collector.collectors)
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        self.collector.record_counter("counter1", 10)
        self.collector.record_gauge("gauge1", 25.5)
        
        # Verify metrics exist
        self.assertEqual(len(self.collector.counters), 1)
        self.assertEqual(len(self.collector.gauges), 1)
        
        # Reset
        self.collector.reset_metrics()
        
        # Verify metrics are cleared
        self.assertEqual(len(self.collector.counters), 0)
        self.assertEqual(len(self.collector.gauges), 0)
        self.assertEqual(len(self.collector.metrics), 0)
    
    @patch('psutil.cpu_percent')
    def test_builtin_cpu_collector(self, mock_cpu):
        """Test built-in CPU collector."""
        mock_cpu.return_value = 75.5
        
        self.collector._collect_cpu_usage()
        
        value = self.collector.get_metric_value("system_cpu_usage_percent")
        self.assertEqual(value, 75.5)
    
    @patch('psutil.virtual_memory')
    def test_builtin_memory_collector(self, mock_memory):
        """Test built-in memory collector."""
        mock_memory.return_value = Mock(
            percent=60.0,
            used=8000000000,
            available=4000000000
        )
        
        self.collector._collect_memory_usage()
        
        percent = self.collector.get_metric_value("system_memory_usage_percent")
        used = self.collector.get_metric_value("system_memory_used_bytes")
        available = self.collector.get_metric_value("system_memory_available_bytes")
        
        self.assertEqual(percent, 60.0)
        self.assertEqual(used, 8000000000)
        self.assertEqual(available, 4000000000)


class TestMetricsCollectorAsync(unittest.IsolatedAsyncioTestCase):
    """Test async functionality of MetricsCollector."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.collector = MetricsCollector(config={'collection_interval': 0.1})
    
    async def test_collect_all_metrics(self):
        """Test collecting all metrics."""
        # Register a test collector
        def test_collector():
            self.collector.record_gauge("test_metric", 100)
        
        self.collector.register_collector("test", test_collector)
        
        # Collect metrics
        await self.collector.collect_all_metrics()
        
        # Verify metric was collected
        value = self.collector.get_metric_value("test_metric")
        self.assertEqual(value, 100)
        
        # Verify collection metrics
        collection_count = self.collector.get_metric_value("metrics_collection_total")
        self.assertGreaterEqual(collection_count, 1)
    
    async def test_async_collector(self):
        """Test async metric collector."""
        async def async_collector():
            await asyncio.sleep(0.01)  # Simulate async work
            self.collector.record_counter("async_metric", 1)
        
        self.collector.register_collector("async_test", async_collector)
        
        # Collect metrics
        await self.collector.collect_all_metrics()
        
        # Verify async metric was collected
        value = self.collector.get_metric_value("async_metric")
        self.assertEqual(value, 1)
    
    async def test_collection_loop(self):
        """Test metrics collection loop."""
        # Register a test collector
        call_count = 0
        
        def counting_collector():
            nonlocal call_count
            call_count += 1
            self.collector.record_gauge("loop_test", call_count)
        
        self.collector.register_collector("counting", counting_collector)
        
        # Start collection
        self.collector.start_collection()
        
        # Wait for a few collection cycles
        await asyncio.sleep(0.3)
        
        # Stop collection
        self.collector.stop_collection()
        
        # Verify multiple collections occurred
        value = self.collector.get_metric_value("loop_test")
        self.assertGreater(value, 1)
    
    async def test_export_metrics(self):
        """Test metrics export."""
        # Mock exporter
        exported_data = None
        
        class MockExporter:
            async def export(self, data):
                nonlocal exported_data
                exported_data = data
        
        exporter = MockExporter()
        self.collector.add_exporter(exporter)
        
        # Add some metrics
        self.collector.record_counter("export_test", 42)
        
        # Export metrics
        await self.collector.export_metrics()
        
        # Verify export
        self.assertIsNotNone(exported_data)
        self.assertIn("counters", exported_data)
        self.assertEqual(exported_data["counters"]["export_test"], 42)
    
    async def test_shutdown(self):
        """Test collector shutdown."""
        # Add some metrics
        self.collector.record_gauge("shutdown_test", 123)
        
        # Start collection
        self.collector.start_collection()
        
        # Shutdown
        await self.collector.shutdown()
        
        # Verify shutdown
        self.assertFalse(self.collector.enabled)
        
        # Collection task should be cancelled
        if self.collector.collection_task:
            self.assertTrue(self.collector.collection_task.cancelled() or 
                          self.collector.collection_task.done())


if __name__ == "__main__":
    unittest.main()
