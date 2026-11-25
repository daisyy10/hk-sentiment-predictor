import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()
client = ApifyClient(os.getenv("APIFY_TOKEN"))

ACTOR_ID = "bovi/aastocks-scraper"
MAX_RESULTS = 30

# ticker -> (naam, title me dhundhne ke words)
STOCKS = {
    "0700.HK": ("Tencent", ["騰訊", "Tencent"]),
    "9988.HK": ("Alibaba", ["阿里", "Alibaba"]),
    "1810.HK": ("Xiaomi", ["小米", "Xiaomi"]),
    "3690.HK": ("Meituan", ["美團", "Meituan"]),
    "0005.HK": ("HSBC", ["滙豐", "匯豐", "HSBC"]),
}

FEEDS = ["latest-news", "top-news", "popular-news", "recommend-news"]
LANGUAGES = ["tc", "en"]  # Chinese aur English headlines dono


def run_actor(feed, language):
    run_input = {"feed": feed, "language": language, "maxResults": MAX_RESULTS}
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    return client.dataset(run.default_dataset_id).list_items().items


def match_stock(title):
    for ticker, (name, words) in STOCKS.items():
        if any(w.lower() in title.lower() for w in words):
            return ticker, name
    return None, None


def main():
    scraped_at = datetime.now(timezone.utc).isoformat()
    all_items = []
    for language in LANGUAGES:
        for feed in FEEDS:
            print("Scraping", feed, language)
            try:
                items = run_actor(feed, language)
            except Exception as e:
                print("  failed:", e)
                continue
            print("  got", len(items), "headlines")
            all_items.extend(items)

    # duplicate hatao aur sirf hamare 5 stocks wali headlines rakho
    seen = set()
    matched = []
    for item in all_items:
        key = item.get("article_id") or item.get("url")
        if key in seen:
            continue
        seen.add(key)
        ticker, name = match_stock(item.get("title", ""))
        if ticker:
            item["ticker"] = ticker
            item["asset_name"] = name
            item["scraped_at"] = scraped_at
            matched.append(item)

    print("Total headlines:", len(all_items))
    with open("data/aastocks_news.json", "w", encoding="utf-8") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)
    print("Saved", len(matched), "matching headlines to data/aastocks_news.json")


if __name__ == "__main__":
    main()