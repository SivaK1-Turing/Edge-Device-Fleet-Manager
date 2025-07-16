#!/usr/bin/env python3
"""
Demo script for Feature 1: Meta-Driven CLI & Configuration

This script demonstrates all the implemented features of Feature 1.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_command(cmd, cwd=None, capture_output=False):
    """Run a command and return the result."""
    print(f"🔧 Running: {' '.join(cmd)}")
    if capture_output:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, cwd=cwd)
        return result.returncode


def demo_basic_cli():
    """Demonstrate basic CLI functionality."""
    print("\n" + "="*60)
    print("🚀 DEMO: Basic CLI Functionality")
    print("="*60)
    
    commands = [
        ["python", "-m", "edge_device_fleet_manager.cli.main", "--help"],
        ["python", "-m", "edge_device_fleet_manager.cli.main", "config", "--format", "table"],
        ["python", "-m", "edge_device_fleet_manager.cli.main", "plugins"],
    ]
    
    for cmd in commands:
        print(f"\n📋 Command: {' '.join(cmd)}")
        run_command(cmd)
        time.sleep(1)


def demo_plugin_system():
    """Demonstrate plugin system with hot-reload."""
    print("\n" + "="*60)
    print("🔌 DEMO: Plugin System with Hot-Reload")
    print("="*60)
    
    # Create a temporary plugin
    with tempfile.TemporaryDirectory() as temp_dir:
        plugins_dir = Path(temp_dir) / "plugins"
        plugins_dir.mkdir()
        
        # Create a demo plugin
        plugin_code = '''
import click
from edge_device_fleet_manager.core.plugins import Plugin, PluginMetadata
from edge_device_fleet_manager.core.context import app_context, get_logger

logger = get_logger(__name__)

class DemoPlugin(Plugin):
    metadata = PluginMetadata(
        name="demo",
        version="1.0.0",
        description="Demo plugin for Feature 1",
        author="Demo Author",
        commands=["demo-hello", "demo-status"]
    )
    
    def initialize(self, config):
        logger.info("Demo plugin initialized", debug=config.debug)
    
    @click.command()
    @click.option('--name', default='Feature 1', help='Name to greet')
    def demo_hello(self, name: str):
        """Demo hello command."""
        correlation_id = app_context.correlation_id
        logger.info("Demo hello executed", name=name, correlation_id=correlation_id)
        click.echo(f"Hello from {name}! (Correlation ID: {correlation_id})")
    
    @click.command()
    def demo_status(self):
        """Demo status command."""
        config = app_context.config
        click.echo("Demo Plugin Status:")
        click.echo(f"  Environment: {config.environment if config else 'Unknown'}")
        click.echo(f"  Debug: {config.debug if config else 'Unknown'}")
        click.echo(f"  Correlation ID: {app_context.correlation_id}")
'''
        
        plugin_file = plugins_dir / "demo_plugin.py"
        plugin_file.write_text(plugin_code)
        
        print(f"📁 Created demo plugin at: {plugin_file}")
        
        # Set environment to use our temp plugins directory
        env = os.environ.copy()
        env["PLUGINS__PLUGINS_DIR"] = str(plugins_dir)
        env["PLUGINS__AUTO_RELOAD"] = "false"  # Disable for demo
        
        # Test plugin loading
        cmd = ["python", "-m", "edge_device_fleet_manager.cli.main", "plugins"]
        print(f"\n📋 Testing plugin loading...")
        subprocess.run(cmd, env=env)


def demo_configuration_system():
    """Demonstrate three-tier configuration system."""
    print("\n" + "="*60)
    print("⚙️ DEMO: Three-Tier Configuration System")
    print("="*60)
    
    # Create temporary config files
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "configs"
        config_dir.mkdir()
        
        # Create demo YAML config
        yaml_config = '''
app_name: "Demo Edge Fleet Manager"
debug: false
environment: "demo"
database:
  url: "sqlite:///demo.db"
  echo: true
logging:
  level: "INFO"
  format: "json"
'''
        
        (config_dir / "default.yaml").write_text(yaml_config)
        
        # Create .env file
        env_config = '''
DEBUG=true
LOGGING__LEVEL=DEBUG
DATABASE__ECHO=false
'''
        
        env_file = Path(temp_dir) / ".env"
        env_file.write_text(env_config)
        
        print(f"📁 Created demo config at: {config_dir}")
        print(f"📁 Created demo .env at: {env_file}")
        
        # Test configuration loading
        env = os.environ.copy()
        env["EDGE_FLEET_CONFIG_DIR"] = str(config_dir)
        
        cmd = ["python", "-m", "edge_device_fleet_manager.cli.main", 
               "--config-dir", str(config_dir), "config", "--format", "json"]
        print(f"\n📋 Testing configuration loading...")
        subprocess.run(cmd, env=env)


def demo_context_management():
    """Demonstrate context management system."""
    print("\n" + "="*60)
    print("🔄 DEMO: Context Management System")
    print("="*60)
    
    # Create a demo script that uses context
    demo_script = '''
import asyncio
from edge_device_fleet_manager.core.context import app_context, async_context_manager
from edge_device_fleet_manager.core.config import Config

async def demo_context():
    config = Config(debug=True, environment="demo")
    
    async with async_context_manager(config=config, correlation_id="demo-123"):
        print(f"Context Config: {app_context.config.app_name}")
        print(f"Context Debug: {app_context.config.debug}")
        print(f"Context Environment: {app_context.config.environment}")
        print(f"Context Correlation ID: {app_context.correlation_id}")

if __name__ == "__main__":
    asyncio.run(demo_context())
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(demo_script)
        script_path = f.name
    
    try:
        print(f"📁 Created demo context script at: {script_path}")
        print(f"\n📋 Testing context management...")
        run_command(["python", script_path])
    finally:
        os.unlink(script_path)


def demo_logging_system():
    """Demonstrate structured logging system."""
    print("\n" + "="*60)
    print("📝 DEMO: Structured Logging System")
    print("="*60)
    
    # Create a demo script that shows logging
    demo_script = '''
import asyncio
from edge_device_fleet_manager.core.config import Config
from edge_device_fleet_manager.core.context import app_context, async_context_manager
from edge_device_fleet_manager.core.logging import setup_logging, get_logger

async def demo_logging():
    config = Config(
        debug=True,
        logging={
            "level": "DEBUG",
            "format": "json",
            "debug_sampling_rate": 1.0
        }
    )
    
    setup_logging(config)
    logger = get_logger("demo")
    
    async with async_context_manager(config=config, correlation_id="demo-logging-123"):
        logger.info("Demo info message", feature="logging", demo=True)
        logger.debug("Demo debug message", feature="logging", demo=True)
        logger.warning("Demo warning message", feature="logging", demo=True)
        
        try:
            raise ValueError("Demo error for logging")
        except Exception as e:
            logger.error("Demo error message", feature="logging", demo=True, exc_info=e)

if __name__ == "__main__":
    asyncio.run(demo_logging())
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(demo_script)
        script_path = f.name
    
    try:
        print(f"📁 Created demo logging script at: {script_path}")
        print(f"\n📋 Testing structured logging...")
        run_command(["python", script_path])
    finally:
        os.unlink(script_path)


def demo_custom_types():
    """Demonstrate custom Click types."""
    print("\n" + "="*60)
    print("🎯 DEMO: Custom Click Types")
    print("="*60)
    
    # Create a demo script that uses custom types
    demo_script = '''
import click
from edge_device_fleet_manager.cli.types import DEVICE_ID, IP_ADDRESS, SUBNET

@click.command()
@click.option('--device-id', type=DEVICE_ID, help='Device ID')
@click.option('--ip-address', type=IP_ADDRESS, help='IP Address')
@click.option('--subnet', type=SUBNET, help='Network subnet')
def demo_types(device_id, ip_address, subnet):
    """Demo command with custom types."""
    if device_id:
        click.echo(f"Device ID: {device_id}")
    if ip_address:
        click.echo(f"IP Address: {ip_address}")
    if subnet:
        click.echo(f"Subnet: {subnet}")

if __name__ == "__main__":
    demo_types()
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(demo_script)
        script_path = f.name
    
    try:
        print(f"📁 Created demo types script at: {script_path}")
        print(f"\n📋 Testing custom types...")
        
        test_commands = [
            ["python", script_path, "--device-id", "device-001"],
            ["python", script_path, "--ip-address", "192.168.1.1"],
            ["python", script_path, "--subnet", "192.168.1.0/24"],
            ["python", script_path, "--help"]
        ]
        
        for cmd in test_commands:
            print(f"\n🔧 Testing: {' '.join(cmd)}")
            run_command(cmd)
            
    finally:
        os.unlink(script_path)


def run_tests():
    """Run the comprehensive test suite."""
    print("\n" + "="*60)
    print("🧪 DEMO: Running Test Suite")
    print("="*60)
    
    test_commands = [
        # Run the specific plugin error test mentioned in requirements
        ["python", "-m", "pytest", 
         "tests/unit/test_plugins.py::TestPluginSystem::test_plugin_load_error_continues_loading_others", 
         "-v"],
        
        # Run all Feature 1 tests
        ["python", "scripts/run_tests.py", "feature1", "-v"],
        
        # Run linting
        ["python", "scripts/run_tests.py", "lint"],
    ]
    
    for cmd in test_commands:
        print(f"\n📋 Running: {' '.join(cmd)}")
        result = run_command(cmd)
        if result != 0:
            print(f"❌ Test failed with exit code: {result}")
        else:
            print(f"✅ Test passed!")


def main():
    """Main demo function."""
    print("🎉 Edge Device Fleet Manager - Feature 1 Demo")
    print("=" * 60)
    print("This demo showcases all implemented features of Feature 1:")
    print("• Meta-Driven CLI & Configuration")
    print("• Hot-Reloadable Plugin System")
    print("• Three-Tier Configuration")
    print("• ContextVar-Based Context Management")
    print("• Structured JSON Logging")
    print("• Custom Click Types")
    print("• Comprehensive Testing")
    print("=" * 60)
    
    demos = [
        ("Basic CLI Functionality", demo_basic_cli),
        ("Plugin System", demo_plugin_system),
        ("Configuration System", demo_configuration_system),
        ("Context Management", demo_context_management),
        ("Logging System", demo_logging_system),
        ("Custom Types", demo_custom_types),
        ("Test Suite", run_tests),
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
            print(f"\n✅ {name} demo completed successfully!")
        except Exception as e:
            print(f"\n❌ {name} demo failed: {e}")
        
        input("\nPress Enter to continue to the next demo...")
    
    print("\n🎉 All Feature 1 demos completed!")
    print("The Edge Device Fleet Manager Feature 1 implementation is ready!")


if __name__ == "__main__":
    main()
