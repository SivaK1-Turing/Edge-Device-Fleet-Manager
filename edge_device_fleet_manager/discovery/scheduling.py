"""
Discovery Scheduling System

This module provides comprehensive scheduling capabilities for device discovery,
including periodic discovery, adaptive scheduling, and background scanning.

Key Features:
- Periodic discovery with configurable intervals
- Adaptive scheduling based on network activity
- Background continuous scanning
- Priority-based job scheduling
- Resource-aware scheduling
- Schedule persistence and recovery
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from ..core.logging import get_logger
from .core import DiscoveryEngine, DiscoveryResult
from .events import DiscoveryEventBus, DiscoveryStartedEvent, DiscoveryCompletedEvent, DiscoveryErrorEvent


class JobStatus(Enum):
    """Discovery job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class JobPriority(Enum):
    """Discovery job priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduleConfig:
    """Configuration for discovery scheduling."""
    
    # Basic scheduling
    enabled: bool = True
    interval_seconds: int = 300  # 5 minutes default
    initial_delay_seconds: int = 0
    
    # Adaptive scheduling
    adaptive_enabled: bool = True
    min_interval_seconds: int = 60
    max_interval_seconds: int = 3600
    activity_threshold: float = 0.1
    
    # Resource limits
    max_concurrent_jobs: int = 3
    job_timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 30
    
    # Protocol selection
    protocols: List[str] = field(default_factory=list)
    protocol_weights: Dict[str, float] = field(default_factory=dict)
    
    # Advanced options
    jitter_enabled: bool = True
    jitter_max_seconds: int = 30
    backoff_enabled: bool = True
    backoff_factor: float = 2.0
    
    def get_effective_interval(self, base_interval: Optional[int] = None) -> int:
        """Get effective interval with adaptive adjustments."""
        interval = base_interval or self.interval_seconds
        
        if self.adaptive_enabled:
            interval = max(self.min_interval_seconds, min(self.max_interval_seconds, interval))
        
        return interval


@dataclass
class DiscoveryJob:
    """Represents a discovery job."""
    
    job_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    protocols: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Scheduling
    priority: JobPriority = JobPriority.NORMAL
    scheduled_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 30
    
    # Status tracking
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Optional[DiscoveryResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_due(self) -> bool:
        """Check if job is due for execution."""
        return (
            self.status in [JobStatus.PENDING, JobStatus.SCHEDULED] and
            datetime.now(timezone.utc) >= self.scheduled_time
        )
    
    def is_expired(self) -> bool:
        """Check if job has expired."""
        if self.started_at:
            elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            return elapsed > self.timeout_seconds
        return False
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED and
            self.retry_count < self.max_retries
        )
    
    def schedule_retry(self) -> None:
        """Schedule job for retry."""
        if self.can_retry():
            self.retry_count += 1
            self.status = JobStatus.SCHEDULED
            self.scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=self.retry_delay_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation."""
        return {
            "job_id": self.job_id,
            "name": self.name,
            "protocols": self.protocols,
            "parameters": self.parameters,
            "priority": self.priority.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


class DiscoveryScheduler:
    """
    Main discovery scheduler.
    
    Manages discovery jobs, handles scheduling, and coordinates with
    the discovery engine and event system.
    """
    
    def __init__(
        self,
        discovery_engine: DiscoveryEngine,
        config: ScheduleConfig,
        event_bus: Optional[DiscoveryEventBus] = None
    ):
        self.discovery_engine = discovery_engine
        self.config = config
        self.event_bus = event_bus
        self.logger = get_logger(__name__)
        
        # Job management
        self._jobs: Dict[str, DiscoveryJob] = {}
        self._job_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_jobs: Set[str] = set()
        self._job_lock = asyncio.Lock()
        
        # Scheduler state
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._worker_tasks: List[asyncio.Task] = []
        
        # Statistics
        self._stats = {
            "jobs_scheduled": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_cancelled": 0,
            "total_discovery_time": 0.0,
            "start_time": datetime.now(timezone.utc)
        }
    
    async def start(self) -> None:
        """Start the discovery scheduler."""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting discovery scheduler")
        
        # Start scheduler task
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_jobs):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(worker_task)
        
        self.logger.info(
            "Discovery scheduler started",
            max_concurrent_jobs=self.config.max_concurrent_jobs,
            interval_seconds=self.config.interval_seconds
        )
    
    async def stop(self) -> None:
        """Stop the discovery scheduler."""
        if not self._running:
            return
        
        self._running = False
        self.logger.info("Stopping discovery scheduler")
        
        # Cancel scheduler task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Cancel running jobs
        async with self._job_lock:
            for job_id in list(self._running_jobs):
                job = self._jobs.get(job_id)
                if job:
                    job.status = JobStatus.CANCELLED
                    self._stats["jobs_cancelled"] += 1
        
        self.logger.info("Discovery scheduler stopped")
    
    async def schedule_job(self, job: DiscoveryJob) -> str:
        """Schedule a discovery job."""
        async with self._job_lock:
            self._jobs[job.job_id] = job
            
            # Add to priority queue (lower priority value = higher priority)
            priority = (job.priority.value, job.scheduled_time.timestamp())
            await self._job_queue.put((priority, job.job_id))
            
            self._stats["jobs_scheduled"] += 1
        
        self.logger.info(
            "Discovery job scheduled",
            job_id=job.job_id,
            name=job.name,
            priority=job.priority.value,
            scheduled_time=job.scheduled_time.isoformat()
        )
        
        return job.job_id
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a discovery job."""
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if job and job.status in [JobStatus.PENDING, JobStatus.SCHEDULED]:
                job.status = JobStatus.CANCELLED
                self._stats["jobs_cancelled"] += 1
                
                self.logger.info("Discovery job cancelled", job_id=job_id)
                return True
        
        return False
    
    async def get_job(self, job_id: str) -> Optional[DiscoveryJob]:
        """Get a job by ID."""
        async with self._job_lock:
            return self._jobs.get(job_id)
    
    async def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None
    ) -> List[DiscoveryJob]:
        """Get jobs with optional filtering."""
        async with self._job_lock:
            jobs = list(self._jobs.values())
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        if limit:
            jobs = jobs[:limit]
        
        return jobs
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        async with self._job_lock:
            running_jobs = len(self._running_jobs)
            pending_jobs = len([j for j in self._jobs.values() if j.status == JobStatus.PENDING])
            queue_size = self._job_queue.qsize()
        
        uptime = (datetime.now(timezone.utc) - self._stats["start_time"]).total_seconds()
        
        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "jobs_scheduled": self._stats["jobs_scheduled"],
            "jobs_completed": self._stats["jobs_completed"],
            "jobs_failed": self._stats["jobs_failed"],
            "jobs_cancelled": self._stats["jobs_cancelled"],
            "running_jobs": running_jobs,
            "pending_jobs": pending_jobs,
            "queue_size": queue_size,
            "total_discovery_time": self._stats["total_discovery_time"],
            "average_discovery_time": (
                self._stats["total_discovery_time"] / max(1, self._stats["jobs_completed"])
            ),
            "config": {
                "enabled": self.config.enabled,
                "interval_seconds": self.config.interval_seconds,
                "max_concurrent_jobs": self.config.max_concurrent_jobs,
                "adaptive_enabled": self.config.adaptive_enabled
            }
        }
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                if self.config.enabled:
                    await self._schedule_periodic_discovery()
                
                # Sleep for a short interval to avoid busy waiting
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Scheduler loop error", error=str(e), exc_info=e)
                await asyncio.sleep(5)  # Back off on error
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Worker loop for processing jobs."""
        while self._running:
            try:
                # Get next job from queue (with timeout to allow cancellation)
                try:
                    priority, job_id = await asyncio.wait_for(
                        self._job_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the job
                await self._process_job(job_id, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Worker loop error",
                    worker=worker_name,
                    error=str(e),
                    exc_info=e
                )
    
    async def _schedule_periodic_discovery(self) -> None:
        """Schedule periodic discovery jobs."""
        # This is a simplified implementation
        # In a real system, you'd track the last discovery time and schedule accordingly
        
        # Check if we need to schedule a new periodic job
        async with self._job_lock:
            pending_periodic = any(
                job.name == "periodic_discovery" and job.status in [JobStatus.PENDING, JobStatus.SCHEDULED]
                for job in self._jobs.values()
            )
        
        if not pending_periodic:
            # Create periodic discovery job
            job = DiscoveryJob(
                name="periodic_discovery",
                protocols=self.config.protocols or [],
                priority=JobPriority.NORMAL,
                scheduled_time=datetime.now(timezone.utc) + timedelta(seconds=self.config.initial_delay_seconds),
                timeout_seconds=self.config.job_timeout_seconds,
                max_retries=self.config.max_retries,
                retry_delay_seconds=self.config.retry_delay_seconds
            )
            
            await self.schedule_job(job)
    
    async def _process_job(self, job_id: str, worker_name: str) -> None:
        """Process a discovery job."""
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if not job or not job.is_due():
                return
            
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            self._running_jobs.add(job_id)
        
        self.logger.info(
            "Starting discovery job",
            job_id=job_id,
            worker=worker_name,
            protocols=job.protocols
        )
        
        # Publish discovery started event
        if self.event_bus:
            event = DiscoveryStartedEvent(
                protocols=job.protocols,
                scan_parameters=job.parameters,
                source=f"scheduler.{worker_name}"
            )
            await self.event_bus.publish(event)
        
        try:
            # Execute discovery
            start_time = datetime.now(timezone.utc)
            result = await asyncio.wait_for(
                self.discovery_engine.discover_all(job.protocols),
                timeout=job.timeout_seconds
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Update job with results
            async with self._job_lock:
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                self._running_jobs.discard(job_id)
                
                self._stats["jobs_completed"] += 1
                self._stats["total_discovery_time"] += duration
            
            # Publish discovery completed event
            if self.event_bus:
                event = DiscoveryCompletedEvent(
                    result=result,
                    duration=duration,
                    devices_found=len(result.devices),
                    source=f"scheduler.{worker_name}"
                )
                await self.event_bus.publish(event)
            
            self.logger.info(
                "Discovery job completed",
                job_id=job_id,
                worker=worker_name,
                duration=duration,
                devices_found=len(result.devices)
            )
            
        except asyncio.TimeoutError:
            await self._handle_job_failure(job_id, "Job timed out", worker_name)
        except Exception as e:
            await self._handle_job_failure(job_id, str(e), worker_name)
    
    async def _handle_job_failure(self, job_id: str, error_message: str, worker_name: str) -> None:
        """Handle job failure."""
        async with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            job.error_message = error_message
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            self._running_jobs.discard(job_id)
            
            self._stats["jobs_failed"] += 1
        
        # Publish discovery error event
        if self.event_bus:
            event = DiscoveryErrorEvent(
                error_message=error_message,
                error_type="job_failure",
                protocol=",".join(job.protocols),
                recoverable=job.can_retry(),
                source=f"scheduler.{worker_name}"
            )
            await self.event_bus.publish(event)
        
        # Schedule retry if possible
        if job.can_retry():
            job.schedule_retry()
            priority = (job.priority.value, job.scheduled_time.timestamp())
            await self._job_queue.put((priority, job_id))
            
            self.logger.info(
                "Discovery job scheduled for retry",
                job_id=job_id,
                retry_count=job.retry_count,
                next_attempt=job.scheduled_time.isoformat()
            )
        else:
            self.logger.error(
                "Discovery job failed",
                job_id=job_id,
                worker=worker_name,
                error=error_message
            )
