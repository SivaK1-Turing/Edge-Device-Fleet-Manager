"""
Wheel Package Builder

Builds Python wheel packages for the Edge Device Fleet Manager with proper
metadata, dependencies, and distribution-ready packaging.
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import uuid

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class WheelBuilder:
    """
    Python wheel package builder.
    
    Creates distribution-ready wheel packages with proper metadata,
    dependency management, and build optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize wheel builder.
        
        Args:
            config: Optional build configuration
        """
        self.config = config or {}
        self.build_id = str(uuid.uuid4())
        self.build_dir = None
        self.dist_dir = None
        self.logger = get_logger(f"{__name__}.WheelBuilder")
        
        # Build configuration
        self.source_dir = Path(self.config.get('source_dir', '.'))
        self.output_dir = Path(self.config.get('output_dir', 'dist'))
        self.build_temp_dir = Path(self.config.get('build_temp_dir', 'build'))
        self.clean_build = self.config.get('clean_build', True)
        self.include_source = self.config.get('include_source', False)
        self.optimize_level = self.config.get('optimize_level', 2)
        
        # Package metadata
        self.package_name = self.config.get('package_name', 'edge-device-fleet-manager')
        self.version = self.config.get('version', '1.0.0')
        self.description = self.config.get('description', 'IoT Edge Device Fleet Management System')
        self.author = self.config.get('author', 'Edge Device Fleet Manager Team')
        self.author_email = self.config.get('author_email', 'team@edgefleetmanager.com')
        self.license = self.config.get('license', 'MIT')
        self.python_requires = self.config.get('python_requires', '>=3.8')
        
        # Dependencies
        self.install_requires = self.config.get('install_requires', [])
        self.extras_require = self.config.get('extras_require', {})
        
        # Build tools
        self.build_tools = self.config.get('build_tools', ['wheel', 'setuptools'])
    
    async def build(self) -> Dict[str, Any]:
        """
        Build the wheel package.
        
        Returns:
            Build result information
        """
        build_start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting wheel build: {self.build_id}")
            
            # Prepare build environment
            await self._prepare_build_environment()
            
            # Generate setup files
            await self._generate_setup_files()
            
            # Install build dependencies
            await self._install_build_dependencies()
            
            # Build wheel
            wheel_path = await self._build_wheel()
            
            # Validate wheel
            validation_result = await self._validate_wheel(wheel_path)
            
            # Calculate build duration
            build_duration = (datetime.now(timezone.utc) - build_start_time).total_seconds()
            
            # Get wheel info
            wheel_info = await self._get_wheel_info(wheel_path)
            
            result = {
                'success': True,
                'build_id': self.build_id,
                'wheel_path': str(wheel_path),
                'wheel_name': wheel_path.name,
                'wheel_size_bytes': wheel_path.stat().st_size,
                'build_duration_seconds': build_duration,
                'package_name': self.package_name,
                'version': self.version,
                'python_requires': self.python_requires,
                'dependencies': self.install_requires,
                'wheel_info': wheel_info,
                'validation': validation_result,
                'build_timestamp': build_start_time.isoformat()
            }
            
            self.logger.info(f"Wheel build completed successfully: {wheel_path.name}")
            
            return result
            
        except Exception as e:
            build_duration = (datetime.now(timezone.utc) - build_start_time).total_seconds()
            
            self.logger.error(f"Wheel build failed: {e}")
            
            return {
                'success': False,
                'build_id': self.build_id,
                'error': str(e),
                'build_duration_seconds': build_duration,
                'build_timestamp': build_start_time.isoformat()
            }
        
        finally:
            # Cleanup if requested
            if self.clean_build:
                await self._cleanup_build_environment()
    
    async def _prepare_build_environment(self):
        """Prepare the build environment."""
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary build directory
        self.build_dir = Path(tempfile.mkdtemp(prefix=f"wheel_build_{self.build_id}_"))
        self.dist_dir = self.build_dir / "dist"
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"Build directory: {self.build_dir}")
        self.logger.debug(f"Dist directory: {self.dist_dir}")
    
    async def _generate_setup_files(self):
        """Generate setup.py and other required files."""
        # Generate setup.py
        setup_py_content = self._generate_setup_py()
        setup_py_path = self.build_dir / "setup.py"
        
        with open(setup_py_path, 'w', encoding='utf-8') as f:
            f.write(setup_py_content)
        
        # Generate setup.cfg if needed
        setup_cfg_content = self._generate_setup_cfg()
        if setup_cfg_content:
            setup_cfg_path = self.build_dir / "setup.cfg"
            with open(setup_cfg_path, 'w', encoding='utf-8') as f:
                f.write(setup_cfg_content)
        
        # Generate pyproject.toml if needed
        pyproject_content = self._generate_pyproject_toml()
        if pyproject_content:
            pyproject_path = self.build_dir / "pyproject.toml"
            with open(pyproject_path, 'w', encoding='utf-8') as f:
                f.write(pyproject_content)
        
        # Copy source files
        await self._copy_source_files()
        
        # Generate MANIFEST.in
        manifest_content = self._generate_manifest()
        if manifest_content:
            manifest_path = self.build_dir / "MANIFEST.in"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_content)
    
    def _generate_setup_py(self) -> str:
        """Generate setup.py content."""
        install_requires_str = ',\n        '.join(f'"{req}"' for req in self.install_requires)
        
        extras_require_str = ""
        if self.extras_require:
            extras_items = []
            for key, deps in self.extras_require.items():
                deps_str = ', '.join(f'"{dep}"' for dep in deps)
                extras_items.append(f'        "{key}": [{deps_str}]')
            extras_require_str = f"""
    extras_require={{
{chr(10).join(extras_items)}
    }},"""
        
        return f'''#!/usr/bin/env python3
"""
Setup script for {self.package_name}
"""

from setuptools import setup, find_packages
import os

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "{self.description}"

setup(
    name="{self.package_name}",
    version="{self.version}",
    description="{self.description}",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="{self.author}",
    author_email="{self.author_email}",
    license="{self.license}",
    python_requires="{self.python_requires}",
    packages=find_packages(),
    install_requires=[
        {install_requires_str}
    ],{extras_require_str}
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    keywords="iot edge device fleet management monitoring",
    project_urls={{
        "Homepage": "https://github.com/edgefleetmanager/edge-device-fleet-manager",
        "Bug Reports": "https://github.com/edgefleetmanager/edge-device-fleet-manager/issues",
        "Source": "https://github.com/edgefleetmanager/edge-device-fleet-manager",
        "Documentation": "https://edgefleetmanager.readthedocs.io/",
    }},
    entry_points={{
        "console_scripts": [
            "edge-fleet-manager=edge_device_fleet_manager.cli.main:main",
            "edfm=edge_device_fleet_manager.cli.main:main",
        ],
    }},
)
'''
    
    def _generate_setup_cfg(self) -> Optional[str]:
        """Generate setup.cfg content."""
        return f"""[metadata]
name = {self.package_name}
version = {self.version}
description = {self.description}
author = {self.author}
author_email = {self.author_email}
license = {self.license}
license_file = LICENSE
platform = any
classifier =
    Development Status :: 4 - Beta
    Intended Audience :: Developers
    License :: OSI Approved :: MIT License
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.8
    Programming Language :: Python :: 3.9
    Programming Language :: Python :: 3.10
    Programming Language :: Python :: 3.11

[options]
zip_safe = False
include_package_data = True
python_requires = {self.python_requires}
packages = find:

[options.packages.find]
exclude =
    tests*
    docs*

[bdist_wheel]
universal = 0
"""
    
    def _generate_pyproject_toml(self) -> Optional[str]:
        """Generate pyproject.toml content."""
        build_requires = ', '.join(f'"{tool}"' for tool in self.build_tools)
        
        return f"""[build-system]
requires = [{build_requires}]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["edge_device_fleet_manager"]

[tool.setuptools.package-data]
edge_device_fleet_manager = ["*.json", "*.yaml", "*.yml", "*.txt", "*.md"]
"""
    
    def _generate_manifest(self) -> Optional[str]:
        """Generate MANIFEST.in content."""
        return """include README.md
include LICENSE
include requirements.txt
include requirements-dev.txt
recursive-include edge_device_fleet_manager *.py
recursive-include edge_device_fleet_manager *.json
recursive-include edge_device_fleet_manager *.yaml
recursive-include edge_device_fleet_manager *.yml
recursive-include edge_device_fleet_manager *.txt
recursive-exclude tests *
recursive-exclude docs *
recursive-exclude .git *
recursive-exclude __pycache__ *
recursive-exclude *.pyc *
"""
    
    async def _copy_source_files(self):
        """Copy source files to build directory."""
        # Copy main package
        source_package = self.source_dir / "edge_device_fleet_manager"
        if source_package.exists():
            dest_package = self.build_dir / "edge_device_fleet_manager"
            shutil.copytree(source_package, dest_package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        
        # Copy additional files
        additional_files = ['README.md', 'LICENSE', 'requirements.txt', 'requirements-dev.txt']
        for filename in additional_files:
            source_file = self.source_dir / filename
            if source_file.exists():
                shutil.copy2(source_file, self.build_dir / filename)
    
    async def _install_build_dependencies(self):
        """Install build dependencies."""
        try:
            # Install build tools
            cmd = ['pip', 'install', '--upgrade'] + self.build_tools
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.debug(f"Installed build dependencies: {' '.join(self.build_tools)}")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to install build dependencies: {e}")
    
    async def _build_wheel(self) -> Path:
        """Build the wheel package."""
        # Change to build directory
        original_cwd = os.getcwd()
        
        try:
            os.chdir(self.build_dir)
            
            # Build wheel
            cmd = ['python', 'setup.py', 'bdist_wheel', '--dist-dir', str(self.dist_dir)]
            
            if self.optimize_level > 0:
                cmd.extend(['-O', str(self.optimize_level)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Find the generated wheel
            wheel_files = list(self.dist_dir.glob('*.whl'))
            if not wheel_files:
                raise RuntimeError("No wheel file generated")
            
            wheel_path = wheel_files[0]
            
            # Move wheel to output directory
            final_wheel_path = self.output_dir / wheel_path.name
            shutil.move(wheel_path, final_wheel_path)
            
            return final_wheel_path
            
        finally:
            os.chdir(original_cwd)
    
    async def _validate_wheel(self, wheel_path: Path) -> Dict[str, Any]:
        """Validate the generated wheel."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if wheel file exists and is not empty
            if not wheel_path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append("Wheel file does not exist")
                return validation_result
            
            if wheel_path.stat().st_size == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("Wheel file is empty")
                return validation_result
            
            # Try to validate with wheel tool if available
            try:
                cmd = ['python', '-m', 'wheel', 'verify', str(wheel_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    validation_result['warnings'].append(f"Wheel verification warning: {result.stderr}")
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                validation_result['warnings'].append("Wheel verification tool not available")
            
            self.logger.info(f"Wheel validation completed: {wheel_path.name}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {e}")
        
        return validation_result
    
    async def _get_wheel_info(self, wheel_path: Path) -> Dict[str, Any]:
        """Get information about the generated wheel."""
        try:
            import zipfile
            
            info = {
                'filename': wheel_path.name,
                'size_bytes': wheel_path.stat().st_size,
                'contents': []
            }
            
            # Read wheel contents
            with zipfile.ZipFile(wheel_path, 'r') as wheel_zip:
                info['contents'] = wheel_zip.namelist()
                info['file_count'] = len(info['contents'])
            
            return info
            
        except Exception as e:
            self.logger.warning(f"Failed to get wheel info: {e}")
            return {
                'filename': wheel_path.name,
                'size_bytes': wheel_path.stat().st_size,
                'error': str(e)
            }
    
    async def _cleanup_build_environment(self):
        """Clean up build environment."""
        if self.build_dir and self.build_dir.exists():
            try:
                shutil.rmtree(self.build_dir)
                self.logger.debug(f"Cleaned up build directory: {self.build_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup build directory: {e}")
    
    def get_build_info(self) -> Dict[str, Any]:
        """Get build configuration information."""
        return {
            'build_id': self.build_id,
            'package_name': self.package_name,
            'version': self.version,
            'source_dir': str(self.source_dir),
            'output_dir': str(self.output_dir),
            'python_requires': self.python_requires,
            'dependencies': self.install_requires,
            'extras_require': self.extras_require,
            'build_tools': self.build_tools,
            'clean_build': self.clean_build,
            'optimize_level': self.optimize_level
        }
