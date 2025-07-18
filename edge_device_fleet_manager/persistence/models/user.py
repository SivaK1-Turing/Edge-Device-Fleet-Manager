"""
User Model

SQLAlchemy model for user management with role-based access control,
authentication, and audit trail support.
"""

import enum
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, JSON,
    Enum, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel


class UserRole(enum.Enum):
    """User role enumeration."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DEVICE_MANAGER = "device_manager"
    ANALYST = "analyst"
    GUEST = "guest"


class UserStatus(enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_ACTIVATION = "pending_activation"
    LOCKED = "locked"


class User(BaseModel):
    """
    User model for authentication and authorization.
    
    Provides comprehensive user management with role-based access control,
    security features, and audit trail support.
    """
    
    __tablename__ = "users"
    
    # Basic user information
    username = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Unique username for login"
    )
    
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="User email address"
    )
    
    first_name = Column(
        String(100),
        nullable=True,
        comment="User first name"
    )
    
    last_name = Column(
        String(100),
        nullable=True,
        comment="User last name"
    )
    
    display_name = Column(
        String(200),
        nullable=True,
        comment="Display name for UI"
    )
    
    # Authentication
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )
    
    salt = Column(
        String(100),
        nullable=True,
        comment="Password salt"
    )
    
    # Role and permissions
    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.VIEWER,
        comment="User role for access control"
    )
    
    status = Column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.PENDING_ACTIVATION,
        comment="Current user status"
    )
    
    permissions = Column(
        JSON,
        nullable=True,
        comment="Additional permissions as JSON"
    )
    
    # Security and session management
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful login"
    )
    
    last_login_ip = Column(
        String(45),
        nullable=True,
        comment="IP address of last login"
    )
    
    failed_login_attempts = Column(
        String(10),
        nullable=False,
        default=0,
        comment="Number of consecutive failed login attempts"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp"
    )
    
    # Multi-factor authentication
    mfa_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Multi-factor authentication enabled"
    )
    
    mfa_secret = Column(
        String(255),
        nullable=True,
        comment="MFA secret key"
    )
    
    backup_codes = Column(
        JSON,
        nullable=True,
        comment="MFA backup codes"
    )
    
    # API access
    api_key = Column(
        String(255),
        nullable=True,
        comment="API key for programmatic access"
    )
    
    api_key_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="API key expiration timestamp"
    )
    
    # Profile and preferences
    timezone = Column(
        String(50),
        nullable=True,
        default="UTC",
        comment="User timezone preference"
    )
    
    language = Column(
        String(10),
        nullable=True,
        default="en",
        comment="User language preference"
    )
    
    preferences = Column(
        JSON,
        nullable=True,
        comment="User preferences as JSON"
    )
    
    # Contact information
    phone = Column(
        String(20),
        nullable=True,
        comment="Phone number"
    )
    
    department = Column(
        String(100),
        nullable=True,
        comment="Department or team"
    )
    
    title = Column(
        String(100),
        nullable=True,
        comment="Job title"
    )
    
    # Activation and verification
    email_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Email verification status"
    )
    
    email_verification_token = Column(
        String(255),
        nullable=True,
        comment="Email verification token"
    )
    
    password_reset_token = Column(
        String(255),
        nullable=True,
        comment="Password reset token"
    )
    
    password_reset_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Password reset token expiration"
    )
    
    # Relationships
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        lazy="dynamic"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint('username', name='uniq_users_username'),
        UniqueConstraint('email', name='uniq_users_email'),
        UniqueConstraint('api_key', name='uniq_users_api_key'),
        
        # Check constraints
        CheckConstraint(
            'failed_login_attempts >= 0',
            name='chk_users_failed_attempts_positive'
        ),
        
        # Indexes for performance
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        Index('idx_users_status', 'status'),
        Index('idx_users_last_login', 'last_login'),
        Index('idx_users_api_key', 'api_key'),
        
        # Composite indexes
        Index('idx_users_role_status', 'role', 'status'),
        Index('idx_users_status_last_login', 'status', 'last_login'),
        
        # Partial indexes for active users
        Index(
            'idx_users_active_username',
            'username',
            postgresql_where="status = 'active' AND is_deleted = false"
        ),
    )
    
    # Validation methods
    @validates('email')
    def validate_email(self, key, value):
        """Validate email format."""
        import re
        if value and not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', value):
            raise ValueError("Invalid email format")
        return value
    
    @validates('failed_login_attempts')
    def validate_failed_attempts(self, key, value):
        """Validate failed login attempts is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Failed login attempts must be non-negative")
        return value
    
    # Hybrid properties
    @hybrid_property
    def full_name(self) -> str:
        """Get full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE and not self.is_deleted
    
    @hybrid_property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.status == UserStatus.LOCKED:
            return True
        
        if self.locked_until:
            return datetime.now(timezone.utc) < self.locked_until
        
        return False
    
    @hybrid_property
    def has_admin_role(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    # Business logic methods
    def check_password(self, password: str) -> bool:
        """Check if provided password matches."""
        # Implementation would use proper password hashing
        # This is a placeholder
        import hashlib
        if self.salt:
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), self.salt.encode(), 100000)
            return hashed.hex() == self.password_hash
        return False
    
    def set_password(self, password: str) -> None:
        """Set user password with proper hashing."""
        import hashlib
        import secrets
        
        self.salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), self.salt.encode(), 100000)
        self.password_hash = hashed.hex()
    
    def record_login(self, ip_address: Optional[str] = None) -> None:
        """Record successful login."""
        self.last_login = datetime.now(timezone.utc)
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def record_failed_login(self, max_attempts: int = 5, lockout_duration: int = 900) -> None:
        """Record failed login attempt."""
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.status = UserStatus.LOCKED
            self.locked_until = datetime.now(timezone.utc) + timedelta(seconds=lockout_duration)
    
    def unlock_account(self) -> None:
        """Unlock user account."""
        self.status = UserStatus.ACTIVE
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        # Role-based permissions
        role_permissions = {
            UserRole.SUPER_ADMIN: ['*'],
            UserRole.ADMIN: [
                'devices.*', 'users.*', 'analytics.*', 'system.*'
            ],
            UserRole.DEVICE_MANAGER: [
                'devices.*', 'telemetry.read', 'analytics.read'
            ],
            UserRole.OPERATOR: [
                'devices.read', 'devices.update', 'telemetry.read', 'analytics.read'
            ],
            UserRole.ANALYST: [
                'devices.read', 'telemetry.read', 'analytics.*'
            ],
            UserRole.VIEWER: [
                'devices.read', 'telemetry.read', 'analytics.read'
            ],
            UserRole.GUEST: [
                'devices.read'
            ]
        }
        
        role_perms = role_permissions.get(self.role, [])
        
        # Check wildcard permission
        if '*' in role_perms:
            return True
        
        # Check exact permission
        if permission in role_perms:
            return True
        
        # Check wildcard patterns
        for perm in role_perms:
            if perm.endswith('.*'):
                prefix = perm[:-2]
                if permission.startswith(prefix + '.'):
                    return True
        
        # Check additional permissions
        if self.permissions and permission in self.permissions:
            return self.permissions[permission]
        
        return False
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, username='{self.username}', role={self.role.value})>"
