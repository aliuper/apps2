from __future__ import annotations

import re

from alibaba.models import ChannelEntry


_EXTINF_RE = re.compile(r"^#EXTINF:(?P<dur>-?\d+)\s*(?P<attrs>[^,]*),(?P<name>.*)$")
_ATTR_RE = re.compile(r"(\w[\w-]*)=\"([^\"]*)\"")


def parse_m3u_plus(text: str) -> list[ChannelEntry]:
    lines = [ln.strip("\ufeff").rstrip() for ln in text.splitlines()]
    entries: list[ChannelEntry] = []

    pending: dict[str, str] | None = None
    pending_name: str | None = None

    for ln in lines:
        if not ln:
            continue

        if ln.startswith("#EXTINF"):
            m = _EXTINF_RE.match(ln)
            pending = {}
            pending_name = ""
            if m:
                attrs = m.group("attrs") or ""
                pending_name = (m.group("name") or "").strip()
                for k, v in _ATTR_RE.findall(attrs):
                    pending[k] = v
            continue

        if ln.startswith("#"):
            continue

        if pending is None:
            continue

        url = ln
        group = pending.get("group-title")
        tvg_id = pending.get("tvg-id")
        tvg_name = pending.get("tvg-name")
        tvg_logo = pending.get("tvg-logo")

        entries.append(
            ChannelEntry(
                name=pending_name or tvg_name or url,
                url=url,
                group=group,
                tvg_id=tvg_id,
                tvg_name=tvg_name,
                tvg_logo=tvg_logo,
            )
        )
        pending = None
        pending_name = None

    return entries


def unique_groups(entries: list[ChannelEntry]) -> list[str]:
    groups = {e.group.strip() for e in entries if e.group and e.group.strip()}
    return sorted(groups, key=lambda s: s.lower())


def build_m3u_plus(entries: list[ChannelEntry]) -> str:
    out: list[str] = ["#EXTM3U"]
    for e in entries:
        attrs: list[str] = []
        if e.tvg_id:
            attrs.append(f'tvg-id="{e.tvg_id}"')
        if e.tvg_name:
            attrs.append(f'tvg-name="{e.tvg_name}"')
        if e.tvg_logo:
            attrs.append(f'tvg-logo="{e.tvg_logo}"')
        if e.group:
            attrs.append(f'group-title="{e.group}"')

        attr_str = " ".join(attrs)
        if attr_str:
            out.append(f"#EXTINF:-1 {attr_str},{e.name}")
        else:
            out.append(f"#EXTINF:-1,{e.name}")
        out.append(e.url)

    return "\n".join(out) + "\n"
