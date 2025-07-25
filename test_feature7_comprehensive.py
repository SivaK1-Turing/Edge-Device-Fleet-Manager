#!/usr/bin/env python3
"""
Comprehensive Test Suite for Feature 7: Report Generation & Alert System

Tests all components of the report generation and alert system including:
- Report engine and generators
- Alert manager and rules
- Notification service
- Audit retention
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.reports import (
    ReportEngine, AlertManager, NotificationService, AuditRetentionManager,
    PDFReportGenerator, HTMLReportGenerator, CSVReportGenerator, JSONReportGenerator,
    AlertRule, AlertRuleEngine, AlertSeverity, AlertStatus,
    EmailNotifier, WebhookNotifier
)
from edge_device_fleet_manager.reports.alerts.alert_rules import RuleCondition, RuleAction, RuleConditionType, RuleActionType
from edge_device_fleet_manager.reports.core.audit_retention import RetentionPolicy, ArchiveFormat


class Feature7TestSuite:
    """Comprehensive test suite for Feature 7."""
    
    def __init__(self):
        """Initialize test suite."""
        self.temp_dir = None
        self.test_results = []
        
    async def run_all_tests(self):
        """Run all Feature 7 tests."""
        print("🚀 Starting Comprehensive Feature 7 Test Suite")
        print("=" * 60)
        
        # Create temporary directory for test outputs
        self.temp_dir = Path(tempfile.mkdtemp(prefix="feature7_test_"))
        print(f"📁 Test directory: {self.temp_dir}")
        
        try:
            # Test categories
            test_categories = [
                ("Report Generators", self.test_report_generators),
                ("Report Engine", self.test_report_engine),
                ("Alert System", self.test_alert_system),
                ("Alert Rules", self.test_alert_rules),
                ("Notification Service", self.test_notification_service),
                ("Audit Retention", self.test_audit_retention),
                ("Integration Tests", self.test_integration)
            ]
            
            for category_name, test_method in test_categories:
                print(f"\n📋 {category_name}")
                try:
                    await test_method()
                    print(f"✅ {category_name} PASSED")
                except Exception as e:
                    print(f"❌ {category_name} FAILED: {e}")
                    self.test_results.append(f"FAILED: {category_name} - {e}")
            
            # Print summary
            self.print_test_summary()
            
        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
    
    async def test_report_generators(self):
        """Test all report generators."""
        # Sample data for testing
        sample_data = [
            {
                'id': '1',
                'name': 'Device 1',
                'status': 'online',
                'health_score': 95.5,
                'last_seen': datetime.now(timezone.utc).isoformat()
            },
            {
                'id': '2',
                'name': 'Device 2',
                'status': 'offline',
                'health_score': 0.0,
                'last_seen': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            }
        ]
        
        # Test PDF Generator
        pdf_gen = PDFReportGenerator()
        pdf_result = await pdf_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(self.temp_dir / 'test_report.pdf')
        )
        assert pdf_result['success'], f"PDF generation failed: {pdf_result.get('error')}"
        print("  ✅ PDF generator working")
        
        # Test HTML Generator
        html_gen = HTMLReportGenerator()
        html_result = await html_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(self.temp_dir / 'test_report.html')
        )
        assert html_result['success'], f"HTML generation failed: {html_result.get('error')}"
        print("  ✅ HTML generator working")
        
        # Test CSV Generator
        csv_gen = CSVReportGenerator()
        csv_result = await csv_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(self.temp_dir / 'test_report.csv')
        )
        assert csv_result['success'], f"CSV generation failed: {csv_result.get('error')}"
        print("  ✅ CSV generator working")
        
        # Test JSON Generator
        json_gen = JSONReportGenerator()
        json_result = await json_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(self.temp_dir / 'test_report.json')
        )
        assert json_result['success'], f"JSON generation failed: {json_result.get('error')}"
        print("  ✅ JSON generator working")
    
    async def test_report_engine(self):
        """Test report engine functionality."""
        engine = ReportEngine()
        
        # Test with sample data
        sample_data = {
            'devices': [
                {'id': '1', 'name': 'Test Device', 'status': 'online'}
            ]
        }
        
        # Test report generation
        result = await engine.generate_report(
            report_type='device_status',
            data_source=sample_data,
            output_format='json',
            output_path=str(self.temp_dir / 'engine_test.json')
        )
        
        assert result['success'], f"Report engine failed: {result.get('error')}"
        assert result['record_count'] == 1
        print("  ✅ Report engine working")
        
        # Test statistics
        stats = engine.get_report_statistics()
        assert stats['total_reports'] >= 1
        print("  ✅ Report statistics working")
    
    async def test_alert_system(self):
        """Test alert management system."""
        alert_manager = AlertManager()
        await alert_manager.initialize()
        
        # Test alert creation
        alert_id = await alert_manager.create_alert(
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.HIGH,
            alert_type="test",
            device_id="device-123"
        )
        
        assert alert_id is not None
        print("  ✅ Alert creation working")
        
        # Test alert acknowledgment
        ack_result = await alert_manager.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by="test_user",
            notes="Test acknowledgment"
        )
        
        assert ack_result is True
        print("  ✅ Alert acknowledgment working")
        
        # Test alert resolution
        resolve_result = await alert_manager.resolve_alert(
            alert_id=alert_id,
            resolved_by="test_user",
            resolution_notes="Test resolution"
        )
        
        assert resolve_result is True
        print("  ✅ Alert resolution working")
        
        # Test statistics
        stats = alert_manager.get_alert_statistics()
        assert isinstance(stats, dict)
        print("  ✅ Alert statistics working")
    
    async def test_alert_rules(self):
        """Test alert rules system."""
        rule_engine = AlertRuleEngine()
        
        # Create test rule
        condition = RuleCondition(
            field='severity',
            condition_type=RuleConditionType.EQUALS,
            value=AlertSeverity.CRITICAL
        )
        
        action = RuleAction(
            action_type=RuleActionType.ESCALATE,
            parameters={'escalation_level': 1}
        )
        
        rule = AlertRule(
            name="Critical Alert Escalation",
            description="Escalate critical alerts",
            conditions=[condition],
            actions=[action]
        )
        
        # Add rule to engine
        rule_id = rule_engine.add_rule(rule)
        assert rule_id is not None
        print("  ✅ Alert rule creation working")
        
        # Test rule evaluation
        test_alert = {
            'id': 'test-alert',
            'severity': AlertSeverity.CRITICAL,
            'title': 'Critical Test Alert'
        }
        
        matches = await rule_engine.evaluate_rule(rule, test_alert)
        assert matches is True
        print("  ✅ Alert rule evaluation working")
        
        # Test rule processing
        results = await rule_engine.process_alert(test_alert)
        assert len(results) >= 1
        print("  ✅ Alert rule processing working")
        
        # Test statistics
        stats = rule_engine.get_rule_statistics()
        assert stats['total_rules'] >= 1
        print("  ✅ Alert rule statistics working")
    
    async def test_notification_service(self):
        """Test notification service."""
        notification_service = NotificationService()
        await notification_service.initialize()
        
        # Test alert notification
        test_alert = {
            'id': 'test-alert',
            'title': 'Test Alert',
            'description': 'This is a test alert',
            'severity': AlertSeverity.MEDIUM,
            'status': AlertStatus.ACTIVE
        }
        
        result = await notification_service.send_alert_notification(
            alert_data=test_alert,
            recipients=['test@example.com']
        )
        
        assert result['notification_id'] is not None
        print("  ✅ Alert notification working")
        
        # Test acknowledgment notification
        ack_result = await notification_service.send_acknowledgment_notification(
            alert_data=test_alert,
            acknowledged_by='test_user'
        )
        
        assert ack_result['notification_id'] is not None
        print("  ✅ Acknowledgment notification working")
        
        # Test statistics
        stats = notification_service.get_delivery_statistics()
        assert isinstance(stats, dict)
        print("  ✅ Notification statistics working")
    
    async def test_audit_retention(self):
        """Test audit retention manager."""
        retention_manager = AuditRetentionManager()
        await retention_manager.initialize()
        
        # Test policy configuration
        policy_config = {
            'retention_type': RetentionPolicy.SHORT_TERM,
            'archive_enabled': True,
            'archive_format': ArchiveFormat.COMPRESSED_JSON,
            'data_types': ['audit_logs']
        }
        
        policy_id = await retention_manager.configure_policy(
            policy_name="Test Retention Policy",
            policy_config=policy_config
        )
        
        assert policy_id is not None
        print("  ✅ Retention policy configuration working")
        
        # Test statistics
        stats = retention_manager.get_retention_statistics()
        assert stats['total_policies'] >= 1
        print("  ✅ Retention statistics working")
    
    async def test_integration(self):
        """Test integration between components."""
        # Test report generation with alert data
        alert_manager = AlertManager()
        await alert_manager.initialize()
        
        # Create test alerts
        for i in range(3):
            await alert_manager.create_alert(
                title=f"Integration Test Alert {i+1}",
                description=f"Test alert {i+1} for integration testing",
                severity=AlertSeverity.MEDIUM,
                alert_type="integration_test"
            )
        
        # Get alerts for reporting
        alerts = alert_manager.get_active_alerts()
        assert len(alerts) >= 3
        print("  ✅ Alert data retrieval working")
        
        # Generate report from alert data
        report_engine = ReportEngine()
        
        # Convert alerts to serializable format
        alert_data = []
        for alert in alerts:
            alert_dict = dict(alert)
            # Convert enum values to strings
            if 'severity' in alert_dict:
                alert_dict['severity'] = alert_dict['severity'].value
            if 'status' in alert_dict:
                alert_dict['status'] = alert_dict['status'].value
            alert_data.append(alert_dict)
        
        result = await report_engine.generate_report(
            report_type='alert_summary',
            data_source=alert_data,
            output_format='html',
            output_path=str(self.temp_dir / 'integration_report.html')
        )
        
        assert result['success'], f"Integration report failed: {result.get('error')}"
        print("  ✅ Alert-to-report integration working")
        
        # Test notification with report
        notification_service = NotificationService()
        await notification_service.initialize()
        
        notification_result = await notification_service.send_custom_notification(
            alert_data={'title': 'Integration Test Report Generated'},
            action_config={
                'channels': ['email'],
                'recipients': ['admin@example.com'],
                'template': 'report_generated'
            }
        )
        
        assert notification_result['notification_id'] is not None
        print("  ✅ Report-to-notification integration working")
    
    def print_test_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 Feature 7 Test Summary")
        print("=" * 60)
        
        if not self.test_results:
            print("🎉 ALL FEATURE 7 TESTS PASSED!")
            print("\n✅ Components tested successfully:")
            print("   - Report generators (PDF, HTML, CSV, JSON)")
            print("   - Report engine with data sources")
            print("   - Alert management system")
            print("   - Alert rules and evaluation")
            print("   - Notification service")
            print("   - Audit retention management")
            print("   - Component integration")
            
            print("\n💡 Feature 7 is ready for production use!")
            
        else:
            print(f"❌ {len(self.test_results)} test(s) failed:")
            for result in self.test_results:
                print(f"   - {result}")
        
        print("\n📁 Test outputs saved to:", self.temp_dir)


async def main():
    """Main test runner."""
    test_suite = Feature7TestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
