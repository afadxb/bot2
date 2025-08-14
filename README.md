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
- Database credentials for the MySQL instance

After configuring `.env`, build and run the stack.

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
