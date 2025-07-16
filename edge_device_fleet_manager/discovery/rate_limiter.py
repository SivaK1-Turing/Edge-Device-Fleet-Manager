"""
Rate limiting for discovery operations.

This module provides adaptive rate limiting to prevent overwhelming network resources
and target devices during discovery operations.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Optional

from .exceptions import RateLimitExceededError
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    per_host_limit: float = 2.0
    global_limit: float = 100.0
    backoff_factor: float = 1.5
    max_backoff: float = 60.0


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        async with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait until tokens are available."""
        start_time = time.time()
        
        while True:
            if await self.consume(tokens):
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # Calculate wait time
            async with self._lock:
                needed_tokens = tokens - self.tokens
                wait_time = needed_tokens / self.rate
                wait_time = min(wait_time, 1.0)  # Cap at 1 second
            
            await asyncio.sleep(wait_time)


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on network conditions."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.global_bucket = TokenBucket(config.global_limit, int(config.global_limit * 2))
        self.host_buckets: Dict[str, TokenBucket] = {}
        self.host_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.backoff_delays: Dict[str, float] = defaultdict(float)
        self.logger = get_logger(__name__)
    
    def _get_host_bucket(self, host: str) -> TokenBucket:
        """Get or create a token bucket for a specific host."""
        if host not in self.host_buckets:
            self.host_buckets[host] = TokenBucket(
                self.config.per_host_limit,
                int(self.config.per_host_limit * 2)
            )
        return self.host_buckets[host]
    
    async def acquire(self, host: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request to a host."""
        # Check global rate limit
        if not await self.global_bucket.wait_for_tokens(1, timeout):
            raise RateLimitExceededError("Global rate limit exceeded")
        
        # Check per-host rate limit
        host_bucket = self._get_host_bucket(host)
        if not await host_bucket.wait_for_tokens(1, timeout):
            raise RateLimitExceededError(f"Rate limit exceeded for host {host}")
        
        # Apply adaptive backoff if needed
        backoff_delay = self.backoff_delays.get(host, 0)
        if backoff_delay > 0:
            await asyncio.sleep(backoff_delay)
        
        return True
    
    def record_success(self, host: str, response_time: float) -> None:
        """Record a successful request."""
        self.host_stats[host].append({
            'success': True,
            'response_time': response_time,
            'timestamp': time.time()
        })
        
        # Reduce backoff on success
        if host in self.backoff_delays:
            self.backoff_delays[host] = max(0, self.backoff_delays[host] * 0.8)
    
    def record_failure(self, host: str, error_type: str = "unknown") -> None:
        """Record a failed request."""
        self.host_stats[host].append({
            'success': False,
            'error_type': error_type,
            'timestamp': time.time()
        })
        
        # Increase backoff on failure
        current_backoff = self.backoff_delays.get(host, 0.1)
        self.backoff_delays[host] = min(
            self.config.max_backoff,
            current_backoff * self.config.backoff_factor
        )
        
        self.logger.warning(
            "Request failed, increasing backoff",
            host=host,
            error_type=error_type,
            new_backoff=self.backoff_delays[host]
        )
    
    def get_host_stats(self, host: str) -> Dict:
        """Get statistics for a specific host."""
        stats = self.host_stats.get(host, deque())
        if not stats:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'current_backoff': 0.0
            }
        
        total = len(stats)
        successes = sum(1 for s in stats if s['success'])
        success_rate = successes / total if total > 0 else 0.0
        
        response_times = [s['response_time'] for s in stats if s['success'] and 'response_time' in s]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            'total_requests': total,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'current_backoff': self.backoff_delays.get(host, 0.0)
        }
    
    def get_global_stats(self) -> Dict:
        """Get global rate limiting statistics."""
        all_stats = []
        for host_stats in self.host_stats.values():
            all_stats.extend(host_stats)
        
        if not all_stats:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'active_hosts': 0
            }
        
        total = len(all_stats)
        successes = sum(1 for s in all_stats if s['success'])
        success_rate = successes / total if total > 0 else 0.0
        
        response_times = [s['response_time'] for s in all_stats if s['success'] and 'response_time' in s]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            'total_requests': total,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'active_hosts': len(self.host_buckets)
        }


class RateLimiter:
    """Main rate limiter interface."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.limiter = AdaptiveRateLimiter(self.config)
        self.logger = get_logger(__name__)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def acquire(self, host: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request."""
        return await self.limiter.acquire(host, timeout)
    
    def record_success(self, host: str, response_time: float) -> None:
        """Record a successful request."""
        self.limiter.record_success(host, response_time)
    
    def record_failure(self, host: str, error_type: str = "unknown") -> None:
        """Record a failed request."""
        self.limiter.record_failure(host, error_type)
    
    def get_stats(self, host: Optional[str] = None) -> Dict:
        """Get rate limiting statistics."""
        if host:
            return self.limiter.get_host_stats(host)
        else:
            return self.limiter.get_global_stats()
