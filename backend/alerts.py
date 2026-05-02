"""Alert dedupe helpers — ensure one alert per ticker per day, with strict rules.

A strong dip alert is only sent if:
  - signal_strength == "Strong"
  - score >= 70
  - RSI <= 40 (confirmed oversold)
  - no alert has been sent for this ticker today (IST date)
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
import pytz

from config import MARKET_TZ
from notifier import send_strong_dip_alert

logger = logging.getLogger(__name__)


def today_ist_key() -> str:
    """Return today's date string in IST (YYYY-MM-DD)."""
    return datetime.now(pytz.timezone(MARKET_TZ)).strftime("%Y-%m-%d")


def passes_alert_rules(analysis: dict) -> bool:
    """Strict, low-noise alert gate.

    Rules:
      - signal_strength == 'Strong'
      - score >= 70
      - RSI present and RSI <= 40 (confirmed oversold)
    """
    if analysis.get("signal_strength") != "Strong":
        return False
    if analysis.get("score", 0) < 70:
        return False
    rsi = analysis.get("rsi")
    if rsi is None or rsi > 40:
        return False
    return True


async def ensure_alert_log_index(db):
    """Create a unique compound index on (ticker, date) to guarantee dedupe at DB level."""
    try:
        await db.alert_log.create_index(
            [("ticker", 1), ("date", 1)], unique=True, name="ticker_date_unique"
        )
    except Exception as e:
        logger.warning(f"create index alert_log failed: {e}")


async def already_alerted_today(db, ticker: str, date_key: str | None = None) -> bool:
    """Return True if an alert was already recorded for this ticker today."""
    key = date_key or today_ist_key()
    doc = await db.alert_log.find_one({"ticker": ticker, "date": key}, {"_id": 0})
    return doc is not None


async def send_alert_if_allowed(db, analysis: dict) -> dict:
    """Attempt to send a strong dip alert respecting both rules:
      1) strict signal gate (passes_alert_rules)
      2) dedupe: once per ticker per IST date

    Returns a dict: {status: 'sent'|'deduped'|'rule_blocked'|'send_failed', ticker, ...}
    Never raises.
    """
    ticker = analysis.get("ticker", "?")
    if not passes_alert_rules(analysis):
        return {"status": "rule_blocked", "ticker": ticker, "reason": "score<70 or RSI>40"}

    date_key = today_ist_key()
    if await already_alerted_today(db, ticker, date_key):
        return {"status": "deduped", "ticker": ticker, "date": date_key}

    ok = send_strong_dip_alert(analysis)
    # Insert log. If a race caused a duplicate, catch and treat as deduped.
    try:
        await db.alert_log.insert_one({
            "ticker": ticker,
            "date": date_key,
            "score": analysis.get("score"),
            "rsi": analysis.get("rsi"),
            "sent": bool(ok),
            "last_alerted_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.info(f"alert_log insert race for {ticker}: {e}")
        return {"status": "deduped", "ticker": ticker, "date": date_key}

    return {"status": "sent" if ok else "send_failed", "ticker": ticker, "date": date_key}
