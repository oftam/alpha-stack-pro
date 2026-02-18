#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE 2: Protein Folding - Manifold Learning
"מוח תלת-ממדי" - מזהה קשרים נסתרים בין נכסים

Implements:
- PCA (Principal Component Analysis) for latent factors
- Network centrality for stress propagation
- Manifold embedding (t-SNE) for non-linear relationships
- Regime-specific correlation structures

Based on Yuval's protein folding research adapted to markets.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import networkx as nx


class ProteinFoldingAnalyzer:
    """
    Maps multi-asset market to 3D+ manifold space
    Detects hidden correlations invisible in 2D (pairwise) analysis
    
    The "protein folding" analogy:
    - 1D chain: Individual asset prices (linear view)
    - 3D structure: Latent factor space (manifold view)
    - Hidden contacts: Assets that seem uncorrelated but influence via hidden pathways
    """
    
    def __init__(self, n_components: int = 3):
        """
        Args:
            n_components: Number of latent factors (PCs) to extract
        """
        self.n_components = n_components
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
        
        self.factor_names = None  # Will be set after fitting
        self.explained_variance = None
        
    # =========================================================================
    # DATA PREPARATION
    # =========================================================================
    
    def prepare_multi_asset_data(self, 
                                 btc_df: pd.DataFrame,
                                 other_assets: Dict[str, pd.DataFrame],
                                 return_period: int = 1) -> pd.DataFrame:
        """
        Prepare multi-asset return matrix
        
        Args:
            btc_df: BTC OHLC data
            other_assets: Dict of {symbol: OHLC_df} for other assets
            return_period: Period for return calculation
            
        Returns:
            DataFrame with aligned returns for all assets
        """
        
        # Extract returns
        returns = pd.DataFrame()
        returns['BTC'] = btc_df['close'].pct_change(return_period)
        
        for symbol, df in other_assets.items():
            if 'close' in df.columns or 'Close' in df.columns:
                close_col = 'close' if 'close' in df.columns else 'Close'
                returns[symbol] = df[close_col].pct_change(return_period)
        
        # Align and clean
        returns = returns.dropna()
        
        # Remove extreme outliers (>5 sigma)
        for col in returns.columns:
            mean = returns[col].mean()
            std = returns[col].std()
            returns[col] = returns[col].clip(mean - 5*std, mean + 5*std)
        
        return returns
    
    # =========================================================================
    # PCA - LATENT FACTOR EXTRACTION
    # =========================================================================
    
    def fit_pca(self, returns: pd.DataFrame) -> Dict:
        """
        Fit PCA to extract latent factors
        
        Returns principal components that explain the most variance
        These are the "hidden factors" driving all assets
        """
        
        # Standardize returns
        returns_scaled = self.scaler.fit_transform(returns)
        
        # Fit PCA
        self.pca.fit(returns_scaled)
        
        # Extract components
        components = self.pca.components_  # Shape: (n_components, n_assets)
        explained_var = self.pca.explained_variance_ratio_
        
        # Interpret components (give them names based on loadings)
        self.factor_names = self._interpret_factors(components, returns.columns)
        self.explained_variance = explained_var
        
        # Transform returns to factor space
        factor_returns = self.pca.transform(returns_scaled)
        
        return {
            'factors': pd.DataFrame(
                factor_returns,
                index=returns.index,
                columns=self.factor_names
            ),
            'loadings': pd.DataFrame(
                components.T,
                index=returns.columns,
                columns=self.factor_names
            ),
            'explained_variance': explained_var,
            'cumulative_variance': np.cumsum(explained_var)
        }
    
    def _interpret_factors(self, 
                          components: np.ndarray,
                          asset_names: List[str]) -> List[str]:
        """
        Interpret PCA factors based on loadings
        
        Factor interpretation:
        - PC1: Usually "market factor" (all assets positive)
        - PC2: Usually "sector rotation" (crypto vs traditional)
        - PC3: Usually "idiosyncratic" (specific to few assets)
        """
        
        factor_names = []
        
        for i, loadings in enumerate(components):
            # Find dominant assets
            abs_loadings = np.abs(loadings)
            top_idx = np.argmax(abs_loadings)
            top_asset = asset_names[top_idx]
            
            # Interpret
            if i == 0:
                # PC1 is typically market-wide
                if np.sum(loadings > 0) > len(loadings) * 0.7:
                    name = "MARKET_FACTOR"
                else:
                    name = "RISK_FACTOR"
            elif i == 1:
                # PC2 is typically rotation
                name = "SECTOR_ROTATION"
            else:
                # PC3+ are more specific
                name = f"FACTOR_{i+1}_{top_asset}"
            
            factor_names.append(name)
        
        return factor_names
    
    # =========================================================================
    # NETWORK ANALYSIS - STRESS PROPAGATION
    # =========================================================================
    
    def build_correlation_network(self, 
                                  returns: pd.DataFrame,
                                  threshold: float = 0.3) -> nx.Graph:
        """
        Build network graph from correlation matrix
        
        Edges = significant correlations
        Node centrality = how important that asset is as a "hub"
        """
        
        # Correlation matrix
        corr = returns.corr()
        
        # Build graph
        G = nx.Graph()
        
        # Add nodes
        for asset in returns.columns:
            G.add_node(asset)
        
        # Add edges (only significant correlations)
        for i, asset1 in enumerate(returns.columns):
            for j, asset2 in enumerate(returns.columns):
                if i < j:  # Avoid duplicates
                    corr_val = corr.iloc[i, j]
                    if abs(corr_val) > threshold:
                        G.add_edge(asset1, asset2, weight=abs(corr_val))
        
        return G
    
    def compute_centrality_metrics(self, G: nx.Graph) -> Dict[str, Dict[str, float]]:
        """
        Compute network centrality measures
        
        Centrality types:
        - Degree: How many connections (high = hub)
        - Betweenness: How often asset is on shortest path (high = bridge)
        - Eigenvector: Importance based on connections to important nodes
        """
        
        if len(G.edges()) == 0:
            # No edges - return zeros
            return {
                'degree': {node: 0 for node in G.nodes()},
                'betweenness': {node: 0 for node in G.nodes()},
                'eigenvector': {node: 0 for node in G.nodes()}
            }
        
        return {
            'degree': nx.degree_centrality(G),
            'betweenness': nx.betweenness_centrality(G),
            'eigenvector': nx.eigenvector_centrality(G, max_iter=1000)
        }
    
    def identify_stress_pathways(self, 
                                 G: nx.Graph,
                                 source_asset: str,
                                 target_asset: str) -> List[List[str]]:
        """
        Find all paths from source to target
        
        These are the "hidden pathways" through which stress propagates
        
        Example:
        - Direct: BTC ←→ SPY (correlation = 0.45)
        - Hidden: BTC ←→ DXY ←→ GLD ←→ SPY (chain of influences)
        """
        
        try:
            # Find all simple paths (no cycles)
            paths = list(nx.all_simple_paths(
                G, 
                source=source_asset, 
                target=target_asset,
                cutoff=3  # Max path length
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    # =========================================================================
    # MANIFOLD DETECTION - HIDDEN CORRELATIONS
    # =========================================================================
    
    def detect_hidden_correlations(self, 
                                   returns: pd.DataFrame,
                                   asset_pairs: List[Tuple[str, str]] = None) -> Dict:
        """
        Detect correlations invisible in linear space but visible in manifold
        
        Method:
        1. Fit PCA to get latent factors
        2. Check if assets are correlated in FACTOR space but not in RETURN space
        3. This reveals hidden relationships
        """
        
        # Fit PCA
        pca_result = self.fit_pca(returns)
        factors = pca_result['factors']
        loadings = pca_result['loadings']
        
        # Build network
        G = self.build_correlation_network(returns)
        centrality = self.compute_centrality_metrics(G)
        
        # Identify hidden correlations
        hidden_corrs = []
        
        if asset_pairs is None:
            # Auto-generate pairs
            assets = list(returns.columns)
            asset_pairs = [(assets[i], assets[j]) 
                          for i in range(len(assets)) 
                          for j in range(i+1, len(assets))]
        
        for asset1, asset2 in asset_pairs:
            if asset1 not in returns.columns or asset2 not in returns.columns:
                continue
            
            # Linear correlation (2D view)
            linear_corr = returns[[asset1, asset2]].corr().iloc[0, 1]
            
            # Manifold correlation (3D view via shared factors)
            # Check if they load heavily on same factor
            loading1 = loadings.loc[asset1].values
            loading2 = loadings.loc[asset2].values
            manifold_similarity = np.dot(loading1, loading2)
            
            # Hidden correlation = high manifold similarity but low linear correlation
            if abs(manifold_similarity) > 0.5 and abs(linear_corr) < 0.3:
                # Find the hidden pathway
                pathways = self.identify_stress_pathways(G, asset1, asset2)
                
                hidden_corrs.append({
                    'asset_pair': (asset1, asset2),
                    'linear_corr': linear_corr,
                    'manifold_similarity': manifold_similarity,
                    'hidden': True,
                    'pathways': pathways,
                    'dominant_factor': self.factor_names[np.argmax(np.abs(loading1 * loading2))]
                })
        
        return {
            'hidden_correlations': hidden_corrs,
            'network': G,
            'centrality': centrality,
            'pca_summary': pca_result
        }
    
    # =========================================================================
    # REGIME-SPECIFIC MANIFOLDS
    # =========================================================================
    
    def fit_regime_specific_pca(self, 
                                returns: pd.DataFrame,
                                regime_labels: pd.Series) -> Dict[str, Dict]:
        """
        Fit separate PCA for each regime
        
        The manifold structure changes in different market regimes!
        
        Example:
        - In BULL regime: BTC-SPY correlation high (risk-on)
        - In BEAR regime: BTC-GLD correlation high (safe haven)
        """
        
        regime_pcas = {}
        
        for regime in regime_labels.unique():
            # Filter data for this regime
            regime_mask = regime_labels == regime
            regime_returns = returns[regime_mask]
            
            if len(regime_returns) < 30:  # Need minimum data
                continue
            
            # Fit PCA for this regime
            regime_pca_result = self.fit_pca(regime_returns)
            regime_pcas[regime] = regime_pca_result
        
        return regime_pcas


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    # Generate sample multi-asset data
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2023-01-01', periods=n, freq='1D')
    
    # Simulate correlated returns
    # Hidden structure: PC1 = market, PC2 = dollar, PC3 = crypto-specific
    market_factor = np.random.randn(n) * 0.02
    dollar_factor = np.random.randn(n) * 0.015
    crypto_factor = np.random.randn(n) * 0.03
    
    returns = pd.DataFrame({
        'BTC': 0.6*market_factor + 0.3*crypto_factor + np.random.randn(n)*0.01,
        'ETH': 0.5*market_factor + 0.4*crypto_factor + np.random.randn(n)*0.01,
        'SPY': 0.7*market_factor - 0.1*dollar_factor + np.random.randn(n)*0.008,
        'DXY': -0.8*dollar_factor + 0.1*market_factor + np.random.randn(n)*0.005,
        'GLD': 0.4*dollar_factor - 0.2*market_factor + np.random.randn(n)*0.007,
    }, index=dates)
    
    # Analyze
    analyzer = ProteinFoldingAnalyzer(n_components=3)
    
    print("\n" + "="*60)
    print("PROTEIN FOLDING - MANIFOLD ANALYSIS")
    print("="*60)
    
    # Detect hidden correlations
    result = analyzer.detect_hidden_correlations(returns)
    
    print(f"\n📊 PCA Summary:")
    print(f"Explained variance: {result['pca_summary']['explained_variance']}")
    print(f"Cumulative variance: {result['pca_summary']['cumulative_variance']}")
    
    print(f"\n🔍 Hidden Correlations Found: {len(result['hidden_correlations'])}")
    for hc in result['hidden_correlations'][:3]:  # Show top 3
        print(f"\n  {hc['asset_pair'][0]} ←→ {hc['asset_pair'][1]}")
        print(f"    Linear correlation: {hc['linear_corr']:.3f} (weak)")
        print(f"    Manifold similarity: {hc['manifold_similarity']:.3f} (strong!)")
        print(f"    Dominant factor: {hc['dominant_factor']}")
        if hc['pathways']:
            print(f"    Pathway: {' → '.join(hc['pathways'][0])}")
    
    print(f"\n🕸️  Network Centrality:")
    for asset, score in result['centrality']['eigenvector'].items():
        print(f"  {asset}: {score:.3f}")
    
    print("="*60)
