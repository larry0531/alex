"""
Observability module for Tagger agent.
Delegates to the shared observability module.
"""

from shared.observability import observe as _observe
from contextlib import contextmanager


@contextmanager
def observe():
    with _observe("alex_tagger_agent") as client:
        yield client
