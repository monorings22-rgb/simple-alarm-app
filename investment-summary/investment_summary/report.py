"""収集したデータをもとに Claude API で投資サマリーを生成する。"""

from __future__ import annotations

import anthropic

MODEL = "claude-opus-4-8"
MAX_OUTPUT_TOKENS = 16000
MAX_CONTINUATIONS = 5  # web検索(サーバーサイドツール)の pause_turn 継続上限

SYSTEM_PROMPT = """\
あなたは経験豊富な市場アナリストです。個人投資家向けの「デイリー投資サマリー」を日本語のMarkdownで作成します。

## レポート構成(この見出し構成に従うこと)
1. `## 本日の市況概観` — 主要指数・為替の動きを3〜5文で要約
2. `## 今後の株価予想` — 短期(数日〜数週間)の見通し。強気/弱気/中立の判断と根拠
3. `## 市場トレンド` — 現在進行中のテーマ・資金の流れ・センチメント(SNSの話題も反映)
4. `## 注目業界` — 2〜4業界。それぞれ注目理由を具体的に
5. `## 注目銘柄` — 3〜6銘柄。ティッカー・注目理由・リスクをセットで
6. `## 投資アドバイス` — ポートフォリオ運営上の実践的な助言(リスク管理を含む)
7. `## リスク要因` — 今後警戒すべきイベント・指標発表・地政学リスク
8. `## 免責事項` — 「本レポートは情報提供のみを目的としており、投資勧誘や個別の投資助言ではありません。投資判断はご自身の責任で行ってください。」を必ず含める

## 執筆ルール
- 提供された市場データ・ニュース・SNSの情報を根拠として使い、数値に言及するときは提供データと矛盾しないこと
- web検索が利用できる場合は、重要イベント(FOMC・日銀会合・決算・経済指標など)の最新状況を確認してから書くこと
- 不確実な事柄は断定せず、「〜の可能性がある」「市場では〜との見方が多い」のように確度を明示する
- 予想には必ず前提条件と外れた場合のシナリオを添える
- 特定銘柄の購入を煽らない。メリットとリスクを必ず両論併記する
- 読者は投資経験1〜3年程度の個人投資家を想定し、専門用語には簡単な補足を付ける
"""

USER_PROMPT_TEMPLATE = """\
本日は {today} です。以下の収集データをもとに、本日のデイリー投資サマリーを作成してください。

## 市場データ(Stooqより取得)
{market}

## ニュースヘッドライン(RSSより取得)
{news}

## SNSで話題のトピック(Reddit投資系サブレディットより取得)
{sns}
"""


def build_user_prompt(today: str, market: str, news: str, sns: str) -> str:
    return USER_PROMPT_TEMPLATE.format(today=today, market=market, news=news, sns=sns)


def generate_report(user_prompt: str, use_web_search: bool = True) -> str:
    """Claude API を呼び出してレポート本文(Markdown)を返す。"""
    client = anthropic.Anthropic()

    tools = []
    if use_web_search:
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]

    messages: list[dict] = [{"role": "user", "content": user_prompt}]

    response = None
    for _ in range(MAX_CONTINUATIONS + 1):
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            thinking={"type": "adaptive"},
            tools=tools,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        # サーバーサイドのweb検索がイテレーション上限に達した場合は続きを再要求する
        if response.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue
        break

    if response is None or response.stop_reason == "refusal":
        raise RuntimeError("レポート生成に失敗しました (refusal または応答なし)")

    text = "\n".join(block.text for block in response.content if block.type == "text")
    if not text.strip():
        raise RuntimeError("レポート本文が空でした")
    return text
