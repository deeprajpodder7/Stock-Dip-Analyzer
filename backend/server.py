from __future__ import annotations
import os
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    DEFAULT_TICKERS,
    MAX_CUSTOM_TICKERS,
    NTFY_TOPIC,
    NTFY_BASE,
    DISCOVER_TOP_N,
    MARKET_UNIVERSE,
)
from data import get_history, validate_ticker_symbol
from scorer import analyze_dataframe
from notifier import send_strong_dip_alert

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stock_dip_analyzer")

# ------------------ MongoDB ------------------
mongo_url = os.environ.get("MONGO_URL")

client = AsyncIOMotorClient(
    mongo_url,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=5000,
)

db = None


async def init_db():
    global db
    try:
        await client.admin.command("ping")
        print("MongoDB connected ✅")
        db = client[os.environ["DB_NAME"]]
    except Exception as e:
        print("MongoDB connection failed ❌", e)
        db = None


# ------------------ Helpers ------------------

async def safe_gather(tasks):
    try:
        return await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=20,
        )
    except asyncio.TimeoutError:
        print("Timeout occurred")
        return []


async def _analyze_one(ticker: str):
    df = await get_history(db, ticker)
    if df is None or df.empty:
        return {"ticker": ticker, "score": 0, "signal_strength": "Weak"}
    return analyze_dataframe(ticker, df)


async def get_watchlist():
    if not db:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]

    cursor = db.watchlist_custom.find({}, {"_id": 0})
    docs = await cursor.to_list(length=MAX_CUSTOM_TICKERS)
    custom = [d["ticker"] for d in docs]

    return (
        [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]
        + [{"ticker": t, "is_default": False} for t in custom]
    )


# ------------------ FastAPI ------------------

app = FastAPI()
api = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup():
    await init_db()


# ------------------ Models ------------------

class TickerAdd(BaseModel):
    ticker: str = Field(...)


# ------------------ Endpoints ------------------

@api.get("/")
async def root():
    return {"status": "ok"}


# -------- DISCOVER --------
@api.get("/discover")
async def discover():
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [
        r for r in results if isinstance(r, dict) and not r.get("error")
    ]

    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "results": valid[:DISCOVER_TOP_N],
        "generated_at": datetime.now(timezone.utc),
    }


# -------- RECOMMENDED ACTION --------
@api.get("/recommended-action")
async def recommended_action():
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [
        r for r in results if isinstance(r, dict) and not r.get("error")
    ]

    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    picks = valid[:2]

    return {
        "picks": picks,
        "message": "Top opportunities",
    }


# -------- INVESTMENT PLAN --------
@api.get("/investment-plan")
async def investment_plan(budget: int = 5000):
    try:
        tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
        results = await safe_gather(tasks)

        candidates = [
            r for r in results
            if isinstance(r, dict) and r.get("score", 0) >= 60
        ]

        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        picks = candidates[:2]

        # ---- FALLBACK ----
        if not picks:
            return {
                "budget": budget,
                "allocations": [{
                    "ticker": "NIFTYBEES.NS",
                    "amount": budget,
                    "percent": 100,
                }],
                "reason": "No good opportunities",
                "total_allocated": budget,
            }

        # ---- NORMAL ----
        total_score = sum(p.get("score", 0) for p in picks)

        if total_score == 0:
            return {
                "budget": budget,
                "allocations": [],
                "reason": "Invalid scoring",
                "total_allocated": 0,
            }

        allocations = []

        for p in picks:
            amt = budget * p["score"] / total_score
            allocations.append({
                "ticker": p["ticker"],
                "amount": int(amt),
                "percent": round(amt / budget * 100, 1),
            })

        return {
            "budget": budget,
            "allocations": allocations,
            "total_allocated": budget,
            "reason": "Top picks",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "budget": budget,
            "allocations": [],
            "reason": "Error generating plan",
            "total_allocated": 0,
        }


# ------------------ Watchlist ------------------

@api.get("/watchlist")
async def watchlist():
    return await get_watchlist()


# ------------------ Notifications ------------------

@api.post("/test-notification")
async def test_notification():
    ok = send_strong_dip_alert({
        "ticker": "TEST.NS",
        "score": 80
    })
    return {"ok": ok}


# ------------------ Status ------------------

@api.get("/status")
async def status():
    return {
        "db_connected": db is not None,
        "time": datetime.now(timezone.utc),
    }


# ------------------ CORS ------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api)
