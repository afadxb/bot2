import MySQLdb as mdb
import os

def get_latest_mood(symbol: str) -> float | None:
    with mdb.connect(
        host=os.getenv("MYSQL_HOST","db"),
        user=os.getenv("MYSQL_USER","root"),
        passwd=os.getenv("MYSQL_PASSWORD","root"),
        db=os.getenv("MYSQL_DB","trading"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        charset="utf8mb4",
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mood_score FROM sentiment_agg WHERE symbol=%s ORDER BY ts DESC LIMIT 1", (symbol,))
            row = cur.fetchone()
            return float(row[0]) if row else None

def entry_allowed(symbol: str, entry_block: int = None) -> bool:
    mood = get_latest_mood(symbol)
    if mood is None:
        return True  # no sentiment -> do not block
    block = int(entry_block or int(os.getenv('ENTRY_BLOCK','30')))
    return mood >= block
