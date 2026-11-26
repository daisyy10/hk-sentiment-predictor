import os
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go

from report_extras import stock_cards, heatmap_html, evidence_html

summary = pd.read_csv("data/ticker_summary.csv")
prices = pd.read_csv("data/prices.csv", parse_dates=["date"])

summary = summary.sort_values(
    ["social_mentions", "sentiment"], ascending=False
).reset_index(drop=True)
summary["label"] = summary["asset_name"] + " (" + summary["ticker"] + ")"

BLUE, ORANGE = "#4a6fa5", "#e4572e"


def read_csv_safe(path):
    try:
        df = pd.read_csv(path)
        return df if len(df) else None
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None


def fig_html(fig, first=False):
    # plotly.js sirf pehle chart ke saath ek baar load hota hai
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if first else False,
        config={"displayModeBar": False},
    )


def chart_mentions():
    fig = go.Figure()
    fig.add_bar(x=summary["label"], y=summary["social_mentions"],
                name="Social (LIHKG)", marker_color=ORANGE)
    fig.add_bar(x=summary["label"], y=summary["news_mentions"],
                name="News (Exa + AAStocks)", marker_color=BLUE)
    fig.update_layout(barmode="stack", title="Mentions per stock (last 10 days)",
                      yaxis_title="Mentions", height=380,
                      margin=dict(t=60, b=40, l=50, r=20),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def chart_sentiment():
    fig = go.Figure()
    fig.add_bar(x=summary["label"], y=summary["social_sentiment"],
                name="Social (LIHKG)", marker_color=ORANGE)
    fig.add_bar(x=summary["label"], y=summary["news_sentiment"],
                name="News", marker_color=BLUE)
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(barmode="group", title="Social vs news sentiment",
                      yaxis=dict(title="Sentiment (-1 to +1)", range=[-1, 1]),
                      height=380, margin=dict(t=60, b=40, l=50, r=20),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def chart_prices():
    # har stock ke 4 traces: candles, 10-day avg, support, resistance
    fig = go.Figure()
    for i, (_, r) in enumerate(summary.iterrows()):
        p = prices[prices["ticker"] == r["ticker"]].sort_values("date").tail(90)
        sma = p["close"].rolling(10).mean()
        show = i == 0
        x_ends = [p["date"].iloc[0], p["date"].iloc[-1]]
        fig.add_trace(go.Candlestick(
            x=p["date"], open=p["open"], high=p["high"], low=p["low"],
            close=p["close"], name="Price", visible=show))
        fig.add_trace(go.Scatter(
            x=p["date"], y=sma, name="10-day avg", visible=show,
            line=dict(color="#8a5cf6", width=1.5)))
        fig.add_trace(go.Scatter(
            x=x_ends, y=[r["support"]] * 2, name="Support", visible=show,
            line=dict(color="green", dash="dash")))
        fig.add_trace(go.Scatter(
            x=x_ends, y=[r["resistance"]] * 2, name="Resistance", visible=show,
            line=dict(color="red", dash="dash")))

    n = len(summary)
    buttons = []
    for i, (_, r) in enumerate(summary.iterrows()):
        vis = [False] * (4 * n)
        for k in range(4):
            vis[4 * i + k] = True
        buttons.append(dict(
            label=r["label"], method="update",
            args=[{"visible": vis}, {"title": f"{r['label']} - last 90 days"}]))

    fig.update_layout(
        title=f"{summary['label'].iloc[0]} - last 90 days",
        updatemenus=[dict(buttons=buttons, direction="down",
                          x=0, y=1.22, xanchor="left")],
        xaxis_rangeslider_visible=False, height=480,
        margin=dict(t=90, b=40, l=50, r=20),
        legend=dict(orientation="h", y=-0.15))
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def fmt(v, nd=2):
    return "-" if pd.isna(v) else f"{v:.{nd}f}"


def td(display, value, cls=""):
    return f'<td class="{cls}" data-v="{value}">{display}</td>'


def table_html():
    head = ["#", "Asset", "Ticker", "Price", "1d %", "Sentiment", "Social",
            "News", "Direction", "Position", "Confidence", "Support",
            "Resistance", "Social posts", "News items", "Flag"]
    th = "".join(f'<th onclick="sortTable({i})">{h}</th>'
                 for i, h in enumerate(head))
    rows = ""
    for i, r in summary.iterrows():
        flag = "DIVERGENCE" if r["divergence"] else ""
        cells = [
            td(i + 1, i + 1),
            td(r["asset_name"], r["asset_name"]),
            td(r["ticker"], r["ticker"]),
            td(fmt(r["price"]), r["price"]),
            td(fmt(r["change_pct"]), r["change_pct"]),
            td(fmt(r["sentiment"]), r["sentiment"]),
            td(fmt(r["social_sentiment"]), r["social_sentiment"]),
            td(fmt(r["news_sentiment"]), r["news_sentiment"]),
            td(r["direction"], r["direction"], r["direction"]),
            td(r["position"], r["position"]),
            td(r["confidence"], r["confidence"]),
            td(fmt(r["support"]), r["support"]),
            td(fmt(r["resistance"]), r["resistance"]),
            td(r["social_mentions"], r["social_mentions"]),
            td(r["news_mentions"], r["news_mentions"]),
            td(flag, flag, "flag" if flag else ""),
        ]
        rows += f'<tr data-dir="{r["direction"]}">{"".join(cells)}</tr>'
    return f'<table id="t"><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table>'


def cards_html():
    bull = summary.sort_values("sentiment", ascending=False).iloc[0]
    talk = summary.sort_values("social_mentions", ascending=False).iloc[0]
    n_div = int(summary["divergence"].sum())
    n_pos = int(summary["position"].isin(["LONG", "SHORT"]).sum())
    items = [
        ("Most bullish", f"{bull['asset_name']} ({bull['sentiment']:+.2f})"),
        ("Most discussed on LIHKG",
         f"{talk['asset_name']} ({int(talk['social_mentions'])} posts)"),
        ("Social vs news divergence", f"{n_div} stock(s)"),
        ("Active positions", f"{n_pos} of {len(summary)}"),
    ]
    return "".join(f'<div class="card"><span>{a}</span><b>{b}</b></div>'
                   for a, b in items)


def df_html(df):
    return df.to_html(index=False, border=0, classes="plain")


def extra_sections():
    out = ""
    pred = read_csv_safe("reports/predictions.csv")
    if pred is not None:
        out += "<h2>Next-day (n+1) prediction</h2>" + df_html(pred)
    check = read_csv_safe("reports/prediction_check.csv")
    if check is not None:
        out += "<h2>Prediction vs actual</h2>" + df_html(check)
    bt = read_csv_safe("reports/backtest_metrics.csv")
    if bt is not None:
        out += ("<h2>Walk-forward test (out-of-sample)</h2>" + df_html(bt)
                + '<p class="note">Lower MAPE is better. Beating the naive row '
                  'means the model adds value.</p>')
    return out


TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HK Sentiment Report</title>
<style>
body { font-family: Arial, sans-serif; max-width: 1100px; margin: 30px auto; padding: 0 15px; color: #222; }
h1 { margin-bottom: 4px; }
.note { font-size: 12px; color: #666; }
.cards { display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }
.card { flex: 1; min-width: 200px; background: #f5f7fa; border-radius: 8px; padding: 12px 14px; }
.card span { display: block; font-size: 12px; color: #666; }
.card b { font-size: 16px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 6px; text-align: center; }
th { background: #f0f0f0; cursor: pointer; user-select: none; }
th:hover { background: #e2e6ea; }
table.plain th { cursor: default; }
.BULLISH { background: #c8f2c8; } .BEARISH { background: #f5c6c6; } .NEUTRAL { background: #eee; }
.flag { background: #ffe9a8; font-weight: bold; }
.btn { border: 1px solid #aaa; background: #fff; padding: 5px 12px; margin-right: 6px; border-radius: 16px; cursor: pointer; }
.btn.on { background: #222; color: #fff; }
body.dark { background: #12161c; color: #e6e9ee; }
body.dark .note, body.dark .sub, body.dark .card span, body.dark .rng-l { color: #9aa4b2; }
body.dark .card { background: #1c222b; }
body.dark .sc { background: #1c222b; border-color: #2b323d; box-shadow: none; }
body.dark th { background: #262d38; color: #e6e9ee; }
body.dark th:hover { background: #303846; }
body.dark th, body.dark td { border-color: #2f3743; }
body.dark .BULLISH { background: #1d5a35; }
body.dark .BEARISH { background: #6b2a2a; }
body.dark .NEUTRAL { background: #333b46; }
body.dark .flag { background: #7a5a00; }
body.dark .btn { background: #1c222b; color: #e6e9ee; border-color: #444; }
body.dark .btn.on { background: #e6e9ee; color: #12161c; }
body.dark details.ev { border-color: #2f3743; }
body.dark .src { background: #2b323d; color: #cdd3dc; }
body.dark .tag.dark { background: #e6e9ee; color: #12161c; }
body.dark .rng-bar { background: linear-gradient(90deg, #1d5a35, #333b46, #6b2a2a); }
body.dark .rng-bar i { background: #e6e9ee; border-color: #1c222b; }
#themeBtn { position: fixed; top: 12px; right: 14px; z-index: 10; border: 1px solid #aaa; background: #fff; color: #222; padding: 6px 12px; border-radius: 18px; cursor: pointer; }
body.dark #themeBtn { background: #1c222b; color: #e6e9ee; border-color: #555; }
</style></head><body>
<button id="themeBtn" onclick="toggleTheme()">Dark mode</button>
<h1>Hong Kong (HKEX) Sentiment Report</h1>
<p class="note">Generated __NOW__. Click a column header to sort. Educational project, not financial advice.</p>
<div class="cards">__CARDS__</div>
<h2>Ranked table</h2>
<p>Filter:
<button class="btn on" data-d="ALL" onclick="filterDir('ALL')">All</button>
<button class="btn" data-d="BULLISH" onclick="filterDir('BULLISH')">Bullish</button>
<button class="btn" data-d="BEARISH" onclick="filterDir('BEARISH')">Bearish</button>
<button class="btn" data-d="NEUTRAL" onclick="filterDir('NEUTRAL')">Neutral</button></p>
__TABLE__
<h2>Mentions</h2>__MENTIONS__
<h2>Sentiment</h2>__SENTIMENT__
<h2>Price explorer</h2>
<p class="note">Pick a stock from the dropdown. Green = support, red = resistance (last 20 days).</p>
__PRICES__
__EXTRA__
<p class="note">Small sample (about 10 days of posts), so treat signals as indicative.</p>
<script>
var asc = {};
function sortTable(col) {
  var tbody = document.querySelector("#t tbody");
  var rows = Array.from(tbody.rows);
  asc[col] = !asc[col];
  rows.sort(function (a, b) {
    var x = a.cells[col].dataset.v, y = b.cells[col].dataset.v;
    var nx = parseFloat(x), ny = parseFloat(y);
    var cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
    return asc[col] ? cmp : -cmp;
  });
  rows.forEach(function (r) { tbody.appendChild(r); });
}
function filterDir(d) {
  document.querySelectorAll("#t tbody tr").forEach(function (r) {
    r.style.display = (d === "ALL" || r.dataset.dir === d) ? "" : "none";
  });
  document.querySelectorAll(".btn").forEach(function (b) {
    b.classList.toggle("on", b.dataset.d === d);
  });
}
</script>
<script>
function applyTheme(dark) {
  document.body.classList.toggle("dark", dark);
  document.getElementById("themeBtn").textContent = dark ? "Light mode" : "Dark mode";
  var font = dark ? "#e6e9ee" : "#222";
  var grid = dark ? "#2f3743" : "#e3e6ea";
  document.querySelectorAll(".plotly-graph-div").forEach(function (g) {
    try {
      Plotly.relayout(g, {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        "font.color": font,
        "xaxis.gridcolor": grid,
        "yaxis.gridcolor": grid
      });
    } catch (e) {}
  });
}
function toggleTheme() {
  var dark = !document.body.classList.contains("dark");
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) {}
  applyTheme(dark);
}
window.addEventListener("load", function () {
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  var dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(dark);
});
</script>
</body></html>"""


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = (TEMPLATE
            .replace("__NOW__", now)
            .replace("__CARDS__", cards_html())
                        .replace("__TABLE__", stock_cards() + "<h2>Ranked table</h2>" + table_html())
            .replace("__MENTIONS__", fig_html(chart_mentions(), first=True))
            .replace("__SENTIMENT__", fig_html(chart_sentiment()))
            .replace("__PRICES__", fig_html(chart_prices()))
                        .replace("__EXTRA__", heatmap_html() + evidence_html() + extra_sections()))
    with open("reports/report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved reports/report.html")


if __name__ == "__main__":
    main()