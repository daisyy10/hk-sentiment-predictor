import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()
exa = Exa(api_key=os.getenv("EXA_API_KEY"))

STOCKS = {
    "0700.HK": "Tencent",
    "9988.HK": "Alibaba",
    "1810.HK": "Xiaomi",
    "3690.HK": "Meituan",
    "0005.HK": "HSBC",
}

NEWS_PER_STOCK = 10


def fetch_news(ticker, name):
    # pichhle 10 din ki date
    since = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")

    results = exa.search(
        f"{name} {ticker} stock news",
        num_results=NEWS_PER_STOCK,
        start_published_date=since,
        category="news",
        contents={"highlights": True},
    )

    articles = []
    for r in results.results:
        highlights = getattr(r, "highlights", None) or []
        articles.append(
            {
                "ticker": ticker,
                "asset_name": name,
                "title": r.title,
                "url": r.url,
                "published_date": r.published_date,
                "text": " ".join(highlights),
            }
        )
    return articles


def main():
    all_news = []
    for ticker, name in STOCKS.items():
        print("Fetching news for", ticker)
        articles = fetch_news(ticker, name)
        print("  got", len(articles), "articles")
        all_news.extend(articles)

    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    print("Saved", len(all_news), "articles to data/news.json")


if __name__ == "__main__":
    main()
