"""Stooq の無料 CSV API から株価・指数・為替のデータを取得する。

Stooq はAPIキー不要で日足の履歴CSVを配信している。
シンボル例: ^spx (S&P 500), ^nkx (日経平均), aapl.us (Apple), 7203.jp (トヨタ), usdjpy (ドル円)
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

STOOQ_HISTORY_URL = "https://stooq.com/q/d/l/"
USER_AGENT = "investment-summary-bot/1.0"


def fetch_history(symbol: str, lookback_days: int = 30) -> list[dict]:
    """直近 lookback_days 日分の日足データを取得する(古い順)。"""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    resp = requests.get(
        STOOQ_HISTORY_URL,
        params={
            "s": symbol,
            "i": "d",
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or text.lower().startswith("no data") or "Date" not in text.splitlines()[0]:
        raise ValueError(f"stooq returned no data for {symbol!r}")
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Close")]
    if not rows:
        raise ValueError(f"stooq returned empty history for {symbol!r}")
    return rows


def _pct(new: float, old: float) -> float:
    return (new - old) / old * 100.0


def summarize_symbol(symbol: str, label: str) -> str:
    """1シンボル分の要約行を作る。例: 'S&P 500: 6,230.5 (前日比 +0.52%, 5日間 +1.8%)'"""
    rows = fetch_history(symbol)
    closes = [float(r["Close"]) for r in rows]
    last_date = rows[-1]["Date"]
    last = closes[-1]
    parts = [f"{last:,.2f}"]
    if len(closes) >= 2:
        parts.append(f"前日比 {_pct(last, closes[-2]):+.2f}%")
    if len(closes) >= 6:
        parts.append(f"直近5営業日 {_pct(last, closes[-6]):+.2f}%")
    if len(closes) >= 21:
        parts.append(f"約1ヶ月 {_pct(last, closes[-21]):+.2f}%")
    return f"- {label} ({symbol}): {parts[0]} [{last_date}時点] ({', '.join(parts[1:])})"


def build_market_section(config: dict) -> str:
    """config の indices / forex / watchlist をまとめてテキスト化する。"""
    sections: list[str] = []
    groups = [
        ("主要指数", config.get("indices", {})),
        ("為替", config.get("forex", {})),
        ("ウォッチリスト銘柄", config.get("watchlist", {})),
    ]
    for title, symbols in groups:
        if not symbols:
            continue
        lines = [f"### {title}"]
        for symbol, label in symbols.items():
            try:
                lines.append(summarize_symbol(symbol, label))
            except Exception as exc:  # 1銘柄の失敗で全体を止めない
                logger.warning("市場データの取得に失敗: %s (%s)", symbol, exc)
                lines.append(f"- {label} ({symbol}): データ取得失敗")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
