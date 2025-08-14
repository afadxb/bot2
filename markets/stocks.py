"""Configuration for equities market workers."""

# Symbols to monitor
WATCHLIST = [
    "AAPL",
    "MSFT",
    "TSLA",
    "AMZN",
]

# Weighting of news vs social components
WEIGHTS = {
    "news": 0.6,
    "social": 0.4,
}

# Placeholder for regime gauge implementation
REGIME_GAUGE = "vix"

# Max allowable staleness for data (seconds)
FRESHNESS_SECONDS = 300  # 5 minutes
