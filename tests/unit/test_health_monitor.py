"""
Unit tests for HealthMonitor
"""

import unittest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.observability.monitoring.health_monitor import (
    HealthMonitor, HealthCheck, HealthResult, HealthStatus, ComponentType
)


class TestHealthCheck(unittest.TestCase):
    """Test HealthCheck class."""
    
    def test_health_check_creation(self):
        """Test health check creation."""
        def test_function():
            return True
        
        check = HealthCheck(
            name="test_check",
            component_type=ComponentType.SERVICE,
            check_function=test_function,
            interval_seconds=30,
            timeout_seconds=10,
            retries=2,
            critical=True,
            tags={"env": "test"}
        )
        
        self.assertEqual(check.name, "test_check")
        self.assertEqual(check.component_type, ComponentType.SERVICE)
        self.assertEqual(check.check_function, test_function)
        self.assertEqual(check.interval_seconds, 30)
        self.assertEqual(check.timeout_seconds, 10)
        self.assertEqual(check.retries, 2)
        self.assertTrue(check.critical)
        self.assertEqual(check.tags["env"], "test")
        self.assertTrue(check.enabled)
    
    def test_health_check_validation(self):
        """Test health check validation."""
        def test_function():
            return True
        
        # Invalid interval
        with self.assertRaises(ValueError):
            HealthCheck(
                name="test",
                component_type=ComponentType.SERVICE,
                check_function=test_function,
                interval_seconds=0
            )
        
        # Invalid timeout
        with self.assertRaises(ValueError):
            HealthCheck(
                name="test",
                component_type=ComponentType.SERVICE,
                check_function=test_function,
                timeout_seconds=0
            )
        
        # Invalid retries
        with self.assertRaises(ValueError):
            HealthCheck(
                name="test",
                component_type=ComponentType.SERVICE,
                check_function=test_function,
                retries=-1
            )


class TestHealthResult(unittest.TestCase):
    """Test HealthResult class."""
    
    def test_health_result_creation(self):
        """Test health result creation."""
        result = HealthResult(
            check_name="test_check",
            status=HealthStatus.HEALTHY,
            duration_ms=150.5,
            message="Check passed",
            details={"response_time": 100},
            error=None
        )
        
        self.assertEqual(result.check_name, "test_check")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.duration_ms, 150.5)
        self.assertEqual(result.message, "Check passed")
        self.assertEqual(result.details["response_time"], 100)
        self.assertIsNone(result.error)
        self.assertIsInstance(result.timestamp, datetime)
    
    def test_health_result_to_dict(self):
        """Test health result dictionary conversion."""
        result = HealthResult(
            check_name="test_check",
            status=HealthStatus.DEGRADED,
            duration_ms=250.0,
            message="Performance degraded",
            details={"cpu_usage": 85},
            error="High CPU usage"
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict["check_name"], "test_check")
        self.assertEqual(result_dict["status"], "degraded")
        self.assertEqual(result_dict["duration_ms"], 250.0)
        self.assertEqual(result_dict["message"], "Performance degraded")
        self.assertEqual(result_dict["details"]["cpu_usage"], 85)
        self.assertEqual(result_dict["error"], "High CPU usage")
        self.assertIn("timestamp", result_dict)


class TestHealthMonitor(unittest.TestCase):
    """Test HealthMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = HealthMonitor(config={'max_result_history': 10})
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.max_result_history, 10)
        self.assertFalse(self.monitor.monitoring_enabled)
        self.assertEqual(self.monitor.overall_status, HealthStatus.UNKNOWN)
        self.assertEqual(len(self.monitor.health_checks), 0)
    
    def test_register_health_check(self):
        """Test registering health checks."""
        def test_function():
            return True
        
        check = HealthCheck(
            name="test_check",
            component_type=ComponentType.SERVICE,
            check_function=test_function
        )
        
        self.monitor.register_health_check(check)
        
        self.assertIn("test_check", self.monitor.health_checks)
        self.assertIn("test_check", self.monitor.check_results)
        self.assertEqual(len(self.monitor.check_results["test_check"]), 0)
    
    def test_unregister_health_check(self):
        """Test unregistering health checks."""
        def test_function():
            return True
        
        check = HealthCheck(
            name="test_check",
            component_type=ComponentType.SERVICE,
            check_function=test_function
        )
        
        self.monitor.register_health_check(check)
        self.assertIn("test_check", self.monitor.health_checks)
        
        self.monitor.unregister_health_check("test_check")
        self.assertNotIn("test_check", self.monitor.health_checks)
        self.assertNotIn("test_check", self.monitor.check_results)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Initially not monitoring
        self.assertFalse(self.monitor.monitoring_enabled)
        
        # Start monitoring
        result = self.monitor.start_monitoring()
        self.assertTrue(result)
        self.assertTrue(self.monitor.monitoring_enabled)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring_enabled)
    
    def test_get_health_status(self):
        """Test getting health status."""
        status = self.monitor.get_health_status()
        
        self.assertIn("overall_status", status)
        self.assertIn("timestamp", status)
        self.assertIn("monitoring_enabled", status)
        self.assertIn("total_checks", status)
        self.assertIn("active_checks", status)
        self.assertIn("check_results", status)
        
        self.assertEqual(status["overall_status"], "unknown")
        self.assertFalse(status["monitoring_enabled"])
        self.assertEqual(status["total_checks"], 0)
    
    def test_get_check_history(self):
        """Test getting check history."""
        # No history initially
        history = self.monitor.get_check_history("nonexistent")
        self.assertEqual(len(history), 0)
        
        # Add some results manually
        result1 = HealthResult("test_check", HealthStatus.HEALTHY, 100.0)
        result2 = HealthResult("test_check", HealthStatus.DEGRADED, 200.0)
        
        self.monitor.check_results["test_check"] = [result1, result2]
        
        history = self.monitor.get_check_history("test_check", limit=5)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["status"], "healthy")
        self.assertEqual(history[1]["status"], "degraded")
    
    def test_calculate_overall_status(self):
        """Test overall status calculation."""
        # No checks - should be unknown
        status = self.monitor._calculate_overall_status()
        self.assertEqual(status, HealthStatus.UNKNOWN)
        
        # Add healthy check
        healthy_result = HealthResult("healthy_check", HealthStatus.HEALTHY, 100.0)
        self.monitor.check_results["healthy_check"] = [healthy_result]
        self.monitor.health_checks["healthy_check"] = HealthCheck(
            "healthy_check", ComponentType.SERVICE, lambda: True, critical=False
        )
        
        status = self.monitor._calculate_overall_status()
        self.assertEqual(status, HealthStatus.HEALTHY)
        
        # Add critical unhealthy check
        unhealthy_result = HealthResult("critical_check", HealthStatus.UNHEALTHY, 100.0)
        self.monitor.check_results["critical_check"] = [unhealthy_result]
        self.monitor.health_checks["critical_check"] = HealthCheck(
            "critical_check", ComponentType.SERVICE, lambda: False, critical=True
        )
        
        status = self.monitor._calculate_overall_status()
        self.assertEqual(status, HealthStatus.UNHEALTHY)
    
    def test_store_result(self):
        """Test storing health check results."""
        result = HealthResult("test_check", HealthStatus.HEALTHY, 100.0)
        
        self.monitor._store_result(result)
        
        self.assertIn("test_check", self.monitor.check_results)
        self.assertEqual(len(self.monitor.check_results["test_check"]), 1)
        self.assertEqual(self.monitor.check_results["test_check"][0], result)
    
    def test_store_result_history_limit(self):
        """Test result history size limit."""
        self.monitor.max_result_history = 3
        
        # Add more results than limit
        for i in range(5):
            result = HealthResult(f"test_check", HealthStatus.HEALTHY, 100.0 + i)
            self.monitor._store_result(result)
        
        # Should only keep the limit
        self.assertEqual(len(self.monitor.check_results["test_check"]), 3)
        
        # Should keep the latest results
        latest_result = self.monitor.check_results["test_check"][-1]
        self.assertEqual(latest_result.duration_ms, 104.0)  # Last added
    
    @patch('psutil.virtual_memory')
    def test_builtin_memory_check(self, mock_memory):
        """Test built-in memory check."""
        # Test healthy memory
        mock_memory.return_value = Mock(
            percent=50.0,
            available=8000000000
        )
        
        result = asyncio.run(self.monitor._check_system_memory())
        
        self.assertEqual(result["status"], "healthy")
        self.assertIn("Memory usage normal", result["message"])
        self.assertEqual(result["details"]["memory_percent"], 50.0)
        
        # Test degraded memory
        mock_memory.return_value = Mock(
            percent=85.0,
            available=2000000000
        )
        
        result = asyncio.run(self.monitor._check_system_memory())
        
        self.assertEqual(result["status"], "degraded")
        self.assertIn("Elevated memory usage", result["message"])
        
        # Test unhealthy memory
        mock_memory.return_value = Mock(
            percent=95.0,
            available=500000000
        )
        
        result = asyncio.run(self.monitor._check_system_memory())
        
        self.assertEqual(result["status"], "unhealthy")
        self.assertIn("High memory usage", result["message"])
    
    @patch('psutil.disk_usage')
    def test_builtin_disk_check(self, mock_disk):
        """Test built-in disk space check."""
        # Test healthy disk
        mock_disk.return_value = Mock(
            total=1000000000000,  # 1TB
            used=500000000000,    # 500GB
            free=500000000000     # 500GB
        )
        
        result = asyncio.run(self.monitor._check_disk_space())
        
        self.assertEqual(result["status"], "healthy")
        self.assertIn("Disk usage normal", result["message"])
        self.assertEqual(result["details"]["disk_percent"], 50.0)
        
        # Test degraded disk
        mock_disk.return_value = Mock(
            total=1000000000000,  # 1TB
            used=900000000000,    # 900GB
            free=100000000000     # 100GB
        )
        
        result = asyncio.run(self.monitor._check_disk_space())
        
        self.assertEqual(result["status"], "degraded")
        self.assertIn("High disk usage", result["message"])
        
        # Test unhealthy disk
        mock_disk.return_value = Mock(
            total=1000000000000,  # 1TB
            used=980000000000,    # 980GB
            free=20000000000      # 20GB
        )
        
        result = asyncio.run(self.monitor._check_disk_space())
        
        self.assertEqual(result["status"], "unhealthy")
        self.assertIn("Critical disk usage", result["message"])


class TestHealthMonitorAsync(unittest.IsolatedAsyncioTestCase):
    """Test async functionality of HealthMonitor."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.monitor = HealthMonitor(config={'status_update_interval': 0.1})
    
    async def test_execute_health_check_success(self):
        """Test executing successful health check."""
        def successful_check():
            return {"status": "healthy", "message": "All good"}
        
        check = HealthCheck(
            name="success_check",
            component_type=ComponentType.SERVICE,
            check_function=successful_check,
            timeout_seconds=5
        )
        
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.check_name, "success_check")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, "All good")
        self.assertIsNone(result.error)
        self.assertGreater(result.duration_ms, 0)
    
    async def test_execute_health_check_failure(self):
        """Test executing failed health check."""
        def failing_check():
            raise Exception("Check failed")
        
        check = HealthCheck(
            name="fail_check",
            component_type=ComponentType.SERVICE,
            check_function=failing_check,
            timeout_seconds=5,
            retries=1
        )
        
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.check_name, "fail_check")
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertIn("Check failed", result.error)
    
    async def test_execute_health_check_timeout(self):
        """Test executing health check with timeout."""
        async def slow_check():
            await asyncio.sleep(1)  # Longer than timeout
            return True
        
        check = HealthCheck(
            name="slow_check",
            component_type=ComponentType.SERVICE,
            check_function=slow_check,
            timeout_seconds=0.1,  # Very short timeout
            retries=0
        )
        
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.check_name, "slow_check")
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertIn("timed out", result.error)
    
    async def test_execute_health_check_retries(self):
        """Test health check with retries."""
        call_count = 0
        
        def flaky_check():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return True
        
        check = HealthCheck(
            name="flaky_check",
            component_type=ComponentType.SERVICE,
            check_function=flaky_check,
            timeout_seconds=5,
            retries=3
        )
        
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.check_name, "flaky_check")
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(call_count, 3)  # Should have retried
    
    async def test_execute_health_check_boolean_result(self):
        """Test health check returning boolean."""
        def boolean_check():
            return True
        
        check = HealthCheck(
            name="bool_check",
            component_type=ComponentType.SERVICE,
            check_function=boolean_check
        )
        
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, "Check passed")
        
        # Test false result
        def false_check():
            return False
        
        check.check_function = false_check
        result = await self.monitor._execute_health_check(check)
        
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertEqual(result.message, "Check failed")
    
    async def test_health_check_loop(self):
        """Test health check monitoring loop."""
        call_count = 0
        
        def counting_check():
            nonlocal call_count
            call_count += 1
            return {"status": "healthy", "message": f"Call {call_count}"}
        
        check = HealthCheck(
            name="loop_check",
            component_type=ComponentType.SERVICE,
            check_function=counting_check,
            interval_seconds=0.1
        )
        
        self.monitor.register_health_check(check)
        self.monitor.monitoring_enabled = True
        
        # Start the check loop
        task = asyncio.create_task(self.monitor._health_check_loop(check))
        
        # Let it run for a bit
        await asyncio.sleep(0.3)
        
        # Stop the loop
        self.monitor.monitoring_enabled = False
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have made multiple calls
        self.assertGreater(call_count, 1)
        
        # Should have stored results
        self.assertIn("loop_check", self.monitor.check_results)
        self.assertGreater(len(self.monitor.check_results["loop_check"]), 0)
    
    async def test_record_health_metrics(self):
        """Test recording health metrics."""
        # Mock metrics collector
        mock_collector = Mock()
        self.monitor.metrics_collector = mock_collector
        
        result = HealthResult(
            check_name="test_check",
            status=HealthStatus.HEALTHY,
            duration_ms=150.0
        )
        
        self.monitor._record_health_metrics(result)
        
        # Verify metrics were recorded
        mock_collector.record_histogram.assert_called_once()
        mock_collector.record_gauge.assert_called_once()
        mock_collector.record_counter.assert_called_once()
        
        # Check the calls
        histogram_call = mock_collector.record_histogram.call_args
        self.assertEqual(histogram_call[0][0], 'health_check_duration_ms')
        self.assertEqual(histogram_call[0][1], 150.0)
        
        gauge_call = mock_collector.record_gauge.call_args
        self.assertEqual(gauge_call[0][0], 'health_check_status')
        self.assertEqual(gauge_call[0][1], 1)  # Healthy = 1
    
    async def test_shutdown(self):
        """Test monitor shutdown."""
        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring_enabled)
        
        # Shutdown
        await self.monitor.shutdown()
        
        # Verify shutdown
        self.assertFalse(self.monitor.monitoring_enabled)


if __name__ == "__main__":
    unittest.main()
