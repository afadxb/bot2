# trading-mood-bot

Production-ready sentiment layer + helpers for a swing-trading bot (crypto & stocks). Combines **technical signals** with an **AI market mood score** derived from **News + Stocktwits** (default) or **News + Reddit** (optional). Includes:

- FastAPI scoring service
- Ingestion workers (news, stocktwits)
- Fusion worker → per-symbol `MoodScore` (0..100)
- MySQL schema & Docker Compose
- Bot integration helpers (entry gating, %-equity sizing multiplier, optional trailing tweaks)

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
- Default model is a lightweight heuristic stub; replace with FinBERT (see comments in `fastapi_sentiment.py`).
- Use shadow mode first: log `mood_score` impact without changing trading decisions.
