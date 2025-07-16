"""
Command and Query handlers for CQRS pattern.

Handlers contain the application logic for processing commands and queries,
coordinating between domain services and infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from uuid import uuid4

from .commands import (
    Command, CommandResult, CommandValidator,
    RegisterDeviceCommand, UpdateDeviceCommand, DeactivateDeviceCommand,
    ActivateDeviceCommand, UpdateLocationCommand, UpdateCapabilitiesCommand,
    UpdateConfigurationCommand, RecordMetricsCommand
)
from .queries import Query, QueryResult, PaginatedQueryResult, QueryValidator
from .dto import DeviceDto, DeviceListDto, DtoConverter
from ..domain.entities import DeviceAggregate, DeviceType
from ..domain.services import DeviceRegistrationService, DeviceValidationService, DeviceLifecycleService
from ..infrastructure.unit_of_work import UnitOfWork
from ...core.exceptions import ValidationError, RepositoryError


class CommandHandler(ABC):
    """Abstract base class for command handlers."""
    
    @abstractmethod
    async def handle(self, command: Command) -> CommandResult:
        """Handle a command and return result."""
        pass


class QueryHandler(ABC):
    """Abstract base class for query handlers."""
    
    @abstractmethod
    async def handle(self, query: Query) -> QueryResult:
        """Handle a query and return result."""
        pass


class DeviceCommandHandler(CommandHandler):
    """Handler for device-related commands."""
    
    def __init__(self, unit_of_work_factory):
        self.unit_of_work_factory = unit_of_work_factory
        self.validation_service = DeviceValidationService()
        self.registration_service = DeviceRegistrationService(self.validation_service)
        self.lifecycle_service = DeviceLifecycleService(self.validation_service)
    
    async def handle(self, command: Command) -> CommandResult:
        """Handle a device command."""
        try:
            if isinstance(command, RegisterDeviceCommand):
                return await self._handle_register_device(command)
            elif isinstance(command, UpdateDeviceCommand):
                return await self._handle_update_device(command)
            elif isinstance(command, DeactivateDeviceCommand):
                return await self._handle_deactivate_device(command)
            elif isinstance(command, ActivateDeviceCommand):
                return await self._handle_activate_device(command)
            elif isinstance(command, UpdateLocationCommand):
                return await self._handle_update_location(command)
            elif isinstance(command, UpdateCapabilitiesCommand):
                return await self._handle_update_capabilities(command)
            elif isinstance(command, UpdateConfigurationCommand):
                return await self._handle_update_configuration(command)
            elif isinstance(command, RecordMetricsCommand):
                return await self._handle_record_metrics(command)
            else:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Unsupported command type: {type(command).__name__}"
                )
        
        except ValidationError as e:
            return CommandResult.failure_result(command.command_id, str(e))
        except RepositoryError as e:
            return CommandResult.failure_result(command.command_id, f"Repository error: {e}")
        except Exception as e:
            return CommandResult.failure_result(command.command_id, f"Unexpected error: {e}")
    
    async def _handle_register_device(self, command: RegisterDeviceCommand) -> CommandResult:
        """Handle register device command."""
        # Validate command
        validation_errors = CommandValidator.validate_register_device_command(command)
        if validation_errors:
            return CommandResult.validation_failure_result(command.command_id, validation_errors)
        
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Check for duplicate identifier
            existing_device = await uow.devices.get_by_serial_number(command.identifier.serial_number)
            if existing_device:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with serial number {command.identifier.serial_number} already exists"
                )
            
            # Create device aggregate
            aggregate = self.registration_service.create_device_aggregate(
                name=command.name,
                device_type=command.device_type,
                identifier=command.identifier,
                manufacturer=command.manufacturer,
                model=command.model,
                location=command.location,
                capabilities=command.capabilities,
            )
            
            # Set initial configuration if provided
            if command.initial_configuration:
                for key, value in command.initial_configuration.items():
                    aggregate.update_configuration(key, value, command.user_id)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_update_device(self, command: UpdateDeviceCommand) -> CommandResult:
        """Handle update device command."""
        # Validate command
        validation_errors = CommandValidator.validate_update_device_command(command)
        if validation_errors:
            return CommandResult.validation_failure_result(command.command_id, validation_errors)
        
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Update device properties
            if command.name is not None:
                aggregate.update_name(command.name)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_deactivate_device(self, command: DeactivateDeviceCommand) -> CommandResult:
        """Handle deactivate device command."""
        # Validate command
        validation_errors = CommandValidator.validate_deactivate_device_command(command)
        if validation_errors:
            return CommandResult.validation_failure_result(command.command_id, validation_errors)
        
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Check if device can be deactivated
            can_deactivate, reason = self.lifecycle_service.can_deactivate_device(aggregate.device)
            if not can_deactivate:
                return CommandResult.failure_result(command.command_id, reason)
            
            # Deactivate device
            aggregate.deactivate(command.reason, command.user_id)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_activate_device(self, command: ActivateDeviceCommand) -> CommandResult:
        """Handle activate device command."""
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Check if device can be activated
            can_activate, reason = self.lifecycle_service.can_activate_device(aggregate.device)
            if not can_activate:
                return CommandResult.failure_result(command.command_id, reason)
            
            # Activate device
            aggregate.activate(command.user_id)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_update_location(self, command: UpdateLocationCommand) -> CommandResult:
        """Handle update location command."""
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Update location
            aggregate.update_location(command.location)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_update_capabilities(self, command: UpdateCapabilitiesCommand) -> CommandResult:
        """Handle update capabilities command."""
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Validate capabilities compatibility
            try:
                self.validation_service.validate_device_type_compatibility(
                    aggregate.device.device_type,
                    command.capabilities
                )
            except ValidationError as e:
                return CommandResult.failure_result(command.command_id, str(e))
            
            # Update capabilities
            aggregate.update_capabilities(command.capabilities)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_update_configuration(self, command: UpdateConfigurationCommand) -> CommandResult:
        """Handle update configuration command."""
        # Validate command
        validation_errors = CommandValidator.validate_update_configuration_command(command)
        if validation_errors:
            return CommandResult.validation_failure_result(command.command_id, validation_errors)
        
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Update configuration
            aggregate.update_configuration(
                command.configuration_key,
                command.configuration_value,
                command.user_id
            )
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)
    
    async def _handle_record_metrics(self, command: RecordMetricsCommand) -> CommandResult:
        """Handle record metrics command."""
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get device aggregate
            aggregate = await uow.devices.get_by_id(command.device_id)
            if not aggregate:
                return CommandResult.failure_result(
                    command.command_id,
                    f"Device with ID {command.device_id} not found"
                )
            
            # Record metrics
            aggregate.record_metrics(command.metrics)
            
            # Save aggregate
            await uow.devices.save(aggregate)
            uow.track_aggregate(aggregate)
            
            await uow.commit()
            
            return CommandResult.success_result(command.command_id, aggregate.device_id)


class DeviceQueryHandler(QueryHandler):
    """Handler for device-related queries."""

    def __init__(self, unit_of_work_factory):
        self.unit_of_work_factory = unit_of_work_factory
        self.lifecycle_service = DeviceLifecycleService(DeviceValidationService())

    async def handle(self, query: Query) -> QueryResult:
        """Handle a device query."""
        try:
            from .queries import (
                GetDeviceQuery, ListDevicesQuery, SearchDevicesQuery,
                GetDevicesByTypeQuery, GetDevicesByStatusQuery, GetStaleDevicesQuery
            )

            if isinstance(query, GetDeviceQuery):
                return await self._handle_get_device(query)
            elif isinstance(query, ListDevicesQuery):
                return await self._handle_list_devices(query)
            elif isinstance(query, SearchDevicesQuery):
                return await self._handle_search_devices(query)
            else:
                return QueryResult.failure_result(
                    query.query_id,
                    f"Unsupported query type: {type(query).__name__}"
                )

        except RepositoryError as e:
            return QueryResult.failure_result(query.query_id, f"Repository error: {e}")
        except Exception as e:
            return QueryResult.failure_result(query.query_id, f"Unexpected error: {e}")

    async def _handle_get_device(self, query) -> QueryResult:
        """Handle get device query."""
        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            aggregate = await uow.devices.get_by_id(query.device_id)
            if not aggregate:
                return QueryResult.failure_result(
                    query.query_id,
                    f"Device with ID {query.device_id} not found"
                )

            device_dto = DtoConverter.device_aggregate_to_dto(
                aggregate,
                include_metrics=query.include_metrics,
                include_configuration=query.include_configuration
            )

            return DeviceQueryResult(
                success=True,
                query_id=query.query_id,
                device=device_dto
            )

    async def _handle_list_devices(self, query) -> QueryResult:
        """Handle list devices query."""
        # Validate pagination
        validation_errors = QueryValidator.validate_pagination(query.page, query.page_size)
        validation_errors.extend(QueryValidator.validate_sort_parameters(query.sort_by, query.sort_order))

        if validation_errors:
            return QueryResult.failure_result(query.query_id, "Validation failed", validation_errors)

        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get all devices (in a real implementation, this would support pagination at the DB level)
            all_aggregates = await uow.devices.get_all()

            # Sort devices
            sorted_aggregates = self._sort_devices(all_aggregates, query.sort_by, query.sort_order)

            # Apply pagination
            total_count = len(sorted_aggregates)
            start_index = (query.page - 1) * query.page_size
            end_index = start_index + query.page_size
            page_aggregates = sorted_aggregates[start_index:end_index]

            # Convert to DTOs
            device_list_dto = DtoConverter.device_aggregates_to_list_dto(
                page_aggregates,
                query.page,
                query.page_size,
                total_count,
                include_metrics=query.include_metrics,
                include_configuration=query.include_configuration
            )

            return DeviceListQueryResult(
                success=True,
                query_id=query.query_id,
                device_list=device_list_dto
            )

    async def _handle_search_devices(self, query) -> QueryResult:
        """Handle search devices query."""
        # Validate pagination and sorting
        validation_errors = QueryValidator.validate_pagination(query.page, query.page_size)
        validation_errors.extend(QueryValidator.validate_sort_parameters(query.sort_by, query.sort_order))

        if validation_errors:
            return QueryResult.failure_result(query.query_id, "Validation failed", validation_errors)

        async with self.unit_of_work_factory.get_unit_of_work() as uow:
            # Get all devices and apply filters
            all_aggregates = await uow.devices.get_all()
            filtered_aggregates = self._apply_search_filters(all_aggregates, query)

            # Sort devices
            sorted_aggregates = self._sort_devices(filtered_aggregates, query.sort_by, query.sort_order)

            # Apply pagination
            total_count = len(sorted_aggregates)
            start_index = (query.page - 1) * query.page_size
            end_index = start_index + query.page_size
            page_aggregates = sorted_aggregates[start_index:end_index]

            # Convert to DTOs
            devices = [
                DtoConverter.device_aggregate_to_dto(aggregate)
                for aggregate in page_aggregates
            ]

            total_pages = (total_count + query.page_size - 1) // query.page_size
            has_next = query.page < total_pages
            has_previous = query.page > 1

            from .dto import DeviceSearchResultDto
            search_result_dto = DeviceSearchResultDto(
                devices=devices,
                search_term=query.search_term,
                filters_applied=self._get_applied_filters(query),
                page=query.page,
                page_size=query.page_size,
                total_count=total_count,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous,
            )

            return DeviceSearchQueryResult(
                success=True,
                query_id=query.query_id,
                search_result=search_result_dto
            )

    def _sort_devices(self, aggregates: List[DeviceAggregate], sort_by: str, sort_order: str) -> List[DeviceAggregate]:
        """Sort device aggregates."""
        reverse = sort_order == "desc"

        if sort_by == "name":
            return sorted(aggregates, key=lambda a: a.device.name.lower(), reverse=reverse)
        elif sort_by == "device_type":
            return sorted(aggregates, key=lambda a: a.device.device_type.value, reverse=reverse)
        elif sort_by == "status":
            return sorted(aggregates, key=lambda a: a.device.status.value, reverse=reverse)
        elif sort_by == "manufacturer":
            return sorted(aggregates, key=lambda a: a.device.manufacturer or "", reverse=reverse)
        elif sort_by == "created_at":
            return sorted(aggregates, key=lambda a: a.device.created_at, reverse=reverse)
        elif sort_by == "last_seen":
            return sorted(aggregates, key=lambda a: a.device.last_seen or a.device.created_at, reverse=reverse)
        else:
            return aggregates

    def _apply_search_filters(self, aggregates: List[DeviceAggregate], query) -> List[DeviceAggregate]:
        """Apply search filters to device aggregates."""
        filtered = aggregates

        # Text search
        if query.search_term:
            search_term = query.search_term.lower()
            filtered = [
                a for a in filtered
                if (search_term in a.device.name.lower() or
                    (a.device.manufacturer and search_term in a.device.manufacturer.lower()) or
                    (a.device.model and search_term in a.device.model.lower()) or
                    search_term in a.device.identifier.serial_number.lower())
            ]

        # Device type filter
        if query.device_types:
            filtered = [a for a in filtered if a.device.device_type in query.device_types]

        # Status filter
        if query.statuses:
            filtered = [a for a in filtered if a.device.status in query.statuses]

        return filtered

    def _get_applied_filters(self, query) -> dict:
        """Get dictionary of applied filters."""
        filters = {}

        if query.search_term:
            filters['search_term'] = query.search_term
        if query.device_types:
            filters['device_types'] = [dt.value for dt in query.device_types]
        if query.statuses:
            filters['statuses'] = [s.value for s in query.statuses]

        return filters


# Query result classes
from dataclasses import dataclass

@dataclass(frozen=True)
class DeviceQueryResult(QueryResult):
    """Result for single device query."""
    device: Optional[DeviceDto] = None


@dataclass(frozen=True)
class DeviceListQueryResult(QueryResult):
    """Result for device list query."""
    device_list: Optional[DeviceListDto] = None


@dataclass(frozen=True)
class DeviceSearchQueryResult(QueryResult):
    """Result for device search query."""
    search_result: Optional[Any] = None
