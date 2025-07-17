"""
Analytics Repository

Specialized repository for analytics data management with aggregation,
reporting, and business intelligence capabilities.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.analytics import Analytics, AnalyticsType, AnalyticsMetric


class AnalyticsRepository(BaseRepository[Analytics]):
    """
    Analytics repository with business intelligence and reporting capabilities.
    
    Provides specialized operations for analytics data including
    aggregations, trend analysis, and reporting functions.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Analytics)
    
    async def get_by_metric(self, metric_name: str,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           scope: Optional[str] = None,
                           skip: int = 0, limit: int = 100) -> List[Analytics]:
        """Get analytics by metric name."""
        try:
            query = select(self.model).where(self.model.metric_name == metric_name)
            
            if start_time:
                query = query.where(self.model.period_start >= start_time)
            if end_time:
                query = query.where(self.model.period_end <= end_time)
            if scope:
                query = query.where(self.model.scope == scope)
            
            query = query.order_by(desc(self.model.period_start))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting analytics by metric {metric_name}: {e}")
            raise RepositoryError(f"Failed to get analytics by metric: {e}")
    
    async def get_latest_metrics(self, analytics_type: AnalyticsType,
                                scope: Optional[str] = None) -> List[Analytics]:
        """Get latest analytics metrics by type."""
        try:
            query = select(self.model).where(self.model.analytics_type == analytics_type)
            
            if scope:
                query = query.where(self.model.scope == scope)
            
            # Get latest for each metric
            subquery = (
                select(
                    self.model.metric_name,
                    func.max(self.model.period_end).label('latest_period')
                )
                .where(self.model.analytics_type == analytics_type)
                .group_by(self.model.metric_name)
            ).subquery()
            
            query = query.join(
                subquery,
                and_(
                    self.model.metric_name == subquery.c.metric_name,
                    self.model.period_end == subquery.c.latest_period
                )
            )
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting latest metrics: {e}")
            raise RepositoryError(f"Failed to get latest metrics: {e}")
    
    async def get_trend_data(self, metric_name: str,
                            days: int = 30,
                            scope: Optional[str] = None) -> List[Analytics]:
        """Get trend data for a metric over specified days."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            return await self.get_by_metric(
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time,
                scope=scope,
                limit=1000  # Get more data for trend analysis
            )
            
        except Exception as e:
            self.logger.error(f"Error getting trend data: {e}")
            raise RepositoryError(f"Failed to get trend data: {e}")
    
    async def get_summary_statistics(self, analytics_type: AnalyticsType,
                                   start_time: Optional[datetime] = None,
                                   end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary statistics for analytics type."""
        try:
            query = select(self.model).where(self.model.analytics_type == analytics_type)
            
            if start_time:
                query = query.where(self.model.period_start >= start_time)
            if end_time:
                query = query.where(self.model.period_end <= end_time)
            
            # Count by metric type
            metric_type_query = (
                select(self.model.metric_type, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.metric_type)
            )
            metric_type_result = await self.session.execute(metric_type_query)
            metric_type_counts = dict(metric_type_result.all())
            
            # Count by scope
            scope_query = (
                select(self.model.scope, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.scope)
            )
            scope_result = await self.session.execute(scope_query)
            scope_counts = dict(scope_result.all())
            
            # Total count
            total_query = select(func.count(self.model.id)).select_from(query.subquery())
            total_result = await self.session.execute(total_query)
            total_count = total_result.scalar()
            
            return {
                'total_analytics': total_count,
                'metric_type_distribution': {
                    metric_type.value: count for metric_type, count in metric_type_counts.items()
                },
                'scope_distribution': scope_counts,
                'analytics_type': analytics_type.value
            }
            
        except Exception as e:
            self.logger.error(f"Error getting summary statistics: {e}")
            raise RepositoryError(f"Failed to get summary statistics: {e}")
    
    async def cleanup_old_analytics(self, retention_days: int = 90) -> int:
        """Clean up old analytics data."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Count records to be deleted
            count_query = select(func.count(self.model.id)).where(
                self.model.period_end < cutoff_date
            )
            count_result = await self.session.execute(count_query)
            count = count_result.scalar()
            
            # Delete old records
            from sqlalchemy import delete
            delete_query = delete(self.model).where(self.model.period_end < cutoff_date)
            await self.session.execute(delete_query)
            await self.session.flush()
            
            self.logger.info(f"Cleaned up {count} old analytics records")
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old analytics: {e}")
            raise RepositoryError(f"Failed to cleanup old analytics: {e}")
