#!/usr/bin/env python3
"""
Simple test runner for persistence tests that handles common issues.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def install_missing_dependencies():
    """Install missing dependencies."""
    print("📦 Installing missing dependencies...")
    
    dependencies = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0", 
        "pytest-cov>=4.0.0",
        "sqlalchemy[asyncio]>=2.0.0",
        "aiosqlite>=0.19.0",
        "alembic>=1.12.0"
    ]
    
    for dep in dependencies:
        try:
            print(f"  Installing {dep}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", dep
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  ✅ {dep}")
        except subprocess.CalledProcessError:
            print(f"  ❌ Failed to install {dep}")
            return False
    
    print("✅ All dependencies installed")
    return True

def run_simple_import_test():
    """Test if we can import the persistence modules."""
    print("🔍 Testing persistence module imports...")
    
    try:
        # Test basic imports
        from edge_device_fleet_manager.persistence.models.device import Device, DeviceStatus, DeviceType
        from edge_device_fleet_manager.persistence.models.telemetry import TelemetryEvent, TelemetryType
        from edge_device_fleet_manager.persistence.connection.config import DatabaseConfig
        print("  ✅ Basic imports successful")
        
        # Test model creation
        import uuid
        device = Device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE
        )
        device.id = uuid.uuid4()
        
        assert device.name == "Test Device"
        print("  ✅ Model creation successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import test failed: {e}")
        return False

def run_pytest_models():
    """Run model tests with pytest."""
    print("🧪 Running model tests...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = str(project_root)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/unit/test_persistence_models.py",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "-x"  # Stop on first failure
        ], capture_output=True, text=True, cwd=project_root)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Model tests passed")
            return True
        else:
            print(f"❌ Model tests failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False

def run_pytest_repositories():
    """Run repository tests with pytest."""
    print("🧪 Running repository tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/unit/test_persistence_repositories.py",
            "-v",
            "--tb=short", 
            "--disable-warnings",
            "-x"  # Stop on first failure
        ], capture_output=True, text=True, cwd=project_root)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Repository tests passed")
            return True
        else:
            print(f"❌ Repository tests failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False

def run_individual_test_classes():
    """Run individual test classes to isolate issues."""
    print("🔍 Running individual test classes...")
    
    test_classes = [
        "tests/unit/test_persistence_models.py::TestDeviceModel::test_device_creation",
        "tests/unit/test_persistence_models.py::TestDeviceModel::test_device_validation",
        "tests/unit/test_persistence_models.py::TestTelemetryEventModel::test_telemetry_event_creation"
    ]
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class}...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_class,
                "-v",
                "--tb=line",
                "--disable-warnings"
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print(f"  ✅ {test_class.split('::')[-1]} passed")
            else:
                print(f"  ❌ {test_class.split('::')[-1]} failed")
                print(f"     STDOUT: {result.stdout}")
                print(f"     STDERR: {result.stderr}")
                
        except Exception as e:
            print(f"  ❌ Error running {test_class}: {e}")

def main():
    """Main test runner."""
    print("🚀 Persistence Test Runner")
    print("=" * 50)
    
    # Check if pytest is available
    try:
        import pytest
        print("✅ pytest is available")
    except ImportError:
        print("❌ pytest not available, installing dependencies...")
        if not install_missing_dependencies():
            print("❌ Failed to install dependencies")
            return False
    
    # Test imports
    if not run_simple_import_test():
        print("❌ Import test failed - check your Python path and dependencies")
        return False
    
    # Run individual test classes first
    run_individual_test_classes()
    
    # Run full test suites
    print("\n" + "=" * 50)
    print("🧪 Running Full Test Suites")
    print("=" * 50)
    
    model_success = run_pytest_models()
    repo_success = run_pytest_repositories()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    print(f"Model Tests: {'✅ PASSED' if model_success else '❌ FAILED'}")
    print(f"Repository Tests: {'✅ PASSED' if repo_success else '❌ FAILED'}")
    
    if model_success and repo_success:
        print("\n🎉 All persistence tests passed!")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
