import os
import json
import time
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()
client = ApifyClient(os.getenv("APIFY_TOKEN"))

ACTOR_ID = "claude_code_reviewer/lihkg-scraper-en"
MAX_ITEMS = 100
RETRIES = 1
WAIT_SECONDS = 30

STOCKS = {
    "0700.HK": {"name": "Tencent", "keywords": ["騰訊", "鵝廠", "0700"]},
    "9988.HK": {"name": "Alibaba", "keywords": ["阿里", "阿里巴巴", "9988"]},
    "1810.HK": {"name": "Xiaomi", "keywords": ["小米", "1810"]},
    "3690.HK": {"name": "Meituan", "keywords": ["美團", "3690"]},
    "0005.HK": {"name": "HSBC", "keywords": ["滙豐", "匯豐", "0005"]},
}


def cache_path(ticker):
    return f"data/lihkg_{ticker}.json"


def fetch_once(info):
    run_input = {
        "mode": "search",
        "keywords": info["keywords"],
        "order": "desc_create_time",
        "dateFrom": "10d",
        "maxItems": MAX_ITEMS,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    return client.dataset(run.default_dataset_id).list_items().items


def scrape_stock(ticker, info):
    path = cache_path(ticker)

    # pehle se saved data ho to dobara scrape nahi karenge
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        if saved:
            print("  using saved data for", ticker)
            return saved

    items = []
    for attempt in range(1, RETRIES + 1):
        items = fetch_once(info)
        if items:
            break
        print(f"  attempt {attempt}: 0 posts, waiting {WAIT_SECONDS}s")
        time.sleep(WAIT_SECONDS)

    # duplicate threads hatao
    seen = set()
    unique = []
    for item in items:
        if item["thread_id"] in seen:
            continue
        seen.add(item["thread_id"])
        item["ticker"] = ticker
        item["asset_name"] = info["name"]
        unique.append(item)

    # sirf tab save karo jab kuch mila, taaki agle run me retry ho sake
    if unique:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
    return unique


def main():
    all_posts = []
    for ticker, info in STOCKS.items():
        print("Scraping", ticker)
        posts = scrape_stock(ticker, info)
        print("  got", len(posts), "posts")
        all_posts.extend(posts)

    with open("data/lihkg_posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    print("Saved", len(all_posts), "posts to data/lihkg_posts.json")


if __name__ == "__main__":
    main()
