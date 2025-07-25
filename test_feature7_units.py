#!/usr/bin/env python3
"""
Feature 7 Unit Tests - Standalone Runner

Runs unit tests for Feature 7 components without external dependencies.
Works with Python's built-in unittest framework.
"""

import unittest
import asyncio
import sys
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
    from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
    from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
    from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
    from edge_device_fleet_manager.reports.alerts.alert_rules import AlertRuleEngine
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Some components may not be available for testing")
    IMPORTS_AVAILABLE = False


class TestReportEngineBasic(unittest.TestCase):
    """Basic tests for ReportEngine that don't require full initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required imports not available")
        self.report_engine = ReportEngine()
    
    def test_engine_creation(self):
        """Test that report engine can be created."""
        self.assertIsNotNone(self.report_engine)
        self.assertTrue(hasattr(self.report_engine, 'generators'))
        self.assertTrue(hasattr(self.report_engine, 'report_history'))
    
    def test_generate_output_path(self):
        """Test output path generation."""
        path = self.report_engine._generate_output_path('device_status', 'json', 'test-id')
        
        self.assertIsInstance(path, Path)
        self.assertEqual(path.suffix, '.json')
        self.assertIn('device_status', path.name)
    
    def test_add_to_history(self):
        """Test adding report to history."""
        metadata = {
            'report_id': 'test-123',
            'report_type': 'test',
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.report_engine._add_to_history(metadata)
        
        self.assertIn('test-123', self.report_engine.report_history)
        self.assertEqual(self.report_engine.report_history['test-123'], metadata)
    
    def test_get_report_statistics_empty(self):
        """Test getting statistics with no reports."""
        stats = self.report_engine.get_report_statistics()
        
        self.assertEqual(stats['total_reports'], 0)
        self.assertEqual(stats['successful_reports'], 0)
        self.assertEqual(stats['failed_reports'], 0)
        self.assertEqual(stats['success_rate'], 0.0)


class TestAlertManagerBasic(unittest.TestCase):
    """Basic tests for AlertManager that don't require full initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required imports not available")
        self.alert_manager = AlertManager()
    
    def test_alert_manager_creation(self):
        """Test that alert manager can be created."""
        self.assertIsNotNone(self.alert_manager)
        self.assertTrue(hasattr(self.alert_manager, 'active_alerts'))
        self.assertTrue(hasattr(self.alert_manager, 'alert_rules'))
        self.assertTrue(hasattr(self.alert_manager, 'alert_history'))
        self.assertTrue(hasattr(self.alert_manager, 'rule_engine'))
        
        # Check initial state
        self.assertEqual(len(self.alert_manager.active_alerts), 0)
        self.assertEqual(len(self.alert_manager.alert_rules), 0)
        self.assertEqual(len(self.alert_manager.alert_history), 0)
        self.assertIsInstance(self.alert_manager.rule_engine, AlertRuleEngine)
    
    def test_get_active_alerts_empty(self):
        """Test getting active alerts when none exist."""
        alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 0)
    
    def test_get_alert_statistics_empty(self):
        """Test getting alert statistics when no alerts exist."""
        stats = self.alert_manager.get_alert_statistics()
        
        self.assertEqual(stats['active_alerts'], 0)
        self.assertEqual(stats['total_alerts_today'], 0)
        self.assertEqual(stats['escalated_alerts'], 0)
        self.assertEqual(stats['suppressed_alerts'], 0)
        self.assertEqual(stats['alert_rules'], 0)
    
    def test_add_to_history(self):
        """Test adding alert to history."""
        alert_data = {
            'id': 'test-alert',
            'title': 'Test Alert',
            'first_occurred': datetime.now(timezone.utc).isoformat()
        }
        
        self.alert_manager._add_to_history(alert_data)
        
        self.assertIn('test-alert', self.alert_manager.alert_history)
        self.assertEqual(self.alert_manager.alert_history['test-alert'], alert_data)


class TestJSONGeneratorBasic(unittest.TestCase):
    """Basic tests for JSON generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required imports not available")
        self.generator = JSONReportGenerator()
        self.sample_data = [
            {'id': '1', 'name': 'Device 1', 'status': 'online'},
            {'id': '2', 'name': 'Device 2', 'status': 'offline'}
        ]
    
    def test_generator_creation(self):
        """Test that JSON generator can be created."""
        self.assertIsNotNone(self.generator)
    
    def test_serialize_simple_data(self):
        """Test serializing simple data."""
        async def run_test():
            result = await self.generator._serialize_data(self.sample_data)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['id'], '1')
            self.assertEqual(result[1]['id'], '2')
        
        asyncio.run(run_test())
    
    def test_generate_summary(self):
        """Test generating data summary."""
        async def run_test():
            summary = await self.generator._generate_summary(self.sample_data, 'device_status')
            self.assertEqual(summary['data_type'], 'list')
            self.assertEqual(summary['record_count'], 2)
            self.assertFalse(summary['is_empty'])
        
        asyncio.run(run_test())


class TestAlertSeverityAndStatus(unittest.TestCase):
    """Test alert severity and status enums."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required imports not available")
    
    def test_alert_severity_values(self):
        """Test alert severity enum values."""
        self.assertEqual(AlertSeverity.LOW.value, "low")
        self.assertEqual(AlertSeverity.MEDIUM.value, "medium")
        self.assertEqual(AlertSeverity.HIGH.value, "high")
        self.assertEqual(AlertSeverity.CRITICAL.value, "critical")
    
    def test_alert_severity_priority(self):
        """Test alert severity priority ordering."""
        self.assertEqual(AlertSeverity.CRITICAL.priority, 0)
        self.assertEqual(AlertSeverity.HIGH.priority, 1)
        self.assertEqual(AlertSeverity.MEDIUM.priority, 2)
        self.assertEqual(AlertSeverity.LOW.priority, 3)
    
    def test_alert_severity_comparison(self):
        """Test alert severity comparison."""
        self.assertTrue(AlertSeverity.CRITICAL < AlertSeverity.HIGH)
        self.assertTrue(AlertSeverity.HIGH < AlertSeverity.MEDIUM)
        self.assertTrue(AlertSeverity.MEDIUM < AlertSeverity.LOW)
    
    def test_alert_status_values(self):
        """Test alert status enum values."""
        self.assertEqual(AlertStatus.ACTIVE.value, "active")
        self.assertEqual(AlertStatus.ACKNOWLEDGED.value, "acknowledged")
        self.assertEqual(AlertStatus.RESOLVED.value, "resolved")
        self.assertEqual(AlertStatus.SUPPRESSED.value, "suppressed")
        self.assertEqual(AlertStatus.EXPIRED.value, "expired")
    
    def test_alert_status_properties(self):
        """Test alert status properties."""
        self.assertTrue(AlertStatus.ACTIVE.is_active)
        self.assertTrue(AlertStatus.ACKNOWLEDGED.is_active)
        self.assertFalse(AlertStatus.RESOLVED.is_active)
        
        self.assertFalse(AlertStatus.ACTIVE.is_closed)
        self.assertTrue(AlertStatus.RESOLVED.is_closed)
        self.assertTrue(AlertStatus.EXPIRED.is_closed)


class TestAsyncComponents(unittest.IsolatedAsyncioTestCase):
    """Test async components with proper async test framework."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        if not IMPORTS_AVAILABLE:
            self.skipTest("Required imports not available")
    
    async def test_json_generator_async(self):
        """Test JSON generator async functionality."""
        generator = JSONReportGenerator()
        sample_data = [{'id': '1', 'name': 'Test'}]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test.json'
            
            result = await generator.generate(
                report_type='test',
                data=sample_data,
                output_path=str(output_path)
            )
            
            self.assertTrue(result['success'])
            self.assertTrue(output_path.exists())
    
    async def test_alert_manager_async_basic(self):
        """Test basic async alert manager functionality."""
        alert_manager = AlertManager()
        await alert_manager.initialize()
        
        # Test creating an alert
        alert_id = await alert_manager.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.MEDIUM
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIn(alert_id, alert_manager.active_alerts)
        
        # Test getting alerts
        alerts = alert_manager.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['title'], "Test Alert")


def run_unit_tests():
    """Run all unit tests."""
    print("🧪 Running Feature 7 Unit Tests (Standalone)")
    print("=" * 55)
    
    if not IMPORTS_AVAILABLE:
        print("❌ Cannot run tests - required imports not available")
        print("   Make sure Feature 7 components are properly installed")
        return False
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestReportEngineBasic,
        TestAlertManagerBasic,
        TestJSONGeneratorBasic,
        TestAlertSeverityAndStatus,
        TestAsyncComponents
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📊 Unit Test Results: {passed}/{total_tests} tests passed")
    
    if failures > 0:
        print(f"❌ {failures} failures:")
        for test, traceback in result.failures:
            print(f"   - {test}")
            print(f"     {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print(f"❌ {errors} errors:")
        for test, traceback in result.errors:
            print(f"   - {test}")
            print(f"     {traceback.split('Error:')[-1].strip()}")
    
    if passed == total_tests:
        print("🎉 All unit tests passed!")
        print("\n✅ Components tested:")
        print("   - Report Engine (basic functionality)")
        print("   - Alert Manager (basic functionality)")
        print("   - JSON Generator (async operations)")
        print("   - Alert Severity and Status enums")
        print("   - Async component integration")
        print("\n💡 For full testing, run the comprehensive test suite:")
        print("   python test_feature7_simple.py")
    else:
        print(f"\n❌ {failures + errors} test(s) failed")
        print("   Check the error messages above for details")
    
    return passed == total_tests


def main():
    """Main test runner."""
    try:
        success = run_unit_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
