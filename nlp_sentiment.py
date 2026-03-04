"""
NLP Sentiment Analysis with Temporal Decay + Geopolitical OSINT Shield
Combines CryptoPanic headlines + RSS fallback with FinBERT local model.
Military keyword scanner bypasses decay for zero-latency threat detection.
"""

import requests
import time
import math
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

# ── Nature Events Engine (synthetic geo-headlines for FinBERT) ──
try:
    from nature_events_engine import NatureEventsEngine, EVENT_WEIGHTS
    _NLP_NATURE_AVAILABLE = True
except ImportError:
    _NLP_NATURE_AVAILABLE = False


# ============================================================================
# GEOPOLITICAL OSINT KEYWORDS — Military/Security Threat Detection
# Bypasses temporal decay. Triggers instant Violence override.
# ============================================================================
GEOPOL_KEYWORDS: Dict[str, Dict] = {
    # ── EXTREME: Violence → 5.0 (instant Kelly lock, Sentinel alarm) ──
    "IRGC":                {"severity": "EXTREME", "violence": 5.0},
    "Strait of Hormuz":    {"severity": "EXTREME", "violence": 5.0},
    "Hormuz":              {"severity": "EXTREME", "violence": 5.0},
    "nuclear strike":      {"severity": "EXTREME", "violence": 5.0},
    "tactical nuke":       {"severity": "EXTREME", "violence": 5.0},
    "ICBM launch":         {"severity": "EXTREME", "violence": 5.0},
    "martial law":         {"severity": "EXTREME", "violence": 5.0},
    "carrier strike group":{"severity": "EXTREME", "violence": 5.0},
    "DEFCON":              {"severity": "EXTREME", "violence": 5.0},
    "Khamenei":            {"severity": "EXTREME", "violence": 5.0},
    "tanker blockade":     {"severity": "EXTREME", "violence": 5.0},
    "oil embargo":         {"severity": "EXTREME", "violence": 5.0},
    "war declaration":     {"severity": "EXTREME", "violence": 5.0},
    # ── HIGH: Violence → 4.0 (gates likely blocked) ──
    "missile launch":      {"severity": "HIGH", "violence": 4.0},
    "airstrike":           {"severity": "HIGH", "violence": 4.0},
    "air strike":          {"severity": "HIGH", "violence": 4.0},
    "sanctions":           {"severity": "HIGH", "violence": 4.0},
    "Hezbollah":           {"severity": "HIGH", "violence": 4.0},
    "Hamas attack":        {"severity": "HIGH", "violence": 4.0},
    "naval blockade":      {"severity": "HIGH", "violence": 4.0},
    "cyber attack":        {"severity": "HIGH", "violence": 4.0},
    "SWIFT ban":           {"severity": "HIGH", "violence": 4.0},
    "military escalation": {"severity": "HIGH", "violence": 4.0},
    "drone strike":        {"severity": "HIGH", "violence": 4.0},
    "ballistic missile":   {"severity": "HIGH", "violence": 4.0},
    "Iran attack":         {"severity": "HIGH", "violence": 4.0},
    "Israel strike":       {"severity": "HIGH", "violence": 4.0},
    "Red Sea":             {"severity": "HIGH", "violence": 4.0},
    "Houthi":              {"severity": "HIGH", "violence": 4.0},
}

# RSS fallback feeds (financial + geopolitical)
_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]


@dataclass
class SentimentResult:
    """NLP sentiment analysis result"""
    sentiment: float  # -1 to +1
    headline_risk: float  # 0 to 1 (volatility/disagreement)
    disagreement: float  # 0 to 1 (std of scores)
    n_headlines: int
    n_fresh: int  # headlines < 1 hour old
    source: str
    # ── Geopolitical OSINT Shield ──
    geopol_alert: bool = False
    geopol_headline: str = ""
    geopol_severity: str = ""  # "EXTREME" or "HIGH"
    violence_override: float = 0.0  # 0 = no override, 5.0 = EXTREME


class NLPSentimentAnalyzer:
    """
    Temporal-weighted sentiment analysis
    
    Features:
    - Exponential decay: recent headlines matter more
    - Disagreement metric: high variance = uncertain market
    - Multiple sentiment models supported
    """
    
    def __init__(self, 
                 cryptopanic_token: Optional[str] = None,
                 half_life_hours: float = 3.0,
                 use_finbert: bool = True):
        """
        Args:
            cryptopanic_token: API token for CryptoPanic (free tier = 50/day)
            half_life_hours: Time for headline weight to decay by 50%
            use_finbert: Use local FinBERT model (True) or simple heuristics (False)
        """
        self.cryptopanic_token = cryptopanic_token
        self.half_life_hours = half_life_hours
        self.decay_lambda = np.log(2) / half_life_hours
        
        # Initialize sentiment model
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
        
        # ── Nature Events Engine ──
        self._nature_engine = None
        if _NLP_NATURE_AVAILABLE:
            try:
                self._nature_engine = NatureEventsEngine()
                print("✅ Nature Events Engine connected to NLP Sentiment")
            except Exception:
                pass
    
    def fetch_headlines_cryptopanic(self, 
                                   symbol: str = "BTC",
                                   limit: int = 20) -> List[Dict]:
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
                    'title': item['title'],
                    'published_at': item['published_at'],  # ISO timestamp
                    'url': item.get('url', '')
                })
            
            return headlines
            
        except Exception as e:
            print(f"⚠️ CryptoPanic fetch failed: {e}")
            return self._stub_headlines()
    
    def _stub_headlines(self) -> List[Dict]:
        """Stub data for testing without API"""
        now = int(time.time())
        return [
            {'title': 'Bitcoin holds steady above support', 'published_at': now - 1800, 'url': ''},
            {'title': 'Whales accumulate BTC during dip', 'published_at': now - 3600, 'url': ''},
            {'title': 'Market uncertainty remains high', 'published_at': now - 7200, 'url': ''},
        ]

    def _fetch_rss_headlines(self, limit: int = 15) -> List[Dict]:
        """Fallback: fetch headlines from RSS feeds when CryptoPanic is down."""
        headlines = []
        now = int(time.time())
        for feed_url in _RSS_FEEDS:
            try:
                resp = requests.get(feed_url, timeout=8)
                resp.raise_for_status()
                # Simple XML title extraction (no lxml dependency)
                import re
                items = re.findall(r'<item>.*?<title>(?:<\!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', resp.text, re.DOTALL)
                for title in items[:5]:
                    title = title.strip()
                    if title:
                        headlines.append({
                            'title': title,
                            'published_at': now - 1800,  # assume recent
                            'url': feed_url,
                        })
            except Exception:
                continue
            if len(headlines) >= limit:
                break
        return headlines[:limit]

    def scan_geopol_keywords(self, headlines: List[str]) -> Tuple[bool, str, str, float]:
        """
        Scan headlines for military/geopolitical critical keywords.
        Bypasses all temporal decay — instant threat detection.

        Returns:
            (alert_detected, matched_headline, severity, violence_override)
        """
        worst_violence = 0.0
        worst_headline = ""
        worst_severity = ""

        for headline in headlines:
            headline_lower = headline.lower()
            for keyword, info in GEOPOL_KEYWORDS.items():
                if keyword.lower() in headline_lower:
                    v = info["violence"]
                    if v > worst_violence:
                        worst_violence = v
                        worst_headline = headline
                        worst_severity = info["severity"]

        if worst_violence > 0:
            return True, worst_headline, worst_severity, worst_violence
        return False, "", "", 0.0
    
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
            
            # Map FinBERT labels to numeric scores
            label_map = {
                'positive': 1.0,
                'negative': -1.0,
                'neutral': 0.0
            }
            
            scores = []
            for result in results:
                label = result['label'].lower()
                confidence = result['score']
                
                base_score = label_map.get(label, 0.0)
                # Weight by confidence: low confidence → pull toward neutral
                score = base_score * confidence
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
            'surge', 'rally', 'bullish', 'gains', 'soar', 'breakout',
            'adoption', 'breakthrough', 'support', 'accumulate', 'buy'
        }
        negative_words = {
            'crash', 'dump', 'bearish', 'losses', 'plunge', 'breakdown',
            'sell-off', 'fear', 'panic', 'resistance', 'decline', 'drop'
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
        
        Args:
            age_hours: Hours since publication
        
        Returns:
            Weight 0.0-1.0
        """
        return np.exp(-self.decay_lambda * age_hours)
    
    def analyze(self, symbol: str = "BTC") -> SentimentResult:
        """
        Full analysis with temporal decay
        
        Returns:
            SentimentResult with weighted sentiment
        """
        # Fetch headlines — multi-source fallback
        headlines_data = self.fetch_headlines_cryptopanic(symbol, limit=20)
        _source_tag = "cryptopanic"

        # FALLBACK: if CryptoPanic returned stub/empty, try RSS
        if not headlines_data or (len(headlines_data) <= 3 and
                headlines_data[0].get('url', '') == '' if headlines_data else True):
            rss_data = self._fetch_rss_headlines(limit=15)
            if rss_data:
                headlines_data = rss_data
                _source_tag = "rss-fallback"

        if not headlines_data:
            return SentimentResult(
                sentiment=0.0,
                headline_risk=0.0,
                disagreement=0.0,
                n_headlines=0,
                n_fresh=0,
                source="none"
            )
        
        # Extract titles
        titles = [h['title'] for h in headlines_data]
        
        # ── 🌍 NATURE EVENTS → Synthetic Headlines ──
        # Inject real-time disaster/geopolitical events as synthetic news
        # into FinBERT pipeline. Uses event time-decay from EVENT_WEIGHTS.
        if self._nature_engine is not None:
            try:
                self._nature_engine.refresh()
                for event in self._nature_engine.events[:5]:  # Top 5 by severity
                    # Build synthetic headline for FinBERT
                    synthetic = (
                        f"BREAKING: {event.event_type} — {event.description}. "
                        f"Markets brace for impact on {event.market_impact_zone or 'global'} supply chains."
                    )
                    titles.append(synthetic)
                    # Add with proper time-decay weight
                    ew = EVENT_WEIGHTS.get(event.event_type, {})
                    decay_h = ew.get('decay_hours', 48)
                    try:
                        from datetime import datetime, timezone
                        et = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                        age_h = (datetime.now(timezone.utc) - et).total_seconds() / 3600
                    except Exception:
                        age_h = 6.0  # default 6h
                    decay_weight = math.exp(-0.693 * age_h / decay_h)
                    headlines_data.append({
                        'title': synthetic,
                        'published_at': int(time.time() - age_h * 3600),
                        'url': f'nature://{event.event_type}/{event.source}',
                        '_nature_decay': decay_weight,
                    })
            except Exception:
                pass
        
        # Analyze sentiment
        raw_scores = self.analyze_sentiment_finbert(titles)
        
        # Calculate temporal weights
        now = time.time()
        weighted_scores = []
        weights = []
        ages_hours = []
        
        for headline, score in zip(headlines_data, raw_scores):
            # Parse timestamp
            if isinstance(headline['published_at'], str):
                # ISO format from API
                import dateutil.parser
                pub_time = dateutil.parser.parse(headline['published_at']).timestamp()
            else:
                # Unix timestamp from stub
                pub_time = headline['published_at']
            
            age_hours = (now - pub_time) / 3600
            ages_hours.append(age_hours)
            
            weight = self.calculate_decay_weight(age_hours)
            weights.append(weight)
            weighted_scores.append(score * weight)
        
        # Weighted average sentiment
        total_weight = sum(weights)
        if total_weight > 0:
            avg_sentiment = sum(weighted_scores) / total_weight
        else:
            avg_sentiment = 0.0
        
        # Disagreement (variance in scores)
        disagreement = np.std(raw_scores) if len(raw_scores) > 1 else 0.0
        
        # Headline risk (magnitude of extreme sentiments)
        extreme_scores = [abs(s) for s in raw_scores if abs(s) > 0.5]
        headline_risk = min(1.0, len(extreme_scores) / len(raw_scores)) if raw_scores else 0.0
        
        # Count fresh headlines (< 1 hour)
        n_fresh = sum(1 for age in ages_hours if age < 1.0)
        
        source = f"{_source_tag}+finbert" if self.use_finbert else f"{_source_tag}+keywords"

        # ── 🛡️ GEOPOLITICAL OSINT SCAN (bypasses decay) ──
        all_titles = [h['title'] for h in headlines_data]
        geopol_detected, geopol_headline, geopol_severity, geopol_violence = \
            self.scan_geopol_keywords(all_titles)

        return SentimentResult(
            sentiment=avg_sentiment,
            headline_risk=headline_risk,
            disagreement=disagreement,
            n_headlines=len(headlines_data),
            n_fresh=n_fresh,
            source=source,
            geopol_alert=geopol_detected,
            geopol_headline=geopol_headline,
            geopol_severity=geopol_severity,
            violence_override=geopol_violence,
        )


# Example usage
if __name__ == "__main__":
    # Without API token (uses stub)
    nlp = NLPSentimentAnalyzer(
        cryptopanic_token=None,
        half_life_hours=3.0,
        use_finbert=False  # Set True if you have transformers installed
    )
    
    result = nlp.analyze("BTC")
    print(f"Sentiment: {result.sentiment:+.3f}")
    print(f"Headline Risk: {result.headline_risk:.2%}")
    print(f"Disagreement: {result.disagreement:.3f}")
    print(f"Headlines: {result.n_headlines} total, {result.n_fresh} fresh")
    print(f"Source: {result.source}")
