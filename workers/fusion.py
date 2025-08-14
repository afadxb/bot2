import os
import time
import numpy as np
import logging
import datetime as dt
from utils import (
    DB,
    now_utc,
    get_env_symbols,
    get_regime_adj,
    normalize_from_raw,
    FUSION_LAG,
    start_metrics_server,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FUSE_WINDOW_MIN = int(os.getenv('FUSE_WINDOW_MIN','120'))
W_NEWS = float(os.getenv('SENT_W_NEWS','0.5'))
W_SOC  = float(os.getenv('SENT_W_SOCIAL','0.5'))

ENTRY_BLOCK = int(os.getenv('ENTRY_BLOCK','30'))
SIZE_UP = int(os.getenv('SIZE_UP','70'))

NEWS_SYM = 'GLOBAL'  # news scored as GLOBAL; we apply it to all symbols equally by default

def wavg(values, weights):
    import numpy as np
    v = np.array(values)
    w = np.clip(np.array(weights), 0, None)
    if len(v) == 0:
        return None
    return float((v*w).sum() / (w.sum() + 1e-9))

def load_recent(db, symbol, source):
    q = ("SELECT raw_score, quality FROM sentiment_raw "
         "WHERE ts >= NOW() - INTERVAL %s MINUTE AND symbol=%s AND source=%s")
    rows = db.exec(q, (FUSE_WINDOW_MIN, symbol, source))
    scores = [normalize_from_raw(r[0]) for r in rows]  # -> 0..100
    weights = [r[1] for r in rows]
    return scores, weights

def fuse_symbol(db, symbol):
    # compute staleness before inserting new record
    last = db.exec(
        "SELECT ts FROM sentiment_agg WHERE symbol=%s ORDER BY ts DESC LIMIT 1",
        (symbol,),
    )
    last_ts = last[0][0] if last else None
    # news: GLOBAL
    n_scores, n_weights = load_recent(db, NEWS_SYM, 'news')
    s_scores, s_weights = [], []
    for src in ('stocktwits','reddit'):
        xs, ws = load_recent(db, symbol, src)
        s_scores += xs
        s_weights += ws

    import numpy as np
    news_score = np.clip(wavg(n_scores, n_weights), 0, 100) if n_scores else None
    social_score = np.clip(wavg(s_scores, s_weights), 0, 100) if s_scores else None

    ns = news_score if news_score is not None else 50.0
    ss = social_score if social_score is not None else 50.0

    regime = get_regime_adj(float(os.getenv('REGIME_MIN','0.6')))
    mood = regime * (W_NEWS*ns + W_SOC*ss)
    mood = float(np.clip(mood, 0, 100))

    rec = {
        'ts': now_utc(),
        'news_score': ns,
        'social_score': ss,
        'mood_score': mood,
        'regime_adj': regime,
        'details': { 'n_news': len(n_scores), 'n_social': len(s_scores) }
    }
    db.upsert_agg(symbol, rec)
    if last_ts:
        lag = (dt.datetime.utcnow() - last_ts).total_seconds()
        FUSION_LAG.labels(symbol=symbol).set(lag)

def loop():
    db = DB()
    symbols = get_env_symbols()
    while True:
        try:
            for sym in symbols:
                fuse_symbol(db, sym)
        except Exception:
            logger.exception("fusion loop error")
        time.sleep(30)

if __name__ == '__main__':
    # Simple supervisor: spawn workers in this container
    import threading
    import worker_news, worker_stocktwits

    start_metrics_server()
    threading.Thread(target=worker_news.main, daemon=True).start()
    threading.Thread(target=worker_stocktwits.main, daemon=True).start()
    loop()
