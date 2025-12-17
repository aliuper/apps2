from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.utils import platform


@dataclass(frozen=True)
class SaveResult:
    file_path: str
    version: int


class StorageService:
    def __init__(self, app_name: str):
        self.app_name = app_name

    def _state_path(self) -> Path:
        app = App.get_running_app()
        base = Path(getattr(app, "user_data_dir", Path.home()))
        base.mkdir(parents=True, exist_ok=True)
        return base / "alibaba_state.json"

    def _load_state(self) -> dict:
        p = self._state_path()
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _save_state(self, state: dict) -> None:
        p = self._state_path()
        p.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    def next_version_for_day(self, day_key: str) -> int:
        state = self._load_state()
        versions = state.get("versions", {})
        cur = int(versions.get(day_key, 0))
        cur += 1
        versions[day_key] = cur
        state["versions"] = versions
        self._save_state(state)
        return cur

    def downloads_dir(self) -> Path:
        if platform == "android":
            return Path(self.private_dir())

        android_guess = Path("/storage/emulated/0/Download")
        if android_guess.exists():
            return android_guess

        home = Path.home()
        for name in ["Downloads", "Download"]:
            p = home / name
            if p.exists():
                return p
        return home

    def ensure_output_dir(self) -> Path:
        out_dir = self.downloads_dir() / "iptv dosyalari"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def private_dir(self) -> str:
        app = App.get_running_app()
        return str(getattr(app, "user_data_dir", Path.home()))

    def build_filename(
        self,
        label: str,
        created: datetime,
        ext: str,
        expiry: datetime | None,
    ) -> tuple[str, int]:
        created_key = created.strftime("%d%m%Y")
        version = self.next_version_for_day(created_key)

        prefix = (expiry or created).strftime("%d%m%Y")
        created_s = created.strftime("%d%m%Y")
        safe_label = "".join(ch for ch in (label or "alibaba") if ch.isalnum() or ch in ["_", "-"]).strip("_")
        safe_label = safe_label or "alibaba"
        ext = (ext or "m3u").lstrip(".")

        filename = f"{prefix}_{safe_label}_v{version}_{created_s}.{ext}"
        return filename, version

    def save_text_file(
        self,
        content: str,
        label: str,
        ext: str,
        expiry: datetime | None,
    ) -> SaveResult:
        created = datetime.now()
        filename, version = self.build_filename(label=label, created=created, ext=ext, expiry=expiry)

        if platform == "android":
            private_path = Path(self.private_dir()) / filename
            private_path.write_text(content, encoding="utf-8")
            shared_uri = self._copy_to_android_downloads(private_file=str(private_path), filename=filename)
            return SaveResult(file_path=shared_uri or str(private_path), version=version)

        out_dir = self.ensure_output_dir()
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        return SaveResult(file_path=str(path), version=version)

    def _copy_to_android_downloads(self, private_file: str, filename: str) -> str | None:
        try:
            from androidstorage4kivy import SharedStorage  # type: ignore
            from jnius import autoclass  # type: ignore

            Environment = autoclass("android.os.Environment")
            ss = SharedStorage()
            collection = getattr(Environment, "DIRECTORY_DOWNLOADS", None)
            shared = ss.copy_to_shared(
                private_file,
                collection=collection,
                filepath=os.path.join("iptv dosyalari", filename),
            )
            if shared is None:
                return None

            try:
                return shared.toString()
            except Exception:  # noqa: BLE001
                return str(shared)
        except Exception:  # noqa: BLE001
            return None
