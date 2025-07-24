"""
Pipeline Configuration

Configuration management for CI/CD pipelines.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
try:
    import yaml
except ImportError:
    yaml = None

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PipelineConfig:
    """
    Pipeline configuration management.
    """
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """Initialize pipeline configuration."""
        self.config_data = config_data or {}
        self.logger = logger
        
        # Default configuration
        self.defaults = {
            'timeout_seconds': 3600,
            'retry_count': 0,
            'allow_failure': False,
            'when': 'always',
            'environment': {},
            'artifacts': []
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PipelineConfig':
        """Create configuration from dictionary."""
        return cls(config_dict)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PipelineConfig':
        """Create configuration from JSON string."""
        try:
            config_dict = json.loads(json_str)
            return cls(config_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON configuration: {e}")
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'PipelineConfig':
        """Create configuration from YAML string."""
        if yaml is None:
            raise ValueError("YAML support not available - install PyYAML")

        try:
            config_dict = yaml.safe_load(yaml_str)
            return cls(config_dict)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get_pipeline_name(self) -> str:
        """Get pipeline name."""
        return self.config_data.get('name', 'unnamed_pipeline')
    
    def get_pipeline_description(self) -> str:
        """Get pipeline description."""
        return self.config_data.get('description', '')
    
    def get_stages(self) -> List[Dict[str, Any]]:
        """Get pipeline stages."""
        stages = self.config_data.get('stages', [])
        
        # Apply defaults to each stage
        for stage in stages:
            for key, default_value in self.defaults.items():
                if key not in stage:
                    stage[key] = default_value
        
        return stages
    
    def get_variables(self) -> Dict[str, str]:
        """Get pipeline variables."""
        return self.config_data.get('variables', {})
    
    def get_triggers(self) -> List[str]:
        """Get pipeline triggers."""
        return self.config_data.get('triggers', [])
    
    def get_environment(self) -> Dict[str, str]:
        """Get global environment variables."""
        return self.config_data.get('environment', {})
    
    def is_enabled(self) -> bool:
        """Check if pipeline is enabled."""
        return self.config_data.get('enabled', True)
    
    def get_timeout(self) -> int:
        """Get global timeout."""
        return self.config_data.get('timeout_seconds', self.defaults['timeout_seconds'])
    
    def get_retry_policy(self) -> Dict[str, Any]:
        """Get retry policy."""
        return self.config_data.get('retry_policy', {
            'max_retries': 0,
            'retry_delay': 1,
            'backoff_multiplier': 1.0
        })
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return self.config_data.get('notifications', {})
    
    def get_artifact_config(self) -> Dict[str, Any]:
        """Get artifact configuration."""
        return self.config_data.get('artifacts', {
            'enabled': True,
            'retention_days': 30,
            'storage_path': 'artifacts'
        })
    
    def validate(self) -> List[str]:
        """
        Validate pipeline configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        if not self.get_pipeline_name():
            errors.append("Pipeline name is required")
        
        stages = self.get_stages()
        if not stages:
            errors.append("At least one stage is required")
        
        # Validate stages
        stage_names = set()
        for i, stage in enumerate(stages):
            stage_errors = self._validate_stage(stage, i)
            errors.extend(stage_errors)
            
            # Check for duplicate stage names
            stage_name = stage.get('name', f'stage_{i}')
            if stage_name in stage_names:
                errors.append(f"Duplicate stage name: {stage_name}")
            stage_names.add(stage_name)
        
        # Validate dependencies
        dependency_errors = self._validate_dependencies(stages)
        errors.extend(dependency_errors)
        
        return errors
    
    def _validate_stage(self, stage: Dict[str, Any], index: int) -> List[str]:
        """Validate a single stage."""
        errors = []
        stage_name = stage.get('name', f'stage_{index}')
        
        # Required fields
        if 'name' not in stage:
            errors.append(f"Stage {index}: name is required")
        
        if 'executor' not in stage:
            errors.append(f"Stage {stage_name}: executor is required")
        
        # Validate timeout
        timeout = stage.get('timeout_seconds')
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            errors.append(f"Stage {stage_name}: timeout must be a positive integer")
        
        # Validate retry count
        retry_count = stage.get('retry_count', 0)
        if not isinstance(retry_count, int) or retry_count < 0:
            errors.append(f"Stage {stage_name}: retry_count must be a non-negative integer")
        
        # Validate when condition
        when = stage.get('when', 'always')
        valid_when = ['always', 'on_success', 'on_failure', 'manual']
        if when not in valid_when:
            errors.append(f"Stage {stage_name}: when must be one of {valid_when}")
        
        return errors
    
    def _validate_dependencies(self, stages: List[Dict[str, Any]]) -> List[str]:
        """Validate stage dependencies."""
        errors = []
        stage_names = {stage.get('name', f'stage_{i}') for i, stage in enumerate(stages)}
        
        for stage in stages:
            stage_name = stage.get('name', 'unnamed')
            depends_on = stage.get('depends_on', [])
            
            for dependency in depends_on:
                if dependency not in stage_names:
                    errors.append(f"Stage {stage_name}: dependency '{dependency}' not found")
                
                if dependency == stage_name:
                    errors.append(f"Stage {stage_name}: cannot depend on itself")
        
        # Check for circular dependencies
        circular_errors = self._check_circular_dependencies(stages)
        errors.extend(circular_errors)
        
        return errors
    
    def _check_circular_dependencies(self, stages: List[Dict[str, Any]]) -> List[str]:
        """Check for circular dependencies."""
        errors = []
        
        # Build dependency graph
        graph = {}
        for stage in stages:
            stage_name = stage.get('name', 'unnamed')
            depends_on = stage.get('depends_on', [])
            graph[stage_name] = depends_on
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for stage_name in graph:
            if stage_name not in visited:
                if has_cycle(stage_name):
                    errors.append(f"Circular dependency detected involving stage: {stage_name}")
                    break
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config_data.copy()
    
    def to_json(self, indent: int = 2) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.config_data, indent=indent)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        if yaml is None:
            raise ValueError("YAML support not available - install PyYAML")
        return yaml.dump(self.config_data, default_flow_style=False)
    
    def merge_with(self, other_config: 'PipelineConfig') -> 'PipelineConfig':
        """Merge with another configuration."""
        merged_data = self.config_data.copy()
        merged_data.update(other_config.config_data)
        return PipelineConfig(merged_data)
    
    def get_stage_by_name(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """Get stage configuration by name."""
        for stage in self.get_stages():
            if stage.get('name') == stage_name:
                return stage
        return None
    
    def update_stage(self, stage_name: str, updates: Dict[str, Any]) -> bool:
        """Update stage configuration."""
        stages = self.config_data.get('stages', [])
        
        for stage in stages:
            if stage.get('name') == stage_name:
                stage.update(updates)
                return True
        
        return False
