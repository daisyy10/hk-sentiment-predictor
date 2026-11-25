import base64
import io
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # window kholne ki zaroorat nahi
import matplotlib.pyplot as plt
import pandas as pd

summary = pd.read_csv("data/ticker_summary.csv")
prices = pd.read_csv("data/prices.csv", parse_dates=["date"])

# mentions aur sentiment ke hisaab se sort
summary = summary.sort_values(
    ["social_mentions", "sentiment"], ascending=False
).reset_index(drop=True)
summary["label"] = summary["asset_name"] + " (" + summary["ticker"] + ")"


def to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def chart_mentions():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(summary["label"], summary["social_mentions"],
           label="Social (LIHKG)", color="#e4572e")
    ax.bar(summary["label"], summary["news_mentions"],
           bottom=summary["social_mentions"],
           label="News (Exa + AAStocks)", color="#4a6fa5")
    ax.set_ylabel("Mentions")
    ax.set_title("Mentions per stock (last 10 days)")
    ax.legend()
    plt.xticks(rotation=25, ha="right")
    return to_b64(fig)


def chart_sentiment():
    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(summary))
    w = 0.38
    ax.bar([i - w / 2 for i in x], summary["social_sentiment"].fillna(0),
           w, label="Social (LIHKG)", color="#e4572e")
    ax.bar([i + w / 2 for i in x], summary["news_sentiment"].fillna(0),
           w, label="News", color="#4a6fa5")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(summary["label"], rotation=25, ha="right")
    ax.set_ylabel("Sentiment (-1 to +1)")
    ax.set_title("Social vs news sentiment")
    ax.legend()
    return to_b64(fig)


def chart_prices():
    fig, axes = plt.subplots(2, 3, figsize=(12, 6))
    axes = axes.flatten()
    for ax, (_, row) in zip(axes, summary.iterrows()):
        p = prices[prices["ticker"] == row["ticker"]].tail(60)
        ax.plot(p["date"], p["close"], color="#222")
        ax.axhline(row["support"], color="green", linestyle="--", label="Support")
        ax.axhline(row["resistance"], color="red", linestyle="--", label="Resistance")
        ax.set_title(row["label"], fontsize=10)
        ax.tick_params(axis="x", rotation=30, labelsize=7)
    axes[0].legend(fontsize=7)
    for ax in axes[len(summary):]:
        ax.axis("off")
    fig.suptitle("Price (last 60 days) with support / resistance")
    fig.tight_layout()
    return to_b64(fig)


def table_html():
    rows = ""
    for i, r in summary.iterrows():
        flag = "DIVERGENCE" if r["divergence"] else ""
        rows += (
            f"<tr><td>{i + 1}</td><td>{r['asset_name']}</td><td>{r['ticker']}</td>"
            f"<td>{r['price']}</td><td>{r['change_pct']}%</td>"
            f"<td>{r['sentiment']}</td>"
            f"<td class='{r['direction']}'>{r['direction']}</td>"
            f"<td>{r['position']}</td><td>{r['confidence']}</td>"
            f"<td>{r['support']}</td><td>{r['resistance']}</td>"
            f"<td>{r['social_mentions']}</td><td>{r['news_mentions']}</td>"
            f"<td>{flag}</td></tr>"
        )
    return rows


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>HK Sentiment Report</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 30px auto; padding: 0 15px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border: 1px solid #ccc; padding: 6px; text-align: center; }}
th {{ background: #f0f0f0; }}
.BULLISH {{ background: #c8f2c8; }}
.BEARISH {{ background: #f5c6c6; }}
.NEUTRAL {{ background: #eee; }}
img {{ max-width: 100%; margin: 10px 0; }}
.note {{ font-size: 12px; color: #555; }}
</style></head><body>
<h1>Hong Kong (HKEX) Sentiment Report</h1>
<p class="note">Generated {now}. Sorted by social mentions, then sentiment.</p>
<table>
<tr><th>#</th><th>Asset</th><th>Ticker</th><th>Price</th><th>1d</th><th>Sentiment</th>
<th>Direction</th><th>Position</th><th>Confidence</th><th>Support</th><th>Resistance</th>
<th>Social</th><th>News</th><th>Flag</th></tr>
{table_html()}
</table>
<h2>Mentions</h2><img src="data:image/png;base64,{chart_mentions()}">
<h2>Sentiment</h2><img src="data:image/png;base64,{chart_sentiment()}">
<h2>Prices</h2><img src="data:image/png;base64,{chart_prices()}">
<p class="note">Educational project only, not financial advice. Small sample
(about 10 days of posts), so treat signals as indicative.</p>
</body></html>"""
    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved reports/report.html")


if __name__ == "__main__":
    main()