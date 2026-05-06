"""Utils."""

import threading
from collections.abc import Callable


class RepeatingTimer:
    """Periodic callback on a daemon thread."""

    def __init__(self, interval: float, callback: Callable[[], None]):
        self._interval = interval
        self._callback = callback
        self._timer: threading.Timer | None = None
        self._stopped = threading.Event()

    def start(self) -> None:
        self._stopped.clear()
        self._schedule()

    def stop(self) -> None:
        self._stopped.set()
        if self._timer:
            self._timer.cancel()

    def _schedule(self) -> None:
        if self._stopped.is_set():
            return
        self._timer = threading.Timer(self._interval, self._run)
        self._timer.daemon = True
        self._timer.start()

    def _run(self) -> None:
        if self._stopped.is_set():
            return
        try:
            self._callback()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        self._schedule()
