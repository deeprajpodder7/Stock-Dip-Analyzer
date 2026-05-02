"""Market-aware background scheduler.

Runs hourly analysis during Indian market hours (9:30-15:30 IST) plus a post-close run.
Dedupes strong dip alerts per ticker per day.
"""
import logging
from datetime import datetime, timezone
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import MARKET_TZ
from notifier import send_strong_dip_alert

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_status = {
    "running": False,
    "last_run": None,
    "last_run_ist": None,
    "last_alerts": [],
    "next_run": None,
}


def get_status() -> dict:
    """Return a copy of scheduler status."""
    return dict(_status)


def _is_market_hours_now() -> bool:
    tz = pytz.timezone(MARKET_TZ)
    now = datetime.now(tz)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    start = now.replace(hour=9, minute=30, second=0, microsecond=0)
    end = now.replace(hour=15, minute=45, second=0, microsecond=0)
    return start <= now <= end


async def _run_analysis_job(analyze_func, db):
    """Internal wrapper that runs analysis and dispatches alerts with dedupe."""
    try:
        tz = pytz.timezone(MARKET_TZ)
        now_ist = datetime.now(tz)
        logger.info(f"[scheduler] running analysis at {now_ist.isoformat()}")
        results = await analyze_func(db)
        today_key = now_ist.strftime("%Y-%m-%d")
        alerts_sent = []
        for r in results:
            if r.get("signal_strength") == "Strong" and r.get("score", 0) >= 70:
                ticker = r["ticker"]
                # Dedupe via mongo collection alert_log
                existing = await db.alert_log.find_one(
                    {"ticker": ticker, "date": today_key}, {"_id": 0}
                )
                if existing:
                    logger.info(f"[scheduler] dedupe: already alerted {ticker} today")
                    continue
                ok = send_strong_dip_alert(r)
                await db.alert_log.insert_one({
                    "ticker": ticker,
                    "date": today_key,
                    "score": r.get("score"),
                    "sent": bool(ok),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                if ok:
                    alerts_sent.append(ticker)
        _status["last_run"] = datetime.now(timezone.utc).isoformat()
        _status["last_run_ist"] = now_ist.isoformat()
        _status["last_alerts"] = alerts_sent
        if _scheduler:
            jobs = _scheduler.get_jobs()
            if jobs:
                nxt = min(j.next_run_time for j in jobs if j.next_run_time)
                _status["next_run"] = nxt.isoformat() if nxt else None
    except Exception as e:
        logger.exception(f"[scheduler] analysis job failed: {e}")


def start_scheduler(analyze_func, db):
    """Start AsyncIO scheduler. analyze_func: async callable(db)->list[dict]."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    tz = pytz.timezone(MARKET_TZ)
    sched = AsyncIOScheduler(timezone=tz)

    # Hourly during market hours on weekdays: 10:00, 11:00, 12:00, 13:00, 14:00, 15:00 IST
    sched.add_job(
        _run_analysis_job,
        CronTrigger(day_of_week="mon-fri", hour="10-15", minute=0, timezone=tz),
        args=[analyze_func, db],
        id="hourly_analysis",
        replace_existing=True,
    )
    # Post-close run at 15:45 IST weekdays
    sched.add_job(
        _run_analysis_job,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=45, timezone=tz),
        args=[analyze_func, db],
        id="post_close_analysis",
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    _status["running"] = True
    jobs = sched.get_jobs()
    if jobs:
        nxt = min(j.next_run_time for j in jobs if j.next_run_time)
        _status["next_run"] = nxt.isoformat() if nxt else None
    logger.info("[scheduler] started with jobs: hourly_analysis, post_close_analysis")
    return sched


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
        _status["running"] = False
