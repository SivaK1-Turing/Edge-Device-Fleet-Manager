"""
Packaging Managers Module

Package management, version control, and dependency resolution.
"""

from .package_manager import PackageManager
from .version_controller import VersionController

__all__ = [
    'PackageManager',
    'VersionController'
]
