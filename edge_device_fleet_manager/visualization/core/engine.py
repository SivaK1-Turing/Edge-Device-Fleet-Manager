"""
Visualization Engine

Core engine for managing visualizations, plugins, and rendering pipeline.
Provides the main interface for creating and managing visualizations.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from ...core.logging import get_logger
from .plugin_manager import PluginManager
from .data_adapter import DataAdapter
from .theme import ThemeManager
from ..plugins.registry import VisualizerRegistry

logger = get_logger(__name__)


class VisualizationEngine:
    """
    Core visualization engine with plugin management and rendering capabilities.
    
    Manages the complete visualization pipeline from data loading through
    plugin discovery to final rendering with theming and interactivity.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize visualization engine.
        
        Args:
            config: Engine configuration options
        """
        self.config = config or {}
        self.plugin_manager = PluginManager()
        self.data_adapter = DataAdapter()
        self.theme_manager = ThemeManager()
        self.registry = VisualizerRegistry()
        
        # Engine state
        self._initialized = False
        self._active_visualizations = {}
        self._render_callbacks = []
        self._update_callbacks = []
        
        # Performance tracking
        self._render_times = []
        self._plugin_load_times = {}
        
        self.logger = get_logger(f"{__name__}.VisualizationEngine")
    
    async def initialize(self) -> None:
        """Initialize the visualization engine."""
        if self._initialized:
            self.logger.warning("Engine already initialized")
            return
        
        try:
            self.logger.info("Initializing visualization engine...")
            
            # Load theme configuration
            await self.theme_manager.load_themes()
            
            # Discover and load plugins
            plugins = await self.plugin_manager.discover_plugins()
            self.logger.info(f"Discovered {len(plugins)} visualizer plugins")
            
            # Register discovered plugins
            for plugin_name, plugin_class in plugins.items():
                self.registry.register(plugin_name, plugin_class)
            
            # Initialize data adapter
            await self.data_adapter.initialize()
            
            self._initialized = True
            self.logger.info("Visualization engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize visualization engine: {e}")
            raise
    
    async def create_visualization(self, 
                                 visualizer_type: str,
                                 data_source: Union[str, Dict[str, Any]],
                                 config: Optional[Dict[str, Any]] = None,
                                 **kwargs) -> str:
        """
        Create a new visualization.
        
        Args:
            visualizer_type: Type of visualizer to use
            data_source: Data source specification
            config: Visualization configuration
            **kwargs: Additional arguments for the visualizer
            
        Returns:
            Visualization ID
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get visualizer class
            visualizer_class = self.registry.get(visualizer_type)
            if not visualizer_class:
                raise ValueError(f"Unknown visualizer type: {visualizer_type}")
            
            # Load data
            data = await self.data_adapter.load_data(data_source)
            
            # Create visualizer instance
            visualizer_config = {**(config or {}), **kwargs}
            visualizer = visualizer_class(visualizer_config)
            
            # Generate unique ID
            viz_id = f"{visualizer_type}_{datetime.now(timezone.utc).timestamp()}"
            
            # Store visualization
            self._active_visualizations[viz_id] = {
                'visualizer': visualizer,
                'data_source': data_source,
                'data': data,
                'config': visualizer_config,
                'created_at': datetime.now(timezone.utc),
                'last_updated': datetime.now(timezone.utc)
            }
            
            self.logger.info(f"Created visualization {viz_id} of type {visualizer_type}")
            return viz_id
            
        except Exception as e:
            self.logger.error(f"Failed to create visualization: {e}")
            raise
    
    async def render_visualization(self, 
                                 viz_id: str,
                                 figure: Optional[matplotlib.figure.Figure] = None,
                                 ax: Optional[plt.Axes] = None,
                                 theme: Optional[str] = None) -> matplotlib.figure.Figure:
        """
        Render a visualization.
        
        Args:
            viz_id: Visualization ID
            figure: Matplotlib figure to render to
            ax: Matplotlib axes to render to
            theme: Theme to apply
            
        Returns:
            Rendered figure
        """
        if viz_id not in self._active_visualizations:
            raise ValueError(f"Visualization {viz_id} not found")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            viz_info = self._active_visualizations[viz_id]
            visualizer = viz_info['visualizer']
            data = viz_info['data']
            
            # Create figure and axes if not provided
            if figure is None:
                figure = plt.figure(figsize=(10, 6))
            
            if ax is None:
                ax = figure.add_subplot(111)
            
            # Apply theme
            if theme:
                self.theme_manager.apply_theme(figure, ax, theme)
            
            # Render visualization using plugin's draw method
            await visualizer.draw(ax, data)
            
            # Update last rendered time
            viz_info['last_updated'] = datetime.now(timezone.utc)
            
            # Track render time
            render_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._render_times.append(render_time)
            if len(self._render_times) > 100:  # Keep last 100 measurements
                self._render_times.pop(0)
            
            # Notify callbacks
            await self._notify_render_callbacks(viz_id, figure)
            
            self.logger.debug(f"Rendered visualization {viz_id} in {render_time:.3f}s")
            return figure
            
        except Exception as e:
            self.logger.error(f"Failed to render visualization {viz_id}: {e}")
            raise
    
    async def update_visualization(self, 
                                 viz_id: str,
                                 data_source: Optional[Union[str, Dict[str, Any]]] = None,
                                 config: Optional[Dict[str, Any]] = None) -> None:
        """
        Update a visualization with new data or configuration.
        
        Args:
            viz_id: Visualization ID
            data_source: New data source (optional)
            config: New configuration (optional)
        """
        if viz_id not in self._active_visualizations:
            raise ValueError(f"Visualization {viz_id} not found")
        
        try:
            viz_info = self._active_visualizations[viz_id]
            
            # Update data source if provided
            if data_source is not None:
                viz_info['data_source'] = data_source
                viz_info['data'] = await self.data_adapter.load_data(data_source)
            
            # Update configuration if provided
            if config is not None:
                viz_info['config'].update(config)
                viz_info['visualizer'].update_config(config)
            
            viz_info['last_updated'] = datetime.now(timezone.utc)
            
            # Notify callbacks
            await self._notify_update_callbacks(viz_id)
            
            self.logger.debug(f"Updated visualization {viz_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update visualization {viz_id}: {e}")
            raise
    
    async def remove_visualization(self, viz_id: str) -> None:
        """
        Remove a visualization.
        
        Args:
            viz_id: Visualization ID
        """
        if viz_id in self._active_visualizations:
            del self._active_visualizations[viz_id]
            self.logger.info(f"Removed visualization {viz_id}")
        else:
            self.logger.warning(f"Visualization {viz_id} not found for removal")
    
    def get_available_visualizers(self) -> List[str]:
        """
        Get list of available visualizer types.
        
        Returns:
            List of visualizer type names
        """
        return list(self.registry.list_visualizers())
    
    def get_visualization_info(self, viz_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a visualization.
        
        Args:
            viz_id: Visualization ID
            
        Returns:
            Visualization information dictionary
        """
        if viz_id not in self._active_visualizations:
            return None
        
        viz_info = self._active_visualizations[viz_id].copy()
        # Remove the actual visualizer object for serialization
        viz_info.pop('visualizer', None)
        viz_info.pop('data', None)  # Data might be large
        
        return viz_info
    
    def get_engine_statistics(self) -> Dict[str, Any]:
        """
        Get engine performance statistics.
        
        Returns:
            Statistics dictionary
        """
        avg_render_time = sum(self._render_times) / len(self._render_times) if self._render_times else 0
        
        return {
            'active_visualizations': len(self._active_visualizations),
            'available_visualizers': len(self.registry.list_visualizers()),
            'total_renders': len(self._render_times),
            'average_render_time_seconds': avg_render_time,
            'plugin_load_times': self._plugin_load_times.copy(),
            'initialized': self._initialized
        }
    
    def add_render_callback(self, callback: Callable[[str, matplotlib.figure.Figure], None]) -> None:
        """Add callback for render events."""
        self._render_callbacks.append(callback)
    
    def add_update_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for update events."""
        self._update_callbacks.append(callback)
    
    async def _notify_render_callbacks(self, viz_id: str, figure: matplotlib.figure.Figure) -> None:
        """Notify render callbacks."""
        for callback in self._render_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(viz_id, figure)
                else:
                    callback(viz_id, figure)
            except Exception as e:
                self.logger.error(f"Error in render callback: {e}")
    
    async def _notify_update_callbacks(self, viz_id: str) -> None:
        """Notify update callbacks."""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(viz_id)
                else:
                    callback(viz_id)
            except Exception as e:
                self.logger.error(f"Error in update callback: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the visualization engine."""
        self.logger.info("Shutting down visualization engine...")
        
        # Clear active visualizations
        self._active_visualizations.clear()
        
        # Shutdown data adapter
        await self.data_adapter.shutdown()
        
        self._initialized = False
        self.logger.info("Visualization engine shutdown complete")
