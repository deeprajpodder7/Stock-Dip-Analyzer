"""Tests for scheduler._run_analysis_job — verifies it delegates to alerts.send_alert_if_allowed
and never raises NameError. Also verifies last_alerts in scheduler status is populated.

This test was added in iteration_6 to verify the fix for the CRITICAL bug flagged in
iteration_5: scheduler.py was calling undefined `send_strong_dip_alert` symbol.
"""
from __future__ import annotations
import os
import sys
import asyncio
import importlib
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/app/backend")


# --- Static import sanity ---
class TestSchedulerImportsAreClean:
    def test_scheduler_module_imports_cleanly(self):
        """Should import without raising — proves no syntax / NameError at import time."""
        import scheduler  # noqa: F401
        importlib.reload(scheduler)

    def test_scheduler_does_not_reference_send_strong_dip_alert(self):
        """The legacy direct call to send_strong_dip_alert should be GONE from scheduler.py.
        The only sender allowed is `send_alert_if_allowed` (delegated)."""
        with open("/app/backend/scheduler.py", "r") as f:
            src = f.read()
        assert "send_strong_dip_alert" not in src, (
            "scheduler.py must NOT reference send_strong_dip_alert directly anymore. "
            "It should fully delegate to alerts.send_alert_if_allowed."
        )
        assert "send_alert_if_allowed" in src, (
            "scheduler.py must import + call alerts.send_alert_if_allowed"
        )


# --- Functional test: run the private job directly ---
class TestRunAnalysisJobDelegates:
    def test_run_analysis_job_routes_through_send_alert_if_allowed(self):
        """Invoke scheduler._run_analysis_job with a fake analyze_func and a fake db.
        Verify each result is routed through alerts.send_alert_if_allowed and that
        the 'sent' tickers get reflected in scheduler._status['last_alerts'].
        """
        import scheduler

        fake_results = [
            {"ticker": "AAA.NS", "signal_strength": "Strong", "score": 85, "rsi": 25},
            {"ticker": "BBB.NS", "signal_strength": "Strong", "score": 75, "rsi": 38},
            {"ticker": "CCC.NS", "signal_strength": "Strong", "score": 65, "rsi": 30},  # blocked: score<70
            {"ticker": "DDD.NS", "signal_strength": "Strong", "score": 90, "rsi": 50},  # blocked: rsi>40
        ]

        async def fake_analyze(_db):
            return fake_results

        # Mock send_alert_if_allowed at the scheduler module level (where it's imported)
        async def fake_send_alert_if_allowed(db, analysis):
            t = analysis["ticker"]
            if t == "AAA.NS":
                return {"status": "sent", "ticker": t}
            if t == "BBB.NS":
                return {"status": "deduped", "ticker": t}
            return {"status": "rule_blocked", "ticker": t, "reason": "x"}

        with patch.object(scheduler, "send_alert_if_allowed", side_effect=fake_send_alert_if_allowed):
            # Run the job — must NOT raise NameError or any other exception
            asyncio.run(scheduler._run_analysis_job(fake_analyze, db=object()))

        status = scheduler.get_status()
        # last_alerts should contain only the 'sent' ticker
        assert "AAA.NS" in status["last_alerts"], f"expected AAA.NS in last_alerts, got {status['last_alerts']}"
        assert "BBB.NS" not in status["last_alerts"], "deduped ticker must not be in last_alerts"
        assert "CCC.NS" not in status["last_alerts"], "rule_blocked ticker must not be in last_alerts"
        assert "DDD.NS" not in status["last_alerts"]

    def test_run_analysis_job_swallows_inner_errors(self):
        """If analyze_func raises, the job should still not propagate (try/except wraps everything)."""
        import scheduler

        async def broken_analyze(_db):
            raise RuntimeError("simulated analysis failure")

        # Must not raise
        asyncio.run(scheduler._run_analysis_job(broken_analyze, db=object()))

    def test_run_analysis_job_with_real_send_alert_if_allowed_does_not_nameerror(self):
        """Smoke test: even with the real alerts.send_alert_if_allowed, the job shouldn't NameError.
        We pass a fake db (AsyncMock) and a fake analyze_func returning rule-blockable rows so no
        real Mongo / network I/O happens (alerts gate them out before any db call)."""
        import scheduler

        async def fake_analyze(_db):
            # All rule_blocked → no DB writes / no notifier I/O
            return [
                {"ticker": "ZZZ.NS", "signal_strength": "Medium", "score": 50, "rsi": 60},
                {"ticker": "YYY.NS", "signal_strength": "Strong", "score": 60, "rsi": 30},
            ]

        fake_db = AsyncMock()
        # Run — must complete without NameError or unhandled exceptions
        asyncio.run(scheduler._run_analysis_job(fake_analyze, fake_db))


# --- Integration: /api/alerts/today sort key alignment ---
class TestAlertsTodayUsesLastAlertedAtSort:
    def test_server_sort_key_is_last_alerted_at(self):
        """server.py /api/alerts/today must sort by 'last_alerted_at' (the field alerts.py writes),
        not by the legacy 'timestamp' field."""
        with open("/app/backend/server.py", "r") as f:
            src = f.read()
        assert ".sort(\"last_alerted_at\"" in src or ".sort('last_alerted_at'" in src, (
            "alerts/today endpoint must sort by last_alerted_at"
        )
