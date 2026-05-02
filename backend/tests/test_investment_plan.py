"""Tests for /api/investment-plan endpoint."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://value-signal-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- allocation shape & rules ---
def test_investment_plan_default_budget_5000(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 5000}, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["budget"] == 5000
    assert "generated_at" in d
    assert "allocations" in d and isinstance(d["allocations"], list)
    assert "total_allocated" in d
    assert "reason" in d and isinstance(d["reason"], str)
    assert "qualifying_count" in d

    allocs = d["allocations"]
    assert 1 <= len(allocs) <= 2, f"expected 1-2 allocations, got {len(allocs)}"

    required_fields = [
        "ticker", "name", "amount", "percent", "score",
        "signal_strength", "price", "estimated_shares", "is_fallback",
    ]
    for a in allocs:
        for f in required_fields:
            assert f in a, f"missing field {f} in allocation"
        assert isinstance(a["ticker"], str) and a["ticker"]
        assert isinstance(a["name"], str)
        assert isinstance(a["amount"], int)
        assert a["amount"] > 0
        assert isinstance(a["percent"], (int, float))
        assert isinstance(a["is_fallback"], bool)

    # Sum equals budget
    total = sum(a["amount"] for a in allocs)
    assert total == d["total_allocated"]
    assert total == 5000, f"sum of allocations {total} != budget 5000"


def test_investment_plan_score_threshold_and_ordering(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 5000}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    allocs = d["allocations"]
    fallback = allocs[0].get("is_fallback") if allocs else False
    if not fallback:
        # Only stocks with score >= 60 are selected
        for a in allocs:
            assert a["score"] >= 60, f"{a['ticker']} score {a['score']} < 60"
        # Higher score => higher amount (when >1)
        if len(allocs) == 2:
            if allocs[0]["score"] > allocs[1]["score"]:
                assert allocs[0]["amount"] >= allocs[1]["amount"]


def test_investment_plan_rounding_nearest_100(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 5000}, timeout=120)
    d = r.json()
    allocs = d["allocations"]
    # total must match budget exactly (diff absorbed by last)
    assert sum(a["amount"] for a in allocs) == 5000
    # all amounts except possibly last are multiples of 100
    if len(allocs) > 1:
        for a in allocs[:-1]:
            assert a["amount"] % 100 == 0, f"{a['ticker']} amount {a['amount']} not rounded to 100"


def test_investment_plan_budget_10000_scales(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 10000}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["budget"] == 10000
    total = sum(a["amount"] for a in d["allocations"])
    assert total == 10000
    assert 1 <= len(d["allocations"]) <= 2


def test_investment_plan_budget_too_low_400(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 100}, timeout=30)
    assert r.status_code == 400
    d = r.json()
    assert "detail" in d
    assert "500" in d["detail"] or "at least" in d["detail"].lower()


def test_investment_plan_budget_499_400(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 499}, timeout=30)
    assert r.status_code == 400


def test_investment_plan_budget_500_ok(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 500}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["budget"] == 500
    assert sum(a["amount"] for a in d["allocations"]) == 500


def test_investment_plan_estimated_shares_reasonable(session):
    r = session.get(f"{API}/investment-plan", params={"budget": 5000}, timeout=120)
    d = r.json()
    for a in d["allocations"]:
        if a.get("price") and a.get("estimated_shares") is not None:
            # shares = floor(amount / price)
            expected = int(a["amount"] // a["price"])
            assert a["estimated_shares"] == expected


def test_investment_plan_fallback_semantics_present_when_qualifying_zero(session):
    """If qualifying_count == 0 -> fallback NIFTYBEES.NS allocation with full budget."""
    r = session.get(f"{API}/investment-plan", params={"budget": 5000}, timeout=120)
    d = r.json()
    if d["qualifying_count"] == 0:
        assert len(d["allocations"]) == 1
        a = d["allocations"][0]
        assert a["ticker"] == "NIFTYBEES.NS"
        assert a["is_fallback"] is True
        assert a["amount"] == 5000
        assert a["percent"] == 100.0
    else:
        # non-fallback path: none should be fallback
        for a in d["allocations"]:
            assert a["is_fallback"] is False
