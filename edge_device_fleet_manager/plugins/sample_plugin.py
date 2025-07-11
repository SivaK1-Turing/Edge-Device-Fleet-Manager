"""
Sample plugin demonstrating the plugin system.
"""

import click

from ..core.plugins import Plugin, PluginMetadata
from ..core.context import app_context
from ..core.logging import get_logger

logger = get_logger(__name__)


class SamplePlugin(Plugin):
    """Sample plugin for demonstration."""
    
    metadata = PluginMetadata(
        name="sample",
        version="1.0.0",
        description="Sample plugin for demonstration",
        author="Edge Fleet Team",
        commands=["hello", "status"]
    )
    
    def initialize(self, config) -> None:
        """Initialize the plugin."""
        logger.info("Sample plugin initialized", config_debug=config.debug)
    
    def cleanup(self) -> None:
        """Cleanup the plugin."""
        logger.info("Sample plugin cleaned up")
    
    @click.command()
    @click.option('--name', default='World', help='Name to greet')
    def hello(self, name: str) -> None:
        """Say hello to someone."""
        correlation_id = app_context.correlation_id
        logger.info("Hello command executed", name=name, correlation_id=correlation_id)
        click.echo(f"Hello, {name}! (Correlation ID: {correlation_id})")
    
    @click.command()
    def status(self) -> None:
        """Show plugin status."""
        config = app_context.config
        if config:
            click.echo(f"Plugin Status: Active")
            click.echo(f"Environment: {config.environment}")
            click.echo(f"Debug Mode: {config.debug}")
        else:
            click.echo("Plugin Status: No configuration available")
