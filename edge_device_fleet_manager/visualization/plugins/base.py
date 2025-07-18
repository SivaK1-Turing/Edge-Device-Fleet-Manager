"""
Base Visualizer

Abstract base class for all visualizer plugins. Defines the standard
interface that all visualizers must implement with draw(ax, data) method.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.axes
import numpy as np
import pandas as pd

from ...core.logging import get_logger

logger = get_logger(__name__)


class BaseVisualizer(ABC):
    """
    Abstract base class for all visualizer plugins.
    
    All visualizer plugins must inherit from this class and implement
    the draw(ax, data) method. Provides common functionality and
    standardized interface for the plugin system.
    """
    
    # Plugin metadata (should be overridden in subclasses)
    name = "Base Visualizer"
    description = "Abstract base visualizer"
    version = "1.0.0"
    
    # Plugin capabilities
    supports_real_time = False
    supports_interaction = False
    supported_data_types = ['dict', 'list', 'pandas.DataFrame', 'numpy.ndarray']
    
    # Configuration schema (JSON Schema format)
    config_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": ""},
            "xlabel": {"type": "string", "default": ""},
            "ylabel": {"type": "string", "default": ""},
            "color": {"type": "string", "default": "auto"},
            "style": {"type": "string", "default": "default"},
            "grid": {"type": "boolean", "default": True},
            "legend": {"type": "boolean", "default": True}
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize visualizer with configuration.
        
        Args:
            config: Visualizer configuration dictionary
        """
        self.config = self._merge_config(config or {})
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Runtime state
        self._last_render_time = None
        self._render_count = 0
        self._data_cache = None
        self._cache_timestamp = None
        
        # Validation
        self._validate_config()
    
    def _merge_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user configuration with defaults from schema.
        
        Args:
            user_config: User-provided configuration
            
        Returns:
            Merged configuration dictionary
        """
        # Extract defaults from schema
        defaults = {}
        if 'properties' in self.config_schema:
            for key, prop in self.config_schema['properties'].items():
                if 'default' in prop:
                    defaults[key] = prop['default']
        
        # Merge with user config
        merged = defaults.copy()
        merged.update(user_config)
        
        return merged
    
    def _validate_config(self) -> None:
        """Validate configuration against schema."""
        # Basic validation - could be extended with jsonschema library
        if 'properties' in self.config_schema:
            for key, prop in self.config_schema['properties'].items():
                if key in self.config:
                    value = self.config[key]
                    expected_type = prop.get('type')
                    
                    # Type checking
                    if expected_type == 'string' and not isinstance(value, str):
                        self.logger.warning(f"Config {key} should be string, got {type(value)}")
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        self.logger.warning(f"Config {key} should be boolean, got {type(value)}")
                    elif expected_type == 'number' and not isinstance(value, (int, float)):
                        self.logger.warning(f"Config {key} should be number, got {type(value)}")
    
    @abstractmethod
    async def draw(self, ax: matplotlib.axes.Axes, data: Any) -> None:
        """
        Draw the visualization on the provided axes.
        
        This is the main method that all visualizer plugins must implement.
        It receives matplotlib axes and data, and should render the visualization.
        
        Args:
            ax: Matplotlib axes to draw on
            data: Data to visualize (format depends on visualizer)
        """
        pass
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update visualizer configuration.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        self._validate_config()
        self.logger.debug(f"Updated config: {new_config}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Current configuration dictionary
        """
        return self.config.copy()
    
    def validate_data(self, data: Any) -> bool:
        """
        Validate that data is in expected format.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid
        """
        try:
            # Check if data type is supported
            data_type = type(data).__name__
            if hasattr(data, '__module__'):
                data_type = f"{data.__module__}.{data_type}"
            
            # Basic type checking
            if isinstance(data, dict):
                return 'dict' in self.supported_data_types
            elif isinstance(data, list):
                return 'list' in self.supported_data_types
            elif hasattr(data, '__module__') and 'pandas' in data.__module__:
                return 'pandas.DataFrame' in self.supported_data_types
            elif hasattr(data, '__module__') and 'numpy' in data.__module__:
                return 'numpy.ndarray' in self.supported_data_types
            else:
                self.logger.warning(f"Unknown data type: {data_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating data: {e}")
            return False
    
    def preprocess_data(self, data: Any) -> Any:
        """
        Preprocess data before visualization.
        
        Override this method to implement custom data preprocessing.
        
        Args:
            data: Raw data
            
        Returns:
            Processed data
        """
        return data
    
    def apply_styling(self, ax: matplotlib.axes.Axes) -> None:
        """
        Apply common styling to the axes.
        
        Args:
            ax: Matplotlib axes to style
        """
        # Apply title
        if self.config.get('title'):
            ax.set_title(self.config['title'])
        
        # Apply axis labels
        if self.config.get('xlabel'):
            ax.set_xlabel(self.config['xlabel'])
        
        if self.config.get('ylabel'):
            ax.set_ylabel(self.config['ylabel'])
        
        # Apply grid
        if self.config.get('grid', True):
            ax.grid(True, alpha=0.3)
        
        # Apply legend if requested and if there are labeled elements
        if self.config.get('legend', True):
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                ax.legend()
    
    def get_color_palette(self, n_colors: int = 10) -> List[str]:
        """
        Get color palette for visualization.
        
        Args:
            n_colors: Number of colors needed
            
        Returns:
            List of color strings
        """
        if self.config.get('color') != 'auto':
            # Use specified color
            return [self.config['color']] * n_colors
        
        # Use default matplotlib color cycle
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']
        
        # Extend if needed
        while len(colors) < n_colors:
            colors.extend(colors)
        
        return colors[:n_colors]
    
    def cache_data(self, data: Any, ttl_seconds: int = 60) -> None:
        """
        Cache data for performance optimization.
        
        Args:
            data: Data to cache
            ttl_seconds: Time to live in seconds
        """
        from datetime import datetime, timezone
        
        self._data_cache = data
        self._cache_timestamp = datetime.now(timezone.utc)
        
        # Schedule cache cleanup
        if hasattr(self, '_cache_cleanup_task'):
            self._cache_cleanup_task.cancel()
        
        async def cleanup():
            await asyncio.sleep(ttl_seconds)
            self._data_cache = None
            self._cache_timestamp = None
        
        self._cache_cleanup_task = asyncio.create_task(cleanup())
    
    def get_cached_data(self) -> Optional[Any]:
        """
        Get cached data if available and valid.
        
        Returns:
            Cached data or None
        """
        if self._data_cache is None or self._cache_timestamp is None:
            return None
        
        from datetime import datetime, timezone, timedelta
        
        # Check if cache is still valid (default 60 seconds)
        if datetime.now(timezone.utc) - self._cache_timestamp > timedelta(seconds=60):
            self._data_cache = None
            self._cache_timestamp = None
            return None
        
        return self._data_cache
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get visualizer statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'name': self.name,
            'version': self.version,
            'render_count': self._render_count,
            'last_render_time': self._last_render_time.isoformat() if self._last_render_time else None,
            'supports_real_time': self.supports_real_time,
            'supports_interaction': self.supports_interaction,
            'supported_data_types': self.supported_data_types,
            'has_cached_data': self._data_cache is not None
        }
    
    def __repr__(self) -> str:
        """String representation of the visualizer."""
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
