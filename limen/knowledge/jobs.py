"""In-process background runner for knowledge document processing."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeJobRunner:
    """Single-process thread pool — no Redis/Celery."""

    def __init__(self, *, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="limen-knowledge",
        )
        self._closed = False

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        if self._closed:
            raise RuntimeError("KnowledgeJobRunner is shut down")

        def _wrapped() -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception:
                logger.exception("Knowledge background job failed")
                raise

        return self._executor.submit(_wrapped)

    def shutdown(self, *, wait: bool = True) -> None:
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)


_runner: KnowledgeJobRunner | None = None


def get_knowledge_job_runner() -> KnowledgeJobRunner:
    global _runner
    if _runner is None or _runner._closed:  # noqa: SLF001
        _runner = KnowledgeJobRunner()
    return _runner


def shutdown_knowledge_job_runner(*, wait: bool = True) -> None:
    global _runner
    if _runner is not None:
        _runner.shutdown(wait=wait)
        _runner = None


def reset_knowledge_job_runner_for_tests(*, wait: bool = True) -> None:
    """Tests must drain in-flight jobs before swapping the SQLite singleton."""
    shutdown_knowledge_job_runner(wait=wait)
