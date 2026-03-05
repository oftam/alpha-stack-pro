"""
qc_dashboard.py  --  MEDALLION Quality Control Dashboard
=========================================================
Standalone QC module that turns the MEDALLION system from a 'black box'
into a transparent, institutional-grade terminal.
"""

import os
import csv
import traceback
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

def _health_color(score: float) -> str:
    if score >= 85: return "var(--success)"
    elif score >= 60: return "var(--warning)"
    return "var(--danger)"

def _bool_dot(val: bool) -> str:
    color = "var(--success)" if val else "var(--danger)"
    return f'<span style="color:{color};font-weight:700;">{"ON" if val else "OFF"}</span>'

def _render_data_validation(st_mod, df, interval: str):
    if df is None or df.empty:
        st_mod.error("Data Validation: No data provided.")
        return 0
    checks = 0
    total = 5
    nan_count = int(df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum())
    if nan_count == 0: checks += 1
    zero_vol = int((df['volume'] == 0).sum())
    if zero_vol == 0: checks += 1
    neg_prices = int((df[['open', 'high', 'low', 'close']] < 0).any(axis=1).sum())
    if neg_prices == 0: checks += 1
    dup_ts = int(df.index.duplicated().sum())
    if dup_ts == 0: checks += 1
    hl_violations = int((df['high'] < df['low']).sum())
    if hl_violations == 0: checks += 1

    score = int(checks / total * 100)
    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {_health_color(score)};">
        <div style="font-size:0.65rem;color:var(--text-muted);font-family:var(--font-mono);">PANEL 1 — DATA VALIDATION</div>
        <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);margin-top:4px;">INTEGRITY SCORE: {score}%</div>
        <div style="font-size:0.7rem;color:var(--text-muted);margin-top:4px;">NaN: {nan_count} | Zero Vol: {zero_vol} | High<Low: {hl_violations}</div>
    </div>""", unsafe_allow_html=True)
    return score

def render_qc_dashboard(st_mod, df, elite_results, interval="1h", current_price=0, cached_price=0, confidence=0.5, bayesian_posterior=0.0, manifold_score=50, fear_greed=50, violence_score=1.0, diffusion_score=50, module_status=None, sentinel_running=False, exchange_source="auto"):
    if module_status is None: module_status = {}
    st_mod.markdown("<h2 style='color:var(--accent-blue);font-family:var(--font-mono);letter-spacing:2px;'>SYSTEM QUALITY CONTROL</h2>", unsafe_allow_html=True)

    try:
        data_score = _render_data_validation(st_mod, df, interval)

        # Bayesian Logic check
        posterior = min(max(bayesian_posterior, 1.0), 98.0)
        gate_status = "OPEN" if posterior >= BAYESIAN_GATE else "LOCKED"
        gate_color = "var(--success)" if gate_status == "OPEN" else "var(--danger)"

        st_mod.markdown(f"""
        <div class="glass-card" style="border-left:4px solid {gate_color};">
            <div style="font-size:0.65rem;color:var(--text-muted);font-family:var(--font-mono);">PANEL 2 — BAYESIAN AUDIT</div>
            <div style="font-size:1.1rem;color:var(--text-primary);margin-top:4px;">
                P(win): <span style="color:{gate_color};font-weight:700;">{posterior:.1f}%</span> / {BAYESIAN_GATE}%
                <span style="margin-left:15px;opacity:0.6;">GATE: {gate_status}</span>
            </div>
        </div>""", unsafe_allow_html=True)

        health = int((data_score + (100 if posterior >= BAYESIAN_GATE else (posterior/BAYESIAN_GATE*100))) / 2)
        st_mod.success(f"System Operational Health: {health}%")

    except Exception as e:
        st_mod.error(f"QC Rendering Error: {e}")
        st_mod.code(traceback.format_exc())
