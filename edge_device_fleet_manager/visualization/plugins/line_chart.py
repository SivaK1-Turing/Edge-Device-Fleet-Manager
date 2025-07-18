"""
Line Chart Visualizer

Plugin for creating line charts with support for time series data,
multiple series, and real-time updates.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.axes
import numpy as np
import pandas as pd

from .base import BaseVisualizer


class LineChartVisualizer(BaseVisualizer):
    """
    Line chart visualizer plugin.
    
    Supports single and multiple line series, time series data,
    real-time updates, and interactive features.
    """
    
    name = "Line Chart"
    description = "Line chart visualizer for time series and continuous data"
    version = "1.0.0"
    
    supports_real_time = True
    supports_interaction = True
    supported_data_types = ['dict', 'list', 'pandas.DataFrame', 'numpy.ndarray']
    
    config_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Line Chart"},
            "xlabel": {"type": "string", "default": "X"},
            "ylabel": {"type": "string", "default": "Y"},
            "color": {"type": "string", "default": "auto"},
            "line_style": {"type": "string", "default": "-", "enum": ["-", "--", "-.", ":"]},
            "line_width": {"type": "number", "default": 2.0},
            "marker": {"type": "string", "default": "none"},
            "marker_size": {"type": "number", "default": 6},
            "alpha": {"type": "number", "default": 1.0},
            "grid": {"type": "boolean", "default": True},
            "legend": {"type": "boolean", "default": True},
            "x_column": {"type": "string", "default": "x"},
            "y_column": {"type": "string", "default": "y"},
            "series_column": {"type": "string", "default": "series"},
            "time_format": {"type": "string", "default": "auto"},
            "smooth": {"type": "boolean", "default": False},
            "fill_area": {"type": "boolean", "default": False}
        }
    }
    
    async def draw(self, ax: matplotlib.axes.Axes, data: Any) -> None:
        """
        Draw line chart on the provided axes.
        
        Args:
            ax: Matplotlib axes to draw on
            data: Data to visualize
        """
        try:
            # Update render statistics
            self._render_count += 1
            self._last_render_time = datetime.now(timezone.utc)
            
            # Validate and preprocess data
            if not self.validate_data(data):
                raise ValueError("Invalid data format for line chart")
            
            processed_data = self.preprocess_data(data)
            
            # Handle different data formats
            if isinstance(processed_data, pd.DataFrame):
                await self._draw_dataframe(ax, processed_data)
            elif isinstance(processed_data, dict):
                await self._draw_dict(ax, processed_data)
            elif isinstance(processed_data, (list, np.ndarray)):
                await self._draw_array(ax, processed_data)
            else:
                raise ValueError(f"Unsupported data type: {type(processed_data)}")
            
            # Apply styling
            self.apply_styling(ax)
            
            self.logger.debug(f"Rendered line chart with {self._render_count} total renders")
            
        except Exception as e:
            self.logger.error(f"Error drawing line chart: {e}")
            # Draw error message on axes
            ax.text(0.5, 0.5, f"Error: {str(e)}", 
                   transform=ax.transAxes, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3))
            raise
    
    async def _draw_dataframe(self, ax: matplotlib.axes.Axes, df: pd.DataFrame) -> None:
        """Draw line chart from pandas DataFrame."""
        x_col = self.config.get('x_column', 'x')
        y_col = self.config.get('y_column', 'y')
        series_col = self.config.get('series_column', 'series')
        
        # Check if we have multiple series
        if series_col in df.columns and len(df[series_col].unique()) > 1:
            await self._draw_multiple_series_df(ax, df, x_col, y_col, series_col)
        else:
            await self._draw_single_series_df(ax, df, x_col, y_col)
    
    async def _draw_single_series_df(self, ax: matplotlib.axes.Axes, 
                                   df: pd.DataFrame, x_col: str, y_col: str) -> None:
        """Draw single series from DataFrame."""
        if x_col not in df.columns or y_col not in df.columns:
            # Use index as x if x_col not found
            x_data = df.index if x_col not in df.columns else df[x_col]
            y_data = df[y_col] if y_col in df.columns else df.iloc[:, 0]
        else:
            x_data = df[x_col]
            y_data = df[y_col]
        
        # Sort by x values
        sorted_indices = np.argsort(x_data)
        x_data = x_data.iloc[sorted_indices] if hasattr(x_data, 'iloc') else x_data[sorted_indices]
        y_data = y_data.iloc[sorted_indices] if hasattr(y_data, 'iloc') else y_data[sorted_indices]
        
        # Apply smoothing if requested
        if self.config.get('smooth', False):
            x_data, y_data = self._smooth_data(x_data, y_data)
        
        # Plot line
        line = ax.plot(x_data, y_data,
                      linestyle=self.config.get('line_style', '-'),
                      linewidth=self.config.get('line_width', 2.0),
                      marker=self.config.get('marker', 'none'),
                      markersize=self.config.get('marker_size', 6),
                      alpha=self.config.get('alpha', 1.0),
                      color=self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color'))
        
        # Fill area under curve if requested
        if self.config.get('fill_area', False):
            ax.fill_between(x_data, y_data, alpha=0.3, color=line[0].get_color())
    
    async def _draw_multiple_series_df(self, ax: matplotlib.axes.Axes, 
                                     df: pd.DataFrame, x_col: str, y_col: str, series_col: str) -> None:
        """Draw multiple series from DataFrame."""
        series_names = df[series_col].unique()
        colors = self.get_color_palette(len(series_names))
        
        for i, series_name in enumerate(series_names):
            series_data = df[df[series_col] == series_name]
            
            if len(series_data) == 0:
                continue
            
            x_data = series_data[x_col]
            y_data = series_data[y_col]
            
            # Sort by x values
            sorted_indices = np.argsort(x_data)
            x_data = x_data.iloc[sorted_indices]
            y_data = y_data.iloc[sorted_indices]
            
            # Apply smoothing if requested
            if self.config.get('smooth', False):
                x_data, y_data = self._smooth_data(x_data, y_data)
            
            # Plot line
            color = colors[i] if self.config.get('color') == 'auto' else self.config.get('color')
            line = ax.plot(x_data, y_data,
                          linestyle=self.config.get('line_style', '-'),
                          linewidth=self.config.get('line_width', 2.0),
                          marker=self.config.get('marker', 'none'),
                          markersize=self.config.get('marker_size', 6),
                          alpha=self.config.get('alpha', 1.0),
                          color=color,
                          label=str(series_name))
            
            # Fill area under curve if requested
            if self.config.get('fill_area', False):
                ax.fill_between(x_data, y_data, alpha=0.2, color=line[0].get_color())
    
    async def _draw_dict(self, ax: matplotlib.axes.Axes, data: Dict[str, Any]) -> None:
        """Draw line chart from dictionary data."""
        if 'x' in data and 'y' in data:
            # Simple x, y data
            x_data = np.array(data['x'])
            y_data = np.array(data['y'])
            
            # Sort by x values
            sorted_indices = np.argsort(x_data)
            x_data = x_data[sorted_indices]
            y_data = y_data[sorted_indices]
            
            # Apply smoothing if requested
            if self.config.get('smooth', False):
                x_data, y_data = self._smooth_data(x_data, y_data)
            
            # Plot line
            line = ax.plot(x_data, y_data,
                          linestyle=self.config.get('line_style', '-'),
                          linewidth=self.config.get('line_width', 2.0),
                          marker=self.config.get('marker', 'none'),
                          markersize=self.config.get('marker_size', 6),
                          alpha=self.config.get('alpha', 1.0),
                          color=self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color'))
            
            # Fill area under curve if requested
            if self.config.get('fill_area', False):
                ax.fill_between(x_data, y_data, alpha=0.3, color=line[0].get_color())
        
        elif 'series' in data:
            # Multiple series data
            series_data = data['series']
            colors = self.get_color_palette(len(series_data))
            
            for i, (series_name, series_values) in enumerate(series_data.items()):
                if 'x' in series_values and 'y' in series_values:
                    x_data = np.array(series_values['x'])
                    y_data = np.array(series_values['y'])
                    
                    # Sort by x values
                    sorted_indices = np.argsort(x_data)
                    x_data = x_data[sorted_indices]
                    y_data = y_data[sorted_indices]
                    
                    # Apply smoothing if requested
                    if self.config.get('smooth', False):
                        x_data, y_data = self._smooth_data(x_data, y_data)
                    
                    # Plot line
                    color = colors[i] if self.config.get('color') == 'auto' else self.config.get('color')
                    line = ax.plot(x_data, y_data,
                                  linestyle=self.config.get('line_style', '-'),
                                  linewidth=self.config.get('line_width', 2.0),
                                  marker=self.config.get('marker', 'none'),
                                  markersize=self.config.get('marker_size', 6),
                                  alpha=self.config.get('alpha', 1.0),
                                  color=color,
                                  label=str(series_name))
                    
                    # Fill area under curve if requested
                    if self.config.get('fill_area', False):
                        ax.fill_between(x_data, y_data, alpha=0.2, color=line[0].get_color())
        else:
            raise ValueError("Dictionary data must contain 'x' and 'y' keys or 'series' key")
    
    async def _draw_array(self, ax: matplotlib.axes.Axes, data: Union[List, np.ndarray]) -> None:
        """Draw line chart from array data."""
        data_array = np.array(data)
        
        if data_array.ndim == 1:
            # 1D array - use indices as x values
            x_data = np.arange(len(data_array))
            y_data = data_array
        elif data_array.ndim == 2:
            if data_array.shape[1] == 2:
                # 2D array with 2 columns - x, y
                x_data = data_array[:, 0]
                y_data = data_array[:, 1]
            else:
                # Multiple series - first column as x, rest as y series
                x_data = data_array[:, 0]
                colors = self.get_color_palette(data_array.shape[1] - 1)
                
                for i in range(1, data_array.shape[1]):
                    y_data = data_array[:, i]
                    
                    # Sort by x values
                    sorted_indices = np.argsort(x_data)
                    x_sorted = x_data[sorted_indices]
                    y_sorted = y_data[sorted_indices]
                    
                    # Apply smoothing if requested
                    if self.config.get('smooth', False):
                        x_sorted, y_sorted = self._smooth_data(x_sorted, y_sorted)
                    
                    # Plot line
                    color = colors[i-1] if self.config.get('color') == 'auto' else self.config.get('color')
                    line = ax.plot(x_sorted, y_sorted,
                                  linestyle=self.config.get('line_style', '-'),
                                  linewidth=self.config.get('line_width', 2.0),
                                  marker=self.config.get('marker', 'none'),
                                  markersize=self.config.get('marker_size', 6),
                                  alpha=self.config.get('alpha', 1.0),
                                  color=color,
                                  label=f"Series {i}")
                    
                    # Fill area under curve if requested
                    if self.config.get('fill_area', False):
                        ax.fill_between(x_sorted, y_sorted, alpha=0.2, color=line[0].get_color())
                return
        else:
            raise ValueError("Array data must be 1D or 2D")
        
        # Sort by x values
        sorted_indices = np.argsort(x_data)
        x_data = x_data[sorted_indices]
        y_data = y_data[sorted_indices]
        
        # Apply smoothing if requested
        if self.config.get('smooth', False):
            x_data, y_data = self._smooth_data(x_data, y_data)
        
        # Plot line
        line = ax.plot(x_data, y_data,
                      linestyle=self.config.get('line_style', '-'),
                      linewidth=self.config.get('line_width', 2.0),
                      marker=self.config.get('marker', 'none'),
                      markersize=self.config.get('marker_size', 6),
                      alpha=self.config.get('alpha', 1.0),
                      color=self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color'))
        
        # Fill area under curve if requested
        if self.config.get('fill_area', False):
            ax.fill_between(x_data, y_data, alpha=0.3, color=line[0].get_color())
    
    def _smooth_data(self, x_data: np.ndarray, y_data: np.ndarray, 
                    window_size: int = 5) -> tuple:
        """
        Apply smoothing to data using moving average.
        
        Args:
            x_data: X values
            y_data: Y values
            window_size: Size of smoothing window
            
        Returns:
            Tuple of smoothed (x_data, y_data)
        """
        if len(y_data) < window_size:
            return x_data, y_data
        
        # Apply moving average
        smoothed_y = np.convolve(y_data, np.ones(window_size)/window_size, mode='valid')
        
        # Adjust x_data to match smoothed_y length
        offset = (window_size - 1) // 2
        smoothed_x = x_data[offset:offset + len(smoothed_y)]
        
        return smoothed_x, smoothed_y
