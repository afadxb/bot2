import os
import time
import logging
import requests
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class PushoverNotifier:
    """Send push notifications using the Pushover service."""
    def __init__(self, token: str | None = None, user: str | None = None):
        self.token = token or os.getenv("PUSHOVER_TOKEN")
        self.user = user or os.getenv("PUSHOVER_USER")
        self.api_url = "https://api.pushover.net/1/messages.json"
        if not self.token or not self.user:
            logger.warning("Pushover credentials missing; alerts disabled")

    def send(self, message: str, title: str = "Trading Mood Bot") -> bool:
        if not self.token or not self.user:
            return False
        try:
            r = requests.post(
                self.api_url,
                data={"token": self.token, "user": self.user, "message": message, "title": title},
                timeout=5,
            )
            r.raise_for_status()
            return True
        except Exception:
            logger.exception("failed to send Pushover alert")
            return False

class MetricsMonitor:
    """Track system metrics and trigger alerts when thresholds are crossed."""
    def __init__(self, notifier: PushoverNotifier | None = None):
        self.notifier = notifier or PushoverNotifier()
        self.ingestion = deque()        # (ts, success)
        self.cache_events = deque()     # (ts, hit)
        self.fallback_events = deque()  # (ts, used_fallback)
        self.last_fused = defaultdict(lambda: 0.0)  # symbol -> ts

    # -- helpers -----------------------------------------------------------------
    @staticmethod
    def _prune(dq: deque, window: int) -> None:
        cutoff = time.time() - window
        while dq and dq[0][0] < cutoff:
            dq.popleft()

    def _alert(self, msg: str) -> None:
        logger.info("ALERT: %s", msg)
        self.notifier.send(msg)

    # -- ingestion ---------------------------------------------------------------
    def record_ingestion(self, success: bool) -> None:
        self.ingestion.append((time.time(), success))
        self._prune(self.ingestion, 600)  # 10m window
        self._check_ingestion_errors()

    def _check_ingestion_errors(self) -> None:
        events = list(self.ingestion)
        if not events:
            return
        errors = sum(1 for _, ok in events if not ok)
        rate = errors / len(events)
        if rate > 0.05:  # >5%
            self._alert(f"Ingestion error rate {rate*100:.1f}% over 10m")

    # -- cache -------------------------------------------------------------------
    def record_cache_hit(self, hit: bool) -> None:
        self.cache_events.append((time.time(), hit))
        self._prune(self.cache_events, 600)
        self._check_cache()

    def _check_cache(self) -> None:
        events = list(self.cache_events)
        if not events:
            return
        hits = sum(1 for _, h in events if h)
        rate = hits / len(events)
        if rate < 0.60:
            self._alert(f"Cache hit ratio low: {rate*100:.1f}% over 10m")

    # -- database ----------------------------------------------------------------
    def record_db_error(self, msg: str) -> None:
        self._alert(f"DB error: {msg}")

    # -- model fallback ---------------------------------------------------------
    def record_model_fallback(self, used_fallback: bool) -> None:
        self.fallback_events.append((time.time(), used_fallback))
        self._prune(self.fallback_events, 600)
        self._check_fallback()

    def _check_fallback(self) -> None:
        events = list(self.fallback_events)
        if not events:
            return
        uses = sum(1 for _, used in events if used)
        rate = uses / len(events)
        if rate > 0.10:
            self._alert(f"Model fallback engaged {rate*100:.1f}% of requests")

    # -- freshness ---------------------------------------------------------------
    def record_fused(self, symbol: str, is_crypto: bool) -> None:
        now = time.time()
        self.last_fused[symbol] = now
        self._check_freshness(symbol, is_crypto, now)

    def _check_freshness(self, symbol: str, is_crypto: bool, now: float) -> None:
        max_age = 120 if is_crypto else 300
        last = self.last_fused.get(symbol, 0.0)
        if last and now - last > max_age:
            age = now - last
            self._alert(f"Freshness breach {symbol}: {age/60:.1f}m old")

    def check_freshness_all(self, symbols: list[str]) -> None:
        now = time.time()
        for sym in symbols:
            is_crypto = sym.endswith("USD")
            self._check_freshness(sym, is_crypto, now)

# Global monitor instance
monitor = MetricsMonitor()
