"""
Alert Models

SQLAlchemy models for alert management with severity levels,
status tracking, and rule-based alert generation.
"""

import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(enum.Enum):
    """Alert status enumeration."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    SUPPRESSED = "suppressed"


class Alert(BaseModel):
    """
    Alert model for system notifications and incident management.
    
    Tracks alerts generated from device events, system conditions,
    and rule-based monitoring with comprehensive metadata.
    """
    
    __tablename__ = "alerts"
    
    # Alert identification
    title = Column(
        String(500),
        nullable=False,
        comment="Alert title or summary"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Detailed alert description"
    )
    
    alert_type = Column(
        String(100),
        nullable=False,
        comment="Type or category of alert"
    )
    
    # Severity and priority
    severity = Column(
        Enum(AlertSeverity),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        comment="Alert severity level"
    )
    
    priority = Column(
        Integer,
        nullable=False,
        default=50,
        comment="Alert priority (0-100, higher is more urgent)"
    )
    
    # Status and lifecycle
    status = Column(
        Enum(AlertStatus),
        nullable=False,
        default=AlertStatus.OPEN,
        comment="Current alert status"
    )
    
    # Source information
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'alerts', 'device_id', 'devices', 'id'
        )),
        nullable=True,
        comment="Reference to source device"
    )
    
    source_component = Column(
        String(255),
        nullable=True,
        comment="Source component or service"
    )
    
    source_event_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Reference to source event or telemetry"
    )
    
    # Rule and trigger information
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey('alert_rules.id', name=create_foreign_key_constraint(
            'alerts', 'rule_id', 'alert_rules', 'id'
        )),
        nullable=True,
        comment="Reference to alert rule that triggered this alert"
    )
    
    trigger_condition = Column(
        Text,
        nullable=True,
        comment="Condition that triggered the alert"
    )
    
    trigger_value = Column(
        String(255),
        nullable=True,
        comment="Value that triggered the alert"
    )
    
    threshold_value = Column(
        String(255),
        nullable=True,
        comment="Threshold value that was exceeded"
    )
    
    # Timing information
    first_occurred = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the alert first occurred"
    )
    
    last_occurred = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the alert last occurred"
    )
    
    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the alert was acknowledged"
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the alert was resolved"
    )
    
    # Assignment and ownership
    assigned_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'alerts', 'assigned_to_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User assigned to handle the alert"
    )
    
    acknowledged_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'alerts', 'acknowledged_by_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User who acknowledged the alert"
    )
    
    resolved_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'alerts', 'resolved_by_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User who resolved the alert"
    )
    
    # Occurrence tracking
    occurrence_count = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of times this alert has occurred"
    )
    
    # Additional data
    alert_data = Column(
        JSON,
        nullable=True,
        comment="Additional alert data as JSON"
    )
    
    tags = Column(
        JSON,
        nullable=True,
        comment="Alert tags for categorization"
    )
    
    # Resolution information
    resolution_notes = Column(
        Text,
        nullable=True,
        comment="Notes about alert resolution"
    )
    
    resolution_action = Column(
        String(255),
        nullable=True,
        comment="Action taken to resolve the alert"
    )
    
    # Notification tracking
    notifications_sent = Column(
        JSON,
        nullable=True,
        comment="Record of notifications sent for this alert"
    )
    
    # Relationships
    device = relationship(
        "Device",
        back_populates="alerts",
        lazy="select"
    )
    
    rule = relationship(
        "AlertRule",
        back_populates="alerts",
        lazy="select"
    )
    
    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_user_id],
        lazy="select"
    )
    
    acknowledged_by = relationship(
        "User",
        foreign_keys=[acknowledged_by_user_id],
        lazy="select"
    )
    
    resolved_by = relationship(
        "User",
        foreign_keys=[resolved_by_user_id],
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            'priority >= 0 AND priority <= 100',
            name='chk_alerts_priority_range'
        ),
        CheckConstraint(
            'occurrence_count >= 1',
            name='chk_alerts_occurrence_count_positive'
        ),
        CheckConstraint(
            'last_occurred >= first_occurred',
            name='chk_alerts_occurrence_order'
        ),
        
        # Indexes for performance
        Index('idx_alerts_severity', 'severity'),
        Index('idx_alerts_status', 'status'),
        Index('idx_alerts_alert_type', 'alert_type'),
        Index('idx_alerts_device_id', 'device_id'),
        Index('idx_alerts_rule_id', 'rule_id'),
        Index('idx_alerts_first_occurred', 'first_occurred'),
        Index('idx_alerts_last_occurred', 'last_occurred'),
        Index('idx_alerts_assigned_to', 'assigned_to_user_id'),
        
        # Composite indexes for common queries
        Index('idx_alerts_status_severity', 'status', 'severity'),
        Index('idx_alerts_device_status', 'device_id', 'status'),
        Index('idx_alerts_type_status', 'alert_type', 'status'),
        Index('idx_alerts_severity_occurred', 'severity', 'first_occurred'),
        
        # Partial indexes for active alerts
        Index(
            'idx_alerts_open',
            'severity', 'first_occurred',
            postgresql_where="status IN ('open', 'acknowledged', 'in_progress')"
        ),
        
        # GIN indexes for JSON data
        Index('idx_alerts_data_gin', 'alert_data', postgresql_using='gin'),
        Index('idx_alerts_tags_gin', 'tags', postgresql_using='gin'),
    )
    
    # Validation methods
    @validates('priority')
    def validate_priority(self, key, value):
        """Validate priority is within valid range."""
        if value is not None and not (0 <= value <= 100):
            raise ValueError("Priority must be between 0 and 100")
        return value
    
    @validates('occurrence_count')
    def validate_occurrence_count(self, key, value):
        """Validate occurrence count is positive."""
        if value is not None and value < 1:
            raise ValueError("Occurrence count must be at least 1")
        return value
    
    # Hybrid properties
    @hybrid_property
    def is_open(self) -> bool:
        """Check if alert is in an open state."""
        return self.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS]
    
    @hybrid_property
    def is_critical(self) -> bool:
        """Check if alert is critical severity."""
        return self.severity == AlertSeverity.CRITICAL
    
    @hybrid_property
    def duration_minutes(self) -> Optional[int]:
        """Get alert duration in minutes."""
        if self.resolved_at:
            end_time = self.resolved_at
        else:
            end_time = datetime.now(timezone.utc)
        
        delta = end_time - self.first_occurred
        return int(delta.total_seconds() / 60)
    
    @hybrid_property
    def is_recurring(self) -> bool:
        """Check if alert has occurred multiple times."""
        return self.occurrence_count > 1
    
    # Business logic methods
    def acknowledge(self, user_id: Optional[str] = None) -> None:
        """Acknowledge the alert."""
        if self.status == AlertStatus.OPEN:
            self.status = AlertStatus.ACKNOWLEDGED
            self.acknowledged_at = datetime.now(timezone.utc)
            self.acknowledged_by_user_id = user_id
    
    def assign_to(self, user_id: str) -> None:
        """Assign alert to a user."""
        self.assigned_to_user_id = user_id
        if self.status == AlertStatus.OPEN:
            self.status = AlertStatus.ACKNOWLEDGED
            self.acknowledged_at = datetime.now(timezone.utc)
    
    def start_progress(self, user_id: Optional[str] = None) -> None:
        """Mark alert as in progress."""
        if self.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
            self.status = AlertStatus.IN_PROGRESS
            if user_id and not self.assigned_to_user_id:
                self.assigned_to_user_id = user_id
    
    def resolve(self, user_id: Optional[str] = None, notes: Optional[str] = None, 
               action: Optional[str] = None) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by_user_id = user_id
        if notes:
            self.resolution_notes = notes
        if action:
            self.resolution_action = action
    
    def close(self) -> None:
        """Close the alert."""
        if self.status == AlertStatus.RESOLVED:
            self.status = AlertStatus.CLOSED
    
    def suppress(self) -> None:
        """Suppress the alert."""
        self.status = AlertStatus.SUPPRESSED
    
    def record_occurrence(self) -> None:
        """Record another occurrence of this alert."""
        self.occurrence_count += 1
        self.last_occurred = datetime.now(timezone.utc)
        
        # Reopen if resolved
        if self.status in [AlertStatus.RESOLVED, AlertStatus.CLOSED]:
            self.status = AlertStatus.OPEN
            self.resolved_at = None
            self.resolved_by_user_id = None
    
    def get_data_field(self, field_name: str, default: Any = None) -> Any:
        """Get a field from alert data."""
        if self.alert_data is None:
            return default
        return self.alert_data.get(field_name, default)
    
    def set_data_field(self, field_name: str, value: Any) -> None:
        """Set a field in alert data."""
        if self.alert_data is None:
            self.alert_data = {}
        self.alert_data[field_name] = value
    
    def __repr__(self) -> str:
        """String representation of the alert."""
        return (
            f"<Alert(id={self.id}, title='{self.title}', "
            f"severity={self.severity.value}, status={self.status.value})>"
        )


class AlertRule(BaseModel):
    """
    Alert rule model for defining conditions that trigger alerts.
    
    Configures automated alert generation based on device metrics,
    system conditions, and custom criteria.
    """
    
    __tablename__ = "alert_rules"
    
    # Rule identification
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable rule name"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Detailed rule description"
    )
    
    # Rule configuration
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the rule is active"
    )
    
    rule_type = Column(
        String(100),
        nullable=False,
        comment="Type of rule (threshold, pattern, etc.)"
    )
    
    # Condition definition
    condition_expression = Column(
        Text,
        nullable=False,
        comment="Rule condition expression"
    )
    
    threshold_value = Column(
        String(255),
        nullable=True,
        comment="Threshold value for comparison"
    )
    
    comparison_operator = Column(
        String(20),
        nullable=True,
        comment="Comparison operator (>, <, ==, etc.)"
    )
    
    # Scope and targeting
    scope = Column(
        String(100),
        nullable=False,
        comment="Rule scope (global, device_group, device)"
    )
    
    target_device_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('device_groups.id', name=create_foreign_key_constraint(
            'alert_rules', 'target_device_group_id', 'device_groups', 'id'
        )),
        nullable=True,
        comment="Target device group for rule"
    )
    
    target_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'alert_rules', 'target_device_id', 'devices', 'id'
        )),
        nullable=True,
        comment="Target device for rule"
    )
    
    # Alert configuration
    alert_severity = Column(
        Enum(AlertSeverity),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        comment="Severity of generated alerts"
    )
    
    alert_title_template = Column(
        String(500),
        nullable=True,
        comment="Template for alert titles"
    )
    
    alert_description_template = Column(
        Text,
        nullable=True,
        comment="Template for alert descriptions"
    )
    
    # Timing and frequency
    evaluation_interval_seconds = Column(
        Integer,
        nullable=False,
        default=300,
        comment="How often to evaluate the rule (seconds)"
    )
    
    cooldown_period_seconds = Column(
        Integer,
        nullable=False,
        default=3600,
        comment="Cooldown period between alerts (seconds)"
    )
    
    # Rule metadata
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'alert_rules', 'created_by_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User who created the rule"
    )
    
    last_evaluated = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the rule was last evaluated"
    )
    
    last_triggered = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the rule last triggered an alert"
    )
    
    trigger_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times the rule has triggered"
    )
    
    # Relationships
    alerts = relationship(
        "Alert",
        back_populates="rule",
        lazy="dynamic"
    )
    
    target_device_group = relationship(
        "DeviceGroup",
        lazy="select"
    )
    
    target_device = relationship(
        "Device",
        lazy="select"
    )
    
    created_by = relationship(
        "User",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint('name', name='uniq_alert_rules_name'),
        
        # Check constraints
        CheckConstraint(
            'evaluation_interval_seconds > 0',
            name='chk_alert_rules_eval_interval_positive'
        ),
        CheckConstraint(
            'cooldown_period_seconds >= 0',
            name='chk_alert_rules_cooldown_positive'
        ),
        CheckConstraint(
            'trigger_count >= 0',
            name='chk_alert_rules_trigger_count_positive'
        ),
        
        # Indexes for performance
        Index('idx_alert_rules_name', 'name'),
        Index('idx_alert_rules_is_enabled', 'is_enabled'),
        Index('idx_alert_rules_rule_type', 'rule_type'),
        Index('idx_alert_rules_scope', 'scope'),
        Index('idx_alert_rules_last_evaluated', 'last_evaluated'),
        Index('idx_alert_rules_target_group', 'target_device_group_id'),
        Index('idx_alert_rules_target_device', 'target_device_id'),
        
        # Composite indexes
        Index('idx_alert_rules_enabled_scope', 'is_enabled', 'scope'),
        Index('idx_alert_rules_type_enabled', 'rule_type', 'is_enabled'),
    )
    
    def __repr__(self) -> str:
        """String representation of the alert rule."""
        return f"<AlertRule(id={self.id}, name='{self.name}', enabled={self.is_enabled})>"
