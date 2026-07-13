"""
Circuit Breaker pattern for external API calls.

States:
  CLOSED   → normal operation, requests pass through
  OPEN     → after 5 failures, requests return fallback immediately
  HALF_OPEN → after 60s recovery timeout, one test request allowed

Why: without circuit breaker, 43 API requests × 30s timeout = 21 min DAG hang
With circuit breaker: after 5 failures, remaining 38 requests return None instantly
"""
import time
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitBreaker:
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.failure_count     = 0
        self.last_failure_time = None
        self.state             = self.CLOSED

    def call(self, func: Callable, *args, fallback: Any = None, **kwargs) -> Any:
        """
        Wraps a function call with circuit breaker logic.

        Args:
            func: function to call
            fallback: value to return when circuit is OPEN
        """
        if self.state == self.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit breaker: OPEN → HALF_OPEN, testing recovery")
                self.state = self.HALF_OPEN
            else:
                logger.debug(f"Circuit breaker OPEN — returning fallback for {func.__name__}")
                return fallback

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        if self.state == self.HALF_OPEN:
            logger.info("Circuit breaker: HALF_OPEN → CLOSED (recovery successful)")
        self.failure_count = 0
        self.state = self.CLOSED

    def _on_failure(self, error: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}: {error}")

        if self.failure_count >= self.failure_threshold:
            if self.state != self.OPEN:
                logger.error(
                    f"Circuit breaker: CLOSED → OPEN after {self.failure_count} failures. "
                    f"Recovery in {self.recovery_timeout}s"
                )
            self.state = self.OPEN

    @property
    def is_open(self) -> bool:
        return self.state == self.OPEN