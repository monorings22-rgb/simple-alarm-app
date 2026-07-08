"""エントリーポイント: データ収集 → レポート生成 → Markdown保存。

使い方:
    python -m investment_summary.main                # reports/YYYY-MM-DD.md に生成
    python -m investment_summary.main --dry-run      # API を呼ばずプロンプトだけ表示
    python -m investment_summary.main --no-web-search
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .feeds import build_feed_section
from .market import build_market_section
from .report import build_user_prompt, generate_report

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def collect_data(config: dict) -> tuple[str, str, str]:
    max_items = config.get("max_items_per_feed", 8)
    logger.info("市場データを取得中...")
    market = build_market_section(config)
    logger.info("ニュースフィードを取得中...")
    news = build_feed_section(config.get("news_feeds", []), max_items)
    logger.info("SNSフィードを取得中...")
    sns = build_feed_section(config.get("sns_feeds", []), max_items)
    return market, news, sns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="デイリー投資サマリーを生成する")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="設定ファイル(JSON)のパス")
    parser.add_argument("--out", type=Path, default=Path("reports"), help="レポート出力ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="APIを呼ばず、収集データとプロンプトを表示して終了")
    parser.add_argument("--no-web-search", action="store_true", help="Claudeのweb検索ツールを無効にする")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    today = datetime.now(JST).strftime("%Y-%m-%d")

    market, news, sns = collect_data(config)
    user_prompt = build_user_prompt(today=today, market=market, news=news, sns=sns)

    if args.dry_run:
        print(user_prompt)
        return 0

    logger.info("Claude API でレポートを生成中...")
    body = generate_report(user_prompt, use_web_search=not args.no_web_search)

    report = f"# デイリー投資サマリー {today}\n\n{body}\n"
    args.out.mkdir(parents=True, exist_ok=True)
    dated_path = args.out / f"{today}.md"
    dated_path.write_text(report, encoding="utf-8")
    (args.out / "latest.md").write_text(report, encoding="utf-8")
    logger.info("レポートを保存しました: %s", dated_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
