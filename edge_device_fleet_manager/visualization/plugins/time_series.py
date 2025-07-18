"""
Time Series Visualizer

Specialized plugin for time series data with advanced features like
multiple metrics, time range selection, and real-time updates.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.axes
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from .base import BaseVisualizer


class TimeSeriesVisualizer(BaseVisualizer):
    """
    Time series visualizer plugin.
    
    Specialized for temporal data with features like time axis formatting,
    multiple metrics, anomaly detection, and real-time streaming.
    """
    
    name = "Time Series"
    description = "Time series visualizer for temporal data analysis"
    version = "1.0.0"
    
    supports_real_time = True
    supports_interaction = True
    supported_data_types = ['dict', 'pandas.DataFrame', 'numpy.ndarray']
    
    config_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Time Series"},
            "xlabel": {"type": "string", "default": "Time"},
            "ylabel": {"type": "string", "default": "Value"},
            "color": {"type": "string", "default": "auto"},
            "line_style": {"type": "string", "default": "-"},
            "line_width": {"type": "number", "default": 2.0},
            "marker": {"type": "string", "default": "none"},
            "alpha": {"type": "number", "default": 1.0},
            "grid": {"type": "boolean", "default": True},
            "legend": {"type": "boolean", "default": True},
            "time_column": {"type": "string", "default": "timestamp"},
            "value_column": {"type": "string", "default": "value"},
            "metric_column": {"type": "string", "default": "metric"},
            "time_format": {"type": "string", "default": "auto"},
            "show_anomalies": {"type": "boolean", "default": False},
            "anomaly_threshold": {"type": "number", "default": 2.0},
            "rolling_window": {"type": "number", "default": 0},
            "fill_missing": {"type": "boolean", "default": True},
            "resample_freq": {"type": "string", "default": "none"},
            "aggregation": {"type": "string", "default": "mean", "enum": ["mean", "sum", "min", "max", "count"]}
        }
    }
    
    async def draw(self, ax: matplotlib.axes.Axes, data: Any) -> None:
        """
        Draw time series chart on the provided axes.
        
        Args:
            ax: Matplotlib axes to draw on
            data: Time series data to visualize
        """
        try:
            # Update render statistics
            self._render_count += 1
            self._last_render_time = datetime.now(timezone.utc)
            
            # Validate and preprocess data
            if not self.validate_data(data):
                raise ValueError("Invalid data format for time series")
            
            processed_data = self.preprocess_data(data)
            
            # Handle different data formats
            if isinstance(processed_data, pd.DataFrame):
                await self._draw_dataframe(ax, processed_data)
            elif isinstance(processed_data, dict):
                await self._draw_dict(ax, processed_data)
            elif isinstance(processed_data, np.ndarray):
                await self._draw_array(ax, processed_data)
            else:
                raise ValueError(f"Unsupported data type: {type(processed_data)}")
            
            # Format time axis
            self._format_time_axis(ax)
            
            # Apply styling
            self.apply_styling(ax)
            
            self.logger.debug(f"Rendered time series with {self._render_count} total renders")
            
        except Exception as e:
            self.logger.error(f"Error drawing time series: {e}")
            # Draw error message on axes
            ax.text(0.5, 0.5, f"Error: {str(e)}", 
                   transform=ax.transAxes, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3))
            raise
    
    async def _draw_dataframe(self, ax: matplotlib.axes.Axes, df: pd.DataFrame) -> None:
        """Draw time series from pandas DataFrame."""
        time_col = self.config.get('time_column', 'timestamp')
        value_col = self.config.get('value_column', 'value')
        metric_col = self.config.get('metric_column', 'metric')
        
        # Ensure time column is datetime
        if time_col in df.columns:
            df[time_col] = pd.to_datetime(df[time_col])
        else:
            # Use index if it's datetime, otherwise create time index
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                time_col = df.columns[0]
            else:
                # Create synthetic time index
                df[time_col] = pd.date_range(start='2024-01-01', periods=len(df), freq='1min')
        
        # Check if we have multiple metrics
        if metric_col in df.columns and len(df[metric_col].unique()) > 1:
            await self._draw_multiple_metrics_df(ax, df, time_col, value_col, metric_col)
        else:
            await self._draw_single_metric_df(ax, df, time_col, value_col)
    
    async def _draw_single_metric_df(self, ax: matplotlib.axes.Axes, 
                                   df: pd.DataFrame, time_col: str, value_col: str) -> None:
        """Draw single metric time series."""
        # Sort by time
        df_sorted = df.sort_values(time_col)
        
        time_data = df_sorted[time_col]
        value_data = df_sorted[value_col] if value_col in df_sorted.columns else df_sorted.iloc[:, -1]
        
        # Apply resampling if requested
        if self.config.get('resample_freq', 'none') != 'none':
            time_data, value_data = self._resample_data(time_data, value_data)
        
        # Apply rolling window if requested
        if self.config.get('rolling_window', 0) > 0:
            value_data = self._apply_rolling_window(value_data)
        
        # Fill missing values if requested
        if self.config.get('fill_missing', True):
            value_data = value_data.fillna(method='forward').fillna(method='backward')
        
        # Plot main line
        color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
        line = ax.plot(time_data, value_data,
                      linestyle=self.config.get('line_style', '-'),
                      linewidth=self.config.get('line_width', 2.0),
                      marker=self.config.get('marker', 'none'),
                      alpha=self.config.get('alpha', 1.0),
                      color=color)
        
        # Detect and show anomalies if requested
        if self.config.get('show_anomalies', False):
            await self._detect_and_show_anomalies(ax, time_data, value_data, color)
    
    async def _draw_multiple_metrics_df(self, ax: matplotlib.axes.Axes, 
                                      df: pd.DataFrame, time_col: str, value_col: str, metric_col: str) -> None:
        """Draw multiple metrics time series."""
        metrics = df[metric_col].unique()
        colors = self.get_color_palette(len(metrics))
        
        for i, metric in enumerate(metrics):
            metric_data = df[df[metric_col] == metric].sort_values(time_col)
            
            if len(metric_data) == 0:
                continue
            
            time_data = metric_data[time_col]
            value_data = metric_data[value_col]
            
            # Apply resampling if requested
            if self.config.get('resample_freq', 'none') != 'none':
                time_data, value_data = self._resample_data(time_data, value_data)
            
            # Apply rolling window if requested
            if self.config.get('rolling_window', 0) > 0:
                value_data = self._apply_rolling_window(value_data)
            
            # Fill missing values if requested
            if self.config.get('fill_missing', True):
                value_data = value_data.fillna(method='forward').fillna(method='backward')
            
            # Plot line
            color = colors[i] if self.config.get('color') == 'auto' else self.config.get('color')
            line = ax.plot(time_data, value_data,
                          linestyle=self.config.get('line_style', '-'),
                          linewidth=self.config.get('line_width', 2.0),
                          marker=self.config.get('marker', 'none'),
                          alpha=self.config.get('alpha', 1.0),
                          color=color,
                          label=str(metric))
            
            # Detect and show anomalies if requested
            if self.config.get('show_anomalies', False):
                await self._detect_and_show_anomalies(ax, time_data, value_data, color)
    
    async def _draw_dict(self, ax: matplotlib.axes.Axes, data: Dict[str, Any]) -> None:
        """Draw time series from dictionary data."""
        if 'timestamps' in data and 'values' in data:
            # Simple timestamp-value data
            timestamps = pd.to_datetime(data['timestamps'])
            values = np.array(data['values'])
            
            # Sort by time
            sorted_indices = np.argsort(timestamps)
            timestamps = timestamps[sorted_indices]
            values = values[sorted_indices]
            
            # Apply processing
            if self.config.get('rolling_window', 0) > 0:
                values = pd.Series(values).rolling(window=self.config['rolling_window']).mean().values
            
            # Plot line
            color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
            line = ax.plot(timestamps, values,
                          linestyle=self.config.get('line_style', '-'),
                          linewidth=self.config.get('line_width', 2.0),
                          marker=self.config.get('marker', 'none'),
                          alpha=self.config.get('alpha', 1.0),
                          color=color)
            
            # Detect and show anomalies if requested
            if self.config.get('show_anomalies', False):
                await self._detect_and_show_anomalies(ax, timestamps, values, color)
        
        elif 'metrics' in data:
            # Multiple metrics data
            metrics_data = data['metrics']
            colors = self.get_color_palette(len(metrics_data))
            
            for i, (metric_name, metric_values) in enumerate(metrics_data.items()):
                if 'timestamps' in metric_values and 'values' in metric_values:
                    timestamps = pd.to_datetime(metric_values['timestamps'])
                    values = np.array(metric_values['values'])
                    
                    # Sort by time
                    sorted_indices = np.argsort(timestamps)
                    timestamps = timestamps[sorted_indices]
                    values = values[sorted_indices]
                    
                    # Apply processing
                    if self.config.get('rolling_window', 0) > 0:
                        values = pd.Series(values).rolling(window=self.config['rolling_window']).mean().values
                    
                    # Plot line
                    color = colors[i] if self.config.get('color') == 'auto' else self.config.get('color')
                    line = ax.plot(timestamps, values,
                                  linestyle=self.config.get('line_style', '-'),
                                  linewidth=self.config.get('line_width', 2.0),
                                  marker=self.config.get('marker', 'none'),
                                  alpha=self.config.get('alpha', 1.0),
                                  color=color,
                                  label=str(metric_name))
                    
                    # Detect and show anomalies if requested
                    if self.config.get('show_anomalies', False):
                        await self._detect_and_show_anomalies(ax, timestamps, values, color)
        else:
            raise ValueError("Dictionary data must contain 'timestamps' and 'values' keys or 'metrics' key")
    
    async def _draw_array(self, ax: matplotlib.axes.Axes, data: np.ndarray) -> None:
        """Draw time series from array data."""
        if data.ndim == 1:
            # 1D array - create synthetic timestamps
            timestamps = pd.date_range(start='2024-01-01', periods=len(data), freq='1min')
            values = data
        elif data.ndim == 2 and data.shape[1] >= 2:
            # 2D array - first column as timestamps, second as values
            timestamps = pd.to_datetime(data[:, 0])
            values = data[:, 1]
        else:
            raise ValueError("Array data must be 1D or 2D with at least 2 columns")
        
        # Sort by time
        sorted_indices = np.argsort(timestamps)
        timestamps = timestamps[sorted_indices]
        values = values[sorted_indices]
        
        # Apply processing
        if self.config.get('rolling_window', 0) > 0:
            values = pd.Series(values).rolling(window=self.config['rolling_window']).mean().values
        
        # Plot line
        color = self.get_color_palette(1)[0] if self.config.get('color') == 'auto' else self.config.get('color')
        line = ax.plot(timestamps, values,
                      linestyle=self.config.get('line_style', '-'),
                      linewidth=self.config.get('line_width', 2.0),
                      marker=self.config.get('marker', 'none'),
                      alpha=self.config.get('alpha', 1.0),
                      color=color)
        
        # Detect and show anomalies if requested
        if self.config.get('show_anomalies', False):
            await self._detect_and_show_anomalies(ax, timestamps, values, color)
    
    def _format_time_axis(self, ax: matplotlib.axes.Axes) -> None:
        """Format the time axis with appropriate date/time formatting."""
        # Auto-format time axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        
        # Rotate labels for better readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Custom format if specified
        time_format = self.config.get('time_format', 'auto')
        if time_format != 'auto':
            ax.xaxis.set_major_formatter(mdates.DateFormatter(time_format))
    
    def _resample_data(self, time_data: pd.Series, value_data: pd.Series) -> tuple:
        """Resample time series data to specified frequency."""
        freq = self.config.get('resample_freq', 'none')
        agg = self.config.get('aggregation', 'mean')
        
        if freq == 'none':
            return time_data, value_data
        
        # Create temporary DataFrame for resampling
        temp_df = pd.DataFrame({'time': time_data, 'value': value_data})
        temp_df.set_index('time', inplace=True)
        
        # Resample
        if agg == 'mean':
            resampled = temp_df.resample(freq).mean()
        elif agg == 'sum':
            resampled = temp_df.resample(freq).sum()
        elif agg == 'min':
            resampled = temp_df.resample(freq).min()
        elif agg == 'max':
            resampled = temp_df.resample(freq).max()
        elif agg == 'count':
            resampled = temp_df.resample(freq).count()
        else:
            resampled = temp_df.resample(freq).mean()
        
        return resampled.index, resampled['value']
    
    def _apply_rolling_window(self, value_data: pd.Series) -> pd.Series:
        """Apply rolling window smoothing."""
        window = self.config.get('rolling_window', 0)
        if window > 0:
            return value_data.rolling(window=window, center=True).mean()
        return value_data
    
    async def _detect_and_show_anomalies(self, ax: matplotlib.axes.Axes, 
                                       time_data: pd.Series, value_data: pd.Series, 
                                       line_color: str) -> None:
        """Detect and highlight anomalies in the time series."""
        threshold = self.config.get('anomaly_threshold', 2.0)
        
        # Simple anomaly detection using z-score
        mean_val = value_data.mean()
        std_val = value_data.std()
        
        if std_val > 0:
            z_scores = np.abs((value_data - mean_val) / std_val)
            anomalies = z_scores > threshold
            
            if anomalies.any():
                # Highlight anomalies
                anomaly_times = time_data[anomalies]
                anomaly_values = value_data[anomalies]
                
                ax.scatter(anomaly_times, anomaly_values, 
                          color='red', s=50, alpha=0.8, 
                          marker='o', edgecolors='darkred',
                          label='Anomalies', zorder=5)
