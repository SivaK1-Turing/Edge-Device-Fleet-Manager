"""
Telemetry Event Model

SQLAlchemy model for device telemetry data with time-series optimization,
custom indexes for high-performance queries, and data validation.
"""

import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class TelemetryType(enum.Enum):
    """Type of telemetry data."""
    SENSOR_DATA = "sensor_data"
    SYSTEM_METRICS = "system_metrics"
    PERFORMANCE = "performance"
    HEALTH_CHECK = "health_check"
    ERROR_LOG = "error_log"
    EVENT_LOG = "event_log"
    CONFIGURATION = "configuration"
    DIAGNOSTIC = "diagnostic"
    ALERT = "alert"
    CUSTOM = "custom"


class TelemetryEvent(BaseModel):
    """
    Telemetry event model for time-series device data.
    
    Optimized for high-volume ingestion and efficient querying
    with time-based partitioning and custom indexes.
    """
    
    __tablename__ = "telemetry_events"
    
    # Device reference
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'telemetry_events', 'device_id', 'devices', 'id'
        )),
        nullable=False,
        comment="Reference to the source device"
    )
    
    # Event identification
    event_type = Column(
        Enum(TelemetryType),
        nullable=False,
        comment="Type of telemetry event"
    )
    
    event_name = Column(
        String(255),
        nullable=False,
        comment="Specific name of the telemetry event"
    )
    
    event_source = Column(
        String(255),
        nullable=True,
        comment="Source component or sensor that generated the event"
    )
    
    # Timing information
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the event occurred"
    )
    
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the event was received by the system"
    )
    
    # Data payload
    data = Column(
        JSONB,
        nullable=True,
        comment="Telemetry data as JSON"
    )
    
    # Numeric values for efficient querying and aggregation
    numeric_value = Column(
        Float,
        nullable=True,
        comment="Primary numeric value for aggregation queries"
    )
    
    string_value = Column(
        String(1000),
        nullable=True,
        comment="Primary string value for text-based telemetry"
    )
    
    boolean_value = Column(
        Boolean,
        nullable=True,
        comment="Primary boolean value for status indicators"
    )
    
    # Quality and metadata
    quality_score = Column(
        Float,
        nullable=True,
        comment="Data quality score (0.0 to 1.0)"
    )
    
    confidence_level = Column(
        Float,
        nullable=True,
        comment="Confidence level of the measurement (0.0 to 1.0)"
    )
    
    units = Column(
        String(50),
        nullable=True,
        comment="Units of measurement for numeric values"
    )
    
    # Processing information
    processed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flag indicating if the event has been processed"
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the event was processed"
    )
    
    processing_duration_ms = Column(
        Integer,
        nullable=True,
        comment="Processing duration in milliseconds"
    )
    
    # Correlation and tracing
    correlation_id = Column(
        String(255),
        nullable=True,
        comment="Correlation ID for related events"
    )
    
    trace_id = Column(
        String(255),
        nullable=True,
        comment="Distributed tracing ID"
    )
    
    span_id = Column(
        String(255),
        nullable=True,
        comment="Span ID for distributed tracing"
    )
    
    # Sequence and ordering
    sequence_number = Column(
        BigInteger,
        nullable=True,
        comment="Sequence number for ordering events from the same device"
    )
    
    batch_id = Column(
        String(255),
        nullable=True,
        comment="Batch ID for events ingested together"
    )
    
    # Error handling
    error_code = Column(
        String(100),
        nullable=True,
        comment="Error code if the event represents an error"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if the event represents an error"
    )
    
    # Relationships
    device = relationship(
        "Device",
        back_populates="telemetry_events",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            'quality_score >= 0.0 AND quality_score <= 1.0',
            name='chk_telemetry_quality_score_range'
        ),
        CheckConstraint(
            'confidence_level >= 0.0 AND confidence_level <= 1.0',
            name='chk_telemetry_confidence_level_range'
        ),
        CheckConstraint(
            'processing_duration_ms >= 0',
            name='chk_telemetry_processing_duration_positive'
        ),
        
        # Time-based indexes for efficient querying
        Index('idx_telemetry_timestamp', 'timestamp'),
        Index('idx_telemetry_received_at', 'received_at'),
        Index('idx_telemetry_device_timestamp', 'device_id', 'timestamp'),
        Index('idx_telemetry_device_type_timestamp', 'device_id', 'event_type', 'timestamp'),
        
        # Query optimization indexes
        Index('idx_telemetry_event_type', 'event_type'),
        Index('idx_telemetry_event_name', 'event_name'),
        Index('idx_telemetry_processed', 'processed'),
        Index('idx_telemetry_correlation_id', 'correlation_id'),
        Index('idx_telemetry_trace_id', 'trace_id'),
        
        # Composite indexes for common query patterns
        Index('idx_telemetry_device_processed', 'device_id', 'processed'),
        Index('idx_telemetry_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_telemetry_source_timestamp', 'event_source', 'timestamp'),
        
        # Partial indexes for active/unprocessed events
        Index(
            'idx_telemetry_unprocessed_timestamp',
            'timestamp',
            postgresql_where="processed = false"
        ),
        Index(
            'idx_telemetry_recent_events',
            'device_id', 'timestamp',
            postgresql_where="timestamp > (NOW() - INTERVAL '24 hours')"
        ),
        
        # GIN indexes for JSON data
        Index('idx_telemetry_data_gin', 'data', postgresql_using='gin'),
        
        # BRIN indexes for time-series data (PostgreSQL)
        Index('idx_telemetry_timestamp_brin', 'timestamp', postgresql_using='brin'),
    )
    
    # Validation methods
    @validates('quality_score')
    def validate_quality_score(self, key, value):
        """Validate quality score is within valid range."""
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("Quality score must be between 0.0 and 1.0")
        return value
    
    @validates('confidence_level')
    def validate_confidence_level(self, key, value):
        """Validate confidence level is within valid range."""
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("Confidence level must be between 0.0 and 1.0")
        return value
    
    @validates('processing_duration_ms')
    def validate_processing_duration(self, key, value):
        """Validate processing duration is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Processing duration must be non-negative")
        return value
    
    # Hybrid properties
    @hybrid_property
    def is_recent(self) -> bool:
        """Check if the event is recent (within last hour)."""
        if self.timestamp is None:
            return False
        
        now = datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds() < 3600
    
    @hybrid_property
    def has_error(self) -> bool:
        """Check if the event represents an error."""
        return self.error_code is not None or self.error_message is not None
    
    @hybrid_property
    def processing_latency_ms(self) -> Optional[int]:
        """Calculate processing latency in milliseconds."""
        if self.received_at is None or self.timestamp is None:
            return None
        
        delta = self.received_at - self.timestamp
        return int(delta.total_seconds() * 1000)
    
    # Business logic methods
    def mark_processed(self, duration_ms: Optional[int] = None) -> None:
        """Mark the event as processed."""
        self.processed = True
        self.processed_at = datetime.now(timezone.utc)
        if duration_ms is not None:
            self.processing_duration_ms = duration_ms
    
    def extract_numeric_value(self) -> Optional[float]:
        """Extract numeric value from data payload."""
        if self.numeric_value is not None:
            return self.numeric_value
        
        if self.data is None:
            return None
        
        # Try to extract from common data fields
        for field in ['value', 'measurement', 'reading', 'level', 'count']:
            if field in self.data:
                try:
                    return float(self.data[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def get_data_field(self, field_name: str, default: Any = None) -> Any:
        """Get a specific field from the data payload."""
        if self.data is None:
            return default
        
        return self.data.get(field_name, default)
    
    def set_data_field(self, field_name: str, value: Any) -> None:
        """Set a specific field in the data payload."""
        if self.data is None:
            self.data = {}
        
        self.data[field_name] = value
    
    def to_time_series_point(self) -> Dict[str, Any]:
        """Convert to time-series data point format."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'device_id': str(self.device_id),
            'event_type': self.event_type.value,
            'event_name': self.event_name,
            'value': self.extract_numeric_value(),
            'units': self.units,
            'quality': self.quality_score,
            'data': self.data
        }
    
    def __repr__(self) -> str:
        """String representation of the telemetry event."""
        return (
            f"<TelemetryEvent(id={self.id}, device_id={self.device_id}, "
            f"type={self.event_type.value}, timestamp={self.timestamp})>"
        )


class TelemetryData:
    """
    Helper class for structured telemetry data.
    
    Provides type-safe access to common telemetry data patterns.
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data or {}
    
    @property
    def temperature(self) -> Optional[float]:
        """Get temperature value."""
        return self._get_numeric('temperature', 'temp')
    
    @property
    def humidity(self) -> Optional[float]:
        """Get humidity value."""
        return self._get_numeric('humidity', 'rh')
    
    @property
    def pressure(self) -> Optional[float]:
        """Get pressure value."""
        return self._get_numeric('pressure', 'press')
    
    @property
    def voltage(self) -> Optional[float]:
        """Get voltage value."""
        return self._get_numeric('voltage', 'v')
    
    @property
    def current(self) -> Optional[float]:
        """Get current value."""
        return self._get_numeric('current', 'i', 'amp')
    
    @property
    def power(self) -> Optional[float]:
        """Get power value."""
        return self._get_numeric('power', 'watt', 'w')
    
    @property
    def cpu_usage(self) -> Optional[float]:
        """Get CPU usage percentage."""
        return self._get_numeric('cpu_usage', 'cpu', 'cpu_percent')
    
    @property
    def memory_usage(self) -> Optional[float]:
        """Get memory usage percentage."""
        return self._get_numeric('memory_usage', 'memory', 'mem_percent')
    
    @property
    def disk_usage(self) -> Optional[float]:
        """Get disk usage percentage."""
        return self._get_numeric('disk_usage', 'disk', 'disk_percent')
    
    def _get_numeric(self, *field_names: str) -> Optional[float]:
        """Get numeric value from multiple possible field names."""
        for field_name in field_names:
            if field_name in self.data:
                try:
                    return float(self.data[field_name])
                except (ValueError, TypeError):
                    continue
        return None
    
    def get(self, field_name: str, default: Any = None) -> Any:
        """Get field value with default."""
        return self.data.get(field_name, default)
    
    def set(self, field_name: str, value: Any) -> None:
        """Set field value."""
        self.data[field_name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data.copy()
