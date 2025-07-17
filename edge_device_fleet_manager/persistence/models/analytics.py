"""
Analytics Model

SQLAlchemy model for analytics data with aggregated metrics,
time-based partitioning, and optimized queries for reporting.
"""

import enum
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INTERVAL
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class AnalyticsType(enum.Enum):
    """Type of analytics data."""
    DEVICE_METRICS = "device_metrics"
    FLEET_SUMMARY = "fleet_summary"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    HEALTH_REPORT = "health_report"
    USAGE_STATISTICS = "usage_statistics"
    TREND_ANALYSIS = "trend_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    COST_ANALYSIS = "cost_analysis"
    CUSTOM_REPORT = "custom_report"


class AnalyticsMetric(enum.Enum):
    """Specific metric types for analytics."""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MEDIAN = "median"
    PERCENTILE_95 = "percentile_95"
    PERCENTILE_99 = "percentile_99"
    STANDARD_DEVIATION = "standard_deviation"
    VARIANCE = "variance"
    RATE = "rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    UPTIME = "uptime"
    DOWNTIME = "downtime"


class Analytics(BaseModel):
    """
    Analytics model for aggregated metrics and reports.
    
    Stores pre-computed analytics data for efficient reporting
    and dashboard visualization with time-based aggregation.
    """
    
    __tablename__ = "analytics"
    
    # Analytics identification
    analytics_type = Column(
        Enum(AnalyticsType),
        nullable=False,
        comment="Type of analytics data"
    )
    
    metric_name = Column(
        String(255),
        nullable=False,
        comment="Name of the specific metric"
    )
    
    metric_type = Column(
        Enum(AnalyticsMetric),
        nullable=False,
        comment="Type of metric calculation"
    )
    
    # Time period information
    period_start = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start of the analytics period"
    )
    
    period_end = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="End of the analytics period"
    )
    
    period_duration = Column(
        INTERVAL,
        nullable=True,
        comment="Duration of the analytics period"
    )
    
    granularity = Column(
        String(50),
        nullable=False,
        comment="Time granularity (hourly, daily, weekly, monthly)"
    )
    
    # Scope and filtering
    scope = Column(
        String(100),
        nullable=False,
        comment="Scope of analytics (global, device_group, device)"
    )
    
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'analytics', 'device_id', 'devices', 'id'
        )),
        nullable=True,
        comment="Reference to specific device (if device-scoped)"
    )
    
    device_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('device_groups.id', name=create_foreign_key_constraint(
            'analytics', 'device_group_id', 'device_groups', 'id'
        )),
        nullable=True,
        comment="Reference to device group (if group-scoped)"
    )
    
    # Metric values
    numeric_value = Column(
        Float,
        nullable=True,
        comment="Primary numeric value of the metric"
    )
    
    count_value = Column(
        BigInteger,
        nullable=True,
        comment="Count value for counting metrics"
    )
    
    percentage_value = Column(
        Float,
        nullable=True,
        comment="Percentage value (0.0 to 100.0)"
    )
    
    # Statistical values
    min_value = Column(
        Float,
        nullable=True,
        comment="Minimum value in the period"
    )
    
    max_value = Column(
        Float,
        nullable=True,
        comment="Maximum value in the period"
    )
    
    avg_value = Column(
        Float,
        nullable=True,
        comment="Average value in the period"
    )
    
    median_value = Column(
        Float,
        nullable=True,
        comment="Median value in the period"
    )
    
    std_deviation = Column(
        Float,
        nullable=True,
        comment="Standard deviation of values"
    )
    
    # Additional metrics
    sample_count = Column(
        BigInteger,
        nullable=True,
        comment="Number of samples used for calculation"
    )
    
    units = Column(
        String(50),
        nullable=True,
        comment="Units of measurement"
    )
    
    # Quality and confidence
    confidence_level = Column(
        Float,
        nullable=True,
        comment="Confidence level of the analytics (0.0 to 1.0)"
    )
    
    data_quality_score = Column(
        Float,
        nullable=True,
        comment="Quality score of underlying data (0.0 to 1.0)"
    )
    
    # Detailed data and metadata
    detailed_data = Column(
        JSONB,
        nullable=True,
        comment="Detailed analytics data as JSON"
    )
    
    metadata_json = Column(
        JSONB,
        nullable=True,
        comment="Additional metadata for the analytics"
    )
    
    # Processing information
    calculation_method = Column(
        String(255),
        nullable=True,
        comment="Method used for calculation"
    )
    
    calculated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when analytics were calculated"
    )
    
    calculation_duration_ms = Column(
        Integer,
        nullable=True,
        comment="Time taken to calculate analytics in milliseconds"
    )
    
    # Data sources
    source_table = Column(
        String(255),
        nullable=True,
        comment="Source table for the analytics"
    )
    
    source_query = Column(
        Text,
        nullable=True,
        comment="Source query used for calculation"
    )
    
    source_filters = Column(
        JSONB,
        nullable=True,
        comment="Filters applied to source data"
    )
    
    # Relationships
    device = relationship(
        "Device",
        lazy="select"
    )
    
    device_group = relationship(
        "DeviceGroup",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            'percentage_value >= 0.0 AND percentage_value <= 100.0',
            name='chk_analytics_percentage_range'
        ),
        CheckConstraint(
            'confidence_level >= 0.0 AND confidence_level <= 1.0',
            name='chk_analytics_confidence_range'
        ),
        CheckConstraint(
            'data_quality_score >= 0.0 AND data_quality_score <= 1.0',
            name='chk_analytics_quality_score_range'
        ),
        CheckConstraint(
            'period_end >= period_start',
            name='chk_analytics_period_order'
        ),
        CheckConstraint(
            'sample_count >= 0',
            name='chk_analytics_sample_count_positive'
        ),
        
        # Time-based indexes for efficient querying
        Index('idx_analytics_period_start', 'period_start'),
        Index('idx_analytics_period_end', 'period_end'),
        Index('idx_analytics_calculated_at', 'calculated_at'),
        
        # Query optimization indexes
        Index('idx_analytics_type', 'analytics_type'),
        Index('idx_analytics_metric_name', 'metric_name'),
        Index('idx_analytics_metric_type', 'metric_type'),
        Index('idx_analytics_scope', 'scope'),
        Index('idx_analytics_granularity', 'granularity'),
        
        # Composite indexes for common queries
        Index('idx_analytics_type_period', 'analytics_type', 'period_start', 'period_end'),
        Index('idx_analytics_device_period', 'device_id', 'period_start', 'period_end'),
        Index('idx_analytics_group_period', 'device_group_id', 'period_start', 'period_end'),
        Index('idx_analytics_metric_period', 'metric_name', 'period_start', 'period_end'),
        Index('idx_analytics_scope_granularity', 'scope', 'granularity'),
        
        # Partial indexes for recent analytics
        Index(
            'idx_analytics_recent',
            'analytics_type', 'metric_name',
            postgresql_where="calculated_at > (NOW() - INTERVAL '7 days')"
        ),
        
        # GIN indexes for JSON data
        Index('idx_analytics_detailed_data_gin', 'detailed_data', postgresql_using='gin'),
        Index('idx_analytics_metadata_gin', 'metadata_json', postgresql_using='gin'),
        
        # BRIN indexes for time-series data
        Index('idx_analytics_period_start_brin', 'period_start', postgresql_using='brin'),
    )
    
    # Validation methods
    @validates('percentage_value')
    def validate_percentage(self, key, value):
        """Validate percentage is within valid range."""
        if value is not None and not (0.0 <= value <= 100.0):
            raise ValueError("Percentage value must be between 0.0 and 100.0")
        return value
    
    @validates('confidence_level')
    def validate_confidence(self, key, value):
        """Validate confidence level is within valid range."""
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("Confidence level must be between 0.0 and 1.0")
        return value
    
    @validates('data_quality_score')
    def validate_quality_score(self, key, value):
        """Validate quality score is within valid range."""
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("Data quality score must be between 0.0 and 1.0")
        return value
    
    # Hybrid properties
    @hybrid_property
    def period_duration_seconds(self) -> Optional[int]:
        """Get period duration in seconds."""
        if self.period_start and self.period_end:
            return int((self.period_end - self.period_start).total_seconds())
        return None
    
    @hybrid_property
    def is_recent(self) -> bool:
        """Check if analytics are recent (calculated within last day)."""
        if self.calculated_at is None:
            return False
        
        now = datetime.now(timezone.utc)
        return (now - self.calculated_at).total_seconds() < 86400
    
    @hybrid_property
    def has_statistical_data(self) -> bool:
        """Check if analytics include statistical measures."""
        return any([
            self.min_value is not None,
            self.max_value is not None,
            self.avg_value is not None,
            self.median_value is not None,
            self.std_deviation is not None
        ])
    
    # Business logic methods
    def get_primary_value(self) -> Optional[float]:
        """Get the primary value based on metric type."""
        if self.metric_type == AnalyticsMetric.COUNT:
            return float(self.count_value) if self.count_value is not None else None
        elif self.metric_type == AnalyticsMetric.AVERAGE:
            return self.avg_value
        elif self.metric_type == AnalyticsMetric.MINIMUM:
            return self.min_value
        elif self.metric_type == AnalyticsMetric.MAXIMUM:
            return self.max_value
        elif self.metric_type == AnalyticsMetric.MEDIAN:
            return self.median_value
        else:
            return self.numeric_value
    
    def get_detailed_field(self, field_name: str, default: Any = None) -> Any:
        """Get a field from detailed data."""
        if self.detailed_data is None:
            return default
        return self.detailed_data.get(field_name, default)
    
    def set_detailed_field(self, field_name: str, value: Any) -> None:
        """Set a field in detailed data."""
        if self.detailed_data is None:
            self.detailed_data = {}
        self.detailed_data[field_name] = value
    
    def calculate_trend(self, previous_analytics: 'Analytics') -> Optional[float]:
        """
        Calculate trend compared to previous analytics.
        
        Args:
            previous_analytics: Previous analytics for comparison
            
        Returns:
            Trend percentage (positive for increase, negative for decrease)
        """
        current_value = self.get_primary_value()
        previous_value = previous_analytics.get_primary_value()
        
        if current_value is None or previous_value is None or previous_value == 0:
            return None
        
        return ((current_value - previous_value) / previous_value) * 100
    
    def to_chart_data(self) -> Dict[str, Any]:
        """Convert to chart-friendly data format."""
        return {
            'timestamp': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'metric': self.metric_name,
            'value': self.get_primary_value(),
            'min': self.min_value,
            'max': self.max_value,
            'avg': self.avg_value,
            'count': self.count_value,
            'units': self.units,
            'confidence': self.confidence_level
        }
    
    def __repr__(self) -> str:
        """String representation of the analytics."""
        return (
            f"<Analytics(id={self.id}, type={self.analytics_type.value}, "
            f"metric={self.metric_name}, period={self.period_start} to {self.period_end})>"
        )
