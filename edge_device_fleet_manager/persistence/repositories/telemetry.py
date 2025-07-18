"""
Telemetry Repository

Specialized repository for telemetry data management with time-series
operations, aggregation, and high-performance data access patterns.
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.telemetry import TelemetryEvent, TelemetryType


class TelemetryRepository(BaseRepository[TelemetryEvent]):
    """
    Telemetry repository with time-series data management capabilities.
    
    Provides specialized operations for telemetry data including
    time-based queries, aggregations, and performance optimizations.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TelemetryEvent)
    
    async def get_by_device(self, device_id: uuid.UUID, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           event_types: Optional[List[TelemetryType]] = None,
                           skip: int = 0, limit: int = 100) -> List[TelemetryEvent]:
        """Get telemetry events for a specific device."""
        try:
            query = select(self.model).where(self.model.device_id == device_id)
            
            # Apply time filters
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            # Apply event type filter
            if event_types:
                query = query.where(self.model.event_type.in_(event_types))
            
            # Order by timestamp descending
            query = query.order_by(desc(self.model.timestamp))
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting telemetry for device {device_id}: {e}")
            raise RepositoryError(f"Failed to get telemetry for device: {e}")
    
    async def get_latest_by_device(self, device_id: uuid.UUID,
                                  event_name: Optional[str] = None) -> Optional[TelemetryEvent]:
        """Get the latest telemetry event for a device."""
        try:
            query = select(self.model).where(self.model.device_id == device_id)
            
            if event_name:
                query = query.where(self.model.event_name == event_name)
            
            query = query.order_by(desc(self.model.timestamp)).limit(1)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting latest telemetry for device {device_id}: {e}")
            raise RepositoryError(f"Failed to get latest telemetry: {e}")
    
    async def get_aggregated_data(self, device_id: uuid.UUID,
                                 event_name: str,
                                 start_time: datetime,
                                 end_time: datetime,
                                 aggregation: str = "avg") -> Optional[float]:
        """Get aggregated telemetry data for a device and event."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.device_id == device_id,
                    self.model.event_name == event_name,
                    self.model.timestamp >= start_time,
                    self.model.timestamp <= end_time,
                    self.model.numeric_value.isnot(None)
                )
            )
            
            if aggregation == "avg":
                agg_query = select(func.avg(self.model.numeric_value)).select_from(query.subquery())
            elif aggregation == "sum":
                agg_query = select(func.sum(self.model.numeric_value)).select_from(query.subquery())
            elif aggregation == "min":
                agg_query = select(func.min(self.model.numeric_value)).select_from(query.subquery())
            elif aggregation == "max":
                agg_query = select(func.max(self.model.numeric_value)).select_from(query.subquery())
            elif aggregation == "count":
                agg_query = select(func.count(self.model.numeric_value)).select_from(query.subquery())
            else:
                raise ValueError(f"Unsupported aggregation: {aggregation}")
            
            result = await self.session.execute(agg_query)
            return result.scalar()
            
        except Exception as e:
            self.logger.error(f"Error getting aggregated telemetry data: {e}")
            raise RepositoryError(f"Failed to get aggregated data: {e}")
    
    async def get_time_series_data(self, device_id: uuid.UUID,
                                  event_name: str,
                                  start_time: datetime,
                                  end_time: datetime,
                                  interval_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get time-series data with specified interval."""
        try:
            # This is a simplified implementation
            # In production, you'd use database-specific time bucketing functions
            query = select(self.model).where(
                and_(
                    self.model.device_id == device_id,
                    self.model.event_name == event_name,
                    self.model.timestamp >= start_time,
                    self.model.timestamp <= end_time,
                    self.model.numeric_value.isnot(None)
                )
            ).order_by(self.model.timestamp)
            
            result = await self.session.execute(query)
            events = result.scalars().all()
            
            # Group by time intervals
            time_series = []
            current_bucket = None
            bucket_values = []
            
            for event in events:
                # Calculate bucket timestamp
                bucket_timestamp = event.timestamp.replace(
                    minute=(event.timestamp.minute // interval_minutes) * interval_minutes,
                    second=0,
                    microsecond=0
                )
                
                if current_bucket != bucket_timestamp:
                    # Save previous bucket
                    if current_bucket and bucket_values:
                        time_series.append({
                            'timestamp': current_bucket,
                            'value': sum(bucket_values) / len(bucket_values),
                            'count': len(bucket_values),
                            'min': min(bucket_values),
                            'max': max(bucket_values)
                        })
                    
                    # Start new bucket
                    current_bucket = bucket_timestamp
                    bucket_values = []
                
                bucket_values.append(event.numeric_value)
            
            # Save last bucket
            if current_bucket and bucket_values:
                time_series.append({
                    'timestamp': current_bucket,
                    'value': sum(bucket_values) / len(bucket_values),
                    'count': len(bucket_values),
                    'min': min(bucket_values),
                    'max': max(bucket_values)
                })
            
            return time_series
            
        except Exception as e:
            self.logger.error(f"Error getting time series data: {e}")
            raise RepositoryError(f"Failed to get time series data: {e}")
    
    async def cleanup_old_data(self, retention_days: int = 30) -> int:
        """Clean up old telemetry data."""
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
            
            self.logger.info(f"Cleaned up {count} old telemetry records")
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old telemetry data: {e}")
            raise RepositoryError(f"Failed to cleanup old data: {e}")
    
    async def get_device_statistics(self, device_id: uuid.UUID,
                                   start_time: Optional[datetime] = None,
                                   end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get telemetry statistics for a device."""
        try:
            query = select(self.model).where(self.model.device_id == device_id)
            
            if start_time:
                query = query.where(self.model.timestamp >= start_time)
            if end_time:
                query = query.where(self.model.timestamp <= end_time)
            
            # Total events
            total_query = select(func.count(self.model.id)).select_from(query.subquery())
            total_result = await self.session.execute(total_query)
            total_events = total_result.scalar()
            
            # Events by type
            type_query = (
                select(self.model.event_type, func.count(self.model.id))
                .select_from(query.subquery())
                .group_by(self.model.event_type)
            )
            type_result = await self.session.execute(type_query)
            type_distribution = dict(type_result.all())
            
            # Latest event
            latest_query = query.order_by(desc(self.model.timestamp)).limit(1)
            latest_result = await self.session.execute(latest_query)
            latest_event = latest_result.scalar_one_or_none()
            
            return {
                'total_events': total_events,
                'type_distribution': {
                    event_type.value: count for event_type, count in type_distribution.items()
                },
                'latest_event_time': latest_event.timestamp if latest_event else None,
                'device_id': str(device_id)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting telemetry statistics: {e}")
            raise RepositoryError(f"Failed to get telemetry statistics: {e}")
