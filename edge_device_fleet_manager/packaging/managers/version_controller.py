"""
Version Controller

Manages package versioning and semantic versioning.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import re

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class VersionController:
    """
    Package version management system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize version controller."""
        self.config = config or {}
        self.logger = logger
        self.versions = {}  # Version history
    
    def create_version(self, version_string: str) -> Dict[str, Any]:
        """Create a new version."""
        version_info = {
            'version': version_string,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_valid': self.validate_version(version_string)
        }
        
        self.versions[version_string] = version_info
        return version_info
    
    def validate_version(self, version_string: str) -> bool:
        """Validate semantic version format."""
        # Simple semantic version pattern: major.minor.patch
        pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?(?:\+[a-zA-Z0-9]+)?$'
        return bool(re.match(pattern, version_string))
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two versions. Returns -1, 0, or 1."""
        # Simple comparison - in real implementation would use proper semver
        if version1 == version2:
            return 0
        elif version1 < version2:
            return -1
        else:
            return 1
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version."""
        if not self.versions:
            return None
        
        # Simple implementation - return the last added version
        return max(self.versions.keys())
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Get version information."""
        return self.versions.get(version)
    
    def list_versions(self) -> List[str]:
        """List all versions."""
        return list(self.versions.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get version statistics."""
        return {
            'total_versions': len(self.versions),
            'latest_version': self.get_latest_version(),
            'controller_type': 'VersionController'
        }
