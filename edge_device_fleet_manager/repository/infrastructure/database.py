"""
Database configuration and session management.

This module provides database connectivity, session management,
and schema creation for the device repository.
"""

import os
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .event_store import Base as EventStoreBase, StoredEvent
from .repositories import Base as RepositoryBase, DeviceModel, DeviceGroupModel
from ...core.exceptions import ConfigurationError


# Use repository base for schema creation
# Event store tables will be created separately if needed
Base = RepositoryBase


class DatabaseSession:
    """Database session manager."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.session_factory = sessionmaker(bind=engine)
    
    @contextmanager
    def get_session(self):
        """Get a database session with automatic cleanup."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_session(self) -> Session:
        """Create a new database session."""
        return self.session_factory()
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(self.engine)


def create_database_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
) -> Engine:
    """Create a database engine with configuration."""
    
    if database_url is None:
        # Try to get from environment
        database_url = os.getenv('DATABASE_URL')
    
    if database_url is None:
        # Default to SQLite for development
        database_url = 'sqlite:///edge_device_fleet.db'
    
    # Configure engine parameters based on database type
    engine_kwargs = {
        'echo': echo,
    }
    
    if database_url.startswith('sqlite'):
        # SQLite-specific configuration
        engine_kwargs.update({
            'poolclass': StaticPool,
            'connect_args': {
                'check_same_thread': False,
                'timeout': 20,
            }
        })
    elif database_url.startswith('postgresql'):
        # PostgreSQL-specific configuration
        engine_kwargs.update({
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': pool_recycle,
            'pool_pre_ping': True,
        })
    elif database_url.startswith('mysql'):
        # MySQL-specific configuration
        engine_kwargs.update({
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': pool_recycle,
            'pool_pre_ping': True,
        })
    
    try:
        engine = create_engine(database_url, **engine_kwargs)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return engine
        
    except Exception as e:
        raise ConfigurationError(f"Failed to create database engine: {e}") from e


def get_database_url_from_config(config) -> str:
    """Get database URL from configuration object."""
    if hasattr(config, 'database') and hasattr(config.database, 'url'):
        return config.database.url
    
    # Fallback to environment variable
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Default to SQLite
    return 'sqlite:///edge_device_fleet.db'


class DatabaseMigration:
    """Database migration utilities."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def create_schema(self) -> None:
        """Create the database schema."""
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            raise ConfigurationError(f"Failed to create database schema: {e}") from e
    
    def drop_schema(self) -> None:
        """Drop the database schema."""
        try:
            Base.metadata.drop_all(self.engine)
        except Exception as e:
            raise ConfigurationError(f"Failed to drop database schema: {e}") from e
    
    def check_schema_exists(self) -> bool:
        """Check if the database schema exists."""
        try:
            with self.engine.connect() as conn:
                # Check if the devices table exists
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='devices'"
                    if self.engine.url.drivername == 'sqlite'
                    else "SELECT table_name FROM information_schema.tables WHERE table_name='devices'"
                )
                return result.fetchone() is not None
        except Exception:
            return False
    
    def get_schema_version(self) -> Optional[str]:
        """Get the current schema version."""
        # This would be implemented with a proper migration system
        # For now, return a simple version
        return "1.0.0" if self.check_schema_exists() else None


def create_test_database() -> DatabaseSession:
    """Create an in-memory database for testing."""
    engine = create_engine(
        'sqlite:///:memory:',
        echo=False,
        poolclass=StaticPool,
        connect_args={'check_same_thread': False}
    )
    
    # Create schema
    Base.metadata.create_all(engine)
    
    return DatabaseSession(engine)


def create_development_database() -> DatabaseSession:
    """Create a development database."""
    database_url = os.getenv('DEV_DATABASE_URL', 'sqlite:///edge_device_fleet_dev.db')
    engine = create_database_engine(database_url, echo=True)
    
    # Create schema if it doesn't exist
    migration = DatabaseMigration(engine)
    if not migration.check_schema_exists():
        migration.create_schema()
    
    return DatabaseSession(engine)


def create_production_database() -> DatabaseSession:
    """Create a production database."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ConfigurationError("DATABASE_URL environment variable is required for production")
    
    engine = create_database_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=30,
        pool_timeout=60,
        pool_recycle=3600,
    )
    
    return DatabaseSession(engine)


# Database health check utilities
def check_database_health(engine: Engine) -> dict:
    """Check database health and return status information."""
    try:
        with engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute("SELECT 1")
            result.fetchone()
            
            # Get connection pool status
            pool = engine.pool
            pool_status = {
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
            }
            
            return {
                'status': 'healthy',
                'database_url': str(engine.url).split('@')[-1],  # Hide credentials
                'driver': engine.url.drivername,
                'pool_status': pool_status,
            }
            
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'database_url': str(engine.url).split('@')[-1],  # Hide credentials
            'driver': engine.url.drivername,
        }


def get_database_info(engine: Engine) -> dict:
    """Get database information."""
    try:
        with engine.connect() as conn:
            if engine.url.drivername == 'sqlite':
                # SQLite-specific queries
                version_result = conn.execute("SELECT sqlite_version()")
                version = version_result.fetchone()[0]
                
                size_result = conn.execute("PRAGMA page_count")
                page_count = size_result.fetchone()[0]
                
                page_size_result = conn.execute("PRAGMA page_size")
                page_size = page_size_result.fetchone()[0]
                
                return {
                    'driver': 'sqlite',
                    'version': version,
                    'size_bytes': page_count * page_size,
                    'page_count': page_count,
                    'page_size': page_size,
                }
            
            elif engine.url.drivername == 'postgresql':
                # PostgreSQL-specific queries
                version_result = conn.execute("SELECT version()")
                version = version_result.fetchone()[0]
                
                return {
                    'driver': 'postgresql',
                    'version': version,
                }
            
            else:
                return {
                    'driver': engine.url.drivername,
                    'version': 'unknown',
                }
                
    except Exception as e:
        return {
            'driver': engine.url.drivername,
            'error': str(e),
        }
