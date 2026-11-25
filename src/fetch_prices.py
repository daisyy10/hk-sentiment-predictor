import pandas as pd
import yfinance as yf

STOCKS = {
    "0700.HK": "Tencent",
    "9988.HK": "Alibaba",
    "1810.HK": "Xiaomi",
    "3690.HK": "Meituan",
    "0005.HK": "HSBC",
}


def fetch_prices(ticker, name):
    # 6 mahine ka daily price (open, high, low, close, volume)
    df = yf.Ticker(ticker).history(period="6mo")
    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    df["ticker"] = ticker
    df["asset_name"] = name
    return df[["date", "ticker", "asset_name", "open", "high", "low", "close", "volume"]]


def main():
    frames = []
    for ticker, name in STOCKS.items():
        print("Fetching prices for", ticker)
        df = fetch_prices(ticker, name)
        print("  got", len(df), "days, latest close:", round(df["close"].iloc[-1], 2))
        frames.append(df)

    prices = pd.concat(frames, ignore_index=True)
    prices.to_csv("data/prices.csv", index=False)
    print("Saved", len(prices), "rows to data/prices.csv")


if __name__ == "__main__":
    main()