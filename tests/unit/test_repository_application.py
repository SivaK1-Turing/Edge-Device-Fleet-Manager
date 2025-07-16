"""
Unit tests for repository application layer.

Tests commands, queries, handlers, DTOs, and application services.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from edge_device_fleet_manager.repository.application.commands import (
    RegisterDeviceCommand, UpdateDeviceCommand, DeactivateDeviceCommand,
    CommandValidator, CommandResult
)
from edge_device_fleet_manager.repository.application.queries import (
    GetDeviceQuery, ListDevicesQuery, SearchDevicesQuery,
    QueryValidator, QueryResult
)
from edge_device_fleet_manager.repository.application.handlers import (
    DeviceCommandHandler, DeviceQueryHandler
)
from edge_device_fleet_manager.repository.application.services import (
    DeviceApplicationService
)
from edge_device_fleet_manager.repository.application.dto import (
    DeviceDto, DeviceIdentifierDto, DtoConverter
)
from edge_device_fleet_manager.repository.domain.entities import DeviceType, DeviceStatus
from edge_device_fleet_manager.repository.domain.value_objects import (
    DeviceId, DeviceIdentifier, DeviceCapabilities, DeviceMetrics
)
from edge_device_fleet_manager.repository.infrastructure.unit_of_work import (
    InMemoryUnitOfWork
)


class TestCommands:
    """Test command objects."""
    
    def test_register_device_command(self):
        """Test register device command."""
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier,
            manufacturer="Test Corp",
            user_id="user123"
        )
        
        assert command.command_type == "register_device"
        assert command.name == "Test Device"
        assert command.device_type == DeviceType.SENSOR
        assert command.identifier.serial_number == "SN123456"
        assert command.manufacturer == "Test Corp"
        assert command.user_id == "user123"
    
    def test_update_device_command(self):
        """Test update device command."""
        device_id = DeviceId.generate()
        
        command = UpdateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            name="Updated Device",
            manufacturer="New Corp"
        )
        
        assert command.command_type == "update_device"
        assert command.device_id == device_id
        assert command.name == "Updated Device"
        assert command.manufacturer == "New Corp"
    
    def test_deactivate_device_command(self):
        """Test deactivate device command."""
        device_id = DeviceId.generate()
        
        command = DeactivateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            reason="Maintenance required"
        )
        
        assert command.command_type == "deactivate_device"
        assert command.device_id == device_id
        assert command.reason == "Maintenance required"


class TestCommandValidation:
    """Test command validation."""
    
    def test_validate_register_device_command(self):
        """Test register device command validation."""
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        # Valid command
        valid_command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        errors = CommandValidator.validate_register_device_command(valid_command)
        assert len(errors) == 0
        
        # Invalid command - empty name
        invalid_command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        errors = CommandValidator.validate_register_device_command(invalid_command)
        assert len(errors) > 0
        assert any("name is required" in error for error in errors)
    
    def test_validate_update_device_command(self):
        """Test update device command validation."""
        device_id = DeviceId.generate()
        
        # Valid command
        valid_command = UpdateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            name="Valid Name"
        )
        
        errors = CommandValidator.validate_update_device_command(valid_command)
        assert len(errors) == 0
        
        # Invalid command - empty name
        invalid_command = UpdateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            name=""
        )
        
        errors = CommandValidator.validate_update_device_command(invalid_command)
        assert len(errors) > 0
        assert any("cannot be empty" in error for error in errors)


class TestQueries:
    """Test query objects."""
    
    def test_get_device_query(self):
        """Test get device query."""
        device_id = DeviceId.generate()
        
        query = GetDeviceQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            include_metrics=True,
            include_configuration=True
        )
        
        assert query.query_type == "get_device"
        assert query.device_id == device_id
        assert query.include_metrics is True
        assert query.include_configuration is True
    
    def test_list_devices_query(self):
        """Test list devices query."""
        query = ListDevicesQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            page=2,
            page_size=25,
            sort_by="name",
            sort_order="desc"
        )
        
        assert query.query_type == "list_devices"
        assert query.page == 2
        assert query.page_size == 25
        assert query.sort_by == "name"
        assert query.sort_order == "desc"
    
    def test_search_devices_query(self):
        """Test search devices query."""
        query = SearchDevicesQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            search_term="sensor",
            device_types=[DeviceType.SENSOR],
            statuses=[DeviceStatus.ACTIVE],
            manufacturers=["Test Corp"]
        )
        
        assert query.query_type == "search_devices"
        assert query.search_term == "sensor"
        assert query.device_types == [DeviceType.SENSOR]
        assert query.statuses == [DeviceStatus.ACTIVE]
        assert query.manufacturers == ["Test Corp"]


class TestQueryValidation:
    """Test query validation."""
    
    def test_validate_pagination(self):
        """Test pagination validation."""
        # Valid pagination
        errors = QueryValidator.validate_pagination(1, 50)
        assert len(errors) == 0
        
        # Invalid page number
        errors = QueryValidator.validate_pagination(0, 50)
        assert len(errors) > 0
        assert any("Page number must be at least 1" in error for error in errors)
        
        # Invalid page size
        errors = QueryValidator.validate_pagination(1, 0)
        assert len(errors) > 0
        assert any("Page size must be at least 1" in error for error in errors)
        
        # Page size too large
        errors = QueryValidator.validate_pagination(1, 2000)
        assert len(errors) > 0
        assert any("cannot exceed 1000" in error for error in errors)
    
    def test_validate_sort_parameters(self):
        """Test sort parameter validation."""
        # Valid sort parameters
        errors = QueryValidator.validate_sort_parameters("name", "asc")
        assert len(errors) == 0
        
        # Invalid sort field
        errors = QueryValidator.validate_sort_parameters("invalid_field", "asc")
        assert len(errors) > 0
        assert any("Invalid sort field" in error for error in errors)
        
        # Invalid sort order
        errors = QueryValidator.validate_sort_parameters("name", "invalid")
        assert len(errors) > 0
        assert any("Sort order must be" in error for error in errors)


class TestCommandResults:
    """Test command result objects."""
    
    def test_success_result(self):
        """Test successful command result."""
        command_id = uuid4()
        device_id = DeviceId.generate()
        
        result = CommandResult.success_result(command_id, device_id)
        
        assert result.success is True
        assert result.command_id == command_id
        assert result.aggregate_id == device_id
        assert result.error_message is None
        assert result.validation_errors is None
    
    def test_failure_result(self):
        """Test failed command result."""
        command_id = uuid4()
        error_message = "Something went wrong"
        
        result = CommandResult.failure_result(command_id, error_message)
        
        assert result.success is False
        assert result.command_id == command_id
        assert result.error_message == error_message
        assert result.aggregate_id is None
    
    def test_validation_failure_result(self):
        """Test validation failure result."""
        command_id = uuid4()
        validation_errors = ["Name is required", "Serial number invalid"]
        
        result = CommandResult.validation_failure_result(command_id, validation_errors)
        
        assert result.success is False
        assert result.command_id == command_id
        assert result.error_message == "Command validation failed"
        assert result.validation_errors == validation_errors


class TestDTOs:
    """Test Data Transfer Objects."""
    
    def test_device_identifier_dto(self):
        """Test device identifier DTO."""
        dto = DeviceIdentifierDto(
            serial_number="SN123456",
            mac_address="00:11:22:33:44:55",
            hardware_id="HW789"
        )
        
        assert dto.serial_number == "SN123456"
        assert dto.mac_address == "00:11:22:33:44:55"
        assert dto.hardware_id == "HW789"
    
    def test_device_dto_from_aggregate(self):
        """Test device DTO creation from aggregate."""
        # Create aggregate
        from edge_device_fleet_manager.repository.domain.entities import DeviceAggregate
        
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier,
            manufacturer="Test Corp"
        )
        
        # Convert to DTO
        dto = DeviceDto.from_aggregate(aggregate)
        
        assert dto.device_id == device_id.value
        assert dto.name == "Test Device"
        assert dto.device_type == DeviceType.SENSOR
        assert dto.status == DeviceStatus.ACTIVE
        assert dto.identifier.serial_number == "SN123456"
        assert dto.manufacturer == "Test Corp"
        assert dto.health_score is not None
        assert dto.is_online is not None
    
    def test_dto_converter(self):
        """Test DTO converter utility."""
        # Create aggregate
        from edge_device_fleet_manager.repository.domain.entities import DeviceAggregate
        
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        # Convert using utility
        dto = DtoConverter.device_aggregate_to_dto(aggregate)
        
        assert dto.device_id == device_id.value
        assert dto.name == "Test Device"
        
        # Test list conversion
        aggregates = [aggregate]
        list_dto = DtoConverter.device_aggregates_to_list_dto(
            aggregates, page=1, page_size=10, total_count=1
        )
        
        assert len(list_dto.devices) == 1
        assert list_dto.page == 1
        assert list_dto.total_count == 1
        assert list_dto.has_next is False
        assert list_dto.has_previous is False


class TestCommandHandler:
    """Test command handler."""
    
    @pytest.fixture
    def unit_of_work_factory(self):
        """Create unit of work factory."""
        class MockUnitOfWorkFactory:
            def __init__(self):
                self.uow = InMemoryUnitOfWork()

            def get_unit_of_work(self):
                return self.uow

        return MockUnitOfWorkFactory()
    
    @pytest.fixture
    def command_handler(self, unit_of_work_factory):
        """Create command handler."""
        return DeviceCommandHandler(unit_of_work_factory)
    
    async def test_handle_register_device_command(self, command_handler):
        """Test handling register device command."""
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        result = await command_handler.handle(command)
        
        assert result.success is True
        assert result.aggregate_id is not None
    
    async def test_handle_invalid_register_command(self, command_handler):
        """Test handling invalid register command."""
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="",  # Invalid empty name
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        result = await command_handler.handle(command)
        
        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
    
    async def test_handle_update_device_command(self, command_handler):
        """Test handling update device command."""
        # First register a device
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        register_command = RegisterDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        register_result = await command_handler.handle(register_command)
        assert register_result.success is True
        
        # Then update it
        update_command = UpdateDeviceCommand(
            command_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=register_result.aggregate_id,
            name="Updated Device"
        )
        
        update_result = await command_handler.handle(update_command)
        
        assert update_result.success is True
        assert update_result.aggregate_id == register_result.aggregate_id


class TestQueryHandler:
    """Test query handler."""
    
    @pytest.fixture
    def unit_of_work_factory(self):
        """Create unit of work factory."""
        class MockUnitOfWorkFactory:
            def __init__(self):
                self.uow = InMemoryUnitOfWork()

            def get_unit_of_work(self):
                return self.uow

        return MockUnitOfWorkFactory()
    
    @pytest.fixture
    def query_handler(self, unit_of_work_factory):
        """Create query handler."""
        return DeviceQueryHandler(unit_of_work_factory)
    
    async def test_handle_get_device_query(self, query_handler, unit_of_work_factory):
        """Test handling get device query."""
        # First create a device
        from edge_device_fleet_manager.repository.domain.entities import DeviceAggregate
        
        device_id = DeviceId.generate()
        identifier = DeviceIdentifier(serial_number="SN123456")
        
        aggregate = DeviceAggregate.create(
            device_id=device_id,
            name="Test Device",
            device_type=DeviceType.SENSOR,
            identifier=identifier
        )
        
        # Save device
        uow = unit_of_work_factory.uow
        await uow.devices.save(aggregate)
        
        # Query device
        query = GetDeviceQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id
        )
        
        result = await query_handler.handle(query)
        
        assert result.success is True
        assert hasattr(result, 'device')
        assert result.device.device_id == device_id.value
    
    async def test_handle_get_nonexistent_device(self, query_handler):
        """Test handling query for non-existent device."""
        device_id = DeviceId.generate()
        
        query = GetDeviceQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            device_id=device_id
        )
        
        result = await query_handler.handle(query)
        
        assert result.success is False
        assert "not found" in result.error_message
    
    async def test_handle_list_devices_query(self, query_handler, unit_of_work_factory):
        """Test handling list devices query."""
        # Create multiple devices
        from edge_device_fleet_manager.repository.domain.entities import DeviceAggregate
        
        uow = unit_of_work_factory.uow
        
        for i in range(3):
            device_id = DeviceId.generate()
            identifier = DeviceIdentifier(serial_number=f"SN{i}")
            
            aggregate = DeviceAggregate.create(
                device_id=device_id,
                name=f"Device {i}",
                device_type=DeviceType.SENSOR,
                identifier=identifier
            )
            
            await uow.devices.save(aggregate)
        
        # Query devices
        query = ListDevicesQuery(
            query_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            page=1,
            page_size=10
        )
        
        result = await query_handler.handle(query)
        
        assert result.success is True
        assert hasattr(result, 'device_list')
        assert len(result.device_list.devices) == 3


class TestApplicationService:
    """Test application service."""
    
    @pytest.fixture
    def unit_of_work_factory(self):
        """Create unit of work factory."""
        class MockUnitOfWorkFactory:
            def __init__(self):
                self.uow = InMemoryUnitOfWork()

            def get_unit_of_work(self):
                return self.uow

        return MockUnitOfWorkFactory()
    
    @pytest.fixture
    def application_service(self, unit_of_work_factory):
        """Create application service."""
        command_handler = DeviceCommandHandler(unit_of_work_factory)
        query_handler = DeviceQueryHandler(unit_of_work_factory)
        
        return DeviceApplicationService(command_handler, query_handler)
    
    async def test_register_device(self, application_service):
        """Test device registration through application service."""
        result = await application_service.register_device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            serial_number="SN123456",
            manufacturer="Test Corp"
        )
        
        assert result.success is True
        assert result.aggregate_id is not None
    
    async def test_get_device(self, application_service):
        """Test getting device through application service."""
        # First register a device
        register_result = await application_service.register_device(
            name="Test Device",
            device_type=DeviceType.SENSOR,
            serial_number="SN123456"
        )
        
        assert register_result.success is True
        
        # Then get it
        get_result = await application_service.get_device(register_result.aggregate_id)
        
        assert get_result.success is True
        assert hasattr(get_result, 'device')
        assert get_result.device.name == "Test Device"
