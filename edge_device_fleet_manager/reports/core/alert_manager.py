"""
Alert Manager

Core alert management system with rule-based alerting, severity levels,
notification routing, and alert lifecycle management.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

from ...core.logging import get_logger
from ...persistence.connection.manager import DatabaseManager
from ..alerts.severity import AlertSeverity, AlertStatus
from ..alerts.alert_rules import AlertRule, AlertRuleEngine
from .notification_service import NotificationService

logger = get_logger(__name__)


class AlertManager:
    """
    Core alert management system.
    
    Manages alert creation, processing, routing, and lifecycle with
    rule-based evaluation and notification delivery.
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None,
                 notification_service: Optional[NotificationService] = None):
        """
        Initialize alert manager.
        
        Args:
            database_manager: Optional database manager for persistence
            notification_service: Optional notification service for delivery
        """
        self.database_manager = database_manager
        self.notification_service = notification_service or NotificationService()
        
        # Alert state
        self.active_alerts = {}
        self.alert_rules = {}
        self.alert_history = {}
        self.suppression_rules = {}
        
        # Rule engine
        self.rule_engine = AlertRuleEngine()
        
        # Configuration
        self.max_history_entries = 10000
        self.default_escalation_timeout = timedelta(hours=1)
        self.auto_resolve_timeout = timedelta(hours=24)
        
        # Callbacks
        self.alert_callbacks = []
        self.escalation_callbacks = []
        
        self.logger = get_logger(f"{__name__}.AlertManager")
    
    async def initialize(self) -> None:
        """Initialize alert manager."""
        await self.notification_service.initialize()
        await self._load_alert_rules()
        await self._load_active_alerts()
        
        self.logger.info("Alert manager initialized")
    
    async def create_alert(self, title: str, description: str, 
                         severity: AlertSeverity = AlertSeverity.MEDIUM,
                         alert_type: str = 'system',
                         device_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         **kwargs) -> str:
        """
        Create a new alert.
        
        Args:
            title: Alert title
            description: Alert description
            severity: Alert severity level
            alert_type: Type of alert
            device_id: Optional associated device ID
            metadata: Optional alert metadata
            **kwargs: Additional alert properties
            
        Returns:
            Alert ID
        """
        try:
            alert_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            # Create alert data
            alert_data = {
                'id': alert_id,
                'title': title,
                'description': description,
                'alert_type': alert_type,
                'severity': severity,
                'status': AlertStatus.ACTIVE,
                'device_id': device_id,
                'metadata': metadata or {},
                'first_occurred': now,
                'last_occurred': now,
                'occurrence_count': 1,
                'acknowledged_at': None,
                'acknowledged_by': None,
                'resolved_at': None,
                'resolved_by': None,
                'escalated': False,
                'escalation_level': 0,
                'suppressed': False,
                **kwargs
            }
            
            # Check for duplicate/similar alerts
            existing_alert = await self._find_similar_alert(alert_data)
            if existing_alert:
                # Update existing alert
                return await self._update_existing_alert(existing_alert['id'], alert_data)
            
            # Check suppression rules
            if await self._is_suppressed(alert_data):
                alert_data['status'] = AlertStatus.SUPPRESSED
                alert_data['suppressed'] = True
                self.logger.info(f"Alert suppressed: {alert_id}")
            
            # Store alert
            self.active_alerts[alert_id] = alert_data
            
            # Persist to database if available
            if self.database_manager:
                await self._persist_alert(alert_data)
            
            # Add to history
            self._add_to_history(alert_data)
            
            # Process alert rules
            await self._process_alert_rules(alert_data)
            
            # Send notifications if not suppressed
            if not alert_data['suppressed']:
                await self._send_alert_notifications(alert_data)
            
            # Notify callbacks
            await self._notify_alert_callbacks(alert_data, 'created')
            
            self.logger.info(f"Alert created: {alert_id} - {title}")
            
            return alert_id
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
            raise
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str,
                              notes: Optional[str] = None) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User acknowledging the alert
            notes: Optional acknowledgment notes
            
        Returns:
            True if acknowledged successfully
        """
        try:
            if alert_id not in self.active_alerts:
                self.logger.warning(f"Alert not found for acknowledgment: {alert_id}")
                return False
            
            alert = self.active_alerts[alert_id]
            
            if alert['status'] == AlertStatus.ACKNOWLEDGED:
                self.logger.warning(f"Alert already acknowledged: {alert_id}")
                return False
            
            # Update alert
            alert['status'] = AlertStatus.ACKNOWLEDGED
            alert['acknowledged_at'] = datetime.now(timezone.utc)
            alert['acknowledged_by'] = acknowledged_by
            if notes:
                alert['metadata']['acknowledgment_notes'] = notes
            
            # Persist changes
            if self.database_manager:
                await self._persist_alert(alert)
            
            # Send acknowledgment notifications
            await self._send_acknowledgment_notifications(alert, acknowledged_by, notes)
            
            # Notify callbacks
            await self._notify_alert_callbacks(alert, 'acknowledged')
            
            self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str,
                          resolution_notes: Optional[str] = None) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolved_by: User resolving the alert
            resolution_notes: Optional resolution notes
            
        Returns:
            True if resolved successfully
        """
        try:
            if alert_id not in self.active_alerts:
                self.logger.warning(f"Alert not found for resolution: {alert_id}")
                return False
            
            alert = self.active_alerts[alert_id]
            
            if alert['status'] == AlertStatus.RESOLVED:
                self.logger.warning(f"Alert already resolved: {alert_id}")
                return False
            
            # Update alert
            alert['status'] = AlertStatus.RESOLVED
            alert['resolved_at'] = datetime.now(timezone.utc)
            alert['resolved_by'] = resolved_by
            if resolution_notes:
                alert['metadata']['resolution_notes'] = resolution_notes
            
            # Persist changes
            if self.database_manager:
                await self._persist_alert(alert)
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            # Send resolution notifications
            await self._send_resolution_notifications(alert, resolved_by, resolution_notes)
            
            # Notify callbacks
            await self._notify_alert_callbacks(alert, 'resolved')
            
            self.logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def escalate_alert(self, alert_id: str, escalation_reason: str = "timeout") -> bool:
        """
        Escalate an alert to higher severity or notification level.
        
        Args:
            alert_id: Alert ID to escalate
            escalation_reason: Reason for escalation
            
        Returns:
            True if escalated successfully
        """
        try:
            if alert_id not in self.active_alerts:
                self.logger.warning(f"Alert not found for escalation: {alert_id}")
                return False
            
            alert = self.active_alerts[alert_id]
            
            # Increase escalation level
            alert['escalation_level'] += 1
            alert['escalated'] = True
            alert['metadata']['escalation_reason'] = escalation_reason
            alert['metadata']['escalated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Escalate severity if possible
            current_severity = alert['severity']
            if current_severity == AlertSeverity.LOW:
                alert['severity'] = AlertSeverity.MEDIUM
            elif current_severity == AlertSeverity.MEDIUM:
                alert['severity'] = AlertSeverity.HIGH
            elif current_severity == AlertSeverity.HIGH:
                alert['severity'] = AlertSeverity.CRITICAL
            
            # Persist changes
            if self.database_manager:
                await self._persist_alert(alert)
            
            # Send escalation notifications
            await self._send_escalation_notifications(alert, escalation_reason)
            
            # Notify callbacks
            await self._notify_escalation_callbacks(alert, escalation_reason)
            
            self.logger.warning(f"Alert escalated: {alert_id} (level {alert['escalation_level']})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to escalate alert {alert_id}: {e}")
            return False
    
    async def add_alert_rule(self, rule: AlertRule) -> str:
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
            
        Returns:
            Rule ID
        """
        rule_id = str(uuid.uuid4())
        self.alert_rules[rule_id] = rule
        
        # Persist rule if database available
        if self.database_manager:
            await self._persist_alert_rule(rule_id, rule)
        
        self.logger.info(f"Alert rule added: {rule_id} - {rule.name}")
        
        return rule_id
    
    async def remove_alert_rule(self, rule_id: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if removed successfully
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            
            # Remove from database if available
            if self.database_manager:
                await self._remove_alert_rule(rule_id)
            
            self.logger.info(f"Alert rule removed: {rule_id}")
            return True
        
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None,
                         alert_type: Optional[str] = None,
                         device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active alerts with optional filtering.
        
        Args:
            severity: Optional severity filter
            alert_type: Optional type filter
            device_id: Optional device filter
            
        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity]
        
        if alert_type:
            alerts = [a for a in alerts if a['alert_type'] == alert_type]
        
        if device_id:
            alerts = [a for a in alerts if a.get('device_id') == device_id]
        
        # Sort by severity and time
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3
        }
        
        alerts.sort(key=lambda x: (
            severity_order.get(x['severity'], 4),
            x['first_occurred']
        ))
        
        return alerts
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics.
        
        Returns:
            Alert statistics dictionary
        """
        active_alerts = list(self.active_alerts.values())
        history_alerts = list(self.alert_history.values())
        
        # Count by severity
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([
                a for a in active_alerts if a['severity'] == severity
            ])
        
        # Count by status
        status_counts = {}
        for status in AlertStatus:
            status_counts[status.value] = len([
                a for a in active_alerts if a['status'] == status
            ])
        
        # Count by type
        type_counts = {}
        for alert in active_alerts:
            alert_type = alert['alert_type']
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        return {
            'active_alerts': len(active_alerts),
            'total_alerts_today': len([
                a for a in history_alerts 
                if datetime.fromisoformat(a['first_occurred']).date() == datetime.now().date()
            ]),
            'severity_distribution': severity_counts,
            'status_distribution': status_counts,
            'type_distribution': type_counts,
            'escalated_alerts': len([a for a in active_alerts if a.get('escalated', False)]),
            'suppressed_alerts': len([a for a in active_alerts if a.get('suppressed', False)]),
            'alert_rules': len(self.alert_rules)
        }
    
    async def _find_similar_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find similar existing alert to avoid duplicates."""
        for alert in self.active_alerts.values():
            if (alert['title'] == alert_data['title'] and
                alert['alert_type'] == alert_data['alert_type'] and
                alert.get('device_id') == alert_data.get('device_id') and
                alert['status'] in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]):
                return alert
        
        return None
    
    async def _update_existing_alert(self, alert_id: str, new_alert_data: Dict[str, Any]) -> str:
        """Update existing similar alert."""
        alert = self.active_alerts[alert_id]
        
        # Update occurrence count and last occurred time
        alert['occurrence_count'] += 1
        alert['last_occurred'] = new_alert_data['first_occurred']
        
        # Update description if different
        if alert['description'] != new_alert_data['description']:
            alert['description'] = new_alert_data['description']
        
        # Merge metadata
        alert['metadata'].update(new_alert_data['metadata'])
        
        # Persist changes
        if self.database_manager:
            await self._persist_alert(alert)
        
        self.logger.info(f"Updated existing alert: {alert_id} (occurrence #{alert['occurrence_count']})")
        
        return alert_id
    
    async def _is_suppressed(self, alert_data: Dict[str, Any]) -> bool:
        """Check if alert should be suppressed."""
        # Check suppression rules
        for rule in self.suppression_rules.values():
            if await self._matches_suppression_rule(alert_data, rule):
                return True
        
        return False
    
    async def _matches_suppression_rule(self, alert_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if alert matches suppression rule."""
        # Simple rule matching - can be extended
        if rule.get('alert_type') and rule['alert_type'] != alert_data['alert_type']:
            return False
        
        if rule.get('device_id') and rule['device_id'] != alert_data.get('device_id'):
            return False
        
        if rule.get('severity') and rule['severity'] != alert_data['severity']:
            return False
        
        return True
    
    async def _process_alert_rules(self, alert_data: Dict[str, Any]) -> None:
        """Process alert against defined rules."""
        for rule_id, rule in self.alert_rules.items():
            try:
                if await self.rule_engine.evaluate_rule(rule, alert_data):
                    await self._execute_rule_actions(rule, alert_data)
            except Exception as e:
                self.logger.error(f"Error processing alert rule {rule_id}: {e}")
    
    async def _execute_rule_actions(self, rule: AlertRule, alert_data: Dict[str, Any]) -> None:
        """Execute actions defined in alert rule."""
        for action in rule.actions:
            try:
                if action['type'] == 'escalate':
                    await self.escalate_alert(alert_data['id'], "rule-based")
                elif action['type'] == 'notify':
                    await self._send_rule_notification(alert_data, action)
                elif action['type'] == 'suppress':
                    alert_data['suppressed'] = True
                    alert_data['status'] = AlertStatus.SUPPRESSED
            except Exception as e:
                self.logger.error(f"Error executing rule action: {e}")
    
    async def _send_alert_notifications(self, alert_data: Dict[str, Any]) -> None:
        """Send notifications for new alert."""
        await self.notification_service.send_alert_notification(alert_data)
    
    async def _send_acknowledgment_notifications(self, alert_data: Dict[str, Any],
                                               acknowledged_by: str, notes: Optional[str]) -> None:
        """Send acknowledgment notifications."""
        await self.notification_service.send_acknowledgment_notification(
            alert_data, acknowledged_by, notes
        )
    
    async def _send_resolution_notifications(self, alert_data: Dict[str, Any],
                                           resolved_by: str, notes: Optional[str]) -> None:
        """Send resolution notifications."""
        await self.notification_service.send_resolution_notification(
            alert_data, resolved_by, notes
        )
    
    async def _send_escalation_notifications(self, alert_data: Dict[str, Any],
                                           escalation_reason: str) -> None:
        """Send escalation notifications."""
        await self.notification_service.send_escalation_notification(
            alert_data, escalation_reason
        )
    
    async def _send_rule_notification(self, alert_data: Dict[str, Any], action: Dict[str, Any]) -> None:
        """Send rule-based notification."""
        await self.notification_service.send_custom_notification(alert_data, action)
    
    def _add_to_history(self, alert_data: Dict[str, Any]) -> None:
        """Add alert to history."""
        self.alert_history[alert_data['id']] = alert_data.copy()
        
        # Limit history size
        if len(self.alert_history) > self.max_history_entries:
            # Remove oldest entries
            oldest_keys = sorted(
                self.alert_history.keys(),
                key=lambda k: self.alert_history[k]['first_occurred']
            )[:1000]
            for key in oldest_keys:
                del self.alert_history[key]
    
    async def _persist_alert(self, alert_data: Dict[str, Any]) -> None:
        """Persist alert to database."""
        # Implementation depends on database schema
        pass
    
    async def _persist_alert_rule(self, rule_id: str, rule: AlertRule) -> None:
        """Persist alert rule to database."""
        # Implementation depends on database schema
        pass
    
    async def _remove_alert_rule(self, rule_id: str) -> None:
        """Remove alert rule from database."""
        # Implementation depends on database schema
        pass
    
    async def _load_alert_rules(self) -> None:
        """Load alert rules from database."""
        # Implementation depends on database schema
        pass
    
    async def _load_active_alerts(self) -> None:
        """Load active alerts from database."""
        # Implementation depends on database schema
        pass
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any], str], None]) -> None:
        """Add alert event callback."""
        self.alert_callbacks.append(callback)
    
    def add_escalation_callback(self, callback: Callable[[Dict[str, Any], str], None]) -> None:
        """Add escalation event callback."""
        self.escalation_callbacks.append(callback)
    
    async def _notify_alert_callbacks(self, alert_data: Dict[str, Any], event_type: str) -> None:
        """Notify alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data, event_type)
                else:
                    callback(alert_data, event_type)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    async def _notify_escalation_callbacks(self, alert_data: Dict[str, Any], reason: str) -> None:
        """Notify escalation callbacks."""
        for callback in self.escalation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data, reason)
                else:
                    callback(alert_data, reason)
            except Exception as e:
                self.logger.error(f"Error in escalation callback: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown alert manager."""
        await self.notification_service.shutdown()
        self.logger.info("Alert manager shutdown complete")
