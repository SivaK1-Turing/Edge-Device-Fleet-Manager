"""
Edge Device Fleet Manager

A production-grade Python CLI and library to discover, configure, monitor,
and maintain IoT edge devices at scale.
"""

__version__ = "0.1.0"
__author__ = "Edge Device Fleet Manager Team"
__email__ = "team@edgefleet.dev"

# Import main components for easy access
from .core.config import Config
from .core.context import AppContext
from .core.exceptions import EdgeFleetError

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "Config",
    "AppContext", 
    "EdgeFleetError",
]
