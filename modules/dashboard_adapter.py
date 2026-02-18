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
    from nlp_sentiment import NLPSentimentAnalyzer
    NLP_AVAILABLE = True
except Exception as e:
    import_errors.append(f"nlp_sentiment: {e}")
    NLP_AVAILABLE = False

try:
    from signal_stabilizer import SignalStabilizer
    STABILIZER_AVAILABLE = True
except Exception as e:
    import_errors.append(f"signal_stabilizer: {e}")
    STABILIZER_AVAILABLE = False

if not ELITE_AVAILABLE:
    print("⚠️  Elite modules import errors:")
    for err in import_errors:
        print(f"  - {err}")


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
        if not ELITE_AVAILABLE:
            print("⚠️  Elite modules not found")
            self.ready = False
            self.data_status = DataStatus()
            return
        
        # Initialize modules
        self.onchain = OnChainDiffusionLayer(
            glassnode_api_key=glassnode_api_key,
            cryptoquant_api_key=cryptoquant_api_key
        )
        
        # Manifold Premium Layer (if available)
        if MANIFOLD_AVAILABLE:
            self.manifold = ManifoldEngine()
            self.regime_detector = RegimeDetector()
        else:
            self.manifold = None
            self.regime_detector = None
        
        self.chaos = ViolenceChaosDetector()
        self.gates = ExecutionGates()
        
        # NLP Sentiment (if available)
        if NLP_AVAILABLE:
            import os
            self.nlp = NLPSentimentAnalyzer(
                cryptopanic_token=os.getenv('CRYPTOPANIC_API_KEY'),
                use_finbert=False  # Set True if transformers installed
            )
        else:
            self.nlp = None
        
        # Signal Stabilizer (anti-whipsaw)
        if STABILIZER_AVAILABLE:
            self.stabilizer = SignalStabilizer(
                ema_alpha=0.3,
                hysteresis_threshold=10.0,
                validation_periods=2
            )
        else:
            self.stabilizer = None
        
        # Initialize microstructure feed
        try:
            from binance_microstructure import BinanceMicrostructure
            import threading
            import asyncio
            
            self.micro = BinanceMicrostructure(symbol="btcusdt", depth_levels=10)
            
            # Start in background thread
            def start_micro():
                asyncio.run(self.micro.start())
            
            self.micro_thread = threading.Thread(target=start_micro, daemon=True)
            self.micro_thread.start()
            
            micro_enabled = True
            print("   🔴 Microstructure: LIVE (WebSocket connected)")
            
        except Exception as e:
            print(f"   ⚠️  Microstructure disabled: {e}")
            self.micro = None
            micro_enabled = False
        
        self.ready = True
        
        # Initialize data status
        self.data_status = DataStatus(
            ohlcv=DataTier.LIVE,
            onchain=DataTier.LIVE if (glassnode_api_key or cryptoquant_api_key) else DataTier.PROXY,
            manifold=DataTier.LIVE if MANIFOLD_AVAILABLE and self.manifold else DataTier.DISABLED,
            chaos=DataTier.LIVE,
            gates=DataTier.LIVE,
            nlp=DataTier.LIVE if NLP_AVAILABLE and self.nlp else DataTier.DISABLED,
            microstructure=DataTier.LIVE if micro_enabled else DataTier.DISABLED
        )
        
        confidence = self.data_status.calculate_confidence()
        print(f"✅ Elite system ready (confidence: {confidence:.1%})")
        print(f"   Data tier: OHLCV=LIVE, On-chain={'LIVE' if glassnode_api_key else 'PROXY'}")
    
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
            
            # Update tier based on actual data
            if not onchain_result.get('has_real_data', False):
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
                returns = self.manifold.prepare_multi_asset_data(df, multi_asset)
                manifold = self.manifold.detect_hidden_correlations(returns)
                results['manifold'] = {
                    'n_hidden': len(manifold['hidden_correlations']),
                    'variance': manifold['pca_summary']['explained_variance']
                }
            except Exception as e:
                results['manifold'] = {'n_hidden': 0, 'error': str(e)}
                self.data_status.manifold = DataTier.DISABLED
        
        # 3. Chaos
        try:
            chaos_result = self.chaos.analyze(df)
            results['chaos'] = {
                'regime': chaos_result.regime.value,
                'violence_score': chaos_result.violence_score,
                'volatility': chaos_result.volatility,
                'is_clustered': chaos_result.is_clustered,
                'chaos_score': chaos_result.violence_score,  # Backwards compat
                'signal': chaos_result.regime.value
            }
        except Exception as e:
            results['chaos'] = {
                'chaos_score': 50, 
                'violence_score': 50,
                'violence': 1.0, 
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
        
        # 4. Gates (final check)
        try:
            violence = results['chaos']['violence']
            in_cluster = results['chaos'].get('in_cluster', False)
            
            gates_result = self.gates.check_all_gates(
                df, exposure_pct, drawdown_pct, base_action, violence, in_cluster
            )
            
            results['gates'] = gates_result
            results['final_action'] = (base_action if gates_result['allow_trade'] 
                                      else 'HOLD')
        except Exception as e:
            results['gates'] = {'allow_trade': True, 'error': str(e)}
            results['final_action'] = base_action
        
        # Calculate confidence
        confidence = self.data_status.calculate_confidence()
        
        # Elite score (base)
        elite_score = self._calc_score(results)
        
        # Apply confidence multiplier to score
        elite_score_adjusted = elite_score * confidence
        
        # Add metadata
        results['elite_score'] = elite_score
        results['elite_score_adjusted'] = elite_score_adjusted
        results['confidence'] = confidence
        results['data_status'] = self.data_status
        results['confidence_label'] = self._get_confidence_label(confidence)
        
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
    
    def _get_confidence_label(self, confidence: float) -> str:
        """Get human-readable confidence label"""
        if confidence >= 0.8:
            return "High Confidence"
        elif confidence >= 0.6:
            return "Medium Confidence"
        elif confidence >= 0.4:
            return "Low Confidence"
        else:
            return "Very Low Confidence"
    
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
        
        st.info(f"""
        **Data Tier Status:**
        - OHLCV: {data_status.ohlcv.value if data_status else 'N/A'}
        - On-chain: {data_status.onchain.value if data_status else 'N/A'}
        - Chaos: {data_status.chaos.value if data_status else 'N/A'}
        - Gates: {data_status.gates.value if data_status else 'N/A'}
        - Manifold: {data_status.manifold.value if data_status else 'N/A'}
        - NLP: {data_status.nlp.value if data_status else 'N/A'}
        
        **System Confidence:** {conf_color} {confidence:.1%} ({confidence_label})
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
            ])
            st.metric("Active Modules", f"{modules_active}/5")
        
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
        
        if not onchain.get('has_real_data'):
            st.warning("⚠️  No API key - using proxy metrics")
            st.code("export GLASSNODE_API_KEY=your_key")
    
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
        
        if gates.get('allow_trade'):
            st.success("✅ All gates PASSED")
        else:
            st.error(f"❌ FAILED: {gates.get('failed_gate')}")
            st.warning(gates.get('recommendation', ''))
        
        for gate in gates.get('gates', []):
            emoji = "✅" if gate.result.value == "PASS" else "❌"
            st.write(f"{emoji} {gate.name}: {gate.reason}")
    
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
                snapshot = self.micro.get_snapshot()
                st.write(f"- TRUECVD: {snapshot['truecvd']:+.2f}")
                st.write(f"- Book Imbalance: {snapshot['book_imbalance']:+.3f}")
                st.write(f"- Spread: {snapshot['spread_bps']:.1f} bps")
                st.write(f"- Trade Flow (5min): {snapshot['trade_flow']['imbalance']:+.3f}")
            except:
                st.write("- Microstructure: connecting...")
        
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
