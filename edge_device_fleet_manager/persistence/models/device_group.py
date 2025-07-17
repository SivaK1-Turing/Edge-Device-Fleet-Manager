"""
Device Group Models

SQLAlchemy models for device grouping and organization with
hierarchical relationships and membership management.
"""

import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Enum, Index, ForeignKey, CheckConstraint, UniqueConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import BaseModel, create_foreign_key_constraint


class DeviceGroup(BaseModel):
    """
    Device group model for organizing devices into logical collections.
    
    Supports hierarchical grouping, metadata, and flexible membership
    management for fleet organization and policy application.
    """
    
    __tablename__ = "device_groups"
    
    # Basic group information
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable group name"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Detailed description of the group"
    )
    
    group_type = Column(
        String(100),
        nullable=True,
        comment="Type or category of the group"
    )
    
    # Hierarchical relationships
    parent_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('device_groups.id', name=create_foreign_key_constraint(
            'device_groups', 'parent_group_id', 'device_groups', 'id'
        )),
        nullable=True,
        comment="Reference to parent group for hierarchy"
    )
    
    # Group properties
    is_dynamic = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether group membership is dynamically determined"
    )
    
    dynamic_criteria = Column(
        JSON,
        nullable=True,
        comment="Criteria for dynamic group membership"
    )
    
    # Metadata and configuration
    tags = Column(
        JSON,
        nullable=True,
        comment="Tags for categorization and filtering"
    )
    
    properties = Column(
        JSON,
        nullable=True,
        comment="Additional group properties"
    )
    
    configuration = Column(
        JSON,
        nullable=True,
        comment="Group-specific configuration settings"
    )
    
    # Management information
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'device_groups', 'owner_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="Reference to group owner"
    )
    
    # Statistics (denormalized for performance)
    device_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of devices in the group"
    )
    
    active_device_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of active devices in the group"
    )
    
    # Relationships
    parent_group = relationship(
        "DeviceGroup",
        remote_side="DeviceGroup.id",
        back_populates="child_groups",
        lazy="select"
    )
    
    child_groups = relationship(
        "DeviceGroup",
        back_populates="parent_group",
        lazy="select"
    )
    
    devices = relationship(
        "Device",
        back_populates="device_group",
        lazy="dynamic"
    )
    
    memberships = relationship(
        "DeviceGroupMembership",
        back_populates="device_group",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    owner = relationship(
        "User",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint('name', 'parent_group_id', name='uniq_device_groups_name_parent'),
        
        # Check constraints
        CheckConstraint(
            'device_count >= 0',
            name='chk_device_groups_device_count_positive'
        ),
        CheckConstraint(
            'active_device_count >= 0',
            name='chk_device_groups_active_count_positive'
        ),
        CheckConstraint(
            'active_device_count <= device_count',
            name='chk_device_groups_active_count_valid'
        ),
        
        # Indexes for performance
        Index('idx_device_groups_name', 'name'),
        Index('idx_device_groups_type', 'group_type'),
        Index('idx_device_groups_parent_id', 'parent_group_id'),
        Index('idx_device_groups_owner_id', 'owner_user_id'),
        Index('idx_device_groups_is_dynamic', 'is_dynamic'),
        
        # Composite indexes
        Index('idx_device_groups_type_parent', 'group_type', 'parent_group_id'),
        
        # Partial indexes for active groups
        Index(
            'idx_device_groups_active',
            'name',
            postgresql_where="is_deleted = false"
        ),
        
        # GIN indexes for JSON data
        Index('idx_device_groups_tags_gin', 'tags', postgresql_using='gin'),
        Index('idx_device_groups_properties_gin', 'properties', postgresql_using='gin'),
    )
    
    # Validation methods
    @validates('device_count')
    def validate_device_count(self, key, value):
        """Validate device count is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Device count must be non-negative")
        return value
    
    @validates('active_device_count')
    def validate_active_device_count(self, key, value):
        """Validate active device count is valid."""
        if value is not None:
            if value < 0:
                raise ValueError("Active device count must be non-negative")
            if self.device_count is not None and value > self.device_count:
                raise ValueError("Active device count cannot exceed total device count")
        return value
    
    # Hybrid properties
    @hybrid_property
    def is_root_group(self) -> bool:
        """Check if this is a root group (no parent)."""
        return self.parent_group_id is None
    
    @hybrid_property
    def has_devices(self) -> bool:
        """Check if group has any devices."""
        return self.device_count > 0
    
    @hybrid_property
    def activity_ratio(self) -> Optional[float]:
        """Calculate ratio of active devices to total devices."""
        if self.device_count == 0:
            return None
        return self.active_device_count / self.device_count
    
    # Business logic methods
    def add_device(self, device) -> None:
        """Add a device to the group."""
        device.device_group_id = self.id
        self.device_count += 1
        if device.is_online:
            self.active_device_count += 1
    
    def remove_device(self, device) -> None:
        """Remove a device from the group."""
        if device.device_group_id == self.id:
            device.device_group_id = None
            self.device_count = max(0, self.device_count - 1)
            if device.is_online:
                self.active_device_count = max(0, self.active_device_count - 1)
    
    def update_device_counts(self) -> None:
        """Update device counts from actual device relationships."""
        from sqlalchemy import func
        from .device import Device, DeviceStatus
        
        # This would be called in a database session context
        # Implementation would query actual device counts
        pass
    
    def get_all_descendant_groups(self) -> List['DeviceGroup']:
        """Get all descendant groups recursively."""
        descendants = []
        for child in self.child_groups:
            descendants.append(child)
            descendants.extend(child.get_all_descendant_groups())
        return descendants
    
    def get_path_to_root(self) -> List['DeviceGroup']:
        """Get path from this group to root group."""
        path = [self]
        current = self
        while current.parent_group:
            current = current.parent_group
            path.append(current)
        return path
    
    def is_ancestor_of(self, other_group: 'DeviceGroup') -> bool:
        """Check if this group is an ancestor of another group."""
        current = other_group.parent_group
        while current:
            if current.id == self.id:
                return True
            current = current.parent_group
        return False
    
    def evaluate_dynamic_criteria(self, device) -> bool:
        """Evaluate if a device matches dynamic group criteria."""
        if not self.is_dynamic or not self.dynamic_criteria:
            return False
        
        # Implementation would evaluate criteria against device properties
        # This is a placeholder for the actual logic
        criteria = self.dynamic_criteria
        
        # Example criteria evaluation
        if 'device_type' in criteria:
            if device.device_type.value not in criteria['device_type']:
                return False
        
        if 'status' in criteria:
            if device.status.value not in criteria['status']:
                return False
        
        if 'tags' in criteria and device.tags:
            required_tags = set(criteria['tags'])
            device_tags = set(device.tags.keys() if isinstance(device.tags, dict) else device.tags)
            if not required_tags.issubset(device_tags):
                return False
        
        return True
    
    def __repr__(self) -> str:
        """String representation of the device group."""
        return f"<DeviceGroup(id={self.id}, name='{self.name}', devices={self.device_count})>"


class DeviceGroupMembership(BaseModel):
    """
    Explicit device group membership model.
    
    Tracks device membership in groups with additional metadata
    and membership-specific properties.
    """
    
    __tablename__ = "device_group_memberships"
    
    # References
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('devices.id', name=create_foreign_key_constraint(
            'device_group_memberships', 'device_id', 'devices', 'id'
        )),
        nullable=False,
        comment="Reference to the device"
    )
    
    device_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('device_groups.id', name=create_foreign_key_constraint(
            'device_group_memberships', 'device_group_id', 'device_groups', 'id'
        )),
        nullable=False,
        comment="Reference to the device group"
    )
    
    # Membership properties
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the primary group for the device"
    )
    
    role = Column(
        String(100),
        nullable=True,
        comment="Role of the device within the group"
    )
    
    priority = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Priority of this membership"
    )
    
    # Membership metadata
    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the device joined the group"
    )
    
    added_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', name=create_foreign_key_constraint(
            'device_group_memberships', 'added_by_user_id', 'users', 'id'
        )),
        nullable=True,
        comment="User who added the device to the group"
    )
    
    membership_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional membership metadata"
    )
    
    # Relationships
    device = relationship(
        "Device",
        lazy="select"
    )
    
    device_group = relationship(
        "DeviceGroup",
        back_populates="memberships",
        lazy="select"
    )
    
    added_by = relationship(
        "User",
        lazy="select"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Unique constraints
        UniqueConstraint(
            'device_id', 'device_group_id',
            name='uniq_device_group_memberships_device_group'
        ),
        
        # Indexes for performance
        Index('idx_memberships_device_id', 'device_id'),
        Index('idx_memberships_group_id', 'device_group_id'),
        Index('idx_memberships_is_primary', 'is_primary'),
        Index('idx_memberships_joined_at', 'joined_at'),
        
        # Composite indexes
        Index('idx_memberships_device_primary', 'device_id', 'is_primary'),
        Index('idx_memberships_group_priority', 'device_group_id', 'priority'),
    )
    
    def __repr__(self) -> str:
        """String representation of the membership."""
        return (
            f"<DeviceGroupMembership(device_id={self.device_id}, "
            f"group_id={self.device_group_id}, primary={self.is_primary})>"
        )
