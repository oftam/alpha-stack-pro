-- ============================================================================
-- ELITE v20 - Memory System Database Schema
-- ============================================================================
-- Platform: Supabase (PostgreSQL 15+ with pgvector)
-- Purpose: Regime-aware organizational memory for Claude AI
-- Timeline: Optimized for time-series queries (partitioning ready)
--
-- Key Design Principles:
-- 1. Regime-aware consistency (don't compare BLOOD_IN_STREETS to NORMAL)
-- 2. UTC timestamps only (no timezone confusion)
-- 3. Partitioning-ready for future scaling
-- 4. Vector embeddings for semantic similarity
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================================
-- TABLE: daily_signals
-- Purpose: Market snapshots + Elite v20 signal data
-- Partitioning: By date (monthly) for optimal time-series queries
-- ============================================================================

CREATE TABLE daily_signals (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'BTCUSDT',
    
    -- Market Data
    price DECIMAL(12,2) NOT NULL,
    price_change_24h DECIMAL(5,2),
    volume_24h DECIMAL(15,2),
    
    -- Elite v20 Core Signals (0-100 scale)
    onchain_score INTEGER CHECK (onchain_score BETWEEN 0 AND 100),
    fear_index INTEGER CHECK (fear_index BETWEEN 0 AND 100),
    manifold_dna INTEGER CHECK (manifold_dna BETWEEN 0 AND 100),
    divergence DECIMAL(6,2), -- Can be negative
    
    -- DUDU Overlay (P10/P50/P90 projection)
    p10_price DECIMAL(12,2),
    p50_price DECIMAL(12,2),
    p90_price DECIMAL(12,2),
    vol_cone_upper DECIMAL(12,2),
    vol_cone_lower DECIMAL(12,2),
    
    -- Regime Classification (CRITICAL for consistency)
    regime VARCHAR(50) NOT NULL, -- BLOOD_IN_STREETS, NORMAL, BULL_RUN, etc.
    regime_confidence DECIMAL(5,2), -- 0-100%
    
    -- Signal Metadata
    signal_strength VARCHAR(20), -- SNIPER, STRONG_BUY, BUILD, HOLD, SELL
    bayesian_probability DECIMAL(5,2), -- Victory Vector probability
    
    -- Technical Indicators (optional)
    sma_20 DECIMAL(12,2),
    sma_50 DECIMAL(12,2),
    sma_200 DECIMAL(12,2),
    rsi_14 DECIMAL(5,2),
    
    -- Indexing
    UNIQUE(date, symbol)
);

-- Create hypertable for time-series optimization (TimescaleDB)
SELECT create_hypertable('daily_signals', 'timestamp', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Indexes for fast queries
CREATE INDEX idx_daily_signals_date ON daily_signals(date DESC);
CREATE INDEX idx_daily_signals_regime ON daily_signals(regime);
CREATE INDEX idx_daily_signals_signal_strength ON daily_signals(signal_strength);
CREATE INDEX idx_daily_signals_manifold ON daily_signals(manifold_dna DESC);

-- ============================================================================
-- TABLE: claude_responses
-- Purpose: AI recommendations with regime context + embeddings
-- Key: Stores full conversation context for consistency checking
-- ============================================================================

CREATE TABLE claude_responses (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT REFERENCES daily_signals(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- User Interaction
    user_question TEXT NOT NULL,
    claude_response TEXT NOT NULL,
    
    -- Recommendation Parsing
    recommendation VARCHAR(50), -- BUY_STRONG, BUY_LIGHT, HOLD, SELL, etc.
    position_size_multiplier DECIMAL(3,2), -- e.g., 1.5x for aggressive
    confidence DECIMAL(5,2), -- 0-100%
    reasoning TEXT, -- Why this recommendation?
    
    -- Regime Context (for consistency checking)
    regime_at_time VARCHAR(50) NOT NULL,
    manifold_at_time INTEGER,
    onchain_at_time INTEGER,
    fear_at_time INTEGER,
    
    -- Vector Embedding (Cohere)
    embedding vector(1024), -- Cohere embed-english-v3.0 = 1024 dims
    
    -- Metadata
    model_version VARCHAR(50) DEFAULT 'claude-sonnet-4-20250514',
    response_time_ms INTEGER
);

-- Indexes
CREATE INDEX idx_claude_responses_signal_id ON claude_responses(signal_id);
CREATE INDEX idx_claude_responses_timestamp ON claude_responses(timestamp DESC);
CREATE INDEX idx_claude_responses_regime ON claude_responses(regime_at_time);
CREATE INDEX idx_claude_responses_recommendation ON claude_responses(recommendation);

-- Vector similarity index (for RAG/consistency checking)
CREATE INDEX idx_claude_responses_embedding ON claude_responses 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================================
-- TABLE: performance_tracking
-- Purpose: Measure actual outcomes of recommendations
-- PRO ENHANCEMENT: Drawdown + Time analysis per regime
-- Updates: Daily cron job to refresh P&L
-- ============================================================================

CREATE TABLE IF NOT EXISTS performance_tracking (
    id BIGSERIAL PRIMARY KEY,
    response_id BIGINT REFERENCES claude_responses(id) ON DELETE CASCADE,
    entry_price DECIMAL(12,2) NOT NULL,
    current_price DECIMAL(12,2),
    pnl_usd DECIMAL(12,2),
    pnl_percent DECIMAL(8,4),
    
    -- Position tracking
    position_size DECIMAL(12,8),  -- BTC amount or position size
    entry_date DATE NOT NULL,
    exit_date DATE,
    
    -- Performance metrics
    is_winner BOOLEAN,
    days_held INTEGER,
    
    -- PRO ENHANCEMENT: Drawdown & Trade Duration Analysis
    -- Helps identify: slow winners in BLOOD_IN_STREETS, whipsaw patterns, regime patience needs
    max_drawdown_percent DECIMAL(8,4),  -- Worst intra-trade drawdown (negative value)
    max_drawdown_usd DECIMAL(12,2),     -- Drawdown in USD
    max_drawdown_date DATE,             -- When did max DD occur?
    time_in_trade_hours INTEGER,        -- Total hours in position
    time_to_profit_hours INTEGER,       -- Hours until first profit (patience metric)
    time_to_exit_hours INTEGER,         -- Hours until realized gain/loss
    
    -- Regime context (for performance attribution)
    regime_at_entry VARCHAR(50),
    regime_at_exit VARCHAR(50),
    regime_changes_during_trade INTEGER DEFAULT 0,  -- Did regime shift mid-trade?
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_performance_response_id ON performance_tracking(response_id);
CREATE INDEX idx_performance_entry_date ON performance_tracking(entry_date DESC);
CREATE INDEX idx_performance_outcome ON performance_tracking(outcome);

-- ============================================================================
-- TABLE: consistency_scores
-- Purpose: Daily calculation of AI reliability
-- Key Metric: "Consistency Arbiter" score
-- ============================================================================

CREATE TABLE consistency_scores (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Consistency Metrics
    consistency_score DECIMAL(5,2) NOT NULL, -- 0-100%
    contradictions_found INTEGER DEFAULT 0,
    similar_scenarios_analyzed INTEGER DEFAULT 0,
    
    -- Statistical Analysis
    avg_confidence_deviation DECIMAL(5,2), -- Standard deviation
    regime_drift_detected BOOLEAN DEFAULT FALSE,
    
    -- Performance Correlation
    win_rate_30d DECIMAL(5,2),
    avg_pnl_30d DECIMAL(6,2),
    sharpe_ratio DECIMAL(5,2),
    
    -- Details
    notes TEXT,
    contradictions_detail JSONB -- Store specific examples
);

-- Index
CREATE INDEX idx_consistency_scores_date ON consistency_scores(date DESC);

-- ============================================================================
-- TABLE: regime_transitions
-- Purpose: Track regime changes for context
-- Use: Understanding when market structure shifts
-- ============================================================================

CREATE TABLE regime_transitions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    from_regime VARCHAR(50),
    to_regime VARCHAR(50) NOT NULL,
    trigger_event TEXT, -- e.g., "OnChain spiked from 60 to 85"
    confidence DECIMAL(5,2)
);

CREATE INDEX idx_regime_transitions_timestamp ON regime_transitions(timestamp DESC);

-- ============================================================================
-- TABLE: reasoning_fingerprints (PRO ENHANCEMENT)
-- Purpose: Track key reasoning patterns for semantic contradiction detection
-- Use: Detect not just BUY→SELL flips, but REASONING changes
-- ============================================================================

CREATE TABLE IF NOT EXISTS reasoning_fingerprints (
    id BIGSERIAL PRIMARY KEY,
    response_id BIGINT REFERENCES claude_responses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Extracted Keywords/Themes
    key_themes TEXT[], -- e.g., ['liquidity_spike', 'fear_capitulation', 'onchain_divergence']
    bullish_phrases TEXT[], -- e.g., ['bottom signal', 'accumulation zone', 'smart money buying']
    bearish_phrases TEXT[], -- e.g., ['distribution', 'euphoria peak', 'leverage flush']
    confidence_language VARCHAR(50), -- 'very_confident', 'cautious', 'uncertain'
    
    -- Similarity Fingerprint
    reasoning_embedding vector(1024), -- Cohere embedding of reasoning text
    
    -- Regime Context
    regime VARCHAR(50),
    
    -- For pattern matching
    CONSTRAINT unique_response_fingerprint UNIQUE(response_id)
);

CREATE INDEX idx_reasoning_fingerprints_regime ON reasoning_fingerprints(regime);
CREATE INDEX idx_reasoning_fingerprints_embedding ON reasoning_fingerprints
    USING ivfflat (reasoning_embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============================================================================
-- TABLE: known_failure_patterns (PRO ENHANCEMENT)
-- Purpose: Learn from mistakes - "In setup X, we lost because Y"
-- Use: Inject into Claude context as warnings
-- ============================================================================

CREATE TABLE IF NOT EXISTS known_failure_patterns (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Failed Trade Context
    regime VARCHAR(50) NOT NULL,
    signal_setup TEXT NOT NULL,  -- Description: "High manifold + Fear <20 + Price rejection at $70K"
    recommendation_made VARCHAR(50), -- What we recommended
    actual_outcome VARCHAR(20), -- LOSS, WHIPSAW, STOPPED_OUT
    
    -- Failure Analysis
    failure_reason TEXT NOT NULL,  -- Why it failed: "Ignored resistance, liquidity dried up"
    loss_amount_pct DECIMAL(6,2),
    max_drawdown_pct DECIMAL(6,2),
    
    -- Signal similarity (for matching)
    setup_embedding vector(1024),
    
    -- Learning
    lesson_learned TEXT, -- "In BLOOD regime, wait for volume confirmation even with high manifold"
    appears_count INTEGER DEFAULT 1,  -- How many times this pattern failed?
    
    -- Status
    still_relevant BOOLEAN DEFAULT TRUE,
    invalidated_at TIMESTAMPTZ,
    invalidation_reason TEXT
);

CREATE INDEX idx_failure_patterns_regime ON known_failure_patterns(regime);
CREATE INDEX idx_failure_patterns_relevant ON known_failure_patterns(still_relevant) WHERE still_relevant = TRUE;
CREATE INDEX idx_failure_patterns_embedding ON known_failure_patterns
    USING ivfflat (setup_embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============================================================================
-- VIEWS: Convenience queries
-- ============================================================================

-- Recent signals with Claude recommendations
CREATE VIEW v_recent_signals_with_responses AS
SELECT 
    ds.date,
    ds.symbol,
    ds.price,
    ds.onchain_score,
    ds.fear_index,
    ds.manifold_dna,
    ds.regime,
    ds.signal_strength,
    cr.recommendation,
    cr.confidence,
    cr.claude_response,
    pt.pnl_pct,
    pt.outcome
FROM daily_signals ds
LEFT JOIN claude_responses cr ON ds.id = cr.signal_id
LEFT JOIN performance_tracking pt ON cr.id = pt.response_id
ORDER BY ds.date DESC
LIMIT 30;

-- Win rate by regime
CREATE VIEW v_win_rate_by_regime AS
SELECT 
    cr.regime_at_time,
    COUNT(*) as total_recommendations,
    SUM(CASE WHEN pt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN pt.outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pt.pnl_pct), 2) as avg_pnl_pct
FROM claude_responses cr
JOIN performance_tracking pt ON cr.id = pt.response_id
WHERE pt.outcome IN ('WIN', 'LOSS')
GROUP BY cr.regime_at_time
ORDER BY win_rate_pct DESC;

-- ============================================================================
-- FUNCTIONS: Automated maintenance
-- ============================================================================

-- Update performance tracking (call daily via cron)
CREATE OR REPLACE FUNCTION update_performance_tracking(
    current_btc_price DECIMAL(12,2)
)
RETURNS void AS $$
BEGIN
    UPDATE performance_tracking
    SET 
        current_price = current_btc_price,
        pnl_pct = ROUND(100.0 * (current_btc_price - entry_price) / entry_price, 2),
        pnl_usd = ROUND((current_btc_price - entry_price) * 0.01, 2), -- Simulated 0.01 BTC position
        days_since_entry = EXTRACT(DAY FROM NOW() - entry_date),
        last_updated = NOW(),
        outcome = CASE
            WHEN pnl_pct > 5 THEN 'WIN'
            WHEN pnl_pct < -5 THEN 'LOSS'
            WHEN pnl_pct BETWEEN -1 AND 1 THEN 'BREAKEVEN'
            ELSE 'PENDING'
        END,
        outcome_determined_at = CASE
            WHEN outcome = 'PENDING' AND (pnl_pct > 5 OR pnl_pct < -5) THEN NOW()
            ELSE outcome_determined_at
        END
    WHERE outcome = 'PENDING';
END;
$$ LANGUAGE plpgsql;

-- Calculate daily consistency score
CREATE OR REPLACE FUNCTION calculate_consistency_score(analysis_date DATE)
RETURNS DECIMAL(5,2) AS $$
DECLARE
    score DECIMAL(5,2);
BEGIN
    -- Simplified version: Compare recommendations in same regime
    -- Full logic will be in Python consistency_analyzer.py
    
    SELECT 
        100.0 - (COUNT(DISTINCT recommendation) * 10.0) 
    INTO score
    FROM claude_responses
    WHERE regime_at_time = (
        SELECT regime FROM daily_signals WHERE date = analysis_date
    )
    AND timestamp >= analysis_date - INTERVAL '7 days'
    AND timestamp < analysis_date + INTERVAL '1 day';
    
    RETURN COALESCE(score, 100.0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ROW-LEVEL SECURITY (Optional - for multi-user)
-- ============================================================================

-- Enable RLS
ALTER TABLE daily_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE claude_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_scores ENABLE ROW LEVEL SECURITY;

-- Policies (read-only for anon, full access for authenticated)
CREATE POLICY "Public read access" ON daily_signals FOR SELECT TO anon USING (true);
CREATE POLICY "Authenticated full access" ON daily_signals FOR ALL TO authenticated USING (true);

-- Repeat for other tables...

-- ============================================================================
-- INITIAL DATA (Sample)
-- ============================================================================

-- Insert sample signal (for testing)
INSERT INTO daily_signals (
    date, symbol, price, onchain_score, fear_index, manifold_dna, 
    divergence, regime, signal_strength, bayesian_probability
) VALUES (
    '2026-02-17', 'BTCUSDT', 70100, 84, 12, 87, 
    29.5, 'BLOOD_IN_STREETS', 'STRONG_BUY', 91.7
);

-- ============================================================================
-- MAINTENANCE NOTES
-- ============================================================================

/*
1. Run update_performance_tracking() daily via cron:
   SELECT update_performance_tracking(70000.00);

2. Calculate consistency every evening:
   INSERT INTO consistency_scores (date, consistency_score)
   VALUES (CURRENT_DATE, calculate_consistency_score(CURRENT_DATE));

3. Backup strategy:
   - Supabase auto-backup enabled
   - Export to CSV weekly: SELECT * FROM daily_signals;

4. Monitoring:
   - Check table sizes: SELECT pg_size_pretty(pg_total_relation_size('daily_signals'));
   - Index usage: SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
*/

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
