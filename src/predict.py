import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TEST_DAYS = 30  # out-of-sample test ke din
PRICE_FEATS = ["ret_1", "ret_5", "gap_sma10", "vol_5"]
SENT_FEATS = ["social_sent", "news_sent"]


def build_features():
    prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
    sent = pd.read_csv("data/daily_sentiment.csv", parse_dates=["trade_date"])

    social = (sent[sent["source"] == "lihkg"]
              .groupby(["ticker", "trade_date"])["score"].mean()
              .rename("social_sent").reset_index()
              .rename(columns={"trade_date": "date"}))
    news = (sent[sent["source"] != "lihkg"]
            .groupby(["ticker", "trade_date"])["score"].mean()
            .rename("news_sent").reset_index()
            .rename(columns={"trade_date": "date"}))

    frames = []
    for ticker, p in prices.groupby("ticker"):
        p = p.sort_values("date").copy()
        p["ret_1"] = p["close"].pct_change()
        p["ret_5"] = p["close"].pct_change(5)
        p["gap_sma10"] = p["close"] / p["close"].rolling(10).mean() - 1
        p["vol_5"] = p["ret_1"].rolling(5).std()
        # target: kal ka return (aakhri row ka NaN, kyunki kal abhi aaya nahi)
        p["target"] = p["close"].shift(-1) / p["close"] - 1
        frames.append(p)
    df = pd.concat(frames, ignore_index=True)

    df = df.merge(social, on=["ticker", "date"], how="left")
    df = df.merge(news, on=["ticker", "date"], how="left")
    df[SENT_FEATS] = df[SENT_FEATS].fillna(0.0)  # sentiment nahi mila = neutral
    return df


def make_model():
    return make_pipeline(StandardScaler(), Ridge(alpha=10.0))


def walk_forward(df, feats, test_dates):
    preds = {}
    for d in test_dates:
        # sirf d se pehle ka data, taaki future leak na ho
        train = df[df["date"] < d]
        test = df[df["date"] == d]
        model = make_model().fit(train[feats], train["target"])
        for idx, val in zip(test.index, model.predict(test[feats])):
            preds[idx] = val
    return pd.Series(preds)


def evaluate(test, pred_ret, name):
    actual_price = test["close"] * (1 + test["target"])
    pred_price = test["close"] * (1 + pred_ret)
    mape = (abs(pred_price - actual_price) / actual_price).mean() * 100
    if (pred_ret == 0).all():
        dir_acc = None  # naive ke paas koi direction nahi hoti
    else:
        dir_acc = (np.sign(pred_ret) == np.sign(test["target"])).mean() * 100
    return {"model": name, "MAPE_%": round(mape, 3),
            "direction_acc_%": None if dir_acc is None else round(dir_acc, 1)}


def main():
    df = build_features()
    labelled = df.dropna(subset=PRICE_FEATS + ["target"]).copy()
    test_dates = sorted(labelled["date"].unique())[-TEST_DAYS:]
    test = labelled[labelled["date"].isin(test_dates)].copy()

    all_feats = PRICE_FEATS + SENT_FEATS
    pred_price_only = walk_forward(labelled, PRICE_FEATS, test_dates).loc[test.index]
    pred_with_sent = walk_forward(labelled, all_feats, test_dates).loc[test.index]

    results = [
        evaluate(test, pd.Series(0.0, index=test.index), "Naive (tomorrow = today)"),
        evaluate(test, pred_price_only, "Ridge, price only"),
        evaluate(test, pred_with_sent, "Ridge, price + sentiment"),
    ]
    res = pd.DataFrame(results)
    res.to_csv("reports/backtest_metrics.csv", index=False)

    print(f"Out-of-sample test: last {TEST_DAYS} trading days, "
          f"{len(test)} predictions (5 stocks pooled)")
    print(res.to_string(index=False))
    print("Always-up baseline direction acc:",
          round((test["target"] > 0).mean() * 100, 1), "%")

    has_sent = (test[SENT_FEATS] != 0).any(axis=1)
    print(f"Test rows that actually had sentiment: {has_sent.sum()} of {len(test)}")

    # final model poore data pe train karke kal (n+1) ka price predict
    final = make_model().fit(labelled[all_feats], labelled["target"])
    latest = df.sort_values("date").groupby("ticker").tail(1).copy()
    latest["pred_change_pct"] = final.predict(latest[all_feats]) * 100
    latest["pred_close_next_day"] = latest["close"] * (1 + latest["pred_change_pct"] / 100)
    out = latest[["ticker", "asset_name", "date", "close",
                                    "pred_close_next_day", "pred_change_pct"]]
    for c in ["last_close", "pred_close_next_day", "pred_change_pct"]:
        out[c] = out[c].round(2)
    out = out.rename(columns={"date": "as_of_date", "close": "last_close"})
    out.to_csv("reports/predictions.csv", index=False)
    print("\nPrediction for next trading day (n+1):")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()