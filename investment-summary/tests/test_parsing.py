"""ネットワーク不要のパース処理テスト。実行: python -m unittest discover -s tests"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from investment_summary.feeds import parse_feed
from investment_summary.market import summarize_symbol, to_yahoo_symbol

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test News</title>
    <item>
      <title>Stocks rally on &amp; earnings</title>
      <description><![CDATA[<p>Markets rose <b>sharply</b> today.</p>]]></description>
      <pubDate>Mon, 06 Jul 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>r/stocks</title>
  <entry>
    <title>What are your moves tomorrow?</title>
    <content type="html">&lt;div&gt;Daily discussion thread&lt;/div&gt;</content>
    <updated>2026-07-06T12:00:00+00:00</updated>
  </entry>
</feed>
"""

HISTORY_ROWS = [
    {"Date": f"2026-07-{d:02d}", "Close": str(close)}
    for d, close in [(1, 100.0), (2, 102.0), (3, 101.0), (4, 103.0), (5, 104.0), (6, 105.0)]
]


class ParseFeedTest(unittest.TestCase):
    def test_rss(self):
        items = parse_feed(RSS_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Stocks rally on & earnings")
        self.assertEqual(items[0]["summary"], "Markets rose sharply today.")
        self.assertIn("2026", items[0]["published"])

    def test_atom(self):
        items = parse_feed(ATOM_SAMPLE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "What are your moves tomorrow?")
        self.assertEqual(items[0]["summary"], "Daily discussion thread")


class YahooSymbolTest(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(to_yahoo_symbol("^spx"), "^GSPC")
        self.assertEqual(to_yahoo_symbol("^nkx"), "^N225")
        self.assertEqual(to_yahoo_symbol("aapl.us"), "AAPL")
        self.assertEqual(to_yahoo_symbol("7203.jp"), "7203.T")
        self.assertEqual(to_yahoo_symbol("usdjpy"), "USDJPY=X")


class MarketSummaryTest(unittest.TestCase):
    def test_summarize_symbol(self):
        with patch("investment_summary.market.fetch_history", return_value=HISTORY_ROWS):
            line = summarize_symbol("^spx", "S&P 500")
        self.assertIn("S&P 500", line)
        self.assertIn("105.00", line)
        self.assertIn("前日比 +0.96%", line)   # 105 vs 104
        self.assertIn("直近5営業日 +5.00%", line)  # 105 vs 100


if __name__ == "__main__":
    unittest.main()
