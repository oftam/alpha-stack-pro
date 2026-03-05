"""
qc_dashboard.py  --  MEDALLION Quality Control Dashboard
=========================================================
Standalone QC module that turns the MEDALLION system from a 'black box'
into a transparent, institutional-grade terminal.
"""

import os
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# Audit log path
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_PATH = Path(_DASHBOARD_DIR) / "elite_audit_log.csv"

# ============================================================================
# CONSTANTS
# ============================================================================
BAYESIAN_GATE = 91.7
HEALTH_WEIGHTS = {
    "data_quality": 20,
    "module_coverage": 25,
    "live_freshness": 20,
    "probability_sanity": 20,
    "api_health": 15,
}

def _health_color(score: float) -> str:
    if score >= 85: return "var(--success)"
    elif score >= 60: return "var(--warning)"
    return "var(--danger)"

def _bool_dot(val: bool) -> str:
    color = "var(--success)" if val else "var(--danger)"
    label = "ON" if val else "OFF"
    return f'<span style="color:{color};font-weight:700;">{label}</span>'

def _age_str(seconds: float) -> str:
    if seconds < 60: return f"{seconds:.0f}s"
    elif seconds < 3600: return f"{seconds / 60:.1f}m"
    elif seconds < 86400: return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"

def _render_data_validation(st_mod, df, interval: str, exchange_source: str = "auto"):
    issues = []
    checks_passed = 0
    total_checks = 6
    nan_count = int(df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum())
    if nan_count == 0: checks_passed += 1
    else: issues.append(f"NaN values detected: {nan_count}")
    zero_vol = int((df['volume'] == 0).sum())
    if zero_vol == 0: checks_passed += 1
    else: issues.append(f"Zero-volume bars: {zero_vol}")
    neg_prices = int((df[['open', 'high', 'low', 'close']] < 0).any(axis=1).sum())
    if neg_prices == 0: checks_passed += 1
    else: issues.append(f"Negative price bars: {neg_prices}")
    dup_ts = int(df.index.duplicated().sum())
    if dup_ts == 0: checks_passed += 1
    else: issues.append(f"Duplicate timestamps: {dup_ts}")
    hl_violations = int((df['high'] < df['low']).sum())
    if hl_violations == 0: checks_passed += 1
    else: issues.append(f"High < Low violations: {hl_violations}")
    interval_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
    expected_gap = interval_map.get(interval, 3600)
    try:
        last_ts = df.index[-1]
        if last_ts.tzinfo is None: last_ts = last_ts.tz_localize('UTC')
        age_sec = (datetime.now(timezone.utc) - last_ts).total_seconds()
        is_fresh = age_sec < expected_gap * 3
        if is_fresh: checks_passed += 1
        else: issues.append(f"Data stale: {_age_str(age_sec)} ago")
    except:
        age_sec = -1
        is_fresh = False
        issues.append("Freshness check failed")
    score = int(checks_passed / total_checks * 100)
    score_color = _health_color(score)
    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {score_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">PANEL 1 — DATA VALIDATION</div>
                <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);margin-top:4px;">{checks_passed}/{total_checks} Checks Passed</div>
            </div>
            <div style="text-align:right;">
                <div class="metric-value" style="font-size:2rem;color:{score_color};">{score}%</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    return score

def _render_system_reliability(st_mod, module_status: dict):
    total = len(module_status)
    online = sum(1 for v in module_status.values() if v)
    coverage = int(online / total * 100) if total > 0 else 0
    cov_color = _health_color(coverage)
    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {cov_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">PANEL 2 — SYSTEM RELIABILITY</div>
                <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);margin-top:4px;">{online}/{total} Modules Online</div>
            </div>
            <div style="text-align:right;">
                <div class="metric-value" style="font-size:2rem;color:{cov_color};">{coverage}%</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    cols = st_mod.columns(4)
    for i, (name, on) in enumerate(module_status.items()):
        with cols[i % 4]:
            st_mod.markdown(f"<div style='font-size:0.7rem;color:var(--text-muted);'>{name.upper()}: {_bool_dot(on)}</div>", unsafe_allow_html=True)
    return coverage

def _render_live_status(st_mod, df, current_price, cached_price, sentinel_running):
    price_delta = abs(current_price - cached_price) / current_price * 100 if current_price > 0 else 0
    delta_ok = price_delta < 1.0
    st_mod.markdown(f'<div class="glass-card" style="border-left:4px solid {"var(--success)" if delta_ok else "var(--danger)"};"><div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">PANEL 3 — LIVE STATUS</div></div>', unsafe_allow_html=True)
    l1, l2, l3, l4 = st_mod.columns(4)
    l1.metric("Current Price", f"${current_price:,.0f}")
    l2.metric("Cache Drift", f"{price_delta:.3f}%", delta=None, delta_color="inverse" if not delta_ok else "normal")
    l4.metric("Sentinel Daemon", "ACTIVE" if sentinel_running else "OFF", delta_color="normal" if sentinel_running else "inverse")
    return 100 if delta_ok else 50

def _render_probability_audit(st_mod, elite_results, confidence, bayesian_posterior):
    posterior = min(max(bayesian_posterior, 1.0), 98.0)
    gate_open = posterior >= BAYESIAN_GATE
    _gate_color = "var(--success)" if gate_open else "var(--danger)"
    st_mod.markdown(f'<div class="glass-card" style="border-left:4px solid {_gate_color};"><div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">PANEL 4 — PROBABILITY AUDIT</div></div>', unsafe_allow_html=True)
    st_mod.markdown(f"<div style='background:var(--bg-secondary);padding:15px;border-radius:8px;font-family:var(--font-mono);font-size:1.2rem;color:{_gate_color};'>BAYESIAN POSTERIOR: {posterior:.1f}% / {BAYESIAN_GATE}% {'[OPEN]' if gate_open else '[LOCKED]'}</div>", unsafe_allow_html=True)
    return 100 if gate_open else int(posterior / BAYESIAN_GATE * 100)

def render_qc_dashboard(st_mod, df, elite_results, interval="1h", current_price=0, cached_price=0, confidence=0.5, bayesian_posterior=0.0, manifold_score=50, fear_greed=50, violence_score=1.0, diffusion_score=50, module_status=None, sentinel_running=False, exchange_source="auto"):
    if module_status is None: module_status = {}
    st_mod.markdown("<h2 style='color:var(--accent-blue);font-family:var(--font-mono);letter-spacing:2px;'>SYSTEM QUALITY CONTROL</h2>", unsafe_allow_html=True)
    data_score = _render_data_validation(st_mod, df, interval, exchange_source)
    reliability_score = _render_system_reliability(st_mod, module_status)
    live_score = _render_live_status(st_mod, df, current_price, cached_price, sentinel_running)
    prob_score = _render_probability_audit(st_mod, elite_results, confidence, bayesian_posterior)
    health = int((data_score + reliability_score + live_score + prob_score) / 4)
    st_mod.markdown(f"<div class='glass-card' style='text-align:center;border-top:4px solid {_health_color(health)};'><div style='font-size:0.7rem;color:var(--text-muted);'>OVERALL SYSTEM HEALTH</div><div style='font-size:3rem;font-weight:900;color:{_health_color(health)};'>{health}%</div></div>", unsafe_allow_html=True)
