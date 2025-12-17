from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from alibaba.models import PlaylistAnalysis, GroupSelection
from alibaba.models import ChannelEntry


@dataclass
class AppState:
    last_analysis: PlaylistAnalysis | None = None
    last_entries: list[ChannelEntry] = field(default_factory=list)
    selection: GroupSelection = field(default_factory=GroupSelection)
    created_at: datetime = field(default_factory=datetime.now)
    output_ext: str = "m3u"
    output_label: str = "alibaba"
    combine_outputs: bool = True

    auto_urls: list[str] = field(default_factory=list)
    auto_working: list[tuple[str, list[ChannelEntry], datetime | None]] = field(default_factory=list)
    auto_country_codes: set[str] = field(default_factory=set)
