from __future__ import annotations

import re


_URL_RE = re.compile(r"https?://[^\s\]\)\}\>\"']+", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    found = [m.group(0).strip() for m in _URL_RE.finditer(text or "")]
    dedup: list[str] = []
    seen = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup
