"""
Bar Chart Visualizer

Plugin for creating bar charts with support for categorical data,
grouped bars, and horizontal/vertical orientations.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.axes
import numpy as np
import pandas as pd

from .base import BaseVisualizer


class BarChartVisualizer(BaseVisualizer):
    """
    Bar chart visualizer plugin.
    
    Supports vertical and horizontal bar charts, grouped bars,
    stacked bars, and categorical data visualization.
    """
    
    name = "Bar Chart"
    description = "Bar chart visualizer for categorical and discrete data"
    version = "1.0.0"
    
    supports_real_time = True
    supports_interaction = True
    supported_data_types = ['dict', 'list', 'pandas.DataFrame', 'numpy.ndarray']
    
    config_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Bar Chart"},
            "xlabel": {"type": "string", "default": "Categories"},
            "ylabel": {"type": "string", "default": "Values"},
            "color": {"type": "string", "default": "auto"},
            "orientation": {"type": "string", "default": "vertical", "enum": ["vertical", "horizontal"]},
            "bar_width": {"type": "number", "default": 0.8},
            "alpha": {"type": "number", "default": 1.0},
            "grid": {"type": "boolean", "default": True},
            "legend": {"type": "boolean", "default": True},
            "stacked": {"type": "boolean", "default": False},
            "grouped": {"type": "boolean", "default": False},
            "show_values": {"type": "boolean", "default": False},
            "value_format": {"type": "string", "default": ".1f"},
            "category_column": {"type": "string", "default": "category"},
            "value_column": {"type": "string", "default": "value"},
            "group_column": {"type": "string", "default": "group"}
        }
    }
    
    async def draw(self, ax: matplotlib.axes.Axes, data: Any) -> None:
        """
        Draw bar chart on the provided axes.
        
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
                raise ValueError("Invalid data format for bar chart")
            
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
            
            self.logger.debug(f"Rendered bar chart with {self._render_count} total renders")
            
        except Exception as e:
            self.logger.error(f"Error drawing bar chart: {e}")
            # Draw error message on axes
            ax.text(0.5, 0.5, f"Error: {str(e)}", 
                   transform=ax.transAxes, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3))
            raise
    
    async def _draw_dataframe(self, ax: matplotlib.axes.Axes, df: pd.DataFrame) -> None:
        """Draw bar chart from pandas DataFrame."""
        cat_col = self.config.get('category_column', 'category')
        val_col = self.config.get('value_column', 'value')
        group_col = self.config.get('group_column', 'group')
        
        # Check if we have grouped data
        if group_col in df.columns and len(df[group_col].unique()) > 1:
            if self.config.get('stacked', False):
                await self._draw_stacked_df(ax, df, cat_col, val_col, group_col)
            else:
                await self._draw_grouped_df(ax, df, cat_col, val_col, group_col)
        else:
            await self._draw_simple_df(ax, df, cat_col, val_col)
    
    async def _draw_simple_df(self, ax: matplotlib.axes.Axes, 
                            df: pd.DataFrame, cat_col: str, val_col: str) -> None:
        """Draw simple bar chart from DataFrame."""
        if cat_col not in df.columns or val_col not in df.columns:
            # Use index as categories if cat_col not found
            categories = df.index if cat_col not in df.columns else df[cat_col]
            values = df[val_col] if val_col in df.columns else df.iloc[:, 0]
        else:
            categories = df[cat_col]
            values = df[val_col]
        
        # Create bar chart
        orientation = self.config.get('orientation', 'vertical')
        color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
        
        if orientation == 'vertical':
            bars = ax.bar(categories, values,
                         width=self.config.get('bar_width', 0.8),
                         alpha=self.config.get('alpha', 1.0),
                         color=color)
        else:
            bars = ax.barh(categories, values,
                          height=self.config.get('bar_width', 0.8),
                          alpha=self.config.get('alpha', 1.0),
                          color=color)
        
        # Show values on bars if requested
        if self.config.get('show_values', False):
            self._add_value_labels(ax, bars, values, orientation)
    
    async def _draw_grouped_df(self, ax: matplotlib.axes.Axes, 
                             df: pd.DataFrame, cat_col: str, val_col: str, group_col: str) -> None:
        """Draw grouped bar chart from DataFrame."""
        categories = df[cat_col].unique()
        groups = df[group_col].unique()
        colors = self.get_color_palette(len(groups))
        
        bar_width = self.config.get('bar_width', 0.8) / len(groups)
        orientation = self.config.get('orientation', 'vertical')
        
        for i, group in enumerate(groups):
            group_data = df[df[group_col] == group]
            
            # Align data with categories
            values = []
            for cat in categories:
                cat_data = group_data[group_data[cat_col] == cat]
                if len(cat_data) > 0:
                    values.append(cat_data[val_col].iloc[0])
                else:
                    values.append(0)
            
            # Calculate positions
            if orientation == 'vertical':
                positions = np.arange(len(categories)) + i * bar_width - (len(groups) - 1) * bar_width / 2
                bars = ax.bar(positions, values,
                             width=bar_width,
                             alpha=self.config.get('alpha', 1.0),
                             color=colors[i],
                             label=str(group))
            else:
                positions = np.arange(len(categories)) + i * bar_width - (len(groups) - 1) * bar_width / 2
                bars = ax.barh(positions, values,
                              height=bar_width,
                              alpha=self.config.get('alpha', 1.0),
                              color=colors[i],
                              label=str(group))
            
            # Show values on bars if requested
            if self.config.get('show_values', False):
                self._add_value_labels(ax, bars, values, orientation)
        
        # Set category labels
        if orientation == 'vertical':
            ax.set_xticks(np.arange(len(categories)))
            ax.set_xticklabels(categories)
        else:
            ax.set_yticks(np.arange(len(categories)))
            ax.set_yticklabels(categories)
    
    async def _draw_stacked_df(self, ax: matplotlib.axes.Axes, 
                             df: pd.DataFrame, cat_col: str, val_col: str, group_col: str) -> None:
        """Draw stacked bar chart from DataFrame."""
        # Pivot data for stacking
        pivot_df = df.pivot_table(index=cat_col, columns=group_col, values=val_col, fill_value=0)
        
        categories = pivot_df.index
        groups = pivot_df.columns
        colors = self.get_color_palette(len(groups))
        
        orientation = self.config.get('orientation', 'vertical')
        bottom = np.zeros(len(categories))
        
        for i, group in enumerate(groups):
            values = pivot_df[group].values
            
            if orientation == 'vertical':
                bars = ax.bar(categories, values,
                             width=self.config.get('bar_width', 0.8),
                             bottom=bottom,
                             alpha=self.config.get('alpha', 1.0),
                             color=colors[i],
                             label=str(group))
            else:
                bars = ax.barh(categories, values,
                              height=self.config.get('bar_width', 0.8),
                              left=bottom,
                              alpha=self.config.get('alpha', 1.0),
                              color=colors[i],
                              label=str(group))
            
            bottom += values
            
            # Show values on bars if requested
            if self.config.get('show_values', False):
                self._add_value_labels(ax, bars, values, orientation)
    
    async def _draw_dict(self, ax: matplotlib.axes.Axes, data: Dict[str, Any]) -> None:
        """Draw bar chart from dictionary data."""
        if 'categories' in data and 'values' in data:
            # Simple category-value data
            categories = data['categories']
            values = data['values']
            
            orientation = self.config.get('orientation', 'vertical')
            color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
            
            if orientation == 'vertical':
                bars = ax.bar(categories, values,
                             width=self.config.get('bar_width', 0.8),
                             alpha=self.config.get('alpha', 1.0),
                             color=color)
            else:
                bars = ax.barh(categories, values,
                              height=self.config.get('bar_width', 0.8),
                              alpha=self.config.get('alpha', 1.0),
                              color=color)
            
            # Show values on bars if requested
            if self.config.get('show_values', False):
                self._add_value_labels(ax, bars, values, orientation)
        
        elif 'groups' in data:
            # Grouped data
            groups_data = data['groups']
            categories = data.get('categories', list(range(len(next(iter(groups_data.values()))))))
            
            colors = self.get_color_palette(len(groups_data))
            bar_width = self.config.get('bar_width', 0.8) / len(groups_data)
            orientation = self.config.get('orientation', 'vertical')
            
            for i, (group_name, values) in enumerate(groups_data.items()):
                if orientation == 'vertical':
                    positions = np.arange(len(categories)) + i * bar_width - (len(groups_data) - 1) * bar_width / 2
                    bars = ax.bar(positions, values,
                                 width=bar_width,
                                 alpha=self.config.get('alpha', 1.0),
                                 color=colors[i],
                                 label=str(group_name))
                else:
                    positions = np.arange(len(categories)) + i * bar_width - (len(groups_data) - 1) * bar_width / 2
                    bars = ax.barh(positions, values,
                                  height=bar_width,
                                  alpha=self.config.get('alpha', 1.0),
                                  color=colors[i],
                                  label=str(group_name))
                
                # Show values on bars if requested
                if self.config.get('show_values', False):
                    self._add_value_labels(ax, bars, values, orientation)
            
            # Set category labels
            if orientation == 'vertical':
                ax.set_xticks(np.arange(len(categories)))
                ax.set_xticklabels(categories)
            else:
                ax.set_yticks(np.arange(len(categories)))
                ax.set_yticklabels(categories)
        else:
            # Assume keys are categories and values are bar heights
            categories = list(data.keys())
            values = list(data.values())
            
            orientation = self.config.get('orientation', 'vertical')
            color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
            
            if orientation == 'vertical':
                bars = ax.bar(categories, values,
                             width=self.config.get('bar_width', 0.8),
                             alpha=self.config.get('alpha', 1.0),
                             color=color)
            else:
                bars = ax.barh(categories, values,
                              height=self.config.get('bar_width', 0.8),
                              alpha=self.config.get('alpha', 1.0),
                              color=color)
            
            # Show values on bars if requested
            if self.config.get('show_values', False):
                self._add_value_labels(ax, bars, values, orientation)
    
    async def _draw_array(self, ax: matplotlib.axes.Axes, data: Union[List, np.ndarray]) -> None:
        """Draw bar chart from array data."""
        data_array = np.array(data)
        
        if data_array.ndim == 1:
            # 1D array - use indices as categories
            categories = np.arange(len(data_array))
            values = data_array
        elif data_array.ndim == 2:
            # 2D array - first column as categories, second as values
            categories = data_array[:, 0] if data_array.shape[1] >= 2 else np.arange(data_array.shape[0])
            values = data_array[:, 1] if data_array.shape[1] >= 2 else data_array[:, 0]
        else:
            raise ValueError("Array data must be 1D or 2D")
        
        orientation = self.config.get('orientation', 'vertical')
        color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
        
        if orientation == 'vertical':
            bars = ax.bar(categories, values,
                         width=self.config.get('bar_width', 0.8),
                         alpha=self.config.get('alpha', 1.0),
                         color=color)
        else:
            bars = ax.barh(categories, values,
                          height=self.config.get('bar_width', 0.8),
                          alpha=self.config.get('alpha', 1.0),
                          color=color)
        
        # Show values on bars if requested
        if self.config.get('show_values', False):
            self._add_value_labels(ax, bars, values, orientation)
    
    def _add_value_labels(self, ax: matplotlib.axes.Axes, bars, values, orientation: str) -> None:
        """Add value labels to bars."""
        value_format = self.config.get('value_format', '.1f')
        
        for bar, value in zip(bars, values):
            if orientation == 'vertical':
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                       f'{value:{value_format}}',
                       ha='center', va='bottom', fontsize=8)
            else:
                width = bar.get_width()
                ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2.,
                       f'{value:{value_format}}',
                       ha='left', va='center', fontsize=8)
