# 🚀 Elite v20 Memory System - DEPLOYMENT CHECKLIST

**Ready to go live!** Follow these steps to activate organizational memory.

---

## ✅ **Pre-Flight Checklist**

Before deploying, verify you have:

- [x] Supabase project created
- [x] API keys (Supabase anon key)
- [x] `.env.memory` file configured
- [x] All Python modules installed
- [ ] SQL schema deployed to Supabase
- [ ] Cohere API key obtained
- [ ] Test connection successful

---

## 🛠️ **Step-by-Step Deployment**

### Step 1: Deploy SQL Schema (5 minutes)

**CRITICAL:** Run this first!

1. Open browser → https://supabase.com/dashboard
2. Select project: `alpha-stack-memory`
3. Click **SQL Editor** (left sidebar)
4. Open file on your computer:
   ```
   C:\Users\ofirt\Documents\alpha-stack-pro\docs\SUPABASE_SCHEMA.sql
   ```
5. Copy **ENTIRE file** (780 lines)
6. Paste into SQL Editor
7. Click **RUN** (bottom right)

**Expected result:**
```
Success. No rows returned.
+ created table daily_signals
+ created table claude_responses
+ created table performance_tracking
+ created table consistency_scores
```

---

### Step 2: Get Cohere API Key (FREE - 3 minutes)

1. Go to: https://dashboard.cohere.com
2. Click **"Sign Up"** → Use Google account
3. Dashboard → **API Keys** → Copy key
4. Open `.env.memory` file:
   ```powershell
   notepad C:\Users\ofirt\Documents\alpha-stack-pro\.env.memory
   ```
5. Replace line:
   ```
   COHERE_API_KEY=your-cohere-api-key-here
   ```
   With your actual key:
   ```
   COHERE_API_KEY=xxx-your-real-key-xxx
   ```
6. Save and close

---

### Step 3: Install Dependencies (2 minutes)

```powershell
cd C:\Users\ofirt\Documents\alpha-stack-pro\files (50)
pip install supabase cohere python-dotenv
```

**Wait for:** "Successfully installed..."

---

### Step 4: Test Connection (1 minute)

```powershell
cd C:\Users\ofirt\Documents\alpha-stack-pro\files (50)
python modules/supabase_client.py
```

**Expected output:**
```
✅ Connected to Supabase | Total signals: 0
✅ All tests passed!
```

**If error:** Check `.env.memory` has correct values

---

###Step 5: Launch MEDALLION with Memory! 🎉

```powershell
cd C:\Users\ofirt\Documents\alpha-stack-pro
streamlit run dashboards/elite_v20_dashboard_MEDALLION.py --server.port 8501
```

**What to look for:**
```
✅ Memory System loaded
📅 Signal logged to memory (ID: 1)
```

---

## 🎯 **Verify It's Working**

### Check 1: Supabase Dashboard

1. Go to Supabase → **Table Editor**
2. Select `daily_signals` table
3. You should see your first signal!

**Example:**
| id | date | price | manifold_dna | regime |
|----|------|-------|--------------|---------|
| 1 | 2026-02-17 | 70100 | 87 | BLOOD_IN_STREETS |

---

### Check 2: MEDALLION Terminal

After running Elite analysis, you should see:
```
✅ Memory System loaded
🧬 Running Elite Analysis...
📅 Signal logged to memory (ID: 1)
```

---

### Check 3: Test Memory Recall (Optional)

```powershell
cd C:\Users\ofirt\Documents/alpha-stack-pro\files (50)
python modules/memory_engine.py
```

Should show recent history!

---

## 🐛 **Troubleshooting**

### "Memory System not available"
- Check `.env.memory` exists in project root
- Verify SUPABASE_URL and SUPABASE_KEY are set

### "Connection refused"
- Check Supabase project is running (not paused)
- Test URL in browser: https://lwcvfpvkutrhyabtwppt.supabase.co
- Should see Supabase API response

### "Table does not exist"
- Re-run SQL schema (Step 1)
- Check all 4 tables created in Supabase → Tables

### "Memory logging failed"
- Check internet connection
- Verify API keys are correct
- Check Supabase quotas (free tier: 500MB)

---

## 📊 **What Happens Next?**

Once deployed, **EVERY TIME** you run MEDALLION:

1. ✅ Market data fetched
2. ✅ Elite analysis runs
3. ✅ **Signal AUTO-LOGGED** to Supabase
4. ✅ Regime, scores, price saved
5. ✅ Ready for consistency checking!

**After 7 days:**
- Memory engine has history to compare
- Consistency analyzer can detect contradictions
- Win rate calculations become meaningful

---

## 🚀 **Phase 2: Claude Memory Injection (Next Step)**

After signals are logging successfully:

1. Integrate with Claude chat module
2. Inject last 7 days context before questions
3. Show similar past scenarios
4. Warn if recommendation contradicts history

**This requires:** Minimum 3-5 days of logged data

---

## 📋 **Daily Usage**

**No maintenance needed!** Just use MEDALLION normally:

1. Open dashboard
2. Elite analysis runs
3. Signal logs automatically
4. Check Supabase to see history grow

**Weekly:** Check consistency score in Supabase

---

**Questions?** Check `docs/MEMORY_SETUP_GUIDE.md` for detailed explanations!

**Status:** 🟢 Ready to deploy!  
**Time to complete:** ~15 minutes  
**Difficulty:** ⭐⭐☆☆☆ (Easy)
