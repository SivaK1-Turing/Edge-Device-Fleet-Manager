"""
Audit Log Repository

Specialized repository for audit log management with compliance,
security monitoring, and audit trail capabilities.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.audit_log import AuditLog, AuditAction, AuditResource


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Audit log repository with compliance and security monitoring.
    
    Provides specialized operations for audit logs including
    security monitoring, compliance reporting, and audit trails.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)
    
    async def get_by_user(self, user_id: uuid.UUID,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a specific user."""
        try:
            query = select(self.model).where(self.model.user_id == user_id)
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting audit logs for user {user_id}: {e}")
            raise RepositoryError(f"Failed to get audit logs for user: {e}")
    
    async def get_by_action(self, action: AuditAction,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by action type."""
        try:
            query = select(self.model).where(self.model.action == action)
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting audit logs by action {action}: {e}")
            raise RepositoryError(f"Failed to get audit logs by action: {e}")
    
    async def get_by_resource(self, resource_type: AuditResource,
                             resource_id: Optional[str] = None,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by resource type and optionally resource ID."""
        try:
            query = select(self.model).where(self.model.resource_type == resource_type)
            
            if resource_id:
                query = query.where(self.model.resource_id == resource_id)
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting audit logs by resource {resource_type}: {e}")
            raise RepositoryError(f"Failed to get audit logs by resource: {e}")
    
    async def get_failed_actions(self, start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None,
                                skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Get failed audit log entries."""
        try:
            query = select(self.model).where(self.model.success == False)
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting failed audit logs: {e}")
            raise RepositoryError(f"Failed to get failed audit logs: {e}")
    
    async def get_security_events(self, start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None,
                                 skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Get security-related audit log entries."""
        try:
            security_actions = [
                AuditAction.LOGIN,
                AuditAction.LOGOUT,
                AuditAction.AUTHENTICATE,
                AuditAction.AUTHORIZE
            ]
            
            query = select(self.model).where(
                or_(
                    self.model.action.in_(security_actions),
                    self.model.success == False
                )
            )
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting security events: {e}")
            raise RepositoryError(f"Failed to get security events: {e}")
    
    async def get_audit_statistics(self, start_time: Optional[datetime] = None,
                                  end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get audit log statistics."""
        try:
            query = select(self.model)
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            # Total entries
            total_query = select(func.count(self.model.id)).select_from(query.subquery())
            total_result = await self.session.execute(total_query)
            total_entries = total_result.scalar()
            
            # Success/failure distribution
            success_query = (
                select(self.model.success, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.success)
            )
            success_result = await self.session.execute(success_query)
            success_counts = dict(success_result.all())
            
            # Actions distribution
            action_query = (
                select(self.model.action, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.action)
            )
            action_result = await self.session.execute(action_query)
            action_counts = dict(action_result.all())
            
            # Resource types distribution
            resource_query = (
                select(self.model.resource_type, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.resource_type)
            )
            resource_result = await self.session.execute(resource_query)
            resource_counts = dict(resource_result.all())
            
            # Recent activity (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_query = select(func.count(self.model.id)).where(
                self.model.timestamp >= recent_cutoff
            )
            recent_result = await self.session.execute(recent_query)
            recent_activity = recent_result.scalar()
            
            return {
                'total_entries': total_entries,
                'recent_activity_24h': recent_activity,
                'success_rate': (success_counts.get(True, 0) / total_entries * 100) if total_entries > 0 else 0,
                'failure_rate': (success_counts.get(False, 0) / total_entries * 100) if total_entries > 0 else 0,
                'action_distribution': {
                    action.value: count for action, count in action_counts.items()
                },
                'resource_distribution': {
                    resource.value: count for resource, count in resource_counts.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting audit statistics: {e}")
            raise RepositoryError(f"Failed to get audit statistics: {e}")
    
    async def cleanup_old_logs(self, retention_days: int = 365) -> int:
        """Clean up old audit logs based on retention policy."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Count records to be deleted
            count_query = select(func.count(self.model.id)).where(
                self.model.timestamp < cutoff_date
            )
            count_result = await self.session.execute(count_query)
            count = count_result.scalar()
            
            # Delete old records
            from sqlalchemy import delete
            delete_query = delete(self.model).where(self.model.timestamp < cutoff_date)
            await self.session.execute(delete_query)
            await self.session.flush()
            
            self.logger.info(f"Cleaned up {count} old audit log records")
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old audit logs: {e}")
            raise RepositoryError(f"Failed to cleanup old audit logs: {e}")
    
    async def search_audit_logs(self, search_term: str, skip: int = 0, 
                               limit: int = 100) -> List[AuditLog]:
        """Search audit logs by description or resource name."""
        search_fields = ['description', 'resource_name', 'username']
        return await self.search(search_term, search_fields, skip, limit)
