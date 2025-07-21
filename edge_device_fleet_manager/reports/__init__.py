"""
Report Generation & Alert System

Comprehensive reporting and alerting system for the Edge Device Fleet Manager.
Provides automated report generation, alert management, notification delivery,
and audit log retention with Docker Compose orchestration.

Features:
- Automated report generation (PDF, HTML, CSV, JSON)
- Real-time alert system with multiple severity levels
- Notification delivery (email, SMS, webhook, Slack)
- Audit log retention and compliance
- Docker Compose orchestration
- Secrets management integration
- Scheduled reporting and alerting
- Template-based report customization
"""

from .core.report_engine import ReportEngine
from .core.alert_manager import AlertManager
from .core.notification_service import NotificationService
from .core.audit_retention import AuditRetentionManager
from .generators.pdf_generator import PDFReportGenerator
from .generators.html_generator import HTMLReportGenerator
from .generators.csv_generator import CSVReportGenerator
from .generators.json_generator import JSONReportGenerator
from .alerts.alert_rules import AlertRule, AlertRuleEngine
from .alerts.severity import AlertSeverity, AlertStatus
from .notifications.email_notifier import EmailNotifier
from .notifications.webhook_notifier import WebhookNotifier

__version__ = "1.0.0"
__author__ = "Edge Device Fleet Manager Team"

# Core exports
__all__ = [
    # Core engines
    'ReportEngine',
    'AlertManager',
    'NotificationService',
    'AuditRetentionManager',
    
    # Report generators
    'PDFReportGenerator',
    'HTMLReportGenerator',
    'CSVReportGenerator',
    'JSONReportGenerator',
    
    # Alert system
    'AlertRule',
    'AlertRuleEngine',
    'AlertSeverity',
    'AlertStatus',
    
    # Notification system
    'EmailNotifier',
    'WebhookNotifier',
    
    # Convenience functions
    'create_report',
    'send_alert',
    'schedule_report',
    'configure_retention',
]

# Convenience functions (synchronous wrappers for async operations)
def create_report(report_type, data_source, output_format='json', **kwargs):
    """Create a report with specified format."""
    import asyncio

    async def _create_report():
        engine = ReportEngine()
        return await engine.generate_report(
            report_type=report_type,
            data_source=data_source,
            output_format=output_format,
            **kwargs
        )

    try:
        return asyncio.run(_create_report())
    except Exception as e:
        return {'success': False, 'error': str(e)}

def send_alert(title, message, severity='medium', **kwargs):
    """Send an alert with specified severity."""
    import asyncio

    async def _send_alert():
        manager = AlertManager()
        await manager.initialize()

        # Convert string severity to enum
        severity_map = {
            'low': AlertSeverity.LOW,
            'medium': AlertSeverity.MEDIUM,
            'high': AlertSeverity.HIGH,
            'critical': AlertSeverity.CRITICAL
        }

        severity_enum = severity_map.get(severity.lower(), AlertSeverity.MEDIUM)

        return await manager.create_alert(
            title=title,
            description=message,
            severity=severity_enum,
            **kwargs
        )

    try:
        return asyncio.run(_send_alert())
    except Exception as e:
        return None

def schedule_report(report_config, schedule_expression, **kwargs):
    """Schedule a report for automatic generation."""
    # Placeholder for scheduling functionality
    return {'success': False, 'error': 'Scheduling not yet implemented'}

def configure_retention(retention_policy, **kwargs):
    """Configure audit log retention policy."""
    import asyncio

    async def _configure_retention():
        manager = AuditRetentionManager()
        await manager.initialize()
        return await manager.configure_policy(
            policy_name=retention_policy.get('name', 'Default Policy'),
            policy_config=retention_policy
        )

    try:
        return asyncio.run(_configure_retention())
    except Exception as e:
        return None
