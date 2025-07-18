"""
Migration Manager

Comprehensive migration management system with Alembic integration,
version control, and automated schema management capabilities.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import subprocess
import tempfile

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ...core.logging import get_logger
from ..models.base import Base

logger = get_logger(__name__)


class MigrationManager:
    """
    Comprehensive migration manager for database schema management.
    
    Provides high-level interface for migration operations including
    generation, application, rollback, and validation.
    """
    
    def __init__(self, database_url: str, migrations_dir: Optional[str] = None):
        """
        Initialize migration manager.
        
        Args:
            database_url: Database connection URL
            migrations_dir: Directory containing migration files
        """
        self.database_url = database_url
        self.migrations_dir = migrations_dir or self._get_default_migrations_dir()
        self.engine = create_engine(database_url)
        self.alembic_cfg = self._setup_alembic_config()
        
        logger.info(f"Migration manager initialized for {database_url}")
    
    def _get_default_migrations_dir(self) -> str:
        """Get default migrations directory."""
        current_dir = Path(__file__).parent
        return str(current_dir / "versions")
    
    def _setup_alembic_config(self) -> Config:
        """Setup Alembic configuration."""
        # Create alembic.ini content
        alembic_ini_content = f"""
[alembic]
script_location = {self.migrations_dir}
sqlalchemy.url = {self.database_url}
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %%(levelname)-5.5s [%%(name)s] %%(message)s
datefmt = %%H:%%M:%%S
"""
        
        # Create temporary alembic.ini file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(alembic_ini_content)
            alembic_ini_path = f.name
        
        # Setup Alembic config
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", self.migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        
        return alembic_cfg
    
    def initialize_migrations(self) -> None:
        """Initialize migration environment."""
        try:
            # Create migrations directory if it doesn't exist
            os.makedirs(self.migrations_dir, exist_ok=True)
            
            # Initialize Alembic
            command.init(self.alembic_cfg, self.migrations_dir)
            
            # Create env.py with our configuration
            self._create_env_py()
            
            logger.info("Migration environment initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize migrations: {e}")
            raise
    
    def _create_env_py(self) -> None:
        """Create custom env.py for Alembic."""
        env_py_content = '''"""
Alembic environment configuration for Edge Device Fleet Manager.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import all models to ensure they're registered with SQLAlchemy
from edge_device_fleet_manager.persistence.models.base import Base
from edge_device_fleet_manager.persistence.models import *

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        
        env_py_path = os.path.join(self.migrations_dir, "env.py")
        with open(env_py_path, 'w') as f:
            f.write(env_py_content)
    
    def generate_migration(self, message: str, auto: bool = True) -> str:
        """
        Generate a new migration.
        
        Args:
            message: Migration message/description
            auto: Whether to auto-generate from model changes
            
        Returns:
            Path to the generated migration file
        """
        try:
            if auto:
                # Auto-generate migration from model changes
                command.revision(
                    self.alembic_cfg,
                    message=message,
                    autogenerate=True
                )
            else:
                # Create empty migration
                command.revision(
                    self.alembic_cfg,
                    message=message
                )
            
            # Get the latest revision
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            latest_revision = script_dir.get_current_head()
            
            logger.info(f"Generated migration: {latest_revision} - {message}")
            return latest_revision
            
        except Exception as e:
            logger.error(f"Failed to generate migration: {e}")
            raise
    
    def apply_migrations(self, target_revision: Optional[str] = None) -> None:
        """
        Apply migrations to the database.
        
        Args:
            target_revision: Target revision to migrate to (latest if None)
        """
        try:
            if target_revision:
                command.upgrade(self.alembic_cfg, target_revision)
                logger.info(f"Applied migrations up to revision: {target_revision}")
            else:
                command.upgrade(self.alembic_cfg, "head")
                logger.info("Applied all pending migrations")
                
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")
            raise
    
    def rollback_migration(self, target_revision: str) -> None:
        """
        Rollback to a specific migration.
        
        Args:
            target_revision: Target revision to rollback to
        """
        try:
            command.downgrade(self.alembic_cfg, target_revision)
            logger.info(f"Rolled back to revision: {target_revision}")
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            with self.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
                
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []
            
            for revision in script_dir.walk_revisions():
                revisions.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'branch_labels': revision.branch_labels,
                    'depends_on': revision.depends_on,
                    'doc': revision.doc,
                    'module_path': revision.path
                })
            
            return revisions
            
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            current_rev = self.get_current_revision()
            
            if current_rev is None:
                # No migrations applied yet
                return [rev.revision for rev in script_dir.walk_revisions()]
            
            pending = []
            for revision in script_dir.walk_revisions():
                if revision.revision != current_rev:
                    pending.append(revision.revision)
                else:
                    break
            
            return pending
            
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def validate_schema(self) -> Tuple[bool, List[str]]:
        """
        Validate current database schema against models.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        try:
            issues = []
            
            # Check if all tables exist
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            model_tables = set(Base.metadata.tables.keys())
            db_tables = set(metadata.tables.keys())
            
            # Check for missing tables
            missing_tables = model_tables - db_tables
            if missing_tables:
                issues.extend([f"Missing table: {table}" for table in missing_tables])
            
            # Check for extra tables
            extra_tables = db_tables - model_tables
            if extra_tables:
                issues.extend([f"Extra table: {table}" for table in extra_tables])
            
            # Check for column differences (simplified check)
            for table_name in model_tables.intersection(db_tables):
                model_table = Base.metadata.tables[table_name]
                db_table = metadata.tables[table_name]
                
                model_columns = set(model_table.columns.keys())
                db_columns = set(db_table.columns.keys())
                
                missing_columns = model_columns - db_columns
                if missing_columns:
                    issues.extend([
                        f"Missing column in {table_name}: {col}" 
                        for col in missing_columns
                    ])
                
                extra_columns = db_columns - model_columns
                if extra_columns:
                    issues.extend([
                        f"Extra column in {table_name}: {col}" 
                        for col in extra_columns
                    ])
            
            is_valid = len(issues) == 0
            
            if is_valid:
                logger.info("Schema validation passed")
            else:
                logger.warning(f"Schema validation failed with {len(issues)} issues")
            
            return is_valid, issues
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False, [f"Validation error: {e}"]
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create database backup before migrations.
        
        Args:
            backup_path: Path to save backup file
            
        Returns:
            True if backup successful
        """
        try:
            # This is a simplified backup - in production you'd use pg_dump, mysqldump, etc.
            logger.info(f"Creating database backup at {backup_path}")
            
            # For SQLite, we can copy the file
            if self.database_url.startswith('sqlite'):
                import shutil
                db_path = self.database_url.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
                return True
            
            # For other databases, you'd implement proper backup logic
            logger.warning("Backup not implemented for this database type")
            return False
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def create_tables(self) -> None:
        """Create all tables from models."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """Drop all tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("All tables dropped successfully")
            
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        try:
            current_rev = self.get_current_revision()
            pending_migrations = self.get_pending_migrations()
            is_valid, issues = self.validate_schema()
            
            return {
                'current_revision': current_rev,
                'pending_migrations': pending_migrations,
                'pending_count': len(pending_migrations),
                'schema_valid': is_valid,
                'schema_issues': issues,
                'database_url': self.database_url,
                'migrations_dir': self.migrations_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                'error': str(e),
                'database_url': self.database_url,
                'migrations_dir': self.migrations_dir
            }
