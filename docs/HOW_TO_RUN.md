# 🚀 EXECUTIVE ORDERS v3.3.1 - הוראות הפעלה

## ✅ קובץ עובד! הנה איך להתחיל:

---

## שלב 1: התקן חבילות (בפעם ראשונה בלבד)

פתח PowerShell/Terminal באותה תיקייה והרץ:

```bash
pip install yfinance python-binance feedparser requests
```

---

## שלב 2: הרץ את הבוט

```bash
python executive_orders_working.py
```

או אם זה לא עובד:

```bash
python3 executive_orders_working.py
```

---

## ✅ מה צריך לקרות:

1. ✓ חלון גדול נפתח עם ניטוח ירוק
2. ✓ כתוב "EXECUTIVE ORDERS v3.3.1"
3. ✓ שתי טבלאות: Technical + Risk Gates
4. ✓ כפתור ירוק "▶️ START"
5. ✓ כפתור אדום "❌ EXIT"

---

## 🔴 אם לא עובד?

### בעיה: "ModuleNotFoundError: No module named 'tkinter'"

**פתרון:**
```bash
# Windows
pip install tk

# Mac
brew install python-tk

# Linux
sudo apt-get install python3-tk
```

### בעיה: "No module named 'yfinance'"

**פתרון:**
```bash
pip install yfinance --upgrade
```

### בעיה: "Port already in use"

**פתרון:**
סגור את כל חלונות הבוט הקודמים:
```bash
# Windows
taskkill /F /IM python.exe

# Mac/Linux
killall python
```

---

## 📊 איך להשתמש בבוט:

1. **לחץ ▶️ START** - הבוט יתחיל לעקוב
2. **חכה לאירוע** - כשמתקיים תנאי BUY - הבוט מודיע
3. **לחץ ⏹️ STOP** - להפסקה
4. **לחץ ❌ EXIT** - לסגירה

---

## 🌐 סוגי התראות:

כדי להוסיף WhatsApp + Gmail + Google Sheets:

1. צור קובץ `.env` באותה תיקייה
2. הוסף API Keys מ-Twilio/Google
3. הרץ את הגרסה ה-PRO (exec-v3.4-pro.py)

ראה: **exec-setup-guide.md** למפורש

---

## 📈 מה הבוט עושה:

✓ סוקר Finnhub Calendar (אירועים כלכליים)  
✓ בודק DXY/VIX/Gold-USD (סיכון בזמן אמת)  
✓ מחשב Alpha Score (65 אינדיקטורים)  
✓ מנהל עסקאות עם Trailing Stops  
✓ יומן מלא של כל עסקה  

---

## 💾 שמור קובץ מוקד:

```python
# אם תרצה לשמור את הנתונים שלך:
# קובץ state שמור תמיד ב:
data/executive_state.json
```

---

## 🎯 Ready!

```bash
python executive_orders_working.py
```

**זה הכל! בוט עובד לחלוטין עם UI מלא.** ✅

לשאלות/בעיות - דוברים את ההוראות מעלה.
