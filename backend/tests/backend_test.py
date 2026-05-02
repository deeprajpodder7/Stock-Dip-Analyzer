"""Backend tests for Stock Dip Analyzer."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://value-signal-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
DEFAULTS = ["NIFTYBEES.NS", "BANKBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_root(session):
    r = session.get(f"{API}/", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["service"] == "Stock Dip Analyzer"
    assert d["status"] == "ok"


def test_status(session):
    r = session.get(f"{API}/status", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["scheduler"]["running"] is True
    assert d["notifier"]["enabled"] is True
    assert d["notifier"]["topic"] == "deepraj-stock-dip-9827"
    assert d["max_custom"] == 10


def test_watchlist_defaults(session):
    r = session.get(f"{API}/watchlist", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["max_custom"] == 10
    tickers = [t["ticker"] for t in d["tickers"] if t["is_default"]]
    for x in DEFAULTS:
        assert x in tickers


def test_analyze(session):
    r = session.get(f"{API}/analyze", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert "results" in d and len(d["results"]) >= 5
    # sorted desc
    scores = [x.get("score", 0) for x in d["results"]]
    assert scores == sorted(scores, reverse=True)
    # fields on at least one
    for r0 in d["results"]:
        if "error" not in r0:
            for f in ["ticker", "price", "drawdown_percent", "rsi", "score", "signal_strength"]:
                assert f in r0
            break


def test_stock_detail(session):
    r = session.get(f"{API}/stock/RELIANCE.NS", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "analysis" in d and "history" in d
    assert len(d["history"]) > 0
    h0 = d["history"][0]
    for k in ["date", "close", "ma50", "ma200", "rsi"]:
        assert k in h0


def test_add_custom_ticker(session):
    # cleanup first
    session.delete(f"{API}/watchlist/HDFCBANK.NS", timeout=30)
    r = session.post(f"{API}/watchlist", json={"ticker": "HDFCBANK.NS"}, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    tickers = [t for t in d["tickers"] if t["ticker"] == "HDFCBANK.NS"]
    assert tickers and tickers[0]["is_default"] is False


def test_add_duplicate(session):
    r = session.post(f"{API}/watchlist", json={"ticker": "HDFCBANK.NS"}, timeout=30)
    assert r.status_code == 400


def test_add_default_rejected(session):
    r = session.post(f"{API}/watchlist", json={"ticker": "RELIANCE.NS"}, timeout=30)
    assert r.status_code == 400


def test_add_invalid_ticker(session):
    r = session.post(f"{API}/watchlist", json={"ticker": "NOTAREAL.NS"}, timeout=60)
    assert r.status_code == 400


def test_delete_default_rejected(session):
    r = session.delete(f"{API}/watchlist/RELIANCE.NS", timeout=30)
    assert r.status_code == 400


def test_delete_custom(session):
    r = session.delete(f"{API}/watchlist/HDFCBANK.NS", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "HDFCBANK.NS" not in [t["ticker"] for t in d["tickers"]]


def test_refresh(session):
    r = session.post(f"{API}/refresh", timeout=180)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert "results" in d


def test_test_notification(session):
    r = session.post(f"{API}/test-notification", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["topic"] == "deepraj-stock-dip-9827"
    assert "ok" in d


def test_alerts_today(session):
    r = session.get(f"{API}/alerts/today", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "date" in d
    assert isinstance(d["alerts"], list)
