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
def _fetch_yf(ticker: str):
    import requests
    import pandas as pd

    try:
        symbol = ticker.replace(".NS", "")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=6mo&interval=1d"

        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            print(f"❌ HTTP ERROR {ticker}: {res.status_code}")
            return None

        data = res.json()

        # 🔥 CRITICAL SAFETY CHECK
        if not data.get("chart") or not data["chart"].get("result"):
            print(f"❌ NO RESULT DATA {ticker}")
            print("RAW:", data)
            return None

        result = data["chart"]["result"][0]

        timestamps = result.get("timestamp")
        quote = result.get("indicators", {}).get("quote", [{}])[0]

        if not timestamps or not quote:
            print(f"❌ INVALID STRUCTURE {ticker}")
            return None

        df = pd.DataFrame({
            "Date": pd.to_datetime(timestamps, unit="s"),
            "Open": quote.get("open"),
            "High": quote.get("high"),
            "Low": quote.get("low"),
            "Close": quote.get("close"),
            "Volume": quote.get("volume"),
        })

        df = df.dropna()

        if df.empty:
            print(f"❌ EMPTY DATAFRAME {ticker}")
            return None

        df = df.set_index("Date")

        print(f"✅ SUCCESS {ticker} rows:", len(df))

        return df

    except Exception as e:
        print(f"❌ FETCH ERROR {ticker}:", e)
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
