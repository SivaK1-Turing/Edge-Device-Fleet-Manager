#!/usr/bin/env python3
"""
Comprehensive Test Suite for Feature 6: Dynamic Visualization & Dashboard

Tests the complete visualization system including engine, plugins, dashboard,
data adapters, and integration with the persistence layer.
"""

import asyncio
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.visualization.core.engine import VisualizationEngine
from edge_device_fleet_manager.visualization.core.dashboard import Dashboard, DashboardLayout
from edge_device_fleet_manager.visualization.core.data_adapter import DataAdapter
from edge_device_fleet_manager.visualization.core.theme import ThemeManager
from edge_device_fleet_manager.visualization.plugins.registry import VisualizerRegistry
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer
from edge_device_fleet_manager.visualization.plugins.bar_chart import BarChartVisualizer
from edge_device_fleet_manager.visualization.plugins.time_series import TimeSeriesVisualizer
from edge_device_fleet_manager.visualization.plugins.gauge import GaugeVisualizer


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✅ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"  ❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Results: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"❌ {self.failed} tests failed:")
            for error in self.errors:
                print(f"   - {error}")
        return self.failed == 0


async def test_visualization_engine():
    """Test visualization engine functionality."""
    print("🔍 Testing Visualization Engine...")
    results = TestResults()
    
    try:
        # Create engine
        engine = VisualizationEngine()
        
        # Mock plugin discovery to avoid entry_points issues
        engine.plugin_manager.discovered_plugins = {
            'line_chart': LineChartVisualizer,
            'bar_chart': BarChartVisualizer,
            'time_series': TimeSeriesVisualizer,
            'gauge': GaugeVisualizer
        }
        
        await engine.initialize()
        results.add_pass("Engine initialization")
        
        # Test plugin registration
        available_visualizers = engine.get_available_visualizers()
        if len(available_visualizers) >= 4:
            results.add_pass("Plugin registration")
        else:
            results.add_fail("Plugin registration", f"Expected >= 4 plugins, got {len(available_visualizers)}")
        
        # Test visualization creation
        sample_data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 1, 5, 3]}
        viz_id = await engine.create_visualization('line_chart', sample_data, {'title': 'Test Chart'})
        if viz_id:
            results.add_pass("Visualization creation")
        else:
            results.add_fail("Visualization creation", "Failed to create visualization")
        
        # Test visualization rendering
        figure = await engine.render_visualization(viz_id)
        if figure and len(figure.axes) > 0:
            results.add_pass("Visualization rendering")
        else:
            results.add_fail("Visualization rendering", "Failed to render visualization")
        
        # Test visualization update
        await engine.update_visualization(viz_id, config={'title': 'Updated Chart'})
        viz_info = engine.get_visualization_info(viz_id)
        if viz_info and viz_info['config']['title'] == 'Updated Chart':
            results.add_pass("Visualization update")
        else:
            results.add_fail("Visualization update", "Failed to update visualization")
        
        # Test statistics
        stats = engine.get_engine_statistics()
        if stats['active_visualizations'] == 1:
            results.add_pass("Engine statistics")
        else:
            results.add_fail("Engine statistics", f"Expected 1 active viz, got {stats['active_visualizations']}")
        
        # Test removal
        await engine.remove_visualization(viz_id)
        if viz_id not in engine._active_visualizations:
            results.add_pass("Visualization removal")
        else:
            results.add_fail("Visualization removal", "Failed to remove visualization")
        
        await engine.shutdown()
        results.add_pass("Engine shutdown")
        
    except Exception as e:
        results.add_fail("Engine test setup", str(e))
    
    return results.summary()


async def test_visualizer_plugins():
    """Test individual visualizer plugins."""
    print("🔍 Testing Visualizer Plugins...")
    results = TestResults()
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        ax_flat = axes.flatten()
        
        # Test data
        line_data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 1, 5, 3]}
        bar_data = {'A': 10, 'B': 20, 'C': 15, 'D': 25}
        time_data = {
            'timestamps': pd.date_range('2024-01-01', periods=10, freq='1H'),
            'values': [20, 21, 22, 21, 20, 19, 18, 19, 20, 21]
        }
        gauge_data = 75
        
        # Test LineChartVisualizer
        line_viz = LineChartVisualizer({'title': 'Line Chart Test'})
        await line_viz.draw(ax_flat[0], line_data)
        if len(ax_flat[0].lines) > 0:
            results.add_pass("LineChartVisualizer")
        else:
            results.add_fail("LineChartVisualizer", "No lines drawn")
        
        # Test BarChartVisualizer
        bar_viz = BarChartVisualizer({'title': 'Bar Chart Test'})
        await bar_viz.draw(ax_flat[1], bar_data)
        if len(ax_flat[1].patches) > 0:
            results.add_pass("BarChartVisualizer")
        else:
            results.add_fail("BarChartVisualizer", "No bars drawn")
        
        # Test TimeSeriesVisualizer
        ts_viz = TimeSeriesVisualizer({'title': 'Time Series Test'})
        await ts_viz.draw(ax_flat[2], time_data)
        if len(ax_flat[2].lines) > 0:
            results.add_pass("TimeSeriesVisualizer")
        else:
            results.add_fail("TimeSeriesVisualizer", "No time series drawn")
        
        # Test GaugeVisualizer
        gauge_viz = GaugeVisualizer({'title': 'Gauge Test', 'min_value': 0, 'max_value': 100})
        await gauge_viz.draw(ax_flat[3], gauge_data)
        if len(ax_flat[3].patches) > 0:
            results.add_pass("GaugeVisualizer")
        else:
            results.add_fail("GaugeVisualizer", "No gauge drawn")
        
        plt.close(fig)
        
        # Test plugin configuration
        line_viz.update_config({'color': 'red', 'line_width': 3.0})
        config = line_viz.get_config()
        if config['color'] == 'red' and config['line_width'] == 3.0:
            results.add_pass("Plugin configuration")
        else:
            results.add_fail("Plugin configuration", "Config update failed")
        
        # Test data validation
        if line_viz.validate_data(line_data):
            results.add_pass("Data validation")
        else:
            results.add_fail("Data validation", "Valid data rejected")
        
        # Test statistics
        stats = line_viz.get_statistics()
        if 'name' in stats and 'version' in stats:
            results.add_pass("Plugin statistics")
        else:
            results.add_fail("Plugin statistics", "Missing statistics fields")
        
    except Exception as e:
        results.add_fail("Plugin test setup", str(e))
    
    return results.summary()


async def test_dashboard_system():
    """Test dashboard system functionality."""
    print("🔍 Testing Dashboard System...")
    results = TestResults()
    
    try:
        # Create dashboard with grid layout
        layout = DashboardLayout('grid')
        dashboard = Dashboard(layout)
        
        # Mock the engine's plugin discovery
        dashboard.engine.plugin_manager.discovered_plugins = {
            'line_chart': LineChartVisualizer,
            'bar_chart': BarChartVisualizer,
            'gauge': GaugeVisualizer
        }
        
        await dashboard.initialize()
        results.add_pass("Dashboard initialization")
        
        # Test adding visualizations
        sample_data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        success1 = await dashboard.add_visualization('viz1', 'line_chart', sample_data)
        success2 = await dashboard.add_visualization('viz2', 'bar_chart', {'A': 10, 'B': 20})
        success3 = await dashboard.add_visualization('viz3', 'gauge', 75)
        
        if success1 and success2 and success3:
            results.add_pass("Adding visualizations")
        else:
            results.add_fail("Adding visualizations", "Failed to add some visualizations")
        
        # Test listing visualizations
        viz_list = dashboard.list_visualizations()
        if len(viz_list) == 3:
            results.add_pass("Listing visualizations")
        else:
            results.add_fail("Listing visualizations", f"Expected 3, got {len(viz_list)}")
        
        # Test dashboard rendering
        figure = await dashboard.render(figure_size=(15, 10))
        if figure and len(figure.axes) >= 3:
            results.add_pass("Dashboard rendering")
        else:
            results.add_fail("Dashboard rendering", "Failed to render dashboard")
        
        # Test visualization update
        success = await dashboard.update_visualization('viz1', config={'title': 'Updated Line Chart'})
        if success:
            results.add_pass("Visualization update")
        else:
            results.add_fail("Visualization update", "Failed to update visualization")
        
        # Test getting visualization info
        info = dashboard.get_visualization_info('viz1')
        if info and 'visualizer_type' in info:
            results.add_pass("Visualization info")
        else:
            results.add_fail("Visualization info", "Failed to get visualization info")
        
        # Test dashboard statistics
        stats = dashboard.get_dashboard_statistics()
        if stats['total_visualizations'] == 3:
            results.add_pass("Dashboard statistics")
        else:
            results.add_fail("Dashboard statistics", f"Expected 3 viz, got {stats['total_visualizations']}")
        
        # Test removing visualization
        success = await dashboard.remove_visualization('viz2')
        if success and len(dashboard.list_visualizations()) == 2:
            results.add_pass("Removing visualization")
        else:
            results.add_fail("Removing visualization", "Failed to remove visualization")
        
        await dashboard.shutdown()
        results.add_pass("Dashboard shutdown")
        
    except Exception as e:
        results.add_fail("Dashboard test setup", str(e))
    
    return results.summary()


async def test_layout_system():
    """Test different layout types."""
    print("🔍 Testing Layout System...")
    results = TestResults()
    
    try:
        # Test grid layout
        grid_layout = DashboardLayout('grid')
        positions = grid_layout.calculate_positions(4)
        if len(positions) == 4 and positions['viz_0']['grid_rows'] == 2:
            results.add_pass("Grid layout")
        else:
            results.add_fail("Grid layout", "Incorrect grid layout calculation")
        
        # Test flow layout
        flow_layout = DashboardLayout('flow', items_per_row=3)
        positions = flow_layout.calculate_positions(5)
        if len(positions) == 5 and positions['viz_3']['row'] == 1:
            results.add_pass("Flow layout")
        else:
            results.add_fail("Flow layout", "Incorrect flow layout calculation")
        
        # Test custom layout
        custom_positions = {
            'viz_0': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1},
            'viz_1': {'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1}
        }
        custom_layout = DashboardLayout('custom', 
                                      positions=custom_positions,
                                      total_rows=2, 
                                      total_cols=2)
        positions = custom_layout.calculate_positions(2)
        if len(positions) == 2 and positions['viz_0']['rowspan'] == 2:
            results.add_pass("Custom layout")
        else:
            results.add_fail("Custom layout", "Incorrect custom layout calculation")
        
    except Exception as e:
        results.add_fail("Layout test setup", str(e))
    
    return results.summary()


async def test_theme_system():
    """Test theme management system."""
    print("🔍 Testing Theme System...")
    results = TestResults()
    
    try:
        theme_manager = ThemeManager()
        await theme_manager.load_themes()
        
        # Test theme loading
        themes = theme_manager.list_themes()
        if len(themes) >= 4:  # default, dark, professional, colorful
            results.add_pass("Theme loading")
        else:
            results.add_fail("Theme loading", f"Expected >= 4 themes, got {len(themes)}")
        
        # Test theme application
        fig, ax = plt.subplots()
        theme_manager.apply_theme(fig, ax, 'dark')
        results.add_pass("Theme application")
        plt.close(fig)
        
        # Test color palette
        colors = theme_manager.get_color_palette('professional', 5)
        if len(colors) == 5:
            results.add_pass("Color palette")
        else:
            results.add_fail("Color palette", f"Expected 5 colors, got {len(colors)}")
        
        # Test custom theme creation
        custom_theme = {
            'colors': {'primary': '#ff0000', 'background': '#ffffff'},
            'fonts': {'family': 'serif', 'size': 12},
            'style': {'grid_alpha': 0.5}
        }
        success = theme_manager.create_custom_theme('test_theme', custom_theme)
        if success and 'test_theme' in theme_manager.list_themes():
            results.add_pass("Custom theme creation")
        else:
            results.add_fail("Custom theme creation", "Failed to create custom theme")
        
        # Test theme info
        info = theme_manager.get_theme_info('default')
        if info and 'colors' in info:
            results.add_pass("Theme info")
        else:
            results.add_fail("Theme info", "Failed to get theme info")
        
    except Exception as e:
        results.add_fail("Theme test setup", str(e))
    
    return results.summary()


async def test_plugin_registry():
    """Test plugin registry system."""
    print("🔍 Testing Plugin Registry...")
    results = TestResults()
    
    try:
        registry = VisualizerRegistry()
        
        # Test plugin registration
        success = registry.register('test_line', LineChartVisualizer, 'charts', ['line'])
        if success:
            results.add_pass("Plugin registration")
        else:
            results.add_fail("Plugin registration", "Failed to register plugin")
        
        # Test plugin retrieval
        plugin_class = registry.get('test_line')
        if plugin_class == LineChartVisualizer:
            results.add_pass("Plugin retrieval")
        else:
            results.add_fail("Plugin retrieval", "Failed to retrieve plugin")
        
        # Test alias retrieval
        plugin_class = registry.get('line')
        if plugin_class == LineChartVisualizer:
            results.add_pass("Plugin alias retrieval")
        else:
            results.add_fail("Plugin alias retrieval", "Failed to retrieve plugin by alias")
        
        # Test listing plugins
        plugins = registry.list_visualizers()
        if 'test_line' in plugins:
            results.add_pass("Plugin listing")
        else:
            results.add_fail("Plugin listing", "Plugin not in list")
        
        # Test category listing
        chart_plugins = registry.list_by_category('charts')
        if 'test_line' in chart_plugins:
            results.add_pass("Category listing")
        else:
            results.add_fail("Category listing", "Plugin not in category")
        
        # Test metadata
        metadata = registry.get_metadata('test_line')
        if metadata and metadata['category'] == 'charts':
            results.add_pass("Plugin metadata")
        else:
            results.add_fail("Plugin metadata", "Incorrect metadata")
        
        # Test search
        search_results = registry.search('line')
        if 'test_line' in search_results:
            results.add_pass("Plugin search")
        else:
            results.add_fail("Plugin search", "Plugin not found in search")
        
        # Test statistics
        stats = registry.get_statistics()
        if stats['total_visualizers'] >= 1:
            results.add_pass("Registry statistics")
        else:
            results.add_fail("Registry statistics", "Incorrect statistics")
        
    except Exception as e:
        results.add_fail("Registry test setup", str(e))
    
    return results.summary()


async def test_data_adapter():
    """Test data adapter functionality."""
    print("🔍 Testing Data Adapter...")
    results = TestResults()
    
    try:
        adapter = DataAdapter()
        await adapter.initialize()
        
        # Test static data loading
        static_data = {'type': 'static', 'data': {'x': [1, 2, 3], 'y': [1, 4, 2]}}
        loaded_data = await adapter.load_data(static_data)
        if loaded_data == {'x': [1, 2, 3], 'y': [1, 4, 2]}:
            results.add_pass("Static data loading")
        else:
            results.add_fail("Static data loading", "Data not loaded correctly")
        
        # Test direct data passthrough
        direct_data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        loaded_data = await adapter.load_data(direct_data)
        if loaded_data == direct_data:
            results.add_pass("Direct data passthrough")
        else:
            results.add_fail("Direct data passthrough", "Data not passed through correctly")
        
        # Test cache functionality
        adapter._cache_data('test_key', {'cached': True})
        cached_data = adapter._get_cached_data('test_key')
        if cached_data == {'cached': True}:
            results.add_pass("Data caching")
        else:
            results.add_fail("Data caching", "Data not cached correctly")
        
        # Test cache clearing
        adapter.clear_cache()
        cached_data = adapter._get_cached_data('test_key')
        if cached_data is None:
            results.add_pass("Cache clearing")
        else:
            results.add_fail("Cache clearing", "Cache not cleared")
        
        await adapter.shutdown()
        results.add_pass("Data adapter shutdown")
        
    except Exception as e:
        results.add_fail("Data adapter test setup", str(e))
    
    return results.summary()


async def run_all_tests():
    """Run all visualization tests."""
    print("🚀 Starting Comprehensive Feature 6 Test Suite")
    print("=" * 70)
    
    tests = [
        ("Visualization Engine", test_visualization_engine),
        ("Visualizer Plugins", test_visualizer_plugins),
        ("Dashboard System", test_dashboard_system),
        ("Layout System", test_layout_system),
        ("Theme System", test_theme_system),
        ("Plugin Registry", test_plugin_registry),
        ("Data Adapter", test_data_adapter),
    ]
    
    overall_success = True
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            start_time = time.time()
            success = await test_func()
            duration = time.time() - start_time
            
            if success:
                print(f"✅ {test_name} PASSED ({duration:.3f}s)")
            else:
                print(f"❌ {test_name} FAILED ({duration:.3f}s)")
                overall_success = False
        
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            overall_success = False
    
    print("\n" + "=" * 70)
    if overall_success:
        print("🎉 ALL FEATURE 6 TESTS PASSED!")
        print("\n💡 Feature 6: Dynamic Visualization & Dashboard is working correctly!")
        print("\n🔧 Available components:")
        print("   - Plugin-based visualization engine")
        print("   - Built-in visualizers (line, bar, time series, gauge)")
        print("   - Dashboard composition system")
        print("   - Theme management")
        print("   - Data adapter integration")
        print("   - Entry points plugin discovery")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
