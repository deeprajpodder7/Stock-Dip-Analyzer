"""ntfy notification client. Fails silently on errors."""
import logging
import requests
from config import NTFY_TOPIC, NTFY_BASE

logger = logging.getLogger(__name__)


def send_strong_dip_alert(analysis: dict) -> bool:
    """Send an ntfy alert for a strong dip. Returns True on success, False otherwise.
    Never raises."""
    try:
        topic = NTFY_TOPIC
        url = f"{NTFY_BASE.rstrip('/')}/{topic}"
        body = (
            f"🚨 Strong Dip Detected\n"
            f"Ticker: {analysis.get('ticker')}\n"
            f"Price: ₹{analysis.get('price')}\n"
            f"Drop: {analysis.get('drawdown_percent')}%\n"
            f"RSI: {analysis.get('rsi')}\n"
            f"Score: {analysis.get('score')}/100"
        )
        headers = {
            "Title": "📉 Stock Dip Alert",
            "Priority": "urgent",
            "Tags": "money,chart_with_downwards_trend",
        }
        r = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=10)
        if 200 <= r.status_code < 300:
            logger.info(f"ntfy alert sent for {analysis.get('ticker')}")
            return True
        logger.warning(f"ntfy non-2xx {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        logger.warning(f"ntfy send failed: {e}")
        return False
