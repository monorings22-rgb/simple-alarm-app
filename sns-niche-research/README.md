# SNSニッチジャンル 週次リサーチツール

「SNS発信で狙うべきニッチジャンルの探し方」を自動化するツールです。
毎週、日本のトレンド情報を自動収集し、Claude API であなたのプロフィールに合った
ニッチジャンル候補を発掘・スコアリングしたレポートを生成します。

## レポートに含まれる内容

- **今週のトレンド概観** — 収集データから読み取れる注目テーマ
- **ニッチジャンル候補ランキング** — 「大ジャンル×掛け合わせ」で生成した候補を4軸(需要 / 競合の少なさ / 発信者適合 / 収益性)で採点
- **注目ニッチ深掘り(上位3件)** — アカウントコンセプト・ペルソナ・差別化ポイント・そのまま使える投稿ネタ10本
- **2週間検証プラン** — 小さくテストするための投稿頻度・KPI・継続/撤退の判断基準
- **注意点** — 過度な期待をさせないための留意事項

## 情報ソース

| 種別 | ソース |
|---|---|
| 検索トレンド | Googleトレンド(日本・急上昇ワード) RSS |
| 話題の記事 | はてなブックマーク人気エントリー(総合・テクノロジー・暮らし・学び・政治と経済) RSS |
| ニュース | NHK 主要ニュース RSS |
| 競合調査 | Claude の web検索ツール(候補ニッチの飽和度チェック) |

## 使い方

```bash
pip install -r requirements.txt

# プロンプトの確認だけ(API不要)
python -m sns_niche_research.main --dry-run

# レポート生成(要 ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
python -m sns_niche_research.main --out reports
```

レポートは `reports/YYYY-MM-DD.md` と `reports/latest.md` に保存されます。

## 自分に合わせてカスタマイズする

`config.json` の `profile` を **必ず自分の情報に書き換えてください**。
分析はこのプロフィールを軸に行われるため、ここの精度がレポートの質を決めます。

```json
{
  "profile": {
    "interests": ["興味・経験のある分野を列挙"],
    "strengths": ["自分の強み・実績"],
    "target_platforms": ["X (Twitter)", "YouTube など"],
    "goal": "発信の目標(収益化・集客など)",
    "available_time": "発信に使える時間"
  }
}
```

- `trend_feeds` — 収集するRSSフィード。追加・削除自由
- `num_candidates` / `num_deep_dives` — 生成する候補数と深掘りする件数

## 自動実行(GitHub Actions)

`.github/workflows/weekly-sns-niche-research.yml` により、**毎週月曜 朝6:30(JST)** に
自動でレポートを生成し `reports/` にコミットします。

有効化するには、リポジトリの **Settings → Secrets and variables → Actions** に
`ANTHROPIC_API_KEY` を登録してください(投資サマリーツールと共通のシークレットです)。
手動実行は Actions タブの「Run workflow」から可能です。

## テスト

```bash
cd sns-niche-research
python -m unittest discover -s tests
```
