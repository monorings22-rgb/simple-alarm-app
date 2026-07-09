"""収集したトレンドデータと発信者プロフィールをもとに Claude API でニッチジャンル分析レポートを生成する。"""

from __future__ import annotations

import json

import anthropic

MODEL = "claude-opus-4-8"
MAX_OUTPUT_TOKENS = 20000
MAX_CONTINUATIONS = 5  # web検索(サーバーサイドツール)の pause_turn 継続上限

SYSTEM_PROMPT = """\
あなたはSNSマーケティングとコンテンツ戦略の専門家です。個人発信者向けに「SNS発信で狙うべきニッチジャンル」を発見する週次リサーチレポートを日本語のMarkdownで作成します。

## ニッチジャンル発掘の方法論(この手順で分析すること)
1. **トレンドの読み取り** — 提供されたトレンドデータから、今伸びている・これから伸びそうなテーマを抽出する
2. **掛け合わせでニッチ化** — 「大ジャンル × 別ジャンル」「大ジャンル × 特定ターゲット」の掛け合わせで、競合が少なく需要があるニッチ候補を生成する(例: 投資 × 子育て世帯、AI × 高齢者向け解説)。発信者のプロフィール(興味・強み)と接点があるものを優先する
3. **4軸スコアリング** — 各候補を以下の4軸で1〜5点評価し、合計点でランキングする
   - 需要: 検索・トレンドの伸び、悩みの深さ
   - 競合の少なさ: 発信者の飽和度(web検索で実際の競合状況を確認すること)
   - 発信者適合: プロフィールとの相性、継続できるか
   - 収益性: アフィリエイト・コンテンツ販売・案件などマネタイズ経路の有無
4. **深掘りと検証プラン** — 上位ニッチについて、具体的なアカウントコンセプトと「小さくテストして反応を見る」検証手順を提示する

## レポート構成(この見出し構成に従うこと)
1. `## 今週のトレンド概観` — 提供データから読み取れる注目テーマを3〜5文で要約
2. `## ニッチジャンル候補ランキング` — 候補をテーブルで提示(ニッチ名 / 掛け合わせの構造 / 需要 / 競合の少なさ / 適合 / 収益性 / 合計点 / 一言コメント)
3. `## 注目ニッチ深掘り` — 上位候補それぞれについて:
   - アカウントコンセプト(誰に・何を・どう届けるか、1行で)
   - ターゲット像(具体的なペルソナ)
   - 差別化ポイント(既存の発信者と何が違うか)
   - 最初の投稿ネタ10本(タイトル案として列挙)
4. `## 2週間検証プラン` — 小さくテストする手順(投稿頻度・計測するKPI・撤退/継続の判断基準)
5. `## 注意点` — 誇大な期待をさせない留意事項(結果には個人差がある、トレンドは変化する等)

## 執筆ルール
- 提供されたトレンドデータと発信者プロフィールを根拠として使うこと
- web検索が利用できる場合は、候補ニッチの競合状況(既に強い発信者がいないか、飽和していないか)を確認してからスコアを付けること
- トレンドデータが空または少ない場合は、web検索で直近の日本のトレンド・話題を調べて補完すること
- 不確実な事柄は断定せず、「〜の傾向がある」「〜の可能性がある」と確度を明示する
- 「絶対に伸びる」「確実に稼げる」といった断定・煽り表現は使わない
- 投稿ネタは発信者がそのまま使える具体的なタイトル案にする(抽象的なテーマ名で終わらせない)
- 読者はSNS運用の初心者〜中級者を想定し、専門用語には簡単な補足を付ける
"""

USER_PROMPT_TEMPLATE = """\
本日は {today} です。以下の発信者プロフィールと今週のトレンドデータをもとに、SNS発信で狙うべきニッチジャンルの週次リサーチレポートを作成してください。

ニッチ候補は {num_candidates} 個生成し、上位 {num_deep_dives} 個を深掘りしてください。

## 発信者プロフィール
{profile}

## 今週のトレンドデータ(RSSより取得)
{trends}
"""


def format_profile(profile: dict) -> str:
    lines = []
    labels = {
        "interests": "興味・経験のある分野",
        "strengths": "強み",
        "target_platforms": "発信したいプラットフォーム",
        "goal": "目標",
        "available_time": "使える時間",
    }
    for key, label in labels.items():
        value = profile.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines.append(f"- {label}: {'、'.join(value)}")
        else:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines) if lines else json.dumps(profile, ensure_ascii=False)


def build_user_prompt(today: str, profile: dict, trends: str, num_candidates: int, num_deep_dives: int) -> str:
    return USER_PROMPT_TEMPLATE.format(
        today=today,
        profile=format_profile(profile),
        trends=trends,
        num_candidates=num_candidates,
        num_deep_dives=num_deep_dives,
    )


def generate_report(user_prompt: str, use_web_search: bool = True) -> str:
    """Claude API を呼び出してレポート本文(Markdown)を返す。"""
    client = anthropic.Anthropic()

    tools = []
    if use_web_search:
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 10}]

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
