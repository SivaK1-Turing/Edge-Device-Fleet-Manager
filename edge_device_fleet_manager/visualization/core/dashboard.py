"""
Dashboard Framework

Provides dashboard composition, layout management, and real-time
updates for multiple visualizations in a unified interface.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib.figure
from matplotlib.gridspec import GridSpec

from ...core.logging import get_logger
from .engine import VisualizationEngine

logger = get_logger(__name__)


class DashboardLayout:
    """
    Dashboard layout manager for organizing visualizations.
    
    Supports various layout types including grid, flow, and custom layouts
    with responsive sizing and positioning.
    """
    
    def __init__(self, layout_type: str = 'grid', **kwargs):
        """
        Initialize dashboard layout.
        
        Args:
            layout_type: Type of layout ('grid', 'flow', 'custom')
            **kwargs: Layout-specific configuration
        """
        self.layout_type = layout_type
        self.config = kwargs
        self.positions = {}
        
        self.logger = get_logger(f"{__name__}.DashboardLayout")
    
    def calculate_positions(self, num_visualizations: int, 
                          figure_size: Tuple[int, int] = (12, 8)) -> Dict[str, Dict[str, Any]]:
        """
        Calculate positions for visualizations based on layout type.
        
        Args:
            num_visualizations: Number of visualizations to layout
            figure_size: Figure size (width, height)
            
        Returns:
            Dictionary mapping visualization IDs to position info
        """
        if self.layout_type == 'grid':
            return self._calculate_grid_positions(num_visualizations, figure_size)
        elif self.layout_type == 'flow':
            return self._calculate_flow_positions(num_visualizations, figure_size)
        elif self.layout_type == 'custom':
            return self._calculate_custom_positions(num_visualizations, figure_size)
        else:
            # Default to grid
            return self._calculate_grid_positions(num_visualizations, figure_size)
    
    def _calculate_grid_positions(self, num_viz: int, figure_size: Tuple[int, int]) -> Dict[str, Dict[str, Any]]:
        """Calculate grid layout positions."""
        if num_viz == 0:
            return {}
        
        # Determine grid dimensions
        cols = self.config.get('columns', None)
        if cols is None:
            # Auto-calculate optimal grid
            if num_viz == 1:
                rows, cols = 1, 1
            elif num_viz == 2:
                rows, cols = 1, 2
            elif num_viz <= 4:
                rows, cols = 2, 2
            elif num_viz <= 6:
                rows, cols = 2, 3
            elif num_viz <= 9:
                rows, cols = 3, 3
            else:
                cols = int(num_viz ** 0.5) + 1
                rows = (num_viz + cols - 1) // cols
        else:
            rows = (num_viz + cols - 1) // cols
        
        positions = {}
        for i in range(num_viz):
            row = i // cols
            col = i % cols
            
            positions[f"viz_{i}"] = {
                'row': row,
                'col': col,
                'rowspan': 1,
                'colspan': 1,
                'grid_rows': rows,
                'grid_cols': cols
            }
        
        return positions
    
    def _calculate_flow_positions(self, num_viz: int, figure_size: Tuple[int, int]) -> Dict[str, Dict[str, Any]]:
        """Calculate flow layout positions."""
        # Flow layout arranges items in rows, wrapping as needed
        items_per_row = self.config.get('items_per_row', 3)
        
        positions = {}
        for i in range(num_viz):
            row = i // items_per_row
            col = i % items_per_row
            
            positions[f"viz_{i}"] = {
                'row': row,
                'col': col,
                'rowspan': 1,
                'colspan': 1,
                'grid_rows': (num_viz + items_per_row - 1) // items_per_row,
                'grid_cols': min(items_per_row, num_viz)
            }
        
        return positions
    
    def _calculate_custom_positions(self, num_viz: int, figure_size: Tuple[int, int]) -> Dict[str, Dict[str, Any]]:
        """Calculate custom layout positions."""
        # Custom layout uses predefined positions
        custom_positions = self.config.get('positions', {})
        
        positions = {}
        for i, (viz_id, pos_info) in enumerate(custom_positions.items()):
            if i >= num_viz:
                break
            
            positions[f"viz_{i}"] = {
                'row': pos_info.get('row', 0),
                'col': pos_info.get('col', 0),
                'rowspan': pos_info.get('rowspan', 1),
                'colspan': pos_info.get('colspan', 1),
                'grid_rows': self.config.get('total_rows', 3),
                'grid_cols': self.config.get('total_cols', 3)
            }
        
        return positions


class Dashboard:
    """
    Dashboard for composing and managing multiple visualizations.
    
    Provides layout management, real-time updates, and unified
    control over multiple visualizations in a single interface.
    """
    
    def __init__(self, layout: DashboardLayout, engine: Optional[VisualizationEngine] = None):
        """
        Initialize dashboard.
        
        Args:
            layout: Dashboard layout manager
            engine: Visualization engine (creates new if None)
        """
        self.layout = layout
        self.engine = engine or VisualizationEngine()
        
        # Dashboard state
        self.visualizations = {}
        self.figure = None
        self.axes = {}
        self.update_callbacks = []
        self.auto_refresh = False
        self.refresh_interval = 30  # seconds
        self._refresh_task = None
        
        self.logger = get_logger(f"{__name__}.Dashboard")
    
    async def initialize(self) -> None:
        """Initialize the dashboard."""
        if not self.engine._initialized:
            await self.engine.initialize()
        
        self.logger.info("Dashboard initialized")
    
    async def add_visualization(self, viz_id: str, visualizer_type: str,
                              data_source: Any, config: Optional[Dict[str, Any]] = None,
                              position: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a visualization to the dashboard.
        
        Args:
            viz_id: Unique identifier for the visualization
            visualizer_type: Type of visualizer to use
            data_source: Data source for the visualization
            config: Visualization configuration
            position: Optional position override
            
        Returns:
            True if visualization was added successfully
        """
        try:
            # Create visualization using engine
            engine_viz_id = await self.engine.create_visualization(
                visualizer_type, data_source, config
            )
            
            # Store visualization info
            self.visualizations[viz_id] = {
                'engine_viz_id': engine_viz_id,
                'visualizer_type': visualizer_type,
                'data_source': data_source,
                'config': config or {},
                'position': position,
                'created_at': datetime.now(timezone.utc),
                'last_updated': datetime.now(timezone.utc)
            }
            
            self.logger.info(f"Added visualization {viz_id} to dashboard")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add visualization {viz_id}: {e}")
            return False
    
    async def remove_visualization(self, viz_id: str) -> bool:
        """
        Remove a visualization from the dashboard.
        
        Args:
            viz_id: ID of visualization to remove
            
        Returns:
            True if visualization was removed successfully
        """
        try:
            if viz_id not in self.visualizations:
                self.logger.warning(f"Visualization {viz_id} not found")
                return False
            
            # Remove from engine
            viz_info = self.visualizations[viz_id]
            await self.engine.remove_visualization(viz_info['engine_viz_id'])
            
            # Remove from dashboard
            del self.visualizations[viz_id]
            
            # Remove axes if exists
            if viz_id in self.axes:
                del self.axes[viz_id]
            
            self.logger.info(f"Removed visualization {viz_id} from dashboard")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove visualization {viz_id}: {e}")
            return False
    
    async def update_visualization(self, viz_id: str, 
                                 data_source: Optional[Any] = None,
                                 config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update a visualization in the dashboard.
        
        Args:
            viz_id: ID of visualization to update
            data_source: New data source (optional)
            config: New configuration (optional)
            
        Returns:
            True if visualization was updated successfully
        """
        try:
            if viz_id not in self.visualizations:
                self.logger.error(f"Visualization {viz_id} not found")
                return False
            
            viz_info = self.visualizations[viz_id]
            
            # Update engine visualization
            await self.engine.update_visualization(
                viz_info['engine_viz_id'], data_source, config
            )
            
            # Update dashboard info
            if data_source is not None:
                viz_info['data_source'] = data_source
            if config is not None:
                viz_info['config'].update(config)
            
            viz_info['last_updated'] = datetime.now(timezone.utc)
            
            self.logger.debug(f"Updated visualization {viz_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update visualization {viz_id}: {e}")
            return False
    
    async def render(self, figure_size: Tuple[int, int] = (15, 10),
                    theme: Optional[str] = None) -> matplotlib.figure.Figure:
        """
        Render the complete dashboard.
        
        Args:
            figure_size: Size of the figure (width, height)
            theme: Theme to apply
            
        Returns:
            Rendered matplotlib figure
        """
        try:
            # Create figure
            self.figure = plt.figure(figsize=figure_size)
            self.figure.suptitle('Dashboard', fontsize=16, fontweight='bold')
            
            # Calculate layout positions
            num_viz = len(self.visualizations)
            if num_viz == 0:
                # Empty dashboard
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, 'No visualizations added', 
                       transform=ax.transAxes, ha='center', va='center',
                       fontsize=14, alpha=0.7)
                ax.axis('off')
                return self.figure
            
            positions = self.layout.calculate_positions(num_viz, figure_size)
            
            # Create grid
            max_rows = max(pos['grid_rows'] for pos in positions.values())
            max_cols = max(pos['grid_cols'] for pos in positions.values())
            gs = GridSpec(max_rows, max_cols, figure=self.figure)
            
            # Render each visualization
            for i, (viz_id, viz_info) in enumerate(self.visualizations.items()):
                try:
                    # Get position
                    pos_key = f"viz_{i}"
                    if pos_key in positions:
                        pos = positions[pos_key]
                    else:
                        # Fallback position
                        pos = {'row': 0, 'col': 0, 'rowspan': 1, 'colspan': 1}
                    
                    # Create subplot
                    ax = self.figure.add_subplot(
                        gs[pos['row']:pos['row']+pos['rowspan'], 
                           pos['col']:pos['col']+pos['colspan']]
                    )
                    
                    # Store axes reference
                    self.axes[viz_id] = ax
                    
                    # Render visualization
                    await self.engine.render_visualization(
                        viz_info['engine_viz_id'], self.figure, ax, theme
                    )
                    
                except Exception as e:
                    self.logger.error(f"Failed to render visualization {viz_id}: {e}")
                    # Show error in subplot
                    if viz_id in self.axes:
                        ax = self.axes[viz_id]
                        ax.text(0.5, 0.5, f"Error: {str(e)}", 
                               transform=ax.transAxes, ha='center', va='center',
                               bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3))
            
            # Adjust layout
            plt.tight_layout()
            
            # Notify callbacks
            await self._notify_update_callbacks()
            
            self.logger.debug(f"Rendered dashboard with {num_viz} visualizations")
            return self.figure
            
        except Exception as e:
            self.logger.error(f"Failed to render dashboard: {e}")
            raise
    
    async def start_auto_refresh(self, interval_seconds: int = 30) -> None:
        """
        Start automatic dashboard refresh.
        
        Args:
            interval_seconds: Refresh interval in seconds
        """
        if self._refresh_task and not self._refresh_task.done():
            self.logger.warning("Auto-refresh already running")
            return
        
        self.auto_refresh = True
        self.refresh_interval = interval_seconds
        
        async def refresh_loop():
            while self.auto_refresh:
                try:
                    await asyncio.sleep(self.refresh_interval)
                    if self.auto_refresh:  # Check again after sleep
                        await self.refresh()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in auto-refresh: {e}")
        
        self._refresh_task = asyncio.create_task(refresh_loop())
        self.logger.info(f"Started auto-refresh with {interval_seconds}s interval")
    
    async def stop_auto_refresh(self) -> None:
        """Stop automatic dashboard refresh."""
        self.auto_refresh = False
        
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped auto-refresh")
    
    async def refresh(self) -> None:
        """Refresh all visualizations in the dashboard."""
        try:
            # Update all visualizations with their current data sources
            for viz_id, viz_info in self.visualizations.items():
                await self.update_visualization(viz_id, viz_info['data_source'])
            
            # Re-render if figure exists
            if self.figure:
                await self.render(self.figure.get_size_inches())
            
            self.logger.debug("Dashboard refreshed")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboard: {e}")
    
    def add_update_callback(self, callback: Callable[[], None]) -> None:
        """Add callback for dashboard update events."""
        self.update_callbacks.append(callback)
    
    async def _notify_update_callbacks(self) -> None:
        """Notify update callbacks."""
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in update callback: {e}")
    
    def get_visualization_info(self, viz_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a visualization.
        
        Args:
            viz_id: Visualization ID
            
        Returns:
            Visualization information dictionary
        """
        if viz_id not in self.visualizations:
            return None
        
        viz_info = self.visualizations[viz_id].copy()
        # Add engine info
        engine_info = self.engine.get_visualization_info(viz_info['engine_viz_id'])
        if engine_info:
            viz_info.update(engine_info)
        
        return viz_info
    
    def list_visualizations(self) -> List[str]:
        """
        Get list of visualization IDs in the dashboard.
        
        Returns:
            List of visualization IDs
        """
        return list(self.visualizations.keys())
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """
        Get dashboard statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_visualizations': len(self.visualizations),
            'layout_type': self.layout.layout_type,
            'auto_refresh_enabled': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'visualization_ids': list(self.visualizations.keys()),
            'engine_stats': self.engine.get_engine_statistics()
        }
    
    async def shutdown(self) -> None:
        """Shutdown the dashboard."""
        # Stop auto-refresh
        await self.stop_auto_refresh()
        
        # Clear visualizations
        for viz_id in list(self.visualizations.keys()):
            await self.remove_visualization(viz_id)
        
        # Shutdown engine
        await self.engine.shutdown()
        
        self.logger.info("Dashboard shutdown complete")
