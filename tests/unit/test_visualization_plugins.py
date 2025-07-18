"""
Unit tests for visualization plugins.

Tests the built-in visualizer plugins including line charts, bar charts,
time series, and gauge visualizers.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import matplotlib.pyplot as plt
import matplotlib.axes
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from edge_device_fleet_manager.visualization.plugins.base import BaseVisualizer
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer
from edge_device_fleet_manager.visualization.plugins.bar_chart import BarChartVisualizer
from edge_device_fleet_manager.visualization.plugins.time_series import TimeSeriesVisualizer
from edge_device_fleet_manager.visualization.plugins.gauge import GaugeVisualizer


class TestBaseVisualizer:
    """Test base visualizer functionality."""
    
    def test_base_visualizer_abstract(self):
        """Test that BaseVisualizer is abstract."""
        with pytest.raises(TypeError):
            BaseVisualizer()
    
    def test_config_merging(self):
        """Test configuration merging with defaults."""
        class TestVisualizer(BaseVisualizer):
            config_schema = {
                "properties": {
                    "title": {"default": "Default Title"},
                    "color": {"default": "blue"}
                }
            }
            
            async def draw(self, ax, data):
                pass
        
        # Test with no config
        viz = TestVisualizer()
        assert viz.config['title'] == "Default Title"
        assert viz.config['color'] == "blue"
        
        # Test with partial config
        viz = TestVisualizer({'title': 'Custom Title'})
        assert viz.config['title'] == "Custom Title"
        assert viz.config['color'] == "blue"
    
    def test_update_config(self):
        """Test configuration updates."""
        class TestVisualizer(BaseVisualizer):
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer({'title': 'Original'})
        viz.update_config({'title': 'Updated', 'color': 'red'})
        
        assert viz.config['title'] == 'Updated'
        assert viz.config['color'] == 'red'
    
    def test_data_validation(self):
        """Test data validation."""
        class TestVisualizer(BaseVisualizer):
            supported_data_types = ['dict', 'list']
            
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        
        # Valid data types
        assert viz.validate_data({'x': [1, 2], 'y': [3, 4]}) is True
        assert viz.validate_data([1, 2, 3]) is True
        
        # Invalid data type (string not in supported types)
        assert viz.validate_data("invalid") is False
    
    def test_color_palette(self):
        """Test color palette generation."""
        class TestVisualizer(BaseVisualizer):
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        
        # Test auto colors
        colors = viz.get_color_palette(5)
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
        
        # Test custom color
        viz = TestVisualizer({'color': 'red'})
        colors = viz.get_color_palette(3)
        assert all(color == 'red' for color in colors)
    
    def test_statistics(self):
        """Test visualizer statistics."""
        class TestVisualizer(BaseVisualizer):
            name = "Test"
            version = "1.0.0"
            
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        stats = viz.get_statistics()
        
        assert stats['name'] == "Test"
        assert stats['version'] == "1.0.0"
        assert stats['render_count'] == 0
        assert stats['supports_real_time'] is False


class TestLineChartVisualizer:
    """Test line chart visualizer."""
    
    @pytest.fixture
    def visualizer(self):
        """Create line chart visualizer."""
        return LineChartVisualizer()
    
    @pytest.fixture
    def ax(self):
        """Create matplotlib axes."""
        fig, ax = plt.subplots()
        return ax
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 1, 5, 3]
        }
    
    @pytest.fixture
    def sample_dataframe(self):
        """Sample DataFrame for testing."""
        return pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 1, 5, 3],
            'series': ['A', 'A', 'B', 'B', 'A']
        })
    
    async def test_draw_dict_data(self, visualizer, ax, sample_data):
        """Test drawing with dictionary data."""
        await visualizer.draw(ax, sample_data)
        
        # Check that line was plotted
        assert len(ax.lines) == 1
        line = ax.lines[0]
        
        # Check data
        x_data, y_data = line.get_data()
        np.testing.assert_array_equal(x_data, [1, 2, 3, 4, 5])
        np.testing.assert_array_equal(y_data, [2, 4, 1, 5, 3])
    
    async def test_draw_dataframe_single_series(self, visualizer, ax, sample_dataframe):
        """Test drawing DataFrame with single series."""
        # Remove series column to test single series
        df = sample_dataframe.drop('series', axis=1)
        await visualizer.draw(ax, df)
        
        assert len(ax.lines) == 1
    
    async def test_draw_dataframe_multiple_series(self, visualizer, ax, sample_dataframe):
        """Test drawing DataFrame with multiple series."""
        await visualizer.draw(ax, sample_dataframe)
        
        # Should have multiple lines for different series
        assert len(ax.lines) >= 1
    
    async def test_draw_array_data(self, visualizer, ax):
        """Test drawing with array data."""
        data = np.array([[1, 2], [2, 4], [3, 1], [4, 5], [5, 3]])
        await visualizer.draw(ax, data)
        
        assert len(ax.lines) == 1
    
    async def test_draw_1d_array(self, visualizer, ax):
        """Test drawing with 1D array."""
        data = np.array([2, 4, 1, 5, 3])
        await visualizer.draw(ax, data)
        
        assert len(ax.lines) == 1
        line = ax.lines[0]
        x_data, y_data = line.get_data()
        np.testing.assert_array_equal(y_data, [2, 4, 1, 5, 3])
    
    async def test_multiple_series_dict(self, visualizer, ax):
        """Test drawing multiple series from dictionary."""
        data = {
            'series': {
                'Series A': {'x': [1, 2, 3], 'y': [1, 2, 3]},
                'Series B': {'x': [1, 2, 3], 'y': [3, 2, 1]}
            }
        }
        await visualizer.draw(ax, data)
        
        assert len(ax.lines) == 2
    
    async def test_smoothing(self, visualizer, ax, sample_data):
        """Test data smoothing."""
        visualizer.update_config({'smooth': True})
        await visualizer.draw(ax, sample_data)
        
        assert len(ax.lines) == 1
    
    async def test_fill_area(self, visualizer, ax, sample_data):
        """Test area filling."""
        visualizer.update_config({'fill_area': True})
        await visualizer.draw(ax, sample_data)
        
        assert len(ax.lines) == 1
        assert len(ax.collections) > 0  # Fill creates collections
    
    async def test_styling_application(self, visualizer, ax, sample_data):
        """Test styling application."""
        visualizer.update_config({
            'title': 'Test Chart',
            'xlabel': 'X Axis',
            'ylabel': 'Y Axis',
            'line_style': '--',
            'line_width': 3.0
        })
        
        await visualizer.draw(ax, sample_data)
        
        assert ax.get_title() == 'Test Chart'
        assert ax.get_xlabel() == 'X Axis'
        assert ax.get_ylabel() == 'Y Axis'
        
        line = ax.lines[0]
        assert line.get_linestyle() == '--'
        assert line.get_linewidth() == 3.0
    
    async def test_invalid_data(self, visualizer, ax):
        """Test handling of invalid data."""
        with pytest.raises(ValueError):
            await visualizer.draw(ax, "invalid_data")
    
    async def test_render_count_tracking(self, visualizer, ax, sample_data):
        """Test render count tracking."""
        initial_count = visualizer._render_count
        
        await visualizer.draw(ax, sample_data)
        
        assert visualizer._render_count == initial_count + 1
        assert visualizer._last_render_time is not None


class TestBarChartVisualizer:
    """Test bar chart visualizer."""
    
    @pytest.fixture
    def visualizer(self):
        """Create bar chart visualizer."""
        return BarChartVisualizer()
    
    @pytest.fixture
    def ax(self):
        """Create matplotlib axes."""
        fig, ax = plt.subplots()
        return ax
    
    async def test_draw_simple_dict(self, visualizer, ax):
        """Test drawing simple dictionary data."""
        data = {'A': 10, 'B': 20, 'C': 15}
        await visualizer.draw(ax, data)
        
        # Check that bars were created
        assert len(ax.patches) == 3
    
    async def test_draw_categories_values(self, visualizer, ax):
        """Test drawing with categories and values."""
        data = {
            'categories': ['A', 'B', 'C'],
            'values': [10, 20, 15]
        }
        await visualizer.draw(ax, data)
        
        assert len(ax.patches) == 3
    
    async def test_horizontal_bars(self, visualizer, ax):
        """Test horizontal bar chart."""
        visualizer.update_config({'orientation': 'horizontal'})
        data = {'A': 10, 'B': 20, 'C': 15}
        await visualizer.draw(ax, data)
        
        assert len(ax.patches) == 3
    
    async def test_grouped_bars(self, visualizer, ax):
        """Test grouped bar chart."""
        data = {
            'groups': {
                'Group 1': [10, 20, 15],
                'Group 2': [12, 18, 17]
            },
            'categories': ['A', 'B', 'C']
        }
        await visualizer.draw(ax, data)
        
        # Should have bars for both groups
        assert len(ax.patches) == 6
    
    async def test_show_values(self, visualizer, ax):
        """Test showing values on bars."""
        visualizer.update_config({'show_values': True})
        data = {'A': 10, 'B': 20, 'C': 15}
        await visualizer.draw(ax, data)
        
        # Check that text annotations were added
        assert len(ax.texts) >= 3
    
    async def test_dataframe_input(self, visualizer, ax):
        """Test DataFrame input."""
        df = pd.DataFrame({
            'category': ['A', 'B', 'C'],
            'value': [10, 20, 15]
        })
        await visualizer.draw(ax, df)
        
        assert len(ax.patches) == 3


class TestTimeSeriesVisualizer:
    """Test time series visualizer."""
    
    @pytest.fixture
    def visualizer(self):
        """Create time series visualizer."""
        return TimeSeriesVisualizer()
    
    @pytest.fixture
    def ax(self):
        """Create matplotlib axes."""
        fig, ax = plt.subplots()
        return ax
    
    @pytest.fixture
    def time_data(self):
        """Sample time series data."""
        timestamps = pd.date_range('2024-01-01', periods=10, freq='1H')
        return {
            'timestamps': timestamps,
            'values': [1, 2, 3, 2, 4, 3, 5, 4, 6, 5]
        }
    
    async def test_draw_time_series(self, visualizer, ax, time_data):
        """Test drawing time series data."""
        await visualizer.draw(ax, time_data)
        
        assert len(ax.lines) == 1
    
    async def test_multiple_metrics(self, visualizer, ax):
        """Test multiple metrics time series."""
        timestamps = pd.date_range('2024-01-01', periods=5, freq='1H')
        data = {
            'metrics': {
                'Temperature': {
                    'timestamps': timestamps,
                    'values': [20, 21, 22, 21, 20]
                },
                'Humidity': {
                    'timestamps': timestamps,
                    'values': [60, 65, 70, 65, 60]
                }
            }
        }
        await visualizer.draw(ax, data)
        
        assert len(ax.lines) == 2
    
    async def test_dataframe_input(self, visualizer, ax):
        """Test DataFrame input."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1H'),
            'value': [1, 2, 3, 2, 1],
            'metric': ['temp', 'temp', 'temp', 'temp', 'temp']
        })
        await visualizer.draw(ax, df)
        
        assert len(ax.lines) == 1
    
    async def test_rolling_window(self, visualizer, ax, time_data):
        """Test rolling window smoothing."""
        visualizer.update_config({'rolling_window': 3})
        await visualizer.draw(ax, time_data)
        
        assert len(ax.lines) == 1
    
    async def test_anomaly_detection(self, visualizer, ax, time_data):
        """Test anomaly detection."""
        visualizer.update_config({'show_anomalies': True})
        await visualizer.draw(ax, time_data)
        
        # Should have line and possibly scatter points for anomalies
        assert len(ax.lines) >= 1


class TestGaugeVisualizer:
    """Test gauge visualizer."""
    
    @pytest.fixture
    def visualizer(self):
        """Create gauge visualizer."""
        return GaugeVisualizer()
    
    @pytest.fixture
    def ax(self):
        """Create matplotlib axes."""
        fig, ax = plt.subplots()
        return ax
    
    async def test_draw_simple_value(self, visualizer, ax):
        """Test drawing with simple numeric value."""
        await visualizer.draw(ax, 75)
        
        # Check that patches were added (gauge components)
        assert len(ax.patches) > 0
    
    async def test_draw_dict_value(self, visualizer, ax):
        """Test drawing with dictionary value."""
        data = {'value': 85, 'units': '%'}
        visualizer.update_config({'units': '%'})
        await visualizer.draw(ax, data)
        
        assert len(ax.patches) > 0
    
    async def test_gauge_types(self, visualizer, ax):
        """Test different gauge types."""
        for gauge_type in ['full', 'semi', 'quarter']:
            visualizer.update_config({'gauge_type': gauge_type})
            await visualizer.draw(ax, 50)
            
            assert len(ax.patches) > 0
            ax.clear()
    
    async def test_color_zones(self, visualizer, ax):
        """Test color zones."""
        visualizer.update_config({
            'color_zones': [
                {'min': 0, 'max': 30, 'color': 'green'},
                {'min': 30, 'max': 70, 'color': 'yellow'},
                {'min': 70, 'max': 100, 'color': 'red'}
            ]
        })
        await visualizer.draw(ax, 50)
        
        assert len(ax.patches) > 0
    
    async def test_value_display(self, visualizer, ax):
        """Test value display."""
        visualizer.update_config({'show_value': True, 'units': 'RPM'})
        await visualizer.draw(ax, 1500)
        
        # Should have text for value display
        assert len(ax.texts) > 0
    
    async def test_out_of_range_value(self, visualizer, ax):
        """Test handling out-of-range values."""
        # This should not raise an error, just log a warning
        await visualizer.draw(ax, 150)  # Above max_value of 100
        
        assert len(ax.patches) > 0
    
    async def test_invalid_data_type(self, visualizer, ax):
        """Test invalid data type handling."""
        with pytest.raises(ValueError):
            await visualizer.draw(ax, "invalid")
