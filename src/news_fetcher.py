import asyncio
import urllib.request
import xml.etree.ElementTree as ET


async def get_recent_news(symbol: str, limit: int = 3) -> str:
    try:
        def _fetch_news() -> list[str]:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            items = root.findall('./channel/item')
            news_items: list[str] = []
            for item in items[:limit]:
                title = item.find('title')
                description = item.find('description')
                if title is not None and title.text:
                    if description is not None and description.text:
                        news_items.append(f"- TITLE: {title.text} | SUMMARY: {description.text}")
                    else:
                        news_items.append("- " + title.text)
            return news_items

        news_items = await asyncio.to_thread(_fetch_news)
        if not news_items:
            return "No recent news available."

        return "\n".join(news_items)
    except Exception:
        return "No recent news available."


async def _main() -> None:
    news = await get_recent_news("META")
    print(news)


if __name__ == "__main__":
    asyncio.run(_main())
