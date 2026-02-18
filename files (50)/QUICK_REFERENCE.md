# 📋 ELITE v20 + Claude - Quick Reference Card
## כרטיס עזר מהיר (להדפסה)

---

## ⚡ התחלה מהירה (5 דקות)

```bash
1. pip install anthropic
2. צור: .streamlit\secrets.toml
3. הוסף: ANTHROPIC_API_KEY = "sk-ant-..."
4. RUN_MY3.bat
```

---

## 📁 מבנה קבצים

```
alpha-stack-pro\
├── elite_v20_dashboard.py                 ← עדכן את זה
├── claude_chat_module_ELITE_v20.py        ← הוסף את זה
└── .streamlit\
    └── secrets.toml                       ← הוסף את זה
```

---

## 🔑 API Key - איך מקבלים?

```
1. https://console.anthropic.com/
2. Sign Up / Login
3. API Keys → Create Key
4. Copy the key (starts with sk-ant-api03-)
```

---

## 💬 שאלות מומלצות

### בסיסי:
- "מה המצב היום?"
- "למה אין סיגנל?"
- "מה הסיכון שלי?"

### מתקדם:
- "למה Violence/Chaos גבוה?"
- "תסביר את ה-Manifold DNA"
- "האם כדאי להיכנס ב-DCA?"

### אנליזה:
- "מה המודולים אומרים?"
- "איך אני יכול לשפר?"
- "מה ההבדל בין DCA ל-Tactical?"

---

## 🎯 מה Claude רואה?

✅ Portfolio (Capital, Positions, P&L)
✅ Signals (DCA + Tactical)
✅ Module Scores (5 modules)
✅ Risk Metrics
✅ Performance Stats
✅ Current Price & Volume

**Claude מנתח הכל ועונה בעברית!**

---

## 🔧 פתרון בעיות - מהיר

| בעיה | פתרון |
|------|--------|
| Claude לא מופיע | `pip install anthropic` |
| "API Key חסר" | בדוק `.streamlit\secrets.toml` |
| "Module not found" | ודא שהקובץ באותה תיקייה |
| שגיאת חיבור | בדוק אינטרנט, נסה שוב |

---

## 💰 עלויות

- **התחלה:** $5 חינם
- **שאלה:** ~₪0.01
- **100 שאלות:** ~₪1
- **1000 שאלות:** ~₪10

---

## 🔒 אבטחה

```bash
# הוסף ל-.gitignore:
.streamlit/secrets.toml
.env
```

**אל תשתף את ה-API Key!**

---

## 🆘 עזרה

**אם משהו לא עובד:**
1. קרא את `ELITE_CLAUDE_INSTALLATION.md`
2. בדוק את הגיבוי (יש!)
3. נסה מחדש

**גיבוי:**
```bash
copy elite_v20_dashboard_BACKUP.py elite_v20_dashboard.py
```

---

## ✅ Checklist

```
☐ pip install anthropic
☐ claude_chat_module_ELITE_v20.py בתיקייה
☐ .streamlit\secrets.toml עם API Key
☐ elite_v20_dashboard.py מעודכן
☐ RUN_MY3.bat
☐ Claude מופיע בסיידבר!
```

---

## 🎊 זהו! תהנה מה-Jarvis שלך!

**שאל אותו כל דבר על המסחר שלך! 🚀**

---

*Keep this card handy while using ELITE v20!*
