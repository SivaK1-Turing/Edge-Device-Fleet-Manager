"""
Plugin Manager

Manages discovery and loading of visualizer plugins via entry_points.
Provides plugin lifecycle management and validation.
"""

import importlib
import inspect
from typing import Dict, List, Any, Type, Optional
from datetime import datetime, timezone
import pkg_resources

from ...core.logging import get_logger
from ..plugins.base import BaseVisualizer

logger = get_logger(__name__)


class PluginManager:
    """
    Plugin manager for visualizer discovery and loading via entry_points.
    
    Discovers visualizer plugins through setuptools entry_points mechanism,
    validates plugin interfaces, and manages plugin lifecycle.
    """
    
    ENTRY_POINT_GROUP = 'edge_device_fleet_manager.visualizers'
    
    def __init__(self):
        """Initialize plugin manager."""
        self.discovered_plugins = {}
        self.loaded_plugins = {}
        self.plugin_metadata = {}
        self.load_errors = {}
        
        self.logger = get_logger(f"{__name__}.PluginManager")
    
    async def discover_plugins(self) -> Dict[str, Type[BaseVisualizer]]:
        """
        Discover visualizer plugins via entry_points.
        
        Returns:
            Dictionary mapping plugin names to visualizer classes
        """
        self.logger.info("Discovering visualizer plugins...")
        
        discovered = {}
        
        try:
            # Discover plugins via entry_points
            for entry_point in pkg_resources.iter_entry_points(self.ENTRY_POINT_GROUP):
                try:
                    plugin_name = entry_point.name
                    self.logger.debug(f"Loading plugin: {plugin_name}")
                    
                    # Load the plugin class
                    plugin_class = entry_point.load()
                    
                    # Validate plugin interface
                    if self._validate_plugin(plugin_class, plugin_name):
                        discovered[plugin_name] = plugin_class
                        
                        # Store metadata
                        self.plugin_metadata[plugin_name] = {
                            'entry_point': entry_point,
                            'module': plugin_class.__module__,
                            'class_name': plugin_class.__name__,
                            'loaded_at': datetime.now(timezone.utc),
                            'version': getattr(plugin_class, '__version__', 'unknown'),
                            'description': getattr(plugin_class, '__doc__', '').strip()
                        }
                        
                        self.logger.info(f"Loaded plugin: {plugin_name}")
                    else:
                        self.logger.warning(f"Plugin {plugin_name} failed validation")
                        
                except Exception as e:
                    self.load_errors[entry_point.name] = str(e)
                    self.logger.error(f"Failed to load plugin {entry_point.name}: {e}")
            
            # Load built-in plugins
            builtin_plugins = await self._discover_builtin_plugins()
            discovered.update(builtin_plugins)
            
            self.discovered_plugins = discovered
            self.logger.info(f"Discovered {len(discovered)} visualizer plugins")
            
            return discovered
            
        except Exception as e:
            self.logger.error(f"Plugin discovery failed: {e}")
            return {}
    
    async def _discover_builtin_plugins(self) -> Dict[str, Type[BaseVisualizer]]:
        """Discover built-in visualizer plugins."""
        builtin_plugins = {}
        
        try:
            # Import built-in plugin modules
            from ..plugins import (
                line_chart, bar_chart, scatter_plot, heatmap,
                gauge, time_series, histogram, pie_chart
            )
            
            # Map module names to plugin classes
            plugin_modules = {
                'line_chart': line_chart.LineChartVisualizer,
                'bar_chart': bar_chart.BarChartVisualizer,
                'scatter_plot': scatter_plot.ScatterPlotVisualizer,
                'heatmap': heatmap.HeatmapVisualizer,
                'gauge': gauge.GaugeVisualizer,
                'time_series': time_series.TimeSeriesVisualizer,
                'histogram': histogram.HistogramVisualizer,
                'pie_chart': pie_chart.PieChartVisualizer,
            }
            
            for plugin_name, plugin_class in plugin_modules.items():
                if self._validate_plugin(plugin_class, plugin_name):
                    builtin_plugins[plugin_name] = plugin_class
                    
                    # Store metadata for built-in plugins
                    self.plugin_metadata[plugin_name] = {
                        'entry_point': None,
                        'module': plugin_class.__module__,
                        'class_name': plugin_class.__name__,
                        'loaded_at': datetime.now(timezone.utc),
                        'version': getattr(plugin_class, '__version__', '1.0.0'),
                        'description': getattr(plugin_class, '__doc__', '').strip(),
                        'builtin': True
                    }
                    
                    self.logger.debug(f"Loaded built-in plugin: {plugin_name}")
            
            self.logger.info(f"Loaded {len(builtin_plugins)} built-in plugins")
            
        except ImportError as e:
            self.logger.warning(f"Some built-in plugins not available: {e}")
        except Exception as e:
            self.logger.error(f"Error loading built-in plugins: {e}")
        
        return builtin_plugins
    
    def _validate_plugin(self, plugin_class: Type, plugin_name: str) -> bool:
        """
        Validate that a plugin class implements the required interface.
        
        Args:
            plugin_class: Plugin class to validate
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin is valid
        """
        try:
            # Check if it's a class
            if not inspect.isclass(plugin_class):
                self.logger.error(f"Plugin {plugin_name} is not a class")
                return False
            
            # Check inheritance from BaseVisualizer
            if not issubclass(plugin_class, BaseVisualizer):
                self.logger.error(f"Plugin {plugin_name} does not inherit from BaseVisualizer")
                return False
            
            # Check for required draw method
            if not hasattr(plugin_class, 'draw'):
                self.logger.error(f"Plugin {plugin_name} missing draw method")
                return False
            
            # Check draw method signature
            draw_method = getattr(plugin_class, 'draw')
            if not callable(draw_method):
                self.logger.error(f"Plugin {plugin_name} draw is not callable")
                return False
            
            # Validate draw method signature
            sig = inspect.signature(draw_method)
            params = list(sig.parameters.keys())
            
            # Expected: self, ax, data (and possibly **kwargs)
            if len(params) < 3 or params[1] != 'ax' or params[2] != 'data':
                self.logger.error(f"Plugin {plugin_name} draw method has invalid signature: {params}")
                return False
            
            # Check for required metadata
            required_attrs = ['name', 'description']
            for attr in required_attrs:
                if not hasattr(plugin_class, attr):
                    self.logger.warning(f"Plugin {plugin_name} missing recommended attribute: {attr}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating plugin {plugin_name}: {e}")
            return False
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin information dictionary
        """
        if plugin_name not in self.plugin_metadata:
            return None
        
        metadata = self.plugin_metadata[plugin_name].copy()
        
        # Add runtime information
        if plugin_name in self.discovered_plugins:
            plugin_class = self.discovered_plugins[plugin_name]
            metadata.update({
                'available': True,
                'supports_real_time': getattr(plugin_class, 'supports_real_time', False),
                'supports_interaction': getattr(plugin_class, 'supports_interaction', False),
                'data_types': getattr(plugin_class, 'supported_data_types', []),
                'config_schema': getattr(plugin_class, 'config_schema', {}),
            })
        else:
            metadata['available'] = False
        
        return metadata
    
    def list_plugins(self) -> List[str]:
        """
        Get list of all discovered plugin names.
        
        Returns:
            List of plugin names
        """
        return list(self.discovered_plugins.keys())
    
    def get_plugin_class(self, plugin_name: str) -> Optional[Type[BaseVisualizer]]:
        """
        Get plugin class by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin class or None if not found
        """
        return self.discovered_plugins.get(plugin_name)
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            
        Returns:
            True if reload successful
        """
        try:
            if plugin_name not in self.plugin_metadata:
                self.logger.error(f"Plugin {plugin_name} not found")
                return False
            
            metadata = self.plugin_metadata[plugin_name]
            
            # Skip built-in plugins
            if metadata.get('builtin', False):
                self.logger.warning(f"Cannot reload built-in plugin {plugin_name}")
                return False
            
            entry_point = metadata.get('entry_point')
            if not entry_point:
                self.logger.error(f"No entry point for plugin {plugin_name}")
                return False
            
            # Reload the module
            module_name = metadata['module']
            if module_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[module_name])
            
            # Reload the plugin class
            plugin_class = entry_point.load()
            
            if self._validate_plugin(plugin_class, plugin_name):
                self.discovered_plugins[plugin_name] = plugin_class
                metadata['loaded_at'] = datetime.now(timezone.utc)
                
                self.logger.info(f"Reloaded plugin: {plugin_name}")
                return True
            else:
                self.logger.error(f"Plugin {plugin_name} failed validation after reload")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False
    
    def get_load_errors(self) -> Dict[str, str]:
        """
        Get plugin load errors.
        
        Returns:
            Dictionary mapping plugin names to error messages
        """
        return self.load_errors.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_plugins = len(self.discovered_plugins)
        builtin_plugins = sum(1 for meta in self.plugin_metadata.values() 
                             if meta.get('builtin', False))
        external_plugins = total_plugins - builtin_plugins
        
        return {
            'total_plugins': total_plugins,
            'builtin_plugins': builtin_plugins,
            'external_plugins': external_plugins,
            'load_errors': len(self.load_errors),
            'entry_point_group': self.ENTRY_POINT_GROUP,
            'plugin_names': list(self.discovered_plugins.keys())
        }
