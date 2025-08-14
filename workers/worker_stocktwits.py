import os
import time
import requests
import logging
from utils import DB, now_utc, score_batch, get_env_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_SEC = int(os.getenv('STOCKTWITS_POLL_SEC','120'))

def fetch_stocktwits(symbol):
    # Map to Stocktwits format: e.g., BTCUSD -> BTC.X, TSLA -> TSLA
    st_sym = symbol
    if symbol.endswith('USD') and len(symbol) in (6,7):
        st_sym = symbol[:-3] + '.X'  # BTCUSD -> BTC.X
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{st_sym}.json"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return []
    j = r.json()
    msgs = j.get('messages', [])
    texts = []
    for m in msgs[:50]:
        body = m.get('body','')
        if body:
            texts.append(body[:4000])
    return texts

def run_once():
    symbols = get_env_symbols()
    db = DB()
    total = 0
    for sym in symbols:
        try:
            texts = fetch_stocktwits(sym)
            if not texts:
                continue
            scores = score_batch(texts)
            ts = now_utc()
            rows = [
                {
                    'ts': ts,
                    'symbol': sym,
                    'source': 'stocktwits',
                    'text': t,
                    'raw_score': (s - 50) / 50.0,
                    'quality': 1.0,
                    'meta': None,
                }
                for t, s in zip(texts, scores)
            ]
            total += db.insert_raw(rows)
        except Exception:
            logger.exception("failed processing stocktwits for %s", sym)
            continue
    return total

def main():
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("worker_stocktwits cycle error")
        time.sleep(POLL_SEC)

if __name__ == '__main__':
    main()
