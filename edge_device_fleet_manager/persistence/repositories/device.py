"""
Device Repository

Specialized repository for device management with advanced querying,
geospatial operations, and device-specific business logic.
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .base import BaseRepository, RepositoryError
from ..models.device import Device, DeviceStatus, DeviceType
from ..models.device_group import DeviceGroup


class DeviceRepository(BaseRepository[Device]):
    """
    Device repository with specialized device management operations.
    
    Provides device-specific queries, geospatial operations,
    health monitoring, and fleet management capabilities.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Device)
    
    async def get_by_ip_address(self, ip_address: str) -> Optional[Device]:
        """Get device by IP address."""
        try:
            query = select(self.model).where(self.model.ip_address == ip_address)
            query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting device by IP {ip_address}: {e}")
            raise RepositoryError(f"Failed to get device by IP: {e}")
    
    async def get_by_mac_address(self, mac_address: str) -> Optional[Device]:
        """Get device by MAC address."""
        try:
            query = select(self.model).where(self.model.mac_address == mac_address)
            query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting device by MAC {mac_address}: {e}")
            raise RepositoryError(f"Failed to get device by MAC: {e}")
    
    async def get_by_serial_number(self, serial_number: str) -> Optional[Device]:
        """Get device by serial number."""
        try:
            query = select(self.model).where(self.model.serial_number == serial_number)
            query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting device by serial {serial_number}: {e}")
            raise RepositoryError(f"Failed to get device by serial: {e}")
    
    async def get_by_status(self, status: DeviceStatus, 
                           skip: int = 0, limit: int = 100) -> List[Device]:
        """Get devices by status."""
        try:
            query = select(self.model).where(self.model.status == status)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(self.model.last_seen.desc())
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting devices by status {status}: {e}")
            raise RepositoryError(f"Failed to get devices by status: {e}")
    
    async def get_by_device_type(self, device_type: DeviceType,
                                skip: int = 0, limit: int = 100) -> List[Device]:
        """Get devices by type."""
        try:
            query = select(self.model).where(self.model.device_type == device_type)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting devices by type {device_type}: {e}")
            raise RepositoryError(f"Failed to get devices by type: {e}")
    
    async def get_by_group(self, group_id: uuid.UUID,
                          skip: int = 0, limit: int = 100) -> List[Device]:
        """Get devices in a specific group."""
        try:
            query = select(self.model).where(self.model.device_group_id == group_id)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting devices by group {group_id}: {e}")
            raise RepositoryError(f"Failed to get devices by group: {e}")
    
    async def get_online_devices(self, skip: int = 0, limit: int = 100) -> List[Device]:
        """Get all online devices."""
        return await self.get_by_status(DeviceStatus.ONLINE, skip, limit)
    
    async def get_offline_devices(self, skip: int = 0, limit: int = 100) -> List[Device]:
        """Get all offline devices."""
        return await self.get_by_status(DeviceStatus.OFFLINE, skip, limit)
    
    async def get_devices_by_location(self, latitude: float, longitude: float,
                                     radius_km: float, skip: int = 0, 
                                     limit: int = 100) -> List[Device]:
        """
        Get devices within a geographic radius.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius in kilometers
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List of devices within the radius
        """
        try:
            # Using Haversine formula for distance calculation
            # This is a simplified version - in production you'd use PostGIS
            query = select(self.model).where(
                and_(
                    self.model.latitude.isnot(None),
                    self.model.longitude.isnot(None),
                    self.model.is_deleted == False
                )
            )
            
            # Add distance calculation (simplified)
            # In production, use proper geospatial functions
            distance_formula = func.sqrt(
                func.pow(69.1 * (self.model.latitude - latitude), 2) +
                func.pow(69.1 * (longitude - self.model.longitude) * 
                        func.cos(self.model.latitude / 57.3), 2)
            )
            
            query = query.where(distance_formula <= radius_km)
            query = query.order_by(distance_formula)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting devices by location: {e}")
            raise RepositoryError(f"Failed to get devices by location: {e}")
    
    async def get_stale_devices(self, stale_threshold_minutes: int = 60) -> List[Device]:
        """
        Get devices that haven't been seen recently.
        
        Args:
            stale_threshold_minutes: Minutes since last seen to consider stale
            
        Returns:
            List of stale devices
        """
        try:
            threshold_time = datetime.now(timezone.utc) - timedelta(minutes=stale_threshold_minutes)
            
            query = select(self.model).where(
                and_(
                    self.model.last_seen < threshold_time,
                    self.model.status == DeviceStatus.ONLINE,
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.last_seen)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting stale devices: {e}")
            raise RepositoryError(f"Failed to get stale devices: {e}")
    
    async def get_unhealthy_devices(self, health_threshold: float = 0.7) -> List[Device]:
        """
        Get devices with low health scores.
        
        Args:
            health_threshold: Minimum health score threshold
            
        Returns:
            List of unhealthy devices
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.health_score < health_threshold,
                    self.model.health_score.isnot(None),
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.health_score)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting unhealthy devices: {e}")
            raise RepositoryError(f"Failed to get unhealthy devices: {e}")
    
    async def get_low_battery_devices(self, battery_threshold: float = 20.0) -> List[Device]:
        """
        Get devices with low battery levels.
        
        Args:
            battery_threshold: Minimum battery level threshold
            
        Returns:
            List of devices with low battery
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.battery_level < battery_threshold,
                    self.model.battery_level.isnot(None),
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.battery_level)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting low battery devices: {e}")
            raise RepositoryError(f"Failed to get low battery devices: {e}")
    
    async def search_devices(self, search_term: str, skip: int = 0, 
                           limit: int = 100) -> List[Device]:
        """
        Search devices by name, hostname, or location.
        
        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List of matching devices
        """
        search_fields = ['name', 'hostname', 'location', 'manufacturer', 'model']
        return await self.search(search_term, search_fields, skip, limit)
    
    async def get_device_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive device statistics.
        
        Returns:
            Dictionary with device statistics
        """
        try:
            # Total devices
            total_query = select(func.count(self.model.id)).where(self.model.is_deleted == False)
            total_result = await self.session.execute(total_query)
            total_devices = total_result.scalar()
            
            # Devices by status
            status_query = (
                select(self.model.status, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.status)
            )
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.all())
            
            # Devices by type
            type_query = (
                select(self.model.device_type, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.device_type)
            )
            type_result = await self.session.execute(type_query)
            type_counts = dict(type_result.all())
            
            # Health statistics
            health_query = select(
                func.avg(self.model.health_score),
                func.min(self.model.health_score),
                func.max(self.model.health_score)
            ).where(
                and_(
                    self.model.health_score.isnot(None),
                    self.model.is_deleted == False
                )
            )
            health_result = await self.session.execute(health_query)
            avg_health, min_health, max_health = health_result.first()
            
            return {
                'total_devices': total_devices,
                'status_distribution': {
                    status.value: count for status, count in status_counts.items()
                },
                'type_distribution': {
                    device_type.value: count for device_type, count in type_counts.items()
                },
                'health_statistics': {
                    'average_health': float(avg_health) if avg_health else None,
                    'min_health': float(min_health) if min_health else None,
                    'max_health': float(max_health) if max_health else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting device statistics: {e}")
            raise RepositoryError(f"Failed to get device statistics: {e}")
    
    async def update_last_seen(self, device_id: uuid.UUID, 
                              timestamp: Optional[datetime] = None) -> bool:
        """
        Update device last seen timestamp.
        
        Args:
            device_id: Device ID
            timestamp: Timestamp (current time if None)
            
        Returns:
            True if updated successfully
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            device = await self.get(device_id)
            if device:
                device.update_last_seen()
                await self.session.flush()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating last seen for device {device_id}: {e}")
            return False
    
    async def update_heartbeat(self, device_id: uuid.UUID,
                              timestamp: Optional[datetime] = None) -> bool:
        """
        Update device heartbeat timestamp.
        
        Args:
            device_id: Device ID
            timestamp: Timestamp (current time if None)
            
        Returns:
            True if updated successfully
        """
        try:
            device = await self.get(device_id)
            if device:
                device.update_heartbeat()
                await self.session.flush()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating heartbeat for device {device_id}: {e}")
            return False
    
    async def mark_devices_offline(self, device_ids: List[uuid.UUID]) -> int:
        """
        Mark multiple devices as offline.
        
        Args:
            device_ids: List of device IDs
            
        Returns:
            Number of devices updated
        """
        try:
            updates = [
                {
                    'id': device_id,
                    'status': DeviceStatus.OFFLINE,
                    'updated_at': datetime.now(timezone.utc)
                }
                for device_id in device_ids
            ]
            
            return await self.bulk_update(updates)
            
        except Exception as e:
            self.logger.error(f"Error marking devices offline: {e}")
            raise RepositoryError(f"Failed to mark devices offline: {e}")
    
    async def get_devices_with_telemetry(self, skip: int = 0, 
                                       limit: int = 100) -> List[Device]:
        """Get devices with their recent telemetry data loaded."""
        try:
            query = select(self.model).where(self.model.is_deleted == False)
            query = query.options(selectinload(self.model.telemetry_events))
            query = query.order_by(self.model.name)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting devices with telemetry: {e}")
            raise RepositoryError(f"Failed to get devices with telemetry: {e}")
