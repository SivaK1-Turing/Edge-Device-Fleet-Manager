"""
Device Group Repository

Specialized repository for device group management with hierarchical
operations, membership management, and group-based queries.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.device_group import DeviceGroup, DeviceGroupMembership


class DeviceGroupRepository(BaseRepository[DeviceGroup]):
    """
    Device group repository with hierarchical and membership management.
    
    Provides specialized operations for device groups including
    hierarchy management, membership operations, and group queries.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, DeviceGroup)
    
    async def get_root_groups(self, skip: int = 0, limit: int = 100) -> List[DeviceGroup]:
        """Get root groups (groups without parent)."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.parent_group_id.is_(None),
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting root groups: {e}")
            raise RepositoryError(f"Failed to get root groups: {e}")
    
    async def get_child_groups(self, parent_id: uuid.UUID,
                              skip: int = 0, limit: int = 100) -> List[DeviceGroup]:
        """Get child groups of a parent group."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.parent_group_id == parent_id,
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting child groups for {parent_id}: {e}")
            raise RepositoryError(f"Failed to get child groups: {e}")
    
    async def get_by_type(self, group_type: str,
                         skip: int = 0, limit: int = 100) -> List[DeviceGroup]:
        """Get groups by type."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.group_type == group_type,
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting groups by type {group_type}: {e}")
            raise RepositoryError(f"Failed to get groups by type: {e}")
    
    async def get_dynamic_groups(self, skip: int = 0, limit: int = 100) -> List[DeviceGroup]:
        """Get dynamic groups."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.is_dynamic == True,
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting dynamic groups: {e}")
            raise RepositoryError(f"Failed to get dynamic groups: {e}")
    
    async def get_group_hierarchy(self, group_id: uuid.UUID) -> List[DeviceGroup]:
        """Get complete hierarchy path for a group."""
        try:
            hierarchy = []
            current_group = await self.get(group_id)
            
            while current_group:
                hierarchy.append(current_group)
                if current_group.parent_group_id:
                    current_group = await self.get(current_group.parent_group_id)
                else:
                    break
            
            return list(reversed(hierarchy))  # Root to leaf order
            
        except Exception as e:
            self.logger.error(f"Error getting group hierarchy for {group_id}: {e}")
            raise RepositoryError(f"Failed to get group hierarchy: {e}")
    
    async def get_group_statistics(self) -> Dict[str, Any]:
        """Get device group statistics."""
        try:
            # Total groups
            total_query = select(func.count(self.model.id)).where(self.model.is_deleted == False)
            total_result = await self.session.execute(total_query)
            total_groups = total_result.scalar()
            
            # Root groups count
            root_query = select(func.count(self.model.id)).where(
                and_(
                    self.model.parent_group_id.is_(None),
                    self.model.is_deleted == False
                )
            )
            root_result = await self.session.execute(root_query)
            root_groups = root_result.scalar()
            
            # Dynamic groups count
            dynamic_query = select(func.count(self.model.id)).where(
                and_(
                    self.model.is_dynamic == True,
                    self.model.is_deleted == False
                )
            )
            dynamic_result = await self.session.execute(dynamic_query)
            dynamic_groups = dynamic_result.scalar()
            
            # Groups by type
            type_query = (
                select(self.model.group_type, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.group_type)
            )
            type_result = await self.session.execute(type_query)
            type_counts = dict(type_result.all())
            
            # Device count statistics
            device_stats_query = select(
                func.sum(self.model.device_count),
                func.sum(self.model.active_device_count),
                func.avg(self.model.device_count)
            ).where(self.model.is_deleted == False)
            device_stats_result = await self.session.execute(device_stats_query)
            total_devices, active_devices, avg_devices = device_stats_result.first()
            
            return {
                'total_groups': total_groups,
                'root_groups': root_groups,
                'dynamic_groups': dynamic_groups,
                'static_groups': total_groups - dynamic_groups,
                'type_distribution': type_counts,
                'device_statistics': {
                    'total_devices_in_groups': total_devices or 0,
                    'active_devices_in_groups': active_devices or 0,
                    'average_devices_per_group': float(avg_devices) if avg_devices else 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting group statistics: {e}")
            raise RepositoryError(f"Failed to get group statistics: {e}")
    
    async def search_groups(self, search_term: str, skip: int = 0, 
                           limit: int = 100) -> List[DeviceGroup]:
        """Search groups by name or description."""
        search_fields = ['name', 'description', 'group_type']
        return await self.search(search_term, search_fields, skip, limit)
