"""株価・指数・為替の日足データを取得する。

Yahoo Finance の chart API(キー不要)を優先し、失敗時は Stooq の無料 CSV API にフォールバックする。
config のシンボルは Stooq 形式で統一: ^spx (S&P 500), ^nkx (日経平均), aapl.us (Apple),
7203.jp (トヨタ), usdjpy (ドル円)。Yahoo 用シンボルへは内部で変換する。
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
STOOQ_HISTORY_URL = "https://stooq.com/q/d/l/"
# GitHub Actions などのデータセンターIPからは bot 風UAが拒否されやすいため、ブラウザ相当のUAを使う
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# Stooq形式 → Yahoo形式の指数マッピング
_INDEX_MAP = {
    "^spx": "^GSPC",
    "^ndq": "^IXIC",
    "^dji": "^DJI",
    "^nkx": "^N225",
    "^tpx": "^TPX",
}


def to_yahoo_symbol(symbol: str) -> str:
    """Stooq形式のシンボルを Yahoo Finance 形式へ変換する。"""
    s = symbol.lower()
    if s in _INDEX_MAP:
        return _INDEX_MAP[s]
    if s.endswith(".us"):
        return s[:-3].upper()  # aapl.us → AAPL
    if s.endswith(".jp"):
        return s[:-3].upper() + ".T"  # 7203.jp → 7203.T
    if len(s) == 6 and s.isalpha():
        return s.upper() + "=X"  # usdjpy → USDJPY=X
    return symbol.upper()


def fetch_history_yahoo(symbol: str, lookback_days: int = 30) -> list[dict]:
    """Yahoo Finance chart API から日足データを取得する(古い順)。"""
    ysym = to_yahoo_symbol(symbol)
    resp = requests.get(
        YAHOO_CHART_URL.format(symbol=quote(ysym)),
        params={"range": "1mo", "interval": "1d"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    rows = [
        {
            "Date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "Close": str(close),
        }
        for ts, close in zip(timestamps, closes)
        if close is not None
    ]
    if not rows:
        raise ValueError(f"yahoo returned no data for {symbol!r} ({ysym})")
    return rows


def fetch_history_stooq(symbol: str, lookback_days: int = 30) -> list[dict]:
    """Stooq の無料 CSV API から日足データを取得する(古い順)。"""
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


def fetch_history(symbol: str, lookback_days: int = 30) -> list[dict]:
    """Yahoo → Stooq の順で試して日足データを返す。"""
    try:
        return fetch_history_yahoo(symbol, lookback_days)
    except Exception as exc:
        logger.info("Yahooからの取得に失敗、Stooqへフォールバック: %s (%s)", symbol, exc)
        return fetch_history_stooq(symbol, lookback_days)


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
