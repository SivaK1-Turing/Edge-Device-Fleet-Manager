#!/usr/bin/env python3
"""
Example Usage: Feature 6 Dynamic Visualization & Dashboard

Demonstrates how to use the visualization system to create dashboards
with multiple chart types and real-time data updates.
"""

import asyncio
import sys
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
from edge_device_fleet_manager.visualization.plugins.line_chart import LineChartVisualizer
from edge_device_fleet_manager.visualization.plugins.bar_chart import BarChartVisualizer
from edge_device_fleet_manager.visualization.plugins.time_series import TimeSeriesVisualizer
from edge_device_fleet_manager.visualization.plugins.gauge import GaugeVisualizer


def generate_sample_data():
    """Generate sample data for demonstration."""
    # Device status data for bar chart
    device_status = {
        'categories': ['Online', 'Offline', 'Maintenance', 'Error'],
        'values': [45, 8, 3, 2]
    }
    
    # Temperature trend for line chart
    hours = list(range(24))
    temperatures = [20 + 5 * np.sin(h * np.pi / 12) + np.random.normal(0, 1) for h in hours]
    temperature_trend = {
        'x': hours,
        'y': temperatures
    }
    
    # Time series data for multiple metrics
    timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
    time_series_data = {
        'timestamps': timestamps,
        'values': [50 + 10 * np.sin(i * np.pi / 24) + np.random.normal(0, 2) for i in range(48)]
    }
    
    # Multiple metrics time series
    multi_metrics = {
        'metrics': {
            'CPU Usage': {
                'timestamps': timestamps[:24],
                'values': [30 + 20 * np.sin(i * np.pi / 12) + np.random.normal(0, 3) for i in range(24)]
            },
            'Memory Usage': {
                'timestamps': timestamps[:24],
                'values': [60 + 15 * np.cos(i * np.pi / 12) + np.random.normal(0, 2) for i in range(24)]
            },
            'Network I/O': {
                'timestamps': timestamps[:24],
                'values': [40 + 25 * np.sin(i * np.pi / 8) + np.random.normal(0, 4) for i in range(24)]
            }
        }
    }
    
    # Gauge data
    system_health = 87.5
    
    return {
        'device_status': device_status,
        'temperature_trend': temperature_trend,
        'time_series': time_series_data,
        'multi_metrics': multi_metrics,
        'system_health': system_health
    }


async def example_individual_visualizations():
    """Example of creating individual visualizations."""
    print("📊 Creating Individual Visualizations")
    print("=" * 40)
    
    # Generate sample data
    data = generate_sample_data()
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Edge Device Fleet Manager - Individual Visualizations', fontsize=16)
    
    # 1. Device Status Bar Chart
    print("Creating device status bar chart...")
    bar_viz = BarChartVisualizer({
        'title': 'Device Status Distribution',
        'xlabel': 'Status',
        'ylabel': 'Number of Devices',
        'color': 'steelblue',
        'show_values': True
    })
    await bar_viz.draw(axes[0, 0], data['device_status'])
    
    # 2. Temperature Trend Line Chart
    print("Creating temperature trend line chart...")
    line_viz = LineChartVisualizer({
        'title': 'Temperature Trend (24 Hours)',
        'xlabel': 'Hour',
        'ylabel': 'Temperature (°C)',
        'color': 'orange',
        'line_width': 2.5,
        'marker': 'o',
        'marker_size': 4
    })
    await line_viz.draw(axes[0, 1], data['temperature_trend'])
    
    # 3. System Metrics Time Series
    print("Creating system metrics time series...")
    ts_viz = TimeSeriesVisualizer({
        'title': 'System Metrics Over Time',
        'xlabel': 'Time',
        'ylabel': 'Usage (%)',
        'rolling_window': 3
    })
    await ts_viz.draw(axes[1, 0], data['multi_metrics'])
    
    # 4. System Health Gauge
    print("Creating system health gauge...")
    gauge_viz = GaugeVisualizer({
        'title': 'System Health Score',
        'min_value': 0,
        'max_value': 100,
        'units': '%',
        'gauge_type': 'semi',
        'color_zones': [
            {'min': 0, 'max': 40, 'color': 'red'},
            {'min': 40, 'max': 70, 'color': 'yellow'},
            {'min': 70, 'max': 100, 'color': 'green'}
        ]
    })
    await gauge_viz.draw(axes[1, 1], data['system_health'])
    
    plt.tight_layout()
    plt.savefig('individual_visualizations.png', dpi=150, bbox_inches='tight')
    print("✅ Individual visualizations saved to 'individual_visualizations.png'")
    plt.close()


async def example_dashboard_composition():
    """Example of creating a dashboard with multiple visualizations."""
    print("\n📊 Creating Dashboard Composition")
    print("=" * 40)
    
    # Create dashboard with grid layout
    layout = DashboardLayout('grid', columns=2)
    dashboard = Dashboard(layout)
    
    # Mock plugin discovery for the engine
    dashboard.engine.plugin_manager.discovered_plugins = {
        'line_chart': LineChartVisualizer,
        'bar_chart': BarChartVisualizer,
        'time_series': TimeSeriesVisualizer,
        'gauge': GaugeVisualizer
    }
    
    await dashboard.initialize()
    print("Dashboard initialized")
    
    # Generate sample data
    data = generate_sample_data()
    
    # Add visualizations to dashboard
    print("Adding visualizations to dashboard...")
    
    await dashboard.add_visualization(
        'device_status',
        'bar_chart',
        data['device_status'],
        {
            'title': 'Device Status',
            'orientation': 'vertical',
            'color': 'steelblue',
            'show_values': True
        }
    )
    
    await dashboard.add_visualization(
        'temperature_trend',
        'line_chart',
        data['temperature_trend'],
        {
            'title': 'Temperature Trend',
            'color': 'orange',
            'line_width': 2.0,
            'fill_area': True
        }
    )
    
    await dashboard.add_visualization(
        'system_metrics',
        'time_series',
        data['multi_metrics'],
        {
            'title': 'System Metrics',
            'rolling_window': 2
        }
    )
    
    await dashboard.add_visualization(
        'health_gauge',
        'gauge',
        data['system_health'],
        {
            'title': 'System Health',
            'units': '%',
            'gauge_type': 'semi'
        }
    )
    
    # Render dashboard
    print("Rendering dashboard...")
    figure = await dashboard.render(figure_size=(16, 12))
    figure.suptitle('Edge Device Fleet Manager Dashboard', fontsize=18, fontweight='bold')
    
    plt.savefig('dashboard_composition.png', dpi=150, bbox_inches='tight')
    print("✅ Dashboard saved to 'dashboard_composition.png'")
    plt.close()
    
    # Display dashboard statistics
    stats = dashboard.get_dashboard_statistics()
    print(f"\n📈 Dashboard Statistics:")
    print(f"   Total visualizations: {stats['total_visualizations']}")
    print(f"   Layout type: {stats['layout_type']}")
    print(f"   Visualization IDs: {', '.join(stats['visualization_ids'])}")
    
    await dashboard.shutdown()
    print("Dashboard shutdown complete")


async def example_real_time_updates():
    """Example of real-time dashboard updates."""
    print("\n📊 Real-time Dashboard Updates Example")
    print("=" * 40)
    
    # Create simple dashboard
    layout = DashboardLayout('flow', items_per_row=2)
    dashboard = Dashboard(layout)
    
    # Mock plugin discovery
    dashboard.engine.plugin_manager.discovered_plugins = {
        'line_chart': LineChartVisualizer,
        'gauge': GaugeVisualizer
    }
    
    await dashboard.initialize()
    
    # Add initial visualizations
    initial_data = {'x': [1, 2, 3], 'y': [1, 2, 3]}
    initial_gauge = 50
    
    await dashboard.add_visualization('trend', 'line_chart', initial_data, {'title': 'Live Trend'})
    await dashboard.add_visualization('live_gauge', 'gauge', initial_gauge, {'title': 'Live Metric'})
    
    print("Simulating real-time updates...")
    
    # Simulate 5 updates
    for i in range(5):
        print(f"Update {i+1}/5...")
        
        # Generate new data
        new_trend_data = {
            'x': list(range(1, 6+i)),
            'y': [1 + j + np.random.normal(0, 0.5) for j in range(5+i)]
        }
        new_gauge_value = 50 + 20 * np.sin(i * np.pi / 4) + np.random.normal(0, 5)
        
        # Update visualizations
        await dashboard.update_visualization('trend', new_trend_data)
        await dashboard.update_visualization('live_gauge', new_gauge_value)
        
        # Render updated dashboard
        figure = await dashboard.render(figure_size=(12, 6))
        figure.suptitle(f'Real-time Dashboard - Update {i+1}', fontsize=14)
        
        plt.savefig(f'realtime_update_{i+1}.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # Simulate delay
        await asyncio.sleep(0.1)
    
    print("✅ Real-time updates complete. Check 'realtime_update_*.png' files")
    
    await dashboard.shutdown()


async def example_custom_layouts():
    """Example of different layout types."""
    print("\n📊 Custom Layout Examples")
    print("=" * 40)
    
    data = generate_sample_data()
    
    # Test different layout types
    layouts = [
        ('Grid Layout (2x2)', DashboardLayout('grid', columns=2)),
        ('Flow Layout (3 per row)', DashboardLayout('flow', items_per_row=3)),
        ('Custom Layout', DashboardLayout('custom', 
                                        positions={
                                            'viz_0': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1},
                                            'viz_1': {'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1},
                                            'viz_2': {'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1}
                                        },
                                        total_rows=2, total_cols=2))
    ]
    
    for layout_name, layout in layouts:
        print(f"Creating {layout_name}...")
        
        dashboard = Dashboard(layout)
        dashboard.engine.plugin_manager.discovered_plugins = {
            'line_chart': LineChartVisualizer,
            'bar_chart': BarChartVisualizer,
            'gauge': GaugeVisualizer
        }
        
        await dashboard.initialize()
        
        # Add visualizations
        await dashboard.add_visualization('chart1', 'line_chart', data['temperature_trend'], {'title': 'Chart 1'})
        await dashboard.add_visualization('chart2', 'bar_chart', data['device_status'], {'title': 'Chart 2'})
        await dashboard.add_visualization('chart3', 'gauge', data['system_health'], {'title': 'Chart 3'})
        
        # Render
        figure = await dashboard.render(figure_size=(14, 8))
        figure.suptitle(layout_name, fontsize=16)
        
        filename = layout_name.lower().replace(' ', '_').replace('(', '').replace(')', '') + '.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        await dashboard.shutdown()
    
    print("✅ Custom layout examples saved")


async def main():
    """Main example runner."""
    print("🚀 Edge Device Fleet Manager - Visualization Examples")
    print("=" * 60)
    
    try:
        # Run examples
        await example_individual_visualizations()
        await example_dashboard_composition()
        await example_real_time_updates()
        await example_custom_layouts()
        
        print("\n🎉 All visualization examples completed successfully!")
        print("\n📁 Generated files:")
        print("   - individual_visualizations.png")
        print("   - dashboard_composition.png")
        print("   - realtime_update_*.png (5 files)")
        print("   - grid_layout_2x2.png")
        print("   - flow_layout_3_per_row.png")
        print("   - custom_layout.png")
        
        print("\n💡 This demonstrates:")
        print("   ✅ Plugin-based visualization system")
        print("   ✅ Multiple chart types (line, bar, time series, gauge)")
        print("   ✅ Dashboard composition with layouts")
        print("   ✅ Real-time data updates")
        print("   ✅ Flexible layout management")
        print("   ✅ Configuration and theming")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
