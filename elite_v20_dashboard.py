"""
ELITE v20 — Sovereign Dashboard (THIN CLIENT / SSOT Mode)
═══════════════════════════════════════════════════════════
All financial physics computed ONCE by the Cloud Run backend.
This dashboard is a pure VIEWER — it fetches /api/state and renders.

Single Source of Truth: https://quantum-ledger-pwa-346753340105.europe-west1.run.app/api/state

Run: streamlit run elite_v20_dashboard.py
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False

# ════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════
BACKEND_URL = "https://quantum-ledger-pwa-346753340105.europe-west1.run.app"
REFRESH_INTERVAL = 30  # seconds — backend updates every 5min (onchain) so 30s is plenty

st.set_page_config(
    page_title="ELITE v20 — Sovereign Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  body, .stApp { background: #0a0a0a; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }
  .block-container { padding: 1rem 1.5rem; max-width: 1400px; }
  .metric-box { background: #111827; border: 1px solid #1e293b; border-radius: 10px;
                padding: 14px 18px; margin-bottom: 8px; }
  .green  { color: #4ade80 !important; }
  .yellow { color: #fbbf24 !important; }
  .red    { color: #f87171 !important; }
  .dim    { color: #6b7280 !important; font-size: 11px; }
  .tag    { display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 10px; font-weight: 700; letter-spacing: .5px; }
  .tag-green  { background: rgba(74,222,128,.15); border: 1px solid rgba(74,222,128,.3); color: #4ade80; }
  .tag-yellow { background: rgba(251,191,36,.12); border: 1px solid rgba(251,191,36,.25); color: #fbbf24; }
  .tag-red    { background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.25); color: #f87171; }
  .tag-gray   { background: rgba(107,114,128,.12); border: 1px solid rgba(107,114,128,.25); color: #9ca3af; }
  h1 { font-size: 22px; color: #e2e8f0; letter-spacing: 1px; }
  h2 { font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px;
       border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-top: 20px; }
  .banner { border-radius: 10px; padding: 12px 18px; margin-bottom: 16px;
            font-size: 13px; font-weight: 700; text-align: center; }
  .banner-go   { background: rgba(74,222,128,.1); border: 1px solid rgba(74,222,128,.3); color: #4ade80; }
  .banner-hold { background: rgba(251,191,36,.08); border: 1px solid rgba(251,191,36,.2); color: #fbbf24; }
</style>
""", unsafe_allow_html=True)


# ── Smooth auto-refresh (no visible flicker) ──
if _HAS_AUTOREFRESH:
    st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresh")

# ════════════════════════════════════════════════════════
# DATA FETCH — SINGLE SOURCE OF TRUTH
# ════════════════════════════════════════════════════════
@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_state() -> dict:
    """Pull all financial physics from the Cloud Run SSOT backend."""
    try:
        r = requests.get(f"{BACKEND_URL}/api/state", timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def val(v, fmt="{}", fallback="—", suffix=""):
    """Safe value formatter — never shows None as 0."""
    if v is None or v == "" or v == "DATA_OFFLINE":
        return fallback
    try:
        return fmt.format(float(v)) + suffix
    except Exception:
        return str(v)


def tag(status: str) -> str:
    color = "green" if status in ("LIVE","INFLOW","ACCUMULATING","CONNECTED") else \
            "yellow" if status in ("BALANCED","NEUTRAL","HOLD","DISABLED") else \
            "red"    if status in ("DISCONNECTED","OFFLINE","DISTRIBUTING","OUTFLOW","DATA_OFFLINE") else "gray"
    return f'<span class="tag tag-{color}">{status}</span>'


# ════════════════════════════════════════════════════════
# MAIN RENDER
# ════════════════════════════════════════════════════════
s = fetch_state()

if "_error" in s:
    st.error(f"⚠️ Backend unreachable: {s['_error']}")
    st.caption(f"SSOT: {BACKEND_URL}")
    st.stop()



kelly  = s.get("kelly", {})
matrix = s.get("matrix", {})
bc     = matrix.get("bayesian_collapse", {})
vault  = s.get("vault", {})
whale  = s.get("xray", {}).get("whale", {})
tiers  = s.get("data_tiers", {})
prices = s.get("prices", {})
fg     = s.get("fear_greed", {})

# ── Header
col_h1, col_h2, col_h3 = st.columns([3, 2, 2])
with col_h1:
    st.markdown("<h1>⚡ ELITE v20 — SOVEREIGN TERMINAL</h1>", unsafe_allow_html=True)
with col_h2:
    ts = s.get("timestamp","")
    st.caption(f"SSOT Backend · {ts[:19].replace('T',' ')} UTC")
with col_h3:
    mode_color = "green" if s.get("mode") == "DRY_RUN" else "yellow"
    st.markdown(f'Mode: <span class="tag tag-{mode_color}">{s.get("mode","—")}</span>', unsafe_allow_html=True)

# ── Operator Banner
op_sig = s.get("operator_signal", "")
if op_sig:
    css = "banner-go" if op_sig.startswith("🟢") else "banner-hold"
    st.markdown(f'<div class="banner {css}">{op_sig}</div>', unsafe_allow_html=True)

st.markdown("---")

# ══════ ROW 1: Price + Kelly + Manifold + Chaos ══════
st.markdown("<h2>CORE METRICS</h2>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("BTC Price", f"${prices.get('btc', 0):,.0f}")
with c2:
    k_frac = kelly.get("kelly_fraction", 0)
    k_locked = kelly.get("kelly_locked", True)
    k_label = f"🔒 LOCKED" if k_locked else f"{k_frac:.1f}% Alloc"
    k_color = "#9ca3af" if k_locked else "#4ade80"
    st.markdown(f'<div class="metric-box"><div class="dim">Kelly Fraction</div>'
                f'<div style="font-size:24px;font-weight:700;color:{k_color}">{k_label}</div>'
                f'<div class="dim">Dynamic Capital | Gate={kelly.get("gate_threshold",0.917)*100:.1f}%</div></div>',
                unsafe_allow_html=True)
with c3:
    manifold = s.get("manifold_score", 0)
    st.metric("Manifold Score", f"{manifold:.1f}%")
with c4:
    chaos = s.get("chaos_penalty", 0)
    chaos_color = "🔴" if chaos > 0.6 else "🟡" if chaos > 0.3 else "🟢"
    st.metric("Chaos Penalty", f"{chaos_color} {chaos:.3f}")
with c5:
    # p_win_input is the actual posterior used in Kelly calculation
    collapse_p = kelly.get("p_win_input", bc.get("posterior", 0.0))
    triggered  = kelly.get("collapse_triggered", bc.get("triggered", False))
    st.markdown(f'<div class="metric-box"><div class="dim">Bayesian Collapse</div>'
                f'<div style="font-size:20px;font-weight:700;color:{"#4ade80" if triggered else "#fbbf24"}">'
                f'{"✅ TRIGGERED" if triggered else f"⚑ {collapse_p*100:.1f}%"}</div>'
                f'<div class="dim">Threshold: 91.7%</div></div>',
                unsafe_allow_html=True)

# ══════ ROW 2: Regime + Fear/Greed + Whale ══════
st.markdown("<h2>MARKET STATE</h2>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    regime = s.get("regime", "UNKNOWN")
    st.markdown(f'<div class="metric-box"><div class="dim">Regime</div>'
                f'<div style="font-size:16px;font-weight:700">{regime}</div></div>',
                unsafe_allow_html=True)
with c2:
    fg_val  = fg.get("value", "—")
    fg_cls  = fg.get("classification", "—")
    st.markdown(f'<div class="metric-box"><div class="dim">Fear & Greed</div>'
                f'<div style="font-size:22px;font-weight:700">{fg_val}</div>'
                f'<div class="dim">{fg_cls}</div></div>',
                unsafe_allow_html=True)
with c3:
    wh_has  = whale.get("has_real_data", False)
    wh_nf   = whale.get("netflow_status", "DATA_OFFLINE")
    wh_tr   = whale.get("trend", "UNKNOWN")
    wh_score= whale.get("score", 0)
    if not wh_has:
        wh_display = '<span class="red">⚠️ DATA_OFFLINE</span>'
        wh_btc = "—"
    else:
        wh_display = tag(wh_tr)
        wh_btc = f"{whale.get('netflow_btc','—')} BTC"
    st.markdown(f'<div class="metric-box"><div class="dim">Whale Δ (CryptoQuant)</div>'
                f'<div style="font-size:16px;margin:4px 0">{wh_display} {wh_btc}</div>'
                f'<div class="dim">Score: {wh_score}/100 · Netflow: {tag(wh_nf)}</div></div>',
                unsafe_allow_html=True)
with c4:
    onchain_status = tiers.get("onchain", "DISCONNECTED")
    ohlcv_status   = tiers.get("ohlcv", "DISCONNECTED")
    mic_status     = tiers.get("microstructure", "DISCONNECTED")
    st.markdown(f'<div class="metric-box"><div class="dim">Data Tiers</div>'
                f'OHLCV: {tag(ohlcv_status)}<br>'
                f'On-Chain: {tag(onchain_status)}<br>'
                f'Microstructure: {tag(mic_status)}</div>',
                unsafe_allow_html=True)

# ══════ ROW 2b: MACRO NLP & EVENT RADAR (XAI Layer) ══════
st.markdown("<h2>📡 MACRO NLP & EVENT RADAR</h2>", unsafe_allow_html=True)
nlp = s.get("nlp", {})
if nlp and nlp.get("source_count", 0) > 0:
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        t1_count = nlp.get("tier1_count", 0)
        t2_count = nlp.get("tier2_count", 0)
        total    = nlp.get("source_count", 0)
        estimate = nlp.get("source_estimate", 0)
        nlp_status = nlp.get("status", "OFFLINE")
        status_color = "#4ade80" if nlp_status == "LIVE" else "#fbbf24" if nlp_status == "DEGRADED" else "#f87171"
        st.markdown(f'<div class="metric-box"><div class="dim">Data Pipeline</div>'
                    f'<div style="font-size:16px;font-weight:700;color:{status_color}">{nlp_status}</div>'
                    f'<div class="dim">T1 (CryptoPanic): {t1_count}<br>'
                    f'T2 (RSS 17-feed): {t2_count}<br>'
                    f'Total: {total} | Est. {estimate}+ sources</div></div>',
                    unsafe_allow_html=True)
    with n2:
        sent = nlp.get("sentiment_score", 0)
        sent_color = "#4ade80" if sent > 0.1 else "#f87171" if sent < -0.1 else "#fbbf24"
        st.markdown(f'<div class="metric-box"><div class="dim">Sentiment Score</div>'
                    f'<div style="font-size:24px;font-weight:700;color:{sent_color}">{sent:+.4f}</div>'
                    f'<div class="dim">Half-life: {nlp.get("decay_halflife_hours", 3.0)}h</div></div>',
                    unsafe_allow_html=True)
    with n3:
        conf_idx = nlp.get("confusion_index", 0)
        conf_color = "#4ade80" if conf_idx < 0.3 else "#fbbf24" if conf_idx < 0.6 else "#f87171"
        conf_label = "LOW" if conf_idx < 0.3 else "MEDIUM" if conf_idx < 0.6 else "HIGH"
        st.markdown(f'<div class="metric-box"><div class="dim">Confusion Index</div>'
                    f'<div style="font-size:24px;font-weight:700;color:{conf_color}">{conf_idx:.4f}</div>'
                    f'<div class="dim">σ of sentiments · {conf_label}</div></div>',
                    unsafe_allow_html=True)
    with n4:
        catalyst = nlp.get("catalyst_detected", None)
        cat_display = catalyst.upper() if catalyst else "NONE"
        cat_color = "#FF00E5" if catalyst else "#6b7280"
        cat_icon = "⚡" if catalyst else "—"
        st.markdown(f'<div class="metric-box"><div class="dim">Catalyst Detected</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{cat_color}">{cat_icon} {cat_display}</div>'
                    f'<div class="dim">Davos Keyword Matrix</div></div>',
                    unsafe_allow_html=True)

    # ── Top Headlines Table (Temporal Decay Filtered) ──
    headlines = nlp.get("top_headlines", [])[:5]
    if headlines:
        h_rows = []
        for h in headlines:
            score = h.get("final_score", 0)
            score_icon = "🟢" if score > 0.05 else "🔴" if score < -0.05 else "⚪"
            cats = ", ".join(h.get("catalysts", [])).upper()
            h_rows.append({
                "": score_icon,
                "Source": h.get("source", "—"),
                "Headline": h.get("title", "—")[:80],
                "Score": f"{score:+.4f}",
                "Decay": f"{h.get('decay_weight', 0):.2f}",
                "Catalysts": cats if cats else "—",
            })
        st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)

    # ── NLP last update timestamp ──
    nlp_ts = nlp.get("last_updated", "")
    if nlp_ts:
        st.caption(f"NLP last scan: {nlp_ts[:19].replace('T', ' ')} UTC")
else:
    st.caption("📡 NLP data not yet available — waiting for first scan cycle")

# ══════ ROW 3: Bayesian Matrix Table ══════
st.markdown("<h2>BAYESIAN DECISION MATRIX — TOP ARCHETYPES</h2>", unsafe_allow_html=True)
archetypes = matrix.get("archetypes", [])
if archetypes:
    rows = []
    for a in sorted(archetypes, key=lambda x: x.get("p_win", 0), reverse=True)[:7]:
        rows.append({
            "Archetype": a.get("id","—"),
            "Action": a.get("action","—"),
            "P_win": f"{a.get('p_win',0)*100:.1f}%",
            "Chaos Penalty": f"{a.get('chaos_penalty',0):+.3f}",
            "Manifold Contrib": f"{a.get('manifold_contribution',0):.1f}%",
            "Alert": "🔴" if a.get("alert") else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.caption("No archetype data available")

# ══════ ROW 3b: FEYNMAN-KAC PROJECTION ══════
import streamlit.components.v1 as components
try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False

dudu = s.get("dudu", {})
fk   = dudu.get("feynman_kac", {})

STATE_PRICE = prices.get("btc", 0)
if fk and STATE_PRICE:
    fk_target = fk.get("expected_target", 0)
    fk_p10    = fk.get("range", [0, 0])[0]
    fk_p90    = fk.get("range", [0, 0])[1]
    fk_dist   = fk.get("distance_pct", 0)
    fk_conv   = fk.get("convergence_alert", False)

    st.markdown("<h2>🔮 FEYNMAN-KAC PROJECTION (24h)</h2>", unsafe_allow_html=True)

    # ── Pulsing Gold CSS (injected once) ──
    st.markdown("""<style>
    @keyframes target-pulse {
        0%   { box-shadow: 0 0 5px #FFD700; transform: scale(1); }
        50%  { box-shadow: 0 0 30px #FFD700, 0 0 60px rgba(255,215,0,0.4); transform: scale(1.02); }
        100% { box-shadow: 0 0 5px #FFD700; transform: scale(1); }
    }
    .convergence-active {
        background: rgba(255,215,0,0.10);
        border: 2px solid #FFD700 !important;
        border-radius: 10px;
        padding: 14px 18px;
        animation: target-pulse 1.5s infinite ease-in-out;
        margin-bottom: 12px;
    }
    .fk-normal { background: #111827; border: 1px solid #1e293b;
                 border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; }
    </style>""", unsafe_allow_html=True)

    fk_col1, fk_col2, fk_col3 = st.columns([2, 2, 2])

    with fk_col1:
        css_class = "convergence-active" if fk_conv else "fk-normal"
        target_color = "#FFD700" if fk_conv else "#00FFFF"
        label_extra  = " 🚨 CONVERGENCE" if fk_conv else ""
        st.markdown(
            f'<div class="{css_class}">'
            f'<div class="dim">Expected Target (24h){label_extra}</div>'
            f'<div style="font-size:24px;font-weight:700;color:{target_color}">${fk_target:,.0f}</div>'
            f'<div class="dim">Distance: {fk_dist:+.2f}%</div>'
            f'</div>', unsafe_allow_html=True)

    with fk_col2:
        st.markdown(
            f'<div class="fk-normal">'
            f'<div class="dim">Confidence Tunnel (P10 → P90)</div>'
            f'<div style="font-size:15px;font-weight:600;color:#4ade80">${fk_p10:,.0f}</div>'
            f'<div class="dim">↕</div>'
            f'<div style="font-size:15px;font-weight:600;color:#f87171">${fk_p90:,.0f}</div>'
            f'</div>', unsafe_allow_html=True)

    with fk_col3:
        sigma = dudu.get("sigma", 0)
        st.markdown(
            f'<div class="fk-normal">'
            f'<div class="dim">Drift Velocity (μ)</div>'
            f'<div style="font-size:18px;font-weight:700;color:#a78bfa">{fk.get("drift_velocity",0)*1000:.2f}‰/day</div>'
            f'<div class="dim">σ (daily): {sigma:.4f}</div>'
            f'</div>', unsafe_allow_html=True)

    # ── Plotly Vector Chart ──
    if _HAS_PLOTLY and fk_p10 > 0:
        fig = go.Figure()

        # Confidence tunnel (cyan bar)
        fig.add_trace(go.Scatter(
            x=[fk_p10, fk_p90], y=[0, 0], mode="lines",
            line=dict(color="rgba(0,255,255,0.25)", width=22), name="P10→P90 Tunnel"
        ))
        # P10 marker
        fig.add_trace(go.Scatter(
            x=[fk_p10], y=[0], mode="markers+text",
            marker=dict(color="#4ade80", size=9, symbol="line-ew"),
            text=["P10"], textposition="bottom center", textfont=dict(color="#4ade80", size=10),
            showlegend=False
        ))
        # P90 marker
        fig.add_trace(go.Scatter(
            x=[fk_p90], y=[0], mode="markers+text",
            marker=dict(color="#f87171", size=9, symbol="line-ew"),
            text=["P90"], textposition="bottom center", textfont=dict(color="#f87171", size=10),
            showlegend=False
        ))
        # Current price (cyan diamond)
        fig.add_trace(go.Scatter(
            x=[STATE_PRICE], y=[0], mode="markers+text",
            marker=dict(color="#00FFFF", size=16, symbol="diamond",
                        line=dict(color="white", width=2)),
            text=["NOW"], textposition="top center",
            textfont=dict(color="#00FFFF", size=11, family="JetBrains Mono"),
            name="Current Price"
        ))
        # FK Target (gold triangle)
        arrow = "triangle-up" if fk_target > STATE_PRICE else "triangle-down"
        fig.add_trace(go.Scatter(
            x=[fk_target], y=[0], mode="markers+text",
            marker=dict(color="#FFD700", size=14, symbol=arrow,
                        line=dict(color="white", width=1)),
            text=["TARGET"], textposition="top center",
            textfont=dict(color="#FFD700", size=11, family="JetBrains Mono"),
            name="FK Target"
        ))
        fig.update_layout(
            height=130, margin=dict(l=10, r=10, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=True,
                       tickfont=dict(color="#6b7280", size=10),
                       tickformat="$,.0f",
                       range=[min(fk_p10, STATE_PRICE, fk_target)*0.985,
                              max(fk_p90, STATE_PRICE, fk_target)*1.015]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1, 1])
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Sonar Audio Alert (edge detection — only write session_state when value changes) ──
    already_played = st.session_state.get("fk_sound_played", False)
    if fk_conv and not already_played:
        st.session_state["fk_sound_played"] = True  # triggers 1 rerun, then stable
        components.html(
            '<audio autoplay><source src="https://www.soundjay.com/buttons/sounds/button-37a.mp3" type="audio/mpeg"></audio>',
            height=0
        )
    elif not fk_conv and already_played:
        st.session_state["fk_sound_played"] = False  # only reset when it was True

# ══════ ROW 4: Vault ══════
st.markdown("<h2>VAULT</h2>", unsafe_allow_html=True)
if vault:
    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("Equity", f"${vault.get('equity', 0):,.2f}")
    vc2.metric("Daily PnL", f"${vault.get('daily_pnl', 0):+,.2f}")
    vc3.metric("BTC Balance", f"{vault.get('btc_balance', 0):.6f} BTC")
    vc4.metric("USDT Balance", f"${vault.get('usdt_balance', 0):,.2f}")

# ══════ FOOTER ══════
st.markdown("---")
st.caption(
    f"SSOT: [{BACKEND_URL}]({BACKEND_URL}/api/state) · "
    f"System Confidence: {matrix.get('system_confidence',0)*100:.1f}% · "
    f"Kelly Gate: {COLLAPSE_GATE*100:.1f}% · "
    f"v{s.get('version','?')}"
    if (COLLAPSE_GATE := kelly.get("gate_threshold", 0.917)) or True
    else ""
)
