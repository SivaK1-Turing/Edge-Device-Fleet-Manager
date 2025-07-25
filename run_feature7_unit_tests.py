#!/usr/bin/env python3
"""
Feature 7 Unit Test Runner

Runs unit tests for Feature 7 components without requiring pytest installation.
Uses Python's built-in unittest framework for maximum compatibility.
"""

import unittest
import asyncio
import sys
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import Feature 7 components
from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
from edge_device_fleet_manager.reports.generators.csv_generator import CSVReportGenerator
from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
from edge_device_fleet_manager.reports.alerts.alert_rules import AlertRule, AlertRuleEngine


class TestReportEngine(unittest.TestCase):
    """Unit tests for ReportEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.report_engine = ReportEngine()
        self.sample_data = [
            {'id': 'device-1', 'name': 'Test Device 1', 'status': 'online', 'health_score': 95.5},
            {'id': 'device-2', 'name': 'Test Device 2', 'status': 'offline', 'health_score': 0.0}
        ]
    
    def test_engine_initialization(self):
        """Test report engine initialization."""
        self.assertIsNotNone(self.report_engine)
        self.assertTrue(hasattr(self.report_engine, 'generators'))
        self.assertTrue(hasattr(self.report_engine, 'templates'))
        self.assertTrue(hasattr(self.report_engine, 'scheduled_reports'))
        self.assertTrue(hasattr(self.report_engine, 'report_history'))
        
        # Check generators are initialized
        self.assertIn('json', self.report_engine.generators)
        self.assertIn('csv', self.report_engine.generators)
        self.assertIn('html', self.report_engine.generators)
        self.assertIn('pdf', self.report_engine.generators)
    
    def test_generate_output_path(self):
        """Test output path generation."""
        path = self.report_engine._generate_output_path('device_status', 'json', 'test-id')
        
        self.assertIsInstance(path, Path)
        self.assertEqual(path.suffix, '.json')
        self.assertIn('device_status', path.name)
        self.assertIn('test-id'[:8], path.name)
    
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
    
    def test_get_report_history(self):
        """Test getting report history."""
        # Add test reports
        for i in range(3):
            metadata = {
                'report_id': f'test-{i}',
                'report_type': 'test',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            self.report_engine._add_to_history(metadata)
        
        history = self.report_engine.get_report_history(limit=2)
        
        self.assertEqual(len(history), 2)
        self.assertTrue(all('report_id' in report for report in history))
    
    def test_get_report_statistics_empty(self):
        """Test getting statistics with no reports."""
        stats = self.report_engine.get_report_statistics()
        
        self.assertEqual(stats['total_reports'], 0)
        self.assertEqual(stats['successful_reports'], 0)
        self.assertEqual(stats['failed_reports'], 0)
        self.assertEqual(stats['success_rate'], 0.0)
        self.assertEqual(stats['formats'], {})
        self.assertEqual(stats['types'], {})
    
    def test_get_report_statistics_with_data(self):
        """Test getting statistics with report data."""
        # Add test reports
        successful_report = {
            'report_id': 'success-1',
            'report_type': 'device_status',
            'output_format': 'json',
            'success': True,
            'duration_seconds': 1.5,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        failed_report = {
            'report_id': 'failed-1',
            'report_type': 'alert_summary',
            'output_format': 'pdf',
            'success': False,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.report_engine._add_to_history(successful_report)
        self.report_engine._add_to_history(failed_report)
        
        stats = self.report_engine.get_report_statistics()
        
        self.assertEqual(stats['total_reports'], 2)
        self.assertEqual(stats['successful_reports'], 1)
        self.assertEqual(stats['failed_reports'], 1)
        self.assertEqual(stats['success_rate'], 50.0)
        self.assertEqual(stats['formats']['json'], 1)
        self.assertEqual(stats['formats']['pdf'], 1)
        self.assertEqual(stats['types']['device_status'], 1)
        self.assertEqual(stats['types']['alert_summary'], 1)
        self.assertEqual(stats['average_duration'], 1.5)


class TestReportEngineAsync(unittest.IsolatedAsyncioTestCase):
    """Async unit tests for ReportEngine."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.report_engine = ReportEngine()
        self.sample_data = [
            {'id': 'device-1', 'name': 'Test Device 1', 'status': 'online'},
            {'id': 'device-2', 'name': 'Test Device 2', 'status': 'offline'}
        ]
    
    async def test_generate_report_with_dict_data(self):
        """Test report generation with dictionary data source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_report.json'
            
            result = await self.report_engine.generate_report(
                report_type='device_status',
                data_source=self.sample_data,
                output_format='json',
                output_path=str(output_path)
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'device_status')
            self.assertEqual(result['output_format'], 'json')
            self.assertEqual(result['record_count'], 2)
            self.assertTrue(Path(result['output_path']).exists())
    
    async def test_load_report_data_dict(self):
        """Test loading data from dictionary source."""
        data = await self.report_engine._load_report_data(self.sample_data, 'device_status')
        self.assertEqual(data, self.sample_data)
    
    async def test_load_report_data_file(self):
        """Test loading data from file source."""
        test_data = {'test': 'data'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            data = await self.report_engine._load_report_data(f'file:{temp_path}', 'test')
            self.assertEqual(data, test_data)
        finally:
            Path(temp_path).unlink()


class TestAlertManager(unittest.TestCase):
    """Unit tests for AlertManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.alert_manager = AlertManager()
    
    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        self.assertIsNotNone(self.alert_manager)
        self.assertTrue(hasattr(self.alert_manager, 'active_alerts'))
        self.assertTrue(hasattr(self.alert_manager, 'alert_rules'))
        self.assertTrue(hasattr(self.alert_manager, 'alert_history'))
        self.assertTrue(hasattr(self.alert_manager, 'suppression_rules'))
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
        
        # Check severity distribution
        for severity in AlertSeverity:
            self.assertEqual(stats['severity_distribution'][severity.value], 0)
        
        # Check status distribution
        for status in AlertStatus:
            self.assertEqual(stats['status_distribution'][status.value], 0)
    
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
    
    def test_add_to_history_limit(self):
        """Test history size limit."""
        # Set small limit for testing
        self.alert_manager.max_history_entries = 5
        
        # Add more alerts than limit
        for i in range(10):
            alert_data = {
                'id': f'alert-{i}',
                'title': f'Alert {i}',
                'first_occurred': datetime.now(timezone.utc).isoformat()
            }
            self.alert_manager._add_to_history(alert_data)
        
        # Should only keep the limit
        self.assertLessEqual(len(self.alert_manager.alert_history), self.alert_manager.max_history_entries)


class TestAlertManagerAsync(unittest.IsolatedAsyncioTestCase):
    """Async unit tests for AlertManager."""
    
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.alert_manager = AlertManager()
        await self.alert_manager.initialize()
    
    async def test_create_alert_basic(self):
        """Test basic alert creation."""
        alert_id = await self.alert_manager.create_alert(
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.MEDIUM,
            alert_type="test"
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIn(alert_id, self.alert_manager.active_alerts)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert['title'], "Test Alert")
        self.assertEqual(alert['description'], "This is a test alert")
        self.assertEqual(alert['severity'], AlertSeverity.MEDIUM)
        self.assertEqual(alert['alert_type'], "test")
        self.assertEqual(alert['status'], AlertStatus.ACTIVE)
        self.assertEqual(alert['occurrence_count'], 1)
    
    async def test_create_alert_with_device(self):
        """Test alert creation with device ID."""
        alert_id = await self.alert_manager.create_alert(
            title="Device Alert",
            description="Device-specific alert",
            severity=AlertSeverity.HIGH,
            alert_type="device",
            device_id="device-123"
        )
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert['device_id'], "device-123")
    
    async def test_acknowledge_alert(self):
        """Test alert acknowledgment."""
        # Create alert
        alert_id = await self.alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for acknowledgment",
            severity=AlertSeverity.MEDIUM
        )
        
        # Acknowledge alert
        result = await self.alert_manager.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by="test_user",
            notes="Test acknowledgment"
        )
        
        self.assertTrue(result)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertEqual(alert['status'], AlertStatus.ACKNOWLEDGED)
        self.assertEqual(alert['acknowledged_by'], "test_user")
        self.assertIsNotNone(alert['acknowledged_at'])
        self.assertEqual(alert['metadata']['acknowledgment_notes'], "Test acknowledgment")
    
    async def test_acknowledge_nonexistent_alert(self):
        """Test acknowledging non-existent alert."""
        result = await self.alert_manager.acknowledge_alert(
            alert_id="nonexistent",
            acknowledged_by="test_user"
        )
        
        self.assertFalse(result)
    
    async def test_resolve_alert(self):
        """Test alert resolution."""
        # Create alert
        alert_id = await self.alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for resolution",
            severity=AlertSeverity.HIGH
        )
        
        # Resolve alert
        result = await self.alert_manager.resolve_alert(
            alert_id=alert_id,
            resolved_by="test_user",
            resolution_notes="Test resolution"
        )
        
        self.assertTrue(result)
        self.assertNotIn(alert_id, self.alert_manager.active_alerts)
        
        # Check in history
        self.assertIn(alert_id, self.alert_manager.alert_history)
        resolved_alert = self.alert_manager.alert_history[alert_id]
        self.assertEqual(resolved_alert['status'], AlertStatus.RESOLVED)
        self.assertEqual(resolved_alert['resolved_by'], "test_user")
        self.assertIsNotNone(resolved_alert['resolved_at'])
        self.assertEqual(resolved_alert['metadata']['resolution_notes'], "Test resolution")
    
    async def test_escalate_alert(self):
        """Test alert escalation."""
        # Create alert
        alert_id = await self.alert_manager.create_alert(
            title="Test Alert",
            description="Test alert for escalation",
            severity=AlertSeverity.LOW
        )
        
        # Escalate alert
        result = await self.alert_manager.escalate_alert(
            alert_id=alert_id,
            escalation_reason="timeout"
        )
        
        self.assertTrue(result)
        
        alert = self.alert_manager.active_alerts[alert_id]
        self.assertTrue(alert['escalated'])
        self.assertEqual(alert['escalation_level'], 1)
        self.assertEqual(alert['severity'], AlertSeverity.MEDIUM)  # Should be escalated from LOW
        self.assertEqual(alert['metadata']['escalation_reason'], "timeout")


class TestJSONGenerator(unittest.IsolatedAsyncioTestCase):
    """Test JSON report generator."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.generator = JSONReportGenerator()
        self.sample_data = [
            {'id': '1', 'name': 'Device 1', 'status': 'online'},
            {'id': '2', 'name': 'Device 2', 'status': 'offline'}
        ]
    
    async def test_generate_json_report(self):
        """Test JSON report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test.json'
            
            result = await self.generator.generate(
                report_type='device_status',
                data=self.sample_data,
                output_path=str(output_path)
            )
            
            self.assertTrue(result['success'])
            self.assertTrue(output_path.exists())
            
            # Verify content
            with open(output_path) as f:
                report_data = json.load(f)
            
            self.assertIn('metadata', report_data)
            self.assertIn('data', report_data)
            self.assertEqual(len(report_data['data']), 2)


def run_unit_tests():
    """Run all unit tests."""
    print("🧪 Running Feature 7 Unit Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestReportEngine,
        TestReportEngineAsync,
        TestAlertManager,
        TestAlertManagerAsync,
        TestJSONGenerator
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
    
    if errors > 0:
        print(f"❌ {errors} errors:")
        for test, traceback in result.errors:
            print(f"   - {test}")
    
    if passed == total_tests:
        print("🎉 All unit tests passed!")
        print("\n✅ Components tested:")
        print("   - Report Engine (sync and async)")
        print("   - Alert Manager (sync and async)")
        print("   - JSON Generator")
        print("   - Core functionality and edge cases")
    
    return passed == total_tests


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)
