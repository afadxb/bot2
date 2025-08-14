# trading-mood-bot

Production-ready sentiment layer + helpers for a swing-trading bot (crypto & stocks). Combines **technical signals** with an **AI market mood score** derived from **News + Stocktwits** (default) or **News + Reddit** (optional).

## Architecture

The system is composed of three core pieces:

- **FastAPI scoring service** – scores arbitrary text and exposes the `/score` and `/health` endpoints.
- **Ingestion workers** – collect news and social data (Stocktwits by default, Reddit optional).
- **Fusion worker** – aggregates raw snippets into a per-symbol `MoodScore` from 0 to 100.
- **MySQL database** – stores both the raw snippets and aggregated scores.
- **Bot integration helpers** – utilities that allow a trading bot to gate entries or size positions based on the mood score.

### Project layout

```
bot_integration/   Helpers for integrating the mood score into your trading bot
db/                MySQL schema and Docker Compose configuration
sentiment_service/ FastAPI app that exposes the sentiment scoring API
workers/           Ingestors and fuser that populate the database
tests/             Pytest test suite
```

## Configuration

Copy the example environment file and adjust it for your setup:

```bash
cp .env.example .env
```

Key variables:

- `WATCHLIST` – comma separated symbols to monitor
- `SOURCES` – feeds to enable (`news,stocktwits` by default, add `reddit` if desired)
- `NEWS_FEEDS` – comma separated RSS URLs for the news worker
- Database credentials for the MySQL instance

After configuring `.env`, build and run the stack.

### Rate limits & backoff

| Source     | Limit (free tier)                | Backoff / retry policy |
|------------|---------------------------------|------------------------|
| Stocktwits | ~200 requests/hour per IP       | Polls each symbol every `STOCKTWITS_POLL_SEC` (120s default). If a call fails (non‑200 or network error) the worker logs it and waits until the next poll before trying again. |
| Reddit     | ~60 requests/min per OAuth token | Optional Reddit worker relies on PRAW's built‑in rate limiter. It sleeps for the API‑specified delay (via headers/429s) and then retries. |

### Stocktwits symbol mapping

Crypto pairs ending with `USD` map to Stocktwits `.X` symbols (`BTCUSD` → `BTC.X`, `ETHUSD` → `ETH.X`). Equity tickers are passed through unchanged (`TSLA` → `TSLA`). Ensure your `WATCHLIST` uses these conventions to avoid empty feeds.

### News feeds

Set `NEWS_FEEDS` to a comma‑separated list of RSS URLs. Suggested defaults:

- https://feeds.reuters.com/reuters/businessNews
- https://finance.yahoo.com/news/rss
- https://www.coindesk.com/arc/outboundfeeds/rss/?output=xml
- https://cointelegraph.com/rss

Example:

```env
NEWS_FEEDS="https://feeds.reuters.com/reuters/businessNews,https://finance.yahoo.com/news/rss,https://www.coindesk.com/arc/outboundfeeds/rss/?output=xml,https://cointelegraph.com/rss"
```

Regional variants exist for Reuters/Yahoo (e.g., world, US, EU editions). You can also add per‑ticker feeds for equities such as `https://finance.yahoo.com/rss/headline?s=TSLA`.

### Alerts (Pushover)

Set up push notifications to catch issues early:

- **Freshness breach** – no crypto updates for >2m or equities for >5m
- **Ingestion error_rate** – >5% failures over a 10m window
- **Cache hit ratio** – drops below 60%
- **Database errors** – connection or query failures
- **Model fallback** – heuristic model used for >10% of scoring requests

### Dashboards

Recommended views for ongoing monitoring:

- **System health** – worker/API uptime and latency
- **Per-symbol sentiment time-series** – track mood per asset
- **Component contributions** – news vs. social vs. regime adjustments
- **Regime over time** – visualise how the adjustment factor shifts

## Quickstart

```bash
cp .env.example .env
# edit .env to set WATCHLIST, DB creds, feeds, etc.
docker-compose up --build
```

Services:
- **db**: MySQL 8
- **sentiment**: FastAPI scoring (CPU-only by default)
- **worker**: ingestors (news + stocktwits) + fuser (runs continuously)

## Development

Run the test suite to ensure everything is functioning:

```bash
pytest
```

The default sentiment model uses the [FinBERT](https://huggingface.co/ProsusAI/finbert) transformer fine-tuned for financial text.
If the model isn't available at runtime, the service falls back to a lightweight heuristic stub.

### Verify
- Health: `curl http://localhost:8000/health` → `{ "ok": true }`
- Score demo:
```bash
curl -X POST http://localhost:8000/score \
  -H 'Content-Type: application/json' \
  -d '{"texts":["stock up on strong guidance","coin plunges after hack"]}'
```

Fetch fused sentiment without touching MySQL:

```bash
# Per-symbol latest
curl http://localhost:8000/sentiment?symbol=BTCUSD
curl http://localhost:8000/sentiment?symbol=DOGEUSD
curl http://localhost:8000/sentiment?symbol=TSLA

# Batch latest for all symbols
curl http://localhost:8000/latest
```

`/sentiment` returns:

```json
{
  "symbol": "BTCUSD",
  "ts": "2024-01-01T00:00:00",
  "news_score": 70.2,
  "social_score": 64.1,
  "mood_score": 67.5,
  "regime_adj": 1.0
}
```

`/latest` returns:

```json
{
  "results": [
    {"symbol": "BTCUSD", "mood_score": 67.5, "news_score": 70.2, "social_score": 64.1, "regime_adj": 1.0, "ts": "2024-01-01T00:00:00"},
    {"symbol": "DOGEUSD", "mood_score": 42.1, "news_score": 40.0, "social_score": 43.2, "regime_adj": 1.0, "ts": "2024-01-01T00:00:00"},
    {"symbol": "TSLA", "mood_score": 55.0, "news_score": 60.0, "social_score": 50.0, "regime_adj": 1.0, "ts": "2024-01-01T00:00:00"}
  ]
}
```

### Output Tables
- `sentiment_raw`: raw scored snippets
- `sentiment_agg`: fused per-symbol scores with regime adjustment

### Bot Integration
Read the latest mood for a symbol and gate entries / size:
```sql
SELECT mood_score
FROM sentiment_agg
WHERE symbol = 'BTCUSD'
ORDER BY ts DESC LIMIT 1;
```
Use helpers in `bot_integration/`.

### Switch to Reddit
Set `SOURCES=news,reddit` and fill Reddit creds in `.env`. (Reddit worker can be added similarly.)

## Notes
- Use shadow mode first: log `mood_score` impact without changing trading decisions.
