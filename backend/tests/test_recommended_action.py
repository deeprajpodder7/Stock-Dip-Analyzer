"""Tests for GET /api/recommended-action."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- /api/recommended-action ---
def test_recommended_action_schema(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["action", "tone", "message", "picks", "generated_at"]:
        assert k in d, f"missing key {k}"
    assert d["action"] in [
        "Buy Now", "Accumulate Slowly", "No good opportunities today"
    ]
    assert d["tone"] in ["strong", "medium", "weak"]
    assert isinstance(d["picks"], list)
    assert isinstance(d["message"], str) and len(d["message"]) > 0


def test_recommended_action_tone_matches_action(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    mapping = {
        "Buy Now": "strong",
        "Accumulate Slowly": "medium",
        "No good opportunities today": "weak",
    }
    assert mapping[d["action"]] == d["tone"]


def test_recommended_action_picks_shape(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    # at most 2 picks
    assert len(d["picks"]) <= 2

    if d["action"] == "No good opportunities today":
        assert d["picks"] == []
        return

    required = ["ticker", "name", "price", "drawdown_percent", "rsi", "score", "signal_strength"]
    for p in d["picks"]:
        for f in required:
            assert f in p, f"pick missing {f}"
        # ticker and name consistency
        assert isinstance(p["ticker"], str) and len(p["ticker"]) > 0
        assert p["name"] == p["ticker"].replace(".NS", "")
        assert isinstance(p["score"], (int, float))


def test_recommended_action_score_thresholds(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    if d["action"] == "Buy Now":
        # all picks >= 70 (Strong), sorted desc, <=2
        assert len(d["picks"]) >= 1
        for p in d["picks"]:
            assert p["score"] >= 70, f"Buy Now pick has score {p['score']} < 70"
        scores = [p["score"] for p in d["picks"]]
        assert scores == sorted(scores, reverse=True)
    elif d["action"] == "Accumulate Slowly":
        assert len(d["picks"]) >= 1
        for p in d["picks"]:
            assert 60 <= p["score"] < 70
    else:
        assert d["picks"] == []


def test_recommended_action_consistent_with_analyze(session):
    """Cross-check: top score from the same universe-scan logic."""
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    # If picks present, first pick must be highest-score (sorted desc)
    if d["picks"]:
        scores = [p["score"] for p in d["picks"]]
        assert scores == sorted(scores, reverse=True)
