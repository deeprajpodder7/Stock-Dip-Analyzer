"""Data layer: yfinance fetch with MongoDB cache and in-memory fallback (production-ready)."""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from config import CACHE_TTL_MINUTES
from indicators import compute_indicators

logger = logging.getLogger(__name__)

# ---------------- MEMORY CACHE ----------------
_MEM_CACHE: dict = {}


# ---------------- HELPERS ----------------
def _records_to_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    out = df.reset_index()
    out["Date"] = out["Date"].apply(
        lambda d: d.isoformat() if hasattr(d, "isoformat") else str(d)
    )

    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in out.columns]
    return out[cols].to_dict(orient="records")


def _format_chart_data(df: pd.DataFrame) -> list[dict]:
    """Convert dataframe into frontend-ready chart format"""
    try:
        return [
            {
                "date": str(idx.date()),
                "price": round(float(row["Close"]), 2),
            }
            for idx, row in df.tail(90).iterrows()
        ]
    except Exception as e:
        logger.warning(f"Chart formatting failed: {e}")
        return []


# ---------------- CACHE ----------------
async def _get_cached(db, ticker: str) -> Optional[pd.DataFrame]:
    now = datetime.now(timezone.utc)

    # Mongo cache
    if db:
        try:
            doc = await db.price_cache.find_one({"ticker": ticker}, {"_id": 0})
            if doc:
                expires = datetime.fromisoformat(doc["expires_at"])
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)

                if expires > now:
                    return _records_to_df(doc["records"])
        except Exception as e:
            logger.warning(f"Mongo read failed ({ticker}): {e}")

    # Memory cache fallback
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

    # Always store in memory
    _MEM_CACHE[ticker] = (expires_at, records)

    # Mongo (optional)
    if db:
        try:
            await db.price_cache.update_one(
                {"ticker": ticker},
                {
                    "$set": {
                        "ticker": ticker,
                        "records": records,
                        "updated_at": now.isoformat(),
                        "expires_at": expires_at.isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Mongo write failed ({ticker}): {e}")


async def _get_stale_cache(db, ticker: str) -> Optional[pd.DataFrame]:
    if db:
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


# ---------------- YFINANCE FETCH ----------------
def _fetch_yf(ticker: str) -> Optional[pd.DataFrame]:
    last_err = None

    for attempt in range(2):
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y", interval="1d", auto_adjust=False)

            if hist is None or hist.empty:
                raise ValueError("empty history")

            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            hist.index.name = "Date"

            return hist[["Open", "High", "Low", "Close", "Volume"]]

        except Exception as e:
            last_err = e
            logger.warning(f"yfinance attempt {attempt+1} failed ({ticker}): {e}")

    logger.error(f"yfinance failed ({ticker}): {last_err}")
    return None


# ---------------- MAIN FUNCTION ----------------
async def get_history(db, ticker: str) -> Optional[pd.DataFrame]:
    """Return 1-year history with indicators + chart-ready data"""

    cached = await _get_cached(db, ticker)

    if cached is not None and not cached.empty:
        df = cached
    else:
        df = _fetch_yf(ticker)

        if df is None or df.empty:
            stale = await _get_stale_cache(db, ticker)
            if stale is not None and not stale.empty:
                logger.info(f"Using stale cache ({ticker})")
                df = stale
            else:
                return None
        else:
            await _set_cache(db, ticker, df)

    try:
        inds = compute_indicators(df["Close"])
        df = df.assign(
            RSI=inds.get("rsi"),
            MA50=inds.get("ma50"),
            MA200=inds.get("ma200"),
        )
    except Exception as e:
        logger.warning(f"Indicator computation failed ({ticker}): {e}")

    # ✅ Attach chart-ready data
    df.attrs["chart"] = _format_chart_data(df)

    return df


# ---------------- VALIDATION ----------------
def validate_ticker_symbol(symbol: str) -> bool:
    if not symbol or len(symbol) > 30:
        return False

    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-&")
    return all(c in allowed for c in symbol.upper())
