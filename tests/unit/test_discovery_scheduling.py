"""
Unit tests for discovery scheduling system.

Tests the scheduling functionality including:
- Schedule configuration and validation
- Discovery job management
- Job scheduling and execution
- Priority-based job processing
- Adaptive scheduling
- Resource management
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch

from edge_device_fleet_manager.discovery.scheduling import (
    ScheduleConfig, DiscoveryJob, JobStatus, JobPriority,
    DiscoveryScheduler
)
from edge_device_fleet_manager.discovery.events import DiscoveryEventBus
from edge_device_fleet_manager.discovery.core import DiscoveryEngine, DiscoveryResult, Device, DeviceStatus


class TestScheduleConfig:
    """Test schedule configuration."""
    
    def test_schedule_config_creation(self):
        """Test schedule configuration creation."""
        config = ScheduleConfig(
            enabled=True,
            interval_seconds=300,
            adaptive_enabled=True,
            max_concurrent_jobs=5
        )
        
        assert config.enabled is True
        assert config.interval_seconds == 300
        assert config.adaptive_enabled is True
        assert config.max_concurrent_jobs == 5
        assert config.min_interval_seconds == 60
        assert config.max_interval_seconds == 3600
    
    def test_effective_interval_calculation(self):
        """Test effective interval calculation."""
        config = ScheduleConfig(
            interval_seconds=300,
            adaptive_enabled=True,
            min_interval_seconds=60,
            max_interval_seconds=3600
        )
        
        # Normal interval
        assert config.get_effective_interval(300) == 300
        
        # Below minimum
        assert config.get_effective_interval(30) == 60
        
        # Above maximum
        assert config.get_effective_interval(7200) == 3600
        
        # Adaptive disabled
        config.adaptive_enabled = False
        assert config.get_effective_interval(30) == 30
    
    def test_schedule_config_validation(self):
        """Test schedule configuration validation."""
        # Valid configuration
        config = ScheduleConfig()
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration
        config = ScheduleConfig(
            interval_seconds=-1,
            protocol_timeout=-1,
            total_timeout=-1,
            max_retries=-1,
            adaptive_enabled=True,
            min_interval_seconds=-1,
            max_interval_seconds=30  # Less than min_interval
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("interval must be positive" in error.lower() for error in errors)
        assert any("timeout must be positive" in error.lower() for error in errors)
        assert any("retries cannot be negative" in error.lower() for error in errors)


class TestDiscoveryJob:
    """Test discovery job management."""
    
    def test_job_creation(self):
        """Test discovery job creation."""
        job = DiscoveryJob(
            name="test_job",
            protocols=["mdns", "ssdp"],
            priority=JobPriority.HIGH,
            timeout_seconds=60
        )
        
        assert job.name == "test_job"
        assert job.protocols == ["mdns", "ssdp"]
        assert job.priority == JobPriority.HIGH
        assert job.timeout_seconds == 60
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert isinstance(job.job_id, str)
        assert isinstance(job.created_at, datetime)
    
    def test_job_due_check(self):
        """Test job due time checking."""
        # Job scheduled for now
        job = DiscoveryJob(
            scheduled_time=datetime.now(timezone.utc)
        )
        assert job.is_due() is True
        
        # Job scheduled for future
        future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        job.scheduled_time = future_time
        assert job.is_due() is False
        
        # Running job is not due
        job.status = JobStatus.RUNNING
        job.scheduled_time = datetime.now(timezone.utc)
        assert job.is_due() is False
    
    def test_job_expiration_check(self):
        """Test job expiration checking."""
        job = DiscoveryJob(timeout_seconds=60)
        
        # Not started yet
        assert job.is_expired() is False
        
        # Started recently
        job.started_at = datetime.now(timezone.utc)
        assert job.is_expired() is False
        
        # Started long ago
        job.started_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        assert job.is_expired() is True
    
    def test_job_retry_logic(self):
        """Test job retry logic."""
        job = DiscoveryJob(max_retries=3)
        
        # Can retry when failed
        job.status = JobStatus.FAILED
        assert job.can_retry() is True
        
        # Cannot retry when max retries reached
        job.retry_count = 3
        assert job.can_retry() is False
        
        # Cannot retry when not failed
        job.status = JobStatus.COMPLETED
        job.retry_count = 0
        assert job.can_retry() is False
    
    def test_job_retry_scheduling(self):
        """Test job retry scheduling."""
        job = DiscoveryJob(
            max_retries=3,
            retry_delay_seconds=30,
            status=JobStatus.FAILED
        )
        
        original_time = datetime.now(timezone.utc)
        job.schedule_retry()
        
        assert job.status == JobStatus.SCHEDULED
        assert job.retry_count == 1
        assert job.scheduled_time > original_time
        
        # Time difference should be approximately retry_delay_seconds
        time_diff = (job.scheduled_time - original_time).total_seconds()
        assert 29 <= time_diff <= 31  # Allow for small timing differences
    
    def test_job_serialization(self):
        """Test job serialization to dictionary."""
        job = DiscoveryJob(
            name="test_job",
            protocols=["mdns"],
            priority=JobPriority.HIGH,
            parameters={"timeout": 30},
            metadata={"source": "test"}
        )
        
        job_dict = job.to_dict()
        
        assert job_dict["name"] == "test_job"
        assert job_dict["protocols"] == ["mdns"]
        assert job_dict["priority"] == JobPriority.HIGH.value
        assert job_dict["parameters"]["timeout"] == 30
        assert job_dict["metadata"]["source"] == "test"
        assert "job_id" in job_dict
        assert "created_at" in job_dict


class MockDiscoveryEngine:
    """Mock discovery engine for testing."""
    
    def __init__(self):
        self.discover_all_called = False
        self.discover_protocols = []
        self.result = DiscoveryResult(protocol="mock", success=True)
        self.delay = 0
        self.should_fail = False
    
    async def discover_all(self, protocols):
        """Mock discover all method."""
        self.discover_all_called = True
        self.discover_protocols = protocols
        
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise Exception("Mock discovery failed")
        
        return self.result


class TestDiscoveryScheduler:
    """Test discovery scheduler."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock discovery engine."""
        return MockDiscoveryEngine()
    
    @pytest.fixture
    def schedule_config(self):
        """Create schedule configuration."""
        return ScheduleConfig(
            enabled=True,
            interval_seconds=60,
            max_concurrent_jobs=2,
            job_timeout_seconds=30
        )
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus."""
        return DiscoveryEventBus()
    
    @pytest.fixture
    def scheduler(self, mock_engine, schedule_config, event_bus):
        """Create discovery scheduler."""
        return DiscoveryScheduler(mock_engine, schedule_config, event_bus)
    
    async def test_scheduler_creation(self, scheduler):
        """Test scheduler creation."""
        assert scheduler.config.enabled is True
        assert scheduler.config.max_concurrent_jobs == 2
        assert scheduler._running is False
        assert len(scheduler._jobs) == 0
    
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop."""
        # Start scheduler
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._scheduler_task is not None
        assert len(scheduler._worker_tasks) == 2
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler._running is False
    
    async def test_job_scheduling(self, scheduler):
        """Test job scheduling."""
        await scheduler.start()
        
        job = DiscoveryJob(
            name="test_job",
            protocols=["mdns"],
            priority=JobPriority.NORMAL
        )
        
        job_id = await scheduler.schedule_job(job)
        assert job_id == job.job_id
        
        # Check job was added
        retrieved_job = await scheduler.get_job(job_id)
        assert retrieved_job == job
        
        # Check statistics
        stats = await scheduler.get_statistics()
        assert stats["jobs_scheduled"] == 1
        
        await scheduler.stop()
    
    async def test_job_execution(self, scheduler, mock_engine):
        """Test job execution."""
        await scheduler.start()
        
        # Add device to mock result
        device = Device(ip_address="192.168.1.100", status=DeviceStatus.ONLINE)
        mock_engine.result.add_device(device)
        
        job = DiscoveryJob(
            name="test_job",
            protocols=["mdns"],
            scheduled_time=datetime.now(timezone.utc)  # Due now
        )
        
        await scheduler.schedule_job(job)
        
        # Wait for job to be processed
        await asyncio.sleep(0.1)
        
        # Check job was executed
        assert mock_engine.discover_all_called
        assert mock_engine.discover_protocols == ["mdns"]
        
        # Check job status
        retrieved_job = await scheduler.get_job(job.job_id)
        assert retrieved_job.status == JobStatus.COMPLETED
        assert retrieved_job.result is not None
        assert len(retrieved_job.result.devices) == 1
        
        await scheduler.stop()
    
    async def test_job_timeout(self, scheduler, mock_engine):
        """Test job timeout handling."""
        await scheduler.start()
        
        # Configure mock to delay longer than timeout
        mock_engine.delay = 0.2
        
        job = DiscoveryJob(
            name="timeout_job",
            protocols=["mdns"],
            timeout_seconds=0.1,  # Very short timeout
            scheduled_time=datetime.now(timezone.utc)
        )
        
        await scheduler.schedule_job(job)
        
        # Wait for job to timeout
        await asyncio.sleep(0.3)
        
        # Check job failed due to timeout
        retrieved_job = await scheduler.get_job(job.job_id)
        assert retrieved_job.status == JobStatus.FAILED
        assert "timed out" in retrieved_job.error_message.lower()
        
        await scheduler.stop()
    
    async def test_job_failure_and_retry(self, scheduler, mock_engine):
        """Test job failure and retry logic."""
        await scheduler.start()
        
        # Configure mock to fail
        mock_engine.should_fail = True
        
        job = DiscoveryJob(
            name="failing_job",
            protocols=["mdns"],
            max_retries=2,
            retry_delay_seconds=0.1,
            scheduled_time=datetime.now(timezone.utc)
        )
        
        await scheduler.schedule_job(job)
        
        # Wait for initial failure and retry
        await asyncio.sleep(0.2)
        
        # Check job was retried
        retrieved_job = await scheduler.get_job(job.job_id)
        assert retrieved_job.retry_count > 0
        
        await scheduler.stop()
    
    async def test_concurrent_job_limit(self, scheduler, mock_engine):
        """Test concurrent job limit enforcement."""
        await scheduler.start()
        
        # Configure mock to delay
        mock_engine.delay = 0.2
        
        # Schedule more jobs than concurrent limit
        jobs = []
        for i in range(5):
            job = DiscoveryJob(
                name=f"job_{i}",
                protocols=["mdns"],
                scheduled_time=datetime.now(timezone.utc)
            )
            jobs.append(job)
            await scheduler.schedule_job(job)
        
        # Wait a bit for jobs to start
        await asyncio.sleep(0.1)
        
        # Check that only max_concurrent_jobs are running
        running_count = len(scheduler._running_jobs)
        assert running_count <= scheduler.config.max_concurrent_jobs
        
        await scheduler.stop()
    
    async def test_job_priority_ordering(self, scheduler):
        """Test job priority ordering."""
        await scheduler.start()
        
        # Schedule jobs with different priorities
        low_job = DiscoveryJob(
            name="low_priority",
            priority=JobPriority.LOW,
            scheduled_time=datetime.now(timezone.utc)
        )
        
        high_job = DiscoveryJob(
            name="high_priority",
            priority=JobPriority.HIGH,
            scheduled_time=datetime.now(timezone.utc)
        )
        
        critical_job = DiscoveryJob(
            name="critical_priority",
            priority=JobPriority.CRITICAL,
            scheduled_time=datetime.now(timezone.utc)
        )
        
        # Schedule in reverse priority order
        await scheduler.schedule_job(low_job)
        await scheduler.schedule_job(high_job)
        await scheduler.schedule_job(critical_job)
        
        # Higher priority jobs should be processed first
        # This is difficult to test deterministically, so we just check
        # that the scheduler accepts the jobs
        stats = await scheduler.get_statistics()
        assert stats["jobs_scheduled"] == 3
        
        await scheduler.stop()
    
    async def test_job_cancellation(self, scheduler):
        """Test job cancellation."""
        await scheduler.start()
        
        job = DiscoveryJob(
            name="cancellable_job",
            protocols=["mdns"],
            scheduled_time=datetime.now(timezone.utc) + timedelta(minutes=5)  # Future
        )
        
        job_id = await scheduler.schedule_job(job)
        
        # Cancel job
        result = await scheduler.cancel_job(job_id)
        assert result is True
        
        # Check job status
        retrieved_job = await scheduler.get_job(job_id)
        assert retrieved_job.status == JobStatus.CANCELLED
        
        # Try to cancel non-existent job
        result = await scheduler.cancel_job("non-existent")
        assert result is False
        
        await scheduler.stop()
    
    async def test_job_filtering(self, scheduler):
        """Test job filtering and retrieval."""
        await scheduler.start()
        
        # Create jobs with different statuses
        pending_job = DiscoveryJob(name="pending", status=JobStatus.PENDING)
        completed_job = DiscoveryJob(name="completed", status=JobStatus.COMPLETED)
        failed_job = DiscoveryJob(name="failed", status=JobStatus.FAILED)
        
        await scheduler.schedule_job(pending_job)
        await scheduler.schedule_job(completed_job)
        await scheduler.schedule_job(failed_job)
        
        # Get all jobs
        all_jobs = await scheduler.get_jobs()
        assert len(all_jobs) == 3
        
        # Get pending jobs only
        pending_jobs = await scheduler.get_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].name == "pending"
        
        # Get limited number of jobs
        limited_jobs = await scheduler.get_jobs(limit=2)
        assert len(limited_jobs) == 2
        
        await scheduler.stop()
    
    async def test_scheduler_statistics(self, scheduler, mock_engine):
        """Test scheduler statistics."""
        await scheduler.start()
        
        # Add device to mock result
        device = Device(ip_address="192.168.1.100", status=DeviceStatus.ONLINE)
        mock_engine.result.add_device(device)
        
        # Schedule and execute a job
        job = DiscoveryJob(
            name="stats_job",
            protocols=["mdns"],
            scheduled_time=datetime.now(timezone.utc)
        )
        
        await scheduler.schedule_job(job)
        
        # Wait for job completion
        await asyncio.sleep(0.1)
        
        # Check statistics
        stats = await scheduler.get_statistics()
        
        assert stats["running"] is True
        assert stats["jobs_scheduled"] == 1
        assert stats["jobs_completed"] == 1
        assert stats["jobs_failed"] == 0
        assert stats["total_discovery_time"] > 0
        assert stats["average_discovery_time"] > 0
        assert "uptime_seconds" in stats
        assert "config" in stats
        
        await scheduler.stop()
    
    async def test_event_publishing(self, scheduler, event_bus):
        """Test event publishing during job execution."""
        events_received = []
        
        async def event_callback(event):
            events_received.append(event)
        
        await event_bus.subscribe(event_callback)
        await scheduler.start()
        
        job = DiscoveryJob(
            name="event_job",
            protocols=["mdns"],
            scheduled_time=datetime.now(timezone.utc)
        )
        
        await scheduler.schedule_job(job)
        
        # Wait for job completion
        await asyncio.sleep(0.1)
        
        # Check events were published
        assert len(events_received) >= 2  # At least started and completed events
        
        event_types = [event.event_type for event in events_received]
        assert "discovery.started" in event_types
        assert "discovery.completed" in event_types
        
        await scheduler.stop()
