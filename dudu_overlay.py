# dudu_overlay.py
# DUDU Overlay V0: Vol Cone + Regime Paths (bootstrap from similar regimes)
# + Spectral Divergence Engine (Classical FFT — Medallion Brain)
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
# SPECTRAL DIVERGENCE ENGINE
# ============================================================================
# The FFT input MUST be the divergence signal — the gap between price action
# and on-chain/whale fundamentals (diffusion score). Running FFT on raw close
# prices gives retail frequency noise; running it on the divergence gap
# extracts whale-cycle resonance frequencies. (The Spectral Rule)

def compute_divergence_eigenvalue(divergence_series) -> dict:
    """
    Classical Spectral Decomposition of the Whale-Gap Divergence signal.
    
    Input: divergence_series — the gap between price and on-chain score.
           Can be a list, np.ndarray, or pd.Series.
           Typically: (close - close.rolling(N).mean()) * (diffusion_score/100)
           or simply the raw diffusion_score series over time.
    
    Returns: {eigenvalue, dominant_freq, amplitude, tension, fft_power}
    
    Eigenvalue maps to a drift multiplier for DUDU cone:
      1.00 = neutral (no spectral pressure)
      1.10 = MEDIUM tension (moderate whale cycle detected)  
      1.25 = HIGH tension (strong resonance — tighten P10 floor)
    """
    try:
        from scipy.fft import fft as scipy_fft
        _fft = scipy_fft
    except ImportError:
        _fft = np.fft.fft  # fallback to numpy FFT

    # Coerce input
    if isinstance(divergence_series, pd.Series):
        signal = divergence_series.dropna().astype(float).values
    elif isinstance(divergence_series, (list, tuple)):
        signal = np.array(divergence_series, dtype=float)
        signal = signal[np.isfinite(signal)]
    else:
        signal = np.asarray(divergence_series, dtype=float)
        signal = signal[np.isfinite(signal)]

    # Not enough data → neutral eigenvalue
    if len(signal) < 8:
        return {
            "eigenvalue": 1.0,
            "dominant_freq": 0,
            "amplitude": 0.0,
            "tension": "LOW",
            "fft_power": [],
        }

    # Normalize: zero-mean, unit-range (avoids DC bias dominating FFT)
    rng = np.ptp(signal)
    if rng > 1e-10:
        signal = (signal - signal.mean()) / (rng / 2.0)
    else:
        # Flat signal → no resonance
        return {
            "eigenvalue": 1.0,
            "dominant_freq": 0,
            "amplitude": 0.0,
            "tension": "LOW",
            "fft_power": [],
        }

    # FFT — only positive frequencies (one-sided spectrum)
    freqs = _fft(signal)
    n = len(freqs)
    power = np.abs(freqs[: n // 2])

    # Skip DC component (index 0 = constant offset, not a cycle)
    power_ac = power[1:]
    dominant_idx = int(np.argmax(power_ac)) + 1  # +1 to restore absolute index
    dominant_amplitude = float(power_ac[dominant_idx - 1] / len(signal))

    # Map amplitude → eigenvalue (1.0 to 1.25 range)
    eigenvalue = float(np.clip(1.0 + dominant_amplitude * 0.5, 1.0, 1.25))

    # Tension tier
    if dominant_amplitude > 0.4:
        tension = "HIGH"
    elif dominant_amplitude > 0.2:
        tension = "MEDIUM"
    else:
        tension = "LOW"

    return {
        "eigenvalue": round(eigenvalue, 4),
        "dominant_freq": dominant_idx,
        "amplitude": round(dominant_amplitude, 4),
        "tension": tension,
        "fft_power": power_ac.tolist(),  # full power spectrum for charting
    }


def apply_spectral_boost(cone_result: dict, eigenvalue: float) -> dict:
    """
    Injects the Spectral Eigenvalue into the DUDU vol cone result.
    
    Tightens (boosts) the P10 floor: a higher eigenvalue means stronger
    whale-cycle support, so the downside floor rises.
    
    cone_result: output dict from build_vol_cone()
    eigenvalue:  float from compute_divergence_eigenvalue() — 1.0 to 1.25
    
    Returns: augmented cone_result with 'spectral_p10_boost' and 
             'eigenvalue' keys added.
    """
    if not cone_result or "last" not in cone_result:
        return cone_result

    last = cone_result["last"]
    bands = cone_result.get("bands", {})

    # Boost P10 (1σ lower band at horizon): floor rises by eigenvalue factor
    boosted_bands = {}
    for s, (dn, up) in bands.items():
        # Upper band unchanged; lower band raised by spectral pressure
        boosted_dn = dn * eigenvalue  # eigenvalue ≥ 1.0 → floor rises
        boosted_up = up               # upside unchanged
        boosted_bands[s] = (boosted_dn, boosted_up)

    # Concrete P10 floor at the end of the horizon
    if 1 in boosted_bands:
        p10_floor_boosted = float(boosted_bands[1][0][-1])
    else:
        p10_floor_boosted = None

    return {
        **cone_result,
        "bands": boosted_bands,
        "eigenvalue": eigenvalue,
        "p10_floor_boosted": p10_floor_boosted,
        "spectral_boost_applied": True,
    }


# ─── helper to build divergence series from OHLCV + diffusion score ──────────
def build_divergence_series(close: pd.Series, diffusion_score: float,
                             window: int = 20) -> pd.Series:
    """
    Constructs the whale-gap divergence series from price data and the
    current on-chain diffusion score.
    
    Formula: divergence = z-score(close, window) * (diffusion_score / 100)
    
    - z-score(close): normalised price deviation from recent mean
    - diffusion_score factor: scales signal by on-chain conviction strength
    
    This means:
      - When diffusion is 80 (bullish) and price is above MA → strong positive divergence
      - When diffusion is 20 (bearish) and price is above MA → muted divergence (whale sell pressure)
    """
    roll_mean = close.rolling(window, min_periods=5).mean()
    roll_std  = close.rolling(window, min_periods=5).std().replace(0, np.nan)
    z_score   = (close - roll_mean) / roll_std
    divergence = z_score * (diffusion_score / 100.0)
    return divergence.fillna(0.0)

def _safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default

def _ensure_returns(close: pd.Series) -> pd.Series:
    close = close.astype(float)
    r = close.pct_change()
    return r.replace([np.inf, -np.inf], np.nan).fillna(0.0)

def _ewma_sigma(returns: np.ndarray, lam: float = 0.94) -> float:
    """
    RiskMetrics EWMA Variance: σ²_t = λ·σ²_{t-1} + (1-λ)·r²_t
    Gives exponential recency weighting so recent crashes dominate.
    λ=0.94 is the JP Morgan / RiskMetrics industry standard for daily data.
    """
    if len(returns) < 2:
        return 0.0
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    var = float(np.var(r[:5]))  # seed with first-5-bar variance
    for rt in r[5:]:
        var = lam * var + (1.0 - lam) * rt ** 2
    return float(np.sqrt(max(var, 0.0)))

# ─── Regime strings that warrant an expanded cone ───────────────────────────
_VOLATILE_REGIMES = {
    "VOLATILE", "CHAOS_SPIKE", "BLOOD_IN_STREETS",
    "BLOOD", "CAPITULATION", "CRASH", "EXTREME_FEAR",
    "WHITE_NOISE", "WHIPSAW",
}

def build_vol_cone(close: pd.Series, horizon: int = 48, lookback: int = 240,
                   sigmas=(1, 2), mode: str = "sqrt_time",
                   current_violence: float = 1.0,
                   current_regime: str | None = None):
    """
    Returns dict with bands: {sigma: (lower, upper)} arrays length horizon+1

    Adaptive Sigma (3-layer):
    1. EWMA λ=0.94 — exponential recency weighting (RiskMetrics standard).
       Recent day crash weights 30× more than a quiet bar 90 days ago.
    2. Dynamic sigma lookback — 90–180 bars (recent vol, NOT full history).
       Full lookback is still used by build_regime_paths for bootstrap diversity.
    3. Regime-Conditional Multiplier — automatically widens cone in volatile regimes:
       VOLATILE / CHAOS_SPIKE / BLOOD_IN_STREETS → 2.0×–2.5× sigma expansion.

    Input current_violence: Legacy chaos multiplier (1.0 = normal).
    Input current_regime:   String from regime_detector, used for tier-3 multiplier.
    """
    close = close.dropna().astype(float)
    n = len(close)

    # ── Layer 2: Dynamic Lookback for sigma (90–180 bars recent, not full history) ──
    sigma_lookback = max(90, min(180, n - 1))
    r_sigma = _ensure_returns(close).tail(sigma_lookback)

    # ── Layer 1: EWMA Sigma (exponentially weighted, λ=0.94) ────────────────────
    sigma_ewma = _ewma_sigma(r_sigma.values, lam=0.94)

    # Fallback: if EWMA gives 0 (degenerate input), use plain std over same window
    if sigma_ewma < 1e-8:
        sigma_ewma = float(np.nanstd(r_sigma.values, ddof=1)) if len(r_sigma) > 5 else 0.0

    # ── Layer 3: Regime-Conditional Multiplier ───────────────────────────────────
    regime_multiplier = 1.0
    if current_regime is not None:
        regime_upper = str(current_regime).upper()
        if any(tag in regime_upper for tag in _VOLATILE_REGIMES):
            # Scale with violence: baseline 2.0× up to 2.5× at violence ≥ 2.0
            regime_multiplier = min(2.5, 2.0 + max(0.0, current_violence - 1.0) * 0.25)

    # ── Legacy chaos adjustment (existing violence multiplier) ───────────────────
    sensitivity = 0.5
    violence_adjustment = 1.0
    if current_violence > 1.0 and regime_multiplier == 1.0:
        # Only apply legacy multiplier if regime multiplier didn't already kick in
        violence_adjustment = min(3.0, 1.0 + (current_violence - 1.0) * sensitivity)

    # Final sigma = EWMA × regime_multiplier × violence_adjustment
    sigma = sigma_ewma  # raw EWMA (for reporting)
    adjusted_sigma = sigma_ewma * regime_multiplier * violence_adjustment

    last = float(close.iloc[-1])
    t = np.arange(0, horizon + 1)
    scale = np.sqrt(t) if mode == "sqrt_time" else t

    bands = {}
    for s in sigmas:
        spread = (adjusted_sigma * _safe_float(s, 1.0)) * scale
        up = last * (1.0 + spread)
        dn = last * (1.0 - spread)
        bands[int(s)] = (dn, up)

    return {
        "last": last,
        "sigma": sigma,                          # EWMA sigma (raw, pre-multiplier)
        "adjusted_sigma": adjusted_sigma,        # Final sigma used for cone width
        "sigma_lookback": sigma_lookback,        # Actual bars used for EWMA
        "regime_multiplier": regime_multiplier,  # Layer-3 regime expansion factor
        "violence_adjustment": violence_adjustment,
        "t": t,
        "bands": bands,
    }

def _labels_to_str(labels) -> str:
    if labels is None:
        return ""
    if isinstance(labels, (list, tuple, set)):
        return "|".join(sorted([str(x) for x in labels]))
    return str(labels)

def build_regime_paths(close: pd.Series,
                       regime_series: pd.Series | None = None,
                       current_regime=None,
                       horizon: int = 48,
                       lookback: int = 1000,
                       n_paths: int = 120,
                       min_windows: int = 20,
                       seed: int = 42):
    """
    Bootstrap forward return windows from historical segments matching current_regime.
    If no regime info provided -> uses all windows.
    Returns: paths array shape (n_paths, horizon+1), plus summary percentiles.
    """
    rng = np.random.default_rng(seed)
    close = close.dropna().astype(float).tail(lookback)
    last = float(close.iloc[-1])
    r = _ensure_returns(close).values  # length N

    N = len(r)
    if N < horizon + 50:
        raise ValueError("Not enough data to build regime paths")

    # windows are start indices for horizon returns
    starts = np.arange(1, N - horizon)  # start from 1 to have prev close
    pick_starts = starts

    # Filter by regime if available
    if regime_series is not None and current_regime is not None:
        rs = regime_series.reindex(close.index).fillna("")
        cur = _labels_to_str(current_regime)
        # keep windows where regime at start matches
        mask = (rs.iloc[pick_starts].astype(str).values == cur)
        pick_starts = pick_starts[mask]

    # If too few matches -> fallback to all (with warning in caller)
    if len(pick_starts) < min_windows:
        # We don't fallback here to force undersampling detection, 
        # unless it's 0 then we must fallback to avoid crash
        if len(pick_starts) == 0:
            pick_starts = starts
    
    # Sample windows
    # Bias Force: replace=True allows amplification of rare events
    chosen = rng.choice(pick_starts, size=n_paths, replace=True)

    paths = np.zeros((n_paths, horizon + 1), dtype=float)
    paths[:, 0] = last

    for i, st in enumerate(chosen):
        window_r = r[st: st + horizon]  # horizon returns
        # price path: P_t = P0 * cumprod(1+r)
        paths[i, 1:] = last * np.cumprod(1.0 + window_r)

    # summaries
    p10 = np.percentile(paths, 10, axis=0)
    p50 = np.percentile(paths, 50, axis=0)
    p90 = np.percentile(paths, 90, axis=0)

    return {
        "last": last,
        "paths": paths,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "num_windows_used": int(len(pick_starts))
    }

def render_projection_tab(st, df: pd.DataFrame, qc_payload: dict | None = None,
                          horizon: int = 48, current_regime: str | None = None,
                          current_violence: float = 1.0,
                          key: str = "dudu_base_chart"):
    """
    Streamlit renderer. Minimal dependencies: numpy, pandas.
    """
    if df is None or len(df) < 50:
        st.warning("Not enough data for projection")
        return

    close = df['close']
    
    cur_regime = current_regime
    if cur_regime is None and qc_payload and isinstance(qc_payload, dict):
        codes = qc_payload.get("qc_codes") or qc_payload.get("codes") or []
        if isinstance(codes, str):
            codes = [codes]
        cur_regime = "|".join(sorted([str(x) for x in codes])) if codes else None

    # Vol Cone (Present) — Adaptive Sigma (EWMA + Dynamic Lookback + Regime Multiplier)
    cone = build_vol_cone(close, horizon=horizon, lookback=min(240, len(close)-1),
                          sigmas=(1, 2), current_violence=current_violence,
                          current_regime=cur_regime)
    
    # Regime Paths (Future)
    # Note: passing None for regime_series implies NO FILTERING currently.
    # TODO: Pass actual regime series from dashboard for historical filtering.
    regime_series = None 
    
    paths_obj = build_regime_paths(close, regime_series=regime_series, current_regime=cur_regime,
                                   horizon=horizon, lookback=min(1200, len(close)),
                                   n_paths=140, min_windows=20)

    t = np.arange(0, horizon + 1)

    fig = go.Figure()

    # historical tail (visual context)
    hist_tail = close.tail(240)
    fig.add_trace(go.Scatter(
        x=np.arange(-len(hist_tail)+1, 1),
        y=hist_tail.values,
        mode="lines",
        name="History (Price)",
        line=dict(color="rgba(255,255,255,0.4)", width=1.5)
    ))
    
    # Vertical line separating Past from Future
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    # shift future x-axis
    x_future = t

    # Cone bands
    for s in [1, 2]:
        dn, up = cone["bands"][s]
        fig.add_trace(go.Scatter(x=x_future, y=up, mode="lines", name=f"Cone +{s}σ", line=dict(dash="dot")))
        fig.add_trace(go.Scatter(x=x_future, y=dn, mode="lines", name=f"Cone -{s}σ", line=dict(dash="dot")))

    # Paths (subsample to avoid mobile overload)
    paths = paths_obj["paths"]
    step = max(1, paths.shape[0] // 60)
    for i in range(0, paths.shape[0], step):
        fig.add_trace(go.Scatter(x=x_future, y=paths[i], mode="lines", name="Path", opacity=0.12, showlegend=False))

    # Percentiles
    fig.add_trace(go.Scatter(x=x_future, y=paths_obj["p50"], mode="lines", name="Median", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=x_future, y=paths_obj["p10"], mode="lines", name="P10", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=x_future, y=paths_obj["p90"], mode="lines", name="P90", line=dict(dash="dash")))

    # Calculate Y-axis bounds to center everything nicely
    y_min = min(hist_tail.min(), cone["bands"][2][0].min(), paths_obj["p10"].min())
    y_max = max(hist_tail.max(), cone["bands"][2][1].max(), paths_obj["p90"].max())
    padding = (y_max - y_min) * 0.05 # 5% buffer
    
    fig.update_layout(
        title="🔮 Manifold Projection (DUDU Overlay)",
        xaxis_title="Bars ahead (0 = now)",
        yaxis_title="Price (USD)",
        yaxis=dict(range=[y_min - padding, y_max + padding], gridcolor='rgba(255,255,255,0.05)'),
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True, key=key)

    # 📉 Undersampling Fail-Safe Check
    num_windows = paths_obj['num_windows_used']
    if num_windows < 20:
        st.error(f"⚠️ LOW CONFIDENCE: Undersampling ({num_windows} windows < 20). FAIL-SAFE: Reduce Position Size (0.5x).")

    st.caption(
        f"Windows: {num_windows} | "
        f"EWMA σ: {cone['sigma']:.6f} ({cone['sigma_lookback']}bars) | "
        f"Adj σ: {cone['adjusted_sigma']:.6f} | "
        f"Regime×: {cone['regime_multiplier']:.1f}× | "
        f"Violence×: {cone['violence_adjustment']:.2f}×"
    )
