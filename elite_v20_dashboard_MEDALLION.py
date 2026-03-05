"""
ELITE v20 MEDALLION DASHBOARD -- Standalone Edition (AUDITED & FIXED)
=====================================================================
STANDALONE VERSION -- No PWA / Cloud Run dependency.
All data sourced locally via EliteDashboardAdapter + ccxt + on-chain APIs.

Run: streamlit run elite_v20_dashboard_MEDALLION.py

# =========================================================================
# CHANGELOG -- MEDALLION AUDIT FIX (CRO Surgical Patch)
# =========================================================================
#
# [FIX-1] Commander's Brief reads gate_status before initialization
#   ROOT CAUSE: Commander's Brief rendered BEFORE Bayesian computation,
#     reading uninitialized gate_status -> "Gate Blocked" / "Gate Unknown".
#   FIX: Introduced unified_state dict computed at top level ONCE after
#     data load. Gate status, posterior, Kelly all computed BEFORE any
#     module renders. All modules read from unified_state.
#
# [FIX-2] Two modules compute Posterior independently (100% vs 98%)
#   ROOT CAUSE: Bayesian Collapse used confidence*100 (adapter output),
#     Waterfall used its own prior=98% hardcoded. Two different numbers.
#   FIX: Single function compute_unified_posterior() with @st.cache_data.
#     Returns one posterior value used by ALL modules.
#
# [FIX-3] Three different Kelly values (0% / 5% / 40%)
#   ROOT CAUSE: Commander read from risk_guidance (adapter), Collapse
#     computed its own, Waterfall used kelly_fraction from data dict.
#   FIX: compute_unified_kelly() derives Kelly from the single posterior.
#     Capped at 5% max (protocol). Passed to all displays.
#
# [FIX-4] Commander's Brief says "stable conditions" ignoring F&G + Flux
#   ROOT CAUSE: Text generation only checked chaos=0.28 -> "stable".
#   FIX: generate_market_condition_text() considers ALL signals.
#
# [FIX-5] Prior = 98% hardcoded -> Posterior always >= 98%
#   ROOT CAUSE: confidence*100 used as prior, capped at 98%.
#   FIX: Prior is ALWAYS 55.0 (Bayesian neutral). Never from adapter.
#
# [FIX-6] confidence = 1.0 exactly is adapter bug
#   FIX: If confidence >= 1.0, force to 0.5.
#
# [FIX-7] Diffusion/F&G posterior cap
#   FIX: If diffusion < 50 AND fear_greed < 25 AND posterior > 60,
#     cap posterior at 55%.
#
# [FIX-8] Iron Law: violence_score > 3.5 -> Kelly=0, Gate=LOCKED
#   FIX: Regardless of posterior, chaos >= 0.7 -> Kelly=0, gate=LOCKED.
#
# [FIX-9] Wyckoff 2/7 should NOT allow gate open
#   FIX: Minimum 4/7 Wyckoff conditions for gate eligibility.
#
# [FIX-10] All print() statements cp1255 safe (no emoji)
# [FIX-11] Dark theme Bloomberg aesthetic preserved
# [FIX-12] Module integration: global_economic_map, bayesian_waterfall,
#           qc_dashboard all imported per spec.
# =========================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
import streamlit as st

st.set_page_config(
    page_title="ELITE v20 | MEDALLION",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import numpy as np
import sys
import os
import importlib
import csv
import time
import threading
import struct
import base64
import math
import io
import traceback
from datetime import datetime, timezone, timedelta, UTC
from pathlib import Path

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import requests
except ImportError:
    requests = None

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
_DASHBOARDS_DIR = _DASHBOARD_DIR
BASE_DIR = os.path.dirname(_DASHBOARD_DIR)
_MODULES_DIR = os.path.join(BASE_DIR, 'modules')

for _p in [BASE_DIR, _MODULES_DIR, _DASHBOARDS_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ADAPTER_AVAILABLE = False
_adapter = None

try:
    from dashboard_adapter import EliteDashboardAdapter
    _ADAPTER_AVAILABLE = True
except ImportError:
    try:
        from modules.dashboard_adapter import EliteDashboardAdapter
        _ADAPTER_AVAILABLE = True
    except ImportError:
        pass

if _ADAPTER_AVAILABLE:
    @st.cache_resource
    def init_elite():
        return EliteDashboardAdapter()
    try:
        _adapter = init_elite()
    except Exception as _e:
        print(f"[WARN] EliteDashboardAdapter initialization failed: {_e}")
        _ADAPTER_AVAILABLE = False

# ============================================================================
# AUDIT LOG
# ============================================================================
AUDIT_PATH = Path(BASE_DIR) / "elite_audit_log.csv"
AUDIT_FIELDS = [
    "timestamp_utc", "symbol", "price", "elite_score", "confidence",
    "final_action", "diffusion_score", "fear_greed", "manifold_score",
    "onchain_signal", "chaos_class", "gates_allow_trade",
]

def append_audit_row(price, elite_results, symbol="BTCUSDT"):
    try:
        onchain = elite_results.get("onchain", {})
        if not isinstance(onchain, dict): onchain = {}
        fg_data = onchain.get("fear_greed", {})
        if not isinstance(fg_data, dict): fg_data = {}
        fg_value = fg_data.get("value", 50)
        row = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "symbol": symbol, "price": price,
            "elite_score": float(elite_results.get("elite_score_adjusted") or elite_results.get("elite_score") or 0.0),
            "confidence": float(elite_results.get("confidence") or 0.0),
            "final_action": elite_results.get("final_action", "NA"),
            "diffusion_score": float(onchain.get("diffusion_score") or 0.0),
            "fear_greed": int(fg_value if fg_value is not None else 50),
            "manifold_score": float(elite_results.get("manifold", {}).get("score") or 0.0),
            "onchain_signal": onchain.get("signal", "NA"),
            "chaos_class": elite_results.get("chaos", {}).get("classification", "NA"),
            "gates_allow_trade": bool(elite_results.get("gates", {}).get("allow_trade", True)),
        }
        file_exists = AUDIT_PATH.exists()
        with AUDIT_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
            if not file_exists: writer.writeheader()
            writer.writerow(row)
    except Exception:
        pass

# ============================================================================
# MODULE IMPORTS
# ============================================================================
try:
    from global_economic_map import render_global_map
    GLOBAL_MAP_AVAILABLE = True
    print("[OK] Global Economic Map loaded (Leaflet + components.html)")
except ImportError:
    GLOBAL_MAP_AVAILABLE = False
    print("[WARN] global_economic_map.py not found -- map tab disabled")

try:
    from bayesian_waterfall import render_bayesian_waterfall
    WATERFALL_AVAILABLE = True
    print("[OK] Bayesian Waterfall + Commander Brief loaded")
except ImportError:
    WATERFALL_AVAILABLE = False
    print("[WARN] bayesian_waterfall.py not found -- waterfall tab disabled")

try:
    from qc_dashboard import render_qc_dashboard
    QC_AVAILABLE = True
    print("[OK] Quality Control Dashboard loaded")
except ImportError:
    QC_AVAILABLE = False
    print("[WARN] qc_dashboard.py not found -- QC tab disabled")

try:
    from module_oracle_node import render_oracle_node
    ORACLE_AVAILABLE = True
    print("[OK] Oracle Node (HUMINT Scanner) loaded")
except ImportError:
    ORACLE_AVAILABLE = False
    print("[WARN] module_oracle_node.py not found -- Oracle tab disabled")

ELITE_AVAILABLE = _ADAPTER_AVAILABLE

try:
    from modules.monolith_backtest import MonolithBacktestEngine
    BACKTEST_AVAILABLE = True
except ImportError:
    try:
        from monolith_backtest import MonolithBacktestEngine
        BACKTEST_AVAILABLE = True
    except ImportError:
        BACKTEST_AVAILABLE = False

try:
    import dudu_overlay
    importlib.reload(dudu_overlay)
    from dudu_overlay import (render_projection_tab, compute_divergence_eigenvalue,
                              apply_spectral_boost, build_divergence_series,
                              build_vol_cone)
    DUDU_AVAILABLE = True
    SPECTRAL_AVAILABLE = True
    print(f"[OK] DUDU + Spectral Engine loaded from: {dudu_overlay.__file__}")
except ImportError as e:
    DUDU_AVAILABLE = False
    SPECTRAL_AVAILABLE = False
    print(f"[ERR] DUDU/Spectral Error: {e}")

try:
    from modules.divergence_chart import render_divergence_chart
    DIVERGENCE_AVAILABLE = True
except ImportError:
    DIVERGENCE_AVAILABLE = False

try:
    from modules.topology_viz import render_topology_manifold
    TOPO_VIZ_AVAILABLE = True
except ImportError:
    TOPO_VIZ_AVAILABLE = False

try:
    from modules.node_topology import render_node_topology, render_node_stats_hud, render_quantum_ledger_anatomy
    NODE_TOPO_AVAILABLE = True
except ImportError:
    NODE_TOPO_AVAILABLE = False

try:
    import gemini_chat_module_ELITE_v20
    importlib.reload(gemini_chat_module_ELITE_v20)
    from gemini_chat_module_ELITE_v20 import render_gemini_sidebar_elite, prepare_elite_dashboard_data
    GEMINI_AVAILABLE = True
    print("[OK] Gemini AI loaded (Google Ultra) - FORCE RELOADED")
except ImportError:
    GEMINI_AVAILABLE = False
    print("[WARN] Gemini AI not available")

CLAUDE_AVAILABLE = False

try:
    from memory_logger import get_logger
    MEMORY_AVAILABLE = True
    print("[OK] Memory System loaded")
except ImportError:
    MEMORY_AVAILABLE = False
    print("[WARN] Memory System not available")

try:
    from mobile_notifier import EliteMobileNotifier
    mobile_notifier = EliteMobileNotifier()
    MOBILE_AVAILABLE = mobile_notifier.available
    if MOBILE_AVAILABLE: print("[OK] Mobile Fortress ready (Telegram)")
    else: print("[WARN] Mobile Fortress: Add TELEGRAM_BOT_TOKEN to secrets.toml")
except ImportError:
    MOBILE_AVAILABLE = False
    mobile_notifier = None
    print("[WARN] Mobile Fortress not available")

try:
    from dca_strategy import DCAStrategy, DCAConfig
    DCA_AVAILABLE = True
except ImportError:
    DCA_AVAILABLE = False

try:
    from modules.backtest_sniper_v2 import fetch_btc_daily
    BACKTEST_DATA_AVAILABLE = True
except ImportError:
    try:
        from backtest_sniper_v2 import fetch_btc_daily
        BACKTEST_DATA_AVAILABLE = True
    except ImportError:
        BACKTEST_DATA_AVAILABLE = False
    print("[WARN] dca_strategy.py not found -- DCA features disabled")

try:
    from misdirection_engine import MisdirectionEngine, render_misdirection_panel
    MISDIRECTION_AVAILABLE = True
    print("[OK] Misdirection Engine loaded")
except ImportError:
    MISDIRECTION_AVAILABLE = False
    print("[WARN] misdirection_engine.py not found")

try:
    from nature_events_engine import NatureEventsEngine
    NATURE_AVAILABLE = True
    print("[OK] Nature Events Engine loaded")
except ImportError:
    NATURE_AVAILABLE = False
    print("[WARN] nature_events_engine.py not found")

try:
    from nlp_sentiment import GEOPOL_KEYWORDS
    GEOPOL_AVAILABLE = True
except ImportError:
    GEOPOL_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if NATURE_AVAILABLE:
    @st.cache_resource
    def init_nature_engine():
        return NatureEventsEngine()
    _nature_engine = init_nature_engine()
else:
    _nature_engine = None

try:
    from supabase import create_client
    MEMORY_BACKEND = "supabase"
except ImportError:
    import sqlite3
    MEMORY_BACKEND = "sqlite"
    def _init_local_memory():
        db_path = os.path.join(BASE_DIR, "elite_memory.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, symbol TEXT,
            price REAL, elite_score REAL, action TEXT, regime TEXT, manifold_score REAL)""")
        conn.commit()
        return conn
    try:
        _memory_conn = _init_local_memory()
        print(f"[OK] Memory Logger: SQLite fallback active ({MEMORY_BACKEND})")
    except Exception as _e:
        _memory_conn = None
        print(f"[WARN] SQLite fallback failed: {_e}")


# ============================================================================
# SYSTEM CONSTANTS
# ============================================================================
BAYESIAN_THRESHOLD = 91.7
BAYESIAN_NEUTRAL_PRIOR = 55.0   # [FIX-5] The one true prior
KELLY_MAX_PCT = 5.0             # [FIX-3] Protocol max Kelly
WYCKOFF_MIN_CONDITIONS = 4      # [FIX-9] Minimum Wyckoff conditions for gate
CURRENT_PHASE = "Whipsaw Defense (Gene Silencing Active)"


# ============================================================================
# [FIX-1/2/3/5/6/7/8/9] UNIFIED COMPUTATION ENGINE
# Single Source of Truth for Posterior, Kelly, Gate Status, Wyckoff
# ============================================================================

def compute_wyckoff_conditions(fear_greed, whale_score, current_price, p10_floor,
                               netflow, nlp_sentiment, regime, diffusion_score):
    """[FIX-9] Compute Wyckoff accumulation conditions (7 checks)."""
    checks = {
        "fear_greed_lt_25": fear_greed < 25,
        "whale_score_gt_55": whale_score > 55,
        "price_below_p10": current_price < p10_floor if p10_floor > 0 else False,
        "netflow_negative": netflow < 0,
        "nlp_negative": nlp_sentiment < -0.05,
        "regime_bearish": regime in ("BLOOD_IN_STREETS", "Blood_in_streets"),
        "diffusion_gt_70": diffusion_score > 70,
    }
    met_count = sum(checks.values())
    return {"checks": checks, "met": met_count, "total": 7,
            "sufficient": met_count >= WYCKOFF_MIN_CONDITIONS}


@st.cache_data(ttl=60)
def compute_unified_posterior(_prior, diffusion_score, fear_greed, book_imbalance,
                              chaos_norm, nlp_sentiment, misdirection_score, regime):
    """[FIX-2/5] THE single Bayesian posterior. Prior is ALWAYS 55.0."""
    prior = _prior
    diff_delta = max(0.0, (diffusion_score - 50.0) / 50.0 * 15.0)
    if fear_greed <= 25:
        fg_delta = (25 - fear_greed) / 25.0 * 10.0
    elif fear_greed >= 75:
        fg_delta = -((fear_greed - 75) / 25.0 * 10.0)
    else:
        fg_delta = 0.0
    book_delta = book_imbalance * 8.0
    chaos_delta = -abs(chaos_norm) * 20.0
    nlp_delta = nlp_sentiment * 10.0 if nlp_sentiment < 0 else nlp_sentiment * 5.0
    regime_delta = 0.0
    if regime in ("BLOOD_IN_STREETS", "Blood_in_streets"):
        regime_delta = 6.0
    elif regime in ("DISTRIBUTION_TOP", "Distribution_top"):
        regime_delta = -4.0
    mis_delta = max(0.0, misdirection_score) * 8.0
    posterior = prior + diff_delta + fg_delta + book_delta + chaos_delta + nlp_delta + regime_delta + mis_delta
    return round(max(0.0, min(100.0, posterior)), 2)


def apply_posterior_safety_caps(posterior, diffusion_score, fear_greed):
    """[FIX-7] If diffusion < 50 AND fear_greed < 25 AND posterior > 60, cap at 55%."""
    if diffusion_score < 50 and fear_greed < 25 and posterior > 60.0:
        return 55.0
    return posterior


def compute_unified_kelly(posterior, violence_score):
    """[FIX-3/8] THE single Kelly computation. Iron Law enforced."""
    if violence_score > 3.5:
        return 0.0
    if posterior < BAYESIAN_THRESHOLD:
        return 0.0
    p_win = posterior / 100.0
    kelly_raw = p_win - (1.0 - p_win)
    kelly_pct = max(0.0, kelly_raw * 100.0)
    return min(kelly_pct, KELLY_MAX_PCT)


def compute_unified_gate_status(posterior, violence_score, wyckoff_result):
    """[FIX-1/8/9] THE single gate status computation."""
    if violence_score > 3.5:
        return {"gate_open": False, "status": "LOCKED",
                "reason": f"Iron Law: violence={violence_score:.2f} > 3.5 (Gene Silencing VETO)",
                "color": "var(--danger)"}
    if not wyckoff_result.get("sufficient", False):
        met = wyckoff_result.get("met", 0)
        total = wyckoff_result.get("total", 7)
        return {"gate_open": False, "status": "LOCKED",
                "reason": f"Wyckoff {met}/{total} < {WYCKOFF_MIN_CONDITIONS}/7 minimum",
                "color": "var(--danger)"}
    if posterior >= BAYESIAN_THRESHOLD:
        return {"gate_open": True, "status": "OPEN",
                "reason": f"P(win)={posterior:.1f}% >= {BAYESIAN_THRESHOLD}%",
                "color": "var(--success)"}
    gap = BAYESIAN_THRESHOLD - posterior
    return {"gate_open": False, "status": "LOCKED",
            "reason": f"P(win)={posterior:.1f}% < {BAYESIAN_THRESHOLD}% (gap: {gap:.1f}pp)",
            "color": "var(--danger)"}


def generate_market_condition_text(chaos, fear_greed, regime, diffusion_score, violence_score):
    """[FIX-4] Market condition considering ALL signals, not just chaos."""
    signals_bad = 0
    signals_good = 0
    details = []
    if chaos < 0.3:
        signals_good += 1; details.append(f"Chaos low ({chaos:.2f})")
    elif chaos < 0.6:
        details.append(f"Chaos moderate ({chaos:.2f})")
    else:
        signals_bad += 2; details.append(f"Chaos HIGH ({chaos:.2f})")
    if fear_greed < 20:
        signals_bad += 2; details.append(f"Extreme Fear ({fear_greed}/100)")
    elif fear_greed < 35:
        signals_bad += 1; details.append(f"Fear ({fear_greed}/100)")
    elif fear_greed > 75:
        signals_bad += 1; details.append(f"Extreme Greed ({fear_greed}/100)")
    else:
        signals_good += 1; details.append(f"Sentiment neutral ({fear_greed}/100)")
    if regime in ("BLOOD_IN_STREETS", "Blood_in_streets"):
        signals_bad += 1; details.append("Regime: BLOOD_IN_STREETS")
    elif "TRANSITION" in str(regime).upper() or "FLUX" in str(regime).upper():
        signals_bad += 1; details.append("Regime: TRANSITION/FLUX")
    elif regime in ("DISTRIBUTION_TOP", "Distribution_top"):
        signals_bad += 1; details.append("Regime: DISTRIBUTION_TOP")
    else:
        signals_good += 1; details.append(f"Regime: {regime}")
    if violence_score > 3.5:
        signals_bad += 2; details.append(f"Violence EXTREME ({violence_score:.1f}/5.0)")
    elif violence_score > 2.0:
        signals_bad += 1; details.append(f"Violence elevated ({violence_score:.1f}/5.0)")
    if diffusion_score < 30:
        signals_bad += 1; details.append(f"Whales inactive (diff={diffusion_score:.0f})")
    elif diffusion_score > 70:
        signals_good += 1; details.append(f"Whales accumulating (diff={diffusion_score:.0f})")
    if signals_bad >= 3:
        condition = "UNSTABLE -- Multiple risk signals active"
    elif signals_bad >= 2:
        condition = "ELEVATED RISK -- Caution required"
    elif signals_good >= 3 and signals_bad == 0:
        condition = "STABLE -- Favorable conditions"
    else:
        condition = "MIXED -- Selective engagement only"
    return f"{condition}. [{'; '.join(details)}]"



# ============================================================================
# DESIGN SYSTEM -- Bloomberg Terminal Grade
# ============================================================================

def load_css():
    """ELITE v20 INSTITUTIONAL DESIGN - Bloomberg Terminal Grade CSS."""
    institutional_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    :root {
        --bg-primary: #0a0e17; --bg-secondary: #0d1117;
        --bg-card: rgba(13, 17, 23, 0.85); --bg-card-hover: rgba(22, 27, 34, 0.95);
        --border-subtle: rgba(48, 54, 61, 0.6); --border-glow: rgba(88, 166, 255, 0.15);
        --text-primary: #e6edf3; --text-secondary: #8b949e; --text-muted: #484f58;
        --accent-blue: #58a6ff; --accent-cyan: #06e8f9;
        --success: #10B981; --danger: #EF4444; --warning: #F59E0B; --purple: #a78bfa;
        --glow-green: rgba(16, 185, 129, 0.12); --glow-red: rgba(239, 68, 68, 0.12);
        --glow-blue: rgba(88, 166, 255, 0.10);
        --font-mono: 'JetBrains Mono', 'Space Mono', 'Consolas', monospace;
        --font-sans: 'Inter', -apple-system, sans-serif;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    .main .block-container, .stMarkdown, .stText, .stCaption, .stAlert, .stException,
    div[data-testid="stExpander"], div[data-testid="stExpanderDetails"],
    div[data-testid="stVerticalBlock"], div[data-testid="stHorizontalBlock"],
    .stSelectbox > div, .stMultiSelect > div, .stNumberInput > div, .stSlider > div,
    .stCheckbox > label, .stRadio > div, .stTextInput > div, .stTextArea > div,
    .stDateInput > div, .stTimeInput > div, .stColorPicker > div, .stFileUploader > div,
    div[data-baseweb="select"] > div, div[data-baseweb="popover"] > div,
    div[data-baseweb="menu"], div[data-baseweb="input"], div[data-baseweb="textarea"] {
        background-color: var(--bg-primary) !important; color: var(--text-primary) !important;
    }
    .stApp {
        background: var(--bg-primary) !important;
        background-image: radial-gradient(ellipse at 20% 50%, rgba(88,166,255,0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(167,139,250,0.02) 0%, transparent 50%) !important;
        color: var(--text-primary) !important; font-family: var(--font-sans) !important;
    }
    #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
        visibility: hidden !important; height: 0 !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #0a0e17 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stCheckbox label, section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: var(--bg-secondary) !important; border-color: var(--border-subtle) !important;
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] hr { border-color: var(--border-subtle) !important; opacity: 0.4; }
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, rgba(88,166,255,0.1), rgba(167,139,250,0.1)) !important;
        border: 1px solid var(--border-glow) !important; color: var(--accent-blue) !important;
        font-family: var(--font-mono) !important; font-size: 0.8rem !important;
        letter-spacing: 0.5px; transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, rgba(88,166,255,0.2), rgba(167,139,250,0.2)) !important;
        border-color: var(--accent-blue) !important; box-shadow: 0 0 15px rgba(88,166,255,0.15);
    }
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-secondary) !important; border-radius: 0 !important;
        border-bottom: 1px solid var(--border-subtle) !important; gap: 0 !important; padding: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important; color: var(--text-secondary) !important;
        font-family: var(--font-mono) !important; font-size: 0.72rem !important;
        letter-spacing: 0.5px !important; padding: 10px 16px !important;
        border-bottom: 2px solid transparent !important; border-radius: 0 !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--text-primary) !important; background: rgba(88,166,255,0.05) !important; }
    .stTabs [aria-selected="true"] { color: var(--accent-blue) !important; border-bottom: 2px solid var(--accent-blue) !important; background: rgba(88,166,255,0.08) !important; }
    .stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 16px !important; }
    .glass-card {
        background: var(--bg-card) !important; backdrop-filter: blur(16px) !important;
        border: 1px solid var(--border-subtle) !important; border-radius: 6px !important;
        padding: 24px; margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.02);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover { border-color: var(--border-glow) !important; box-shadow: 0 0 20px var(--glow-blue), 0 1px 3px rgba(0,0,0,0.3); }
    .metric-card-glow {
        background: var(--bg-card) !important; border: 1px solid var(--border-subtle);
        border-radius: 6px; padding: 16px 20px; position: relative; overflow: hidden;
    }
    .metric-card-glow::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, var(--card-accent, var(--accent-blue)), transparent); opacity: 0.6; }
    h1, h2, h3, .stSubheader { font-family: var(--font-sans) !important; font-weight: 600 !important; color: var(--text-primary) !important; }
    .inst-header { border-bottom: 1px solid var(--border-subtle); padding-bottom: 20px; margin-bottom: 30px; }
    .inst-title { font-size: 1.5rem !important; color: var(--accent-blue) !important; font-weight: 700 !important; font-family: var(--font-mono) !important; letter-spacing: 1px; margin: 0 !important; }
    .metric-value { font-size: 1.8rem !important; font-weight: 700 !important; font-family: var(--font-mono) !important; color: var(--text-primary) !important; white-space: nowrap !important; line-height: 1.2; }
    .metric-label { font-size: 0.65rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; color: var(--text-muted) !important; font-family: var(--font-mono) !important; margin-bottom: 4px; }
    hr, .stMarkdown hr { border: none !important; height: 1px !important; background: linear-gradient(90deg, transparent, var(--border-subtle), rgba(88,166,255,0.15), var(--border-subtle), transparent) !important; margin: 20px 0 !important; }
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 0; }
    .zone-card { padding: 16px 20px; border-radius: 6px; margin: 10px 0; border-left: 3px solid var(--border-subtle); background: rgba(255,255,255,0.01); }
    .zone-noise { border-left-color: var(--text-muted); }
    .zone-ambush { border-left-color: var(--danger); background: var(--glow-red); }
    .zone-assault { border-left-color: var(--success); background: var(--glow-green); }
    .status-pill { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 6px 16px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.8rem; font-weight: 600; letter-spacing: 0.5px; }
    .status-execute { background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); color: var(--success); }
    .status-silence { background: rgba(139,148,158,0.08); border: 1px solid var(--border-subtle); color: var(--text-secondary); }
    .action-badge { display: inline-flex; align-items: center; gap: 8px; padding: 10px 24px; border-radius: 6px; font-family: var(--font-mono); font-weight: 700; font-size: 1.1rem; letter-spacing: 1px; }
    .action-badge-buy { background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05)); border: 1px solid rgba(16,185,129,0.4); color: var(--success); box-shadow: 0 0 20px rgba(16,185,129,0.1); }
    .action-badge-hold { background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04)); border: 1px solid rgba(245,158,11,0.3); color: var(--warning); box-shadow: 0 0 15px rgba(245,158,11,0.08); }
    .action-badge-sell { background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05)); border: 1px solid rgba(239,68,68,0.4); color: var(--danger); box-shadow: 0 0 20px rgba(239,68,68,0.1); }
    @keyframes sentinel-breathe { 0%, 100% { opacity: 1; box-shadow: 0 0 20px rgba(16,185,129,0.3); } 50% { opacity: 0.85; box-shadow: 0 0 40px rgba(16,185,129,0.6), 0 0 80px rgba(16,185,129,0.2); } }
    .sentinel-alert-banner { position: relative; background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(16,185,129,0.02)); border: 2px solid rgba(16,185,129,0.5); border-radius: 8px; padding: 18px 28px; margin: 12px 0; animation: sentinel-breathe 3s ease-in-out infinite; }
    .sentinel-alert-banner .sentinel-title { font-family: var(--font-mono); font-size: 1.3rem; font-weight: 800; letter-spacing: 2px; color: var(--success); text-transform: uppercase; }
    .sentinel-alert-banner .sentinel-subtitle { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; }
    .sentinel-alert-banner .sentinel-metric { font-family: var(--font-mono); font-size: 2.2rem; font-weight: 900; color: var(--accent-cyan); }
    .signal-bar-track { width: 100%; height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden; border: 1px solid var(--border-subtle); }
    .signal-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
    .stDataFrame, .stTable { background: var(--bg-card) !important; }
    [data-testid="stDataFrame"] > div { background: var(--bg-card) !important; }
    .stExpander { background: var(--bg-card) !important; border: 1px solid var(--border-subtle) !important; border-radius: 6px !important; }
    .stMetric { background: var(--bg-card) !important; }
    [data-testid="stMetricValue"] { color: var(--text-primary) !important; font-family: var(--font-mono) !important; }
    [data-testid="stMetricLabel"] { color: var(--text-secondary) !important; }
    .stSuccess, .stInfo, .stWarning, .stError { background: var(--bg-card) !important; border-radius: 6px !important; }
    .js-plotly-plot .plotly .main-svg { background: transparent !important; }
    .status-good { color: var(--success); }
    .status-danger { color: var(--danger); }
    .status-caution { color: var(--warning); }
    </style>
    """
    st.markdown(institutional_css, unsafe_allow_html=True)

load_css()


# ============================================================================
# ELITE SYSTEM INIT
# ============================================================================

@st.cache_resource
def init_elite_system():
    if not ELITE_AVAILABLE: return None
    cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
    glassnode_key = os.getenv('GLASSNODE_API_KEY')
    return EliteDashboardAdapter(cryptoquant_api_key=cryptoquant_key, glassnode_api_key=glassnode_key)


@st.cache_resource
def start_sentinel_daemon():
    for t in threading.enumerate():
        if t.name == "SentinelWorker":
            print("[OK] Sentinel already active")
            return

    def sentinel_loop():
        print("[OK] Sentinel Active: Monitoring market every 15m...")
        last_action = None
        try:
            notifier = EliteMobileNotifier()
            if not notifier.available:
                print("[WARN] Sentinel disabled: No Telegram config")
                return

            cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
            glassnode_key = os.getenv('GLASSNODE_API_KEY')
            adapter = EliteDashboardAdapter(cryptoquant_api_key=cryptoquant_key, glassnode_api_key=glassnode_key)

            while True:
                try:
                    exchange = None
                    if CCXT_AVAILABLE:
                        for ex_name in ['bybit', 'kraken', 'okx', 'binance']:
                            try:
                                exchange = getattr(ccxt, ex_name)()
                                ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
                                break
                            except Exception:
                                continue

                    if exchange is None:
                        print("[WARN] Sentinel: All exchanges failed or ccxt not available")
                        time.sleep(900)
                        continue

                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    current_price = df['close'].iloc[-1]
                    results = adapter.analyze_elite(df, exposure_pct=15.0)
                    current_action = results.get('final_action', 'HOLD')
                    confidence = results.get('confidence', 0)
                    manifold_score = results.get('elite_score', 0)

                    if current_action != last_action:
                        notifier.send_smart_alert({
                            'action': current_action, 'confidence': confidence,
                            'price': current_price, 'dna': manifold_score,
                            'div_label': "NEUTRAL", 'div_score': 50,
                            'sentiment': 50, 'strategy_hint': "Sentinel Auto"
                        })
                        last_action = current_action
                except Exception as e:
                    print(f"[WARN] Sentinel cycle error: {e}")
                time.sleep(900)
        except Exception as e:
            print(f"[ERR] Sentinel init failed: {e}")

    t = threading.Thread(target=sentinel_loop, name="SentinelWorker", daemon=True)
    t.start()


# ============================================================================
# DATA FETCHING
# ============================================================================

@st.cache_data(ttl=120)
def fetch_crypto_data(symbol="BTCUSDT", interval="1h"):
    if not CCXT_AVAILABLE:
        st.error("ccxt not installed!")
        return pd.DataFrame()
    pair = symbol.replace("USDT", "/USDT")
    for ex_name in ['bybit', 'kraken', 'okx', 'binance']:
        try:
            exchange = getattr(ccxt, ex_name)()
            ohlcv = exchange.fetch_ohlcv(pair, interval, limit=200)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            print(f"[OK] Data from {ex_name}")
            return df
        except Exception as e:
            print(f"[WARN] {ex_name} failed: {e}")
            continue
    st.error("All exchanges failed! Check your internet connection.")
    return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_fear_greed():
    if not requests:
        return 50
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url, timeout=10)
        data = r.json()
        return int(data['data'][0]['value'])
    except Exception:
        return 50


@st.cache_data(ttl=60)
def fetch_btc_spot_price():
    """Robust BTC spot price fetcher with multiple failovers."""
    # Attempt CCXT first for high-frequency trading accuracy
    if CCXT_AVAILABLE:
        for ex_name in ['bybit', 'binance', 'kraken', 'okx']:
            try:
                exchange = getattr(ccxt, ex_name)()
                ticker = exchange.fetch_ticker('BTC/USDT')
                return {
                    "price": round(ticker['last'], 2),
                    "change_24h": round(ticker.get('percentage', 0) or 0, 2),
                    "source": ex_name.upper()
                }
            except Exception:
                continue

    # Failover to CoinGecko
    if requests:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=5)
            r.raise_for_status()
            d = r.json()["bitcoin"]
            return {
                "price": round(d.get("usd", 0), 2),
                "change_24h": round(d.get("usd_24h_change", 0), 2),
                "source": "COINGECKO"
            }
        except Exception:
            pass

    return {"price": 0, "change_24h": 0, "source": "N/A"}


def calculate_heikin_ashi(df):
    ha = df.copy()
    ha['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    for i in range(1, len(ha)):
        ha.iloc[i, ha.columns.get_loc('open')] = (ha.iloc[i-1, ha.columns.get_loc('open')] + ha.iloc[i-1, ha.columns.get_loc('close')]) / 2
    ha['high'] = ha[['open', 'close', 'high']].max(axis=1)
    ha['low'] = ha[['open', 'close', 'low']].min(axis=1)
    return ha


def get_next_macro_event():
    now = datetime.now(timezone.utc)
    MACRO_CALENDAR = [
        (1, 13, 30, "CPI"), (2, 13, 30, "PPI"), (3, 13, 30, "GDP"),
        (3, 14, 0, "Initial Claims"), (4, 13, 30, "NFP / PCE"), (2, 14, 0, "FOMC Minutes"),
    ]
    best_name = "--"
    best_delta = timedelta(days=8)
    for wd, h, m, name in MACRO_CALENDAR:
        days_ahead = (wd - now.weekday()) % 7
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=days_ahead)
        if candidate < now: candidate += timedelta(weeks=1)
        delta = candidate - now
        if delta < best_delta:
            best_delta = delta
            best_name = name
    total_h = int(best_delta.total_seconds() // 3600)
    total_m = int((best_delta.total_seconds() % 3600) // 60)
    if total_h >= 48: time_str = f"{best_delta.days}d"
    elif total_h >= 1: time_str = f"{total_h}h {total_m}m"
    else: time_str = f"IMMINENT {total_m}m"
    return best_name, time_str


def _render_signal_strength_html(confidence, threshold=0.917):
    pct = min(confidence * 100, 100)
    if pct >= threshold * 100: bar_color, label = "var(--success)", "STRONG"
    elif pct >= 70: bar_color, label = "var(--warning)", "MODERATE"
    elif pct >= 50: bar_color, label = "var(--accent-cyan)", "WEAK"
    else: bar_color, label = "var(--danger)", "INSUFFICIENT"
    marker_left = threshold * 100
    return f"""
    <div style="margin: 8px 0;">
        <div style="display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:0.65rem; color:var(--text-muted); margin-bottom:4px;">
            <span>SIGNAL STRENGTH</span>
            <span style="color:{bar_color}; font-weight:600;">{pct:.1f}% -- {label}</span>
        </div>
        <div class="signal-bar-track" style="position:relative;">
            <div class="signal-bar-fill" style="width:{pct}%; background: linear-gradient(90deg, {bar_color}88, {bar_color});"></div>
            <div style="position:absolute; top:-2px; left:{marker_left}%; width:2px; height:12px; background:var(--text-secondary); opacity:0.6;" title="Bayesian Gate {threshold*100:.1f}%"></div>
        </div>
        <div style="font-family:var(--font-mono); font-size:0.55rem; color:var(--text-muted); margin-top:2px; text-align:right;">
            Gate: {threshold*100:.1f}% | Distance: {max(0, threshold*100 - pct):.1f}pp
        </div>
    </div>
    """


@st.cache_data
def _generate_sentinel_sonar():
    sr = 8000
    samples = []
    for i in range(4000):
        t = i / sr; freq = 800 + (400 * t / 0.5); envelope = math.exp(-3.0 * t)
        samples.append(int(max(-128, min(127, envelope * math.sin(2 * math.pi * freq * t) * 127)) + 128))
    samples.extend([128] * 1200)
    for i in range(2400):
        t = i / sr; freq = 1000 + (200 * t / 0.3); envelope = math.exp(-4.0 * t)
        samples.append(int(max(-128, min(127, envelope * math.sin(2 * math.pi * freq * t) * 127)) + 128))
    buf = io.BytesIO()
    n = len(samples)
    buf.write(b'RIFF'); buf.write(struct.pack('<I', 36 + n)); buf.write(b'WAVEfmt ')
    buf.write(struct.pack('<IHHIIHH', 16, 1, 1, sr, sr, 1, 8))
    buf.write(b'data'); buf.write(struct.pack('<I', n)); buf.write(bytes(samples))
    return base64.b64encode(buf.getvalue()).decode()



# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_sidebar():
    """Render institutional sidebar controls."""
    with st.sidebar:
        st.markdown("""
        <div style="font-family:var(--font-mono); font-size:0.7rem; letter-spacing:2px;
                    color:var(--accent-blue); margin-bottom:12px; padding-bottom:8px;
                    border-bottom:1px solid var(--border-subtle);">
            SYSTEM CONTROL
        </div>
        """, unsafe_allow_html=True)

        symbol = st.selectbox("Asset", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
        interval = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
        st.markdown("---")

        st.markdown("""
        <div style="font-family:var(--font-mono); font-size:0.65rem; letter-spacing:1.5px;
                    color:var(--text-secondary); margin-bottom:6px;">
            ELITE PROTOCOL
        </div>
        """, unsafe_allow_html=True)
        enable_elite = st.checkbox("Activate Elite Engine", value=True)
        use_heikin_ashi = st.checkbox("Heikin Ashi (noise filter)", value=False,
                                      help="Replaces raw candles with HA candles to filter whipsaw noise")

        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        _sidebar_update_ts = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        st.markdown(f"""
        <div style="font-family:var(--font-mono); font-size:0.6rem; color:var(--text-muted);
                    padding:6px 0; border-top:1px solid var(--border-subtle); margin-top:4px;">
            LAST UPDATED<br/>
            <span style="color:var(--accent-cyan);">{_sidebar_update_ts}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-family:var(--font-mono); font-size:0.65rem; letter-spacing:1.5px;
                    color:var(--text-secondary); margin-bottom:6px;">
            DEFENSE PROTOCOL
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Pre-Flight Checklist"):
            st.markdown(f"""
            **Standalone Checks:**
            - [{'x' if ELITE_AVAILABLE else ' '}] Elite Adapter initialized
            - [{'x' if CCXT_AVAILABLE else ' '}] CCXT Data layer ready
            - [{'x' if PLOTLY_AVAILABLE else ' '}] Visualization engine active
            - [{'x' if MOBILE_AVAILABLE else ' '}] Telegram Fortress status
            """)

        st.markdown("---")
        st.markdown("""
        <div style="font-family:var(--font-mono); font-size:0.65rem; letter-spacing:1.5px;
                    color:var(--text-secondary); margin-bottom:6px;">
            HFT & MACRO RADAR
        </div>
        """, unsafe_allow_html=True)

        try:
            _next_event, _time_left = get_next_macro_event()
            _evt_color = "#EF4444" if "IMMINENT" in _time_left else "#F59E0B"
            st.markdown(f"""
            <div style='background:var(--bg-secondary);border-left:3px solid {_evt_color};
                        padding:8px 12px;border-radius:4px;margin-bottom:8px;'>
                <div style='font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);
                            letter-spacing:1px;'>NEXT MACRO EVENT</div>
                <div style='font-size:1.0rem;font-weight:700;color:{_evt_color};'>{_time_left}</div>
                <div style='font-size:0.75rem;color:var(--text-secondary);'>{_next_event}</div>
            </div>""", unsafe_allow_html=True)
        except Exception:
            st.metric("Next Macro", "N/A")

        st.info("Momentum Osc -- loaded below")
        momentum_placeholder = st.empty()

    return symbol, interval, enable_elite, use_heikin_ashi, momentum_placeholder


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def load_system_data(symbol, interval, use_heikin_ashi, momentum_placeholder):
    """Load core market data and compute momentum."""
    with st.spinner("Connecting to Quantum Field..."):
        df = fetch_crypto_data(symbol, interval)
        fear_greed = fetch_fear_greed()
        if df.empty:
            st.error("No data available!")
            st.stop()
        current_price = float(df['close'].iloc[-1])
        data_timestamp = df.index[-1]
        st.success(f"Data loaded successfully - {len(df)} bars")

    if use_heikin_ashi:
        df = calculate_heikin_ashi(df)

    try:
        _roc14 = ((df['close'].iloc[-1] - df['close'].iloc[-15]) /
                  df['close'].iloc[-15] * 100) if len(df) >= 15 else 0.0
        _mom_color = "#EF4444" if _roc14 < -3 else "#10B981" if _roc14 > 3 else "#F59E0B"
        _oversold_label = "OVERSOLD" if _roc14 < -5 else "OVERBOUGHT" if _roc14 > 7 else ""
        momentum_placeholder.markdown(f"""
        <div style='background:var(--bg-secondary);border-left:3px solid {_mom_color};
                    padding:8px 12px;border-radius:4px;'>
            <div style='font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);
                        letter-spacing:1px;'>MOMENTUM OSC (ROC-14)</div>
            <div style='font-size:1.0rem;font-weight:700;color:{_mom_color};'>{_roc14:+.2f}%</div>
            <div style='font-size:0.75rem;color:#EF4444;font-weight:600;'>{_oversold_label}</div>
        </div>""", unsafe_allow_html=True)
    except Exception:
        momentum_placeholder.metric("Momentum Osc", "N/A")

    return df, fear_greed, current_price, data_timestamp



def run_elite_analysis(df, symbol, interval, enable_elite, current_price, memory_logger):
    """Execute multi-layer Elite analysis suite."""
    elite_results = {}
    if enable_elite:
        with st.spinner("Running Elite Analysis (Standalone)..."):
            try:
                if _adapter is not None:
                    elite_results = _adapter.analyze_elite(df=df, exposure_pct=15.0)
                elif ELITE_AVAILABLE:
                    # Fallback to local init if global adapter failed
                    temp_adapter = init_elite_system()
                    if temp_adapter:
                        elite_results = temp_adapter.analyze_elite(df=df, exposure_pct=15.0)
            except Exception as _ea_e:
                st.warning(f"Elite analysis error: {_ea_e}")
                elite_results = {}

            if elite_results:
                append_audit_row(current_price, elite_results, symbol)
                if MOBILE_AVAILABLE and mobile_notifier:
                    try:
                        onchain = elite_results.get('onchain', {})
                        fg_data = onchain.get('fear_greed', {})
                        fg_val = int(fg_data.get('value', 50)) if isinstance(fg_data, dict) else 50
                        triggered = mobile_notifier.check_sniper_trigger(elite_results, fg_val)
                        if triggered:
                            st.error("PRECISION EXECUTION TRIGGER FIRED -- Check Telegram!")
                    except Exception:
                        pass

            if memory_logger and MEMORY_AVAILABLE and elite_results:
                try:
                    signal_id = memory_logger.log_daily_signal(elite_results=elite_results, current_price=current_price)
                    if signal_id:
                        st.success(f"Signal logged to memory (ID: {signal_id})")
                except Exception as e:
                    st.warning(f"Memory logging failed: {e}")
    return elite_results


def render_geopolitical_banner(active, headline, severity, violence_score, unified_gate, unified_kelly):
    """Render high-priority geopolitical alert banner."""
    if not active:
        return

    _sonar_b64 = _generate_sentinel_sonar()
    st.components.v1.html(f"""
    <audio autoplay style="display:none">
        <source src="data:audio/wav;base64,{_sonar_b64}" type="audio/wav">
    </audio>
    """, height=0)
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1a0000, #330000);
                border:2px solid #ff2222; border-radius:10px;
                padding:16px 24px; margin:12px 0;
                box-shadow: 0 0 30px rgba(255,0,0,0.3);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="color:#ff4444; font-size:1rem; font-weight:900;
                            font-family:var(--font-mono); letter-spacing:2px;">
                    [!] GEOPOLITICAL SHOCK DETECTED -- {severity}
                </div>
                <div style="color:#ffcccc; font-size:0.85rem; margin-top:6px;
                            font-family:var(--font-mono);">
                    {headline[:120]}
                </div>
                <div style="color:#ff8888; font-size:0.7rem; margin-top:4px;">
                    Violence Override: {violence_score:.1f}/5.0 | Gates: LOCKED | Kelly: 0%
                </div>
            </div>
            <div style="text-align:right;">
                <div style="color:#ff2222; font-size:2.5rem; font-weight:900;
                            font-family:var(--font-mono); text-shadow: 0 0 20px #ff0000;">
                    [!]
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if MOBILE_AVAILABLE and mobile_notifier:
        try:
            _push_msg = (
                f"[!] GEOPOLITICAL SHOCK DETECTED\n\n"
                f"Severity: {severity}\n"
                f"Headline: {headline[:200]}\n\n"
                f"Violence: {violence_score:.1f}/5.0 EXTREME\n"
                f"Gates: LOCKED | Kelly: 0%\n"
                f"Action: ALL POSITIONS FROZEN\n\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
            )
            mobile_notifier.send_message(_push_msg, parse_mode="HTML")
        except Exception:
            pass


def render_metrics_hud(current_price, price_delta, manifold_score, regime,
                       unified_posterior, unified_kelly, unified_gate,
                       diffusion_score, elite_results, elite_system):
    """Render the main metrics HUD cards."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

    with m_col1:
        _pd_color = "var(--success)" if price_delta >= 0 else "var(--danger)"
        st.markdown(f"""
            <div class="metric-label">BTC Price</div>
            <div class="metric-value">${current_price:,.0f}</div>
            <div style="color: {_pd_color}; font-size: 0.8rem; font-family:var(--font-mono);">
                {'+' if price_delta > 0 else ''}{price_delta:.2%}
            </div>
        """, unsafe_allow_html=True)

    with m_col2:
        _regime_color = "var(--danger)" if regime == "BLOOD_IN_STREETS" else "var(--success)" if regime == "DISTRIBUTION_TOP" else "var(--text-secondary)"
        st.markdown(f"""
            <div class="metric-label">Manifold DNA</div>
            <div class="metric-value">{manifold_score:.1f}</div>
            <div style="font-size: 0.8rem; color:{_regime_color}; font-family:var(--font-mono);">{regime}</div>
        """, unsafe_allow_html=True)

    with m_col3:
        _post_color = "var(--success)" if unified_posterior >= BAYESIAN_THRESHOLD else "var(--accent-cyan)"
        st.markdown(f"""
            <div class="metric-label">Bayesian P(win)</div>
            <div class="metric-value" style="color: {_post_color};">{unified_posterior:.1f}%</div>
            <div style="font-size: 0.8rem; color:var(--text-muted); font-family:var(--font-mono);">Gate: {unified_gate['status']} | Kelly: {unified_kelly:.1f}%</div>
        """, unsafe_allow_html=True)

    with m_col4:
        _diff_color = "var(--success)" if diffusion_score > 60 else "var(--danger)" if diffusion_score < 40 else "var(--warning)"
        st.markdown(f"""
            <div class="metric-label">Whale Diffusion</div>
            <div class="metric-value" style="color:{_diff_color};">{diffusion_score}</div>
            <div style="font-size: 0.8rem; color:var(--text-muted); font-family:var(--font-mono);">On-Chain Depth</div>
        """, unsafe_allow_html=True)

    with m_col5:
        impact = elite_results.get('impact_cost', {})
        if not impact and elite_system:
            impact = elite_system.micro.calculate_impact_cost(100000, side='BUY') if hasattr(elite_system, 'micro') and elite_system.micro else {}
        slip_bps = impact.get('slippage_bps', 0) if isinstance(impact, dict) else 0
        st.markdown(f"""
            <div class="metric-label">Slippage Adj.</div>
            <div class="metric-value">{slip_bps:.1f}</div>
            <div style="font-size: 0.8rem; color:var(--text-muted); font-family:var(--font-mono);">Impact Cost (bps)</div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_commanders_brief(final_action, unified_posterior, unified_kelly, unified_gate,
                             regime, market_condition_text, wyckoff_result, elite_results, current_price):
    """Render the high-level Commander's Brief."""
    action_color = "var(--success)" if final_action in ['BUY', 'ADD', 'SNIPER_BUY'] else "var(--danger)"
    action_icon = "EXECUTE" if final_action in ['BUY', 'ADD', 'SNIPER_BUY'] else "HOLD"

    if unified_kelly == 0:
        _kelly_line = f"Kelly LOCKED to 0.0% -- Blocker: <b>{unified_gate['reason']}</b>"
        _kelly_color = "var(--danger)"
    else:
        _kelly_line = f"Kelly Allocation: <b>{unified_kelly:.1f}%</b> of capital"
        _kelly_color = "var(--success)"

    _dca_legs_html = ""
    if final_action in ['BUY', 'ADD', 'SNIPER_BUY'] and unified_gate['gate_open']:
        _physics = elite_results.get('physics_pdf', {})
        _p10 = _physics.get('lower_bound_p10', 0)
        _p50 = _physics.get('expected_value', 0)
        if _p10 and _p50:
            _l1 = current_price
            _l2 = (_p10 + current_price) / 2
            _l3 = _p10
            _dca_legs_html = f"""
                <div style="margin-top:8px; font-size:0.85rem; font-family: var(--font-mono); color:var(--accent-cyan);">
                  DCA AMBUSH:
                  Leg 1 (33%) ${_l1:,.0f} >
                  Leg 2 (33%) ${_l2:,.0f} >
                  Leg 3 (34%) ${_l3:,.0f} <- P10 Floor
                </div>
            """

    _pwin_color = 'var(--text-muted)' if not unified_gate['gate_open'] else 'var(--accent-cyan)'
    _pwin_text = f'{unified_posterior:.1f}%' if unified_gate['gate_open'] else f'{unified_posterior:.1f}% (Gate Locked)'

    _brief_html = (
        f'<div class="glass-card" style="border-left: 4px solid {action_color}; padding: 18px 24px; margin-bottom: 16px;">'
        '<div style="font-size:0.65rem; letter-spacing:3px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:6px;">COMMANDER\'S BRIEF -- LEVEL 1 DECISION CENTER</div>'
        '<div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">'
        '<div>'
        '<div style="font-size:0.75rem; color:var(--text-muted);">FINAL ACTION</div>'
        f'<div style="font-size:2rem; font-weight:900; color:{action_color};">{action_icon}</div>'
        '</div>'
        '<div>'
        '<div style="font-size:0.75rem; color:var(--text-muted);">BAYESIAN P_WIN</div>'
        f'<div style="font-size:1.8rem; font-weight:900; color:{_pwin_color};">{_pwin_text}</div>'
        f'<div style="font-size:0.7rem; color:var(--text-muted);">Regime: {regime} | Gate: {unified_gate["status"]}</div>'
        '</div>'
        '<div style="flex:1;">'
        '<div style="font-size:0.75rem; color:var(--text-muted);">POSITION SIZING (KELLY)</div>'
        f'<div style="color:{_kelly_color}; font-size:0.9rem; margin-top:4px;">{_kelly_line}</div>'
        f'{_dca_legs_html}'
        '</div>'
        '</div>'
        f'<div style="margin-top:12px; padding-top:8px; border-top:1px solid var(--border-subtle); font-family:var(--font-mono); font-size:0.75rem; color:var(--text-secondary);">'
        f'CONDITION: {market_condition_text}'
        '</div>'
        f'<div style="font-family:var(--font-mono); font-size:0.7rem; color:var(--text-muted); margin-top:4px;">'
        f'Wyckoff: {wyckoff_result["met"]}/{wyckoff_result["total"]} conditions met (min {WYCKOFF_MIN_CONDITIONS} required)'
        '</div>'
        '</div>'
    )
    st.markdown(_brief_html, unsafe_allow_html=True)


def render_strategic_positioning_matrix(current_price, final_action, unified_gate):
    """Render the Strategic Zone Mapping card."""
    def get_strategic_zone(price):
        if price <= 0 or current_price <= 0:
            return {"name": "DATA ERROR", "hebrew": "shgiat netunim",
                    "status": "Price unavailable", "class": "zone-outside", "icon": "X"}
        pct = (price - current_price) / current_price
        NOISE_BAND = 0.025
        AMBUSH_BAND = 0.080
        ASSAULT_BAND = -0.080
        if abs(pct) <= NOISE_BAND:
            return {"name": "WHITE NOISE AREA (+/-2.5%)", "hebrew": "azor ha-raash ha-lavan",
                    "status": f"Gene Silencing Active | Price Range: ${current_price*(1-NOISE_BAND):,.0f}-${current_price*(1+NOISE_BAND):,.0f}",
                    "class": "zone-noise", "icon": "~"}
        elif NOISE_BAND < pct <= AMBUSH_BAND:
            return {"name": "UPPER AMBUSH ZONE (+2.5% to +8%)", "hebrew": "maarav elyon (shia kmonai)",
                    "status": f"Profit Harvesting Mode | Resistance: ${current_price*(1+AMBUSH_BAND):,.0f}",
                    "class": "zone-ambush", "icon": ">>"}
        elif ASSAULT_BAND <= pct < -NOISE_BAND:
            return {"name": "ULTIMATE ASSAULT ZONE (-2.5% to -8%)", "hebrew": "azor ha-histaarut (Assault Zone)",
                    "status": f"Bayesian Singularity | Support: ${current_price*(1+ASSAULT_BAND):,.0f}",
                    "class": "zone-assault", "icon": "<<"}
        else:
            return {"name": "OUTSIDE PRIMARY ZONES (>+/-8%)", "hebrew": "mi-chutz le-azorei ha-maarav",
                    "status": "Awaiting Macro-Structural Alignment", "class": "zone-outside", "icon": "--"}

    zone_data = get_strategic_zone(current_price)
    if final_action in ['HOLD'] and 'ASSAULT' in zone_data['name']:
        _zone_icon = '!!'
        _zone_name = 'TRANSITION WATCH -- No Entry'
        _zone_hebrew = 'azor maavar -- lelo knisa'
        _zone_status = f'Zone conditions met but Execution Gates BLOCKED (Final Action: {final_action})'
    else:
        _zone_icon = zone_data['icon']
        _zone_name = zone_data['name']
        _zone_hebrew = zone_data['hebrew']
        _zone_status = zone_data['status']

    st.markdown(f"""
        <div class="zone-card {zone_data['class']}">
            <div style="font-size: 0.75em; color:var(--text-muted); font-family:var(--font-mono); letter-spacing:1px;">STRATEGIC POSITIONING MATRIX</div>
            <div style="font-size: 1.4em; margin: 10px 0; color:var(--text-primary); font-weight:700;">[{_zone_icon}] {_zone_name}</div>
            <div style="font-size: 1.0em; color: var(--text-secondary);">{_zone_hebrew}</div>
            <hr style="opacity: 0.15; margin: 10px 0;">
            <div style="font-size: 0.85em; font-family: var(--font-mono); color:var(--text-secondary);">STATUS: {_zone_status}</div>
        </div>
    """, unsafe_allow_html=True)


def render_interference_dark_signals(elite_results):
    """Render interference matrix and dark signals cards."""
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Epigenetic Interference Matrix")
        if 'interference_matrix' in elite_results:
            matrix = np.array(elite_results['interference_matrix'])
            labels = ["ONCHAIN", "MICRO", "CHAOS", "SENTIMENT", "TECH"]
            fig = go.Figure(data=go.Heatmap(
                z=matrix, x=labels, y=labels,
                colorscale=[[0.0, 'rgba(50,50,50,1)'], [0.5, 'rgba(255,50,50,0.8)'], [1.0, 'rgba(0,255,0,0.8)']],
                texttemplate="%{z:.1f}", showscale=False
            ))
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color="rgba(255,255,255,0.7)"))
            try:
                st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})
            except TypeError:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Awaiting Monolithic Initialization...")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Dark Signals")
        dark_edge = elite_results.get('dark_edge', 0)
        st.markdown(f"""
            <div class="metric-label">Statistical Edge</div>
            <div class="metric-value" style="font-size: 1.8rem;">{dark_edge:+.2%}</div>
        """, unsafe_allow_html=True)
        dark_signals = elite_results.get('dark_signals', [])
        if dark_signals:
            for ds in dark_signals:
                st.caption(f"TARGET **{ds.name}** | p={ds.p_value:.3f}")
        else:
            st.write("No statistically significant hidden edges detected.")
        st.markdown('</div>', unsafe_allow_html=True)


def render_advanced_diagnostics(elite_results, df, unified_kelly, unified_gate):
    """Render advanced quantum diagnostics expander."""
    with st.expander("ADVANCED QUANTUM DIAGNOSTICS (Physics & Math Teams)", expanded=False):
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)

        if TOPO_VIZ_AVAILABLE and isinstance(elite_results, dict) and elite_results.get('topology'):
            topo_report = elite_results.get('topology', {})
            render_topology_manifold(st, df['close'].values, df['volume'].values, topo_report)

        s_col1, s_col2, s_col3 = st.columns(3)

        with s_col1:
            st.markdown("#### Hidden Markov States")
            hmm_regime = elite_results.get('hmm_regime', 'AWAITING_STATE_TRANSITION')
            st.info(f"**Current Hidden State:**\n\n{hmm_regime}")

            st.markdown(f"""
                <div class="metric-label">Kelly Allocation</div>
                <div class="metric-value" style="font-size: 1.5rem; color: {'var(--success)' if unified_kelly > 0 else 'var(--danger)'}">{unified_kelly:.1f}%</div>
            """, unsafe_allow_html=True)
            if unified_kelly == 0:
                st.error(f"Kelly LOCKED to 0.0% by: `{unified_gate['reason']}`")

        with s_col2:
            st.markdown("#### Price Probability Density")
            pdf = elite_results.get('physics_pdf', {})
            if pdf:
                st.write(f"**Feynman-Kac Projection (24h):**")
                st.write(f"Expected: ${pdf.get('expected_value', 0):,.0f}")
                st.write(f"Range: ${pdf.get('lower_bound_p10', 0):,.0f} - ${pdf.get('upper_bound_p90', 0):,.0f}")
            else:
                st.write("Diffusion Model: CALIBRATING...")

        with s_col3:
            st.markdown("#### Manifold Stability")
            topo = elite_results.get('topology', {}) if isinstance(elite_results, dict) else {}
            if topo and isinstance(topo, dict):
                flux = topo.get('topological_flux', 0.5)
                stability = topo.get('manifold_stability', 'TRANSITION')
                st.markdown(f"""
                    <div class="metric-label">Topological Flux</div>
                    <div class="metric-value" style="font-size: 1.5rem; color: {'var(--success)' if stability == 'LOCKED' else 'var(--danger)'};">{flux:.3f}</div>
                    <div style="font-size: 0.8rem; color:var(--text-muted);">Stability: {stability}</div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


def render_macro_pulse(diffusion_score):
    """Render real-time macro pulse from Google Finance."""
    if not GEMINI_AVAILABLE:
        return

    st.markdown("---")
    st.markdown("## Macro Pulse (Google Finance)")
    st.caption("Real-time market context from Google Finance")
    try:
        if 'gemini_chat' not in st.session_state:
            from gemini_chat_module_ELITE_v20 import EliteGeminiChat
            st.session_state.gemini_chat = EliteGeminiChat()
        macro_data = st.session_state.gemini_chat.fetch_macro_pulse()
        if macro_data.get('status') == 'live':
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                etf_flow = macro_data.get('btc_etf_flow_24h', 0)
                delta_color = "normal" if etf_flow >= 0 else "inverse"
                st.metric("BTC ETF Flows (24h)", f"${etf_flow:+.0f}M",
                         delta=f"{'+' if etf_flow > 0 else ''}Inflow" if etf_flow >= 0 else "Outflow",
                         delta_color=delta_color)
            with col2:
                sp500 = macro_data.get('sp500_change', 0)
                st.metric("S&P 500 (Today)", f"{sp500:+.2f}%", delta="Bullish" if sp500 > 0 else "Bearish")
            with col3:
                vix = macro_data.get('vix', 0)
                st.metric("VIX (Fear Index)", f"{vix:.1f}", delta="High volatility" if vix > 20 else "Calm")
            with col4:
                sentiment = macro_data.get('sentiment', 'NEUTRAL')
                indicator = "[+]" if sentiment == "Bullish" else "[-]" if sentiment == "Bearish" else "[=]"
                st.metric("Market Sentiment", f"{indicator} {sentiment}")
            if diffusion_score > 70 and etf_flow < -200:
                st.warning("**DIVERGENCE ALERT!** On-Chain: Whales accumulating (Score: {:.0f}/100) | ETF Flows: Retail selling (${:+.0f}M outflow) | Action: SNIPER ENTRY opportunity".format(diffusion_score, etf_flow))
            elif diffusion_score < 50 and etf_flow > 200:
                st.info("**Macro Confluence:** On-Chain: Neutral activity | ETF Flows: Retail buying (${:+.0f}M inflow) | Note: Watch for on-chain confirmation".format(etf_flow))
            st.caption(f"Last updated: {macro_data.get('timestamp', 'N/A')}")
        else:
            st.info("Macro data unavailable - check API connectivity")
        return macro_data
    except Exception as e:
        st.warning(f"Macro Pulse error: {str(e)}")
        return {}


def extract_geopol_shield(elite_results, violence_score):
    """Detect geopolitical shocks from NLP headlines and nature events."""
    active = False
    headline = ""
    severity = ""
    if GEOPOL_AVAILABLE:
        _all_headlines = []
        _nlp_data = elite_results.get('nlp', {}) if elite_results else {}
        if isinstance(_nlp_data, dict):
            for h in _nlp_data.get('headlines', []):
                if isinstance(h, dict):
                    _all_headlines.append(h.get('title', h.get('text', '')))
                elif isinstance(h, str):
                    _all_headlines.append(h)
        _nature_data = elite_results.get('nature_events', []) if elite_results else []
        if isinstance(_nature_data, list):
            for ev in _nature_data:
                if isinstance(ev, dict):
                    _all_headlines.append(ev.get('description', ''))
        _worst_v = 0.0
        for hl in _all_headlines:
            hl_lower = hl.lower()
            for kw, info in GEOPOL_KEYWORDS.items():
                if kw.lower() in hl_lower:
                    v = info["violence"]
                    if v > _worst_v:
                        _worst_v = v
                        headline = hl
                        severity = info["severity"]
        if _worst_v > 0:
            _prev_shock_ts = st.session_state.get('geopol_shock_ts', 0)
            _shock_age_h = (time.time() - _prev_shock_ts) / 3600 if _prev_shock_ts else 999
            if _shock_age_h > 3.0 or st.session_state.get('geopol_shock_headline', '') != headline:
                active = True
                st.session_state['geopol_shock'] = True
                st.session_state['geopol_shock_ts'] = time.time()
                st.session_state['geopol_shock_headline'] = headline
                st.session_state['geopol_shock_severity'] = severity
            violence_score = max(violence_score, _worst_v)
    return active, headline, severity, violence_score


def run_misdirection_engine(misdirection, elite_results, current_price, fear_greed, regime, diffusion_score, violence_score):
    """Run and render the Misdirection Engine panel."""
    if not (misdirection and MISDIRECTION_AVAILABLE):
        return
    try:
        _physics = elite_results.get('physics_pdf', {})
        _p10 = _physics.get('lower_bound_p10', current_price * 0.95) if _physics else current_price * 0.95
        _onchain = elite_results.get('onchain', {}) if isinstance(elite_results.get('onchain'), dict) else {}
        _onchain_components = _onchain.get('components', {}) if isinstance(_onchain.get('components'), dict) else {}
        _whale = float(_onchain_components.get('whale', 50) or 50)
        _netflow = float(_onchain.get('recent_netflow', 0) or 0)
        _nlp_data = elite_results.get('nlp', {}) if isinstance(elite_results.get('nlp'), dict) else {}
        _nlp_s = float(_nlp_data.get('sentiment', 0) or 0)
        if _nlp_data.get('geopol_alert'):
            _geopol_sev = float(_nlp_data.get('geopol_severity', 0) or 0)
            _nlp_s = min(_nlp_s, -0.5 * _geopol_sev)

        _prior = BAYESIAN_NEUTRAL_PRIOR
        _chaos = float(violence_score / 5.0)

        if _nature_engine is not None:
            try:
                _nature_engine.refresh()
                _chaos += _nature_engine.get_chaos_adjustment()
                _chaos = min(1.0, _chaos)
            except Exception:
                pass

        mis_result = misdirection.analyze(
            price=current_price, p10_floor=float(_p10),
            fear_greed=int(fear_greed), whale_score=_whale,
            exchange_netflow=_netflow, nlp_sentiment=_nlp_s,
            regime=str(regime), diffusion_score=float(diffusion_score),
            prior=_prior, chaos=_chaos,
        )
        render_misdirection_panel(st, misdirection, mis_result)
    except Exception as _mis_err:
        st.warning(f"Misdirection Engine error: {_mis_err}")


def compute_unified_system_state(elite_results, current_price, violence_score, fear_greed, regime, diffusion_score):
    """Compute the unified state dictionary for all modules."""
    _onchain = elite_results.get('onchain', {}) if isinstance(elite_results.get('onchain'), dict) else {}
    _onchain_components = _onchain.get('components', {}) if isinstance(_onchain.get('components'), dict) else {}
    _nlp_data_u = elite_results.get('nlp', {}) if isinstance(elite_results.get('nlp'), dict) else {}
    _nlp_sentiment_u = float(_nlp_data_u.get('sentiment', 0) or 0)
    _book_imbalance_u = float(_onchain.get('book_imbalance', 0) or 0)
    _chaos_norm = float(violence_score / 5.0)
    _whale_score = float(_onchain_components.get('whale', 50) or 50)
    _netflow_u = float(_onchain.get('recent_netflow', 0) or 0)
    _physics_u = elite_results.get('physics_pdf', {}) if elite_results else {}
    _p10_floor = float(_physics_u.get('lower_bound_p10', current_price * 0.95)) if _physics_u else current_price * 0.95
    _mis_score_u = 0.0

    # [FIX-2/5] Compute posterior ONCE from neutral prior
    unified_posterior = compute_unified_posterior(
        _prior=BAYESIAN_NEUTRAL_PRIOR,
        diffusion_score=float(diffusion_score),
        fear_greed=int(fear_greed),
        book_imbalance=_book_imbalance_u,
        chaos_norm=_chaos_norm,
        nlp_sentiment=_nlp_sentiment_u,
        misdirection_score=_mis_score_u,
        regime=str(regime),
    )

    # [FIX-7] Safety cap
    unified_posterior = apply_posterior_safety_caps(unified_posterior, float(diffusion_score), int(fear_greed))

    # [FIX-9] Wyckoff check
    wyckoff_result = compute_wyckoff_conditions(
        fear_greed=int(fear_greed),
        whale_score=_whale_score,
        current_price=current_price,
        p10_floor=_p10_floor,
        netflow=_netflow_u,
        nlp_sentiment=_nlp_sentiment_u,
        regime=str(regime),
        diffusion_score=float(diffusion_score),
    )

    # [FIX-3/8] Kelly ONCE
    unified_kelly = compute_unified_kelly(unified_posterior, violence_score)

    # [FIX-1/8/9] Gate status ONCE
    unified_gate = compute_unified_gate_status(unified_posterior, violence_score, wyckoff_result)

    # [FIX-4] Market condition text
    market_condition_text = generate_market_condition_text(
        chaos=_chaos_norm, fear_greed=int(fear_greed), regime=str(regime),
        diffusion_score=float(diffusion_score), violence_score=violence_score,
    )

    # Store in session state for other modules
    st.session_state['sentinel_p_win'] = unified_posterior
    st.session_state['sentinel_gate_open'] = unified_gate['gate_open']
    st.session_state['unified_kelly'] = unified_kelly
    st.session_state['unified_gate'] = unified_gate

    return {
        "posterior": unified_posterior,
        "kelly": unified_kelly,
        "gate": unified_gate,
        "wyckoff": wyckoff_result,
        "market_text": market_condition_text,
        "chaos_norm": _chaos_norm
    }


def render_tactical_sentinel(unified_posterior, unified_gate, final_action):
    """Render Tactical Sentinel alerts and sound logic."""
    _sentinel_p_win = unified_posterior
    _sentinel_gate_open = unified_gate['gate_open']
    _sentinel_prev_fired = st.session_state.get('sentinel_alert_fired', False)

    if _sentinel_gate_open and not _sentinel_prev_fired:
        st.session_state['sentinel_alert_fired'] = True
        st.session_state['sentinel_alert_ts'] = time.strftime('%H:%M:%S')
        _sonar_b64 = _generate_sentinel_sonar()
        st.components.v1.html(f"""
        <audio autoplay style="display:none">
            <source src="data:audio/wav;base64,{_sonar_b64}" type="audio/wav">
        </audio>
        """, height=0)
        st.markdown(f"""
        <div class="sentinel-alert-banner">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div class="sentinel-title">TACTICAL SENTINEL -- GATE CROSSING DETECTED</div>
                    <div class="sentinel-subtitle">
                        P(win) crossed execution threshold | {time.strftime('%H:%M:%S')} |
                        System detected decision point -- verify and confirm
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="sentinel-metric">{_sentinel_p_win:.1f}%</div>
                    <div style="color:var(--success);font-family:var(--font-mono);font-size:0.8rem;">GATE {BAYESIAN_THRESHOLD}% [OK]</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif not _sentinel_gate_open and _sentinel_prev_fired:
        st.session_state['sentinel_alert_fired'] = False

    if final_action == 'HOLD':
        st.session_state['sentinel_alert_fired'] = False


def render_execution_gates_tab(enable_elite, elite_system, elite_results, df):
    """Render Execution Gates tab content."""
    st.subheader("Elite v20 - Medallion Analysis")
    if enable_elite and elite_system and elite_results:
        elite_system.render_elite_section(st, elite_results, df)
    else:
        st.warning("Elite Engine is disabled or unavailable")


def render_quantum_diagnostics_tab(df, regime, confidence, violence_score):
    """Render Quantum Diagnostics (DUDU Projection) tab content."""
    st.subheader("Manifold Projection (DUDU Overlay)")
    st.caption("Past: Regime Filter | Present: Dynamic Vol Cone | Future: Bootstrap Paths")
    if DUDU_AVAILABLE:
        qc_payload = {'regime': regime, 'confidence': confidence, 'qc_codes': [regime]}
        try:
            render_projection_tab(st, df, qc_payload=qc_payload, horizon=48,
                                 current_regime=regime, current_violence=violence_score,
                                 key="dudu_projection_tab3")
            st.info("**Defense Check**: If 'Windows used' < 20, reduce position size by 0.5x")
        except Exception as e:
            st.error(f"DUDU Error: {e}")
    else:
        st.warning("DUDU Overlay module not available")


def render_liquidity_xray_tab(df, elite_results):
    """Render Liquidity X-Ray tab content."""
    st.subheader("Liquidity X-Ray (Price vs OnChain)")
    st.caption("Green = Bullish Divergence (Whales buying) | Red = Bearish Divergence")
    if DIVERGENCE_AVAILABLE:
        try:
            render_divergence_chart(st, df, elite_results if elite_results else {})
        except Exception as e:
            st.error(f"Divergence Error: {e}")
    else:
        st.warning("Divergence Chart module not available")


def render_node_topology_tab():
    """Render Node Topology tab content."""
    if NODE_TOPO_AVAILABLE:
        render_node_stats_hud()
        render_quantum_ledger_anatomy()
        render_node_topology()
    else:
        st.warning("Node Topology module initializing...")


def render_simulation_lab_tab():
    """Render Simulation Lab tab content."""
    st.subheader("Institutional Simulation Lab")
    st.caption("Engine-driven backtest of the current Victory Protocol configuration")
    if BACKTEST_AVAILABLE and BACKTEST_DATA_AVAILABLE:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            sim_days = st.slider("Duration (Days)", 30, 365, 180)
        with col_s2:
            sim_capital = st.number_input("Initial Capital ($)", 1000, 1000000, 100000, step=10000)
        with col_s3:
            sim_lookback = st.number_input("Lookback Window", 50, 200, 100)
        if st.button("Run Victory Simulation", use_container_width=True):
            with st.spinner("Running simulation..."):
                try:
                    sim_df = fetch_btc_daily(days=sim_days + sim_lookback + 10)
                    if not sim_df.empty:
                        engine = MonolithBacktestEngine(initial_capital=sim_capital)
                        sim_results = engine.run_simulation(sim_df, lookback_period=sim_lookback)
                        metrics = sim_results['metrics']
                        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                        m_col1.metric("CAGR", f"{metrics['cagr_pct']:+.1f}%")
                        m_col2.metric("Sortino", f"{metrics['sortino_ratio']:.2f}")
                        m_col3.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.1f}%")
                        m_col4.metric("Total Return", f"{metrics['total_return_pct']:+.1f}%")
                        history_df = sim_results['history']
                        fig_sim = go.Figure()
                        norm_eq = (history_df['equity'] / history_df['equity'].iloc[0]) * 100
                        norm_price = (history_df['price'] / history_df['price'].iloc[0]) * 100
                        fig_sim.add_trace(go.Scatter(x=history_df['timestamp'], y=norm_eq, name="Elite v20 (Equity)", line=dict(color='#00f2ff', width=3)))
                        fig_sim.add_trace(go.Scatter(x=history_df['timestamp'], y=norm_price, name="BTC Benchmark", line=dict(color='rgba(255,255,255,0.2)', width=2, dash='dot')))
                        fig_sim.update_layout(template='plotly_dark', title="Victory Protocol Performance (Relative Growth)",
                                             margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor='rgba(0,0,0,0)',
                                             plot_bgcolor='rgba(0,0,0,0)', height=400)
                        try:
                            st.plotly_chart(fig_sim, width="stretch")
                        except TypeError:
                            st.plotly_chart(fig_sim, use_container_width=True)
                        if sim_results['trades']:
                            with st.expander("View Trade Execution Logs"):
                                for t in sim_results['trades']:
                                    icon = "[BUY]" if t['type'] == 'BUY' else "[SELL]"
                                    st.write(f"{icon} **{t['type']}** at ${t['price']:,.0f} | {t['time'].strftime('%Y-%m-%d')} | {t['reason']}")
                    else:
                        st.error("Could not fetch simulation data.")
                except Exception as e:
                    st.error(f"Simulation Error: {str(e)}")
    else:
        st.warning("Simulation Engine (MonolithBacktest) not available.")


def render_spectral_dudu_tab(df, _spectral, _p10_boosted, regime, confidence, violence_score, final_action):
    """Render Spectral Divergence & DUDU tab content."""
    st.markdown("""
    <div style="font-size:0.65rem;letter-spacing:3px;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:12px;">
    SPECTRAL DIVERGENCE ENGINE -- WHALE-GAP FFT ANALYSIS
    </div>
    """, unsafe_allow_html=True)

    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    _ev = _spectral.get("eigenvalue", 1.0)
    _tension = _spectral.get("tension", "LOW")
    _amp = _spectral.get("amplitude", 0.0)
    _freq = _spectral.get("dominant_freq", 0)
    _tension_color = "var(--danger)" if _tension == "HIGH" else "var(--warning)" if _tension == "MEDIUM" else "var(--success)"

    with s_col1:
        st.markdown(f"""
        <div class="metric-label">EIGENVALUE (Drift x)</div>
        <div class="metric-value" style="color:var(--accent-cyan);">{_ev:.4f}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);">1.0 = neutral | 1.25 = max</div>
        """, unsafe_allow_html=True)
    with s_col2:
        st.markdown(f"""
        <div class="metric-label">TENSION (Whale Spring)</div>
        <div class="metric-value" style="color:{_tension_color};">{_tension}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);">Amplitude: {_amp:.3f}</div>
        """, unsafe_allow_html=True)
    with s_col3:
        _p10_display = f"${_p10_boosted:,.0f}" if _p10_boosted else "Pending"
        st.markdown(f"""
        <div class="metric-label">P10 FLOOR (Boosted)</div>
        <div class="metric-value" style="color:var(--purple);">{_p10_display}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);">48h horizon | eigenvalue lifted</div>
        """, unsafe_allow_html=True)
    with s_col4:
        st.markdown(f"""
        <div class="metric-label">DOMINANT FREQ</div>
        <div class="metric-value">{_freq}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);">Whale-cycle resonance index</div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    _fft_power = _spectral.get("fft_power", [])
    if _fft_power and len(_fft_power) > 1:
        _fig_fft = go.Figure()
        _x_axis = list(range(1, len(_fft_power) + 1))
        _fig_fft.add_trace(go.Bar(
            x=_x_axis, y=_fft_power,
            marker_color=["#EF4444" if i + 1 == _freq else "#06e8f9" for i in range(len(_fft_power))],
            name="FFT Power", showlegend=False,
        ))
        _fig_fft.add_vline(x=_freq, line_dash="dash", line_color="#F59E0B",
                          annotation_text=f"Dominant: f={_freq}", annotation_font_color="#F59E0B",
                          annotation_position="top right")
        _fig_fft.update_layout(title="FFT Power Spectrum -- Whale-Gap Divergence Signal",
                              xaxis_title="Frequency Index (cycles per lookback window)",
                              yaxis_title="Power Amplitude", height=320,
                              margin=dict(l=10, r=10, t=40, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                              yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                              font=dict(color="#9ca3af"))
        st.plotly_chart(_fig_fft, use_container_width=True)
        st.caption(f"Dominant frequency f={_freq} (eigenvalue {_ev:.4f}) | Input: whale-gap divergence = z-score(close) x diffusion/100")
    else:
        st.info("Insufficient divergence history for FFT -- need >=8 bars. Refresh after data loads.")

    st.markdown("---")

    st.subheader("DUDU Manifold Projection (Spectral-Boosted Cone)")
    if DUDU_AVAILABLE and not df.empty:
        qc_payload = {"regime": regime, "confidence": confidence}
        render_projection_tab(st, df, qc_payload=qc_payload, horizon=48,
                             current_regime=regime, current_violence=violence_score,
                             key="dudu_spectral_tab7")
        if _p10_boosted:
            st.success(f"Spectral Boost Active: P10 floor raised to **${_p10_boosted:,.0f}** (eigenvalue = {_ev:.4f})")
    else:
        st.warning("DUDU overlay not available or no data loaded.")

    st.markdown("---")
    _brief_color = "var(--danger)" if _tension == "HIGH" else "var(--warning)" if _tension == "MEDIUM" else "var(--success)"
    _action_color_spectral = "var(--success)" if final_action in ['BUY', 'ADD', 'SNIPER_BUY'] else "var(--danger)"
    st.markdown(f"""
    <div class="glass-card" style="border-left: 4px solid {_brief_color}; padding: 14px 20px;">
        <div style="font-size:0.65rem;letter-spacing:3px;color:var(--text-muted);margin-bottom:6px;">SPECTRAL BRIEF -- COMMAND LINE</div>
        <div style="font-family:var(--font-mono);font-size:0.9rem;color:var(--text-primary);">
            EIGENVALUE: <span style="color:var(--accent-cyan);font-weight:700;">{_ev:.4f}</span> &nbsp;|
            TENSION: <span style="color:{_brief_color};font-weight:700;">{_tension}</span> &nbsp;|
            P10: <span style="color:var(--purple);font-weight:700;">{_p10_display}</span> &nbsp;|
            ACTION: <span style="color:{_action_color_spectral};font-weight:700;">{final_action}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_bayesian_waterfall_tab(elite_results, unified_posterior, diffusion_score, fear_greed, violence_score, regime, unified_kelly, current_price, manifold_score):
    """Render Bayesian Waterfall tab content."""
    if WATERFALL_AVAILABLE:
        try:
            _onchain_wf = elite_results.get('onchain', {}) if elite_results else {}
            if not isinstance(_onchain_wf, dict):
                _onchain_wf = {}
            _nlp_data_wf = elite_results.get('nlp', {}) if elite_results else {}
            _nlp_wf_val = float(_nlp_data_wf.get('sentiment', 0) or 0) if isinstance(_nlp_data_wf, dict) else 0.0

            _waterfall_data = {
                "posterior": unified_posterior,
                "prior": BAYESIAN_NEUTRAL_PRIOR,
                "diffusion_score": float(diffusion_score),
                "fear_greed": int(fear_greed),
                "fg_label": "Extreme Fear" if fear_greed < 20 else "Fear" if fear_greed < 40 else "Neutral" if fear_greed < 60 else "Greed" if fear_greed < 80 else "Extreme Greed",
                "book_imbalance": float(_onchain_wf.get('book_imbalance', 0) or 0),
                "chaos_penalty": float(violence_score / 5.0),
                "nlp_sentiment": _nlp_wf_val,
                "misdirection": 0.0,
                "regime": str(regime),
                "kelly_fraction": unified_kelly,
                "btc_price": float(current_price),
                "elite_score": float(manifold_score),
                "gate_threshold": BAYESIAN_THRESHOLD,
            }
            render_bayesian_waterfall(st, _waterfall_data)
        except Exception as _wf_err:
            st.error(f"Bayesian Waterfall error: {_wf_err}")
    else:
        st.warning("bayesian_waterfall.py not found in dashboards/ folder")


def render_header(symbol, unified_gate):
    """Render the institutional dashboard header."""
    st.markdown(f"""
        <div class="inst-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="inst-title">ELITE v20 | TERMINAL</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono); letter-spacing: 1px;">
                        INSTITUTIONAL ACCESS // {symbol} // {CURRENT_PHASE}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-blue);">
                        SYSTEM STATUS: {'<span class="status-good">ONLINE</span>' if unified_gate['gate_open'] else '<span style="color: var(--danger); font-weight: bold;">GATES LOCKED</span>'}
                    </div>
                    <div style="font-size: 0.6rem; color: var(--text-muted);">ARCHITECTURE: V20.4 MONOLITHIC STANDALONE</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not unified_gate['gate_open']:
        st.error(f"EXECUTION GATES LOCKED: {unified_gate['reason']}")


def render_action_bar(regime, final_action):
    """Render the bottom regime and action bar."""
    r_col1, r_col2 = st.columns([1, 1])
    with r_col1:
        if regime == "BLOOD_IN_STREETS":
            st.markdown(f'<div class="status-pill status-execute">REGIME: {regime}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-pill status-silence">REGIME: {regime}</div>', unsafe_allow_html=True)
    with r_col2:
        status_class = "status-execute" if final_action in ['BUY', 'ADD'] else "status-silence"
        st.markdown(f'<div style="text-align:right;"><span class="status-pill {status_class}">FINAL ACTION: {final_action}</span></div>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_ai_sidebar_components(symbol, current_price, manifold_score, unified_posterior, diffusion_score, violence_score, fear_greed, unified_kelly, final_action, regime):
    """Render Gemini AI chat and Mobile Fortress components in sidebar."""
    if GEMINI_AVAILABLE:
        dashboard_data = prepare_elite_dashboard_data(
            market_data={'symbol': symbol, 'current_price': current_price, 'price_change_24h': 0},
            portfolio_data={'capital': {'total_value': 10000, 'available': 5000},
                           'dca': {'btc_held': 0.05, 'avg_entry': 95000},
                           'tactical': {'active_positions': 0, 'total_pnl': 0}},
            signals={'dca': {'status': final_action, 'manifold_score': manifold_score, 'regime': regime},
                    'tactical': {'direction': final_action, 'confidence': unified_posterior / 100.0}},
            modules={'Manifold DNA': manifold_score, 'OnChain Diffusion': diffusion_score,
                    'Chaos/Violence': violence_score, 'Fear & Greed': fear_greed},
            risk_metrics={'max_risk_pct': 5.0, 'kelly_fraction': unified_kelly / 100.0, 'current_exposure': 0},
            performance={'total_trades': 0, 'win_rate': 0, 'total_pnl': 0, 'rr_ratio': 0}
        )
        render_gemini_sidebar_elite(dashboard_data)

    with st.sidebar:
        st.markdown("---")
        st.markdown("""
        <div style="font-family:var(--font-mono); font-size:0.65rem; letter-spacing:1.5px;
                    color:var(--text-secondary); margin-bottom:6px;">
            MOBILE FORTRESS
        </div>
        """, unsafe_allow_html=True)
        if MOBILE_AVAILABLE:
            st.success("Telegram Connected")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Test Alert", key="test_telegram"):
                    mobile_notifier.test_connection()
                    st.success("Sent!")
            with col_b:
                if st.button("Daily Brief", key="daily_brief"):
                    brief_data = {
                        'action': final_action, 'confidence': unified_posterior / 100.0,
                        'price': current_price, 'dna': manifold_score,
                        'div_label': "BULLISH" if diffusion_score > 60 else "BEARISH" if diffusion_score < 40 else "NEUTRAL",
                        'div_score': diffusion_score, 'sentiment': fear_greed,
                        'strategy_hint': f"Regime: {regime}"
                    }
                    mobile_notifier.send_smart_alert(brief_data)
                    st.success("Sent!")
            if final_action in ["SNIPER_BUY", "BUY"] and unified_posterior > 80:
                if 'last_alert_action' not in st.session_state or st.session_state.last_alert_action != final_action:
                    mobile_notifier.alert_victory_vector(score=manifold_score, kelly_fraction=unified_kelly / 100.0, action="BUY")
                    st.session_state.last_alert_action = final_action
                    st.toast("Alert sent to phone!")
        else:
            st.warning("Not configured")
            st.caption("Add to secrets.toml:")
            st.code('TELEGRAM_BOT_TOKEN = "..."\nTELEGRAM_CHAT_ID = "..."', language="toml")


def render_footer(data_timestamp, macro_data):
    """Render institutional footer and module status."""
    st.markdown("---")
    _clean_ts = data_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    _macro_ts = macro_data.get('timestamp', 'LIVE') if macro_data else 'PENDING'
    st.caption(f"**Elite v20 Medallion (Standalone)** | Last Update: {_clean_ts} | Macro Pulse: {_macro_ts} | All times in UTC")

    _mod_status = []
    _mod_status.append(f'<span class="{"status-good" if ELITE_AVAILABLE else "status-danger"}">Elite: {"ON" if ELITE_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if DUDU_AVAILABLE else "status-danger"}">DUDU: {"ON" if DUDU_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if DIVERGENCE_AVAILABLE else "status-danger"}">Divergence: {"ON" if DIVERGENCE_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if GEMINI_AVAILABLE else "status-danger"}">Gemini: {"ON" if GEMINI_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if GLOBAL_MAP_AVAILABLE else "status-caution"}">Map: {"ON" if GLOBAL_MAP_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if WATERFALL_AVAILABLE else "status-caution"}">Waterfall: {"ON" if WATERFALL_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if QC_AVAILABLE else "status-caution"}">QC: {"ON" if QC_AVAILABLE else "OFF"}</span>')
    _mod_status.append(f'<span class="{"status-good" if ORACLE_AVAILABLE else "status-caution"}">Oracle: {"ON" if ORACLE_AVAILABLE else "OFF"}</span>')
    st.markdown(f"""
    <div style="font-size:0.65rem; font-family:var(--font-mono); color:var(--text-muted); letter-spacing:0.5px;">
        MODULES: {' | '.join(_mod_status)}
    </div>
    """, unsafe_allow_html=True)


def render_quality_control_tab(df, elite_results, interval, current_price, confidence, unified_posterior, manifold_score, fear_greed, violence_score, diffusion_score):
    """Render Quality Control tab content."""
    if QC_AVAILABLE:
        try:
            _sentinel_alive = any(t.name == "SentinelWorker" for t in threading.enumerate())
            _qc_module_status = {
                "Elite": ELITE_AVAILABLE, "DUDU": DUDU_AVAILABLE,
                "Divergence": DIVERGENCE_AVAILABLE, "Gemini": GEMINI_AVAILABLE,
                "Global Map": GLOBAL_MAP_AVAILABLE, "Waterfall": WATERFALL_AVAILABLE,
                "Misdirection": MISDIRECTION_AVAILABLE, "Nature": NATURE_AVAILABLE,
                "Mobile": MOBILE_AVAILABLE, "Memory": MEMORY_AVAILABLE,
                "Backtest": BACKTEST_AVAILABLE, "Spectral": SPECTRAL_AVAILABLE,
                "Fear&Greed API": fear_greed != 50,
            }
            _qc_cached = fetch_btc_spot_price()
            _qc_cached_price = _qc_cached.get('price', current_price) if isinstance(_qc_cached, dict) else current_price
            render_qc_dashboard(
                st, df, elite_results, interval=interval,
                current_price=current_price, cached_price=_qc_cached_price,
                confidence=confidence,
                bayesian_posterior=unified_posterior,
                manifold_score=manifold_score, fear_greed=fear_greed,
                violence_score=violence_score, diffusion_score=diffusion_score,
                module_status=_qc_module_status, sentinel_running=_sentinel_alive,
                exchange_source="multi-fallback",
            )
        except Exception as _qc_err:
            st.error(f"Quality Control Error: {_qc_err}")
            st.code(traceback.format_exc())
    else:
        st.warning("qc_dashboard.py not found in dashboards/ folder")


def render_strategic_overview_tab(df, final_action, fear_greed, unified_posterior, regime, violence_score):
    """Render the Strategic Overview tab content."""
    _badge_class = "action-badge-buy" if final_action in ['BUY', 'ADD', 'SNIPER_BUY'] else ("action-badge-sell" if final_action in ['SELL', 'REDUCE'] else "action-badge-hold")
    _badge_label = final_action
    _fg_label = "Extreme Fear" if fear_greed < 20 else "Fear" if fear_greed < 40 else "Neutral" if fear_greed < 60 else "Greed" if fear_greed < 80 else "Extreme Greed"
    _fg_color = "var(--danger)" if fear_greed < 30 else "var(--success)" if fear_greed > 70 else "var(--warning)"
    _signal_html = _render_signal_strength_html(unified_posterior / 100.0)
    _violence_fmt = f"{violence_score:.2f}"

    st.markdown(_signal_html, unsafe_allow_html=True)

    _verdict_html = (
        '<div class="glass-card" style="padding:16px 24px;">'
        '<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px;">'
        '<div>'
        '<div style="font-family:var(--font-mono); font-size:0.6rem; letter-spacing:2px; color:var(--text-muted); margin-bottom:6px;">SYSTEM VERDICT</div>'
        f'<div class="action-badge {_badge_class}">{_badge_label}</div>'
        '</div>'
        '<div style="text-align:right;">'
        '<div class="metric-label">FEAR &amp; GREED</div>'
        f'<div class="metric-value" style="font-size:1.5rem; color:{_fg_color};">{fear_greed}</div>'
        f'<div style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">{_fg_label}</div>'
        '</div>'
        '<div style="text-align:right;">'
        '<div class="metric-label">REGIME</div>'
        f'<div style="font-family:var(--font-mono); font-size:1.0rem; font-weight:600; color:var(--text-primary);">{regime}</div>'
        f'<div style="font-size:0.7rem; color:var(--text-muted);">Violence: {_violence_fmt}</div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(_verdict_html, unsafe_allow_html=True)

    # Technical charts
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                       row_heights=[0.6, 0.2, 0.2],
                       subplot_titles=("STRATEGIC PRICE ACTION", "MACD (12,26,9)", "RSI (14)"))
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'))
    std = df['close'].rolling(20).std()
    df['BB_mid'] = df['close'].rolling(20).mean()
    df['BB_upper'] = df['BB_mid'] + (std * 2)
    df['BB_lower'] = df['BB_mid'] - (std * 2)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], line=dict(color='rgba(176,196,222,0.2)', width=1), name='BB Upper', showlegend=False))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], line=dict(color='rgba(176,196,222,0.2)', width=1), fill='tonexty', fillcolor='rgba(176,196,222,0.05)', name='BB Lower', showlegend=False))
    df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    fig.add_trace(go.Scatter(x=df.index, y=df['vwap'], line=dict(color='#06e8f9', width=2, dash='dot'), name='VWAP'))
    df['ema_fast'] = df['close'].ewm(span=20).mean()
    df['ema_slow'] = df['close'].ewm(span=50).mean()
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_fast'], line=dict(color='#10B981', width=1.5), name='EMA 20'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_slow'], line=dict(color='#EF4444', width=1.5), name='EMA 50'))
    fig.add_trace(go.Scatter(x=[df.index[0]], y=[None], mode='lines', line=dict(color='rgba(176,196,222,0.4)'), name='Bollinger (20,2)'))
    if len(df) >= 200:
        sma200 = df['close'].rolling(200).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma200, mode='lines', name='SMA200', line=dict(color='orange', width=2, dash='longdash')))
    fig.add_trace(go.Scatter(x=df.index, y=df['macd'], line=dict(color='#06e8f9', width=1.5), name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], line=dict(color='#EF4444', width=1), name='Signal'), row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Hist',
                         marker_color=['#10B981' if v >= 0 else '#EF4444' for v in df['macd_hist']]), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='#B0C4DE', width=1.5), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(239,68,68,0.5)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(16,185,129,0.5)", row=3, col=1)
    fig.update_layout(template='plotly_dark', height=900, xaxis_rangeslider_visible=False, showlegend=True,
                     hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)
    try:
        st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    colors = ['#10B981' if df['close'].iloc[i] >= df['open'].iloc[i] else '#EF4444' for i in range(len(df))]
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors, opacity=0.8))
    fig_vol.update_layout(template='plotly_dark', height=150, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                         paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                         yaxis=dict(showgrid=False, showticklabels=True, side='right', tickfont=dict(size=8), nticks=3),
                         xaxis=dict(showgrid=False, showticklabels=False))
    try:
        st.plotly_chart(fig_vol, width="stretch", config={'displayModeBar': False})
    except TypeError:
        st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})


def render_nlp_kelly_radar(elite_results, unified_kelly, unified_posterior, unified_gate):
    """Render the Macro NLP & Kelly Fraction panel."""
    nlp_data = elite_results.get('nlp', {}) if elite_results else {}
    if not (nlp_data and isinstance(nlp_data, dict) and nlp_data.get('status')):
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('### Macro NLP & Event Radar')
    n1, n2, n3, n4, n5 = st.columns(5)

    tier1 = nlp_data.get('tier1_count', 0)
    tier2 = nlp_data.get('tier2_count', 0)
    total_src = nlp_data.get('source_count', 0)
    nlp_status = nlp_data.get('status', 'OFFLINE')
    status_color = 'var(--success)' if nlp_status == 'LIVE' else ('var(--warning)' if nlp_status == 'DEGRADED' else 'var(--danger)')

    with n1:
        st.markdown(f"""
            <div class="metric-label">Data Tiers</div>
            <div class="metric-value" style="font-size:1.4rem;">T1:{tier1} T2:{tier2}</div>
            <div style="font-size:0.75rem; color:{status_color};">Total: {total_src} -- {nlp_status}</div>
        """, unsafe_allow_html=True)

    sent_score = nlp_data.get('sentiment_score', 0)
    half_life = nlp_data.get('decay_halflife_hours', 3)
    sent_color = 'var(--success)' if sent_score > 0.05 else ('var(--danger)' if sent_score < -0.05 else 'var(--warning)')
    with n2:
        st.markdown(f"""
            <div class="metric-label">Sentiment Score</div>
            <div class="metric-value" style="color:{sent_color};">{sent_score:+.3f}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">HL: {half_life}h</div>
        """, unsafe_allow_html=True)

    confusion = nlp_data.get('confusion_index', 0)
    conf_label = 'LOW' if confusion < 0.15 else ('HIGH' if confusion > 0.35 else 'MEDIUM')
    conf_color = 'var(--success)' if conf_label == 'LOW' else ('var(--danger)' if conf_label == 'HIGH' else 'var(--warning)')
    with n3:
        st.markdown(f"""
            <div class="metric-label">Confusion Index</div>
            <div class="metric-value" style="color:{conf_color};">{confusion:.3f}</div>
            <div style="font-size:0.75rem; color:{conf_color};">{conf_label}</div>
        """, unsafe_allow_html=True)

    catalyst = nlp_data.get('catalyst_detected', '--')
    with n4:
        st.markdown(f"""
            <div class="metric-label">Catalyst Detected</div>
            <div class="metric-value" style="font-size:1.1rem;">{catalyst.upper() if catalyst else '--'}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Davos Matrix</div>
        """, unsafe_allow_html=True)

    k_color = 'var(--danger)' if unified_kelly == 0 else 'var(--success)'
    k_label = f'{unified_kelly:.1f}% {"LOCKED" if unified_kelly == 0 else "OPEN"}'
    with n5:
        st.markdown(f"""
            <div class="metric-label">Kelly Fraction</div>
            <div class="metric-value" style="color:{k_color};">{k_label}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Dynamic Capital | Gate={BAYESIAN_THRESHOLD:.0f}%</div>
        """, unsafe_allow_html=True)

    headlines = nlp_data.get('top_headlines', [])
    if headlines:
        st.markdown('#### Top Headlines (Decay-Weighted)')
        rows = []
        for h in headlines[:7]:
            if isinstance(h, str):
                h = {'title': h, 'source': 'RSS', 'raw_score': 0.0,
                     'decay_weight': 1.0, 'final_score': 0.0, 'catalysts': []}
            rows.append({
                'Source': h.get('source', ''), 'Headline': h.get('title', '')[:80],
                'Sentiment': f"{h.get('raw_score', 0):+.2f}",
                'Decay Wt': f"{h.get('decay_weight', 0):.2f}",
                'Final': f"{h.get('final_score', 0):+.3f}",
                'Catalysts': ', '.join(h.get('catalysts', [])) or '--'
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown(f"""
    <div style="display:flex; gap:20px; margin-top:8px; font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">
        <span>Kelly: {unified_kelly:.1f}%</span>
        <span>Max Risk: 5%</span>
        <span>P(win) = {unified_posterior:.1f}%</span>
        <span>Gate: {unified_gate['status']}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('---')


def main():
    """Main dashboard execution (standalone -- no PWA dependency)."""

    elite_system = init_elite_system()
    elite_results = {}

    try:
        start_sentinel_daemon()
    except Exception as e:
        print(f"[WARN] Sentinel startup failed: {e}")

    misdirection = MisdirectionEngine() if MISDIRECTION_AVAILABLE else None

    memory_logger = None
    if MEMORY_AVAILABLE:
        try:
            memory_logger = get_logger()
        except Exception as e:
            st.warning(f"Memory system unavailable: {e}")

    # ========================================================================
    # SIDEBAR & DATA
    # ========================================================================
    symbol, interval, enable_elite, use_heikin_ashi, momentum_placeholder = render_sidebar()
    df, fear_greed, current_price, data_timestamp = load_system_data(symbol, interval, use_heikin_ashi, momentum_placeholder)

    # ========================================================================
    # ELITE ANALYSIS
    # ========================================================================
    elite_results = run_elite_analysis(df, symbol, interval, enable_elite, current_price, memory_logger)

    # ========================================================================
    # EXTRACT KEY METRICS
    # ========================================================================
    manifold_score = elite_results.get('elite_score', 50) if elite_results else 50
    confidence = elite_results.get('confidence', 0.5) if elite_results else 0.5
    regime = elite_results.get('chaos', {}).get('regime', 'NORMAL') if elite_results else 'NORMAL'
    _raw_violence = elite_results.get('chaos', {}).get('violence_score', 1.0) if elite_results else 1.0
    violence_score = _raw_violence / 20.0 if _raw_violence > 5 else _raw_violence
    diffusion_score = elite_results.get('onchain', {}).get('diffusion_score', 50) if elite_results else 50
    final_action = elite_results.get('final_action', 'HOLD') if elite_results else 'HOLD'

    if confidence >= 1.0:
        confidence = 0.5
        print("[WARN] confidence >= 1.0 detected (adapter bug) -> forced to 0.5")

    # ========================================================================
    # OSINT & MISDIRECTION
    # ========================================================================
    _geopol_shock_active, _geopol_headline, _geopol_severity, violence_score = extract_geopol_shield(elite_results, violence_score)
    run_misdirection_engine(misdirection, elite_results, current_price, fear_greed, regime, diffusion_score, violence_score)

    # ========================================================================
    # UNIFIED STATE & SENTINEL
    # ========================================================================
    sys_state = compute_unified_system_state(elite_results, current_price, violence_score, fear_greed, regime, diffusion_score)
    unified_posterior = sys_state["posterior"]
    unified_kelly = sys_state["kelly"]
    unified_gate = sys_state["gate"]
    wyckoff_result = sys_state["wyckoff"]
    market_condition_text = sys_state["market_text"]

    render_tactical_sentinel(unified_posterior, unified_gate, final_action)
    render_geopolitical_banner(_geopol_shock_active, _geopol_headline, _geopol_severity, violence_score, unified_gate, unified_kelly)

    # ========================================================================
    # CORE UI COMPONENTS
    # ========================================================================
    render_header(symbol, unified_gate)

    price_delta = df['close'].pct_change().iloc[-1]
    render_metrics_hud(current_price, price_delta, manifold_score, regime,
                       unified_posterior, unified_kelly, unified_gate,
                       diffusion_score, elite_results, elite_system)
    st.markdown("---")

    render_nlp_kelly_radar(elite_results, unified_kelly, unified_posterior, unified_gate)
    render_strategic_positioning_matrix(current_price, final_action, unified_gate)
    render_interference_dark_signals(elite_results)
    render_advanced_diagnostics(elite_results, df, unified_kelly, unified_gate)
    st.markdown("---")

    render_action_bar(regime, final_action)
    st.markdown("---")

    # ========================================================================
    # COMMANDER'S BRIEF
    # ========================================================================
    render_commanders_brief(final_action, unified_posterior, unified_kelly, unified_gate,
                             regime, market_condition_text, wyckoff_result, elite_results, current_price)

    # ========================================================================
    # TABS
    # ========================================================================
    _tab_names = [
        "Strategic Overview", "Execution Gates", "Quantum Diagnostics",
        "Liquidity X-Ray", "Node Topology", "Simulation Lab",
        "Spectral & DUDU", "Global Map", "Bayesian Waterfall", "Quality Control",
    ]
    if ORACLE_AVAILABLE:
        _tab_names.append("Oracle Node")
    _all_tabs = st.tabs(_tab_names)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = _all_tabs[:10]
    tab11 = _all_tabs[10] if len(_all_tabs) > 10 else None

    # Spectral computation
    if 'diffusion_history' not in st.session_state:
        st.session_state.diffusion_history = []
    st.session_state.diffusion_history.append(float(diffusion_score))
    if len(st.session_state.diffusion_history) > 50:
        st.session_state.diffusion_history = st.session_state.diffusion_history[-50:]

    _spectral = {"eigenvalue": 1.0, "tension": "LOW", "amplitude": 0.0, "dominant_freq": 0, "fft_power": []}
    _p10_boosted = None
    if SPECTRAL_AVAILABLE and not df.empty:
        try:
            _hist = st.session_state.diffusion_history
            if len(_hist) >= 8:
                _div_series = np.array(_hist, dtype=float)
            else:
                _div_series = build_divergence_series(df['close'], diffusion_score, window=20)
            _spectral = compute_divergence_eigenvalue(_div_series)
            _cone = build_vol_cone(df['close'], horizon=48, current_violence=violence_score, current_regime=regime)
            _boosted_cone = apply_spectral_boost(_cone, _spectral["eigenvalue"])
            _p10_boosted = _boosted_cone.get("p10_floor_boosted")
            if _spectral["tension"] == "HIGH" and MOBILE_AVAILABLE:
                _alert_key = f"spectral_high_{int(_spectral['eigenvalue'] * 1000)}"
                if st.session_state.get('last_spectral_alert') != _alert_key:
                    try:
                        mobile_notifier.send_message(
                            f"SPECTRAL HIGH TENSION ALERT\n"
                            f"Eigenvalue: {_spectral['eigenvalue']:.4f}\n"
                            f"Amplitude: {_spectral['amplitude']:.3f}\n"
                            f"Dominant Freq: {_spectral['dominant_freq']}\n"
                            f"Action: {final_action} | P_win: {unified_posterior:.1f}%"
                        )
                        st.session_state.last_spectral_alert = _alert_key
                        st.toast("Spectral HIGH alert sent!", icon="!")
                    except Exception as _te:
                        print(f"Telegram spectral alert failed: {_te}")
        except Exception as _se:
            print(f"[WARN] Spectral computation error: {_se}")

    # ========================================================================
    # TAB 1: Strategic Overview
    # ========================================================================
    with tab1:
        render_strategic_overview_tab(df, final_action, fear_greed, unified_posterior, regime, violence_score)


    # ========================================================================
    # TAB 5: Node Topology
    # ========================================================================
    with tab5:
        render_node_topology_tab()

    # ========================================================================
    # TAB 2: Execution Gates
    # ========================================================================
    with tab2:
        render_execution_gates_tab(enable_elite, elite_system, elite_results, df)

    # ========================================================================
    # TAB 3: Quantum Diagnostics
    # ========================================================================
    with tab3:
        render_quantum_diagnostics_tab(df, regime, confidence, violence_score)

    # ========================================================================
    # TAB 4: Liquidity X-Ray
    # ========================================================================
    with tab4:
        render_liquidity_xray_tab(df, elite_results)

    # ========================================================================
    # TAB 6: Simulation Lab
    # ========================================================================
    with tab6:
        render_simulation_lab_tab()

    # ========================================================================
    # MACRO PULSE (Google Finance Integration)
    # ========================================================================
    macro_data = render_macro_pulse(diffusion_score)

    # ========================================================================
    # NATURE & SIDEBAR
    # ========================================================================
    if _nature_engine is not None:
        try:
            _nature_engine.render_panel()
        except Exception as _ne_err:
            st.warning(f"Nature Events Engine error: {_ne_err}")

    render_ai_sidebar_components(symbol, current_price, manifold_score, unified_posterior, diffusion_score, violence_score, fear_greed, unified_kelly, final_action, regime)

    # ========================================================================
    # TAB 8: GLOBAL ECONOMIC MAP
    # ========================================================================
    with tab8:
        if GLOBAL_MAP_AVAILABLE:
            try:
                render_global_map(st)
            except Exception as _map_err:
                st.error(f"Global Map error: {_map_err}")
        else:
            st.warning("global_economic_map.py not found in dashboards/ folder")

    # ========================================================================
    # TAB 9: BAYESIAN WATERFALL
    # ========================================================================
    with tab9:
        render_bayesian_waterfall_tab(elite_results, unified_posterior, diffusion_score, fear_greed, violence_score, regime, unified_kelly, current_price, manifold_score)

    # ========================================================================
    # TAB 7: SPECTRAL DIVERGENCE ENGINE
    # ========================================================================
    with tab7:
        render_spectral_dudu_tab(df, _spectral, _p10_boosted, regime, confidence, violence_score, final_action)

    # ========================================================================
    # TAB 10: QUALITY CONTROL
    # ========================================================================
    with tab10:
        render_quality_control_tab(df, elite_results, interval, current_price, confidence, unified_posterior, manifold_score, fear_greed, violence_score, diffusion_score)

    # ========================================================================
    # TAB 11: ORACLE NODE (HUMINT SCANNER)
    # ========================================================================
    if tab11 is not None:
        with tab11:
            if ORACLE_AVAILABLE:
                try:
                    render_oracle_node(st)
                except Exception as _oracle_err:
                    st.error(f"Oracle Node Error: {_oracle_err}")
                    st.code(traceback.format_exc())
            else:
                st.warning("module_oracle_node.py not found in project folder")

    # ========================================================================
    # FOOTER
    # ========================================================================
    render_footer(data_timestamp, macro_data)


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
