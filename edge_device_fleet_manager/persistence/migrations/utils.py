"""
Migration Utilities

Utility functions and helpers for database migrations including
data migration helpers, schema comparison, and migration validation.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import MetaData, Table, Column, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from ...core.logging import get_logger

logger = get_logger(__name__)


class MigrationUtils:
    """
    Utility class for migration operations and data transformations.
    
    Provides helper methods for common migration tasks including
    data migration, schema comparison, and validation utilities.
    """
    
    @staticmethod
    def compare_schemas(source_metadata: MetaData, 
                       target_metadata: MetaData) -> Dict[str, Any]:
        """
        Compare two database schemas and return differences.
        
        Args:
            source_metadata: Source schema metadata
            target_metadata: Target schema metadata
            
        Returns:
            Dictionary containing schema differences
        """
        differences = {
            'missing_tables': [],
            'extra_tables': [],
            'table_differences': {},
            'missing_columns': {},
            'extra_columns': {},
            'column_differences': {}
        }
        
        source_tables = set(source_metadata.tables.keys())
        target_tables = set(target_metadata.tables.keys())
        
        # Find missing and extra tables
        differences['missing_tables'] = list(target_tables - source_tables)
        differences['extra_tables'] = list(source_tables - target_tables)
        
        # Compare common tables
        common_tables = source_tables.intersection(target_tables)
        
        for table_name in common_tables:
            source_table = source_metadata.tables[table_name]
            target_table = target_metadata.tables[table_name]
            
            table_diff = MigrationUtils._compare_tables(source_table, target_table)
            if table_diff:
                differences['table_differences'][table_name] = table_diff
        
        return differences
    
    @staticmethod
    def _compare_tables(source_table: Table, target_table: Table) -> Dict[str, Any]:
        """Compare two tables and return differences."""
        differences = {
            'missing_columns': [],
            'extra_columns': [],
            'column_differences': {}
        }
        
        source_columns = {col.name: col for col in source_table.columns}
        target_columns = {col.name: col for col in target_table.columns}
        
        source_column_names = set(source_columns.keys())
        target_column_names = set(target_columns.keys())
        
        # Find missing and extra columns
        differences['missing_columns'] = list(target_column_names - source_column_names)
        differences['extra_columns'] = list(source_column_names - target_column_names)
        
        # Compare common columns
        common_columns = source_column_names.intersection(target_column_names)
        
        for column_name in common_columns:
            source_col = source_columns[column_name]
            target_col = target_columns[column_name]
            
            col_diff = MigrationUtils._compare_columns(source_col, target_col)
            if col_diff:
                differences['column_differences'][column_name] = col_diff
        
        # Remove empty sections
        return {k: v for k, v in differences.items() if v}
    
    @staticmethod
    def _compare_columns(source_col: Column, target_col: Column) -> Dict[str, Any]:
        """Compare two columns and return differences."""
        differences = {}
        
        # Compare types
        if str(source_col.type) != str(target_col.type):
            differences['type_change'] = {
                'from': str(source_col.type),
                'to': str(target_col.type)
            }
        
        # Compare nullable
        if source_col.nullable != target_col.nullable:
            differences['nullable_change'] = {
                'from': source_col.nullable,
                'to': target_col.nullable
            }
        
        # Compare default values
        source_default = str(source_col.default) if source_col.default else None
        target_default = str(target_col.default) if target_col.default else None
        
        if source_default != target_default:
            differences['default_change'] = {
                'from': source_default,
                'to': target_default
            }
        
        return differences
    
    @staticmethod
    def generate_migration_script(differences: Dict[str, Any], 
                                 migration_name: str) -> str:
        """
        Generate Alembic migration script from schema differences.
        
        Args:
            differences: Schema differences from compare_schemas
            migration_name: Name for the migration
            
        Returns:
            Generated migration script content
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        script_template = f'''"""
{migration_name}

Revision ID: {timestamp}
Revises: 
Create Date: {datetime.now(timezone.utc).isoformat()}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
{MigrationUtils._generate_upgrade_operations(differences)}


def downgrade() -> None:
    """Downgrade database schema."""
{MigrationUtils._generate_downgrade_operations(differences)}
'''
        
        return script_template
    
    @staticmethod
    def _generate_upgrade_operations(differences: Dict[str, Any]) -> str:
        """Generate upgrade operations from differences."""
        operations = []
        
        # Create missing tables
        for table_name in differences.get('missing_tables', []):
            operations.append(f"    # TODO: Create table {table_name}")
            operations.append(f"    # op.create_table('{table_name}', ...)")
        
        # Add missing columns
        for table_name, table_diff in differences.get('table_differences', {}).items():
            for column_name in table_diff.get('missing_columns', []):
                operations.append(f"    # TODO: Add column {column_name} to {table_name}")
                operations.append(f"    # op.add_column('{table_name}', sa.Column('{column_name}', ...))")
        
        # Drop extra tables
        for table_name in differences.get('extra_tables', []):
            operations.append(f"    # TODO: Drop table {table_name}")
            operations.append(f"    # op.drop_table('{table_name}')")
        
        if not operations:
            operations.append("    pass")
        
        return '\n'.join(operations)
    
    @staticmethod
    def _generate_downgrade_operations(differences: Dict[str, Any]) -> str:
        """Generate downgrade operations from differences."""
        operations = []
        
        # Reverse the upgrade operations
        for table_name in differences.get('extra_tables', []):
            operations.append(f"    # TODO: Recreate table {table_name}")
            operations.append(f"    # op.create_table('{table_name}', ...)")
        
        for table_name, table_diff in differences.get('table_differences', {}).items():
            for column_name in table_diff.get('missing_columns', []):
                operations.append(f"    # TODO: Drop column {column_name} from {table_name}")
                operations.append(f"    # op.drop_column('{table_name}', '{column_name}')")
        
        for table_name in differences.get('missing_tables', []):
            operations.append(f"    # TODO: Drop table {table_name}")
            operations.append(f"    # op.drop_table('{table_name}')")
        
        if not operations:
            operations.append("    pass")
        
        return '\n'.join(operations)
    
    @staticmethod
    def validate_migration_data(engine: Engine, 
                               validation_queries: List[str]) -> List[Dict[str, Any]]:
        """
        Validate data after migration using custom queries.
        
        Args:
            engine: Database engine
            validation_queries: List of SQL queries for validation
            
        Returns:
            List of validation results
        """
        results = []
        
        with engine.connect() as connection:
            for i, query in enumerate(validation_queries):
                try:
                    result = connection.execute(text(query))
                    rows = result.fetchall()
                    
                    results.append({
                        'query_index': i,
                        'query': query,
                        'success': True,
                        'row_count': len(rows),
                        'sample_data': [dict(row) for row in rows[:5]]  # First 5 rows
                    })
                    
                except Exception as e:
                    results.append({
                        'query_index': i,
                        'query': query,
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    @staticmethod
    def create_data_migration_script(source_table: str, 
                                   target_table: str,
                                   column_mapping: Dict[str, str],
                                   transformation_functions: Optional[Dict[str, str]] = None) -> str:
        """
        Create data migration script for moving data between tables.
        
        Args:
            source_table: Source table name
            target_table: Target table name
            column_mapping: Mapping of source columns to target columns
            transformation_functions: Optional transformation functions for columns
            
        Returns:
            Data migration script
        """
        transformations = transformation_functions or {}
        
        # Build SELECT clause
        select_columns = []
        for source_col, target_col in column_mapping.items():
            if source_col in transformations:
                select_columns.append(f"{transformations[source_col]} AS {target_col}")
            else:
                select_columns.append(f"{source_col} AS {target_col}")
        
        select_clause = ', '.join(select_columns)
        target_columns = ', '.join(column_mapping.values())
        
        script = f"""
-- Data migration from {source_table} to {target_table}
INSERT INTO {target_table} ({target_columns})
SELECT {select_clause}
FROM {source_table};
"""
        
        return script
    
    @staticmethod
    def backup_table_data(engine: Engine, table_name: str, 
                         backup_file: str) -> bool:
        """
        Backup table data to JSON file.
        
        Args:
            engine: Database engine
            table_name: Table to backup
            backup_file: Backup file path
            
        Returns:
            True if backup successful
        """
        try:
            with engine.connect() as connection:
                # Get table metadata
                inspector = inspect(engine)
                columns = inspector.get_columns(table_name)
                column_names = [col['name'] for col in columns]
                
                # Query all data
                query = text(f"SELECT * FROM {table_name}")
                result = connection.execute(query)
                rows = result.fetchall()
                
                # Convert to JSON-serializable format
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        column_name = column_names[i]
                        # Handle datetime objects
                        if isinstance(value, datetime):
                            row_dict[column_name] = value.isoformat()
                        else:
                            row_dict[column_name] = value
                    data.append(row_dict)
                
                # Write to file
                backup_data = {
                    'table_name': table_name,
                    'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                    'row_count': len(data),
                    'columns': column_names,
                    'data': data
                }
                
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                logger.info(f"Backed up {len(data)} rows from {table_name} to {backup_file}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to backup table {table_name}: {e}")
            return False
    
    @staticmethod
    def restore_table_data(engine: Engine, backup_file: str) -> bool:
        """
        Restore table data from JSON backup file.
        
        Args:
            engine: Database engine
            backup_file: Backup file path
            
        Returns:
            True if restore successful
        """
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            table_name = backup_data['table_name']
            data = backup_data['data']
            
            if not data:
                logger.info(f"No data to restore for table {table_name}")
                return True
            
            # Build INSERT statement
            columns = list(data[0].keys())
            column_list = ', '.join(columns)
            placeholders = ', '.join([f":{col}" for col in columns])
            
            insert_query = text(f"""
                INSERT INTO {table_name} ({column_list})
                VALUES ({placeholders})
            """)
            
            with engine.connect() as connection:
                with connection.begin():
                    # Clear existing data
                    connection.execute(text(f"DELETE FROM {table_name}"))
                    
                    # Insert backup data
                    connection.execute(insert_query, data)
            
            logger.info(f"Restored {len(data)} rows to {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup {backup_file}: {e}")
            return False
    
    @staticmethod
    def get_table_statistics(engine: Engine, table_name: str) -> Dict[str, Any]:
        """
        Get statistics for a table.
        
        Args:
            engine: Database engine
            table_name: Table name
            
        Returns:
            Table statistics
        """
        try:
            with engine.connect() as connection:
                # Row count
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                row_count = connection.execute(count_query).scalar()
                
                # Table size (database-specific)
                # This is a simplified version
                stats = {
                    'table_name': table_name,
                    'row_count': row_count,
                    'estimated_size': 'N/A'  # Would need database-specific queries
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get statistics for table {table_name}: {e}")
            return {
                'table_name': table_name,
                'error': str(e)
            }
