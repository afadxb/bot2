import os
import time
import feedparser
import logging
import sys

sys.path.append(os.path.dirname(__file__) + '/..')
from alerts import monitor
from utils import DB, now_utc, score_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_SEC = int(os.getenv('NEWS_POLL_SEC','180'))
FEEDS = [u.strip() for u in os.getenv('NEWS_FEEDS','').split(',') if u.strip()]

HASH_TTL_HOURS = int(os.getenv('NEWS_HASH_TTL_HOURS','168'))

def _hash(s):
    import hashlib
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def run_once():
    if not FEEDS:
        return 0
    db = DB()
    candidates = []
    for url in FEEDS:
        try:
            d = feedparser.parse(url)
            for e in d.entries[:30]:
                title = e.get('title','')
                summ = e.get('summary','')
                t = (title + ' ' + summ).strip()
                if not t:
                    continue
                h = _hash(t[:512])
                candidates.append((h, t[:4000], {"feed": url, "link": e.get('link','')}))
        except Exception:
            logger.exception("failed to parse feed %s", url)
            continue
    if not candidates:
        db.prune_news_hashes(HASH_TTL_HOURS)
        return 0
    hashes = [h for h, _, _ in candidates]
    existing = db.get_news_hashes(hashes)
    texts = []
    metas = []
    new_hashes = []
    for h, t, m in candidates:
        if h in existing:
            continue
        texts.append(t)
        metas.append(m)
        new_hashes.append(h)
    if not texts:
        db.prune_news_hashes(HASH_TTL_HOURS)
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
    db.insert_raw(rows)
    db.insert_news_hashes(new_hashes)
    db.prune_news_hashes(HASH_TTL_HOURS)
    return len(rows)

def main():
    while True:
        try:
            run_once()
            monitor.record_ingestion(True)
        except Exception:
            monitor.record_ingestion(False)
            logger.exception("worker_news cycle error")
        time.sleep(POLL_SEC)

if __name__ == '__main__':
    main()
