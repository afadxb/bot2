from .mood_gate import get_latest_mood

def trail_params(k_atr: float, p_trail: float, symbol: str) -> tuple[float,float]:
    mood = get_latest_mood(symbol)
    if mood is None:
        return k_atr, p_trail
    if mood < 40:
        return k_atr + 0.25, p_trail
    if mood > 70:
        return max(1.0, k_atr - 0.25), max(0.005, p_trail - 0.005)
    return k_atr, p_trail
