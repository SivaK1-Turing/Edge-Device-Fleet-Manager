"""
Docker Package Builder

Builds Docker container images for the Edge Device Fleet Manager.
"""

import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import json

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DockerPackageBuilder:
    """
    Docker container image builder.
    
    Creates Docker images with proper layering, optimization, and metadata.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Docker builder."""
        self.config = config or {}
        self.logger = logger
        
        # Build configuration
        self.image_name = self.config.get('image_name', 'edge-device-fleet-manager')
        self.image_tag = self.config.get('image_tag', 'latest')
        self.base_image = self.config.get('base_image', 'python:3.11-slim')
        self.working_dir = self.config.get('working_dir', '/app')
        self.expose_ports = self.config.get('expose_ports', [8000])
        self.build_context = self.config.get('build_context', '.')
        self.dockerfile_path = self.config.get('dockerfile_path', 'Dockerfile')
        
        # Build options
        self.no_cache = self.config.get('no_cache', False)
        self.pull = self.config.get('pull', True)
        self.build_args = self.config.get('build_args', {})
        self.labels = self.config.get('labels', {})
    
    async def build(self) -> Dict[str, Any]:
        """Build Docker image."""
        build_start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting Docker build: {self.image_name}:{self.image_tag}")
            
            # Generate Dockerfile if not exists
            dockerfile_content = await self._generate_dockerfile()
            
            # Create build context
            build_context_path = await self._prepare_build_context(dockerfile_content)
            
            # Build image
            image_id = await self._build_image(build_context_path)
            
            # Get image info
            image_info = await self._get_image_info(image_id)
            
            # Calculate build duration
            build_duration = (datetime.now(timezone.utc) - build_start_time).total_seconds()
            
            result = {
                'success': True,
                'image_id': image_id,
                'image_name': self.image_name,
                'image_tag': self.image_tag,
                'full_name': f"{self.image_name}:{self.image_tag}",
                'build_duration_seconds': build_duration,
                'image_info': image_info,
                'build_timestamp': build_start_time.isoformat()
            }
            
            self.logger.info(f"Docker build completed: {self.image_name}:{self.image_tag}")
            return result
            
        except Exception as e:
            build_duration = (datetime.now(timezone.utc) - build_start_time).total_seconds()
            
            self.logger.error(f"Docker build failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'build_duration_seconds': build_duration,
                'build_timestamp': build_start_time.isoformat()
            }
    
    async def _generate_dockerfile(self) -> str:
        """Generate Dockerfile content."""
        # Check if custom Dockerfile exists
        if Path(self.dockerfile_path).exists():
            with open(self.dockerfile_path, 'r') as f:
                return f.read()
        
        # Generate default Dockerfile
        ports_expose = '\n'.join(f'EXPOSE {port}' for port in self.expose_ports)
        
        dockerfile_content = f'''# Generated Dockerfile for Edge Device Fleet Manager
FROM {self.base_image}

# Set working directory
WORKDIR {self.working_dir}

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the application
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app {self.working_dir}
USER app

# Expose ports
{ports_expose}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "edge_device_fleet_manager.cli.main", "serve"]
'''
        
        return dockerfile_content
    
    async def _prepare_build_context(self, dockerfile_content: str) -> Path:
        """Prepare build context directory."""
        # Create temporary build directory
        build_dir = Path(tempfile.mkdtemp(prefix="docker_build_"))
        
        # Write Dockerfile
        dockerfile_path = build_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Copy source files
        source_dir = Path(self.build_context)
        if source_dir.exists():
            # Copy main package
            package_source = source_dir / "edge_device_fleet_manager"
            if package_source.exists():
                import shutil
                shutil.copytree(package_source, build_dir / "edge_device_fleet_manager")
            
            # Copy additional files
            additional_files = ['requirements.txt', 'setup.py', 'README.md', 'LICENSE']
            for filename in additional_files:
                source_file = source_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, build_dir / filename)
        
        # Create .dockerignore
        dockerignore_content = '''__pycache__
*.pyc
*.pyo
*.pyd
.git
.gitignore
.pytest_cache
.coverage
.tox
.venv
venv/
env/
.env
*.log
.DS_Store
Thumbs.db
'''
        
        with open(build_dir / ".dockerignore", 'w') as f:
            f.write(dockerignore_content)
        
        return build_dir
    
    async def _build_image(self, build_context_path: Path) -> str:
        """Build Docker image."""
        # Construct build command
        cmd = ['docker', 'build']
        
        # Add build options
        if self.no_cache:
            cmd.append('--no-cache')
        
        if self.pull:
            cmd.append('--pull')
        
        # Add build args
        for key, value in self.build_args.items():
            cmd.extend(['--build-arg', f'{key}={value}'])
        
        # Add labels
        default_labels = {
            'org.opencontainers.image.title': 'Edge Device Fleet Manager',
            'org.opencontainers.image.description': 'IoT Edge Device Fleet Management System',
            'org.opencontainers.image.created': datetime.now(timezone.utc).isoformat(),
            'org.opencontainers.image.source': 'https://github.com/edgefleetmanager/edge-device-fleet-manager'
        }
        
        all_labels = {**default_labels, **self.labels}
        for key, value in all_labels.items():
            cmd.extend(['--label', f'{key}={value}'])
        
        # Add tag
        cmd.extend(['-t', f'{self.image_name}:{self.image_tag}'])
        
        # Add build context
        cmd.append(str(build_context_path))
        
        # Execute build
        self.logger.debug(f"Docker build command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=build_context_path
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker build failed: {result.stderr}")
        
        # Extract image ID from output
        image_id = self._extract_image_id(result.stdout)
        
        return image_id
    
    def _extract_image_id(self, build_output: str) -> str:
        """Extract image ID from build output."""
        lines = build_output.strip().split('\n')
        
        # Look for "Successfully built" line
        for line in lines:
            if 'Successfully built' in line:
                return line.split()[-1]
        
        # Fallback: use image name:tag
        return f"{self.image_name}:{self.image_tag}"
    
    async def _get_image_info(self, image_id: str) -> Dict[str, Any]:
        """Get information about the built image."""
        try:
            # Get image details
            cmd = ['docker', 'inspect', image_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                image_data = json.loads(result.stdout)[0]
                
                return {
                    'id': image_data.get('Id', image_id),
                    'created': image_data.get('Created'),
                    'size': image_data.get('Size', 0),
                    'architecture': image_data.get('Architecture'),
                    'os': image_data.get('Os'),
                    'config': {
                        'exposed_ports': list(image_data.get('Config', {}).get('ExposedPorts', {}).keys()),
                        'env': image_data.get('Config', {}).get('Env', []),
                        'cmd': image_data.get('Config', {}).get('Cmd', []),
                        'working_dir': image_data.get('Config', {}).get('WorkingDir'),
                        'user': image_data.get('Config', {}).get('User')
                    },
                    'layers': len(image_data.get('RootFS', {}).get('Layers', []))
                }
            else:
                return {
                    'id': image_id,
                    'error': 'Could not inspect image'
                }
                
        except Exception as e:
            self.logger.warning(f"Failed to get image info: {e}")
            return {
                'id': image_id,
                'error': str(e)
            }
    
    def get_build_info(self) -> Dict[str, Any]:
        """Get build configuration information."""
        return {
            'image_name': self.image_name,
            'image_tag': self.image_tag,
            'base_image': self.base_image,
            'working_dir': self.working_dir,
            'expose_ports': self.expose_ports,
            'build_context': self.build_context,
            'dockerfile_path': self.dockerfile_path,
            'no_cache': self.no_cache,
            'pull': self.pull,
            'build_args': self.build_args,
            'labels': self.labels
        }
    
    async def push_image(self, registry: Optional[str] = None) -> Dict[str, Any]:
        """Push image to registry."""
        try:
            image_name = f"{self.image_name}:{self.image_tag}"
            
            if registry:
                # Tag for registry
                registry_image = f"{registry}/{image_name}"
                tag_cmd = ['docker', 'tag', image_name, registry_image]
                
                tag_result = subprocess.run(tag_cmd, capture_output=True, text=True)
                if tag_result.returncode != 0:
                    raise RuntimeError(f"Failed to tag image: {tag_result.stderr}")
                
                image_name = registry_image
            
            # Push image
            push_cmd = ['docker', 'push', image_name]
            push_result = subprocess.run(push_cmd, capture_output=True, text=True)
            
            if push_result.returncode != 0:
                raise RuntimeError(f"Failed to push image: {push_result.stderr}")
            
            return {
                'success': True,
                'image_name': image_name,
                'registry': registry
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
