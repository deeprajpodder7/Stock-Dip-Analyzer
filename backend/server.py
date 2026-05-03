from __future__ import annotations
import os
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

from config import DEFAULT_TICKERS, MARKET_UNIVERSE
from data import get_history
from scorer import analyze_dataframe

# ---------------- Mongo ----------------
mongo_url = os.environ.get("MONGO_URL")

if mongo_url:
    client = AsyncIOMotorClient(
        mongo_url,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000,
    )
else:
    client = None

db = None


async def init_db():
    global db

    if not client:
        print("Mongo not configured ⚠️")
        db = None
        return

    try:
        await client.admin.command("ping")
        print("MongoDB connected ✅")
        db = client[os.environ.get("DB_NAME", "test")]
    except Exception as e:
        print("MongoDB failed ❌", e)
        db = None

# ---------------- Helpers ----------------
async def safe_gather(tasks):
    try:
        return await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=20
        )
    except asyncio.TimeoutError:
        return []


async def _analyze_one(ticker: str):
    try:
        df = await get_history(db, ticker)
        if df is None or df.empty:
            return {"ticker": ticker, "score": 0}
        return analyze_dataframe(ticker, df)
    except Exception:
        return {"ticker": ticker, "score": 0}


async def get_watchlist_safe():
    if not db:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]

    try:
        docs = await db.watchlist_custom.find({}, {"_id": 0}).to_list(50)
        custom = [d.get("ticker") for d in docs if d.get("ticker")]

        return (
            [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]
            + [{"ticker": t, "is_default": False} for t in custom]
        )
    except Exception:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]


# ---------------- App ----------------
app = FastAPI(title="Stock Dip Analyzer")
api = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup():
    await init_db()


# ---------------- STATUS ----------------
@api.get("/status")
async def status():
    return {
        "scheduler": {"running": True},
        "notifier": {"enabled": True}
    }


# ---------------- WATCHLIST ----------------
@api.get("/watchlist")
async def watchlist():
    try:
        return await get_watchlist_safe()
    except Exception:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]


# ---------------- ANALYZE ----------------
@api.get("/analyze")
async def analyze():
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [r for r in results if isinstance(r, dict)]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {"results": valid}


# ---------------- DISCOVER ----------------
@api.get("/discover")
async def discover(top: int = 12, include_weak: bool = False):
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:top]]
    results = await safe_gather(tasks)

    valid = [r for r in results if isinstance(r, dict)]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    strong = [r for r in valid if r.get("score", 0) >= 70]

    return {
        "results": valid,
        "strong_count": len(strong),
        "universe_size": len(MARKET_UNIVERSE)
    }


# ---------------- RECOMMENDED ----------------
@api.get("/recommended-action")
async def recommended():
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [r for r in results if isinstance(r, dict)]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    picks = valid[:2]

    if not picks:
        return {
            "picks": [],
            "action": "Wait",
            "message": "No good opportunities",
            "tone": "weak"
        }

    top_score = picks[0].get("score", 0)

    if top_score >= 80:
        action = "Strong Buy"
        tone = "strong"
    elif top_score >= 70:
        action = "Buy"
        tone = "strong"
    elif top_score >= 60:
        action = "Accumulate"
        tone = "medium"
    else:
        return {
            "picks": [],
            "action": "Wait",
            "message": "No strong signal",
            "tone": "weak"
            }


# ---------------- INVESTMENT PLAN ----------------
@api.get("/investment-plan")
async def investment_plan(budget: int = 5000):
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [
        r for r in results if isinstance(r, dict) and r.get("score", 0) >= 60
    ]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    picks = valid[:2]

    if not picks:
        return {
            "budget": budget,
            "allocations": [{
                "ticker": "NIFTYBEES.NS",
                "amount": budget
            }],
            "total_allocated": budget,
            "reason": "No opportunities",
            "qualifying_count": 0
        }

    total_score = sum(p.get("score", 0) for p in picks)

    allocations = []
    for p in picks:
        amt = int(budget * p["score"] / total_score)
        allocations.append({
            "ticker": p["ticker"],
            "amount": amt
        })

    return {
        "budget": budget,
        "allocations": allocations,
        "total_allocated": sum(a["amount"] for a in allocations),
        "reason": "Top picks",
        "qualifying_count": len(valid)
    }


# ---------------- STOCK DETAIL ----------------
@api.get("/stock/{ticker}")
async def stock_detail(ticker: str):
    try:
        df = await get_history(db, ticker)

        if df is None or df.empty:
            return {"analysis": {}, "history": []}

        analysis = analyze_dataframe(ticker, df)

        history = df.attrs.get("chart", [])

        return {
            "analysis": analysis,
            "history": history
        }

    except Exception:
        return {"analysis": {}, "history": []}


# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api)
