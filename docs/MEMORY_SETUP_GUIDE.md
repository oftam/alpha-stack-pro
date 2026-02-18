# 🧠 Elite v20 Memory System - Quick Start Guide

## 🎯 What This Does

The Memory System gives Elite v20 **organizational memory** - it remembers:
- ✅ Every signal you generated (OnChain, Fear, Manifold, Regime)
- ✅ Every Claude recommendation (with full context)
- ✅ Performance of past recommendations (Win Rate, P&L)
- ✅ Consistency scores (Does Claude contradict himself?)

---

## 🚀 Setup (15 Minutes)

### Step 1: Install Dependencies

```bash
cd C:\Users\ofirt\Documents\alpha-stack-pro
pip install -r requirements_memory.txt
```

---

### Step 2: Create Supabase Project

1. Go to **https://supabase.com**
2. Click **"New Project"**
3. Name: `alpha-stack-memory`
4. Choose region (closest to you)
5. Set database password (save it!)
6. Wait 2 minutes for provisioning

---

### Step 3: Run Database Schema

1. In Supabase Dashboard → **SQL Editor**
2. Open `docs/SUPABASE_SCHEMA.sql`
3. Copy entire file
4. Paste into SQL Editor
5. Click **"Run"**
6. ✅ You should see: "Success. No rows returned"

---

### Step 4: Enable Extensions

1. Supabase → **Database** → **Extensions**
2. Search and enable:
   - ✅ `vector` (for embeddings)
   - ✅ `pg_cron` (for scheduled tasks)

**Note:** TimescaleDB may not be available on free tier - that's okay!

---

### Step 5: Get API Keys

#### Supabase
1. Supabase → **Project Settings** → **API**
2. Copy:
   - `Project URL`
   - `anon public` key

#### Cohere
1. Go to **https://dashboard.cohere.com**
2. Sign up (free)
3. Copy **API Key**

---

### Step 6: Configure Environment

Create `.env` file in project root:

```env
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Cohere
COHERE_API_KEY=your-cohere-api-key

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

**Or** add to `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
COHERE_API_KEY = "your-key"
```

---

### Step 7: Test Connection

```bash
python modules/supabase_client.py
```

Expected output:
```
✅ Connected to Supabase | Total signals: 0
✅ All tests passed!
```

---

## 📊 How to Use

### Automatic Logging (Recommended)

The memory system **auto-logs** signals when you use MEDALLION dashboard:

```python
# In MEDALLION dashboard (already integrated)
from modules.memory_logger import get_logger

logger = get_logger()

# After Elite analysis
logger.log_daily_signal(elite_results, current_price)

# After Claude responds
logger.log_claude_interaction(question, response, elite_results)
```

That's it! Everything is saved automatically.

---

### Manual Logging (Advanced)

```python
from modules.supabase_client import get_client

db = get_client()

# Save signal
signal_data = {
    'date': '2026-02-17',
    'price': 70100,
    'onchain_score': 84,
    'fear_index': 12,
    'manifold_dna': 87,
    'regime': 'BLOOD_IN_STREETS',
    'signal_strength': 'STRONG_BUY'
}

signal_id = db.save_signal(signal_data)

# Get recent history
recent = db.get_recent_signals(days=7)
print(f"Last 7 days: {len(recent)} signals")

# Calculate win rate
stats = db.get_win_rate(days=30)
print(f"Win Rate: {stats['win_rate']:.1f}%")
```

---

## 🔍 Verify It's Working

### Check Database

1. Supabase → **Table Editor**
2. Look at `daily_signals` table
3. You should see your logged signals

### Check Logs

In MEDALLION terminal output:
```
📝 Signal logged | ID: 123 | Regime: BLOOD_IN_STREETS
💬 Claude response logged | ID: 456
✅ Performance tracking updated @ $70,100
```

---

## 🎯 Next Steps

Once logging is working:

1. **Phase 3:** Build Consistency Analyzer
   - Detects contradictions
   - Calculates reliability score

2. **Phase 4:** Memory Injection
   - Claude remembers past 7 days
   - "You said X yesterday, conditions are similar..."

3. **Phase 5:** Analytics Dashboard
   - Visualize consistency trends
   - Performance charts
   - Win rate by regime

---

## 🐛 Troubleshooting

### "Module not found: supabase"
```bash
pip install supabase
```

### "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### "Supabase connection failed"
1. Check `.env` file exists
2. Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
3. Test in Supabase dashboard → SQL Editor → `SELECT 1;`

### "Table does not exist"
- Re-run `docs/SUPABASE_SCHEMA.sql` in SQL Editor

---

## 📋 Daily Maintenance

### Update Performance (Manual)

```python
from modules.memory_logger import get_logger

logger = get_logger()
logger.update_daily_performance(current_price=71500.00)
```

**Or** set up daily cron job (advanced):
```sql
SELECT cron.schedule(
    'update-performance',
    '0 0 * * *',  -- Daily at midnight
    $$ 
    SELECT update_performance_tracking(
        (SELECT price FROM daily_signals ORDER BY date DESC LIMIT 1)
    );
    $$
);
```

---

## ✅ Success Checklist

- [ ] Supabase project created
- [ ] Schema deployed (4 tables)
- [ ] Extensions enabled (vector, pg_cron)
- [ ] `.env` configured with API keys
- [ ] `python modules/supabase_client.py` passes
- [ ] First signal logged successfully
- [ ] Claude response captured

**You're ready for Phase 2!** 🚀

---

**Questions?** Check `implementation_plan.md` for full technical details.
