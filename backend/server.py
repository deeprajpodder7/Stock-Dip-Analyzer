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


async def get_watchlist():
    if not db:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]

    try:
        docs = await db.watchlist_custom.find({}, {"_id": 0}).to_list(50)
        custom = [d["ticker"] for d in docs]

        return (
            [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]
            + [{"ticker": t, "is_default": False} for t in custom]
        )
    except Exception:
        return [{"ticker": t, "is_default": True} for t in DEFAULT_TICKERS]


# ---------------- App ----------------
app = FastAPI()
api = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup():
    await init_db()


# -------- Watchlist --------
@api.get("/watchlist")
async def watchlist():
    return await get_watchlist()


# -------- Analyze --------
@api.get("/analyze")
async def analyze():
    tasks = [_analyze_one(t) for t in MARKET_UNIVERSE[:6]]
    results = await safe_gather(tasks)

    valid = [r for r in results if isinstance(r, dict)]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {"results": valid}


# -------- Recommended Action --------
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
            "message": "No good opportunities right now",
            "tone": "weak"
        }

    top_score = picks[0].get("score", 0)

    if top_score >= 70:
        return {
            "picks": picks,
            "action": "Buy Now",
            "message": "Strong dip opportunity",
            "tone": "strong"
        }
    elif top_score >= 60:
        return {
            "picks": picks,
            "action": "Accumulate",
            "message": "Moderate opportunity",
            "tone": "medium"
        }
    else:
        return {
            "picks": [],
            "action": "Wait",
            "message": "No strong signal",
            "tone": "weak"
        }


# -------- Investment Plan --------
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
            "allocations": [{"ticker": "NIFTYBEES.NS", "amount": budget}],
            "reason": "No opportunities"
        }

    total_score = sum(p.get("score", 0) for p in picks)

    allocations = []
    for p in picks:
        amt = budget * p["score"] / total_score
        allocations.append({
            "ticker": p["ticker"],
            "amount": int(amt)
        })

    return {
        "budget": budget,
        "allocations": allocations,
        "reason": "Top picks"
    }


# -------- CORS --------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api)
