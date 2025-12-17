from __future__ import annotations

import threading
from typing import Callable

from kivy.clock import Clock


def run_in_thread(fn: Callable[[], None], on_error: Callable[[Exception], None] | None = None) -> None:
    def _runner():
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            if on_error:
                Clock.schedule_once(lambda *_: on_error(e), 0)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
