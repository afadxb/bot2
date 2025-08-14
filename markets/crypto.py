"""Configuration for crypto market workers."""

# Symbols to monitor
WATCHLIST = [
    "BTCUSD",
    "ETHUSD",
    "SOLUSD",
]

# Weighting of news vs social components
WEIGHTS = {
    "news": 0.5,
    "social": 0.5,
}

# Placeholder for regime gauge implementation
REGIME_GAUGE = "crypto_vol"

# Max allowable staleness for data (seconds)
FRESHNESS_SECONDS = 120  # 2 minutes
