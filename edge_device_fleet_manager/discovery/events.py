"""
Discovery Event System

This module provides a comprehensive event system for device discovery,
enabling real-time notifications and event-driven architecture.

Key Features:
- Async event bus with pub/sub pattern
- Typed event classes for different discovery events
- Event filtering and routing
- Event persistence and replay
- Performance monitoring and metrics
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from ..core.logging import get_logger
from .core import Device, DiscoveryResult


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class DiscoveryEvent(ABC):
    """Base class for all discovery events."""
    
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type identifier."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "source": self.source,
            "metadata": self.metadata
        }


@dataclass
class DeviceDiscoveredEvent(DiscoveryEvent):
    """Event raised when a new device is discovered."""
    
    device: Device = field(default_factory=lambda: Device())
    discovery_protocol: str = ""
    is_new_device: bool = True
    
    @property
    def event_type(self) -> str:
        return "device.discovered"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "device": self.device.to_dict(),
            "discovery_protocol": self.discovery_protocol,
            "is_new_device": self.is_new_device
        })
        return data


@dataclass
class DeviceLostEvent(DiscoveryEvent):
    """Event raised when a device is no longer discoverable."""
    
    device_id: str = ""
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = "timeout"
    
    @property
    def event_type(self) -> str:
        return "device.lost"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "device_id": self.device_id,
            "last_seen": self.last_seen.isoformat(),
            "reason": self.reason
        })
        return data


@dataclass
class DeviceUpdatedEvent(DiscoveryEvent):
    """Event raised when device information is updated."""
    
    device: Device = field(default_factory=lambda: Device())
    changed_fields: List[str] = field(default_factory=list)
    previous_values: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return "device.updated"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "device": self.device.to_dict(),
            "changed_fields": self.changed_fields,
            "previous_values": self.previous_values
        })
        return data


@dataclass
class DiscoveryStartedEvent(DiscoveryEvent):
    """Event raised when discovery process starts."""
    
    protocols: List[str] = field(default_factory=list)
    scan_parameters: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return "discovery.started"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "protocols": self.protocols,
            "scan_parameters": self.scan_parameters
        })
        return data


@dataclass
class DiscoveryCompletedEvent(DiscoveryEvent):
    """Event raised when discovery process completes."""
    
    result: DiscoveryResult = field(default_factory=lambda: DiscoveryResult())
    duration: float = 0.0
    devices_found: int = 0
    
    @property
    def event_type(self) -> str:
        return "discovery.completed"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "duration": self.duration,
            "devices_found": self.devices_found,
            "success": self.result.success,
            "protocol": self.result.protocol
        })
        return data


@dataclass
class DiscoveryErrorEvent(DiscoveryEvent):
    """Event raised when discovery encounters an error."""
    
    error_message: str = ""
    error_type: str = ""
    protocol: str = ""
    recoverable: bool = True
    
    @property
    def event_type(self) -> str:
        return "discovery.error"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "error_message": self.error_message,
            "error_type": self.error_type,
            "protocol": self.protocol,
            "recoverable": self.recoverable
        })
        return data


@dataclass
class PluginLoadedEvent(DiscoveryEvent):
    """Event raised when a plugin is loaded."""
    
    plugin_name: str = ""
    plugin_version: str = ""
    
    @property
    def event_type(self) -> str:
        return "plugin.loaded"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "plugin_name": self.plugin_name,
            "plugin_version": self.plugin_version
        })
        return data


@dataclass
class PluginUnloadedEvent(DiscoveryEvent):
    """Event raised when a plugin is unloaded."""
    
    plugin_name: str = ""
    reason: str = ""
    
    @property
    def event_type(self) -> str:
        return "plugin.unloaded"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "plugin_name": self.plugin_name,
            "reason": self.reason
        })
        return data


class EventFilter:
    """Filter for event subscriptions."""
    
    def __init__(
        self,
        event_types: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        min_priority: Optional[EventPriority] = None,
        custom_filter: Optional[Callable[[DiscoveryEvent], bool]] = None
    ):
        self.event_types = set(event_types) if event_types else None
        self.sources = set(sources) if sources else None
        self.min_priority = min_priority
        self.custom_filter = custom_filter
    
    def matches(self, event: DiscoveryEvent) -> bool:
        """Check if event matches this filter."""
        # Check event type
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check source
        if self.sources and event.source not in self.sources:
            return False
        
        # Check priority
        if self.min_priority and event.priority.value < self.min_priority.value:
            return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True


class EventSubscription:
    """Event subscription with callback and filter."""
    
    def __init__(
        self,
        callback: Callable[[DiscoveryEvent], None],
        event_filter: Optional[EventFilter] = None,
        subscription_id: Optional[str] = None
    ):
        self.callback = callback
        self.filter = event_filter or EventFilter()
        self.subscription_id = subscription_id or str(uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.event_count = 0
        self.last_event_time: Optional[datetime] = None
    
    async def handle_event(self, event: DiscoveryEvent) -> bool:
        """Handle an event if it matches the filter."""
        if self.filter.matches(event):
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(event)
                else:
                    self.callback(event)
                
                self.event_count += 1
                self.last_event_time = datetime.now(timezone.utc)
                return True
            except Exception as e:
                # Log error but don't propagate to avoid breaking other subscriptions
                logger = get_logger(__name__)
                logger.error(
                    "Event callback failed",
                    subscription_id=self.subscription_id,
                    event_type=event.event_type,
                    error=str(e),
                    exc_info=e
                )
        
        return False


class DiscoveryEventBus:
    """
    Async event bus for discovery system.
    
    Provides pub/sub functionality with filtering, routing, and persistence.
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.logger = get_logger(__name__)
        
        # Subscriptions
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._subscriptions_lock = asyncio.Lock()
        
        # Event history
        self._event_history: List[DiscoveryEvent] = []
        self._history_lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "subscriptions_count": 0,
            "start_time": datetime.now(timezone.utc)
        }
    
    async def subscribe(
        self,
        callback: Callable[[DiscoveryEvent], None],
        event_filter: Optional[EventFilter] = None,
        subscription_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to events.
        
        Args:
            callback: Callback function to handle events
            event_filter: Optional filter for events
            subscription_id: Optional custom subscription ID
        
        Returns:
            str: Subscription ID
        """
        subscription = EventSubscription(callback, event_filter, subscription_id)
        
        async with self._subscriptions_lock:
            self._subscriptions[subscription.subscription_id] = subscription
            self._stats["subscriptions_count"] = len(self._subscriptions)
        
        self.logger.debug("Event subscription created", subscription_id=subscription.subscription_id)
        return subscription.subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID to remove
        
        Returns:
            bool: True if subscription was removed
        """
        async with self._subscriptions_lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                self._stats["subscriptions_count"] = len(self._subscriptions)
                self.logger.debug("Event subscription removed", subscription_id=subscription_id)
                return True
        
        return False
    
    async def publish(self, event: DiscoveryEvent) -> int:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        
        Returns:
            int: Number of subscribers that received the event
        """
        # Add to history
        async with self._history_lock:
            self._event_history.append(event)
            if len(self._event_history) > self.max_history:
                self._event_history.pop(0)
        
        # Update statistics
        self._stats["events_published"] += 1
        
        # Deliver to subscribers
        delivered_count = 0
        async with self._subscriptions_lock:
            subscriptions = list(self._subscriptions.values())
        
        # Process subscriptions concurrently
        tasks = []
        for subscription in subscriptions:
            task = asyncio.create_task(subscription.handle_event(event))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            delivered_count = sum(1 for result in results if result is True)
        
        self._stats["events_delivered"] += delivered_count
        
        self.logger.debug(
            "Event published",
            event_type=event.event_type,
            event_id=event.event_id,
            subscribers=len(subscriptions),
            delivered=delivered_count
        )
        
        return delivered_count
    
    async def get_event_history(
        self,
        event_types: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[DiscoveryEvent]:
        """
        Get event history with optional filtering.
        
        Args:
            event_types: Filter by event types
            since: Filter events since this timestamp
            limit: Maximum number of events to return
        
        Returns:
            List[DiscoveryEvent]: Filtered event history
        """
        async with self._history_lock:
            events = self._event_history.copy()
        
        # Apply filters
        if event_types:
            event_types_set = set(event_types)
            events = [e for e in events if e.event_type in event_types_set]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return events
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        async with self._subscriptions_lock:
            subscription_stats = {
                sub_id: {
                    "event_count": sub.event_count,
                    "last_event_time": sub.last_event_time.isoformat() if sub.last_event_time else None,
                    "created_at": sub.created_at.isoformat()
                }
                for sub_id, sub in self._subscriptions.items()
            }
        
        uptime = (datetime.now(timezone.utc) - self._stats["start_time"]).total_seconds()
        
        return {
            "events_published": self._stats["events_published"],
            "events_delivered": self._stats["events_delivered"],
            "subscriptions_count": self._stats["subscriptions_count"],
            "history_size": len(self._event_history),
            "uptime_seconds": uptime,
            "subscriptions": subscription_stats
        }
    
    async def clear_history(self) -> None:
        """Clear event history."""
        async with self._history_lock:
            self._event_history.clear()
        
        self.logger.info("Event history cleared")
    
    async def shutdown(self) -> None:
        """Shutdown the event bus."""
        async with self._subscriptions_lock:
            self._subscriptions.clear()
            self._stats["subscriptions_count"] = 0
        
        await self.clear_history()
        self.logger.info("Event bus shutdown")
