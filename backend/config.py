"""Application configuration loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Default watchlist (always present)
DEFAULT_TICKERS = ["NIFTYBEES.NS", "BANKBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
MAX_CUSTOM_TICKERS = 10

# Market universe for "Top Dip Opportunities" discovery feed.
# Curated list of liquid NSE stocks + popular ETFs — good long-term candidates.
MARKET_UNIVERSE = [
    # Broad-market & sector ETFs
    "NIFTYBEES.NS", "BANKBEES.NS", "JUNIORBEES.NS", "ITBEES.NS",
    "CPSEETF.NS", "GOLDBEES.NS",
    # Nifty 50 large caps across sectors
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS"
]
# Max results on discovery feed
DISCOVER_TOP_N = int(os.environ.get("DISCOVER_TOP_N", "12"))

# ntfy
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "deepraj-stock-dip-9827")
NTFY_BASE = os.environ.get("NTFY_BASE", "https://ntfy.sh")

# Cache TTL (minutes)
CACHE_TTL_MINUTES = int(os.environ.get("CACHE_TTL_MINUTES", "45"))

# Score thresholds
STRONG_SCORE = 70
MEDIUM_SCORE = 40

# Scheduler - IST market hours (9:30 AM - 3:30 PM IST)
MARKET_TZ = "Asia/Kolkata"
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 30
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MIN = 30

# Scoring weights
W_DRAWDOWN = 0.30
W_MA = 0.25
W_RSI = 0.25
W_CONF = 0.20
