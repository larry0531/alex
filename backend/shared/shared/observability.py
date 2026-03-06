"""
Shared observability module for LangFuse integration.
Provides a parameterized context manager for setting up and flushing traces.

Usage:
    from shared import observe

    with observe("alex_planner_agent"):
        result = await agent.run(...)

    # Or with the LangFuse client yielded:
    with observe("alex_reporter_agent") as langfuse_client:
        result = await agent.run(...)
        if langfuse_client:
            langfuse_client.create_event(...)
"""

import os
import logging
from contextlib import contextmanager

logger = logging.getLogger()


@contextmanager
def observe(service_name: str = "alex_agent", flush_wait: int = 10):
    """
    Context manager for observability with LangFuse.

    Sets up LangFuse observability if environment variables are configured,
    and ensures traces are flushed on exit.

    Args:
        service_name: Logfire service name for this agent (e.g. "alex_planner_agent")
        flush_wait: Seconds to wait for flush to complete before Lambda terminates
    """
    logger.info("Observability: Checking configuration...")

    has_langfuse = bool(os.getenv("LANGFUSE_SECRET_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    logger.info(f"Observability: LANGFUSE_SECRET_KEY exists: {has_langfuse}")
    logger.info(f"Observability: OPENAI_API_KEY exists: {has_openai}")

    if not has_langfuse:
        logger.info("Observability: LangFuse not configured, skipping setup")
        yield None
        return

    if not has_openai:
        logger.warning("Observability: OPENAI_API_KEY not set, traces may not export")

    langfuse_client = None

    try:
        logger.info("Observability: Setting up LangFuse...")

        import logfire
        from langfuse import get_client

        logfire.configure(
            service_name=service_name,
            send_to_logfire=False,
        )
        logger.info("Observability: Logfire configured")

        logfire.instrument_openai_agents()
        logger.info("Observability: OpenAI Agents SDK instrumented")

        langfuse_client = get_client()
        logger.info("Observability: LangFuse client initialized")

        try:
            auth_result = langfuse_client.auth_check()
            logger.info(f"Observability: LangFuse auth check passed (result: {auth_result})")
        except Exception as auth_error:
            logger.warning(f"Observability: Auth check failed but continuing: {auth_error}")

        logger.info("Observability: Setup complete - traces will be sent to LangFuse")

    except ImportError as e:
        logger.error(f"Observability: Missing required package: {e}")
        langfuse_client = None
    except Exception as e:
        logger.error(f"Observability: Setup failed: {e}")
        langfuse_client = None

    try:
        yield langfuse_client
    finally:
        if langfuse_client:
            try:
                logger.info("Observability: Flushing traces to LangFuse...")
                langfuse_client.flush()
                langfuse_client.shutdown()

                import time

                logger.info(f"Observability: Waiting {flush_wait} seconds for flush to complete...")
                time.sleep(flush_wait)

                logger.info("Observability: Traces flushed successfully")
            except Exception as e:
                logger.error(f"Observability: Failed to flush traces: {e}")
        else:
            logger.debug("Observability: No client to flush")
