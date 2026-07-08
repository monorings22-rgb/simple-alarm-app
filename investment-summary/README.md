# デイリー投資サマリー生成ツール

SNS・ニュース・株式市場の情報を毎日自動収集し、Claude API で投資サマリーを生成するツールです。

## レポートに含まれる内容

- 本日の市況概観
- 今後の株価予想(短期見通し)
- 市場トレンド(SNSのセンチメント含む)
- 注目業界
- 注目銘柄(注目理由とリスクをセットで)
- 投資アドバイス
- リスク要因
- 免責事項

## 情報ソース

| 種別 | ソース | 取得方法 |
|---|---|---|
| 株式市場 | 主要指数(S&P 500・NASDAQ・NYダウ・日経平均)、為替、ウォッチリスト銘柄 | [Stooq](https://stooq.com) の無料CSV API(キー不要) |
| ニュース | NHK経済・Yahoo!ニュース経済・CNBC・MarketWatch | RSSフィード |
| SNS | Reddit (r/stocks, r/investing, r/wallstreetbets) | RSSフィード |
| 補完情報 | 当日の重要イベント(FOMC・決算など) | Claude の web検索ツール |

ソースは `config.json` で自由に追加・変更できます(ウォッチリスト銘柄は Stooq のシンボル形式: 米国株 `aapl.us`、日本株 `7203.jp`)。

## セットアップ

```bash
cd investment-summary
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 使い方

```bash
# レポート生成(reports/YYYY-MM-DD.md と reports/latest.md に保存)
python -m investment_summary.main

# APIを呼ばずに、収集データとプロンプトだけ確認
python -m investment_summary.main --dry-run

# Claudeのweb検索を使わない(収集データのみで生成)
python -m investment_summary.main --no-web-search
```

## 毎日の自動実行(GitHub Actions)

`.github/workflows/daily-investment-summary.yml` により、**平日の朝6:30(日本時間)** に自動でレポートを生成し、`investment-summary/reports/` にコミットします。

有効化するには、リポジトリの **Settings → Secrets and variables → Actions** で以下のシークレットを登録してください:

- `ANTHROPIC_API_KEY` — Anthropic の APIキー

手動実行は Actions タブの「Daily Investment Summary」→「Run workflow」からいつでも可能です。

## 免責事項

本ツールが生成するレポートは情報提供のみを目的としており、投資勧誘や個別の投資助言ではありません。投資判断はご自身の責任で行ってください。
