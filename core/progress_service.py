from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(slots=True)
class ProgressInfo:
    phase: str
    current: int
    total: int
    message: str
    percent: float
    eta_seconds: Optional[float]


class ProgressService:
    def __init__(self) -> None:
        self._callback: Optional[Callable[[ProgressInfo], None]] = None
        self._phase_started_at: Optional[float] = None
        self._last_phase: Optional[str] = None

    def bind(self, callback: Callable[[ProgressInfo], None]) -> None:
        self._callback = callback

    def reset(self) -> None:
        self._phase_started_at = None
        self._last_phase = None

    def update(self, phase: str, current: int, total: int, message: str) -> None:
        now = time.time()
        if self._last_phase != phase or self._phase_started_at is None:
            self._last_phase = phase
            self._phase_started_at = now

        safe_total = max(total, 1)
        percent = min(max((current / safe_total) * 100.0, 0.0), 100.0)
        eta_seconds: Optional[float] = None
        if current > 0 and current < safe_total and self._phase_started_at is not None:
            elapsed = max(now - self._phase_started_at, 0.001)
            rate = current / elapsed
            if rate > 0:
                eta_seconds = (safe_total - current) / rate

        if self._callback is None:
            return
        self._callback(
            ProgressInfo(
                phase=phase,
                current=current,
                total=total,
                message=message,
                percent=percent,
                eta_seconds=eta_seconds,
            )
        )
