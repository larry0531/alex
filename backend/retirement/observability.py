"""
Observability module for Retirement agent.
Delegates to the shared observability module.
"""

from shared.observability import observe as _observe
from contextlib import contextmanager


@contextmanager
def observe():
    with _observe("alex_retirement_agent") as client:
        yield client
