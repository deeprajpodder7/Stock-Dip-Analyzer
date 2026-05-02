"""Tests for GET /api/recommended-action with strict RSI+score gate."""
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


# --- /api/recommended-action schema ---
def test_recommended_action_schema(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["action", "tone", "message", "picks", "generated_at"]:
        assert k in d
    assert d["action"] in [
        "Buy Now", "Accumulate Slowly", "No good opportunities today"
    ]
    assert d["tone"] in ["strong", "medium", "weak"]
    assert isinstance(d["picks"], list)


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
    assert len(d["picks"]) <= 2
    if d["action"] == "No good opportunities today":
        assert d["picks"] == []
        return
    required = ["ticker", "name", "price", "drawdown_percent", "rsi", "score", "signal_strength"]
    for p in d["picks"]:
        for f in required:
            assert f in p
        assert p["name"] == p["ticker"].replace(".NS", "")


# --- NEW strict rules ---
def test_buy_now_requires_score_70_and_rsi_le_40(session):
    """If action=='Buy Now', every pick must have score>=70 AND RSI<=40."""
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    if d["action"] != "Buy Now":
        pytest.skip(f"action is {d['action']} — cannot verify Buy Now gate directly")
    assert len(d["picks"]) >= 1
    for p in d["picks"]:
        assert p["score"] >= 70, f"Buy Now pick {p['ticker']} score={p['score']} < 70"
        assert p["rsi"] is not None, f"Buy Now pick {p['ticker']} has null RSI"
        assert p["rsi"] <= 40, f"Buy Now pick {p['ticker']} RSI={p['rsi']} > 40 (must be oversold)"


def test_buy_now_message_mentions_strict_criteria(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    if d["action"] != "Buy Now":
        pytest.skip("Not Buy Now right now")
    msg = d["message"]
    assert "70" in msg and "40" in msg, f"message must mention score and RSI thresholds: {msg}"


def test_accumulate_pool_rules(session):
    """Every Accumulate pick must either be (60<=score<70) OR (score>=70 AND rsi is None or >40)."""
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    if d["action"] != "Accumulate Slowly":
        pytest.skip(f"action is {d['action']}")
    assert len(d["picks"]) >= 1
    for p in d["picks"]:
        in_medium_band = 60 <= p["score"] < 70
        demoted_strong = p["score"] >= 70 and (p["rsi"] is None or p["rsi"] > 40)
        assert in_medium_band or demoted_strong, (
            f"Accumulate pick {p['ticker']} score={p['score']} rsi={p['rsi']} violates pool rule"
        )


def test_no_pick_below_60(session):
    """Critical invariant: picks NEVER include stocks with score < 60."""
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    for p in d["picks"]:
        assert p["score"] >= 60, f"pick {p['ticker']} score={p['score']} must be >=60"


def test_picks_sorted_desc_by_score(session):
    r = session.get(f"{API}/recommended-action", timeout=180)
    d = r.json()
    if d["picks"]:
        scores = [p["score"] for p in d["picks"]]
        assert scores == sorted(scores, reverse=True)
