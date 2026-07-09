"""エントリーポイント: トレンド収集 → ニッチ分析レポート生成 → Markdown保存。

使い方:
    python -m sns_niche_research.main                # reports/YYYY-MM-DD.md に生成
    python -m sns_niche_research.main --dry-run      # API を呼ばずプロンプトだけ表示
    python -m sns_niche_research.main --no-web-search
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .feeds import build_feed_section
from .report import build_user_prompt, generate_report

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SNSニッチジャンルの週次リサーチレポートを生成する")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="設定ファイル(JSON)のパス")
    parser.add_argument("--out", type=Path, default=Path("reports"), help="レポート出力ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="APIを呼ばず、収集データとプロンプトを表示して終了")
    parser.add_argument("--no-web-search", action="store_true", help="Claudeのweb検索ツールを無効にする")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    today = datetime.now(JST).strftime("%Y-%m-%d")

    logger.info("トレンドフィードを取得中...")
    trends = build_feed_section(config.get("trend_feeds", []), config.get("max_items_per_feed", 10))

    user_prompt = build_user_prompt(
        today=today,
        profile=config.get("profile", {}),
        trends=trends,
        num_candidates=config.get("num_candidates", 8),
        num_deep_dives=config.get("num_deep_dives", 3),
    )

    if args.dry_run:
        print(user_prompt)
        return 0

    logger.info("Claude API でレポートを生成中...")
    body = generate_report(user_prompt, use_web_search=not args.no_web_search)

    report = f"# SNSニッチジャンル リサーチレポート {today}\n\n{body}\n"
    args.out.mkdir(parents=True, exist_ok=True)
    dated_path = args.out / f"{today}.md"
    dated_path.write_text(report, encoding="utf-8")
    (args.out / "latest.md").write_text(report, encoding="utf-8")
    logger.info("レポートを保存しました: %s", dated_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
