# HK Sentiment Price Predictor

A small pipeline that collects social and news sentiment for 5 Hong Kong (HKEX) stocks, aligns it with daily prices, builds a report, and predicts the next trading day's price (n+1).

Stocks: Tencent (0700.HK), Alibaba (9988.HK), Xiaomi (1810.HK), Meituan (3690.HK), HSBC (0005.HK).

Built for the CrowdWisdomTrading intern assessment by Daisy.

## Data sources

| Source | Tool | Actor / API | What I used it for |
|---|---|---|---|
| LIHKG (social forum) | Apify | `claude_code_reviewer/lihkg-scraper-en` (search mode) | Posts from the last 10 days, likes, replies |
| AAStocks (HK financial portal) | Apify | `bovi/aastocks-scraper` | News headlines (no timestamp provided) |
| News | Exa | `exa.search` (news category) | 10 recent articles per stock |
| Prices | yfinance | free | 6 months of daily OHLCV |

## How it works

1. `src/scrape_lihkg.py` - searches LIHKG by Chinese company name and ticker number (retry and per-stock caching, because LIHKG rate-limited me).
2. `src/fetch_news.py` - Exa news from the last 10 days.
3. `src/scrape_aastocks.py` - headlines from 4 AAStocks feeds in Chinese and English, filtered by company name.
4. `src/fetch_prices.py` - daily prices from yfinance.
5. `src/sentiment.py` - scores each item from -1 to +1 (keyword score for Chinese, VADER for English), converts time to UTC, then to HK time, and attaches each item to a trading day. Anything after the 16:00 HKT close counts for the next trading day, so no future information leaks into a day.
6. `src/summary.py` - one row per ticker: price, sentiment, direction, position, support/resistance.
7. `src/report.py` - HTML report, sorted by social mentions then sentiment (`reports/report.html`).
8. `src/predict.py` - Ridge regression for next-day return, tested with walk-forward validation.
9. `src/check_prediction.py` - compares the prediction with the actual close.

Rules used in the summary:
- Direction: BULLISH above +0.15, BEARISH below -0.15, else NEUTRAL.
- Support / resistance: lowest low / highest high of the last 20 trading days.
- Position: LONG only if sentiment is bullish and price is above its 10-day average (SHORT is the mirror). Otherwise FLAT.
- Engagement weight: likes and replies give a post more weight (follower counts are not available).
- Divergence flag: shown when social and news sentiment point in opposite directions.

## Results

Walk-forward test on the last 30 trading days (150 predictions, 5 stocks pooled). Each day the model is trained only on earlier days.

| Model | MAPE | Direction accuracy |
|---|---|---|
| Naive (tomorrow = today) | 2.138% | - |
| Ridge, price only | 2.157% | 49.3% |
| Ridge, price + sentiment | 2.174% | 50.0% |

Neither model beat the naive baseline. Only 10 of the 150 test rows had any sentiment, so this test cannot say whether sentiment helps. I am reporting it as it is.

Next-day check (26 Nov 2026, 5 stocks): average error was 1.55% for the model against 0.99% for the naive baseline (tomorrow = today). The model called the direction correctly for 1 of 5 stocks. It predicted a fall for all five, but four of them rose. Five predictions are too few to conclude anything, and the result agrees with the walk-forward test, where the model did not beat the baseline either. 
Details: `reports/prediction_check.csv`.

## Limitations

- Only Hong Kong is covered, not Korea.
- LIHKG gave few posts (24 in total) because of rate limits and low volume for these names.
- The LIHKG actor does not return views, reposts or author follower counts, so I used likes, dislikes and replies instead.
- The AAStocks actor returns only headlines with no timestamp, so I used the scrape time for them.
- Chinese sentiment is a simple keyword list, so sarcasm and slang are missed.
- Sentiment covers about 10 days, prices cover 6 months, so the sentiment feature is zero for most training rows.
- Not financial advice.

## What I would do with more time

- More social sources (Futu / Moomoo, Telegram) and a longer history.
- A proper Chinese or multilingual sentiment model.
- Test on more days, and compare against more baselines.

## Run it yourself

```bash
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env              # then add your own APIFY_TOKEN and EXA_API_KEY
python src/scrape_lihkg.py
python src/fetch_news.py
python src/scrape_aastocks.py
python src/fetch_prices.py
python src/sentiment.py
python src/summary.py
python src/report.py
python src/predict.py
python src/check_prediction.py
```

Apify actors are pay-per-event; a full run cost about $1 of the free credit.