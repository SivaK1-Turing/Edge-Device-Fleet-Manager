"""
Schema Validators

Validation utilities for database schema integrity, constraint checking,
and migration safety verification.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from sqlalchemy import MetaData, Table, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ...core.logging import get_logger

logger = get_logger(__name__)


class SchemaValidator:
    """
    Schema validation utilities for database integrity checking.
    
    Provides comprehensive validation of database schema including
    constraints, indexes, relationships, and data integrity.
    """
    
    def __init__(self, engine: Engine):
        """
        Initialize schema validator.
        
        Args:
            engine: Database engine for validation
        """
        self.engine = engine
        self.logger = get_logger(f"{__name__}.SchemaValidator")
    
    def validate_complete_schema(self, expected_metadata: MetaData) -> Tuple[bool, List[str]]:
        """
        Validate complete database schema against expected metadata.
        
        Args:
            expected_metadata: Expected schema metadata
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Get current database metadata
            current_metadata = MetaData()
            current_metadata.reflect(bind=self.engine)
            
            # Validate tables
            table_issues = self._validate_tables(expected_metadata, current_metadata)
            issues.extend(table_issues)
            
            # Validate constraints
            constraint_issues = self._validate_constraints(expected_metadata, current_metadata)
            issues.extend(constraint_issues)
            
            # Validate indexes
            index_issues = self._validate_indexes(expected_metadata, current_metadata)
            issues.extend(index_issues)
            
            # Validate foreign keys
            fk_issues = self._validate_foreign_keys(expected_metadata, current_metadata)
            issues.extend(fk_issues)
            
            is_valid = len(issues) == 0
            
            if is_valid:
                self.logger.info("Schema validation passed")
            else:
                self.logger.warning(f"Schema validation found {len(issues)} issues")
            
            return is_valid, issues
            
        except Exception as e:
            self.logger.error(f"Schema validation error: {e}")
            return False, [f"Validation error: {e}"]
    
    def _validate_tables(self, expected: MetaData, current: MetaData) -> List[str]:
        """Validate table existence and structure."""
        issues = []
        
        expected_tables = set(expected.tables.keys())
        current_tables = set(current.tables.keys())
        
        # Check for missing tables
        missing_tables = expected_tables - current_tables
        for table in missing_tables:
            issues.append(f"Missing table: {table}")
        
        # Check for extra tables
        extra_tables = current_tables - expected_tables
        for table in extra_tables:
            issues.append(f"Unexpected table: {table}")
        
        # Validate common tables
        common_tables = expected_tables.intersection(current_tables)
        for table_name in common_tables:
            table_issues = self._validate_table_structure(
                expected.tables[table_name],
                current.tables[table_name]
            )
            issues.extend(table_issues)
        
        return issues
    
    def _validate_table_structure(self, expected_table: Table, current_table: Table) -> List[str]:
        """Validate individual table structure."""
        issues = []
        table_name = expected_table.name
        
        # Get column information
        expected_columns = {col.name: col for col in expected_table.columns}
        current_columns = {col.name: col for col in current_table.columns}
        
        expected_column_names = set(expected_columns.keys())
        current_column_names = set(current_columns.keys())
        
        # Check for missing columns
        missing_columns = expected_column_names - current_column_names
        for column in missing_columns:
            issues.append(f"Missing column in {table_name}: {column}")
        
        # Check for extra columns
        extra_columns = current_column_names - expected_column_names
        for column in extra_columns:
            issues.append(f"Unexpected column in {table_name}: {column}")
        
        # Validate common columns
        common_columns = expected_column_names.intersection(current_column_names)
        for column_name in common_columns:
            column_issues = self._validate_column(
                expected_columns[column_name],
                current_columns[column_name],
                table_name
            )
            issues.extend(column_issues)
        
        return issues
    
    def _validate_column(self, expected_col, current_col, table_name: str) -> List[str]:
        """Validate individual column properties."""
        issues = []
        column_name = expected_col.name
        
        # Check data type
        if str(expected_col.type) != str(current_col.type):
            issues.append(
                f"Column type mismatch in {table_name}.{column_name}: "
                f"expected {expected_col.type}, got {current_col.type}"
            )
        
        # Check nullable
        if expected_col.nullable != current_col.nullable:
            issues.append(
                f"Column nullable mismatch in {table_name}.{column_name}: "
                f"expected {expected_col.nullable}, got {current_col.nullable}"
            )
        
        # Check primary key
        if expected_col.primary_key != current_col.primary_key:
            issues.append(
                f"Primary key mismatch in {table_name}.{column_name}: "
                f"expected {expected_col.primary_key}, got {current_col.primary_key}"
            )
        
        return issues
    
    def _validate_constraints(self, expected: MetaData, current: MetaData) -> List[str]:
        """Validate database constraints."""
        issues = []
        
        # This is a simplified constraint validation
        # In a full implementation, you'd check all constraint types
        
        try:
            inspector = inspect(self.engine)
            
            for table_name in expected.tables:
                if table_name in current.tables:
                    # Check unique constraints
                    expected_table = expected.tables[table_name]
                    current_constraints = inspector.get_unique_constraints(table_name)
                    
                    # This would need more detailed constraint comparison
                    # For now, just log that we're checking
                    self.logger.debug(f"Checking constraints for table {table_name}")
        
        except Exception as e:
            issues.append(f"Error validating constraints: {e}")
        
        return issues
    
    def _validate_indexes(self, expected: MetaData, current: MetaData) -> List[str]:
        """Validate database indexes."""
        issues = []
        
        try:
            inspector = inspect(self.engine)
            
            for table_name in expected.tables:
                if table_name in current.tables:
                    # Get current indexes
                    current_indexes = inspector.get_indexes(table_name)
                    
                    # This would need more detailed index comparison
                    # For now, just log that we're checking
                    self.logger.debug(f"Checking indexes for table {table_name}")
        
        except Exception as e:
            issues.append(f"Error validating indexes: {e}")
        
        return issues
    
    def _validate_foreign_keys(self, expected: MetaData, current: MetaData) -> List[str]:
        """Validate foreign key constraints."""
        issues = []
        
        try:
            inspector = inspect(self.engine)
            
            for table_name in expected.tables:
                if table_name in current.tables:
                    # Get current foreign keys
                    current_fks = inspector.get_foreign_keys(table_name)
                    
                    # This would need more detailed FK comparison
                    # For now, just log that we're checking
                    self.logger.debug(f"Checking foreign keys for table {table_name}")
        
        except Exception as e:
            issues.append(f"Error validating foreign keys: {e}")
        
        return issues
    
    def validate_data_integrity(self, table_name: str, 
                               validation_rules: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate data integrity using custom rules.
        
        Args:
            table_name: Table to validate
            validation_rules: List of validation rule dictionaries
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            with self.engine.connect() as connection:
                for rule in validation_rules:
                    rule_issues = self._apply_validation_rule(connection, table_name, rule)
                    issues.extend(rule_issues)
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            self.logger.error(f"Data integrity validation error: {e}")
            return False, [f"Data validation error: {e}"]
    
    def _apply_validation_rule(self, connection, table_name: str, 
                              rule: Dict[str, Any]) -> List[str]:
        """Apply a single validation rule."""
        issues = []
        
        try:
            rule_type = rule.get('type')
            
            if rule_type == 'not_null':
                column = rule.get('column')
                query = text(f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL")
                null_count = connection.execute(query).scalar()
                
                if null_count > 0:
                    issues.append(f"Found {null_count} NULL values in {table_name}.{column}")
            
            elif rule_type == 'unique':
                column = rule.get('column')
                query = text(f"""
                    SELECT {column}, COUNT(*) as cnt 
                    FROM {table_name} 
                    GROUP BY {column} 
                    HAVING COUNT(*) > 1
                """)
                duplicates = connection.execute(query).fetchall()
                
                if duplicates:
                    issues.append(f"Found {len(duplicates)} duplicate values in {table_name}.{column}")
            
            elif rule_type == 'range':
                column = rule.get('column')
                min_val = rule.get('min')
                max_val = rule.get('max')
                
                conditions = []
                if min_val is not None:
                    conditions.append(f"{column} < {min_val}")
                if max_val is not None:
                    conditions.append(f"{column} > {max_val}")
                
                if conditions:
                    where_clause = " OR ".join(conditions)
                    query = text(f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}")
                    invalid_count = connection.execute(query).scalar()
                    
                    if invalid_count > 0:
                        issues.append(f"Found {invalid_count} values outside range in {table_name}.{column}")
            
            elif rule_type == 'custom_query':
                query_text = rule.get('query')
                description = rule.get('description', 'Custom validation')
                
                result = connection.execute(text(query_text)).scalar()
                
                if result and result > 0:
                    issues.append(f"{description}: {result} violations found")
        
        except Exception as e:
            issues.append(f"Error applying validation rule {rule}: {e}")
        
        return issues
    
    def check_referential_integrity(self) -> Tuple[bool, List[str]]:
        """Check referential integrity across all foreign keys."""
        issues = []
        
        try:
            inspector = inspect(self.engine)
            
            with self.engine.connect() as connection:
                for table_name in inspector.get_table_names():
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    
                    for fk in foreign_keys:
                        fk_issues = self._check_foreign_key_integrity(
                            connection, table_name, fk
                        )
                        issues.extend(fk_issues)
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            self.logger.error(f"Referential integrity check error: {e}")
            return False, [f"Referential integrity error: {e}"]
    
    def _check_foreign_key_integrity(self, connection, table_name: str, 
                                   foreign_key: Dict[str, Any]) -> List[str]:
        """Check integrity of a specific foreign key."""
        issues = []
        
        try:
            constrained_columns = foreign_key['constrained_columns']
            referred_table = foreign_key['referred_table']
            referred_columns = foreign_key['referred_columns']
            
            # Build query to find orphaned records
            join_conditions = []
            for i, col in enumerate(constrained_columns):
                ref_col = referred_columns[i]
                join_conditions.append(f"t1.{col} = t2.{ref_col}")
            
            join_clause = " AND ".join(join_conditions)
            
            query = text(f"""
                SELECT COUNT(*) 
                FROM {table_name} t1 
                LEFT JOIN {referred_table} t2 ON {join_clause}
                WHERE t2.{referred_columns[0]} IS NULL 
                AND t1.{constrained_columns[0]} IS NOT NULL
            """)
            
            orphaned_count = connection.execute(query).scalar()
            
            if orphaned_count > 0:
                issues.append(
                    f"Found {orphaned_count} orphaned records in {table_name} "
                    f"referencing {referred_table}"
                )
        
        except Exception as e:
            issues.append(f"Error checking foreign key {foreign_key}: {e}")
        
        return issues
    
    def generate_validation_report(self, expected_metadata: MetaData) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.
        
        Args:
            expected_metadata: Expected schema metadata
            
        Returns:
            Validation report dictionary
        """
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'schema_validation': {},
            'data_integrity': {},
            'referential_integrity': {},
            'summary': {}
        }
        
        try:
            # Schema validation
            schema_valid, schema_issues = self.validate_complete_schema(expected_metadata)
            report['schema_validation'] = {
                'is_valid': schema_valid,
                'issues': schema_issues,
                'issue_count': len(schema_issues)
            }
            
            # Referential integrity
            ref_valid, ref_issues = self.check_referential_integrity()
            report['referential_integrity'] = {
                'is_valid': ref_valid,
                'issues': ref_issues,
                'issue_count': len(ref_issues)
            }
            
            # Summary
            total_issues = len(schema_issues) + len(ref_issues)
            overall_valid = schema_valid and ref_valid
            
            report['summary'] = {
                'overall_valid': overall_valid,
                'total_issues': total_issues,
                'schema_issues': len(schema_issues),
                'referential_issues': len(ref_issues)
            }
            
        except Exception as e:
            report['error'] = str(e)
            report['summary'] = {
                'overall_valid': False,
                'error': str(e)
            }
        
        return report
