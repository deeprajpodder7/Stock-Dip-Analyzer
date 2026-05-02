"""Stock Dip Analyzer - FastAPI backend."""
from __future__ import annotations
import os
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    DEFAULT_TICKERS, MAX_CUSTOM_TICKERS, NTFY_TOPIC, NTFY_BASE,
    MARKET_UNIVERSE, DISCOVER_TOP_N,
)
from data import get_history, validate_ticker_symbol
from scorer import analyze_dataframe
from notifier import send_strong_dip_alert
from alerts import send_alert_if_allowed, ensure_alert_log_index, passes_alert_rules
from scheduler import start_scheduler, shutdown_scheduler, get_status as get_scheduler_status

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("stock_dip_analyzer")

# --- MongoDB ---
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# --- FastAPI ---
app = FastAPI(title="Stock Dip Analyzer", version="1.0.0")
api = APIRouter(prefix="/api")


class TickerAdd(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=30)


async def get_watchlist() -> List[dict]:
    """Return ordered list: defaults first then custom tickers."""
    cursor = db.watchlist_custom.find({}, {"_id": 0}).sort("added_at", 1)
    custom_docs = await cursor.to_list(length=MAX_CUSTOM_TICKERS + 5)
    custom_tickers = [d["ticker"] for d in custom_docs]

    out = [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]
    seen = set(DEFAULT_TICKERS)
    for t in custom_tickers:
        if t not in seen:
            out.append({"ticker": t, "is_default": False})
            seen.add(t)
    return out


async def _analyze_one(ticker: str) -> dict:
    df = await get_history(db, ticker)
    if df is None or df.empty:
        return {
            "ticker": ticker,
            "error": "Data unavailable",
            "score": 0,
            "signal_strength": "Weak",
            "recommendation": "Could not fetch data.",
        }
    return analyze_dataframe(ticker, df)


async def analyze_all(db_arg=None) -> List[dict]:
    wl = await get_watchlist()
    tasks = [_analyze_one(item["ticker"]) for item in wl]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for item, res in zip(wl, results):
        if isinstance(res, Exception):
            logger.warning(f"analyze error for {item['ticker']}: {res}")
            out.append({
                "ticker": item["ticker"],
                "error": str(res),
                "score": 0,
                "signal_strength": "Weak",
                "recommendation": "Analysis failed.",
                "is_default": item["is_default"],
            })
        else:
            res["is_default"] = item["is_default"]
            out.append(res)
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    return out


@api.get("/")
async def root():
    return {"service": "Stock Dip Analyzer", "status": "ok"}


@api.get("/watchlist")
async def watchlist_get():
    wl = await get_watchlist()
    return {
        "default_tickers": DEFAULT_TICKERS,
        "max_custom": MAX_CUSTOM_TICKERS,
        "tickers": wl,
    }


@api.post("/watchlist")
async def watchlist_add(payload: TickerAdd):
    raw = payload.ticker.strip().upper()
    if not raw:
        raise HTTPException(400, "Ticker is required")
    if not validate_ticker_symbol(raw):
        raise HTTPException(400, "Invalid ticker format")
    if raw in DEFAULT_TICKERS:
        raise HTTPException(400, f"{raw} is already in the default watchlist")
    existing = await db.watchlist_custom.find_one({"ticker": raw}, {"_id": 0})
    if existing:
        raise HTTPException(400, f"{raw} is already in your watchlist")
    count = await db.watchlist_custom.count_documents({})
    if count >= MAX_CUSTOM_TICKERS:
        raise HTTPException(400, f"Maximum {MAX_CUSTOM_TICKERS} custom tickers allowed")
    df = await get_history(db, raw)
    if df is None or df.empty:
        raise HTTPException(400, f"Could not fetch data for {raw}. Verify the ticker (use .NS for NSE).")
    await db.watchlist_custom.insert_one({
        "ticker": raw,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    wl = await get_watchlist()
    return {"ok": True, "tickers": wl}


@api.delete("/watchlist/{ticker}")
async def watchlist_delete(ticker: str):
    raw = ticker.strip().upper()
    if raw in DEFAULT_TICKERS:
        raise HTTPException(400, "Default tickers cannot be removed")
    result = await db.watchlist_custom.delete_one({"ticker": raw})
    if result.deleted_count == 0:
        raise HTTPException(404, f"{raw} not found in custom watchlist")
    wl = await get_watchlist()
    return {"ok": True, "tickers": wl}


@api.get("/discover")
async def discover(top: int = DISCOVER_TOP_N, include_weak: bool = False):
    """Scan the curated market universe and return the best-scored dip opportunities.
    Results are cached via the same yfinance+Mongo cache used by /analyze."""
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    custom = {d["ticker"] async for d in db.watchlist_custom.find({}, {"_id": 0, "ticker": 1})}
    for ticker, res in zip(MARKET_UNIVERSE, results):
        if isinstance(res, Exception) or res.get("error"):
            continue
        res["in_watchlist"] = (ticker in DEFAULT_TICKERS) or (ticker in custom)
        res["is_default"] = ticker in DEFAULT_TICKERS
        out.append(res)
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    if not include_weak:
        # Only show Medium and Strong by default on discovery
        out = [r for r in out if r.get("signal_strength") in ("Medium", "Strong")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe_size": len(MARKET_UNIVERSE),
        "results": out[: max(1, top)],
        "strong_count": sum(1 for r in out if r.get("signal_strength") == "Strong"),
    }


@api.get("/recommended-action")
async def recommended_action():
    """Simple, clear top-of-dashboard recommendation.

    Strict, low-noise rules:
      - "Buy Now": score >= 70 AND RSI <= 40 (oversold confirmation required)
      - "Accumulate Slowly": 60 <= score < 70  (OR score >= 70 but RSI > 40 → demoted)
      - "No good opportunities today": otherwise
      - Picks NEVER include stocks with score < 60.
    Returns top 1-2 qualifying stocks.
    """
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [
        r for r in results
        if not isinstance(r, Exception) and not r.get("error")
    ]
    valid.sort(key=lambda r: r.get("score", 0), reverse=True)

    # Rule: "Buy" requires score>=70 AND RSI<=40
    buy_candidates = [
        r for r in valid
        if r.get("score", 0) >= 70 and (r.get("rsi") is not None and r["rsi"] <= 40)
    ][:2]

    # Accumulate: 60-70 range + any score>=70 with RSI>40 (demoted because not confirmed oversold)
    accumulate_pool = (
        [r for r in valid if 60 <= r.get("score", 0) < 70]
        + [r for r in valid if r.get("score", 0) >= 70 and (r.get("rsi") is None or r["rsi"] > 40)]
    )
    accumulate_pool.sort(key=lambda r: r.get("score", 0), reverse=True)
    accumulate_candidates = accumulate_pool[:2]

    if buy_candidates:
        action = "Buy Now"
        tone = "strong"
        picks = buy_candidates
        message = "High-confidence dip detected (score ≥ 70 and RSI ≤ 40) — act today."
    elif accumulate_candidates:
        action = "Accumulate Slowly"
        tone = "medium"
        picks = accumulate_candidates
        message = "Moderate dips — split your entry across a few days."
    else:
        action = "No good opportunities today"
        tone = "weak"
        picks = []
        message = "Markets look steady. Stay patient, keep SIPs running."

    slim_picks = [
        {
            "ticker": p["ticker"],
            "name": p["ticker"].replace(".NS", ""),
            "price": p.get("price"),
            "drawdown_percent": p.get("drawdown_percent"),
            "rsi": p.get("rsi"),
            "score": p.get("score"),
            "signal_strength": p.get("signal_strength"),
        }
        for p in picks
    ]

    return {
        "action": action,
        "tone": tone,
        "message": message,
        "picks": slim_picks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@api.get("/investment-plan")
async def investment_plan(budget: int = 5000):
    """Generate a simple allocation plan for the given budget.

    Rules:
      - Scan market universe (same as /discover)
      - Pick top 1-2 stocks with score >= 60
      - Allocate proportionally to score (higher score = more money)
      - Round to nearest ₹100, total must equal budget
      - If no stock >= 60, fall back to full budget in NIFTYBEES.NS
    """
    if budget < 500:
        raise HTTPException(400, "Budget must be at least ₹500")

    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    candidates = []
    for ticker, res in zip(MARKET_UNIVERSE, results):
        if isinstance(res, Exception) or res.get("error"):
            continue
        if res.get("score", 0) >= 60:
            candidates.append(res)

    candidates.sort(key=lambda r: r.get("score", 0), reverse=True)
    picks = candidates[:2]

    allocations: list[dict] = []
    reason: str

    if not picks:
        # Fallback: safe ETF
        fallback_ticker = "NIFTYBEES.NS"
        fallback_analysis = next(
            (r for r, t in zip(results, MARKET_UNIVERSE)
             if t == fallback_ticker and not isinstance(r, Exception) and not r.get("error")),
            None,
        )
        price = fallback_analysis.get("price") if fallback_analysis else None
        shares = int(budget // price) if price else None
        allocations.append({
            "ticker": fallback_ticker,
            "name": fallback_ticker.replace(".NS", ""),
            "amount": budget,
            "percent": 100.0,
            "score": fallback_analysis.get("score") if fallback_analysis else None,
            "signal_strength": fallback_analysis.get("signal_strength") if fallback_analysis else "Weak",
            "price": price,
            "estimated_shares": shares,
            "is_fallback": True,
        })
        reason = "No meaningful dip (score ≥ 60) in the scanned universe. Park the full ₹{:,} in NIFTYBEES (broad-market ETF) until stronger opportunities appear.".format(budget)
    else:
        total_score = sum(p["score"] for p in picks)
        raw_alloc = [(p, budget * p["score"] / total_score) for p in picks]
        # Round each to nearest ₹100, adjust last one to make total = budget
        rounded = [(p, int(round(a / 100.0)) * 100) for p, a in raw_alloc]
        diff = budget - sum(a for _, a in rounded)
        if rounded:
            last_p, last_a = rounded[-1]
            rounded[-1] = (last_p, max(0, last_a + diff))
        for p, amt in rounded:
            price = p.get("price")
            shares = int(amt // price) if price else None
            allocations.append({
                "ticker": p["ticker"],
                "name": p["ticker"].replace(".NS", ""),
                "amount": int(amt),
                "percent": round(amt / budget * 100, 1),
                "score": p["score"],
                "signal_strength": p.get("signal_strength"),
                "price": price,
                "estimated_shares": shares,
                "is_fallback": False,
            })
        if len(picks) == 1:
            reason = f"Only 1 high-quality dip found (score ≥ 60). Concentrate the budget in {picks[0]['ticker'].replace('.NS','')}."
        else:
            reason = "Top 2 dip opportunities selected. Higher score gets a bigger allocation."

    total_allocated = sum(a["amount"] for a in allocations)
    return {
        "budget": budget,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allocations": allocations,
        "total_allocated": total_allocated,
        "reason": reason,
        "qualifying_count": len(candidates),
    }


@api.get("/analyze")
async def analyze():
    results = await analyze_all(db)
    best = results[0] if results and results[0].get("score", 0) > 0 else None
    strong_count = sum(1 for r in results if r.get("signal_strength") == "Strong")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "best_buy_today": best,
        "strong_count": strong_count,
    }


@api.get("/stock/{ticker}")
async def stock_detail(ticker: str):
    raw = ticker.strip().upper()
    df = await get_history(db, raw)
    if df is None or df.empty:
        raise HTTPException(404, f"No data for {raw}")
    analysis = analyze_dataframe(raw, df)
    hist = []
    for idx, row in df.iterrows():
        hist.append({
            "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
            "close": None if row["Close"] != row["Close"] else round(float(row["Close"]), 2),
            "ma50": None if row["MA50"] != row["MA50"] else round(float(row["MA50"]), 2),
            "ma200": None if row["MA200"] != row["MA200"] else round(float(row["MA200"]), 2),
            "rsi": None if row["RSI"] != row["RSI"] else round(float(row["RSI"]), 2),
        })
    return {"analysis": analysis, "history": hist}


@api.post("/refresh")
async def refresh():
    try:
        await db.price_cache.delete_many({})
    except Exception as e:
        logger.warning(f"clear cache failed: {e}")
    results = await analyze_all(db)
    best = results[0] if results and results[0].get("score", 0) > 0 else None
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "best_buy_today": best,
    }


@api.post("/test-notification")
async def test_notification():
    fake = {
        "ticker": "TEST.NS",
        "price": 100,
        "drawdown_percent": -15.0,
        "rsi": 28,
        "score": 85,
    }
    ok = send_strong_dip_alert(fake)
    return {"ok": ok, "topic": NTFY_TOPIC}


@api.get("/status")
async def status():
    sched = get_scheduler_status()
    return {
        "scheduler": sched,
        "notifier": {
            "enabled": bool(NTFY_TOPIC),
            "topic": NTFY_TOPIC,
            "base": NTFY_BASE,
        },
        "watchlist_defaults": DEFAULT_TICKERS,
        "max_custom": MAX_CUSTOM_TICKERS,
    }


@api.post("/trigger-alerts")
async def trigger_alerts():
    """Manually run an analysis pass and send any qualifying alerts (respecting daily dedupe
    and the strict rule: score>=70 AND RSI<=40). Never raises — always returns a summary."""
    results = await analyze_all(db)
    outcomes = []
    for r in results:
        outcome = await send_alert_if_allowed(db, r)
        outcomes.append(outcome)
    sent = [o for o in outcomes if o["status"] == "sent"]
    deduped = [o for o in outcomes if o["status"] == "deduped"]
    blocked = [o for o in outcomes if o["status"] == "rule_blocked"]
    return {
        "ok": True,
        "sent": [o["ticker"] for o in sent],
        "deduped": [o["ticker"] for o in deduped],
        "rule_blocked": [o["ticker"] for o in blocked],
        "total_analyzed": len(results),
    }


@api.get("/alerts/today")
async def alerts_today():
    import pytz
    from config import MARKET_TZ
    tz = pytz.timezone(MARKET_TZ)
    today_key = datetime.now(tz).strftime("%Y-%m-%d")
    cursor = db.alert_log.find({"date": today_key}, {"_id": 0}).sort("timestamp", -1)
    docs = await cursor.to_list(length=100)
    return {"date": today_key, "alerts": docs}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Starting Stock Dip Analyzer")
    try:
        await ensure_alert_log_index(db)
    except Exception as e:
        logger.warning(f"alert_log index setup failed: {e}")
    try:
        start_scheduler(analyze_all, db)
    except Exception as e:
        logger.exception(f"scheduler start failed: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    shutdown_scheduler()
    client.close()
