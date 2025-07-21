"""
Unit Tests for Report Engine

Tests the core report generation engine functionality including
data loading, generator management, and report metadata.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from edge_device_fleet_manager.reports.core.report_engine import ReportEngine
from edge_device_fleet_manager.reports.generators.json_generator import JSONReportGenerator


class TestReportEngine:
    """Test cases for ReportEngine."""
    
    @pytest.fixture
    def report_engine(self):
        """Create report engine instance."""
        return ReportEngine()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return [
            {
                'id': 'device-1',
                'name': 'Test Device 1',
                'status': 'online',
                'health_score': 95.5
            },
            {
                'id': 'device-2',
                'name': 'Test Device 2',
                'status': 'offline',
                'health_score': 0.0
            }
        ]
    
    def test_engine_initialization(self, report_engine):
        """Test report engine initialization."""
        assert report_engine is not None
        assert hasattr(report_engine, 'generators')
        assert hasattr(report_engine, 'templates')
        assert hasattr(report_engine, 'scheduled_reports')
        assert hasattr(report_engine, 'report_history')
        
        # Check generators are initialized
        assert 'json' in report_engine.generators
        assert 'csv' in report_engine.generators
        assert 'html' in report_engine.generators
        assert 'pdf' in report_engine.generators
    
    @pytest.mark.asyncio
    async def test_generate_report_with_dict_data(self, report_engine, sample_data):
        """Test report generation with dictionary data source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_report.json'
            
            result = await report_engine.generate_report(
                report_type='device_status',
                data_source=sample_data,
                output_format='json',
                output_path=str(output_path)
            )
            
            assert result['success'] is True
            assert result['report_type'] == 'device_status'
            assert result['output_format'] == 'json'
            assert result['record_count'] == 2
            assert Path(result['output_path']).exists()
    
    @pytest.mark.asyncio
    async def test_generate_report_invalid_format(self, report_engine, sample_data):
        """Test report generation with invalid format."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            await report_engine.generate_report(
                report_type='device_status',
                data_source=sample_data,
                output_format='invalid_format'
            )
    
    @pytest.mark.asyncio
    async def test_load_report_data_dict(self, report_engine, sample_data):
        """Test loading data from dictionary source."""
        data = await report_engine._load_report_data(sample_data, 'device_status')
        assert data == sample_data
    
    @pytest.mark.asyncio
    async def test_load_report_data_file(self, report_engine):
        """Test loading data from file source."""
        test_data = {'test': 'data'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            data = await report_engine._load_report_data(f'file:{temp_path}', 'test')
            assert data == test_data
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_load_report_data_invalid_source(self, report_engine):
        """Test loading data from invalid source."""
        with pytest.raises(ValueError, match="Unsupported data source"):
            await report_engine._load_report_data('invalid:source', 'test')
    
    def test_generate_output_path(self, report_engine):
        """Test output path generation."""
        path = report_engine._generate_output_path('device_status', 'json', 'test-id')
        
        assert isinstance(path, Path)
        assert path.suffix == '.json'
        assert 'device_status' in path.name
        assert 'test-id'[:8] in path.name
    
    def test_add_to_history(self, report_engine):
        """Test adding report to history."""
        metadata = {
            'report_id': 'test-123',
            'report_type': 'test',
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        report_engine._add_to_history(metadata)
        
        assert 'test-123' in report_engine.report_history
        assert report_engine.report_history['test-123'] == metadata
    
    def test_get_report_history(self, report_engine):
        """Test getting report history."""
        # Add test reports
        for i in range(3):
            metadata = {
                'report_id': f'test-{i}',
                'report_type': 'test',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            report_engine._add_to_history(metadata)
        
        history = report_engine.get_report_history(limit=2)
        
        assert len(history) == 2
        assert all('report_id' in report for report in history)
    
    def test_get_report_statistics_empty(self, report_engine):
        """Test getting statistics with no reports."""
        stats = report_engine.get_report_statistics()
        
        assert stats['total_reports'] == 0
        assert stats['successful_reports'] == 0
        assert stats['failed_reports'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['formats'] == {}
        assert stats['types'] == {}
    
    def test_get_report_statistics_with_data(self, report_engine):
        """Test getting statistics with report data."""
        # Add test reports
        successful_report = {
            'report_id': 'success-1',
            'report_type': 'device_status',
            'output_format': 'json',
            'success': True,
            'duration_seconds': 1.5,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        failed_report = {
            'report_id': 'failed-1',
            'report_type': 'alert_summary',
            'output_format': 'pdf',
            'success': False,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        report_engine._add_to_history(successful_report)
        report_engine._add_to_history(failed_report)
        
        stats = report_engine.get_report_statistics()
        
        assert stats['total_reports'] == 2
        assert stats['successful_reports'] == 1
        assert stats['failed_reports'] == 1
        assert stats['success_rate'] == 50.0
        assert stats['formats']['json'] == 1
        assert stats['formats']['pdf'] == 1
        assert stats['types']['device_status'] == 1
        assert stats['types']['alert_summary'] == 1
        assert stats['average_duration'] == 1.5
    
    def test_device_to_dict(self, report_engine):
        """Test device model to dictionary conversion."""
        # Mock device object
        device = Mock()
        device.id = 'device-123'
        device.name = 'Test Device'
        device.device_type.value = 'sensor'
        device.status.value = 'online'
        device.health_score = 95.5
        device.battery_level = 80
        device.last_seen = datetime.now(timezone.utc)
        device.created_at = datetime.now(timezone.utc)
        device.ip_address = '192.168.1.100'
        device.latitude = 40.7128
        device.longitude = -74.0060
        
        result = report_engine._device_to_dict(device)
        
        assert result['id'] == 'device-123'
        assert result['name'] == 'Test Device'
        assert result['device_type'] == 'sensor'
        assert result['status'] == 'online'
        assert result['health_score'] == 95.5
        assert result['battery_level'] == 80
        assert result['ip_address'] == '192.168.1.100'
        assert result['location']['latitude'] == 40.7128
        assert result['location']['longitude'] == -74.0060
    
    def test_telemetry_to_dict(self, report_engine):
        """Test telemetry event to dictionary conversion."""
        # Mock telemetry event
        event = Mock()
        event.id = 'event-123'
        event.device_id = 'device-456'
        event.event_type.value = 'temperature'
        event.event_name = 'temperature_reading'
        event.timestamp = datetime.now(timezone.utc)
        event.numeric_value = 23.5
        event.string_value = None
        event.units = 'celsius'
        event.quality_score = 0.95
        event.processed = True
        
        result = report_engine._telemetry_to_dict(event)
        
        assert result['id'] == 'event-123'
        assert result['device_id'] == 'device-456'
        assert result['event_type'] == 'temperature'
        assert result['event_name'] == 'temperature_reading'
        assert result['numeric_value'] == 23.5
        assert result['string_value'] is None
        assert result['units'] == 'celsius'
        assert result['quality_score'] == 0.95
        assert result['processed'] is True
    
    @pytest.mark.asyncio
    async def test_load_template(self, report_engine):
        """Test template loading."""
        # Create temporary template
        template_content = "Test template content"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            report_engine.template_directory = Path(temp_dir)
            template_path = report_engine.template_directory / 'test.json'
            
            with open(template_path, 'w') as f:
                f.write(template_content)
            
            result = await report_engine._load_template('test', 'json')
            assert result == template_content
    
    @pytest.mark.asyncio
    async def test_load_template_not_found(self, report_engine):
        """Test template loading when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            report_engine.template_directory = Path(temp_dir)
            
            result = await report_engine._load_template('nonexistent', 'json')
            assert result is None
    
    @pytest.mark.asyncio
    async def test_load_file_data_json(self, report_engine):
        """Test loading JSON file data."""
        test_data = {'key': 'value', 'number': 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            result = await report_engine._load_file_data(temp_path)
            assert result == test_data
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_load_file_data_not_found(self, report_engine):
        """Test loading file data when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await report_engine._load_file_data('/nonexistent/file.json')
    
    @pytest.mark.asyncio
    async def test_load_file_data_unsupported_format(self, report_engine):
        """Test loading file data with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test content')
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                await report_engine._load_file_data(temp_path)
        finally:
            Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_report_engine_integration():
    """Integration test for report engine."""
    engine = ReportEngine()
    
    sample_data = [
        {'id': '1', 'name': 'Device 1', 'status': 'online'},
        {'id': '2', 'name': 'Device 2', 'status': 'offline'}
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / 'integration_test.json'
        
        result = await engine.generate_report(
            report_type='device_status',
            data_source=sample_data,
            output_format='json',
            output_path=str(output_path)
        )
        
        assert result['success'] is True
        assert output_path.exists()
        
        # Verify file content
        with open(output_path) as f:
            report_data = json.load(f)
        
        assert 'metadata' in report_data
        assert 'data' in report_data
        assert report_data['metadata']['report_type'] == 'device_status'
        assert len(report_data['data']) == 2
