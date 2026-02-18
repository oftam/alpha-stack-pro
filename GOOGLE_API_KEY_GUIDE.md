# 🔑 Google API Key - מדריך קבלה מהירה

## צעד 1: כנס ל-Google AI Studio

פתח דפדפן:
```
https://aistudio.google.com/app/apikey
```

---

## צעד 2: צור API Key

1. לחץ על **"Create API key"**
2. בחר: **"Create API key in new project"** (או בחר פרויקט קיים)
3. **העתק את המפתח** (מתחיל ב-`AIzaSy...`)

**שים לב:** המפתח יוצג רק פעם אחת - שמור אותו!

---

## צעד 3: שמור בקובץ Secrets

### יצירת קובץ Secrets (אם לא קיים):

```powershell
# צור תיקייה
mkdir C:\Users\ofirt\Documents\alpha-stack-pro\.streamlit

# צור קובץ secrets
notepad C:\Users\ofirt\Documents\alpha-stack-pro\.streamlit\secrets.toml
```

### הדבק את זה ושמור:

```toml
# Google Gemini API Key
GOOGLE_API_KEY = "AIzaSy..."  # שים את המפתח שלך כאן
```

**החלף את `AIzaSy...` במפתח האמיתי שקיבלת!**

---

## ✅ סיימת!

עכשיו המפתח מוכן לשימוש ב-MEDALLION Dashboard.

---

## 🧪 בדיקה מהירה:

```powershell
cd C:\Users\ofirt\Documents\alpha-stack-pro
python modules/gemini_chat_module_ELITE_v20.py
```

אמור לראות:
```
✅ Gemini initialized
```

---

## 💡 טיפים:

- **Free Tier:** 15 requests/min, 1M tokens/day
- **Ultra Subscription:** limits גבוהים יותר
- **Model:** Gemini 1.5 Pro (הטוב ביותר)

---

**יש בעיה?** תגיד לי!
