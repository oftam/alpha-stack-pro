"""
qc_dashboard.py  --  MEDALLION Quality Control Dashboard
=========================================================
Standalone QC module that turns the MEDALLION system from a 'black box'
into a transparent, institutional-grade terminal.

6 Panels:
  1. Data Validation   (בקרת נתונים)
  2. System Reliability (אמינות)
  3. Live Status        (לייב)
  4. Probability Audit  (הסתברויות)
  5. Improvements       (שיפורים וחידודים)
  6. Audit Trail        (יומן ביקורת)

Design: Bloomberg-terminal dark theme, zero external API calls (reuses
elite_results & df passed from the main dashboard).
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

# Audit log path -- same as main dashboard
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_PATH = Path(_DASHBOARD_DIR).parent / "data" / "audit_log.csv"

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


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _health_color(score: float) -> str:
    if score >= 85:
        return "var(--success)"
    elif score >= 60:
        return "var(--warning)"
    return "var(--danger)"


def _bool_dot(val: bool) -> str:
    """Return a colored dot HTML span."""
    color = "var(--success)" if val else "var(--danger)"
    label = "ON" if val else "OFF"
    return f'<span style="color:{color};font-weight:700;">{label}</span>'


def _age_str(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


# ============================================================================
# PANEL 1 -- DATA VALIDATION (בקרת נתונים)
# ============================================================================

def _render_data_validation(st_mod, df, interval: str, exchange_source: str = "auto"):
    """Check OHLCV integrity, freshness, completeness."""

    issues = []
    checks_passed = 0
    total_checks = 6

    # 1. NaN check
    nan_count = int(df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum())
    if nan_count == 0:
        checks_passed += 1
    else:
        issues.append(f"NaN values detected: {nan_count} cells")

    # 2. Zero volume
    zero_vol = int((df['volume'] == 0).sum())
    if zero_vol == 0:
        checks_passed += 1
    else:
        issues.append(f"Zero-volume bars: {zero_vol}")

    # 3. Negative prices
    neg_prices = int((df[['open', 'high', 'low', 'close']] < 0).any(axis=1).sum())
    if neg_prices == 0:
        checks_passed += 1
    else:
        issues.append(f"Negative price bars: {neg_prices}")

    # 4. Duplicate timestamps
    dup_ts = int(df.index.duplicated().sum())
    if dup_ts == 0:
        checks_passed += 1
    else:
        issues.append(f"Duplicate timestamps: {dup_ts}")

    # 5. H > L integrity
    hl_violations = int((df['high'] < df['low']).sum())
    if hl_violations == 0:
        checks_passed += 1
    else:
        issues.append(f"High < Low violations: {hl_violations}")

    # 6. Freshness
    interval_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
    expected_gap = interval_map.get(interval, 3600)
    try:
        last_ts = df.index[-1]
        if last_ts.tzinfo is None:
            last_ts = last_ts.tz_localize('UTC')
        age_sec = (datetime.now(timezone.utc) - last_ts).total_seconds()
        is_fresh = age_sec < expected_gap * 3  # allow 3x gap tolerance
        if is_fresh:
            checks_passed += 1
        else:
            issues.append(f"Data stale: last bar {_age_str(age_sec)} ago (expected < {_age_str(expected_gap * 3)})")
    except Exception:
        age_sec = -1
        issues.append("Cannot determine data freshness")

    score = int(checks_passed / total_checks * 100)
    score_color = _health_color(score)

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {score_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
                    PANEL 1 — DATA VALIDATION (בקרת נתונים)
                </div>
                <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);margin-top:4px;">
                    {checks_passed}/{total_checks} Checks Passed
                </div>
            </div>
            <div style="text-align:right;">
                <div class="metric-value" style="font-size:2rem;color:{score_color};">{score}%</div>
                <div style="font-size:0.7rem;color:var(--text-muted);">Data Integrity</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    d1, d2, d3, d4 = st_mod.columns(4)
    with d1:
        st_mod.markdown(f"""
        <div class="metric-label">Total Bars</div>
        <div class="metric-value">{len(df):,}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">Interval: {interval}</div>
        """, unsafe_allow_html=True)
    with d2:
        st_mod.markdown(f"""
        <div class="metric-label">NaN Cells</div>
        <div class="metric-value" style="color:{'var(--success)' if nan_count == 0 else 'var(--danger)'};">{nan_count}</div>
        """, unsafe_allow_html=True)
    with d3:
        st_mod.markdown(f"""
        <div class="metric-label">Zero Volume Bars</div>
        <div class="metric-value" style="color:{'var(--success)' if zero_vol == 0 else 'var(--warning)'};">{zero_vol}</div>
        """, unsafe_allow_html=True)
    with d4:
        _age_display = _age_str(age_sec) if age_sec >= 0 else "N/A"
        _fresh_color = "var(--success)" if is_fresh else "var(--danger)"
        st_mod.markdown(f"""
        <div class="metric-label">Data Age</div>
        <div class="metric-value" style="color:{_fresh_color};">{_age_display}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">Source: {exchange_source}</div>
        """, unsafe_allow_html=True)

    if issues:
        for iss in issues:
            st_mod.warning(f"⚠ {iss}")

    return score


# ============================================================================
# PANEL 2 -- SYSTEM RELIABILITY (אמינות)
# ============================================================================

def _render_system_reliability(st_mod, module_status: dict):
    """Module availability matrix and health."""

    total = len(module_status)
    online = sum(1 for v in module_status.values() if v)
    coverage = int(online / total * 100) if total > 0 else 0
    cov_color = _health_color(coverage)

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {cov_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
                    PANEL 2 — SYSTEM RELIABILITY (אמינות)
                </div>
                <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary);margin-top:4px;">
                    {online}/{total} Modules Online
                </div>
            </div>
            <div style="text-align:right;">
                <div class="metric-value" style="font-size:2rem;color:{cov_color};">{coverage}%</div>
                <div style="font-size:0.7rem;color:var(--text-muted);">Module Coverage</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Build grid -- 4 columns
    cols = st_mod.columns(4)
    for i, (mod_name, is_on) in enumerate(module_status.items()):
        with cols[i % 4]:
            dot = _bool_dot(is_on)
            st_mod.markdown(f"""
            <div style="background:var(--bg-secondary);border-radius:6px;padding:8px 12px;margin-bottom:6px;
                        border:1px solid var(--border-subtle);">
                <div style="font-size:0.65rem;color:var(--text-muted);font-family:var(--font-mono);letter-spacing:1px;">
                    {mod_name.upper()}
                </div>
                <div style="font-size:0.9rem;margin-top:2px;">{dot}</div>
            </div>
            """, unsafe_allow_html=True)

    return coverage


# ============================================================================
# PANEL 3 -- LIVE STATUS (לייב)
# ============================================================================

def _render_live_status(st_mod, df, current_price: float, cached_price: float,
                        sentinel_running: bool):
    """Real-time vs cached delta, sentinel status, freshness."""

    try:
        last_bar_ts = df.index[-1]
        if last_bar_ts.tzinfo is None:
            last_bar_ts = last_bar_ts.tz_localize('UTC')
        age_sec = (datetime.now(timezone.utc) - last_bar_ts).total_seconds()
    except Exception:
        age_sec = -1

    price_delta = abs(current_price - cached_price) / current_price * 100 if current_price > 0 else 0
    delta_ok = price_delta < 1.0  # < 1% divergence is OK

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {'var(--success)' if delta_ok else 'var(--danger)'};">
        <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
            PANEL 3 — LIVE STATUS (לייב)
        </div>
    </div>
    """, unsafe_allow_html=True)

    l1, l2, l3, l4 = st_mod.columns(4)
    with l1:
        st_mod.markdown(f"""
        <div class="metric-label">Current Price</div>
        <div class="metric-value">${current_price:,.0f}</div>
        """, unsafe_allow_html=True)
    with l2:
        _dc = "var(--success)" if delta_ok else "var(--danger)"
        st_mod.markdown(f"""
        <div class="metric-label">Cache Drift</div>
        <div class="metric-value" style="color:{_dc};">{price_delta:.3f}%</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">{'OK' if delta_ok else 'STALE CACHE'}</div>
        """, unsafe_allow_html=True)
    with l3:
        _age = _age_str(age_sec) if age_sec >= 0 else "N/A"
        st_mod.markdown(f"""
        <div class="metric-label">Last Bar Age</div>
        <div class="metric-value">{_age}</div>
        """, unsafe_allow_html=True)
    with l4:
        _sc = "var(--success)" if sentinel_running else "var(--danger)"
        _sl = "ACTIVE" if sentinel_running else "INACTIVE"
        st_mod.markdown(f"""
        <div class="metric-label">Sentinel Daemon</div>
        <div class="metric-value" style="color:{_sc};">{_sl}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">15m cycle</div>
        """, unsafe_allow_html=True)

    # TTL status strip
    ttl_items = [
        ("OHLCV Data", "5m", 300),
        ("Fear & Greed", "10m", 600),
        ("BTC Spot", "2m", 120),
    ]
    _ttl_html_parts = []
    for name, label, _ttl_sec in ttl_items:
        _ttl_html_parts.append(
            f'<span style="margin-right:16px;">'
            f'<span style="color:var(--text-muted);">{name}:</span> '
            f'<span style="color:var(--accent-cyan);">TTL {label}</span>'
            f'</span>'
        )
    st_mod.markdown(f"""
    <div style="font-size:0.7rem;font-family:var(--font-mono);padding:8px 0;color:var(--text-muted);">
        CACHE TTL: {''.join(_ttl_html_parts)}
    </div>
    """, unsafe_allow_html=True)

    return 100 if delta_ok else 50


# ============================================================================
# PANEL 4 -- PROBABILITY AUDIT (הסתברויות)
# ============================================================================

def _render_probability_audit(st_mod, elite_results: dict, confidence: float,
                              manifold_score: float, fear_greed: int,
                              violence_score: float, diffusion_score: float,
                              bayesian_posterior: float = 0.0):
    """Bayesian equation visualization + Kelly sanity + gate blocker."""

    prior = 55.0  # System default prior
    # ROOT CAUSE FIX: use actual Bayesian posterior, NOT confidence (data quality)
    posterior = min(max(bayesian_posterior, 1.0), 98.0)  # Humility cap 1-98%

    # Evidence contributions (reconstruct from available data)
    diffusion_contrib = (diffusion_score - 50) / 50 * 15  # ±15 range
    fg_contrib = (50 - fear_greed) / 50 * 10  # Contrarian: low FG = positive
    chaos_penalty = min(violence_score / 5.0 * 20, 20)  # 0-20 penalty
    onchain_data = elite_results.get('onchain', {}) if isinstance(elite_results.get('onchain'), dict) else {}
    book_imbalance = float(onchain_data.get('book_imbalance', 0) or 0)
    book_contrib = book_imbalance * 10  # ±10 range

    gate_distance = max(0, BAYESIAN_GATE - posterior)
    gate_open = posterior >= BAYESIAN_GATE

    # Kelly info
    risk_guidance = elite_results.get('risk_guidance', {}) if elite_results else {}
    kelly_pct = risk_guidance.get('optimal_position_pct', 0) if risk_guidance else 0
    kelly_locked = kelly_pct == 0

    # Blocker identification
    if kelly_locked:
        gates_info = elite_results.get('gates', {}) if elite_results else {}
        failed = gates_info.get('failed_gates', gates_info.get('reasons', []))
        if isinstance(failed, list) and failed:
            blocker = " | ".join(str(r) for r in failed[:3])
        elif not gates_info.get('allow_trade', True):
            blocker = "Execution Gates CLOSED"
        elif posterior < BAYESIAN_GATE:
            blocker = f"p_win={posterior:.1f}% < {BAYESIAN_GATE}% threshold"
        elif violence_score >= 3.5:
            blocker = f"High Chaos (violence={violence_score:.2f} >= 3.5)"
        else:
            blocker = "Unknown Gate"
    else:
        blocker = "—"

    _gate_color = "var(--success)" if gate_open else "var(--danger)"

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {_gate_color};">
        <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
            PANEL 4 — PROBABILITY AUDIT (הסתברויות)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Visual Bayesian Equation ──
    st_mod.markdown(f"""
    <div style="background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:8px;
                padding:16px 24px;margin:8px 0;font-family:var(--font-mono);">
        <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);margin-bottom:10px;">
            BAYESIAN POSTERIOR DECOMPOSITION
        </div>
        <div style="font-size:1.1rem;color:var(--text-primary);line-height:2;">
            <span style="color:var(--accent-blue);">Prior</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:var(--accent-cyan);font-weight:700;">{prior:.1f}%</span>
        </div>
        <div style="font-size:1.1rem;color:var(--text-primary);line-height:2;">
            <span style="color:var(--accent-blue);">+ Diffusion Evidence</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:{'var(--success)' if diffusion_contrib >= 0 else 'var(--danger)'};font-weight:700;">
                {diffusion_contrib:+.1f}pp
            </span>
            <span style="font-size:0.75rem;color:var(--text-muted);"> (score: {diffusion_score:.0f})</span>
        </div>
        <div style="font-size:1.1rem;color:var(--text-primary);line-height:2;">
            <span style="color:var(--accent-blue);">+ F&G Contrarian</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:{'var(--success)' if fg_contrib >= 0 else 'var(--danger)'};font-weight:700;">
                {fg_contrib:+.1f}pp
            </span>
            <span style="font-size:0.75rem;color:var(--text-muted);"> (F&G: {fear_greed})</span>
        </div>
        <div style="font-size:1.1rem;color:var(--text-primary);line-height:2;">
            <span style="color:var(--accent-blue);">+ OrderBook Imbalance</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:{'var(--success)' if book_contrib >= 0 else 'var(--danger)'};font-weight:700;">
                {book_contrib:+.1f}pp
            </span>
        </div>
        <div style="font-size:1.1rem;color:var(--text-primary);line-height:2;">
            <span style="color:var(--danger);">− Chaos Penalty</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:var(--danger);font-weight:700;">
                −{chaos_penalty:.1f}pp
            </span>
            <span style="font-size:0.75rem;color:var(--text-muted);"> (violence: {violence_score:.2f})</span>
        </div>
        <hr style="border-color:var(--border-subtle);margin:8px 0;">
        <div style="font-size:1.3rem;color:var(--text-primary);line-height:2;font-weight:900;">
            <span style="color:{_gate_color};">POSTERIOR</span>
            <span style="color:var(--text-muted);"> = </span>
            <span style="color:{_gate_color};font-size:1.5rem;">{posterior:.1f}%</span>
            <span style="font-size:0.85rem;color:var(--text-muted);margin-left:12px;">
                Gate: {BAYESIAN_GATE}% | Distance: {gate_distance:.1f}pp | {'OPEN' if gate_open else 'CLOSED'}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Gate distance visual bar ──
    pct_fill = min(posterior / BAYESIAN_GATE * 100, 100)
    st_mod.markdown(f"""
    <div style="margin:8px 0;">
        <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:var(--text-muted);
                    font-family:var(--font-mono);margin-bottom:4px;">
            <span>GATE PROGRESS</span>
            <span style="color:{_gate_color};font-weight:600;">{posterior:.1f}% / {BAYESIAN_GATE}%</span>
        </div>
        <div style="width:100%;height:10px;background:var(--bg-secondary);border-radius:5px;overflow:hidden;
                    border:1px solid var(--border-subtle);position:relative;">
            <div style="width:{pct_fill}%;height:100%;border-radius:4px;
                        background:linear-gradient(90deg, {_gate_color}88, {_gate_color});
                        transition:width 0.5s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Kelly Sanity ──
    k1, k2, k3 = st_mod.columns(3)
    with k1:
        _kc = "var(--success)" if not kelly_locked else "var(--danger)"
        st_mod.markdown(f"""
        <div class="metric-label">Kelly Fraction</div>
        <div class="metric-value" style="color:{_kc};">{kelly_pct:.1f}%</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">{'OPEN' if not kelly_locked else 'LOCKED'}</div>
        """, unsafe_allow_html=True)
    with k2:
        st_mod.markdown(f"""
        <div class="metric-label">Manifold Score</div>
        <div class="metric-value">{manifold_score:.1f}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">DNA Score</div>
        """, unsafe_allow_html=True)
    with k3:
        _bl_color = "var(--success)" if blocker == "—" else "var(--danger)"
        st_mod.markdown(f"""
        <div class="metric-label">Blocker</div>
        <div style="font-size:0.85rem;font-weight:700;color:{_bl_color};font-family:var(--font-mono);
                    margin-top:4px;word-break:break-word;">{blocker}</div>
        """, unsafe_allow_html=True)

    # Score: gate_open = 100, else proportional
    return 100 if gate_open else int(pct_fill)


# ============================================================================
# PANEL 5 -- IMPROVEMENTS & REFINEMENTS (שיפורים וחידודים)
# ============================================================================

def _render_improvements(st_mod, module_status: dict, data_score: int,
                         reliability_score: int, live_score: int,
                         probability_score: int, df=None):
    """Actionable suggestions + overall health score."""

    # ── Health score computation ──
    health = int(
        data_score * HEALTH_WEIGHTS["data_quality"] / 100 +
        reliability_score * HEALTH_WEIGHTS["module_coverage"] / 100 +
        live_score * HEALTH_WEIGHTS["live_freshness"] / 100 +
        probability_score * HEALTH_WEIGHTS["probability_sanity"] / 100 +
        (100 if module_status.get("Fear&Greed API", False) else 0) * HEALTH_WEIGHTS["api_health"] / 100
    )
    health = min(100, max(0, health))
    h_color = _health_color(health)

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid {h_color};">
        <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
            PANEL 5 — IMPROVEMENTS & REFINEMENTS (שיפורים וחידודים)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Suggestions ──
    suggestions = []

    # Missing modules
    missing = [k for k, v in module_status.items() if not v]
    if missing:
        suggestions.append({
            "severity": "WARNING",
            "text": f"Missing modules: {', '.join(missing)}",
            "action": "Install or configure missing modules to increase coverage."
        })

    # Data quality
    if data_score < 80:
        suggestions.append({
            "severity": "CAUTION",
            "text": "Data quality below 80%",
            "action": "Check exchange connectivity and data pipeline integrity."
        })

    # Stale cache
    if live_score < 80:
        suggestions.append({
            "severity": "WARNING",
            "text": "Cache drift detected or data is stale",
            "action": "Click 'Refresh Data' or verify exchange API connectivity."
        })

    # Low probability sanity
    if probability_score < 50:
        suggestions.append({
            "severity": "INFO",
            "text": f"Gate distance is significant ({100 - probability_score}pp away)",
            "action": "This is normal in non-accumulation regimes. Monitor for Blood-in-Streets conditions."
        })

    # DUDU undersampling
    if not module_status.get("DUDU", False):
        suggestions.append({
            "severity": "WARNING",
            "text": "DUDU overlay offline — no manifold projection available",
            "action": "Ensure dudu_overlay.py is accessible in the dashboards directory."
        })

    # All good
    if not suggestions:
        suggestions.append({
            "severity": "OK",
            "text": "All systems nominal",
            "action": "No corrective actions required."
        })

    for s in suggestions:
        sev = s["severity"]
        if sev == "CAUTION":
            st_mod.error(f"🔴 {s['text']} — {s['action']}")
        elif sev == "WARNING":
            st_mod.warning(f"⚠️ {s['text']} — {s['action']}")
        elif sev == "INFO":
            st_mod.info(f"ℹ️ {s['text']} — {s['action']}")
        else:
            st_mod.success(f"✅ {s['text']}")

    return health


# ============================================================================
# PANEL 6 -- AUDIT TRAIL (יומן ביקורת)
# ============================================================================

def _render_audit_trail(st_mod):
    """Last 20 audit log entries from CSV + win/loss stats."""

    st_mod.markdown(f"""
    <div class="glass-card" style="border-left:4px solid var(--accent-blue);">
        <div style="font-size:0.65rem;letter-spacing:2px;color:var(--text-muted);font-family:var(--font-mono);">
            PANEL 6 — AUDIT TRAIL (יומן ביקורת)
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not AUDIT_PATH.exists():
        st_mod.info("No audit log found yet. Signals will be logged after the first Elite analysis cycle.")
        return

    try:
        audit_df = pd.read_csv(AUDIT_PATH)
        if audit_df.empty:
            st_mod.info("Audit log is empty.")
            return

        total_signals = len(audit_df)

        # Stats
        a1, a2, a3, a4 = st_mod.columns(4)
        with a1:
            st_mod.markdown(f"""
            <div class="metric-label">Total Signals Logged</div>
            <div class="metric-value">{total_signals}</div>
            """, unsafe_allow_html=True)

        with a2:
            if 'final_action' in audit_df.columns:
                buy_signals = int((audit_df['final_action'].isin(['BUY', 'SNIPER_BUY', 'ADD'])).sum())
                st_mod.markdown(f"""
                <div class="metric-label">BUY Signals</div>
                <div class="metric-value" style="color:var(--success);">{buy_signals}</div>
                """, unsafe_allow_html=True)
            else:
                st_mod.markdown("""
                <div class="metric-label">BUY Signals</div>
                <div class="metric-value">N/A</div>
                """, unsafe_allow_html=True)

        with a3:
            if 'elite_score' in audit_df.columns:
                avg_score = audit_df['elite_score'].mean()
                st_mod.markdown(f"""
                <div class="metric-label">Avg Elite Score</div>
                <div class="metric-value">{avg_score:.1f}</div>
                """, unsafe_allow_html=True)
            else:
                st_mod.markdown("""
                <div class="metric-label">Avg Elite Score</div>
                <div class="metric-value">N/A</div>
                """, unsafe_allow_html=True)

        with a4:
            if 'gates_allow_trade' in audit_df.columns:
                gates_open_pct = audit_df['gates_allow_trade'].mean() * 100
                st_mod.markdown(f"""
                <div class="metric-label">Gates Open Rate</div>
                <div class="metric-value">{gates_open_pct:.1f}%</div>
                """, unsafe_allow_html=True)
            else:
                st_mod.markdown("""
                <div class="metric-label">Gates Open Rate</div>
                <div class="metric-value">N/A</div>
                """, unsafe_allow_html=True)

        # Last 20 entries
        with st_mod.expander("Last 20 Audit Entries", expanded=False):
            display_cols = [c for c in ['timestamp_utc', 'symbol', 'price', 'elite_score',
                                         'confidence', 'final_action', 'diffusion_score',
                                         'fear_greed', 'gates_allow_trade'] if c in audit_df.columns]
            st_mod.dataframe(
                audit_df[display_cols].tail(20).iloc[::-1],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st_mod.warning(f"Error reading audit log: {e}")


# ============================================================================
# PUBLIC API
# ============================================================================

def render_qc_dashboard(st_mod, df, elite_results: dict,
                        interval: str = "1h",
                        current_price: float = 0,
                        cached_price: float = 0,
                        confidence: float = 0.5,
                        bayesian_posterior: float = 0.0,
                        manifold_score: float = 50,
                        fear_greed: int = 50,
                        violence_score: float = 1.0,
                        diffusion_score: float = 50,
                        module_status: dict = None,
                        sentinel_running: bool = False,
                        exchange_source: str = "auto"):
    """
    Render the full Quality Control dashboard.

    Parameters
    ----------
    st_mod : streamlit
        The Streamlit module.
    df : pd.DataFrame
        OHLCV DataFrame (same as main dashboard uses).
    elite_results : dict
        Full elite_results dict from analyze_elite().
    interval : str
        Timeframe string (e.g., '1h', '4h', '1d').
    current_price : float
        Latest price from df.
    cached_price : float
        Price from BTC spot cache (for drift check).
    confidence : float
        Bayesian confidence (0.0 - 1.0).
    manifold_score : float
        Elite manifold DNA score.
    fear_greed : int
        Fear & Greed index value.
    violence_score : float
        Chaos violence score.
    diffusion_score : float
        On-chain diffusion score.
    module_status : dict
        {module_name: bool} availability map.
    sentinel_running : bool
        Whether the Sentinel daemon thread is alive.
    exchange_source : str
        Name of the exchange that provided data.
    """

    if module_status is None:
        module_status = {}

    if cached_price == 0:
        cached_price = current_price  # no drift if no cache data

    # ── HEALTH SCORE HERO (computed early, displayed first) ──
    # We compute panel scores first for the hero, then render panels below.
    # Use lightweight pre-checks to avoid double rendering.

    # Pre-compute scores for the hero banner
    _data_q = 100
    if df is not None and not df.empty:
        nan_c = int(df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum())
        zero_v = int((df['volume'] == 0).sum())
        neg_p = int((df[['open', 'high', 'low', 'close']] < 0).any(axis=1).sum())
        dup_t = int(df.index.duplicated().sum())
        hl_v = int((df['high'] < df['low']).sum())
        checks = 5 - sum([nan_c > 0, zero_v > 0, neg_p > 0, dup_t > 0, hl_v > 0])
        _data_q = int(checks / 5 * 100)

    _mod_total = len(module_status)
    _mod_on = sum(1 for v in module_status.values() if v)
    _mod_cov = int(_mod_on / _mod_total * 100) if _mod_total > 0 else 0

    # ROOT CAUSE FIX: use actual Bayesian posterior, NOT confidence (data quality)
    posterior = min(max(bayesian_posterior, 1.0), 98.0)  # Humility cap 1-98%
    _prob_score = 100 if posterior >= BAYESIAN_GATE else int(min(posterior / BAYESIAN_GATE * 100, 100))

    _price_drift = abs(current_price - cached_price) / current_price * 100 if current_price > 0 else 0
    _live_ok = _price_drift < 1.0

    _pre_health = int(
        _data_q * HEALTH_WEIGHTS["data_quality"] / 100 +
        _mod_cov * HEALTH_WEIGHTS["module_coverage"] / 100 +
        (100 if _live_ok else 50) * HEALTH_WEIGHTS["live_freshness"] / 100 +
        _prob_score * HEALTH_WEIGHTS["probability_sanity"] / 100 +
        (100 if module_status.get("Fear&Greed API", False) else 0) * HEALTH_WEIGHTS["api_health"] / 100
    )
    _pre_health = min(100, max(0, _pre_health))
    _h_color = _health_color(_pre_health)

    # ── HERO BANNER ──
    st_mod.markdown(f"""
    <div style="background:linear-gradient(135deg, var(--bg-card), var(--bg-secondary));
                border:1px solid var(--border-subtle);border-radius:10px;
                padding:20px 28px;margin-bottom:16px;
                box-shadow:0 0 30px {_h_color}15;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">
            <div>
                <div style="font-size:0.65rem;letter-spacing:3px;color:var(--text-muted);font-family:var(--font-mono);">
                    SYSTEM HEALTH INDEX
                </div>
                <div style="font-size:3rem;font-weight:900;color:{_h_color};line-height:1.1;
                            text-shadow:0 0 20px {_h_color}40;">
                    {_pre_health}
                </div>
                <div style="font-size:0.75rem;color:var(--text-muted);font-family:var(--font-mono);">
                    / 100  —  {'EXCELLENT' if _pre_health >= 85 else 'OPERATIONAL' if _pre_health >= 60 else 'DEGRADED'}
                </div>
            </div>
            <div style="display:flex;gap:20px;flex-wrap:wrap;">
                <div style="text-align:center;">
                    <div style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">DATA</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{_health_color(_data_q)};">{_data_q}%</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">MODULES</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{_health_color(_mod_cov)};">{_mod_cov}%</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">LIVE</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{'var(--success)' if _live_ok else 'var(--danger)'};">{'OK' if _live_ok else 'DRIFT'}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:0.6rem;color:var(--text-muted);font-family:var(--font-mono);">BAYESIAN</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{_health_color(_prob_score)};">{_prob_score}%</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st_mod.markdown("---")

    # ── PANEL 1: Data Validation ──
    data_score = _render_data_validation(st_mod, df, interval, exchange_source)
    st_mod.markdown("---")

    # ── PANEL 2: System Reliability ──
    reliability_score = _render_system_reliability(st_mod, module_status)
    st_mod.markdown("---")

    # ── PANEL 3: Live Status ──
    live_score = _render_live_status(st_mod, df, current_price, cached_price, sentinel_running)
    st_mod.markdown("---")

    # ── PANEL 4: Probability Audit ──
    probability_score = _render_probability_audit(
        st_mod, elite_results, confidence, manifold_score,
        fear_greed, violence_score, diffusion_score,
        bayesian_posterior=bayesian_posterior
    )
    st_mod.markdown("---")

    # ── PANEL 5: Improvements ──
    _render_improvements(
        st_mod, module_status, data_score, reliability_score,
        live_score, probability_score, df
    )
    st_mod.markdown("---")

    # ── PANEL 6: Audit Trail ──
    _render_audit_trail(st_mod)


# ============================================================================
# STANDALONE MODE
# ============================================================================
if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(page_title="QC Dashboard", layout="wide")
    st.title("Quality Control — Standalone Test")

    # Generate dummy data
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=100, freq='h')
    dummy_df = pd.DataFrame({
        'open': np.random.uniform(80000, 90000, 100),
        'high': np.random.uniform(85000, 95000, 100),
        'low': np.random.uniform(75000, 85000, 100),
        'close': np.random.uniform(80000, 90000, 100),
        'volume': np.random.uniform(100, 10000, 100),
    }, index=dates)

    dummy_modules = {
        "Elite": True, "DUDU": True, "Divergence": True,
        "Gemini": False, "Global Map": True, "Waterfall": True,
        "Misdirection": True, "Nature": False, "Mobile": False,
        "Memory": True, "Backtest": True, "Spectral": True,
        "Fear&Greed API": True,
    }

    render_qc_dashboard(
        st, dummy_df, {},
        interval="1h", current_price=85000, cached_price=85010,
        confidence=0.42, manifold_score=55.3, fear_greed=25,
        violence_score=1.8, diffusion_score=62,
        module_status=dummy_modules, sentinel_running=True,
        exchange_source="bybit"
    )
