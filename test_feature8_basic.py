#!/usr/bin/env python3
"""
Feature 8 Basic Test - Import Validation

Tests that all Feature 8 components can be imported successfully.
This is the most basic test to verify the module structure is correct.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_observability_imports():
    """Test observability module imports."""
    print("🔍 Testing Observability imports...")
    
    success_count = 0
    total_tests = 0
    
    # Test metrics collector
    total_tests += 1
    try:
        from edge_device_fleet_manager.observability.metrics.collector import MetricsCollector
        print("  ✅ MetricsCollector import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ MetricsCollector import failed: {e}")
    
    # Test health monitor
    total_tests += 1
    try:
        from edge_device_fleet_manager.observability.monitoring.health_monitor import HealthMonitor
        print("  ✅ HealthMonitor import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ HealthMonitor import failed: {e}")
    
    # Test main observability module
    total_tests += 1
    try:
        import edge_device_fleet_manager.observability
        print("  ✅ Main observability module import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ Main observability module import failed: {e}")
    
    return success_count, total_tests

def test_cicd_imports():
    """Test CI/CD module imports."""
    print("🚀 Testing CI/CD imports...")
    
    success_count = 0
    total_tests = 0
    
    # Test pipeline manager
    total_tests += 1
    try:
        from edge_device_fleet_manager.cicd.pipeline.pipeline_manager import PipelineManager
        print("  ✅ PipelineManager import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ PipelineManager import failed: {e}")
    
    # Test main CI/CD module
    total_tests += 1
    try:
        import edge_device_fleet_manager.cicd
        print("  ✅ Main CI/CD module import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ Main CI/CD module import failed: {e}")
    
    return success_count, total_tests

def test_packaging_imports():
    """Test packaging module imports."""
    print("📦 Testing Packaging imports...")
    
    success_count = 0
    total_tests = 0
    
    # Test wheel builder
    total_tests += 1
    try:
        from edge_device_fleet_manager.packaging.builders.wheel_builder import WheelBuilder
        print("  ✅ WheelBuilder import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ WheelBuilder import failed: {e}")
    
    # Test main packaging module
    total_tests += 1
    try:
        import edge_device_fleet_manager.packaging
        print("  ✅ Main packaging module import successful")
        success_count += 1
    except Exception as e:
        print(f"  ❌ Main packaging module import failed: {e}")
    
    return success_count, total_tests

def test_basic_functionality():
    """Test very basic functionality without complex operations."""
    print("🔧 Testing Basic Functionality")
    print("=" * 35)
    
    success_count = 0
    total_tests = 0
    
    # Test metrics collector creation
    total_tests += 1
    try:
        from edge_device_fleet_manager.observability.metrics.collector import MetricsCollector
        collector = MetricsCollector()
        assert hasattr(collector, 'counters')
        assert hasattr(collector, 'gauges')
        print("  ✅ MetricsCollector creation working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ MetricsCollector creation failed: {e}")
    
    # Test health monitor creation
    total_tests += 1
    try:
        from edge_device_fleet_manager.observability.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        assert hasattr(monitor, 'health_checks')
        assert hasattr(monitor, 'check_results')
        print("  ✅ HealthMonitor creation working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ HealthMonitor creation failed: {e}")
    
    # Test pipeline manager creation
    total_tests += 1
    try:
        from edge_device_fleet_manager.cicd.pipeline.pipeline_manager import PipelineManager
        manager = PipelineManager()
        assert hasattr(manager, 'pipelines')
        assert hasattr(manager, 'executions')
        print("  ✅ PipelineManager creation working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ PipelineManager creation failed: {e}")
    
    # Test wheel builder creation
    total_tests += 1
    try:
        from edge_device_fleet_manager.packaging.builders.wheel_builder import WheelBuilder
        builder = WheelBuilder()
        assert hasattr(builder, 'config')
        assert hasattr(builder, 'build_id')
        print("  ✅ WheelBuilder creation working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ WheelBuilder creation failed: {e}")
    
    return success_count, total_tests

def test_convenience_functions():
    """Test convenience functions."""
    print("🎯 Testing Convenience Functions")
    print("=" * 35)
    
    success_count = 0
    total_tests = 0
    
    # Test observability convenience functions
    total_tests += 1
    try:
        from edge_device_fleet_manager.observability import get_metrics_collector, get_health_monitor
        collector = get_metrics_collector()
        monitor = get_health_monitor()
        assert collector is not None
        assert monitor is not None
        print("  ✅ Observability convenience functions working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ Observability convenience functions failed: {e}")
    
    # Test packaging convenience functions
    total_tests += 1
    try:
        from edge_device_fleet_manager.packaging import get_package_manager, get_version_controller
        package_manager = get_package_manager()
        version_controller = get_version_controller()
        assert package_manager is not None
        assert version_controller is not None
        print("  ✅ Packaging convenience functions working")
        success_count += 1
    except Exception as e:
        print(f"  ❌ Packaging convenience functions failed: {e}")
    
    return success_count, total_tests

def main():
    """Main test function."""
    print("🚀 Feature 8 Basic Validation Test")
    print("=" * 40)
    print("This test validates that Feature 8 components can be imported.")
    print("It does NOT test functionality - just module structure.\n")
    
    total_passed = 0
    total_tests = 0
    
    # Test imports
    obs_passed, obs_total = test_observability_imports()
    total_passed += obs_passed
    total_tests += obs_total
    
    print()
    cicd_passed, cicd_total = test_cicd_imports()
    total_passed += cicd_passed
    total_tests += cicd_total
    
    print()
    pkg_passed, pkg_total = test_packaging_imports()
    total_passed += pkg_passed
    total_tests += pkg_total
    
    print()
    func_passed, func_total = test_basic_functionality()
    total_passed += func_passed
    total_tests += func_total
    
    print()
    conv_passed, conv_total = test_convenience_functions()
    total_passed += conv_passed
    total_tests += conv_total
    
    # Summary
    print(f"\n📊 Import Test Results: {total_passed}/{total_tests} successful")
    
    if total_passed == total_tests:
        print("🎉 All Feature 8 imports working!")
        print("\n✅ Successfully imported:")
        print("   - MetricsCollector (metrics collection)")
        print("   - HealthMonitor (health monitoring)")
        print("   - PipelineManager (CI/CD pipelines)")
        print("   - WheelBuilder (package building)")
        print("   - Main modules (observability, cicd, packaging)")
        print("   - Convenience functions")
        print("\n💡 Feature 8 module structure is correct!")
        print("   You can now run more comprehensive tests:")
        print("   - python test_feature8_simple.py")
        print("   - python test_feature8_comprehensive.py")
        return True
    else:
        print(f"❌ {total_tests - total_passed} import(s) failed")
        print("\n🔧 Common fixes:")
        print("   - Ensure you're in the project root directory")
        print("   - Check that all __init__.py files exist")
        print("   - Verify no syntax errors in imported modules")
        print("   - Check for missing dependencies")
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
