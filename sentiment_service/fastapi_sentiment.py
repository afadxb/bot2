from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import numpy as np

app = FastAPI()

class Item(BaseModel):
    texts: List[str]

@app.get("/health")
def health():
    return {"ok": True}

# TODO: Replace with FinBERT or another finance-tuned model.
# Stub heuristic: + if contains bullish verbs, - if contains bearish verbs.
BULL = {"beat","beats","up","surge","guidance","buy","upgrade","breakout","bull"}
BEAR = {"miss","misses","down","plunge","downgrade","sell","hack","bear"}

def stub_sentiment(text: str) -> float:
    t = text.lower()
    p = sum(1 for w in BULL if w in t)
    n = sum(1 for w in BEAR if w in t)
    score = np.tanh(0.7*(p-n))  # -1..1
    return float(score)

def normalize(x: float) -> float:
    return float((x + 1.0) * 50.0)  # -> 0..100

@app.post("/score")
def score(item: Item):
    raw = [stub_sentiment(t) for t in item.texts]
    return {"scores": [normalize(x) for x in raw]}
