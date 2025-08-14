import MySQLdb as mdb
import os
import threading

_conn_local = threading.local()
MARKET = os.getenv("MARKET", "crypto")

def _get_conn():
    conn = getattr(_conn_local, "conn", None)
    if conn is None or not conn.open:
        _conn_local.conn = mdb.connect(
            host=os.getenv("MYSQL_HOST", "db"),
            user=os.getenv("MYSQL_USER", "root"),
            passwd=os.getenv("MYSQL_PASSWORD", "root"),
            db=os.getenv("MYSQL_DB", "trading"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            charset="utf8mb4",
            autocommit=True,
        )
    return _conn_local.conn

def get_latest_mood(symbol: str, market: str | None = None) -> float | None:
    conn = _get_conn()
    mkt = market or MARKET
    with conn.cursor() as cur:
        cur.execute(
            "SELECT mood_score FROM sentiment_agg WHERE market=%s AND symbol=%s ORDER BY ts DESC LIMIT 1",
            (mkt, symbol),
        )
        row = cur.fetchone()
        return float(row[0]) if row else None

def entry_allowed(symbol: str, entry_block: int = None, market: str | None = None) -> bool:
    mood = get_latest_mood(symbol, market)
    if mood is None:
        return True  # no sentiment -> do not block
    block = int(entry_block or int(os.getenv('ENTRY_BLOCK','30')))
    return mood >= block
