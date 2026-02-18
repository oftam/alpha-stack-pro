#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 DUDU PROGRESSION DASHBOARD
Full visualization of 14 psychological market phases

Run: streamlit run dudu_progression_dashboard.py --server.port 8503
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dudu_progression import DuduProgression, PSYCHOLOGICAL_PHASES


st.set_page_config(
    page_title="Dudu Progression - Market Psychology",
    page_icon="🎨",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .phase-card {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid;
        text-align: center;
    }
    .current-phase {
        animation: pulse 2s infinite;
        box-shadow: 0 0 20px;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .target-price {
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def create_progression_chart(dudu: DuduProgression, 
                             current_price: float,
                             current_phase,
                             df: pd.DataFrame):
    """Create beautiful progression chart with all phases"""
    
    targets = dudu.calculate_targets(current_price, current_phase)
    
    # Create figure
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=('Market Psychology Cycle', 'Sentiment Progression'),
        vertical_spacing=0.1
    )
    
    # Phase progression line
    phases_x = list(range(len(dudu.phases)))
    phases_y = [targets[p.name] for p in dudu.phases]
    phases_colors = [p.color for p in dudu.phases]
    phases_names = [f"{p.emoji} {p.name}" for p in dudu.phases]
    
    # Add main progression line
    fig.add_trace(
        go.Scatter(
            x=phases_x,
            y=phases_y,
            mode='lines+markers',
            name='Price Progression',
            line=dict(width=3, color='white'),
            marker=dict(
                size=15,
                color=phases_colors,
                line=dict(width=2, color='white')
            ),
            text=phases_names,
            hovertemplate='<b>%{text}</b><br>Target: $%{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Highlight current phase
    current_idx = next(i for i, p in enumerate(dudu.phases) if p.name == current_phase.name)
    
    fig.add_trace(
        go.Scatter(
            x=[current_idx],
            y=[current_price],
            mode='markers',
            name='Current Position',
            marker=dict(
                size=25,
                color='yellow',
                symbol='star',
                line=dict(width=3, color='red')
            ),
            text=[f"{current_phase.emoji} {current_phase.name}<br>NOW"],
            hovertemplate='<b>%{text}</b><br>Price: $%{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Add key level lines
    angola_price = targets['Angola']
    euphoria_price = targets['Euphoria']
    
    fig.add_hline(
        y=angola_price,
        line_dash="dash",
        line_color="red",
        annotation_text="💀 Angola (Capitulation)",
        row=1, col=1
    )
    
    fig.add_hline(
        y=euphoria_price,
        line_dash="dash",
        line_color="cyan",
        annotation_text="🎉 Euphoria (Top)",
        row=1, col=1
    )
    
    fig.add_hline(
        y=current_price,
        line_dash="dot",
        line_color="yellow",
        annotation_text=f"Current: ${current_price:,.0f}",
        row=1, col=1
    )
    
    # Sentiment progression (row 2)
    sentiments = [p.sentiment_score for p in dudu.phases]
    
    fig.add_trace(
        go.Bar(
            x=phases_x,
            y=sentiments,
            name='Sentiment',
            marker=dict(
                color=sentiments,
                colorscale='RdYlGn',
                cmin=-100,
                cmax=100,
                showscale=True,
                colorbar=dict(title="Sentiment", y=0.15, len=0.3)
            ),
            text=[p.emoji for p in dudu.phases],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Sentiment: %{y}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
        hovermode='x unified'
    )
    
    # Update axes
    fig.update_xaxes(
        ticktext=phases_names,
        tickvals=phases_x,
        tickangle=45,
        showgrid=True,
        gridcolor='#1e1e1e',
        row=1, col=1
    )
    
    fig.update_xaxes(
        ticktext=[p.name for p in dudu.phases],
        tickvals=phases_x,
        tickangle=45,
        showgrid=True,
        gridcolor='#1e1e1e',
        row=2, col=1
    )
    
    fig.update_yaxes(
        title="Price (USD)",
        showgrid=True,
        gridcolor='#1e1e1e',
        row=1, col=1
    )
    
    fig.update_yaxes(
        title="Sentiment",
        range=[-110, 110],
        showgrid=True,
        gridcolor='#1e1e1e',
        row=2, col=1
    )
    
    return fig


def create_vol_cone_chart(vol_cone: dict):
    """Create volatility cone visualization"""
    
    fig = go.Figure()
    
    t = np.arange(0, vol_cone['horizon'] + 1)
    current_price = vol_cone['current_price']
    
    # Add bands
    for sigma in [3, 2, 1]:
        lower, upper = vol_cone['bands'][sigma]
        
        # Upper band
        fig.add_trace(go.Scatter(
            x=t,
            y=upper,
            mode='lines',
            name=f'{sigma}σ Upper',
            line=dict(width=1, dash='dash'),
            showlegend=True
        ))
        
        # Lower band
        fig.add_trace(go.Scatter(
            x=t,
            y=lower,
            mode='lines',
            name=f'{sigma}σ Lower',
            line=dict(width=1, dash='dash'),
            fill='tonexty' if sigma == 1 else None,
            showlegend=True
        ))
    
    # Current price line
    fig.add_trace(go.Scatter(
        x=t,
        y=[current_price] * len(t),
        mode='lines',
        name='Current Price',
        line=dict(width=2, color='yellow')
    ))
    
    fig.update_layout(
        title="Volatility Cone Projection",
        xaxis_title="Periods Ahead",
        yaxis_title="Price (USD)",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig


def main():
    st.title("🎨 Dudu Progression - Market Psychology Cycle")
    st.markdown("### 14 Phases from Angola (Despair) to Euphoria (Greed)")
    
    # Initialize Dudu
    dudu = DuduProgression()
    
    # Sidebar inputs
    with st.sidebar:
        st.header("📊 Current Market State")
        
        current_price = st.number_input(
            "Current BTC Price",
            min_value=1000,
            max_value=1000000,
            value=98000,
            step=1000
        )
        
        price_change = st.slider(
            "% Change from Recent Low",
            min_value=-50.0,
            max_value=150.0,
            value=15.0,
            step=5.0
        )
        
        fear_greed = st.slider(
            "Fear & Greed Index",
            min_value=0,
            max_value=100,
            value=50
        )
        
        vol_percentile = st.slider(
            "Volatility Percentile",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=5.0
        )
        
        st.markdown("---")
        
        horizon = st.slider(
            "Projection Horizon (days)",
            min_value=10,
            max_value=180,
            value=48
        )
    
    # Detect current phase
    current_phase = dudu.detect_current_phase(
        price_change_pct=price_change,
        fear_greed=fear_greed,
        volatility_percentile=vol_percentile
    )
    
    # Display current phase (big banner)
    st.markdown(f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, {current_phase.color}40 0%, {current_phase.color}20 100%); border-radius: 15px; border: 3px solid {current_phase.color}; margin: 20px 0;">
        <h1 style="font-size: 48px; margin: 0;">{current_phase.emoji}</h1>
        <h2 style="margin: 10px 0;">{current_phase.name}</h2>
        <h3 style="margin: 5px 0; color: #aaa;">{current_phase.hebrew_name}</h3>
        <p style="font-size: 18px; margin: 15px 0;">{current_phase.description}</p>
        <div style="font-size: 24px; font-weight: bold; margin-top: 15px;">
            Sentiment: {current_phase.sentiment_score:+.0f}/100
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Progression Chart",
        "🎯 Target Prices",
        "📊 Vol Cone",
        "📚 Phase Guide"
    ])
    
    # Generate sample price data for vol cone
    dates = pd.date_range(end=datetime.now(), periods=200, freq='1h')
    prices = current_price + np.cumsum(np.random.randn(200) * 500)
    df = pd.DataFrame({'close': prices}, index=dates)
    
    with tab1:
        st.subheader("Market Psychology Progression")
        
        fig = create_progression_chart(dudu, current_price, current_phase, df)
        st.plotly_chart(fig, use_container_width=True)
        
        # Key insights
        col1, col2, col3 = st.columns(3)
        
        targets = dudu.calculate_targets(current_price, current_phase)
        
        with col1:
            st.metric(
                "💀 Angola (Bottom)",
                f"${targets['Angola']:,.0f}",
                f"{(targets['Angola']/current_price - 1)*100:+.1f}%"
            )
        
        with col2:
            st.metric(
                "🎉 Euphoria (Top)",
                f"${targets['Euphoria']:,.0f}",
                f"{(targets['Euphoria']/current_price - 1)*100:+.1f}%"
            )
        
        with col3:
            range_pct = (targets['Euphoria'] / targets['Angola'] - 1) * 100
            st.metric(
                "Full Cycle Range",
                f"{range_pct:.0f}%",
                "Angola → Euphoria"
            )
    
    with tab2:
        st.subheader("🎯 Target Prices for All Phases")
        
        targets = dudu.calculate_targets(current_price, current_phase)
        
        # Create 2 columns for phases
        col1, col2 = st.columns(2)
        
        for i, phase in enumerate(dudu.phases):
            target = targets[phase.name]
            change_pct = (target / current_price - 1) * 100
            
            is_current = (phase.name == current_phase.name)
            
            card_html = f"""
            <div class="phase-card {'current-phase' if is_current else ''}" style="border-color: {phase.color}; background: {phase.color}20;">
                <div style="font-size: 36px;">{phase.emoji}</div>
                <div style="font-size: 20px; font-weight: bold; margin: 10px 0;">{phase.name}</div>
                <div style="font-size: 14px; color: #aaa; margin: 5px 0;">{phase.hebrew_name}</div>
                <div class="target-price" style="color: {phase.color};">${target:,.0f}</div>
                <div style="font-size: 16px; {'color: lime;' if change_pct > 0 else 'color: red;'}">{change_pct:+.1f}%</div>
                {'<div style="margin-top: 10px; font-weight: bold; color: yellow;">📍 YOU ARE HERE</div>' if is_current else ''}
            </div>
            """
            
            if i % 2 == 0:
                col1.markdown(card_html, unsafe_allow_html=True)
            else:
                col2.markdown(card_html, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("📊 Volatility Cone Projection")
        
        vol_cone = dudu.build_vol_cone(df['close'], current_phase, horizon=horizon)
        
        fig_cone = create_vol_cone_chart(vol_cone)
        st.plotly_chart(fig_cone, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Base Volatility", f"{vol_cone['base_vol']*100:.2f}%")
        
        with col2:
            st.metric("Phase Volatility", f"{vol_cone['phase_vol']*100:.2f}%")
        
        with col3:
            st.metric("Multiplier", f"{current_phase.volatility_multiplier:.1f}x")
    
    with tab4:
        st.subheader("📚 Complete Phase Guide")
        
        for phase in dudu.phases:
            with st.expander(f"{phase.emoji} {phase.name} - {phase.hebrew_name}"):
                st.markdown(dudu.get_phase_summary(phase))
                
                # Add target info
                target = targets[phase.name]
                change_pct = (target / current_price - 1) * 100
                
                st.markdown(f"""
                **Target Price:** ${target:,.0f} ({change_pct:+.1f}% from current)
                
                **When to expect this:**
                {_get_timing_hint(phase, current_phase)}
                """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🎨 Dudu Progression v2.0 - Full Psychological Cycle Mapping</p>
        <p>Based on historical market psychology patterns and behavioral finance research</p>
    </div>
    """, unsafe_allow_html=True)


def _get_timing_hint(phase, current_phase):
    """Estimate when we might reach this phase"""
    
    current_idx = next(i for i, p in enumerate(PSYCHOLOGICAL_PHASES) if p.name == current_phase.name)
    target_idx = next(i for i, p in enumerate(PSYCHOLOGICAL_PHASES) if p.name == phase.name)
    
    phases_away = (target_idx - current_idx) % len(PSYCHOLOGICAL_PHASES)
    
    if phases_away == 0:
        return "**Now** - This is your current phase"
    elif phases_away <= 3:
        return f"**Near-term** - Approximately {phases_away * 30} days away ({phases_away} phases)"
    elif phases_away <= 7:
        return f"**Medium-term** - Approximately {phases_away * 30} days away ({phases_away} phases)"
    else:
        return f"**Long-term** - Approximately {phases_away * 30} days away ({phases_away} phases)"


if __name__ == '__main__':
    main()
