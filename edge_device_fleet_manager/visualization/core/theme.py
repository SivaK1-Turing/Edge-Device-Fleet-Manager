"""
Theme Manager

Manages visualization themes, styling, and appearance customization
for consistent visual design across all charts and dashboards.
"""

from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.axes
from matplotlib import rcParams
import json
from pathlib import Path

from ...core.logging import get_logger

logger = get_logger(__name__)


class ThemeManager:
    """
    Theme manager for visualization styling and appearance.
    
    Provides theme loading, application, and customization capabilities
    for consistent visual design across all visualizations.
    """
    
    def __init__(self):
        """Initialize theme manager."""
        self.themes = {}
        self.current_theme = 'default'
        self.custom_themes = {}
        
        self.logger = get_logger(f"{__name__}.ThemeManager")
        
        # Load default themes
        self._load_default_themes()
    
    async def load_themes(self) -> None:
        """Load themes from configuration files."""
        try:
            # Load built-in themes
            self._load_default_themes()
            
            # Load custom themes from files
            await self._load_custom_themes()
            
            self.logger.info(f"Loaded {len(self.themes)} themes")
            
        except Exception as e:
            self.logger.error(f"Failed to load themes: {e}")
    
    def _load_default_themes(self) -> None:
        """Load default built-in themes."""
        # Default theme
        self.themes['default'] = {
            'name': 'Default',
            'description': 'Default matplotlib theme',
            'colors': {
                'primary': '#1f77b4',
                'secondary': '#ff7f0e',
                'success': '#2ca02c',
                'warning': '#d62728',
                'info': '#9467bd',
                'background': '#ffffff',
                'text': '#000000',
                'grid': '#cccccc'
            },
            'fonts': {
                'family': 'sans-serif',
                'size': 10,
                'title_size': 14,
                'label_size': 12
            },
            'style': {
                'grid_alpha': 0.3,
                'line_width': 2.0,
                'marker_size': 6,
                'figure_facecolor': '#ffffff',
                'axes_facecolor': '#ffffff'
            }
        }
        
        # Dark theme
        self.themes['dark'] = {
            'name': 'Dark',
            'description': 'Dark theme for low-light environments',
            'colors': {
                'primary': '#8dd3c7',
                'secondary': '#ffffb3',
                'success': '#bebada',
                'warning': '#fb8072',
                'info': '#80b1d3',
                'background': '#2e2e2e',
                'text': '#ffffff',
                'grid': '#555555'
            },
            'fonts': {
                'family': 'sans-serif',
                'size': 10,
                'title_size': 14,
                'label_size': 12
            },
            'style': {
                'grid_alpha': 0.3,
                'line_width': 2.0,
                'marker_size': 6,
                'figure_facecolor': '#2e2e2e',
                'axes_facecolor': '#2e2e2e'
            }
        }
        
        # Professional theme
        self.themes['professional'] = {
            'name': 'Professional',
            'description': 'Clean professional theme for presentations',
            'colors': {
                'primary': '#003f5c',
                'secondary': '#2f4b7c',
                'success': '#665191',
                'warning': '#a05195',
                'info': '#d45087',
                'background': '#ffffff',
                'text': '#333333',
                'grid': '#e0e0e0'
            },
            'fonts': {
                'family': 'serif',
                'size': 11,
                'title_size': 16,
                'label_size': 13
            },
            'style': {
                'grid_alpha': 0.2,
                'line_width': 2.5,
                'marker_size': 7,
                'figure_facecolor': '#ffffff',
                'axes_facecolor': '#ffffff'
            }
        }
        
        # Colorful theme
        self.themes['colorful'] = {
            'name': 'Colorful',
            'description': 'Vibrant colorful theme for engaging visualizations',
            'colors': {
                'primary': '#e41a1c',
                'secondary': '#377eb8',
                'success': '#4daf4a',
                'warning': '#ff7f00',
                'info': '#984ea3',
                'background': '#ffffff',
                'text': '#000000',
                'grid': '#f0f0f0'
            },
            'fonts': {
                'family': 'sans-serif',
                'size': 10,
                'title_size': 14,
                'label_size': 12
            },
            'style': {
                'grid_alpha': 0.4,
                'line_width': 2.0,
                'marker_size': 8,
                'figure_facecolor': '#ffffff',
                'axes_facecolor': '#ffffff'
            }
        }
    
    async def _load_custom_themes(self) -> None:
        """Load custom themes from configuration files."""
        try:
            # Look for theme files in config directory
            config_dir = Path('config/themes')
            if config_dir.exists():
                for theme_file in config_dir.glob('*.json'):
                    try:
                        with open(theme_file, 'r') as f:
                            theme_data = json.load(f)
                        
                        theme_name = theme_file.stem
                        self.themes[theme_name] = theme_data
                        self.custom_themes[theme_name] = theme_data
                        
                        self.logger.debug(f"Loaded custom theme: {theme_name}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to load theme {theme_file}: {e}")
            
        except Exception as e:
            self.logger.warning(f"Could not load custom themes: {e}")
    
    def apply_theme(self, figure: plt.Figure, ax: matplotlib.axes.Axes, 
                   theme_name: Optional[str] = None) -> None:
        """
        Apply theme to figure and axes.
        
        Args:
            figure: Matplotlib figure
            ax: Matplotlib axes
            theme_name: Name of theme to apply (uses current if None)
        """
        try:
            theme_name = theme_name or self.current_theme
            
            if theme_name not in self.themes:
                self.logger.warning(f"Theme {theme_name} not found, using default")
                theme_name = 'default'
            
            theme = self.themes[theme_name]
            
            # Apply figure styling
            self._apply_figure_style(figure, theme)
            
            # Apply axes styling
            self._apply_axes_style(ax, theme)
            
            self.logger.debug(f"Applied theme: {theme_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply theme {theme_name}: {e}")
    
    def _apply_figure_style(self, figure: plt.Figure, theme: Dict[str, Any]) -> None:
        """Apply theme styling to figure."""
        style = theme.get('style', {})
        colors = theme.get('colors', {})
        
        # Set figure background
        figure_bg = style.get('figure_facecolor', colors.get('background', '#ffffff'))
        figure.patch.set_facecolor(figure_bg)
        
        # Set figure text color
        text_color = colors.get('text', '#000000')
        rcParams['text.color'] = text_color
    
    def _apply_axes_style(self, ax: matplotlib.axes.Axes, theme: Dict[str, Any]) -> None:
        """Apply theme styling to axes."""
        colors = theme.get('colors', {})
        fonts = theme.get('fonts', {})
        style = theme.get('style', {})
        
        # Set axes background
        axes_bg = style.get('axes_facecolor', colors.get('background', '#ffffff'))
        ax.set_facecolor(axes_bg)
        
        # Set text colors
        text_color = colors.get('text', '#000000')
        ax.tick_params(colors=text_color, labelcolor=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        
        # Set grid styling
        grid_color = colors.get('grid', '#cccccc')
        grid_alpha = style.get('grid_alpha', 0.3)
        ax.grid(True, color=grid_color, alpha=grid_alpha)
        
        # Set font properties
        font_family = fonts.get('family', 'sans-serif')
        font_size = fonts.get('size', 10)
        title_size = fonts.get('title_size', 14)
        label_size = fonts.get('label_size', 12)
        
        ax.tick_params(labelsize=font_size)
        ax.xaxis.label.set_fontsize(label_size)
        ax.yaxis.label.set_fontsize(label_size)
        ax.title.set_fontsize(title_size)
        
        # Set spine colors
        for spine in ax.spines.values():
            spine.set_color(text_color)
    
    def set_current_theme(self, theme_name: str) -> bool:
        """
        Set the current default theme.
        
        Args:
            theme_name: Name of theme to set as current
            
        Returns:
            True if theme was set successfully
        """
        if theme_name not in self.themes:
            self.logger.error(f"Theme {theme_name} not found")
            return False
        
        self.current_theme = theme_name
        self.logger.info(f"Current theme set to: {theme_name}")
        return True
    
    def get_theme_colors(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get color palette for a theme.
        
        Args:
            theme_name: Name of theme (uses current if None)
            
        Returns:
            Dictionary of color names to hex values
        """
        theme_name = theme_name or self.current_theme
        
        if theme_name not in self.themes:
            theme_name = 'default'
        
        return self.themes[theme_name].get('colors', {}).copy()
    
    def get_color_palette(self, theme_name: Optional[str] = None, n_colors: int = 10) -> List[str]:
        """
        Get color palette as list of colors.
        
        Args:
            theme_name: Name of theme (uses current if None)
            n_colors: Number of colors needed
            
        Returns:
            List of color hex values
        """
        colors = self.get_theme_colors(theme_name)
        
        # Extract main colors
        palette = [
            colors.get('primary', '#1f77b4'),
            colors.get('secondary', '#ff7f0e'),
            colors.get('success', '#2ca02c'),
            colors.get('warning', '#d62728'),
            colors.get('info', '#9467bd'),
        ]
        
        # Extend palette if needed
        while len(palette) < n_colors:
            palette.extend(palette)
        
        return palette[:n_colors]
    
    def create_custom_theme(self, name: str, theme_data: Dict[str, Any]) -> bool:
        """
        Create a custom theme.
        
        Args:
            name: Name for the custom theme
            theme_data: Theme configuration dictionary
            
        Returns:
            True if theme was created successfully
        """
        try:
            # Validate theme data structure
            required_keys = ['colors', 'fonts', 'style']
            for key in required_keys:
                if key not in theme_data:
                    raise ValueError(f"Missing required theme key: {key}")
            
            # Add theme
            self.themes[name] = theme_data
            self.custom_themes[name] = theme_data
            
            self.logger.info(f"Created custom theme: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create custom theme {name}: {e}")
            return False
    
    def save_custom_theme(self, name: str, file_path: Optional[str] = None) -> bool:
        """
        Save a custom theme to file.
        
        Args:
            name: Name of theme to save
            file_path: Optional file path (auto-generated if None)
            
        Returns:
            True if theme was saved successfully
        """
        try:
            if name not in self.custom_themes:
                self.logger.error(f"Custom theme {name} not found")
                return False
            
            if file_path is None:
                config_dir = Path('config/themes')
                config_dir.mkdir(parents=True, exist_ok=True)
                file_path = config_dir / f"{name}.json"
            
            with open(file_path, 'w') as f:
                json.dump(self.custom_themes[name], f, indent=2)
            
            self.logger.info(f"Saved custom theme {name} to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save custom theme {name}: {e}")
            return False
    
    def list_themes(self) -> List[str]:
        """
        Get list of available theme names.
        
        Returns:
            List of theme names
        """
        return list(self.themes.keys())
    
    def get_theme_info(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a theme.
        
        Args:
            theme_name: Name of theme
            
        Returns:
            Theme information dictionary
        """
        if theme_name not in self.themes:
            return None
        
        theme = self.themes[theme_name].copy()
        theme['is_custom'] = theme_name in self.custom_themes
        return theme
    
    def delete_custom_theme(self, name: str) -> bool:
        """
        Delete a custom theme.
        
        Args:
            name: Name of custom theme to delete
            
        Returns:
            True if theme was deleted successfully
        """
        try:
            if name not in self.custom_themes:
                self.logger.error(f"Custom theme {name} not found")
                return False
            
            # Remove from both dictionaries
            del self.themes[name]
            del self.custom_themes[name]
            
            # If this was the current theme, reset to default
            if self.current_theme == name:
                self.current_theme = 'default'
            
            self.logger.info(f"Deleted custom theme: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete custom theme {name}: {e}")
            return False
