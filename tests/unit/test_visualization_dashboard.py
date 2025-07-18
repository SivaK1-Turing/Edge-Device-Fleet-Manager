"""
Unit tests for visualization dashboard.

Tests the dashboard framework including layout management,
visualization composition, and real-time updates.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import matplotlib.pyplot as plt

from edge_device_fleet_manager.visualization.core.dashboard import Dashboard, DashboardLayout
from edge_device_fleet_manager.visualization.core.engine import VisualizationEngine
from edge_device_fleet_manager.visualization.plugins.base import BaseVisualizer


class MockVisualizer(BaseVisualizer):
    """Mock visualizer for testing."""
    
    name = "Mock Visualizer"
    description = "Test visualizer"
    version = "1.0.0"
    
    async def draw(self, ax, data):
        """Mock draw method."""
        ax.plot([1, 2, 3], [1, 4, 2])
        ax.set_title(f"Mock Chart - {data.get('title', 'Default')}")


class TestDashboardLayout:
    """Test dashboard layout functionality."""
    
    def test_grid_layout_creation(self):
        """Test grid layout creation."""
        layout = DashboardLayout('grid', columns=2)
        assert layout.layout_type == 'grid'
        assert layout.config['columns'] == 2
    
    def test_grid_layout_single_viz(self):
        """Test grid layout with single visualization."""
        layout = DashboardLayout('grid')
        positions = layout.calculate_positions(1)
        
        assert len(positions) == 1
        assert 'viz_0' in positions
        assert positions['viz_0']['row'] == 0
        assert positions['viz_0']['col'] == 0
    
    def test_grid_layout_multiple_viz(self):
        """Test grid layout with multiple visualizations."""
        layout = DashboardLayout('grid')
        positions = layout.calculate_positions(4)
        
        assert len(positions) == 4
        # Should create 2x2 grid
        assert positions['viz_0']['grid_rows'] == 2
        assert positions['viz_0']['grid_cols'] == 2
    
    def test_grid_layout_custom_columns(self):
        """Test grid layout with custom columns."""
        layout = DashboardLayout('grid', columns=3)
        positions = layout.calculate_positions(5)
        
        assert len(positions) == 5
        # Should use 3 columns
        assert positions['viz_0']['grid_cols'] == 3
        assert positions['viz_0']['grid_rows'] == 2  # 5 items in 3 columns = 2 rows
    
    def test_flow_layout(self):
        """Test flow layout."""
        layout = DashboardLayout('flow', items_per_row=2)
        positions = layout.calculate_positions(5)
        
        assert len(positions) == 5
        # First row should have 2 items
        assert positions['viz_0']['row'] == 0
        assert positions['viz_1']['row'] == 0
        # Third item should be on second row
        assert positions['viz_2']['row'] == 1
    
    def test_custom_layout(self):
        """Test custom layout."""
        custom_positions = {
            'viz_0': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1},
            'viz_1': {'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1},
            'viz_2': {'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1}
        }
        
        layout = DashboardLayout('custom', 
                                positions=custom_positions,
                                total_rows=2, 
                                total_cols=2)
        positions = layout.calculate_positions(3)
        
        assert len(positions) == 3
        assert positions['viz_0']['rowspan'] == 2
        assert positions['viz_0']['colspan'] == 1


class TestDashboard:
    """Test dashboard functionality."""
    
    @pytest.fixture
    async def mock_engine(self):
        """Create mock visualization engine."""
        engine = Mock(spec=VisualizationEngine)
        engine._initialized = True
        engine.create_visualization = AsyncMock(return_value='mock_viz_id')
        engine.remove_visualization = AsyncMock()
        engine.update_visualization = AsyncMock()
        engine.render_visualization = AsyncMock(return_value=plt.figure())
        engine.get_visualization_info = Mock(return_value={'config': {}})
        engine.get_engine_statistics = Mock(return_value={'active_visualizations': 0})
        engine.shutdown = AsyncMock()
        return engine
    
    @pytest.fixture
    async def dashboard(self, mock_engine):
        """Create test dashboard."""
        layout = DashboardLayout('grid')
        dashboard = Dashboard(layout, mock_engine)
        await dashboard.initialize()
        yield dashboard
        await dashboard.shutdown()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {'title': 'Test Data', 'values': [1, 2, 3, 4, 5]}
    
    async def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.engine._initialized is True
        assert len(dashboard.visualizations) == 0
    
    async def test_add_visualization(self, dashboard, sample_data):
        """Test adding visualization to dashboard."""
        success = await dashboard.add_visualization(
            'test_viz', 'mock', sample_data, {'title': 'Test Chart'}
        )
        
        assert success is True
        assert 'test_viz' in dashboard.visualizations
        assert dashboard.visualizations['test_viz']['visualizer_type'] == 'mock'
        
        # Verify engine was called
        dashboard.engine.create_visualization.assert_called_once_with(
            'mock', sample_data, {'title': 'Test Chart'}
        )
    
    async def test_add_multiple_visualizations(self, dashboard, sample_data):
        """Test adding multiple visualizations."""
        viz_ids = ['viz1', 'viz2', 'viz3']
        
        for viz_id in viz_ids:
            success = await dashboard.add_visualization(
                viz_id, 'mock', sample_data
            )
            assert success is True
        
        assert len(dashboard.visualizations) == 3
        assert all(viz_id in dashboard.visualizations for viz_id in viz_ids)
    
    async def test_remove_visualization(self, dashboard, sample_data):
        """Test removing visualization from dashboard."""
        # Add visualization first
        await dashboard.add_visualization('test_viz', 'mock', sample_data)
        
        # Remove it
        success = await dashboard.remove_visualization('test_viz')
        
        assert success is True
        assert 'test_viz' not in dashboard.visualizations
        
        # Verify engine was called
        dashboard.engine.remove_visualization.assert_called_once()
    
    async def test_remove_nonexistent_visualization(self, dashboard):
        """Test removing non-existent visualization."""
        success = await dashboard.remove_visualization('nonexistent')
        
        assert success is False
    
    async def test_update_visualization(self, dashboard, sample_data):
        """Test updating visualization."""
        # Add visualization first
        await dashboard.add_visualization('test_viz', 'mock', sample_data)
        
        # Update it
        new_data = {'title': 'Updated Data'}
        success = await dashboard.update_visualization('test_viz', new_data)
        
        assert success is True
        
        # Verify engine was called
        dashboard.engine.update_visualization.assert_called_once()
    
    async def test_render_empty_dashboard(self, dashboard):
        """Test rendering empty dashboard."""
        figure = await dashboard.render()
        
        assert figure is not None
        assert len(figure.axes) == 1  # Should have one axis with "No visualizations" message
    
    async def test_render_dashboard_with_visualizations(self, dashboard, sample_data):
        """Test rendering dashboard with visualizations."""
        # Add some visualizations
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        await dashboard.add_visualization('viz2', 'mock', sample_data)
        
        figure = await dashboard.render()
        
        assert figure is not None
        # Should have called render for each visualization
        assert dashboard.engine.render_visualization.call_count == 2
    
    async def test_render_with_custom_figure_size(self, dashboard, sample_data):
        """Test rendering with custom figure size."""
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        
        figure = await dashboard.render(figure_size=(20, 15))
        
        assert figure is not None
        assert figure.get_size_inches()[0] == 20
        assert figure.get_size_inches()[1] == 15
    
    async def test_auto_refresh_start_stop(self, dashboard, sample_data):
        """Test auto-refresh functionality."""
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        
        # Start auto-refresh
        await dashboard.start_auto_refresh(interval_seconds=1)
        
        assert dashboard.auto_refresh is True
        assert dashboard.refresh_interval == 1
        assert dashboard._refresh_task is not None
        
        # Wait a bit to ensure refresh happens
        await asyncio.sleep(0.1)
        
        # Stop auto-refresh
        await dashboard.stop_auto_refresh()
        
        assert dashboard.auto_refresh is False
        assert dashboard._refresh_task.done()
    
    async def test_manual_refresh(self, dashboard, sample_data):
        """Test manual refresh."""
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        
        # Reset mock call count
        dashboard.engine.update_visualization.reset_mock()
        
        await dashboard.refresh()
        
        # Should have called update for the visualization
        dashboard.engine.update_visualization.assert_called_once()
    
    async def test_update_callbacks(self, dashboard, sample_data):
        """Test update callbacks."""
        callback_called = False
        
        def update_callback():
            nonlocal callback_called
            callback_called = True
        
        dashboard.add_update_callback(update_callback)
        
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        await dashboard.render()
        
        assert callback_called is True
    
    async def test_async_update_callbacks(self, dashboard, sample_data):
        """Test async update callbacks."""
        callback_called = False
        
        async def async_update_callback():
            nonlocal callback_called
            callback_called = True
        
        dashboard.add_update_callback(async_update_callback)
        
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        await dashboard.render()
        
        assert callback_called is True
    
    async def test_get_visualization_info(self, dashboard, sample_data):
        """Test getting visualization info."""
        await dashboard.add_visualization('test_viz', 'mock', sample_data)
        
        info = dashboard.get_visualization_info('test_viz')
        
        assert info is not None
        assert info['visualizer_type'] == 'mock'
        assert 'created_at' in info
    
    async def test_get_nonexistent_visualization_info(self, dashboard):
        """Test getting info for non-existent visualization."""
        info = dashboard.get_visualization_info('nonexistent')
        
        assert info is None
    
    async def test_list_visualizations(self, dashboard, sample_data):
        """Test listing visualizations."""
        viz_ids = ['viz1', 'viz2', 'viz3']
        
        for viz_id in viz_ids:
            await dashboard.add_visualization(viz_id, 'mock', sample_data)
        
        listed_viz_ids = dashboard.list_visualizations()
        
        assert len(listed_viz_ids) == 3
        assert all(viz_id in listed_viz_ids for viz_id in viz_ids)
    
    async def test_dashboard_statistics(self, dashboard, sample_data):
        """Test getting dashboard statistics."""
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        await dashboard.add_visualization('viz2', 'mock', sample_data)
        
        stats = dashboard.get_dashboard_statistics()
        
        assert stats['total_visualizations'] == 2
        assert stats['layout_type'] == 'grid'
        assert stats['auto_refresh_enabled'] is False
        assert 'engine_stats' in stats
    
    async def test_error_handling_in_add_visualization(self, dashboard, sample_data):
        """Test error handling when adding visualization fails."""
        # Make engine raise an error
        dashboard.engine.create_visualization.side_effect = Exception("Test error")
        
        success = await dashboard.add_visualization('test_viz', 'mock', sample_data)
        
        assert success is False
        assert 'test_viz' not in dashboard.visualizations
    
    async def test_error_handling_in_render(self, dashboard, sample_data):
        """Test error handling during render."""
        await dashboard.add_visualization('viz1', 'mock', sample_data)
        
        # Make engine render raise an error
        dashboard.engine.render_visualization.side_effect = Exception("Render error")
        
        # Should not raise exception, but handle gracefully
        figure = await dashboard.render()
        
        assert figure is not None
    
    async def test_concurrent_operations(self, dashboard, sample_data):
        """Test concurrent dashboard operations."""
        # Add multiple visualizations concurrently
        tasks = []
        for i in range(5):
            task = dashboard.add_visualization(f'viz_{i}', 'mock', sample_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result is True for result in results)
        assert len(dashboard.visualizations) == 5
    
    async def test_layout_integration(self, mock_engine):
        """Test different layout types."""
        layouts = [
            DashboardLayout('grid'),
            DashboardLayout('flow', items_per_row=2),
            DashboardLayout('custom', positions={}, total_rows=2, total_cols=2)
        ]
        
        for layout in layouts:
            dashboard = Dashboard(layout, mock_engine)
            await dashboard.initialize()
            
            # Add visualization and render
            await dashboard.add_visualization('viz1', 'mock', {})
            figure = await dashboard.render()
            
            assert figure is not None
            
            await dashboard.shutdown()
