#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Integration - Connect Ensemble to Your v20 Dashboard

This adapter:
1. Takes your existing dashboard's DataFrame
2. Runs ensemble forecast
3. Returns results in format compatible with your display logic
4. Minimal changes to your existing code
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
from pathlib import Path

# Add forecasting module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forecasting.ensemble import EnsembleForecaster


class DashboardForecastAdapter:
    """
    Adapter between ensemble forecaster and your Streamlit dashboard
    
    Usage in your v20 dashboard:
    
    ```python
    from integration.dashboard_adapter import DashboardForecastAdapter
    
    # After you fetch df with OHLCV data:
    adapter = DashboardForecastAdapter()
    
    # Simple forecast (BTC only)
    forecast = adapter.forecast_simple(df)
    
    # Advanced forecast (with multi-asset)
    forecast = adapter.forecast_advanced(
        df_btc, 
        multi_asset={'ETH': df_eth, 'SOL': df_sol},
        qc_payload=decision.extra  # Your existing QC metrics
    )
    
    # Then render (replaces your DUDU overlay):
    adapter.render_in_streamlit(st, forecast, df)
    ```
    """
    
    def __init__(self,
                 enable_garch: bool = True,
                 enable_var: bool = True,
                 enable_lstm: bool = False):
        """
        Initialize adapter with ensemble
        
        Args:
            enable_garch: Use GARCH forecaster
            enable_var: Use VAR forecaster (needs multi-asset data)
            enable_lstm: Use LSTM (needs training first)
        """
        self.ensemble = EnsembleForecaster(
            enable_bootstrap=True,  # Always enable (your DUDU)
            enable_garch=enable_garch,
            enable_var=enable_var,
            enable_lstm=enable_lstm
        )
    
    def _extract_close_series(self, df: pd.DataFrame) -> pd.Series:
        """Extract close price series from various DataFrame formats"""
        
        # Try different column names
        for col_name in ['close', 'Close', 'CLOSE']:
            if col_name in df.columns:
                return df[col_name].astype(float)
        
        raise ValueError("DataFrame must have 'close' or 'Close' column")
    
    def forecast_simple(self,
                       df: pd.DataFrame,
                       horizon: int = 48,
                       n_paths: int = 500) -> Dict:
        """
        Simple forecast - single asset only
        
        Args:
            df: DataFrame with 'close' column
            horizon: Forecast horizon
            n_paths: Number of Monte Carlo paths
            
        Returns:
            Dict with forecast results
        """
        close = self._extract_close_series(df)
        
        # Run ensemble
        forecast = self.ensemble.forecast(
            close=close,
            horizon=horizon,
            n_paths=n_paths
        )
        
        return forecast
    
    def forecast_advanced(self,
                         df_primary: pd.DataFrame,
                         multi_asset: Optional[Dict[str, pd.DataFrame]] = None,
                         qc_payload: Optional[Dict] = None,
                         horizon: int = 48,
                         n_paths: int = 500) -> Dict:
        """
        Advanced forecast - multi-asset + regime awareness
        
        Args:
            df_primary: Primary asset DataFrame (BTC)
            multi_asset: Dict of other asset DataFrames {'ETH': df_eth, ...}
            qc_payload: Your QC metrics from decision.extra
            horizon: Forecast horizon
            n_paths: Number of paths
            
        Returns:
            Enhanced forecast dict
        """
        # Extract close series
        close = self._extract_close_series(df_primary)
        
        # Extract multi-asset closes
        multi_close = None
        if multi_asset:
            multi_close = {}
            for symbol, df in multi_asset.items():
                try:
                    multi_close[symbol] = self._extract_close_series(df)
                except Exception as e:
                    print(f"Warning: Could not extract {symbol}: {e}")
        
        # Extract regime from QC payload
        regime = None
        if qc_payload:
            # Try different keys
            codes = (qc_payload.get('qc_codes') or 
                    qc_payload.get('codes') or 
                    qc_payload.get('reason_codes') or [])
            
            # Map QC codes to regime
            if any('DRIFT_HIGH' in str(c) or 'BEAR' in str(c) for c in codes):
                regime = 'HIGH_VOL'
            elif any('STRESS' in str(c) or 'CLUSTER' in str(c) for c in codes):
                regime = 'HIGH_VOL'
            elif any('TREND' in str(c) or 'BREAKOUT' in str(c) for c in codes):
                regime = 'TRENDING'
            # Otherwise let ensemble auto-detect
        
        # Run ensemble
        forecast = self.ensemble.forecast(
            close=close,
            multi_asset=multi_close,
            regime=regime,
            horizon=horizon,
            n_paths=n_paths
        )
        
        # Add QC context
        forecast['qc_context'] = qc_payload
        
        return forecast
    
    def render_in_streamlit(self,
                           st,
                           forecast: Dict,
                           df: pd.DataFrame,
                           show_components: bool = True):
        """
        Render forecast in Streamlit
        
        Args:
            st: Streamlit module
            forecast: Forecast dict from forecast_simple/advanced
            df: Historical DataFrame (for context)
            show_components: Show individual model forecasts
        """
        import plotly.graph_objects as go
        
        close = self._extract_close_series(df)
        
        # Create figure
        fig = go.Figure()
        
        # Historical tail (visual context)
        hist_tail = close.tail(100)
        fig.add_trace(go.Scatter(
            x=np.arange(-len(hist_tail) + 1, 1),
            y=hist_tail.values,
            mode='lines',
            name='History',
            line=dict(color='black', width=2)
        ))
        
        # Future x-axis
        t = np.arange(0, forecast['horizon'] + 1)
        
        # Ensemble forecast
        fig.add_trace(go.Scatter(
            x=t,
            y=forecast['p50'],
            mode='lines',
            name='Ensemble P50',
            line=dict(color='blue', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=t,
            y=forecast['p90'],
            mode='lines',
            name='P90',
            line=dict(color='blue', width=1, dash='dash'),
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=t,
            y=forecast['p10'],
            mode='lines',
            name='P10',
            line=dict(color='blue', width=1, dash='dash'),
            fill='tonexty',
            fillcolor='rgba(0,100,255,0.2)',
            showlegend=True
        ))
        
        # Component forecasts
        if show_components and 'component_forecasts' in forecast:
            colors = {
                'Bootstrap': 'purple',
                'GARCH': 'red',
                'VAR': 'green',
                'LSTM': 'orange'
            }
            
            for name, fc in forecast['component_forecasts'].items():
                fig.add_trace(go.Scatter(
                    x=t,
                    y=fc.p50,
                    mode='lines',
                    name=f'{name} P50',
                    line=dict(color=colors.get(name, 'gray'), width=1, dash='dot'),
                    opacity=0.6
                ))
        
        # Uncertainty band (model disagreement)
        if 'uncertainty' in forecast:
            upper_uncertainty = forecast['p50'] + forecast['uncertainty']
            lower_uncertainty = forecast['p50'] - forecast['uncertainty']
            
            fig.add_trace(go.Scatter(
                x=t,
                y=upper_uncertainty,
                mode='lines',
                name='Uncertainty',
                line=dict(color='orange', width=0),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=t,
                y=lower_uncertainty,
                mode='lines',
                name='Uncertainty',
                line=dict(color='orange', width=0),
                fill='tonexty',
                fillcolor='rgba(255,165,0,0.1)',
                showlegend=True
            ))
        
        # Layout
        fig.update_layout(
            title=f"Elite Ensemble Forecast (Regime: {forecast.get('regime', 'AUTO')})",
            xaxis_title="Bars ahead (0 = now)",
            yaxis_title="Price",
            height=550,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "24h P50",
                f"${forecast['p50'][24]:,.0f}" if forecast['horizon'] >= 24 else "N/A",
                delta=f"{((forecast['p50'][24] / forecast['last_price']) - 1) * 100:+.1f}%" if forecast['horizon'] >= 24 else None
            )
        
        with col2:
            st.metric(
                "Regime",
                forecast.get('regime', 'AUTO')
            )
        
        with col3:
            uncertainty_pct = (forecast['uncertainty'][24] / forecast['last_price']) * 100 if forecast['horizon'] >= 24 else 0
            st.metric(
                "Uncertainty",
                f"{uncertainty_pct:.1f}%"
            )
        
        with col4:
            n_models = len(forecast.get('component_forecasts', {}))
            st.metric(
                "Models",
                f"{n_models}/4"
            )
        
        # Model weights
        if 'weights_used' in forecast:
            with st.expander("🎚️ Model Weights & Details"):
                st.write("**Weights Applied:**")
                for model, weight in forecast['weights_used'].items():
                    st.write(f"- {model}: {weight:.1%}")
                
                st.write("**Component Forecasts (24h):**")
                for name, fc in forecast.get('component_forecasts', {}).items():
                    if forecast['horizon'] >= 24:
                        st.write(f"- {name}: ${fc.p50[24]:,.0f} (confidence: {fc.confidence:.1%})")


# =============================================================================
# QUICK INTEGRATION EXAMPLE
# =============================================================================

def example_integration_code():
    """
    Copy-paste this into your v20 dashboard
    """
    code = '''
# ========================================
# ADD TO YOUR v20 DASHBOARD
# ========================================

# 1. At top of file, add import:
from integration.dashboard_adapter import DashboardForecastAdapter

# 2. After you create tabs, add a new tab for elite forecast:
tab1, tab2, tab_events, tab_qc, tab_elite, tab3, tab4 = st.tabs([
    "📈 Market", 
    "🧠 Signal + Policy", 
    "🛰️ Events", 
    "🫧🧬 QC",
    "🎯 Elite Forecast",  # NEW
    "🛰️ Drift + Quality", 
    "⚙️ Raw"
])

# 3. In the new elite tab, add:
with tab_elite:
    st.subheader("🎯 Elite Ensemble Forecast")
    
    # Initialize adapter (cache it)
    if 'elite_adapter' not in st.session_state:
        st.session_state.elite_adapter = DashboardForecastAdapter(
            enable_garch=True,
            enable_var=True,
            enable_lstm=False
        )
    
    adapter = st.session_state.elite_adapter
    
    # Forecast
    with st.spinner("Running ensemble forecast..."):
        try:
            # Simple version (BTC only):
            forecast = adapter.forecast_simple(df, horizon=48)
            
            # OR Advanced version (with multi-asset):
            # multi_asset_dfs = {
            #     'ETH': fetch_binance_klines('ETHUSDT', interval, bars),
            #     'SOL': fetch_binance_klines('SOLUSDT', interval, bars)
            # }
            # forecast = adapter.forecast_advanced(
            #     df, 
            #     multi_asset=multi_asset_dfs,
            #     qc_payload=decision.extra if decision else None
            # )
            
            # Render
            adapter.render_in_streamlit(st, forecast, df)
            
        except Exception as e:
            st.error(f"Forecast failed: {e}")
            import traceback
            st.code(traceback.format_exc())

# That's it! Your v20 dashboard now has elite forecasting.
'''
    return code


if __name__ == '__main__':
    print("\n" + "="*60)
    print("DASHBOARD INTEGRATION CODE")
    print("="*60)
    print(example_integration_code())
    print("="*60)
