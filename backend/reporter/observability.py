"""
Observability module for Reporter agent.
Delegates to the shared observability module.
"""

from shared.observability import observe as _observe
from contextlib import contextmanager


@contextmanager
def observe():
    with _observe("alex_reporter_agent") as client:
        yield client
