#!/usr/bin/env python3
"""
Minimal Feature 7 Test

Basic validation test for Feature 7 components with minimal dependencies.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all core components can be imported."""
    print("📦 Testing imports...")
    
    try:
        from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
        print("  ✅ ReportEngine imported")
    except Exception as e:
        print(f"  ❌ ReportEngine import failed: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
        print("  ✅ AlertManager imported")
    except Exception as e:
        print(f"  ❌ AlertManager import failed: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
        print("  ✅ JSONReportGenerator imported")
    except Exception as e:
        print(f"  ❌ JSONReportGenerator import failed: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
        print("  ✅ AlertSeverity and AlertStatus imported")
    except Exception as e:
        print(f"  ❌ AlertSeverity/AlertStatus import failed: {e}")
        return False
    
    return True


async def test_json_generator():
    """Test JSON report generator."""
    print("📋 Testing JSON Generator...")
    
    try:
        from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
        
        generator = JSONReportGenerator()
        sample_data = [
            {'id': '1', 'name': 'Device 1', 'status': 'online'},
            {'id': '2', 'name': 'Device 2', 'status': 'offline'}
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test.json'
            
            result = await generator.generate(
                report_type='device_status',
                data=sample_data,
                output_path=str(output_path)
            )
            
            if result['success'] and output_path.exists():
                print("  ✅ JSON generation working")
                return True
            else:
                print(f"  ❌ JSON generation failed: {result.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"  ❌ JSON generator test failed: {e}")
        return False


async def test_alert_manager():
    """Test alert manager basic functionality."""
    print("📋 Testing Alert Manager...")
    
    try:
        from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
        from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity
        
        alert_manager = AlertManager()
        await alert_manager.initialize()
        
        # Test alert creation
        alert_id = await alert_manager.create_alert(
            title="Test Alert",
            description="Minimal test alert",
            severity=AlertSeverity.MEDIUM,
            alert_type="test"
        )
        
        if alert_id and alert_id in alert_manager.active_alerts:
            print("  ✅ Alert creation working")
            
            # Test getting alerts
            alerts = alert_manager.get_active_alerts()
            if len(alerts) >= 1:
                print("  ✅ Alert retrieval working")
                return True
            else:
                print("  ❌ Alert retrieval failed")
                return False
        else:
            print("  ❌ Alert creation failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Alert manager test failed: {e}")
        return False


async def test_report_engine():
    """Test report engine basic functionality."""
    print("📋 Testing Report Engine...")
    
    try:
        from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
        
        engine = ReportEngine()
        sample_data = [
            {'id': '1', 'name': 'Device 1', 'status': 'online'},
            {'id': '2', 'name': 'Device 2', 'status': 'offline'}
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_report.json'
            
            result = await engine.generate_report(
                report_type='device_status',
                data_source=sample_data,
                output_format='json',
                output_path=str(output_path)
            )
            
            if result['success'] and output_path.exists():
                print("  ✅ Report generation working")
                
                # Test statistics
                stats = engine.get_report_statistics()
                if stats['total_reports'] >= 1:
                    print("  ✅ Report statistics working")
                    return True
                else:
                    print("  ❌ Report statistics failed")
                    return False
            else:
                print(f"  ❌ Report generation failed: {result.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"  ❌ Report engine test failed: {e}")
        return False


def test_severity_enums():
    """Test alert severity and status enums."""
    print("📋 Testing Alert Enums...")
    
    try:
        from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
        
        # Test severity values
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"
        print("  ✅ AlertSeverity values correct")
        
        # Test status values
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        print("  ✅ AlertStatus values correct")
        
        # Test severity comparison
        assert AlertSeverity.CRITICAL < AlertSeverity.HIGH
        assert AlertSeverity.HIGH < AlertSeverity.MEDIUM
        assert AlertSeverity.MEDIUM < AlertSeverity.LOW
        print("  ✅ AlertSeverity comparison working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Alert enums test failed: {e}")
        return False


async def main():
    """Main test runner."""
    print("🚀 Starting Minimal Feature 7 Test")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports, False),  # Sync test
        ("Alert Enums", test_severity_enums, False),  # Sync test
        ("JSON Generator", test_json_generator, True),  # Async test
        ("Alert Manager", test_alert_manager, True),  # Async test
        ("Report Engine", test_report_engine, True),  # Async test
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func, is_async in tests:
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} ERROR: {e}")
    
    total = passed + failed
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All minimal Feature 7 tests passed!")
        print("\n✅ Core components working:")
        print("   - Component imports successful")
        print("   - Alert severity/status enums")
        print("   - JSON report generation")
        print("   - Alert management lifecycle")
        print("   - Report engine integration")
        print("\n💡 Feature 7 basic functionality verified!")
        return True
    else:
        print(f"❌ {failed} test(s) failed")
        print("\n🔧 Troubleshooting tips:")
        print("   - Check that all __init__.py files exist")
        print("   - Verify Python path includes project root")
        print("   - Ensure no circular import issues")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
