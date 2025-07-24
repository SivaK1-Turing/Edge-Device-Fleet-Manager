"""
Pipeline Manager

Comprehensive CI/CD pipeline management system for orchestrating automated
testing, building, packaging, and deployment workflows.
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
import json

try:
    from ...core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StageStatus(Enum):
    """Stage execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """Represents a pipeline stage configuration."""
    
    name: str
    executor: Callable
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    retry_count: int = 0
    allow_failure: bool = False
    when: str = "always"  # always, on_success, on_failure, manual
    environment: Dict[str, str] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be at least 1 second")
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")


@dataclass
class StageResult:
    """Represents the result of a stage execution."""
    
    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    output: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'stage_name': self.stage_name,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'output': self.output,
            'error': self.error,
            'artifacts': self.artifacts,
            'metadata': self.metadata
        }


@dataclass
class PipelineExecution:
    """Represents a pipeline execution instance."""
    
    pipeline_id: str
    execution_id: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    trigger: str = "manual"
    branch: Optional[str] = None
    commit: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'pipeline_id': self.pipeline_id,
            'execution_id': self.execution_id,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'stage_results': {name: result.to_dict() for name, result in self.stage_results.items()},
            'trigger': self.trigger,
            'branch': self.branch,
            'commit': self.commit,
            'metadata': self.metadata
        }


class Pipeline:
    """
    Represents a CI/CD pipeline configuration.
    """
    
    def __init__(self, pipeline_id: str, name: str, description: str = ""):
        """
        Initialize pipeline.
        
        Args:
            pipeline_id: Unique pipeline identifier
            name: Pipeline name
            description: Optional pipeline description
        """
        self.pipeline_id = pipeline_id
        self.name = name
        self.description = description
        self.stages = {}  # Dict[str, PipelineStage]
        self.stage_order = []  # List[str]
        self.variables = {}  # Dict[str, str]
        self.triggers = []  # List[str]
        self.enabled = True
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_stage(self, stage: PipelineStage):
        """Add a stage to the pipeline."""
        self.stages[stage.name] = stage
        if stage.name not in self.stage_order:
            self.stage_order.append(stage.name)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_stage(self, stage_name: str):
        """Remove a stage from the pipeline."""
        if stage_name in self.stages:
            del self.stages[stage_name]
            if stage_name in self.stage_order:
                self.stage_order.remove(stage_name)
            self.updated_at = datetime.now(timezone.utc)
    
    def get_stage_dependencies(self, stage_name: str) -> List[str]:
        """Get dependencies for a stage."""
        if stage_name not in self.stages:
            return []
        return self.stages[stage_name].depends_on
    
    def validate(self) -> List[str]:
        """Validate pipeline configuration."""
        errors = []
        
        # Check for circular dependencies
        visited = set()
        rec_stack = set()
        
        def has_cycle(stage_name: str) -> bool:
            visited.add(stage_name)
            rec_stack.add(stage_name)
            
            for dep in self.get_stage_dependencies(stage_name):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(stage_name)
            return False
        
        for stage_name in self.stages:
            if stage_name not in visited:
                if has_cycle(stage_name):
                    errors.append(f"Circular dependency detected involving stage: {stage_name}")
        
        # Check for missing dependencies
        for stage_name, stage in self.stages.items():
            for dep in stage.depends_on:
                if dep not in self.stages:
                    errors.append(f"Stage '{stage_name}' depends on non-existent stage '{dep}'")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'pipeline_id': self.pipeline_id,
            'name': self.name,
            'description': self.description,
            'stages': {name: {
                'name': stage.name,
                'depends_on': stage.depends_on,
                'timeout_seconds': stage.timeout_seconds,
                'retry_count': stage.retry_count,
                'allow_failure': stage.allow_failure,
                'when': stage.when,
                'environment': stage.environment,
                'artifacts': stage.artifacts
            } for name, stage in self.stages.items()},
            'stage_order': self.stage_order,
            'variables': self.variables,
            'triggers': self.triggers,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PipelineManager:
    """
    Comprehensive CI/CD pipeline management system.
    
    Manages pipeline definitions, executions, and orchestrates the execution
    of stages with dependency resolution and parallel execution support.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize pipeline manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.pipelines = {}  # Dict[str, Pipeline]
        self.executions = {}  # Dict[str, PipelineExecution]
        self.execution_history = []  # List[str]
        self.max_history_size = self.config.get('max_history_size', 1000)
        self.max_concurrent_executions = self.config.get('max_concurrent_executions', 5)
        self.running_executions = set()
        
        self.logger = get_logger(f"{__name__}.PipelineManager")
    
    def create_pipeline(self, pipeline_config: Dict[str, Any]) -> Pipeline:
        """
        Create a new pipeline.
        
        Args:
            pipeline_config: Pipeline configuration
            
        Returns:
            Created pipeline
        """
        pipeline_id = pipeline_config.get('id', str(uuid.uuid4()))
        name = pipeline_config['name']
        description = pipeline_config.get('description', '')
        
        pipeline = Pipeline(pipeline_id, name, description)
        
        # Add stages
        for stage_config in pipeline_config.get('stages', []):
            stage = PipelineStage(
                name=stage_config['name'],
                executor=stage_config['executor'],
                depends_on=stage_config.get('depends_on', []),
                timeout_seconds=stage_config.get('timeout_seconds', 3600),
                retry_count=stage_config.get('retry_count', 0),
                allow_failure=stage_config.get('allow_failure', False),
                when=stage_config.get('when', 'always'),
                environment=stage_config.get('environment', {}),
                artifacts=stage_config.get('artifacts', [])
            )
            pipeline.add_stage(stage)
        
        # Set variables and triggers
        pipeline.variables = pipeline_config.get('variables', {})
        pipeline.triggers = pipeline_config.get('triggers', [])
        pipeline.enabled = pipeline_config.get('enabled', True)
        
        # Validate pipeline
        errors = pipeline.validate()
        if errors:
            raise ValueError(f"Pipeline validation failed: {'; '.join(errors)}")
        
        self.pipelines[pipeline_id] = pipeline
        self.logger.info(f"Created pipeline: {name} ({pipeline_id})")
        
        return pipeline
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self.pipelines.get(pipeline_id)
    
    def list_pipelines(self) -> List[Pipeline]:
        """List all pipelines."""
        return list(self.pipelines.values())
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline."""
        if pipeline_id in self.pipelines:
            del self.pipelines[pipeline_id]
            self.logger.info(f"Deleted pipeline: {pipeline_id}")
            return True
        return False
    
    async def execute_pipeline(self, pipeline_id: str, trigger: str = "manual",
                             variables: Optional[Dict[str, str]] = None,
                             branch: Optional[str] = None,
                             commit: Optional[str] = None) -> str:
        """
        Execute a pipeline.
        
        Args:
            pipeline_id: Pipeline to execute
            trigger: Execution trigger
            variables: Optional runtime variables
            branch: Optional branch name
            commit: Optional commit hash
            
        Returns:
            Execution ID
        """
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        pipeline = self.pipelines[pipeline_id]
        
        if not pipeline.enabled:
            raise ValueError(f"Pipeline is disabled: {pipeline_id}")
        
        # Check concurrent execution limit
        if len(self.running_executions) >= self.max_concurrent_executions:
            raise RuntimeError("Maximum concurrent executions reached")
        
        execution_id = str(uuid.uuid4())
        execution = PipelineExecution(
            pipeline_id=pipeline_id,
            execution_id=execution_id,
            status=PipelineStatus.PENDING,
            start_time=datetime.now(timezone.utc),
            trigger=trigger,
            branch=branch,
            commit=commit
        )
        
        # Merge variables
        execution.metadata['variables'] = {**pipeline.variables, **(variables or {})}
        
        self.executions[execution_id] = execution
        self.execution_history.append(execution_id)
        
        # Limit history size
        if len(self.execution_history) > self.max_history_size:
            old_execution_id = self.execution_history.pop(0)
            if old_execution_id in self.executions:
                del self.executions[old_execution_id]
        
        # Start execution
        self.running_executions.add(execution_id)
        asyncio.create_task(self._execute_pipeline_async(execution_id))
        
        self.logger.info(f"Started pipeline execution: {pipeline.name} ({execution_id})")
        
        return execution_id
    
    async def _execute_pipeline_async(self, execution_id: str):
        """Execute pipeline asynchronously."""
        try:
            execution = self.executions[execution_id]
            pipeline = self.pipelines[execution.pipeline_id]
            
            execution.status = PipelineStatus.RUNNING
            
            # Build execution graph
            execution_graph = self._build_execution_graph(pipeline)
            
            # Execute stages
            await self._execute_stages(execution, pipeline, execution_graph)
            
            # Determine final status
            failed_stages = [r for r in execution.stage_results.values() if r.status == StageStatus.FAILED]
            if failed_stages:
                execution.status = PipelineStatus.FAILED
            else:
                execution.status = PipelineStatus.SUCCESS
            
        except Exception as e:
            execution.status = PipelineStatus.FAILED
            self.logger.error(f"Pipeline execution failed: {execution_id} - {e}")
        
        finally:
            execution.end_time = datetime.now(timezone.utc)
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            self.running_executions.discard(execution_id)
            
            self.logger.info(f"Pipeline execution completed: {execution_id} - {execution.status.value}")
    
    def _build_execution_graph(self, pipeline: Pipeline) -> Dict[str, List[str]]:
        """Build stage execution dependency graph."""
        graph = {}
        
        for stage_name in pipeline.stages:
            dependencies = pipeline.get_stage_dependencies(stage_name)
            graph[stage_name] = dependencies
        
        return graph
    
    async def _execute_stages(self, execution: PipelineExecution, pipeline: Pipeline,
                            execution_graph: Dict[str, List[str]]):
        """Execute pipeline stages with dependency resolution."""
        completed_stages = set()
        running_stages = set()
        
        while len(completed_stages) < len(pipeline.stages):
            # Find stages ready to run
            ready_stages = []
            for stage_name, dependencies in execution_graph.items():
                if (stage_name not in completed_stages and 
                    stage_name not in running_stages and
                    all(dep in completed_stages for dep in dependencies)):
                    ready_stages.append(stage_name)
            
            if not ready_stages:
                # Check if we're waiting for running stages
                if running_stages:
                    await asyncio.sleep(1)
                    continue
                else:
                    # Deadlock or all remaining stages failed dependencies
                    break
            
            # Start ready stages
            stage_tasks = []
            for stage_name in ready_stages:
                running_stages.add(stage_name)
                task = asyncio.create_task(
                    self._execute_stage(execution, pipeline.stages[stage_name])
                )
                stage_tasks.append((stage_name, task))
            
            # Wait for at least one stage to complete
            if stage_tasks:
                done, pending = await asyncio.wait(
                    [task for _, task in stage_tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed stages
                for stage_name, task in stage_tasks:
                    if task in done:
                        running_stages.remove(stage_name)
                        completed_stages.add(stage_name)
    
    async def _execute_stage(self, execution: PipelineExecution, stage: PipelineStage):
        """Execute a single pipeline stage."""
        stage_result = StageResult(
            stage_name=stage.name,
            status=StageStatus.RUNNING,
            start_time=datetime.now(timezone.utc)
        )
        
        execution.stage_results[stage.name] = stage_result
        
        try:
            # Check execution condition
            if not self._should_execute_stage(stage, execution):
                stage_result.status = StageStatus.SKIPPED
                stage_result.end_time = datetime.now(timezone.utc)
                return
            
            # Execute stage with retries
            for attempt in range(stage.retry_count + 1):
                try:
                    # Execute stage function
                    if asyncio.iscoroutinefunction(stage.executor):
                        result = await asyncio.wait_for(
                            stage.executor(execution, stage),
                            timeout=stage.timeout_seconds
                        )
                    else:
                        result = stage.executor(execution, stage)
                    
                    # Process result
                    if isinstance(result, dict):
                        stage_result.output = result.get('output')
                        stage_result.artifacts = result.get('artifacts', [])
                        stage_result.metadata = result.get('metadata', {})
                    else:
                        stage_result.output = str(result) if result is not None else None
                    
                    stage_result.status = StageStatus.SUCCESS
                    break
                    
                except asyncio.TimeoutError:
                    if attempt < stage.retry_count:
                        continue
                    stage_result.status = StageStatus.FAILED
                    stage_result.error = f"Stage timed out after {stage.timeout_seconds} seconds"
                    
                except Exception as e:
                    if attempt < stage.retry_count:
                        continue
                    stage_result.status = StageStatus.FAILED
                    stage_result.error = str(e)
        
        except Exception as e:
            stage_result.status = StageStatus.FAILED
            stage_result.error = str(e)
        
        finally:
            stage_result.end_time = datetime.now(timezone.utc)
            stage_result.duration_seconds = (stage_result.end_time - stage_result.start_time).total_seconds()
    
    def _should_execute_stage(self, stage: PipelineStage, execution: PipelineExecution) -> bool:
        """Determine if a stage should be executed based on conditions."""
        if stage.when == "always":
            return True
        elif stage.when == "on_success":
            # Check if all previous stages succeeded
            for result in execution.stage_results.values():
                if result.status == StageStatus.FAILED:
                    return False
            return True
        elif stage.when == "on_failure":
            # Check if any previous stage failed
            for result in execution.stage_results.values():
                if result.status == StageStatus.FAILED:
                    return True
            return False
        elif stage.when == "manual":
            return False  # Manual stages require explicit triggering
        
        return True
    
    def get_execution(self, execution_id: str) -> Optional[PipelineExecution]:
        """Get a pipeline execution by ID."""
        return self.executions.get(execution_id)
    
    def list_executions(self, pipeline_id: Optional[str] = None, limit: int = 50) -> List[PipelineExecution]:
        """List pipeline executions."""
        executions = []
        
        for exec_id in reversed(self.execution_history[-limit:]):
            if exec_id in self.executions:
                execution = self.executions[exec_id]
                if pipeline_id is None or execution.pipeline_id == pipeline_id:
                    executions.append(execution)
        
        return executions
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running pipeline execution."""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        if execution.status == PipelineStatus.RUNNING:
            execution.status = PipelineStatus.CANCELLED
            execution.end_time = datetime.now(timezone.utc)
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            
            self.running_executions.discard(execution_id)
            
            self.logger.info(f"Cancelled pipeline execution: {execution_id}")
            return True
        
        return False
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        total_executions = len(self.execution_history)
        successful_executions = len([
            e for e in self.executions.values() 
            if e.status == PipelineStatus.SUCCESS
        ])
        failed_executions = len([
            e for e in self.executions.values() 
            if e.status == PipelineStatus.FAILED
        ])
        
        return {
            'total_pipelines': len(self.pipelines),
            'enabled_pipelines': len([p for p in self.pipelines.values() if p.enabled]),
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0.0,
            'running_executions': len(self.running_executions),
            'max_concurrent_executions': self.max_concurrent_executions
        }
