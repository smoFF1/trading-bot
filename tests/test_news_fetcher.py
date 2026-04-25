import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.news_fetcher import get_recent_news


RSS_WITH_THREE_ITEMS = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Alpha surges on earnings</title>
      <description>Alpha reported strong quarterly revenue growth.</description>
    </item>
    <item>
      <title>Beta expands into new markets</title>
      <description>Beta announced expansion plans across Europe.</description>
    </item>
    <item>
      <title>Gamma shares fall after guidance cut</title>
      <description>Gamma lowered its outlook for the next quarter.</description>
    </item>
  </channel>
</rss>
"""

RSS_WITH_MISSING_DESCRIPTION = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>Solo headline without summary</title>
    </item>
  </channel>
</rss>
"""


class FakeUrlopenResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


@pytest.mark.asyncio
async def test_get_recent_news_returns_limited_formatted_items():
    with patch("src.news_fetcher.urllib.request.urlopen", return_value=FakeUrlopenResponse(RSS_WITH_THREE_ITEMS)):
        result = await get_recent_news(limit=2, symbol="META")

    lines = result.splitlines()
    assert len(lines) == 2
    assert lines[0] == "- TITLE: Alpha surges on earnings | SUMMARY: Alpha reported strong quarterly revenue growth."
    assert lines[1] == "- TITLE: Beta expands into new markets | SUMMARY: Beta announced expansion plans across Europe."


@pytest.mark.asyncio
async def test_get_recent_news_falls_back_to_title_when_description_missing():
    with patch("src.news_fetcher.urllib.request.urlopen", return_value=FakeUrlopenResponse(RSS_WITH_MISSING_DESCRIPTION)):
        result = await get_recent_news(symbol="META")

    assert result == "- Solo headline without summary"


@pytest.mark.asyncio
async def test_get_recent_news_returns_default_message_on_url_error():
    with patch("src.news_fetcher.urllib.request.urlopen", side_effect=urllib.error.URLError("network down")):
        result = await get_recent_news(symbol="META")

    assert result == "No recent news available."