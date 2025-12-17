from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class ChannelEntry:
    name: str
    url: str
    group: str | None = None
    tvg_id: str | None = None
    tvg_name: str | None = None
    tvg_logo: str | None = None


@dataclass
class PlaylistAnalysis:
    source_url: str
    fetched_ok: bool
    parsed_ok: bool
    channel_count: int
    groups: list[str]
    expiry: datetime | None = None


@dataclass
class GroupSelection:
    selected_groups: set[str] = field(default_factory=set)

    def set_all(self, groups: Iterable[str]) -> None:
        self.selected_groups = set(groups)

    def clear(self) -> None:
        self.selected_groups.clear()
