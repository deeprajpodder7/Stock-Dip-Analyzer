# PRODUCTION-GRADE SCORER

from __future__ import annotations
import math
import pandas as pd

# ---------------- CONFIG ----------------
STRONG_SCORE = 80
BUY_SCORE = 70
ACCUMULATE_SCORE = 60


# ---------------- CORE SCORING ----------------
def _drawdown_score(drawdown_pct: float) -> float:
    dd = abs(drawdown_pct)

    if dd >= 35:
        return 100
    if dd >= 30:
        return 90
    if dd >= 25:
        return 80
    if dd >= 20:
        return 65
    if dd >= 15:
        return 50
    if dd >= 10:
        return 30
    return 10


def _rsi_score(rsi_val: float) -> float:
    if rsi_val <= 25:
        return 100
    if rsi_val <= 30:
        return 85
    if rsi_val <= 35:
        return 70
    if rsi_val <= 40:
        return 50
    if rsi_val <= 50:
        return 25
    return 0


def _ma_score(price: float, ma50: float | None, ma200: float | None) -> float:
    score = 0

    if ma50 and price < ma50:
        score += 40

    if ma200 and price < ma200:
        score += 60

    return min(100, score)


def _market_confidence(close: pd.Series) -> float:
    if len(close) < 60:
        return 50

    returns = close.pct_change().dropna()
    recent_vol = returns.tail(20).std()
    long_vol = returns.std()

    if not recent_vol or not long_vol:
        return 50

    ratio = recent_vol / long_vol

    if ratio < 0.7:
        return 90
    if ratio < 1:
        return 70
    if ratio < 1.3:
        return 50
    return 30


# ---------------- INTELLIGENT BOOST ----------------
def _conviction_boost(score, rsi, drawdown):
    boost = 0

    if rsi < 30 and abs(drawdown) > 20:
        boost += 10

    if rsi < 25 and abs(drawdown) > 25:
        boost += 10

    return boost


# ---------------- CLASSIFICATION ----------------
def classify(score: float) -> str:
    if score >= STRONG_SCORE:
        return "Strong"
    if score >= BUY_SCORE:
        return "Buy"
    if score >= ACCUMULATE_SCORE:
        return "Accumulate"
    return "Weak"


def recommendation(signal: str, score: float) -> str:
    if signal == "Strong":
        return "High conviction dip — strong buy opportunity."
    if signal == "Buy":
        return "Good dip — start buying in parts."
    if signal == "Accumulate":
        return "Mild dip — accumulate slowly."
    return "No meaningful opportunity."


def action(signal: str) -> str:
    return signal


def build_reasons(price, drawdown, rsi, ma50, ma200):
    reasons = []

    if abs(drawdown) > 25:
        reasons.append("Deep correction from highs")
    elif abs(drawdown) > 15:
        reasons.append("Moderate correction")
    else:
        reasons.append("Near highs")

    if rsi < 30:
        reasons.append("Oversold RSI")
    elif rsi < 40:
        reasons.append("Weak momentum")
    else:
        reasons.append("Neutral momentum")

    if ma50 and price < ma50:
        reasons.append("Below MA50")

    if ma200 and price < ma200:
        reasons.append("Below MA200")

    return reasons


# ---------------- MAIN ----------------
def analyze_dataframe(ticker: str, df: pd.DataFrame) -> dict:
    close = df["Close"].dropna()

    if len(close) < 30:
        return {"ticker": ticker, "score": 0, "signal_strength": "Weak"}

    price = float(close.iloc[-1])
    prev = float(close.iloc[-2])

    high = float(close.max())
    drawdown = (price - high) / high * 100

    rsi = float(df["RSI"].iloc[-1])
    ma50 = float(df["MA50"].iloc[-1]) if "MA50" in df else None
    ma200 = float(df["MA200"].iloc[-1]) if "MA200" in df else None

    s1 = _drawdown_score(drawdown)
    s2 = _rsi_score(rsi)
    s3 = _ma_score(price, ma50, ma200)
    s4 = _market_confidence(close)

    base_score = 0.35*s1 + 0.25*s2 + 0.2*s3 + 0.2*s4

    boost = _conviction_boost(base_score, rsi, drawdown)

    score = round(min(100, base_score + boost), 1)

    signal = classify(score)

    return {
        "ticker": ticker,
        "price": round(price, 2),
        "previous_price": round(prev, 2),
        "change_percent": round((price-prev)/prev*100, 2),
        "drawdown_percent": round(drawdown, 2),
        "rsi": round(rsi, 2),
        "score": score,
        "signal_strength": signal,
        "action": action(signal),
        "confidence": round(score/100, 2),
        "recommendation": recommendation(signal, score),
        "reasons": build_reasons(price, drawdown, rsi, ma50, ma200),
    }
