"""
Unit tests for discovery event system.

Tests the event-driven architecture including:
- Event classes and serialization
- Event bus functionality
- Event filtering and routing
- Event subscriptions and callbacks
- Event history and persistence
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock

from edge_device_fleet_manager.discovery.events import (
    DiscoveryEvent, EventPriority, EventFilter, EventSubscription,
    DiscoveryEventBus, DeviceDiscoveredEvent, DeviceLostEvent,
    DeviceUpdatedEvent, DiscoveryStartedEvent, DiscoveryCompletedEvent,
    DiscoveryErrorEvent, PluginLoadedEvent, PluginUnloadedEvent
)
from edge_device_fleet_manager.discovery.core import Device, DiscoveryResult, DeviceStatus, DiscoveryEngine


class TestDiscoveryEvents:
    """Test discovery event classes."""
    
    def test_device_discovered_event(self):
        """Test device discovered event."""
        device = Device(
            ip_address="192.168.1.100",
            name="Test Device",
            discovery_protocol="mdns",
            status=DeviceStatus.ONLINE
        )
        
        event = DeviceDiscoveredEvent(
            device=device,
            discovery_protocol="mdns",
            is_new_device=True,
            source="test"
        )
        
        assert event.event_type == "device.discovered"
        assert event.device == device
        assert event.discovery_protocol == "mdns"
        assert event.is_new_device is True
        assert event.source == "test"
        assert event.priority == EventPriority.NORMAL
        assert isinstance(event.timestamp, datetime)
        assert event.event_id is not None
    
    def test_device_lost_event(self):
        """Test device lost event."""
        last_seen = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        event = DeviceLostEvent(
            device_id="device-123",
            last_seen=last_seen,
            reason="timeout",
            priority=EventPriority.HIGH
        )
        
        assert event.event_type == "device.lost"
        assert event.device_id == "device-123"
        assert event.last_seen == last_seen
        assert event.reason == "timeout"
        assert event.priority == EventPriority.HIGH
    
    def test_device_updated_event(self):
        """Test device updated event."""
        device = Device(
            ip_address="192.168.1.100",
            name="Updated Device",
            status=DeviceStatus.ONLINE
        )
        
        event = DeviceUpdatedEvent(
            device=device,
            changed_fields=["name", "status"],
            previous_values={"name": "Old Device", "status": "offline"}
        )
        
        assert event.event_type == "device.updated"
        assert event.device == device
        assert event.changed_fields == ["name", "status"]
        assert event.previous_values["name"] == "Old Device"
    
    def test_discovery_started_event(self):
        """Test discovery started event."""
        event = DiscoveryStartedEvent(
            protocols=["mdns", "ssdp"],
            scan_parameters={"timeout": 30, "max_devices": 100}
        )
        
        assert event.event_type == "discovery.started"
        assert event.protocols == ["mdns", "ssdp"]
        assert event.scan_parameters["timeout"] == 30
        assert event.scan_parameters["max_devices"] == 100
    
    def test_discovery_completed_event(self):
        """Test discovery completed event."""
        result = DiscoveryResult(protocol="mdns", success=True)
        result.add_device(Device(ip_address="192.168.1.100", status=DeviceStatus.ONLINE))
        
        event = DiscoveryCompletedEvent(
            result=result,
            duration=15.5,
            devices_found=1
        )
        
        assert event.event_type == "discovery.completed"
        assert event.result == result
        assert event.duration == 15.5
        assert event.devices_found == 1
    
    def test_discovery_error_event(self):
        """Test discovery error event."""
        event = DiscoveryErrorEvent(
            error_message="Connection timeout",
            error_type="TimeoutError",
            protocol="mdns",
            recoverable=True,
            priority=EventPriority.HIGH
        )
        
        assert event.event_type == "discovery.error"
        assert event.error_message == "Connection timeout"
        assert event.error_type == "TimeoutError"
        assert event.protocol == "mdns"
        assert event.recoverable is True
        assert event.priority == EventPriority.HIGH
    
    def test_plugin_events(self):
        """Test plugin-related events."""
        loaded_event = PluginLoadedEvent(
            plugin_name="test_plugin",
            plugin_version="1.0.0"
        )
        
        assert loaded_event.event_type == "plugin.loaded"
        assert loaded_event.plugin_name == "test_plugin"
        assert loaded_event.plugin_version == "1.0.0"
        
        unloaded_event = PluginUnloadedEvent(
            plugin_name="test_plugin",
            reason="shutdown"
        )
        
        assert unloaded_event.event_type == "plugin.unloaded"
        assert unloaded_event.plugin_name == "test_plugin"
        assert unloaded_event.reason == "shutdown"
    
    def test_event_serialization(self):
        """Test event serialization to dictionary."""
        device = Device(
            ip_address="192.168.1.100",
            name="Test Device",
            status=DeviceStatus.ONLINE
        )
        
        event = DeviceDiscoveredEvent(
            device=device,
            discovery_protocol="mdns",
            is_new_device=True,
            source="test",
            metadata={"key": "value"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "device.discovered"
        assert event_dict["discovery_protocol"] == "mdns"
        assert event_dict["is_new_device"] is True
        assert event_dict["source"] == "test"
        assert event_dict["metadata"]["key"] == "value"
        assert "device" in event_dict
        assert "timestamp" in event_dict
        assert "event_id" in event_dict


class TestEventFilter:
    """Test event filtering."""
    
    def test_event_type_filter(self):
        """Test filtering by event type."""
        event_filter = EventFilter(event_types=["device.discovered", "device.lost"])
        
        discovered_event = DeviceDiscoveredEvent()
        lost_event = DeviceLostEvent()
        error_event = DiscoveryErrorEvent()
        
        assert event_filter.matches(discovered_event) is True
        assert event_filter.matches(lost_event) is True
        assert event_filter.matches(error_event) is False
    
    def test_source_filter(self):
        """Test filtering by source."""
        event_filter = EventFilter(sources=["mdns", "ssdp"])
        
        mdns_event = DeviceDiscoveredEvent(source="mdns")
        ssdp_event = DeviceDiscoveredEvent(source="ssdp")
        snmp_event = DeviceDiscoveredEvent(source="snmp")
        
        assert event_filter.matches(mdns_event) is True
        assert event_filter.matches(ssdp_event) is True
        assert event_filter.matches(snmp_event) is False
    
    def test_priority_filter(self):
        """Test filtering by priority."""
        event_filter = EventFilter(min_priority=EventPriority.HIGH)
        
        low_event = DeviceDiscoveredEvent(priority=EventPriority.LOW)
        normal_event = DeviceDiscoveredEvent(priority=EventPriority.NORMAL)
        high_event = DeviceDiscoveredEvent(priority=EventPriority.HIGH)
        critical_event = DeviceDiscoveredEvent(priority=EventPriority.CRITICAL)
        
        assert event_filter.matches(low_event) is False
        assert event_filter.matches(normal_event) is False
        assert event_filter.matches(high_event) is True
        assert event_filter.matches(critical_event) is True
    
    def test_custom_filter(self):
        """Test custom filter function."""
        def custom_filter(event):
            return hasattr(event, 'device') and event.device.ip_address.startswith("192.168.1.")
        
        event_filter = EventFilter(custom_filter=custom_filter)
        
        device1 = Device(ip_address="192.168.1.100", status=DeviceStatus.ONLINE)
        device2 = Device(ip_address="10.0.0.100", status=DeviceStatus.ONLINE)
        
        event1 = DeviceDiscoveredEvent(device=device1)
        event2 = DeviceDiscoveredEvent(device=device2)
        error_event = DiscoveryErrorEvent()
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
        assert event_filter.matches(error_event) is False
    
    def test_combined_filters(self):
        """Test combining multiple filters."""
        event_filter = EventFilter(
            event_types=["device.discovered"],
            sources=["mdns"],
            min_priority=EventPriority.NORMAL
        )
        
        # Matches all criteria
        matching_event = DeviceDiscoveredEvent(
            source="mdns",
            priority=EventPriority.HIGH
        )
        
        # Wrong event type
        wrong_type = DeviceLostEvent(
            source="mdns",
            priority=EventPriority.HIGH
        )
        
        # Wrong source
        wrong_source = DeviceDiscoveredEvent(
            source="ssdp",
            priority=EventPriority.HIGH
        )
        
        # Wrong priority
        wrong_priority = DeviceDiscoveredEvent(
            source="mdns",
            priority=EventPriority.LOW
        )
        
        assert event_filter.matches(matching_event) is True
        assert event_filter.matches(wrong_type) is False
        assert event_filter.matches(wrong_source) is False
        assert event_filter.matches(wrong_priority) is False


class TestEventSubscription:
    """Test event subscriptions."""
    
    def test_subscription_creation(self):
        """Test subscription creation."""
        callback = Mock()
        event_filter = EventFilter(event_types=["device.discovered"])
        
        subscription = EventSubscription(
            callback=callback,
            event_filter=event_filter,
            subscription_id="test-sub"
        )
        
        assert subscription.callback == callback
        assert subscription.filter == event_filter
        assert subscription.subscription_id == "test-sub"
        assert subscription.event_count == 0
        assert subscription.last_event_time is None
        assert isinstance(subscription.created_at, datetime)
    
    async def test_sync_callback_handling(self):
        """Test synchronous callback handling."""
        callback = Mock()
        subscription = EventSubscription(callback=callback)
        
        event = DeviceDiscoveredEvent()
        result = await subscription.handle_event(event)
        
        assert result is True
        assert subscription.event_count == 1
        assert subscription.last_event_time is not None
        callback.assert_called_once_with(event)
    
    async def test_async_callback_handling(self):
        """Test asynchronous callback handling."""
        callback = AsyncMock()
        subscription = EventSubscription(callback=callback)
        
        event = DeviceDiscoveredEvent()
        result = await subscription.handle_event(event)
        
        assert result is True
        assert subscription.event_count == 1
        callback.assert_called_once_with(event)
    
    async def test_filtered_callback_handling(self):
        """Test callback handling with filtering."""
        callback = Mock()
        event_filter = EventFilter(event_types=["device.discovered"])
        subscription = EventSubscription(callback=callback, event_filter=event_filter)
        
        # Matching event
        matching_event = DeviceDiscoveredEvent()
        result1 = await subscription.handle_event(matching_event)
        
        # Non-matching event
        non_matching_event = DeviceLostEvent()
        result2 = await subscription.handle_event(non_matching_event)
        
        assert result1 is True
        assert result2 is False
        assert subscription.event_count == 1
        callback.assert_called_once_with(matching_event)
    
    async def test_callback_error_handling(self):
        """Test callback error handling."""
        def failing_callback(event):
            raise Exception("Callback failed")
        
        subscription = EventSubscription(callback=failing_callback)
        
        event = DeviceDiscoveredEvent()
        result = await subscription.handle_event(event)
        
        # Should return False but not raise exception
        assert result is False
        assert subscription.event_count == 0


class TestDiscoveryEventBus:
    """Test discovery event bus."""
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus."""
        return DiscoveryEventBus(max_history=100)
    
    async def test_event_bus_creation(self, event_bus):
        """Test event bus creation."""
        stats = await event_bus.get_statistics()
        
        assert stats["events_published"] == 0
        assert stats["events_delivered"] == 0
        assert stats["subscriptions_count"] == 0
        assert stats["history_size"] == 0
        assert "uptime_seconds" in stats
    
    async def test_subscription_management(self, event_bus):
        """Test subscription management."""
        callback = Mock()
        
        # Subscribe
        sub_id = await event_bus.subscribe(callback)
        assert isinstance(sub_id, str)
        
        stats = await event_bus.get_statistics()
        assert stats["subscriptions_count"] == 1
        
        # Unsubscribe
        result = await event_bus.unsubscribe(sub_id)
        assert result is True
        
        stats = await event_bus.get_statistics()
        assert stats["subscriptions_count"] == 0
        
        # Unsubscribe non-existent
        result = await event_bus.unsubscribe("non-existent")
        assert result is False
    
    async def test_event_publishing(self, event_bus):
        """Test event publishing."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Subscribe callbacks
        await event_bus.subscribe(callback1)
        await event_bus.subscribe(callback2)
        
        # Publish event
        event = DeviceDiscoveredEvent()
        delivered_count = await event_bus.publish(event)
        
        assert delivered_count == 2
        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)
        
        # Check statistics
        stats = await event_bus.get_statistics()
        assert stats["events_published"] == 1
        assert stats["events_delivered"] == 2
    
    async def test_filtered_publishing(self, event_bus):
        """Test publishing with filtered subscriptions."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Subscribe with different filters
        filter1 = EventFilter(event_types=["device.discovered"])
        filter2 = EventFilter(event_types=["device.lost"])
        
        await event_bus.subscribe(callback1, filter1)
        await event_bus.subscribe(callback2, filter2)
        
        # Publish device discovered event
        discovered_event = DeviceDiscoveredEvent()
        delivered_count = await event_bus.publish(discovered_event)
        
        assert delivered_count == 1
        callback1.assert_called_once_with(discovered_event)
        callback2.assert_not_called()
        
        # Publish device lost event
        lost_event = DeviceLostEvent()
        delivered_count = await event_bus.publish(lost_event)
        
        assert delivered_count == 1
        callback2.assert_called_once_with(lost_event)
    
    async def test_event_history(self, event_bus):
        """Test event history management."""
        # Publish some events
        events = [
            DeviceDiscoveredEvent(),
            DeviceLostEvent(),
            DiscoveryErrorEvent()
        ]
        
        for event in events:
            await event_bus.publish(event)
        
        # Get all history
        history = await event_bus.get_event_history()
        assert len(history) == 3
        
        # Get filtered history
        filtered_history = await event_bus.get_event_history(
            event_types=["device.discovered", "device.lost"]
        )
        assert len(filtered_history) == 2
        
        # Get limited history
        limited_history = await event_bus.get_event_history(limit=1)
        assert len(limited_history) == 1
        
        # Get history since timestamp
        since = datetime.now(timezone.utc) - timedelta(seconds=1)
        recent_history = await event_bus.get_event_history(since=since)
        assert len(recent_history) == 3
    
    async def test_history_size_limit(self):
        """Test event history size limit."""
        event_bus = DiscoveryEventBus(max_history=2)
        
        # Publish more events than history limit
        for i in range(5):
            event = DeviceDiscoveredEvent()
            await event_bus.publish(event)
        
        # Should only keep the last 2 events
        history = await event_bus.get_event_history()
        assert len(history) == 2
    
    async def test_concurrent_publishing(self, event_bus):
        """Test concurrent event publishing."""
        callback = Mock()
        await event_bus.subscribe(callback)
        
        # Publish multiple events concurrently
        events = [DeviceDiscoveredEvent() for _ in range(10)]
        tasks = [event_bus.publish(event) for event in events]
        
        results = await asyncio.gather(*tasks)
        
        # All events should be delivered
        assert all(result == 1 for result in results)
        assert callback.call_count == 10
        
        # Check statistics
        stats = await event_bus.get_statistics()
        assert stats["events_published"] == 10
        assert stats["events_delivered"] == 10
    
    async def test_event_bus_shutdown(self, event_bus):
        """Test event bus shutdown."""
        callback = Mock()
        await event_bus.subscribe(callback)
        
        # Publish event before shutdown
        event = DeviceDiscoveredEvent()
        await event_bus.publish(event)
        
        # Shutdown
        await event_bus.shutdown()
        
        # Check state after shutdown
        stats = await event_bus.get_statistics()
        assert stats["subscriptions_count"] == 0
        assert stats["history_size"] == 0
