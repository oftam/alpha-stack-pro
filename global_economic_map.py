"""
Global Economic Intelligence Map - Renaissance Protocol
ELITE v20 | MEDALLION | LIVE FEED | ZERO EMOTION

A futuristic, sci-fi mission control map module for Streamlit.
Renders an interactive Leaflet.js map with real-time economic data,
geopolitical hotspots, BTC mining zones, and animated trade routes.

Usage:
    from global_economic_map import render_global_map
    render_global_map(st)
"""

import json
import requests
import pandas as pd
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# DATA FETCHING LAYER
# ---------------------------------------------------------------------------

def _fetch_btc_price():
    """Fetch BTC price and 24h change from CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
            timeout=8,
        )
        r.raise_for_status()
        d = r.json()["bitcoin"]
        return {
            "price": round(d.get("usd", 0), 2),
            "change_24h": round(d.get("usd_24h_change", 0), 2),
        }
    except Exception:
        return {"price": 0, "change_24h": 0}


def _fetch_fear_greed():
    """Fetch Fear & Greed Index from alternative.me."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        r.raise_for_status()
        d = r.json()["data"][0]
        return {
            "value": int(d.get("value", 0)),
            "label": d.get("value_classification", "N/A"),
        }
    except Exception:
        return {"value": 0, "label": "N/A"}


def _fetch_yfinance_quote(ticker):
    """Fetch latest close price from yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        h = t.history(period="2d")
        if len(h) > 0:
            return round(float(h["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return 0.0


def _fetch_earthquakes():
    """Fetch M2.5+ earthquakes from USGS (past 7 days)."""
    try:
        r = requests.get(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson",
            timeout=10,
        )
        r.raise_for_status()
        features = r.json().get("features", [])
        quakes = []
        for f in features[:200]:  # cap at 200 for performance
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            quakes.append({
                "lat": round(coords[1], 3),
                "lng": round(coords[0], 3),
                "mag": round(props.get("mag", 0) or 0, 1),
                "place": (props.get("place", "") or "")[:60],
            })
        return quakes
    except Exception:
        return []


def _collect_all_data(st_cache_data=None):
    """Collect all data, optionally using Streamlit cache."""
    btc = _fetch_btc_price()
    fng = _fetch_fear_greed()
    gold = _fetch_yfinance_quote("GC=F")
    oil = _fetch_yfinance_quote("CL=F")
    vix = _fetch_yfinance_quote("^VIX")
    dxy = _fetch_yfinance_quote("DX-Y.NYB")
    sp500 = _fetch_yfinance_quote("^GSPC")
    earthquakes = _fetch_earthquakes()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return {
        "btc_price": btc["price"],
        "btc_change": btc["change_24h"],
        "fng_value": fng["value"],
        "fng_label": fng["label"],
        "gold": gold,
        "oil": oil,
        "vix": vix,
        "dxy": dxy,
        "sp500": sp500,
        "earthquakes": earthquakes,
        "eq_count": len(earthquakes),
        "timestamp": now_utc,
    }


# ---------------------------------------------------------------------------
# GEOGRAPHIC DATA
# ---------------------------------------------------------------------------

ECONOMIC_NODES = [
    # Major Financial Centers
    {"name": "New York", "lat": 40.7128, "lng": -74.0060, "type": "finance", "label": "NYSE / Wall St"},
    {"name": "Silicon Valley", "lat": 37.3861, "lng": -122.0839, "type": "tech", "label": "Big Tech HQ"},
    {"name": "London", "lat": 51.5074, "lng": -0.1278, "type": "finance", "label": "City of London"},
    {"name": "Frankfurt", "lat": 50.1109, "lng": 8.6821, "type": "finance", "label": "ECB / Deutsche Borse"},
    {"name": "Zurich", "lat": 47.3769, "lng": 8.5417, "type": "finance", "label": "Swiss Banking / Gold"},
    {"name": "Shanghai", "lat": 31.2304, "lng": 121.4737, "type": "finance", "label": "SSE / PBoC"},
    {"name": "Beijing", "lat": 39.9042, "lng": 116.4074, "type": "gov", "label": "CCP / Policy"},
    {"name": "Tokyo", "lat": 35.6762, "lng": 139.6503, "type": "finance", "label": "BOJ / Nikkei"},
    {"name": "Dubai", "lat": 25.2048, "lng": 55.2708, "type": "finance", "label": "DIFC / Crypto Hub"},
    {"name": "Riyadh", "lat": 24.7136, "lng": 46.6753, "type": "energy", "label": "Saudi Aramco"},
    {"name": "Singapore", "lat": 1.3521, "lng": 103.8198, "type": "finance", "label": "MAS / Crypto Hub"},
    {"name": "Taipei", "lat": 25.0330, "lng": 121.5654, "type": "tech", "label": "TSMC / Semiconductors"},
    {"name": "Moscow", "lat": 55.7558, "lng": 37.6173, "type": "energy", "label": "MOEX / Energy"},
    {"name": "Sao Paulo", "lat": -23.5505, "lng": -46.6333, "type": "finance", "label": "B3 / LatAm Hub"},
    {"name": "Lagos", "lat": 6.5244, "lng": 3.3792, "type": "emerging", "label": "Africa Fintech"},
    {"name": "Johannesburg", "lat": -26.2041, "lng": 28.0473, "type": "finance", "label": "JSE / Mining"},
    {"name": "Sydney", "lat": -33.8688, "lng": 151.2093, "type": "finance", "label": "ASX / Pacific"},
    {"name": "Mumbai", "lat": 19.0760, "lng": 72.8777, "type": "finance", "label": "BSE / NSE India"},
    {"name": "Hong Kong", "lat": 22.3193, "lng": 114.1694, "type": "finance", "label": "HKEX / Gateway"},
    {"name": "Seoul", "lat": 37.5665, "lng": 126.9780, "type": "tech", "label": "Samsung / KRX"},
    {"name": "Chicago", "lat": 41.8781, "lng": -87.6298, "type": "finance", "label": "CME / Derivatives"},
    {"name": "Toronto", "lat": 43.6532, "lng": -79.3832, "type": "finance", "label": "TSX / Mining"},
    {"name": "Paris", "lat": 48.8566, "lng": 2.3522, "type": "finance", "label": "Euronext"},
    {"name": "Amsterdam", "lat": 52.3676, "lng": 4.9041, "type": "tech", "label": "ASML / Euronext"},
    {"name": "Tel Aviv", "lat": 32.0853, "lng": 34.7818, "type": "tech", "label": "TASE / Cyber"},
    {"name": "Shenzhen", "lat": 22.5431, "lng": 114.0579, "type": "tech", "label": "SZSE / Hardware"},
    {"name": "Abu Dhabi", "lat": 24.4539, "lng": 54.3773, "type": "energy", "label": "ADIA / Sovereign"},
    {"name": "Doha", "lat": 25.2854, "lng": 51.5310, "type": "energy", "label": "QIA / LNG"},
    {"name": "Mexico City", "lat": 19.4326, "lng": -99.1332, "type": "emerging", "label": "BMV / Nearshoring"},
    {"name": "Jakarta", "lat": -6.2088, "lng": 106.8456, "type": "emerging", "label": "IDX / Commodities"},
]

HOTSPOTS = [
    {"name": "Bushehr", "lat": 28.9684, "lng": 50.8385, "threat": "Nuclear Facility"},
    {"name": "Natanz", "lat": 33.7225, "lng": 51.7267, "threat": "Enrichment Site"},
    {"name": "Tehran", "lat": 35.6892, "lng": 51.3890, "threat": "Command Center"},
    {"name": "Strait of Hormuz", "lat": 26.5667, "lng": 56.2500, "threat": "Oil Chokepoint - 21% Global"},
    {"name": "Taiwan Strait", "lat": 24.0000, "lng": 119.5000, "threat": "Chip Supply Risk"},
    {"name": "Ukraine Front", "lat": 48.3794, "lng": 31.1656, "threat": "Active Conflict Zone"},
]

MINING_ZONES = [
    {"name": "Kazakhstan", "lat": 48.0196, "lng": 66.9237, "hashrate": "18.1%", "pct": 18.1},
    {"name": "Texas, USA", "lat": 31.9686, "lng": -99.9018, "hashrate": "14.0%", "pct": 14.0},
    {"name": "BC, Canada", "lat": 53.7267, "lng": -127.6476, "hashrate": "7.2%", "pct": 7.2},
    {"name": "Iceland", "lat": 64.9631, "lng": -19.0208, "hashrate": "5.5%", "pct": 5.5},
    {"name": "Sichuan, China", "lat": 30.5728, "lng": 102.0000, "hashrate": "4.8%", "pct": 4.8},
]

CONNECTION_LINES = [
    # Oil routes (red)
    {"from": [26.5667, 56.25], "to": [50.1109, 8.6821], "type": "oil", "label": "Persian Gulf > Europe"},
    {"from": [26.5667, 56.25], "to": [31.2304, 121.4737], "type": "oil", "label": "Persian Gulf > China"},
    {"from": [26.5667, 56.25], "to": [35.6762, 139.6503], "type": "oil", "label": "Persian Gulf > Japan"},
    {"from": [26.5667, 56.25], "to": [19.0760, 72.8777], "type": "oil", "label": "Persian Gulf > India"},
    # Tech/Chip routes (cyan/blue)
    {"from": [25.0330, 121.5654], "to": [37.3861, -122.0839], "type": "tech", "label": "TSMC > Silicon Valley"},
    {"from": [25.0330, 121.5654], "to": [50.1109, 8.6821], "type": "tech", "label": "TSMC > Europe"},
    {"from": [25.0330, 121.5654], "to": [35.6762, 139.6503], "type": "tech", "label": "TSMC > Japan"},
    {"from": [52.3676, 4.9041], "to": [25.0330, 121.5654], "type": "tech", "label": "ASML > TSMC"},
    # Capital flows (gold)
    {"from": [40.7128, -74.006], "to": [51.5074, -0.1278], "type": "capital", "label": "NY > London"},
    {"from": [40.7128, -74.006], "to": [35.6762, 139.6503], "type": "capital", "label": "NY > Tokyo"},
    {"from": [40.7128, -74.006], "to": [31.2304, 121.4737], "type": "capital", "label": "NY > Shanghai"},
    {"from": [40.7128, -74.006], "to": [1.3521, 103.8198], "type": "capital", "label": "NY > Singapore"},
    {"from": [40.7128, -74.006], "to": [25.2048, 55.2708], "type": "capital", "label": "NY > Dubai"},
    # Gold routes (amber)
    {"from": [47.3769, 8.5417], "to": [40.7128, -74.006], "type": "gold", "label": "Zurich > NY"},
    {"from": [47.3769, 8.5417], "to": [51.5074, -0.1278], "type": "gold", "label": "Zurich > London"},
    {"from": [47.3769, 8.5417], "to": [31.2304, 121.4737], "type": "gold", "label": "Zurich > Shanghai"},
    # BTC Hashrate routes (green)
    {"from": [48.0196, 66.9237], "to": [40.7128, -74.006], "type": "btc", "label": "Kazakhstan > NY"},
    {"from": [31.9686, -99.9018], "to": [40.7128, -74.006], "type": "btc", "label": "Texas > NY"},
    {"from": [64.9631, -19.0208], "to": [40.7128, -74.006], "type": "btc", "label": "Iceland > NY"},
]


# ---------------------------------------------------------------------------
# HTML TEMPLATE BUILDER
# ---------------------------------------------------------------------------

def _build_html(data: dict) -> str:
    """Build the complete HTML/CSS/JS string for the map."""

    nodes_json = json.dumps(ECONOMIC_NODES)
    hotspots_json = json.dumps(HOTSPOTS)
    mining_json = json.dumps(MINING_ZONES)
    connections_json = json.dumps(CONNECTION_LINES)
    earthquakes_json = json.dumps(data.get("earthquakes", []))

    btc_price = data.get("btc_price", 0)
    btc_change = data.get("btc_change", 0)
    fng_value = data.get("fng_value", 0)
    fng_label = data.get("fng_label", "N/A")
    gold = data.get("gold", 0)
    oil = data.get("oil", 0)
    vix = data.get("vix", 0)
    dxy = data.get("dxy", 0)
    sp500 = data.get("sp500", 0)
    eq_count = data.get("eq_count", 0)
    timestamp = data.get("timestamp", "")

    # Determine FnG color
    if fng_value <= 25:
        fng_color = "#ff2020"
    elif fng_value <= 45:
        fng_color = "#ff8800"
    elif fng_value <= 55:
        fng_color = "#ffdd00"
    elif fng_value <= 75:
        fng_color = "#88ff00"
    else:
        fng_color = "#00ff88"

    btc_color = "#00ff88" if btc_change >= 0 else "#ff2020"
    btc_arrow = "+" if btc_change >= 0 else ""

    vix_color = "#00ff88" if vix < 20 else ("#ffdd00" if vix < 30 else "#ff2020")

    # ------------------------------------------------------------------
    # HEBREW INTELLIGENCE BRIEFING — NARRATIVE ANALYSIS (reads the map)
    # ------------------------------------------------------------------

    # Build narrative paragraphs that INTERPRET the map, not repeat numbers
    narrative_lines = []

    # --- Earthquake geo-intelligence: scan quakes near critical zones ---
    earthquakes = data.get('earthquakes', [])
    quake_near_hormuz = []  # lat 24-29, lng 50-60 (Persian Gulf / Hormuz)
    quake_near_iran = []    # lat 25-38, lng 44-63 (Iran)
    quake_near_taiwan = []  # lat 20-28, lng 118-125 (Taiwan Strait)
    quake_near_mining = []  # Kazakhstan lat 40-55, lng 50-87 | Iceland lat 63-67, lng -25--13
    quake_significant = []  # M5.0+
    for eq in earthquakes:
        lat, lng, mag = eq.get('lat', 0), eq.get('lng', 0), eq.get('mag', 0)
        place = eq.get('place', '')
        if 24 <= lat <= 29 and 50 <= lng <= 60:
            quake_near_hormuz.append(eq)
        if 25 <= lat <= 38 and 44 <= lng <= 63:
            quake_near_iran.append(eq)
        if 20 <= lat <= 28 and 118 <= lng <= 125:
            quake_near_taiwan.append(eq)
        if (40 <= lat <= 55 and 50 <= lng <= 87) or (63 <= lat <= 67 and -25 <= lng <= -13):
            quake_near_mining.append(eq)
        if mag >= 5.0:
            quake_significant.append(eq)

    # Build seismic alert line if quakes near critical zones
    seismic_alerts = []
    if quake_near_hormuz:
        max_mag = max(q.get('mag', 0) for q in quake_near_hormuz)
        seismic_alerts.append(f'<span style="color:#ff4444;">\u26a0 \u05e8\u05e2\u05d9\u05d3\u05d4 \u05dc\u05d9\u05d3 \u05d4\u05d5\u05e8\u05de\u05d5\u05d6! M{max_mag:.1f} \u2014 \u05e1\u05d9\u05db\u05d5\u05df \u05dc\u05e7\u05d5\u05d5\u05d9 \u05d4\u05e0\u05e4\u05d8 \u05d5\u05ea\u05e9\u05ea\u05d9\u05d5\u05ea \u05d4\u05de\u05e4\u05e8\u05e5. {len(quake_near_hormuz)} \u05d0\u05d9\u05e8\u05d5\u05e2\u05d9\u05dd \u05d1\u05d0\u05d6\u05d5\u05e8.</span>')  # ⚠ רעידה ליד הורמוז! MX.X — סיכון לקווי הנפט ותשתיות המפרץ
    if quake_near_iran and not quake_near_hormuz:
        max_mag = max(q.get('mag', 0) for q in quake_near_iran)
        seismic_alerts.append(f'<span style="color:#ff8800;">\u26a0 \u05e8\u05e2\u05d9\u05d3\u05d4 \u05d1\u05d0\u05d9\u05e8\u05d0\u05df M{max_mag:.1f} \u2014 \u05dc\u05d9\u05d3 \u05de\u05ea\u05e7\u05e0\u05d9\u05dd \u05d2\u05e8\u05e2\u05d9\u05e0\u05d9\u05d9\u05dd/\u05e6\u05d1\u05d0\u05d9\u05d9\u05dd. \u05de\u05e2\u05dc\u05d4 \u05de\u05ea\u05d7 \u05d2\u05d9\u05d0\u05d5\u05e4\u05d5\u05dc\u05d9\u05d8\u05d9.</span>')  # ⚠ רעידה באיראן MX.X — ליד מתקנים גרעיניים/צבאיים. מעלה מתח גיאופוליטי.
    if quake_near_taiwan:
        max_mag = max(q.get('mag', 0) for q in quake_near_taiwan)
        seismic_alerts.append(f'<span style="color:#ff8800;">\u26a0 \u05e8\u05e2\u05d9\u05d3\u05d4 \u05dc\u05d9\u05d3 \u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df M{max_mag:.1f} \u2014 \u05e1\u05d9\u05db\u05d5\u05df \u05dc\u05e9\u05e8\u05e9\u05e8\u05ea \u05d4\u05e9\u05d1\u05d1\u05d9\u05dd TSMC.</span>')  # ⚠ רעידה ליד טייוואן MX.X — סיכון לשרשרת השבבים TSMC.
    if quake_near_mining:
        max_mag = max(q.get('mag', 0) for q in quake_near_mining)
        seismic_alerts.append(f'<span style="color:#ffa000;">\u26a0 \u05e8\u05e2\u05d9\u05d3\u05d4 \u05d1\u05d0\u05d6\u05d5\u05e8 \u05db\u05e8\u05d9\u05d9\u05d4 M{max_mag:.1f} \u2014 \u05e1\u05d9\u05db\u05d5\u05df \u05dc\u05d7\u05d5\u05d5\u05ea \u05db\u05e8\u05d9\u05d9\u05d4 \u05d5-hashrate.</span>')  # ⚠ רעידה באזור כרייה MX.X — סיכון לחוות כרייה ו-hashrate.
    if quake_significant:
        top = sorted(quake_significant, key=lambda q: q.get('mag', 0), reverse=True)[:3]
        for q in top:
            if q not in quake_near_hormuz and q not in quake_near_iran and q not in quake_near_taiwan:
                seismic_alerts.append(f'<span style="color:#ffa000;">\u26a0 M{q["mag"]:.1f} \u2014 {q["place"]}. \u05dc\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8 \u05d4\u05e9\u05e4\u05e2\u05d5\u05ea \u05e2\u05dc \u05ea\u05e9\u05ea\u05d9\u05d5\u05ea.</span>')  # ⚠ MX.X — place. לעקוב אחר השפעות על תשתיות.

    # Insert seismic alerts at the top of narrative if any exist
    if seismic_alerts:
        narrative_lines.append('<span style="color:#ff2020; font-weight:700; font-size:13px;">\u2622\ufe0f \u05d4\u05ea\u05e8\u05d0\u05d5\u05ea \u05e1\u05d9\u05d9\u05e1\u05de\u05d9\u05d5\u05ea \u05d7\u05d9\u05d5\u05ea:</span>')  # ☢️ התראות סייסמיות חיות:
        narrative_lines.extend(seismic_alerts)
        narrative_lines.append('')  # spacer

    # --- Paragraph 1: Oil routes & Hormuz ---
    if oil >= 85:
        narrative_lines.append(f'<span style="color:#ff4444;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05e0\u05e4\u05d8 \u05de\u05d4\u05de\u05e4\u05e8\u05e5 \u05dc\u05d0\u05d9\u05e8\u05d5\u05e4\u05d4, \u05e1\u05d9\u05df \u05d5\u05d9\u05e4\u05df \u05ea\u05d7\u05ea \u05dc\u05d7\u05e5. \u05de\u05e6\u05e8 \u05d4\u05d5\u05e8\u05de\u05d5\u05d6 \u2014 \u05e6\u05d5\u05d5\u05d0\u05e8 \u05e6\u05e8 \u05e7\u05e8\u05d9\u05d8\u05d9. \u05e1\u05d9\u05db\u05d5\u05df \u05d0\u05d9\u05e0\u05e4\u05dc\u05e6\u05d9\u05d4 \u05e2\u05d5\u05dc\u05de\u05d9\u05ea \u05e2\u05d5\u05dc\u05d4.</span>')  # קווי הנפט מהמפרץ לאירופה, סין ויפן תחת לחץ. מצר הורמוז — צוואר צר קריטי. סיכון אינפלציה עולמית עולה.
    elif oil >= 70:
        narrative_lines.append(f'<span style="color:#ff8800;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05e0\u05e4\u05d8 \u05de\u05d4\u05de\u05e4\u05e8\u05e5 \u05e4\u05e2\u05d9\u05dc\u05d9\u05dd \u05d0\u05da \u05ea\u05d7\u05ea \u05de\u05ea\u05d7. \u05de\u05e6\u05e8 \u05d4\u05d5\u05e8\u05de\u05d5\u05d6 \u05e4\u05ea\u05d5\u05d7 \u05d0\u05da \u05ea\u05d7\u05ea \u05d0\u05d9\u05d5\u05dd. \u05e4\u05e8\u05de\u05d9\u05d9\u05ea \u05e1\u05d9\u05db\u05d5\u05df \u05e2\u05dc \u05d4\u05d0\u05e1\u05e4\u05e7\u05d4.</span>')  # קווי הנפט מהמפרץ פעילים אך תחת מתח. מצר הורמוז פתוח אך תחת איום. פרמיית סיכון על האספקה.
    else:
        narrative_lines.append(f'<span style="color:#00ff88;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05e0\u05e4\u05d8 \u05de\u05d4\u05de\u05e4\u05e8\u05e5 \u05d6\u05d5\u05e8\u05de\u05d9\u05dd \u05d1\u05e9\u05d2\u05e8\u05d4. \u05de\u05e6\u05e8 \u05d4\u05d5\u05e8\u05de\u05d5\u05d6 \u05e4\u05ea\u05d5\u05d7. \u05d0\u05d9\u05df \u05dc\u05d7\u05e5 \u05e2\u05dc \u05e9\u05e8\u05e9\u05e8\u05ea \u05d4\u05d0\u05e0\u05e8\u05d2\u05d9\u05d4.</span>')  # קווי הנפט מהמפרץ זורמים בשגרה. מצר הורמוז פתוח. אין לחץ על שרשרת האנרגיה.

    # --- Paragraph 2: Gold & Safe Haven flows ---
    if gold >= 2500 and fng_value <= 25:
        narrative_lines.append(f'<span style="color:#ffd700;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05d6\u05d4\u05d1 \u05de\u05e6\u05d5\u05e8\u05d9\u05da \u05dc\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05d5\u05dc\u05dc\u05d5\u05e0\u05d3\u05d5\u05df \u05d1\u05d5\u05e2\u05e8\u05d9\u05dd. \u05d4\u05db\u05e1\u05e3 \u05d4\u05d7\u05db\u05dd \u05d1\u05d5\u05e8\u05d7 \u05dc\u05de\u05e7\u05dc\u05d8 \u2014 Flight to Safety \u05e7\u05dc\u05d0\u05e1\u05d9. \u05d6\u05d4\u05d1 \u05d1\u05e9\u05d9\u05d0 \u05d4\u05d9\u05e1\u05d8\u05d5\u05e8\u05d9.</span>')  # קווי הזהב מצוריך לניו יורק וללונדון בוערים. הכסף החכם בורח למקלט — Flight to Safety קלאסי. זהב בשיא היסטורי.
    elif gold >= 2000:
        narrative_lines.append(f'<span style="color:#cc8800;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05d6\u05d4\u05d1 \u05de\u05e6\u05d5\u05e8\u05d9\u05da \u05dc\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05d5\u05dc\u05dc\u05d5\u05e0\u05d3\u05d5\u05df \u05e4\u05e2\u05d9\u05dc\u05d9\u05dd. \u05d6\u05e8\u05d9\u05de\u05ea \u05d4\u05d5\u05df \u05dc\u05e0\u05db\u05e1\u05d9 \u05de\u05e7\u05dc\u05d8 \u05de\u05d5\u05d2\u05d1\u05e8\u05ea.</span>')  # קווי הזהב מצוריך לניו יורק וללונדון פעילים. זרימת הון לנכסי מקלט מוגברת.
    else:
        narrative_lines.append(f'<span style="color:#556677;">\u05e7\u05d5\u05d5\u05d9 \u05d4\u05d6\u05d4\u05d1 \u05d1\u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u05e8\u05d2\u05d9\u05dc\u05d4. \u05d0\u05d9\u05df \u05d1\u05e8\u05d9\u05d7\u05d4 \u05de\u05e9\u05de\u05e2\u05d5\u05ea\u05d9\u05ea \u05dc\u05de\u05e7\u05dc\u05d8.</span>')  # קווי הזהב בפעילות רגילה. אין בריחה משמעותית למקלט.

    # --- Paragraph 3: Tech/Chip supply chain ---
    if vix >= 30:
        narrative_lines.append(f'<span style="color:#00ccff;">\u05e9\u05e8\u05e9\u05e8\u05ea \u05d4\u05e9\u05d1\u05d1\u05d9\u05dd TSMC-ASML \u05ea\u05d7\u05ea \u05dc\u05d7\u05e5. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05de\u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df \u05dc\u05e1\u05d9\u05dc\u05d9\u05e7\u05d5\u05df \u05d5\u05d0\u05dc\u05d9, \u05d0\u05d9\u05e8\u05d5\u05e4\u05d4 \u05d5\u05d9\u05e4\u05df \u05e4\u05d2\u05d9\u05e2\u05d9\u05dd \u05d0\u05da \u05de\u05e6\u05e8 \u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df \u05de\u05d4\u05d5\u05d5\u05d4 \u05e1\u05d9\u05db\u05d5\u05df.</span>')  # שרשרת השבבים TSMC-ASML תחת לחץ. הקווים מטייוואן לסיליקון ואלי, אירופה ויפן פגיעים אך מצר טייוואן מהווה סיכון.
    else:
        narrative_lines.append(f'<span style="color:#00ccff;">\u05e9\u05e8\u05e9\u05e8\u05ea \u05d4\u05e9\u05d1\u05d1\u05d9\u05dd \u05ea\u05e7\u05d9\u05e0\u05d4. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05de\u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df \u05dc\u05e1\u05d9\u05dc\u05d9\u05e7\u05d5\u05df \u05d5\u05d0\u05dc\u05d9, \u05d0\u05d9\u05e8\u05d5\u05e4\u05d4 \u05d5\u05d9\u05e4\u05df \u05d6\u05d5\u05e8\u05de\u05d9\u05dd \u05d1\u05e9\u05d2\u05e8\u05d4. ASML \u05de\u05d6\u05d9\u05e0\u05d4 \u05dc-TSMC \u05dc\u05dc\u05d0 \u05d4\u05e4\u05e8\u05e2\u05d4.</span>')  # שרשרת השבבים תקינה. הקווים מטייוואן לסיליקון ואלי, אירופה ויפן זורמים בשגרה. ASML מזינה ל-TSMC ללא הפרעה.

    # --- Paragraph 4: Capital flows ---
    if dxy >= 105:
        narrative_lines.append(f'<span style="color:#ffd700;">\u05d4\u05d5\u05df \u05d6\u05d5\u05e8\u05dd \u05dc\u05d3\u05d5\u05dc\u05e8. \u05e7\u05d5\u05d5\u05d9 \u05d4\u05d4\u05d5\u05df \u05de\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05dc\u05dc\u05d5\u05e0\u05d3\u05d5\u05df, \u05d8\u05d5\u05e7\u05d9\u05d5, \u05e9\u05e0\u05d2\u05d7\u05d0\u05d9 \u05d5\u05d3\u05d5\u05d1\u05d0\u05d9 \u05de\u05e8\u05d0\u05d9\u05dd \u05d3\u05d5\u05de\u05d9\u05e0\u05e0\u05d8\u05d9\u05d5\u05ea \u05d3\u05d5\u05dc\u05e8\u05d9\u05ea. \u05e8\u05e2 \u05dc-BTC.</span>')  # הון זורם לדולר. קווי ההון מניו יורק ללונדון, טוקיו, שנגחאי ודובאי מראים דומיננטיות דולרית. רע ל-BTC.
    elif dxy >= 100:
        narrative_lines.append(f'<span style="color:#ffdd00;">\u05d4\u05d5\u05df \u05d6\u05d5\u05e8\u05dd \u05dc\u05d3\u05d5\u05dc\u05e8 \u05d1\u05de\u05ea\u05d9\u05e0\u05d5\u05ea. \u05e7\u05d5\u05d5\u05d9 \u05d4\u05d4\u05d5\u05df \u05de\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05dc\u05e9\u05d5\u05d5\u05e7\u05d9\u05dd \u05d4\u05e2\u05d5\u05dc\u05de\u05d9\u05d9\u05dd \u05e4\u05e2\u05d9\u05dc\u05d9\u05dd \u05d0\u05da \u05dc\u05d0 \u05d0\u05d2\u05e8\u05e1\u05d9\u05d1\u05d9\u05d9\u05dd.</span>')  # הון זורם לדולר במתינות. קווי ההון מניו יורק לשווקים העולמיים פעילים אך לא אגרסיביים.
    else:
        narrative_lines.append(f'<span style="color:#00ff88;">\u05d3\u05d5\u05dc\u05e8 \u05e0\u05d7\u05dc\u05e9. \u05e7\u05d5\u05d5\u05d9 \u05d4\u05d4\u05d5\u05df \u05de\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05de\u05e8\u05d0\u05d9\u05dd \u05d4\u05d5\u05df \u05d6\u05d5\u05e8\u05dd \u05d4\u05d7\u05d5\u05e6\u05d4 \u2014 \u05e1\u05d1\u05d9\u05d1\u05d4 \u05d7\u05d9\u05d5\u05d1\u05d9\u05ea \u05dc-BTC.</span>')  # דולר נחלש. קווי ההון מניו יורק מראים הון זורם החוצה — סביבה חיובית ל-BTC.

    # --- Paragraph 5: BTC Mining network ---
    narrative_lines.append(f'<span style="color:#00ff88;">\u05e8\u05e9\u05ea \u05db\u05e8\u05d9\u05d9\u05ea BTC \u05e4\u05e2\u05d9\u05dc\u05d4. \u05e7\u05d6\u05d7\u05e1\u05d8\u05df 18.1%, \u05d8\u05e7\u05e1\u05e1 14%, \u05e7\u05e0\u05d3\u05d4 7.2%, \u05d0\u05d9\u05e1\u05dc\u05e0\u05d3 5.5%. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05dc\u05e0\u05d9\u05d5 \u05d9\u05d5\u05e8\u05e7 \u05d9\u05e6\u05d9\u05d1\u05d9\u05dd \u2014 \u05d4\u05e8\u05e9\u05ea \u05de\u05d1\u05d5\u05d6\u05e8\u05ea \u05d2\u05d9\u05d0\u05d5\u05d2\u05e8\u05e4\u05d9\u05ea.</span>')  # רשת כריית BTC פעילה. קזחסטן 18.1%, טקסס 14%, קנדה 7.2%, איסלנד 5.5%. הקווים לניו יורק יציבים — הרשת מבוזרת גיאוגרפית.

    # --- Paragraph 6: Hotspots & Geopolitical ---
    hotspot_count = 6  # 3 Iran + Taiwan + Ukraine
    iran_hotspots = 3
    if vix >= 25 and fng_value <= 25:
        narrative_lines.append(f'<span style="color:#ff2020;">6 \u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d7\u05de\u05d5\u05ea \u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u05e2\u05dc \u05d4\u05de\u05e4\u05d4. 3 \u05d1\u05d0\u05d9\u05e8\u05d0\u05df (\u05d2\u05e8\u05e2\u05d9\u05df, \u05e0\u05ea\u05e0\u05d6, \u05d8\u05d4\u05e8\u05d0\u05df), \u05de\u05e6\u05e8 \u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df \u05d5\u05d7\u05d6\u05d9\u05ea \u05d0\u05d5\u05e7\u05e8\u05d0\u05d9\u05e0\u05d4. \u05d4\u05e9\u05d5\u05e7 \u05de\u05ea\u05de\u05d7\u05e8 \u05d1\u05e1\u05d9\u05db\u05d5\u05df \u2014 \u05d4\u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d4\u05d0\u05d3\u05d5\u05de\u05d5\u05ea \u05de\u05e9\u05e4\u05d9\u05e2\u05d5\u05ea \u05e2\u05dc \u05db\u05dc \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd.</span>')  # 6 נקודות חמות פעילות על המפה. 3 באיראן (גרעין, נתנז, טהראן), מצר טייוואן וחזית אוקראינה. השוק מתמחר בסיכון — הנקודות האדומות משפיעות על כל הקווים.
    elif vix >= 20:
        narrative_lines.append(f'<span style="color:#ff8800;">6 \u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d7\u05de\u05d5\u05ea \u05e2\u05dc \u05d4\u05de\u05e4\u05d4. \u05d4\u05de\u05ea\u05d7 \u05d1\u05d0\u05d9\u05e8\u05d0\u05df \u05de\u05e9\u05e4\u05d9\u05e2 \u05e2\u05dc \u05e7\u05d5\u05d5\u05d9 \u05d4\u05e0\u05e4\u05d8 \u05d0\u05da \u05dc\u05d0 \u05d7\u05d5\u05e1\u05dd. \u05de\u05e6\u05e8 \u05d8\u05d9\u05d9\u05d5\u05d5\u05d0\u05df \u05d5\u05d0\u05d5\u05e7\u05e8\u05d0\u05d9\u05e0\u05d4 \u05d1\u05e8\u05e7\u05e2 \u2014 \u05e2\u05e8\u05e0\u05d5\u05ea \u05de\u05d5\u05d2\u05d1\u05e8\u05ea.</span>')  # 6 נקודות חמות על המפה. המתח באיראן משפיע על קווי הנפט אך לא חוסם. מצר טייוואן ואוקראינה ברקע — ערנות מוגברת.
    else:
        narrative_lines.append(f'<span style="color:#556677;">\u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d7\u05de\u05d5\u05ea \u05e7\u05d9\u05d9\u05de\u05d5\u05ea \u05d0\u05da \u05dc\u05d0 \u05de\u05e9\u05e4\u05d9\u05e2\u05d5\u05ea \u05e2\u05dc \u05d4\u05e9\u05d5\u05d5\u05e7\u05d9\u05dd \u05db\u05e8\u05d2\u05e2. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05d6\u05d5\u05e8\u05de\u05d9\u05dd \u05d1\u05e9\u05d2\u05e8\u05d4.</span>')  # נקודות חמות קיימות אך לא משפיעות על השווקים כרגע. הקווים זורמים בשגרה.

    # --- Paragraph 7: Seismic ---
    if eq_count >= 150:
        narrative_lines.append(f'<span style="color:#ffa000;">\u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u05e1\u05d9\u05d9\u05e1\u05de\u05d9\u05ea \u05d7\u05e8\u05d9\u05d2\u05d4 \u2014 {eq_count} \u05d0\u05d9\u05e8\u05d5\u05e2\u05d9\u05dd \u05d1-7 \u05d9\u05de\u05d9\u05dd. \u05e1\u05d9\u05db\u05d5\u05df \u05dc\u05ea\u05e9\u05ea\u05d9\u05d5\u05ea \u05d5\u05e9\u05e8\u05e9\u05e8\u05d5\u05ea \u05d0\u05e1\u05e4\u05e7\u05d4.</span>')  # פעילות סייסמית חריגה — X אירועים ב-7 ימים. סיכון לתשתיות ושרשרות אספקה.
    elif eq_count >= 80:
        narrative_lines.append(f'<span style="color:#cc8800;">\u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u05e1\u05d9\u05d9\u05e1\u05de\u05d9\u05ea \u05de\u05d5\u05d2\u05d1\u05e8\u05ea \u2014 {eq_count} \u05d0\u05d9\u05e8\u05d5\u05e2\u05d9\u05dd. \u05dc\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8 \u05d0\u05d6\u05d5\u05e8\u05d9 \u05db\u05e8\u05d9\u05d9\u05d4 \u05d5\u05ea\u05e9\u05ea\u05d9\u05d5\u05ea.</span>')  # פעילות סייסמית מוגברת — X אירועים. לעקוב אחר אזורי כרייה ותשתיות.

    # --- Final Conclusion ---
    if fng_value <= 20 and vix >= 25 and gold >= 2400:
        conclusion = '<span style="color:#ff4444; font-weight:700;">\u05d4\u05de\u05e4\u05d4 \u05d0\u05d5\u05de\u05e8\u05ea: Risk-Off. \u05d4\u05db\u05e1\u05e3 \u05d1\u05d5\u05e8\u05d7 \u05dc\u05d6\u05d4\u05d1 \u05d5\u05dc\u05d3\u05d5\u05dc\u05e8. \u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d7\u05de\u05d5\u05ea \u05de\u05e9\u05e4\u05d9\u05e2\u05d5\u05ea \u05e2\u05dc \u05db\u05dc \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd. \u05d4\u05de\u05ea\u05e0\u05d4.</span>'  # המפה אומרת: Risk-Off. הכסף בורח לזהב ולדולר. נקודות חמות משפיעות על כל הקווים. המתנה.
    elif fng_value <= 25 and vix < 22:
        conclusion = '<span style="color:#ffdd00; font-weight:700;">\u05d4\u05de\u05e4\u05d4 \u05d0\u05d5\u05de\u05e8\u05ea: \u05e4\u05d7\u05d3 \u05e7\u05de\u05e2\u05d5\u05e0\u05d0\u05d9, \u05dc\u05d0 \u05de\u05d5\u05e1\u05d3\u05d9. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05d6\u05d5\u05e8\u05de\u05d9\u05dd \u05d1\u05e9\u05d2\u05e8\u05d4 \u05d0\u05da \u05d4\u05e6\u05d9\u05d1\u05d5\u05e8 \u05de\u05e4\u05d7\u05d3. \u05e4\u05d5\u05d8\u05e0\u05e6\u05d9\u05d0\u05dc \u05e7\u05d5\u05e0\u05d8\u05e8\u05e8\u05d9\u05d0\u05e0\u05d9.</span>'  # המפה אומרת: פחד קמעונאי, לא מוסדי. הקווים זורמים בשגרה אך הציבור מפחד. פוטנציאל קונטרריאני.
    elif fng_value >= 70:
        conclusion = '<span style="color:#ff8800; font-weight:700;">\u05d4\u05de\u05e4\u05d4 \u05d0\u05d5\u05de\u05e8\u05ea: \u05ea\u05d0\u05d5\u05d5\u05d4 \u05de\u05d5\u05e4\u05e8\u05d6\u05ea. \u05d4\u05db\u05dc \u05d6\u05d5\u05e8\u05dd \u05d0\u05d1\u05dc \u05d6\u05d4 \u05d1\u05d3\u05d9\u05d5\u05e7 \u05d4\u05e8\u05d2\u05e2 \u05e9\u05dc\u05e4\u05e0\u05d9 \u05d4\u05ea\u05d9\u05e7\u05d5\u05df. \u05d6\u05d4\u05d9\u05e8\u05d5\u05ea.</span>'  # המפה אומרת: תאווה מופרזת. הכל זורם אבל זה בדיוק הרגע שלפני התיקון. זהירות.
    else:
        conclusion = '<span style="color:#00ccff; font-weight:700;">\u05d4\u05de\u05e4\u05d4 \u05d0\u05d5\u05de\u05e8\u05ea: \u05de\u05e2\u05d1\u05e8. \u05d4\u05e7\u05d5\u05d5\u05d9\u05dd \u05e4\u05e2\u05d9\u05dc\u05d9\u05dd, \u05d4\u05e0\u05e7\u05d5\u05d3\u05d5\u05ea \u05d4\u05d7\u05de\u05d5\u05ea \u05d1\u05e8\u05e7\u05e2. \u05d0\u05d9\u05df \u05d0\u05d5\u05ea \u05d7\u05d3 \u05de\u05e9\u05de\u05e2\u05d5\u05ea\u05d9 \u2014 \u05d4\u05de\u05e9\u05da \u05de\u05e2\u05e7\u05d1.</span>'  # המפה אומרת: מעבר. הקווים פעילים, הנקודות החמות ברקע. אין אות חד משמעותי — המשך מעקב.

    narrative_html = '<br>'.join(narrative_lines)
    conclusion_html = conclusion

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #0a0e17;
    color: #c0d0e0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    overflow-x: hidden;
  }}

  /* ---- HEADER ---- */
  .header {{
    background: linear-gradient(180deg, #0e1220 0%, #0a0e17 100%);
    border-bottom: 1px solid rgba(0, 255, 136, 0.15);
    padding: 12px 20px 8px 20px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00ff88, #00aaff, #ff0044, transparent);
    animation: headerScan 4s linear infinite;
  }}
  @keyframes headerScan {{
    0% {{ opacity: 0.3; }}
    50% {{ opacity: 1; }}
    100% {{ opacity: 0.3; }}
  }}
  .header-title {{
    font-family: 'Orbitron', sans-serif;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 3px;
    background: linear-gradient(90deg, #00ff88, #00ccff, #00ff88);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 3s linear infinite;
    text-transform: uppercase;
  }}
  @keyframes gradientShift {{
    0% {{ background-position: 0% center; }}
    100% {{ background-position: 200% center; }}
  }}
  .header-sub {{
    font-size: 10px;
    letter-spacing: 4px;
    color: #445566;
    margin-top: 2px;
  }}
  .header-sub span {{
    color: #00ff88;
  }}
  .header-time {{
    position: absolute;
    right: 20px;
    top: 14px;
    font-size: 11px;
    color: #336655;
    font-family: 'JetBrains Mono', monospace;
  }}
  .header-time .live-dot {{
    display: inline-block;
    width: 6px; height: 6px;
    background: #00ff88;
    border-radius: 50%;
    margin-right: 6px;
    animation: livePulse 1.5s ease-in-out infinite;
    vertical-align: middle;
  }}
  @keyframes livePulse {{
    0%, 100% {{ opacity: 1; box-shadow: 0 0 4px #00ff88; }}
    50% {{ opacity: 0.3; box-shadow: 0 0 12px #00ff88; }}
  }}

  /* ---- METRIC CARDS ---- */
  .metrics-row {{
    display: flex;
    gap: 8px;
    padding: 10px 20px;
    background: #0a0e17;
    overflow-x: auto;
    flex-wrap: nowrap;
  }}
  .metric-card {{
    flex: 1;
    min-width: 120px;
    background: rgba(10, 15, 25, 0.9);
    border: 1px solid rgba(0, 255, 136, 0.12);
    border-radius: 6px;
    padding: 10px 12px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }}
  .metric-card:hover {{
    border-color: rgba(0, 255, 136, 0.4);
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.08);
  }}
  .metric-card::before {{
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 1px;
    background: linear-gradient(90deg, transparent, var(--card-glow, #00ff88), transparent);
    animation: cardSweep 3s linear infinite;
  }}
  @keyframes cardSweep {{
    0% {{ left: -100%; }}
    100% {{ left: 100%; }}
  }}
  .metric-label {{
    font-size: 9px;
    letter-spacing: 2px;
    color: #556677;
    text-transform: uppercase;
    margin-bottom: 4px;
  }}
  .metric-value {{
    font-family: 'Orbitron', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: var(--card-color, #00ff88);
    text-shadow: 0 0 10px var(--card-glow, rgba(0,255,136,0.3));
  }}
  .metric-sub {{
    font-size: 9px;
    color: #445566;
    margin-top: 2px;
  }}

  /* ---- MAP CONTAINER ---- */
  #map {{
    width: 100%;
    height: 520px;
    background: #0a0e17;
    border-top: 1px solid rgba(0, 255, 136, 0.08);
    border-bottom: 1px solid rgba(0, 255, 136, 0.08);
  }}

  /* Leaflet overrides for dark theme */
  .leaflet-container {{
    background: #0a0e17 !important;
    font-family: 'JetBrains Mono', monospace !important;
  }}
  .leaflet-control-zoom a {{
    background: rgba(10, 15, 25, 0.9) !important;
    color: #00ff88 !important;
    border-color: rgba(0, 255, 136, 0.2) !important;
  }}
  .leaflet-control-attribution {{
    display: none !important;
  }}

  /* Custom markers */
  .node-marker {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #00ccff;
    box-shadow: 0 0 8px #00ccff, 0 0 20px rgba(0, 204, 255, 0.3);
    animation: nodeBreath 2.5s ease-in-out infinite;
    border: 1px solid rgba(0, 204, 255, 0.6);
  }}
  .node-marker.finance {{ background: #00ccff; box-shadow: 0 0 8px #00ccff, 0 0 20px rgba(0,204,255,0.3); border-color: rgba(0,204,255,0.6); }}
  .node-marker.tech {{ background: #aa44ff; box-shadow: 0 0 8px #aa44ff, 0 0 20px rgba(170,68,255,0.3); border-color: rgba(170,68,255,0.6); }}
  .node-marker.energy {{ background: #ff8800; box-shadow: 0 0 8px #ff8800, 0 0 20px rgba(255,136,0,0.3); border-color: rgba(255,136,0,0.6); }}
  .node-marker.gov {{ background: #ff4444; box-shadow: 0 0 8px #ff4444, 0 0 20px rgba(255,68,68,0.3); border-color: rgba(255,68,68,0.6); }}
  .node-marker.emerging {{ background: #ffdd00; box-shadow: 0 0 8px #ffdd00, 0 0 20px rgba(255,221,0,0.3); border-color: rgba(255,221,0,0.6); }}
  @keyframes nodeBreath {{
    0%, 100% {{ transform: scale(1); opacity: 0.9; }}
    50% {{ transform: scale(1.3); opacity: 1; }}
  }}

  .hotspot-marker {{
    width: 18px; height: 18px;
    border-radius: 50%;
    background: rgba(255, 50, 70, 0.4);
    border: 2px solid #cc3344;
    box-shadow: 0 0 10px #cc3344, 0 0 25px rgba(255, 50, 70, 0.25), 0 0 50px rgba(255, 50, 70, 0.08);
    animation: hotspotPulse 1.2s ease-in-out infinite;
  }}
  @keyframes hotspotPulse {{
    0%, 100% {{ transform: scale(1); box-shadow: 0 0 10px #cc3344, 0 0 25px rgba(255,50,70,0.25); }}
    50% {{ transform: scale(1.3); box-shadow: 0 0 15px #cc3344, 0 0 35px rgba(255,50,70,0.35), 0 0 60px rgba(255,50,70,0.1); }}
  }}
  .hotspot-ring {{
    position: absolute;
    top: -8px; left: -8px;
    width: 34px; height: 34px;
    border-radius: 50%;
    border: 1px solid rgba(255, 50, 70, 0.25);
    animation: ringExpand 2s ease-out infinite;
  }}
  @keyframes ringExpand {{
    0% {{ transform: scale(0.5); opacity: 1; }}
    100% {{ transform: scale(2.5); opacity: 0; }}
  }}

  .mining-marker {{
    width: 14px; height: 14px;
    border-radius: 50%;
    background: rgba(0, 255, 136, 0.5);
    border: 2px solid #00ff88;
    box-shadow: 0 0 12px #00ff88, 0 0 30px rgba(0, 255, 136, 0.3);
    animation: miningPulse 2s ease-in-out infinite;
  }}
  @keyframes miningPulse {{
    0%, 100% {{ transform: scale(1); opacity: 0.8; }}
    50% {{ transform: scale(1.3); opacity: 1; }}
  }}

  .eq-marker {{
    width: 5px; height: 5px;
    border-radius: 50%;
    background: rgba(255, 160, 0, 0.5);
    box-shadow: 0 0 4px rgba(255, 160, 0, 0.4);
  }}

  /* Tooltip styling */
  .leaflet-tooltip {{
    background: rgba(5, 5, 16, 0.95) !important;
    border: 1px solid rgba(0, 255, 136, 0.3) !important;
    color: #c0d0e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    padding: 6px 10px !important;
    border-radius: 4px !important;
    box-shadow: 0 0 15px rgba(0, 255, 136, 0.1) !important;
  }}
  .leaflet-tooltip::before {{
    border-right-color: rgba(0, 255, 136, 0.3) !important;
  }}
  .tt-name {{ color: #00ff88; font-weight: 600; font-size: 12px; }}
  .tt-label {{ color: #8899aa; font-size: 10px; }}
  .tt-threat {{ color: #ff2020; font-weight: 600; }}
  .tt-hash {{ color: #00ff88; font-weight: 600; }}

  /* ---- LEGEND ---- */
  .legend-bar {{
    display: flex;
    justify-content: center;
    gap: 16px;
    padding: 8px 20px;
    background: #0a0e17;
    flex-wrap: wrap;
    border-top: 1px solid rgba(0, 255, 136, 0.06);
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 9px;
    letter-spacing: 1px;
    color: #556677;
    text-transform: uppercase;
  }}
  .legend-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .legend-line {{
    width: 20px; height: 2px;
    flex-shrink: 0;
    border-radius: 1px;
  }}

  /* ---- ANIMATED FLOW LINES (SVG overlay) ---- */
  .flow-line {{
    fill: none;
    stroke-width: 1.5;
    stroke-linecap: round;
    opacity: 0.6;
  }}
  .flow-line-glow {{
    fill: none;
    stroke-width: 4;
    stroke-linecap: round;
    opacity: 0.15;
    filter: blur(2px);
  }}

  /* ---- HEBREW INTELLIGENCE BRIEFING PANEL (COLLAPSIBLE) ---- */
  .intel-panel {{
    position: fixed;
    top: 50%;
    right: 0;
    transform: translateY(-50%) translateX(100%);
    width: 300px;
    max-height: 90vh;
    overflow-y: auto;
    background: rgba(8, 12, 22, 0.95);
    border: 1px solid rgba(0, 255, 136, 0.18);
    border-radius: 6px 0 0 6px;
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.06), 0 0 60px rgba(0, 255, 136, 0.03), inset 0 0 30px rgba(0, 0, 0, 0.3);
    z-index: 9999;
    font-family: 'Heebo', 'Assistant', sans-serif;
    direction: rtl;
    text-align: right;
    padding: 0;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }}
  .intel-panel.open {{
    transform: translateY(-50%) translateX(0);
  }}
  /* Toggle Tab */
  .intel-toggle {{
    position: fixed;
    top: 50%;
    right: 0;
    transform: translateY(-50%);
    z-index: 10000;
    writing-mode: vertical-rl;
    background: rgba(8, 12, 22, 0.92);
    border: 1px solid rgba(0, 255, 136, 0.25);
    border-right: none;
    border-radius: 6px 0 0 6px;
    padding: 14px 7px;
    cursor: pointer;
    font-family: 'Heebo', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #00ff88;
    letter-spacing: 2px;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: all 0.3s ease;
    box-shadow: 0 0 12px rgba(0, 255, 136, 0.08);
    user-select: none;
  }}
  .intel-toggle:hover {{
    background: rgba(0, 255, 136, 0.08);
    border-color: rgba(0, 255, 136, 0.5);
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.15);
  }}
  .intel-toggle.shifted {{
    right: 300px;
    transition: right 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }}
  .intel-toggle .toggle-dot {{
    display: inline-block;
    width: 5px; height: 5px;
    background: #00ff88;
    border-radius: 50%;
    margin-bottom: 6px;
    animation: livePulse 1.5s ease-in-out infinite;
  }}
  .intel-panel::-webkit-scrollbar {{
    width: 3px;
  }}
  .intel-panel::-webkit-scrollbar-track {{
    background: transparent;
  }}
  .intel-panel::-webkit-scrollbar-thumb {{
    background: rgba(0, 255, 136, 0.15);
    border-radius: 2px;
  }}
  .intel-panel-header {{
    background: linear-gradient(180deg, rgba(0, 255, 136, 0.08) 0%, transparent 100%);
    border-bottom: 1px solid rgba(0, 255, 136, 0.12);
    padding: 14px 16px 10px 16px;
    position: relative;
  }}
  .intel-panel-header::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00ff88, transparent);
  }}
  .intel-panel-title {{
    font-family: 'Heebo', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #00ff88;
    letter-spacing: 1px;
    margin-bottom: 2px;
  }}
  .intel-panel-subtitle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    color: #445566;
    letter-spacing: 2px;
    direction: ltr;
    text-align: right;
  }}
  .intel-section {{
    padding: 10px 16px;
    border-bottom: 1px solid rgba(0, 255, 136, 0.06);
  }}
  .intel-section:last-child {{
    border-bottom: none;
  }}
  .intel-section-title {{
    font-family: 'Heebo', sans-serif;
    font-size: 10px;
    font-weight: 600;
    color: #556677;
    letter-spacing: 1px;
    margin-bottom: 6px;
    text-transform: uppercase;
  }}
  .intel-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 3px 0;
    font-size: 12px;
    direction: rtl;
  }}
  .intel-row-label {{
    color: #778899;
    font-family: 'Heebo', sans-serif;
    font-weight: 400;
    font-size: 12px;
  }}
  .intel-row-value {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 12px;
    direction: ltr;
  }}
  .intel-status-line {{
    font-family: 'Heebo', sans-serif;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.7;
    color: #a0b0c0;
  }}
  .intel-action-box {{
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 255, 136, 0.12);
    border-radius: 4px;
    padding: 10px 14px;
    margin-top: 4px;
    text-align: center;
  }}
  .intel-action-label {{
    font-family: 'Orbitron', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 4px;
  }}
  .intel-action-desc {{
    font-family: 'Heebo', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: #778899;
    margin-top: 4px;
    direction: rtl;
  }}
  .intel-threat-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    direction: rtl;
  }}
  .intel-threat-indicator {{
    width: 100%;
    height: 4px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }}
  .intel-threat-fill {{
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
  }}
  .intel-threat-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 1px;
  }}
  .intel-footer {{
    padding: 8px 16px;
    border-top: 1px solid rgba(0, 255, 136, 0.06);
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    color: #334455;
    letter-spacing: 1px;
    direction: ltr;
    text-align: center;
  }}

  /* Status bar */
  .status-bar {{
    display: flex;
    justify-content: space-between;
    padding: 4px 20px;
    background: #0a0e17;
    font-size: 9px;
    color: #334455;
    letter-spacing: 1px;
    border-top: 1px solid rgba(0, 255, 136, 0.05);
  }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="header-title">Global Economic Intelligence Map -- Renaissance Protocol</div>
  <div class="header-sub">
    <span>ELITE v20</span> | MEDALLION | <span>LIVE FEED</span> | ZERO EMOTION
  </div>
  <div class="header-time">
    <span class="live-dot"></span>
    <span id="clock">{timestamp}</span>
  </div>
</div>

<!-- METRIC CARDS -->
<div class="metrics-row">
  <div class="metric-card" style="--card-color: {btc_color}; --card-glow: {btc_color};">
    <div class="metric-label">BTC/USD</div>
    <div class="metric-value">${btc_price:,.0f}</div>
    <div class="metric-sub" style="color: {btc_color};">{btc_arrow}{btc_change}%</div>
  </div>
  <div class="metric-card" style="--card-color: {fng_color}; --card-glow: {fng_color};">
    <div class="metric-label">Fear & Greed</div>
    <div class="metric-value">{fng_value}</div>
    <div class="metric-sub">{fng_label}</div>
  </div>
  <div class="metric-card" style="--card-color: #ffd700; --card-glow: #ffd700;">
    <div class="metric-label">Gold XAU</div>
    <div class="metric-value">${gold:,.0f}</div>
    <div class="metric-sub">Spot Price</div>
  </div>
  <div class="metric-card" style="--card-color: #ff6600; --card-glow: #ff6600;">
    <div class="metric-label">Oil WTI</div>
    <div class="metric-value">${oil:,.2f}</div>
    <div class="metric-sub">Crude Futures</div>
  </div>
  <div class="metric-card" style="--card-color: {vix_color}; --card-glow: {vix_color};">
    <div class="metric-label">VIX</div>
    <div class="metric-value">{vix:.1f}</div>
    <div class="metric-sub">{"LOW FEAR" if vix < 20 else ("ELEVATED" if vix < 30 else "HIGH FEAR")}</div>
  </div>
  <div class="metric-card" style="--card-color: #00ccff; --card-glow: #00ccff;">
    <div class="metric-label">DXY</div>
    <div class="metric-value">{dxy:.1f}</div>
    <div class="metric-sub">Dollar Index</div>
  </div>
  <div class="metric-card" style="--card-color: #aa44ff; --card-glow: #aa44ff;">
    <div class="metric-label">S&P 500</div>
    <div class="metric-value">{sp500:,.0f}</div>
    <div class="metric-sub">US Equities</div>
  </div>
  <div class="metric-card" style="--card-color: #ff8800; --card-glow: #ff8800;">
    <div class="metric-label">Seismic</div>
    <div class="metric-value">{eq_count}</div>
    <div class="metric-sub">M2.5+ / 7 Days</div>
  </div>
</div>

<!-- MAP -->
<div id="map"></div>

<!-- HEBREW INTELLIGENCE TOGGLE TAB -->
<div class="intel-toggle" id="intelToggle" onclick="toggleIntelPanel()">
  <span class="toggle-dot"></span>
  {chr(0x05EA)}{chr(0x05D3)}{chr(0x05E8)}{chr(0x05D9)}{chr(0x05DA)}
</div>

<!-- HEBREW INTELLIGENCE BRIEFING PANEL -->
<div class="intel-panel" id="intelPanel">
  <div class="intel-panel-header">
    <div class="intel-panel-title">{chr(0x05DE)}{chr(0x05D4)} {chr(0x05D4)}{chr(0x05DE)}{chr(0x05E4)}{chr(0x05D4)} {chr(0x05D0)}{chr(0x05D5)}{chr(0x05DE)}{chr(0x05E8)}{chr(0x05EA)}</div>
    <div class="intel-panel-subtitle">ELITE v20 // MAP NARRATIVE ANALYSIS</div>
  </div>

  <div class="intel-section">
    <div class="intel-status-line" style="line-height: 1.9; font-size: 12px;">{narrative_html}</div>
  </div>

  <div class="intel-section" style="border-top: 1px solid rgba(0, 255, 136, 0.15); padding-top: 12px;">
    <div class="intel-section-title">{chr(0x05DE)}{chr(0x05E1)}{chr(0x05E7)}{chr(0x05E0)}{chr(0x05D4)}</div>
    <div class="intel-status-line" style="line-height: 1.8; font-size: 13px;">{conclusion_html}</div>
  </div>

  <div class="intel-footer">RENAISSANCE PROTOCOL // ZERO EMOTION // LIVE</div>
</div>

<script>
function toggleIntelPanel() {{
  const panel = document.getElementById('intelPanel');
  const toggle = document.getElementById('intelToggle');
  panel.classList.toggle('open');
  toggle.classList.toggle('shifted');
}}
</script>

<!-- LEGEND -->
<div class="legend-bar">
  <div class="legend-item"><div class="legend-dot" style="background:#00ccff;box-shadow:0 0 6px #00ccff;"></div>Finance</div>
  <div class="legend-item"><div class="legend-dot" style="background:#aa44ff;box-shadow:0 0 6px #aa44ff;"></div>Tech</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ff8800;box-shadow:0 0 6px #ff8800;"></div>Energy</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ffdd00;box-shadow:0 0 6px #ffdd00;"></div>Emerging</div>
  <div class="legend-item"><div class="legend-dot" style="background:#cc3344;box-shadow:0 0 8px #cc3344;"></div>Hotspot</div>
  <div class="legend-item"><div class="legend-dot" style="background:#00ff88;box-shadow:0 0 8px #00ff88;"></div>BTC Mining</div>
  <div class="legend-item"><div class="legend-line" style="background:#cc4444;box-shadow:0 0 4px #cc4444;"></div>Oil</div>
  <div class="legend-item"><div class="legend-line" style="background:#00ccff;box-shadow:0 0 4px #00ccff;"></div>Tech/Chips</div>
  <div class="legend-item"><div class="legend-line" style="background:#ffd700;box-shadow:0 0 4px #ffd700;"></div>Capital</div>
  <div class="legend-item"><div class="legend-line" style="background:#cc8800;box-shadow:0 0 4px #cc8800;"></div>Gold</div>
  <div class="legend-item"><div class="legend-line" style="background:#00ff88;box-shadow:0 0 4px #00ff88;"></div>BTC Hash</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ffa000;box-shadow:0 0 4px #ffa000;width:5px;height:5px;"></div>Seismic</div>
</div>

<!-- STATUS BAR -->
<div class="status-bar">
  <span>RENAISSANCE PROTOCOL // ELITE v20 // ZERO EMOTION</span>
  <span>NODES: 30 | HOTSPOTS: 6 | MINING: 5 | ROUTES: 19 | SEISMIC: {eq_count}</span>
  <span id="statusClock"></span>
</div>

<script>
// ---- DATA ----
const nodes = {nodes_json};
const hotspots = {hotspots_json};
const miningZones = {mining_json};
const connections = {connections_json};
const earthquakes = {earthquakes_json};

// ---- MAP INIT ----
const map = L.map('map', {{
  center: [25, 30],
  zoom: 2.5,
  minZoom: 2,
  maxZoom: 8,
  zoomControl: true,
  attributionControl: false,
  preferCanvas: true,
  worldCopyJump: true,
}});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  subdomains: 'abcd',
  maxZoom: 19,
}}).addTo(map);

// Subtle labels layer on top
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  subdomains: 'abcd',
  maxZoom: 19,
  opacity: 0.35,
}}).addTo(map);

// ---- COLOR MAP ----
const lineColors = {{
  oil: '#cc4444',
  tech: '#00ccff',
  capital: '#ffd700',
  gold: '#cc8800',
  btc: '#00ff88',
}};

// ---- ANIMATED CONNECTION LINES ----
function createAnimatedLine(fromLL, toLL, type, label) {{
  const color = lineColors[type] || '#ffffff';

  // Base glow line
  const glowLine = L.polyline([fromLL, toLL], {{
    color: color,
    weight: 4,
    opacity: 0.08,
    smoothFactor: 1,
    className: 'flow-line-glow',
  }}).addTo(map);

  // Main line
  const mainLine = L.polyline([fromLL, toLL], {{
    color: color,
    weight: 1.2,
    opacity: 0.35,
    smoothFactor: 1,
    dashArray: '8, 12',
    className: 'flow-line',
  }}).addTo(map);

  mainLine.bindTooltip('<span style="color:' + color + ';">' + label + '</span>', {{
    sticky: true,
    className: 'leaflet-tooltip',
  }});

  // Animated particle along the line
  animateParticle(fromLL, toLL, color, type);
}}

function animateParticle(from, to, color, type) {{
  const marker = L.circleMarker(from, {{
    radius: 3,
    color: color,
    fillColor: color,
    fillOpacity: 0.9,
    weight: 0,
    className: 'particle-' + type,
  }}).addTo(map);

  // Add glow effect
  const glowMarker = L.circleMarker(from, {{
    radius: 6,
    color: color,
    fillColor: color,
    fillOpacity: 0.2,
    weight: 0,
  }}).addTo(map);

  let progress = Math.random(); // stagger start
  const speed = 0.002 + Math.random() * 0.001;

  function step() {{
    progress += speed;
    if (progress > 1) progress = 0;

    const lat = from[0] + (to[0] - from[0]) * progress;
    const lng = from[1] + (to[1] - from[1]) * progress;
    const pos = L.latLng(lat, lng);

    marker.setLatLng(pos);
    glowMarker.setLatLng(pos);

    // Pulse opacity
    const pulse = 0.5 + 0.5 * Math.sin(progress * Math.PI * 2);
    marker.setStyle({{ fillOpacity: 0.6 + pulse * 0.4 }});
    glowMarker.setStyle({{ fillOpacity: 0.1 + pulse * 0.15 }});

    requestAnimationFrame(step);
  }}
  requestAnimationFrame(step);
}}

// Draw all connections
connections.forEach(c => {{
  createAnimatedLine(c.from, c.to, c.type, c.label);
}});

// ---- ECONOMIC NODES ----
nodes.forEach(n => {{
  const el = document.createElement('div');
  el.className = 'node-marker ' + (n.type || 'finance');

  const icon = L.divIcon({{
    className: '',
    html: el.outerHTML,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  }});

  const marker = L.marker([n.lat, n.lng], {{ icon: icon }}).addTo(map);
  marker.bindTooltip(
    '<div class="tt-name">' + n.name + '</div><div class="tt-label">' + n.label + '</div>',
    {{ direction: 'top', offset: [0, -8] }}
  );
}});

// ---- HOTSPOTS ----
hotspots.forEach(h => {{
  const html = '<div class="hotspot-marker"><div class="hotspot-ring"></div><div class="hotspot-ring" style="animation-delay:0.6s;"></div></div>';
  const icon = L.divIcon({{
    className: '',
    html: html,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  }});

  const marker = L.marker([h.lat, h.lng], {{ icon: icon }}).addTo(map);
  marker.bindTooltip(
    '<div class="tt-threat">THREAT: ' + h.name + '</div><div class="tt-label">' + h.threat + '</div>',
    {{ direction: 'top', offset: [0, -14] }}
  );
}});

// ---- MINING ZONES ----
miningZones.forEach(m => {{
  const html = '<div class="mining-marker"></div>';
  const icon = L.divIcon({{
    className: '',
    html: html,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  }});

  const marker = L.marker([m.lat, m.lng], {{ icon: icon }}).addTo(map);
  marker.bindTooltip(
    '<div class="tt-hash">BTC MINING: ' + m.name + '</div><div class="tt-label">Hashrate: ' + m.hashrate + ' Global</div>',
    {{ direction: 'top', offset: [0, -10] }}
  );
}});

// ---- EARTHQUAKES ----
earthquakes.forEach(eq => {{
  const r = Math.max(2, eq.mag * 1.2);
  L.circleMarker([eq.lat, eq.lng], {{
    radius: r,
    color: 'rgba(255,160,0,0.4)',
    fillColor: 'rgba(255,160,0,0.25)',
    fillOpacity: 0.25,
    weight: 0.5,
  }}).addTo(map).bindTooltip(
    '<div style="color:#ffa000;">M' + eq.mag + '</div><div class="tt-label">' + eq.place + '</div>',
    {{ direction: 'top' }}
  );
}});

// ---- LIVE CLOCK ----
function updateClock() {{
  const now = new Date();
  const utc = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  const el = document.getElementById('clock');
  if (el) el.textContent = utc;
  const el2 = document.getElementById('statusClock');
  if (el2) el2.textContent = 'SYS TIME: ' + utc;
}}
setInterval(updateClock, 1000);
updateClock();

// ---- GRID OVERLAY (subtle) ----
const gridGroup = L.layerGroup().addTo(map);
for (let lat = -60; lat <= 80; lat += 30) {{
  L.polyline([[lat, -180], [lat, 180]], {{
    color: 'rgba(0, 255, 136, 0.03)',
    weight: 0.5,
    interactive: false,
  }}).addTo(gridGroup);
}}
for (let lng = -180; lng <= 180; lng += 30) {{
  L.polyline([[-90, lng], [90, lng]], {{
    color: 'rgba(0, 255, 136, 0.03)',
    weight: 0.5,
    interactive: false,
  }}).addTo(gridGroup);
}}

</script>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# STREAMLIT ENTRY POINT
# ---------------------------------------------------------------------------

def render_global_map(st):
    """
    Render the Global Economic Intelligence Map in a Streamlit app.

    Usage:
        import streamlit as st
        from global_economic_map import render_global_map
        render_global_map(st)
    """
    import streamlit.components.v1 as components

    # Use Streamlit cache if available
    try:
        @st.cache_data(ttl=300, show_spinner=False)
        def get_data():
            return _collect_all_data()
        data = get_data()
    except Exception:
        data = _collect_all_data()

    html_content = _build_html(data)

    # Inject full-width CSS
    st.markdown(
        """
        <style>
        .stApp { background-color: #0a0e17 !important; }
        [data-testid="stAppViewContainer"] { background-color: #0a0e17 !important; }
        [data-testid="stHeader"] { background-color: #0a0e17 !important; }
        section[data-testid="stSidebar"] { background-color: #0a0a1a !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        iframe { border: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    components.html(html_content, height=780, scrolling=False)


# ---------------------------------------------------------------------------
# STANDALONE MODE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(
        page_title="Global Economic Intelligence Map",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_global_map(st)
