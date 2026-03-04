import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st

def generate_simulated_nodes(n=50):
    """Generates random geographic coordinates for nodes."""
    lats = np.random.uniform(-60, 80, n)
    lons = np.random.uniform(-180, 180, n)
    versions = np.random.choice(["v24.0.1 (Satoshi)", "v23.9.0", "v24.1.0-alpha"], n)
    latencies = np.random.randint(10, 150, n)
    return pd.DataFrame({
        'lat': lats,
        'lon': lons,
        'version': versions,
        'latency': latencies,
        'ip': [f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}" for _ in range(n)]
    })

def render_node_topology():
    """Renders the Quantum Ledger style 3D Node Topology."""
    
    nodes = generate_simulated_nodes(80)
    
    # 3D Globe Projection
    fig = go.Figure()

    # 1. Background Sphere (Hollow/Wireframe feel)
    # Using a mesh3d for a subtle sphere surface
    phi = np.linspace(0, 2*np.pi, 50)
    theta = np.linspace(-np.pi/2, np.pi/2, 50)
    phi, theta = np.meshgrid(phi, theta)
    x = np.cos(theta) * np.sin(phi)
    y = np.cos(theta) * np.cos(phi)
    z = np.sin(theta)

    fig.add_trace(go.Mesh3d(
        x=x.flatten(), y=y.flatten(), z=z.flatten(),
        alphahull=0,
        opacity=0.05,
        color='#1c1538',
        hoverinfo='none',
        name='Globe'
    ))

    # 2. Add Node Markers with Signal Beams
    # Convert lat/lon to 3D coords
    lats_rad = np.radians(nodes['lat'])
    lons_rad = np.radians(nodes['lon'])
    
    nx = np.cos(lats_rad) * np.sin(lons_rad)
    ny = np.cos(lats_rad) * np.cos(lons_rad)
    nz = np.sin(lats_rad)

    # Beams (line from surface outwards)
    beam_length = 0.15
    bx = nx * (1 + beam_length)
    by = ny * (1 + beam_length)
    bz = nz * (1 + beam_length)

    for i in range(len(nx)):
        fig.add_trace(go.Scatter3d(
            x=[nx[i], bx[i]], 
            y=[ny[i], by[i]], 
            z=[nz[i], bz[i]],
            mode='lines',
            line=dict(
                color='#06e8f9' if nodes['latency'].iloc[i] < 50 else '#7000FF',
                width=2
            ),
            hoverinfo='none',
            showlegend=False
        ))

    # Actual Nodes
    fig.add_trace(go.Scatter3d(
        x=nx, y=ny, z=nz,
        mode='markers',
        marker=dict(
            size=4,
            color=nodes['latency'],
            colorscale=[[0, '#06e8f9'], [0.5, '#7000FF'], [1, '#FF2A6D']],
            opacity=0.8,
            symbol='circle'
        ),
        text=nodes.apply(lambda r: f"Node: {r['ip']}<br>Lat: {r['lat']:.1f}<br>Lon: {r['lon']:.1f}<br>Ver: {r['version']}<br>Ping: {r['latency']}ms", axis=1),
        hoverinfo='text',
        name='Nodes'
    ))

    fig.update_layout(
        template='plotly_dark',
        title={
            'text': "🌐 GLOBAL QUANTUM LEDGER TOPOLOGY",
            'font': {'size': 16, 'family': "Space Mono", 'color': "#06e8f9"},
            'y': 0.95
        },
        margin={'l': 0, 'r': 0, 't': 20, 'b': 0},
        scene={
            'xaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False, 'title': ''},
            'yaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False, 'title': ''},
            'zaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False, 'title': ''},
            'aspectmode': 'cube',
            'bgcolor': 'rgba(0,0,0,0)'
        },
        paper_bgcolor='rgba(0,0,0,0)',
        height=600,
        showlegend=True,
        legend={
            'orientation': "h",
            'yanchor': "bottom",
            'y': 0.01,
            'xanchor': "right",
            'x': 0.99,
            'bgcolor': "rgba(0,0,0,0.5)",
            'font': {'size': 10, 'color': "white"}
        }
    )
    
    # Add Legend Markers Manually
    fig.add_trace(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers', marker={'color': '#06e8f9'}, name='High-Speed Nodes (<50ms)'))
    fig.add_trace(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers', marker={'color': '#FF2A6D'}, name='Congested Nodes (>100ms)'))

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_node_stats_hud():
    """Renders the top HUD metrics from the mockup."""
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div class="glass-card" style="max-width: 250px; padding: 15px;">
                <h1 style="font-size: 0.7rem; letter-spacing: 0.15em; color: var(--text-muted); text-transform: uppercase; margin-bottom: 5px;">Active Nodes</h1>
                <div style="display: flex; align-items: baseline; gap: 10px;">
                    <span style="font-size: 1.8rem; font-weight: bold; color: #06e8f9; filter: drop-shadow(0 0 8px rgba(6,232,249,0.5));">14,203</span>
                    <div style="color: #06e8f9; font-size: 0.8rem;">↑ 12%</div>
                </div>
                <div style="margin-top: 15px; font-family: monospace; font-size: 0.6rem;">
                    <div style="display: flex; justify-content: space-between; color: var(--text-muted);">
                        <span>TOR NETWORK</span>
                        <span style="color: white;">35%</span>
                    </div>
                    <div style="height: 4px; width: 100%; background: rgba(255,255,255,0.1); border-radius: 2px; margin: 4px 0;">
                        <div style="height: 100%; width: 35%; background: #7000FF; box-shadow: 0 0 10px #7000FF; border-radius: 2px;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: var(--text-muted); margin-top: 8px;">
                        <span>CLEARNET</span>
                        <span style="color: white;">65%</span>
                    </div>
                </div>
            </div>
            <div class="glass-card" style="border-radius: 40px; padding: 5px 15px; display: flex; align-items: center; gap: 8px;">
                <div style="width: 8px; height: 8px; border-radius: 50%; background: #06e8f9; box-shadow: 0 0 8px #06e8f9;"></div>
                <span style="font-family: monospace; font-size: 0.7rem; color: #06e8f9;">LIVE: 42ms</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_quantum_ledger_anatomy():
    """Displays the upper view of core assets (Quantum Ledger)."""
    st.markdown("""
        <div class="glass-card">
            <h2 style="font-size: 0.8rem; letter-spacing: 0.15em; color: var(--text-muted); text-transform: uppercase;">Quantum Ledger Anatomy</h2>
            <div style="display: flex; gap: 40px; margin-top: 15px;">
                <div>
                    <div style="font-size: 0.6rem; color: var(--text-muted);">BTC CORE</div>
                    <div style="font-size: 1.4rem; font-weight: bold; color: #06e8f9;">0.530147 BTC</div>
                </div>
                <div>
                    <div style="font-size: 0.6rem; color: var(--text-muted);">GLD INVARIANT</div>
                    <div style="font-size: 1.4rem; font-weight: bold; color: #7000FF;">50 Units</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
