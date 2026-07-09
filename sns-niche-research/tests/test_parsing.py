"""ネットワーク不要のパース処理テスト。実行: python -m unittest discover -s tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sns_niche_research.feeds import parse_feed
from sns_niche_research.report import build_user_prompt, format_profile

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Trends</title>
    <item>
      <title>AI &amp; \xe8\xb3\x87\xe7\x94\xa3\xe9\x81\x8b\xe7\x94\xa8\xe3\x81\x8c\xe8\xa9\xb1\xe9\xa1\x8c</title>
      <description><![CDATA[<p>New tools are <b>trending</b> now.</p>]]></description>
      <pubDate>Mon, 06 Jul 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>hotentry</title>
  <entry>
    <title>Weekly hot topic</title>
    <content type="html">&lt;div&gt;Deep dive article&lt;/div&gt;</content>
    <updated>2026-07-06T12:00:00+00:00</updated>
  </entry>
</feed>
"""


class ParseFeedTest(unittest.TestCase):
    def test_rss(self):
        items = parse_feed(RSS_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "AI & 資産運用が話題")
        self.assertEqual(items[0]["summary"], "New tools are trending now.")
        self.assertIn("2026", items[0]["published"])

    def test_atom(self):
        items = parse_feed(ATOM_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Weekly hot topic")
        self.assertEqual(items[0]["summary"], "Deep dive article")


class PromptBuildTest(unittest.TestCase):
    PROFILE = {
        "interests": ["投資", "AI"],
        "goal": "収益化",
        "target_platforms": ["X (Twitter)"],
    }

    def test_format_profile(self):
        text = format_profile(self.PROFILE)
        self.assertIn("興味・経験のある分野: 投資、AI", text)
        self.assertIn("目標: 収益化", text)
        self.assertIn("X (Twitter)", text)

    def test_build_user_prompt(self):
        prompt = build_user_prompt(
            today="2026-07-09",
            profile=self.PROFILE,
            trends="- [テスト] トレンド記事",
            num_candidates=8,
            num_deep_dives=3,
        )
        self.assertIn("2026-07-09", prompt)
        self.assertIn("8 個生成", prompt)
        self.assertIn("上位 3 個", prompt)
        self.assertIn("トレンド記事", prompt)
        self.assertIn("投資、AI", prompt)


if __name__ == "__main__":
    unittest.main()
