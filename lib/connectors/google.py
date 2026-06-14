"""Google web search via Jina (s.jina.ai) — always-on default source.

Jina's search endpoint runs a Google query server-side and returns the SERP as
structured JSON, so PulseTrace gets open-web coverage (news, blogs, forums) on
top of the platform connectors. Auth is a single `JINA_API` bearer key.
"""
from __future__ import annotations
import os
import requests
from .base import Connector, Post

_URL = "https://s.jina.ai/"


class GoogleConnector(Connector):
    name = "google"

    def fetch(self, query: str, limit: int = 20) -> list[Post]:
        key = os.environ.get("JINA_API", "").strip()
        if not key:
            return []
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "X-Respond-With": "no-content",
        }
        try:
            r = requests.get(_URL, params={"q": query}, headers=headers, timeout=30)
            r.raise_for_status()
            rows = r.json().get("data", [])
        except (requests.RequestException, ValueError):
            return []

        out: list[Post] = []
        for i, h in enumerate(rows[:limit]):
            title = (h.get("title") or "").strip()
            body = (h.get("description") or h.get("content") or "").strip()
            text = (title + "\n\n" + body).strip()
            if not text:
                continue
            url = h.get("url") or ""
            out.append(Post(
                id=f"google:{url or i}",
                source="google",
                text=text[:2000],
                author=None,
                url=url or None,
                ts=0,
                reactions=0,
                comments=0,
                shares=0,
                raw={"date": h.get("date")},
            ))
        return out
