import os
import time
import feedparser
from utils import DB, now_utc, score_batch

POLL_SEC = int(os.getenv('NEWS_POLL_SEC','180'))
FEEDS = [u.strip() for u in os.getenv('NEWS_FEEDS','').split(',') if u.strip()]

HASH_SET = set()  # simple in-memory dedupe for demo; move to DB if needed.

def _hash(s):
    import hashlib
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def run_once():
    if not FEEDS:
        return 0
    texts = []
    metas = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:30]:
                title = e.get('title','')
                summ = e.get('summary','')
                t = (title + ' ' + summ).strip()
                if not t: continue
                h = _hash(t[:512])
                if h in HASH_SET: continue
                HASH_SET.add(h)
                texts.append(t[:4000])
                metas.append({"feed": url, "link": e.get('link','')})
        except Exception:
            continue
    if not texts:
        return 0
    scores = score_batch(texts)
    rows = []
    ts = now_utc()
    for t, s, m in zip(texts, scores, metas):
        rows.append({
            'ts': ts,
            'symbol': 'GLOBAL',           # news often market-wide; fusion maps per symbol later
            'source': 'news',
            'text': t,
            'raw_score': (s-50)/50.0,     # back to -1..1
            'quality': 1.0,
            'meta': m
        })
    if rows:
        with DB() as db:
            db.insert_raw(rows)
    return len(rows)

def main():
    while True:
        try:
            run_once()
        except Exception:
            pass
        time.sleep(POLL_SEC)

if __name__ == '__main__':
    main()
