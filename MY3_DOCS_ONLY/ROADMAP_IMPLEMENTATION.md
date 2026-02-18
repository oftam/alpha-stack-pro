# MY3 — Roadmap Implementation (only v15 + v19 + Alpha v9 + Engine v8b)

Goal: turn the current, already-strong system into a **verifiable, institutional-grade** stack by
1) wiring missing data feeds,
2) making every module measurable,
3) proving edge via walk-forward + calibration + costed PnL.

---

## Phase 1 — Stabilize & “Truth Table” (1–2 sessions)

### 1.1 Freeze the working MY3 set
**Do not edit** the dashboards/engine in-place. Work only via new modules + config flags.

Deliverables:
- `MY3_RUNBOOK.md` (how to run + ports + troubleshooting)
- `INDICATORS_MAP.md` (already produced)

### 1.2 Confidence ladder everywhere (no silent PROXY)
Make the system print and log:
- `DATA_TIER = LIVE / PROXY / DISABLED`
- `CONFIDENCE_MULT` (e.g., 1.0, 0.6, 0.2)

Acceptance criteria:
- No more hidden NaNs
- Every QC metric has “source tag”
- Policy output includes `confidence_level`

---

## Phase 2 — Diffusion LIVE (Microstructure first) (2–4 sessions)

### 2.1 Binance microstructure feed
Implement:
- orderbook top N depth
- aggTrades stream (or polling)
- TRUECVD from trades
- robust rate-limit & retry

Deliverable module:
- `diffusion_live_binance.py` (self-contained)
- cache layer `cache_store.py` (simple local cache)

Why this first:
- It gives “pre-price” signals **without** paying for on-chain providers.

Acceptance criteria:
- `Book Imbalance` becomes **LIVE**
- `TRUECVD` becomes **LIVE**
- `Diffusion Score` uses these features by default
- fallback to OHLCV proxy is explicit

### 2.2 On-chain integration (optional but recommended)
Options:
- Glassnode / CryptoQuant / similar provider

Deliverables:
- `onchain_provider.py` adapter
- `netflow`, `whale wallets`, `SOPR` feeds
- timestamp alignment tests

Acceptance criteria:
- `Netflow Z` becomes **LIVE**
- `Whale Accum` becomes **LIVE**
- QC no longer depends on proxy for flow

---

## Phase 3 — Protein Layer (PCA + Network) (2–5 sessions)

### 3.1 Multi-asset frame
Standard set (v1):
- BTC, ETH (optional), SPY, GLD, DXY proxy, 10Y/2Y yields (or ETFs)

Deliverable:
- `macro_universe.py` (download, align, resample)

Acceptance criteria:
- assets_n >= 4 most of the time
- missing asset handling is clean

### 3.2 PCA + centrality
Deliverable:
- `protein_layer.py`
Outputs:
- `PC1, PC2, explained_variance`
- `CorrStress`
- `LeaderCentrality`

Policy hooks:
- if `CorrStress↑` → tighten gates / reduce ladder
- if `PC1 risk-off` + `BEAR` → reduce exposure
- if leader is `DXY` and rising sharply → risk-off bias

Acceptance criteria:
- new tab “🧬 Protein”
- policy prints what protein signals contributed

---

## Phase 4 — Walk-Forward Backtester + LIVE Scoreboard (the proof) (3–8 sessions)

This is the “no-BS” phase: we prove the edge.

### 4.1 Dataset builder
Input: OHLCV (+ microstructure + protein + event bias)
Output: feature table + label
- label options:
  - forward return (regression)
  - event label (classification) e.g., `return_{t+H} > threshold`

Deliverable:
- `dataset_builder.py`

### 4.2 Walk-forward training + evaluation
Rolling windows:
- train W, test T, step S

Metrics:
- AUC
- Brier (calibration)
- Precision@TopK
- Costed PnL (fees + slippage)

Deliverable:
- `walkforward.py`
- `scoreboard_store.json` (latest OOS metrics)

### 4.3 Calibration
Methods:
- isotonic
- Platt scaling
Deliverable:
- `calibration.py`

Acceptance criteria:
- v20 “LIVE Scoreboard” is real (not placeholder)
- dashboard shows time series of OOS metrics
- automated alerts on degradation

---

## Phase 5 — Signal-to-Trade Engine (execution realism) (2–6 sessions)

Not just “signals”: trades with EV, stop/target, sizing.

Deliverables:
- `trade_engine.py`
- `position_sizer.py`
- `risk_model.py`

Rules:
- EV > 0 after costs
- sizing based on calibrated probability and drawdown constraints
- stop/target based on volatility regime

Acceptance criteria:
- paper-trade mode
- logs every decision (audit trail)

---

## Phase 6 — Events & NLP (bias, not dictatorship) (optional) (2–6 sessions)

Principle:
- events should **bias** risk, not override price/flow

Deliverables:
- `events_rss.py` (reliable sources)
- `nlp_scoring.py` (lightweight scoring)
- `event_persistence.py` (noise vs regime change)

Acceptance criteria:
- event bias modifies `confidence_mult` and `risk_gate`
- zero “headline whipsaw” (requires persistence)

---

## Test Suite (runs every time)

Must-have tests:
- label leakage
- time ordering
- NaNs / infs
- feature availability by tier
- backtest determinism

Deliverable:
- `tests/` + `pytest` entrypoint

---

## Decision: “My3 first, then expand”
We will keep MY3 clean and stable.
New capabilities go into **new modules** + **toggle flags**, never random edits to working dashboards.
