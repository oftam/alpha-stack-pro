"""
NLP Sentiment Analysis with Temporal Decay
Combines CryptoPanic headlines with FinBERT local model
"""

import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class SentimentResult:
    """NLP sentiment analysis result"""
    sentiment: float  # -1 to +1
    headline_risk: float  # 0 to 1 (volatility/disagreement)
    disagreement: float  # 0 to 1 (std of scores)
    n_headlines: int
    n_fresh: int  # headlines < 1 hour old
    source: str


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
        # Fetch headlines
        headlines_data = self.fetch_headlines_cryptopanic(symbol, limit=20)
        
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
        
        source = "cryptopanic+finbert" if self.use_finbert else "cryptopanic+keywords"
        
        return SentimentResult(
            sentiment=avg_sentiment,
            headline_risk=headline_risk,
            disagreement=disagreement,
            n_headlines=len(headlines_data),
            n_fresh=n_fresh,
            source=source
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
