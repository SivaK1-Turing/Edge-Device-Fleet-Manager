"""
JSON Report Generator

Generates JSON reports with structured data export, pretty formatting,
and support for complex nested data structures.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import uuid

from ...core.logging import get_logger

logger = get_logger(__name__)


class JSONReportGenerator:
    """
    JSON report generator.
    
    Creates JSON reports with proper formatting, metadata, and support
    for complex data structures and custom serialization.
    """
    
    def __init__(self):
        """Initialize JSON report generator."""
        self.logger = get_logger(f"{__name__}.JSONReportGenerator")
    
    async def generate(self, report_type: str, data: Any, output_path: str,
                      template: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate JSON report.
        
        Args:
            report_type: Type of report to generate
            data: Report data
            output_path: Output file path
            template: Optional template (not used for JSON)
            **kwargs: Additional generation parameters
            
        Returns:
            Generation result
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Prepare JSON structure
            json_data = await self._prepare_json_data(report_type, data, **kwargs)
            
            # Write JSON file
            await self._write_json_file(json_data, output_path, **kwargs)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get file size
            file_size = Path(output_path).stat().st_size
            
            # Calculate data statistics
            stats = self._calculate_json_stats(json_data)
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'encoding': kwargs.get('encoding', 'utf-8'),
                'pretty_printed': kwargs.get('pretty_print', True),
                **stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    async def _prepare_json_data(self, report_type: str, data: Any, **kwargs) -> Dict[str, Any]:
        """Prepare data for JSON export."""
        # Create report structure
        report_data = {
            'metadata': {
                'report_id': str(uuid.uuid4()),
                'report_type': report_type,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'generator': 'Edge Device Fleet Manager JSON Generator',
                'version': '1.0.0'
            },
            'data': await self._serialize_data(data),
            'summary': await self._generate_summary(data, report_type)
        }
        
        # Add custom metadata if provided
        custom_metadata = kwargs.get('metadata', {})
        if custom_metadata:
            report_data['metadata'].update(custom_metadata)
        
        # Add schema information if requested
        if kwargs.get('include_schema', False):
            report_data['schema'] = await self._generate_schema(data)
        
        return report_data
    
    async def _serialize_data(self, data: Any) -> Any:
        """Serialize data for JSON export with custom handling."""
        if data is None:
            return None
        
        elif isinstance(data, (str, int, float, bool)):
            return data
        
        elif isinstance(data, datetime):
            return data.isoformat()
        
        elif isinstance(data, uuid.UUID):
            return str(data)
        
        elif isinstance(data, (list, tuple)):
            return [await self._serialize_data(item) for item in data]
        
        elif isinstance(data, dict):
            serialized = {}
            for key, value in data.items():
                # Ensure key is string
                str_key = str(key)
                serialized[str_key] = await self._serialize_data(value)
            return serialized
        
        elif hasattr(data, '__dict__'):
            # Handle objects with __dict__
            return await self._serialize_data(data.__dict__)
        
        elif hasattr(data, '_asdict'):
            # Handle namedtuples
            return await self._serialize_data(data._asdict())
        
        else:
            # Fallback to string representation
            return str(data)
    
    async def _generate_summary(self, data: Any, report_type: str) -> Dict[str, Any]:
        """Generate summary information about the data."""
        summary = {
            'data_type': type(data).__name__,
            'report_type': report_type
        }
        
        if isinstance(data, list):
            summary.update({
                'record_count': len(data),
                'is_empty': len(data) == 0
            })
            
            if data and isinstance(data[0], dict):
                # Analyze structure of first record
                first_record = data[0]
                summary.update({
                    'fields': list(first_record.keys()),
                    'field_count': len(first_record.keys())
                })
                
                # Analyze data types
                field_types = {}
                for field, value in first_record.items():
                    field_types[field] = type(value).__name__
                summary['field_types'] = field_types
        
        elif isinstance(data, dict):
            summary.update({
                'field_count': len(data),
                'fields': list(data.keys()),
                'is_empty': len(data) == 0
            })
            
            # Analyze value types
            field_types = {}
            for field, value in data.items():
                field_types[field] = type(value).__name__
            summary['field_types'] = field_types
        
        else:
            summary.update({
                'value': str(data)[:100] + '...' if len(str(data)) > 100 else str(data),
                'length': len(str(data))
            })
        
        return summary
    
    async def _generate_schema(self, data: Any) -> Dict[str, Any]:
        """Generate schema information for the data."""
        schema = {
            'type': type(data).__name__,
            'description': f'Schema for {type(data).__name__} data'
        }
        
        if isinstance(data, list) and data:
            # Analyze list structure
            if isinstance(data[0], dict):
                # Generate schema for object list
                schema.update({
                    'items': {
                        'type': 'object',
                        'properties': {}
                    }
                })
                
                # Analyze all records to get complete field list
                all_fields = set()
                for item in data:
                    if isinstance(item, dict):
                        all_fields.update(item.keys())
                
                # Generate property schemas
                for field in all_fields:
                    # Sample values to determine type
                    sample_values = []
                    for item in data:
                        if isinstance(item, dict) and field in item:
                            sample_values.append(item[field])
                            if len(sample_values) >= 10:  # Sample first 10
                                break
                    
                    if sample_values:
                        field_type = self._infer_field_type(sample_values)
                        schema['items']['properties'][field] = {
                            'type': field_type,
                            'description': f'Field {field} of type {field_type}'
                        }
        
        elif isinstance(data, dict):
            # Generate schema for object
            schema.update({
                'properties': {}
            })
            
            for field, value in data.items():
                field_type = self._infer_value_type(value)
                schema['properties'][field] = {
                    'type': field_type,
                    'description': f'Field {field} of type {field_type}'
                }
        
        return schema
    
    def _infer_field_type(self, values: List[Any]) -> str:
        """Infer field type from sample values."""
        if not values:
            return 'unknown'
        
        # Check if all values are of the same type
        types = set(type(v).__name__ for v in values if v is not None)
        
        if len(types) == 1:
            return types.pop()
        elif len(types) == 0:
            return 'null'
        else:
            return 'mixed'
    
    def _infer_value_type(self, value: Any) -> str:
        """Infer type of a single value."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return 'unknown'
    
    async def _write_json_file(self, json_data: Dict[str, Any], output_path: str, **kwargs) -> None:
        """Write JSON data to file."""
        encoding = kwargs.get('encoding', 'utf-8')
        pretty_print = kwargs.get('pretty_print', True)
        
        # JSON serialization options
        json_options = {
            'ensure_ascii': kwargs.get('ensure_ascii', False),
            'sort_keys': kwargs.get('sort_keys', True)
        }
        
        if pretty_print:
            json_options.update({
                'indent': kwargs.get('indent', 2),
                'separators': kwargs.get('separators', (',', ': '))
            })
        
        with open(output_path, 'w', encoding=encoding) as f:
            json.dump(json_data, f, **json_options)
    
    def _calculate_json_stats(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics about the JSON data."""
        stats = {
            'total_keys': 0,
            'max_depth': 0,
            'data_record_count': 0
        }
        
        # Count keys and calculate depth
        def analyze_structure(obj, depth=0):
            stats['max_depth'] = max(stats['max_depth'], depth)
            
            if isinstance(obj, dict):
                stats['total_keys'] += len(obj)
                for value in obj.values():
                    analyze_structure(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    analyze_structure(item, depth + 1)
        
        analyze_structure(json_data)
        
        # Count data records
        if 'data' in json_data and isinstance(json_data['data'], list):
            stats['data_record_count'] = len(json_data['data'])
        
        return stats
    
    async def generate_compact_json(self, report_type: str, data: Any, output_path: str,
                                  **kwargs) -> Dict[str, Any]:
        """
        Generate compact JSON without metadata and formatting.
        
        Args:
            report_type: Type of report
            data: Report data
            output_path: Output file path
            **kwargs: Additional parameters
            
        Returns:
            Generation result
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Serialize data directly without metadata wrapper
            serialized_data = await self._serialize_data(data)
            
            # Write compact JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serialized_data, f, separators=(',', ':'), ensure_ascii=False)
            
            # Calculate duration and file size
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            file_size = Path(output_path).stat().st_size
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'format': 'compact',
                'data_type': type(data).__name__
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate compact JSON: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    async def generate_json_lines(self, data: List[Any], output_path: str, **kwargs) -> Dict[str, Any]:
        """
        Generate JSON Lines format (one JSON object per line).
        
        Args:
            data: List of data objects
            output_path: Output file path
            **kwargs: Additional parameters
            
        Returns:
            Generation result
        """
        try:
            if not isinstance(data, list):
                return {
                    'success': False,
                    'error': 'JSON Lines format requires list data',
                    'output_path': output_path
                }
            
            start_time = datetime.now(timezone.utc)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in data:
                    serialized_item = await self._serialize_data(item)
                    json.dump(serialized_item, f, separators=(',', ':'), ensure_ascii=False)
                    f.write('\n')
            
            # Calculate duration and file size
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            file_size = Path(output_path).stat().st_size
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'format': 'json_lines',
                'record_count': len(data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate JSON Lines: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    def validate_json_structure(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate JSON report structure.
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            Validation result
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required top-level fields
        required_fields = ['metadata', 'data']
        for field in required_fields:
            if field not in json_data:
                validation['errors'].append(f"Missing required field: {field}")
                validation['valid'] = False
        
        # Validate metadata structure
        if 'metadata' in json_data:
            metadata = json_data['metadata']
            if not isinstance(metadata, dict):
                validation['errors'].append("Metadata must be an object")
                validation['valid'] = False
            else:
                # Check required metadata fields
                required_metadata = ['report_type', 'generated_at']
                for field in required_metadata:
                    if field not in metadata:
                        validation['warnings'].append(f"Missing recommended metadata field: {field}")
        
        # Check data field
        if 'data' in json_data:
            data = json_data['data']
            if data is None:
                validation['warnings'].append("Data field is null")
        
        return validation
    
    async def merge_json_reports(self, report_paths: List[str], output_path: str,
                               **kwargs) -> Dict[str, Any]:
        """
        Merge multiple JSON reports into a single report.
        
        Args:
            report_paths: List of JSON report file paths
            output_path: Output file path for merged report
            **kwargs: Additional parameters
            
        Returns:
            Merge result
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            merged_data = {
                'metadata': {
                    'report_id': str(uuid.uuid4()),
                    'report_type': 'merged_report',
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'source_reports': len(report_paths),
                    'generator': 'Edge Device Fleet Manager JSON Generator'
                },
                'reports': []
            }
            
            # Load and merge reports
            for report_path in report_paths:
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    merged_data['reports'].append({
                        'source_file': Path(report_path).name,
                        'data': report_data
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load report {report_path}: {e}")
            
            # Write merged report
            await self._write_json_file(merged_data, output_path, **kwargs)
            
            # Calculate duration and file size
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            file_size = Path(output_path).stat().st_size
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'source_reports': len(report_paths),
                'merged_reports': len(merged_data['reports'])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to merge JSON reports: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
