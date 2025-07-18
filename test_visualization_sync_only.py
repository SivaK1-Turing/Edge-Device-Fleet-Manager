#!/usr/bin/env python3
"""
Synchronous Unit Tests for Feature 6: Dynamic Visualization & Dashboard

These tests avoid async complications and focus on core functionality
that can be tested synchronously.
"""

import os
import sys
import unittest
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Set non-GUI backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.visualization.plugins.base import BaseVisualizer
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer
from edge_device_fleet_manager.visualization.plugins.bar_chart import BarChartVisualizer
from edge_device_fleet_manager.visualization.plugins.gauge import GaugeVisualizer
from edge_device_fleet_manager.visualization.core.dashboard import DashboardLayout
from edge_device_fleet_manager.visualization.core.theme import ThemeManager


class TestBaseVisualizerSync(unittest.TestCase):
    """Test base visualizer functionality synchronously."""
    
    def test_base_visualizer_abstract(self):
        """Test that BaseVisualizer is abstract."""
        with self.assertRaises(TypeError):
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
        self.assertEqual(viz.config['title'], "Default Title")
        self.assertEqual(viz.config['color'], "blue")
        
        # Test with partial config
        viz = TestVisualizer({'title': 'Custom Title'})
        self.assertEqual(viz.config['title'], "Custom Title")
        self.assertEqual(viz.config['color'], "blue")
    
    def test_update_config(self):
        """Test configuration updates."""
        class TestVisualizer(BaseVisualizer):
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer({'title': 'Original'})
        viz.update_config({'title': 'Updated', 'color': 'red'})
        
        self.assertEqual(viz.config['title'], 'Updated')
        self.assertEqual(viz.config['color'], 'red')
    
    def test_data_validation(self):
        """Test data validation."""
        class TestVisualizer(BaseVisualizer):
            supported_data_types = ['dict', 'list']
            
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        
        # Valid data types
        self.assertTrue(viz.validate_data({'x': [1, 2], 'y': [3, 4]}))
        self.assertTrue(viz.validate_data([1, 2, 3]))
        
        # Invalid data type
        self.assertFalse(viz.validate_data("invalid"))
    
    def test_color_palette(self):
        """Test color palette generation."""
        class TestVisualizer(BaseVisualizer):
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        
        # Test auto colors
        colors = viz.get_color_palette(5)
        self.assertEqual(len(colors), 5)
        self.assertTrue(all(isinstance(color, str) for color in colors))
        
        # Test custom color
        viz = TestVisualizer({'color': 'red'})
        colors = viz.get_color_palette(3)
        self.assertTrue(all(color == 'red' for color in colors))
    
    def test_statistics(self):
        """Test visualizer statistics."""
        class TestVisualizer(BaseVisualizer):
            name = "Test"
            version = "1.0.0"
            
            async def draw(self, ax, data):
                pass
        
        viz = TestVisualizer()
        stats = viz.get_statistics()
        
        self.assertEqual(stats['name'], "Test")
        self.assertEqual(stats['version'], "1.0.0")
        self.assertEqual(stats['render_count'], 0)
        self.assertFalse(stats['supports_real_time'])


class TestDashboardLayoutSync(unittest.TestCase):
    """Test dashboard layout functionality synchronously."""
    
    def test_grid_layout_creation(self):
        """Test grid layout creation."""
        layout = DashboardLayout('grid', columns=2)
        self.assertEqual(layout.layout_type, 'grid')
        self.assertEqual(layout.config['columns'], 2)
    
    def test_grid_layout_single_viz(self):
        """Test grid layout with single visualization."""
        layout = DashboardLayout('grid')
        positions = layout.calculate_positions(1)
        
        self.assertEqual(len(positions), 1)
        self.assertIn('viz_0', positions)
        self.assertEqual(positions['viz_0']['row'], 0)
        self.assertEqual(positions['viz_0']['col'], 0)
    
    def test_grid_layout_multiple_viz(self):
        """Test grid layout with multiple visualizations."""
        layout = DashboardLayout('grid')
        positions = layout.calculate_positions(4)
        
        self.assertEqual(len(positions), 4)
        # Should create 2x2 grid
        self.assertEqual(positions['viz_0']['grid_rows'], 2)
        self.assertEqual(positions['viz_0']['grid_cols'], 2)
    
    def test_grid_layout_custom_columns(self):
        """Test grid layout with custom columns."""
        layout = DashboardLayout('grid', columns=3)
        positions = layout.calculate_positions(5)
        
        self.assertEqual(len(positions), 5)
        # Should use 3 columns
        self.assertEqual(positions['viz_0']['grid_cols'], 3)
        self.assertEqual(positions['viz_0']['grid_rows'], 2)  # 5 items in 3 columns = 2 rows
    
    def test_flow_layout(self):
        """Test flow layout."""
        layout = DashboardLayout('flow', items_per_row=2)
        positions = layout.calculate_positions(3)
        
        self.assertEqual(len(positions), 3)
        # First row should have 2 items
        self.assertEqual(positions['viz_0']['row'], 0)
        self.assertEqual(positions['viz_1']['row'], 0)
        # Third item should be on second row
        self.assertEqual(positions['viz_2']['row'], 1)
    
    def test_custom_layout(self):
        """Test custom layout."""
        custom_positions = {
            'viz_0': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1},
            'viz_1': {'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1}
        }
        
        layout = DashboardLayout('custom', 
                                positions=custom_positions,
                                total_rows=2, 
                                total_cols=2)
        positions = layout.calculate_positions(2)
        
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions['viz_0']['rowspan'], 2)
        self.assertEqual(positions['viz_0']['colspan'], 1)


class TestThemeManagerSync(unittest.TestCase):
    """Test theme manager functionality synchronously."""
    
    def setUp(self):
        """Set up theme manager for testing."""
        self.theme_manager = ThemeManager()
    
    def test_theme_loading(self):
        """Test theme loading."""
        themes = self.theme_manager.list_themes()
        self.assertGreaterEqual(len(themes), 4)  # default, dark, professional, colorful
        self.assertIn('default', themes)
        self.assertIn('dark', themes)
    
    def test_color_palette(self):
        """Test color palette."""
        colors = self.theme_manager.get_color_palette('professional', 5)
        self.assertEqual(len(colors), 5)
        self.assertTrue(all(isinstance(color, str) for color in colors))
    
    def test_theme_info(self):
        """Test theme info."""
        info = self.theme_manager.get_theme_info('default')
        self.assertIsNotNone(info)
        self.assertIn('colors', info)
        self.assertIn('fonts', info)
        self.assertIn('style', info)
    
    def test_custom_theme_creation(self):
        """Test custom theme creation."""
        custom_theme = {
            'colors': {'primary': '#ff0000', 'background': '#ffffff'},
            'fonts': {'family': 'serif', 'size': 12},
            'style': {'grid_alpha': 0.5}
        }
        
        success = self.theme_manager.create_custom_theme('test_theme', custom_theme)
        self.assertTrue(success)
        self.assertIn('test_theme', self.theme_manager.list_themes())


class TestVisualizationPluginsSync(unittest.TestCase):
    """Test visualization plugins synchronously."""
    
    def test_line_chart_creation(self):
        """Test line chart visualizer creation."""
        viz = LineChartVisualizer({'title': 'Test Line Chart'})
        self.assertEqual(viz.name, 'Line Chart')
        self.assertEqual(viz.config['title'], 'Test Line Chart')
        self.assertTrue(viz.supports_real_time)
    
    def test_bar_chart_creation(self):
        """Test bar chart visualizer creation."""
        viz = BarChartVisualizer({'title': 'Test Bar Chart'})
        self.assertEqual(viz.name, 'Bar Chart')
        self.assertEqual(viz.config['title'], 'Test Bar Chart')
        self.assertTrue(viz.supports_real_time)
    
    def test_gauge_creation(self):
        """Test gauge visualizer creation."""
        viz = GaugeVisualizer({'title': 'Test Gauge'})
        self.assertEqual(viz.name, 'Gauge')
        self.assertEqual(viz.config['title'], 'Test Gauge')
        self.assertTrue(viz.supports_real_time)
    
    def test_plugin_configuration(self):
        """Test plugin configuration."""
        viz = LineChartVisualizer({'title': 'Original'})
        
        # Test initial config
        config = viz.get_config()
        self.assertEqual(config['title'], 'Original')
        
        # Test config update
        viz.update_config({'title': 'Updated', 'color': 'red'})
        config = viz.get_config()
        self.assertEqual(config['title'], 'Updated')
        self.assertEqual(config['color'], 'red')
    
    def test_data_validation(self):
        """Test data validation."""
        viz = LineChartVisualizer()
        
        # Valid data
        self.assertTrue(viz.validate_data({'x': [1, 2, 3], 'y': [1, 4, 2]}))
        self.assertTrue(viz.validate_data([1, 2, 3]))
        
        # DataFrame validation (if pandas is available)
        try:
            df = pd.DataFrame({'x': [1, 2, 3], 'y': [1, 4, 2]})
            self.assertTrue(viz.validate_data(df))
        except ImportError:
            pass  # Skip if pandas not available


def run_sync_tests():
    """Run all synchronous tests."""
    print("🧪 Running Synchronous Unit Tests for Feature 6")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBaseVisualizerSync,
        TestDashboardLayoutSync,
        TestThemeManagerSync,
        TestVisualizationPluginsSync
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📊 Results: {passed}/{total_tests} tests passed")
    
    if failures > 0:
        print(f"❌ {failures} failures")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print(f"❌ {errors} errors")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if passed == total_tests:
        print("🎉 All synchronous tests passed!")
        print("\n💡 Core visualization functionality is working:")
        print("   - Plugin system and base classes")
        print("   - Dashboard layout management")
        print("   - Theme management")
        print("   - Configuration handling")
    
    return passed == total_tests


if __name__ == "__main__":
    success = run_sync_tests()
    sys.exit(0 if success else 1)
