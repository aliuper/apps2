from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from kivymd.uix.list import IRightBodyTouch, OneLineAvatarIconListItem, MDList
from kivymd.uix.selectioncontrol import MDCheckbox

from alibaba.models import ChannelEntry
from alibaba.services.url_finder import extract_urls
from alibaba.utils.threading import run_in_thread


class HomeScreen(Screen):
    pass


class ManualScreen(Screen):
    progress = NumericProperty(0.0)
    eta_text = StringProperty("")

    def on_analyze(self) -> None:
        app = App.get_running_app()
        url = (self.ids.url_input.text or "").strip()
        if not url.lower().startswith("http"):
            app.show_error("Hata", "Lütfen geçerli bir IPTV linki gir.")
            return

        self.progress = 0.0
        self.eta_text = ""
        started = time.time()

        def _progress(p: float, msg: str) -> None:
            def _ui(*_):
                self.progress = float(max(0.0, min(1.0, p)))
                app.root.status_text = msg
                elapsed = time.time() - started
                if self.progress > 0.02:
                    remaining = max(0.0, (elapsed / self.progress) - elapsed)
                    self.eta_text = f"~{int(remaining)} sn"

            Clock.schedule_once(_ui, 0)

        def _work() -> None:
            analysis, entries = app.iptv.analyze_playlist(url, on_progress=_progress)

            def _done(*_):
                app.state.last_analysis = analysis
                app.state.last_entries = entries
                app.state.selection.clear()
                app.root.current = "group_select"

            Clock.schedule_once(_done, 0)

        run_in_thread(_work, on_error=lambda e: app.show_error("Hata", str(e)))


class AutoScreen(Screen):
    progress = NumericProperty(0.0)
    eta_text = StringProperty("")

    def on_extract(self) -> None:
        text = self.ids.auto_text.text or ""
        urls = extract_urls(text)
        self.ids.found_label.text = f"Bulunan link: {len(urls)}"
        self.ids.urls_preview.text = "\n".join(urls[:8])
        app = App.get_running_app()
        app.state.auto_urls = urls

    def on_start(self) -> None:
        app = App.get_running_app()
        urls = list(app.state.auto_urls)
        if not urls:
            self.on_extract()
            urls = list(app.state.auto_urls)

        if not urls:
            app.show_error("Hata", "Metinden IPTV linki bulunamadı.")
            return

        self.progress = 0.0
        self.eta_text = ""
        started = time.time()

        working: list[tuple[str, list[ChannelEntry], datetime | None]] = []

        def _set_progress(p: float, msg: str) -> None:
            def _ui(*_):
                self.progress = float(max(0.0, min(1.0, p)))
                app.root.status_text = msg
                elapsed = time.time() - started
                if self.progress > 0.02:
                    remaining = max(0.0, (elapsed / self.progress) - elapsed)
                    self.eta_text = f"~{int(remaining)} sn"

            Clock.schedule_once(_ui, 0)

        def _work() -> None:
            for i, url in enumerate(urls, start=1):
                base = (i - 1) / len(urls)

                def _inner_progress(p: float, msg: str) -> None:
                    _set_progress(base + (p * (1.0 / len(urls))), f"{i}/{len(urls)}: {msg}")

                analysis, entries = app.iptv.analyze_playlist(url, on_progress=_inner_progress)
                if analysis.fetched_ok and analysis.parsed_ok and entries:
                    working.append((url, entries, analysis.expiry))

            def _done(*_):
                app.state.auto_working = working
                app.root.current = "auto_country"

            Clock.schedule_once(_done, 0)

        run_in_thread(_work, on_error=lambda e: app.show_error("Hata", str(e)))


class CountrySelectScreen(Screen):
    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._render()

    def _render(self) -> None:
        app = App.get_running_app()
        working = list(app.state.auto_working)
        codes = set()
        for _, entries, _ in working:
            for e in entries:
                if not e.group:
                    continue
                code = _guess_country_code(e.group)
                if code:
                    codes.add(code)

        codes_sorted = sorted(codes)
        container: MDList = self.ids.country_list
        container.clear_widgets()

        for c in codes_sorted:
            item = CodeItem(text=c)
            item.checkbox.active = c in app.state.auto_country_codes
            item.checkbox.bind(active=lambda cb, val, code=c: _on_code_toggle(code, val))
            container.add_widget(item)

        self.ids.summary_label.text = f"Çalışan link: {len(working)} | Ülke kodu: {len(codes_sorted)}"

        def _on_code_toggle(code: str, val: bool) -> None:
            if val:
                app.state.auto_country_codes.add(code)
            else:
                app.state.auto_country_codes.discard(code)

    def on_next(self) -> None:
        app = App.get_running_app()
        if not app.state.auto_country_codes:
            app.show_error("Hata", "En az 1 ülke kodu seç.")
            return
        app.root.current = "output_auto"


class GroupSelectScreen(Screen):
    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._render(filter_text="")

    def on_filter(self) -> None:
        self._render(filter_text=(self.ids.group_filter.text or "").strip())

    def _render(self, filter_text: str) -> None:
        app = App.get_running_app()
        analysis = app.state.last_analysis
        if not analysis:
            return

        groups = list(analysis.groups)
        if filter_text:
            f = filter_text.lower()
            groups = [g for g in groups if f in g.lower()]

        container: MDList = self.ids.group_list
        container.clear_widgets()

        selected = app.state.selection.selected_groups

        for g in groups:
            item = GroupItem(text=g)
            item.checkbox.active = g in selected
            item.checkbox.bind(active=lambda cb, val, group=g: _on_toggle(group, val))
            container.add_widget(item)

        self.ids.summary_label.text = f"Grup: {len(analysis.groups)} | Seçili: {len(selected)}"

        def _on_toggle(group: str, val: bool) -> None:
            if val:
                selected.add(group)
            else:
                selected.discard(group)
            self.ids.summary_label.text = f"Grup: {len(analysis.groups)} | Seçili: {len(selected)}"

    def select_all(self) -> None:
        app = App.get_running_app()
        analysis = app.state.last_analysis
        if not analysis:
            return
        app.state.selection.set_all(analysis.groups)
        self._render(filter_text=(self.ids.group_filter.text or "").strip())

    def clear_all(self) -> None:
        app = App.get_running_app()
        app.state.selection.clear()
        self._render(filter_text=(self.ids.group_filter.text or "").strip())

    def on_next(self) -> None:
        app = App.get_running_app()
        if not app.state.selection.selected_groups:
            app.show_error("Hata", "En az 1 grup seç.")
            return
        app.root.current = "output_manual"


class OutputManualScreen(Screen):
    def save(self) -> None:
        app = App.get_running_app()
        analysis = app.state.last_analysis
        if not analysis:
            app.show_error("Hata", "Analiz bulunamadı.")
            return

        ext = _ext_from_ui(self)
        label = (self.ids.label_input.text or "alibaba").strip() or "alibaba"

        selected = set(app.state.selection.selected_groups)
        filtered = app.iptv.filter_entries_by_groups(app.state.last_entries, selected)
        if not filtered:
            app.show_error("Hata", "Seçili gruplarda kanal bulunamadı.")
            return

        content = app.iptv.to_m3u_plus(filtered)
        res = app.storage.save_text_file(content=content, label=label, ext=ext, expiry=analysis.expiry)
        app.root.status_text = f"Kaydedildi: {res.file_path}"


class OutputAutoScreen(Screen):
    def save(self) -> None:
        app = App.get_running_app()
        working = list(app.state.auto_working)
        if not working:
            app.show_error("Hata", "Çalışan link bulunamadı.")
            return

        ext = _ext_from_ui(self)
        label = (self.ids.label_input.text or "alibaba").strip() or "alibaba"
        combine = bool(self.ids.combine_switch.active)
        codes = set(app.state.auto_country_codes)

        outputs: list[tuple[str, datetime | None]] = []

        if combine:
            merged: list[ChannelEntry] = []
            expiries: list[datetime] = []
            for _, entries, expiry in working:
                merged.extend(_filter_by_country_codes(entries, codes))
                if expiry:
                    expiries.append(expiry)
            expiry_min = min(expiries) if expiries else None
            outputs.append((app.iptv.to_m3u_plus(merged), expiry_min))

            res = app.storage.save_text_file(content=outputs[0][0], label=f"{label}_auto", ext=ext, expiry=outputs[0][1])
            app.root.status_text = f"Kaydedildi: {res.file_path}"
            return

        for idx, (_, entries, expiry) in enumerate(working, start=1):
            filtered = _filter_by_country_codes(entries, codes)
            if not filtered:
                continue
            content = app.iptv.to_m3u_plus(filtered)
            res = app.storage.save_text_file(content=content, label=f"{label}_{idx}", ext=ext, expiry=expiry)
            app.root.status_text = f"Kaydedildi: {res.file_path}"


class _RightCheckbox(IRightBodyTouch, MDCheckbox):
    pass


class GroupItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkbox = _RightCheckbox(size_hint=(None, None), size=(dp(48), dp(48)))
        self.add_widget(self.checkbox)


class CodeItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkbox = _RightCheckbox(size_hint=(None, None), size=(dp(48), dp(48)))
        self.add_widget(self.checkbox)


def _guess_country_code(group_title: str) -> str | None:
    if not group_title:
        return None
    g = group_title.strip()
    if not g:
        return None

    for sep in ["|", "-", "_", "/", " "]:
        if sep in g:
            token = g.split(sep, 1)[0].strip()
            break
    else:
        token = g

    token = token.upper()
    if 2 <= len(token) <= 3 and token.isalpha():
        return token
    return None


def _filter_by_country_codes(entries: list[ChannelEntry], codes: set[str]) -> list[ChannelEntry]:
    if not codes:
        return []

    codes_u = {c.upper() for c in codes}
    out: list[ChannelEntry] = []
    for e in entries:
        if not e.group:
            continue
        code = _guess_country_code(e.group)
        if code and code.upper() in codes_u:
            out.append(e)
    return out


def _ext_from_ui(screen: Screen) -> str:
    if getattr(screen.ids, "ext_m3u8", None) and screen.ids.ext_m3u8.active:
        return "m3u8"
    return "m3u"
