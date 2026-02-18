#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTRA ML Dashboard — ONEFILE (v20) — QC + DUDU Projection + Elite Projection + LIVE Scoreboard
SPOT + (optional futures education), long-only direction, reduce/exit allowed.

What’s new vs v18/v19:
- Live Scoreboard (SQLite) for out-of-sample tracking:
  - Logs predictions every run (p_up, ev, action, policy_state, qc codes, close)
  - Resolves outcomes when horizon has passed
  - Computes AUC, Brier, Precision@TopK, simple PnL proxy
  - Model Health: GREEN/YELLOW/RED and auto "confidence throttle" hints

Run:
    streamlit run ultimate_dashboard_ULTRA_ML_v20_ONEFILE_SCOREBOARD.py

Note:
- Engine is loaded from a sibling file if present (default tries common engine filenames).
- If sklearn isn't installed, AUC/Brier will degrade gracefully.

"""

from __future__ import annotations


# Elite Forecasting System
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from integration.dashboard_adapter import DashboardForecastAdapter
    ELITE_FORECASTING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Elite forecasting not available: {e}")
    ELITE_FORECASTING_AVAILABLE = False

import os
import time
import json
import math
import sqlite3
import importlib.util
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------
# Optional sklearn metrics
# ----------------------------
try:
    from sklearn.metrics import roc_auc_score, brier_score_loss
except Exception:
    roc_auc_score = None
    brier_score_loss = None


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "🧠📊 ULTRA ML Dashboard (v20) — ONEFILE + LIVE Scoreboard"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_INTERVAL = "1h"
DEFAULT_BARS = 1000
DEFAULT_HORIZON = 5  # bars

CORE_FLOOR_DEFAULT = 0.15  # 15% core floor
REDUCE_LEVELS_DEFAULT = (0.20, 0.35, 0.50)  # 20/35/50

DB_PATH = os.path.join(os.path.dirname(__file__), "scoreboard.sqlite")

# Engine candidates (in same folder)
ENGINE_CANDIDATES = [
    "quant_war_room_ml_pro_ONEFILE_v8b_spot_eventbias_QC_DIFF_CORR_TRUECVD.py",
    "quant_war_room_ml_pro_ONEFILE_v8_spot_eventbias_QC_DIFF_CORR_TRUECVD.py",
    "quant_war_room_ml_pro_ONEFILE_v7_spot_eventbias.py",
    "quant_war_room_ml_pro_ONEFILE_v6_spot_short_edu.py",
    "quant_war_room_ml_pro_ONEFILE_v4_policy.py",
]

# ============================================================
# UTIL
# ============================================================

def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def safe_float(x, default=np.nan):
    try:
        if x is None:
            return default
        if isinstance(x, (float, int, np.floating, np.integer)):
            return float(x)
        s = str(x).strip()
        if s.lower() in ("nan", "none", ""):
            return default
        return float(s)
    except Exception:
        return default



# ============================================================
# BINANCE OHLCV FALLBACK (REST)
# ============================================================
def _fetch_ohlcv_binance_rest(symbol: str, interval: str = "1h", limit: int = 1000) -> pd.DataFrame:
    """Fetch OHLCV directly from Binance REST (no engine dependency).
    Returns DataFrame with columns: ts, open, high, low, close, volume (UTC).
    """
    import requests

    # Binance supports: 1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": int(limit)}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_asset_volume","num_trades","taker_buy_base","taker_buy_quote","ignore"]
    df = pd.DataFrame(data, columns=cols)
    df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["ts","open","high","low","close","volume"]].sort_values("ts").reset_index(drop=True)
    return df

def _fetch_ohlcv_any(engine, symbol: str, interval: str, bars: int) -> pd.DataFrame:
    """Try engine fetchers, fallback to Binance REST."""
    # Engine variants
    for fname in ["fetch_ohlcv_binance", "fetch_binance_ohlcv", "fetch_ohlcv", "get_ohlcv", "load_ohlcv"]:
        if hasattr(engine, fname):
            f = getattr(engine, fname)
            try:
                return f(symbol=symbol, interval=interval, limit=int(bars))
            except TypeError:
                # Some engines use different param names
                try:
                    return f(symbol, interval, int(bars))
                except Exception:
                    return f(symbol=symbol, interval=interval, bars=int(bars))
    # Hard fallback
    return _fetch_ohlcv_binance_rest(symbol=symbol, interval=interval, limit=int(bars))
def load_engine():
    """
    Load external engine module from same directory.
    Returns (ENGINE_MODULE, ENGINE_PATH).
    """
    here = os.path.dirname(__file__)
    explicit = os.getenv("ULTRA_ENGINE_PATH", "").strip()
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates += [os.path.join(here, f) for f in ENGINE_CANDIDATES]
    for p in candidates:
        if p and os.path.exists(p):
            spec = importlib.util.spec_from_file_location("qwr_engine", p)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            return mod, p
    raise FileNotFoundError("Cannot find engine file. Set ULTRA_ENGINE_PATH env var or place engine next to dashboard.")

# ============================================================
# SCOREBOARD (SQLite)
# ============================================================

def sb_init(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_utc TEXT NOT NULL,
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        horizon INTEGER NOT NULL,
        close REAL,
        p_up REAL,
        ev REAL,
        action TEXT,
        policy_state TEXT,
        qc_codes TEXT,
        drift_flag INTEGER DEFAULT 0,
        meta TEXT,
        outcome_ts_utc TEXT,
        close_fwd REAL,
        ret_fwd REAL,
        y_actual INTEGER,
        resolved INTEGER DEFAULT 0
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_lookup ON predictions(symbol, interval, ts_utc, horizon)")
    conn.commit()
    conn.close()

def sb_log_prediction(payload: dict, db_path: str = DB_PATH):
    """
    payload keys: ts_utc, symbol, interval, horizon, close, p_up, ev, action, policy_state, qc_codes(list/str), drift_flag(bool/int), meta(dict)
    """
    sb_init(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    qc_codes = payload.get("qc_codes", [])
    if isinstance(qc_codes, (list, tuple)):
        qc_codes = ",".join([str(x) for x in qc_codes])
    meta = payload.get("meta", {})
    cur.execute("""
        INSERT INTO predictions
        (ts_utc, symbol, interval, horizon, close, p_up, ev, action, policy_state, qc_codes, drift_flag, meta, resolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        payload.get("ts_utc"),
        payload.get("symbol"),
        payload.get("interval"),
        int(payload.get("horizon", 0)),
        safe_float(payload.get("close")),
        safe_float(payload.get("p_up")),
        safe_float(payload.get("ev")),
        str(payload.get("action") or ""),
        str(payload.get("policy_state") or ""),
        str(qc_codes or ""),
        int(bool(payload.get("drift_flag", 0))),
        json.dumps(meta, ensure_ascii=False),
    ))
    conn.commit()
    conn.close()

def sb_resolve_outcomes(df: pd.DataFrame, symbol: str, interval: str, horizon: int, db_path: str = DB_PATH):
    """
    Resolve any unresolved rows where we now have forward close for (ts + horizon bars).
    Assumes df indexed by UTC timestamps (or convertible).
    """
    sb_init(db_path)
    if df is None or df.empty:
        return 0
    # Ensure datetime index
    dfi = df.copy()
    if not isinstance(dfi.index, pd.DatetimeIndex):
        if "ts" in dfi.columns:
            dfi.index = pd.to_datetime(dfi["ts"], utc=True, errors="coerce")
        else:
            dfi.index = pd.to_datetime(dfi.index, utc=True, errors="coerce")
    dfi = dfi.sort_index()
    # Map timestamp->close
    close_series = dfi["close"].astype(float)
    idx = close_series.index

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ts_utc, close
        FROM predictions
        WHERE symbol=? AND interval=? AND horizon=? AND resolved=0
        ORDER BY id ASC
        LIMIT 5000
    """, (symbol, interval, int(horizon)))
    rows = cur.fetchall()
    resolved = 0

    # Build lookup: for each ts, find index position and forward position
    for rid, ts_utc, close0 in rows:
        try:
            t0 = pd.to_datetime(ts_utc.replace(" UTC",""), utc=True)
            # find nearest exact match (we log ts as candle close time)
            if t0 not in idx:
                # try nearest (tolerance)
                pos = idx.get_indexer([t0], method="nearest")[0]
            else:
                pos = idx.get_loc(t0)
            fpos = pos + int(horizon)
            if fpos >= len(idx):
                continue
            t1 = idx[fpos]
            close1 = float(close_series.iloc[fpos])
            close0 = float(close0) if close0 is not None else float(close_series.iloc[pos])
            ret = (close1 / close0) - 1.0
            y = 1 if ret > 0 else 0
            cur.execute("""
                UPDATE predictions
                SET outcome_ts_utc=?, close_fwd=?, ret_fwd=?, y_actual=?, resolved=1
                WHERE id=?
            """, (t1.strftime("%Y-%m-%d %H:%M:%S UTC"), close1, ret, y, rid))
            resolved += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    return resolved

def sb_fetch_resolved(symbol: str, interval: str, horizon: int, limit: int = 2000, db_path: str = DB_PATH) -> pd.DataFrame:
    sb_init(db_path)
    conn = sqlite3.connect(db_path)
    q = """
        SELECT ts_utc, close, p_up, ev, action, policy_state, qc_codes, drift_flag,
               outcome_ts_utc, close_fwd, ret_fwd, y_actual
        FROM predictions
        WHERE symbol=? AND interval=? AND horizon=? AND resolved=1
        ORDER BY id DESC
        LIMIT ?
    """
    df = pd.read_sql_query(q, conn, params=(symbol, interval, int(horizon), int(limit)))
    conn.close()
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"].str.replace(" UTC",""), utc=True, errors="coerce")
        df = df.sort_values("ts_utc")
    return df

def compute_scoreboard_metrics(df_res: pd.DataFrame, topk: int = 20) -> dict:
    """
    Metrics: AUC, Brier, Precision@TopK, mean ret when p_up topk, proxy PnL with simple rule.
    """
    if df_res is None or df_res.empty or len(df_res) < 30:
        return {"n": 0}

    y = df_res["y_actual"].astype(int).values
    p = df_res["p_up"].astype(float).clip(1e-6, 1-1e-6).values

    out = {"n": int(len(df_res))}
    # AUC
    if roc_auc_score is not None and len(np.unique(y)) > 1:
        try:
            out["auc"] = float(roc_auc_score(y, p))
        except Exception:
            out["auc"] = np.nan
    else:
        out["auc"] = np.nan

    # Brier
    if brier_score_loss is not None:
        try:
            out["brier"] = float(brier_score_loss(y, p))
        except Exception:
            out["brier"] = np.nan
    else:
        # fallback: mean squared error
        out["brier"] = float(np.mean((p - y) ** 2))

    # Precision@TopK
    k = max(5, min(int(topk), len(df_res)))
    df_sorted = df_res.assign(p=p).sort_values("p", ascending=False).tail(0)  # just to keep linter calm
    df_sorted = df_res.copy()
    df_sorted["p"] = p
    df_sorted = df_sorted.sort_values("p", ascending=False).head(k)
    out["precision_at_k"] = float(df_sorted["y_actual"].mean())

    # Average forward return for topK
    out["mean_ret_topk"] = float(df_sorted["ret_fwd"].mean())

    # Simple proxy PnL: take exposure=1 if p_up>0.55 else 0.2; always long-only
    expo = np.where(p > 0.55, 1.0, 0.2)
    out["pnl_proxy_mean"] = float(np.mean(expo * df_res["ret_fwd"].astype(float).values))

    return out

def health_from_metrics(metrics: dict, drift_high: bool) -> tuple[str, str]:
    """
    Return (label, color)
    """
    if metrics.get("n", 0) < 30:
        return ("INSUFFICIENT_DATA", "gray")
    auc = metrics.get("auc", np.nan)
    brier = metrics.get("brier", np.nan)
    prec = metrics.get("precision_at_k", np.nan)

    # Conservative thresholds
    good = (not np.isnan(auc) and auc >= 0.56) and (not np.isnan(brier) and brier <= 0.22) and (not np.isnan(prec) and prec >= 0.55)
    bad = (not np.isnan(auc) and auc <= 0.50) or (not np.isnan(brier) and brier >= 0.30) or (not np.isnan(prec) and prec <= 0.45)

    if drift_high:
        # drift elevates risk: downgrade one notch
        if good:
            return ("YELLOW_DRIFT", "orange")
        return ("RED_DRIFT", "red")

    if good:
        return ("GREEN", "green")
    if bad:
        return ("RED", "red")
    return ("YELLOW", "orange")


# ============================================================
# DUDU OVERLAY (simple)
# ============================================================

def dudu_projection(df: pd.DataFrame, horizon: int = 48, sims: int = 800):
    """
    Simple cone projection: GBM-ish using recent returns mean/std (base).
    Returns quantiles for price paths: P10/P50/P90 and sigma estimate.
    """
    dfi = df.copy()
    if "close" not in dfi.columns or len(dfi) < 50:
        return None
    rets = dfi["close"].pct_change().dropna().values
    mu = float(np.mean(rets[-200:])) if len(rets) >= 200 else float(np.mean(rets))
    sig = float(np.std(rets[-200:])) if len(rets) >= 200 else float(np.std(rets))
    sig = max(sig, 1e-6)

    last = float(dfi["close"].iloc[-1])
    paths = np.zeros((sims, horizon+1), dtype=float)
    paths[:, 0] = last
    for t in range(1, horizon+1):
        z = np.random.normal(size=sims)
        step = (mu - 0.5*sig*sig) + sig*z
        paths[:, t] = paths[:, t-1] * np.exp(step)

    p10 = np.percentile(paths, 10, axis=0)
    p50 = np.percentile(paths, 50, axis=0)
    p90 = np.percentile(paths, 90, axis=0)
    return {"p10": p10, "p50": p50, "p90": p90, "sigma": sig, "mu": mu, "paths": paths}


# ============================================================
# Elite Projection (practical, not zoo)
# ============================================================

def elite_projection(df: pd.DataFrame, horizon: int = 48, sims: int = 800):
    """
    Elite = DUDU base + vol conditioning + fat-tail (Student-t) inflation + learned regimes-lite.
    Returns dict with cone quantiles and regime probabilities.
    """
    if df is None or df.empty or "close" not in df.columns:
        return None

    dfi = df.copy()
    rets = dfi["close"].pct_change().dropna()
    if len(rets) < 200:
        return None

    # --- Vol conditioning: short vs long realized vol multiplier
    vol_short = float(rets[-48:].std())
    vol_long  = float(rets[-500:].std())
    vol_long = max(vol_long, 1e-6)
    vol_mult = float(np.clip(vol_short / vol_long, 0.7, 2.5))

    # --- Base mu/sigma
    mu = float(rets[-200:].mean())
    sig = float(rets[-200:].std())
    sig_eff = max(sig * vol_mult, 1e-6)

    # --- Fat tail inflation using Student-t kurtosis proxy
    # Fit a simple df estimate from excess kurtosis (robust-ish), clamp.
    x = rets[-500:].values
    m4 = np.mean((x - x.mean())**4)
    v2 = np.mean((x - x.mean())**2)
    kurt = (m4 / (v2*v2 + 1e-12)) if v2 > 0 else 3.0
    # Map kurtosis -> df (rough): high kurtosis => low df
    # For Student-t, kurtosis = 3*(df-2)/(df-4) for df>4
    # Solve approx; clamp df in [4.5, 30]
    df_est = 30.0
    try:
        if kurt > 3.2:
            df_est = max(4.6, min(30.0, 4.0 + 6.0/(kurt-3.0)))
    except Exception:
        df_est = 12.0

    # --- Learned regimes-lite: Gaussian mixture on (ret, vol)
    # We avoid hmmlearn dependency. We compute simple regime probs by clustering recent points.
    # Features: [ret, abs(ret)]
    feats = np.vstack([rets[-500:].values, np.abs(rets[-500:].values)]).T
    # Simple k=3 quantile-based "soft" regimes: low/med/high vol buckets
    vol_feat = feats[:, 1]
    q1, q2 = np.quantile(vol_feat, [0.33, 0.66])
    # Current point
    cur = np.array([rets.iloc[-1], abs(rets.iloc[-1])])
    # Soft distances to bucket centroids
    centroids = np.array([
        [0.0, np.mean(vol_feat[vol_feat<=q1])],
        [0.0, np.mean(vol_feat[(vol_feat>q1)&(vol_feat<=q2)])],
        [0.0, np.mean(vol_feat[vol_feat>q2])]
    ])
    d = np.linalg.norm(centroids - cur, axis=1)
    # Convert to probs
    w = np.exp(-d / (np.std(d)+1e-6))
    probs = (w / (w.sum()+1e-12)).tolist()
    regime_probs = {"LOW_VOL": float(probs[0]), "MID_VOL": float(probs[1]), "HIGH_VOL": float(probs[2])}

    # --- Simulate paths with mixed innovations:
    # 90% normal, 10% fat-tail (Student-t)
    last = float(dfi["close"].iloc[-1])
    paths = np.zeros((sims, horizon+1), dtype=float)
    paths[:, 0] = last
    n_fat = max(1, int(sims * 0.10))
    fat_idx = np.random.choice(np.arange(sims), size=n_fat, replace=False)
    # innovations
    for t in range(1, horizon+1):
        z = np.random.normal(size=sims)
        # fat tail replacement
        # Student-t via standard formula using numpy: t = normal / sqrt(chi2/df)
        chi = np.random.chisquare(df_est, size=n_fat)
        t_innov = np.random.normal(size=n_fat) / np.sqrt(chi / df_est)
        z[fat_idx] = t_innov
        step = (mu - 0.5*sig_eff*sig_eff) + sig_eff*z
        paths[:, t] = paths[:, t-1] * np.exp(step)

    p10 = np.percentile(paths, 10, axis=0)
    p50 = np.percentile(paths, 50, axis=0)
    p90 = np.percentile(paths, 90, axis=0)
    p01 = np.percentile(paths, 1, axis=0)
    p99 = np.percentile(paths, 99, axis=0)

    # Ensemble: weighted median-ish: here just return both DUDU base + elite
    return {
        "p01": p01, "p10": p10, "p50": p50, "p90": p90, "p99": p99,
        "sigma_eff": sig_eff, "sigma_base": sig, "mu": mu,
        "vol_mult": vol_mult, "df_est": float(df_est),
        "regime_probs": regime_probs,
        "paths": paths
    }


# ============================================================
# Streamlit UI
# ============================================================

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption(f"Server time: {utc_now_str()}")

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Controls")
        symbol = st.text_input("Symbol", DEFAULT_SYMBOL)
        interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
        bars = st.number_input("Bars", min_value=200, max_value=5000, value=DEFAULT_BARS, step=100)
        horizon = st.number_input("Horizon (bars)", min_value=1, max_value=240, value=DEFAULT_HORIZON, step=1)
        core_floor = st.slider("core_floor", 0.0, 1.0, float(CORE_FLOOR_DEFAULT), 0.01)
        reduce_lvls = st.multiselect("Reduce ladder", [0.10,0.20,0.25,0.35,0.50,0.60,0.75], default=list(REDUCE_LEVELS_DEFAULT))
        st.divider()
        st.subheader("🧾 Portfolio (optional)")
        nav_usd = st.number_input("NAV נזיל (Portfolio Value $)", min_value=0.0, value=0.0, step=100.0)
        cash_usd = st.number_input("מזומן נזיל (Cash $)", min_value=0.0, value=0.0, step=100.0)
        btc_units = st.number_input("BTC Units", min_value=0.0, value=0.0, step=0.01)
        st.divider()
        st.subheader("🧪 Scoreboard")
        sb_limit = st.slider("Recent samples", 100, 5000, 2000, 100)
        topk = st.slider("TopK for Precision@K", 10, 200, 20, 5)

    # Load engine
    try:
        ENGINE, ENGINE_PATH = load_engine()
        st.success(f"Engine loaded: {os.path.basename(ENGINE_PATH)}")
    except Exception as e:
        st.error(f"Engine load failed: {e}")
        return

    # Fetch data
    try:
        df = _fetch_ohlcv_any(ENGINE, symbol=symbol, interval=interval, bars=int(bars))
        if df is None or len(df) == 0:
            st.error("OHLCV fetch returned empty data")
            return
    except Exception as e:
        st.error(f"Data fetch failed: {e}")
        return

    if df is None or df.empty:
        st.error("No data.")
        return

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        if "ts" in df.columns:
            df.index = pd.to_datetime(df["ts"], utc=True, errors="coerce")
        else:
            df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df = df.sort_index()

    last_close = float(df["close"].iloc[-1])
    st.metric("Last Close", f"{last_close:,.2f}")

    # Compute QC + Signal/Policy from engine if available
    qc_payload = {}
    action = "HOLD"
    policy_state = "HOLD"
    p_up = np.nan
    ev = np.nan
    qc_codes = []
    drift_high = False

    try:
        if hasattr(ENGINE, "compute_qc_flow_structure"):
            qc_payload = ENGINE.compute_qc_flow_structure(df.copy())
            qc_codes = qc_payload.get("qc_codes", []) or []
    except Exception:
        qc_payload = {}

    try:
        if hasattr(ENGINE, "predict_and_policy"):
            out = ENGINE.predict_and_policy(df.copy(), horizon=int(horizon))
            p_up = safe_float(out.get("p_up"))
            ev = safe_float(out.get("ev"))
            action = out.get("action", action)
            policy_state = out.get("policy_state", policy_state)
            qc_codes = out.get("reason_codes", qc_codes) or qc_codes
        elif hasattr(ENGINE, "predict_proba"):
            # fallback
            proba = ENGINE.predict_proba(df.copy(), horizon=int(horizon))
            p_up = safe_float(proba)
    except Exception as e:
        st.warning(f"Signal/Policy failed: {e}")

    # Drift flag
    drift_high = any(str(c).upper().startswith("DRIFT_HIGH") for c in (qc_codes or []))

    # Log prediction to scoreboard
    try:
        ts_utc = df.index[-1].strftime("%Y-%m-%d %H:%M:%S UTC")
        sb_log_prediction({
            "ts_utc": ts_utc,
            "symbol": symbol,
            "interval": interval,
            "horizon": int(horizon),
            "close": last_close,
            "p_up": p_up,
            "ev": ev,
            "action": action,
            "policy_state": policy_state,
            "qc_codes": qc_codes,
            "drift_flag": drift_high,
            "meta": {"engine": os.path.basename(ENGINE_PATH)}
        })
    except Exception as e:
        st.warning(f"Scoreboard log failed: {e}")

    # Resolve outcomes
    try:
        resolved = sb_resolve_outcomes(df, symbol=symbol, interval=interval, horizon=int(horizon))
    except Exception:
        resolved = 0

    # Tabs
    tabs, tab_elite = st.tabs(["📈 Market", "🧠 Signal + Policy", "🫧 QC", "🧪 Projection", "📊 Scoreboard", "🎯 Elite Forecast", "⚙️ Raw"])

    with tabs[0]:
        st.subheader("📈 Market")
        st.line_chart(df["close"], height=260)
        st.caption(f"Bars: {len(df)} | Interval: {interval} | Updated: {utc_now_str()}")

    with tabs[1]:
        st.subheader("🧠 Signal + Policy")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Action", str(action))
        c2.metric("Policy State", str(policy_state))
        c3.metric("P(up)", f"{p_up:.4f}" if not np.isnan(p_up) else "nan")
        c4.metric("EV (proxy)", f"{ev:.4f}" if not np.isnan(ev) else "nan")

        st.write("**QC Codes / Reasons:**", ", ".join([str(x) for x in (qc_codes or [])]) if qc_codes else "(none)")

        # DCA guidance from core_floor + policy
        st.divider()
        st.subheader("🧭 DCA CORE Guidance")
        if policy_state.upper().startswith("REDUCE") or str(action).upper().startswith("REDUCE"):
            st.info("מצב: **זהירות / REDUCE** — לא להגדיל קצב, לשקול הורדה לפי סולם Reduce.")
        elif policy_state.upper() in ("BUILD", "ADD"):
            st.success("מצב: **BUILD** — אפשר DCA יותר אגרסיבי (עדיין בתוך גבולות).")
        else:
            st.warning("מצב: **HOLD/KEEP_PACE** — לשמור קצב, לא לרדוף אחרי ראלי.")

        st.caption(f"core_floor={core_floor:.2f} | reduce ladder={reduce_lvls}")

    with tabs[2]:
        st.subheader("🫧 QC — Flow + Structure")
        if qc_payload:
            flow = qc_payload.get("flow", {})
            struct = qc_payload.get("structure", {})
            met = qc_payload.get("meta", {})
            cols = st.columns(6)
            cols[0].metric("Diffusion Score", f"{safe_float(flow.get('diffusion_score'), 50.0):.1f}")
            cols[1].metric("Book Imbalance", f"{safe_float(flow.get('book_imbalance'), 0.0):.3f}")
            cols[2].metric("Netflow Z", f"{safe_float(flow.get('netflow_z'), np.nan):+.2f}")
            cols[3].metric("Whale Accum", f"{safe_float(flow.get('whale_accum'), 0.0):.2f}")
            cols[4].metric("Coherence", f"{safe_float(struct.get('coherence'), 0.0):.2f}")
            cols[5].metric("Corr Break", f"{safe_float(struct.get('corr_break'), 0.0):+.2f}")
            st.write("Assets:", struct.get("assets_n", 0))
            st.write("QC Codes:", ", ".join(qc_payload.get("qc_codes", []) or []))
        else:
            st.info("QC payload not available from engine.")

    with tabs[3]:
        st.subheader("🧪 Projection")
        st.caption("DUDU Overlay stays as base. Elite Projection adds vol conditioning + fat tails + learned regimes-lite.")

        # DUDU
        dudu = dudu_projection(df, horizon=48, sims=800)
        if dudu:
            st.write(f"**DUDU Base Cone** | sigma={dudu['sigma']:.6f} | mu={dudu['mu']:.6f}")
            proj_df = pd.DataFrame({
                "P10": dudu["p10"],
                "P50": dudu["p50"],
                "P90": dudu["p90"],
            })
            st.line_chart(proj_df, height=260)

        # Elite
        elite = elite_projection(df, horizon=48, sims=800)
        if elite:
            st.write(f"**Elite Cone** | sigma_eff={elite['sigma_eff']:.6f} | vol_mult={elite['vol_mult']:.2f} | df_est={elite['df_est']:.2f}")
            st.write("Regime probabilities:", elite["regime_probs"])
            proj2 = pd.DataFrame({
                "P01": elite["p01"],
                "P10": elite["p10"],
                "P50": elite["p50"],
                "P90": elite["p90"],
                "P99": elite["p99"],
            })
            st.line_chart(proj2, height=300)
        else:
            st.warning("Elite Projection unavailable (need >=200 bars).")

    with tabs[4]:
        st.subheader("📊 Scoreboard — LIVE Out-of-Sample")
        if resolved:
            st.success(f"Resolved {resolved} pending outcomes.")

        df_res = sb_fetch_resolved(symbol=symbol, interval=interval, horizon=int(horizon), limit=int(sb_limit))
        metrics = compute_scoreboard_metrics(df_res, topk=int(topk))
        label, color = health_from_metrics(metrics, drift_high=drift_high)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Samples", str(metrics.get("n", 0)))
        c2.metric("AUC", f"{metrics.get('auc', np.nan):.3f}" if metrics.get("n",0) else "—")
        c3.metric("Brier", f"{metrics.get('brier', np.nan):.3f}" if metrics.get("n",0) else "—")
        c4.metric("Precision@K", f"{metrics.get('precision_at_k', np.nan):.3f}" if metrics.get("n",0) else "—")

        st.write(f"**Model Health:** :{color}[{label}]")
        if metrics.get("n", 0) >= 30:
            st.caption(f"PnL proxy mean per horizon: {metrics.get('pnl_proxy_mean', np.nan):+.4f} | mean_ret_topk: {metrics.get('mean_ret_topk', np.nan):+.4f}")

        if not df_res.empty:
            st.dataframe(df_res.tail(50), use_container_width=True)

        st.divider()
        st.subheader("🧭 What to do when model degrades")
        st.write("- GREEN: אפשר להעלות קצב (בגבולות).")
        st.write("- YELLOW: KEEP_PACE / REDUCE קטן, לא לרדוף.")
        st.write("- RED: core_floor בלבד + Reduce ladder, עד שהמדדים חוזרים.")

    with tabs[5]:
        st.subheader("⚙️ Raw")
        st.write("QC payload:", qc_payload)
        st.write("Last policy:", {"action": action, "policy_state": policy_state, "p_up": p_up, "ev": ev, "qc_codes": qc_codes, "drift_high": drift_high})
        st.write("Engine path:", ENGINE_PATH)
        st.write("DB path:", DB_PATH)

if __name__ == "__main__":
    main()


# ============================================================================
# ELITE FORECAST TAB
# ============================================================================

with tab_elite:
    st.subheader("🎯 Elite Ensemble Forecast")
    
    if not ELITE_FORECASTING_AVAILABLE:
        st.error("""
        Elite forecasting not available. 
        
        Install:
        ```bash
        pip install arch statsmodels
        ```
        
        And ensure forecasting/ and integration/ folders are in the same directory as this dashboard.
        """)
    else:
        # Configuration
        col1, col2, col3 = st.columns(3)
        
        with col1:
            forecast_horizon = st.number_input("Horizon (bars)", 24, 100, 48, step=12)
        
        with col2:
            n_paths = st.number_input("Paths", 100, 2000, 500, step=100)
        
        with col3:
            use_multiasset = st.checkbox("Multi-asset (VAR)", value=False)
        
        # Initialize adapter (cache)
        if 'elite_adapter' not in st.session_state:
            st.session_state.elite_adapter = DashboardForecastAdapter(
                enable_garch=True,
                enable_var=True,
                enable_lstm=False  # Set True if you have trained model
            )
        
        adapter = st.session_state.elite_adapter
        
        # Forecast button
        if st.button("🚀 Run Ensemble Forecast"):
            with st.spinner("Running ensemble (4 models)..."):
                try:
                    # Fetch multi-asset data if requested
                    multi_asset_dfs = None
                    if use_multiasset:
                        try:
                            eth_df = fetch_binance_klines('ETHUSDT', interval, min(1000, bars))
                            sol_df = fetch_binance_klines('SOLUSDT', interval, min(1000, bars))
                            multi_asset_dfs = {
                                'ETH': eth_df,
                                'SOL': sol_df
                            }
                        except Exception as e:
                            st.warning(f"Could not fetch multi-asset: {e}")
                    
                    # Get QC context if available
                    qc_context = None
                    if decision and hasattr(decision, 'extra'):
                        qc_context = decision.extra
                    
                    # Run forecast
                    if multi_asset_dfs:
                        forecast = adapter.forecast_advanced(
                            df,
                            multi_asset=multi_asset_dfs,
                            qc_payload=qc_context,
                            horizon=forecast_horizon,
                            n_paths=n_paths
                        )
                    else:
                        forecast = adapter.forecast_simple(
                            df,
                            horizon=forecast_horizon,
                            n_paths=n_paths
                        )
                    
                    # Store in session state
                    st.session_state.elite_forecast = forecast
                    st.success("✅ Forecast complete!")
                    
                except Exception as e:
                    st.error(f"Forecast failed: {e}")
                    import traceback
                    with st.expander("Error details"):
                        st.code(traceback.format_exc())
        
        # Display forecast if available
        if 'elite_forecast' in st.session_state:
            forecast = st.session_state.elite_forecast
            
            # Render
            adapter.render_in_streamlit(st, forecast, df, show_components=True)
            
            # Additional stats
            with st.expander("📊 Detailed Statistics"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**24h Forecast Distribution:**")
                    if forecast['horizon'] >= 24:
                        st.write(f"- P10: ${forecast['p10'][24]:,.0f}")
                        st.write(f"- P25: ${np.percentile(forecast['paths'][:, 24], 25):,.0f}")
                        st.write(f"- P50: ${forecast['p50'][24]:,.0f}")
                        st.write(f"- P75: ${np.percentile(forecast['paths'][:, 24], 75):,.0f}")
                        st.write(f"- P90: ${forecast['p90'][24]:,.0f}")
                        st.write(f"- Mean: ${np.mean(forecast['paths'][:, 24]):,.0f}")
                        st.write(f"- Std: ${np.std(forecast['paths'][:, 24]):,.0f}")
                
                with col2:
                    st.write("**Model Contributions:**")
                    for model, weight in forecast.get('weights_used', {}).items():
                        st.write(f"- {model}: {weight:.1%}")
                    
                    st.write(f"\n**Regime:** {forecast.get('regime', 'AUTO')}")
                    st.write(f"**Horizon:** {forecast['horizon']} bars")
            
            # Download forecast data
            with st.expander("💾 Export Forecast Data"):
                # Create export DataFrame
                export_df = pd.DataFrame({
                    'horizon': range(forecast['horizon'] + 1),
                    'p10': forecast['p10'],
                    'p50': forecast['p50'],
                    'p90': forecast['p90'],
                    'uncertainty': forecast['uncertainty']
                })
                
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"elite_forecast_{symbol}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("👆 Click 'Run Ensemble Forecast' to generate prediction")

