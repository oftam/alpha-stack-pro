#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 DASHBOARD INTEGRATION ADAPTER
מחבר את 5 המודולים Elite לדאשבורד הקיים שלך + Data Tier & Confidence

Data Tier System:
- LIVE: Real-time data from APIs
- PROXY: Estimated/fallback metrics
- DISABLED: Module not available
- N/A: Not applicable

Confidence: 0.0-1.0 based on data quality
"""

import sys
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np


class DataTier(Enum):
    """Data quality tier"""
    LIVE = "LIVE"           # Real API data
    PROXY = "PROXY"         # Estimated/fallback
    DISABLED = "DISABLED"   # Module off
    NA = "N/A"             # Not applicable


@dataclass
class DataStatus:
    """
    Tracks data quality across all modules
    
    Used to calculate confidence multiplier:
    - All LIVE → confidence = 1.0
    - Mix LIVE/PROXY → confidence = 0.4-0.7
    - Mostly PROXY → confidence = 0.2-0.4
    - DISABLED → excluded from calc
    """
    ohlcv: DataTier = DataTier.LIVE
    onchain: DataTier = DataTier.DISABLED
    manifold: DataTier = DataTier.DISABLED
    chaos: DataTier = DataTier.LIVE
    gates: DataTier = DataTier.LIVE
    nlp: DataTier = DataTier.DISABLED
    microstructure: DataTier = DataTier.DISABLED
    
    def calculate_confidence(self) -> float:
        """
        Calculate overall confidence (0.0-1.0)
        
        Core modules (always counted):
        - OHLCV: 0.2
        - Microstructure: 0.2
        - Chaos: 0.15
        - Gates: 0.1
        
        Optional modules (only if LIVE/PROXY):
        - On-chain: 0.3
        - Manifold: 0.05
        - NLP: 0.05
        """
        
        weights = {
            'ohlcv': 0.2,
            'microstructure': 0.2,
            'onchain': 0.3,
            'chaos': 0.15,
            'gates': 0.1,
            'manifold': 0.05,
            'nlp': 0.05
        }
        
        tier_scores = {
            DataTier.LIVE: 1.0,
            DataTier.PROXY: 0.4,
            DataTier.DISABLED: 0.0,
            DataTier.NA: 0.0
        }
        
        # Core modules that always count
        core_modules = {'ohlcv', 'microstructure', 'chaos', 'gates'}
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for component, weight in weights.items():
            tier = getattr(self, component)
            
            # Core modules always count (even if DISABLED, score=0)
            if component in core_modules:
                total_weight += weight
                weighted_score += tier_scores[tier] * weight
            else:
                # Optional modules only count if LIVE/PROXY
                if tier in (DataTier.LIVE, DataTier.PROXY):
                    total_weight += weight
                    weighted_score += tier_scores[tier] * weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_score / total_weight
    
    def get_summary(self) -> str:
        """Human-readable summary"""
        lines = []
        for component in ['ohlcv', 'onchain', 'manifold', 'chaos', 'gates', 'nlp']:
            tier = getattr(self, component)
            emoji = "✅" if tier == DataTier.LIVE else "⚠️" if tier == DataTier.PROXY else "❌"
            lines.append(f"{emoji} {component.upper()}: {tier.value}")
        return "\n".join(lines)

# Import Elite modules with better error handling
ELITE_AVAILABLE = True
import_errors = []

try:
    from module_1_onchain_diffusion import OnChainDiffusionLayer
except Exception as e:
    import_errors.append(f"module_1_onchain_diffusion: {e}")
    ELITE_AVAILABLE = False

try:
    from manifold_premium_layer import ManifoldEngine, RegimeDetector
    MANIFOLD_AVAILABLE = True
except Exception as e:
    import_errors.append(f"manifold_premium_layer: {e}")
    MANIFOLD_AVAILABLE = False

try:
    from module_3_violence_chaos import ViolenceChaosDetector
except Exception as e:
    import_errors.append(f"module_3_violence_chaos: {e}")
    ELITE_AVAILABLE = False

try:
    from module_4_execution_gates import ExecutionGates, Gate, GateResult
except Exception as e:
    import_errors.append(f"module_4_execution_gates: {e}")
    ELITE_AVAILABLE = False

try:
    from final_arbiter import FinalArbiter
except Exception as e:
    import_errors.append(f"final_arbiter: {e}")

try:
    from nlp_sentiment import NLPSentimentAnalyzer
    NLP_AVAILABLE = True
except Exception as e:
    import_errors.append(f"nlp_sentiment: {e}")
    NLP_AVAILABLE = False

try:
    from signal_stabilizer import SignalStabilizer
    STABILIZER_AVAILABLE = True
except Exception:
    STABILIZER_AVAILABLE = False

try:
    from monolith_engine import MonolithEngine
    MONOLITH_AVAILABLE = True
except Exception:
    MONOLITH_AVAILABLE = False

try:
    from dark_signals_sandbox import DarkSignalsSandbox
    DARK_AVAILABLE = True
except Exception:
    DARK_AVAILABLE = False

try:
    from signal_stabilizer import SignalStabilizer
    STABILIZER_AVAILABLE = True
except Exception:
    STABILIZER_AVAILABLE = False

try:
    from monolith_engine import MonolithEngine
    MONOLITH_AVAILABLE = True
except Exception:
    MONOLITH_AVAILABLE = False

try:
    from dark_signals_sandbox import DarkSignalsSandbox
    DARK_AVAILABLE = True
except Exception:
    DARK_AVAILABLE = False

# Scientific Engines Availability (Phase 6)
try:
    from hmm_regime_engine import HMMEngine
    HMM_AVAILABLE = True
except Exception:
    HMM_AVAILABLE = False

try:
    from quantum_physics_engine import QuantumPhysicsEngine
    PHYSICS_AVAILABLE = True
except Exception:
    PHYSICS_AVAILABLE = False

try:
    from manifold_topology_engine import ManifoldTopologyEngine
    TOPOLOGY_AVAILABLE = True
except Exception:
    TOPOLOGY_AVAILABLE = False

try:
    from risk_management_engine import RiskManagementEngine
    RISK_ENGINE_AVAILABLE = True
except Exception:
    RISK_ENGINE_AVAILABLE = False


class EliteDashboardAdapter:
    """
    מתאם לשילוב 5 המודולים + Data Tier & Confidence
    
    Tracks:
    - Which modules are active
    - Data quality tier for each
    - Overall system confidence
    """
    
    def __init__(self, 
                 glassnode_api_key: Optional[str] = None,
                 cryptoquant_api_key: Optional[str] = None):
        import os
        # Auto-load from env vars if not passed explicitly — critical for Cloud Run
        glassnode_api_key = glassnode_api_key or os.getenv('GLASSNODE_API_KEY')
        cryptoquant_api_key = cryptoquant_api_key or os.getenv('CRYPTOQUANT_API_KEY')
        
        if not ELITE_AVAILABLE:
            print("\u26a0\ufe0f  Elite modules not found")
            self.ready = False
            self.data_status = DataStatus()
            return

        # Initialize core components
        self.onchain = OnChainDiffusionLayer(
            glassnode_api_key=glassnode_api_key,
            cryptoquant_api_key=cryptoquant_api_key
        )
        
        if MANIFOLD_AVAILABLE:
            self.manifold = ManifoldEngine()
            self.regime_detector = RegimeDetector()
        else:
            self.manifold = None
            self.regime_detector = None
            
        self.chaos = ViolenceChaosDetector()
        self.gates = ExecutionGates()
        self.arbiter = FinalArbiter() if ELITE_AVAILABLE else None
        
        if NLP_AVAILABLE:
            import os
            self.nlp = NLPSentimentAnalyzer(cryptopanic_token=os.getenv('CRYPTOPANIC_API_KEY'), use_finbert=False)
        else:
            self.nlp = None

        self.stabilizer = SignalStabilizer() if STABILIZER_AVAILABLE else None
        
        # Renaissance & Scientific Suite
        self.monolith = MonolithEngine() if MONOLITH_AVAILABLE else None
        self.dark_sandbox = DarkSignalsSandbox() if DARK_AVAILABLE else None
        self.hmm = HMMEngine() if HMM_AVAILABLE else None
        self.physics = QuantumPhysicsEngine() if PHYSICS_AVAILABLE else None
        self.topology = ManifoldTopologyEngine() if TOPOLOGY_AVAILABLE else None
        self.risk_engine = RiskManagementEngine() if RISK_ENGINE_AVAILABLE else None
        
        # Microstructure (WebSocket)
        micro_enabled = False
        try:
            from binance_microstructure import BinanceMicrostructure
            import threading
            import asyncio
            
            self.micro = BinanceMicrostructure(symbol="btcusdt", depth_levels=10)
            def start_micro(): asyncio.run(self.micro.start())
            self.micro_thread = threading.Thread(target=start_micro, daemon=True)
            self.micro_thread.start()
            micro_enabled = True
            print("   🔴 Microstructure: LIVE")
        except Exception as e:
            print(f"   ⚠️  Microstructure disabled: {e}")
            self.micro = None
        
        self.ready = True
        # Determine initial on-chain tier based on which provider loaded
        _has_live_onchain = bool(
            getattr(self.onchain, 'has_glassnode', False) or
            getattr(self.onchain, 'has_cryptoquant', False) or
            getattr(self.onchain, 'has_coinmetrics', False)
        )
        self.data_status = DataStatus(
            ohlcv=DataTier.LIVE,
            onchain=DataTier.LIVE if _has_live_onchain else DataTier.PROXY,
            manifold=DataTier.LIVE if MANIFOLD_AVAILABLE and self.manifold else DataTier.DISABLED,
            chaos=DataTier.LIVE,
            gates=DataTier.LIVE,
            nlp=DataTier.LIVE if NLP_AVAILABLE and self.nlp else DataTier.DISABLED,
            microstructure=DataTier.LIVE if micro_enabled else DataTier.DISABLED
        )
            
        confidence = self.data_status.calculate_confidence()
        print(f"\u2705 Elite system ready (confidence: {confidence:.1%})")
        onchain_tier = 'LIVE' if _has_live_onchain else 'PROXY'
        print(f"   Data tier: OHLCV=LIVE, On-chain={onchain_tier}")
    
    def analyze_elite(self,
                     df: pd.DataFrame,
                     multi_asset: Optional[Dict] = None,
                     exposure_pct: float = 0,
                     drawdown_pct: float = 0,
                     base_action: str = 'HOLD',
                     news_headlines: Optional[List[Dict]] = None) -> Dict:
        """
        ניתוח מלא עם כל 5 המודולים + Data Status & Confidence
        
        Returns:
            Dict with:
            - Module results (onchain, chaos, gates, etc.)
            - data_status: DataStatus object
            - confidence: float (0.0-1.0)
            - final_action: str with confidence tag
        """
        
        if not self.ready:
            return {
                'error': 'Elite modules not available',
                'data_status': DataStatus(),
                'confidence': 0.0
            }
        
        results = {
            'price': float(df['close'].iloc[-1]),
            'timestamp': pd.Timestamp.now()
        }
        
        # Update data status based on what's available
        if multi_asset:
            self.data_status.manifold = DataTier.LIVE
        
        if news_headlines:
            self.data_status.nlp = DataTier.LIVE
        
        # 1. On-chain
        try:
            onchain_result = self.onchain.analyze_diffusion(df, 30)
            results['onchain'] = onchain_result
            
            # Update tier: LIVE if provider returned real data, PROXY otherwise
            if onchain_result.get('has_real_data', False):
                self.data_status.onchain = DataTier.LIVE
            else:
                self.data_status.onchain = DataTier.PROXY
        except Exception as e:
            results['onchain'] = {
                'diffusion_score': 50, 
                'signal': 'NEUTRAL',
                'error': str(e)
            }
            self.data_status.onchain = DataTier.PROXY
        
        # 2. Manifold (if multi-asset)
        if multi_asset:
            try:
                # Use topological learning for raw score if available
                if self.topology:
                    manifold_data = self.topology.generate_topology_report(df['close'].values, results['onchain'].get('whale_balance', df['close'].values))
                    manifold_score = 100 * (1 - manifold_data.get('topological_flux', 0.5))
                else:
                    returns = self.manifold.prepare_multi_asset_data(df, multi_asset)
                    manifold = self.manifold.detect_hidden_correlations(returns)
                    manifold_score = float(manifold['pca_summary']['explained_variance'][0] * 100) if manifold['pca_summary']['explained_variance'] else 50
                
                results['manifold'] = {
                    'score': manifold_score,
                    'is_premium': True
                }
            except Exception as e:
                results['manifold'] = {'score': 0, 'error': str(e)}
                self.data_status.manifold = DataTier.DISABLED
        
        # 3. Regime Detection (Scientific HMM)
        try:
            if self.hmm:
                regime_idx, regime_label = self.hmm.get_regime_label(df)
                results['regime'] = {
                    'regime': regime_label,
                    'confidence': 1.0 # HMM provides definitive state
                }
            elif self.regime_detector:
                results['regime'] = self.regime_detector.detect_regime(df)
            else:
                results['regime'] = {'regime': 'normal', 'confidence': 0.5}
        except Exception:
            results['regime'] = {'regime': 'normal', 'confidence': 0.5}

        # 4. Divergence & Physics (DUDU)
        try:
            # Divergence from on-chain
            results['divergence'] = {
                'spread': results.get('onchain', {}).get('divergence_spread', 0)
            }
            
            # Physics (DUDU Overlay)
            if self.physics:
                physics_data = self.physics.feynman_kac_pdf(df['close'].values)
                results['dudu_overlay'] = {
                    'p10': physics_data.get('p10', 0),
                    'p50': physics_data.get('p50', 0),
                }
            else:
                results['dudu_overlay'] = {'p10': 0, 'p50': 0}
        except Exception:
            results['divergence'] = {'spread': 0}
            results['dudu_overlay'] = {'p10': 0, 'p50': 0}
        
        # 3. Chaos
        try:
            chaos_result = self.chaos.analyze(df)
            results['chaos'] = {
                'regime': chaos_result.regime.value,
                'violence_score': chaos_result.violence_score,
                'violence': chaos_result.violence_score, # For backward compat and gates
                'volatility': chaos_result.volatility,
                'is_clustered': chaos_result.is_clustered,
                'chaos_score': chaos_result.violence_score,
                'signal': chaos_result.regime.value
            }
        except Exception as e:
            results['chaos'] = {
                'chaos_score': 50, 
                'violence_score': 50,
                'violence': 1.0, 
                'classification': 'NORMAL',
                'signal': 'NORMAL',
                'error': str(e)
            }
        
        # 5. NLP (if news available)
        if news_headlines:
            try:
                analyzed = [
                    self.nlp.analyze_headline(h['text'], h.get('source', 'unknown'))
                    for h in news_headlines
                ]
                results['nlp'] = self.nlp.aggregate_news(analyzed)
            except Exception as e:
                results['nlp'] = {'error': str(e)}
                self.data_status.nlp = DataTier.DISABLED
        
        # 2. Extract Microstructure (if available)
        micro_data = {}
        if self.micro:
            # Check for stale data (Phase 14.1 logic)
            is_active = getattr(self.micro, 'is_active', False)
            last_update = getattr(self.micro, 'last_update', None)
            
            # If no update for 30s, mark as dropped
            if is_active and last_update:
                from datetime import datetime
                if (datetime.now() - last_update).total_seconds() > 30:
                   is_active = False
            
            micro_data = self.micro.get_snapshot()
            micro_data['status'] = "ACTIVE" if is_active else "OFFLINE (Connection Dropped)"
        else:
            micro_data = {'status': 'OFFLINE (Module Missing)', 'truecvd': 0.0}
        
        # 4. Gates (final check)
        try:
            chaos_data = results.get('chaos', {})
            violence = chaos_data.get('violence_score', 0.5)
            # Standardize chaos input (1.0 = high chaos) as entropy proxy
            chaos_score = results.get('chaos', {}).get('chaos_score', 50) / 100.0
            
            gates_result = self.gates.check_all_gates(
                df, exposure_pct, drawdown_pct, base_action, 
                current_volatility=violence, 
                chaos_score=chaos_score
            )
            
            results['gates'] = gates_result
            results['allow_trade'] = gates_result['can_trade'] if 'can_trade' in gates_result else gates_result.get('allow_trade', False)
            
            # Arbiter decision (The Victory Protocol Core)
            if self.arbiter:
                decision_summary = {
                    'direction': base_action,
                    'size_multiplier': 1.0,
                    'reasoning': f"Consolidated score: {results.get('elite_score', 0):.0f}"
                }
                final_decision = self.arbiter.decide(results, decision_summary)
                results['final_action'] = final_decision.action
                results['arbiter_reason'] = final_decision.reason
            else:
                results['final_action'] = base_action if results.get('allow_trade', False) else 'HOLD'
        except Exception as e:
            results['gates'] = {'allow_trade': True, 'error': str(e)}
            results['final_action'] = base_action
            
        # 6. Monolithic Integration
        if self.monolith:
            # Add price change metadata for interference logic
            results['price_change_1h'] = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) if len(df) > 1 else 0
            
            # Use microstructure if available
            results['microstructure'] = self.get_microstructure_snapshot() or {}
            
            # Compute Monolithic Score (Epigenetic Interference)
            results['monolith_score'] = self.monolith.apply_monolithic_score(results)
            results['interference_matrix'] = self.monolith.calculate_interference_matrix(results).tolist()
            
        # 7. Dark Signals Integration
        if self.dark_sandbox:
            # Simulated alt data for demonstration (in production, fetch from APIs)
            alt_data = {
                'etf_flows': {'correlation_p': 0.008, 'value': 250000000},
                'macro_entropy': {'p_value': 0.005, 'value': 0.85}
            }
            results['dark_signals'] = self.dark_sandbox.scan_alternative_data(df, alt_data)
            results['dark_edge'] = self.dark_sandbox.get_consolidated_edge()
            
            # Add Dark Edge to final score if significant
            if 'monolith_score' in results:
                results['monolith_score'] = np.clip(results['monolith_score'] + (results['dark_edge'] * 100), 0, 100)

        # 8. Scientific Deep-Dive (Phase 6)
        if self.hmm:
            # Use last 100 price changes as observations (binned 0-9)
            prices = df['close'].values
            pct_changes = np.diff(prices) / prices[:-1]
            bins = np.linspace(-0.05, 0.05, 10)
            observations = np.digitize(pct_changes[-100:], bins) - 1
            results['hmm_states'] = self.hmm.estimate_states(observations)
            results['hmm_regime'] = self.hmm.get_regime_label(results['hmm_states'][-1])
            
        if self.physics:
            results['physics_pdf'] = self.physics.feynman_kac_pdf(df['close'].iloc[-1])
            results['quantum_status'] = self.physics.detect_phase_transition(df['close'].iloc[-1], results['physics_pdf'])
            
        if self.topology:
            price_arr = df['close'].values[-50:].reshape(-1, 1)
            onchain_score = results.get('onchain', {})
            onchain_val = onchain_score.get('diffusion_score', 50) if isinstance(onchain_score, dict) else 50
            onchain_arr = float(onchain_val) * np.ones((50, 1)) / 100.0
            results['topology'] = self.topology.generate_topology_report(price_arr, onchain_arr)
            
            # 🏁 QC OVERRIDE: Stability vs Regime contradiction fix
            flux = results['topology'].get('topological_flux', 0)
            if flux > 0.8 and results.get('chaos', {}).get('regime') in ['CALM', 'NORMAL']:
                results['chaos']['regime'] = "TRANSITION (Flux Alert)"
                results['chaos']['classification'] = "TRANSITION"
            
        if self.risk_engine:
            # Update balance if needed; for now use default or adapter metadata
            results['risk_guidance'] = self.risk_engine.get_allocation_guidance(results)
        
        # Calculate confidence
        confidence = self.data_status.calculate_confidence()
        
        # Elite score (Consolidated)
        if self.monolith:
            elite_score = results['monolith_score']
        else:
            elite_score = self._calc_score(results)
        
        # Apply confidence multiplier to score
        elite_score_adjusted = elite_score * confidence
        
        # Add metadata
        results['elite_score'] = elite_score
        results['elite_score_adjusted'] = elite_score_adjusted
        results['confidence'] = confidence
        results['data_status'] = self.data_status
        results['confidence_label'] = self._get_confidence_label(confidence, score=elite_score_adjusted)
        
        # Tag action with confidence
        results['final_action_tagged'] = f"{results['final_action']} ({results['confidence_label']} {confidence:.1%})"
        
        return results
    
    def get_microstructure_snapshot(self) -> Optional[Dict]:
        """Get live microstructure metrics if available"""
        if not hasattr(self, 'micro') or self.micro is None:
            return None
        
        try:
            return self.micro.get_snapshot()
        except:
            return None
    
    def _get_confidence_label(self, confidence: float, score: float = 50.0) -> str:
        """Get human-readable confidence label based primarily on score (Institutional Requirement)"""
        if score >= 70.0:
            return "High Confidence"
        elif score >= 40.0:
            return "Medium Confidence"
        else:
            return "Low Confidence"
    
    def _calc_score(self, r: Dict) -> float:
        """חישוב ציון אליטה (0-100)"""
        scores = []
        scores.append(r.get('onchain', {}).get('diffusion_score', 50))
        
        chaos = r.get('chaos', {}).get('chaos_score', 50)
        if chaos > 90 and r.get('chaos', {}).get('in_cluster'):
            scores.append(90)
        else:
            scores.append(max(0, 100 - chaos))
        
        return sum(scores) / len(scores) if scores else 50
    
    def render_elite_section(self, st, results: Dict, df: pd.DataFrame):
        """תצוגה ב-Streamlit עם Data Tier + Confidence"""
        
        st.markdown("---")
        st.header("🧬 Elite Analysis")
        
        # Data Status Banner (PROMINENT)
        confidence = results.get('confidence', 0.0)
        confidence_label = results.get('confidence_label', 'Unknown')
        data_status = results.get('data_status')
        
        # Color coding
        if confidence >= 0.8:
            conf_color = "🟢"
        elif confidence >= 0.6:
            conf_color = "🟡"
        elif confidence >= 0.4:
            conf_color = "🟠"
        else:
            conf_color = "🔴"
        
        # Determine offline modules
        offline_list = []
        if data_status:
            if data_status.ohlcv != DataTier.LIVE: offline_list.append("Price/OHLCV")
            if data_status.onchain not in [DataTier.LIVE, DataTier.PROXY]: offline_list.append("On-chain")
            if data_status.chaos != DataTier.LIVE: offline_list.append("Chaos Engine")
            if data_status.gates != DataTier.LIVE: offline_list.append("Execution Gates")
            if data_status.manifold != DataTier.LIVE: offline_list.append("Manifold Alpha")
            if data_status.nlp != DataTier.LIVE: offline_list.append("NLP Sentiment")

        st.info(f"""
        **Data Tier Status:**
        - Price: {data_status.ohlcv.value if data_status else 'N/A'}
        - On-chain: {data_status.onchain.value if data_status else 'N/A'}
        - Chaos: {data_status.chaos.value if data_status else 'N/A'}
        - Gates: {data_status.gates.value if data_status else 'N/A'}
        - Manifold: {data_status.manifold.value if data_status else 'N/A'}
        - NLP: {data_status.nlp.value if data_status else 'N/A'}
        
        **System Confidence:** {conf_color} {confidence:.1%} ({confidence_label})
        {f'**⛔ OFFLINE:** {", ".join(offline_list)}' if offline_list else '✅ ALL MODULES LIVE'}
        """)
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            elite_score = results.get('elite_score_adjusted', results.get('elite_score', 50))
            st.metric("Elite Score", f"{elite_score:.0f}/100")
        
        with col2:
            final_action = results.get('final_action_tagged', results.get('final_action', 'HOLD'))
            st.metric("Final Action", final_action)
        
        with col3:
            modules_active = sum([
                data_status.ohlcv == DataTier.LIVE if data_status else False,
                data_status.onchain in [DataTier.LIVE, DataTier.PROXY] if data_status else False,
                data_status.chaos == DataTier.LIVE if data_status else False,
                data_status.gates == DataTier.LIVE if data_status else False,
                data_status.manifold == DataTier.LIVE if data_status else False,
                data_status.nlp == DataTier.LIVE if data_status else False,
            ])
            st.metric("Active Modules", f"{modules_active}/6")
        
        with col4:
            gates_pass = results.get('gates', {}).get('allow_trade', False)
            st.metric("Execution Gates", "✅ PASS" if gates_pass else "❌ FAIL")
        
        # Detailed breakdown
        t1, t2, t3, t4 = st.tabs(["📡 On-chain", "💥 Chaos", "🚦 Gates", "📊 Summary"])
        
        with t1:
            self._show_onchain(st, results)
        with t2:
            self._show_chaos(st, results, df)
        with t3:
            self._show_gates(st, results)
        with t4:
            self._show_summary(st, results)
    
    def _show_onchain(self, st, r):
        onchain = r.get('onchain', {})
        st.metric("Diffusion Score", f"{onchain.get('diffusion_score', 50):.0f}/100")
        st.metric("Signal", onchain.get('signal', 'NEUTRAL'))
        st.info(onchain.get('interpretation', 'No data'))
        
        source = onchain.get('data_source', 'N/A')
        netflow = onchain.get('recent_netflow', None)
        if netflow is not None:
            direction = '\u2193 Accumulation' if netflow < 0 else '\u2191 Distribution'
            st.caption(f"📡 Source: **{source}** | Netflow (7d avg): `{netflow:+.1f} BTC` — {direction}")
        
        if not onchain.get('has_real_data'):
            st.warning("⚠️  No API key — using proxy metrics")
            st.code("# Set one of these env vars:\nexport CRYPTOQUANT_API_KEY=your_key\nexport GLASSNODE_API_KEY=your_key")
    
    def _show_chaos(self, st, r, df):
        chaos = r.get('chaos', {})
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Violence", f"{chaos.get('violence', 0):.2f}")
        col2.metric("Chaos Score", f"{chaos.get('chaos_score', 0):.0f}/100")
        col3.metric("Class", chaos.get('classification', 'CALM'))
        
        st.info(chaos.get('interpretation', ''))
        
        # Position sizing
        try:
            pos = self.chaos.get_antifragile_position_size(df, 1000)
            st.write(f"**Position Size:** {pos['position_multiplier']}x (${pos['adjusted_size']:,.0f})")
            st.write(f"Reason: {pos['reason']}")
        except:
            pass
    
    def _show_gates(self, st, r):
        gates = r.get('gates', {})
        can_trade = gates.get('can_trade', gates.get('allow_trade', False))
        
        if can_trade:
            st.success("✅ All gates PASSED")
        else:
            failed_name = gates.get('failed_gate', 'Unknown Protocol Breach')
            st.error(f"❌ FAILED: {failed_name}")
            st.warning(gates.get('recommendation', 'Stand by for market stabilization.'))
        
        for gate in gates.get('gates', []):
            status_val = gate.status.value if hasattr(gate.status, 'value') else str(gate.status)
            emoji = "✅" if status_val == "OPEN" else "🟡" if status_val == "CAUTION" else "❌"
            st.write(f"{emoji} {gate.gate_name}: {gate.reason}")
    
    def _show_summary(self, st, r):
        st.subheader("Elite System Summary")
        
        # Data tier breakdown
        st.write("**Data Tier Status:**")
        data_status = r.get('data_status')
        if data_status:
            st.code(data_status.get_summary())
        else:
            st.warning("Data status not available")
        
        # Microstructure snapshot (if live)
        if hasattr(self, 'micro') and self.micro:
            st.write("\n**🔴 Live Microstructure:**")
            try:
                # Add a check for empty/connecting state
                snapshot = self.micro.get_snapshot()
                if not snapshot or not snapshot.get('truecvd'):
                     st.write("- Microstructure: OFFLINE (Institutional Latency)")
                else:
                    st.write(f"- TRUECVD: {snapshot['truecvd']:+.2f}")
                    st.write(f"- Book Imbalance: {snapshot['book_imbalance']:+.3f}")
                    st.write(f"- Spread: {snapshot['spread_bps']:.1f} bps")
                    st.write(f"- Trade Flow (5min): {snapshot['trade_flow']['imbalance']:+.3f}")
            except:
                st.write("- Microstructure: OFFLINE (Connection Dropped)")
        else:
             st.write("\n**🔴 Live Microstructure: DISABLED**")
        
        # Confidence breakdown
        confidence = r.get('confidence', 0.0)
        st.write(f"\n**Confidence Analysis:**")
        st.write(f"- Raw Score: {r.get('elite_score', 0):.0f}/100")
        st.write(f"- Confidence Multiplier: {confidence:.1%}")
        st.write(f"- Adjusted Score: {r.get('elite_score_adjusted', 0):.0f}/100")
        st.write(f"- Confidence Label: {r.get('confidence_label', 'Unknown')}")
        
        # Action recommendation
        st.write(f"\n**Recommendation:**")
        st.write(f"- Base Action: {r.get('base_action', 'HOLD')}")
        st.write(f"- Final Action: {r.get('final_action', 'HOLD')}")
        st.write(f"- Tagged: {r.get('final_action_tagged', 'N/A')}")
        
        # Module breakdown
        st.write(f"\n**Module Signals:**")
        st.write(f"- Price: ${r.get('price', 0):,.0f}")
        st.write(f"- On-chain: {r.get('onchain', {}).get('signal', 'N/A')}")
        st.write(f"- Chaos: {r.get('chaos', {}).get('classification', 'N/A')}")
        st.write(f"- Gates: {'PASS' if r.get('gates', {}).get('allow_trade') else 'FAIL'}")
        
        # Warnings
        if confidence < 0.5:
            st.error(f"⚠️ LOW CONFIDENCE ({confidence:.1%})")
            st.write("Recommendations:")
            st.write("- Consider getting Glassnode API key for real on-chain data")
            st.write("- Add multi-asset data for manifold analysis")
            st.write("- Add news feed for NLP analysis")
            st.write("- With full data tier: confidence could reach 0.9-1.0")
    
    def generate_decision_summary(self, elite_results: Dict, df: pd.DataFrame) -> Dict:
        """
        Generate decision summary for DecisionInterpreter
        
        Args:
            elite_results: Results from analyze_elite()
            df: Price dataframe
            
        Returns:
            Dict with:
            - direction: 'BUY', 'SELL', 'HOLD'
            - reasoning: List[str] of reasons
            - size_multiplier: float (0.0-2.0)
            - confidence: float (0.0-1.0)
            - risk_factors: List[str]
            - supporting_signals: List[str]
        """
        
        # Extract key metrics
        final_action = elite_results.get('final_action', 'HOLD')
        elite_score = elite_results.get('elite_score', 50)
        confidence = elite_results.get('confidence', 0.5)
        
        # Map action to direction
        if 'ADD' in final_action:
            direction = 'BUY'
        elif 'REDUCE' in final_action:
            direction = 'SELL'
        else:
            direction = 'HOLD'
        
        # Size multiplier based on action
        size_map = {
            'ADD_AGGRESSIVE': 2.0,
            'ADD_SMALL': 1.0,
            'HOLD': 0.5,
            'REDUCE_20': 0.8,
            'REDUCE_35': 0.6
        }
        size_multiplier = size_map.get(final_action, 1.0)
        
        # Build reasoning
        reasoning = []
        
        # On-chain signal
        onchain = elite_results.get('onchain', {})
        if onchain.get('signal'):
            reasoning.append(f"On-chain: {onchain['signal']}")
        
        # Chaos/regime
        chaos = elite_results.get('chaos', {})
        if chaos.get('regime'):
            reasoning.append(f"Market regime: {chaos['regime']}")
        
        # Manifold
        manifold = elite_results.get('manifold', {})
        if manifold.get('regime'):
            reasoning.append(f"Multi-asset regime: {manifold['regime']}")
        
        # NLP sentiment
        nlp = elite_results.get('nlp', {})
        if nlp.get('sentiment') is not None:
            sentiment_val = nlp['sentiment']
            if sentiment_val > 0.3:
                reasoning.append("News sentiment: Positive")
            elif sentiment_val < -0.3:
                reasoning.append("News sentiment: Negative")
            else:
                reasoning.append("News sentiment: Neutral")
        
        # Elite score
        reasoning.append(f"Elite score: {elite_score:.0f}/100")
        
        # Risk factors
        risk_factors = []
        
        gates = elite_results.get('gates', {})
        if not gates.get('allow_trade', True):
            risk_factors.append("⚠️ Execution gates CLOSED - high risk environment")
        
        if confidence < 0.5:
            risk_factors.append("⚠️ Low system confidence - data quality issues")
        
        if chaos.get('violence_score', 0) > 70:
            risk_factors.append("⚠️ High market violence - expect volatility")
        
        # Supporting signals
        supporting_signals = []
        
        if confidence > 0.8:
            supporting_signals.append("✅ High system confidence")
        
        if gates.get('allow_trade', False):
            supporting_signals.append("✅ All execution gates OPEN")
        
        if elite_score > 70:
            supporting_signals.append("✅ Strong bullish signal")
        elif elite_score < 30:
            supporting_signals.append("✅ Strong bearish signal (consider shorting)")
        
        return {
            'direction': direction,
            'reasoning': reasoning,
            'size_multiplier': size_multiplier,
            'confidence': confidence,
            'risk_factors': risk_factors,
            'supporting_signals': supporting_signals,
            'elite_score': elite_score,
            'final_action': final_action
        }



# =============================================================================
# הוראות שימוש
# =============================================================================

"""
איך לשלב בדאשבורד שלך:

1. בראש הקובץ:
   
   from dashboard_adapter import EliteDashboardAdapter
   
   @st.cache_resource
   def init_elite():
       return EliteDashboardAdapter()
   
   adapter = init_elite()

2. בפונקציית analyze() שלך:
   
   # הניתוח הקיים שלך
   your_action = your_existing_logic()
   
   # הוסף Elite
   elite = adapter.analyze_elite(
       df=df,
       exposure_pct=15.0,
       base_action=your_action
   )
   
   final_action = elite['final_action']

3. בתצוגה:
   
   # הוסף טאב חדש
   with st.expander("🧬 Elite Analysis"):
       adapter.render_elite_section(st, elite, df)

זהו!
"""

if __name__ == '__main__':
    print(__doc__)
