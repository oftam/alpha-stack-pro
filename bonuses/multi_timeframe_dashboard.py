#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ELITE v20 - MULTI-TIMEFRAME DASHBOARD
Confluence detection across 1H, 4H, 1D timeframes

BONUS #2 - Enhanced market perspective
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List


class MultiTimeframeDashboard:
    """
    Analyzes and displays Elite signals across multiple timeframes
    
    Features:
    - Confluence detection
    - Visual heatmap
    - Alert priority system
    - Optimal entry timing
    """
    
    def __init__(self):
        self.timeframes = ['1h', '4h', '1d']
        self.signals_cache = {}
    
    # =========================================================================
    # CONFLUENCE ANALYSIS
    # =========================================================================
    
    def analyze_confluence(self, 
                          manifold_1h: float,
                          manifold_4h: float,
                          manifold_1d: float,
                          confidence_1h: float,
                          confidence_4h: float,
                          confidence_1d: float) -> Dict:
        """
        Detect signal agreement across timeframes
        
        Strong confluence = multiple TFs showing same direction
        """
        
        # Scoring system
        scores = {
            '1h': manifold_1h * confidence_1h,
            '4h': manifold_4h * confidence_4h,
            '1d': manifold_1d * confidence_1d
        }
        
        # Check agreement (all bullish or all bearish)
        bullish_count = sum(1 for s in scores.values() if s > 55)
        bearish_count = sum(1 for s in scores.values() if s < 45)
        
        if bullish_count == 3:
            confluence = "STRONG_BULLISH"
            strength = 95
            priority = "🔥 HIGHEST"
        elif bullish_count == 2:
            confluence = "MODERATE_BULLISH"
            strength = 70
            priority = "⚡ HIGH"
        elif bearish_count == 3:
            confluence = "STRONG_BEARISH"
            strength = 95
            priority = "🔥 HIGHEST (SHORT)"
        elif bearish_count == 2:
            confluence = "MODERATE_BEARISH"
            strength = 70
            priority = "⚡ HIGH (SHORT)"
        else:
            confluence = "MIXED"
            strength = 40
            priority = "⏸️ WAIT"
        
        # Weighted average (higher TF = more weight)
        weighted_score = (
            scores['1h'] * 0.2 +
            scores['4h'] * 0.3 +
            scores['1d'] * 0.5
        )
        
        return {
            'confluence': confluence,
            'strength': strength,
            'priority': priority,
            'weighted_score': weighted_score,
            'agreement': f"{max(bullish_count, bearish_count)}/3",
            'recommendation': self._generate_confluence_recommendation(
                confluence, strength
            )
        }
    
    def _generate_confluence_recommendation(self,
                                           confluence: str,
                                           strength: float) -> str:
        """Generate actionable recommendation"""
        
        if "STRONG" in confluence:
            if "BULLISH" in confluence:
                return (
                    "✅ STRONG BUY SIGNAL\n"
                    "All timeframes aligned bullish\n"
                    "→ Full position size recommended"
                )
            else:
                return (
                    "⚠️ STRONG BEARISH\n"
                    "All timeframes aligned bearish\n"
                    "→ Stay in cash or consider short"
                )
        
        elif "MODERATE" in confluence:
            if "BULLISH" in confluence:
                return (
                    "✅ MODERATE BUY\n"
                    "2/3 timeframes bullish\n"
                    "→ Half position or wait for 1H confirmation"
                )
            else:
                return (
                    "⚠️ MODERATE BEARISH\n"
                    "2/3 timeframes bearish\n"
                    "→ Reduce exposure or wait"
                )
        
        else:
            return (
                "⏸️ MIXED SIGNALS\n"
                "Timeframes not aligned\n"
                "→ Wait for clarity before entering"
            )
    
    # =========================================================================
    # VISUAL HEATMAP
    # =========================================================================
    
    def create_confluence_heatmap(self, 
                                 signals_data: Dict) -> go.Figure:
        """
        Create visual heatmap showing confluence across timeframes
        
        Args:
            signals_data: Dict with keys ['1h', '4h', '1d']
                         each containing manifold, confidence, regime
        """
        
        # Prepare data for heatmap
        timeframes = ['1H', '4H', '1D']
        metrics = ['Manifold', 'Confidence', 'Diffusion', 'Overall']
        
        # Build matrix
        z_data = []
        for metric in metrics:
            row = []
            for tf in ['1h', '4h', '1d']:
                if metric == 'Manifold':
                    val = signals_data[tf].get('manifold', 50)
                elif metric == 'Confidence':
                    val = signals_data[tf].get('confidence', 0.5) * 100
                elif metric == 'Diffusion':
                    val = signals_data[tf].get('diffusion', 50)
                else:  # Overall
                    val = (
                        signals_data[tf].get('manifold', 50) * 0.4 +
                        signals_data[tf].get('confidence', 0.5) * 100 * 0.3 +
                        signals_data[tf].get('diffusion', 50) * 0.3
                    )
                row.append(val)
            z_data.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=timeframes,
            y=metrics,
            colorscale=[
                [0, 'red'],
                [0.5, 'yellow'],
                [1, 'green']
            ],
            text=[[f"{val:.1f}" for val in row] for row in z_data],
            texttemplate="%{text}",
            textfont={"size": 16, "color": "white"},
            colorbar=dict(title="Score"),
            hoverongaps=False
        ))
        
        fig.update_layout(
            title="📊 Multi-Timeframe Confluence Heatmap",
            xaxis_title="Timeframe",
            yaxis_title="Metric",
            height=400
        )
        
        return fig
    
    # =========================================================================
    # ALERT PRIORITY SYSTEM
    # =========================================================================
    
    def calculate_alert_priority(self,
                                signals_data: Dict) -> List[Dict]:
        """
        Rank signals by priority based on confluence and strength
        
        Returns list of alerts ordered by priority
        """
        
        alerts = []
        
        # Check each timeframe
        for tf in self.timeframes:
            data = signals_data.get(tf, {})
            
            manifold = data.get('manifold', 50)
            confidence = data.get('confidence', 0.5)
            diffusion = data.get('diffusion', 50)
            
            # Calculate composite score
            composite = manifold * 0.4 + confidence * 100 * 0.3 + diffusion * 0.3
            
            # Determine signal type
            if composite > 70:
                signal_type = "BULLISH"
                emoji = "🟢"
            elif composite < 30:
                signal_type = "BEARISH"
                emoji = "🔴"
            else:
                signal_type = "NEUTRAL"
                emoji = "⚪"
                continue  # Skip neutral signals
            
            # Priority calculation
            if composite > 85:
                priority = 1  # Highest
                priority_label = "🔥 URGENT"
            elif composite > 70 or composite < 15:
                priority = 2  # High
                priority_label = "⚡ HIGH"
            elif composite > 60 or composite < 25:
                priority = 3  # Medium
                priority_label = "📊 MEDIUM"
            else:
                priority = 4  # Low
                priority_label = "💤 LOW"
                continue  # Skip low priority
            
            alerts.append({
                'timeframe': tf.upper(),
                'priority': priority,
                'priority_label': priority_label,
                'signal_type': signal_type,
                'composite_score': composite,
                'emoji': emoji,
                'manifold': manifold,
                'confidence': confidence * 100,
                'diffusion': diffusion,
                'message': self._generate_alert_message(
                    tf, signal_type, composite
                )
            })
        
        # Sort by priority
        alerts.sort(key=lambda x: (x['priority'], -x['composite_score']))
        
        return alerts
    
    def _generate_alert_message(self,
                               timeframe: str,
                               signal_type: str,
                               score: float) -> str:
        """Generate alert message"""
        
        return (
            f"{timeframe.upper()} {signal_type} signal detected\n"
            f"Composite score: {score:.1f}/100\n"
            f"→ {'Enter position' if signal_type == 'BULLISH' else 'Reduce exposure'}"
        )
    
    # =========================================================================
    # STREAMLIT DASHBOARD
    # =========================================================================
    
    def render_dashboard(self, signals_data: Dict):
        """
        Render complete multi-timeframe dashboard in Streamlit
        """
        
        st.title("📊 Multi-Timeframe Analysis Dashboard")
        st.caption("Elite v20 - Enhanced Confluence Detection")
        
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate confluence
        confluence = self.analyze_confluence(
            manifold_1h=signals_data.get('1h', {}).get('manifold', 50),
            manifold_4h=signals_data.get('4h', {}).get('manifold', 50),
            manifold_1d=signals_data.get('1d', {}).get('manifold', 50),
            confidence_1h=signals_data.get('1h', {}).get('confidence', 0.5),
            confidence_4h=signals_data.get('4h', {}).get('confidence', 0.5),
            confidence_1d=signals_data.get('1d', {}).get('confidence', 0.5)
        )
        
        with col1:
            st.metric("Confluence", confluence['confluence'].replace('_', ' '))
        
        with col2:
            st.metric("Strength", f"{confluence['strength']}/100")
        
        with col3:
            st.metric("Agreement", confluence['agreement'])
        
        with col4:
            st.metric("Priority", confluence['priority'])
        
        # Recommendation box
        st.info(confluence['recommendation'])
        
        # Heatmap
        st.plotly_chart(
            self.create_confluence_heatmap(signals_data),
            use_container_width=True
        )
        
        # Alert priority list
        st.subheader("🔔 Active Alerts (by Priority)")
        
        alerts = self.calculate_alert_priority(signals_data)
        
        if alerts:
            for alert in alerts:
                with st.expander(
                    f"{alert['emoji']} {alert['timeframe']} - {alert['priority_label']}"
                ):
                    st.write(f"**Signal:** {alert['signal_type']}")
                    st.write(f"**Composite Score:** {alert['composite_score']:.1f}/100")
                    st.write(f"**Manifold:** {alert['manifold']:.1f}")
                    st.write(f"**Confidence:** {alert['confidence']:.1f}%")
                    st.write(f"**Diffusion:** {alert['diffusion']:.1f}")
                    st.write(f"\n{alert['message']}")
        else:
            st.warning("No high-priority signals at this time")
        
        # Individual timeframe details
        st.subheader("📈 Timeframe Details")
        
        tabs = st.tabs(["1 Hour", "4 Hour", "1 Day"])
        
        for idx, tf in enumerate(['1h', '4h', '1d']):
            with tabs[idx]:
                data = signals_data.get(tf, {})
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Manifold DNA", f"{data.get('manifold', 50):.1f}/100")
                
                with col2:
                    st.metric("Confidence", f"{data.get('confidence', 0.5)*100:.1f}%")
                
                with col3:
                    st.metric("Diffusion", f"{data.get('diffusion', 50):.1f}/100")
                
                # Conditions checklist
                st.write("**Signal Conditions:**")
                
                manifold_ok = data.get('manifold', 50) > 70
                confidence_ok = data.get('confidence', 0.5) > 0.7
                diffusion_ok = data.get('diffusion', 50) > 70
                
                st.write(f"{'✅' if manifold_ok else '❌'} Manifold > 70")
                st.write(f"{'✅' if confidence_ok else '❌'} Confidence > 70%")
                st.write(f"{'✅' if diffusion_ok else '❌'} Diffusion > 70")
                
                if manifold_ok and confidence_ok and diffusion_ok:
                    st.success(f"✅ {tf.upper()} SIGNAL ACTIVE")
                else:
                    st.info(f"⏸️ {tf.upper()} waiting for confirmation")


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integrate_with_elite_v20():
    """
    Example of how to integrate with main Elite v20 dashboard
    """
    
    # Initialize
    mtf = MultiTimeframeDashboard()
    
    # Mock data (would come from actual Elite analysis)
    signals_data = {
        '1h': {
            'manifold': 75.2,
            'confidence': 0.82,
            'diffusion': 68.5,
            'regime': 'VOLATILE'
        },
        '4h': {
            'manifold': 82.1,
            'confidence': 0.88,
            'diffusion': 79.3,
            'regime': 'NORMAL'
        },
        '1d': {
            'manifold': 71.8,
            'confidence': 0.75,
            'diffusion': 72.1,
            'regime': 'NORMAL'
        }
    }
    
    # Render dashboard
    mtf.render_dashboard(signals_data)


if __name__ == '__main__':
    # Run standalone
    integrate_with_elite_v20()
