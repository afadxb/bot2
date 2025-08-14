from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Callable, List
import numpy as np
import logging
import os

try:  # optional dependency; endpoints handle absence gracefully
    import MySQLdb as mdb
except Exception:  # pragma: no cover - missing driver
    mdb = None

logger = logging.getLogger(__name__)

app = FastAPI()


class Item(BaseModel):
    texts: List[str]


@app.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
_conn = None


def _get_conn():  # pragma: no cover - exercised in integration
    if mdb is None:
        raise RuntimeError("MySQLdb not installed")
    global _conn
    if _conn is None or not getattr(_conn, "open", False):
        _conn = mdb.connect(
            host=os.getenv("MYSQL_HOST", "db"),
            user=os.getenv("MYSQL_USER", "root"),
            passwd=os.getenv("MYSQL_PASSWORD", "root"),
            db=os.getenv("MYSQL_DB", "trading"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            charset="utf8mb4",
            autocommit=True,
        )
    return _conn


############################################################
# Sentiment model
############################################################

try:  # pragma: no cover - heavy dependency; exercised in production
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        pipeline,
    )

    _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    _pipe = pipeline("sentiment-analysis", model=_model, tokenizer=_tokenizer)

    def finbert_sentiment(text: str) -> float:
        """Score sentiment using the FinBERT model."""
        res = _pipe(text)[0]
        label = res["label"].lower()
        score = res["score"]
        if label == "positive":
            return float(score)
        if label == "negative":
            return float(-score)
        return 0.0

    sentiment_fn: Callable[[str], float] = finbert_sentiment
    logger.info("FinBERT model loaded")
except Exception as exc:  # pragma: no cover - exercised when model unavailable
    logger.warning("FinBERT unavailable, using heuristic sentiment: %s", exc)

    BULL = {
        "beat",
        "beats",
        "up",
        "surge",
        "guidance",
        "buy",
        "upgrade",
        "breakout",
        "bull",
    }
    BEAR = {
        "miss",
        "misses",
        "down",
        "plunge",
        "downgrade",
        "sell",
        "hack",
        "bear",
    }

    def stub_sentiment(text: str) -> float:
        t = text.lower()
        p = sum(1 for w in BULL if w in t)
        n = sum(1 for w in BEAR if w in t)
        score = np.tanh(0.7 * (p - n))  # -1..1
        return float(score)

    sentiment_fn = stub_sentiment


def normalize(x: float) -> float:
    return float((x + 1.0) * 50.0)  # -> 0..100


@app.post("/score")
def score(item: Item):
    raw = [sentiment_fn(t) for t in item.texts]
    return {"scores": [normalize(x) for x in raw]}


@app.get("/sentiment")
def sentiment(symbol: str):
    """Return latest fused sentiment for a symbol."""
    try:
        conn = _get_conn()
    except Exception as exc:  # pragma: no cover - exercised when db missing
        logger.error("DB connection failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ts, news_score, social_score, mood_score, regime_adj "
            "FROM sentiment_agg WHERE symbol=%s ORDER BY ts DESC LIMIT 1",
            (symbol,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="symbol not found")
    ts, news, social, mood, regime = row
    return {
        "symbol": symbol,
        "ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        "news_score": news,
        "social_score": social,
        "mood_score": mood,
        "regime_adj": regime,
    }


@app.get("/latest")
def latest():
    """Return latest fused sentiment for all symbols."""
    try:
        conn = _get_conn()
    except Exception as exc:  # pragma: no cover - exercised when db missing
        logger.error("DB connection failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.symbol, s.ts, s.news_score, s.social_score, s.mood_score, s.regime_adj "
            "FROM sentiment_agg s JOIN (SELECT symbol, MAX(ts) ts FROM sentiment_agg GROUP BY symbol) m "
            "ON s.symbol=m.symbol AND s.ts=m.ts"
        )
        rows = cur.fetchall()
    res = []
    for sym, ts, news, social, mood, regime in rows:
        res.append(
            {
                "symbol": sym,
                "ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "news_score": news,
                "social_score": social,
                "mood_score": mood,
                "regime_adj": regime,
            }
        )
    return {"results": res}
