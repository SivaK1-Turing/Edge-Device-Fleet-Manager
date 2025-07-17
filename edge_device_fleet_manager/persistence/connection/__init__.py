"""
Database Connection Management

Comprehensive database connection management with connection pooling,
health monitoring, failover capabilities, and async support.

Key Features:
- Connection pooling with configurable parameters
- Health monitoring and automatic recovery
- Failover and retry mechanisms
- Transaction management
- Connection lifecycle management
- Performance monitoring
- Multi-database support
"""

from .manager import DatabaseManager
from .pool import ConnectionPool
from .health import HealthChecker
from .config import DatabaseConfig

__all__ = [
    "DatabaseManager",
    "ConnectionPool", 
    "HealthChecker",
    "DatabaseConfig"
]
