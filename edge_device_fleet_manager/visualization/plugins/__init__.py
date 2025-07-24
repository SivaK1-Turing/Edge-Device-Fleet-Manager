"""
Visualization Plugins

Built-in visualizer plugins for the Edge Device Fleet Manager.
Each plugin implements the draw(ax, data) interface defined by BaseVisualizer.
"""

from .base import BaseVisualizer
from .line_chart import LineChartVisualizer
from .bar_chart import BarChartVisualizer
from .time_series import TimeSeriesVisualizer
from .gauge import GaugeVisualizer

# Import additional plugins
try:
    from .scatter_plot import ScatterPlotVisualizer
except ImportError:
    ScatterPlotVisualizer = None

try:
    from .heatmap import HeatmapVisualizer
except ImportError:
    HeatmapVisualizer = None

try:
    from .histogram import HistogramVisualizer
except ImportError:
    HistogramVisualizer = None

try:
    from .pie_chart import PieChartVisualizer
except ImportError:
    PieChartVisualizer = None

# Export all available plugins
__all__ = [
    'BaseVisualizer',
    'LineChartVisualizer',
    'BarChartVisualizer', 
    'TimeSeriesVisualizer',
    'GaugeVisualizer',
]

# Add optional plugins if available
if ScatterPlotVisualizer:
    __all__.append('ScatterPlotVisualizer')

if HeatmapVisualizer:
    __all__.append('HeatmapVisualizer')

if HistogramVisualizer:
    __all__.append('HistogramVisualizer')

if PieChartVisualizer:
    __all__.append('PieChartVisualizer')

# Plugin metadata for discovery
BUILTIN_PLUGINS = {
    'line_chart': LineChartVisualizer,
    'bar_chart': BarChartVisualizer,
    'time_series': TimeSeriesVisualizer,
    'gauge': GaugeVisualizer,
}

# Add optional plugins
if ScatterPlotVisualizer:
    BUILTIN_PLUGINS['scatter_plot'] = ScatterPlotVisualizer

if HeatmapVisualizer:
    BUILTIN_PLUGINS['heatmap'] = HeatmapVisualizer

if HistogramVisualizer:
    BUILTIN_PLUGINS['histogram'] = HistogramVisualizer

if PieChartVisualizer:
    BUILTIN_PLUGINS['pie_chart'] = PieChartVisualizer
