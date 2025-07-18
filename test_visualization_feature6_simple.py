#!/usr/bin/env python3
"""
Simple Test Suite for Feature 6: Dynamic Visualization & Dashboard

Quick validation of core visualization functionality.
"""

import asyncio
import sys
import time
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.visualization.core.engine import VisualizationEngine
from edge_device_fleet_manager.visualization.core.dashboard import Dashboard, DashboardLayout
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer
from edge_device_fleet_manager.visualization.plugins.bar_chart import BarChartVisualizer
from edge_device_fleet_manager.visualization.plugins.gauge import GaugeVisualizer


async def test_basic_visualization():
    """Test basic visualization functionality."""
    print("🔍 Testing Basic Visualization...")
    
    try:
        # Create line chart visualizer
        line_viz = LineChartVisualizer({'title': 'Test Line Chart'})
        
        # Test data
        data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 1, 5, 3]}
        
        # Create figure and draw
        fig, ax = plt.subplots()
        await line_viz.draw(ax, data)
        
        # Verify chart was drawn
        assert len(ax.lines) > 0, "No lines drawn"
        assert ax.get_title() == 'Test Line Chart', "Title not set"
        
        plt.close(fig)
        print("  ✅ Basic line chart visualization")
        
        # Test bar chart
        bar_viz = BarChartVisualizer({'title': 'Test Bar Chart'})
        bar_data = {'A': 10, 'B': 20, 'C': 15}
        
        fig, ax = plt.subplots()
        await bar_viz.draw(ax, bar_data)
        
        assert len(ax.patches) > 0, "No bars drawn"
        plt.close(fig)
        print("  ✅ Basic bar chart visualization")
        
        # Test gauge
        gauge_viz = GaugeVisualizer({'title': 'Test Gauge'})
        
        fig, ax = plt.subplots()
        await gauge_viz.draw(ax, 75)
        
        assert len(ax.patches) > 0, "No gauge drawn"
        plt.close(fig)
        print("  ✅ Basic gauge visualization")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Basic visualization failed: {e}")
        return False


async def test_visualization_engine():
    """Test visualization engine."""
    print("🔍 Testing Visualization Engine...")
    
    try:
        # Create engine
        engine = VisualizationEngine()
        
        # Mock plugin discovery
        engine.plugin_manager.discovered_plugins = {
            'line_chart': LineChartVisualizer,
            'bar_chart': BarChartVisualizer,
            'gauge': GaugeVisualizer
        }
        
        await engine.initialize()
        print("  ✅ Engine initialization")
        
        # Test creating visualization
        data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        viz_id = await engine.create_visualization('line_chart', data, {'title': 'Engine Test'})
        
        assert viz_id is not None, "Failed to create visualization"
        print("  ✅ Visualization creation")
        
        # Test rendering
        figure = await engine.render_visualization(viz_id)
        assert figure is not None, "Failed to render visualization"
        assert len(figure.axes) > 0, "No axes in figure"
        print("  ✅ Visualization rendering")
        
        # Test statistics
        stats = engine.get_engine_statistics()
        assert stats['active_visualizations'] == 1, "Incorrect active visualization count"
        print("  ✅ Engine statistics")
        
        await engine.shutdown()
        print("  ✅ Engine shutdown")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Engine test failed: {e}")
        return False


async def test_dashboard():
    """Test dashboard functionality."""
    print("🔍 Testing Dashboard...")
    
    try:
        # Create dashboard
        layout = DashboardLayout('grid')
        dashboard = Dashboard(layout)
        
        # Mock engine plugins
        dashboard.engine.plugin_manager.discovered_plugins = {
            'line_chart': LineChartVisualizer,
            'bar_chart': BarChartVisualizer,
            'gauge': GaugeVisualizer
        }
        
        await dashboard.initialize()
        print("  ✅ Dashboard initialization")
        
        # Add visualizations
        line_data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        bar_data = {'A': 10, 'B': 20}
        gauge_data = 75
        
        await dashboard.add_visualization('line', 'line_chart', line_data)
        await dashboard.add_visualization('bar', 'bar_chart', bar_data)
        await dashboard.add_visualization('gauge', 'gauge', gauge_data)
        
        assert len(dashboard.list_visualizations()) == 3, "Incorrect visualization count"
        print("  ✅ Adding visualizations")
        
        # Test rendering
        figure = await dashboard.render()
        assert figure is not None, "Failed to render dashboard"
        print("  ✅ Dashboard rendering")
        
        # Test statistics
        stats = dashboard.get_dashboard_statistics()
        assert stats['total_visualizations'] == 3, "Incorrect dashboard statistics"
        print("  ✅ Dashboard statistics")
        
        await dashboard.shutdown()
        print("  ✅ Dashboard shutdown")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Dashboard test failed: {e}")
        return False


async def test_plugin_configuration():
    """Test plugin configuration."""
    print("🔍 Testing Plugin Configuration...")
    
    try:
        # Test configuration merging
        viz = LineChartVisualizer({'title': 'Custom Title', 'color': 'red'})
        
        config = viz.get_config()
        assert config['title'] == 'Custom Title', "Custom title not set"
        assert config['color'] == 'red', "Custom color not set"
        print("  ✅ Configuration merging")
        
        # Test configuration update
        viz.update_config({'line_width': 3.0, 'marker': 'o'})
        config = viz.get_config()
        assert config['line_width'] == 3.0, "Line width not updated"
        assert config['marker'] == 'o', "Marker not updated"
        print("  ✅ Configuration update")
        
        # Test data validation
        valid_data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        assert viz.validate_data(valid_data), "Valid data rejected"
        print("  ✅ Data validation")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Plugin configuration test failed: {e}")
        return False


async def test_layout_system():
    """Test layout system."""
    print("🔍 Testing Layout System...")
    
    try:
        # Test grid layout
        grid_layout = DashboardLayout('grid')
        positions = grid_layout.calculate_positions(4)
        
        assert len(positions) == 4, "Incorrect position count"
        assert 'viz_0' in positions, "Missing viz_0 position"
        print("  ✅ Grid layout")
        
        # Test flow layout
        flow_layout = DashboardLayout('flow', items_per_row=2)
        positions = flow_layout.calculate_positions(3)
        
        assert len(positions) == 3, "Incorrect flow position count"
        assert positions['viz_2']['row'] == 1, "Incorrect flow positioning"
        print("  ✅ Flow layout")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Layout test failed: {e}")
        return False


async def test_data_types():
    """Test different data types."""
    print("🔍 Testing Data Types...")
    
    try:
        viz = LineChartVisualizer()
        fig, ax = plt.subplots()
        
        # Test dictionary data
        dict_data = {'x': [1, 2, 3], 'y': [1, 4, 2]}
        await viz.draw(ax, dict_data)
        assert len(ax.lines) > 0, "Dictionary data not drawn"
        ax.clear()
        print("  ✅ Dictionary data")
        
        # Test array data
        array_data = np.array([[1, 1], [2, 4], [3, 2]])
        await viz.draw(ax, array_data)
        assert len(ax.lines) > 0, "Array data not drawn"
        ax.clear()
        print("  ✅ Array data")
        
        # Test DataFrame data
        df_data = pd.DataFrame({'x': [1, 2, 3], 'y': [1, 4, 2]})
        await viz.draw(ax, df_data)
        assert len(ax.lines) > 0, "DataFrame data not drawn"
        
        plt.close(fig)
        print("  ✅ DataFrame data")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Data types test failed: {e}")
        return False


async def run_simple_tests():
    """Run all simple tests."""
    print("🚀 Starting Simple Feature 6 Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Visualization", test_basic_visualization),
        ("Visualization Engine", test_visualization_engine),
        ("Dashboard", test_dashboard),
        ("Plugin Configuration", test_plugin_configuration),
        ("Layout System", test_layout_system),
        ("Data Types", test_data_types),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            start_time = time.time()
            success = await test_func()
            duration = time.time() - start_time
            
            if success:
                passed += 1
                print(f"✅ {test_name} PASSED ({duration:.3f}s)")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED ({duration:.3f}s)")
        
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    total = passed + failed
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if failed == 0:
        print("🎉 All simple Feature 6 tests passed!")
        print("\n💡 Core visualization functionality is working:")
        print("   - Plugin-based visualizers")
        print("   - Visualization engine")
        print("   - Dashboard composition")
        print("   - Layout management")
        print("   - Multiple data type support")
    else:
        print(f"❌ {failed} tests failed")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_simple_tests())
    sys.exit(0 if success else 1)
