import plotly.graph_objects as go
import numpy as np
import pandas as pd

def render_topology_manifold(st, price_data, onchain_data, topology_report):
    """
    Renders a 3D holographic flow representation of the market's hidden manifold.
    Distinguishes between Local Geometry (Price) and Global Topology (Whales).
    """
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🪐 Institutional Manifold Projection")
    st.caption("3D Flow: Dimension Reduction of Global Liquidity vs price Geometry")

    # Generate synthetic manifold data for visualization (simulating PCA/Topological projection)
    n_points = len(price_data)
    t = np.linspace(0, 10, n_points)
    
    # Global Topology (The stable anchor)
    z_topo = onchain_data / np.max(onchain_data) if np.max(onchain_data) != 0 else np.zeros_like(onchain_data)
    
    # Local Geometry (The noisy price)
    x_price = price_data / np.max(price_data) if np.max(price_data) != 0 else np.zeros_like(price_data)
    
    # Manifold Drift (Interaction)
    y_flux = np.sin(t) * 0.1 + (z_topo * 0.5)
    
    fig = go.Figure()

    # 1. The Institutional Anchor (The "Whale Manifold")
    fig.add_trace(go.Scatter3d(
        x=x_price, 
        y=y_flux, 
        z=z_topo,
        mode='lines',
        line=dict(color='#00f2ff', width=4),
        name='Global Topology',
        hovertemplate='Price: %{x}<br>Flux: %{y}<br>Topology: %{z}'
    ))

    # 2. Retail Noise Cloud (Dithering around the manifold)
    noise_x = x_price + np.random.normal(0, 0.02, n_points)
    noise_z = z_topo + np.random.normal(0, 0.02, n_points)
    
    fig.add_trace(go.Scatter3d(
        x=noise_x, 
        y=y_flux, 
        z=noise_z,
        mode='markers',
        marker=dict(
            size=2,
            color='rgba(188, 19, 254, 0.3)',
            symbol='circle'
        ),
        name='Retail Distortion'
    ))

    # 🪐 Stretched Spring Highlight (Divergence indicator)
    if topology_report.get('is_divergent_invariant'):
        # Get last point where divergence is highest
        fig.add_trace(go.Scatter3d(
            x=[x_price[-1]], 
            y=[y_flux[-1]], 
            z=[z_topo[-1]],
            mode='markers+text',
            marker=dict(size=10, color='#00ff88', symbol='diamond'),
            text=["INVARIANT STABLE"],
            name='Stretched Spring'
        ))

    fig.update_layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=40, b=0),
        scene=dict(
            xaxis=dict(title='Price Geometry', showticklabels=False),
            yaxis=dict(title='Topological Flux', showticklabels=False),
            zaxis=dict(title='Whale Anchor', showticklabels=False),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        height=600,
        showlegend=True,
        legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01,
                    font=dict(color='rgba(255,255,255,0.7)', size=11))
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # Energy metrics below chart
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        energy = topology_report.get('stretched_spring_energy', 0.0)
        st.markdown(f"**Stretched Spring Energy:** `{energy:.4f}`")
    with e_col2:
        drift = topology_report.get('manifold_drift', 0.0)
        st.markdown(f"**Manifold Drift:** `{drift:.4f}`")
        
    st.markdown('</div>', unsafe_allow_html=True)
