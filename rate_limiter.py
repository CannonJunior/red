#!/usr/bin/env python3
"""
Rate Limiting Module

Provides IP-based rate limiting for API endpoints using token bucket algorithm.

Features:
- Token bucket algorithm for smooth rate limiting
- IP-based tracking with automatic cleanup
- Configurable limits per endpoint
- Thread-safe implementation
- Decorator pattern for easy application
- Detailed rate limit headers in responses

Usage:
    from rate_limiter import rate_limit

    class MyHandler:
        @rate_limit(requests_per_minute=60, burst=10)
        def handle_api(self):
            # Your endpoint logic here
            pass
"""

import time
import threading
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from debug_logger import debug_log, info_log, error_log


@dataclass
class TokenBucket:
    """Token bucket for rate limiting with refill mechanism."""
    capacity: int  # Maximum tokens (burst capacity)
    tokens: float  # Current available tokens
    refill_rate: float  # Tokens per second
    last_refill: float  # Last refill timestamp

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            bool: True if tokens were consumed, False if insufficient tokens
        """
        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate

        # Add refilled tokens (capped at capacity)
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_wait_time(self) -> float:
        """Get time to wait until next token is available."""
        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1.0 - self.tokens
        return tokens_needed / self.refill_rate

    def get_reset_time(self) -> float:
        """Get timestamp when bucket will be full."""
        if self.tokens >= self.capacity:
            return time.time()

        tokens_needed = self.capacity - self.tokens
        seconds_to_full = tokens_needed / self.refill_rate
        return time.time() + seconds_to_full


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.

    Tracks rate limits per IP address and endpoint.
    """

    def __init__(self):
        """Initialize rate limiter with tracking storage."""
        # Storage: {(ip, endpoint): TokenBucket}
        self.buckets: Dict[Tuple[str, str], TokenBucket] = {}

        # Lock for thread safety
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'unique_ips': 0
        }

        # Cleanup configuration
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        self.bucket_expiry = 3600  # 1 hour of inactivity

        info_log("Rate limiter initialized", "🚦")

    def check_rate_limit(
        self,
        ip: str,
        endpoint: str,
        requests_per_minute: int,
        burst: int
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limit.

        Args:
            ip: Client IP address
            endpoint: API endpoint name
            requests_per_minute: Maximum requests per minute
            burst: Maximum burst capacity

        Returns:
            Tuple of (allowed: bool, info: dict)
            - allowed: True if request is allowed, False if rate limited
            - info: Dictionary with rate limit information
        """
        with self.lock:
            self.stats['total_requests'] += 1

            # Periodic cleanup of old buckets
            self._cleanup_old_buckets()

            # Get or create bucket for this IP + endpoint
            key = (ip, endpoint)
            if key not in self.buckets:
                # Create new bucket
                refill_rate = requests_per_minute / 60.0  # Convert to tokens per second
                self.buckets[key] = TokenBucket(
                    capacity=burst,
                    tokens=burst,  # Start with full bucket
                    refill_rate=refill_rate,
                    last_refill=time.time()
                )
                self.stats['unique_ips'] = len(set(k[0] for k in self.buckets.keys()))

            bucket = self.buckets[key]

            # Try to consume a token
            allowed = bucket.consume(1)

            # Prepare response info
            info = {
                'limit': requests_per_minute,
                'remaining': int(bucket.tokens),
                'reset': int(bucket.get_reset_time()),
                'retry_after': int(bucket.get_wait_time()) + 1 if not allowed else 0
            }

            if not allowed:
                self.stats['rate_limited'] += 1
                debug_log(f"Rate limited: {ip} on {endpoint} (wait {info['retry_after']}s)", "🚫")

            return allowed, info

    def _cleanup_old_buckets(self):
        """Remove inactive buckets to prevent memory leaks."""
        now = time.time()

        # Only cleanup periodically
        if now - self.last_cleanup < self.cleanup_interval:
            return

        self.last_cleanup = now

        # Find expired buckets
        expired_keys = []
        for key, bucket in self.buckets.items():
            if now - bucket.last_refill > self.bucket_expiry:
                expired_keys.append(key)

        # Remove expired buckets
        for key in expired_keys:
            del self.buckets[key]

        if expired_keys:
            debug_log(f"Cleaned up {len(expired_keys)} expired rate limit buckets", "🧹")
            self.stats['unique_ips'] = len(set(k[0] for k in self.buckets.keys()))

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics."""
        with self.lock:
            return {
                **self.stats,
                'active_buckets': len(self.buckets),
                'rate_limit_percentage': (
                    (self.stats['rate_limited'] / max(self.stats['total_requests'], 1)) * 100
                )
            }

    def reset_ip(self, ip: str):
        """Reset rate limits for a specific IP (admin function)."""
        with self.lock:
            keys_to_remove = [k for k in self.buckets.keys() if k[0] == ip]
            for key in keys_to_remove:
                del self.buckets[key]

            if keys_to_remove:
                info_log(f"Reset rate limits for IP: {ip}", "🔄")


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(requests_per_minute: int = 60, burst: Optional[int] = None, endpoint_name: Optional[str] = None):
    """
    Decorator for rate limiting HTTP handler methods.

    Args:
        requests_per_minute: Maximum requests per minute per IP
        burst: Maximum burst capacity (default: 2x requests_per_minute / 60)
        endpoint_name: Custom endpoint name (default: function name)

    Usage:
        @rate_limit(requests_per_minute=60, burst=10)
        def handle_chat_api(self):
            # Your endpoint code
            pass

    Returns:
        Decorated function with rate limiting
    """
    # Calculate default burst if not provided
    if burst is None:
        burst = max(10, int(requests_per_minute / 60 * 2))

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get endpoint name
            endpoint = endpoint_name or func.__name__

            # Get client IP from handler
            client_ip = self.client_address[0] if hasattr(self, 'client_address') else 'unknown'

            # Check rate limit
            allowed, info = _rate_limiter.check_rate_limit(
                ip=client_ip,
                endpoint=endpoint,
                requests_per_minute=requests_per_minute,
                burst=burst
            )

            # Add rate limit headers to response
            if hasattr(self, 'send_header'):
                self.send_header('X-RateLimit-Limit', str(info['limit']))
                self.send_header('X-RateLimit-Remaining', str(info['remaining']))
                self.send_header('X-RateLimit-Reset', str(info['reset']))

            if not allowed:
                # Rate limit exceeded
                if hasattr(self, 'send_header'):
                    self.send_header('Retry-After', str(info['retry_after']))

                if hasattr(self, 'send_json_response'):
                    self.send_json_response({
                        'status': 'error',
                        'error': 'Rate limit exceeded',
                        'message': f"Too many requests. Please wait {info['retry_after']} seconds.",
                        'retry_after': info['retry_after'],
                        'limit': info['limit'],
                        'reset': info['reset']
                    }, 429)
                else:
                    # Fallback for handlers without send_json_response
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    import json
                    response = json.dumps({
                        'error': 'Rate limit exceeded',
                        'retry_after': info['retry_after']
                    })
                    self.wfile.write(response.encode())

                return

            # Call original function
            return func(self, *args, **kwargs)

        return wrapper
    return decorator


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


# Testing
if __name__ == "__main__":
    print("Testing Rate Limiter...")

    # Create test rate limiter
    limiter = RateLimiter()

    # Test 1: Normal usage
    print("\n1. Testing normal usage (5 requests per minute, burst 3):")
    for i in range(5):
        allowed, info = limiter.check_rate_limit(
            ip="127.0.0.1",
            endpoint="test_api",
            requests_per_minute=5,
            burst=3
        )
        print(f"   Request {i+1}: {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']})")
        time.sleep(0.1)

    # Test 2: Burst limit
    print("\n2. Testing burst limit (rapid requests):")
    for i in range(5):
        allowed, info = limiter.check_rate_limit(
            ip="127.0.0.2",
            endpoint="test_api",
            requests_per_minute=60,
            burst=3
        )
        print(f"   Request {i+1}: {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']}, retry_after: {info['retry_after']}s)")

    # Test 3: Token refill
    print("\n3. Testing token refill (wait 2 seconds):")
    allowed, info = limiter.check_rate_limit(
        ip="127.0.0.3",
        endpoint="test_api",
        requests_per_minute=30,  # 0.5 tokens per second
        burst=2
    )
    print(f"   Request 1: {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']})")

    allowed, info = limiter.check_rate_limit("127.0.0.3", "test_api", 30, 2)
    print(f"   Request 2: {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']})")

    allowed, info = limiter.check_rate_limit("127.0.0.3", "test_api", 30, 2)
    print(f"   Request 3: {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']})")

    print("   Waiting 2 seconds for token refill...")
    time.sleep(2)

    allowed, info = limiter.check_rate_limit("127.0.0.3", "test_api", 30, 2)
    print(f"   Request 4 (after wait): {'✅ Allowed' if allowed else '❌ Rate limited'} (remaining: {info['remaining']})")

    # Test 4: Statistics
    print("\n4. Rate limiter statistics:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✅ Rate limiter tests completed!")
