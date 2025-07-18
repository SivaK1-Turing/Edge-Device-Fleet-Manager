"""
Visualizer Registry

Central registry for managing visualizer plugins with registration,
discovery, and lifecycle management capabilities.
"""

from typing import Dict, List, Type, Optional, Any
from datetime import datetime, timezone
import threading

from ...core.logging import get_logger
from .base import BaseVisualizer

logger = get_logger(__name__)


class VisualizerRegistry:
    """
    Central registry for visualizer plugins.
    
    Manages registration, discovery, and lifecycle of visualizer plugins
    with thread-safe operations and metadata tracking.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize registry if not already initialized."""
        if hasattr(self, '_initialized'):
            return
        
        self._visualizers = {}
        self._metadata = {}
        self._aliases = {}
        self._categories = {}
        self._lock = threading.RLock()
        self._initialized = True
        
        self.logger = get_logger(f"{__name__}.VisualizerRegistry")
        self.logger.info("Visualizer registry initialized")
    
    def register(self, name: str, visualizer_class: Type[BaseVisualizer], 
                category: Optional[str] = None, aliases: Optional[List[str]] = None) -> bool:
        """
        Register a visualizer plugin.
        
        Args:
            name: Unique name for the visualizer
            visualizer_class: Visualizer class that inherits from BaseVisualizer
            category: Optional category for grouping
            aliases: Optional list of alternative names
            
        Returns:
            True if registration successful
        """
        with self._lock:
            try:
                # Validate visualizer class
                if not self._validate_visualizer_class(visualizer_class, name):
                    return False
                
                # Check for name conflicts
                if name in self._visualizers:
                    self.logger.warning(f"Visualizer {name} already registered, overwriting")
                
                # Register the visualizer
                self._visualizers[name] = visualizer_class
                
                # Store metadata
                self._metadata[name] = {
                    'class': visualizer_class,
                    'name': getattr(visualizer_class, 'name', name),
                    'description': getattr(visualizer_class, 'description', ''),
                    'version': getattr(visualizer_class, 'version', '1.0.0'),
                    'category': category or 'general',
                    'supports_real_time': getattr(visualizer_class, 'supports_real_time', False),
                    'supports_interaction': getattr(visualizer_class, 'supports_interaction', False),
                    'supported_data_types': getattr(visualizer_class, 'supported_data_types', []),
                    'config_schema': getattr(visualizer_class, 'config_schema', {}),
                    'registered_at': datetime.now(timezone.utc),
                    'aliases': aliases or []
                }
                
                # Register category
                if category:
                    if category not in self._categories:
                        self._categories[category] = []
                    if name not in self._categories[category]:
                        self._categories[category].append(name)
                
                # Register aliases
                if aliases:
                    for alias in aliases:
                        if alias in self._aliases:
                            self.logger.warning(f"Alias {alias} already exists, overwriting")
                        self._aliases[alias] = name
                
                self.logger.info(f"Registered visualizer: {name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register visualizer {name}: {e}")
                return False
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a visualizer plugin.
        
        Args:
            name: Name of the visualizer to unregister
            
        Returns:
            True if unregistration successful
        """
        with self._lock:
            try:
                if name not in self._visualizers:
                    self.logger.warning(f"Visualizer {name} not found for unregistration")
                    return False
                
                # Get metadata before removal
                metadata = self._metadata.get(name, {})
                
                # Remove from main registry
                del self._visualizers[name]
                del self._metadata[name]
                
                # Remove from category
                category = metadata.get('category')
                if category and category in self._categories:
                    if name in self._categories[category]:
                        self._categories[category].remove(name)
                    if not self._categories[category]:
                        del self._categories[category]
                
                # Remove aliases
                aliases = metadata.get('aliases', [])
                for alias in aliases:
                    if alias in self._aliases and self._aliases[alias] == name:
                        del self._aliases[alias]
                
                self.logger.info(f"Unregistered visualizer: {name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister visualizer {name}: {e}")
                return False
    
    def get(self, name: str) -> Optional[Type[BaseVisualizer]]:
        """
        Get a visualizer class by name or alias.
        
        Args:
            name: Name or alias of the visualizer
            
        Returns:
            Visualizer class or None if not found
        """
        with self._lock:
            # Check direct name
            if name in self._visualizers:
                return self._visualizers[name]
            
            # Check aliases
            if name in self._aliases:
                actual_name = self._aliases[name]
                return self._visualizers.get(actual_name)
            
            return None
    
    def list_visualizers(self) -> List[str]:
        """
        Get list of all registered visualizer names.
        
        Returns:
            List of visualizer names
        """
        with self._lock:
            return list(self._visualizers.keys())
    
    def list_by_category(self, category: str) -> List[str]:
        """
        Get list of visualizers in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of visualizer names in the category
        """
        with self._lock:
            return self._categories.get(category, []).copy()
    
    def get_categories(self) -> List[str]:
        """
        Get list of all categories.
        
        Returns:
            List of category names
        """
        with self._lock:
            return list(self._categories.keys())
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a visualizer.
        
        Args:
            name: Name of the visualizer
            
        Returns:
            Metadata dictionary or None if not found
        """
        with self._lock:
            # Resolve alias if needed
            if name in self._aliases:
                name = self._aliases[name]
            
            if name in self._metadata:
                return self._metadata[name].copy()
            
            return None
    
    def search(self, query: str) -> List[str]:
        """
        Search for visualizers by name, description, or category.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching visualizer names
        """
        with self._lock:
            query_lower = query.lower()
            matches = []
            
            for name, metadata in self._metadata.items():
                # Search in name
                if query_lower in name.lower():
                    matches.append(name)
                    continue
                
                # Search in description
                description = metadata.get('description', '').lower()
                if query_lower in description:
                    matches.append(name)
                    continue
                
                # Search in category
                category = metadata.get('category', '').lower()
                if query_lower in category:
                    matches.append(name)
                    continue
                
                # Search in aliases
                aliases = metadata.get('aliases', [])
                for alias in aliases:
                    if query_lower in alias.lower():
                        matches.append(name)
                        break
            
            return matches
    
    def get_by_data_type(self, data_type: str) -> List[str]:
        """
        Get visualizers that support a specific data type.
        
        Args:
            data_type: Data type to search for
            
        Returns:
            List of visualizer names that support the data type
        """
        with self._lock:
            matches = []
            
            for name, metadata in self._metadata.items():
                supported_types = metadata.get('supported_data_types', [])
                if data_type in supported_types:
                    matches.append(name)
            
            return matches
    
    def get_real_time_visualizers(self) -> List[str]:
        """
        Get visualizers that support real-time updates.
        
        Returns:
            List of real-time capable visualizer names
        """
        with self._lock:
            matches = []
            
            for name, metadata in self._metadata.items():
                if metadata.get('supports_real_time', False):
                    matches.append(name)
            
            return matches
    
    def get_interactive_visualizers(self) -> List[str]:
        """
        Get visualizers that support interaction.
        
        Returns:
            List of interactive visualizer names
        """
        with self._lock:
            matches = []
            
            for name, metadata in self._metadata.items():
                if metadata.get('supports_interaction', False):
                    matches.append(name)
            
            return matches
    
    def clear(self) -> None:
        """Clear all registered visualizers."""
        with self._lock:
            self._visualizers.clear()
            self._metadata.clear()
            self._aliases.clear()
            self._categories.clear()
            self.logger.info("Registry cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            total_visualizers = len(self._visualizers)
            total_aliases = len(self._aliases)
            total_categories = len(self._categories)
            
            real_time_count = len(self.get_real_time_visualizers())
            interactive_count = len(self.get_interactive_visualizers())
            
            return {
                'total_visualizers': total_visualizers,
                'total_aliases': total_aliases,
                'total_categories': total_categories,
                'real_time_visualizers': real_time_count,
                'interactive_visualizers': interactive_count,
                'categories': dict(self._categories),
                'visualizer_names': list(self._visualizers.keys())
            }
    
    def _validate_visualizer_class(self, visualizer_class: Type, name: str) -> bool:
        """
        Validate that a class is a proper visualizer.
        
        Args:
            visualizer_class: Class to validate
            name: Name for error reporting
            
        Returns:
            True if valid
        """
        try:
            # Check if it's a class
            if not isinstance(visualizer_class, type):
                self.logger.error(f"Visualizer {name} is not a class")
                return False
            
            # Check inheritance
            if not issubclass(visualizer_class, BaseVisualizer):
                self.logger.error(f"Visualizer {name} does not inherit from BaseVisualizer")
                return False
            
            # Check for required methods
            if not hasattr(visualizer_class, 'draw'):
                self.logger.error(f"Visualizer {name} missing draw method")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating visualizer {name}: {e}")
            return False
