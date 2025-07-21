#!/usr/bin/env python3
"""
Simple Test Suite for Feature 7: Report Generation & Alert System

Quick validation tests for core Feature 7 functionality.
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.reports import (
    ReportEngine, AlertManager, NotificationService,
    PDFReportGenerator, HTMLReportGenerator, CSVReportGenerator, JSONReportGenerator,
    AlertSeverity, AlertStatus
)


async def test_report_generators():
    """Test basic report generator functionality."""
    print("📋 Testing Report Generators")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="feature7_simple_"))
    
    try:
        # Sample data
        sample_data = [
            {'id': '1', 'name': 'Device A', 'status': 'online', 'health': 95},
            {'id': '2', 'name': 'Device B', 'status': 'offline', 'health': 0}
        ]
        
        # Test JSON Generator (most reliable)
        json_gen = JSONReportGenerator()
        json_result = await json_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(temp_dir / 'test.json')
        )
        
        assert json_result['success'], f"JSON generation failed: {json_result.get('error')}"
        print("  ✅ JSON generator working")
        
        # Test CSV Generator
        csv_gen = CSVReportGenerator()
        csv_result = await csv_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(temp_dir / 'test.csv')
        )
        
        assert csv_result['success'], f"CSV generation failed: {csv_result.get('error')}"
        print("  ✅ CSV generator working")
        
        # Test HTML Generator
        html_gen = HTMLReportGenerator()
        html_result = await html_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(temp_dir / 'test.html')
        )
        
        assert html_result['success'], f"HTML generation failed: {html_result.get('error')}"
        print("  ✅ HTML generator working")
        
        # Test PDF Generator (may fallback to text)
        pdf_gen = PDFReportGenerator()
        pdf_result = await pdf_gen.generate(
            report_type='device_status',
            data=sample_data,
            output_path=str(temp_dir / 'test.pdf')
        )
        
        assert pdf_result['success'], f"PDF generation failed: {pdf_result.get('error')}"
        print("  ✅ PDF generator working")
        
        return True
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def test_alert_system():
    """Test basic alert system functionality."""
    print("📋 Testing Alert System")
    
    # Initialize alert manager
    alert_manager = AlertManager()
    await alert_manager.initialize()
    
    # Test alert creation
    alert_id = await alert_manager.create_alert(
        title="Test Alert",
        description="Simple test alert",
        severity=AlertSeverity.MEDIUM,
        alert_type="test"
    )
    
    assert alert_id is not None, "Alert creation failed"
    print("  ✅ Alert creation working")
    
    # Test getting active alerts
    active_alerts = alert_manager.get_active_alerts()
    assert len(active_alerts) >= 1, "No active alerts found"
    print("  ✅ Alert retrieval working")
    
    # Test alert acknowledgment
    ack_result = await alert_manager.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by="test_user"
    )
    
    assert ack_result is True, "Alert acknowledgment failed"
    print("  ✅ Alert acknowledgment working")
    
    # Test alert resolution
    resolve_result = await alert_manager.resolve_alert(
        alert_id=alert_id,
        resolved_by="test_user"
    )
    
    assert resolve_result is True, "Alert resolution failed"
    print("  ✅ Alert resolution working")
    
    # Test statistics
    stats = alert_manager.get_alert_statistics()
    assert isinstance(stats, dict), "Statistics not returned as dict"
    print("  ✅ Alert statistics working")
    
    return True


async def test_notification_system():
    """Test basic notification system functionality."""
    print("📋 Testing Notification System")
    
    # Initialize notification service
    notification_service = NotificationService()
    await notification_service.initialize()
    
    # Test alert notification
    test_alert = {
        'id': 'test-alert-123',
        'title': 'Test Notification Alert',
        'description': 'Testing notification system',
        'severity': AlertSeverity.HIGH,
        'status': AlertStatus.ACTIVE,
        'first_occurred': datetime.now(timezone.utc).isoformat()
    }
    
    # Send notification (will be simulated)
    result = await notification_service.send_alert_notification(
        alert_data=test_alert,
        recipients=['test@example.com']
    )
    
    assert result['notification_id'] is not None, "Notification failed"
    print("  ✅ Alert notification working")
    
    # Test custom notification
    custom_result = await notification_service.send_custom_notification(
        alert_data=test_alert,
        action_config={
            'channels': ['email'],
            'recipients': ['admin@example.com'],
            'template': 'test_template'
        }
    )
    
    assert custom_result['notification_id'] is not None, "Custom notification failed"
    print("  ✅ Custom notification working")
    
    # Test statistics
    stats = notification_service.get_delivery_statistics()
    assert isinstance(stats, dict), "Statistics not returned as dict"
    print("  ✅ Notification statistics working")
    
    return True


async def test_report_engine():
    """Test basic report engine functionality."""
    print("📋 Testing Report Engine")
    
    # Initialize report engine
    engine = ReportEngine()
    
    # Test with sample data
    sample_data = [
        {
            'id': 'device-1',
            'name': 'Test Device 1',
            'status': 'online',
            'health_score': 98.5,
            'last_seen': datetime.now(timezone.utc).isoformat()
        },
        {
            'id': 'device-2',
            'name': 'Test Device 2',
            'status': 'maintenance',
            'health_score': 85.0,
            'last_seen': datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Create temporary file
    temp_dir = Path(tempfile.mkdtemp(prefix="feature7_engine_"))
    
    try:
        # Test report generation
        result = await engine.generate_report(
            report_type='device_status',
            data_source=sample_data,
            output_format='json',
            output_path=str(temp_dir / 'engine_test.json')
        )
        
        assert result['success'], f"Report generation failed: {result.get('error')}"
        assert result['record_count'] == 2, f"Expected 2 records, got {result['record_count']}"
        print("  ✅ Report generation working")
        
        # Test statistics
        stats = engine.get_report_statistics()
        assert stats['total_reports'] >= 1, "No reports in statistics"
        print("  ✅ Report statistics working")
        
        # Test history
        history = engine.get_report_history(limit=5)
        assert len(history) >= 1, "No reports in history"
        print("  ✅ Report history working")
        
        return True
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def test_integration():
    """Test basic integration between components."""
    print("📋 Testing Component Integration")
    
    # Create alert and generate report from it
    alert_manager = AlertManager()
    await alert_manager.initialize()
    
    # Create test alert
    alert_id = await alert_manager.create_alert(
        title="Integration Test Alert",
        description="Testing integration between alert and report systems",
        severity=AlertSeverity.HIGH,
        alert_type="integration_test"
    )
    
    # Get alerts for reporting
    alerts = alert_manager.get_active_alerts()
    assert len(alerts) >= 1, "No alerts available for integration test"
    print("  ✅ Alert data available for reporting")
    
    # Convert alerts to reportable format
    alert_data = []
    for alert in alerts:
        alert_dict = dict(alert)
        # Convert enum values to strings for JSON serialization
        if 'severity' in alert_dict and hasattr(alert_dict['severity'], 'value'):
            alert_dict['severity'] = alert_dict['severity'].value
        if 'status' in alert_dict and hasattr(alert_dict['status'], 'value'):
            alert_dict['status'] = alert_dict['status'].value
        alert_data.append(alert_dict)
    
    # Generate report from alert data
    engine = ReportEngine()
    temp_dir = Path(tempfile.mkdtemp(prefix="feature7_integration_"))
    
    try:
        result = await engine.generate_report(
            report_type='alert_summary',
            data_source=alert_data,
            output_format='json',
            output_path=str(temp_dir / 'integration_report.json')
        )
        
        assert result['success'], f"Integration report failed: {result.get('error')}"
        print("  ✅ Alert-to-report integration working")
        
        # Test notification about the report
        notification_service = NotificationService()
        await notification_service.initialize()
        
        notification_result = await notification_service.send_custom_notification(
            alert_data={'title': 'Report Generated', 'description': 'Integration test report'},
            action_config={
                'channels': ['email'],
                'recipients': ['admin@example.com']
            }
        )
        
        assert notification_result['notification_id'] is not None, "Integration notification failed"
        print("  ✅ Report-to-notification integration working")
        
        return True
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def main():
    """Main test runner."""
    print("🚀 Starting Simple Feature 7 Test Suite")
    print("=" * 50)
    
    tests = [
        ("Report Generators", test_report_generators),
        ("Alert System", test_alert_system),
        ("Notification System", test_notification_system),
        ("Report Engine", test_report_engine),
        ("Component Integration", test_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
            print(f"✅ {test_name} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}")
    
    total = passed + failed
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All simple Feature 7 tests passed!")
        print("\n💡 Core functionality verified:")
        print("   - Report generation in multiple formats")
        print("   - Alert creation, acknowledgment, and resolution")
        print("   - Notification delivery system")
        print("   - Report engine with data processing")
        print("   - Component integration")
        print("\n✅ Feature 7 is working correctly!")
    else:
        print(f"❌ {failed} test(s) failed - check implementation")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
