"""
Webhook Notifier

HTTP webhook notification delivery with retry logic, authentication,
and payload customization.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import hashlib
import hmac

from ...core.logging import get_logger

logger = get_logger(__name__)


class WebhookNotifier:
    """
    Webhook notification delivery service.
    
    Supports HTTP POST webhooks with authentication, retry logic,
    and payload customization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize webhook notifier.
        
        Args:
            config: Optional webhook configuration
        """
        self.config = config or {}
        self.webhooks = {}
        self.delivery_history = {}
        
        # Default configuration
        self.default_timeout = 30
        self.default_retry_attempts = 3
        self.default_retry_delay = 5
        
        self.logger = get_logger(f"{__name__}.WebhookNotifier")
    
    async def initialize(self) -> None:
        """Initialize webhook notifier with configuration."""
        try:
            # Load webhook configurations
            webhooks_config = self.config.get('webhooks', {})
            
            for name, webhook_config in webhooks_config.items():
                self.webhooks[name] = {
                    'url': webhook_config['url'],
                    'method': webhook_config.get('method', 'POST'),
                    'headers': webhook_config.get('headers', {}),
                    'auth_type': webhook_config.get('auth_type'),
                    'auth_config': webhook_config.get('auth_config', {}),
                    'timeout': webhook_config.get('timeout', self.default_timeout),
                    'retry_attempts': webhook_config.get('retry_attempts', self.default_retry_attempts),
                    'retry_delay': webhook_config.get('retry_delay', self.default_retry_delay),
                    'payload_template': webhook_config.get('payload_template'),
                    'enabled': webhook_config.get('enabled', True)
                }
            
            self.logger.info(f"Webhook notifier initialized with {len(self.webhooks)} webhooks")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize webhook notifier: {e}")
            raise
    
    async def send_notification(self, recipients: List[str], content: Dict[str, Any],
                              priority: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send webhook notification.
        
        Args:
            recipients: List of webhook names or URLs
            content: Notification content
            priority: Notification priority
            metadata: Optional metadata
            
        Returns:
            Delivery result
        """
        try:
            message_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Process recipients
            webhook_targets = self._process_recipients(recipients)
            if not webhook_targets:
                return {
                    'success': False,
                    'error': 'No valid webhook targets',
                    'message_id': message_id,
                    'recipients_delivered': 0
                }
            
            # Send to all webhook targets
            delivery_results = []
            successful_deliveries = 0
            
            for target in webhook_targets:
                result = await self._send_webhook(target, content, metadata, message_id)
                delivery_results.append(result)
                
                if result.get('success', False):
                    successful_deliveries += 1
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Track delivery
            self._track_delivery(message_id, webhook_targets, delivery_results, duration)
            
            overall_success = successful_deliveries > 0
            
            result = {
                'success': overall_success,
                'message_id': message_id,
                'recipients_delivered': successful_deliveries,
                'total_recipients': len(webhook_targets),
                'duration_seconds': duration,
                'delivery_results': delivery_results,
                'error': None if overall_success else 'All webhook deliveries failed'
            }
            
            if overall_success:
                self.logger.info(f"Webhook notification sent: {message_id} ({successful_deliveries}/{len(webhook_targets)} successful)")
            else:
                self.logger.error(f"Webhook notification failed: {message_id} - all deliveries failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id if 'message_id' in locals() else str(uuid.uuid4()),
                'recipients_delivered': 0
            }
    
    def _process_recipients(self, recipients: List[str]) -> List[Dict[str, Any]]:
        """Process recipients into webhook targets."""
        targets = []
        
        for recipient in recipients:
            if recipient in self.webhooks:
                # Named webhook configuration
                webhook_config = self.webhooks[recipient]
                if webhook_config.get('enabled', True):
                    targets.append({
                        'name': recipient,
                        'config': webhook_config
                    })
                else:
                    self.logger.warning(f"Webhook disabled: {recipient}")
            
            elif recipient.startswith(('http://', 'https://')):
                # Direct URL
                targets.append({
                    'name': recipient,
                    'config': {
                        'url': recipient,
                        'method': 'POST',
                        'headers': {},
                        'timeout': self.default_timeout,
                        'retry_attempts': self.default_retry_attempts,
                        'retry_delay': self.default_retry_delay
                    }
                })
            
            else:
                self.logger.warning(f"Invalid webhook recipient: {recipient}")
        
        return targets
    
    async def _send_webhook(self, target: Dict[str, Any], content: Dict[str, Any],
                          metadata: Optional[Dict[str, Any]], message_id: str) -> Dict[str, Any]:
        """Send webhook to a single target."""
        config = target['config']
        target_name = target['name']
        
        try:
            # Create payload
            payload = await self._create_payload(content, metadata, config, message_id)
            
            # Prepare headers
            headers = config.get('headers', {}).copy()
            headers['Content-Type'] = 'application/json'
            headers['User-Agent'] = 'EdgeDeviceFleetManager-Webhook/1.0'
            headers['X-Message-ID'] = message_id
            
            # Add authentication
            await self._add_authentication(headers, payload, config)
            
            # Send with retry logic
            result = await self._send_with_retry(
                url=config['url'],
                method=config.get('method', 'POST'),
                payload=payload,
                headers=headers,
                timeout=config.get('timeout', self.default_timeout),
                retry_attempts=config.get('retry_attempts', self.default_retry_attempts),
                retry_delay=config.get('retry_delay', self.default_retry_delay)
            )
            
            return {
                'target': target_name,
                'success': result.get('success', False),
                'status_code': result.get('status_code'),
                'response': result.get('response'),
                'error': result.get('error'),
                'attempts': result.get('attempts', 1),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook to {target_name}: {e}")
            return {
                'target': target_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _create_payload(self, content: Dict[str, Any], metadata: Optional[Dict[str, Any]],
                            config: Dict[str, Any], message_id: str) -> Dict[str, Any]:
        """Create webhook payload."""
        # Default payload structure
        payload = {
            'message_id': message_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'edge-device-fleet-manager',
            'content': content,
            'metadata': metadata or {}
        }
        
        # Apply custom template if configured
        template = config.get('payload_template')
        if template:
            try:
                # Simple template substitution
                if isinstance(template, dict):
                    payload.update(template)
                elif isinstance(template, str):
                    # JSON template
                    template_data = json.loads(template)
                    payload.update(template_data)
            except Exception as e:
                self.logger.warning(f"Failed to apply payload template: {e}")
        
        return payload
    
    async def _add_authentication(self, headers: Dict[str, str], payload: Dict[str, Any],
                                config: Dict[str, Any]) -> None:
        """Add authentication to webhook request."""
        auth_type = config.get('auth_type')
        auth_config = config.get('auth_config', {})
        
        if auth_type == 'bearer':
            token = auth_config.get('token')
            if token:
                headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'api_key':
            api_key = auth_config.get('api_key')
            header_name = auth_config.get('header_name', 'X-API-Key')
            if api_key:
                headers[header_name] = api_key
        
        elif auth_type == 'hmac':
            secret = auth_config.get('secret')
            algorithm = auth_config.get('algorithm', 'sha256')
            header_name = auth_config.get('header_name', 'X-Signature')
            
            if secret:
                payload_str = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    secret.encode('utf-8'),
                    payload_str.encode('utf-8'),
                    getattr(hashlib, algorithm)
                ).hexdigest()
                headers[header_name] = f'{algorithm}={signature}'
        
        elif auth_type == 'basic':
            username = auth_config.get('username')
            password = auth_config.get('password')
            if username and password:
                import base64
                credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'
    
    async def _send_with_retry(self, url: str, method: str, payload: Dict[str, Any],
                             headers: Dict[str, str], timeout: int,
                             retry_attempts: int, retry_delay: int) -> Dict[str, Any]:
        """Send webhook with retry logic."""
        last_error = None
        
        for attempt in range(retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                    async with session.request(
                        method=method,
                        url=url,
                        json=payload,
                        headers=headers
                    ) as response:
                        
                        response_text = await response.text()
                        
                        # Consider 2xx status codes as success
                        success = 200 <= response.status < 300
                        
                        return {
                            'success': success,
                            'status_code': response.status,
                            'response': response_text,
                            'attempts': attempt + 1,
                            'error': None if success else f'HTTP {response.status}: {response_text}'
                        }
            
            except asyncio.TimeoutError:
                last_error = f'Timeout after {timeout} seconds'
                self.logger.warning(f"Webhook timeout (attempt {attempt + 1}/{retry_attempts}): {url}")
            
            except aiohttp.ClientError as e:
                last_error = f'Client error: {e}'
                self.logger.warning(f"Webhook client error (attempt {attempt + 1}/{retry_attempts}): {e}")
            
            except Exception as e:
                last_error = f'Unexpected error: {e}'
                self.logger.warning(f"Webhook error (attempt {attempt + 1}/{retry_attempts}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < retry_attempts - 1:
                await asyncio.sleep(retry_delay)
        
        return {
            'success': False,
            'error': last_error,
            'attempts': retry_attempts
        }
    
    def _track_delivery(self, message_id: str, targets: List[Dict[str, Any]],
                       results: List[Dict[str, Any]], duration: float) -> None:
        """Track webhook delivery."""
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
        """Get webhook delivery statistics."""
        deliveries = list(self.delivery_history.values())
        
        if not deliveries:
            return {
                'total_webhooks': 0,
                'successful_webhooks': 0,
                'failed_webhooks': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'target_statistics': {}
            }
        
        total_deliveries = 0
        successful_deliveries = 0
        total_duration = 0
        target_stats = {}
        
        for delivery in deliveries:
            total_duration += delivery['duration_seconds']
            
            for result in delivery['results']:
                total_deliveries += 1
                target = result['target']
                
                if target not in target_stats:
                    target_stats[target] = {'success': 0, 'failed': 0}
                
                if result.get('success', False):
                    successful_deliveries += 1
                    target_stats[target]['success'] += 1
                else:
                    target_stats[target]['failed'] += 1
        
        return {
            'total_webhooks': len(deliveries),
            'total_deliveries': total_deliveries,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': total_deliveries - successful_deliveries,
            'success_rate': (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0.0,
            'average_duration': total_duration / len(deliveries) if deliveries else 0.0,
            'target_statistics': target_stats
        }
    
    async def test_webhook(self, webhook_name_or_url: str) -> Dict[str, Any]:
        """Test webhook delivery."""
        test_content = {
            'subject': 'Edge Device Fleet Manager - Test Webhook',
            'body': 'This is a test webhook from the Edge Device Fleet Manager notification system.',
            'test': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return await self.send_notification(
            recipients=[webhook_name_or_url],
            content=test_content,
            metadata={'type': 'test'}
        )
    
    async def shutdown(self) -> None:
        """Shutdown webhook notifier."""
        self.logger.info("Webhook notifier shutdown complete")
