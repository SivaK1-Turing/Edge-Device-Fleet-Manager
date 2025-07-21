"""
SMS Notifier

SMS notification delivery with multiple provider support,
message formatting, and delivery tracking.
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import re

from ...core.logging import get_logger

logger = get_logger(__name__)


class SMSNotifier:
    """
    SMS notification delivery service.
    
    Supports multiple SMS providers with message formatting,
    delivery tracking, and phone number validation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SMS notifier.
        
        Args:
            config: Optional SMS configuration
        """
        self.config = config or {}
        self.provider_config = {}
        self.delivery_history = {}
        
        # Message limits
        self.max_message_length = 160
        self.max_long_message_length = 1600
        
        self.logger = get_logger(f"{__name__}.SMSNotifier")
    
    async def initialize(self) -> None:
        """Initialize SMS notifier with configuration."""
        try:
            # Load SMS provider configuration
            sms_config = self.config.get('sms', {})
            
            # Provider configuration
            self.provider_config = {
                'provider': sms_config.get('provider', 'twilio'),
                'account_sid': sms_config.get('account_sid'),
                'auth_token': sms_config.get('auth_token'),
                'from_number': sms_config.get('from_number'),
                'api_url': sms_config.get('api_url'),
                'api_key': sms_config.get('api_key')
            }
            
            # Message configuration
            self.max_message_length = sms_config.get('max_message_length', 160)
            
            self.logger.info(f"SMS notifier initialized with provider: {self.provider_config['provider']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SMS notifier: {e}")
            raise
    
    async def send_notification(self, recipients: List[str], content: Dict[str, Any],
                              priority: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send SMS notification.
        
        Args:
            recipients: List of phone numbers
            content: Notification content
            priority: Notification priority
            metadata: Optional metadata
            
        Returns:
            Delivery result
        """
        try:
            message_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Validate and format phone numbers
            valid_numbers = self._validate_phone_numbers(recipients)
            if not valid_numbers:
                return {
                    'success': False,
                    'error': 'No valid phone numbers',
                    'message_id': message_id,
                    'recipients_delivered': 0
                }
            
            # Create SMS message
            sms_message = self._create_sms_message(content, metadata, priority)
            
            # Send to all numbers
            delivery_results = []
            successful_deliveries = 0
            
            for phone_number in valid_numbers:
                result = await self._send_sms(phone_number, sms_message, message_id)
                delivery_results.append(result)
                
                if result.get('success', False):
                    successful_deliveries += 1
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Track delivery
            self._track_delivery(message_id, valid_numbers, delivery_results, duration)
            
            overall_success = successful_deliveries > 0
            
            result = {
                'success': overall_success,
                'message_id': message_id,
                'recipients_delivered': successful_deliveries,
                'total_recipients': len(valid_numbers),
                'duration_seconds': duration,
                'delivery_results': delivery_results,
                'error': None if overall_success else 'All SMS deliveries failed'
            }
            
            if overall_success:
                self.logger.info(f"SMS notification sent: {message_id} ({successful_deliveries}/{len(valid_numbers)} successful)")
            else:
                self.logger.error(f"SMS notification failed: {message_id} - all deliveries failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send SMS notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id if 'message_id' in locals() else str(uuid.uuid4()),
                'recipients_delivered': 0
            }
    
    def _validate_phone_numbers(self, phone_numbers: List[str]) -> List[str]:
        """Validate and format phone numbers."""
        valid_numbers = []
        
        # Simple phone number regex (international format)
        phone_pattern = re.compile(r'^\+?[1-9]\d{1,14}$')
        
        for number in phone_numbers:
            # Clean the number
            cleaned = re.sub(r'[^\d+]', '', str(number))
            
            # Add + if missing and number doesn't start with +
            if not cleaned.startswith('+') and len(cleaned) >= 10:
                cleaned = '+' + cleaned
            
            # Validate format
            if phone_pattern.match(cleaned):
                valid_numbers.append(cleaned)
            else:
                self.logger.warning(f"Invalid phone number: {number}")
        
        return valid_numbers
    
    def _create_sms_message(self, content: Dict[str, Any], metadata: Optional[Dict[str, Any]],
                          priority: Any = None) -> str:
        """Create SMS message text."""
        # Extract content
        subject = content.get('subject', '')
        body = content.get('body', '')
        
        # Create message
        if subject and body:
            message = f"{subject}\n\n{body}"
        elif subject:
            message = subject
        elif body:
            message = body
        else:
            message = "Alert notification"
        
        # Add priority indicator
        if priority == 'urgent':
            message = f"🚨 URGENT: {message}"
        elif priority == 'high':
            message = f"⚠️ HIGH: {message}"
        
        # Truncate if too long
        if len(message) > self.max_message_length:
            # Try to fit in single SMS
            truncated = message[:self.max_message_length - 3] + "..."
            message = truncated
        
        return message
    
    async def _send_sms(self, phone_number: str, message: str, message_id: str) -> Dict[str, Any]:
        """Send SMS to a single phone number."""
        provider = self.provider_config.get('provider', 'twilio')
        
        try:
            if provider == 'twilio':
                return await self._send_twilio_sms(phone_number, message, message_id)
            elif provider == 'aws_sns':
                return await self._send_aws_sns_sms(phone_number, message, message_id)
            elif provider == 'custom':
                return await self._send_custom_sms(phone_number, message, message_id)
            else:
                return {
                    'phone_number': phone_number,
                    'success': False,
                    'error': f'Unknown SMS provider: {provider}',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return {
                'phone_number': phone_number,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _send_twilio_sms(self, phone_number: str, message: str, message_id: str) -> Dict[str, Any]:
        """Send SMS via Twilio API."""
        # For now, simulate Twilio SMS sending
        # In a real implementation, this would use the Twilio API
        
        account_sid = self.provider_config.get('account_sid')
        auth_token = self.provider_config.get('auth_token')
        from_number = self.provider_config.get('from_number')
        
        if not all([account_sid, auth_token, from_number]):
            return {
                'phone_number': phone_number,
                'success': False,
                'error': 'Missing Twilio configuration',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Simulate API call
        self.logger.info(f"Would send Twilio SMS to {phone_number}: {message[:50]}...")
        
        return {
            'phone_number': phone_number,
            'success': True,
            'provider': 'twilio',
            'message_sid': f'SM{uuid.uuid4().hex[:32]}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _send_aws_sns_sms(self, phone_number: str, message: str, message_id: str) -> Dict[str, Any]:
        """Send SMS via AWS SNS."""
        # For now, simulate AWS SNS SMS sending
        # In a real implementation, this would use boto3 and AWS SNS
        
        self.logger.info(f"Would send AWS SNS SMS to {phone_number}: {message[:50]}...")
        
        return {
            'phone_number': phone_number,
            'success': True,
            'provider': 'aws_sns',
            'message_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _send_custom_sms(self, phone_number: str, message: str, message_id: str) -> Dict[str, Any]:
        """Send SMS via custom API."""
        api_url = self.provider_config.get('api_url')
        api_key = self.provider_config.get('api_key')
        
        if not api_url:
            return {
                'phone_number': phone_number,
                'success': False,
                'error': 'Missing custom API URL',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Prepare payload
            payload = {
                'to': phone_number,
                'message': message,
                'from': self.provider_config.get('from_number', 'EdgeFleetManager')
            }
            
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    success = 200 <= response.status < 300
                    
                    return {
                        'phone_number': phone_number,
                        'success': success,
                        'provider': 'custom',
                        'status_code': response.status,
                        'response': response_text,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
        except Exception as e:
            return {
                'phone_number': phone_number,
                'success': False,
                'provider': 'custom',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _track_delivery(self, message_id: str, phone_numbers: List[str],
                       results: List[Dict[str, Any]], duration: float) -> None:
        """Track SMS delivery."""
        self.delivery_history[message_id] = {
            'message_id': message_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'phone_numbers': phone_numbers,
            'results': results,
            'duration_seconds': duration
        }
        
        # Limit history size
        if len(self.delivery_history) > 1000:
            oldest_keys = sorted(self.delivery_history.keys())[:100]
            for key in oldest_keys:
                del self.delivery_history[key]
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get SMS delivery statistics."""
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
    
    async def test_sms_notification(self, phone_number: str) -> Dict[str, Any]:
        """Send test SMS notification."""
        test_content = {
            'subject': 'Test SMS',
            'body': 'This is a test SMS from Edge Device Fleet Manager.'
        }
        
        return await self.send_notification(
            recipients=[phone_number],
            content=test_content,
            metadata={'type': 'test'}
        )
    
    async def shutdown(self) -> None:
        """Shutdown SMS notifier."""
        self.logger.info("SMS notifier shutdown complete")
