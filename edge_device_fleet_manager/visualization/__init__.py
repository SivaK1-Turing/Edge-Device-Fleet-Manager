"""
Dynamic Visualization & Dashboard

Plugin-based plotting engine with extensible visualizers loaded via entry_points.
Each visualizer defines a draw(ax, data) method for flexible chart rendering.

Features:
- Plugin-based architecture with entry_points discovery
- Extensible visualizer system with standardized interface
- Real-time dashboard composition and updates
- Interactive features (zoom, pan, filtering)
- Data adapters for persistence layer integration
- Comprehensive theming and styling support
"""

from .core.engine import VisualizationEngine
from .core.plugin_manager import PluginManager
from .core.dashboard import Dashboard, DashboardLayout
from .core.data_adapter import DataAdapter
from .plugins.base import BaseVisualizer
from .plugins.registry import VisualizerRegistry

__version__ = "1.0.0"
__author__ = "Edge Device Fleet Manager Team"

# Core exports
__all__ = [
    # Core engine
    'VisualizationEngine',
    'PluginManager',
    
    # Dashboard system
    'Dashboard',
    'DashboardLayout',
    
    # Data integration
    'DataAdapter',
    
    # Plugin system
    'BaseVisualizer',
    'VisualizerRegistry',
    
    # Convenience functions
    'create_dashboard',
    'load_visualizers',
    'register_visualizer',
]

# Convenience functions
def create_dashboard(layout='grid', **kwargs):
    """Create a new dashboard with specified layout."""
    return Dashboard(layout=DashboardLayout(layout), **kwargs)

def load_visualizers():
    """Load all available visualizers from entry points."""
    manager = PluginManager()
    return manager.discover_plugins()

def register_visualizer(name, visualizer_class):
    """Register a visualizer class."""
    registry = VisualizerRegistry()
    registry.register(name, visualizer_class)
    return registry
