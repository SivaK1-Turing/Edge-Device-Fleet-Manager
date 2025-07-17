"""
Base Repository Implementation

Generic repository base class with async support, transaction management,
and comprehensive CRUD operations for all model types.
"""

import uuid
from abc import ABC, abstractmethod
from typing import (
    TypeVar, Generic, Type, Optional, List, Dict, Any, Union,
    Sequence, Callable, Tuple
)
from datetime import datetime, timezone

from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.sql import Select

from ...core.logging import get_logger
from ..models.base import BaseModel

# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = get_logger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class BaseRepository(Generic[ModelType], ABC):
    """
    Generic base repository with comprehensive CRUD operations.
    
    Provides async/await support, transaction management, query optimization,
    and common database operations for all model types.
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        Initialize repository.
        
        Args:
            session: Async SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
        self.logger = get_logger(f"{__name__}.{model.__name__}Repository")
    
    async def create(self, obj_in: Union[CreateSchemaType, Dict[str, Any]], 
                    **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_in: Input data (schema or dict)
            **kwargs: Additional fields
            
        Returns:
            Created model instance
        """
        try:
            # Convert schema to dict if needed
            if hasattr(obj_in, 'dict'):
                create_data = obj_in.dict()
            elif isinstance(obj_in, dict):
                create_data = obj_in.copy()
            else:
                create_data = obj_in
            
            # Add any additional kwargs
            create_data.update(kwargs)
            
            # Create model instance
            db_obj = self.model(**create_data)
            
            # Add to session and flush to get ID
            self.session.add(db_obj)
            await self.session.flush()
            await self.session.refresh(db_obj)
            
            self.logger.debug(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
            
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to create {self.model.__name__}: {e}")
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error creating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to create {self.model.__name__}: {e}")
    
    async def get(self, id: Union[uuid.UUID, str], 
                 include_deleted: bool = False) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Model instance or None
        """
        try:
            query = select(self.model).where(self.model.id == id)
            
            # Filter out soft-deleted records unless requested
            if not include_deleted and hasattr(self.model, 'is_deleted'):
                query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__}: {e}")
    
    async def get_multi(self, skip: int = 0, limit: int = 100,
                       include_deleted: bool = False,
                       order_by: Optional[str] = None,
                       **filters) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records
            order_by: Field to order by
            **filters: Additional filters
            
        Returns:
            List of model instances
        """
        try:
            query = select(self.model)
            
            # Apply filters
            query = self._apply_filters(query, include_deleted, **filters)
            
            # Apply ordering
            if order_by:
                if hasattr(self.model, order_by):
                    order_field = getattr(self.model, order_by)
                    query = query.order_by(order_field)
            else:
                # Default ordering by created_at if available
                if hasattr(self.model, 'created_at'):
                    query = query.order_by(self.model.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__} records: {e}")
    
    async def update(self, id: Union[uuid.UUID, str],
                    obj_in: Union[UpdateSchemaType, Dict[str, Any]],
                    **kwargs) -> Optional[ModelType]:
        """
        Update a record.
        
        Args:
            id: Record ID
            obj_in: Update data (schema or dict)
            **kwargs: Additional fields
            
        Returns:
            Updated model instance or None
        """
        try:
            # Get existing record
            db_obj = await self.get(id)
            if not db_obj:
                return None
            
            # Convert schema to dict if needed
            if hasattr(obj_in, 'dict'):
                update_data = obj_in.dict(exclude_unset=True)
            elif isinstance(obj_in, dict):
                update_data = obj_in.copy()
            else:
                update_data = obj_in
            
            # Add any additional kwargs
            update_data.update(kwargs)
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Update timestamp if available
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = datetime.now(timezone.utc)
            
            await self.session.flush()
            await self.session.refresh(db_obj)
            
            self.logger.debug(f"Updated {self.model.__name__} with ID: {id}")
            return db_obj
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error updating {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to update {self.model.__name__}: {e}")
    
    async def delete(self, id: Union[uuid.UUID, str], 
                    soft_delete: bool = True) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            soft_delete: Whether to soft delete (if supported)
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db_obj = await self.get(id)
            if not db_obj:
                return False
            
            if soft_delete and hasattr(db_obj, 'soft_delete'):
                # Soft delete
                db_obj.soft_delete()
                await self.session.flush()
            else:
                # Hard delete
                await self.session.delete(db_obj)
                await self.session.flush()
            
            self.logger.debug(f"Deleted {self.model.__name__} with ID: {id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error deleting {self.model.__name__} {id}: {e}")
            raise RepositoryError(f"Failed to delete {self.model.__name__}: {e}")
    
    async def count(self, include_deleted: bool = False, **filters) -> int:
        """
        Count records with optional filtering.
        
        Args:
            include_deleted: Whether to include soft-deleted records
            **filters: Additional filters
            
        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(self.model.id))
            query = self._apply_filters(query, include_deleted, **filters)
            
            result = await self.session.execute(query)
            return result.scalar()
            
        except Exception as e:
            self.logger.error(f"Error counting {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to count {self.model.__name__}: {e}")
    
    async def exists(self, id: Union[uuid.UUID, str],
                    include_deleted: bool = False) -> bool:
        """
        Check if a record exists.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            True if exists, False otherwise
        """
        try:
            query = select(func.count(self.model.id)).where(self.model.id == id)
            
            if not include_deleted and hasattr(self.model, 'is_deleted'):
                query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar() > 0
            
        except Exception as e:
            self.logger.error(f"Error checking existence of {self.model.__name__} {id}: {e}")
            return False
    
    async def bulk_create(self, objects: List[Union[CreateSchemaType, Dict[str, Any]]]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            objects: List of input data
            
        Returns:
            List of created model instances
        """
        try:
            db_objects = []
            
            for obj_in in objects:
                # Convert schema to dict if needed
                if hasattr(obj_in, 'dict'):
                    create_data = obj_in.dict()
                elif isinstance(obj_in, dict):
                    create_data = obj_in.copy()
                else:
                    create_data = obj_in
                
                db_obj = self.model(**create_data)
                db_objects.append(db_obj)
            
            # Add all objects to session
            self.session.add_all(db_objects)
            await self.session.flush()
            
            # Refresh all objects to get IDs
            for db_obj in db_objects:
                await self.session.refresh(db_obj)
            
            self.logger.debug(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to bulk create {self.model.__name__}: {e}")
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in bulk.
        
        Args:
            updates: List of update dictionaries with 'id' and update fields
            
        Returns:
            Number of updated records
        """
        try:
            updated_count = 0
            
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                record_id = update_data.pop('id')
                
                # Add updated_at timestamp if available
                if hasattr(self.model, 'updated_at'):
                    update_data['updated_at'] = datetime.now(timezone.utc)
                
                query = (
                    update(self.model)
                    .where(self.model.id == record_id)
                    .values(**update_data)
                )
                
                result = await self.session.execute(query)
                updated_count += result.rowcount
            
            await self.session.flush()
            
            self.logger.debug(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error bulk updating {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to bulk update {self.model.__name__}: {e}")
    
    def _apply_filters(self, query: Select, include_deleted: bool = False, **filters) -> Select:
        """
        Apply filters to a query.
        
        Args:
            query: SQLAlchemy query
            include_deleted: Whether to include soft-deleted records
            **filters: Filter conditions
            
        Returns:
            Modified query
        """
        # Filter out soft-deleted records unless requested
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        # Apply additional filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                
                if isinstance(value, list):
                    # IN clause for lists
                    query = query.where(column.in_(value))
                elif isinstance(value, dict):
                    # Handle complex filters
                    for op, val in value.items():
                        if op == 'gt':
                            query = query.where(column > val)
                        elif op == 'gte':
                            query = query.where(column >= val)
                        elif op == 'lt':
                            query = query.where(column < val)
                        elif op == 'lte':
                            query = query.where(column <= val)
                        elif op == 'ne':
                            query = query.where(column != val)
                        elif op == 'like':
                            query = query.where(column.like(f"%{val}%"))
                        elif op == 'ilike':
                            query = query.where(column.ilike(f"%{val}%"))
                else:
                    # Simple equality
                    query = query.where(column == value)
        
        return query
    
    async def get_with_relationships(self, id: Union[uuid.UUID, str],
                                   relationships: List[str]) -> Optional[ModelType]:
        """
        Get a record with specified relationships loaded.
        
        Args:
            id: Record ID
            relationships: List of relationship names to load
            
        Returns:
            Model instance with relationships loaded
        """
        try:
            query = select(self.model).where(self.model.id == id)
            
            # Add relationship loading
            for rel in relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting {self.model.__name__} with relationships: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__} with relationships: {e}")
    
    async def search(self, search_term: str, search_fields: List[str],
                    skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Search records by text in specified fields.
        
        Args:
            search_term: Text to search for
            search_fields: List of field names to search in
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching model instances
        """
        try:
            query = select(self.model)
            
            # Build search conditions
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    search_conditions.append(column.ilike(f"%{search_term}%"))
            
            if search_conditions:
                query = query.where(or_(*search_conditions))
            
            # Filter out soft-deleted records
            if hasattr(self.model, 'is_deleted'):
                query = query.where(self.model.is_deleted == False)
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error searching {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to search {self.model.__name__}: {e}")
