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

The default sentiment model is a lightweight heuristic stub; swap in a stronger model such as FinBERT by editing `sentiment_service/fastapi_sentiment.py`.

### Verify
- Health: `curl http://localhost:8000/health` → `{ "ok": true }`
- Score demo:
```bash
curl -X POST http://localhost:8000/score \
  -H 'Content-Type: application/json' \
  -d '{"texts":["stock up on strong guidance","coin plunges after hack"]}'
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
