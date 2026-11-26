import pandas as pd

BULL, BEAR = 0.15, -0.15
LOOKBACK = 20  # support/resistance ke liye din
SMA_DAYS = 10  # trend ke liye average


def weighted_mean(df):
    if df.empty:
        return None
    return (df["score"] * df["weight"]).sum() / df["weight"].sum()


def get_direction(score):
    if score > BULL:
        return "BULLISH"
    if score < BEAR:
        return "BEARISH"
    return "NEUTRAL"


def get_confidence(n_items, score):
    if n_items >= 15 and abs(score) >= 0.3:
        return "HIGH"
    if n_items >= 8:
        return "MEDIUM"
    return "LOW"


def main():
    items = pd.read_csv("data/sentiment_items.csv")
    prices = pd.read_csv("data/prices.csv", parse_dates=["date"])

    rows = []
    for ticker, p in prices.groupby("ticker"):
        p = p.sort_values("date")
        close = p["close"].iloc[-1]
        prev = p["close"].iloc[-2]

        recent = p.tail(LOOKBACK)
        support = recent["low"].min()
        resistance = recent["high"].max()
        trend_up = close > p["close"].tail(SMA_DAYS).mean()

        it = items[items["ticker"] == ticker]
        social = it[it["source"] == "lihkg"]
        news = it[it["source"] != "lihkg"]
        s_social = weighted_mean(social)
        s_news = weighted_mean(news)

        parts = [s for s in (s_social, s_news) if s is not None]
        overall = sum(parts) / len(parts) if parts else 0.0
        direction = get_direction(overall)

        if direction == "BULLISH" and trend_up:
            position = "LONG"
        elif direction == "BEARISH" and not trend_up:
            position = "SHORT"
        else:
            position = "FLAT"

        divergence = (
            s_social is not None
            and s_news is not None
            and s_social * s_news < 0
            and abs(s_social - s_news) >= 0.4
        )

        rows.append(
            {
                "ticker": ticker,
                "asset_name": p["asset_name"].iloc[0],
                "price": round(close, 2),
                "change_pct": round((close / prev - 1) * 100, 2),
                "sentiment": round(overall, 2),
                "social_sentiment": None if s_social is None else round(s_social, 2),
                "news_sentiment": None if s_news is None else round(s_news, 2),
                "direction": direction,
                "position": position,
                "confidence": get_confidence(len(it), overall),
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "to_support_pct": round((close / support - 1) * 100, 1),
                "to_resistance_pct": round((resistance / close - 1) * 100, 1),
                "social_mentions": len(social),
                "news_mentions": len(news),
                "divergence": divergence,
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(["social_mentions", "sentiment"], ascending=False)
    out.to_csv("data/ticker_summary.csv", index=False)

    cols = [
        "ticker",
        "price",
        "sentiment",
        "direction",
        "position",
        "support",
        "resistance",
        "social_mentions",
        "divergence",
    ]
    print(out[cols].to_string(index=False))


if __name__ == "__main__":
    main()
