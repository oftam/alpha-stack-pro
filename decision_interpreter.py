"""
Decision Interpreter - Educational Layer for Trading Decisions

Takes raw decision_summary from dashboard_adapter and generates:
- Scenario-based trade plans
- Reasoning explanations
- Risk breakdowns
- Warnings and edge cases
"""

from typing import Dict, Optional


class DecisionInterpreter:
    """
    Interprets algorithmic trading decisions into actionable trade plans
    
    Input: decision_summary dict from generate_decision_summary()
    Output: Formatted markdown explanation with scenarios
    """
    
    def __init__(self):
        self.risk_tolerance_multipliers = {
            'conservative': 0.67,  # 2/3 of suggested
            'moderate': 1.0,       # As suggested
            'aggressive': 1.33     # 4/3 of suggested
        }
    
    def interpret(self, 
                 decision_summary: Dict, 
                 current_price: float,
                 user_capital: Optional[float] = None,
                 risk_tolerance: str = 'moderate') -> str:
        """
        Generate comprehensive interpretation
        
        Args:
            decision_summary: Output from generate_decision_summary()
            current_price: Current market price
            user_capital: Optional - for position sizing in dollars
            risk_tolerance: 'conservative' | 'moderate' | 'aggressive'
        
        Returns:
            Markdown-formatted interpretation
        """
        
        direction = decision_summary['direction']
        reasoning = decision_summary['reasoning']
        size_mult = decision_summary['size_multiplier']
        stop = decision_summary['stop_loss']
        tp = decision_summary['take_profit']
        rr = decision_summary['risk_reward']
        regime = decision_summary['regime']
        warnings = decision_summary['warnings']
        
        # Adjust size for user risk tolerance
        adjusted_size = size_mult * self.risk_tolerance_multipliers[risk_tolerance]
        adjusted_size = max(0.0, min(2.0, adjusted_size))  # Cap at 2x
        
        output = []
        
        # Header
        output.append("# 🎯 Trade Interpretation\n")
        output.append("---\n")
        
        # Direction banner
        if direction == "BUY":
            emoji = "📈"
            color = "🟢"
        elif direction == "SELL":
            emoji = "📉"
            color = "🔴"
        else:
            emoji = "⏸️"
            color = "🟡"
        
        output.append(f"## {emoji} {direction}: {reasoning}\n")
        output.append(f"**Market Regime:** {regime.replace('_', ' ').title()}\n")
        output.append("---\n\n")
        
        # Scenarios
        output.append("## 📋 How To Use This Signal\n\n")
        
        if direction == "HOLD":
            output.append(self._format_hold_scenario(warnings))
        else:
            # Scenario 1: Direct implementation
            output.append(self._format_direct_scenario(
                direction, current_price, adjusted_size, stop, tp, rr
            ))
            
            # Scenario 2: Conservative adjustment
            conservative_size = adjusted_size * 0.67
            output.append(self._format_conservative_scenario(
                direction, conservative_size, stop, tp
            ))
            
            # Scenario 3: Disagreement protocol
            output.append(self._format_disagreement_scenario(direction))
        
        # Reasoning breakdown
        output.append("\n---\n")
        output.append("## 💡 Why These Numbers?\n\n")
        output.append(self._explain_position_size(size_mult, regime, decision_summary))
        output.append(self._explain_stop_loss(stop, current_price))
        output.append(self._explain_targets(tp, regime, current_price))
        
        # Risk/Reward explanation
        if direction != "HOLD":
            output.append(self._explain_risk_reward(rr, stop, tp))
        
        # Warnings
        if warnings:
            output.append("\n---\n")
            output.append("## ⚠️ Important Considerations\n\n")
            for warning in warnings:
                output.append(f"- {warning}\n")
        
        # General disclaimers
        output.append("\n---\n")
        output.append(self._format_disclaimers())
        
        # Position sizing calculator (if capital provided)
        if user_capital and direction != "HOLD":
            output.append("\n---\n")
            output.append(self._calculate_position_sizing(
                user_capital, current_price, adjusted_size, stop, tp
            ))
        
        return "".join(output)
    
    def _format_direct_scenario(self, direction, price, size, stop, tp, rr):
        """Scenario 1: Follow the signal directly"""
        
        risk_amt = abs(price - stop['price'])
        reward_t1 = abs(tp['tp1_price'] - price)
        reward_t2 = abs(tp['tp2_price'] - price)
        
        text = f"""### Scenario 1: Follow The Signal

```
Entry: ${price:,.2f} (current market price)
Size: {size:.2f}x your normal position
Stop Loss: ${stop['price']:,.2f} ({stop['percent']:.1%})
Target 1: ${tp['tp1_price']:,.2f} ({tp['tp1_percent']:.1%}) ← Take 50% profit
Target 2: ${tp['tp2_price']:,.2f} ({tp['tp2_percent']:.1%}) ← Let rest run

Risk per unit: ${risk_amt:,.2f}
Reward (T1): ${reward_t1:,.2f}
Reward (T2): ${reward_t2:,.2f}
R/R Ratio: {rr['conservative']:.1f}:1 (conservative) / {rr['aggressive']:.1f}:1 (aggressive)
```

**Execution Plan:**
1. Enter {direction} at ${price:,.2f}
2. Place stop at ${stop['price']:,.2f}
3. Set alert at ${tp['tp1_price']:,.2f} (Target 1)
4. When T1 hit: Close 50% of position, move stop to breakeven
5. Let remaining 50% run to ${tp['tp2_price']:,.2f}

"""
        return text
    
    def _format_conservative_scenario(self, direction, size, stop, tp):
        """Scenario 2: More conservative approach"""
        
        text = f"""### Scenario 2: Conservative Approach

If you're uncomfortable with the suggested size or targets:

```
Entry: Same (current price)
Size: {size:.2f}x ← Reduced from system suggestion
Stop: Same (${stop['price']:,.2f})
Target: ${tp['tp1_price']:,.2f} ONLY ← Skip aggressive target
Exit: Close 100% at T1, don't hold for T2
```

**Why Go Conservative:**
- Lower confidence in your own analysis
- Already have exposure to this market
- Risk management requires smaller size
- Prefer certainty over maximum reward

"""
        return text
    
    def _format_disagreement_scenario(self, direction):
        """Scenario 3: What if you disagree"""
        
        text = f"""### Scenario 3: You See Something Different

```
System: {direction}
You: "I see strong resistance/support that invalidates this"
```

**Correct Response:** 
- ❌ Don't force the trade because the algorithm said so
- ✅ Trust your independent analysis
- ✅ The system provides data, YOU make decisions
- ✅ Wait for agreement between system + your view

**The algorithm can't see:**
- Key levels you've marked
- News events you're aware of
- Your existing positions
- Your risk limits

**Always combine algorithmic signals with your own analysis.**

"""
        return text
    
    def _format_hold_scenario(self, warnings):
        """Special formatting for HOLD decisions"""
        
        text = """### Current Recommendation: HOLD (No Trade)

**Why:**
- Mixed signals from different modules
- Gates blocking trade (risk filters)
- Insufficient confidence in direction
- Market conditions unclear

**What To Do:**
1. ✅ Stay in cash/existing positions
2. ✅ Monitor for clearer setup
3. ✅ Review warnings below for what's blocking

**Not every moment requires a trade.**
Patience and capital preservation are strategies too.

"""
        if warnings:
            text += "\n**Specific Issues:**\n"
            for w in warnings:
                text += f"- {w}\n"
        
        return text
    
    def _explain_position_size(self, size, regime, decision):
        """Explain how position size was calculated"""
        
        confidence = decision['confidence_breakdown'].get('System Quality', 'N/A')
        conviction = decision['confidence_breakdown'].get('Conviction', 'N/A')
        chaos = decision['chaos_level']
        
        text = f"""### Position Size = {size:.2f}x

**Calculation Logic:**
```python
Base = 1.0x (your normal position)
× System Confidence ({confidence}) 
× Signal Conviction ({conviction})
× Market State ({chaos}) adjustment
× Regime bonus/penalty
────────────────
= {size:.2f}x final suggestion
```

**Factors Increasing Size:**
- High system confidence (good data)
- Strong conviction (clear signal)
- Calm market (low chaos)
- Favorable regime (e.g., blood_in_streets)

**Factors Decreasing Size:**
- Lower confidence
- Mixed signals
- High volatility
- Unclear regime

**Remember:** This is a SUGGESTION. Adjust to your:
- Available capital
- Risk tolerance
- Existing exposure
- Personal comfort level

"""
        return text
    
    def _explain_stop_loss(self, stop, price):
        """Explain stop loss calculation"""
        
        text = f"""### Stop Loss = ${stop['price']:,.2f} ({stop['percent']:.1%})

**Calculation:**
```python
Recent daily volatility ≈ {abs(stop['percent'])/2:.2%}
Stop = 2 × daily_vol = {abs(stop['percent']):.1%}
```

**Why 2× volatility:**
- Captures ~95% of normal price moves
- Avoids getting stopped out by noise
- Still protects capital on real moves

**Not guaranteed:**
- Gap downs can bypass stop
- Slippage in fast markets
- Consider this your MAXIMUM loss

"""
        return text
    
    def _explain_targets(self, tp, regime, price):
        """Explain take profit targets"""
        
        text = f"""### Targets: ${tp['tp1_price']:,.2f} / ${tp['tp2_price']:,.2f}

**Target 1 (Conservative): {tp['tp1_percent']:.1%}**
- Based on: Current regime ({regime})
- Probability: Moderate-High
- Action: Take 50% profit, secure gains

**Target 2 (Aggressive): {tp['tp2_percent']:.1%}**
- Based on: Regime + favorable conditions
- Probability: Lower, but possible
- Action: Let remaining 50% run

**Regime-Specific:**
```python
if regime == 'blood_in_streets':
    targets = [+10%, +25%]  # Extreme fear = big upside
elif regime == 'normal':
    targets = [+5%, +12%]   # Standard expectations
elif regime == 'distribution_top':
    targets = [-5%, -15%]   # Downside in greed
```

**Current regime: {regime}** → Targets as shown above

"""
        return text
    
    def _explain_risk_reward(self, rr, stop, tp):
        """Explain R/R ratio and expectancy"""
        
        rr_cons = rr['conservative']
        rr_agg = rr['aggressive']
        
        # Calculate expectancy at different win rates
        expectancy_30 = (0.30 * rr_cons - 0.70 * 1)
        expectancy_40 = (0.40 * rr_cons - 0.60 * 1)
        expectancy_50 = (0.50 * rr_cons - 0.50 * 1)
        
        text = f"""### Risk/Reward: {rr_cons:.1f}:1 (conservative)

**What This Means:**
```
You risk: $1 (stop loss distance)
To make: ${rr_cons:.1f} (Target 1)
      or: ${rr_agg:.1f} (Target 2)
```

**Why This Matters - Expectancy:**
```
Even with low win rate, positive expectancy:

If you're right 30% of time:
  Wins:   30% × ${rr_cons:.1f} = +${expectancy_30 + 0.70:.2f}
  Losses: 70% × -$1.0 = -$0.70
  Net: ${expectancy_30:+.2f} per $1 risked

If you're right 50% of time:
  Net: ${expectancy_50:+.2f} per $1 risked
```

**Rule of Thumb:**
- R/R > 2:1 = Acceptable
- R/R > 3:1 = Good
- R/R > 4:1 = Excellent ✅ ← You're here

"""
        return text
    
    def _format_disclaimers(self):
        """Standard disclaimers"""
        
        text = """## ⚠️ Critical Disclaimers

1. **Not Financial Advice**
   - This is algorithmic analysis
   - You make your own trading decisions
   - We don't know your situation

2. **Past ≠ Future**
   - Historical patterns inform, don't guarantee
   - Markets change constantly
   - Black swans happen

3. **Risk Management Required**
   - Never risk more than you can afford
   - Position sizing is personal
   - Use stop losses, but they're not perfect

4. **System Limitations**
   - Can't see all market factors
   - Can't predict news events
   - Can't guarantee fills at stop prices

5. **You Are Responsible**
   - For all trading decisions
   - For risk management
   - For tax implications
   - For regulatory compliance

"""
        return text
    
    def _calculate_position_sizing(self, capital, price, size_mult, stop, tp):
        """
        Calculate actual position size in dollars/units
        FIXED: Capital-constrained (realistic) instead of risk-only based
        """
        
        # Risk per unit (distance from entry to stop)
        risk_per_unit = abs(price - stop['price'])
        
        # Available capital for this trade
        # size_mult suggests how aggressive (1.0x = normal, 1.5x = aggressive)
        # But we can't use more capital than we have!
        suggested_capital = capital * size_mult
        available_capital = min(suggested_capital, capital)  # Cap at total capital
        
        # How much can we actually buy with available capital
        units_to_buy = available_capital / price
        actual_position_value = units_to_buy * price
        
        # What's the actual risk if stop is hit
        actual_risk_dollars = units_to_buy * risk_per_unit
        actual_risk_pct = (actual_risk_dollars / capital) * 100
        
        # Calculate potential profits at targets
        tp1_price = tp.get('tp1_price', 0)
        tp2_price = tp.get('tp2_price', 0)
        
        profit_t1 = units_to_buy * (tp1_price - price) if tp1_price > 0 else 0
        profit_t2 = units_to_buy * (tp2_price - price) if tp2_price > 0 else 0
        
        profit_t1_pct = ((tp1_price - price) / price * 100) if tp1_price > 0 else 0
        profit_t2_pct = ((tp2_price - price) / price * 100) if tp2_price > 0 else 0
        
        # Risk/Reward ratios
        rr_t1 = abs(profit_t1 / actual_risk_dollars) if actual_risk_dollars > 0 else 0
        rr_t2 = abs(profit_t2 / actual_risk_dollars) if actual_risk_dollars > 0 else 0
        
        text = f"""## 💰 Position Sizing Calculator

**Your Trading Capital:** ${capital:,.2f}

**Suggested Position ({size_mult:.2f}x):**
```
Entry Price: ${price:,.2f}
Units to Buy: {units_to_buy:.4f} BTC
Position Cost: ${actual_position_value:,.2f} ({actual_position_value/capital*100:.1f}% of capital)

Stop Loss: ${stop['price']:,.2f} ({stop['percent']:.1%})
Risk if Stopped: ${actual_risk_dollars:,.2f} ({actual_risk_pct:.2f}% of capital)
```

**Profit Targets:**
```
Target 1 (Conservative - {profit_t1_pct:.1f}%):
  Price: ${tp1_price:,.2f}
  Profit: ${profit_t1:,.2f}
  R/R Ratio: {rr_t1:.1f}:1

Target 2 (Aggressive - {profit_t2_pct:.1f}%):
  Price: ${tp2_price:,.2f}
  Profit: ${profit_t2:,.2f}
  R/R Ratio: {rr_t2:.1f}:1
```

**Execution:**
1. Buy {units_to_buy:.4f} BTC at ${price:,.2f} = ${actual_position_value:,.2f}
2. Set stop loss at ${stop['price']:,.2f}
3. Take 50% profit at Target 1 (${profit_t1/2:,.2f})
4. Let 50% run to Target 2 (${profit_t2/2:,.2f})
5. Total potential: ${profit_t1/2 + profit_t2/2:,.2f}

**Note:** Position size is based on available capital, not just risk percentage.
The {size_mult:.2f}x multiplier is already applied but capped at your total capital.

"""
        return text


# Command-line interface for standalone use
if __name__ == "__main__":
    import json
    import sys
    
    # Example usage
    example_decision = {
        'direction': 'BUY',
        'reasoning': '✅ Elite score strong + positive manifold',
        'size_multiplier': 1.2,
        'stop_loss': {'percent': -0.011, 'price': 66093},
        'take_profit': {
            'tp1_percent': 0.05,
            'tp1_price': 70179,
            'tp2_percent': 0.12,
            'tp2_price': 74858
        },
        'risk_reward': {'conservative': 4.5, 'aggressive': 8.0},
        'confidence_breakdown': {
            'System Quality': '98%',
            'Conviction': '78%',
            'Regime Clarity': '100%',
            'Gate Status': 'PASS'
        },
        'warnings': [],
        'regime': 'normal',
        'chaos_level': 'CALM'
    }
    
    interpreter = DecisionInterpreter()
    interpretation = interpreter.interpret(
        example_decision,
        current_price=66866,
        user_capital=10000,
        risk_tolerance='moderate'
    )
    
    print(interpretation)
