"""Tests for new alert module + /api/trigger-alerts + /api/alerts/today."""
import os
import sys
import asyncio
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

# Import alerts helpers directly for unit tests
sys.path.insert(0, "/app/backend")
from alerts import passes_alert_rules, today_ist_key  # noqa: E402


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Unit tests for passes_alert_rules ---
class TestPassesAlertRules:
    def test_strong_score80_rsi30_passes(self):
        a = {"signal_strength": "Strong", "score": 80, "rsi": 30}
        assert passes_alert_rules(a) is True

    def test_score_below_70_fails(self):
        a = {"signal_strength": "Strong", "score": 69, "rsi": 30}
        assert passes_alert_rules(a) is False

    def test_rsi_above_40_fails(self):
        a = {"signal_strength": "Strong", "score": 85, "rsi": 41}
        assert passes_alert_rules(a) is False

    def test_not_strong_fails(self):
        a = {"signal_strength": "Medium", "score": 85, "rsi": 30}
        assert passes_alert_rules(a) is False

    def test_rsi_none_fails(self):
        a = {"signal_strength": "Strong", "score": 85, "rsi": None}
        assert passes_alert_rules(a) is False

    def test_boundary_score70_rsi40_passes(self):
        a = {"signal_strength": "Strong", "score": 70, "rsi": 40}
        assert passes_alert_rules(a) is True

    def test_today_ist_key_format(self):
        key = today_ist_key()
        assert len(key) == 10 and key[4] == "-" and key[7] == "-"


# --- /api/trigger-alerts ---
def test_trigger_alerts_schema(session):
    r = session.post(f"{API}/trigger-alerts", timeout=180)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["ok", "sent", "deduped", "rule_blocked", "total_analyzed"]:
        assert k in d, f"missing {k}"
    assert d["ok"] is True
    assert isinstance(d["sent"], list)
    assert isinstance(d["deduped"], list)
    assert isinstance(d["rule_blocked"], list)
    assert d["total_analyzed"] >= 1


def test_trigger_alerts_dedupes_on_second_call(session):
    """Second call immediately after first should move everything previously sent into 'deduped'."""
    # First call — sends (or not). Capture sent tickers.
    r1 = session.post(f"{API}/trigger-alerts", timeout=180)
    assert r1.status_code == 200
    d1 = r1.json()
    previously_sent = set(d1["sent"]) | set(d1["deduped"])  # all previously logged today

    # Second call immediately
    r2 = session.post(f"{API}/trigger-alerts", timeout=180)
    assert r2.status_code == 200
    d2 = r2.json()
    # Nothing new should be sent the second time
    assert d2["sent"] == [], f"expected no new sends, got {d2['sent']}"
    # Every ticker from first run (sent or deduped) must appear in deduped of second run
    for t in previously_sent:
        assert t in d2["deduped"], f"ticker {t} should be deduped on second call"


# --- /api/alerts/today ---
def test_alerts_today_shape(session):
    # ensure at least one row by triggering alerts first
    session.post(f"{API}/trigger-alerts", timeout=180)
    r = session.get(f"{API}/alerts/today", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "date" in d and "alerts" in d
    assert isinstance(d["alerts"], list)
    if d["alerts"]:
        a = d["alerts"][0]
        for f in ["ticker", "date", "score", "rsi", "sent", "last_alerted_at"]:
            assert f in a, f"alert row missing {f}: {a}"


# --- sanity: /api/trigger-alerts sent tickers all satisfy strict rule ---
def test_trigger_alerts_respects_strict_rule(session):
    """Any ticker in 'sent' must currently satisfy score>=70 AND RSI<=40 AND Strong."""
    # Fresh call
    r = session.post(f"{API}/trigger-alerts", timeout=180)
    d = r.json()
    if not (d["sent"] or d["deduped"]):
        pytest.skip("Nothing passed alert rules right now")
    # Cross-check with /analyze
    an = session.get(f"{API}/analyze", timeout=180).json()
    results = {x["ticker"]: x for x in an["results"]}
    for t in d["sent"] + d["deduped"]:
        row = results.get(t)
        if not row:
            continue
        assert row.get("signal_strength") == "Strong"
        assert row.get("score", 0) >= 70
        assert row.get("rsi") is not None and row["rsi"] <= 40


# --- Mongo index check ---
def test_alert_log_has_unique_index():
    """Verify ensure_alert_log_index created the unique compound index."""
    import pymongo
    mongo_url = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
    db_name = os.environ.get("DB_NAME", "test_database")
    # Attempt to read backend/.env
    try:
        from dotenv import dotenv_values
        env = dotenv_values("/app/backend/.env")
        mongo_url = env.get("MONGO_URL") or mongo_url
        db_name = env.get("DB_NAME") or db_name
    except Exception:
        pass
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    idx = db.alert_log.index_information()
    # Look for unique index on (ticker, date)
    found = False
    for name, info in idx.items():
        keys = info.get("key", [])
        if keys == [("ticker", 1), ("date", 1)] and info.get("unique"):
            found = True
            break
    assert found, f"unique compound index on (ticker,date) not found. indexes={idx}"
    client.close()
