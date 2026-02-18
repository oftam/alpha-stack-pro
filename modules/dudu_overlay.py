# dudu_overlay.py
# DUDU Overlay V0: Vol Cone + Regime Paths (bootstrap from similar regimes)
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def _safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default

def _ensure_returns(close: pd.Series) -> pd.Series:
    close = close.astype(float)
    r = close.pct_change()
    return r.replace([np.inf, -np.inf], np.nan).fillna(0.0)

def build_vol_cone(close: pd.Series, horizon: int = 48, lookback: int = 240,
                   sigmas=(1, 2), mode: str = "sqrt_time", current_violence: float = 1.0):
    """
    Returns dict with bands: {sigma: (lower, upper)} arrays length horizon+1
    Input current_violence: Multiplier for chaos adjustment (1.0 = normal).
    """
    close = close.dropna().astype(float)
    if len(close) < max(lookback, 50):
        lookback = max(50, len(close) - 1)

    r = _ensure_returns(close).tail(lookback)
    sigma = float(np.nanstd(r.values, ddof=1)) if len(r) > 5 else 0.0
    last = float(close.iloc[-1])

    t = np.arange(0, horizon + 1)
    if mode == "sqrt_time":
        scale = np.sqrt(t)
    else:
        scale = t

    bands = {}
    
    # 🚀 Dynamic Chaos Adjustment: Calibration Protocol
    # If violence > 1.0 (Chaos), expand the cone to contain kinetic energy
    sensitivity = 0.5
    adjustment = 1.0
    if current_violence > 1.0:
        adjustment = 1.0 + (current_violence - 1.0) * sensitivity
        # Cap adjustment to prevent explosion (e.g., max 3x sigma)
        adjustment = min(adjustment, 3.0)
    
    adjusted_sigma = sigma * adjustment

    for s in sigmas:
        spread = (adjusted_sigma * _safe_float(s, 1.0)) * scale
        up = last * (1.0 + spread)
        dn = last * (1.0 - spread)
        bands[int(s)] = (dn, up)

    return {"last": last, "sigma": sigma, "adjusted_sigma": adjusted_sigma, "t": t, "bands": bands}

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
                          current_violence: float = 1.0):
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

    # Vol Cone (Present)
    cone = build_vol_cone(close, horizon=horizon, lookback=min(240, len(close)-1), 
                         sigmas=(1,2), current_violence=current_violence)
    
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
        name="History (tail)"
    ))

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

    fig.update_layout(
        title="Projection (DUDU Overlay): Cone + Regime Paths",
        xaxis_title="Bars ahead (0 = now)",
        yaxis_title="Price",
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h")
    )

    st.plotly_chart(fig, width="stretch")

    # 📉 Undersampling Fail-Safe Check
    num_windows = paths_obj['num_windows_used']
    if num_windows < 20:
        st.error(f"⚠️ LOW CONFIDENCE: Undersampling ({num_windows} windows < 20). FAIL-SAFE: Reduce Position Size (0.5x).")

    st.caption(f"Windows used: {num_windows} | Cone sigma: {cone['sigma']:.6f} | Adj Sigma: {cone['adjusted_sigma']:.6f}")
