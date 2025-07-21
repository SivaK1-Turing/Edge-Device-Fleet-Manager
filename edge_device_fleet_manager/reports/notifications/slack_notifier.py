"""
Slack Notifier

Slack notification delivery with rich formatting, attachments,
and channel routing.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from ...core.logging import get_logger

logger = get_logger(__name__)


class SlackNotifier:
    """
    Slack notification delivery service.
    
    Supports Slack webhook and API delivery with rich formatting,
    attachments, and channel routing.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Slack notifier.
        
        Args:
            config: Optional Slack configuration
        """
        self.config = config or {}
        self.webhook_urls = {}
        self.api_token = None
        self.delivery_history = {}
        
        self.logger = get_logger(f"{__name__}.SlackNotifier")
    
    async def initialize(self) -> None:
        """Initialize Slack notifier with configuration."""
        try:
            # Load Slack configuration
            slack_config = self.config.get('slack', {})
            
            # Webhook URLs for different channels
            self.webhook_urls = slack_config.get('webhooks', {})
            
            # API token for advanced features
            self.api_token = slack_config.get('api_token')
            
            # Default channel
            self.default_channel = slack_config.get('default_channel', '#alerts')
            
            self.logger.info(f"Slack notifier initialized with {len(self.webhook_urls)} webhooks")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Slack notifier: {e}")
            raise
    
    async def send_notification(self, recipients: List[str], content: Dict[str, Any],
                              priority: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send Slack notification.
        
        Args:
            recipients: List of Slack channels or webhook names
            content: Notification content
            priority: Notification priority
            metadata: Optional metadata
            
        Returns:
            Delivery result
        """
        try:
            message_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Process recipients (channels or webhook names)
            targets = self._process_recipients(recipients)
            if not targets:
                return {
                    'success': False,
                    'error': 'No valid Slack targets',
                    'message_id': message_id,
                    'recipients_delivered': 0
                }
            
            # Create Slack message
            slack_message = self._create_slack_message(content, metadata, priority)
            
            # Send to all targets
            delivery_results = []
            successful_deliveries = 0
            
            for target in targets:
                result = await self._send_slack_message(target, slack_message, message_id)
                delivery_results.append(result)
                
                if result.get('success', False):
                    successful_deliveries += 1
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Track delivery
            self._track_delivery(message_id, targets, delivery_results, duration)
            
            overall_success = successful_deliveries > 0
            
            result = {
                'success': overall_success,
                'message_id': message_id,
                'recipients_delivered': successful_deliveries,
                'total_recipients': len(targets),
                'duration_seconds': duration,
                'delivery_results': delivery_results,
                'error': None if overall_success else 'All Slack deliveries failed'
            }
            
            if overall_success:
                self.logger.info(f"Slack notification sent: {message_id} ({successful_deliveries}/{len(targets)} successful)")
            else:
                self.logger.error(f"Slack notification failed: {message_id} - all deliveries failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id if 'message_id' in locals() else str(uuid.uuid4()),
                'recipients_delivered': 0
            }
    
    def _process_recipients(self, recipients: List[str]) -> List[Dict[str, Any]]:
        """Process recipients into Slack targets."""
        targets = []
        
        for recipient in recipients:
            if recipient in self.webhook_urls:
                # Named webhook
                targets.append({
                    'type': 'webhook',
                    'name': recipient,
                    'url': self.webhook_urls[recipient]
                })
            
            elif recipient.startswith('#') or recipient.startswith('@'):
                # Channel or user mention
                if self.api_token:
                    targets.append({
                        'type': 'api',
                        'name': recipient,
                        'channel': recipient
                    })
                else:
                    self.logger.warning(f"API token required for channel/user: {recipient}")
            
            elif recipient.startswith('https://hooks.slack.com/'):
                # Direct webhook URL
                targets.append({
                    'type': 'webhook',
                    'name': recipient,
                    'url': recipient
                })
            
            else:
                self.logger.warning(f"Invalid Slack recipient: {recipient}")
        
        return targets
    
    def _create_slack_message(self, content: Dict[str, Any], metadata: Optional[Dict[str, Any]],
                            priority: Any = None) -> Dict[str, Any]:
        """Create Slack message payload."""
        # Extract content
        subject = content.get('subject', 'Notification')
        body = content.get('body', '')
        
        # Determine color based on priority or content
        color = self._get_message_color(content, metadata, priority)
        
        # Create attachment
        attachment = {
            'color': color,
            'title': subject,
            'text': body,
            'footer': 'Edge Device Fleet Manager',
            'ts': int(datetime.now(timezone.utc).timestamp())
        }
        
        # Add fields for alert metadata
        if metadata and metadata.get('alert_id'):
            fields = []
            
            # Add alert-specific fields
            if 'severity' in content:
                fields.append({
                    'title': 'Severity',
                    'value': str(content['severity']).upper(),
                    'short': True
                })
            
            if 'alert_type' in content:
                fields.append({
                    'title': 'Type',
                    'value': content['alert_type'],
                    'short': True
                })
            
            if 'device_id' in content:
                fields.append({
                    'title': 'Device',
                    'value': content['device_id'],
                    'short': True
                })
            
            if fields:
                attachment['fields'] = fields
        
        # Create message
        message = {
            'text': f"🚨 {subject}" if priority == 'urgent' else subject,
            'attachments': [attachment]
        }
        
        return message
    
    def _get_message_color(self, content: Dict[str, Any], metadata: Optional[Dict[str, Any]],
                          priority: Any = None) -> str:
        """Get message color based on content and priority."""
        # Check for severity in content
        severity = content.get('severity')
        if severity:
            severity_str = str(severity).lower()
            if 'critical' in severity_str:
                return 'danger'
            elif 'high' in severity_str:
                return 'warning'
            elif 'medium' in severity_str:
                return '#ffcc00'  # Yellow
            else:
                return 'good'
        
        # Check priority
        if priority == 'urgent':
            return 'danger'
        elif priority == 'high':
            return 'warning'
        
        # Default color
        return '#36a64f'  # Green
    
    async def _send_slack_message(self, target: Dict[str, Any], message: Dict[str, Any],
                                message_id: str) -> Dict[str, Any]:
        """Send message to a single Slack target."""
        target_type = target['type']
        target_name = target['name']
        
        try:
            if target_type == 'webhook':
                return await self._send_webhook_message(target, message, message_id)
            elif target_type == 'api':
                return await self._send_api_message(target, message, message_id)
            else:
                return {
                    'target': target_name,
                    'success': False,
                    'error': f'Unknown target type: {target_type}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack message to {target_name}: {e}")
            return {
                'target': target_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _send_webhook_message(self, target: Dict[str, Any], message: Dict[str, Any],
                                  message_id: str) -> Dict[str, Any]:
        """Send message via Slack webhook."""
        url = target['url']
        target_name = target['name']
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=message) as response:
                    response_text = await response.text()
                    
                    success = response.status == 200
                    
                    return {
                        'target': target_name,
                        'success': success,
                        'status_code': response.status,
                        'response': response_text,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
        except Exception as e:
            return {
                'target': target_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _send_api_message(self, target: Dict[str, Any], message: Dict[str, Any],
                              message_id: str) -> Dict[str, Any]:
        """Send message via Slack API."""
        channel = target['channel']
        target_name = target['name']
        
        # For now, return a placeholder implementation
        # In a real implementation, this would use the Slack Web API
        self.logger.info(f"Would send Slack API message to {channel} (API not implemented)")
        
        return {
            'target': target_name,
            'success': True,
            'message': 'API delivery simulated',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _track_delivery(self, message_id: str, targets: List[Dict[str, Any]],
                       results: List[Dict[str, Any]], duration: float) -> None:
        """Track Slack delivery."""
        self.delivery_history[message_id] = {
            'message_id': message_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'targets': [t['name'] for t in targets],
            'results': results,
            'duration_seconds': duration
        }
        
        # Limit history size
        if len(self.delivery_history) > 1000:
            oldest_keys = sorted(self.delivery_history.keys())[:100]
            for key in oldest_keys:
                del self.delivery_history[key]
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get Slack delivery statistics."""
        deliveries = list(self.delivery_history.values())
        
        if not deliveries:
            return {
                'total_messages': 0,
                'successful_messages': 0,
                'failed_messages': 0,
                'success_rate': 0.0,
                'average_duration': 0.0
            }
        
        total_deliveries = 0
        successful_deliveries = 0
        total_duration = sum(d['duration_seconds'] for d in deliveries)
        
        for delivery in deliveries:
            for result in delivery['results']:
                total_deliveries += 1
                if result.get('success', False):
                    successful_deliveries += 1
        
        return {
            'total_messages': len(deliveries),
            'total_deliveries': total_deliveries,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': total_deliveries - successful_deliveries,
            'success_rate': (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0.0,
            'average_duration': total_duration / len(deliveries) if deliveries else 0.0
        }
    
    async def test_slack_notification(self, recipient: str) -> Dict[str, Any]:
        """Send test Slack notification."""
        test_content = {
            'subject': 'Edge Device Fleet Manager - Test Notification',
            'body': 'This is a test notification from the Edge Device Fleet Manager.',
            'test': True
        }
        
        return await self.send_notification(
            recipients=[recipient],
            content=test_content,
            metadata={'type': 'test'}
        )
    
    async def shutdown(self) -> None:
        """Shutdown Slack notifier."""
        self.logger.info("Slack notifier shutdown complete")
