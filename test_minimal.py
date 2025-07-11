#!/usr/bin/env python3
"""
Minimal test script to verify the plugin error handling functionality.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"

async def test_plugin_error_handling():
    """Test the plugin error handling functionality."""
    print("🧪 Testing Plugin Error Handling...")
    
    try:
        from edge_device_fleet_manager.core.plugins import PluginLoader
        from edge_device_fleet_manager.core.config import PluginConfig
        
        # Create temporary directory for plugins
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir) / "plugins"
            plugins_dir.mkdir()
            
            # Create a valid plugin
            valid_plugin = '''
import click
from edge_device_fleet_manager.core.plugins import Plugin, PluginMetadata

class ValidPlugin(Plugin):
    metadata = PluginMetadata(name="valid", version="1.0.0")
    
    @click.command()
    def valid_command(self):
        click.echo("Valid plugin works!")
'''
            
            # Create a broken plugin with syntax error
            broken_plugin = '''
import click
from edge_device_fleet_manager.core.plugins import Plugin

class BrokenPlugin(Plugin):
    def __init__(self):
        super().__init__()
        raise SyntaxError("This plugin is intentionally broken")
    
    @click.command()
    def broken_command(self):
        click.echo("This should not work")
'''
            
            # Write plugins to files
            (plugins_dir / "valid_plugin.py").write_text(valid_plugin)
            (plugins_dir / "broken_plugin.py").write_text(broken_plugin)
            
            print(f"📁 Created test plugins in: {plugins_dir}")
            
            # Create plugin loader
            config = PluginConfig(
                plugins_dir=str(plugins_dir),
                auto_reload=False
            )
            
            loader = PluginLoader(config)
            
            # Load all plugins
            print("🔄 Loading plugins...")
            results = await loader.load_all_plugins()
            
            # Check results
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            print(f"✅ Successful loads: {len(successful)}")
            print(f"❌ Failed loads: {len(failed)}")
            
            # Verify that we have both success and failure
            assert len(successful) >= 1, "Should have at least one successful plugin load"
            assert len(failed) >= 1, "Should have at least one failed plugin load"
            
            # Verify that valid plugins are loaded
            loaded_plugins = loader.get_loaded_plugins()
            print(f"🔌 Loaded plugins: {list(loaded_plugins.keys())}")
            
            # Cleanup
            await loader.stop()
            
            print("✅ Plugin error handling test PASSED!")
            print("   - Valid plugins loaded successfully")
            print("   - Broken plugins failed gracefully")
            print("   - System continued operating despite errors")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_basic_cli():
    """Test basic CLI functionality."""
    print("\n🧪 Testing Basic CLI...")
    
    try:
        from edge_device_fleet_manager.cli.main import cli
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test help command
        result = runner.invoke(cli, ['--help'])
        print(f"CLI help exit code: {result.exit_code}")
        
        if result.exit_code == 0:
            print("✅ CLI help command works!")
            return True
        else:
            print(f"❌ CLI help failed: {result.output}")
            return False
            
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("🚀 Edge Device Fleet Manager - Feature 1 Test Suite")
    print("=" * 60)
    
    tests = [
        ("Plugin Error Handling", test_plugin_error_handling),
        ("Basic CLI", test_basic_cli),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Feature 1 is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
