import html
import pandas as pd
import plotly.graph_objects as go

summary = pd.read_csv("data/ticker_summary.csv")
prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
items = pd.read_csv("data/sentiment_items.csv")
daily = pd.read_csv("data/daily_sentiment.csv")

summary = summary.sort_values(
    ["social_mentions", "sentiment"], ascending=False
).reset_index(drop=True)

COLORS = {"BULLISH": "#1b9e4b", "BEARISH": "#d64545", "NEUTRAL": "#888888"}

CSS = """<style>
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 14px 0 22px; }
.sc { background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.sc-top { display: flex; justify-content: space-between; align-items: center; }
.sub { font-size: 11px; color: #777; margin-top: 2px; }
.price { font-size: 20px; font-weight: bold; margin: 8px 0 6px; }
.up { color: #1b9e4b; font-size: 13px; } .down { color: #d64545; font-size: 13px; }
.tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.tag { color: #fff; background: #999; font-size: 10px; padding: 2px 7px; border-radius: 10px; }
.tag.dark { background: #222; } .tag.warn { background: #e0a100; }
.rng-bar { position: relative; height: 6px; background: linear-gradient(90deg, #bfe8c9, #f3f3f3, #f5c6c6); border-radius: 3px; margin-top: 4px; }
.rng-bar i { position: absolute; top: -3px; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; background: #222; border: 2px solid #fff; }
.rng-l { display: flex; justify-content: space-between; font-size: 10px; color: #666; margin: 4px 0 8px; }
details.ev { border: 1px solid #e3e6ea; border-radius: 8px; padding: 8px 12px; margin: 8px 0; }
details.ev summary { cursor: pointer; }
details.ev ul { list-style: none; padding-left: 0; font-size: 13px; }
details.ev li { margin: 8px 0; line-height: 1.5; }
.src { font-size: 10px; color: #555; background: #eee; padding: 1px 6px; border-radius: 8px; margin-right: 4px; }
</style>"""


def sparkline(values, w=110, h=34):
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pts = " ".join(
        f"{i * w / (len(values) - 1):.1f},{h - (v - lo) / span * h:.1f}"
        for i, v in enumerate(values)
    )
    color = "#1b9e4b" if values[-1] >= values[0] else "#d64545"
    return (f'<svg width="{w}" height="{h}"><polyline fill="none" '
            f'stroke="{color}" stroke-width="2" points="{pts}"/></svg>')


def stock_cards():
    cards = ""
    for _, r in summary.iterrows():
        p = prices[prices["ticker"] == r["ticker"]].sort_values("date").tail(30)
        spark = sparkline(list(p["close"]))
        span = (r["resistance"] - r["support"]) or 1
        pos = min(max((r["price"] - r["support"]) / span * 100, 0), 100)
        color = COLORS.get(r["direction"], "#888")
        chg = r["change_pct"]
        chg_cls = "up" if chg >= 0 else "down"
        flag = '<span class="tag warn">DIVERGENCE</span>' if r["divergence"] else ""
        cards += f"""
<div class="sc" style="border-top:4px solid {color}">
  <div class="sc-top"><div><b>{html.escape(r['asset_name'])}</b>
  <div class="sub">{r['ticker']}</div></div>{spark}</div>
  <div class="price">{r['price']:.2f} <span class="{chg_cls}">{chg:+.2f}%</span></div>
  <div class="tags"><span class="tag" style="background:{color}">{r['direction']}</span>
  <span class="tag dark">{r['position']}</span>
  <span class="tag">{r['confidence']} conf.</span>{flag}</div>
  <div class="rng-bar"><i style="left:{pos:.0f}%"></i></div>
  <div class="rng-l"><span>S {r['support']}</span><span>R {r['resistance']}</span></div>
  <div class="sub">Sentiment {r['sentiment']:+.2f} | {int(r['social_mentions'])} posts | {int(r['news_mentions'])} news</div>
</div>"""
    return CSS + f'<div class="grid">{cards}</div>'


def heatmap_html():
    d = daily.groupby(["ticker", "trade_date"])["score"].mean().reset_index()
    pv = d.pivot(index="ticker", columns="trade_date", values="score")
    pv = pv.reindex(summary["ticker"])
    names = dict(zip(summary["ticker"], summary["asset_name"]))
    fig = go.Figure(go.Heatmap(
        z=pv.values,
        x=[str(c)[:10] for c in pv.columns],
        y=[names[t] for t in pv.index],
        colorscale="RdYlGn", zmin=-1, zmax=1,
        colorbar=dict(title="Sentiment"),
        hovertemplate="%{y}<br>%{x}<br>score %{z:.2f}<extra></extra>",
    ))
    fig.update_xaxes(type="category")
    fig.update_layout(title="Daily sentiment heatmap (social + news)",
                      height=320, margin=dict(t=60, b=40, l=80, r=20))
    return ("<h2>Sentiment heatmap</h2>"
            + fig.to_html(full_html=False, include_plotlyjs=False,
                          config={"displayModeBar": False})
            + '<p class="note">Blank cell = no posts or news that day.</p>')


def evidence_html():
    it_all = items.copy()
    it_all["text"] = it_all["text"].fillna("").astype(str)
    it_all["impact"] = it_all["score"].abs() * it_all["weight"]
    out = ('<h2>Evidence behind the scores</h2>'
           '<p class="note">Strongest items per stock. Click a stock to expand.</p>')
    for _, r in summary.iterrows():
        it = it_all[(it_all["ticker"] == r["ticker"])
                    & (it_all["text"].str.strip() != "")]
        it = it.sort_values("impact", ascending=False).head(6)
        rows = ""
        for _, x in it.iterrows():
            s = x["score"]
            col = "#1b9e4b" if s > 0.15 else "#d64545" if s < -0.15 else "#888"
            snippet = html.escape(x["text"].strip().replace("\n", " ")[:160])
            rows += (f'<li><span class="tag" style="background:{col}">{s:+.2f}</span> '
                     f'<span class="src">{x["source"]}</span>{snippet}</li>')
        out += (f'<details class="ev"><summary><b>{html.escape(r["asset_name"])}</b> '
                f'({r["ticker"]}) - top {len(it)} items</summary><ul>{rows}</ul></details>')
    return out