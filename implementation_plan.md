# Implementation Plan - Manifold DNA / DUDU Overlay Integration

## Goal Description
Integrate the "Manifold DNA Score / DUDU Overlay" graph into the `elite_v20_dashboard_MEDALLION.py`. This graph is defined as the "Projection Dashboard" in the user request and includes:
1.  **Past**: Regime Filter (using historical data matching the current regime).
2.  **Present**: Volatility Cone (Physics/Sigma bands).
3.  **Future**: Probability Cloud (Bootstrap P10/P50/P90 paths).

## User Review Required
> [!IMPORTANT]
> The "Manifold DNA Score" graph described in the text header ("function of time") seems to refer to the **DUDU Overlay** (Price vs Time with overlays) based on the detailed breakdown in the prompt. I am proceeding with the **DUDU Overlay (Price Projection)** implementation as the primary visual.

## Proposed Changes

### [Root Directory]

#### [MODIFY] [dudu_overlay.py](file:///c:/Users/ofirt/Documents/alpha-stack-pro/dudu_overlay.py)
*   Update `render_projection_tab` to accept a `current_regime` string directly, bypassing the `qc_payload` parsing if already provided.
*   Ensure the function is robust to missing data.

#### [MODIFY] [elite_v20_dashboard_MEDALLION.py](file:///c:/Users/ofirt/Documents/alpha-stack-pro/elite_v20_dashboard_MEDALLION.py)
*   **Import**: Add `from dudu_overlay import render_projection_tab`.
*   **Layout**: Add a new section **"Manifold Projection (Past/Present/Future)"** immediately after the key metrics (cols 1-4) and before the "System Status".
*   **Data Passing**: Call `render_projection_tab` passing:
    *   `st`: The streamlit module.
    *   `df`: The DataFrame with 'close' prices (already fetched).
    *   `current_regime`: The `regime` variable determined by `elite_adapter`.
    *   `horizon`: 48 (as requested/default).

## Verification Plan

### Automated Tests
*   Run the dashboard locally using `streamlit run elite_v20_dashboard_MEDALLION.py`.
*   Verify that `dudu_overlay.py` functions (unit test style) return valid objects (e.g., `build_vol_cone` returns dict with bands).

### Manual Verification
*   Launch the dashboard.
*   Check if the "Manifold Projection" graph appears.
*   Verify it shows:
    *   Historical price tail.
    *   Cone bands (dotted lines).
    *   Future paths (clouds/lines).
    *   P10/P50/P90 lines.
*   Verify the title/regime matches the dashboard calculation.
