"""Dip detection scoring engine.

Score 0-100 combining:
  Drawdown (30%), MA position (25%), RSI (25%), Market confidence (20%).

Classification:
  Strong: score >= 70
  Medium: 40 <= score < 70
  Weak:   score < 40
"""
from __future__ import annotations
import math
import pandas as pd
from config import W_DRAWDOWN, W_MA, W_RSI, W_CONF, STRONG_SCORE, MEDIUM_SCORE


def _drawdown_score(drawdown_pct: float) -> float:
    """Drawdown-based score (0-100). drawdown_pct is positive value."""
    dd = abs(drawdown_pct)
    if dd >= 25:
        return 100
    if dd >= 20:
        return 85
    if dd >= 15:
        return 70
    if dd >= 10:
        return 55
    if dd >= 5:
        return 30
    return max(0, dd * 4)  # gentle ramp for <5%


def _ma_score(price: float, ma50: float | None, ma200: float | None) -> float:
    """MA position score. Below MA50=signal, below MA200=strong."""
    score = 0
    if ma50 and price < ma50:
        # how far below MA50
        diff = (ma50 - price) / ma50 * 100
        score += min(50, 20 + diff * 2)
    if ma200 and price < ma200:
        diff = (ma200 - price) / ma200 * 100
        score += min(50, 25 + diff * 2)
    return min(100, score)


def _rsi_score(rsi_val: float) -> float:
    """RSI score: <30 strong, <35 medium, <45 weak."""
    if rsi_val <= 25:
        return 100
    if rsi_val <= 30:
        return 85
    if rsi_val <= 35:
        return 65
    if rsi_val <= 45:
        return 35
    if rsi_val <= 55:
        return 15
    return 0


def _market_confidence(close: pd.Series) -> float:
    """Heuristic market confidence based on recent volatility vs historical.
    Lower realised volatility last 20 days relative to 252 days = higher confidence.
    Returns 0-100.
    """
    if len(close) < 60:
        return 50
    returns = close.pct_change().dropna()
    recent_vol = returns.tail(20).std()
    long_vol = returns.tail(252).std() if len(returns) >= 252 else returns.std()
    if not recent_vol or not long_vol or math.isnan(recent_vol) or math.isnan(long_vol):
        return 50
    ratio = recent_vol / long_vol
    # ratio < 1 means calm => high confidence; ratio > 1 => turbulent
    if ratio <= 0.7:
        return 90
    if ratio <= 0.9:
        return 75
    if ratio <= 1.1:
        return 60
    if ratio <= 1.3:
        return 40
    return 25


def classify(score: float) -> str:
    if score >= STRONG_SCORE:
        return "Strong"
    if score >= MEDIUM_SCORE:
        return "Medium"
    return "Weak"


def recommendation(signal: str, score: float) -> str:
    if signal == "Strong":
        return "Strong dip - good for long-term accumulation."
    if signal == "Medium":
        return "Moderate dip - consider staggered entry."
    return "No meaningful dip - wait for better opportunity."


def analyze_dataframe(ticker: str, df: pd.DataFrame) -> dict:
    """Analyze a ticker given OHLC dataframe with 'Close' column + pre-computed indicators.
    df must have: Close, RSI, MA50, MA200 columns."""
    close = df["Close"].dropna()
    if len(close) < 30:
        return {
            "ticker": ticker,
            "error": "Insufficient data",
            "price": None,
            "previous_price": None,
            "drawdown_percent": None,
            "rsi": None,
            "score": 0,
            "signal_strength": "Weak",
            "recommendation": "Insufficient data",
        }

    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) >= 2 else price

    # 52-week high drawdown
    year_window = close.tail(252) if len(close) >= 252 else close
    high_52w = float(year_window.max())
    drawdown_pct = (price - high_52w) / high_52w * 100  # negative

    rsi_val = float(df["RSI"].dropna().iloc[-1]) if df["RSI"].dropna().size else 50.0
    ma50_val = float(df["MA50"].dropna().iloc[-1]) if df["MA50"].dropna().size else None
    ma200_val = float(df["MA200"].dropna().iloc[-1]) if df["MA200"].dropna().size else None

    s_dd = _drawdown_score(drawdown_pct)
    s_ma = _ma_score(price, ma50_val, ma200_val)
    s_rsi = _rsi_score(rsi_val)
    s_conf = _market_confidence(close)

    score = W_DRAWDOWN * s_dd + W_MA * s_ma + W_RSI * s_rsi + W_CONF * s_conf
    score = round(float(score), 1)
    signal = classify(score)

    return {
        "ticker": ticker,
        "price": round(price, 2),
        "previous_price": round(prev, 2),
        "change_percent": round((price - prev) / prev * 100, 2) if prev else 0,
        "high_52w": round(high_52w, 2),
        "drawdown_percent": round(drawdown_pct, 2),
        "rsi": round(rsi_val, 2),
        "ma50": round(ma50_val, 2) if ma50_val else None,
        "ma200": round(ma200_val, 2) if ma200_val else None,
        "score": score,
        "signal_strength": signal,
        "recommendation": recommendation(signal, score),
        "components": {
            "drawdown_score": round(s_dd, 1),
            "ma_score": round(s_ma, 1),
            "rsi_score": round(s_rsi, 1),
            "confidence_score": round(s_conf, 1),
        },
    }
