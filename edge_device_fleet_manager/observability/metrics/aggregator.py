"""
Metrics Aggregator

Aggregates and processes collected metrics for analysis and export.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import statistics

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Aggregates metrics data for analysis and reporting.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize metrics aggregator."""
        self.config = config or {}
        self.logger = logger
    
    def aggregate_counters(self, counters: Dict[str, float]) -> Dict[str, Any]:
        """Aggregate counter metrics."""
        return {
            'total_count': len(counters),
            'total_value': sum(counters.values()),
            'average_value': statistics.mean(counters.values()) if counters else 0,
            'max_value': max(counters.values()) if counters else 0,
            'min_value': min(counters.values()) if counters else 0
        }
    
    def aggregate_gauges(self, gauges: Dict[str, float]) -> Dict[str, Any]:
        """Aggregate gauge metrics."""
        return {
            'total_count': len(gauges),
            'average_value': statistics.mean(gauges.values()) if gauges else 0,
            'max_value': max(gauges.values()) if gauges else 0,
            'min_value': min(gauges.values()) if gauges else 0,
            'median_value': statistics.median(gauges.values()) if gauges else 0
        }
    
    def aggregate_histograms(self, histograms: Dict[str, List[float]]) -> Dict[str, Any]:
        """Aggregate histogram metrics."""
        aggregated = {}
        
        for name, values in histograms.items():
            if values:
                aggregated[name] = {
                    'count': len(values),
                    'sum': sum(values),
                    'average': statistics.mean(values),
                    'median': statistics.median(values),
                    'p95': self._percentile(values, 95),
                    'p99': self._percentile(values, 99),
                    'min': min(values),
                    'max': max(values)
                }
            else:
                aggregated[name] = {
                    'count': 0,
                    'sum': 0,
                    'average': 0,
                    'median': 0,
                    'p95': 0,
                    'p99': 0,
                    'min': 0,
                    'max': 0
                }
        
        return aggregated
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def generate_summary(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of all metrics."""
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'counters': self.aggregate_counters(metrics_data.get('counters', {})),
            'gauges': self.aggregate_gauges(metrics_data.get('gauges', {})),
            'histograms': self.aggregate_histograms(metrics_data.get('histograms', {}))
        }
        
        return summary
