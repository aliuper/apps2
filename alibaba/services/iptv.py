from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from urllib.parse import parse_qs, urlparse

import requests
from dateutil import parser as dtparser

from alibaba.models import ChannelEntry, PlaylistAnalysis
from alibaba.services.m3u import parse_m3u_plus, unique_groups, build_m3u_plus


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    status_code: int | None


class IPTVService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AliBaba/1.0"})

    def fetch_text(self, url: str, timeout_s: int = 15) -> str:
        r = self.session.get(url, timeout=timeout_s, allow_redirects=True)
        r.raise_for_status()
        r.encoding = r.encoding or "utf-8"
        return r.text

    def guess_expiry(self, url: str) -> datetime | None:
        try:
            u = urlparse(url)
            qs = parse_qs(u.query)
        except Exception:  # noqa: BLE001
            return None

        keys = ["exp", "expires", "expiry", "end", "validto", "valid_to", "until"]
        for k in keys:
            if k not in qs:
                continue
            raw = qs.get(k, [None])[0]
            if not raw:
                continue
            dt = self._parse_expiry_value(raw)
            if dt:
                return dt
        return None

    def _parse_expiry_value(self, raw: str) -> datetime | None:
        raw = raw.strip()
        if not raw:
            return None

        if raw.isdigit():
            n = int(raw)
            if n > 10_000_000_000:
                n = int(n / 1000)
            try:
                return datetime.fromtimestamp(n)
            except Exception:  # noqa: BLE001
                return None

        try:
            dt = dtparser.parse(raw, fuzzy=True)
            return dt
        except Exception:  # noqa: BLE001
            return None

    def probe_stream(self, url: str, timeout_s: int = 8) -> ProbeResult:
        try:
            h = self.session.head(url, timeout=timeout_s, allow_redirects=True)
            if h.status_code in (200, 206, 302, 301):
                return ProbeResult(ok=True, status_code=h.status_code)
        except Exception:  # noqa: BLE001
            pass

        try:
            r = self.session.get(url, timeout=timeout_s, stream=True, headers={"Range": "bytes=0-2047"}, allow_redirects=True)
            ok = r.status_code in (200, 206)
            return ProbeResult(ok=ok, status_code=r.status_code)
        except Exception:  # noqa: BLE001
            return ProbeResult(ok=False, status_code=None)

    def analyze_playlist(
        self,
        url: str,
        on_progress: Callable[[float, str], None] | None = None,
        test_channels: int = 3,
    ) -> tuple[PlaylistAnalysis, list[ChannelEntry]]:
        start = time.time()
        if on_progress:
            on_progress(0.05, "Liste indiriliyor")

        text = self.fetch_text(url)
        expiry = self.guess_expiry(url)

        if on_progress:
            on_progress(0.35, "Liste ayrıştırılıyor")

        entries = parse_m3u_plus(text)
        groups = unique_groups(entries)
        parsed_ok = len(entries) > 0

        if on_progress:
            on_progress(0.55, "Kanal örnekleri test ediliyor")

        fetched_ok = True
        if parsed_ok and entries:
            sample = entries[:]
            random.shuffle(sample)
            sample = sample[: max(1, min(test_channels, len(sample)))]
            ok_count = 0
            for idx, e in enumerate(sample, start=1):
                pr = self.probe_stream(e.url)
                if pr.ok:
                    ok_count += 1
                if on_progress:
                    on_progress(0.55 + (0.35 * (idx / len(sample))), f"Kanal testi {idx}/{len(sample)}")
            fetched_ok = ok_count >= 1

        if on_progress:
            on_progress(0.95, "Tamamlandı")

        analysis = PlaylistAnalysis(
            source_url=url,
            fetched_ok=fetched_ok,
            parsed_ok=parsed_ok,
            channel_count=len(entries),
            groups=groups,
            expiry=expiry,
        )

        _ = time.time() - start
        if on_progress:
            on_progress(1.0, "Hazır")

        return analysis, entries

    def filter_entries_by_groups(self, entries: list[ChannelEntry], groups: set[str]) -> list[ChannelEntry]:
        if not groups:
            return []
        norm = {g.strip() for g in groups if g and g.strip()}
        return [e for e in entries if e.group and e.group.strip() in norm]

    def to_m3u_plus(self, entries: list[ChannelEntry]) -> str:
        return build_m3u_plus(entries)
