"""
Observability module for Planner agent.
Delegates to the shared observability module.
"""

from shared.observability import observe as _observe
from contextlib import contextmanager


@contextmanager
def observe():
    with _observe("alex_planner_agent", flush_wait=15) as client:
        yield client
