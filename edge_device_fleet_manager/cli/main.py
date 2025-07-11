"""
Main CLI entry point for Edge Device Fleet Manager.
"""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from ..core.config import get_config, get_config_sync
from ..core.context import app_context, async_context_manager, context_manager
from ..core.logging import setup_logging, get_logger
from ..core.plugins import initialize_plugin_system, shutdown_plugin_system
from ..core.exceptions import EdgeFleetError

# Install rich traceback handler
install(show_locals=True)

console = Console()
logger = get_logger(__name__)


class AsyncGroup(click.Group):
    """Click group that supports async commands."""

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the group, handling async commands."""
        return super().invoke(ctx)


class AsyncCommand(click.Command):
    """Click command that supports async callbacks."""

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the command, handling async callbacks."""
        if asyncio.iscoroutinefunction(self.callback):
            return asyncio.run(self.callback(**ctx.params))
        return super().invoke(ctx)


@click.group(cls=AsyncGroup)
@click.option(
    '--config-dir',
    default='configs',
    help='Configuration directory path',
    envvar='EDGE_FLEET_CONFIG_DIR'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode',
    envvar='EDGE_FLEET_DEBUG'
)
@click.option(
    '--log-level',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    help='Set logging level',
    envvar='EDGE_FLEET_LOG_LEVEL'
)
@click.option(
    '--correlation-id',
    help='Set correlation ID for request tracing',
    envvar='EDGE_FLEET_CORRELATION_ID'
)
@click.pass_context
def cli(
    ctx: click.Context,
    config_dir: str,
    debug: bool,
    log_level: str,
    correlation_id: Optional[str]
) -> None:
    """
    Edge Device Fleet Manager - Production-grade IoT device management at scale.
    
    A comprehensive CLI and library for discovering, configuring, monitoring,
    and maintaining IoT edge devices with hot-reloadable plugins, multi-tier
    configuration, and advanced analytics.
    """
    try:
        # Load configuration synchronously for now
        config = get_config_sync()

        # Override config with CLI options
        if debug:
            config.debug = debug
        if log_level:
            config.logging.level = log_level

        # Setup logging
        setup_logging(config)

        # Setup application context
        with context_manager(
            config=config,
            correlation_id=correlation_id
        ):
            # Store context in Click context
            ctx.ensure_object(dict)
            ctx.obj['config'] = config
            ctx.obj['app_context'] = app_context

            # For now, skip plugin system initialization in the main CLI
            # Plugins can be initialized per-command if needed
            ctx.obj['plugin_loader'] = None

    except Exception as e:
        console.print(f"[red]Error initializing CLI: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['table', 'json', 'yaml']),
              help='Output format')
@click.pass_context
def config(ctx: click.Context, output_format: str) -> None:
    """Show current configuration."""
    try:
        config_obj = ctx.obj['config']
        
        if output_format == 'json':
            import json
            console.print(json.dumps(config_obj.dict(), indent=2))
        elif output_format == 'yaml':
            import yaml
            console.print(yaml.dump(config_obj.dict(), default_flow_style=False))
        else:
            # Table format
            from rich.table import Table
            
            table = Table(title="Edge Fleet Manager Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            
            # Flatten config for display
            def flatten_dict(d, parent_key='', sep='__'):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, str(v)))
                return dict(items)
            
            flat_config = flatten_dict(config_obj.dict())
            for key, value in sorted(flat_config.items()):
                table.add_row(key, value)
            
            console.print(table)
            
    except Exception as e:
        logger.error("Failed to show configuration", error=str(e), exc_info=e)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def plugins(ctx: click.Context) -> None:
    """List loaded plugins."""
    try:
        plugin_loader = ctx.obj.get('plugin_loader')
        if not plugin_loader:
            console.print("[yellow]Plugin system not initialized[/yellow]")
            return
        
        loaded_plugins = plugin_loader.get_loaded_plugins()
        
        if not loaded_plugins:
            console.print("[yellow]No plugins loaded[/yellow]")
            return
        
        from rich.table import Table
        
        table = Table(title="Loaded Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Description", style="white")
        table.add_column("Commands", style="yellow")
        
        for name, plugin in loaded_plugins.items():
            commands = [cmd.name for cmd in plugin.get_commands()]
            table.add_row(
                plugin.metadata.name,
                plugin.metadata.version,
                plugin.metadata.description,
                ", ".join(commands)
            )
        
        console.print(table)
        
    except Exception as e:
        logger.error("Failed to list plugins", error=str(e), exc_info=e)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--name', required=True, help='Plugin name to reload')
@click.pass_context
def reload_plugin(ctx: click.Context, name: str) -> None:
    """Reload a specific plugin."""
    try:
        plugin_loader = ctx.obj.get('plugin_loader')
        if not plugin_loader:
            console.print("[red]Plugin system not initialized[/red]")
            sys.exit(1)
        
        # Find plugin file
        plugin_files = {v: k for k, v in plugin_loader.plugin_files.items()}
        plugin_file = plugin_files.get(name)
        
        if not plugin_file:
            console.print(f"[red]Plugin '{name}' not found[/red]")
            sys.exit(1)
        
        # Reload plugin (would need async implementation)
        console.print(f"[yellow]Plugin reload not implemented in sync mode[/yellow]")
        return
        
        if result.success:
            console.print(f"[green]Plugin '{name}' reloaded successfully[/green]")
        else:
            console.print(f"[red]Failed to reload plugin '{name}': {result.error}[/red]")
            sys.exit(1)
            
    except Exception as e:
        logger.error("Failed to reload plugin", plugin_name=name, error=str(e), exc_info=e)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command(hidden=True)
@click.pass_context
def debug_repl(ctx: click.Context) -> None:
    """Launch IPython REPL with app context (hidden debug command)."""
    try:
        import IPython
        
        # Prepare namespace with app context
        namespace = {
            'config': ctx.obj['config'],
            'app_context': ctx.obj['app_context'],
            'plugin_loader': ctx.obj.get('plugin_loader'),
            'logger': logger,
            'console': console,
        }
        
        console.print("[cyan]Starting debug REPL with app context...[/cyan]")
        console.print("[dim]Available objects: config, app_context, plugin_loader, logger, console[/dim]")
        
        IPython.start_ipython(argv=[], user_ns=namespace)
        
    except ImportError:
        console.print("[red]IPython not available. Install with: pip install ipython[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to start debug REPL", error=str(e), exc_info=e)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except EdgeFleetError as e:
        console.print(f"[red]Edge Fleet Error: {e.message}[/red]")
        if e.error_code:
            console.print(f"[dim]Error Code: {e.error_code}[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.error("Unexpected error in main", error=str(e), exc_info=e)
        sys.exit(1)
    finally:
        # Cleanup (skip for now in sync mode)
        pass


if __name__ == '__main__':
    main()
