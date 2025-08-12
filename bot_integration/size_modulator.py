import os
from .mood_gate import get_latest_mood

def size_multiplier(symbol: str) -> float:
    mood = get_latest_mood(symbol)
    if mood is None:
        return 1.0
    if mood < int(os.getenv('ENTRY_BLOCK','30')):
        return 0.0
    if mood > int(os.getenv('SIZE_UP','70')):
        return 1.15
    return 1.0

def compute_qty_percent_equity(equity: float, price: float, symbol: str) -> float:
    pct = float(os.getenv('POS_SIZE_PCT','0.30'))
    base = (equity * pct) / price
    return base * size_multiplier(symbol)
