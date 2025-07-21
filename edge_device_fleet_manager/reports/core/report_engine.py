"""
Report Engine

Core engine for generating reports in multiple formats with scheduling,
templating, and data source integration capabilities.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import uuid

from ...core.logging import get_logger
from ...persistence.connection.manager import DatabaseManager
from ..generators.pdf_generator import PDFReportGenerator
from ..generators.html_generator import HTMLReportGenerator
from ..generators.csv_generator import CSVReportGenerator
from ..generators.json_generator import JSONReportGenerator

logger = get_logger(__name__)


class ReportEngine:
    """
    Core report generation engine.
    
    Manages report generation across multiple formats, handles scheduling,
    template management, and data source integration.
    """
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        """
        Initialize report engine.
        
        Args:
            database_manager: Optional database manager for data access
        """
        self.database_manager = database_manager
        self.generators = {}
        self.templates = {}
        self.scheduled_reports = {}
        self.report_history = {}
        
        # Configuration
        self.output_directory = Path("reports/output")
        self.template_directory = Path("reports/templates")
        self.max_history_entries = 1000
        
        self.logger = get_logger(f"{__name__}.ReportEngine")
        
        # Initialize generators
        self._initialize_generators()
    
    def _initialize_generators(self) -> None:
        """Initialize report generators for different formats."""
        self.generators = {
            'pdf': PDFReportGenerator(),
            'html': HTMLReportGenerator(),
            'csv': CSVReportGenerator(),
            'json': JSONReportGenerator()
        }
        
        self.logger.info(f"Initialized {len(self.generators)} report generators")
    
    async def generate_report(self, report_type: str, data_source: Union[str, Dict[str, Any]],
                            output_format: str = 'pdf', template: Optional[str] = None,
                            output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate a report.
        
        Args:
            report_type: Type of report to generate
            data_source: Data source specification or data dict
            output_format: Output format (pdf, html, csv, json)
            template: Optional template name
            output_path: Optional custom output path
            **kwargs: Additional generation parameters
            
        Returns:
            Report generation result with metadata
        """
        try:
            report_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            self.logger.info(f"Starting report generation: {report_id}")
            
            # Validate format
            if output_format not in self.generators:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            # Load data
            data = await self._load_report_data(data_source, report_type)
            
            # Get generator
            generator = self.generators[output_format]
            
            # Load template if specified
            template_data = None
            if template:
                template_data = await self._load_template(template, output_format)
            
            # Generate output path
            if not output_path:
                output_path = self._generate_output_path(report_type, output_format, report_id)
            
            # Generate report
            result = await generator.generate(
                report_type=report_type,
                data=data,
                output_path=output_path,
                template=template_data,
                **kwargs
            )
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create report metadata
            report_metadata = {
                'report_id': report_id,
                'report_type': report_type,
                'output_format': output_format,
                'output_path': str(output_path),
                'template': template,
                'generated_at': start_time.isoformat(),
                'duration_seconds': duration,
                'data_source': str(data_source),
                'record_count': len(data) if isinstance(data, (list, dict)) else 0,
                'file_size_bytes': Path(output_path).stat().st_size if Path(output_path).exists() else 0,
                'success': True,
                'generator_result': result
            }
            
            # Store in history
            self._add_to_history(report_metadata)
            
            self.logger.info(f"Report generated successfully: {report_id} ({duration:.2f}s)")
            
            return report_metadata
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            
            # Create error metadata
            error_metadata = {
                'report_id': report_id if 'report_id' in locals() else str(uuid.uuid4()),
                'report_type': report_type,
                'output_format': output_format,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'success': False,
                'error': str(e),
                'data_source': str(data_source)
            }
            
            self._add_to_history(error_metadata)
            raise
    
    async def _load_report_data(self, data_source: Union[str, Dict[str, Any]], 
                              report_type: str) -> Any:
        """Load data for report generation."""
        if isinstance(data_source, dict):
            return data_source
        
        if isinstance(data_source, str):
            if data_source.startswith('query:'):
                # Database query
                return await self._execute_database_query(data_source[6:])
            elif data_source.startswith('file:'):
                # File data source
                return await self._load_file_data(data_source[5:])
            elif data_source.startswith('api:'):
                # API data source
                return await self._load_api_data(data_source[4:])
            else:
                # Predefined report type
                return await self._load_predefined_data(data_source, report_type)
        
        raise ValueError(f"Unsupported data source: {data_source}")
    
    async def _execute_database_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute database query for report data."""
        if not self.database_manager:
            raise ValueError("Database manager not available for query execution")
        
        async with self.database_manager.get_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            columns = result.keys()
            
            return [dict(zip(columns, row)) for row in rows]
    
    async def _load_file_data(self, file_path: str) -> Any:
        """Load data from file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Report data file not found: {file_path}")
        
        if path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                return json.load(f)
        elif path.suffix.lower() == '.csv':
            import pandas as pd
            df = pd.read_csv(path)
            return df.to_dict('records')
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    async def _load_api_data(self, api_spec: str) -> Any:
        """Load data from API endpoint."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_spec) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    text = await response.text()
                    return {'data': text}
    
    async def _load_predefined_data(self, data_source: str, report_type: str) -> Any:
        """Load predefined report data based on type."""
        if not self.database_manager:
            raise ValueError("Database manager required for predefined reports")
        
        # Import repositories
        from ...persistence.repositories.device import DeviceRepository
        from ...persistence.repositories.telemetry import TelemetryRepository
        from ...persistence.repositories.analytics import AnalyticsRepository
        from ...persistence.repositories.alert import AlertRepository
        from ...persistence.repositories.audit_log import AuditLogRepository
        
        async with self.database_manager.get_session() as session:
            if data_source == 'devices':
                repo = DeviceRepository(session)
                devices = await repo.get_all()
                return [self._device_to_dict(device) for device in devices]
            
            elif data_source == 'telemetry':
                repo = TelemetryRepository(session)
                # Get recent telemetry data
                since = datetime.now(timezone.utc) - timedelta(days=7)
                events = await repo.get_recent(since=since, limit=10000)
                return [self._telemetry_to_dict(event) for event in events]
            
            elif data_source == 'analytics':
                repo = AnalyticsRepository(session)
                since = datetime.now(timezone.utc) - timedelta(days=30)
                analytics = await repo.get_recent(since=since, limit=1000)
                return [self._analytics_to_dict(analytic) for analytic in analytics]
            
            elif data_source == 'alerts':
                repo = AlertRepository(session)
                since = datetime.now(timezone.utc) - timedelta(days=30)
                alerts = await repo.get_recent(since=since, limit=1000)
                return [self._alert_to_dict(alert) for alert in alerts]
            
            elif data_source == 'audit_logs':
                repo = AuditLogRepository(session)
                since = datetime.now(timezone.utc) - timedelta(days=30)
                logs = await repo.get_recent(since=since, limit=5000)
                return [self._audit_log_to_dict(log) for log in logs]
            
            else:
                raise ValueError(f"Unknown predefined data source: {data_source}")
    
    def _device_to_dict(self, device) -> Dict[str, Any]:
        """Convert device model to dictionary."""
        return {
            'id': str(device.id),
            'name': device.name,
            'device_type': device.device_type.value,
            'status': device.status.value,
            'health_score': device.health_score,
            'battery_level': device.battery_level,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'created_at': device.created_at.isoformat(),
            'ip_address': device.ip_address,
            'location': {
                'latitude': device.latitude,
                'longitude': device.longitude
            } if device.latitude and device.longitude else None
        }
    
    def _telemetry_to_dict(self, event) -> Dict[str, Any]:
        """Convert telemetry event to dictionary."""
        return {
            'id': str(event.id),
            'device_id': str(event.device_id),
            'event_type': event.event_type.value,
            'event_name': event.event_name,
            'timestamp': event.timestamp.isoformat(),
            'numeric_value': event.numeric_value,
            'string_value': event.string_value,
            'units': event.units,
            'quality_score': event.quality_score,
            'processed': event.processed
        }
    
    def _analytics_to_dict(self, analytic) -> Dict[str, Any]:
        """Convert analytics to dictionary."""
        return {
            'id': str(analytic.id),
            'analytics_type': analytic.analytics_type.value,
            'metric_name': analytic.metric_name,
            'metric_type': analytic.metric_type.value,
            'period_start': analytic.period_start.isoformat(),
            'period_end': analytic.period_end.isoformat(),
            'numeric_value': analytic.numeric_value,
            'granularity': analytic.granularity,
            'scope': analytic.scope
        }
    
    def _alert_to_dict(self, alert) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': str(alert.id),
            'title': alert.title,
            'description': alert.description,
            'alert_type': alert.alert_type,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'device_id': str(alert.device_id) if alert.device_id else None,
            'first_occurred': alert.first_occurred.isoformat(),
            'last_occurred': alert.last_occurred.isoformat() if alert.last_occurred else None,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def _audit_log_to_dict(self, log) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            'id': str(log.id),
            'action': log.action.value,
            'resource_type': log.resource_type.value,
            'resource_id': log.resource_id,
            'user_id': str(log.user_id) if log.user_id else None,
            'description': log.description,
            'success': log.success,
            'timestamp': log.timestamp.isoformat(),
            'ip_address': log.ip_address,
            'user_agent': log.user_agent
        }
    
    async def _load_template(self, template_name: str, output_format: str) -> Optional[str]:
        """Load report template."""
        template_path = self.template_directory / f"{template_name}.{output_format}"
        
        if template_path.exists():
            with open(template_path, 'r') as f:
                return f.read()
        
        self.logger.warning(f"Template not found: {template_path}")
        return None
    
    def _generate_output_path(self, report_type: str, output_format: str, report_id: str) -> Path:
        """Generate output file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{timestamp}_{report_id[:8]}.{output_format}"
        
        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        return self.output_directory / filename
    
    def _add_to_history(self, metadata: Dict[str, Any]) -> None:
        """Add report to generation history."""
        self.report_history[metadata['report_id']] = metadata
        
        # Limit history size
        if len(self.report_history) > self.max_history_entries:
            # Remove oldest entries
            oldest_keys = sorted(self.report_history.keys())[:100]
            for key in oldest_keys:
                del self.report_history[key]
    
    def get_report_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get report generation history."""
        reports = list(self.report_history.values())
        reports.sort(key=lambda x: x['generated_at'], reverse=True)
        return reports[:limit]
    
    def get_report_statistics(self) -> Dict[str, Any]:
        """Get report generation statistics."""
        reports = list(self.report_history.values())
        
        if not reports:
            return {
                'total_reports': 0,
                'successful_reports': 0,
                'failed_reports': 0,
                'success_rate': 0.0,
                'formats': {},
                'types': {}
            }
        
        successful = [r for r in reports if r.get('success', False)]
        failed = [r for r in reports if not r.get('success', False)]
        
        # Count by format
        formats = {}
        for report in reports:
            fmt = report.get('output_format', 'unknown')
            formats[fmt] = formats.get(fmt, 0) + 1
        
        # Count by type
        types = {}
        for report in reports:
            rtype = report.get('report_type', 'unknown')
            types[rtype] = types.get(rtype, 0) + 1
        
        return {
            'total_reports': len(reports),
            'successful_reports': len(successful),
            'failed_reports': len(failed),
            'success_rate': len(successful) / len(reports) * 100,
            'formats': formats,
            'types': types,
            'average_duration': sum(r.get('duration_seconds', 0) for r in successful) / len(successful) if successful else 0
        }
