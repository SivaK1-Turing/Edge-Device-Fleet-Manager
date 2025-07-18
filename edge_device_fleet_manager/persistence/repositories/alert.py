"""
Alert Repository

Specialized repository for alert management with severity-based queries,
status tracking, and alert lifecycle operations.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.alert import Alert, AlertSeverity, AlertStatus


class AlertRepository(BaseRepository[Alert]):
    """
    Alert repository with alert management and lifecycle operations.
    
    Provides specialized operations for alerts including
    severity-based queries, status management, and reporting.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Alert)
    
    async def get_by_severity(self, severity: AlertSeverity,
                             skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get alerts by severity."""
        try:
            query = select(self.model).where(self.model.severity == severity)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(desc(self.model.first_occurred))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting alerts by severity {severity}: {e}")
            raise RepositoryError(f"Failed to get alerts by severity: {e}")
    
    async def get_by_status(self, status: AlertStatus,
                           skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get alerts by status."""
        try:
            query = select(self.model).where(self.model.status == status)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(desc(self.model.first_occurred))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting alerts by status {status}: {e}")
            raise RepositoryError(f"Failed to get alerts by status: {e}")
    
    async def get_open_alerts(self, skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get all open alerts."""
        try:
            open_statuses = [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS]
            
            query = select(self.model).where(self.model.status.in_(open_statuses))
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(desc(self.model.severity), desc(self.model.first_occurred))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting open alerts: {e}")
            raise RepositoryError(f"Failed to get open alerts: {e}")
    
    async def get_critical_alerts(self, skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get critical alerts."""
        return await self.get_by_severity(AlertSeverity.CRITICAL, skip, limit)
    
    async def get_by_device(self, device_id: uuid.UUID,
                           skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get alerts for a specific device."""
        try:
            query = select(self.model).where(self.model.device_id == device_id)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(desc(self.model.first_occurred))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting alerts for device {device_id}: {e}")
            raise RepositoryError(f"Failed to get alerts for device: {e}")
    
    async def get_recent_alerts(self, hours: int = 24,
                               skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get recent alerts within specified hours."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = select(self.model).where(self.model.first_occurred >= cutoff_time)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(desc(self.model.first_occurred))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            raise RepositoryError(f"Failed to get recent alerts: {e}")
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        try:
            # Total alerts
            total_query = select(func.count(self.model.id)).where(self.model.is_deleted == False)
            total_result = await self.session.execute(total_query)
            total_alerts = total_result.scalar()
            
            # Alerts by severity
            severity_query = (
                select(self.model.severity, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.severity)
            )
            severity_result = await self.session.execute(severity_query)
            severity_counts = dict(severity_result.all())
            
            # Alerts by status
            status_query = (
                select(self.model.status, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.status)
            )
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.all())
            
            # Open alerts count
            open_statuses = [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS]
            open_query = select(func.count(self.model.id)).where(
                and_(
                    self.model.status.in_(open_statuses),
                    self.model.is_deleted == False
                )
            )
            open_result = await self.session.execute(open_query)
            open_alerts = open_result.scalar()
            
            # Recent alerts (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_query = select(func.count(self.model.id)).where(
                and_(
                    self.model.first_occurred >= recent_cutoff,
                    self.model.is_deleted == False
                )
            )
            recent_result = await self.session.execute(recent_query)
            recent_alerts = recent_result.scalar()
            
            return {
                'total_alerts': total_alerts,
                'open_alerts': open_alerts,
                'recent_alerts_24h': recent_alerts,
                'severity_distribution': {
                    severity.value: count for severity, count in severity_counts.items()
                },
                'status_distribution': {
                    status.value: count for status, count in status_counts.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting alert statistics: {e}")
            raise RepositoryError(f"Failed to get alert statistics: {e}")
    
    async def search_alerts(self, search_term: str, skip: int = 0, 
                           limit: int = 100) -> List[Alert]:
        """Search alerts by title or description."""
        search_fields = ['title', 'description', 'alert_type']
        return await self.search(search_term, search_fields, skip, limit)
