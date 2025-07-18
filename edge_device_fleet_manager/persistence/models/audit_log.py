"""
Audit Log Model

SQLAlchemy model for comprehensive audit logging with
action tracking, resource monitoring, and compliance support.
"""

import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class AuditAction(enum.Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    CONFIGURE = "configure"
    DEPLOY = "deploy"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    BACKUP = "backup"
    RESTORE = "restore"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    ASSIGN = "assign"
    UNASSIGN = "unassign"
    ENABLE = "enable"
    DISABLE = "disable"
    CUSTOM = "custom"


class AuditResource(enum.Enum):
    """Resource types for audit logging."""
    USER = "user"
    DEVICE = "device"
    DEVICE_GROUP = "device_group"
    TELEMETRY = "telemetry"
    ANALYTICS = "analytics"
    ALERT = "alert"
    ALERT_RULE = "alert_rule"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    FILE = "file"
    REPORT = "report"
    DASHBOARD = "dashboard"
    PLUGIN = "plugin"
    CUSTOM = "custom"


class AuditLog(BaseModel):
    """
    Comprehensive audit log model for tracking all system activities.
    
    Provides detailed logging of user actions, system events, and
    resource changes for security, compliance, and debugging purposes.
    """
    
    __tablename__ = "audit_logs"
    
    # Action identification
    action = Column(
        Enum(AuditAction),
        nullable=False,
        comment="Type of action performed"
    )
    
    resource_type = Column(
        Enum(AuditResource),
        nullable=False,
        comment="Type of resource affected"
    )
    
    resource_id = Column(
        String(255),
        nullable=True,
        comment="ID of the specific resource affected"
    )
    
    resource_name = Column(
        String(500),
        nullable=True,
        comment="Name or identifier of the resource"
    )
    
    # User and session information
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'audit_logs', 'user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User who performed the action"
    )
    
    username = Column(
        String(100),
        nullable=True,
        comment="Username at the time of action (for historical reference)"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        comment="Session ID associated with the action"
    )
    
    # Request and context information
    ip_address = Column(
        INET,
        nullable=True,
        comment="IP address of the client"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string from the request"
    )
    
    request_id = Column(
        String(255),
        nullable=True,
        comment="Unique request identifier"
    )
    
    correlation_id = Column(
        String(255),
        nullable=True,
        comment="Correlation ID for related actions"
    )
    
    # Action details
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the action"
    )
    
    details = Column(
        JSON,
        nullable=True,
        comment="Detailed information about the action"
    )
    
    # Change tracking
    old_values = Column(
        JSON,
        nullable=True,
        comment="Previous values before the change"
    )
    
    new_values = Column(
        JSON,
        nullable=True,
        comment="New values after the change"
    )
    
    changed_fields = Column(
        JSON,
        nullable=True,
        comment="List of fields that were changed"
    )
    
    # Result and status
    success = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the action was successful"
    )
    
    error_code = Column(
        String(100),
        nullable=True,
        comment="Error code if the action failed"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if the action failed"
    )
    
    # Timing information
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the action occurred"
    )
    
    duration_ms = Column(
        Integer,
        nullable=True,
        comment="Duration of the action in milliseconds"
    )
    
    # Source and method
    source_system = Column(
        String(100),
        nullable=True,
        comment="System or component that generated the log"
    )
    
    source_method = Column(
        String(255),
        nullable=True,
        comment="Method or function that performed the action"
    )
    
    api_endpoint = Column(
        String(500),
        nullable=True,
        comment="API endpoint if action was via API"
    )
    
    http_method = Column(
        String(10),
        nullable=True,
        comment="HTTP method if action was via API"
    )
    
    # Security and compliance
    security_level = Column(
        String(50),
        nullable=True,
        comment="Security level of the action"
    )
    
    compliance_tags = Column(
        JSON,
        nullable=True,
        comment="Compliance-related tags"
    )
    
    retention_period_days = Column(
        Integer,
        nullable=True,
        comment="How long to retain this log entry"
    )
    
    # Additional metadata
    environment = Column(
        String(50),
        nullable=True,
        comment="Environment where the action occurred"
    )
    
    version = Column(
        String(50),
        nullable=True,
        comment="System version at the time of action"
    )
    
    additional_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata for the audit log"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="audit_logs",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            'duration_ms >= 0',
            name='chk_audit_logs_duration_positive'
        ),
        CheckConstraint(
            'retention_period_days > 0',
            name='chk_audit_logs_retention_positive'
        ),
        
        # Time-based indexes for efficient querying
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_timestamp_desc', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
        
        # Query optimization indexes
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_resource_id', 'resource_id'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_username', 'username'),
        Index('idx_audit_logs_success', 'success'),
        Index('idx_audit_logs_ip_address', 'ip_address'),
        Index('idx_audit_logs_session_id', 'session_id'),
        Index('idx_audit_logs_request_id', 'request_id'),
        Index('idx_audit_logs_correlation_id', 'correlation_id'),
        
        # Composite indexes for common query patterns
        Index('idx_audit_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_logs_action_timestamp', 'action', 'timestamp'),
        Index('idx_audit_logs_resource_timestamp', 'resource_type', 'timestamp'),
        Index('idx_audit_logs_success_timestamp', 'success', 'timestamp'),
        Index('idx_audit_logs_user_action', 'user_id', 'action'),
        Index('idx_audit_logs_resource_action', 'resource_type', 'action'),
        
        # Partial indexes for failed actions
        Index(
            'idx_audit_logs_failures',
            'timestamp', 'action', 'resource_type',
            postgresql_where="success = false"
        ),
        
        # Partial indexes for recent logs
        Index(
            'idx_audit_logs_recent',
            'user_id', 'action',
            postgresql_where="timestamp > (NOW() - INTERVAL '30 days')"
        ),
        
        # GIN indexes for JSON data
        Index('idx_audit_logs_details_gin', 'details', postgresql_using='gin'),
        Index('idx_audit_logs_metadata_gin', 'additional_metadata', postgresql_using='gin'),
        
        # BRIN indexes for time-series data
        Index('idx_audit_logs_timestamp_brin', 'timestamp', postgresql_using='brin'),
    )
    
    # Validation methods
    @validates('duration_ms')
    def validate_duration(self, key, value):
        """Validate duration is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Duration must be non-negative")
        return value
    
    @validates('retention_period_days')
    def validate_retention_period(self, key, value):
        """Validate retention period is positive."""
        if value is not None and value <= 0:
            raise ValueError("Retention period must be positive")
        return value
    
    # Hybrid properties
    @hybrid_property
    def is_recent(self) -> bool:
        """Check if the log entry is recent (within last hour)."""
        if self.timestamp is None:
            return False
        
        now = datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds() < 3600
    
    @hybrid_property
    def is_security_relevant(self) -> bool:
        """Check if the log entry is security-relevant."""
        security_actions = [
            AuditAction.LOGIN,
            AuditAction.LOGOUT,
            AuditAction.AUTHENTICATE,
            AuditAction.AUTHORIZE
        ]
        return self.action in security_actions or not self.success
    
    @hybrid_property
    def has_changes(self) -> bool:
        """Check if the log entry represents a change."""
        return self.old_values is not None or self.new_values is not None
    
    # Business logic methods
    def get_detail(self, key: str, default: Any = None) -> Any:
        """Get a specific detail from the details JSON."""
        if self.details is None:
            return default
        return self.details.get(key, default)
    
    def set_detail(self, key: str, value: Any) -> None:
        """Set a specific detail in the details JSON."""
        if self.details is None:
            self.details = {}
        self.details[key] = value
    
    def get_old_value(self, field: str, default: Any = None) -> Any:
        """Get the old value for a specific field."""
        if self.old_values is None:
            return default
        return self.old_values.get(field, default)
    
    def get_new_value(self, field: str, default: Any = None) -> Any:
        """Get the new value for a specific field."""
        if self.new_values is None:
            return default
        return self.new_values.get(field, default)
    
    def add_changed_field(self, field: str) -> None:
        """Add a field to the list of changed fields."""
        if self.changed_fields is None:
            self.changed_fields = []
        if field not in self.changed_fields:
            self.changed_fields.append(field)
    
    def set_change(self, field: str, old_value: Any, new_value: Any) -> None:
        """Set old and new values for a changed field."""
        if self.old_values is None:
            self.old_values = {}
        if self.new_values is None:
            self.new_values = {}
        
        self.old_values[field] = old_value
        self.new_values[field] = new_value
        self.add_changed_field(field)
    
    def mark_failed(self, error_code: Optional[str] = None, 
                   error_message: Optional[str] = None) -> None:
        """Mark the audit log as failed."""
        self.success = False
        if error_code:
            self.error_code = error_code
        if error_message:
            self.error_message = error_message
    
    def to_summary(self) -> Dict[str, Any]:
        """Convert to summary format for reporting."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'resource_type': self.resource_type.value,
            'resource_id': self.resource_id,
            'user': self.username or str(self.user_id),
            'success': self.success,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'description': self.description
        }
    
    @classmethod
    def create_log(cls, action: AuditAction, resource_type: AuditResource,
                   user_id: Optional[str] = None, resource_id: Optional[str] = None,
                   description: Optional[str] = None, **kwargs) -> 'AuditLog':
        """
        Create a new audit log entry.
        
        Args:
            action: The action performed
            resource_type: The type of resource affected
            user_id: ID of the user who performed the action
            resource_id: ID of the specific resource
            description: Human-readable description
            **kwargs: Additional fields
            
        Returns:
            New AuditLog instance
        """
        return cls(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            description=description,
            **kwargs
        )
    
    def __repr__(self) -> str:
        """String representation of the audit log."""
        return (
            f"<AuditLog(id={self.id}, action={self.action.value}, "
            f"resource={self.resource_type.value}, user={self.username}, "
            f"timestamp={self.timestamp})>"
        )
