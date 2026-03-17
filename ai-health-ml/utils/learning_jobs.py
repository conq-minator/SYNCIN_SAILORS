from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional


@dataclass
class LearningJob:
    id: str
    created_at: float = field(default_factory=lambda: time.time())
    status: str = "queued"  # queued|running|done|error
    message: str = ""
    progress: float = 0.0  # 0..1
    result: dict[str, Any] = field(default_factory=dict)


_LOCK = Lock()
_JOBS: dict[str, LearningJob] = {}
_MAX_JOBS = 200


def create_job() -> LearningJob:
    job = LearningJob(id=str(uuid.uuid4()))
    with _LOCK:
        _JOBS[job.id] = job
        _trim()
    return job


def get_job(job_id: str) -> Optional[LearningJob]:
    with _LOCK:
        return _JOBS.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> None:
    with _LOCK:
        j = _JOBS.get(job_id)
        if not j:
            return
        for k, v in kwargs.items():
            if hasattr(j, k):
                setattr(j, k, v)


def finish_job(job_id: str, *, status: str, message: str = "", result: Optional[dict[str, Any]] = None) -> None:
    update_job(job_id, status=status, message=message, progress=1.0, result=result or {})


def _trim() -> None:
    # drop oldest jobs
    if len(_JOBS) <= _MAX_JOBS:
        return
    items = sorted(_JOBS.values(), key=lambda x: x.created_at)
    for j in items[: max(0, len(items) - _MAX_JOBS)]:
        _JOBS.pop(j.id, None)

