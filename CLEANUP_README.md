# 🗂️ Alpha-Stack-Pro Cleanup - Quick Guide

## ✅ **מה יצרתי לך:**

קובץ: `CLEANUP_ALPHA_STACK.ps1` - Script אוטומטי שמסדר הכל!

---

## 🚀 **איך להריץ:**

### אופציה 1: Dry Run (מומלץ ראשון!)
```powershell
# בדוק מה ייעשה בלי לעשות שינויים
.\CLEANUP_ALPHA_STACK.ps1 -DryRun
```

### אופציה 2: הרצה מלאה
```powershell
# עושה cleanup מלא + גיבוי אוטומטי
.\CLEANUP_ALPHA_STACK.ps1
```

### אופציה 3: ללא גיבוי (לא מומלץ!)
```powershell
# אם כבר יש לך backup
.\CLEANUP_ALPHA_STACK.ps1 -SkipBackup
```

---

## 📋 **מה ה-Script עושה:**

### שלב 1: **גיבוי מלא** 💾
- יוצר backup folder: `alpha-stack-pro_BACKUP_2026-02-17_HHmmss`
- יוצר ZIP: `alpha-stack-pro_BACKUP_2026-02-17_HHmmss.zip`

### שלב 2: **יוצר מבנה חדש** 📁
```
dashboards/   ← כל הדשבורדים
scripts/      ← BAT files
docs/         ← תיעוד
archive/      ← קבצים ישנים
modules/      ← נשאר כמו שהוא
```

### שלב 3: **מעביר קבצים פעילים** ✅
- 5 דשבורדים → `dashboards/`
- 4 scripts → `scripts/`
- 5 docs → `docs/`
- 2 קבצים → `modules/`

### שלב 4: **מארכב ~350 קבצים ישנים** 🗄️
- כל ה-BACKUP, OLD, FIXED files
- alpha_stack, war_room, executive files
- HTML, PS1, ישנים
- 40+ תיקיות ישנות

### שלב 5: **סיכום** 📊
- כמה קבצים הועברו
- איפה ה-backup
- הוראות להמשך

---

## ⚠️ **לפני שמריצים:**

1. ✅ **סגור את כל הדשבורדים הפועלים**
2. ✅ **תריץ Dry Run קודם** - תראה מה ייעשה
3. ✅ **וודא שיש לך מקום בדיסק** (~2GB לbackup)

---

## 🎯 **אחרי ההרצה:**

### בדוק שהכל עובד:
```bash
cd C:\Users\ofirt\Documents\alpha-stack-pro\scripts
.\RUN_MEDALLION.bat
```

### אם הכל עובד:
- ✅ המבנה החדש מושלם!
- ⚠️ אפשר למחוק את `archive/` (אחרי כמה ימים)
- ⚠️ הbackup ב-ZIP נשאר תמיד!

### אם משהו שבור:
```powershell
# שחזר מה-backup
$BackupPath = "C:\Users\ofirt\Documents\alpha-stack-pro_BACKUP_*"
Copy-Item -Path $BackupPath\* -Destination "C:\Users\ofirt\Documents\alpha-stack-pro" -Recurse -Force
```

---

## 📊 **תוצאה צפויה:**

**לפני:**
```
479 קבצים, 54 תיקיות = בלגן
```

**אחרי:**
```
dashboards/  (5 קבצים)
modules/     (25 קבצים)
scripts/     (4 קבצים)
docs/        (6 קבצים)
archive/     (350+ קבצים ישנים)
+ Config files
= סדר מושלם! ✨
```

---

## 🔧 **פתרון בעיות:**

### "Execution Policy Error"
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "Access Denied"
הרץ PowerShell כ-Administrator

### "File in use"
סגור את VS Code, Streamlit, וכל תוכנה שפותחת את הקבצים

---

## ✅ **מוכן להתחיל!**

```powershell
# 1. Dry Run (ראשון!)
cd C:\Users\ofirt\Documents\alpha-stack-pro
.\CLEANUP_ALPHA_STACK.ps1 -DryRun

# 2. אם הכל נראה טוב - הרץ!
.\CLEANUP_ALPHA_STACK.ps1
```

**בהצלחה! 🚀**
