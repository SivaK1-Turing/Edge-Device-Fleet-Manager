"""
PDF Report Generator

Generates PDF reports with charts, tables, and formatted content
using matplotlib and reportlab for professional report output.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import io
import base64

from ...core.logging import get_logger

logger = get_logger(__name__)


class PDFReportGenerator:
    """
    PDF report generator.
    
    Creates professional PDF reports with charts, tables, headers,
    footers, and custom styling.
    """
    
    def __init__(self):
        """Initialize PDF report generator."""
        self.logger = get_logger(f"{__name__}.PDFReportGenerator")
        
        # Check for required dependencies
        self.reportlab_available = self._check_reportlab()
        self.matplotlib_available = self._check_matplotlib()
    
    def _check_reportlab(self) -> bool:
        """Check if reportlab is available."""
        try:
            import reportlab
            return True
        except ImportError:
            self.logger.warning("reportlab not available - PDF generation will be limited")
            return False
    
    def _check_matplotlib(self) -> bool:
        """Check if matplotlib is available."""
        try:
            import matplotlib
            return True
        except ImportError:
            self.logger.warning("matplotlib not available - chart generation will be limited")
            return False
    
    async def generate(self, report_type: str, data: Any, output_path: str,
                      template: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate PDF report.
        
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
            
            if not self.reportlab_available:
                # Fallback to simple text-based PDF
                return await self._generate_simple_pdf(report_type, data, output_path, **kwargs)
            
            # Generate full-featured PDF
            result = await self._generate_reportlab_pdf(report_type, data, output_path, template, **kwargs)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get file size
            file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'pages': result.get('pages', 1),
                'charts': result.get('charts', 0),
                'tables': result.get('tables', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF report: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    async def _generate_reportlab_pdf(self, report_type: str, data: Any, output_path: str,
                                    template: Optional[str], **kwargs) -> Dict[str, Any]:
        """Generate PDF using reportlab."""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=kwargs.get('page_size', A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build story (content)
        story = []
        styles = getSampleStyleSheet()
        
        # Add custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Title
        title = kwargs.get('title', f'{report_type.replace("_", " ").title()} Report')
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # Report metadata
        metadata_table = [
            ['Generated:', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Report Type:', report_type.replace('_', ' ').title()],
            ['Data Records:', str(len(data)) if isinstance(data, list) else 'N/A']
        ]
        
        metadata_table_obj = Table(metadata_table, colWidths=[2*inch, 4*inch])
        metadata_table_obj.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table_obj)
        story.append(Spacer(1, 20))
        
        # Generate content based on report type
        charts_count = 0
        tables_count = 0
        
        if report_type == 'device_status':
            content_result = await self._generate_device_status_content(story, data, styles)
        elif report_type == 'alert_summary':
            content_result = await self._generate_alert_summary_content(story, data, styles)
        elif report_type == 'telemetry_analysis':
            content_result = await self._generate_telemetry_analysis_content(story, data, styles)
        elif report_type == 'audit_report':
            content_result = await self._generate_audit_report_content(story, data, styles)
        else:
            content_result = await self._generate_generic_content(story, data, styles)
        
        charts_count += content_result.get('charts', 0)
        tables_count += content_result.get('tables', 0)
        
        # Build PDF
        doc.build(story)
        
        return {
            'pages': len(story) // 20 + 1,  # Rough estimate
            'charts': charts_count,
            'tables': tables_count
        }
    
    async def _generate_device_status_content(self, story: List, data: List[Dict[str, Any]], 
                                            styles) -> Dict[str, Any]:
        """Generate device status report content."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        # Summary section
        story.append(Paragraph("Device Status Summary", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if not data:
            story.append(Paragraph("No device data available.", styles['Normal']))
            return {'tables': 0, 'charts': 0}
        
        # Status distribution
        status_counts = {}
        for device in data:
            status = device.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Summary table
        summary_data = [['Status', 'Count', 'Percentage']]
        total_devices = len(data)
        
        for status, count in status_counts.items():
            percentage = (count / total_devices * 100) if total_devices > 0 else 0
            summary_data.append([status.title(), str(count), f"{percentage:.1f}%"])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Device details table
        story.append(Paragraph("Device Details", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        device_data = [['Device Name', 'Type', 'Status', 'Health Score', 'Last Seen']]
        
        for device in data[:20]:  # Limit to first 20 devices
            device_data.append([
                device.get('name', 'Unknown'),
                device.get('device_type', 'Unknown'),
                device.get('status', 'Unknown'),
                f"{device.get('health_score', 0):.1f}%" if device.get('health_score') else 'N/A',
                device.get('last_seen', 'Never')[:19] if device.get('last_seen') else 'Never'
            ])
        
        device_table = Table(device_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
        device_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(device_table)
        
        return {'tables': 2, 'charts': 0}
    
    async def _generate_alert_summary_content(self, story: List, data: List[Dict[str, Any]], 
                                            styles) -> Dict[str, Any]:
        """Generate alert summary report content."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        story.append(Paragraph("Alert Summary", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if not data:
            story.append(Paragraph("No alert data available.", styles['Normal']))
            return {'tables': 0, 'charts': 0}
        
        # Severity distribution
        severity_counts = {}
        for alert in data:
            severity = alert.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Alert summary table
        alert_data = [['Severity', 'Count', 'Percentage']]
        total_alerts = len(data)
        
        for severity, count in severity_counts.items():
            percentage = (count / total_alerts * 100) if total_alerts > 0 else 0
            alert_data.append([severity.title(), str(count), f"{percentage:.1f}%"])
        
        alert_table = Table(alert_data, colWidths=[2*inch, 1*inch, 1*inch])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(alert_table)
        story.append(Spacer(1, 20))
        
        # Recent alerts
        story.append(Paragraph("Recent Alerts", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        recent_data = [['Title', 'Severity', 'Status', 'First Occurred']]
        
        for alert in data[:15]:  # Limit to first 15 alerts
            recent_data.append([
                alert.get('title', 'Unknown')[:30] + '...' if len(alert.get('title', '')) > 30 else alert.get('title', 'Unknown'),
                alert.get('severity', 'Unknown'),
                alert.get('status', 'Unknown'),
                alert.get('first_occurred', 'Unknown')[:19] if alert.get('first_occurred') else 'Unknown'
            ])
        
        recent_table = Table(recent_data, colWidths=[3*inch, 1*inch, 1*inch, 1.5*inch])
        recent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(recent_table)
        
        return {'tables': 2, 'charts': 0}
    
    async def _generate_telemetry_analysis_content(self, story: List, data: List[Dict[str, Any]], 
                                                 styles) -> Dict[str, Any]:
        """Generate telemetry analysis report content."""
        from reportlab.platypus import Paragraph, Spacer
        
        story.append(Paragraph("Telemetry Analysis", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if not data:
            story.append(Paragraph("No telemetry data available.", styles['Normal']))
            return {'tables': 0, 'charts': 0}
        
        # Basic statistics
        total_events = len(data)
        event_types = set(event.get('event_type', 'unknown') for event in data)
        
        story.append(Paragraph(f"Total Events: {total_events}", styles['Normal']))
        story.append(Paragraph(f"Event Types: {', '.join(event_types)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        return {'tables': 0, 'charts': 0}
    
    async def _generate_audit_report_content(self, story: List, data: List[Dict[str, Any]], 
                                           styles) -> Dict[str, Any]:
        """Generate audit report content."""
        from reportlab.platypus import Paragraph, Spacer
        
        story.append(Paragraph("Audit Log Report", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if not data:
            story.append(Paragraph("No audit log data available.", styles['Normal']))
            return {'tables': 0, 'charts': 0}
        
        # Basic statistics
        total_logs = len(data)
        actions = set(log.get('action', 'unknown') for log in data)
        
        story.append(Paragraph(f"Total Log Entries: {total_logs}", styles['Normal']))
        story.append(Paragraph(f"Actions: {', '.join(actions)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        return {'tables': 0, 'charts': 0}
    
    async def _generate_generic_content(self, story: List, data: Any, styles) -> Dict[str, Any]:
        """Generate generic report content."""
        from reportlab.platypus import Paragraph, Spacer
        
        story.append(Paragraph("Report Data", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        if isinstance(data, list):
            story.append(Paragraph(f"Data contains {len(data)} records.", styles['Normal']))
        elif isinstance(data, dict):
            story.append(Paragraph(f"Data contains {len(data)} fields.", styles['Normal']))
        else:
            story.append(Paragraph("Data type: " + type(data).__name__, styles['Normal']))
        
        story.append(Spacer(1, 12))
        
        return {'tables': 0, 'charts': 0}
    
    async def _generate_simple_pdf(self, report_type: str, data: Any, output_path: str, 
                                 **kwargs) -> Dict[str, Any]:
        """Generate simple text-based PDF without reportlab."""
        # Fallback implementation using basic text
        content = f"""
{report_type.replace('_', ' ').title()} Report
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Data Summary:
- Type: {type(data).__name__}
- Records: {len(data) if isinstance(data, list) else 'N/A'}

Note: This is a simplified report. Install 'reportlab' for full PDF features.
        """.strip()
        
        # Write to text file (since we can't generate PDF without reportlab)
        text_path = output_path.replace('.pdf', '.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'success': True,
            'output_path': text_path,
            'file_size_bytes': len(content.encode('utf-8')),
            'pages': 1,
            'charts': 0,
            'tables': 0,
            'note': 'Generated as text file - install reportlab for PDF support'
        }
