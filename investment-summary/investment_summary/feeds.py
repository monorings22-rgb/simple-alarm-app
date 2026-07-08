"""RSS/Atom フィード(ニュースサイト・Reddit など)から記事を収集する。

外部パーサへの依存を避けるため、標準ライブラリの xml.etree で RSS 2.0 / Atom を直接パースする。
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

USER_AGENT = "investment-summary-bot/1.0 (daily market digest)"
SUMMARY_MAX_CHARS = 240

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    """HTMLタグ除去・実体参照デコード・空白正規化。"""
    text = _TAG_RE.sub(" ", text or "")
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _first_text(elem: ET.Element, *tags: str) -> str:
    """名前空間を無視して、最初に見つかったタグのテキストを返す。"""
    for tag in tags:
        found = elem.find(f"{{*}}{tag}")
        if found is None:
            found = elem.find(tag)
        if found is not None and found.text:
            return found.text
    return ""


def parse_feed(content: bytes) -> list[dict]:
    """RSS 2.0 / Atom のバイト列をパースして記事のリストを返す。"""
    root = ET.fromstring(content)
    # RSS 2.0: <rss><channel><item>... / Atom: <feed><entry>...
    entries = root.findall(".//{*}item") or root.findall(".//item") or root.findall("{*}entry")
    items = []
    for entry in entries:
        items.append(
            {
                "title": _clean(_first_text(entry, "title")),
                "summary": _clean(_first_text(entry, "description", "summary", "content")),
                "published": _first_text(entry, "pubDate", "published", "updated").strip(),
            }
        )
    return items


def fetch_feed(name: str, url: str, max_items: int) -> list[dict]:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    items = []
    for entry in parse_feed(resp.content)[:max_items]:
        summary = entry["summary"]
        if len(summary) > SUMMARY_MAX_CHARS:
            summary = summary[:SUMMARY_MAX_CHARS] + "…"
        items.append({**entry, "summary": summary, "source": name})
    return items


def build_feed_section(feeds: list[dict], max_items: int) -> str:
    """複数フィードの記事をテキスト化する。失敗したフィードはスキップ。"""
    lines: list[str] = []
    for feed in feeds:
        try:
            items = fetch_feed(feed["name"], feed["url"], max_items)
        except Exception as exc:
            logger.warning("フィードの取得に失敗: %s (%s)", feed["url"], exc)
            continue
        for item in items:
            line = f"- [{item['source']}] {item['title']}"
            if item["published"]:
                line += f" ({item['published']})"
            if item["summary"]:
                line += f"\n  {item['summary']}"
            lines.append(line)
    return "\n".join(lines) if lines else "(取得できた記事はありません)"
