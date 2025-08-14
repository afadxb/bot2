import os
import time
import json
import hashlib
import datetime as dt
import pytz
import MySQLdb as mdb
import requests
import sys

sys.path.append(os.path.dirname(__file__) + '/..')
from alerts import monitor

TZ_UTC = pytz.UTC

class DB:
    def __init__(self):
        self.conn = mdb.connect(
            host=os.getenv("MYSQL_HOST","db"),
            user=os.getenv("MYSQL_USER","root"),
            passwd=os.getenv("MYSQL_PASSWORD","root"),
            db=os.getenv("MYSQL_DB","trading"),
            port=int(os.getenv("MYSQL_PORT","3306")),
            charset="utf8mb4",
            autocommit=True,
        )

    def exec(self, q, args=None):
        with self.conn.cursor() as cur:
            try:
                cur.execute(q, args or ())
                return cur.fetchall()
            except Exception as exc:
                monitor.record_db_error(str(exc))
                raise

    def insert_raw(self, rows):
        if not rows: return 0
        q = ("INSERT INTO sentiment_raw (ts, symbol, source, text, raw_score, quality, meta) "
             "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        with self.conn.cursor() as cur:
            try:
                cur.executemany(q, [(
                    r['ts'], r['symbol'], r['source'], r['text'], r.get('raw_score'), r.get('quality',1.0), json.dumps(r.get('meta',{}))
                ) for r in rows])
            except Exception as exc:
                monitor.record_db_error(str(exc))
                raise
        return len(rows)

    def upsert_agg(self, symbol, rec):
        q = ("REPLACE INTO sentiment_agg (symbol, ts, news_score, social_score, mood_score, regime_adj, details) "
             "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        with self.conn.cursor() as cur:
            try:
                cur.execute(q, (
                    symbol, rec['ts'], rec.get('news_score'), rec.get('social_score'), rec.get('mood_score'), rec.get('regime_adj'), json.dumps(rec.get('details',{}))
                ))
            except Exception as exc:
                monitor.record_db_error(str(exc))
                raise

    def get_news_hashes(self, hashes):
        if not hashes:
            return set()
        q = "SELECT hash FROM news_hashes WHERE hash IN (" + ",".join(["%s"] * len(hashes)) + ")"
        rows = self.exec(q, list(hashes))
        return {r[0] for r in rows}

    def insert_news_hashes(self, hashes):
        if not hashes:
            return 0
        q = "INSERT IGNORE INTO news_hashes (hash, ts) VALUES (%s, NOW())"
        with self.conn.cursor() as cur:
            try:
                cur.executemany(q, [(h,) for h in hashes])
            except Exception as exc:
                monitor.record_db_error(str(exc))
                raise
        return len(hashes)

    def prune_news_hashes(self, max_age_hours):
        q = "DELETE FROM news_hashes WHERE ts < NOW() - INTERVAL %s HOUR"
        with self.conn.cursor() as cur:
            try:
                cur.execute(q, (max_age_hours,))
            except Exception as exc:
                monitor.record_db_error(str(exc))
                raise

def now_utc():
    return dt.datetime.now(tz=TZ_UTC).strftime('%Y-%m-%d %H:%M:%S')

_CACHE = {}

def score_batch(texts):
    url = os.getenv('SENTIMENT_URL','http://sentiment:8000/score')
    results = [None] * len(texts)
    to_query = []
    idx_map = {}
    for i, t in enumerate(texts):
        if t in _CACHE:
            results[i] = _CACHE[t]
            monitor.record_cache_hit(True)
        else:
            idx_map[len(to_query)] = i
            to_query.append(t)
            monitor.record_cache_hit(False)
    if to_query:
        r = requests.post(url, json={"texts": to_query}, timeout=15)
        r.raise_for_status()
        scores = r.json()["scores"]
        for j, s in enumerate(scores):
            orig = idx_map[j]
            results[orig] = s
            _CACHE[to_query[j]] = s
    return results

def get_env_symbols():
    return [s.strip() for s in os.getenv('WATCHLIST','BTCUSD').split(',') if s.strip()]

def get_regime_adj(min_val=0.6):
    # Placeholder: 1.0 (no dampening). Wire VIX or crypto vol index later.
    return max(min_val, 1.0)

def normalize_from_raw(raw_score):
    # raw_score stored as -1..1; convert to 0..100
    return float((raw_score + 1.0) * 50.0)
