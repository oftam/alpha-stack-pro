#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE 5: NLP Event Bias - Smart News Analysis
"פענוח האירועים" - מבדיל בין רעש לאירוע משמעותי

Implements:
- Sentiment scoring from headlines
- Event classification (GEO/REGULATORY/INSTITUTIONAL/MACRO)
- Impact weighting (noise vs regime change)
- Multi-source aggregation

Data sources:
- Bloomberg/Reuters RSS (if available)
- CoinDesk/Cointelegraph
- Twitter/Reddit sentiment (optional)
- Fallback to keyword-based scoring
"""

import re
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter


class NLPEventBiasAnalyzer:
    """
    Analyzes news/events and scores market impact
    
    Key capabilities:
    - Sentiment: Positive/Negative/Neutral
    - Classification: GEO/REG/INST/MACRO
    - Impact: 0-100 score
    - Regime change detection
    
    Without fancy NLP:
    - Uses keyword matching + rules
    - Weighted by source credibility
    - Historical calibration
    """
    
    def __init__(self):
        """Initialize with keyword dictionaries"""
        
        # Sentiment keywords
        self.positive_keywords = {
            'adoption', 'institutional', 'bullish', 'approval', 'etf', 
            'rally', 'surge', 'breakthrough', 'partnership', 'integration',
            'demand', 'inflow', 'accumulation', 'breakout', 'upgrade'
        }
        
        self.negative_keywords = {
            'ban', 'regulation', 'crackdown', 'crash', 'dump', 'bearish',
            'lawsuit', 'fraud', 'hack', 'exploit', 'fear', 'panic',
            'restriction', 'prohibition', 'outflow', 'selloff', 'downgrade'
        }
        
        # Event type keywords
        self.event_types = {
            'GEO': {'war', 'conflict', 'sanctions', 'trade', 'tariff', 'geopolitical', 'china', 'russia', 'iran'},
            'REG': {'regulation', 'sec', 'law', 'ban', 'legal', 'compliance', 'policy', 'government'},
            'INST': {'institutional', 'etf', 'fund', 'blackrock', 'fidelity', 'grayscale', 'microstrategy'},
            'MACRO': {'fed', 'interest', 'inflation', 'gdp', 'employment', 'powell', 'yellen', 'treasury'}
        }
        
        # Impact weights by source
        self.source_credibility = {
            'bloomberg': 1.0,
            'reuters': 1.0,
            'wsj': 0.9,
            'ft': 0.9,
            'coindesk': 0.7,
            'cointelegraph': 0.6,
            'twitter': 0.3,
            'reddit': 0.2,
            'unknown': 0.5
        }
    
    # =========================================================================
    # TEXT ANALYSIS
    # =========================================================================
    
    def analyze_headline(self, 
                        headline: str,
                        source: str = 'unknown',
                        timestamp: Optional[datetime] = None) -> Dict:
        """
        Analyze single headline
        
        Returns sentiment, event type, impact score
        """
        
        headline_lower = headline.lower()
        
        # Sentiment scoring
        pos_count = sum(1 for word in self.positive_keywords if word in headline_lower)
        neg_count = sum(1 for word in self.negative_keywords if word in headline_lower)
        
        if pos_count > neg_count:
            sentiment = 'POSITIVE'
            sentiment_score = min(100, (pos_count - neg_count) * 20)
        elif neg_count > pos_count:
            sentiment = 'NEGATIVE'
            sentiment_score = -min(100, (neg_count - pos_count) * 20)
        else:
            sentiment = 'NEUTRAL'
            sentiment_score = 0
        
        # Event classification
        event_matches = {}
        for event_type, keywords in self.event_types.items():
            matches = sum(1 for word in keywords if word in headline_lower)
            event_matches[event_type] = matches
        
        primary_event = max(event_matches.items(), key=lambda x: x[1])
        event_type = primary_event[0] if primary_event[1] > 0 else 'OTHER'
        
        # Impact score (0-100)
        base_impact = abs(sentiment_score)
        
        # Boost by event type (some types more impactful)
        type_multipliers = {
            'GEO': 1.5,      # Geopolitical = high impact
            'MACRO': 1.4,    # Macro = high impact
            'REG': 1.3,      # Regulation = medium-high
            'INST': 1.2,     # Institutional = medium
            'OTHER': 1.0
        }
        
        # Boost by source credibility
        source_weight = self.source_credibility.get(source.lower(), 0.5)
        
        impact_score = min(100, base_impact * type_multipliers[event_type] * source_weight)
        
        # Determine if regime-changing
        regime_change = impact_score > 70 and event_type in ['GEO', 'MACRO', 'REG']
        
        return {
            'headline': headline,
            'source': source,
            'timestamp': timestamp or datetime.now(),
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'event_type': event_type,
            'impact_score': impact_score,
            'regime_change': regime_change,
            'keywords_matched': {
                'positive': pos_count,
                'negative': neg_count
            }
        }
    
    # =========================================================================
    # MULTI-SOURCE AGGREGATION
    # =========================================================================
    
    def aggregate_news(self, 
                      headlines: List[Dict],
                      window_hours: int = 24) -> Dict:
        """
        Aggregate multiple headlines into overall bias
        
        Args:
            headlines: List of analyzed headlines
            window_hours: Time window for aggregation
            
        Returns:
            Aggregate sentiment and event bias
        """
        
        if not headlines:
            return {
                'sentiment': 'NEUTRAL',
                'sentiment_score': 0,
                'impact_score': 0,
                'dominant_event': 'NONE',
                'regime_change_detected': False
            }
        
        # Filter to time window
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [h for h in headlines if h['timestamp'] > cutoff]
        
        if not recent:
            recent = headlines  # Fallback to all if none recent
        
        # Aggregate sentiment (weighted by impact)
        total_impact = sum(h['impact_score'] for h in recent)
        
        if total_impact > 0:
            weighted_sentiment = sum(
                h['sentiment_score'] * h['impact_score'] 
                for h in recent
            ) / total_impact
        else:
            weighted_sentiment = 0
        
        # Aggregate impact
        avg_impact = sum(h['impact_score'] for h in recent) / len(recent)
        
        # Dominant event type
        event_counts = Counter(h['event_type'] for h in recent)
        dominant_event = event_counts.most_common(1)[0][0]
        
        # Check for regime change
        regime_change_count = sum(1 for h in recent if h['regime_change'])
        regime_change_detected = regime_change_count >= 2  # At least 2 major events
        
        # Overall sentiment
        if weighted_sentiment > 30:
            sentiment = 'POSITIVE'
        elif weighted_sentiment < -30:
            sentiment = 'NEGATIVE'
        else:
            sentiment = 'NEUTRAL'
        
        return {
            'sentiment': sentiment,
            'sentiment_score': weighted_sentiment,
            'impact_score': avg_impact,
            'dominant_event': dominant_event,
            'regime_change_detected': regime_change_detected,
            'n_headlines': len(recent),
            'event_breakdown': dict(event_counts)
        }
    
    # =========================================================================
    # DATA FETCHING (Placeholder - needs API keys)
    # =========================================================================
    
    def fetch_coindesk_headlines(self, limit: int = 20) -> List[Dict]:
        """
        Fetch headlines from CoinDesk RSS
        
        Note: This is a placeholder. In production, use:
        - Bloomberg Terminal API
        - Reuters News API
        - CoinDesk/Cointelegraph RSS
        """
        
        # Placeholder: return empty
        # In production, implement RSS parsing or API calls
        return []
    
    def fetch_twitter_sentiment(self, query: str = 'bitcoin', limit: int = 100) -> Dict:
        """
        Fetch Twitter sentiment
        
        Note: Requires Twitter API key
        """
        # Placeholder
        return {'sentiment': 'NEUTRAL', 'score': 0}
    
    # =========================================================================
    # DECISION INTEGRATION
    # =========================================================================
    
    def get_event_bias_adjustment(self, 
                                  base_action: str,
                                  news_analysis: Dict) -> Dict:
        """
        Adjust trading action based on event bias
        
        Rules:
        - Positive news + high impact → boost position
        - Negative news + high impact → reduce position
        - Regime change → halt aggressive actions
        """
        
        sentiment = news_analysis['sentiment']
        impact = news_analysis['impact_score']
        regime_change = news_analysis['regime_change_detected']
        
        # Default: no adjustment
        adjusted_action = base_action
        multiplier = 1.0
        reason = "No significant news bias"
        
        # Regime change → caution
        if regime_change:
            if base_action in ['ADD', 'ADD_SMALL', 'DCA_BOOST']:
                adjusted_action = 'HOLD'
                multiplier = 0.0
                reason = "Regime change detected - wait for clarity"
        
        # Strong positive news
        elif sentiment == 'POSITIVE' and impact > 60:
            if base_action in ['ADD_SMALL']:
                adjusted_action = 'ADD'
                multiplier = 1.5
                reason = f"Positive event bias (impact {impact:.0f}) - boost position"
            elif base_action == 'HOLD':
                adjusted_action = 'ADD_SMALL'
                multiplier = 0.5
                reason = "Positive news - consider small add"
        
        # Strong negative news
        elif sentiment == 'NEGATIVE' and impact > 60:
            if base_action in ['ADD', 'ADD_SMALL']:
                adjusted_action = 'HOLD'
                multiplier = 0.0
                reason = f"Negative event bias (impact {impact:.0f}) - hold off"
            elif base_action == 'HOLD':
                adjusted_action = 'REDUCE_20'
                multiplier = 0.0
                reason = "Negative news - consider reducing"
        
        return {
            'original_action': base_action,
            'adjusted_action': adjusted_action,
            'multiplier': multiplier,
            'reason': reason,
            'news_summary': news_analysis
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    analyzer = NLPEventBiasAnalyzer()
    
    print("\n" + "="*60)
    print("NLP EVENT BIAS ANALYSIS")
    print("="*60)
    
    # Sample headlines
    headlines = [
        {
            'text': 'BlackRock Bitcoin ETF sees record $500M inflow as institutional demand surges',
            'source': 'bloomberg',
            'timestamp': datetime.now()
        },
        {
            'text': 'SEC approves spot Bitcoin ETFs after decade-long wait, market rallies',
            'source': 'reuters',
            'timestamp': datetime.now() - timedelta(hours=2)
        },
        {
            'text': 'China announces new cryptocurrency trading restrictions amid crackdown',
            'source': 'coindesk',
            'timestamp': datetime.now() - timedelta(hours=5)
        },
        {
            'text': 'Fed signals potential interest rate cuts in 2025, risk appetite increases',
            'source': 'wsj',
            'timestamp': datetime.now() - timedelta(hours=12)
        }
    ]
    
    # Analyze each
    analyzed = []
    
    print("\n📰 Individual Headlines:")
    for h in headlines:
        result = analyzer.analyze_headline(
            h['text'],
            h['source'],
            h['timestamp']
        )
        analyzed.append(result)
        
        print(f"\n  {h['text'][:60]}...")
        print(f"  Source: {result['source']} | Type: {result['event_type']}")
        print(f"  Sentiment: {result['sentiment']} ({result['sentiment_score']:+.0f})")
        print(f"  Impact: {result['impact_score']:.0f}/100")
        if result['regime_change']:
            print(f"  ⚠️  REGIME CHANGE EVENT")
    
    # Aggregate
    print("\n" + "="*60)
    print("📊 AGGREGATE NEWS BIAS (24h)")
    print("="*60)
    
    aggregate = analyzer.aggregate_news(analyzed, window_hours=24)
    
    print(f"\nOverall Sentiment: {aggregate['sentiment']}")
    print(f"Sentiment Score: {aggregate['sentiment_score']:+.1f}")
    print(f"Average Impact: {aggregate['impact_score']:.1f}/100")
    print(f"Dominant Event Type: {aggregate['dominant_event']}")
    print(f"Regime Change Detected: {aggregate['regime_change_detected']}")
    
    print(f"\nEvent Breakdown:")
    for event_type, count in aggregate['event_breakdown'].items():
        print(f"  {event_type}: {count}")
    
    # Decision adjustment
    print("\n" + "="*60)
    print("🎯 TRADING ACTION ADJUSTMENT")
    print("="*60)
    
    base_action = "ADD_SMALL"
    adjustment = analyzer.get_event_bias_adjustment(base_action, aggregate)
    
    print(f"\nBase Action: {adjustment['original_action']}")
    print(f"Adjusted Action: {adjustment['adjusted_action']}")
    print(f"Position Multiplier: {adjustment['multiplier']}x")
    print(f"Reason: {adjustment['reason']}")
    
    print("="*60)
