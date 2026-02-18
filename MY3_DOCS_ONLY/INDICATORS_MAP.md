# MY3 — Indicators Map (ULTRA v15 + ULTRA v19 + Alpha v9 + Engine v8b)

This document is a **ground-truth map** of what your **current MY3 stack** uses *in practice*.
It separates **LIVE / PROXY / PLANNED** so you always know what’s real vs. aspirational.

**Scope (only):**
- ULTRA v15: `ultimate_dashboard_ULTRA_ML_v15_QC_FLOW_STRUCTURE_KEEP_PACE.py`
- ULTRA v19: `ultimate_dashboard_ULTRA_ML_v19_QC_TRUECVD_FLOW_STRUCTURE_ELITE_PROJECTION.py`
- ALPHA v9: `alpha_stack_pro_v3_4_whale_online_v9.py`
- ENGINE: `quant_war_room_ml_pro_ONEFILE_v8b_spot_eventbias_QC_DIFF_CORR_TRUECVD.py`

**Status legend**
- **LIVE**: computed from real-time market feeds available to the app (e.g., Binance OHLCV, order book / trades when connected).
- **PROXY**: approximated from OHLCV because the intended data feed is missing.
- **PLANNED**: described in the architecture/vision but not active in MY3 yet.

---

## Layer 0 — Data Inputs

| Input | Intended source | Current MY3 source | Status | Used in |
|---|---|---:|:---:|---|
| OHLCV (price, volume) | Binance | Binance (or proxy fetch) | **LIVE** | All layers |
| Order book depth | Binance | sometimes missing → fallback | **PROXY/LIVE** | QC Flow (imbalance) |
| Agg trades (market orders) | Binance | sometimes missing → fallback | **PROXY/LIVE** | TRUECVD / CVD |
| On-chain (netflow, whales, SOPR) | Glassnode/CryptoQuant/etc | **not wired in** | **PLANNED** | Diffusion vision |
| Macro series (rates, spreads, DXY proxy) | FRED / market data | optional / not guaranteed | **PLANNED/OPTIONAL** | Overlays |
| News/events (NLP sentiment) | RSS/APIs | heuristic tags only | **PLANNED** | Event bias |

---

## Layer 1 — Diffusion / Liquidity (QC Flow)

| Indicator | Definition (operational) | Status in MY3 | Feeds / Notes | Consumed by |
|---|---|:---:|---|---|
| **Diffusion Score (0–100)** | composite anomaly score from flow features | **LIVE/PROXY** | when engine payload missing → local OHLCV proxy | QC codes + Policy |
| **Book Imbalance** | (bid−ask)/(bid+ask) across top levels | **LIVE/PROXY** | if book feed missing → proxy estimate | QC + Policy |
| **Netflow Z (proxy)** | z-score of “flow proxy” | **PROXY** | should be on-chain netflow; currently OHLCV proxy | QC codes |
| **Whale Accum (proxy)** | proxy for smart accumulation | **PROXY** | should be whale wallets / exchange outflows | QC codes |
| **TRUECVD / CVD** | cumulative volume delta from trades | **LIVE/PROXY** | true only when aggTrades enabled; otherwise proxy | Projection + QC |

**QC Codes (examples seen):**
- `DIFF_NEUTRAL`, `DIFF_POS`, `DIFF_NEG`
- `EVENT_*` (bias tags)
- `DRIFT_HIGH` (model drift)

---

## Layer 2 — Structure / Protein (QC Structure)

| Indicator | Definition (operational) | Status | Notes | Consumed by |
|---|---|:---:|---|---|
| **Coherence (|corr| mean)** | mean absolute rolling correlation across assets | **LIVE** (if assets_n>1) | with 1 asset becomes near-zero/noisy | QC codes |
| **Corr Break (short−long)** | delta between short/long correlation regimes | **LIVE** (if multi-asset) | helps detect regime shifts | QC + Policy |
| **assets_n** | number of assets in structure calc | **LIVE** | if 1 → structure layer limited | QC |

**Not yet implemented (Protein “full”):**
- Rolling correlation matrix as first-class object (**PLANNED**)
- PCA factors (PC1/PC2 + explained variance) (**PLANNED**)
- Network centrality (graph-based leaders) (**PLANNED**)

---

## Layer 3 — Chaos / Stress (Module C)

| Indicator | Definition | Status | Thresholds | Consumed by |
|---|---|:---:|---|---|
| **Violence v** | `TR / ATR(14)` | **LIVE** | `>2.0 VIOLENT`, `>3.2 EXTREME` | Stress Gate |
| **Vol clustering (proxy)** | persistence of high v/vol | **LIVE/PROXY** | used to label clusters | Policy + Projection |
| **Stress Gate** | hard block on adds/leverage | **LIVE** | triggered by EXTREME/cluster | Policy |

---

## Layer 4 — Execution Modules (A–D)

### Module A — Breakout / Acceptance
| Signal | Definition | Status |
|---|---|:---:|
| Breakout | `Close > High(N=60)` (or equivalent) | **LIVE** |
| Retest / Acceptance | holds level without violating structure | **LIVE** |

### Module B — Absorption
| Signal | Definition | Status |
|---|---|:---:|
| Dip Buy Ratio | buy strength / sell strength; absorption if `>1.3` | **LIVE** |
| Recovery Speed | recovers X% within Y bars/days | **LIVE** |

### Module D — Trend Health
| Signal | Definition | Status |
|---|---|:---:|
| SMA50 slope | slope(SMA50) must be positive for trend-ok | **LIVE** |
| Market structure | HH/HL logic over lookback window | **LIVE** |

---

## Projection (DUDU + Elite)

| Component | What it does | Status | Notes |
|---|---|:---:|---|
| DUDU Cone | baseline `mu/sigma` cone | **LIVE** | used as base projection |
| Bootstrap | iid historical returns sampling | **LIVE** | ensemble member |
| EWMA | recent-weighted volatility | **LIVE** | ensemble member |
| GARCH proxy | volatility clustering model | **LIVE** | ensemble member |
| Fat tails (Student‑t) | heavy-tail scenarios | **LIVE** | ensemble member |
| Regimes-lite | assigns regime + weights ensemble | **LIVE** | outputs probabilities |

---

## Policy Outputs (what you actually act on)

| Output | Meaning | Status | Notes |
|---|---|:---:|---|
| **Action** | `HOLD / REDUCE_x / ADD_SMALL / WAIT` | **LIVE** | ladder constrained by gates |
| **Policy State** | aligned with action | **LIVE** | e.g., `REDUCE` |
| **P(up)** | probability up (if model healthy) | **LIVE/NA** | may be NaN when missing model head |
| **EV (proxy)** | expected value proxy | **LIVE/NA** | may be NaN when missing |
| **Reasons / QC codes** | why action chosen | **LIVE** | human-readable summary |

---

## What’s “science” vs “story” (strict)

**Science that is already operational in MY3 (today):**
- Stress/Violence gating (TR/ATR + clusters)
- A–D execution logic
- probabilistic projection (ensemble + tails + regimes-lite)
- QC flow/structure (with proxy fallbacks)

**Science that is still *vision* until data feeds are wired:**
- True on-chain diffusion (netflow/whale wallets/SOPR)
- Full protein layer (PCA + network centrality)
- NLP-driven event bias beyond heuristics
