"""
Base Model Classes

Provides foundational SQLAlchemy models with common functionality including:
- Timestamp tracking (created_at, updated_at)
- Soft delete capability
- UUID primary keys
- JSON serialization
- Audit trail support
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import Column, DateTime, String, Boolean, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ...core.logging import get_logger

# Create base class for all models
Base = declarative_base()

# Type variable for model classes
ModelType = TypeVar("ModelType", bound="BaseModel")

logger = get_logger(__name__)


class TimestampMixin:
    """Mixin for automatic timestamp tracking."""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="Timestamp when the record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="Timestamp when the record was last updated"
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the record was soft deleted"
    )
    
    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='false',
        comment="Flag indicating if the record is soft deleted"
    )
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if the record is active (not soft deleted)."""
        return not self.is_deleted
    
    def soft_delete(self) -> None:
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        logger.debug(f"Soft deleted {self.__class__.__name__} with ID {self.id}")
    
    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        logger.debug(f"Restored {self.__class__.__name__} with ID {self.id}")


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Base model class for all database entities.
    
    Provides:
    - UUID primary key
    - Timestamp tracking
    - Soft delete capability
    - JSON serialization
    - Common query methods
    """
    
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the record"
    )
    
    # Metadata fields
    metadata_json = Column(
        Text,
        nullable=True,
        comment="JSON metadata for extensible attributes"
    )
    
    version = Column(
        String(50),
        nullable=True,
        comment="Version information for the record"
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            include_relationships: Whether to include relationship data
            
        Returns:
            Dictionary representation of the model
        """
        result = {}
        
        # Include column values
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle special types
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            else:
                result[column.name] = value
        
        # Include relationships if requested
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                try:
                    value = getattr(self, relationship.key)
                    if value is not None:
                        if hasattr(value, '__iter__') and not isinstance(value, str):
                            # Collection relationship
                            result[relationship.key] = [
                                item.to_dict() if hasattr(item, 'to_dict') else str(item)
                                for item in value
                            ]
                        else:
                            # Single relationship
                            result[relationship.key] = (
                                value.to_dict() if hasattr(value, 'to_dict') else str(value)
                            )
                except Exception as e:
                    logger.warning(f"Failed to serialize relationship {relationship.key}: {e}")
                    result[relationship.key] = None
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[set] = None) -> None:
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary with update values
            exclude: Set of fields to exclude from update
        """
        exclude = exclude or {'id', 'created_at'}
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                # Handle special types
                if key.endswith('_at') and isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Failed to parse datetime for {key}: {value}")
                        continue
                
                setattr(self, key, value)
        
        self.updated_at = datetime.now(timezone.utc)
    
    @classmethod
    def create(cls: Type[ModelType], **kwargs) -> ModelType:
        """
        Create a new instance of the model.
        
        Args:
            **kwargs: Field values for the new instance
            
        Returns:
            New model instance
        """
        return cls(**kwargs)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.__repr__()


# Event listeners for automatic timestamp updates
@event.listens_for(BaseModel, 'before_update', propagate=True)
def update_timestamp(mapper, connection, target):
    """Automatically update the updated_at timestamp before updates."""
    target.updated_at = datetime.now(timezone.utc)


@event.listens_for(BaseModel, 'before_insert', propagate=True)
def set_creation_timestamp(mapper, connection, target):
    """Ensure creation timestamp is set before insert."""
    if target.created_at is None:
        target.created_at = datetime.now(timezone.utc)
    if target.updated_at is None:
        target.updated_at = target.created_at


# Index creation helpers
def create_index(table_name: str, column_names: list, unique: bool = False,
                partial: Optional[str] = None) -> str:
    """
    Generate index creation SQL.

    Args:
        table_name: Name of the table
        column_names: List of column names for the index
        unique: Whether the index should be unique
        partial: Partial index condition

    Returns:
        Index name for reference
    """
    index_name = f"idx_{table_name}_{'_'.join(column_names)}"
    if unique:
        index_name = f"uniq_{table_name}_{'_'.join(column_names)}"

    return index_name


# Custom constraint helpers
def create_foreign_key_constraint(table_name: str, column_name: str,
                                referenced_table: str, referenced_column: str = 'id',
                                on_delete: str = 'CASCADE') -> str:
    """
    Generate foreign key constraint name.

    Args:
        table_name: Name of the table with the foreign key
        column_name: Name of the foreign key column
        referenced_table: Name of the referenced table
        referenced_column: Name of the referenced column
        on_delete: ON DELETE action

    Returns:
        Constraint name for reference
    """
    return f"fk_{table_name}_{column_name}_{referenced_table}_{referenced_column}"
