"""
Manifold Premium Layer
- RegimeDetector: מזהה משטרי שוק
- NLPSentimentAnalyzer: NLP עם FinBERT + Temporal Decay
- ManifoldEngine: ציון מניפולד עם משקלים לפי Regime + NLP
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
import time
import requests
import numpy as np


# ========= Regime Detection =========

@dataclass
class RegimeSignal:
    """Single regime score with confidence"""
    regime: str
    confidence: float  # 0.0-1.0
    contributing_factors: Dict[str, float]


class RegimeDetector:
    """
    Multi-dimensional regime detection
    
    Regimes:
    - blood_in_streets: Extreme fear + heavy outflows (BEST buy signal)
    - capitulation: Extreme fear + moderate outflows
    - short_squeeze_risk: Negative funding + price rising
    - long_squeeze_risk: Positive funding + price falling
    - distribution_top: Extreme greed + inflows to exchanges
    - deleveraging: Extreme funding unwind
    - normal: No extreme conditions
    """
    
    def __init__(self):
        # Regime thresholds (tunable)
        self.thresholds = {
            "fg_extreme_fear": 20,
            "fg_extreme_greed": 80,
            "funding_extreme": 0.01,  # 1% = extreme
            "netflow_strong": 2.0,    # z-score
        }
    
    def detect(self, features: Dict[str, float]) -> RegimeSignal:
        """
        Detect current market regime
        
        features:
            fg_index: 0-100
            funding_skew: float (typically -0.02 to +0.02)
            netflow_z: z-score
            onchain_bias: -1 to +1
            price_change_1h: float (optional)
        """
        fg = features.get("fg_index", 50.0)
        funding = features.get("funding_skew", 0.0)
        netflow_z = features.get("netflow_z", 0.0)
        onchain_bias = features.get("onchain_bias", 0.0)
        price_change = features.get("price_change_1h", 0.0)
        
        regime_scores: Dict[str, float] = {}
        
        # 1. BLOOD IN STREETS (extreme fear + strong accumulation)
        if fg < self.thresholds["fg_extreme_fear"] and netflow_z < -2:
            fear_intensity = (self.thresholds["fg_extreme_fear"] - fg) / 20.0  # 0-1
            accumulation_intensity = min(1.0, abs(netflow_z) / 3.0)  # z-score to 0-1
            regime_scores["blood_in_streets"] = min(
                1.0, (fear_intensity + accumulation_intensity) / 2.0
            )
        
        # 2. CAPITULATION (fear without heavy accumulation yet)
        elif fg < self.thresholds["fg_extreme_fear"]:
            fear_intensity = (self.thresholds["fg_extreme_fear"] - fg) / 20.0
            regime_scores["capitulation"] = fear_intensity * 0.8  # slightly lower
        
        # 3. SHORT SQUEEZE RISK (negative funding + price might spike)
        if funding < -self.thresholds["funding_extreme"]:
            funding_intensity = min(1.0, abs(funding) / 0.02)
            price_boost = 1.2 if price_change > 0 else 1.0
            regime_scores["short_squeeze_risk"] = min(
                1.0, funding_intensity * price_boost
            )
        
        # 4. LONG SQUEEZE RISK (positive funding + price falling)
        if funding > self.thresholds["funding_extreme"]:
            funding_intensity = min(1.0, funding / 0.02)
            price_boost = 1.2 if price_change < 0 else 1.0
            regime_scores["long_squeeze_risk"] = min(
                1.0, funding_intensity * price_boost
            )
        
        # 5. DISTRIBUTION TOP (greed + coins flowing to exchanges)
        if fg > self.thresholds["fg_extreme_greed"] and netflow_z > 2:
            greed_intensity = (fg - self.thresholds["fg_extreme_greed"]) / 20.0
            distribution_intensity = min(1.0, netflow_z / 3.0)
            regime_scores["distribution_top"] = min(
                1.0, (greed_intensity + distribution_intensity) / 2.0
            )
        
        # 6. DELEVERAGING (extreme funding unwind)
        if abs(funding) > 0.015:  # 1.5%+ = crisis
            regime_scores["deleveraging"] = min(1.0, abs(funding) / 0.03)
        
        # No regimes hit → normal
        if not regime_scores:
            return RegimeSignal(
                regime="normal",
                confidence=1.0,
                contributing_factors={
                    "fear_greed": fg,
                    "funding": funding,
                    "netflow_z": netflow_z,
                    "onchain_bias": onchain_bias,
                },
            )
        
        # Winner Takes All dominant regime
        dominant_regime, dom_score = max(
            regime_scores.items(), key=lambda x: x[1]
        )
        
        return RegimeSignal(
            regime=dominant_regime,
            confidence=dom_score,
            contributing_factors={
                "fear_greed": fg,
                "funding": funding,
                "netflow_z": netflow_z,
                "onchain_bias": onchain_bias,
            },
        )
    
    def get_regime_weights(self, regime: str) -> Dict[str, float]:
        """
        Return optimal signal weights for each regime
        
        Keys:
        - onchain
        - funding
        - fg
        - netflow
        - nlp
        """
        weights = {
            "blood_in_streets": {
                "onchain": 0.7,   # On-chain is king during capitulation
                "funding": 0.1,
                "fg": 0.1,
                "netflow": 0.1,
                "nlp": 0.0,       # Ignore noise during blood in streets
            },
            "capitulation": {
                "onchain": 0.6,
                "funding": 0.15,
                "fg": 0.15,
                "netflow": 0.1,
                "nlp": 0.0,
            },
            "short_squeeze_risk": {
                "funding": 0.6,   # Funding is key signal
                "onchain": 0.2,
                "fg": 0.1,
                "netflow": 0.05,
                "nlp": 0.05,
            },
            "long_squeeze_risk": {
                "funding": 0.6,
                "onchain": 0.2,
                "fg": 0.1,
                "netflow": 0.05,
                "nlp": 0.05,
            },
            "distribution_top": {
                "netflow": 0.4,   # Exchange flows matter most
                "onchain": 0.3,
                "fg": 0.2,
                "funding": 0.05,
                "nlp": 0.05,
            },
            "deleveraging": {
                "funding": 0.5,
                "onchain": 0.25,
                "netflow": 0.15,
                "fg": 0.05,
                "nlp": 0.05,
            },
            "normal": {
                "onchain": 0.35,
                "funding": 0.25,
                "fg": 0.2,
                "netflow": 0.15,
                "nlp": 0.05,
            },
        }
        return weights.get(regime, weights["normal"])


# ========= NLP Sentiment with Temporal Decay =========

@dataclass
class SentimentResult:
    """NLP sentiment analysis result"""
    sentiment: float       # -1 to +1
    headline_risk: float   # 0 to 1 (volatility/extremes)
    disagreement: float    # 0 to 1 (std of scores normalized)
    n_headlines: int
    n_fresh: int           # headlines < 1 hour old
    source: str


class NLPSentimentAnalyzer:
    """
    Temporal-weighted sentiment analysis
    
    Features:
    - Exponential decay: recent headlines matter more
    - Disagreement metric: high variance = uncertain market
    - FinBERT or keyword-based fallback
    """
    
    def __init__(
        self,
        cryptopanic_token: Optional[str] = None,
        half_life_hours: float = 3.0,
        use_finbert: bool = True,
    ):
        """
        Args:
            cryptopanic_token: API token for CryptoPanic (free tier = 50/day)
            half_life_hours: Time for headline weight to decay by 50%
            use_finbert: Use local FinBERT model (True) or simple heuristics (False)
        """
        self.cryptopanic_token = cryptopanic_token
        self.half_life_hours = half_life_hours
        self.decay_lambda = np.log(2) / half_life_hours
        
        self.use_finbert = use_finbert
        if use_finbert:
            try:
                from transformers import pipeline
                self.sentiment_model = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert"
                )
                print("✅ FinBERT loaded successfully")
            except Exception as e:
                print(f"⚠️ FinBERT load failed: {e}")
                print("   Falling back to keyword-based sentiment")
                self.use_finbert = False
                self.sentiment_model = None
        else:
            self.sentiment_model = None
    
    def fetch_headlines_cryptopanic(
        self,
        symbol: str = "BTC",
        limit: int = 20,
    ) -> List[Dict]:
        """
        Fetch recent headlines from CryptoPanic
        
        Returns:
            List of {title, published_at, url}
        """
        if not self.cryptopanic_token:
            print("⚠️ No CryptoPanic token - using stub data")
            return self._stub_headlines()
        
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": self.cryptopanic_token,
            "currencies": symbol,
            "public": "true",
            "kind": "news",
            "filter": "hot",
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            headlines = []
            for item in data.get("results", [])[:limit]:
                headlines.append({
                    "title": item["title"],
                    "published_at": item["published_at"],  # ISO timestamp
                    "url": item.get("url", ""),
                })
            
            return headlines
        
        except Exception as e:
            print(f"⚠️ CryptoPanic fetch failed: {e}")
            return self._stub_headlines()
    
    def _stub_headlines(self) -> List[Dict]:
        """Stub data for testing without API"""
        now = int(time.time())
        return [
            {
                "title": "Bitcoin holds steady above support",
                "published_at": now - 1800,
                "url": "",
            },
            {
                "title": "Whales accumulate BTC during dip",
                "published_at": now - 3600,
                "url": "",
            },
            {
                "title": "Market uncertainty remains high",
                "published_at": now - 7200,
                "url": "",
            },
        ]
    
    def analyze_sentiment_finbert(self, headlines: List[str]) -> List[float]:
        """
        Use FinBERT to analyze sentiment
        
        Returns:
            List of scores -1 to +1
        """
        if not self.sentiment_model:
            return self.analyze_sentiment_keywords(headlines)
        
        try:
            results = self.sentiment_model(headlines)
            
            label_map = {
                "positive": 1.0,
                "negative": -1.0,
                "neutral": 0.0,
            }
            
            scores = []
            for result in results:
                label = result["label"].lower()
                confidence = result["score"]
                base_score = label_map.get(label, 0.0)
                score = base_score * confidence  # weight by confidence
                scores.append(score)
            
            return scores
        
        except Exception as e:
            print(f"⚠️ FinBERT analysis failed: {e}")
            return self.analyze_sentiment_keywords(headlines)
    
    def analyze_sentiment_keywords(self, headlines: List[str]) -> List[float]:
        """
        Fallback: Simple keyword-based sentiment
        """
        positive_words = {
            "surge", "rally", "bullish", "gains", "soar", "breakout",
            "adoption", "breakthrough", "support", "accumulate", "buy",
        }
        negative_words = {
            "crash", "dump", "bearish", "losses", "plunge", "breakdown",
            "sell-off", "fear", "panic", "resistance", "decline", "drop",
        }
        
        scores = []
        for headline in headlines:
            headline_lower = headline.lower()
            
            pos_count = sum(1 for word in positive_words if word in headline_lower)
            neg_count = sum(1 for word in negative_words if word in headline_lower)
            
            if pos_count + neg_count > 0:
                score = (pos_count - neg_count) / (pos_count + neg_count)
            else:
                score = 0.0
            
            scores.append(score)
        
        return scores
    
    def calculate_decay_weight(self, age_hours: float) -> float:
        """
        Exponential decay: w(t) = exp(-λt)
        """
        return float(np.exp(-self.decay_lambda * age_hours))
    
    def analyze(self, symbol: str = "BTC") -> SentimentResult:
        """
        Full analysis with temporal decay
        """
        headlines_data = self.fetch_headlines_cryptopanic(symbol, limit=20)
        
        if not headlines_data:
            return SentimentResult(
                sentiment=0.0,
                headline_risk=0.0,
                disagreement=0.0,
                n_headlines=0,
                n_fresh=0,
                source="none",
            )
        
        titles = [h["title"] for h in headlines_data]
        raw_scores = self.analyze_sentiment_finbert(titles)
        
        now = time.time()
        weighted_scores: List[float] = []
        weights: List[float] = []
        ages_hours: List[float] = []
        
        for headline, score in zip(headlines_data, raw_scores):
            if isinstance(headline["published_at"], str):
                import dateutil.parser
                pub_time = dateutil.parser.parse(headline["published_at"]).timestamp()
            else:
                pub_time = headline["published_at"]
            
            age_hours = (now - pub_time) / 3600.0
            ages_hours.append(age_hours)
            
            weight = self.calculate_decay_weight(age_hours)
            weights.append(weight)
            weighted_scores.append(score * weight)
        
        total_weight = sum(weights)
        if total_weight > 0:
            avg_sentiment = sum(weighted_scores) / total_weight
        else:
            avg_sentiment = 0.0
        
        disagreement = float(np.std(raw_scores)) if len(raw_scores) > 1 else 0.0
        
        extreme_scores = [abs(s) for s in raw_scores if abs(s) > 0.5]
        headline_risk = min(1.0, len(extreme_scores) / len(raw_scores)) if raw_scores else 0.0
        
        n_fresh = sum(1 for age in ages_hours if age < 1.0)
        
        source = "cryptopanic+finbert" if self.use_finbert else "cryptopanic+keywords"
        
        return SentimentResult(
            sentiment=float(avg_sentiment),
            headline_risk=float(headline_risk),
            disagreement=disagreement,
            n_headlines=len(headlines_data),
            n_fresh=n_fresh,
            source=source,
        )


# ========= Manifold Engine =========

@dataclass
class ManifoldResult:
    score: float              # -1..+1
    regime: str
    regime_confidence: float  # 0..1
    weights: Dict[str, float] # normalized weights
    raw_features: Dict[str, float]
    nlp: Optional[SentimentResult]


class ManifoldEngine:
    """
    Manifold score with regime-aware, dynamic weights and NLP input.
    """
    def __init__(
        self,
        detector: Optional[RegimeDetector] = None,
        nlp_analyzer: Optional[NLPSentimentAnalyzer] = None,
        nlp_enabled: bool = True,
    ):
        self.detector = detector or RegimeDetector()
        self.nlp_analyzer = nlp_analyzer
        self.nlp_enabled = nlp_enabled
    
    def compute(
        self,
        features: Dict[str, float],
        symbol: str = "BTC",
    ) -> ManifoldResult:
        # NLP sentiment
        nlp_result: Optional[SentimentResult] = None
        nlp_sentiment = 0.0
        
        if self.nlp_enabled and self.nlp_analyzer is not None:
            nlp_result = self.nlp_analyzer.analyze(symbol)
            nlp_sentiment = nlp_result.sentiment
        
        # Regime detection
        regime_signal = self.detector.detect(features)
        base_weights = self.detector.get_regime_weights(regime_signal.regime)
        
        fg_index = features.get("fg_index", 50.0)
        fg_component = (fg_index - 50.0) / 50.0
        
        onchain_bias = features.get("onchain_bias", 0.0)
        funding_skew = features.get("funding_skew", 0.0)
        netflow_z = features.get("netflow_z", 0.0)
        
        total_w = sum(base_weights.values())
        weights_norm = {k: v / total_w for k, v in base_weights.items()}
        
        score = (
            weights_norm["onchain"] * onchain_bias +
            weights_norm["funding"] * funding_skew +
            weights_norm["fg"] * fg_component +
            weights_norm["netflow"] * netflow_z +
            weights_norm["nlp"] * nlp_sentiment
        )
        
        score = max(-1.0, min(1.0, score))
        
        return ManifoldResult(
            score=score,
            regime=regime_signal.regime,
            regime_confidence=regime_signal.confidence,
            weights=weights_norm,
            raw_features={
                "onchain_bias": onchain_bias,
                "funding_skew": funding_skew,
                "fg_component": fg_component,
                "netflow_z": netflow_z,
                "nlp_sentiment": nlp_sentiment,
            },
            nlp=nlp_result,
        )


# ========= Example usage =========

if __name__ == "__main__":
    # Init NLP (ל‑dev אפשר token=None ו‑use_finbert=False)
    nlp = NLPSentimentAnalyzer(
        cryptopanic_token=None,
        half_life_hours=3.0,
        use_finbert=False,
    )
    
    detector = RegimeDetector()
    engine = ManifoldEngine(detector=detector, nlp_analyzer=nlp, nlp_enabled=True)
    
    features = {
        "fg_index": 12.0,
        "funding_skew": -0.005,
        "netflow_z": -2.8,
        "onchain_bias": 0.6,
        "price_change_1h": -0.02,
    }
    
    result = engine.compute(features, symbol="BTC")
    
    print(f"Regime: {result.regime} ({result.regime_confidence:.0%})")
    print(f"Manifold score: {result.score:+.3f}")
    print("Weights:", result.weights)
    if result.nlp:
        print(f"NLP sentiment: {result.nlp.sentiment:+.3f}, "
              f"risk={result.nlp.headline_risk:.2%}, "
              f"disagreement={result.nlp.disagreement:.3f}, "
              f"n={result.nlp.n_headlines}, fresh={result.nlp.n_fresh}")
