import pandas as pd
import yfinance as yf

pred = pd.read_csv("reports/predictions.csv")
rows = []
for _, r in pred.iterrows():
    h = yf.Ticker(r["ticker"]).history(period="10d").reset_index()
    h["Date"] = pd.to_datetime(h["Date"]).dt.date.astype(str)
    later = h[h["Date"] > r["as_of_date"]]
    if later.empty:
        print(r["ticker"], "- next day price not available yet")
        continue
    actual = later["Close"].iloc[0]
    actual_chg = (actual / r["last_close"] - 1) * 100
    rows.append(
        {
            "ticker": r["ticker"],
            "last_close": r["last_close"],
            "predicted": r["pred_close_next_day"],
            "actual": round(actual, 2),
            "error_%": round(abs(r["pred_close_next_day"] - actual) / actual * 100, 2),
            "direction_correct": (r["pred_change_pct"] > 0) == (actual_chg > 0),
        }
    )

res = pd.DataFrame(rows)
print(res.to_string(index=False))
res.to_csv("reports/prediction_check.csv", index=False)
