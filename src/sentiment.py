import json
import math
import re
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

vader = SentimentIntensityAnalyzer()
CJK = re.compile(r"[\u4e00-\u9fff]")

# Chinese ke liye chhoti keyword list (crude, README me bataenge)
POSITIVE = [
    "升",
    "反彈",
    "睇好",
    "買入",
    "加倉",
    "見底",
    "利好",
    "增長",
    "盈利",
    "新高",
    "突破",
    "看好",
    "回購",
    "賺",
    "強",
]
NEGATIVE = [
    "跌",
    "睇淡",
    "沽",
    "減持",
    "蝕",
    "虧",
    "利淡",
    "暴跌",
    "新低",
    "跌破",
    "弱",
    "垃圾",
    "割",
    "套",
]

MARKET_CLOSE_HOUR = 16  # HKT


def score_text(text):
    if not text:
        return 0.0
    if CJK.search(text):
        pos = sum(text.count(w) for w in POSITIVE)
        neg = sum(text.count(w) for w in NEGATIVE)
        return 0.0 if pos + neg == 0 else (pos - neg) / (pos + neg)
    return vader.polarity_scores(text)["compound"]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def build_rows():
    rows = []
    for p in load_json("data/lihkg_posts.json"):
        text = p.get("own_text") or p.get("content") or p.get("title") or ""
        likes = (p.get("like_count") or 0) + (p.get("dislike_count") or 0)
        replies = p.get("reply_count") or 0
        rows.append(
            {
                "source": "lihkg",
                "ticker": p["ticker"],
                "text": text,
                "ts": p.get("created_at"),
                # zyada engagement = zyada weight
                "weight": 1 + math.log1p(likes + replies),
            }
        )
    for n in load_json("data/news.json"):
        rows.append(
            {
                "source": "exa",
                "ticker": n["ticker"],
                "text": f"{n.get('title') or ''} {n.get('text') or ''}",
                "ts": n.get("published_date"),
                "weight": 1.0,
            }
        )
    for a in load_json("data/aastocks_news.json"):
        rows.append(
            {
                "source": "aastocks",
                "ticker": a["ticker"],
                "text": a.get("title") or "",
                "ts": a.get("scraped_at"),
                "weight": 1.0,
            }
        )
    return pd.DataFrame(rows)


def main():
    df = build_rows()
    df["score"] = df["text"].apply(score_text)

    # 1) time ko UTC me badlo, phir Hong Kong time me
    df["ts_utc"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts_utc"]).copy()
    hk = df["ts_utc"].dt.tz_convert("Asia/Hong_Kong")
    df["hk_date"] = hk.dt.normalize().dt.tz_localize(None)
    # market band hone ke baad aaya post agle din ka mana jayega
    after_close = hk.dt.hour >= MARKET_CLOSE_HOUR
    df.loc[after_close, "hk_date"] += pd.Timedelta(days=1)

    # 2) agle trading day se jodo (weekend/holiday ke liye forward)
    prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
    cal = pd.DataFrame({"trade_date": sorted(prices["date"].unique())})
    df = df.sort_values("hk_date")
    df = pd.merge_asof(
        df, cal, left_on="hk_date", right_on="trade_date", direction="forward"
    )
    df.to_csv("data/sentiment_items.csv", index=False)

    # 3) ticker + din + source ke hisaab se weighted average
    aligned = df.dropna(subset=["trade_date"]).copy()
    aligned["ws"] = aligned["score"] * aligned["weight"]
    g = (
        aligned.groupby(["ticker", "trade_date", "source"])
        .agg(ws=("ws", "sum"), w=("weight", "sum"), n=("score", "size"))
        .reset_index()
    )
    g["score"] = g["ws"] / g["w"]
    g[["ticker", "trade_date", "source", "score", "n"]].to_csv(
        "data/daily_sentiment.csv", index=False
    )

    print("Items scored:", len(df), "| aligned to a trading day:", len(aligned))
    print(df.groupby(["ticker", "source"])["score"].agg(["count", "mean"]).round(2))


if __name__ == "__main__":
    main()
