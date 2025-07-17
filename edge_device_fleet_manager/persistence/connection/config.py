"""
Database Configuration

Configuration classes for database connection management with
environment variable support and validation.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


@dataclass
class DatabaseConfig:
    """
    Database configuration with connection pooling and health monitoring settings.
    
    Supports environment variable configuration and validation.
    """
    
    # Connection settings
    database_url: str = "sqlite+aiosqlite:///./edge_fleet_manager.db"
    
    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Session settings
    autoflush: bool = True
    autocommit: bool = False
    
    # Logging settings
    echo_sql: bool = False
    echo_pool: bool = False
    
    # Health monitoring
    enable_health_checks: bool = True
    health_check_interval: int = 60
    health_check_timeout: int = 10
    
    # Retry and failover
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_failover: bool = False
    failover_urls: List[str] = None
    
    # Performance settings
    statement_timeout: Optional[int] = None
    query_cache_size: int = 500
    
    # Security settings
    ssl_mode: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.failover_urls is None:
            self.failover_urls = []
        
        # Validate configuration
        self.validate()
    
    def validate(self) -> List[str]:
        """
        Validate configuration settings.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate database URL
        if not self.database_url:
            errors.append("Database URL is required")
        else:
            try:
                parsed = urlparse(self.database_url)
                if not parsed.scheme:
                    errors.append("Database URL must include a scheme")
            except Exception as e:
                errors.append(f"Invalid database URL: {e}")
        
        # Validate pool settings
        if self.pool_size <= 0:
            errors.append("Pool size must be positive")
        
        if self.max_overflow < 0:
            errors.append("Max overflow cannot be negative")
        
        if self.pool_timeout <= 0:
            errors.append("Pool timeout must be positive")
        
        if self.pool_recycle <= 0:
            errors.append("Pool recycle must be positive")
        
        # Validate health check settings
        if self.health_check_interval <= 0:
            errors.append("Health check interval must be positive")
        
        if self.health_check_timeout <= 0:
            errors.append("Health check timeout must be positive")
        
        # Validate retry settings
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        if self.retry_delay <= 0:
            errors.append("Retry delay must be positive")
        
        # Validate failover URLs
        for url in self.failover_urls:
            try:
                parsed = urlparse(url)
                if not parsed.scheme:
                    errors.append(f"Failover URL must include a scheme: {url}")
            except Exception as e:
                errors.append(f"Invalid failover URL {url}: {e}")
        
        return errors
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """
        Create configuration from environment variables.
        
        Returns:
            DatabaseConfig instance
        """
        return cls(
            database_url=os.getenv('DATABASE_URL', cls.database_url),
            
            # Pool settings
            pool_size=int(os.getenv('DB_POOL_SIZE', cls.pool_size)),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', cls.max_overflow)),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', cls.pool_timeout)),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', cls.pool_recycle)),
            pool_pre_ping=os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true',
            
            # Session settings
            autoflush=os.getenv('DB_AUTOFLUSH', 'true').lower() == 'true',
            autocommit=os.getenv('DB_AUTOCOMMIT', 'false').lower() == 'true',
            
            # Logging settings
            echo_sql=os.getenv('DB_ECHO_SQL', 'false').lower() == 'true',
            echo_pool=os.getenv('DB_ECHO_POOL', 'false').lower() == 'true',
            
            # Health monitoring
            enable_health_checks=os.getenv('DB_ENABLE_HEALTH_CHECKS', 'true').lower() == 'true',
            health_check_interval=int(os.getenv('DB_HEALTH_CHECK_INTERVAL', cls.health_check_interval)),
            health_check_timeout=int(os.getenv('DB_HEALTH_CHECK_TIMEOUT', cls.health_check_timeout)),
            
            # Retry and failover
            max_retries=int(os.getenv('DB_MAX_RETRIES', cls.max_retries)),
            retry_delay=float(os.getenv('DB_RETRY_DELAY', cls.retry_delay)),
            enable_failover=os.getenv('DB_ENABLE_FAILOVER', 'false').lower() == 'true',
            failover_urls=os.getenv('DB_FAILOVER_URLS', '').split(',') if os.getenv('DB_FAILOVER_URLS') else [],
            
            # Performance settings
            statement_timeout=int(os.getenv('DB_STATEMENT_TIMEOUT')) if os.getenv('DB_STATEMENT_TIMEOUT') else None,
            query_cache_size=int(os.getenv('DB_QUERY_CACHE_SIZE', cls.query_cache_size)),
            
            # Security settings
            ssl_mode=os.getenv('DB_SSL_MODE'),
            ssl_cert=os.getenv('DB_SSL_CERT'),
            ssl_key=os.getenv('DB_SSL_KEY'),
            ssl_ca=os.getenv('DB_SSL_CA'),
        )
    
    def get_connection_args(self) -> Dict[str, Any]:
        """
        Get connection arguments for SQLAlchemy engine.
        
        Returns:
            Dictionary of connection arguments
        """
        args = {}
        
        # Add SSL settings if configured
        if self.ssl_mode:
            args['sslmode'] = self.ssl_mode
        
        if self.ssl_cert:
            args['sslcert'] = self.ssl_cert
        
        if self.ssl_key:
            args['sslkey'] = self.ssl_key
        
        if self.ssl_ca:
            args['sslrootcert'] = self.ssl_ca
        
        # Add statement timeout if configured
        if self.statement_timeout:
            args['options'] = f'-c statement_timeout={self.statement_timeout}s'
        
        return args
    
    def get_engine_url(self) -> str:
        """
        Get the complete engine URL with connection arguments.
        
        Returns:
            Complete database URL
        """
        base_url = self.database_url
        connection_args = self.get_connection_args()
        
        if connection_args:
            # Add connection arguments to URL
            # This is a simplified implementation - in production you'd handle this more carefully
            if '?' in base_url:
                separator = '&'
            else:
                separator = '?'
            
            args_string = '&'.join([f"{k}={v}" for k, v in connection_args.items()])
            base_url = f"{base_url}{separator}{args_string}"
        
        return base_url
    
    def is_sqlite(self) -> bool:
        """Check if database is SQLite."""
        return self.database_url.startswith('sqlite')
    
    def is_postgresql(self) -> bool:
        """Check if database is PostgreSQL."""
        return self.database_url.startswith(('postgresql', 'postgres'))
    
    def is_mysql(self) -> bool:
        """Check if database is MySQL."""
        return self.database_url.startswith('mysql')
    
    def get_database_type(self) -> str:
        """
        Get database type from URL.
        
        Returns:
            Database type string
        """
        if self.is_sqlite():
            return 'sqlite'
        elif self.is_postgresql():
            return 'postgresql'
        elif self.is_mysql():
            return 'mysql'
        else:
            parsed = urlparse(self.database_url)
            return parsed.scheme.split('+')[0] if '+' in parsed.scheme else parsed.scheme
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            'database_url': self.database_url,
            'database_type': self.get_database_type(),
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': self.pool_pre_ping,
            'autoflush': self.autoflush,
            'autocommit': self.autocommit,
            'echo_sql': self.echo_sql,
            'echo_pool': self.echo_pool,
            'enable_health_checks': self.enable_health_checks,
            'health_check_interval': self.health_check_interval,
            'health_check_timeout': self.health_check_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'enable_failover': self.enable_failover,
            'failover_urls': self.failover_urls,
            'statement_timeout': self.statement_timeout,
            'query_cache_size': self.query_cache_size,
            'ssl_mode': self.ssl_mode,
        }
    
    def __repr__(self) -> str:
        """String representation of the configuration."""
        # Hide sensitive information
        safe_url = self.database_url
        if '@' in safe_url:
            # Hide password in URL
            parts = safe_url.split('@')
            if len(parts) == 2:
                user_pass = parts[0].split('//')[-1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    safe_url = safe_url.replace(user_pass, f"{user}:***")
        
        return f"DatabaseConfig(url='{safe_url}', type='{self.get_database_type()}')"
