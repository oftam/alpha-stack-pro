import streamlit as st
import os
import sys
from pathlib import Path

# ============================================================================
# SYSTEM CONFIG
# ============================================================================
st.set_page_config(
    page_title="🌐 QUANTUM LEDGER | ELITE v20",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
CURRENT_PHASE = "Whipsaw Defense (Gene Silencing Active)"

# Import Specialized Modules
sys.path.append(PARENT_DIR)
try:
    from modules.node_topology import render_node_topology, render_node_stats_hud, render_quantum_ledger_anatomy
    MODULES_AVAILABLE = True
except ImportError as e:
    st.error(f"Module Import Error: {e}")
    MODULES_AVAILABLE = False

def load_css():
    """🏛️ ELITE v20 INSTITUTIONAL DESIGN - Quant-Grade Implementation"""
    institutional_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Space+Mono:wght@400;700&display=swap');

    :root {
        --inst-blue: #B0C4DE;
        --inst-bg: #0B0E14;
        --inst-text: #F8FAFC;
        --inst-muted: #64748B;
        --inst-border: rgba(255, 255, 255, 0.08);
        --inst-glass: rgba(15, 23, 42, 0.6);
    }

    .stApp {
        background: var(--inst-bg) !important;
        background-image: linear-gradient(180deg, rgba(30, 41, 59, 0.1) 0%, var(--inst-bg) 100%) !important;
        color: var(--inst-text) !important;
        font-family: 'Inter', sans-serif !important;
    }

    #MainMenu, header, footer { visibility: hidden !important; }

    .glass-card {
        background: var(--inst-glass) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--inst-border) !important;
        border-radius: 4px !important;
        padding: 24px;
        margin-bottom: 24px;
    }

    h1, h2, h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: var(--inst-text) !important;
    }

    .inst-header {
        border-bottom: 1px solid var(--inst-border);
        padding-bottom: 20px;
        margin-bottom: 30px;
    }

    .inst-title {
        font-size: 1.5rem !important;
        color: var(--inst-blue) !important;
        font-weight: 700 !important;
    }

    .metric-value {
        font-size: 2rem !important;
        font-family: 'Space Mono', monospace !important;
        color: white !important;
    }

    .metric-label {
        font-size: 0.7rem !important;
        text-transform: uppercase !important;
        color: var(--inst-muted) !important;
    }
    </style>
    """
    st.markdown(institutional_css, unsafe_allow_html=True)

def main():
    load_css()
    
    # Institutional Header Bar
    st.markdown(f"""
        <div class="inst-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="inst-title">🌐 QUANTUM LEDGER | NODE TOPOLOGY</div>
                    <div style="font-size: 0.7rem; color: var(--inst-muted); font-family: 'Space Mono'; letter-spacing: 1px;">
                        STANDALONE TQFT VISUALIZATION LAYER
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-family: 'Space Mono'; font-size: 0.8rem; color: var(--inst-blue);">SYSTEM: ACTIVE</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if MODULES_AVAILABLE:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            render_quantum_ledger_anatomy()
            render_node_stats_hud()
            
            st.markdown("""
                <div class="glass-card">
                    <h3 style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">System Integrity</h3>
                    <div style="margin-top: 10px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                            <span>Manifold Alignment</span>
                            <span style="color: #06e8f9;">99.8%</span>
                        </div>
                        <div style="height: 2px; background: rgba(255,255,255,0.1); margin-top: 5px;">
                            <div style="width: 99.8%; height: 100%; background: #06e8f9;"></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            render_node_topology()
    else:
        st.error("Tactical modules not found. Ensure modules/node_topology.py exists.")

if __name__ == "__main__":
    main()
