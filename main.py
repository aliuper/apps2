from __future__ import annotations

import os
import sys
import signal
import traceback
from datetime import datetime
from pathlib import Path
import faulthandler


def _is_android() -> bool:
    return bool(os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT"))


def _crash_private_dir() -> Path:
    if _is_android():
        p = os.environ.get("ANDROID_PRIVATE")
        if p:
            return Path(p)
    return Path.home() / ".alibaba"


def _write_crash_log(text: str) -> str | None:
    try:
        base = _crash_private_dir() / "crash_logs"
        base.mkdir(parents=True, exist_ok=True)
        name = f"alibaba_crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        p = base / name
        p.write_text(text, encoding="utf-8")

        if _is_android():
            try:
                from androidstorage4kivy import SharedStorage  # type: ignore
                from jnius import autoclass  # type: ignore

                Environment = autoclass("android.os.Environment")
                ss = SharedStorage()
                collection = getattr(Environment, "DIRECTORY_DOWNLOADS", None)
                ss.copy_to_shared(
                    str(p),
                    collection=collection,
                    filepath=os.path.join("crash_logs", name),
                )
            except Exception:  # noqa: BLE001
                pass

        return str(p)
    except Exception:  # noqa: BLE001
        return None


def _touch_startup_marker() -> None:
    try:
        base = _crash_private_dir() / "crash_logs"
        base.mkdir(parents=True, exist_ok=True)
        p = base / "alibaba_startup_marker.txt"
        p.write_text(datetime.now().isoformat(), encoding="utf-8")

        if _is_android():
            try:
                from androidstorage4kivy import SharedStorage  # type: ignore
                from jnius import autoclass  # type: ignore

                Environment = autoclass("android.os.Environment")
                ss = SharedStorage()
                collection = getattr(Environment, "DIRECTORY_DOWNLOADS", None)
                ss.copy_to_shared(
                    str(p),
                    collection=collection,
                    filepath=os.path.join("crash_logs", "alibaba_startup_marker.txt"),
                )
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass


def _setup_faulthandler() -> None:
    try:
        base = _crash_private_dir() / "crash_logs"
        base.mkdir(parents=True, exist_ok=True)
        p = base / "alibaba_faulthandler.txt"
        f = open(p, "a", encoding="utf-8")
        f.write(f"\n=== START {datetime.now().isoformat()} ===\n")
        f.flush()
        faulthandler.enable(file=f, all_threads=True)
        try:
            faulthandler.register(signal.SIGABRT, file=f, all_threads=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            faulthandler.register(signal.SIGILL, file=f, all_threads=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            faulthandler.register(signal.SIGFPE, file=f, all_threads=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            faulthandler.register(signal.SIGSEGV, file=f, all_threads=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            faulthandler.register(signal.SIGBUS, file=f, all_threads=True)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    _write_crash_log(text)
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _excepthook
_setup_faulthandler()
_touch_startup_marker()

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.screenmanager import ScreenManager

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

from alibaba.app_state import AppState
from alibaba.services.storage import StorageService
from alibaba.services.iptv import IPTVService
from alibaba.ui import screens as _screens  # noqa: F401


class Root(ScreenManager):
    status_text = StringProperty("")


class AliBabaApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = AppState()
        self.iptv = IPTVService()
        self.storage = StorageService(app_name="AliBaba")
        self._dialog: MDDialog | None = None

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Dark"

        try:
            kv_path = os.path.join(os.path.dirname(__file__), "alibaba", "ui", "alibaba.kv")
            Builder.load_file(kv_path)
            root = Root()

            Clock.schedule_once(lambda *_: self._wire(root), 0)
            return root
        except Exception:  # noqa: BLE001
            err = traceback.format_exc()
            _write_crash_log(err)
            print(err)
            root = Root()
            scr = Screen(name="error")
            scr.add_widget(Label(text=err))
            root.add_widget(scr)
            root.current = "error"
            return root

    def _wire(self, root: Root):
        self.root = root

    def show_error(self, title: str, text: str):
        if self._dialog:
            self._dialog.dismiss()
            self._dialog = None

        self._dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="Tamam", on_release=lambda *_: self._dialog.dismiss())],
        )
        self._dialog.open()


if __name__ == "__main__":
    try:
        AliBabaApp().run()
    except Exception:  # noqa: BLE001
        _write_crash_log(traceback.format_exc())
        raise
