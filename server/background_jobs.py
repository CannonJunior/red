"""
server/background_jobs.py — Lightweight in-process background job queue.

Runs jobs in daemon threads so the HTTP request handler returns immediately.
Designed for the 5-user local deployment: no Redis, no Celery, just threads.

Usage:
    from server.background_jobs import job_store

    job_id = job_store.submit(my_fn, arg1, arg2, kwarg=value)
    # → returns immediately

    status = job_store.get(job_id)
    # → {'status': 'pending'|'running'|'done'|'error',
    #    'result': ..., 'error': None, 'progress': '...'}
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Job lifecycle states
_PENDING = "pending"
_RUNNING = "running"
_DONE    = "done"
_ERROR   = "error"


class _JobStore:
    """
    Thread-safe in-memory store for background job state.

    Attributes:
        _lock: Protects _jobs dict from concurrent modification.
        _jobs: Maps job_id str → job state dict.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> str:
        """
        Submit a callable to run in a background daemon thread.

        Args:
            fn: The function to call.
            *args: Positional arguments forwarded to fn.
            **kwargs: Keyword arguments forwarded to fn.

        Returns:
            str: Unique job ID for polling.
        """
        return self._enqueue(fn, args, kwargs)

    def submit_with_id(self, fn: Callable, *args: Any, **kwargs: Any) -> str:
        """
        Like submit(), but passes the assigned job_id as the first positional
        argument to fn so the function can report progress back via
        job_store.update_progress(job_id, message).

        Args:
            fn: Callable whose first parameter is the job_id string.
            *args: Additional positional arguments (after job_id).
            **kwargs: Keyword arguments forwarded to fn.

        Returns:
            str: Unique job ID for polling.
        """
        job_id = str(uuid.uuid4())
        self._register(job_id)
        t = threading.Thread(
            target=self._run,
            args=(job_id, fn, (job_id,) + args, kwargs),
            daemon=True,
            name=f"bg-job-{job_id[:8]}",
        )
        t.start()
        logger.debug("Submitted (with_id) job %s → %s", job_id[:8], fn.__name__)
        return job_id

    def _register(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = {
                "status": _PENDING,
                "result": None,
                "error": None,
                "progress": "Queued",
            }

    def _enqueue(self, fn: Callable, args: tuple, kwargs: dict) -> str:
        job_id = str(uuid.uuid4())
        self._register(job_id)
        t = threading.Thread(
            target=self._run,
            args=(job_id, fn, args, kwargs),
            daemon=True,
            name=f"bg-job-{job_id[:8]}",
        )
        t.start()
        logger.debug("Submitted background job %s → %s", job_id[:8], fn.__name__)
        return job_id

    def _run(self, job_id: str, fn: Callable, args: tuple, kwargs: dict) -> None:
        """Execute fn in the current (background) thread and record outcome."""
        self._update(job_id, status=_RUNNING, progress="Running")
        try:
            result = fn(*args, **kwargs)
            self._update(job_id, status=_DONE, result=result, progress="Complete")
            logger.debug("Job %s finished successfully", job_id[:8])
        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id[:8], exc)
            self._update(job_id, status=_ERROR, error=str(exc), progress="Failed")

    def _update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the current state of a job, or None if not found.

        Args:
            job_id: Job UUID returned by submit().

        Returns:
            dict with keys: status, result, error, progress.
        """
        with self._lock:
            entry = self._jobs.get(job_id)
            return dict(entry) if entry else None

    def update_progress(self, job_id: str, message: str) -> None:
        """
        Allow long-running jobs to report intermediate progress.

        Args:
            job_id: Job UUID.
            message: Human-readable progress description.
        """
        self._update(job_id, progress=message)


# Module-level singleton — import and use this everywhere
job_store = _JobStore()
