import os
import time
import json
import hashlib
import datetime as dt
import pytz
import MySQLdb as mdb
import requests

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

    # Support use as a context manager to ensure connections are closed
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def exec(self, q, args=None):
        with self.conn.cursor() as cur:
            cur.execute(q, args or ())
            return cur.fetchall()

    def insert_raw(self, rows):
        if not rows: return 0
        q = ("INSERT INTO sentiment_raw (ts, symbol, source, text, raw_score, quality, meta) "
             "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        with self.conn.cursor() as cur:
            cur.executemany(q, [(
                r['ts'], r['symbol'], r['source'], r['text'], r.get('raw_score'), r.get('quality',1.0), json.dumps(r.get('meta',{}))
            ) for r in rows])
        return len(rows)

    def upsert_agg(self, symbol, rec):
        q = ("REPLACE INTO sentiment_agg (symbol, ts, news_score, social_score, mood_score, regime_adj, details) "
             "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        with self.conn.cursor() as cur:
            cur.execute(q, (
                symbol, rec['ts'], rec.get('news_score'), rec.get('social_score'), rec.get('mood_score'), rec.get('regime_adj'), json.dumps(rec.get('details',{}))
            ))

def now_utc():
    return dt.datetime.now(tz=TZ_UTC).strftime('%Y-%m-%d %H:%M:%S')

def score_batch(texts):
    url = os.getenv('SENTIMENT_URL','http://sentiment:8000/score')
    r = requests.post(url, json={"texts": texts}, timeout=15)
    r.raise_for_status()
    return r.json()["scores"]

def get_env_symbols():
    return [s.strip() for s in os.getenv('WATCHLIST','BTCUSD').split(',') if s.strip()]

def get_regime_adj(min_val=0.6):
    # Placeholder: 1.0 (no dampening). Wire VIX or crypto vol index later.
    return max(min_val, 1.0)

def normalize_from_raw(raw_score):
    # raw_score stored as -1..1; convert to 0..100
    return float((raw_score + 1.0) * 50.0)
