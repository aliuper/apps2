from __future__ import annotations

import os

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty
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

        kv_path = os.path.join(os.path.dirname(__file__), "alibaba", "ui", "alibaba.kv")
        Builder.load_file(kv_path)
        root = Root()

        Clock.schedule_once(lambda *_: self._wire(root), 0)
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
    AliBabaApp().run()
