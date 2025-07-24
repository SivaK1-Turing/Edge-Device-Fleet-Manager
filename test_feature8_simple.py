#!/usr/bin/env python3
"""
Feature 8 Simple Test Suite

Basic validation tests for CI/CD, Packaging & Observability components.
Tests core functionality without complex integrations.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all Feature 8 components can be imported."""
    print("📦 Testing Feature 8 imports...")
    
    try:
        # Test observability imports
        from edge_device_fleet_manager.observability.metrics.collector import MetricsCollector
        from edge_device_fleet_manager.observability.monitoring.health_monitor import HealthMonitor
        print("  ✅ Observability components imported")
        
        # Test CI/CD imports
        from edge_device_fleet_manager.cicd.pipeline.pipeline_manager import PipelineManager
        print("  ✅ CI/CD components imported")
        
        # Test packaging imports
        from edge_device_fleet_manager.packaging.builders.wheel_builder import WheelBuilder
        print("  ✅ Packaging components imported")
        
        # Test main module imports
        import edge_device_fleet_manager.observability
        import edge_device_fleet_manager.cicd
        import edge_device_fleet_manager.packaging
        print("  ✅ Main modules imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_metrics_collector_basic():
    """Test basic metrics collector functionality."""
    print("📊 Testing Metrics Collector...")
    
    try:
        from edge_device_fleet_manager.observability.metrics.collector import MetricsCollector
        
        # Create collector
        collector = MetricsCollector()
        
        # Test metric recording
        collector.record_counter('test_requests', 10)
        collector.record_gauge('test_temperature', 25.5)
        collector.record_histogram('test_response_time', 150)
        
        # Test metric retrieval
        requests = collector.get_metric_value('test_requests')
        temperature = collector.get_metric_value('test_temperature')
        
        assert requests == 10, f"Expected 10 requests, got {requests}"
        assert temperature == 25.5, f"Expected 25.5 temperature, got {temperature}"
        
        # Test metrics summary
        summary = collector.get_metrics_summary()
        assert summary['counters'] >= 1, "Should have counters"
        assert summary['gauges'] >= 1, "Should have gauges"
        
        print("  ✅ Metrics Collector working")
        return True
        
    except Exception as e:
        print(f"  ❌ Metrics Collector failed: {e}")
        return False

async def test_health_monitor_basic():
    """Test basic health monitor functionality."""
    print("🏥 Testing Health Monitor...")
    
    try:
        from edge_device_fleet_manager.observability.monitoring.health_monitor import (
            HealthMonitor, HealthCheck, ComponentType
        )
        
        # Create health monitor
        monitor = HealthMonitor()
        
        # Create simple health check
        def simple_check():
            return True
        
        health_check = HealthCheck(
            name='simple_test',
            component_type=ComponentType.SERVICE,
            check_function=simple_check
        )
        
        # Register check
        monitor.register_health_check(health_check)
        
        # Test status
        status = monitor.get_health_status()
        assert 'overall_status' in status, "Should have overall status"
        assert status['total_checks'] >= 1, "Should have at least 1 check"
        
        print("  ✅ Health Monitor working")
        return True
        
    except Exception as e:
        print(f"  ❌ Health Monitor failed: {e}")
        return False

def test_pipeline_manager_basic():
    """Test basic pipeline manager functionality."""
    print("🔄 Testing Pipeline Manager...")
    
    try:
        from edge_device_fleet_manager.cicd.pipeline.pipeline_manager import PipelineManager
        
        # Create pipeline manager
        manager = PipelineManager()
        
        # Test simple pipeline creation
        def simple_executor(execution, stage):
            return {'output': 'Success'}
        
        pipeline_config = {
            'name': 'simple_test_pipeline',
            'stages': [
                {
                    'name': 'test_stage',
                    'executor': simple_executor
                }
            ]
        }
        
        pipeline = manager.create_pipeline(pipeline_config)
        assert pipeline.name == 'simple_test_pipeline', "Pipeline name should match"
        assert len(pipeline.stages) == 1, "Should have 1 stage"
        
        # Test pipeline validation
        errors = pipeline.validate()
        assert len(errors) == 0, f"Pipeline should be valid, got errors: {errors}"
        
        # Test statistics
        stats = manager.get_pipeline_statistics()
        assert stats['total_pipelines'] >= 1, "Should have at least 1 pipeline"
        
        print("  ✅ Pipeline Manager working")
        return True
        
    except Exception as e:
        print(f"  ❌ Pipeline Manager failed: {e}")
        return False

def test_wheel_builder_basic():
    """Test basic wheel builder functionality."""
    print("📦 Testing Wheel Builder...")
    
    try:
        from edge_device_fleet_manager.packaging.builders.wheel_builder import WheelBuilder
        
        # Create wheel builder with test config
        config = {
            'package_name': 'test-package',
            'version': '1.0.0',
            'description': 'Test package',
            'install_requires': ['requests']
        }
        
        builder = WheelBuilder(config)
        
        # Test build info
        build_info = builder.get_build_info()
        assert build_info['package_name'] == 'test-package', "Package name should match"
        assert build_info['version'] == '1.0.0', "Version should match"
        assert 'requests' in build_info['dependencies'], "Should have requests dependency"
        
        print("  ✅ Wheel Builder working")
        return True
        
    except Exception as e:
        print(f"  ❌ Wheel Builder failed: {e}")
        return False

def test_observability_convenience():
    """Test observability convenience functions."""
    print("🔍 Testing Observability convenience functions...")
    
    try:
        from edge_device_fleet_manager.observability import (
            setup_observability, get_metrics_collector, get_health_monitor
        )
        
        # Test setup
        components = setup_observability()
        assert 'metrics_collector' in components, "Should have metrics collector"
        assert 'health_monitor' in components, "Should have health monitor"
        
        # Test global getters
        collector = get_metrics_collector()
        monitor = get_health_monitor()
        
        assert collector is not None, "Should get metrics collector"
        assert monitor is not None, "Should get health monitor"
        
        print("  ✅ Observability convenience functions working")
        return True
        
    except Exception as e:
        print(f"  ❌ Observability convenience functions failed: {e}")
        return False

def test_cicd_convenience():
    """Test CI/CD convenience functions."""
    print("🚀 Testing CI/CD convenience functions...")
    
    try:
        from edge_device_fleet_manager.cicd import create_pipeline
        
        # Test pipeline creation
        pipeline_config = {
            'name': 'convenience_test_pipeline',
            'stages': [
                {
                    'name': 'test',
                    'executor': lambda execution, stage: {'output': 'Test passed'}
                }
            ]
        }
        
        pipeline = create_pipeline(pipeline_config)
        assert pipeline.name == 'convenience_test_pipeline', "Pipeline name should match"
        
        print("  ✅ CI/CD convenience functions working")
        return True
        
    except Exception as e:
        print(f"  ❌ CI/CD convenience functions failed: {e}")
        return False

def test_packaging_convenience():
    """Test packaging convenience functions."""
    print("📦 Testing Packaging convenience functions...")
    
    try:
        from edge_device_fleet_manager.packaging import get_package_manager, get_version_controller
        
        # Test global getters
        package_manager = get_package_manager()
        version_controller = get_version_controller()
        
        assert package_manager is not None, "Should get package manager"
        assert version_controller is not None, "Should get version controller"
        
        print("  ✅ Packaging convenience functions working")
        return True
        
    except Exception as e:
        print(f"  ❌ Packaging convenience functions failed: {e}")
        return False

async def main():
    """Main test runner."""
    print("🚀 Starting Feature 8 Simple Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports, False),
        ("Metrics Collector", test_metrics_collector_basic, False),
        ("Health Monitor", test_health_monitor_basic, True),
        ("Pipeline Manager", test_pipeline_manager_basic, False),
        ("Wheel Builder", test_wheel_builder_basic, False),
        ("Observability Convenience", test_observability_convenience, False),
        ("CI/CD Convenience", test_cicd_convenience, False),
        ("Packaging Convenience", test_packaging_convenience, False)
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
        print("🎉 All Feature 8 simple tests passed!")
        print("\n✅ Core functionality verified:")
        print("   - Metrics collection and recording")
        print("   - Health monitoring and checks")
        print("   - CI/CD pipeline management")
        print("   - Package building configuration")
        print("   - Observability system setup")
        print("   - CI/CD convenience functions")
        print("   - Packaging convenience functions")
        print("\n💡 Feature 8 basic functionality is working!")
        print("   Run 'python test_feature8_comprehensive.py' for full testing")
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
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
