# 🧬 ELITE v20 - PRODUCTION Dashboard
### תמם - מערכת מסחר מתקדמת / Biological-Quant Hybrid System

## 🚀 Quick Start

### Windows:
```bash
run_elite_v20.bat
```

### Linux/Mac:
```bash
./run_elite_v20.sh
```

### Manual:
```bash
pip install -r requirements.txt
streamlit run elite_v20_dashboard.py
```

## ⚙️ Configuration

1. Copy `.env_template` to `.env`:
   ```bash
   cp .env_template .env
   ```

2. Add your API keys to `.env`:
   - CryptoQuant API key (for on-chain data)
   - Anthropic API key (for Claude AI chat) - **NEW!**
   - Glassnode API key (optional)
   - Telegram bot token (optional, for alerts)

## 🤖 NEW: Claude AI Assistant

**Integrated AI chat in sidebar that understands your entire ELITE v20 system!**

Features:
- **Deep System Knowledge**: Knows all 6 layers, Manifold DNA, Fear Amplifier
- **Real-time Context**: Sees your current portfolio, signals, and scores
- **Hebrew Interface**: Professional responses in Hebrew
- **Quick Questions**: Pre-built common queries
- **Mathematical Explanations**: Explains Bayesian logic, Victory Vector, etc.

Setup:
1. Get Anthropic API key from https://console.anthropic.com
2. Add to `.env`: `ANTHROPIC_API_KEY=your_key_here`
3. Chat appears automatically in sidebar!

## 📊 System Architecture

**6 Layers:**
- Layer 1: Data Sources (Binance, CryptoQuant, Fear & Greed)
- Layer 2: Feature Engineering (Diffusion, Chaos, NLP)
- Layer 3: ML Models (Regime Detection, Phase Transitions)
- Layer 4: Decision Engine (Manifold DNA, Bayesian Logic)
- Layer 5: Execution (DCA 60% + Tactical 40%)
- Layer 6: Infrastructure (Telegram, Paper Trading, Audit)

## 💰 Strategy

- **DCA Strategy (60%)**: Long-term accumulation targeting $600k-$1M BTC by 2030
- **Tactical Strategy (40%)**: Active trading with T1/T2 protocol
- **Risk Management**: Never risk >5% per trade (Iron Rule)

## 🎯 Key Features

- **Manifold DNA Scoring**: 0-100 signal strength
- **OnChain Diffusion**: Whale activity tracking
- **Fear & Greed Integration**: Market sentiment analysis
- **Multi-Timeframe Analysis**: 1H, 4H, 1D confluence
- **Telegram Alerts**: Real-time notifications
- **Paper Trading**: Safe testing environment
- **🤖 Claude AI Chat**: Expert trading assistant (NEW!)

## 📱 Dashboard Access

- **Main Dashboard**: http://localhost:8501
- **Multi-Timeframe**: http://localhost:8502 (if deployed)
- **DUDU Overlay**: http://localhost:8503 (if deployed)

## ⚠️ Important Notes

1. **IRON RULE**: Never risk more than 5% per trade
2. **Fallback Mode**: System works without API keys (uses synthetic data)
3. **Self-Healing**: Auto-creates missing directories and files
4. **Extensible**: Modular architecture for easy updates
5. **AI Assistant**: Claude works even without other APIs (uses fallback data)

## 🔧 Troubleshooting

**Missing modules**: The system includes fallback classes for all components.
**API Errors**: Check your .env file and API key validity.
**Claude not responding**: Verify ANTHROPIC_API_KEY in .env file.
**Port Issues**: Change port in run script if 8501 is occupied.

---

**Created by תמם | ELITE v20 + Claude AI | Top 0.001% Trading System**
