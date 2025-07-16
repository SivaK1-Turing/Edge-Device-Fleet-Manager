"""
Repository implementations for device management.

Repositories provide an abstraction layer over data persistence,
implementing the Repository pattern for domain aggregates.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Numeric, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from ..domain.entities import DeviceAggregate, DeviceEntity, DeviceGroup, DeviceType, DeviceStatus
from ..domain.value_objects import DeviceId, DeviceIdentifier, DeviceLocation, DeviceCapabilities
from .event_store import EventStore
from ...core.exceptions import RepositoryError


Base = declarative_base()


class DeviceModel(Base):
    """SQLAlchemy model for device persistence."""
    
    __tablename__ = 'devices'
    
    device_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default='active')
    
    # Identifier fields
    serial_number = Column(String(100), nullable=False, unique=True)
    mac_address = Column(String(17), nullable=True)
    hardware_id = Column(String(100), nullable=True)
    
    # Basic info
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    
    # Location fields
    latitude = Column(Numeric(precision=10, scale=8), nullable=True)
    longitude = Column(Numeric(precision=11, scale=8), nullable=True)
    altitude = Column(Numeric(precision=8, scale=2), nullable=True)
    address = Column(String(500), nullable=True)
    building = Column(String(100), nullable=True)
    floor = Column(String(20), nullable=True)
    room = Column(String(50), nullable=True)
    
    # Capabilities (stored as JSON)
    capabilities = Column(JSON, nullable=True)
    
    # Configuration (stored as JSON)
    configuration = Column(JSON, nullable=True, default=dict)
    configuration_version = Column(Integer, nullable=False, default=1)
    
    # Timestamps
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    
    def __repr__(self):
        return f"<DeviceModel(device_id={self.device_id}, name={self.name}, type={self.device_type})>"


class DeviceGroupModel(Base):
    """SQLAlchemy model for device group persistence."""
    
    __tablename__ = 'device_groups'
    
    group_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    parent_group_id = Column(PostgresUUID(as_uuid=True), nullable=True)
    device_ids = Column(JSON, nullable=False, default=list)
    group_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    
    def __repr__(self):
        return f"<DeviceGroupModel(group_id={self.group_id}, name={self.name})>"


class DeviceRepository(ABC):
    """Abstract repository for device aggregates."""
    
    @abstractmethod
    async def save(self, aggregate: DeviceAggregate) -> None:
        """Save a device aggregate."""
        pass
    
    @abstractmethod
    async def get_by_id(self, device_id: DeviceId) -> Optional[DeviceAggregate]:
        """Get device aggregate by ID."""
        pass
    
    @abstractmethod
    async def get_by_serial_number(self, serial_number: str) -> Optional[DeviceAggregate]:
        """Get device aggregate by serial number."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[DeviceAggregate]:
        """Get all device aggregates."""
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[DeviceAggregate]:
        """Find devices by criteria."""
        pass
    
    @abstractmethod
    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device aggregate."""
        pass


class DeviceGroupRepository(ABC):
    """Abstract repository for device groups."""
    
    @abstractmethod
    async def save(self, group: DeviceGroup) -> None:
        """Save a device group."""
        pass
    
    @abstractmethod
    async def get_by_id(self, group_id: DeviceId) -> Optional[DeviceGroup]:
        """Get device group by ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[DeviceGroup]:
        """Get all device groups."""
        pass
    
    @abstractmethod
    async def delete(self, group_id: DeviceId) -> bool:
        """Delete a device group."""
        pass


class InMemoryDeviceRepository(DeviceRepository):
    """In-memory device repository implementation for testing."""
    
    def __init__(self):
        self._devices: Dict[str, DeviceAggregate] = {}
    
    async def save(self, aggregate: DeviceAggregate) -> None:
        """Save a device aggregate."""
        self._devices[str(aggregate.device_id)] = aggregate
    
    async def get_by_id(self, device_id: DeviceId) -> Optional[DeviceAggregate]:
        """Get device aggregate by ID."""
        return self._devices.get(str(device_id))
    
    async def get_by_serial_number(self, serial_number: str) -> Optional[DeviceAggregate]:
        """Get device aggregate by serial number."""
        for aggregate in self._devices.values():
            if aggregate.device.identifier.serial_number == serial_number:
                return aggregate
        return None
    
    async def get_all(self) -> List[DeviceAggregate]:
        """Get all device aggregates."""
        return list(self._devices.values())
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[DeviceAggregate]:
        """Find devices by criteria."""
        results = []
        
        for aggregate in self._devices.values():
            device = aggregate.device
            matches = True
            
            # Check each criterion
            for key, value in criteria.items():
                if key == 'device_type' and device.device_type.value != value:
                    matches = False
                    break
                elif key == 'status' and device.status.value != value:
                    matches = False
                    break
                elif key == 'manufacturer' and device.manufacturer != value:
                    matches = False
                    break
                elif key == 'model' and device.model != value:
                    matches = False
                    break
            
            if matches:
                results.append(aggregate)
        
        return results
    
    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device aggregate."""
        key = str(device_id)
        if key in self._devices:
            del self._devices[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all devices (for testing)."""
        self._devices.clear()


class SqlDeviceRepository(DeviceRepository):
    """SQL-based device repository implementation."""
    
    def __init__(self, session_factory: sessionmaker, event_store: EventStore):
        self.session_factory = session_factory
        self.event_store = event_store
    
    async def save(self, aggregate: DeviceAggregate) -> None:
        """Save a device aggregate."""
        session: Session = self.session_factory()
        
        try:
            device = aggregate.device
            
            # Check if device exists
            existing = session.query(DeviceModel).filter(
                DeviceModel.device_id == device.device_id.value
            ).first()
            
            if existing:
                # Update existing device
                self._update_device_model(existing, device)
            else:
                # Create new device
                device_model = self._create_device_model(device)
                session.add(device_model)
            
            # Save events to event store
            events = aggregate.get_uncommitted_events()
            if events:
                await self.event_store.save_events(
                    aggregate.device_id,
                    events,
                    device.version - len(events)
                )
                aggregate.mark_events_as_committed()
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to save device: {e}") from e
        finally:
            session.close()
    
    async def get_by_id(self, device_id: DeviceId) -> Optional[DeviceAggregate]:
        """Get device aggregate by ID."""
        session: Session = self.session_factory()
        
        try:
            device_model = session.query(DeviceModel).filter(
                DeviceModel.device_id == device_id.value
            ).first()
            
            if not device_model:
                return None
            
            return self._create_aggregate_from_model(device_model)
            
        except Exception as e:
            raise RepositoryError(f"Failed to get device: {e}") from e
        finally:
            session.close()
    
    async def get_by_serial_number(self, serial_number: str) -> Optional[DeviceAggregate]:
        """Get device aggregate by serial number."""
        session: Session = self.session_factory()
        
        try:
            device_model = session.query(DeviceModel).filter(
                DeviceModel.serial_number == serial_number
            ).first()
            
            if not device_model:
                return None
            
            return self._create_aggregate_from_model(device_model)
            
        except Exception as e:
            raise RepositoryError(f"Failed to get device by serial number: {e}") from e
        finally:
            session.close()
    
    async def get_all(self) -> List[DeviceAggregate]:
        """Get all device aggregates."""
        session: Session = self.session_factory()
        
        try:
            device_models = session.query(DeviceModel).all()
            return [self._create_aggregate_from_model(model) for model in device_models]
            
        except Exception as e:
            raise RepositoryError(f"Failed to get all devices: {e}") from e
        finally:
            session.close()
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[DeviceAggregate]:
        """Find devices by criteria."""
        session: Session = self.session_factory()
        
        try:
            query = session.query(DeviceModel)
            
            # Apply filters based on criteria
            for key, value in criteria.items():
                if key == 'device_type':
                    query = query.filter(DeviceModel.device_type == value)
                elif key == 'status':
                    query = query.filter(DeviceModel.status == value)
                elif key == 'manufacturer':
                    query = query.filter(DeviceModel.manufacturer == value)
                elif key == 'model':
                    query = query.filter(DeviceModel.model == value)
            
            device_models = query.all()
            return [self._create_aggregate_from_model(model) for model in device_models]
            
        except Exception as e:
            raise RepositoryError(f"Failed to find devices by criteria: {e}") from e
        finally:
            session.close()
    
    async def delete(self, device_id: DeviceId) -> bool:
        """Delete a device aggregate."""
        session: Session = self.session_factory()
        
        try:
            result = session.query(DeviceModel).filter(
                DeviceModel.device_id == device_id.value
            ).delete()
            
            session.commit()
            return result > 0
            
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to delete device: {e}") from e
        finally:
            session.close()
    
    def _create_device_model(self, device: DeviceEntity) -> DeviceModel:
        """Create DeviceModel from DeviceEntity."""
        capabilities_data = None
        if device.capabilities:
            capabilities_data = {
                'supported_protocols': device.capabilities.supported_protocols,
                'sensors': device.capabilities.sensors,
                'actuators': device.capabilities.actuators,
                'connectivity': device.capabilities.connectivity,
                'power_source': device.capabilities.power_source,
                'operating_system': device.capabilities.operating_system,
                'firmware_version': device.capabilities.firmware_version,
                'hardware_version': device.capabilities.hardware_version,
                'memory_mb': device.capabilities.memory_mb,
                'storage_mb': device.capabilities.storage_mb,
                'cpu_cores': device.capabilities.cpu_cores,
            }
        
        return DeviceModel(
            device_id=device.device_id.value,
            name=device.name,
            device_type=device.device_type.value,
            status=device.status.value,
            serial_number=device.identifier.serial_number,
            mac_address=device.identifier.mac_address,
            hardware_id=device.identifier.hardware_id,
            manufacturer=device.manufacturer,
            model=device.model,
            latitude=device.location.latitude if device.location else None,
            longitude=device.location.longitude if device.location else None,
            altitude=device.location.altitude if device.location else None,
            address=device.location.address if device.location else None,
            building=device.location.building if device.location else None,
            floor=device.location.floor if device.location else None,
            room=device.location.room if device.location else None,
            capabilities=capabilities_data,
            configuration=device.configuration.configuration if device.configuration else {},
            configuration_version=device.configuration.version if device.configuration else 1,
            last_seen=device.last_seen,
            created_at=device.created_at,
            updated_at=device.updated_at,
            version=device.version,
        )

    def _update_device_model(self, model: DeviceModel, device: DeviceEntity) -> None:
        """Update DeviceModel from DeviceEntity."""
        model.name = device.name
        model.device_type = device.device_type.value
        model.status = device.status.value
        model.serial_number = device.identifier.serial_number
        model.mac_address = device.identifier.mac_address
        model.hardware_id = device.identifier.hardware_id
        model.manufacturer = device.manufacturer
        model.model = device.model

        if device.location:
            model.latitude = device.location.latitude
            model.longitude = device.location.longitude
            model.altitude = device.location.altitude
            model.address = device.location.address
            model.building = device.location.building
            model.floor = device.location.floor
            model.room = device.location.room

        if device.capabilities:
            model.capabilities = {
                'supported_protocols': device.capabilities.supported_protocols,
                'sensors': device.capabilities.sensors,
                'actuators': device.capabilities.actuators,
                'connectivity': device.capabilities.connectivity,
                'power_source': device.capabilities.power_source,
                'operating_system': device.capabilities.operating_system,
                'firmware_version': device.capabilities.firmware_version,
                'hardware_version': device.capabilities.hardware_version,
                'memory_mb': device.capabilities.memory_mb,
                'storage_mb': device.capabilities.storage_mb,
                'cpu_cores': device.capabilities.cpu_cores,
            }

        if device.configuration:
            model.configuration = device.configuration.configuration
            model.configuration_version = device.configuration.version

        model.last_seen = device.last_seen
        model.updated_at = device.updated_at
        model.version = device.version

    def _create_aggregate_from_model(self, model: DeviceModel) -> DeviceAggregate:
        """Create DeviceAggregate from DeviceModel."""
        from decimal import Decimal

        # Create identifier
        identifier = DeviceIdentifier(
            serial_number=model.serial_number,
            mac_address=model.mac_address,
            hardware_id=model.hardware_id,
        )

        # Create location if data exists
        location = None
        if any([model.latitude, model.longitude, model.address, model.building]):
            location = DeviceLocation(
                latitude=Decimal(str(model.latitude)) if model.latitude else None,
                longitude=Decimal(str(model.longitude)) if model.longitude else None,
                altitude=Decimal(str(model.altitude)) if model.altitude else None,
                address=model.address,
                building=model.building,
                floor=model.floor,
                room=model.room,
            )

        # Create capabilities if data exists
        capabilities = None
        if model.capabilities:
            capabilities = DeviceCapabilities(
                supported_protocols=model.capabilities.get('supported_protocols', []),
                sensors=model.capabilities.get('sensors', []),
                actuators=model.capabilities.get('actuators', []),
                connectivity=model.capabilities.get('connectivity', []),
                power_source=model.capabilities.get('power_source'),
                operating_system=model.capabilities.get('operating_system'),
                firmware_version=model.capabilities.get('firmware_version'),
                hardware_version=model.capabilities.get('hardware_version'),
                memory_mb=model.capabilities.get('memory_mb'),
                storage_mb=model.capabilities.get('storage_mb'),
                cpu_cores=model.capabilities.get('cpu_cores'),
            )

        # Create device entity
        device = DeviceEntity(
            device_id=DeviceId(model.device_id),
            name=model.name,
            device_type=DeviceType(model.device_type),
            identifier=identifier,
            status=DeviceStatus(model.status),
            manufacturer=model.manufacturer,
            model=model.model,
            location=location,
            capabilities=capabilities,
            last_seen=model.last_seen,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

        # Set configuration if exists
        if model.configuration:
            from ..domain.entities import DeviceConfiguration
            device.configuration = DeviceConfiguration(
                device_id=device.device_id,
                configuration=model.configuration,
                version=model.configuration_version,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

        return DeviceAggregate(device)
