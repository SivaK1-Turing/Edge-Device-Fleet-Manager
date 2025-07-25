"""
Stage Executor

Executes individual pipeline stages with proper isolation and error handling.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of stage execution."""
    
    def __init__(self, success: bool, output: Optional[str] = None, 
                 error: Optional[str] = None, duration: float = 0.0,
                 artifacts: Optional[list] = None, metadata: Optional[dict] = None):
        """Initialize execution result."""
        self.success = success
        self.output = output
        self.error = error
        self.duration = duration
        self.artifacts = artifacts or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'duration': self.duration,
            'artifacts': self.artifacts,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class StageExecutor:
    """
    Executes pipeline stages with proper isolation and error handling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize stage executor."""
        self.config = config or {}
        self.logger = logger
        self.default_timeout = self.config.get('default_timeout', 3600)  # 1 hour
        self.max_retries = self.config.get('max_retries', 3)
    
    async def execute_stage(self, stage_name: str, executor_func: Callable,
                          execution_context: Dict[str, Any],
                          timeout: Optional[int] = None,
                          retries: int = 0) -> ExecutionResult:
        """
        Execute a single stage.
        
        Args:
            stage_name: Name of the stage
            executor_func: Function to execute
            execution_context: Execution context and variables
            timeout: Timeout in seconds
            retries: Number of retries
            
        Returns:
            ExecutionResult with outcome
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        self.logger.info(f"Executing stage: {stage_name}")
        
        for attempt in range(retries + 1):
            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(executor_func):
                    result = await asyncio.wait_for(
                        executor_func(execution_context),
                        timeout=timeout
                    )
                else:
                    result = executor_func(execution_context)
                
                duration = time.time() - start_time
                
                # Process result
                if isinstance(result, dict):
                    return ExecutionResult(
                        success=result.get('success', True),
                        output=result.get('output'),
                        error=result.get('error'),
                        duration=duration,
                        artifacts=result.get('artifacts', []),
                        metadata=result.get('metadata', {})
                    )
                else:
                    return ExecutionResult(
                        success=True,
                        output=str(result) if result is not None else None,
                        duration=duration
                    )
                    
            except asyncio.TimeoutError:
                if attempt < retries:
                    self.logger.warning(f"Stage {stage_name} timed out, retrying ({attempt + 1}/{retries})")
                    continue
                
                duration = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    error=f"Stage timed out after {timeout} seconds",
                    duration=duration
                )
                
            except Exception as e:
                if attempt < retries:
                    self.logger.warning(f"Stage {stage_name} failed, retrying ({attempt + 1}/{retries}): {e}")
                    continue
                
                duration = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    duration=duration
                )
        
        # Should not reach here
        duration = time.time() - start_time
        return ExecutionResult(
            success=False,
            error="Unexpected execution path",
            duration=duration
        )
    
    async def execute_parallel_stages(self, stages: Dict[str, Dict[str, Any]],
                                    execution_context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """
        Execute multiple stages in parallel.
        
        Args:
            stages: Dictionary of stage configurations
            execution_context: Shared execution context
            
        Returns:
            Dictionary of stage results
        """
        self.logger.info(f"Executing {len(stages)} stages in parallel")
        
        # Create tasks for all stages
        tasks = {}
        for stage_name, stage_config in stages.items():
            task = asyncio.create_task(
                self.execute_stage(
                    stage_name=stage_name,
                    executor_func=stage_config['executor'],
                    execution_context=execution_context,
                    timeout=stage_config.get('timeout'),
                    retries=stage_config.get('retries', 0)
                )
            )
            tasks[stage_name] = task
        
        # Wait for all tasks to complete
        results = {}
        for stage_name, task in tasks.items():
            try:
                results[stage_name] = await task
            except Exception as e:
                results[stage_name] = ExecutionResult(
                    success=False,
                    error=f"Task execution failed: {e}"
                )
        
        return results
    
    def prepare_execution_context(self, base_context: Dict[str, Any],
                                stage_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare execution context for a stage.
        
        Args:
            base_context: Base execution context
            stage_config: Stage-specific configuration
            
        Returns:
            Prepared execution context
        """
        context = base_context.copy()
        
        # Add stage-specific environment variables
        if 'environment' in stage_config:
            context.setdefault('environment', {}).update(stage_config['environment'])
        
        # Add stage metadata
        context['stage'] = {
            'name': stage_config.get('name'),
            'type': stage_config.get('type', 'generic'),
            'config': stage_config
        }
        
        return context
    
    def validate_stage_config(self, stage_config: Dict[str, Any]) -> list:
        """
        Validate stage configuration.
        
        Args:
            stage_config: Stage configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required fields
        if 'name' not in stage_config:
            errors.append("Stage name is required")
        
        if 'executor' not in stage_config:
            errors.append("Stage executor is required")
        
        # Validate timeout
        timeout = stage_config.get('timeout')
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            errors.append("Timeout must be a positive integer")
        
        # Validate retries
        retries = stage_config.get('retries', 0)
        if not isinstance(retries, int) or retries < 0:
            errors.append("Retries must be a non-negative integer")
        
        return errors
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            'default_timeout': self.default_timeout,
            'max_retries': self.max_retries,
            'executor_type': 'StageExecutor'
        }
