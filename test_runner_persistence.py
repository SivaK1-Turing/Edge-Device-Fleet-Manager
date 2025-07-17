#!/usr/bin/env python3
"""
Test Runner for Persistence Tests

Diagnoses and runs persistence tests with proper error handling.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'pytest',
        'sqlalchemy',
        'aiosqlite',
        'alembic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package} - MISSING")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All dependencies available")
    return True

def check_imports():
    """Check if persistence modules can be imported."""
    print("\n🔍 Checking persistence module imports...")
    
    try:
        from edge_device_fleet_manager.persistence.models.device import Device, DeviceStatus, DeviceType
        print("  ✅ Device model")
    except Exception as e:
        print(f"  ❌ Device model: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent, TelemetryType
        print("  ✅ Telemetry model")
    except Exception as e:
        print(f"  ❌ Telemetry model: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.persistence.repositories.device import DeviceRepository
        print("  ✅ Device repository")
    except Exception as e:
        print(f"  ❌ Device repository: {e}")
        return False
    
    try:
        from edge_device_fleet_manager.persistence.connection.manager import DatabaseManager
        print("  ✅ Database manager")
    except Exception as e:
        print(f"  ❌ Database manager: {e}")
        return False
    
    print("✅ All persistence modules can be imported")
    return True

def run_simple_model_test():
    """Run a simple model test to verify basic functionality."""
    print("\n🔍 Running simple model test...")
    
    try:
        import uuid
        from edge_device_fleet_manager.persistence.models.device import Device, DeviceStatus, DeviceType
        
        # Create a device
        device = Device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE,
            ip_address="192.168.1.100"
        )
        device.id = uuid.uuid4()  # Manually set ID for testing
        
        # Test basic properties
        assert device.name == "Test Device"
        assert device.device_type == DeviceType.SENSOR
        assert device.status == DeviceStatus.ONLINE
        assert device.is_online is True
        
        # Test validation
        try:
            device.health_score = 1.5  # Should fail
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
        
        print("  ✅ Device model test passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Simple model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_pytest_with_diagnostics():
    """Run pytest with proper diagnostics."""
    print("\n🔍 Running pytest with diagnostics...")
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("❌ pytest not available. Install with: pip install pytest")
        return False
    
    # Set up environment
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Run specific test files
    test_files = [
        "tests/unit/test_persistence_models.py",
        "tests/unit/test_persistence_repositories.py"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n📋 Running {test_file}...")
            
            # Run pytest programmatically
            try:
                exit_code = pytest.main([
                    test_file,
                    "-v",
                    "--tb=short",
                    "--no-header",
                    "--disable-warnings"
                ])
                
                if exit_code == 0:
                    print(f"  ✅ {test_file} passed")
                else:
                    print(f"  ❌ {test_file} failed (exit code: {exit_code})")
                    
            except Exception as e:
                print(f"  ❌ Error running {test_file}: {e}")
        else:
            print(f"  ⚠️  {test_file} not found")

def run_individual_test_functions():
    """Run individual test functions to isolate issues."""
    print("\n🔍 Running individual test functions...")
    
    try:
        # Import test modules directly
        sys.path.append(str(project_root / "tests" / "unit"))
        
        # Try to import and run specific test functions
        try:
            from test_persistence_models import TestDeviceModel
            
            # Create test instance
            test_instance = TestDeviceModel()
            
            # Run individual test methods
            test_methods = [
                'test_device_creation',
                'test_device_validation',
                'test_device_hybrid_properties'
            ]
            
            for method_name in test_methods:
                if hasattr(test_instance, method_name):
                    try:
                        method = getattr(test_instance, method_name)
                        method()
                        print(f"  ✅ {method_name}")
                    except Exception as e:
                        print(f"  ❌ {method_name}: {e}")
                else:
                    print(f"  ⚠️  {method_name} not found")
                    
        except ImportError as e:
            print(f"  ❌ Could not import test module: {e}")
            
    except Exception as e:
        print(f"  ❌ Error running individual tests: {e}")

def main():
    """Main test runner."""
    print("🚀 Persistence Test Runner")
    print("=" * 50)
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return False
    
    # Step 2: Check imports
    if not check_imports():
        print("\n❌ Import errors detected")
        return False
    
    # Step 3: Run simple test
    if not run_simple_model_test():
        print("\n❌ Basic functionality test failed")
        return False
    
    # Step 4: Run individual test functions
    run_individual_test_functions()
    
    # Step 5: Run pytest
    run_pytest_with_diagnostics()
    
    print("\n" + "=" * 50)
    print("🎯 Test runner complete")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
