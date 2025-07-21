"""
Notification Service

Multi-channel notification delivery system supporting email, SMS, webhooks,
Slack, and other notification channels with routing and templating.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from enum import Enum
import json
import uuid

from ...core.logging import get_logger
from ..notifications.email_notifier import EmailNotifier
from ..notifications.webhook_notifier import WebhookNotifier
from ..notifications.slack_notifier import SlackNotifier
from ..notifications.sms_notifier import SMSNotifier
from ..alerts.severity import AlertSeverity, AlertStatus

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """Notification channel types."""
    
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    PUSH = "push"
    CUSTOM = "custom"


class NotificationPriority(Enum):
    """Notification priority levels."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    """
    Multi-channel notification delivery service.
    
    Manages notification routing, delivery, templating, and tracking
    across multiple channels and providers.
    """
    
    def __init__(self):
        """Initialize notification service."""
        self.notifiers = {}
        self.routing_rules = {}
        self.templates = {}
        self.delivery_history = {}
        self.failed_deliveries = {}
        
        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_seconds = 60
        self.max_history_entries = 10000
        
        # Rate limiting
        self.rate_limits = {}
        self.rate_limit_windows = {}
        
        self.logger = get_logger(f"{__name__}.NotificationService")
    
    async def initialize(self) -> None:
        """Initialize notification service and notifiers."""
        # Initialize built-in notifiers
        self.notifiers = {
            NotificationChannel.EMAIL: EmailNotifier(),
            NotificationChannel.WEBHOOK: WebhookNotifier(),
            NotificationChannel.SLACK: SlackNotifier(),
            NotificationChannel.SMS: SMSNotifier()
        }
        
        # Initialize each notifier
        for channel, notifier in self.notifiers.items():
            try:
                await notifier.initialize()
                self.logger.info(f"Initialized {channel.value} notifier")
            except Exception as e:
                self.logger.error(f"Failed to initialize {channel.value} notifier: {e}")
        
        # Load default routing rules
        await self._load_default_routing_rules()
        
        # Load notification templates
        await self._load_notification_templates()
        
        self.logger.info("Notification service initialized")
    
    async def send_alert_notification(self, alert_data: Dict[str, Any],
                                    channels: Optional[List[NotificationChannel]] = None,
                                    recipients: Optional[List[str]] = None,
                                    template: Optional[str] = None) -> Dict[str, Any]:
        """
        Send alert notification.
        
        Args:
            alert_data: Alert data to send
            channels: Optional specific channels to use
            recipients: Optional specific recipients
            template: Optional template name
            
        Returns:
            Delivery results
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Determine channels and recipients
            if not channels:
                channels = await self._route_alert_notification(alert_data)
            
            if not recipients:
                recipients = await self._get_alert_recipients(alert_data, channels)
            
            # Get template
            template_name = template or self._get_alert_template(alert_data)
            notification_content = await self._render_alert_template(alert_data, template_name)
            
            # Send notifications
            delivery_results = await self._send_multi_channel_notification(
                notification_id=notification_id,
                channels=channels,
                recipients=recipients,
                content=notification_content,
                priority=self._get_alert_priority(alert_data),
                metadata={'alert_id': alert_data.get('id'), 'type': 'alert'}
            )
            
            # Track delivery
            self._track_delivery(notification_id, 'alert', alert_data, delivery_results)
            
            self.logger.info(f"Alert notification sent: {notification_id}")
            
            return {
                'notification_id': notification_id,
                'channels_attempted': len(channels),
                'recipients_attempted': len(recipients),
                'delivery_results': delivery_results,
                'success': any(r.get('success', False) for r in delivery_results.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {e}")
            raise
    
    async def send_acknowledgment_notification(self, alert_data: Dict[str, Any],
                                             acknowledged_by: str,
                                             notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Send alert acknowledgment notification.
        
        Args:
            alert_data: Alert data
            acknowledged_by: User who acknowledged
            notes: Optional acknowledgment notes
            
        Returns:
            Delivery results
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Create acknowledgment content
            ack_data = {
                **alert_data,
                'acknowledged_by': acknowledged_by,
                'acknowledgment_notes': notes,
                'acknowledgment_time': datetime.now(timezone.utc).isoformat()
            }
            
            # Route notification
            channels = await self._route_acknowledgment_notification(ack_data)
            recipients = await self._get_acknowledgment_recipients(ack_data, channels)
            
            # Render template
            content = await self._render_acknowledgment_template(ack_data)
            
            # Send notifications
            delivery_results = await self._send_multi_channel_notification(
                notification_id=notification_id,
                channels=channels,
                recipients=recipients,
                content=content,
                priority=NotificationPriority.NORMAL,
                metadata={'alert_id': alert_data.get('id'), 'type': 'acknowledgment'}
            )
            
            self._track_delivery(notification_id, 'acknowledgment', ack_data, delivery_results)
            
            return {
                'notification_id': notification_id,
                'delivery_results': delivery_results,
                'success': any(r.get('success', False) for r in delivery_results.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send acknowledgment notification: {e}")
            raise
    
    async def send_resolution_notification(self, alert_data: Dict[str, Any],
                                         resolved_by: str,
                                         resolution_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Send alert resolution notification.
        
        Args:
            alert_data: Alert data
            resolved_by: User who resolved
            resolution_notes: Optional resolution notes
            
        Returns:
            Delivery results
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Create resolution content
            resolution_data = {
                **alert_data,
                'resolved_by': resolved_by,
                'resolution_notes': resolution_notes,
                'resolution_time': datetime.now(timezone.utc).isoformat()
            }
            
            # Route notification
            channels = await self._route_resolution_notification(resolution_data)
            recipients = await self._get_resolution_recipients(resolution_data, channels)
            
            # Render template
            content = await self._render_resolution_template(resolution_data)
            
            # Send notifications
            delivery_results = await self._send_multi_channel_notification(
                notification_id=notification_id,
                channels=channels,
                recipients=recipients,
                content=content,
                priority=NotificationPriority.NORMAL,
                metadata={'alert_id': alert_data.get('id'), 'type': 'resolution'}
            )
            
            self._track_delivery(notification_id, 'resolution', resolution_data, delivery_results)
            
            return {
                'notification_id': notification_id,
                'delivery_results': delivery_results,
                'success': any(r.get('success', False) for r in delivery_results.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send resolution notification: {e}")
            raise
    
    async def send_escalation_notification(self, alert_data: Dict[str, Any],
                                         escalation_reason: str) -> Dict[str, Any]:
        """
        Send alert escalation notification.
        
        Args:
            alert_data: Alert data
            escalation_reason: Reason for escalation
            
        Returns:
            Delivery results
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Create escalation content
            escalation_data = {
                **alert_data,
                'escalation_reason': escalation_reason,
                'escalation_time': datetime.now(timezone.utc).isoformat()
            }
            
            # Route notification (escalations typically go to higher-level recipients)
            channels = await self._route_escalation_notification(escalation_data)
            recipients = await self._get_escalation_recipients(escalation_data, channels)
            
            # Render template
            content = await self._render_escalation_template(escalation_data)
            
            # Send notifications with high priority
            delivery_results = await self._send_multi_channel_notification(
                notification_id=notification_id,
                channels=channels,
                recipients=recipients,
                content=content,
                priority=NotificationPriority.URGENT,
                metadata={'alert_id': alert_data.get('id'), 'type': 'escalation'}
            )
            
            self._track_delivery(notification_id, 'escalation', escalation_data, delivery_results)
            
            return {
                'notification_id': notification_id,
                'delivery_results': delivery_results,
                'success': any(r.get('success', False) for r in delivery_results.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send escalation notification: {e}")
            raise
    
    async def send_custom_notification(self, alert_data: Dict[str, Any],
                                     action_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send custom notification based on action configuration.
        
        Args:
            alert_data: Alert data
            action_config: Action configuration
            
        Returns:
            Delivery results
        """
        try:
            notification_id = str(uuid.uuid4())
            
            # Extract configuration
            channels = [NotificationChannel(ch) for ch in action_config.get('channels', ['email'])]
            recipients = action_config.get('recipients', [])
            template = action_config.get('template', 'default_alert')
            priority = NotificationPriority(action_config.get('priority', 'normal'))
            
            # Render content
            content = await self._render_custom_template(alert_data, template, action_config)
            
            # Send notifications
            delivery_results = await self._send_multi_channel_notification(
                notification_id=notification_id,
                channels=channels,
                recipients=recipients,
                content=content,
                priority=priority,
                metadata={'alert_id': alert_data.get('id'), 'type': 'custom'}
            )
            
            self._track_delivery(notification_id, 'custom', alert_data, delivery_results)
            
            return {
                'notification_id': notification_id,
                'delivery_results': delivery_results,
                'success': any(r.get('success', False) for r in delivery_results.values())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send custom notification: {e}")
            raise
    
    async def _send_multi_channel_notification(self, notification_id: str,
                                             channels: List[NotificationChannel],
                                             recipients: List[str],
                                             content: Dict[str, Any],
                                             priority: NotificationPriority,
                                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification across multiple channels."""
        delivery_results = {}
        
        for channel in channels:
            if channel not in self.notifiers:
                self.logger.warning(f"Notifier not available for channel: {channel}")
                continue
            
            try:
                # Check rate limits
                if not await self._check_rate_limit(channel, recipients):
                    delivery_results[channel.value] = {
                        'success': False,
                        'error': 'Rate limit exceeded',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    continue
                
                # Send notification
                notifier = self.notifiers[channel]
                result = await notifier.send_notification(
                    recipients=recipients,
                    content=content,
                    priority=priority,
                    metadata=metadata
                )
                
                delivery_results[channel.value] = {
                    'success': result.get('success', False),
                    'message_id': result.get('message_id'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'recipients_delivered': result.get('recipients_delivered', 0),
                    'error': result.get('error')
                }
                
                # Update rate limits
                await self._update_rate_limit(channel, recipients)
                
            except Exception as e:
                self.logger.error(f"Failed to send notification via {channel.value}: {e}")
                delivery_results[channel.value] = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        
        return delivery_results
    
    async def _route_alert_notification(self, alert_data: Dict[str, Any]) -> List[NotificationChannel]:
        """Route alert notification to appropriate channels."""
        severity = alert_data.get('severity', AlertSeverity.MEDIUM)
        alert_type = alert_data.get('alert_type', 'system')
        
        # Default routing based on severity
        if severity == AlertSeverity.CRITICAL:
            return [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.SLACK]
        elif severity == AlertSeverity.HIGH:
            return [NotificationChannel.EMAIL, NotificationChannel.SLACK]
        elif severity == AlertSeverity.MEDIUM:
            return [NotificationChannel.EMAIL]
        else:
            return [NotificationChannel.EMAIL]
    
    async def _get_alert_recipients(self, alert_data: Dict[str, Any], 
                                  channels: List[NotificationChannel]) -> List[str]:
        """Get recipients for alert notification."""
        # This would typically integrate with user management system
        # For now, return default recipients
        return ['admin@example.com', 'ops-team@example.com']
    
    def _get_alert_template(self, alert_data: Dict[str, Any]) -> str:
        """Get template name for alert."""
        severity = alert_data.get('severity', AlertSeverity.MEDIUM)
        
        if severity == AlertSeverity.CRITICAL:
            return 'critical_alert'
        elif severity == AlertSeverity.HIGH:
            return 'high_alert'
        else:
            return 'default_alert'
    
    def _get_alert_priority(self, alert_data: Dict[str, Any]) -> NotificationPriority:
        """Get notification priority for alert."""
        severity = alert_data.get('severity', AlertSeverity.MEDIUM)
        
        if severity == AlertSeverity.CRITICAL:
            return NotificationPriority.URGENT
        elif severity == AlertSeverity.HIGH:
            return NotificationPriority.HIGH
        else:
            return NotificationPriority.NORMAL
    
    async def _render_alert_template(self, alert_data: Dict[str, Any], 
                                   template_name: str) -> Dict[str, Any]:
        """Render alert notification template."""
        # Simple template rendering - could be enhanced with Jinja2 or similar
        severity_emoji = alert_data.get('severity', AlertSeverity.MEDIUM).emoji
        
        return {
            'subject': f"{severity_emoji} Alert: {alert_data.get('title', 'Unknown Alert')}",
            'body': f"""
Alert Details:
- Title: {alert_data.get('title', 'Unknown')}
- Description: {alert_data.get('description', 'No description')}
- Severity: {alert_data.get('severity', AlertSeverity.MEDIUM).value.upper()}
- Type: {alert_data.get('alert_type', 'system')}
- Device: {alert_data.get('device_id', 'N/A')}
- First Occurred: {alert_data.get('first_occurred', 'Unknown')}
- Status: {alert_data.get('status', AlertStatus.ACTIVE).value.upper()}

Please investigate and take appropriate action.
            """.strip(),
            'html_body': f"""
<h2>{severity_emoji} Alert Notification</h2>
<table>
    <tr><td><strong>Title:</strong></td><td>{alert_data.get('title', 'Unknown')}</td></tr>
    <tr><td><strong>Description:</strong></td><td>{alert_data.get('description', 'No description')}</td></tr>
    <tr><td><strong>Severity:</strong></td><td>{alert_data.get('severity', AlertSeverity.MEDIUM).value.upper()}</td></tr>
    <tr><td><strong>Type:</strong></td><td>{alert_data.get('alert_type', 'system')}</td></tr>
    <tr><td><strong>Device:</strong></td><td>{alert_data.get('device_id', 'N/A')}</td></tr>
    <tr><td><strong>First Occurred:</strong></td><td>{alert_data.get('first_occurred', 'Unknown')}</td></tr>
    <tr><td><strong>Status:</strong></td><td>{alert_data.get('status', AlertStatus.ACTIVE).value.upper()}</td></tr>
</table>
<p>Please investigate and take appropriate action.</p>
            """.strip()
        }
    
    async def _render_acknowledgment_template(self, ack_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render acknowledgment notification template."""
        return {
            'subject': f"✅ Alert Acknowledged: {ack_data.get('title', 'Unknown Alert')}",
            'body': f"""
Alert Acknowledgment:
- Alert: {ack_data.get('title', 'Unknown')}
- Acknowledged by: {ack_data.get('acknowledged_by', 'Unknown')}
- Time: {ack_data.get('acknowledgment_time', 'Unknown')}
- Notes: {ack_data.get('acknowledgment_notes', 'No notes provided')}
            """.strip()
        }
    
    async def _render_resolution_template(self, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render resolution notification template."""
        return {
            'subject': f"✅ Alert Resolved: {resolution_data.get('title', 'Unknown Alert')}",
            'body': f"""
Alert Resolution:
- Alert: {resolution_data.get('title', 'Unknown')}
- Resolved by: {resolution_data.get('resolved_by', 'Unknown')}
- Time: {resolution_data.get('resolution_time', 'Unknown')}
- Notes: {resolution_data.get('resolution_notes', 'No notes provided')}
            """.strip()
        }
    
    async def _render_escalation_template(self, escalation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render escalation notification template."""
        return {
            'subject': f"🚨 Alert Escalated: {escalation_data.get('title', 'Unknown Alert')}",
            'body': f"""
Alert Escalation:
- Alert: {escalation_data.get('title', 'Unknown')}
- Escalation Reason: {escalation_data.get('escalation_reason', 'Unknown')}
- Escalation Level: {escalation_data.get('escalation_level', 1)}
- Time: {escalation_data.get('escalation_time', 'Unknown')}

URGENT: This alert requires immediate attention.
            """.strip()
        }
    
    async def _render_custom_template(self, alert_data: Dict[str, Any], 
                                    template_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Render custom notification template."""
        # Simple custom template rendering
        return {
            'subject': config.get('subject', f"Alert: {alert_data.get('title', 'Unknown')}"),
            'body': config.get('body', f"Alert: {alert_data.get('description', 'No description')}")
        }
    
    # Placeholder methods for other routing functions
    async def _route_acknowledgment_notification(self, ack_data: Dict[str, Any]) -> List[NotificationChannel]:
        return [NotificationChannel.EMAIL]
    
    async def _get_acknowledgment_recipients(self, ack_data: Dict[str, Any], 
                                           channels: List[NotificationChannel]) -> List[str]:
        return ['admin@example.com']
    
    async def _route_resolution_notification(self, resolution_data: Dict[str, Any]) -> List[NotificationChannel]:
        return [NotificationChannel.EMAIL]
    
    async def _get_resolution_recipients(self, resolution_data: Dict[str, Any], 
                                       channels: List[NotificationChannel]) -> List[str]:
        return ['admin@example.com']
    
    async def _route_escalation_notification(self, escalation_data: Dict[str, Any]) -> List[NotificationChannel]:
        return [NotificationChannel.EMAIL, NotificationChannel.SMS]
    
    async def _get_escalation_recipients(self, escalation_data: Dict[str, Any], 
                                       channels: List[NotificationChannel]) -> List[str]:
        return ['admin@example.com', 'manager@example.com']
    
    async def _check_rate_limit(self, channel: NotificationChannel, recipients: List[str]) -> bool:
        """Check if rate limit allows sending."""
        # Simple rate limiting implementation
        return True
    
    async def _update_rate_limit(self, channel: NotificationChannel, recipients: List[str]) -> None:
        """Update rate limit counters."""
        pass
    
    async def _load_default_routing_rules(self) -> None:
        """Load default routing rules."""
        pass
    
    async def _load_notification_templates(self) -> None:
        """Load notification templates."""
        pass
    
    def _track_delivery(self, notification_id: str, notification_type: str, 
                       data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Track notification delivery."""
        self.delivery_history[notification_id] = {
            'notification_id': notification_id,
            'type': notification_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'results': results
        }
        
        # Limit history size
        if len(self.delivery_history) > self.max_history_entries:
            oldest_keys = sorted(self.delivery_history.keys())[:1000]
            for key in oldest_keys:
                del self.delivery_history[key]
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get notification delivery statistics."""
        deliveries = list(self.delivery_history.values())
        
        if not deliveries:
            return {
                'total_notifications': 0,
                'successful_deliveries': 0,
                'failed_deliveries': 0,
                'success_rate': 0.0,
                'channels': {},
                'types': {}
            }
        
        successful = 0
        failed = 0
        channels = {}
        types = {}
        
        for delivery in deliveries:
            results = delivery.get('results', {})
            delivery_type = delivery.get('type', 'unknown')
            
            # Count by type
            types[delivery_type] = types.get(delivery_type, 0) + 1
            
            # Count by channel and success
            for channel, result in results.items():
                channels[channel] = channels.get(channel, {'success': 0, 'failed': 0})
                
                if result.get('success', False):
                    successful += 1
                    channels[channel]['success'] += 1
                else:
                    failed += 1
                    channels[channel]['failed'] += 1
        
        total = successful + failed
        
        return {
            'total_notifications': len(deliveries),
            'total_deliveries': total,
            'successful_deliveries': successful,
            'failed_deliveries': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0.0,
            'channels': channels,
            'types': types
        }
    
    async def shutdown(self) -> None:
        """Shutdown notification service."""
        for notifier in self.notifiers.values():
            try:
                await notifier.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down notifier: {e}")
        
        self.logger.info("Notification service shutdown complete")
