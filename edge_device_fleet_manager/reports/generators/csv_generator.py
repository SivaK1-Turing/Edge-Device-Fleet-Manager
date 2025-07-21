"""
CSV Report Generator

Generates CSV reports with tabular data export, custom formatting,
and support for large datasets.
"""

import asyncio
import csv
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import io

from ...core.logging import get_logger

logger = get_logger(__name__)


class CSVReportGenerator:
    """
    CSV report generator.
    
    Creates CSV reports with proper formatting, headers, and support
    for various data structures and large datasets.
    """
    
    def __init__(self):
        """Initialize CSV report generator."""
        self.logger = get_logger(f"{__name__}.CSVReportGenerator")
    
    async def generate(self, report_type: str, data: Any, output_path: str,
                      template: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate CSV report.
        
        Args:
            report_type: Type of report to generate
            data: Report data
            output_path: Output file path
            template: Optional template (not used for CSV)
            **kwargs: Additional generation parameters
            
        Returns:
            Generation result
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Convert data to CSV format
            csv_data = await self._prepare_csv_data(report_type, data, **kwargs)
            
            # Write CSV file
            await self._write_csv_file(csv_data, output_path, **kwargs)
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get file size
            file_size = Path(output_path).stat().st_size
            
            # Count rows and columns
            row_count = len(csv_data) - 1 if csv_data else 0  # Subtract header row
            col_count = len(csv_data[0]) if csv_data else 0
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'row_count': row_count,
                'column_count': col_count,
                'encoding': kwargs.get('encoding', 'utf-8')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate CSV report: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    async def _prepare_csv_data(self, report_type: str, data: Any, **kwargs) -> List[List[str]]:
        """Prepare data for CSV export."""
        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # List of dictionaries - standard case
                return await self._dict_list_to_csv(data, **kwargs)
            else:
                # List of other types
                return await self._simple_list_to_csv(data, **kwargs)
        
        elif isinstance(data, dict):
            # Single dictionary or nested structure
            return await self._dict_to_csv(data, **kwargs)
        
        else:
            # Other data types
            return await self._generic_to_csv(data, report_type, **kwargs)
    
    async def _dict_list_to_csv(self, data: List[Dict[str, Any]], **kwargs) -> List[List[str]]:
        """Convert list of dictionaries to CSV format."""
        if not data:
            return []
        
        # Get all unique keys from all dictionaries
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        
        # Sort keys for consistent column order
        columns = kwargs.get('columns', sorted(all_keys))
        
        # Create header row
        csv_data = [columns]
        
        # Add data rows
        for item in data:
            row = []
            for column in columns:
                value = item.get(column, '')
                
                # Convert value to string
                if value is None:
                    row.append('')
                elif isinstance(value, (dict, list)):
                    # Convert complex types to JSON string
                    import json
                    row.append(json.dumps(value))
                elif isinstance(value, datetime):
                    # Format datetime
                    row.append(value.isoformat())
                else:
                    row.append(str(value))
            
            csv_data.append(row)
        
        return csv_data
    
    async def _simple_list_to_csv(self, data: List[Any], **kwargs) -> List[List[str]]:
        """Convert simple list to CSV format."""
        # Create single column CSV
        column_name = kwargs.get('column_name', 'Value')
        csv_data = [[column_name]]
        
        for item in data:
            if isinstance(item, (dict, list)):
                import json
                csv_data.append([json.dumps(item)])
            else:
                csv_data.append([str(item)])
        
        return csv_data
    
    async def _dict_to_csv(self, data: Dict[str, Any], **kwargs) -> List[List[str]]:
        """Convert dictionary to CSV format."""
        # Create key-value CSV
        csv_data = [['Key', 'Value']]
        
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                import json
                csv_data.append([str(key), json.dumps(value)])
            elif isinstance(value, datetime):
                csv_data.append([str(key), value.isoformat()])
            else:
                csv_data.append([str(key), str(value)])
        
        return csv_data
    
    async def _generic_to_csv(self, data: Any, report_type: str, **kwargs) -> List[List[str]]:
        """Convert generic data to CSV format."""
        # Create simple representation
        csv_data = [['Report Type', 'Data Type', 'Value']]
        
        data_type = type(data).__name__
        value_str = str(data)
        
        # Limit value string length
        if len(value_str) > 1000:
            value_str = value_str[:997] + '...'
        
        csv_data.append([report_type, data_type, value_str])
        
        return csv_data
    
    async def _write_csv_file(self, csv_data: List[List[str]], output_path: str, **kwargs) -> None:
        """Write CSV data to file."""
        encoding = kwargs.get('encoding', 'utf-8')
        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        
        # Handle quoting parameter
        if isinstance(quoting, str):
            quoting_map = {
                'minimal': csv.QUOTE_MINIMAL,
                'all': csv.QUOTE_ALL,
                'nonnumeric': csv.QUOTE_NONNUMERIC,
                'none': csv.QUOTE_NONE
            }
            quoting = quoting_map.get(quoting.lower(), csv.QUOTE_MINIMAL)
        
        with open(output_path, 'w', newline='', encoding=encoding) as csvfile:
            writer = csv.writer(
                csvfile,
                delimiter=delimiter,
                quotechar=quotechar,
                quoting=quoting
            )
            
            # Write header comment if requested
            if kwargs.get('include_metadata', True):
                # Write metadata as comments (if supported by reader)
                metadata_comment = f"# Generated by Edge Device Fleet Manager on {datetime.now(timezone.utc).isoformat()}"
                csvfile.write(metadata_comment + '\n')
            
            # Write CSV data
            writer.writerows(csv_data)
    
    async def generate_multi_sheet_csv(self, report_data: Dict[str, Any], output_directory: str,
                                     **kwargs) -> Dict[str, Any]:
        """
        Generate multiple CSV files for different data sections.
        
        Args:
            report_data: Dictionary with different data sections
            output_directory: Directory to save CSV files
            **kwargs: Additional generation parameters
            
        Returns:
            Generation result with file information
        """
        try:
            start_time = datetime.now(timezone.utc)
            output_dir = Path(output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            generated_files = []
            total_size = 0
            
            for section_name, section_data in report_data.items():
                # Generate filename
                safe_name = section_name.replace(' ', '_').replace('/', '_')
                csv_filename = f"{safe_name}.csv"
                csv_path = output_dir / csv_filename
                
                # Generate CSV for this section
                result = await self.generate(
                    report_type=section_name,
                    data=section_data,
                    output_path=str(csv_path),
                    **kwargs
                )
                
                if result['success']:
                    generated_files.append({
                        'section': section_name,
                        'filename': csv_filename,
                        'path': str(csv_path),
                        'size_bytes': result['file_size_bytes'],
                        'row_count': result.get('row_count', 0),
                        'column_count': result.get('column_count', 0)
                    })
                    total_size += result['file_size_bytes']
                else:
                    self.logger.error(f"Failed to generate CSV for section {section_name}: {result.get('error')}")
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'success': len(generated_files) > 0,
                'output_directory': str(output_dir),
                'generated_files': generated_files,
                'total_files': len(generated_files),
                'total_size_bytes': total_size,
                'duration_seconds': duration
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate multi-sheet CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_directory': output_directory
            }
    
    async def generate_summary_csv(self, data: List[Dict[str, Any]], output_path: str,
                                 summary_fields: List[str], **kwargs) -> Dict[str, Any]:
        """
        Generate summary CSV with aggregated data.
        
        Args:
            data: Source data
            output_path: Output file path
            summary_fields: Fields to include in summary
            **kwargs: Additional parameters
            
        Returns:
            Generation result
        """
        try:
            if not data or not summary_fields:
                return {
                    'success': False,
                    'error': 'No data or summary fields provided',
                    'output_path': output_path
                }
            
            # Create summary data
            summary_data = []
            
            # Group by specified fields and calculate counts
            from collections import defaultdict
            groups = defaultdict(int)
            
            for item in data:
                # Create group key from summary fields
                group_key = tuple(str(item.get(field, '')) for field in summary_fields)
                groups[group_key] += 1
            
            # Convert to list format
            header = summary_fields + ['Count']
            summary_data.append(header)
            
            for group_key, count in groups.items():
                row = list(group_key) + [str(count)]
                summary_data.append(row)
            
            # Write summary CSV
            await self._write_csv_file(summary_data, output_path, **kwargs)
            
            # Get file info
            file_size = Path(output_path).stat().st_size
            row_count = len(summary_data) - 1  # Subtract header
            
            return {
                'success': True,
                'output_path': output_path,
                'file_size_bytes': file_size,
                'row_count': row_count,
                'column_count': len(header),
                'summary_fields': summary_fields,
                'unique_groups': len(groups)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'output_path': output_path
            }
    
    def validate_csv_data(self, data: List[List[str]]) -> Dict[str, Any]:
        """
        Validate CSV data structure.
        
        Args:
            data: CSV data as list of lists
            
        Returns:
            Validation result
        """
        if not data:
            return {
                'valid': False,
                'error': 'No data provided'
            }
        
        if not isinstance(data, list):
            return {
                'valid': False,
                'error': 'Data must be a list'
            }
        
        # Check if all rows have the same number of columns
        if data:
            expected_columns = len(data[0])
            for i, row in enumerate(data):
                if not isinstance(row, list):
                    return {
                        'valid': False,
                        'error': f'Row {i} is not a list'
                    }
                
                if len(row) != expected_columns:
                    return {
                        'valid': False,
                        'error': f'Row {i} has {len(row)} columns, expected {expected_columns}'
                    }
        
        return {
            'valid': True,
            'row_count': len(data),
            'column_count': len(data[0]) if data else 0
        }
    
    async def convert_to_excel_compatible(self, csv_path: str, excel_path: str) -> Dict[str, Any]:
        """
        Convert CSV to Excel-compatible format.
        
        Args:
            csv_path: Source CSV file path
            excel_path: Target Excel file path
            
        Returns:
            Conversion result
        """
        try:
            # Check if pandas and openpyxl are available
            try:
                import pandas as pd
            except ImportError:
                return {
                    'success': False,
                    'error': 'pandas required for Excel conversion'
                }
            
            # Read CSV and write Excel
            df = pd.read_csv(csv_path)
            df.to_excel(excel_path, index=False)
            
            # Get file info
            excel_size = Path(excel_path).stat().st_size
            
            return {
                'success': True,
                'csv_path': csv_path,
                'excel_path': excel_path,
                'excel_size_bytes': excel_size,
                'row_count': len(df),
                'column_count': len(df.columns)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to convert CSV to Excel: {e}")
            return {
                'success': False,
                'error': str(e),
                'csv_path': csv_path,
                'excel_path': excel_path
            }
