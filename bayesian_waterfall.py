"""
bayesian_waterfall.py  --  MEDALLION Elite v20 Bayesian Waterfall Module
========================================================================
Component 1: Bayesian Waterfall Chart (visual probability cascade)
Component 2: Commander's Brief (Gemini AI military-style briefing)

Standalone:  streamlit run bayesian_waterfall.py
Integrated:  from bayesian_waterfall import render_bayesian_waterfall
"""

import os
import streamlit as st
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Theme constants  --  Bloomberg terminal aesthetic
# ---------------------------------------------------------------------------
BG_PRIMARY = "#0a0e17"
BG_SECONDARY = "#0f1520"
BG_CARD = "#141b2d"
TEXT_PRIMARY = "#e0e6ed"
TEXT_SECONDARY = "#8892a0"
TEXT_MUTED = "#4a5568"
GREEN_POSITIVE = "#00c896"
GREEN_GLOW = "rgba(0,200,150,0.15)"
RED_NEGATIVE = "#ff4757"
RED_GLOW = "rgba(255,71,87,0.15)"
BLUE_TOTAL = "#3b82f6"
BLUE_GLOW = "rgba(59,130,246,0.15)"
GRAY_PRIOR = "#6b7280"
GOLD_ACCENT = "#f5a623"
AMBER_WARN = "#fbbf24"
CONNECTOR_COLOR = "rgba(100,116,139,0.35)"
FONT_MONO = "JetBrains Mono, SF Mono, Fira Code, Consolas, monospace"

GATE_THRESHOLD = 91.7

# ---------------------------------------------------------------------------
# Default elite_data for standalone testing / fallback
# ---------------------------------------------------------------------------
DEFAULT_ELITE_DATA = {
    "posterior": 41.6,
    "prior": 55.0,
    "diffusion_score": 85.0,
    "fear_greed": 10,
    "fg_label": "Extreme Fear",
    "book_imbalance": 0.12,
    "chaos_penalty": 0.32,
    "nlp_sentiment": -0.15,
    "misdirection": 0.08,
    "regime": "Blood_in_streets",
    "kelly_fraction": 0.0,
    "btc_price": 58420.0,
    "elite_score": 41.6,
    "gate_threshold": GATE_THRESHOLD,
}

# ---------------------------------------------------------------------------
# Regime display mapping (Hebrew)
# ---------------------------------------------------------------------------
REGIME_MAP = {
    "Blood_in_streets": "\u05d3\u05dd \u05d1\u05e8\u05d7\u05d5\u05d1\u05d5\u05ea",
    "Normal": "\u05e9\u05d2\u05e8\u05d4",
    "Distribution_top": "\u05d7\u05dc\u05d5\u05e7\u05d4 \u05d1\u05e8\u05d0\u05e9",
}


def _safe_get(data: dict, key: str, default=0.0):
    """Safely extract a value from elite_data with fallback."""
    val = data.get(key, default)
    if val is None:
        return default
    return val


def _compute_waterfall_steps(data: dict) -> dict:
    """
    Compute the waterfall decomposition from Prior to Final Posterior.

    Returns a dict with labels, values, measures, bar_colors, text_labels,
    final_posterior, and running_bases (for shape overlays).
    """
    prior = _safe_get(data, "prior", 55.0)
    diffusion = _safe_get(data, "diffusion_score", 0.0)
    fear_greed = _safe_get(data, "fear_greed", 50)
    fg_label = _safe_get(data, "fg_label", "Neutral")
    book_imbalance = _safe_get(data, "book_imbalance", 0.0)
    chaos_penalty = _safe_get(data, "chaos_penalty", 0.0)
    nlp_sentiment = _safe_get(data, "nlp_sentiment", 0.0)
    misdirection = _safe_get(data, "misdirection", 0.0)
    posterior = _safe_get(data, "posterior", 41.6)

    # --- Calculate deltas ---
    # Diffusion: high diffusion (whales accumulating) is bullish
    diff_delta = max(0.0, (diffusion - 50.0) / 50.0 * 15.0)
    diff_delta = round(diff_delta, 2)

    # Fear & Greed: Extreme Fear is contrarian bullish, Greed is bearish
    if fear_greed <= 25:
        fg_delta = round((25 - fear_greed) / 25.0 * 10.0, 2)
    elif fear_greed >= 75:
        fg_delta = round(-((fear_greed - 75) / 25.0 * 10.0), 2)
    else:
        fg_delta = 0.0

    # Order book imbalance: -1 to +1 -> -8pp to +8pp
    book_delta = round(book_imbalance * 8.0, 2)

    # Chaos penalty: always negative, 0-1 -> 0 to -20pp
    chaos_delta = round(-abs(chaos_penalty) * 20.0, 2)

    # NLP sentiment decay: negative -> -10pp, positive -> +5pp
    if nlp_sentiment < 0:
        nlp_delta = round(nlp_sentiment * 10.0, 2)
    else:
        nlp_delta = round(nlp_sentiment * 5.0, 2)

    # Misdirection signal: 0-1 -> 0 to +8pp
    mis_delta = round(max(0.0, misdirection) * 8.0, 2)

    # Adjust misdirection to make waterfall sum match actual posterior
    computed_sum = prior + diff_delta + fg_delta + book_delta + chaos_delta + nlp_delta + mis_delta
    adjustment = posterior - computed_sum
    mis_delta = round(mis_delta + adjustment, 2)

    # Labels (Hebrew + English)
    labels = [
        "Prior\n(\u05d1\u05e1\u05d9\u05e1)",
        "\u05d3\u05d9\u05e4\u05d5\u05d6\u05d9\u05d4\nOn-Chain",
        "\u05e8\u05d2\u05f3\u05d9\u05dd\nFear & Greed",
        "\u05e1\u05e4\u05e8 \u05e4\u05e7\u05d5\u05d3\u05d5\u05ea\nOrder Book",
        "\u05e7\u05e0\u05e1 \u05db\u05d0\u05d5\u05e1\nChaos",
        "\u05e8\u05e2\u05e9 \u05d7\u05d3\u05e9\u05d5\u05ea\u05d9\nNLP Decay",
        "\u05de\u05d9\u05e1\u05d3\u05d9\u05e8\u05e7\u05e9\u05df\nMisdirection",
        "\u05d4\u05e1\u05ea\u05d1\u05e8\u05d5\u05ea \u05e1\u05d5\u05e4\u05d9\u05ea\nPosterior",
    ]

    values = [prior, diff_delta, fg_delta, book_delta, chaos_delta, nlp_delta, mis_delta, 0]
    measures = ["absolute", "relative", "relative", "relative", "relative", "relative", "relative", "total"]

    # Desired color per bar
    bar_colors = [
        GRAY_PRIOR,                                                # Prior
        GREEN_POSITIVE if diff_delta >= 0 else RED_NEGATIVE,       # Diffusion
        GREEN_POSITIVE if fg_delta >= 0 else RED_NEGATIVE,         # Fear & Greed
        GREEN_POSITIVE if book_delta >= 0 else RED_NEGATIVE,       # Order Book
        RED_NEGATIVE,                                              # Chaos (always red)
        RED_NEGATIVE if nlp_delta < 0 else GREEN_POSITIVE,         # NLP
        GREEN_POSITIVE if mis_delta >= 0 else RED_NEGATIVE,        # Misdirection
        BLUE_TOTAL,                                                # Posterior total
    ]

    # Text labels on bars
    text_labels = []
    for i, v in enumerate(values):
        if measures[i] == "absolute":
            text_labels.append(f"{v:.1f}%")
        elif measures[i] == "total":
            text_labels.append(f"{posterior:.1f}%")
        else:
            sign = "+" if v >= 0 else ""
            text_labels.append(f"{sign}{v:.1f}pp")

    # Compute running bases for shape overlays
    running = 0.0
    bases = []
    tops = []
    for i, (m, v) in enumerate(zip(measures, values)):
        if m == "absolute":
            bases.append(0.0)
            tops.append(v)
            running = v
        elif m == "relative":
            if v >= 0:
                bases.append(running)
                tops.append(running + v)
            else:
                bases.append(running + v)
                tops.append(running)
            running += v
        elif m == "total":
            bases.append(0.0)
            tops.append(running)

    return {
        "labels": labels,
        "values": values,
        "measures": measures,
        "bar_colors": bar_colors,
        "text_labels": text_labels,
        "posterior": posterior,
        "bases": bases,
        "tops": tops,
    }


def _build_waterfall_figure(data: dict) -> go.Figure:
    """Build the Plotly waterfall figure with dark Bloomberg theme."""
    wf = _compute_waterfall_steps(data)
    labels = wf["labels"]
    values = wf["values"]
    measures = wf["measures"]
    bar_colors = wf["bar_colors"]
    text_labels = wf["text_labels"]
    posterior = wf["posterior"]
    bases = wf["bases"]
    tops = wf["tops"]
    gate_threshold = _safe_get(data, "gate_threshold", GATE_THRESHOLD)

    fig = go.Figure()

    # Add waterfall trace with default colors (will be overridden by shapes)
    fig.add_trace(go.Waterfall(
        name="Bayesian Cascade",
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        text=text_labels,
        textposition="outside",
        textfont=dict(
            family=FONT_MONO,
            size=13,
            color=TEXT_PRIMARY,
        ),
        connector=dict(
            line=dict(
                color=CONNECTOR_COLOR,
                width=1,
                dash="dot",
            ),
            visible=True,
        ),
        increasing=dict(
            marker=dict(
                color=GREEN_POSITIVE,
                line=dict(color="rgba(0,200,150,0.5)", width=1),
            )
        ),
        decreasing=dict(
            marker=dict(
                color=RED_NEGATIVE,
                line=dict(color="rgba(255,71,87,0.5)", width=1),
            )
        ),
        totals=dict(
            marker=dict(
                color=BLUE_TOTAL,
                line=dict(color="rgba(59,130,246,0.7)", width=2),
            )
        ),
    ))

    # Overlay shapes for bars that need custom colors (Prior = gray, Total = blue)
    # The Prior bar (index 0) is "absolute" which Plotly colors as a total by default
    # We overlay a gray rectangle to make it visually distinct
    bar_width = 0.35
    override_indices = [0]  # Prior needs gray override (Plotly treats absolute as total color)
    for idx in override_indices:
        fig.add_shape(
            type="rect",
            fillcolor=bar_colors[idx],
            line=dict(color=bar_colors[idx], width=1),
            opacity=1,
            x0=idx - bar_width,
            x1=idx + bar_width,
            xref="x",
            y0=bases[idx],
            y1=tops[idx],
            yref="y",
            layer="above",
        )

    # Gate threshold line
    fig.add_hline(
        y=gate_threshold,
        line=dict(color=GOLD_ACCENT, width=1.5, dash="dash"),
        annotation=dict(
            text=f"GATE {gate_threshold}%",
            font=dict(family=FONT_MONO, size=11, color=GOLD_ACCENT),
            bgcolor="rgba(245,166,35,0.08)",
            bordercolor=GOLD_ACCENT,
            borderwidth=1,
            borderpad=4,
        ),
        annotation_position="top right",
    )

    # Layout
    y_max = max(posterior + 20, gate_threshold + 10, 100)
    fig.update_layout(
        title=dict(
            text="BAYESIAN PROBABILITY CASCADE",
            font=dict(family=FONT_MONO, size=16, color=TEXT_PRIMARY),
            x=0.5,
            xanchor="center",
        ),
        paper_bgcolor=BG_PRIMARY,
        plot_bgcolor=BG_PRIMARY,
        font=dict(family=FONT_MONO, color=TEXT_SECONDARY, size=11),
        xaxis=dict(
            tickfont=dict(family=FONT_MONO, size=10, color=TEXT_SECONDARY),
            gridcolor="rgba(100,116,139,0.08)",
            linecolor="rgba(100,116,139,0.15)",
            tickangle=0,
        ),
        yaxis=dict(
            title=dict(
                text="P(win) %",
                font=dict(family=FONT_MONO, size=12, color=TEXT_SECONDARY),
            ),
            tickfont=dict(family=FONT_MONO, size=11, color=TEXT_SECONDARY),
            gridcolor="rgba(100,116,139,0.06)",
            linecolor="rgba(100,116,139,0.15)",
            zeroline=True,
            zerolinecolor="rgba(100,116,139,0.1)",
            range=[0, y_max],
            ticksuffix="%",
        ),
        showlegend=False,
        margin=dict(l=60, r=40, t=60, b=100),
        height=520,
        waterfallgap=0.3,
    )

    return fig


def _render_gate_status(st_module, data: dict):
    """Render the gate status indicator and summary text."""
    posterior = _safe_get(data, "posterior", 41.6)
    gate_threshold = _safe_get(data, "gate_threshold", GATE_THRESHOLD)
    chaos = _safe_get(data, "chaos_penalty", 0.0)
    gate_open = posterior >= gate_threshold
    gap = round(gate_threshold - posterior, 1)

    # IRON LAW: Gene Silencing overrides gate_open
    gene_silencing_active = chaos >= 0.7
    if gene_silencing_active:
        gate_open = False

    if gate_open:
        kelly = _safe_get(data, "kelly_fraction", 0.0)
        gate_color = GREEN_POSITIVE
        gate_icon_html = "&#x1F513;"
        gate_text = "GATE OPEN"
        kelly_pct = kelly * 100 if kelly > 0 else 40
        gate_text_he = (
            f"\u05d4\u05e9\u05e2\u05e8 \u05e0\u05e4\u05ea\u05d7! "
            f"{posterior:.1f}% \u2014 "
            f"\u05e7\u05e8\u05d9\u05d8\u05e8\u05d9\u05d5\u05df \u05e7\u05dc\u05d9 \u05de\u05d0\u05e9\u05e8. "
            f"\u05db\u05e0\u05d9\u05e1\u05d4 \u05d8\u05e7\u05d8\u05d9\u05ea {kelly_pct:.0f}%."
        )
        border_glow = GREEN_GLOW
    else:
        gate_color = RED_NEGATIVE
        gate_icon_html = "&#x1F512;"
        gate_text = "GATE LOCKED"
        gate_text_he = (
            f"\u05d4\u05e9\u05e2\u05e8 \u05e0\u05e2\u05d5\u05dc \u2014 "
            f"{posterior:.1f}% \u05de\u05ea\u05d5\u05da {gate_threshold}% \u05e0\u05d3\u05e8\u05e9\u05d9\u05dd. "
            f"\u05d7\u05e1\u05e8\u05d9\u05dd {gap:.1f}pp. "
            f"\u05d4\u05de\u05e9\u05da DCA 60%."
        )
        border_glow = RED_GLOW

    # Progress bar percentage
    progress_pct = min(100.0, max(0.0, (posterior / gate_threshold) * 100.0))

    st_module.markdown(f"""
    <div style="
        background: {BG_CARD};
        border: 1px solid {gate_color};
        border-radius: 6px;
        padding: 20px 28px;
        margin: 8px 0 20px 0;
        box-shadow: 0 0 24px {border_glow};
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <div style="
                font-family: {FONT_MONO};
                font-size: 24px;
                font-weight: 700;
                color: {gate_color};
                letter-spacing: 3px;
            ">
                {gate_icon_html} {gate_text}
            </div>
            <div style="
                font-family: {FONT_MONO};
                font-size: 32px;
                font-weight: 700;
                color: {gate_color};
            ">
                {posterior:.1f}%
            </div>
        </div>
        <div style="
            background: {BG_PRIMARY};
            border-radius: 3px;
            height: 8px;
            margin-bottom: 14px;
            overflow: hidden;
        ">
            <div style="
                width: {progress_pct:.1f}%;
                height: 100%;
                background: linear-gradient(90deg, {gate_color}, {gate_color}88);
                border-radius: 3px;
                transition: width 0.5s ease;
            "></div>
        </div>
        <div style="
            display: flex;
            justify-content: space-between;
            font-family: {FONT_MONO};
            font-size: 11px;
            color: {TEXT_MUTED};
            margin-bottom: 14px;
        ">
            <span>P(win) = {posterior:.1f}%</span>
            <span>Threshold = {gate_threshold}%</span>
            <span>Gap = {gap:.1f}pp</span>
        </div>
        <div style="
            font-family: {FONT_MONO};
            font-size: 14px;
            color: {TEXT_PRIMARY};
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            padding: 10px 14px;
            background: {BG_PRIMARY};
            border-radius: 4px;
            border-right: 3px solid {gate_color};
        ">
            {gate_text_he}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_metrics_strip(st_module, data: dict):
    """Render a compact metrics strip above the waterfall."""
    regime = _safe_get(data, "regime", "Unknown")
    regime_he = REGIME_MAP.get(regime, regime)
    btc_price = _safe_get(data, "btc_price", 0.0)
    fear_greed = _safe_get(data, "fear_greed", 50)
    fg_label = _safe_get(data, "fg_label", "Neutral")
    chaos = _safe_get(data, "chaos_penalty", 0.0)
    diffusion = _safe_get(data, "diffusion_score", 0.0)

    regime_colors = {
        "Blood_in_streets": RED_NEGATIVE,
        "Normal": AMBER_WARN,
        "Distribution_top": "#a855f7",
    }
    regime_color = regime_colors.get(regime, TEXT_SECONDARY)

    if fear_greed <= 25:
        fg_color = RED_NEGATIVE
    elif fear_greed <= 45:
        fg_color = "#ff8c42"
    elif fear_greed <= 55:
        fg_color = AMBER_WARN
    elif fear_greed <= 75:
        fg_color = GREEN_POSITIVE
    else:
        fg_color = "#22c55e"

    def _metric_card(label, value, color):
        return (
            f'<div style="flex:1;min-width:130px;background:{BG_CARD};'
            f'border:1px solid rgba(100,116,139,0.12);'
            f'border-bottom:2px solid {color}33;'
            f'border-radius:4px;padding:10px 14px;text-align:center;">'
            f'<div style="font-family:{FONT_MONO};font-size:9px;color:{TEXT_MUTED};'
            f'text-transform:uppercase;letter-spacing:1.5px;">{label}</div>'
            f'<div style="font-family:{FONT_MONO};font-size:14px;color:{color};'
            f'font-weight:600;margin-top:5px;">{value}</div></div>'
        )

    cards = "".join([
        _metric_card("REGIME", regime_he, regime_color),
        _metric_card("BTC", f"${btc_price:,.0f}", TEXT_PRIMARY),
        _metric_card("FEAR & GREED", f"{fear_greed}/100", fg_color),
        _metric_card("DIFFUSION", f"{diffusion:.0f}/100", GREEN_POSITIVE if diffusion >= 60 else TEXT_SECONDARY),
        _metric_card("CHAOS", f"{chaos:.2f}", RED_NEGATIVE if chaos >= 0.5 else AMBER_WARN if chaos >= 0.3 else GREEN_POSITIVE),
    ])

    html = f'<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">{cards}</div>'
    st_module.markdown(html, unsafe_allow_html=True)


def _generate_commanders_brief(data: dict) -> str:
    """
    Generate a Commander's Brief using Gemini AI.
    Falls back to a template-based brief if API is unavailable.
    """
    regime = _safe_get(data, "regime", "Unknown")
    regime_he = REGIME_MAP.get(regime, regime)
    posterior = _safe_get(data, "posterior", 0.0)
    prior = _safe_get(data, "prior", 55.0)
    diffusion = _safe_get(data, "diffusion_score", 0.0)
    fear_greed = _safe_get(data, "fear_greed", 50)
    fg_label = _safe_get(data, "fg_label", "Neutral")
    chaos = _safe_get(data, "chaos_penalty", 0.0)
    nlp_sentiment = _safe_get(data, "nlp_sentiment", 0.0)
    misdirection = _safe_get(data, "misdirection", 0.0)
    book_imbalance = _safe_get(data, "book_imbalance", 0.0)
    btc_price = _safe_get(data, "btc_price", 0.0)
    kelly = _safe_get(data, "kelly_fraction", 0.0)
    gate_threshold = _safe_get(data, "gate_threshold", GATE_THRESHOLD)
    gate_open = posterior >= gate_threshold
    gap = round(gate_threshold - posterior, 1)

    # =====================================================================
    # IRON LAW: Violence/Chaos > 3.5 (normalized > 0.7) = ABSOLUTE VETO
    # Gene Silencing overrides EVERYTHING -- even if Posterior shows 100%.
    # This prevents the fatal contradiction: "Gene Silencing active" +
    # "Kelly approves entry" can NEVER coexist.
    # =====================================================================
    gene_silencing_active = chaos >= 0.7  # violence_score / 5.0 >= 0.7 => violence >= 3.5
    if gene_silencing_active:
        gate_open = False  # Force gate closed
        kelly = 0.0        # Force Kelly to zero
        gap = round(gate_threshold - posterior, 1)

    prompt = f"""You are EliteV20_CRO, the Chief Risk Officer of an institutional algorithmic crypto fund.
Write a Commander's Brief (military intelligence style) in Hebrew.

CRITICAL RULES:
- Write ENTIRELY in Hebrew, but keep quant terms in English (DCA, P10, Bayesian, GARCH, Vol Cone, NLP, Kelly, Posterior, Prior, Diffusion, Fear & Greed)
- Address the reader as "מפעיל" (Operator)
- Be concise, clinical, professional -- zero emotion
- Do NOT use emoji in the text
- Structure: situation assessment, whale activity, fear analysis, waterfall result, action directive, watch triggers
- IRON LAW: If Gene Silencing is active (Chaos >= 0.7 / Violence >= 3.5), Kelly MUST be 0.0% and action MUST be HOLD. You CANNOT approve entry (BUY) under chaos conditions, even if Posterior shows 100%. The math of violence overrides everything.

CURRENT SYSTEM DATA:
- Regime: {regime} ({regime_he})
- BTC Price: ${btc_price:,.0f}
- Prior Probability: {prior:.1f}%
- Diffusion Score (whale activity): {diffusion:.0f}/100
- Fear & Greed Index: {fear_greed}/100 ({fg_label})
- Order Book Imbalance: {book_imbalance:+.2f}
- Chaos Penalty: {chaos:.2f}
- Gene Silencing: {"ACTIVE -- ABSOLUTE VETO" if gene_silencing_active else "Inactive"}
- NLP Sentiment: {nlp_sentiment:+.2f}
- Misdirection Signal: {misdirection:.2f}
- Final Posterior: {posterior:.1f}%
- Gate Threshold: {gate_threshold}%
- Gate Status: {"LOCKED (Gene Silencing VETO)" if gene_silencing_active else ("OPEN" if gate_open else "LOCKED")}
- Gap to Gate: {gap:.1f}pp
- Kelly Fraction: {kelly:.2f}

Write the brief now. Keep it 6-10 sentences. Professional military intelligence tone in Hebrew."""

    # Try Gemini API key from Streamlit secrets or env
    api_key = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", None)

    # Also try OpenAI-compatible endpoint as fallback
    openai_key = os.environ.get("OPENAI_API_KEY", None)

    # Attempt 1: google.generativeai
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            pass

    # Attempt 2: OpenAI-compatible (pre-configured base_url)
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are EliteV20_CRO, a military-style quantitative risk officer. Respond only in Hebrew with English quant terms."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception:
            pass

    # Fallback: template
    return _template_brief(data)


def _template_brief(data: dict) -> str:
    """Generate a template-based Commander's Brief when AI is unavailable."""
    regime = _safe_get(data, "regime", "Unknown")
    regime_he = REGIME_MAP.get(regime, regime)
    posterior = _safe_get(data, "posterior", 0.0)
    diffusion = _safe_get(data, "diffusion_score", 0.0)
    fear_greed = _safe_get(data, "fear_greed", 50)
    chaos = _safe_get(data, "chaos_penalty", 0.0)
    btc_price = _safe_get(data, "btc_price", 0.0)
    gate_threshold = _safe_get(data, "gate_threshold", GATE_THRESHOLD)
    gate_open = posterior >= gate_threshold
    gap = round(gate_threshold - posterior, 1)
    book_imbalance = _safe_get(data, "book_imbalance", 0.0)

    # IRON LAW: Gene Silencing overrides gate_open
    gene_silencing_active = chaos >= 0.7
    if gene_silencing_active:
        gate_open = False

    if diffusion >= 75:
        whale_text = (
            f"\u05e8\u05d3\u05d0\u05e8 \u05d4\u05d3\u05d9\u05e4\u05d5\u05d6\u05d9\u05d4 "
            f"\u05de\u05d6\u05d4\u05d4 \u05e6\u05d9\u05d5\u05df {diffusion:.0f}/100 "
            f"-- \u05dc\u05d5\u05d5\u05d9\u05d9\u05ea\u05e0\u05d9\u05dd \u05d1\u05d5\u05dc\u05e2\u05d9\u05dd "
            f"\u05d4\u05d9\u05e6\u05e2 \u05d1\u05e9\u05e7\u05d8. "
            f"\u05d6\u05d4\u05d5 \u05e1\u05d9\u05d2\u05e0\u05dc \u05d7\u05d9\u05d5\u05d1\u05d9."
        )
    elif diffusion >= 50:
        whale_text = (
            f"\u05e6\u05d9\u05d5\u05df \u05d3\u05d9\u05e4\u05d5\u05d6\u05d9\u05d4 {diffusion:.0f}/100 "
            f"-- \u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u05dc\u05d5\u05d5\u05d9\u05d9\u05ea\u05e0\u05d9\u05dd "
            f"\u05de\u05ea\u05d5\u05e0\u05d4. \u05d0\u05d9\u05df \u05d0\u05d5\u05ea "
            f"\u05d7\u05d3-\u05de\u05e9\u05de\u05e2\u05d9."
        )
    else:
        whale_text = (
            f"\u05e6\u05d9\u05d5\u05df \u05d3\u05d9\u05e4\u05d5\u05d6\u05d9\u05d4 {diffusion:.0f}/100 "
            f"-- \u05dc\u05d5\u05d5\u05d9\u05d9\u05ea\u05e0\u05d9\u05dd \u05dc\u05d0 \u05e4\u05e2\u05d9\u05dc\u05d9\u05dd. "
            f"\u05d0\u05d9\u05df \u05e6\u05d1\u05d9\u05e8\u05d4 \u05de\u05e9\u05de\u05e2\u05d5\u05ea\u05d9\u05ea."
        )

    if fear_greed <= 20:
        fear_text = (
            f"\u05e4\u05d7\u05d3 \u05e7\u05d9\u05e6\u05d5\u05e0\u05d9 ({fear_greed}/100). "
            f"\u05de\u05d1\u05d7\u05d9\u05e0\u05d4 \u05e7\u05d5\u05e0\u05d8\u05e8\u05e8\u05d9\u05d0\u05e0\u05d9\u05ea "
            f"-- \u05d6\u05d4\u05d5 \u05d0\u05d5\u05ea \u05d7\u05d9\u05d5\u05d1\u05d9. "
            f"\u05d4\u05e9\u05d5\u05e7 \u05d1\u05e4\u05e0\u05d9\u05e7\u05d4."
        )
    elif fear_greed <= 40:
        fear_text = (
            f"\u05e4\u05d7\u05d3 ({fear_greed}/100). "
            f"\u05e1\u05e0\u05d8\u05d9\u05de\u05e0\u05d8 \u05e9\u05dc\u05d9\u05dc\u05d9 "
            f"\u05d0\u05da \u05dc\u05d0 \u05e7\u05d9\u05e6\u05d5\u05e0\u05d9."
        )
    elif fear_greed <= 60:
        fear_text = (
            f"\u05e0\u05d9\u05d8\u05e8\u05dc\u05d9 ({fear_greed}/100). "
            f"\u05d0\u05d9\u05df \u05e1\u05d9\u05d2\u05e0\u05dc \u05de\u05d5\u05d1\u05d4\u05e7 "
            f"\u05de\u05d4\u05e1\u05e0\u05d8\u05d9\u05de\u05e0\u05d8."
        )
    elif fear_greed <= 80:
        fear_text = (
            f"\u05d7\u05de\u05d3\u05e0\u05d5\u05ea ({fear_greed}/100). "
            f"\u05e1\u05d9\u05de\u05df \u05d0\u05d6\u05d4\u05e8\u05d4 -- "
            f"\u05d4\u05e9\u05d5\u05e7 \u05d0\u05d5\u05e4\u05d8\u05d9\u05de\u05d9 \u05de\u05d3\u05d9."
        )
    else:
        fear_text = (
            f"\u05d7\u05de\u05d3\u05e0\u05d5\u05ea \u05e7\u05d9\u05e6\u05d5\u05e0\u05d9\u05ea ({fear_greed}/100). "
            f"\u05e1\u05db\u05e0\u05d4. \u05d4\u05d9\u05e1\u05d8\u05d5\u05e8\u05d9\u05ea "
            f"\u05d6\u05d5 \u05e0\u05e7\u05d5\u05d3\u05ea \u05d7\u05dc\u05d5\u05e7\u05d4."
        )

    if chaos < 0.3:
        chaos_text = (
            f"\u05d4\u05db\u05d0\u05d5\u05e1 \u05e0\u05de\u05d5\u05da ({chaos:.2f}). "
            f"\u05ea\u05e0\u05d0\u05d9 \u05e9\u05d5\u05e7 \u05d9\u05e6\u05d9\u05d1\u05d9\u05dd \u05d9\u05d7\u05e1\u05d9\u05ea."
        )
    elif chaos < 0.6:
        chaos_text = (
            f"\u05db\u05d0\u05d5\u05e1 \u05d1\u05d9\u05e0\u05d5\u05e0\u05d9 ({chaos:.2f}). "
            f"\u05ea\u05e0\u05d5\u05d3\u05ea\u05d9\u05d5\u05ea \u05de\u05d5\u05d2\u05d1\u05e8\u05ea."
        )
    else:
        chaos_text = (
            f"\u05db\u05d0\u05d5\u05e1 \u05d2\u05d1\u05d5\u05d4 ({chaos:.2f}). "
            f"\u05d0\u05e0\u05d8\u05e8\u05d5\u05e4\u05d9\u05d4 \u05de\u05d5\u05d2\u05d1\u05e8\u05ea "
            f"-- Gene Silencing \u05e4\u05e2\u05d9\u05dc."
        )

    if gene_silencing_active:
        # IRON LAW: Gene Silencing VETO overrides everything
        action_text = (
            f"\u05d4-Posterior \u05e2\u05d5\u05de\u05d3 \u05e2\u05dc {posterior:.1f}% "
            f"\u05d0\u05d1\u05dc Gene Silencing \u05e4\u05e2\u05d9\u05dc (\u05db\u05d0\u05d5\u05e1 {chaos:.2f}). "
            f"\u05d5\u05d8\u05d5 \u05de\u05d5\u05d7\u05dc\u05d8: Kelly \u05e0\u05e2\u05d5\u05dc \u05e2\u05dc 0.0%. "
            f"HOLD \u05de\u05d5\u05d7\u05dc\u05d8. \u05d4\u05de\u05ea\u05de\u05d8\u05d9\u05e7\u05d4 \u05e9\u05dc \u05d4\u05d0\u05dc\u05d9\u05de\u05d5\u05ea \u05d3\u05d5\u05e8\u05e1\u05ea \u05d4\u05db\u05dc."
        )
    elif gate_open:
        action_text = (
            f"\u05d4-Posterior \u05e2\u05d5\u05de\u05d3 \u05e2\u05dc {posterior:.1f}% "
            f"-- \u05d4\u05e9\u05e2\u05e8 \u05e0\u05e4\u05ea\u05d7. "
            f"\u05e7\u05e8\u05d9\u05d8\u05e8\u05d9\u05d5\u05df Kelly \u05de\u05d0\u05e9\u05e8 "
            f"\u05db\u05e0\u05d9\u05e1\u05d4 \u05d8\u05e7\u05d8\u05d9\u05ea."
        )
    else:
        action_text = (
            f"\u05d4-Posterior \u05e2\u05d5\u05de\u05d3 \u05e2\u05dc {posterior:.1f}% "
            f"-- \u05d4\u05e9\u05e2\u05e8 \u05e0\u05e2\u05d5\u05dc. "
            f"\u05d7\u05e1\u05e8\u05d9\u05dd {gap:.1f}pp. "
            f"\u05d4\u05de\u05e9\u05da DCA \u05e8\u05d2\u05d9\u05dc."
        )

    if posterior < 60:
        watch_text = (
            "\u05e0\u05e7\u05d5\u05d3\u05ea \u05de\u05e2\u05e7\u05d1: "
            "\u05d0\u05dd Posterior \u05e2\u05d5\u05dc\u05d4 \u05de\u05e2\u05dc 60% "
            "-- \u05d4\u05ea\u05db\u05d5\u05e0\u05df \u05dc\u05e9\u05d9\u05e0\u05d5\u05d9 \u05e1\u05d8\u05d8\u05d5\u05e1."
        )
    elif posterior < gate_threshold:
        watch_text = (
            f"\u05e0\u05e7\u05d5\u05d3\u05ea \u05de\u05e2\u05e7\u05d1: "
            f"\u05d7\u05e1\u05e8\u05d9\u05dd {gap:.1f}pp \u05d1\u05dc\u05d1\u05d3. "
            f"\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8\u05d9 \u05e9\u05d9\u05e0\u05d5\u05d9\u05d9 "
            f"Diffusion \u05d5-Fear & Greed."
        )
    else:
        watch_text = (
            "\u05e0\u05e7\u05d5\u05d3\u05ea \u05de\u05e2\u05e7\u05d1: "
            "\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8\u05d9 \u05d9\u05e8\u05d9\u05d3\u05d4 "
            "\u05d1-Posterior \u05de\u05ea\u05d7\u05ea \u05dc-Threshold. "
            "\u05e9\u05de\u05d5\u05e8 \u05e2\u05dc \u05de\u05e9\u05de\u05e2\u05ea."
        )

    brief = (
        f"\u05de\u05e4\u05e2\u05d9\u05dc, \u05d0\u05e0\u05d7\u05e0\u05d5 "
        f"\u05d1\u05e8\u05d2\u05f3\u05d9\u05dd \u05e9\u05dc {regime_he}. "
        f"\u05de\u05d7\u05d9\u05e8 BTC: ${btc_price:,.0f}.\n\n"
        f"{whale_text}\n\n"
        f"{fear_text}\n\n"
        f"{chaos_text}\n\n"
        f"\u05e1\u05e4\u05e8 \u05d4\u05e4\u05e7\u05d5\u05d3\u05d5\u05ea "
        f"\u05de\u05e8\u05d0\u05d4 Imbalance \u05e9\u05dc {book_imbalance:+.2f}.\n\n"
        f"{action_text}\n\n"
        f"{watch_text}\n\n"
        f"-- EliteV20_CRO, \u05e1\u05d5\u05e3 \u05ea\u05d3\u05e8\u05d5\u05da."
    )

    return brief


def _render_commanders_brief_section(st_module, data: dict):
    """Render the Commander's Brief button and output section."""

    st_module.markdown(f"""
    <div style="
        border-top: 1px solid rgba(100,116,139,0.12);
        margin-top: 28px;
        padding-top: 20px;
    ">
        <div style="
            font-family: {FONT_MONO};
            font-size: 12px;
            color: {TEXT_MUTED};
            letter-spacing: 2.5px;
            text-transform: uppercase;
            margin-bottom: 14px;
        ">
            COMMANDER'S BRIEF // CLASSIFIED
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st_module.button("\u05ea\u05d3\u05e8\u05d5\u05da \u05de\u05e4\u05e7\u05d3", key="commanders_brief_btn", type="primary"):
        with st_module.spinner("\u05de\u05d9\u05d9\u05e6\u05e8 \u05ea\u05d3\u05e8\u05d5\u05da \u05de\u05e4\u05e7\u05d3..."):
            brief_text = _generate_commanders_brief(data)
            st_module.session_state["commanders_brief"] = brief_text

    if "commanders_brief" in st_module.session_state and st_module.session_state["commanders_brief"]:
        brief = st_module.session_state["commanders_brief"]
        posterior = _safe_get(data, "posterior", 0.0)
        gate_threshold = _safe_get(data, "gate_threshold", GATE_THRESHOLD)
        gate_open = posterior >= gate_threshold
        accent = GREEN_POSITIVE if gate_open else AMBER_WARN
        regime_he = REGIME_MAP.get(_safe_get(data, "regime", "Unknown"), "")

        st_module.markdown(f"""
        <div style="
            background: {BG_CARD};
            border: 1px solid rgba(100,116,139,0.15);
            border-right: 4px solid {accent};
            border-radius: 4px;
            padding: 22px 26px;
            margin-top: 14px;
        ">
            <div style="
                font-family: {FONT_MONO};
                font-size: 9px;
                color: {TEXT_MUTED};
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 14px;
            ">
                CLASSIFIED // ELITE V20 // CRO BRIEF // {regime_he}
            </div>
            <div style="
                font-family: {FONT_MONO};
                font-size: 13px;
                color: {TEXT_PRIMARY};
                line-height: 2.0;
                white-space: pre-wrap;
                direction: rtl;
                text-align: right;
            ">{brief}</div>
            <div style="
                font-family: {FONT_MONO};
                font-size: 9px;
                color: {TEXT_MUTED};
                margin-top: 18px;
                letter-spacing: 1.5px;
            ">
                END TRANSMISSION
            </div>
        </div>
        """, unsafe_allow_html=True)




# ===========================================================================
# PUBLIC API
# ===========================================================================

def render_bayesian_waterfall(st_module, elite_data: dict = None):
    """
    Render the full Bayesian Waterfall module.

    Parameters
    ----------
    st_module : streamlit
        The Streamlit module (import streamlit as st; pass st).
    elite_data : dict, optional
        Dictionary containing all Elite v20 metrics.
        Falls back to DEFAULT_ELITE_DATA if not provided.
    """
    data = dict(DEFAULT_ELITE_DATA)
    if elite_data:
        data.update({k: v for k, v in elite_data.items() if v is not None})

    # Section Header
    st_module.markdown(f"""
    <div style="
        font-family: {FONT_MONO};
        font-size: 10px;
        color: {TEXT_MUTED};
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 2px;
    ">
        MEDALLION // ELITE V20 // BAYESIAN ENGINE
    </div>
    <div style="
        font-family: {FONT_MONO};
        font-size: 20px;
        color: {TEXT_PRIMARY};
        font-weight: 600;
        margin-bottom: 18px;
        direction: rtl;
    ">
        \u05de\u05e4\u05dc \u05d4\u05d4\u05e1\u05ea\u05d1\u05e8\u05d5\u05d9\u05d5\u05ea \u05d4\u05d1\u05d9\u05d9\u05e1\u05d9\u05d0\u05e0\u05d9
    </div>
    """, unsafe_allow_html=True)

    # Metrics Strip
    _render_metrics_strip(st_module, data)

    # Waterfall Chart
    fig = _build_waterfall_figure(data)
    st_module.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": False,
        "staticPlot": False,
    })

    # Gate Status
    _render_gate_status(st_module, data)

    # Commander's Brief
    _render_commanders_brief_section(st_module, data)


# ===========================================================================
# STANDALONE MODE
# ===========================================================================

def _standalone_app():
    """Run the module as a standalone Streamlit app for testing."""
    st.set_page_config(
        page_title="MEDALLION | Bayesian Waterfall",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Global dark theme CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {BG_PRIMARY};
        }}
        .main .block-container {{
            background-color: {BG_PRIMARY};
            padding-top: 2rem;
            max-width: 1100px;
        }}
        header[data-testid="stHeader"] {{
            background-color: {BG_PRIMARY};
            border-bottom: 1px solid rgba(100,116,139,0.08);
        }}
        footer {{ visibility: hidden; }}
        [data-testid="stSidebar"] {{
            background-color: {BG_SECONDARY};
        }}
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stNumberInput label {{
            font-family: {FONT_MONO};
            font-size: 11px;
            color: {TEXT_SECONDARY};
        }}
        .stButton > button {{
            background-color: {BG_CARD};
            color: {TEXT_PRIMARY};
            border: 1px solid rgba(100,116,139,0.25);
            font-family: {FONT_MONO};
            font-size: 14px;
            letter-spacing: 1px;
            padding: 10px 28px;
            border-radius: 4px;
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background-color: rgba(59,130,246,0.12);
            border-color: {BLUE_TOTAL};
            color: {BLUE_TOTAL};
        }}
        .stButton > button[kind="primary"],
        .stButton > button:first-child {{
            background-color: rgba(59,130,246,0.08);
            border-color: {BLUE_TOTAL};
            color: {BLUE_TOTAL};
        }}
    </style>
    """, unsafe_allow_html=True)

    # Sidebar: Parameter Controls
    with st.sidebar:
        st.markdown(f"""
        <div style="
            font-family: {FONT_MONO};
            font-size: 11px;
            color: {TEXT_MUTED};
            letter-spacing: 2px;
            margin-bottom: 16px;
        ">
            PARAMETER CONTROLS
        </div>
        """, unsafe_allow_html=True)

        prior = st.slider("Prior (%)", 30.0, 70.0, 55.0, 0.5)
        diffusion = st.slider("Diffusion Score", 0.0, 100.0, 85.0, 1.0)
        fear_greed = st.slider("Fear & Greed Index", 0, 100, 10, 1)

        fg_labels = {
            (0, 20): "Extreme Fear",
            (21, 40): "Fear",
            (41, 60): "Neutral",
            (61, 80): "Greed",
            (81, 100): "Extreme Greed",
        }
        fg_label = "Neutral"
        for (lo, hi), label in fg_labels.items():
            if lo <= fear_greed <= hi:
                fg_label = label
                break

        book_imbalance = st.slider("Book Imbalance", -1.0, 1.0, 0.12, 0.01)
        chaos_penalty = st.slider("Chaos Penalty", 0.0, 1.0, 0.32, 0.01)
        nlp_sentiment = st.slider("NLP Sentiment", -1.0, 1.0, -0.15, 0.01)
        misdirection = st.slider("Misdirection Signal", 0.0, 1.0, 0.08, 0.01)
        btc_price = st.number_input("BTC Price ($)", value=58420.0, step=100.0)
        regime = st.selectbox("Regime", ["Blood_in_streets", "Normal", "Distribution_top"], index=0)

        # Compute posterior from inputs
        diff_d = max(0.0, (diffusion - 50.0) / 50.0 * 15.0)
        if fear_greed <= 25:
            fg_d = (25 - fear_greed) / 25.0 * 10.0
        elif fear_greed >= 75:
            fg_d = -((fear_greed - 75) / 25.0 * 10.0)
        else:
            fg_d = 0.0
        book_d = book_imbalance * 8.0
        chaos_d = -abs(chaos_penalty) * 20.0
        nlp_d = nlp_sentiment * 10.0 if nlp_sentiment < 0 else nlp_sentiment * 5.0
        mis_d = max(0.0, misdirection) * 8.0
        computed_posterior = prior + diff_d + fg_d + book_d + chaos_d + nlp_d + mis_d
        computed_posterior = max(0.0, min(100.0, round(computed_posterior, 1)))

        posterior_override = st.slider(
            "Posterior Override",
            0.0, 100.0,
            computed_posterior,
            0.1,
        )

        kelly_f = 0.4 if posterior_override >= GATE_THRESHOLD else 0.0

        st.markdown(f"""
        <div style="
            font-family: {FONT_MONO};
            font-size: 10px;
            color: {TEXT_MUTED};
            margin-top: 20px;
            letter-spacing: 1px;
        ">
            COMPUTED: {computed_posterior:.1f}%<br>
            OVERRIDE: {posterior_override:.1f}%
        </div>
        """, unsafe_allow_html=True)

    # Build elite_data
    test_data = {
        "posterior": posterior_override,
        "prior": prior,
        "diffusion_score": diffusion,
        "fear_greed": fear_greed,
        "fg_label": fg_label,
        "book_imbalance": book_imbalance,
        "chaos_penalty": chaos_penalty,
        "nlp_sentiment": nlp_sentiment,
        "misdirection": misdirection,
        "regime": regime,
        "kelly_fraction": kelly_f,
        "btc_price": btc_price,
        "elite_score": posterior_override,
        "gate_threshold": GATE_THRESHOLD,
    }

    render_bayesian_waterfall(st, test_data)


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    _standalone_app()
