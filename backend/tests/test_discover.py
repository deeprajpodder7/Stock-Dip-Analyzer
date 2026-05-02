"""Tests for the new GET /api/discover endpoint."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://value-signal-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
DEFAULTS = {"NIFTYBEES.NS", "BANKBEES.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_discover_basic(session):
    # First call may hit yfinance for 40 tickers; give it a generous timeout
    r = session.get(f"{API}/discover", timeout=180)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "results" in d
    assert "universe_size" in d and d["universe_size"] == 40
    assert "strong_count" in d and isinstance(d["strong_count"], int)
    assert "generated_at" in d

    results = d["results"]
    assert isinstance(results, list)
    # results sorted by score desc
    scores = [r0.get("score", 0) for r0 in results]
    assert scores == sorted(scores, reverse=True)


def test_discover_default_excludes_weak(session):
    r = session.get(f"{API}/discover", timeout=120)
    assert r.status_code == 200
    d = r.json()
    for r0 in d["results"]:
        # should only contain Medium / Strong
        assert r0.get("signal_strength") in ("Medium", "Strong"), (
            f"Weak signal leaked into default discover: {r0}"
        )


def test_discover_include_weak(session):
    r = session.get(f"{API}/discover", params={"include_weak": "true"}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    signals = {r0.get("signal_strength") for r0 in d["results"]}
    # In practice the 40-ticker universe will almost always include at least one Weak
    # signal when include_weak=true. We allow any of the 3 strengths to be present.
    assert signals.issubset({"Weak", "Medium", "Strong"})
    # include_weak should return >= default (non-weak) result count
    r2 = session.get(f"{API}/discover", timeout=120).json()
    assert len(d["results"]) >= len(r2["results"])


def test_discover_top_limit(session):
    r = session.get(f"{API}/discover", params={"top": 5, "include_weak": "true"}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert len(d["results"]) <= 5


def test_discover_in_watchlist_flag(session):
    r = session.get(f"{API}/discover", params={"include_weak": "true", "top": 40}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    tickers = {r0["ticker"]: r0 for r0 in d["results"]}
    # Default tickers that appear in universe must have in_watchlist=True
    for t in DEFAULTS:
        if t in tickers:
            assert tickers[t]["in_watchlist"] is True, f"{t} should be flagged in_watchlist"
            assert tickers[t]["is_default"] is True
    # At least one default should be present
    assert any(t in tickers for t in DEFAULTS)


def test_discover_result_shape(session):
    r = session.get(f"{API}/discover", params={"include_weak": "true", "top": 3}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert len(d["results"]) > 0
    r0 = d["results"][0]
    for field in ["ticker", "price", "drawdown_percent", "rsi", "score",
                  "signal_strength", "in_watchlist", "is_default"]:
        assert field in r0, f"missing field {field} in discover result"
