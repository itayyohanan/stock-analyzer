# 📈 מנתח מניות

אפליקציית ניתוח מניות מקצועית בנויה עם Streamlit, Plotly ו-yfinance.

## תכונות

- **dark theme** מקצועי בהשראת TradingView
- **גרף נרות** עם ממוצעים נעים 50/200 ורצועות בולינגר
- **מדד RSI** עם אזורי קניית/מכירת יתר
- **נתונים פונדמנטליים** — מכפיל רווח, הכנסות, רווח, EPS
- **המלצה אוטומטית** — קנה / המתן / מכור
- **בדיקת אחור (Backtesting)** — סימולציית אסטרטגיית RSI מ-2017 עד היום
- **עברית מלאה** עם תמיכה ב-RTL

---

## הרצה מקומית

### 1. כנס לתיקייה

```bash
cd stock-analyzer
```

### 2. צור סביבה וירטואלית

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. התקן תלויות

```bash
pip install -r requirements.txt
```

### 4. הפעל את האפליקציה

```bash
streamlit run app.py
```

האפליקציה תיפתח אוטומטית בכתובת [http://localhost:8501](http://localhost:8501).

---

## פריסה ל-Streamlit Cloud (חינם)

1. **העלה ל-GitHub** — צור repo ודחוף את הקבצים:

   ```bash
   git init
   git add app.py requirements.txt README.md
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/stock-analyzer.git
   git push -u origin main
   ```

2. **היכנס** ל-[share.streamlit.io](https://share.streamlit.io) עם חשבון GitHub.

3. לחץ **"New app"**, בחר את ה-repo, וודא שהקובץ הראשי הוא `app.py`, לחץ **Deploy**.

4. האפליקציה תהיה פעילה תוך ~2 דקות ב:
   `https://YOUR_USERNAME-stock-analyzer-app-XXXX.streamlit.app`

> Streamlit Cloud חינמי לחלוטין עבור repos ציבוריים.

---

## מבנה הפרויקט

```
stock-analyzer/
├── app.py              # קוד האפליקציה המלא
├── requirements.txt    # תלויות Python
└── README.md           # מסמך זה
```
