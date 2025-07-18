"""
Unit tests for visualization engine.

Tests the core visualization engine functionality including plugin management,
rendering pipeline, and data integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from edge_device_fleet_manager.visualization.core.engine import VisualizationEngine
from edge_device_fleet_manager.visualization.plugins.base import BaseVisualizer
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer


class MockVisualizer(BaseVisualizer):
    """Mock visualizer for testing."""
    
    name = "Mock Visualizer"
    description = "Test visualizer"
    version = "1.0.0"
    
    async def draw(self, ax, data):
        """Mock draw method."""
        ax.plot([1, 2, 3], [1, 4, 2])
        ax.set_title("Mock Chart")


class TestVisualizationEngine:
    """Test visualization engine functionality."""
    
    @pytest.fixture
    async def engine(self):
        """Create test visualization engine."""
        engine = VisualizationEngine()
        # Mock the plugin manager to avoid entry_points discovery
        engine.plugin_manager.discover_plugins = AsyncMock(return_value={
            'mock': MockVisualizer,
            'line_chart': LineChartVisualizer
        })
        await engine.initialize()
        yield engine
        await engine.shutdown()
    
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
            'category': ['A', 'B', 'A', 'B', 'A']
        })
    
    async def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine._initialized is True
        assert len(engine.registry.list_visualizers()) >= 2
        assert 'mock' in engine.registry.list_visualizers()
        assert 'line_chart' in engine.registry.list_visualizers()
    
    async def test_create_visualization(self, engine, sample_data):
        """Test creating a visualization."""
        viz_id = await engine.create_visualization(
            'mock', sample_data, {'title': 'Test Chart'}
        )
        
        assert viz_id is not None
        assert viz_id in engine._active_visualizations
        
        viz_info = engine.get_visualization_info(viz_id)
        assert viz_info is not None
        assert viz_info['config']['title'] == 'Test Chart'
    
    async def test_create_visualization_invalid_type(self, engine, sample_data):
        """Test creating visualization with invalid type."""
        with pytest.raises(ValueError, match="Unknown visualizer type"):
            await engine.create_visualization('invalid_type', sample_data)
    
    async def test_render_visualization(self, engine, sample_data):
        """Test rendering a visualization."""
        viz_id = await engine.create_visualization('mock', sample_data)
        
        figure = await engine.render_visualization(viz_id)
        
        assert figure is not None
        assert len(figure.axes) > 0
        
        # Check that the mock visualizer was called
        ax = figure.axes[0]
        assert ax.get_title() == "Mock Chart"
    
    async def test_render_visualization_with_custom_figure(self, engine, sample_data):
        """Test rendering with custom figure and axes."""
        viz_id = await engine.create_visualization('mock', sample_data)
        
        fig, ax = plt.subplots()
        result_fig = await engine.render_visualization(viz_id, figure=fig, ax=ax)
        
        assert result_fig is fig
        assert ax.get_title() == "Mock Chart"
    
    async def test_render_nonexistent_visualization(self, engine):
        """Test rendering non-existent visualization."""
        with pytest.raises(ValueError, match="Visualization .* not found"):
            await engine.render_visualization('nonexistent')
    
    async def test_update_visualization(self, engine, sample_data):
        """Test updating a visualization."""
        viz_id = await engine.create_visualization('mock', sample_data)
        
        new_data = {'x': [1, 2], 'y': [3, 4]}
        await engine.update_visualization(viz_id, data_source=new_data)
        
        viz_info = engine.get_visualization_info(viz_id)
        assert viz_info['last_updated'] is not None
    
    async def test_update_visualization_config(self, engine, sample_data):
        """Test updating visualization configuration."""
        viz_id = await engine.create_visualization('mock', sample_data, {'title': 'Original'})
        
        await engine.update_visualization(viz_id, config={'title': 'Updated'})
        
        viz_info = engine.get_visualization_info(viz_id)
        assert viz_info['config']['title'] == 'Updated'
    
    async def test_remove_visualization(self, engine, sample_data):
        """Test removing a visualization."""
        viz_id = await engine.create_visualization('mock', sample_data)
        
        await engine.remove_visualization(viz_id)
        
        assert viz_id not in engine._active_visualizations
        assert engine.get_visualization_info(viz_id) is None
    
    async def test_get_available_visualizers(self, engine):
        """Test getting available visualizers."""
        visualizers = engine.get_available_visualizers()
        
        assert isinstance(visualizers, list)
        assert 'mock' in visualizers
        assert 'line_chart' in visualizers
    
    async def test_engine_statistics(self, engine, sample_data):
        """Test getting engine statistics."""
        # Create some visualizations
        await engine.create_visualization('mock', sample_data)
        await engine.create_visualization('line_chart', sample_data)
        
        stats = engine.get_engine_statistics()
        
        assert stats['active_visualizations'] == 2
        assert stats['available_visualizers'] >= 2
        assert stats['initialized'] is True
    
    async def test_render_callbacks(self, engine, sample_data):
        """Test render callbacks."""
        callback_called = False
        callback_viz_id = None
        callback_figure = None
        
        def render_callback(viz_id, figure):
            nonlocal callback_called, callback_viz_id, callback_figure
            callback_called = True
            callback_viz_id = viz_id
            callback_figure = figure
        
        engine.add_render_callback(render_callback)
        
        viz_id = await engine.create_visualization('mock', sample_data)
        figure = await engine.render_visualization(viz_id)
        
        assert callback_called is True
        assert callback_viz_id == viz_id
        assert callback_figure is figure
    
    async def test_update_callbacks(self, engine, sample_data):
        """Test update callbacks."""
        callback_called = False
        callback_viz_id = None
        
        def update_callback(viz_id):
            nonlocal callback_called, callback_viz_id
            callback_called = True
            callback_viz_id = viz_id
        
        engine.add_update_callback(update_callback)
        
        viz_id = await engine.create_visualization('mock', sample_data)
        await engine.update_visualization(viz_id, config={'title': 'Updated'})
        
        assert callback_called is True
        assert callback_viz_id == viz_id
    
    async def test_async_callbacks(self, engine, sample_data):
        """Test async callbacks."""
        callback_called = False
        
        async def async_callback(viz_id):
            nonlocal callback_called
            callback_called = True
        
        engine.add_update_callback(async_callback)
        
        viz_id = await engine.create_visualization('mock', sample_data)
        await engine.update_visualization(viz_id, config={'title': 'Updated'})
        
        assert callback_called is True
    
    async def test_data_adapter_integration(self, engine):
        """Test data adapter integration."""
        # Mock data adapter
        engine.data_adapter.load_data = AsyncMock(return_value={'x': [1, 2], 'y': [3, 4]})
        
        viz_id = await engine.create_visualization('mock', 'test_source')
        
        # Verify data adapter was called
        engine.data_adapter.load_data.assert_called_once_with('test_source')
        
        # Verify visualization was created
        assert viz_id in engine._active_visualizations
    
    async def test_theme_integration(self, engine, sample_data):
        """Test theme integration."""
        # Mock theme manager
        engine.theme_manager.apply_theme = Mock()
        
        viz_id = await engine.create_visualization('mock', sample_data)
        await engine.render_visualization(viz_id, theme='dark')
        
        # Verify theme was applied
        engine.theme_manager.apply_theme.assert_called_once()
        call_args = engine.theme_manager.apply_theme.call_args
        assert call_args[0][2] == 'dark'  # theme parameter
    
    async def test_performance_tracking(self, engine, sample_data):
        """Test performance tracking."""
        viz_id = await engine.create_visualization('mock', sample_data)
        
        # Render multiple times
        for _ in range(3):
            await engine.render_visualization(viz_id)
        
        stats = engine.get_engine_statistics()
        assert stats['total_renders'] == 3
        assert stats['average_render_time_seconds'] >= 0
    
    async def test_error_handling_in_render(self, engine):
        """Test error handling during rendering."""
        # Create a visualizer that raises an error
        class ErrorVisualizer(BaseVisualizer):
            name = "Error Visualizer"
            
            async def draw(self, ax, data):
                raise ValueError("Test error")
        
        engine.registry.register('error', ErrorVisualizer)
        
        viz_id = await engine.create_visualization('error', {})
        
        with pytest.raises(ValueError, match="Test error"):
            await engine.render_visualization(viz_id)
    
    async def test_multiple_visualizations(self, engine, sample_data):
        """Test managing multiple visualizations."""
        viz_ids = []
        
        # Create multiple visualizations
        for i in range(5):
            viz_id = await engine.create_visualization(
                'mock', sample_data, {'title': f'Chart {i}'}
            )
            viz_ids.append(viz_id)
        
        # Verify all were created
        assert len(engine._active_visualizations) == 5
        
        # Remove some
        for viz_id in viz_ids[:2]:
            await engine.remove_visualization(viz_id)
        
        # Verify removal
        assert len(engine._active_visualizations) == 3
    
    async def test_concurrent_operations(self, engine, sample_data):
        """Test concurrent visualization operations."""
        # Create multiple visualizations concurrently
        tasks = []
        for i in range(10):
            task = engine.create_visualization(
                'mock', sample_data, {'title': f'Chart {i}'}
            )
            tasks.append(task)
        
        viz_ids = await asyncio.gather(*tasks)
        
        # Verify all were created
        assert len(viz_ids) == 10
        assert len(engine._active_visualizations) == 10
        
        # Render all concurrently
        render_tasks = [engine.render_visualization(viz_id) for viz_id in viz_ids]
        figures = await asyncio.gather(*render_tasks)
        
        # Verify all were rendered
        assert len(figures) == 10
        assert all(fig is not None for fig in figures)
