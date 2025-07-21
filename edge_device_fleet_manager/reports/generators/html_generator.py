"""
HTML Report Generator

Generates HTML reports with interactive charts, tables, and responsive design
for web-based report viewing and sharing.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

from ...core.logging import get_logger

logger = get_logger(__name__)


class HTMLReportGenerator:
    """
    HTML report generator.
    
    Creates interactive HTML reports with charts, tables, responsive design,
    and modern web styling.
    """
    
    def __init__(self):
        """Initialize HTML report generator."""
        self.logger = get_logger(f"{__name__}.HTMLReportGenerator")
    
    async def generate(self, report_type: str, data: Any, output_path: str,
                      template: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate HTML report.
        
        Args:
            report_type: Type of report to generate
            data: Report data
            output_path: Output file path
            template: Optional template
            **kwargs: Additional generation parameters
            
        Returns:
            Generation result
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Generate HTML content
            html_content = await self._generate_html_content(report_type, data, template, **kwargs)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get file size
            file_size = Path(output_path).stat().st_size
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'content_length': len(html_content),
                'interactive': True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    async def _generate_html_content(self, report_type: str, data: Any, 
                                   template: Optional[str], **kwargs) -> str:
        """Generate complete HTML content."""
        title = kwargs.get('title', f'{report_type.replace("_", " ").title()} Report')
        
        # HTML structure
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {self._get_css_styles()}
    {self._get_javascript_libraries()}
</head>
<body>
    <div class="container">
        {await self._generate_header(title, report_type)}
        {await self._generate_metadata_section(data, report_type)}
        {await self._generate_content_section(report_type, data, **kwargs)}
        {self._generate_footer()}
    </div>
    {await self._generate_javascript(report_type, data)}
</body>
</html>"""
        
        return html
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for the report."""
        return """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #007bff;
        }
        
        .header h1 {
            color: #007bff;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .metadata {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        
        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .metadata-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background-color: white;
            border-radius: 3px;
            border-left: 4px solid #007bff;
        }
        
        .metadata-label {
            font-weight: bold;
            color: #495057;
        }
        
        .metadata-value {
            color: #007bff;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #495057;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .chart-container {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .table-container {
            overflow-x: auto;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        
        th {
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }
        
        tr:hover {
            background-color: #f8f9fa;
        }
        
        .status-online { color: #28a745; font-weight: bold; }
        .status-offline { color: #dc3545; font-weight: bold; }
        .status-maintenance { color: #ffc107; font-weight: bold; }
        
        .severity-critical { color: #dc3545; font-weight: bold; }
        .severity-high { color: #fd7e14; font-weight: bold; }
        .severity-medium { color: #ffc107; font-weight: bold; }
        .severity-low { color: #28a745; font-weight: bold; }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.9em;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .summary-card h3 {
            color: #495057;
            margin-bottom: 10px;
        }
        
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .metadata-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>"""
    
    def _get_javascript_libraries(self) -> str:
        """Get JavaScript libraries for charts."""
        return """
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>"""
    
    async def _generate_header(self, title: str, report_type: str) -> str:
        """Generate report header."""
        return f"""
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}</p>
    </div>"""
    
    async def _generate_metadata_section(self, data: Any, report_type: str) -> str:
        """Generate metadata section."""
        record_count = len(data) if isinstance(data, list) else 'N/A'
        data_type = type(data).__name__
        
        return f"""
    <div class="metadata">
        <h2>Report Information</h2>
        <div class="metadata-grid">
            <div class="metadata-item">
                <span class="metadata-label">Report Type:</span>
                <span class="metadata-value">{report_type.replace('_', ' ').title()}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Data Records:</span>
                <span class="metadata-value">{record_count}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Data Type:</span>
                <span class="metadata-value">{data_type}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Generated:</span>
                <span class="metadata-value">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
            </div>
        </div>
    </div>"""
    
    async def _generate_content_section(self, report_type: str, data: Any, **kwargs) -> str:
        """Generate main content section."""
        if report_type == 'device_status':
            return await self._generate_device_status_content(data)
        elif report_type == 'alert_summary':
            return await self._generate_alert_summary_content(data)
        elif report_type == 'telemetry_analysis':
            return await self._generate_telemetry_analysis_content(data)
        elif report_type == 'audit_report':
            return await self._generate_audit_report_content(data)
        else:
            return await self._generate_generic_content(data)
    
    async def _generate_device_status_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate device status report content."""
        if not data:
            return '<div class="section"><h2>Device Status</h2><p>No device data available.</p></div>'
        
        # Calculate summary statistics
        total_devices = len(data)
        online_devices = len([d for d in data if d.get('status') == 'online'])
        offline_devices = len([d for d in data if d.get('status') == 'offline'])
        maintenance_devices = len([d for d in data if d.get('status') == 'maintenance'])
        
        avg_health = sum(d.get('health_score', 0) for d in data) / total_devices if total_devices > 0 else 0
        
        # Summary cards
        summary_cards = f"""
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total Devices</h3>
                <div class="value">{total_devices}</div>
            </div>
            <div class="summary-card">
                <h3>Online</h3>
                <div class="value status-online">{online_devices}</div>
            </div>
            <div class="summary-card">
                <h3>Offline</h3>
                <div class="value status-offline">{offline_devices}</div>
            </div>
            <div class="summary-card">
                <h3>Maintenance</h3>
                <div class="value status-maintenance">{maintenance_devices}</div>
            </div>
            <div class="summary-card">
                <h3>Avg Health</h3>
                <div class="value">{avg_health:.1f}%</div>
            </div>
        </div>"""
        
        # Chart container
        chart_section = """
        <div class="chart-container">
            <h3>Device Status Distribution</h3>
            <canvas id="deviceStatusChart" width="400" height="200"></canvas>
        </div>"""
        
        # Device table
        table_rows = ""
        for device in data[:20]:  # Limit to first 20 devices
            status_class = f"status-{device.get('status', 'unknown')}"
            health_score = device.get('health_score', 0)
            last_seen = device.get('last_seen', 'Never')[:19] if device.get('last_seen') else 'Never'
            
            table_rows += f"""
            <tr>
                <td>{device.get('name', 'Unknown')}</td>
                <td>{device.get('device_type', 'Unknown')}</td>
                <td class="{status_class}">{device.get('status', 'Unknown').title()}</td>
                <td>{health_score:.1f}%</td>
                <td>{last_seen}</td>
            </tr>"""
        
        device_table = f"""
        <div class="table-container">
            <h3>Device Details</h3>
            <table>
                <thead>
                    <tr>
                        <th>Device Name</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Health Score</th>
                        <th>Last Seen</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>"""
        
        return f"""
        <div class="section">
            <h2>Device Status Report</h2>
            {summary_cards}
            {chart_section}
            {device_table}
        </div>"""
    
    async def _generate_alert_summary_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate alert summary report content."""
        if not data:
            return '<div class="section"><h2>Alert Summary</h2><p>No alert data available.</p></div>'
        
        # Calculate summary statistics
        total_alerts = len(data)
        critical_alerts = len([a for a in data if a.get('severity') == 'critical'])
        high_alerts = len([a for a in data if a.get('severity') == 'high'])
        medium_alerts = len([a for a in data if a.get('severity') == 'medium'])
        low_alerts = len([a for a in data if a.get('severity') == 'low'])
        
        # Summary cards
        summary_cards = f"""
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total Alerts</h3>
                <div class="value">{total_alerts}</div>
            </div>
            <div class="summary-card">
                <h3>Critical</h3>
                <div class="value severity-critical">{critical_alerts}</div>
            </div>
            <div class="summary-card">
                <h3>High</h3>
                <div class="value severity-high">{high_alerts}</div>
            </div>
            <div class="summary-card">
                <h3>Medium</h3>
                <div class="value severity-medium">{medium_alerts}</div>
            </div>
            <div class="summary-card">
                <h3>Low</h3>
                <div class="value severity-low">{low_alerts}</div>
            </div>
        </div>"""
        
        # Chart container
        chart_section = """
        <div class="chart-container">
            <h3>Alert Severity Distribution</h3>
            <canvas id="alertSeverityChart" width="400" height="200"></canvas>
        </div>"""
        
        # Alert table
        table_rows = ""
        for alert in data[:15]:  # Limit to first 15 alerts
            severity_class = f"severity-{alert.get('severity', 'unknown')}"
            title = alert.get('title', 'Unknown')
            if len(title) > 40:
                title = title[:37] + '...'
            
            first_occurred = alert.get('first_occurred', 'Unknown')[:19] if alert.get('first_occurred') else 'Unknown'
            
            table_rows += f"""
            <tr>
                <td>{title}</td>
                <td class="{severity_class}">{alert.get('severity', 'Unknown').title()}</td>
                <td>{alert.get('status', 'Unknown').title()}</td>
                <td>{first_occurred}</td>
            </tr>"""
        
        alert_table = f"""
        <div class="table-container">
            <h3>Recent Alerts</h3>
            <table>
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>First Occurred</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>"""
        
        return f"""
        <div class="section">
            <h2>Alert Summary Report</h2>
            {summary_cards}
            {chart_section}
            {alert_table}
        </div>"""
    
    async def _generate_telemetry_analysis_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate telemetry analysis report content."""
        if not data:
            return '<div class="section"><h2>Telemetry Analysis</h2><p>No telemetry data available.</p></div>'
        
        total_events = len(data)
        event_types = set(event.get('event_type', 'unknown') for event in data)
        
        return f"""
        <div class="section">
            <h2>Telemetry Analysis Report</h2>
            <div class="summary-cards">
                <div class="summary-card">
                    <h3>Total Events</h3>
                    <div class="value">{total_events}</div>
                </div>
                <div class="summary-card">
                    <h3>Event Types</h3>
                    <div class="value">{len(event_types)}</div>
                </div>
            </div>
            <p><strong>Event Types:</strong> {', '.join(event_types)}</p>
        </div>"""
    
    async def _generate_audit_report_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate audit report content."""
        if not data:
            return '<div class="section"><h2>Audit Report</h2><p>No audit log data available.</p></div>'
        
        total_logs = len(data)
        actions = set(log.get('action', 'unknown') for log in data)
        
        return f"""
        <div class="section">
            <h2>Audit Log Report</h2>
            <div class="summary-cards">
                <div class="summary-card">
                    <h3>Total Logs</h3>
                    <div class="value">{total_logs}</div>
                </div>
                <div class="summary-card">
                    <h3>Actions</h3>
                    <div class="value">{len(actions)}</div>
                </div>
            </div>
            <p><strong>Actions:</strong> {', '.join(actions)}</p>
        </div>"""
    
    async def _generate_generic_content(self, data: Any) -> str:
        """Generate generic report content."""
        if isinstance(data, list):
            content = f"Data contains {len(data)} records."
        elif isinstance(data, dict):
            content = f"Data contains {len(data)} fields."
        else:
            content = f"Data type: {type(data).__name__}"
        
        return f"""
        <div class="section">
            <h2>Report Data</h2>
            <p>{content}</p>
        </div>"""
    
    def _generate_footer(self) -> str:
        """Generate report footer."""
        return f"""
    <div class="footer">
        <p>Generated by Edge Device Fleet Manager | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>"""
    
    async def _generate_javascript(self, report_type: str, data: Any) -> str:
        """Generate JavaScript for interactive features."""
        if report_type == 'device_status' and isinstance(data, list):
            return self._generate_device_status_js(data)
        elif report_type == 'alert_summary' and isinstance(data, list):
            return self._generate_alert_summary_js(data)
        else:
            return "<script>console.log('Report loaded successfully');</script>"
    
    def _generate_device_status_js(self, data: List[Dict[str, Any]]) -> str:
        """Generate JavaScript for device status charts."""
        # Calculate status distribution
        status_counts = {}
        for device in data:
            status = device.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        
        return f"""
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('deviceStatusChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        data: {json.dumps(values)},
                        backgroundColor: [
                            '#28a745',  // online - green
                            '#dc3545',  // offline - red
                            '#ffc107',  // maintenance - yellow
                            '#6c757d'   // unknown - gray
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});
        }});
    </script>"""
    
    def _generate_alert_summary_js(self, data: List[Dict[str, Any]]) -> str:
        """Generate JavaScript for alert summary charts."""
        # Calculate severity distribution
        severity_counts = {}
        for alert in data:
            severity = alert.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        labels = list(severity_counts.keys())
        values = list(severity_counts.values())
        
        return f"""
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('alertSeverityChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: 'Alert Count',
                        data: {json.dumps(values)},
                        backgroundColor: [
                            '#dc3545',  // critical - red
                            '#fd7e14',  // high - orange
                            '#ffc107',  // medium - yellow
                            '#28a745'   // low - green
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        }});
    </script>"""
