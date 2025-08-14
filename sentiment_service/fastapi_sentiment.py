from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Callable
import numpy as np
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

class Item(BaseModel):
    texts: List[str]

@app.get("/health")
def health():
    return {"ok": True}

############################################################
# Sentiment model
############################################################

BULL = {"beat","beats","up","surge","guidance","buy","upgrade","breakout","bull"}
BEAR = {"miss","misses","down","plunge","downgrade","sell","hack","bear"}

def stub_sentiment(text: str) -> float:
    """Fallback heuristic when FinBERT isn't available."""
    t = text.lower()
    p = sum(1 for w in BULL if w in t)
    n = sum(1 for w in BEAR if w in t)
    score = np.tanh(0.7 * (p - n))  # -1..1
    return float(score)

sentiment_fn: Callable[[str], float] = stub_sentiment

try:  # pragma: no cover - heavy dependency; exercised in production
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

    _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    _pipe = pipeline("sentiment-analysis", model=_model, tokenizer=_tokenizer)

    def finbert_sentiment(text: str) -> float:
        res = _pipe(text)[0]
        label = res["label"].lower()
        score = res["score"]
        if label == "positive":
            return float(score)
        if label == "negative":
            return float(-score)
        return 0.0

    sentiment_fn = finbert_sentiment
    logger.info("FinBERT model loaded")
except Exception as exc:  # pragma: no cover - exercised when model unavailable
    logger.warning("FinBERT unavailable, using heuristic sentiment: %s", exc)

def normalize(x: float) -> float:
    return float((x + 1.0) * 50.0)  # -> 0..100

@app.post("/score")
def score(item: Item):
    raw = [sentiment_fn(t) for t in item.texts]
    return {"scores": [normalize(x) for x in raw]}
