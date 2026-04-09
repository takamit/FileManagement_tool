from __future__ import annotations
import threading
import time

class OperationController:
    def __init__(self) -> None:
        self._pause = threading.Event()
        self._stop = threading.Event()
        self._pause.set()

    def reset(self) -> None:
        self._stop.clear()
        self._pause.set()

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()

    def is_paused(self) -> bool:
        return not self._pause.is_set()

    def is_stopped(self) -> bool:
        return self._stop.is_set()

    def check(self) -> None:
        while not self._pause.is_set():
            if self._stop.is_set():
                raise InterruptedError("処理は停止されました。")
            time.sleep(0.05)
        if self._stop.is_set():
            raise InterruptedError("処理は停止されました。")
