"""Data layer: yfinance fetch with MongoDB cache and in-memory fallback."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf

from config import CACHE_TTL_MINUTES
from indicators import compute_indicators

logger = logging.getLogger(__name__)

# In-memory fallback cache keyed by ticker -> (expires_at, dataframe_records)
_MEM_CACHE: dict = {}


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    out = df.reset_index()
    out["Date"] = out["Date"].apply(lambda d: d.isoformat() if hasattr(d, "isoformat") else str(d))
    # keep only needed columns
    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in out.columns]
    return out[cols].to_dict(orient="records")


async def _get_cached(db, ticker: str) -> Optional[pd.DataFrame]:
    """Retrieve cached history from Mongo (or memory fallback). Returns df or None if expired."""
    now = datetime.now(timezone.utc)
    # Try Mongo first
    try:
        doc = await db.price_cache.find_one({"ticker": ticker}, {"_id": 0})
        if doc:
            expires = datetime.fromisoformat(doc["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires > now:
                return _records_to_df(doc["records"])
    except Exception as e:
        logger.warning(f"Mongo cache read failed for {ticker}: {e}")

    # Memory fallback
    entry = _MEM_CACHE.get(ticker)
    if entry:
        expires_at, records = entry
        if expires_at > now:
            return _records_to_df(records)
    return None


async def _set_cache(db, ticker: str, df: pd.DataFrame):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=CACHE_TTL_MINUTES)
    records = _df_to_records(df)
    # Memory always
    _MEM_CACHE[ticker] = (expires_at, records)
    # Mongo upsert
    try:
        await db.price_cache.update_one(
            {"ticker": ticker},
            {"$set": {
                "ticker": ticker,
                "records": records,
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"Mongo cache write failed for {ticker}: {e}")


async def _get_stale_cache(db, ticker: str) -> Optional[pd.DataFrame]:
    """Return cached data ignoring expiry (fallback on API failure)."""
    try:
        doc = await db.price_cache.find_one({"ticker": ticker}, {"_id": 0})
        if doc:
            return _records_to_df(doc["records"])
    except Exception:
        pass
    entry = _MEM_CACHE.get(ticker)
    if entry:
        return _records_to_df(entry[1])
    return None


def _fetch_yf(ticker: str) -> Optional[pd.DataFrame]:
    """Blocking yfinance fetch with retry."""
    last_err = None
    for attempt in range(2):
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y", interval="1d", auto_adjust=False)
            if hist is None or hist.empty:
                raise ValueError("empty history")
            # Normalize index to naive datetime
            hist.index = pd.to_datetime(hist.index).tz_localize(None) if hist.index.tz is not None else pd.to_datetime(hist.index)
            hist.index.name = "Date"
            return hist[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            last_err = e
            logger.warning(f"yfinance attempt {attempt+1} failed for {ticker}: {e}")
    logger.error(f"yfinance failed for {ticker}: {last_err}")
    return None


async def get_history(db, ticker: str) -> Optional[pd.DataFrame]:
    """Return 1y daily history with indicators merged. Uses cache where possible."""
    cached = await _get_cached(db, ticker)
    if cached is not None and not cached.empty:
        df = cached
    else:
        df = _fetch_yf(ticker)
        if df is None or df.empty:
            stale = await _get_stale_cache(db, ticker)
            if stale is not None and not stale.empty:
                logger.info(f"Using stale cache for {ticker}")
                df = stale
            else:
                return None
        else:
            await _set_cache(db, ticker, df)

    # Add indicators
    inds = compute_indicators(df["Close"])
    df = df.assign(RSI=inds["rsi"], MA50=inds["ma50"], MA200=inds["ma200"])
    return df


def validate_ticker_symbol(symbol: str) -> bool:
    """Basic validation: non-empty, uppercase alnum + dots. Typical NSE tickers end with .NS or .BO."""
    if not symbol or len(symbol) > 30:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-&")
    return all(c in allowed for c in symbol.upper())
