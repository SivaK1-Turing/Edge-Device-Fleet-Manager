"""
Gauge Visualizer

Plugin for creating gauge/dial charts for displaying single values
with thresholds, ranges, and visual indicators.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.axes
import matplotlib.patches as patches
import numpy as np

from .base import BaseVisualizer


class GaugeVisualizer(BaseVisualizer):
    """
    Gauge visualizer plugin.
    
    Creates circular or semi-circular gauge charts for displaying
    single values with customizable ranges, thresholds, and styling.
    """
    
    name = "Gauge"
    description = "Gauge/dial chart visualizer for single value display"
    version = "1.0.0"
    
    supports_real_time = True
    supports_interaction = False
    supported_data_types = ['dict', 'float', 'int']
    
    config_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Gauge"},
            "min_value": {"type": "number", "default": 0},
            "max_value": {"type": "number", "default": 100},
            "value": {"type": "number", "default": 50},
            "units": {"type": "string", "default": ""},
            "gauge_type": {"type": "string", "default": "semi", "enum": ["full", "semi", "quarter"]},
            "color_zones": {"type": "array", "default": []},
            "needle_color": {"type": "string", "default": "black"},
            "background_color": {"type": "string", "default": "lightgray"},
            "show_value": {"type": "boolean", "default": True},
            "show_range": {"type": "boolean", "default": True},
            "show_ticks": {"type": "boolean", "default": True},
            "tick_count": {"type": "number", "default": 10},
            "precision": {"type": "number", "default": 1},
            "thresholds": {"type": "array", "default": []},
            "warning_threshold": {"type": "number", "default": 80},
            "critical_threshold": {"type": "number", "default": 90}
        }
    }
    
    async def draw(self, ax: matplotlib.axes.Axes, data: Any) -> None:
        """
        Draw gauge chart on the provided axes.
        
        Args:
            ax: Matplotlib axes to draw on
            data: Value or data dictionary to display
        """
        try:
            # Update render statistics
            self._render_count += 1
            self._last_render_time = datetime.now(timezone.utc)
            
            # Extract value from data
            value = self._extract_value(data)
            
            # Validate value
            min_val = self.config.get('min_value', 0)
            max_val = self.config.get('max_value', 100)
            
            if value < min_val or value > max_val:
                self.logger.warning(f"Value {value} outside range [{min_val}, {max_val}]")
            
            # Clear axes and set equal aspect ratio
            ax.clear()
            ax.set_aspect('equal')
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-1.2, 1.2)
            ax.axis('off')
            
            # Draw gauge components
            await self._draw_gauge_background(ax)
            await self._draw_color_zones(ax)
            await self._draw_ticks(ax)
            await self._draw_needle(ax, value)
            await self._draw_center_circle(ax)
            await self._draw_value_text(ax, value)
            await self._draw_title(ax)
            
            self.logger.debug(f"Rendered gauge with value {value}")
            
        except Exception as e:
            self.logger.error(f"Error drawing gauge: {e}")
            # Draw error message
            ax.text(0, 0, f"Error: {str(e)}", 
                   transform=ax.transData, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3))
            raise
    
    def _extract_value(self, data: Any) -> float:
        """Extract numeric value from data."""
        if isinstance(data, (int, float)):
            return float(data)
        elif isinstance(data, dict):
            if 'value' in data:
                return float(data['value'])
            elif 'current' in data:
                return float(data['current'])
            elif len(data) == 1:
                return float(list(data.values())[0])
            else:
                raise ValueError("Dictionary must contain 'value' or 'current' key")
        else:
            raise ValueError(f"Unsupported data type for gauge: {type(data)}")
    
    async def _draw_gauge_background(self, ax: matplotlib.axes.Axes) -> None:
        """Draw the gauge background arc."""
        gauge_type = self.config.get('gauge_type', 'semi')
        background_color = self.config.get('background_color', 'lightgray')
        
        if gauge_type == 'full':
            # Full circle
            start_angle = 0
            end_angle = 360
        elif gauge_type == 'semi':
            # Semi-circle
            start_angle = 180
            end_angle = 0
        elif gauge_type == 'quarter':
            # Quarter circle
            start_angle = 180
            end_angle = 90
        else:
            start_angle = 180
            end_angle = 0
        
        # Draw background arc
        wedge = patches.Wedge((0, 0), 1.0, start_angle, end_angle,
                             width=0.2, facecolor=background_color,
                             edgecolor='gray', linewidth=1)
        ax.add_patch(wedge)
    
    async def _draw_color_zones(self, ax: matplotlib.axes.Axes) -> None:
        """Draw colored zones on the gauge."""
        color_zones = self.config.get('color_zones', [])
        gauge_type = self.config.get('gauge_type', 'semi')
        min_val = self.config.get('min_value', 0)
        max_val = self.config.get('max_value', 100)
        
        # Default color zones if none specified
        if not color_zones:
            warning_threshold = self.config.get('warning_threshold', 80)
            critical_threshold = self.config.get('critical_threshold', 90)
            
            color_zones = [
                {'min': min_val, 'max': warning_threshold, 'color': 'green'},
                {'min': warning_threshold, 'max': critical_threshold, 'color': 'yellow'},
                {'min': critical_threshold, 'max': max_val, 'color': 'red'}
            ]
        
        # Calculate angle range
        if gauge_type == 'full':
            total_angle = 360
            start_angle = 0
        elif gauge_type == 'semi':
            total_angle = 180
            start_angle = 180
        elif gauge_type == 'quarter':
            total_angle = 90
            start_angle = 180
        else:
            total_angle = 180
            start_angle = 180
        
        # Draw each color zone
        for zone in color_zones:
            zone_min = zone.get('min', min_val)
            zone_max = zone.get('max', max_val)
            zone_color = zone.get('color', 'gray')
            
            # Calculate angles for this zone
            zone_start_ratio = (zone_min - min_val) / (max_val - min_val)
            zone_end_ratio = (zone_max - min_val) / (max_val - min_val)
            
            zone_start_angle = start_angle - zone_start_ratio * total_angle
            zone_end_angle = start_angle - zone_end_ratio * total_angle
            
            # Draw zone arc
            wedge = patches.Wedge((0, 0), 1.0, zone_end_angle, zone_start_angle,
                                 width=0.2, facecolor=zone_color,
                                 alpha=0.7, edgecolor='white', linewidth=0.5)
            ax.add_patch(wedge)
    
    async def _draw_ticks(self, ax: matplotlib.axes.Axes) -> None:
        """Draw tick marks and labels on the gauge."""
        if not self.config.get('show_ticks', True):
            return
        
        gauge_type = self.config.get('gauge_type', 'semi')
        min_val = self.config.get('min_value', 0)
        max_val = self.config.get('max_value', 100)
        tick_count = self.config.get('tick_count', 10)
        
        # Calculate angle range
        if gauge_type == 'full':
            total_angle = 360
            start_angle = 0
        elif gauge_type == 'semi':
            total_angle = 180
            start_angle = 180
        elif gauge_type == 'quarter':
            total_angle = 90
            start_angle = 180
        else:
            total_angle = 180
            start_angle = 180
        
        # Draw ticks
        for i in range(tick_count + 1):
            ratio = i / tick_count
            angle_deg = start_angle - ratio * total_angle
            angle_rad = np.radians(angle_deg)
            
            # Tick positions
            inner_radius = 0.8
            outer_radius = 0.9
            label_radius = 0.7
            
            # Calculate positions
            x_inner = inner_radius * np.cos(angle_rad)
            y_inner = inner_radius * np.sin(angle_rad)
            x_outer = outer_radius * np.cos(angle_rad)
            y_outer = outer_radius * np.sin(angle_rad)
            x_label = label_radius * np.cos(angle_rad)
            y_label = label_radius * np.sin(angle_rad)
            
            # Draw tick line
            ax.plot([x_inner, x_outer], [y_inner, y_outer], 
                   color='black', linewidth=1)
            
            # Draw tick label
            if self.config.get('show_range', True):
                tick_value = min_val + ratio * (max_val - min_val)
                precision = self.config.get('precision', 1)
                label = f"{tick_value:.{precision}f}"
                
                ax.text(x_label, y_label, label, 
                       ha='center', va='center', fontsize=8,
                       bbox=dict(boxstyle="round,pad=0.1", 
                               facecolor="white", alpha=0.8))
    
    async def _draw_needle(self, ax: matplotlib.axes.Axes, value: float) -> None:
        """Draw the gauge needle pointing to the current value."""
        gauge_type = self.config.get('gauge_type', 'semi')
        min_val = self.config.get('min_value', 0)
        max_val = self.config.get('max_value', 100)
        needle_color = self.config.get('needle_color', 'black')
        
        # Calculate needle angle
        value_ratio = (value - min_val) / (max_val - min_val)
        value_ratio = max(0, min(1, value_ratio))  # Clamp to [0, 1]
        
        if gauge_type == 'full':
            total_angle = 360
            start_angle = 0
        elif gauge_type == 'semi':
            total_angle = 180
            start_angle = 180
        elif gauge_type == 'quarter':
            total_angle = 90
            start_angle = 180
        else:
            total_angle = 180
            start_angle = 180
        
        needle_angle_deg = start_angle - value_ratio * total_angle
        needle_angle_rad = np.radians(needle_angle_deg)
        
        # Needle dimensions
        needle_length = 0.75
        needle_width = 0.02
        
        # Calculate needle tip position
        tip_x = needle_length * np.cos(needle_angle_rad)
        tip_y = needle_length * np.sin(needle_angle_rad)
        
        # Draw needle as a line with arrow
        ax.annotate('', xy=(tip_x, tip_y), xytext=(0, 0),
                   arrowprops=dict(arrowstyle='->', color=needle_color, 
                                 lw=3, shrinkA=0, shrinkB=0))
    
    async def _draw_center_circle(self, ax: matplotlib.axes.Axes) -> None:
        """Draw the center circle of the gauge."""
        center_circle = patches.Circle((0, 0), 0.05, 
                                     facecolor='black', 
                                     edgecolor='gray', 
                                     linewidth=1)
        ax.add_patch(center_circle)
    
    async def _draw_value_text(self, ax: matplotlib.axes.Axes, value: float) -> None:
        """Draw the current value as text."""
        if not self.config.get('show_value', True):
            return
        
        precision = self.config.get('precision', 1)
        units = self.config.get('units', '')
        
        value_text = f"{value:.{precision}f}"
        if units:
            value_text += f" {units}"
        
        # Position text below center
        ax.text(0, -0.3, value_text, 
               ha='center', va='center', fontsize=14, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", 
                       facecolor="white", alpha=0.9, edgecolor='gray'))
    
    async def _draw_title(self, ax: matplotlib.axes.Axes) -> None:
        """Draw the gauge title."""
        title = self.config.get('title', '')
        if title:
            # Position title above the gauge
            y_pos = 0.5 if self.config.get('gauge_type', 'semi') == 'semi' else 1.1
            ax.text(0, y_pos, title, 
                   ha='center', va='center', fontsize=12, fontweight='bold')
