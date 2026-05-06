"""Controller input via pygame joystick."""

import threading
import time
from collections.abc import Callable

from log_setup import get_logger

log = get_logger(__name__)

try:
    import pygame  # pylint: disable=import-error

    pygame.joystick.init()
    HAS_JOYSTICK = True
except Exception:  # pylint: disable=broad-exception-caught
    HAS_JOYSTICK = False

_BUTTON_MAP = {
    "a": 0, "b": 1, "x": 2, "y": 3,
    "lb": 4, "rb": 5,
    "back": 6, "start": 7,
    "share": 6, "options": 7,
    "ls": 8, "rs": 9,
}


class Controller:
    """Polls gamepad, fires callbacks on press."""

    def __init__(
        self,
        callbacks: dict[str, Callable[[], None]],
        actions: dict[str, str] | None = None,
    ):
        self._callbacks = callbacks
        self._actions: dict[str, str] = actions or {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._joystick = None
        self._prev_buttons: list[int] = []
        self._prev_hat: tuple[float, float] = (0.0, 0.0)

    def start(self) -> None:
        if not HAS_JOYSTICK:
            log.warning("pygame joystick not available")
            return
        if not self._actions:
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="controller"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            if pygame.joystick.get_count() == 0:
                time.sleep(2)
                continue
            try:
                self._joystick = pygame.joystick.Joystick(0)
                self._joystick.init()
                self._prev_buttons = [0] * self._joystick.get_numbuttons()
                self._prev_hat = self._joystick.get_hat(0)
                self._poll()
            except pygame.error:
                self._joystick = None
                time.sleep(2)

    def _poll(self) -> None:
        while not self._stop.is_set():
            if pygame.joystick.get_count() == 0:
                self._joystick = None
                return

            joystick = self._joystick
            if joystick is None:
                return

            pygame.event.pump()

            for action, name in self._actions.items():
                if name in _BUTTON_MAP:
                    index = _BUTTON_MAP[name]
                    if index >= joystick.get_numbuttons():
                        continue
                    state = joystick.get_button(index)
                    if state and not self._prev_buttons[index]:
                        callback = self._callbacks.get(action)
                        if callback:
                            callback()
                    self._prev_buttons[index] = state

            hat = joystick.get_hat(0)
            if hat != self._prev_hat:
                self._fire_hat("dpad_right", hat[0] == 1, self._prev_hat[0] == 1)
                self._fire_hat("dpad_left", hat[0] == -1, self._prev_hat[0] == -1)
                self._fire_hat("dpad_up", hat[1] == 1, self._prev_hat[1] == 1)
                self._fire_hat("dpad_down", hat[1] == -1, self._prev_hat[1] == -1)
                self._prev_hat = hat

            time.sleep(0.05)

    def _fire_hat(self, direction: str, pressed: bool, was_pressed: bool) -> None:
        if not pressed or was_pressed:
            return
        for action, name in self._actions.items():
            if name == direction:
                callback = self._callbacks.get(action)
                if callback:
                    callback()
                return
