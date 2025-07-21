#!/usr/bin/env python3
"""
Basic Feature 7 Test - Import Validation Only

Tests that all Feature 7 components can be imported successfully.
This is the most basic test to verify the module structure is correct.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test basic imports of Feature 7 components."""
    print("🔍 Testing Feature 7 Component Imports")
    print("=" * 45)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Core components
    total_tests += 1
    try:
        from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
        print("✅ ReportEngine import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ ReportEngine import failed: {e}")
    
    # Test 2: Alert manager
    total_tests += 1
    try:
        from edge_device_fleet_manager.reports.core.alert_manager import AlertManager
        print("✅ AlertManager import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ AlertManager import failed: {e}")
    
    # Test 3: JSON generator
    total_tests += 1
    try:
        from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
        print("✅ JSONReportGenerator import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ JSONReportGenerator import failed: {e}")
    
    # Test 4: Alert severity
    total_tests += 1
    try:
        from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
        print("✅ AlertSeverity/AlertStatus import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ AlertSeverity/AlertStatus import failed: {e}")
    
    # Test 5: Notification service
    total_tests += 1
    try:
        from edge_device_fleet_manager.reports.core.notification_service import NotificationService
        print("✅ NotificationService import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ NotificationService import failed: {e}")
    
    # Test 6: Main module import
    total_tests += 1
    try:
        import edge_device_fleet_manager.reports
        print("✅ Main reports module import successful")
        success_count += 1
    except Exception as e:
        print(f"❌ Main reports module import failed: {e}")
    
    # Summary
    print(f"\n📊 Import Test Results: {success_count}/{total_tests} successful")
    
    if success_count == total_tests:
        print("🎉 All Feature 7 imports working!")
        print("\n✅ Successfully imported:")
        print("   - ReportEngine (core report generation)")
        print("   - AlertManager (alert lifecycle management)")
        print("   - JSONReportGenerator (JSON report output)")
        print("   - AlertSeverity/AlertStatus (alert enums)")
        print("   - NotificationService (multi-channel notifications)")
        print("   - Main reports module")
        print("\n💡 Feature 7 module structure is correct!")
        print("   You can now run more comprehensive tests:")
        print("   - python test_feature7_minimal.py")
        print("   - python test_feature7_simple.py")
        return True
    else:
        print(f"❌ {total_tests - success_count} import(s) failed")
        print("\n🔧 Common fixes:")
        print("   - Ensure you're in the project root directory")
        print("   - Check that all __init__.py files exist")
        print("   - Verify no syntax errors in imported modules")
        return False


def test_basic_functionality():
    """Test very basic functionality without async."""
    print("\n🔧 Testing Basic Functionality")
    print("=" * 35)
    
    try:
        # Test enum values
        from edge_device_fleet_manager.reports.alerts.severity import AlertSeverity, AlertStatus
        
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertStatus.ACTIVE.value == "active"
        print("✅ Alert enums working correctly")
        
        # Test basic object creation
        from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
        from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator
        
        engine = ReportEngine()
        generator = JSONReportGenerator()
        print("✅ Object creation working")
        
        # Test basic properties
        assert hasattr(engine, 'generators')
        assert hasattr(engine, 'report_history')
        print("✅ Object properties correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Feature 7 Basic Validation Test")
    print("=" * 40)
    print("This test validates that Feature 7 components can be imported.")
    print("It does NOT test functionality - just module structure.\n")
    
    # Test imports
    import_success = test_basic_imports()
    
    if import_success:
        # Test basic functionality
        func_success = test_basic_functionality()
        
        if func_success:
            print("\n🎉 Feature 7 Basic Validation PASSED!")
            print("✅ All components can be imported and created")
            print("✅ Basic properties and enums work correctly")
            print("\n🚀 Next steps:")
            print("   - Run 'python test_feature7_minimal.py' for functionality tests")
            print("   - Run 'python test_feature7_simple.py' for comprehensive tests")
            return True
        else:
            print("\n❌ Basic functionality test failed")
            return False
    else:
        print("\n❌ Import tests failed - cannot proceed with functionality tests")
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        print(f"\nExiting with code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
