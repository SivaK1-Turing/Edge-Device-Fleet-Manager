"""
Metrics Exporters

Export metrics to external monitoring systems like Prometheus and InfluxDB.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for metrics exporters."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize exporter."""
        self.config = config or {}
        self.logger = logger
    
    async def export(self, metrics_data: Dict[str, Any]):
        """Export metrics data."""
        raise NotImplementedError("Subclasses must implement export method")


class PrometheusExporter(BaseExporter):
    """Export metrics in Prometheus format."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Prometheus exporter."""
        super().__init__(config)
        self.endpoint = self.config.get('endpoint', 'http://localhost:9090')
        self.job_name = self.config.get('job_name', 'edge_fleet_manager')
    
    async def export(self, metrics_data: Dict[str, Any]):
        """Export metrics to Prometheus."""
        try:
            prometheus_format = self._convert_to_prometheus_format(metrics_data)
            
            # In a real implementation, this would push to Prometheus pushgateway
            # For now, we'll just log the formatted metrics
            self.logger.info(f"Exporting {len(prometheus_format)} metrics to Prometheus")
            
            return {
                'success': True,
                'exported_metrics': len(prometheus_format),
                'endpoint': self.endpoint
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export to Prometheus: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _convert_to_prometheus_format(self, metrics_data: Dict[str, Any]) -> List[str]:
        """Convert metrics to Prometheus format."""
        prometheus_metrics = []
        
        # Convert counters
        for name, value in metrics_data.get('counters', {}).items():
            prometheus_metrics.append(f"{name}_total {value}")
        
        # Convert gauges
        for name, value in metrics_data.get('gauges', {}).items():
            prometheus_metrics.append(f"{name} {value}")
        
        # Convert histograms (simplified)
        for name, values in metrics_data.get('histograms', {}).items():
            if values:
                prometheus_metrics.append(f"{name}_count {len(values)}")
                prometheus_metrics.append(f"{name}_sum {sum(values)}")
        
        return prometheus_metrics


class InfluxDBExporter(BaseExporter):
    """Export metrics to InfluxDB."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize InfluxDB exporter."""
        super().__init__(config)
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 8086)
        self.database = self.config.get('database', 'edge_fleet_metrics')
        self.measurement = self.config.get('measurement', 'metrics')
    
    async def export(self, metrics_data: Dict[str, Any]):
        """Export metrics to InfluxDB."""
        try:
            influx_format = self._convert_to_influx_format(metrics_data)
            
            # In a real implementation, this would write to InfluxDB
            # For now, we'll just log the formatted metrics
            self.logger.info(f"Exporting {len(influx_format)} metrics to InfluxDB")
            
            return {
                'success': True,
                'exported_metrics': len(influx_format),
                'database': self.database
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export to InfluxDB: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _convert_to_influx_format(self, metrics_data: Dict[str, Any]) -> List[str]:
        """Convert metrics to InfluxDB line protocol format."""
        influx_lines = []
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000000000)  # nanoseconds
        
        # Convert counters
        for name, value in metrics_data.get('counters', {}).items():
            influx_lines.append(f"{self.measurement},metric_type=counter,name={name} value={value} {timestamp}")
        
        # Convert gauges
        for name, value in metrics_data.get('gauges', {}).items():
            influx_lines.append(f"{self.measurement},metric_type=gauge,name={name} value={value} {timestamp}")
        
        # Convert histograms
        for name, values in metrics_data.get('histograms', {}).items():
            if values:
                count = len(values)
                sum_val = sum(values)
                avg_val = sum_val / count if count > 0 else 0
                
                influx_lines.append(f"{self.measurement},metric_type=histogram,name={name} count={count},sum={sum_val},avg={avg_val} {timestamp}")
        
        return influx_lines


class JSONExporter(BaseExporter):
    """Export metrics as JSON."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize JSON exporter."""
        super().__init__(config)
        self.output_file = self.config.get('output_file', 'metrics.json')
    
    async def export(self, metrics_data: Dict[str, Any]):
        """Export metrics as JSON."""
        try:
            # Add timestamp
            export_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': metrics_data
            }
            
            # In a real implementation, this would write to file
            # For now, we'll just return the data
            self.logger.info(f"Exporting metrics as JSON")
            
            return {
                'success': True,
                'data': export_data,
                'output_file': self.output_file
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export as JSON: {e}")
            return {
                'success': False,
                'error': str(e)
            }
