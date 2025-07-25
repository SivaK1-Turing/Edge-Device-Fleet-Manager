"""
Email Notifier

Email notification delivery with SMTP support, HTML/text formatting,
attachments, and delivery tracking.
"""

import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
from pathlib import Path

from ...core.logging import get_logger
from ...core.config import get_config

logger = get_logger(__name__)


class EmailNotifier:
    """
    Email notification delivery service.
    
    Supports SMTP delivery with HTML/text formatting, attachments,
    and delivery tracking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize email notifier.
        
        Args:
            config: Optional email configuration
        """
        self.config = config or {}
        self.smtp_config = {}
        self.default_sender = None
        self.delivery_history = {}
        
        self.logger = get_logger(f"{__name__}.EmailNotifier")
    
    async def initialize(self) -> None:
        """Initialize email notifier with configuration."""
        try:
            # Load configuration
            app_config = get_config()
            email_config = app_config.get('notifications', {}).get('email', {})
            
            # Merge with provided config
            self.config.update(email_config)
            
            # Extract SMTP configuration
            self.smtp_config = {
                'host': self.config.get('smtp_host', 'localhost'),
                'port': self.config.get('smtp_port', 587),
                'username': self.config.get('smtp_username'),
                'password': self.config.get('smtp_password'),
                'use_tls': self.config.get('smtp_use_tls', True),
                'use_ssl': self.config.get('smtp_use_ssl', False),
                'timeout': self.config.get('smtp_timeout', 30)
            }
            
            # Default sender
            self.default_sender = self.config.get('default_sender', 'noreply@example.com')
            
            # Test connection if enabled
            if self.config.get('test_connection_on_init', False):
                await self._test_smtp_connection()
            
            self.logger.info("Email notifier initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize email notifier: {e}")
            raise
    
    async def send_notification(self, recipients: List[str], content: Dict[str, Any],
                              priority: Any = None, metadata: Optional[Dict[str, Any]] = None,
                              attachments: Optional[List[str]] = None,
                              sender: Optional[str] = None) -> Dict[str, Any]:
        """
        Send email notification.
        
        Args:
            recipients: List of email addresses
            content: Email content with subject, body, html_body
            priority: Notification priority (unused for email)
            metadata: Optional metadata
            attachments: Optional list of file paths to attach
            sender: Optional sender email address
            
        Returns:
            Delivery result
        """
        try:
            message_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Validate recipients
            valid_recipients = self._validate_recipients(recipients)
            if not valid_recipients:
                return {
                    'success': False,
                    'error': 'No valid recipients',
                    'message_id': message_id,
                    'recipients_delivered': 0
                }
            
            # Create email message
            message = await self._create_email_message(
                recipients=valid_recipients,
                content=content,
                sender=sender or self.default_sender,
                attachments=attachments,
                metadata=metadata
            )
            
            # Send email
            delivery_result = await self._send_email(message, valid_recipients)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Track delivery
            self._track_delivery(message_id, valid_recipients, delivery_result, duration)
            
            result = {
                'success': delivery_result.get('success', False),
                'message_id': message_id,
                'recipients_delivered': delivery_result.get('recipients_delivered', 0),
                'duration_seconds': duration,
                'error': delivery_result.get('error')
            }
            
            if result['success']:
                self.logger.info(f"Email sent successfully: {message_id} to {len(valid_recipients)} recipients")
            else:
                self.logger.error(f"Email delivery failed: {message_id} - {result['error']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return {
                'success': False,
                'error': str(e),
                'message_id': message_id if 'message_id' in locals() else str(uuid.uuid4()),
                'recipients_delivered': 0
            }
    
    def _validate_recipients(self, recipients: List[str]) -> List[str]:
        """Validate email addresses."""
        import re
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        valid_recipients = []
        
        for recipient in recipients:
            if isinstance(recipient, str) and email_pattern.match(recipient.strip()):
                valid_recipients.append(recipient.strip())
            else:
                self.logger.warning(f"Invalid email address: {recipient}")
        
        return valid_recipients
    
    async def _create_email_message(self, recipients: List[str], content: Dict[str, Any],
                                   sender: str, attachments: Optional[List[str]] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> MIMEMultipart:
        """Create email message."""
        # Create message
        message = MIMEMultipart('alternative')
        
        # Set headers
        message['From'] = sender
        message['To'] = ', '.join(recipients)
        message['Subject'] = content.get('subject', 'Notification')
        message['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Add custom headers
        if metadata:
            alert_id = metadata.get('alert_id')
            if alert_id:
                message['X-Alert-ID'] = alert_id
            
            notification_type = metadata.get('type')
            if notification_type:
                message['X-Notification-Type'] = notification_type
        
        # Add message ID
        message['Message-ID'] = f"<{uuid.uuid4()}@{sender.split('@')[1]}>"
        
        # Add text content
        text_body = content.get('body', '')
        if text_body:
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            message.attach(text_part)
        
        # Add HTML content
        html_body = content.get('html_body', '')
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
        elif text_body:
            # Convert text to simple HTML
            html_body = text_body.replace('\n', '<br>\n')
            html_part = MIMEText(f'<html><body><pre>{html_body}</pre></body></html>', 'html', 'utf-8')
            message.attach(html_part)
        
        # Add attachments
        if attachments:
            await self._add_attachments(message, attachments)
        
        return message
    
    async def _add_attachments(self, message: MIMEMultipart, attachments: List[str]) -> None:
        """Add file attachments to email."""
        for attachment_path in attachments:
            try:
                path = Path(attachment_path)
                if not path.exists():
                    self.logger.warning(f"Attachment file not found: {attachment_path}")
                    continue
                
                # Read file
                with open(path, 'rb') as f:
                    attachment_data = f.read()
                
                # Create attachment
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(attachment_data)
                encoders.encode_base64(attachment)
                
                # Add header
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {path.name}'
                )
                
                message.attach(attachment)
                self.logger.debug(f"Added attachment: {path.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to add attachment {attachment_path}: {e}")
    
    async def _send_email(self, message: MIMEMultipart, recipients: List[str]) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Create SMTP connection
            if self.smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(
                    self.smtp_config['host'],
                    self.smtp_config['port'],
                    timeout=self.smtp_config['timeout']
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_config['host'],
                    self.smtp_config['port'],
                    timeout=self.smtp_config['timeout']
                )
                
                if self.smtp_config['use_tls']:
                    server.starttls()
            
            # Authenticate if credentials provided
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            
            # Send email
            sender = message['From']
            failed_recipients = server.sendmail(sender, recipients, message.as_string())
            
            # Close connection
            server.quit()
            
            # Calculate success
            successful_recipients = len(recipients) - len(failed_recipients)
            
            if failed_recipients:
                self.logger.warning(f"Failed to deliver to some recipients: {failed_recipients}")
            
            return {
                'success': successful_recipients > 0,
                'recipients_delivered': successful_recipients,
                'failed_recipients': failed_recipients,
                'error': f"Failed recipients: {failed_recipients}" if failed_recipients else None
            }
            
        except smtplib.SMTPAuthenticationError as e:
            return {
                'success': False,
                'recipients_delivered': 0,
                'error': f"SMTP authentication failed: {e}"
            }
        
        except smtplib.SMTPRecipientsRefused as e:
            return {
                'success': False,
                'recipients_delivered': 0,
                'error': f"All recipients refused: {e}"
            }
        
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'recipients_delivered': 0,
                'error': f"SMTP error: {e}"
            }
        
        except Exception as e:
            return {
                'success': False,
                'recipients_delivered': 0,
                'error': f"Email delivery error: {e}"
            }
    
    async def _test_smtp_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            if self.smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(
                    self.smtp_config['host'],
                    self.smtp_config['port'],
                    timeout=self.smtp_config['timeout']
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_config['host'],
                    self.smtp_config['port'],
                    timeout=self.smtp_config['timeout']
                )
                
                if self.smtp_config['use_tls']:
                    server.starttls()
            
            # Test authentication if credentials provided
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            
            server.quit()
            self.logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def _track_delivery(self, message_id: str, recipients: List[str], 
                       result: Dict[str, Any], duration: float) -> None:
        """Track email delivery."""
        self.delivery_history[message_id] = {
            'message_id': message_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recipients': recipients,
            'result': result,
            'duration_seconds': duration
        }
        
        # Limit history size
        if len(self.delivery_history) > 1000:
            oldest_keys = sorted(self.delivery_history.keys())[:100]
            for key in oldest_keys:
                del self.delivery_history[key]
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get email delivery statistics."""
        deliveries = list(self.delivery_history.values())
        
        if not deliveries:
            return {
                'total_emails': 0,
                'successful_emails': 0,
                'failed_emails': 0,
                'success_rate': 0.0,
                'total_recipients': 0,
                'average_duration': 0.0
            }
        
        successful = len([d for d in deliveries if d['result'].get('success', False)])
        failed = len(deliveries) - successful
        total_recipients = sum(len(d['recipients']) for d in deliveries)
        total_duration = sum(d['duration_seconds'] for d in deliveries)
        
        return {
            'total_emails': len(deliveries),
            'successful_emails': successful,
            'failed_emails': failed,
            'success_rate': (successful / len(deliveries) * 100) if deliveries else 0.0,
            'total_recipients': total_recipients,
            'average_duration': total_duration / len(deliveries) if deliveries else 0.0
        }
    
    async def send_test_email(self, recipient: str) -> Dict[str, Any]:
        """Send test email to verify configuration."""
        test_content = {
            'subject': 'Edge Device Fleet Manager - Test Email',
            'body': '''
This is a test email from the Edge Device Fleet Manager notification system.

If you received this email, the email notification configuration is working correctly.

Test Details:
- Timestamp: {timestamp}
- SMTP Host: {host}
- SMTP Port: {port}
- TLS Enabled: {tls}

Best regards,
Edge Device Fleet Manager
            '''.format(
                timestamp=datetime.now(timezone.utc).isoformat(),
                host=self.smtp_config['host'],
                port=self.smtp_config['port'],
                tls=self.smtp_config['use_tls']
            ).strip(),
            'html_body': '''
<html>
<body>
    <h2>Edge Device Fleet Manager - Test Email</h2>
    <p>This is a test email from the Edge Device Fleet Manager notification system.</p>
    <p>If you received this email, the email notification configuration is working correctly.</p>
    
    <h3>Test Details:</h3>
    <ul>
        <li><strong>Timestamp:</strong> {timestamp}</li>
        <li><strong>SMTP Host:</strong> {host}</li>
        <li><strong>SMTP Port:</strong> {port}</li>
        <li><strong>TLS Enabled:</strong> {tls}</li>
    </ul>
    
    <p>Best regards,<br>Edge Device Fleet Manager</p>
</body>
</html>
            '''.format(
                timestamp=datetime.now(timezone.utc).isoformat(),
                host=self.smtp_config['host'],
                port=self.smtp_config['port'],
                tls=self.smtp_config['use_tls']
            ).strip()
        }
        
        return await self.send_notification(
            recipients=[recipient],
            content=test_content,
            metadata={'type': 'test'}
        )
    
    async def shutdown(self) -> None:
        """Shutdown email notifier."""
        self.logger.info("Email notifier shutdown complete")
