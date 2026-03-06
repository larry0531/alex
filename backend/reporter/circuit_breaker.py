"""
Circuit breaker pattern for external API calls.

Three states:
- CLOSED: Normal operation, calls go through. Failures are counted.
- OPEN: Calls are blocked immediately. After a cooldown period, transitions to HALF_OPEN.
- HALF_OPEN: One trial call is allowed. If it succeeds, transitions to CLOSED. If it fails, back to OPEN.
"""

import time
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger()


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Thread-safe circuit breaker for external API calls.

    Args:
        name: Identifier for this circuit (used in logs)
        failure_threshold: Number of consecutive failures before opening the circuit
        recovery_timeout: Seconds to wait before transitioning from OPEN to HALF_OPEN
        success_threshold: Number of consecutive successes in HALF_OPEN to close the circuit
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        success_threshold: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(f"CircuitBreaker[{self.name}]: Recovery timeout elapsed, transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return True
        # OPEN
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                logger.info(f"CircuitBreaker[{self.name}]: Trial succeeded, closing circuit")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"CircuitBreaker[{self.name}]: Trial failed, reopening circuit")
            self._state = CircuitState.OPEN
            return

        if self._failure_count >= self.failure_threshold:
            logger.warning(
                f"CircuitBreaker[{self.name}]: {self._failure_count} consecutive failures, opening circuit "
                f"(will retry after {self.recovery_timeout}s)"
            )
            self._state = CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when a call is blocked because the circuit is open."""

    def __init__(self, name: str):
        super().__init__(f"Circuit breaker '{name}' is OPEN - call blocked")
        self.circuit_name = name
