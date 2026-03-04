"""
ORACLE NODE v2 — RAPID STRIKE HUMINT SCANNER
ELITE v20 | MEDALLION | ZERO EMOTION

Accepts human intelligence (insider tips, Discord intel) and cross-validates
against live market data. Outputs a clean probability with INSTANT action:
Entry, Size, Take Profit, Stop Loss — in 30 seconds.

TWO MODES:
  1. RAPID STRIKE — Discord intel drops, instant scan, instant action
  2. DEEP SCAN — Full cross-validation with all APIs (original mode)

Usage:
    from module_oracle_node import render_oracle_node
    render_oracle_node(st)
"""

import streamlit as st
import requests
import json
import math
import time
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

GATE_THRESHOLD = 91.7       # Bayesian gate — must exceed for EXECUTE
KELLY_MAX_EVENT = 0.02      # Max 2% of portfolio for event trades
TRAILING_STOP_PCT = 0.02    # 2% trailing stop
DECAY_HALFLIFE_H = 3        # Intel decays with 3h half-life

# Source Tier mapping — Tier 5 (Discord inner circle) gets highest prior
SOURCE_TIERS = {
    1: {"name": "RUMOR", "prior_base": 0.55, "color": "#556677"},
    2: {"name": "INDIRECT", "prior_base": 0.60, "color": "#778899"},
    3: {"name": "DIRECT", "prior_base": 0.65, "color": "#58a6ff"},
    4: {"name": "VERIFIED DOC", "prior_base": 0.72, "color": "#ffdd00"},
    5: {"name": "INNER CIRCLE", "prior_base": 0.82, "color": "#ff4444"},
}

# --- BUILT-IN API KEYS (loaded from env or hardcoded) ---
import os

_BUILTIN_CQ_KEY = os.environ.get("CRYPTOQUANT_API_KEY", "ON2ZykQbM1JsefxH9ZiNh0yqCZboZnJOKSNyiXZ0DcnjWzeSam3cflkucBhNIFBTrKZhBtC020yztVmUJSqWbKAuVfr")
_BUILTIN_CP_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "d046924bac4c8ebd903290e6b1d79c1ae98bc36a")
_BUILTIN_BINANCE_KEY = os.environ.get("BINANCE_API_KEY", "9hPVqxSVR1A8Nga5cPt5rnqsfQEey5Zv00qts6PgFfgvHoIgEWe8N5r60vPwFU0U")
_BUILTIN_BINANCE_SECRET = os.environ.get("BINANCE_API_SECRET", "PTSRG1TSz5Vz0Oxx8d95uq1VqUASLLsEp1QWeIIzFanltutvjU29KEt2ILumLeMc")

# CryptoQuant API
CQ_BASE = "https://api.cryptoquant.com/v1"

# CryptoPanic API — DEVELOPER v2
CP_BASE = "https://cryptopanic.com/api/developer/v2"

# Fear & Greed
FNG_URL = "https://api.alternative.me/fng/?limit=1"

# CoinGecko — token price lookup
CG_SEARCH = "https://api.coingecko.com/api/v3/search"
CG_PRICE = "https://api.coingecko.com/api/v3/simple/price"
CG_MARKET = "https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=1"

# Binance — live price fallback
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"


# ---------------------------------------------------------------------------
# DATA FETCHING
# ---------------------------------------------------------------------------

def _fetch_fear_greed():
    try:
        r = requests.get(FNG_URL, timeout=8)
        r.raise_for_status()
        d = r.json()["data"][0]
        return {"value": int(d.get("value", 50)), "label": d.get("value_classification", "N/A")}
    except Exception:
        return {"value": 50, "label": "N/A"}


def _fetch_cryptoquant_metric(api_key, endpoint, window="day", limit=1):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{CQ_BASE}/{endpoint}?window={window}&limit={limit}"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("result", {}).get("data", [])
        return data[0] if data else {}
    except Exception:
        return {}


def _fetch_exchange_netflow(api_key):
    return _fetch_cryptoquant_metric(api_key, "btc/exchange-flows/netflow-total")


def _fetch_whale_ratio(api_key):
    return _fetch_cryptoquant_metric(api_key, "btc/exchange-flows/whale-ratio")


def _fetch_funding_rate(api_key):
    return _fetch_cryptoquant_metric(api_key, "btc/market-data/funding-rates")


def _fetch_mvrv(api_key):
    return _fetch_cryptoquant_metric(api_key, "btc/market-data/mvrv")


def _fetch_cryptopanic_sentiment(api_key, symbol="BTC"):
    try:
        url = f"{CP_BASE}/posts/?auth_token={api_key}&currencies={symbol}&kind=news&filter=hot"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        posts = r.json().get("results", [])
        if not posts:
            return {"sentiment": 0.0, "headlines": [], "leak_detected": False}

        bullish = sum(1 for p in posts if p.get("votes", {}).get("positive", 0) > p.get("votes", {}).get("negative", 0))
        bearish = sum(1 for p in posts if p.get("votes", {}).get("negative", 0) > p.get("votes", {}).get("positive", 0))
        total = max(len(posts), 1)
        sentiment = (bullish - bearish) / total

        headlines = [p.get("title", "")[:80] for p in posts[:5]]

        now = datetime.now(timezone.utc)
        recent_count = 0
        for p in posts:
            try:
                pub = datetime.fromisoformat(p.get("published_at", "").replace("Z", "+00:00"))
                if (now - pub).total_seconds() < 7200:
                    recent_count += 1
            except Exception:
                pass
        leak_detected = recent_count >= 3

        return {"sentiment": round(sentiment, 3), "headlines": headlines, "leak_detected": leak_detected}
    except Exception:
        return {"sentiment": 0.0, "headlines": [], "leak_detected": False}


def _fetch_btc_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        return {"price": round(d.get("usd", 0), 2), "change": round(d.get("usd_24h_change", 0), 2)}
    except Exception:
        return {"price": 0, "change": 0}


# Symbol aliases — maps common names to CoinGecko search terms
_SYMBOL_ALIASES = {
    "EMT": "email token",
    "EMAIL": "email token",
    "ETHERMAIL": "email token",
}


def _fetch_token_price(symbol):
    """Try to get token price from CoinGecko by symbol search."""
    try:
        # Use alias if available for better search results
        search_term = _SYMBOL_ALIASES.get(symbol.upper(), symbol)
        # Search for the token
        r = requests.get(f"{CG_SEARCH}?query={search_term}", timeout=8)
        r.raise_for_status()
        coins = r.json().get("coins", [])
        if not coins:
            return None

        # Find best match
        coin_id = None
        for c in coins:
            if c.get("symbol", "").upper() == symbol.upper():
                coin_id = c["id"]
                break
        if not coin_id and coins:
            coin_id = coins[0]["id"]

        if not coin_id:
            return None

        # Get price
        r2 = requests.get(
            f"{CG_PRICE}?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true",
            timeout=8,
        )
        r2.raise_for_status()
        d = r2.json().get(coin_id, {})

        # Get 24h chart for momentum
        r3 = requests.get(CG_MARKET.format(id=coin_id), timeout=8)
        prices_24h = []
        if r3.ok:
            prices_24h = [p[1] for p in r3.json().get("prices", [])]

        # Compute momentum metrics
        current = d.get("usd", 0)
        change_24h = d.get("usd_24h_change", 0)
        vol_24h = d.get("usd_24h_vol", 0)
        mcap = d.get("usd_market_cap", 0)

        # Pump detection: if price ran up >50% in 24h, high risk of dump
        pump_score = 0
        if change_24h > 100:
            pump_score = 3  # Extreme pump
        elif change_24h > 50:
            pump_score = 2  # Strong pump
        elif change_24h > 20:
            pump_score = 1  # Moderate pump

        # Volume spike detection
        vol_spike = False
        if prices_24h and len(prices_24h) > 12:
            # Compare last 2h avg vs first 12h avg
            early_avg = sum(prices_24h[:len(prices_24h)//2]) / max(len(prices_24h)//2, 1)
            late_avg = sum(prices_24h[len(prices_24h)//2:]) / max(len(prices_24h)//2, 1)
            if early_avg > 0 and late_avg / early_avg > 1.5:
                vol_spike = True

        return {
            "coin_id": coin_id,
            "price": current,
            "change_24h": change_24h,
            "volume_24h": vol_24h,
            "market_cap": mcap,
            "pump_score": pump_score,
            "vol_spike": vol_spike,
            "prices_24h": prices_24h[-24:] if prices_24h else [],  # Last 24 data points
        }
    except Exception:
        return None


def _fetch_binance_price(symbol):
    """Fetch token price from Binance as fallback. Tries USDT pair first."""
    try:
        # Try common pairs
        for quote in ["USDT", "BUSD", "BTC"]:
            pair = f"{symbol.upper()}{quote}"
            r = requests.get(f"{BINANCE_TICKER}?symbol={pair}", timeout=8)
            if r.ok:
                d = r.json()
                price = float(d.get("lastPrice", 0))
                change = float(d.get("priceChangePercent", 0))
                vol = float(d.get("quoteVolume", 0))
                high = float(d.get("highPrice", 0))
                low = float(d.get("lowPrice", 0))

                if price <= 0:
                    continue

                # If BTC pair, convert to USD
                if quote == "BTC":
                    btc_r = requests.get(f"{BINANCE_TICKER}?symbol=BTCUSDT", timeout=5)
                    if btc_r.ok:
                        btc_price = float(btc_r.json().get("lastPrice", 68000))
                        price *= btc_price
                        high *= btc_price
                        low *= btc_price

                # Pump detection
                pump_score = 0
                if change > 100:
                    pump_score = 3
                elif change > 50:
                    pump_score = 2
                elif change > 20:
                    pump_score = 1

                # Volume spike: high/low spread > 50% = volatile
                vol_spike = False
                if low > 0 and (high / low - 1) > 0.5:
                    vol_spike = True

                return {
                    "coin_id": pair,
                    "price": price,
                    "change_24h": change,
                    "volume_24h": vol,
                    "market_cap": 0,  # Binance doesn't provide mcap
                    "pump_score": pump_score,
                    "vol_spike": vol_spike,
                    "prices_24h": [],
                    "source": "Binance",
                }
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CROSS-VALIDATION ENGINE
# ---------------------------------------------------------------------------

def _compute_validation(intel_direction, source_reliability,
                        netflow_val, whale_ratio_val, funding_val,
                        mvrv_val, fng_val, sentiment_val, leak_detected,
                        hours_since_input, token_data=None):
    """
    Cross-validate human intel against market physics.
    Returns a dict with scores and final posterior.
    """

    # --- 1. Prior from human intel ---
    tier = SOURCE_TIERS.get(source_reliability, SOURCE_TIERS[3])
    prior = tier["prior_base"]

    # Time decay: intel loses value over time (3h half-life)
    decay = math.exp(-0.693 * hours_since_input / DECAY_HALFLIFE_H)
    prior = 0.50 + (prior - 0.50) * decay

    # --- 2. On-Chain Validation (CryptoQuant) ---
    onchain_score = 0.0
    onchain_signals = []

    if netflow_val is not None:
        if netflow_val < -1000:
            onchain_score += 0.08
            onchain_signals.append(("Netflow", "BULLISH", f"{netflow_val:,.0f} BTC leaving exchanges"))
        elif netflow_val > 1000:
            onchain_score -= 0.08
            onchain_signals.append(("Netflow", "BEARISH", f"{netflow_val:,.0f} BTC entering exchanges"))
        else:
            onchain_signals.append(("Netflow", "NEUTRAL", f"{netflow_val:,.0f} BTC"))

    if whale_ratio_val is not None:
        if whale_ratio_val > 0.85:
            onchain_score -= 0.05
            onchain_signals.append(("Whale Ratio", "CAUTION", f"{whale_ratio_val:.2f}"))
        elif whale_ratio_val < 0.5:
            onchain_score += 0.05
            onchain_signals.append(("Whale Ratio", "SAFE", f"{whale_ratio_val:.2f}"))
        else:
            onchain_signals.append(("Whale Ratio", "NEUTRAL", f"{whale_ratio_val:.2f}"))

    if funding_val is not None:
        if funding_val < -0.01:
            onchain_score += 0.06
            onchain_signals.append(("Funding Rate", "SQUEEZE", f"{funding_val:.4f}"))
        elif funding_val > 0.03:
            onchain_score -= 0.06
            onchain_signals.append(("Funding Rate", "OVERHEATED", f"{funding_val:.4f}"))
        else:
            onchain_signals.append(("Funding Rate", "NEUTRAL", f"{funding_val:.4f}"))

    if mvrv_val is not None:
        if mvrv_val < 1.0:
            onchain_score += 0.07
            onchain_signals.append(("MVRV", "UNDERVALUED", f"{mvrv_val:.2f}"))
        elif mvrv_val > 3.5:
            onchain_score -= 0.07
            onchain_signals.append(("MVRV", "OVERVALUED", f"{mvrv_val:.2f}"))
        else:
            onchain_signals.append(("MVRV", "FAIR", f"{mvrv_val:.2f}"))

    # --- 3. Token-specific validation ---
    token_signals = []
    token_score = 0.0

    if token_data:
        price = token_data.get("price", 0)
        change = token_data.get("change_24h", 0)
        pump = token_data.get("pump_score", 0)
        vol_spike = token_data.get("vol_spike", False)
        mcap = token_data.get("market_cap", 0)

        # Pump detection — if already pumped hard, Sell-the-News risk
        if pump >= 3:
            token_score -= 0.12
            token_signals.append(("Pump Alert", "EXTREME", f"+{change:.0f}% in 24h — Sell-the-News risk HIGH"))
        elif pump >= 2:
            token_score -= 0.06
            token_signals.append(("Pump Alert", "STRONG", f"+{change:.0f}% in 24h — late entry risk"))
        elif pump >= 1:
            token_score -= 0.02
            token_signals.append(("Pump Alert", "MODERATE", f"+{change:.0f}% in 24h"))
        else:
            token_score += 0.04
            token_signals.append(("Pump Alert", "CLEAN", f"{change:+.1f}% — no prior pump"))

        # Volume spike
        if vol_spike:
            token_score -= 0.03
            token_signals.append(("Volume Spike", "DETECTED", "Price acceleration in last hours"))
        else:
            token_signals.append(("Volume Spike", "NORMAL", "No abnormal volume"))

        # Market cap risk
        if mcap > 0 and mcap < 10_000_000:
            token_score -= 0.04
            token_signals.append(("Market Cap", "MICRO", f"${mcap/1e6:.1f}M — high manipulation risk"))
        elif mcap > 0 and mcap < 100_000_000:
            token_signals.append(("Market Cap", "SMALL", f"${mcap/1e6:.1f}M"))
        elif mcap > 0:
            token_score += 0.02
            token_signals.append(("Market Cap", "SOLID", f"${mcap/1e6:.0f}M"))

    # --- 4. Sentiment Validation ---
    sentiment_score = 0.0
    sentiment_signals = []

    if fng_val <= 15:
        if intel_direction == "LONG":
            sentiment_score += 0.06
            sentiment_signals.append(("Fear & Greed", "CONTRARIAN BUY", f"{fng_val}/100 Extreme Fear"))
        else:
            sentiment_score += 0.03
            sentiment_signals.append(("Fear & Greed", "ALIGNED", f"{fng_val}/100"))
    elif fng_val >= 80:
        if intel_direction == "SHORT":
            sentiment_score += 0.06
            sentiment_signals.append(("Fear & Greed", "CONTRARIAN SELL", f"{fng_val}/100"))
        else:
            sentiment_score -= 0.04
            sentiment_signals.append(("Fear & Greed", "CAUTION", f"{fng_val}/100 Extreme Greed"))
    else:
        sentiment_signals.append(("Fear & Greed", "NEUTRAL", f"{fng_val}/100"))

    if sentiment_val > 0.3 and intel_direction == "LONG":
        sentiment_score += 0.04
        sentiment_signals.append(("News Sentiment", "ALIGNED", f"{sentiment_val:+.2f}"))
    elif sentiment_val < -0.3 and intel_direction == "SHORT":
        sentiment_score += 0.04
        sentiment_signals.append(("News Sentiment", "ALIGNED", f"{sentiment_val:+.2f}"))
    elif abs(sentiment_val) > 0.3:
        sentiment_score -= 0.03
        sentiment_signals.append(("News Sentiment", "CONFLICT", f"{sentiment_val:+.2f}"))
    else:
        sentiment_signals.append(("News Sentiment", "QUIET", f"{sentiment_val:+.2f}"))

    if leak_detected:
        sentiment_score -= 0.08
        sentiment_signals.append(("Leak Detection", "LEAKED", "3+ hot articles — edge eroding"))
    else:
        sentiment_signals.append(("Leak Detection", "CLEAN", "No premature leak"))

    # --- 5. Direction alignment ---
    if intel_direction == "SHORT":
        onchain_score = -onchain_score

    # --- 6. Bayesian Collapse ---
    total_evidence = onchain_score + sentiment_score + token_score
    posterior = prior + total_evidence
    posterior = max(0.01, min(0.99, posterior))

    # --- 7. Gate Check ---
    gate_open = posterior * 100 >= GATE_THRESHOLD

    # --- 8. Kelly Criterion ---
    if gate_open and posterior > 0.5:
        q = 1 - posterior
        b = 2.0
        kelly_raw = (posterior * b - q) / b
        kelly = max(0, min(kelly_raw, KELLY_MAX_EVENT))
    else:
        kelly = 0.0

    # --- 9. Entry/TP/SL computation ---
    entry_price = None
    take_profit = None
    stop_loss = None

    if token_data and token_data.get("price", 0) > 0:
        entry_price = token_data["price"]
        if intel_direction == "LONG":
            # TP: based on posterior strength
            tp_mult = 1.05 + (posterior - 0.5) * 0.20  # 5% to 15%
            sl_mult = 1.0 - TRAILING_STOP_PCT
            take_profit = entry_price * tp_mult
            stop_loss = entry_price * sl_mult
        else:
            tp_mult = 0.95 - (posterior - 0.5) * 0.20
            sl_mult = 1.0 + TRAILING_STOP_PCT
            take_profit = entry_price * tp_mult
            stop_loss = entry_price * sl_mult

    # --- 10. Final Action ---
    if gate_open:
        action = "EXECUTE"
        action_color = "#00ff88"
    elif posterior >= 0.70:
        action = "STANDBY"
        action_color = "#ffdd00"
    elif posterior >= 0.50:
        action = "HOLD"
        action_color = "#ff8800"
    else:
        action = "REJECT"
        action_color = "#ff2020"

    return {
        "prior": prior,
        "posterior": posterior,
        "gate_open": gate_open,
        "kelly": kelly,
        "action": action,
        "action_color": action_color,
        "decay": decay,
        "onchain_score": onchain_score,
        "sentiment_score": sentiment_score,
        "token_score": token_score,
        "onchain_signals": onchain_signals,
        "sentiment_signals": sentiment_signals,
        "token_signals": token_signals,
        "total_evidence": total_evidence,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
    }


# ---------------------------------------------------------------------------
# RAPID STRIKE — COMMAND CARD
# ---------------------------------------------------------------------------

def _render_command_card(st_app, result, symbol, direction, token_data, scan_time_sec):
    """Render the instant action command card — the only thing that matters."""

    post_pct = result["posterior"] * 100
    gate_pct = GATE_THRESHOLD
    gap = gate_pct - post_pct

    if result["gate_open"]:
        border_color = "#00ff88"
        bg = "rgba(0, 255, 136, 0.08)"
        status_text = "GATE OPEN"
        status_icon = "🟢"
    elif post_pct >= 70:
        border_color = "#ffdd00"
        bg = "rgba(255, 221, 0, 0.08)"
        status_text = "APPROACHING"
        status_icon = "🟡"
    elif post_pct >= 50:
        border_color = "#ff8800"
        bg = "rgba(255, 136, 0, 0.08)"
        status_text = "INSUFFICIENT"
        status_icon = "🔴"
    else:
        border_color = "#ff2020"
        bg = "rgba(255, 32, 32, 0.08)"
        status_text = "REJECTED"
        status_icon = "⛔"

    # Entry/TP/SL strings
    entry_str = f"${result['entry_price']:.6f}" if result['entry_price'] and result['entry_price'] < 1 else (
        f"${result['entry_price']:,.2f}" if result['entry_price'] else "N/A"
    )
    tp_str = f"${result['take_profit']:.6f}" if result['take_profit'] and result['take_profit'] < 1 else (
        f"${result['take_profit']:,.2f}" if result['take_profit'] else "N/A"
    )
    sl_str = f"${result['stop_loss']:.6f}" if result['stop_loss'] and result['stop_loss'] < 1 else (
        f"${result['stop_loss']:,.2f}" if result['stop_loss'] else "N/A"
    )

    kelly_pct = result['kelly'] * 100

    # Token stats
    token_price_str = ""
    token_change_str = ""
    if token_data:
        p = token_data.get("price", 0)
        c = token_data.get("change_24h", 0)
        token_price_str = f"${p:.6f}" if p < 1 else f"${p:,.2f}"
        token_change_str = f"{c:+.1f}%"

    st_app.markdown(f"""
    <div style="background: {bg}; border: 2px solid {border_color}; border-radius: 16px;
                padding: 24px; margin: 10px 0; font-family: 'JetBrains Mono', monospace;">

        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <span style="font-family: 'Orbitron', monospace; font-size: 28px; color: {border_color};
                            text-shadow: 0 0 20px {border_color}; font-weight: 900; letter-spacing: 2px;">
                    {result['action']}
                </span>
                <span style="font-size: 12px; color: #556677; margin-left: 12px;">
                    {status_icon} {status_text} | Scanned in {scan_time_sec:.1f}s
                </span>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 11px; color: #556677;">POSTERIOR</div>
                <div style="font-size: 32px; color: {border_color}; font-weight: 700;">{post_pct:.1f}%</div>
                <div style="font-size: 10px; color: #556677;">Gate: {gate_pct}% | Gap: {gap:+.1f}pp</div>
            </div>
        </div>

        <!-- Command Grid -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0;">
            <div style="background: rgba(10,14,23,0.6); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 9px; color: #556677; text-transform: uppercase;">Symbol</div>
                <div style="font-size: 18px; color: #58a6ff; font-weight: 700;">{symbol}</div>
                <div style="font-size: 10px; color: #556677;">{direction}</div>
            </div>
            <div style="background: rgba(10,14,23,0.6); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 9px; color: #556677; text-transform: uppercase;">Entry</div>
                <div style="font-size: 16px; color: #e6edf3; font-weight: 600;">{entry_str}</div>
                <div style="font-size: 10px; color: #556677;">{token_change_str} 24h</div>
            </div>
            <div style="background: rgba(0,255,136,0.08); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 9px; color: #00ff88; text-transform: uppercase;">Take Profit</div>
                <div style="font-size: 16px; color: #00ff88; font-weight: 600;">{tp_str}</div>
                <div style="font-size: 10px; color: #556677;">Target</div>
            </div>
            <div style="background: rgba(255,68,68,0.08); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 9px; color: #ff4444; text-transform: uppercase;">Stop Loss</div>
                <div style="font-size: 16px; color: #ff4444; font-weight: 600;">{sl_str}</div>
                <div style="font-size: 10px; color: #556677;">Trailing {TRAILING_STOP_PCT*100:.0f}%</div>
            </div>
        </div>

        <!-- Kelly + Risk -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            <div style="background: rgba(10,14,23,0.6); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 9px; color: #556677;">KELLY SIZE</div>
                <div style="font-size: 20px; color: {'#00ff88' if kelly_pct > 0 else '#ff4444'}; font-weight: 700;">
                    {kelly_pct:.1f}%
                </div>
                <div style="font-size: 9px; color: #556677;">{'ACTIVE' if kelly_pct > 0 else 'LOCKED'}</div>
            </div>
            <div style="background: rgba(10,14,23,0.6); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 9px; color: #556677;">INTEL DECAY</div>
                <div style="font-size: 20px; color: {'#00ff88' if result['decay'] > 0.7 else '#ffdd00' if result['decay'] > 0.3 else '#ff4444'}; font-weight: 700;">
                    {result['decay']*100:.0f}%
                </div>
                <div style="font-size: 9px; color: #556677;">Freshness</div>
            </div>
            <div style="background: rgba(10,14,23,0.6); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="font-size: 9px; color: #556677;">EVIDENCE</div>
                <div style="font-size: 20px; color: {'#00ff88' if result['total_evidence'] > 0 else '#ff4444'}; font-weight: 700;">
                    {result['total_evidence']:+.3f}
                </div>
                <div style="font-size: 9px; color: #556677;">On-Chain + Sentiment + Token</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SIGNAL BREAKDOWN
# ---------------------------------------------------------------------------

def _render_signals(st_app, result, fng, btc, cp_data, token_data):
    """Render detailed signal breakdown — expandable."""

    with st_app.expander("📡 Signal Breakdown — פירוט אותות", expanded=False):

        # Token signals
        if result["token_signals"]:
            st_app.markdown("**Token Analysis**")
            for name, status, detail in result["token_signals"]:
                color = "#00ff88" if "CLEAN" in status or "SOLID" in status else (
                    "#ff4444" if "EXTREME" in status or "STRONG" in status or "MICRO" in status else "#ffdd00"
                )
                st_app.markdown(f"""
                <div style="background: rgba(10,14,23,0.8); border-left: 3px solid {color};
                            padding: 8px 12px; margin: 4px 0; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                    <span style="color: {color}; font-weight: 600;">[{status}]</span>
                    <span style="color: #aabbcc;">{name}:</span>
                    <span style="color: #c0d0e0;">{detail}</span>
                </div>
                """, unsafe_allow_html=True)

        # On-Chain signals
        if result["onchain_signals"]:
            st_app.markdown("**On-Chain (CryptoQuant)**")
            for name, status, detail in result["onchain_signals"]:
                color = "#00ff88" if any(k in status for k in ["BULL", "SAFE", "SQUEEZE", "UNDER"]) else (
                    "#ff4444" if any(k in status for k in ["BEAR", "CAUTION", "OVER"]) else "#556677"
                )
                st_app.markdown(f"""
                <div style="background: rgba(10,14,23,0.8); border-left: 3px solid {color};
                            padding: 8px 12px; margin: 4px 0; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                    <span style="color: {color}; font-weight: 600;">[{status}]</span>
                    <span style="color: #aabbcc;">{name}:</span>
                    <span style="color: #c0d0e0;">{detail}</span>
                </div>
                """, unsafe_allow_html=True)

        # Sentiment signals
        if result["sentiment_signals"]:
            st_app.markdown("**Sentiment (CryptoPanic + F&G)**")
            for name, status, detail in result["sentiment_signals"]:
                color = "#00ff88" if any(k in status for k in ["ALIGNED", "CONTRARIAN", "CLEAN"]) else (
                    "#ff4444" if any(k in status for k in ["CONFLICT", "LEAKED", "CAUTION"]) else "#556677"
                )
                st_app.markdown(f"""
                <div style="background: rgba(10,14,23,0.8); border-left: 3px solid {color};
                            padding: 8px 12px; margin: 4px 0; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                    <span style="color: {color}; font-weight: 600;">[{status}]</span>
                    <span style="color: #aabbcc;">{name}:</span>
                    <span style="color: #c0d0e0;">{detail}</span>
                </div>
                """, unsafe_allow_html=True)

        # Score summary
        st_app.markdown("---")
        c1, c2, c3, c4 = st_app.columns(4)
        c1.metric("Prior", f"{result['prior']*100:.1f}%")
        c2.metric("On-Chain", f"{result['onchain_score']:+.3f}")
        c3.metric("Sentiment", f"{result['sentiment_score']:+.3f}")
        c4.metric("Token", f"{result['token_score']:+.3f}")


# ---------------------------------------------------------------------------
# STREAMLIT UI — MAIN RENDER
# ---------------------------------------------------------------------------

def render_oracle_node(st_app):
    """Render the Oracle Node panel in Streamlit — Rapid Strike + Deep Scan."""

    st_app.markdown("""
    <style>
    .oracle-header-v2 {
        background: linear-gradient(135deg, #0a0e17 0%, #1a0a2e 100%);
        border: 1px solid rgba(138, 43, 226, 0.4);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .oracle-title-v2 {
        font-family: 'Orbitron', monospace;
        font-size: 22px;
        color: #8a2be2;
        text-shadow: 0 0 20px rgba(138, 43, 226, 0.5);
        letter-spacing: 3px;
    }
    .oracle-mode {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        padding: 4px 12px;
        border-radius: 4px;
        letter-spacing: 1px;
    }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    # Header
    st_app.markdown("""
    <div class="oracle-header-v2">
        <div>
            <div class="oracle-title-v2">ORACLE NODE v2</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #556677; margin-top: 4px;">
                RAPID STRIKE HUMINT SCANNER // 30-SEC CROSS-VALIDATION // ZERO TRUST
            </div>
        </div>
        <div>
            <span class="oracle-mode" style="background: rgba(255,68,68,0.2); color: #ff4444; border: 1px solid #ff4444;">
                RAPID STRIKE
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- RAPID INPUT ---
    st_app.markdown("""
    <div style="direction: rtl; text-align: right; font-family: 'JetBrains Mono', monospace;
                font-size: 12px; color: #8a2be2; margin-bottom: 8px; letter-spacing: 0.5px;">
        הזן את המידע מהדיסקורד. 30 שניות סריקה. פקודה ברורה.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st_app.columns([2, 1, 1])

    with col1:
        target_symbol = st_app.text_input(
            "Target Symbol",
            value="EMT",
            help="הסמל של הנכס — EMT, BTC, ETH, SOL..."
        )

    with col2:
        intel_direction = st_app.selectbox(
            "Direction",
            ["LONG", "SHORT"],
        )

    with col3:
        source_tier = st_app.selectbox(
            "Source Tier",
            [5, 4, 3, 2, 1],
            format_func=lambda x: f"T{x}: {SOURCE_TIERS[x]['name']}",
            help="T5=Inner Circle (Discord), T4=Verified Doc, T3=Direct, T2=Indirect, T1=Rumor"
        )

    # Time since intel
    col_t1, col_t2 = st_app.columns(2)
    with col_t1:
        minutes_ago = st_app.number_input(
            "Minutes since intel received",
            min_value=0, max_value=1440, value=5,
            help="כמה דקות עברו מאז שקיבלת את המידע"
        )
    with col_t2:
        event_minutes = st_app.number_input(
            "Minutes until event/announcement",
            min_value=-1440, max_value=1440, value=60,
            help="כמה דקות עד ההודעה הרשמית (שלילי = כבר קרה)"
        )

    # API Keys — built-in, no manual entry needed
    if "cq_api_key" not in st_app.session_state:
        st_app.session_state["cq_api_key"] = _BUILTIN_CQ_KEY
    if "cp_api_key" not in st_app.session_state:
        st_app.session_state["cp_api_key"] = _BUILTIN_CP_KEY

    # Show connection status
    cq_color = '#00ff88' if st_app.session_state['cq_api_key'] else '#ff4444'
    cq_dot = '\u25cf' if st_app.session_state['cq_api_key'] else '\u25cb'
    cp_color = '#00ff88' if st_app.session_state['cp_api_key'] else '#ff4444'
    cp_dot = '\u25cf' if st_app.session_state['cp_api_key'] else '\u25cb'
    dot_on = '\u25cf'
    st_app.markdown(f"""
    <div style="display: flex; gap: 12px; margin-bottom: 10px; font-family: 'JetBrains Mono', monospace; font-size: 10px;">
        <span style="color: {cq_color};">{cq_dot} CryptoQuant</span>
        <span style="color: {cp_color};">{cp_dot} CryptoPanic</span>
        <span style="color: #00ff88;">{dot_on} CoinGecko</span>
        <span style="color: #00ff88;">{dot_on} Binance</span>
        <span style="color: #00ff88;">{dot_on} Fear&amp;Greed</span>
    </div>
    """, unsafe_allow_html=True)

    # --- RAPID STRIKE BUTTON ---
    if st_app.button("RAPID STRIKE — SCAN NOW", type="primary", use_container_width=True):

        scan_start = time.time()

        progress = st_app.progress(0, text="Scanning...")

        # 1. Token price
        progress.progress(10, text=f"Fetching {target_symbol} price...")
        token_data = _fetch_token_price(target_symbol)

        # 2. Fear & Greed
        progress.progress(25, text="Fear & Greed Index...")
        fng = _fetch_fear_greed()

        # 3. BTC baseline
        progress.progress(40, text="BTC baseline price...")
        btc = _fetch_btc_price()

        # 3.5. Binance price (fallback/additional)
        binance_data = _fetch_binance_price(target_symbol)
        if binance_data and (not token_data or token_data.get('price', 0) == 0):
            token_data = binance_data

        # 4. CryptoQuant
        cq_key = st_app.session_state.get("cq_api_key", _BUILTIN_CQ_KEY)
        cp_key = st_app.session_state.get("cp_api_key", _BUILTIN_CP_KEY)

        progress.progress(55, text="On-chain validation (CryptoQuant)...")
        netflow_data = _fetch_exchange_netflow(cq_key) if cq_key else {}
        whale_data = _fetch_whale_ratio(cq_key) if cq_key else {}
        funding_data = _fetch_funding_rate(cq_key) if cq_key else {}
        mvrv_data = _fetch_mvrv(cq_key) if cq_key else {}

        netflow_val = netflow_data.get("netflow_total", netflow_data.get("value", None))
        whale_ratio_val = whale_data.get("whale_ratio", whale_data.get("value", None))
        funding_val = funding_data.get("funding_rate", funding_data.get("value", None))
        mvrv_val = mvrv_data.get("mvrv", mvrv_data.get("value", None))

        # 5. CryptoPanic
        progress.progress(75, text="Sentiment scan (CryptoPanic)...")
        cp_data = _fetch_cryptopanic_sentiment(cp_key, target_symbol) if cp_key else {
            "sentiment": 0.0, "headlines": [], "leak_detected": False
        }

        # 6. Compute
        progress.progress(90, text="Bayesian collapse...")
        hours_since = minutes_ago / 60.0

        result = _compute_validation(
            intel_direction=intel_direction,
            source_reliability=source_tier,
            netflow_val=netflow_val,
            whale_ratio_val=whale_ratio_val,
            funding_val=funding_val,
            mvrv_val=mvrv_val,
            fng_val=fng["value"],
            sentiment_val=cp_data["sentiment"],
            leak_detected=cp_data["leak_detected"],
            hours_since_input=hours_since,
            token_data=token_data,
        )

        scan_time = time.time() - scan_start
        progress.progress(100, text=f"COMPLETE — {scan_time:.1f}s")

        # --- RENDER COMMAND CARD ---
        _render_command_card(st_app, result, target_symbol, intel_direction, token_data, scan_time)

        # --- RENDER SIGNALS ---
        _render_signals(st_app, result, fng, btc, cp_data, token_data)

        # --- TIMING ADVISORY ---
        if event_minutes > 0:
            st_app.markdown(f"""
            <div style="background: rgba(88, 166, 255, 0.1); border: 1px solid #58a6ff;
                        border-radius: 8px; padding: 12px; margin-top: 12px; direction: rtl; text-align: right;">
                <div style="color: #58a6ff; font-weight: 700; font-size: 13px;">
                    ⏰ ההודעה הרשמית בעוד {event_minutes} דקות
                </div>
                <div style="color: #8899aa; font-size: 11px; margin-top: 6px; line-height: 1.6;">
                    {'אם נכנסת — שים TP לפני ההודעה. Sell the News סביר.' if result['posterior'] * 100 >= 70 else
                     'המערכת לא מאשרת כניסה. אם בכל זאת נכנסת — מקסימום 1% מהתיק.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif event_minutes < 0:
            st_app.markdown(f"""
            <div style="background: rgba(255, 136, 0, 0.1); border: 1px solid #ff8800;
                        border-radius: 8px; padding: 12px; margin-top: 12px; direction: rtl; text-align: right;">
                <div style="color: #ff8800; font-weight: 700; font-size: 13px;">
                    ⚠️ ההודעה כבר פורסמה לפני {abs(event_minutes)} דקות
                </div>
                <div style="color: #8899aa; font-size: 11px; margin-top: 6px; line-height: 1.6;">
                    המומנטום הראשוני כנראה כבר עבר. כניסה עכשיו = סיכון גבוה יותר.
                    {'אם נכנסת — TP הדוק מאוד.' if result['posterior'] * 100 >= 70 else 'לא מומלץ.'}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Risk warning
        st_app.markdown("""
        <div style="background: rgba(255, 32, 32, 0.05); border: 1px solid rgba(255,32,32,0.3);
                    border-radius: 8px; padding: 12px; margin-top: 12px; direction: rtl; text-align: right;">
            <div style="color: #ff4444; font-size: 11px; line-height: 1.6;">
                Oracle Node מאמת מידע אנושי מול נתוני שוק חיים. הוא לא מבטיח רווח.
                כניסה מבוססת אירוע: מקסימום 2% מהתיק, Trailing Stop 2%.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CASE TRADE MODULE — WYCKOFF UTAD SCANNER
# ---------------------------------------------------------------------------

def _fetch_binance_ohlc(symbol, interval="30m", limit=100):
    """Fetch OHLCV candlestick data from Binance."""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol.upper() + "USDT", "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=10)
        if not r.ok:
            return None
        raw = r.json()
        if not raw:
            return None
        ohlc = {
            "open":   [float(c[1]) for c in raw],
            "high":   [float(c[2]) for c in raw],
            "low":    [float(c[3]) for c in raw],
            "close":  [float(c[4]) for c in raw],
            "volume": [float(c[5]) for c in raw],
        }
        return ohlc
    except Exception:
        return None


def _compute_rsi(closes, period=14):
    """Compute RSI series from close prices."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    # Initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_vals = []
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi_vals.append(100 - (100 / (1 + rs)))
    # Pad front
    pad = [50.0] * (len(closes) - len(rsi_vals))
    return pad + rsi_vals


def _find_swing_highs(highs, window=5):
    """Find indices of swing highs (local maxima)."""
    peaks = []
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i - window:i + window + 1]):
            peaks.append(i)
    return peaks


def _detect_wyckoff_utad(ohlc):
    """
    Detect Wyckoff Distribution + UTAD pattern.
    Returns dict with phase, event, range_high, range_low, ut_high, utad_high.
    """
    structure = {"phase": None, "event": None, "range_high": None,
                 "range_low": None, "ut_high": None, "utad_high": None}
    highs = ohlc["high"]
    lows = ohlc["low"]
    closes = ohlc["close"]
    n = len(highs)
    if n < 30:
        return structure

    # Find swing highs in the last 80 bars
    peaks = _find_swing_highs(highs, window=4)
    if len(peaks) < 2:
        return structure

    # BC = highest swing high in lookback
    bc_idx = max(peaks, key=lambda i: highs[i])
    bc_high = highs[bc_idx]

    # AR = lowest close after BC
    ar_idx = bc_idx + lows[bc_idx:].index(min(lows[bc_idx:bc_idx + 40])) if bc_idx + 5 < n else None
    if ar_idx is None:
        return structure
    range_low = lows[ar_idx]
    range_high = bc_high

    # UT = swing high after AR that is below BC but above midpoint
    mid = (range_high + range_low) / 2
    ut_peaks = [i for i in peaks if i > ar_idx and highs[i] > mid and highs[i] < range_high * 1.02]
    if not ut_peaks:
        return structure
    ut_idx = ut_peaks[0]
    ut_high = highs[ut_idx]

    # UTAD = swing high after UT that slightly exceeds UT high
    utad_peaks = [i for i in peaks if i > ut_idx and highs[i] > ut_high and highs[i] < ut_high * 1.05]
    if not utad_peaks:
        return structure
    utad_idx = utad_peaks[-1]  # Most recent UTAD
    utad_high = highs[utad_idx]

    # Verify price returned inside range after UTAD
    if utad_idx + 2 < n and closes[utad_idx + 1] < utad_high * 0.995:
        structure.update({
            "phase": "Distribution",
            "event": "UTAD",
            "range_high": range_high,
            "range_low": range_low,
            "ut_high": ut_high,
            "utad_high": utad_high,
            "bc_idx": bc_idx,
            "utad_idx": utad_idx,
        })
    return structure


def _detect_bearish_rsi_divergence(closes, rsi_vals, lookback=20):
    """Detect bearish RSI divergence: Higher High in price, Lower High in RSI."""
    if len(closes) < lookback or len(rsi_vals) < lookback:
        return False, None, None
    recent_closes = closes[-lookback:]
    recent_rsi = rsi_vals[-lookback:]
    price_peaks = _find_swing_highs(recent_closes, window=3)
    rsi_peaks = _find_swing_highs(recent_rsi, window=3)
    if len(price_peaks) < 2 or len(rsi_peaks) < 2:
        return False, None, None
    # Last two price highs
    ph1, ph2 = price_peaks[-2], price_peaks[-1]
    rh1, rh2 = rsi_peaks[-2], rsi_peaks[-1]
    price_hh = recent_closes[ph2] > recent_closes[ph1]
    rsi_lh = recent_rsi[rh2] < recent_rsi[rh1]
    divergence = price_hh and rsi_lh
    return divergence, recent_closes[ph2], recent_rsi[rh2]


def scan_case_trade(symbol="SOL", trigger_price=88.0, gate_pct=70.0):
    """
    Full Wyckoff UTAD Case Trade scanner.
    Returns a case_trade dict if setup is active, else None.
    """
    ohlc_30m = _fetch_binance_ohlc(symbol, interval="30m", limit=120)
    if not ohlc_30m:
        return {"error": f"No OHLC data for {symbol}"}

    # Wyckoff detection
    wyckoff = _detect_wyckoff_utad(ohlc_30m)

    # RSI
    rsi_vals = _compute_rsi(ohlc_30m["close"], period=14)
    divergence, price_h, rsi_h = _detect_bearish_rsi_divergence(ohlc_30m["close"], rsi_vals)

    current_price = ohlc_30m["close"][-1]
    last_close = ohlc_30m["close"][-1]

    # Auto-detect trigger from UTAD if not specified
    if wyckoff.get("utad_high"):
        # Trigger = midpoint of range upper half
        trigger_price = wyckoff["range_high"] * 0.97  # ~3% below range high

    # Build result
    result = {
        "symbol": symbol.upper(),
        "current_price": current_price,
        "wyckoff": wyckoff,
        "rsi_divergence": divergence,
        "price_high": price_h,
        "rsi_high": rsi_h,
        "trigger_price": trigger_price,
        "trigger_met": last_close < trigger_price,
        "setup_active": False,
        "case_trade": None,
    }

    # All 3 conditions
    if (wyckoff.get("phase") == "Distribution" and
            wyckoff.get("event") == "UTAD" and
            divergence and
            last_close < trigger_price):

        utad_h = wyckoff.get("utad_high", current_price * 1.03)
        stop = max(utad_h * 1.005, trigger_price * 1.03)
        risk = stop - trigger_price
        tp1 = trigger_price - risk * 1.5
        tp2 = trigger_price - risk * 3.0

        result["setup_active"] = True
        result["case_trade"] = {
            "symbol": f"{symbol.upper()}USDT",
            "side": "SHORT",
            "entry_zone": [round(trigger_price - 0.5, 2), round(trigger_price, 2)],
            "stop_loss": round(stop, 2),
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "risk_pct_of_equity": 0.01,
            "timeframe": "30m",
            "setup": "Wyckoff_UTAD_Distribution_RSI_Divergence",
            "misdirection_boost": 25,
        }

    return result


def render_case_trade_scanner(st_app):
    """Render the Case Trade / Wyckoff UTAD scanner tab in Streamlit."""
    st_app.markdown("""
    <div style="background: linear-gradient(135deg, #0a0e17 0%, #0d1a0d 100%);
                border: 1px solid rgba(0,255,136,0.3); border-radius: 12px;
                padding: 16px 20px; margin-bottom: 16px;">
        <div style="font-family: 'Orbitron', monospace; font-size: 18px; color: #00ff88;
                    letter-spacing: 3px; text-shadow: 0 0 15px rgba(0,255,136,0.4);">
            CASE TRADE SCANNER
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px;
                    color: #556677; margin-top: 4px;">
            WYCKOFF UTAD DISTRIBUTION // RSI DIVERGENCE // TACTICAL ENTRY
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st_app.columns([2, 1, 1])
    with col1:
        ct_symbol = st_app.text_input("Symbol", value="SOL",
                                      help="SOL, ETH, BTC, etc. — סריקת Wyckoff UTAD")
    with col2:
        ct_trigger = st_app.number_input("Trigger Price ($)", value=88.0, step=0.5,
                                         help="מחיר הטריגר לכניסה (ברירת מחדל: אוטומטי מה-UTAD)")
    with col3:
        ct_gate = st_app.number_input("Gate (%)", value=70.0, step=1.0,
                                      help="Posterior Gate לפתיחת Case Trade (נמוך מ-91.7% של BTC)")

    if st_app.button("SCAN WYCKOFF UTAD", type="primary", use_container_width=True):
        with st_app.spinner(f"Scanning {ct_symbol} 30m OHLC..."):
            scan = scan_case_trade(ct_symbol, trigger_price=ct_trigger, gate_pct=ct_gate)

        if "error" in scan:
            st_app.error(f"Error: {scan['error']}")
            return

        # Status display
        w = scan["wyckoff"]
        price = scan["current_price"]
        trigger = scan["trigger_price"]

        # Condition cards
        cond1 = w.get("phase") == "Distribution" and w.get("event") == "UTAD"
        cond2 = scan["rsi_divergence"]
        cond3 = scan["trigger_met"]
        all_met = cond1 and cond2 and cond3

        c1, c2, c3 = st_app.columns(3)
        c1.metric(
            "Wyckoff UTAD",
            "DETECTED" if cond1 else "NOT FOUND",
            delta=f"Range: ${w.get('range_low', 0):.1f}–${w.get('range_high', 0):.1f}" if cond1 else "Scanning..."
        )
        c2.metric(
            "RSI Divergence",
            "BEARISH" if cond2 else "NONE",
            delta=f"RSI High: {scan.get('rsi_high', 0):.1f}" if cond2 else "No divergence"
        )
        c3.metric(
            "Trigger",
            "MET" if cond3 else "WAITING",
            delta=f"${price:.2f} vs ${trigger:.2f}"
        )

        if all_met and scan.get("case_trade"):
            ct = scan["case_trade"]
            st_app.markdown(f"""
            <div style="background: rgba(0,255,136,0.1); border: 2px solid #00ff88;
                        border-radius: 12px; padding: 20px; margin-top: 16px;">
                <div style="font-family: 'Orbitron', monospace; font-size: 16px; color: #00ff88;
                            letter-spacing: 2px; margin-bottom: 12px;">
                    CASE TRADE ACTIVE — {ct['symbol']} {ct['side']}
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
                            font-family: 'JetBrains Mono', monospace;">
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                        <div style="color: #556677; font-size: 10px;">ENTRY ZONE</div>
                        <div style="color: #00ff88; font-size: 14px; font-weight: 700;">
                            ${ct['entry_zone'][0]}–${ct['entry_zone'][1]}
                        </div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                        <div style="color: #556677; font-size: 10px;">STOP LOSS</div>
                        <div style="color: #ff4444; font-size: 14px; font-weight: 700;">${ct['stop_loss']}</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                        <div style="color: #556677; font-size: 10px;">TP1</div>
                        <div style="color: #ffdd00; font-size: 14px; font-weight: 700;">${ct['tp1']}</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">
                        <div style="color: #556677; font-size: 10px;">TP2</div>
                        <div style="color: #58a6ff; font-size: 14px; font-weight: 700;">${ct['tp2']}</div>
                    </div>
                </div>
                <div style="margin-top: 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #8899aa;">
                    Risk: {ct['risk_pct_of_equity']*100:.1f}% of portfolio | Setup: {ct['setup']} | TF: {ct['timeframe']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif not all_met:
            conditions_met = sum([cond1, cond2, cond3])
            st_app.markdown(f"""
            <div style="background: rgba(88,166,255,0.1); border: 1px solid #58a6ff;
                        border-radius: 8px; padding: 16px; margin-top: 16px; direction: rtl; text-align: right;">
                <div style="color: #58a6ff; font-size: 14px; font-weight: 700; margin-bottom: 8px;">
                    STANDBY — {conditions_met}/3 תנאים מתקיימים
                </div>
                <div style="color: #8899aa; font-size: 12px; line-height: 1.8;">
                    {'✅' if cond1 else '❌'} Wyckoff Distribution + UTAD<br>
                    {'✅' if cond2 else '❌'} RSI Bearish Divergence (30m)<br>
                    {'✅' if cond3 else '❌'} Trigger: מחיר מתחת ${trigger:.2f}<br><br>
                    כשהשלושה יתקיימו — Case Trade יופעל אוטומטית.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Raw data expander
        with st_app.expander("Raw Wyckoff Data"):
            st_app.json({
                "wyckoff": {k: v for k, v in w.items() if k not in ['bc_idx', 'utad_idx']},
                "current_price": price,
                "trigger": trigger,
                "rsi_divergence": scan["rsi_divergence"],
            })


# ---------------------------------------------------------------------------
# STANDALONE TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== ORACLE NODE v2 — RAPID STRIKE TEST ===\n")

    # Test 1: Fresh intel, inner circle
    result = _compute_validation(
        intel_direction="LONG",
        source_reliability=5,
        netflow_val=-2500,
        whale_ratio_val=0.45,
        funding_val=-0.015,
        mvrv_val=1.8,
        fng_val=14,
        sentiment_val=0.1,
        leak_detected=False,
        hours_since_input=0.08,  # 5 minutes ago
        token_data={"price": 0.001284, "change_24h": 109, "pump_score": 3, "vol_spike": True, "market_cap": 5000000},
    )

    print(f"TEST 1 — Inner Circle + Already Pumped Token:")
    print(f"  Prior: {result['prior']*100:.1f}%")
    print(f"  Posterior: {result['posterior']*100:.1f}%")
    print(f"  Gate: {'OPEN' if result['gate_open'] else 'LOCKED'}")
    print(f"  Action: {result['action']}")
    print(f"  Kelly: {result['kelly']*100:.1f}%")
    if result['entry_price']:
        print(f"  Entry: ${result['entry_price']:.6f}")
        print(f"  TP: ${result['take_profit']:.6f}")
        print(f"  SL: ${result['stop_loss']:.6f}")
    print()

    # Test 2: Fresh intel, clean token
    result2 = _compute_validation(
        intel_direction="LONG",
        source_reliability=5,
        netflow_val=-2500,
        whale_ratio_val=0.45,
        funding_val=-0.015,
        mvrv_val=1.8,
        fng_val=14,
        sentiment_val=0.1,
        leak_detected=False,
        hours_since_input=0.08,
        token_data={"price": 0.0006, "change_24h": 5, "pump_score": 0, "vol_spike": False, "market_cap": 50000000},
    )

    print(f"TEST 2 — Inner Circle + Clean Token (no prior pump):")
    print(f"  Prior: {result2['prior']*100:.1f}%")
    print(f"  Posterior: {result2['posterior']*100:.1f}%")
    print(f"  Gate: {'OPEN' if result2['gate_open'] else 'LOCKED'}")
    print(f"  Action: {result2['action']}")
    print(f"  Kelly: {result2['kelly']*100:.1f}%")
    if result2['entry_price']:
        print(f"  Entry: ${result2['entry_price']:.6f}")
        print(f"  TP: ${result2['take_profit']:.6f}")
        print(f"  SL: ${result2['stop_loss']:.6f}")
