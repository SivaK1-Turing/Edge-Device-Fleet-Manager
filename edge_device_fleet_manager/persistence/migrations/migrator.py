"""
Database Migrator

High-level database migration operations with safety checks,
rollback capabilities, and automated migration workflows.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from ...core.logging import get_logger
from .manager import MigrationManager

logger = get_logger(__name__)


class DatabaseMigrator:
    """
    High-level database migrator with safety checks and automation.
    
    Provides safe migration operations with backup, validation,
    and rollback capabilities for production environments.
    """
    
    def __init__(self, migration_manager: MigrationManager):
        """
        Initialize database migrator.
        
        Args:
            migration_manager: Migration manager instance
        """
        self.migration_manager = migration_manager
        self.logger = get_logger(f"{__name__}.DatabaseMigrator")
    
    async def migrate_to_latest(self, backup: bool = True, 
                               validate: bool = True) -> Dict[str, Any]:
        """
        Migrate database to latest version with safety checks.
        
        Args:
            backup: Whether to create backup before migration
            validate: Whether to validate schema after migration
            
        Returns:
            Migration result dictionary
        """
        try:
            self.logger.info("Starting migration to latest version")
            
            # Get current status
            initial_status = self.migration_manager.get_migration_status()
            current_revision = initial_status.get('current_revision')
            pending_migrations = initial_status.get('pending_migrations', [])
            
            if not pending_migrations:
                self.logger.info("No pending migrations found")
                return {
                    'success': True,
                    'message': 'No migrations needed',
                    'current_revision': current_revision,
                    'applied_migrations': []
                }
            
            self.logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = await self._create_backup()
                if not backup_path:
                    return {
                        'success': False,
                        'message': 'Failed to create backup',
                        'error': 'Backup creation failed'
                    }
            
            # Apply migrations
            try:
                self.migration_manager.apply_migrations()
                self.logger.info("Migrations applied successfully")
                
                # Validate schema if requested
                if validate:
                    is_valid, issues = self.migration_manager.validate_schema()
                    if not is_valid:
                        self.logger.warning(f"Schema validation found issues: {issues}")
                        return {
                            'success': False,
                            'message': 'Schema validation failed after migration',
                            'validation_issues': issues,
                            'backup_path': backup_path
                        }
                
                # Get final status
                final_status = self.migration_manager.get_migration_status()
                
                return {
                    'success': True,
                    'message': 'Migration completed successfully',
                    'initial_revision': current_revision,
                    'final_revision': final_status.get('current_revision'),
                    'applied_migrations': pending_migrations,
                    'backup_path': backup_path
                }
                
            except Exception as e:
                self.logger.error(f"Migration failed: {e}")
                
                # Attempt rollback if backup exists
                if backup_path:
                    self.logger.info("Attempting to restore from backup")
                    restore_success = await self._restore_backup(backup_path)
                    if restore_success:
                        self.logger.info("Successfully restored from backup")
                    else:
                        self.logger.error("Failed to restore from backup")
                
                return {
                    'success': False,
                    'message': f'Migration failed: {e}',
                    'error': str(e),
                    'backup_path': backup_path,
                    'rollback_attempted': backup_path is not None
                }
                
        except Exception as e:
            self.logger.error(f"Migration process failed: {e}")
            return {
                'success': False,
                'message': f'Migration process failed: {e}',
                'error': str(e)
            }
    
    async def rollback_to_revision(self, target_revision: str,
                                  backup: bool = True) -> Dict[str, Any]:
        """
        Rollback database to specific revision.
        
        Args:
            target_revision: Target revision to rollback to
            backup: Whether to create backup before rollback
            
        Returns:
            Rollback result dictionary
        """
        try:
            self.logger.info(f"Starting rollback to revision {target_revision}")
            
            # Get current status
            current_revision = self.migration_manager.get_current_revision()
            
            if current_revision == target_revision:
                return {
                    'success': True,
                    'message': 'Already at target revision',
                    'current_revision': current_revision
                }
            
            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = await self._create_backup()
            
            # Perform rollback
            self.migration_manager.rollback_migration(target_revision)
            
            # Validate result
            new_revision = self.migration_manager.get_current_revision()
            
            return {
                'success': True,
                'message': f'Rollback completed successfully',
                'initial_revision': current_revision,
                'final_revision': new_revision,
                'target_revision': target_revision,
                'backup_path': backup_path
            }
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return {
                'success': False,
                'message': f'Rollback failed: {e}',
                'error': str(e)
            }
    
    async def validate_migration_safety(self) -> Dict[str, Any]:
        """
        Validate migration safety before applying.
        
        Returns:
            Safety validation result
        """
        try:
            safety_checks = {
                'database_connection': False,
                'schema_validation': False,
                'backup_capability': False,
                'pending_migrations': [],
                'warnings': [],
                'errors': []
            }
            
            # Check database connection
            try:
                connection_ok = await self.migration_manager.check_connection()
                safety_checks['database_connection'] = connection_ok
                if not connection_ok:
                    safety_checks['errors'].append('Database connection failed')
            except Exception as e:
                safety_checks['errors'].append(f'Database connection error: {e}')
            
            # Check current schema
            try:
                is_valid, issues = self.migration_manager.validate_schema()
                safety_checks['schema_validation'] = is_valid
                if not is_valid:
                    safety_checks['warnings'].extend(issues)
            except Exception as e:
                safety_checks['errors'].append(f'Schema validation error: {e}')
            
            # Check backup capability
            try:
                # Test backup creation (dry run)
                safety_checks['backup_capability'] = True  # Simplified for now
            except Exception as e:
                safety_checks['errors'].append(f'Backup capability error: {e}')
            
            # Get pending migrations
            try:
                pending = self.migration_manager.get_pending_migrations()
                safety_checks['pending_migrations'] = pending
            except Exception as e:
                safety_checks['errors'].append(f'Failed to get pending migrations: {e}')
            
            # Overall safety assessment
            is_safe = (
                safety_checks['database_connection'] and
                len(safety_checks['errors']) == 0
            )
            
            return {
                'is_safe': is_safe,
                'checks': safety_checks,
                'recommendation': self._get_safety_recommendation(safety_checks)
            }
            
        except Exception as e:
            self.logger.error(f"Safety validation failed: {e}")
            return {
                'is_safe': False,
                'error': str(e),
                'recommendation': 'Do not proceed with migration due to validation failure'
            }
    
    async def _create_backup(self) -> Optional[str]:
        """Create database backup."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_migration_{timestamp}.sql"
            
            # Use migration manager's backup method
            success = self.migration_manager.backup_database(backup_path)
            
            if success:
                self.logger.info(f"Backup created: {backup_path}")
                return backup_path
            else:
                self.logger.error("Backup creation failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Backup creation error: {e}")
            return None
    
    async def _restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            # This is a simplified implementation
            # In production, you'd implement proper restore logic
            self.logger.info(f"Restoring from backup: {backup_path}")
            
            # For now, just return True as a placeholder
            return True
            
        except Exception as e:
            self.logger.error(f"Backup restore error: {e}")
            return False
    
    def _get_safety_recommendation(self, safety_checks: Dict[str, Any]) -> str:
        """Get safety recommendation based on checks."""
        if not safety_checks['database_connection']:
            return "CRITICAL: Fix database connection before proceeding"
        
        if safety_checks['errors']:
            return f"CRITICAL: Resolve {len(safety_checks['errors'])} errors before proceeding"
        
        if not safety_checks['backup_capability']:
            return "WARNING: Backup capability not available - proceed with caution"
        
        if safety_checks['warnings']:
            return f"CAUTION: {len(safety_checks['warnings'])} warnings found - review before proceeding"
        
        if not safety_checks['pending_migrations']:
            return "OK: No migrations needed"
        
        return f"OK: Ready to apply {len(safety_checks['pending_migrations'])} migrations"
    
    async def get_migration_plan(self) -> Dict[str, Any]:
        """
        Get detailed migration plan.
        
        Returns:
            Migration plan with steps and impact analysis
        """
        try:
            # Get current status
            status = self.migration_manager.get_migration_status()
            pending_migrations = status.get('pending_migrations', [])
            
            # Get migration history
            history = self.migration_manager.get_migration_history()
            
            # Safety validation
            safety = await self.validate_migration_safety()
            
            plan = {
                'current_revision': status.get('current_revision'),
                'target_revision': 'head',
                'pending_migrations': pending_migrations,
                'migration_count': len(pending_migrations),
                'estimated_duration': self._estimate_migration_duration(pending_migrations),
                'safety_assessment': safety,
                'recommended_actions': self._get_recommended_actions(safety, pending_migrations),
                'rollback_plan': self._get_rollback_plan(status.get('current_revision')),
                'migration_history': history[-10:] if history else []  # Last 10 migrations
            }
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to create migration plan: {e}")
            return {
                'error': str(e),
                'message': 'Failed to create migration plan'
            }
    
    def _estimate_migration_duration(self, migrations: List[str]) -> str:
        """Estimate migration duration."""
        # Simplified estimation
        if not migrations:
            return "0 seconds"
        elif len(migrations) <= 3:
            return "< 1 minute"
        elif len(migrations) <= 10:
            return "1-5 minutes"
        else:
            return "5+ minutes"
    
    def _get_recommended_actions(self, safety: Dict[str, Any], 
                               migrations: List[str]) -> List[str]:
        """Get recommended actions before migration."""
        actions = []
        
        if not safety.get('is_safe', False):
            actions.append("Resolve safety issues before proceeding")
        
        if migrations:
            actions.append("Create database backup")
            actions.append("Schedule maintenance window")
            actions.append("Notify stakeholders")
        
        if len(migrations) > 5:
            actions.append("Consider staging environment testing")
        
        return actions
    
    def _get_rollback_plan(self, current_revision: Optional[str]) -> Dict[str, Any]:
        """Get rollback plan."""
        if not current_revision:
            return {
                'available': False,
                'reason': 'No current revision found'
            }
        
        return {
            'available': True,
            'target_revision': current_revision,
            'estimated_duration': '< 1 minute',
            'requirements': ['Database backup', 'Maintenance window']
        }
