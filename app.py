import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json, os, time, concurrent.futures, threading, urllib.parse, tempfile
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ── Writable data directory (local = script dir; Cloud = /tmp) ────────────────
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    _test = os.path.join(_APP_DIR, ".write_test")
    open(_test, "w").close(); os.remove(_test)
    DATA_DIR = _APP_DIR
except (IOError, OSError):
    DATA_DIR = os.path.join(tempfile.gettempdir(), "stock_analyzer")
    os.makedirs(DATA_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
BG   = "#02070f"; SURF  = "#06101c"; SURF2 = "#091522"; SURF3 = "#0c1c30"
BDR  = "#111e2e"; BDR2  = "#182b40"
CYAN = "#00b4d8"; GRN   = "#22c55e"; RED   = "#ef4444"
AMB  = "#f59e0b"; PUR   = "#a78bfa"
TX   = "#ddeeff"; TX2   = "#4d7a9a"; TX3   = "#253d52"

PB = dict(
    plot_bgcolor=SURF, paper_bgcolor=SURF,
    font=dict(color=TX, family="Heebo, sans-serif", size=11),
    xaxis=dict(gridcolor=BDR, zerolinecolor=BDR, tickfont=dict(color=TX2)),
    yaxis=dict(gridcolor=BDR, zerolinecolor=BDR, tickfont=dict(color=TX2)),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0,
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=8, r=8, t=36, b=8),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=SURF2, bordercolor=BDR, font=dict(color=TX, size=11)),
)

HOT = [
    {"t":"MRVL","n":"Marvell Technology", "c":"מוליכים למחצה",   "a":CYAN,
     "w":"מייצרת שבבים ייעודיים למרכזי נתונים ורשתות. "
         "נהנית מחוזים עם ענקיות הענן לשבבי AI מותאמים אישית."},
    {"t":"NVDA","n":"NVIDIA",             "c":"GPU / AI",         "a":PUR,
     "w":"מייצרת GPU שמניעים כמעט כל מערכת AI בעולם. "
         "ה-H100 וה-B200 שלה הכי מבוקשים בשוק."},
    {"t":"AMD", "n":"AMD",                "c":"מעבדים",           "a":RED,
     "w":"מתחרה ב-Intel וב-NVIDIA. "
         "כובשת נתחי שוק בשרתים ובשוק ה-AI עם מחיר-ביצועים גבוה."},
    {"t":"ARM", "n":"ARM Holdings",       "c":"ארכיטקטורת שבבים","a":AMB,
     "w":"מעצבת ארכיטקטורת שבבים ומוכרת רישיונות. "
         "כמעט כל סמארטפון ושבב AI בעולם מבוסס עליה."},
    {"t":"CRWD","n":"CrowdStrike",        "c":"אבטחת סייבר",      "a":GRN,
     "w":"מגנה על חברות מפני האקרים ותוכנות כופר בענן. "
         "פלטפורמת Falcon עוצרת מתקפות בזמן אמת."},
    {"t":"PLTR","n":"Palantir",           "c":"ניתוח נתונים / AI","a":PUR,
     "w":"בונה תוכנות לניתוח נתונים לממשלות וחברות ענק. "
         "פלטפורמת AI שמאפשרת קבלת החלטות בשפה יומיומית."},
    {"t":"DDOG","n":"Datadog",            "c":"מוניטורינג ענן",   "a":CYAN,
     "w":"עוקבת אחרי שרתים ואפליקציות ומתריעה על תקלות. "
         "הביקוש גדל עם המעבר לענן."},
    {"t":"NET", "n":"Cloudflare",         "c":"אבטחת רשת",        "a":AMB,
     "w":"מגנה על מיליוני אתרים ומאיצה טעינתם. "
         "כמעט כל גלישה עוברת דרך התשתית שלה."},
    {"t":"AXON","n":"Axon Enterprise",    "c":"ביטחון ציבורי",    "a":GRN,
     "w":"מייצרת ציוד לכוחות ביטחון — מצלמות גוף, נשק חשמלי ותוכנת ניהול ראיות. "
         "צומחת ממכירות לרשויות משטרה."},
    {"t":"TTD", "n":"The Trade Desk",     "c":"פרסום דיגיטלי",    "a":RED,
     "w":"מאפשרת קניית שטחי פרסום דיגיטלי בזמן אמת. "
         "מרוויחה ממעבר תקציבי פרסום מטלוויזיה לדיגיטל."},
]

PF_FILE          = os.path.join(DATA_DIR, "portfolio.json")
WL_FILE          = os.path.join(DATA_DIR, "watchlist.json")
ALERTS_FILE      = os.path.join(DATA_DIR, "alerts.json")
TELEGRAM_FILE    = os.path.join(DATA_DIR, "telegram_config.json")
GURU_SEEN_FILE   = os.path.join(DATA_DIR, "guru_seen.json")

GURUS = [
    {"id": "burry",        "name": "Michael Burry",        "fund": "Scion Asset Management",  "emoji": "🐻",
     "cik": "0001649339", "q": "Michael Burry stock investment"},
    {"id": "buffett",      "name": "Warren Buffett",       "fund": "Berkshire Hathaway",      "emoji": "🏦",
     "cik": "0000102909", "q": "Warren Buffett Berkshire Hathaway buy sell"},
    {"id": "musk",         "name": "Elon Musk",            "fund": "Tesla / SpaceX / xAI",   "emoji": "⚡",
     "cik": None,         "q": "Elon Musk Tesla SpaceX investment market"},
    {"id": "ackman",       "name": "Bill Ackman",          "fund": "Pershing Square",         "emoji": "🎯",
     "cik": "0001336528", "q": "Bill Ackman Pershing Square position"},
    {"id": "wood",         "name": "Cathie Wood",          "fund": "ARK Invest",              "emoji": "🚀",
     "cik": "0001579982", "q": "Cathie Wood ARK Invest buy sell"},
    {"id": "dalio",        "name": "Ray Dalio",            "fund": "Bridgewater",             "emoji": "🌊",
     "cik": "0001350694", "q": "Ray Dalio Bridgewater portfolio"},
    {"id": "druckenmiller","name": "Stanley Druckenmiller","fund": "Duquesne Family Office",  "emoji": "🦅",
     "cik": "0001536411", "q": "Stanley Druckenmiller Duquesne investment"},
    {"id": "dimon",        "name": "Jamie Dimon",          "fund": "JPMorgan Chase",          "emoji": "🏛️",
     "cik": None,         "q": "Jamie Dimon JPMorgan economy market outlook"},
    {"id": "icahn",        "name": "Carl Icahn",           "fund": "Icahn Enterprises",       "emoji": "🦁",
     "cik": "0000813672", "q": "Carl Icahn activist investor position"},
    {"id": "fink",         "name": "Larry Fink",           "fund": "BlackRock",               "emoji": "🌑",
     "cik": None,         "q": "Larry Fink BlackRock investment market"},
    {"id": "tepper",       "name": "David Tepper",         "fund": "Appaloosa Management",    "emoji": "🐐",
     "cik": "0001418100", "q": "David Tepper Appaloosa hedge fund"},
    {"id": "tudor",        "name": "Paul Tudor Jones",     "fund": "Tudor Investment",        "emoji": "🎲",
     "cik": "0000859001", "q": "Paul Tudor Jones Tudor Investment macro"},
    {"id": "soros",        "name": "George Soros",         "fund": "Soros Fund Management",  "emoji": "♟️",
     "cik": "0001029160", "q": "George Soros fund investment"},
]

# ── Israeli stocks (TASE) ──────────────────────────────────────────────────────
TASE_UNIVERSE = [
    {"t":"TEVA.TA",  "n":"טבע תעשיות פרמצבטיות", "s":"פארמה"},
    {"t":"NICE.TA",  "n":"נייס סיסטמס",           "s":"טכנולוגיה"},
    {"t":"ICL.TA",   "n":"ICL Group",              "s":"כימיה"},
    {"t":"ESLT.TA",  "n":"אלביט מערכות",           "s":"ביטחון"},
    {"t":"CHKP",     "n":"Check Point",            "s":"אבטחת סייבר"},
    {"t":"MNDY",     "n":"Monday.com",             "s":"תוכנה"},
    {"t":"GLBE",     "n":"Global-E Online",        "s":"מסחר אלקטרוני"},
    {"t":"WIX",      "n":"Wix.com",               "s":"תוכנה"},
    {"t":"FVRR",     "n":"Fiverr",                 "s":"פלטפורמת שירותים"},
    {"t":"DSGX",     "n":"Descartes Systems",      "s":"לוגיסטיקה"},
    {"t":"LUMI.TA",  "n":"בנק לאומי",              "s":"בנקאות"},
    {"t":"DSCT.TA",  "n":"בנק דיסקונט",            "s":"בנקאות"},
    {"t":"HARL.TA",  "n":"הראל ביטוח",             "s":"ביטוח"},
    {"t":"MGDL.TA",  "n":"מגדל ביטוח",             "s":"ביטוח"},
    {"t":"AMOT.TA",  "n":"אמות השקעות",            "s":"נדל\"ן"},
    {"t":"AZRG.TA",  "n":"עזריאלי גרופ",           "s":"נדל\"ן"},
    {"t":"PHMD.TA",  "n":"פרמקים",                 "s":"פארמה"},
    {"t":"ENLT.TA",  "n":"אנלייט אנרגיה",          "s":"אנרגיה ירוקה"},
    {"t":"SMCH.TA",  "n":"שמחה מובייל",            "s":"תקשורת"},
    {"t":"BEZQ.TA",  "n":"בזק",                   "s":"תקשורת"},
]

# ── Deep-scan universe: 100+ stocks with Hebrew metadata ──────────────────────
# Fields: t=ticker, n=name, s=sector(Hebrew), d=description(Hebrew), u=why-under-radar
DEEP_SCAN_UNIVERSE = [
    # ── Large/Mid-cap Tech ─────────────────────────────────────────────────────
    {"t":"MRVL", "n":"Marvell Technology", "s":"מוליכים למחצה",
     "d":"מייצרת שבבי AI מותאמים אישית למרכזי נתונים ורשתות 5G.", "u":""},
    {"t":"ANET", "n":"Arista Networks",    "s":"רשתות",
     "d":"ספקית ציוד רשת ענן מתקדם לחברות הגדולות בעולם.", "u":""},
    {"t":"DDOG", "n":"Datadog",            "s":"ענן / מוניטורינג",
     "d":"פלטפורמת מוניטורינג לתשתיות ענן — הכרחית לכל DevOps.", "u":""},
    {"t":"CRWD", "n":"CrowdStrike",        "s":"אבטחת סייבר",
     "d":"מגנה על ארגונים מפני מתקפות סייבר בפלטפורמת Falcon.", "u":""},
    {"t":"ZS",   "n":"Zscaler",            "s":"אבטחת סייבר",
     "d":"אבטחת גישה לענן ללא VPN — מודל Zero Trust.", "u":""},
    {"t":"NET",  "n":"Cloudflare",         "s":"אבטחת רשת",
     "d":"מגנה ומאיצה מיליוני אתרים — תשתית האינטרנט הנסתרת.", "u":""},
    {"t":"SNOW", "n":"Snowflake",          "s":"נתונים בענן",
     "d":"פלטפורמת מחסן נתונים בענן — מרכז של ניתוח Big Data.", "u":""},
    {"t":"PLTR", "n":"Palantir",           "s":"AI / ניתוח נתונים",
     "d":"בונה תוכנות AI לממשלות וחברות ענק לקבלת החלטות.", "u":""},
    {"t":"AXON", "n":"Axon Enterprise",    "s":"ביטחון ציבורי",
     "d":"מייצרת מצלמות גוף, נשק חשמלי ותוכנות לכוחות ביטחון.", "u":""},
    {"t":"AVGO", "n":"Broadcom",           "s":"מוליכים למחצה",
     "d":"מייצרת שבבי רשת, Wi-Fi ותשתית מרכזי נתונים.", "u":""},
    {"t":"KLAC", "n":"KLA Corporation",    "s":"ציוד מוליכים",
     "d":"מייצרת ציוד בקרת תהליכים לייצור שבבים — מונופול בתחומה.", "u":""},
    {"t":"LRCX", "n":"Lam Research",       "s":"ציוד מוליכים",
     "d":"ציוד חריטה ושקיעה לייצור שבבים — שולט ב-50% מהשוק.", "u":""},
    {"t":"SNPS", "n":"Synopsys",           "s":"תוכנת שבבים",
     "d":"תוכנה לתכנון שבבים — כלי חיוני לכל חברת מוליכים.", "u":""},
    {"t":"CDNS", "n":"Cadence Design",     "s":"תוכנת שבבים",
     "d":"מתחרה ב-Synopsys בתכנון שבבים — מונופול יחד עם Synopsys.", "u":""},
    {"t":"PAYC", "n":"Paycom Software",    "s":"HR / פינטק",
     "d":"תוכנת ניהול שכר ומשאבי אנוש לעסקים.", "u":""},
    {"t":"PCTY", "n":"Paylocity",          "s":"HR / פינטק",
     "d":"פלטפורמת HR ושכר לעסקים בינוניים — צמיחה עקבית.", "u":""},
    # ── Small/Unknown Gems ─────────────────────────────────────────────────────
    {"t":"CEVA", "n":"CEVA Inc.",          "s":"IP שבבים",
     "d":"מספקת ליבות IP לעיבוד אותות ו-AI בשבבים ניידים.",
     "u":"חברה קטנה ב-3 מיליארד דולר — מסייעת לכל יצרן שבבי IoT ו-5G אך לא בכותרות."},
    {"t":"SLAB", "n":"Silicon Labs",       "s":"IoT",
     "d":"מייצרת שבבים חסכוניים לאינטרנט של הדברים (IoT).",
     "u":"כ-2 מיליארד שווי שוק — IoT עדיין לא הגיע לשלב הצמיחה הגדולה."},
    {"t":"AMBA", "n":"Ambarella",          "s":"AI Edge",
     "d":"מייצרת שבבי AI לעיבוד וידאו — מצלמות אבטחה ורכבים אוטונומיים.",
     "u":"מתחת לרדאר — פחות מ-4 מיליארד, אך שבביה נמצאים בכל מצלמת אבטחה חכמה."},
    {"t":"LSCC", "n":"Lattice Semiconductor","s":"FPGA",
     "d":"שבבי FPGA לצריכת חשמל נמוכה — מובילה בשוק ה-Edge AI.",
     "u":"נישה של FPGA קטן לא מוכרת לרוב המשקיעים, אך הצמיחה חזקה."},
    {"t":"ALGM", "n":"Allegro MicroSystems","s":"חיישנים",
     "d":"חיישני מגנטיות וזרם לרכבים חשמליים ותעשייה.",
     "u":"חברה ב-2 מיליארד שמסייעת לכל EV — המניה לא על מדורי הפיננסים."},
    {"t":"ACLS", "n":"Axcelis Technologies","s":"ציוד מוליכים",
     "d":"ציוד שתל יונים לייצור שבבים — ביקוש גדל עם הרחבת Fabs.",
     "u":"מתחת 2 מיליארד שווי שוק — סגמנט נישה של ציוד שבבים שמעטים עוקבים אחריו."},
    {"t":"ONTO", "n":"Onto Innovation",    "s":"ציוד מוליכים",
     "d":"מערכות בקרת תהליכים ומדידה לייצור שבבים.",
     "u":"כמיליארד וחצי שווי — מונופול קטן בבקרת תהליכי עיבוד שבבים."},
    {"t":"FORM", "n":"FormFactor",         "s":"בדיקת שבבים",
     "d":"מייצרת כרטיסי probe לבדיקת שבבים — הכרחי בכל fab.",
     "u":"פחות מ-2 מיליארד — מרוויחה מכל fab expansion ב-TSMC/Intel."},
    {"t":"SITM", "n":"SiTime Corporation", "s":"אוסצילטורים",
     "d":"שבבי תזמון מדויקים — מחליפה קריסטלים קוורץ מסורתיים.",
     "u":"שוק נישה של אוסצילטורים — חברה ב-2.5 מיליארד עם שליטה על 20% מהשוק הגדל."},
    {"t":"AEHR", "n":"Aehr Test Systems",  "s":"בדיקת שבבים",
     "d":"בודקת שבבי SiC לרכבים חשמליים — ביקוש גדל מאוד.",
     "u":"כ-500 מיליון שווי — פנינה קטנה שנהנית ישירות מהמעבר ל-EV."},
    {"t":"DIOD", "n":"Diodes Inc.",        "s":"רכיבים אנלוגיים",
     "d":"מייצרת רכיבי חצי מוליך דיסקרטיים ולוגיים לתעשייה.",
     "u":"נסחרת ב-1.8 מיליארד — שוק יציב עם ביקוש יציב, לא מסקרן מספיק לתקשורת."},
    # ── AI / Quantum ───────────────────────────────────────────────────────────
    {"t":"IONQ", "n":"IonQ",              "s":"מחשוב קוואנטי",
     "d":"מפתחת מחשבים קוואנטיים מסחריים על בסיס יוני מלכודת.",
     "u":"קוואנטום עדיין ב-hype — אך IonQ היא המובילה המסחרית. מסוכן אך פוטנציאל עצום."},
    {"t":"RGTI", "n":"Rigetti Computing",  "s":"מחשוב קוואנטי",
     "d":"מחשבים קוואנטיים היברידיים קלאסי-קוואנטי.",
     "u":"מניה ספקולטיבית — ניצול חוסר ידע ציבורי על קוואנטום."},
    {"t":"QUBT", "n":"Quantum Computing", "s":"מחשוב קוואנטי",
     "d":"תוכנת אופטימיזציה קוואנטית לבעיות לוגיסטיקה ופיננסים.",
     "u":"ספקולטיבי מאוד — אבל עשוי לזנק עם כל הודעת פריצת דרך קוואנטית."},
    {"t":"SOUN", "n":"SoundHound AI",     "s":"AI קולי",
     "d":"טכנולוגיית זיהוי קול ומסייע AI לרכבים ומסעדות.",
     "u":"לא בכותרות — אבל NVIDIA השקיעה בה. פחות מ-3 מיליארד שווי."},
    {"t":"BBAI", "n":"BigBear.ai",        "s":"AI ביטחוני",
     "d":"AI לניתוח מודיעין ולוגיסטיקה לממשל האמריקאי.",
     "u":"מניה ביטחונית קטנה שנהנית מתקציבי AI ממשלתיים — אינה נסקרת מספיק."},
    # ── Clean Energy ───────────────────────────────────────────────────────────
    {"t":"ENPH", "n":"Enphase Energy",    "s":"אנרגיה סולארית",
     "d":"מהפכי מיקרו — מנהלת כל פאנל סולארי ביתי בנפרד.",
     "u":""},
    {"t":"SEDG", "n":"SolarEdge",         "s":"אנרגיה סולארית",
     "d":"מהפכי חשמל לפאנלים סולאריים — מותקנת במיליוני בתים.",
     "u":"ירדה מאוד מהשיא — מכפיל נמוך היסטורית, שאלה אם זה Bounce."},
    {"t":"ARRY", "n":"Array Technologies","s":"עוקבי שמש",
     "d":"מייצרת מכונות עוקבי שמש לפרויקטים סולאריים גדולים.",
     "u":"כ-2 מיליארד — מרוויחה מביקוש עצום לסולאר מסחרי. לא בכותרות."},
    {"t":"NOVA", "n":"Sunnova Energy",    "s":"שירותי סולאר",
     "d":"מאפשרת לבתים להתקין סולאר ללא עלות ראשונית.",
     "u":"ספקולטיבי — תלוי בסביבת ריבית, אבל לאחר ירידה גדולה עשוי להתאושש."},
    {"t":"SHLS", "n":"Shoals Technologies","s":"תשתית סולאר",
     "d":"מייצרת רכיבי תיל ומחברים לשדות סולאריים גדולים.",
     "u":"כ-1.5 מיליארד — נישה הכרחית בבניית תשתיות סולאר שאף אחד לא מדבר עליה."},
    {"t":"FSLR", "n":"First Solar",       "s":"פאנלים סולאריים",
     "d":"מייצרת פאנלים סולאריים בארה\"ב — מרוויחה מ-IRA.", "u":""},
    {"t":"RUN",  "n":"Sunrun",            "s":"שירותי סולאר",
     "d":"מתקינה סולאר ואחסון אנרגיה לבתים פרטיים בארה\"ב.", "u":""},
    # ── Biotech Growth ─────────────────────────────────────────────────────────
    {"t":"RXRX", "n":"Recursion Pharma",  "s":"AI ביו-טק",
     "d":"משתמשת ב-AI לגילוי תרופות מהר פי 10 מהמסורתי.",
     "u":"כ-4 מיליארד — AI לביו-טק הוא הסגמנט הכי מעניין שאנשים לא מכירים."},
    {"t":"BEAM", "n":"Beam Therapeutics", "s":"עריכת גנום",
     "d":"עריכת גנום מדויקת (Base Editing) לריפוי מחלות גנטיות.",
     "u":"תת-נישה של עריכת גנום — מתקדמת יותר מ-CRISPR בדיוק. שווי נמוך."},
    {"t":"EDIT", "n":"Editas Medicine",   "s":"CRISPR",
     "d":"עריכת גנום CRISPR לטיפול במחלות גנטיות וסרטן.", "u":""},
    {"t":"NTLA", "n":"Intellia Therapeutics","s":"CRISPR",
     "d":"עריכת גנום in-vivo — מרפאת מחלות גנטיות בתוך הגוף.", "u":""},
    {"t":"PACB", "n":"Pacific Biosciences","s":"ריצוף גנום",
     "d":"ריצוף DNA ארוך-קריאה — מדויק יותר משיטת Illumina.",
     "u":"מתחת 700 מיליון שווי — הטכנולוגיה שלה עדיפה אך Illumina שולטת בשוק."},
    # ── Fintech ────────────────────────────────────────────────────────────────
    {"t":"AFRM", "n":"Affirm Holdings",   "s":"BNPL / פינטק",
     "d":"רכישה עכשיו תשלום אחר כך (BNPL) — שותפת Amazon ו-Shopify.",
     "u":""},
    {"t":"UPST", "n":"Upstart Holdings",  "s":"AI אשראי",
     "d":"AI להחלטות הלוואות — מחשבת סיכון טוב ממודלים מסורתיים.",
     "u":"ירדה 90% מהשיא — אם הריבית תרד, עשויה לשוב לגדולה."},
    {"t":"RELY", "n":"Remitly Global",    "s":"העברות כסף",
     "d":"שליחת כסף בינלאומית לשווקים מתפתחים — זולה ומהירה.",
     "u":"כ-5 מיליארד — שוק העברות כסף ב-700 מיליארד דולר, Remitly כובשת נתחים."},
    {"t":"BILL", "n":"Bill.com",          "s":"B2B פינטק",
     "d":"אוטומציית חשבונות לעסקים קטנים ובינוניים.",
     "u":""},
    {"t":"FLYW", "n":"Flywire",           "s":"פינטק גלובלי",
     "d":"פתרונות תשלום למוסדות חינוך ובריאות ברחבי העולם.",
     "u":"כ-2 מיליארד — נישה ייחודית של תשלומים מורכבים שאף אחד לא עוסק בה."},
    {"t":"NCNO", "n":"nCino",             "s":"פינטק בנקאות",
     "d":"ענן לבנקים — מייעלת הנפקת הלוואות ופתיחת חשבונות.",
     "u":"כ-4 מיליארד — פינטק B2B לבנקים, פחות מוכרת מ-Stripe/Square."},
    # ── Space / Defense ────────────────────────────────────────────────────────
    {"t":"RKLB", "n":"Rocket Lab",        "s":"חלל מסחרי",
     "d":"משגרת לוויינים קטנים — תחרות ל-SpaceX בשוק ה-small sat.",
     "u":"כ-8 מיליארד — SpaceX פרטית, RKLB ציבורית. נהנית מביקוש עצום ללוויינים."},
    {"t":"ASTS", "n":"AST SpaceMobile",   "s":"אינטרנט לוויני",
     "d":"אינטרנט סלולרי ישירות ללוויין — ללא Starlink.",
     "u":"ספקולטיבי — אבל AT&T ו-Verizon השקיעו. פוטנציאל ענק אם יצליח."},
    {"t":"ACHR", "n":"Archer Aviation",   "s":"eVTOL / תחבורה אוויר",
     "d":"מטוסי מונית חשמליים — סטארטאפ eVTOL בדרך לאישור FAA.",
     "u":"ספקולטיבי מאוד — אבל United Airlines הזמינה 200 מטוסים."},
    {"t":"JOBY", "n":"Joby Aviation",     "s":"eVTOL",
     "d":"מונית אווירית חשמלית שקטה — אישור FAA צפוי בשנים הקרובות.",
     "u":"ספקולטיבי — Toyota השקיעה. שוק מונית אווירית ב-2030+ הוא ענק."},
    {"t":"LUNR", "n":"Intuitive Machines","s":"חלל / ירח",
     "d":"החברה הפרטית הראשונה שנחתה על הירח — חוזים עם NASA.",
     "u":"כ-2 מיליארד — תוכנית Artemis של NASA מייצרת ביקוש, כמעט לא מכוסה."},
    {"t":"KTOS", "n":"Kratos Defense",    "s":"ביטחון / Drones",
     "d":"מפתחת כלי טיס בלתי מאוישים וטילים לצבא האמריקאי.",
     "u":"כ-3 מיליארד — תקציבי ביטחון גדולים, מוכרת ביחס לגודל שלה."},
    {"t":"AVAV", "n":"AeroVironment",     "s":"Drones ביטחוניים",
     "d":"Drones קרביים וטקטיים — מרוויחה מעלייה בביקוש מלחמתי.",
     "u":""},
]

# ══════════════════════════════════════════════════════════════════════════════
# AUTH SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
def _hash_pw(pw: str) -> bytes:
    import bcrypt
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())

def _check_pw(pw: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def _try_login(username: str, password: str) -> bool:
    try:
        users = st.secrets.get("users", {})
        if username in users:
            return _check_pw(password, users[username]["password_hash"])
    except Exception:
        pass
    return False

def _show_login() -> bool:
    """Renders login screen. Returns True when authenticated."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(f"""<style>
    #MainMenu,footer,header{{visibility:hidden;}}
    .stDeployButton{{display:none;}}
    html,body,.stApp{{background:{BG}!important;}}
    .block-container{{padding:0!important;max-width:100%!important;}}
    .stButton>button{{
        background:{CYAN}22!important;border:1px solid {CYAN}!important;
        color:{CYAN}!important;font-family:'Heebo',sans-serif!important;
        font-size:1rem!important;font-weight:700!important;
        border-radius:6px!important;padding:10px!important;
    }}
    .stTextInput>div>div>input{{
        background:{SURF2}!important;color:{TX}!important;
        border:1px solid {BDR}!important;border-radius:6px!important;
        font-family:'Heebo',sans-serif!important;font-size:.95rem!important;
        text-align:right!important;direction:rtl!important;
    }}
    label{{color:{TX2}!important;font-size:.82rem!important;direction:rtl!important;}}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700;900&display=swap"
          rel="stylesheet">""", unsafe_allow_html=True)

    _, c, _ = st.columns([1, 1.4, 1])
    with c:
        st.markdown(f"""
        <div style="text-align:center;padding:70px 0 36px;direction:rtl;">
            <div style="font-size:3.8rem;margin-bottom:10px;">📈</div>
            <div style="font-size:2rem;font-weight:900;color:{CYAN};
                        font-family:'Heebo',sans-serif;letter-spacing:-.02em;">
                מנתח מניות
            </div>
            <div style="color:{TX2};font-size:.88rem;margin-top:6px;">
                מערכת ניתוח מניות אישית
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style="background:{SURF};border:1px solid {BDR};
            border-radius:8px;padding:28px 32px;direction:rtl;">
            <div style="font-size:1rem;font-weight:700;color:{TX};
                        margin-bottom:20px;text-align:center;">
                🔐 כניסה למערכת
            </div>""", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("שם משתמש", placeholder="שם משתמש")
            password = st.text_input("סיסמה", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("כניסה  →", use_container_width=True,
                                              type="primary")
            if submitted:
                if _try_login(username.strip(), password):
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"]  = username.strip()
                    st.session_state["user_name"] = (
                        st.secrets.get("users", {})
                        .get(username.strip(), {}).get("name", username.strip()))
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים ❌")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="text-align:center;color:{TX3};
            font-size:.72rem;margin-top:16px;">
            🔒 גישה מאובטחת · הנתונים שלך פרטיים
        </div>""", unsafe_allow_html=True)

    return False

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="מנתח מניות",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset & Base ──────────────────────────────────────────────────────── */
#MainMenu,footer,header,.stDeployButton{{visibility:hidden;display:none;}}
html,body,.stApp{{
    background:{BG}!important;
    font-family:'Heebo',sans-serif!important;
    color:{TX}!important;
}}
.block-container{{
    padding:1.2rem 1.8rem!important;
    max-width:100%!important;
}}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar{{width:3px;height:3px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:{BDR2};border-radius:2px;}}
::-webkit-scrollbar-thumb:hover{{background:{CYAN}66;}}

/* ── Buttons ───────────────────────────────────────────────────────────── */
.stButton>button{{
    border-radius:6px!important;
    font-family:'Heebo',sans-serif!important;
    font-weight:600!important;
    font-size:.82rem!important;
    padding:.36rem .8rem!important;
    transition:border-color .15s,color .15s!important;
    border:1px solid {BDR2}!important;
    background:{SURF}!important;
    color:{TX2}!important;
    letter-spacing:.01em!important;
    box-shadow:none!important;
}}
.stButton>button:hover{{
    border-color:{CYAN}!important;
    color:{CYAN}!important;
    background:{SURF}!important;
    box-shadow:none!important;
}}
button[kind="primary"]{{
    background:{SURF2}!important;
    border:1px solid {CYAN}88!important;
    color:{CYAN}!important;
    box-shadow:none!important;
}}
button[kind="primary"]:hover{{
    border-color:{CYAN}!important;
    color:{TX}!important;
    background:{SURF2}!important;
}}

/* ── Inputs ────────────────────────────────────────────────────────────── */
.stTextInput>div>div>input,
.stNumberInput>div>div>input{{
    background:{SURF}!important;
    color:{TX}!important;
    border:1px solid {BDR2}!important;
    border-radius:6px!important;
    font-family:'Heebo',sans-serif!important;
    font-size:.88rem!important;
    transition:border-color .15s!important;
    direction:rtl!important;
    text-align:right!important;
    padding:.45rem .85rem!important;
}}
.stTextInput>div>div>input:focus,
.stNumberInput>div>div>input:focus{{
    border-color:{CYAN}!important;
    box-shadow:none!important;
    outline:none!important;
}}
.stSelectbox>div>div{{
    background:{SURF}!important;
    border:1px solid {BDR2}!important;
    border-radius:6px!important;
    color:{TX}!important;
    font-family:'Heebo',sans-serif!important;
}}
.stSelectbox>div>div:hover{{border-color:{CYAN}66!important;}}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{{
    background:transparent!important;
    border-radius:0!important;
    padding:0!important;
    gap:0!important;
    border:none!important;
    border-bottom:1px solid {BDR2}!important;
}}
.stTabs [data-baseweb="tab"]{{
    border-radius:0!important;
    color:{TX2}!important;
    font-family:'Heebo',sans-serif!important;
    font-weight:600!important;
    font-size:.85rem!important;
    padding:.45rem 1.2rem!important;
    transition:color .15s!important;
    border:none!important;
    background:transparent!important;
    border-bottom:2px solid transparent!important;
    margin-bottom:-1px!important;
}}
.stTabs [aria-selected="true"]{{
    background:transparent!important;
    color:{CYAN}!important;
    border-bottom:2px solid {CYAN}!important;
    box-shadow:none!important;
}}
.stTabs [data-baseweb="tab-border"]{{display:none!important;}}
.stTabs [data-baseweb="tab-highlight"]{{display:none!important;}}

/* ── Expander ──────────────────────────────────────────────────────────── */
.streamlit-expanderHeader{{
    background:{SURF}!important;
    border:1px solid {BDR2}!important;
    border-radius:6px!important;
    color:{TX2}!important;
    font-family:'Heebo',sans-serif!important;
    font-weight:600!important;
    font-size:.85rem!important;
    padding:.5rem 1rem!important;
    transition:border-color .15s,color .15s!important;
}}
.streamlit-expanderHeader:hover{{
    border-color:{CYAN}55!important;
    color:{TX}!important;
}}
.streamlit-expanderContent{{
    border:1px solid {BDR2}!important;
    border-top:none!important;
    border-radius:0 0 6px 6px!important;
    background:{SURF}!important;
    padding:1rem!important;
}}

/* ── Metrics ───────────────────────────────────────────────────────────── */
[data-testid="metric-container"]{{
    background:{SURF}!important;
    border:1px solid {BDR2}!important;
    border-radius:6px!important;
    padding:.85rem 1rem!important;
    box-shadow:none!important;
}}
[data-testid="metric-container"]:hover{{
    border-color:{CYAN}55!important;
}}

/* ── Dataframe ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"]{{
    border:1px solid {BDR2}!important;
    border-radius:6px!important;
    overflow:hidden!important;
}}

/* ── File uploader ─────────────────────────────────────────────────────── */
[data-testid="stFileUploader"]{{
    background:{SURF}!important;
    border:1px dashed {BDR2}!important;
    border-radius:6px!important;
}}
[data-testid="stFileUploader"]:hover{{border-color:{CYAN}55!important;}}

/* ── Spinner ───────────────────────────────────────────────────────────── */
div[data-testid="stSpinner"]>div{{border-top-color:{CYAN}!important;}}

/* ── Labels & Text ─────────────────────────────────────────────────────── */
label{{
    color:{TX2}!important;
    font-family:'Heebo',sans-serif!important;
    font-size:.82rem!important;
    font-weight:500!important;
}}
.section-head{{
    font-size:1.4rem;
    font-weight:800;
    color:{TX};
    margin-bottom:2px;
    letter-spacing:-.02em;
    border-bottom:2px solid {CYAN};
    padding-bottom:6px;
    display:inline-block;
}}

/* ── Alert / Info boxes ────────────────────────────────────────────────── */
.stAlert{{
    border-radius:6px!important;
    border:1px solid {BDR2}!important;
    font-family:'Heebo',sans-serif!important;
}}

/* ── Plotly tooltips ───────────────────────────────────────────────────── */
.js-plotly-plot .plotly .modebar{{
    background:transparent!important;
}}

/* ── Slider ────────────────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"]{{
    padding:0!important;
}}
[data-testid="stSlider"] [data-baseweb="thumb"]{{
    background:{CYAN}!important;
    border:2px solid {BG}!important;
    box-shadow:none!important;
}}
[data-testid="stSlider"] [data-baseweb="track-fill"]{{
    background:{CYAN}!important;
}}

/* ── Progress bar ──────────────────────────────────────────────────────── */
.stProgress>div>div>div>div{{background:{CYAN}!important;}}

/* ── Checkbox ──────────────────────────────────────────────────────────── */
.stCheckbox label{{color:{TX}!important;font-size:.88rem!important;}}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_DEFS = {
    "page":            "home",
    "home_selected":   None,
    "pf_prefill":      "",
    "search_ticker":   "",
    "mobile_mode":     False,
    "compare_tickers": ["NVDA", "AAPL"],
    # Autonomous backtest simulator
    "demo2_state":       "setup",
    "demo2_budget":      10000.0,
    "demo2_target_pct":  50.0,
    "demo2_start_year":  2018,
    "demo2_end_year":    2023,
    "demo2_tickers":     ["NVDA", "AAPL", "AMD", "MSFT"],
    "demo2_risk":        "מאוזן",
    "demo2_speed":       "רגיל",
    "demo2_results":     None,
    "demo2_frame":       0,
    "demo2_strategy":    "📊 RSI קלאסי",
    "demo2_scenario":    None,
    # Screener
    "sc_results":        None,
    "sc_running":        False,
}
for _k, _v in _DEFS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ══════════════════════════════════════════════════════════════════════════════
# FILE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM — state, notifications, worker threads
# ══════════════════════════════════════════════════════════════════════════════
AGENT_STATE_FILE  = os.path.join(DATA_DIR, "agent_state.json")
NOTIFICATIONS_FILE= os.path.join(DATA_DIR, "notifications.json")
AGENT_LOGS_FILE   = os.path.join(DATA_DIR, "agent_logs.json")

_agent_threads: dict = {}
_agent_lock = threading.Lock()

def _load_agent_state() -> dict:
    try:
        with open(AGENT_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "monitor": {"enabled": True,  "status": "ממתין", "last_run": None, "interval": 30},
            "scanner": {"enabled": True,  "status": "ממתין", "last_run": None, "interval": 60},
            "news":    {"enabled": True,  "status": "ממתין", "last_run": None, "interval": 15},
        }

def _save_agent_state(state: dict):
    with _agent_lock:
        try:
            with open(AGENT_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def _load_notifications() -> list:
    try:
        with open(NOTIFICATIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _unread_count() -> int:
    return sum(1 for n in _load_notifications() if not n.get("read", True))

def _mark_all_read():
    with _agent_lock:
        notifs = _load_notifications()
        for n in notifs:
            n["read"] = True
        try:
            with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(notifs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def _clear_notifications():
    with _agent_lock:
        try:
            with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass

def _add_notification(agent: str, title: str, body: str, level: str = "info",
                      key: str = "", extra=None):
    if key:
        cutoff = time.time() - 6 * 3600
        for n in _load_notifications():
            if n.get("key") == key and n.get("ts", 0) > cutoff:
                return
    with _agent_lock:
        notifs = _load_notifications()
        entry = {
            "ts":    time.time(),
            "agent": agent,
            "title": title,
            "body":  body,
            "level": level,
            "key":   key,
            "time":  datetime.now().strftime("%d/%m/%Y %H:%M"),
            "read":  False,
        }
        if extra:
            entry.update(extra)
        notifs.insert(0, entry)
        try:
            with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(notifs[:200], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def _add_log(agent: str, message: str):
    with _agent_lock:
        try:
            with open(AGENT_LOGS_FILE, encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
        logs.insert(0, {
            "time":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "agent":   agent,
            "message": message,
        })
        try:
            with open(AGENT_LOGS_FILE, "w", encoding="utf-8") as f:
                json.dump(logs[:500], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def _should_notify(key: str, hours: float = 6) -> bool:
    cutoff = time.time() - hours * 3600
    for n in _load_notifications():
        if n.get("key") == key and n.get("ts", 0) > cutoff:
            return False
    return True

# ── Direct (non-cached) data fetch for agent threads ─────────────────────────

def _agent_quote(sym: str) -> dict:
    try:
        hist = yf.Ticker(sym).history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 15:
            return {}
        c      = hist["Close"].dropna()
        price  = float(c.iloc[-1])
        prev   = float(c.iloc[-2])
        chg    = (price - prev) / prev * 100
        d  = c.diff()
        g  = d.clip(lower=0).rolling(14).mean()
        lo = (-d.clip(upper=0)).rolling(14).mean()
        rsi    = float(100 - 100 / (1 + g / lo).iloc[-1])
        ma50_s = c.rolling(50).mean()
        ma50   = float(ma50_s.iloc[-1])  if not pd.isna(ma50_s.iloc[-1])  else None
        ma50_p = float(ma50_s.iloc[-2])  if (ma50 and not pd.isna(ma50_s.iloc[-2])) else None
        return {"price": price, "chg": chg, "rsi": rsi,
                "prev": prev, "ma50": ma50, "ma50_prev": ma50_p}
    except Exception:
        return {}

# ── Agent worker functions ────────────────────────────────────────────────────

def _run_monitor():
    portfolio = load_json(PF_FILE)
    watchlist = load_json(WL_FILE) or []
    pf_syms   = [h["sym"] for h in portfolio]
    all_syms  = list(dict.fromkeys(pf_syms + watchlist))
    _add_log("monitor", f"מתחיל סריקה של {len(all_syms)} מניות")
    alerts = 0
    for sym in all_syms:
        q = _agent_quote(sym)
        if not q:
            continue
        chg, rsi, price = q["chg"], q["rsi"], q["price"]
        prev, ma50, ma50_p = q["prev"], q.get("ma50"), q.get("ma50_prev")
        today = datetime.now().strftime("%Y%m%d")
        hour  = datetime.now().strftime("%Y%m%d_%H")
        if chg <= -3:
            k = f"mon_drop_{sym}_{today}"
            if _should_notify(k):
                _add_notification("monitor",
                    f"📉 ירידה חדה: {sym}",
                    f"המניה ירדה {chg:.1f}% היום — מחיר ${price:,.2f}", "danger", k)
                alerts += 1
        if rsi >= 70:
            k = f"mon_rsi_hi_{sym}_{hour}"
            if _should_notify(k, 4):
                _add_notification("monitor",
                    f"📈 קנייה יתר: {sym}",
                    f"RSI = {rsi:.0f} — שקול מכירה", "warning", k)
                alerts += 1
        elif rsi <= 30:
            k = f"mon_rsi_lo_{sym}_{hour}"
            if _should_notify(k, 4):
                _add_notification("monitor",
                    f"📉 מכירת יתר: {sym}",
                    f"RSI = {rsi:.0f} — הזדמנות קנייה אפשרית", "info", k)
                alerts += 1
        if ma50 and ma50_p:
            if prev < ma50_p and price > ma50:
                k = f"mon_cross_up_{sym}_{today}"
                if _should_notify(k):
                    _add_notification("monitor",
                        f"🟢 פריצה מעל MA50: {sym}",
                        f"המחיר חצה מעל ממוצע 50 יום (${ma50:,.2f})", "info", k)
                    alerts += 1
            elif prev > ma50_p and price < ma50:
                k = f"mon_cross_dn_{sym}_{today}"
                if _should_notify(k):
                    _add_notification("monitor",
                        f"🔴 שבירה מתחת ל-MA50: {sym}",
                        f"המחיר ירד מתחת לממוצע 50 יום (${ma50:,.2f})", "warning", k)
                    alerts += 1
    _add_log("monitor", f"סריקה הסתיימה — {alerts} התראות חדשות")

def _deep_scan_stock(sym: str, meta: dict):
    """Full technical analysis for one stock. Returns signal dict or None."""
    try:
        hist = yf.Ticker(sym).history(period="1y", interval="1d")
        if hist.empty or len(hist) < 60:
            return None
        close  = hist["Close"].dropna()
        volume = hist["Volume"].dropna()
        price  = float(close.iloc[-1])
        if price <= 0:
            return None

        # ── RSI(14) ────────────────────────────────────────────────────────────
        d  = close.diff()
        g  = d.clip(lower=0).rolling(14).mean()
        lo = (-d.clip(upper=0)).rolling(14).mean()
        rsi_s = 100 - 100 / (1 + g / lo)
        rsi   = float(rsi_s.iloc[-1])

        # ── MA50 / MA200 ───────────────────────────────────────────────────────
        ma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        # ── 52-week range ──────────────────────────────────────────────────────
        low_52w  = float(close.tail(252).min())
        high_52w = float(close.tail(252).max())

        # ── Volume ─────────────────────────────────────────────────────────────
        vol_avg30 = float(volume.tail(30).mean())
        vol_today = float(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else 0
        vol_ratio = vol_today / vol_avg30 if vol_avg30 > 0 else 1.0

        signals, score, reasons = [], 0, []

        # Signal 1 — Unusual volume spike
        if vol_ratio >= 3.0:
            signals.append("volume_spike")
            score += 3
            reasons.append(f"נפח מסחר חריג פי {vol_ratio:.1f} מהממוצע")
        elif vol_ratio >= 2.0:
            signals.append("volume_elevated")
            score += 2
            reasons.append(f"נפח מסחר גבוה פי {vol_ratio:.1f} מהממוצע")

        # Signal 2 — RSI recovery from extreme oversold
        rsi_5d    = rsi_s.tail(6).values
        min_rsi5  = float(min(rsi_5d[:-1]))
        rsi_trend = float(rsi_s.iloc[-1]) - float(rsi_s.iloc[-6]) if len(rsi_s) >= 6 else 0
        if min_rsi5 < 25 and rsi > min_rsi5 + 5 and rsi < 48:
            signals.append("rsi_recovery")
            score += 4
            reasons.append(f"RSI מתאושש מ-{min_rsi5:.0f} ← כעת {rsi:.0f}")
        elif rsi < 30:
            signals.append("rsi_oversold")
            score += 2
            reasons.append(f"RSI במכירת יתר קיצונית ({rsi:.0f})")

        # Signal 3 — Resistance breakout after consolidation
        if len(close) >= 70:
            resistance = float(close.iloc[-70:-5].max())
            rng_30d    = (float(close.tail(30).max()) - float(close.tail(30).min())) / price
            if price >= resistance * 0.97 and rng_30d < 0.18:
                signals.append("breakout")
                score += 3
                reasons.append(f"פריצת התנגדות של {resistance:.2f}$ לאחר קונסולידציה")

        # Signal 4 — Near 52-week low with improving momentum
        pct_from_low = (price - low_52w) / low_52w if low_52w > 0 else 1
        if pct_from_low < 0.15 and rsi_trend > 3 and vol_ratio > 1.2:
            signals.append("near_52w_low")
            score += 3
            reasons.append(f"קרוב לשפל שנתי ({pct_from_low*100:.0f}% מעל) עם מומנטום עולה")

        # Signal 5 — Quiet institutional accumulation
        if len(close) >= 22:
            rng_20d   = (float(close.tail(20).max()) - float(close.tail(20).min())) / price
            vol_trend = float(volume.tail(5).mean()) / float(volume.tail(20).mean())
            if rng_20d < 0.10 and vol_trend > 1.25 and 44 <= rsi <= 63:
                signals.append("accumulation")
                score += 3
                reasons.append("צבירה מוסדית שקטה — טווח מצומצם עם עלייה בנפח")

        # MA bonuses
        if ma50  and price > ma50:  score += 1
        if ma200 and price > ma200: score += 1
        if ma50  and price > ma50 and rsi_trend > 0: score += 1

        if score < 3 or not signals:
            return None

        # ── Confidence ────────────────────────────────────────────────────────
        if score >= 8:
            confidence, conf_icon, level = "גבוה",       "🔥", "warning"
        elif score >= 5:
            confidence, conf_icon, level = "בינוני",     "⚡", "info"
        else:
            confidence, conf_icon, level = "שווה מעקב", "👀", "info"

        # ── Risk ──────────────────────────────────────────────────────────────
        pct_from_high = (high_52w - price) / high_52w if high_52w > 0 else 0
        if pct_from_high > 0.45:  risk = "גבוה"
        elif pct_from_high > 0.22: risk = "בינוני"
        else:                      risk = "נמוך"

        return {
            "sym":          sym,
            "name":         meta.get("n", sym),
            "sector":       meta.get("s", ""),
            "desc":         meta.get("d", ""),
            "why_unknown":  meta.get("u", ""),
            "price":        price,
            "rsi":          rsi,
            "vol_ratio":    vol_ratio,
            "score":        score,
            "signals":      signals,
            "primary":      reasons[0] if reasons else "",
            "all_reasons":  " · ".join(reasons),
            "confidence":   confidence,
            "conf_icon":    conf_icon,
            "risk":         risk,
            "entry":        round(price, 2),
            "target1":      round(price * 1.12, 2),
            "target2":      round(price * 1.25, 2),
            "stop":         round(price * 0.93, 2),
            "level":        level,
        }
    except Exception:
        return None


def _run_deep_scanner():
    """Scans 100+ stocks autonomously every 30 min."""
    state         = _load_agent_state()
    min_conf_pref = state.get("scanner_min_confidence", "שווה מעקב")
    conf_rank     = {"שווה מעקב": 1, "בינוני": 2, "גבוה": 3}
    min_rank      = conf_rank.get(min_conf_pref, 1)

    universe = DEEP_SCAN_UNIVERSE.copy()
    # Also add HOT stocks not already in universe
    uni_tickers = {m["t"] for m in universe}
    for s in HOT:
        if s["t"] not in uni_tickers:
            universe.append({"t": s["t"], "n": s["n"], "s": s["c"], "d": s["w"], "u": ""})

    _add_log("scanner", f"🔍 מתחיל סריקה עמוקה של {len(universe)} מניות")
    found = []

    # Parallel batches to avoid rate-limit
    batch_size = 10
    for i in range(0, len(universe), batch_size):
        batch = universe[i:i + batch_size]
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as ex:
                futures = {ex.submit(_deep_scan_stock, m["t"], m): m for m in batch}
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        r = fut.result()
                        if r:
                            found.append(r)
                    except Exception:
                        pass
        except RuntimeError:
            return  # interpreter shutting down during Streamlit reload
        time.sleep(1.5)

    found.sort(key=lambda x: x["score"], reverse=True)
    _add_log("scanner", f"סריקה הסתיימה — {len(found)} מניות עם אות | שולח התראות")

    notified = 0
    date_key = datetime.now().strftime("%Y%m%d")
    for stock in found[:12]:
        if conf_rank.get(stock["confidence"], 1) < min_rank:
            continue
        sym = stock["sym"]
        k   = f"deep_{sym}_{date_key}"
        if not _should_notify(k, 8):
            continue

        title = (f"{stock['conf_icon']} {sym} — {stock['primary'][:65]}")
        body  = "\n".join(filter(None, [
            f"🏢 {stock['desc']}" if stock.get("desc") else None,
            f"📊 ביטחון: {stock['conf_icon']} {stock['confidence']} (ציון {stock['score']})",
            f"⚠️ סיכון: {stock['risk']}",
            f"🎯 כניסה: ${stock['entry']:.2f}  |  יעד 1: ${stock['target1']:.2f}  |  יעד 2: ${stock['target2']:.2f}",
            f"🛑 סטופ הפסד: ${stock['stop']:.2f}",
            f"🔍 {stock['why_unknown']}" if stock.get("why_unknown") else None,
        ]))

        _add_notification("scanner", title, body, stock["level"], k, extra={
            "sym":         sym,
            "confidence":  stock["confidence"],
            "conf_icon":   stock["conf_icon"],
            "risk":        stock["risk"],
            "entry":       stock["entry"],
            "target1":     stock["target1"],
            "target2":     stock["target2"],
            "stop":        stock["stop"],
            "signals":     stock["signals"],
            "all_reasons": stock["all_reasons"],
            "desc":        stock.get("desc", ""),
            "why_unknown": stock.get("why_unknown", ""),
            "sector":      stock.get("sector", ""),
            "vol_ratio":   round(stock.get("vol_ratio", 1), 1),
            "rsi":         round(stock.get("rsi", 50), 1),
            "score":       stock["score"],
        })
        notified += 1

    if not found:
        _add_log("scanner", "לא נמצאו אותות בסריקה זו")

def _run_news_agent():
    portfolio = load_json(PF_FILE)
    watchlist = load_json(WL_FILE) or []
    pf_syms   = [h["sym"] for h in portfolio]
    all_syms  = list(dict.fromkeys(pf_syms + watchlist))
    if not all_syms:
        _add_log("news", "אין מניות בתיק / מעקב"); return
    today_ts = int(datetime.combine(datetime.now().date(), datetime.min.time()).timestamp())
    flagged = 0
    _add_log("news", f"מתחיל ניתוח חדשות עבור {len(all_syms)} מניות")
    for sym in all_syms:
        try:
            items = yf.Ticker(sym).news or []
            today = [it for it in items if it.get("providerPublishTime", 0) >= today_ts]
            neg = sum(1 for it in today if _sentiment(it.get("title",""))[0] == "🔴")
            pos = sum(1 for it in today if _sentiment(it.get("title",""))[0] == "🟢")
            if neg >= 3:
                k = f"news_neg3_{sym}_{datetime.now().strftime('%Y%m%d')}"
                if _should_notify(k):
                    _add_notification("news",
                        f"⚠️ {sym} — {neg} חדשות שליליות היום",
                        f"{neg} שליליות · {pos} חיוביות", "danger", k)
                    flagged += 1
            for it in today[:1]:
                title = it.get("title","")
                si, _, _ = _sentiment(title)
                if si == "🔴":
                    k = f"news_item_{sym}_{abs(hash(title)) % 99999}"
                    if _should_notify(k, 12):
                        _add_notification("news",
                            f"📰 {sym}: {title[:80]}",
                            f"מ-{it.get('publisher','')}",
                            "warning", k)
        except Exception:
            pass
    _add_log("news", f"ניתוח חדשות הסתיים — {flagged} מניות מסומנות")

# ── Thread lifecycle ──────────────────────────────────────────────────────────

def _agent_loop(name: str, fn, interval_min: int):
    while True:
        state = _load_agent_state()
        if state.get(name, {}).get("enabled", True):
            state[name]["status"]   = "פעיל"
            state[name]["last_run"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            _save_agent_state(state)
            try:
                fn()
                state = _load_agent_state()
                state[name]["status"] = "ממתין"
                _save_agent_state(state)
            except Exception as exc:
                state = _load_agent_state()
                state[name]["status"] = "שגיאה"
                _save_agent_state(state)
                _add_log(name, f"שגיאה: {str(exc)[:120]}")
        time.sleep(interval_min * 60)

# ── Telegram helper ───────────────────────────────────────────────────────────
def _telegram_cfg() -> dict:
    try:
        if os.path.exists(TELEGRAM_FILE):
            return load_json(TELEGRAM_FILE)
    except Exception:
        pass
    return {}

def _send_telegram(message: str):
    cfg = _telegram_cfg()
    token   = cfg.get("token", "")
    chat_id = cfg.get("chat_id", "")
    if not token or not chat_id:
        return
    try:
        import urllib.request
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode(
            {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass

# ── Guru Monitor agent ────────────────────────────────────────────────────────
def _run_guru_monitor():
    seen_list = load_json(GURU_SEEN_FILE) if os.path.exists(GURU_SEEN_FILE) else []
    seen      = set(seen_list)
    new_seen  = set(seen)
    new_total = 0

    for guru in GURUS:
        try:
            rss_url = (
                f"https://news.google.com/rss/search"
                f"?q={urllib.parse.quote(guru['q'])}&hl=iw&gl=IL&ceid=IL:iw"
            )
            items = _parse_rss(rss_url, guru["name"], max_items=5)
            for item in items:
                uid = (item.get("link") or item.get("title") or "")[:100]
                if uid in seen:
                    continue
                new_seen.add(uid)
                title = item.get("title", "")
                if not title:
                    continue
                link = item.get("link", "")
                _add_notification(
                    "guru",
                    f"{guru['emoji']} {guru['name']}",
                    title, "info",
                    f"guru_{hash(uid) & 0xFFFFFF}",
                )
                _link_tag = f'<a href="{link}">קרא עוד</a>' if link else ""
                _send_telegram(
                    f"{guru['emoji']} <b>{guru['name']}</b>\n"
                    f"{title}\n"
                    f"{_link_tag}"
                )
                new_total += 1
        except Exception as e:
            _add_log("guru", f"שגיאה ב-{guru['name']}: {str(e)[:60]}")

    with open(GURU_SEEN_FILE, "w", encoding="utf-8") as f:
        import json as _j
        _j.dump(list(new_seen)[-500:], f)  # keep last 500
    _add_log("guru", f"סריקת גורו הסתיימה — {new_total} חדשות חדשות")


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_13f(cik: str) -> list:
    """Fetch latest 13F-HR holdings from SEC EDGAR. Returns list of holding dicts."""
    try:
        import urllib.request as _ur
        headers = {"User-Agent": "StockAnalyzer itayyohanan91@gmail.com"}

        sub_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        req = _ur.Request(sub_url, headers=headers)
        with _ur.urlopen(req, timeout=10) as r:
            sub = json.load(r)

        recent = sub.get("filings", {}).get("recent", {})
        forms  = recent.get("form", [])
        accs   = recent.get("accessionNumber", [])
        dates  = recent.get("filingDate", [])

        acc_no = date_str = None
        for i, f in enumerate(forms):
            if f in ("13F-HR", "13F-HR/A"):
                acc_no   = accs[i]
                date_str = dates[i]
                break
        if not acc_no:
            return []

        cik_int  = int(cik)
        acc_path = acc_no.replace("-", "")
        idx_url  = (f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_int}/{acc_path}/{acc_no}-index.json")
        req2 = _ur.Request(idx_url, headers=headers)
        with _ur.urlopen(req2, timeout=10) as r2:
            idx = json.load(r2)

        xml_file = next(
            (d["name"] for d in idx.get("directory", {}).get("item", [])
             if d["name"].endswith(".xml") and "primary_doc" not in d["name"].lower()
             and "infotable" in d["name"].lower()),
            None
        )
        if not xml_file:
            xml_file = next(
                (d["name"] for d in idx.get("directory", {}).get("item", [])
                 if d["name"].endswith(".xml") and d["name"] != "primary_doc.xml"),
                None
            )
        if not xml_file:
            return []

        xml_url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{cik_int}/{acc_path}/{xml_file}")
        req3 = _ur.Request(xml_url, headers=headers)
        with _ur.urlopen(req3, timeout=15) as r3:
            xml_data = r3.read()

        import xml.etree.ElementTree as ET
        ns = {"ns": "http://www.sec.gov/cgi-bin/browse-edgar"}
        root = ET.fromstring(xml_data)

        holdings = []
        for info in root.findall(".//{*}infoTable"):
            name  = (info.findtext("{*}nameOfIssuer") or
                     info.findtext("nameOfIssuer") or "").strip()
            val   = (info.findtext("{*}value") or
                     info.findtext("value") or "0").strip().replace(",","")
            shs   = (info.findtext(".//{*}sshPrnamt") or
                     info.findtext(".//sshPrnamt") or "0").strip().replace(",","")
            cls   = (info.findtext("{*}titleOfClass") or
                     info.findtext("titleOfClass") or "").strip()
            try:    val_k = int(val)
            except: val_k = 0
            try:    shares = int(shs)
            except: shares = 0
            if name and val_k > 0:
                holdings.append({"name": name, "value_k": val_k,
                                  "shares": shares, "cls": cls,
                                  "date": date_str})

        holdings.sort(key=lambda x: x["value_k"], reverse=True)
        return holdings[:30]
    except Exception:
        return []


def _ensure_agents():
    """Restart any dead agent thread. Called on every page render."""
    state = _load_agent_state()
    scanner_interval = int(state.get("scanner_interval", 30))
    defs = [
        ("monitor", _run_monitor,       30),
        ("scanner", _run_deep_scanner,  scanner_interval),
        ("news",    _run_news_agent,    15),
        ("guru",    _run_guru_monitor,  15),
    ]
    for name, fn, interval in defs:
        if not state.get(name, {}).get("enabled", True):
            continue
        t = _agent_threads.get(name)
        if t is None or not t.is_alive():
            t = threading.Thread(target=_agent_loop, args=(name, fn, interval),
                                 daemon=True, name=f"agent-{name}")
            t.start()
            _agent_threads[name] = t

# ══════════════════════════════════════════════════════════════════════════════
# MARKET DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60)
def quote(sym: str) -> dict:
    """Returns price, chg (%), rsi, sig, sig_c for a ticker."""
    try:
        hist = yf.Ticker(sym).history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 15:
            return {}
        c = hist["Close"].dropna()
        price   = float(c.iloc[-1])
        prev    = float(c.iloc[-2])
        chg     = (price - prev) / prev * 100
        d = c.diff()
        g = d.clip(lower=0).rolling(14).mean()
        lo = (-d.clip(upper=0)).rolling(14).mean()
        rsi = float(100 - 100 / (1 + g / lo).iloc[-1])
        if   rsi < 35: sig, sig_c = "קנייה",  GRN
        elif rsi > 65: sig, sig_c = "מכירה",  RED
        else:          sig, sig_c = "המתנה",  AMB
        return {"price": price, "chg": chg, "rsi": rsi,
                "sig": sig, "sig_c": sig_c}
    except Exception:
        return {}

@st.cache_data(ttl=30)
def fast_price(sym: str):
    try:
        fi = yf.Ticker(sym).fast_info
        # fast_info is a FastInfo object in yfinance 0.2+, not a dict
        for attr in ("last_price", "lastPrice", "previous_close", "previousClose"):
            val = (fi.get(attr) if hasattr(fi, "get")
                   else getattr(fi, attr, None))
            if val:
                return float(val)
        return None
    except Exception:
        return None

@st.cache_data(ttl=300)
def fetch_history(sym: str, period: str = "6mo"):
    try:
        df = yf.Ticker(sym).history(period=period, interval="1d")
        if df.empty:
            return pd.DataFrame()
        df = df[["Open","High","Low","Close","Volume"]].copy()
        c = df["Close"]
        # MAs
        df["MA20"]  = c.rolling(20).mean()
        df["MA50"]  = c.rolling(50).mean()
        df["MA200"] = c.rolling(200).mean()
        # Bollinger Bands (20, 2σ)
        std20 = c.rolling(20).std()
        df["BB_U"] = df["MA20"] + 2 * std20
        df["BB_L"] = df["MA20"] - 2 * std20
        # RSI(14)
        d  = c.diff()
        g  = d.clip(lower=0).rolling(14).mean()
        lo = (-d.clip(upper=0)).rolling(14).mean()
        df["RSI"] = 100 - 100 / (1 + g / lo)
        # MACD (12,26,9)
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        df["MACD"]   = ema12 - ema26
        df["MACD_S"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_H"] = df["MACD"] - df["MACD_S"]
        # Volume trend
        df["Vol_MA20"] = df["Volume"].rolling(20).mean()
        df["Vol_ratio"] = df["Volume"] / df["Vol_MA20"].replace(0, np.nan)
        # 30-day annualized volatility
        rets = df["Close"].pct_change()
        df["Volatility30"] = rets.rolling(30).std() * (252 ** 0.5) * 100
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_info(sym: str) -> dict:
    try:
        return yf.Ticker(sym).info or {}
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def fetch_calendar(sym: str) -> dict:
    try:
        cal = yf.Ticker(sym).calendar
        if cal is None:
            return {}
        if isinstance(cal, pd.DataFrame) and not cal.empty:
            for col in ["Earnings Date", "Earnings High", "Earnings Low"]:
                if col in cal.columns:
                    val = cal[col].iloc[0]
                    if pd.notna(val):
                        return {"earnings_date": pd.Timestamp(val)}
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if ed:
                return {"earnings_date": pd.Timestamp(ed[0] if isinstance(ed, list) else ed)}
    except Exception:
        pass
    return {}

@st.cache_data(ttl=1800)
def fetch_news(sym: str) -> list:
    try:
        return yf.Ticker(sym).news or []
    except Exception:
        return []

# ── RSS sources + broad yfinance tickers ─────────────────────────────────────
_RSS_SOURCES = [
    ("Yahoo Finance",  "https://finance.yahoo.com/rss/topstories"),
    ("Reuters",        "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC Markets",   "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("MarketWatch",    "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Benzinga",       "https://www.benzinga.com/feed"),
]
_BROAD_TICKERS = [
    "SPY","QQQ","^GSPC","^DJI","^VIX","GLD","USO","BTC-USD",
    "AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL","JPM","V","NFLX",
]

def _parse_rss(url: str, source: str, max_items: int = 20) -> list:
    import urllib.request as _ur, xml.etree.ElementTree as _ET, re as _re
    from email.utils import parsedate_to_datetime as _pdt
    try:
        req = _ur.Request(url, headers={
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 Chrome/120 Safari/537.36"),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        with _ur.urlopen(req, timeout=7) as resp:
            data = resp.read()
        root = _ET.fromstring(data)
        out = []
        for item in root.findall(".//item")[:max_items]:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            desc  = (item.findtext("description") or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            ts = 0
            if pub:
                try: ts = int(_pdt(pub).timestamp())
                except Exception: pass
            desc = _re.sub(r"<[^>]+>", "", desc)[:400]
            if title:
                out.append({"title": title, "link": link or "#",
                            "summary": desc, "providerPublishTime": ts,
                            "publisher": source})
        return out
    except Exception:
        return []

@st.cache_data(ttl=900, show_spinner=False)
def fetch_general_news() -> list:
    """Combines RSS feeds + broad yfinance tickers, deduped, sorted by time."""
    seen, news = set(), []

    # RSS feeds in parallel
    def _fetch_rss(args):
        src, url = args
        return _parse_rss(url, src)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_RSS_SOURCES)) as ex:
        for batch in ex.map(_fetch_rss, [(s, u) for s, u in _RSS_SOURCES]):
            for item in batch:
                t = item.get("title","")
                if t and t not in seen:
                    seen.add(t); news.append(item)

    # yfinance tickers as fallback / supplement
    def _fetch_yf(sym):
        try: return yf.Ticker(sym).news or []
        except: return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_BROAD_TICKERS)) as ex:
        for batch in ex.map(_fetch_yf, _BROAD_TICKERS):
            for item in batch:
                t = item.get("title","")
                if t and t not in seen:
                    seen.add(t); news.append(item)

    news.sort(key=lambda x: x.get("providerPublishTime", 0), reverse=True)
    return news[:30]

@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_overview() -> dict:
    """Returns live price+change for major indices."""
    tickers = {
        "S&P 500":   "^GSPC", "נאסד\"ק": "^IXIC",
        "דאו":       "^DJI",  "VIX":      "^VIX",
        "זהב":       "GC=F",  "נפט":      "CL=F",
        "ביטקוין":   "BTC-USD","דולר/שקל": "ILS=X",
    }
    def _get(args):
        name, sym = args
        try:
            h = yf.Ticker(sym).history(period="2d", interval="1d")
            if len(h) >= 2:
                c = float(h["Close"].iloc[-1])
                p = float(h["Close"].iloc[-2])
                return name, {"price": c, "chg": (c-p)/p*100, "sym": sym}
        except Exception:
            pass
        return name, None

    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for name, data in ex.map(_get, list(tickers.items())):
            if data:
                result[name] = data
    return result

@st.cache_data(ttl=86400, show_spinner=False)
def translate_to_hebrew(text: str) -> str:
    try:
        import urllib.request as _ur, urllib.parse as _up, json as _j
        url = ("https://translate.googleapis.com/translate_a/single"
               f"?client=gtx&sl=en&tl=iw&dt=t&q={_up.quote(text[:500])}")
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=5) as r:
            data = _j.loads(r.read())
            return "".join(p[0] for p in data[0] if p[0])
    except Exception:
        return text

def _time_ago(ts: int) -> str:
    diff = int(time.time()) - int(ts)
    if diff < 60:    return "עכשיו"
    if diff < 3600:  return f"לפני {diff // 60} דקות"
    if diff < 86400: return f"לפני {diff // 3600} שעות"
    return f"לפני {diff // 86400} ימים"

def _sentiment(title: str) -> tuple:
    t = title.lower()
    pos = sum(1 for w in [
        "surge","gain","rise","rally","soar","jump","climb","beat","record",
        "growth","profit","strong","bullish","boost","high","win","exceed",
        "positive","upgrade","outperform","better","robust","launch","expand",
    ] if w in t)
    neg = sum(1 for w in [
        "fall","drop","decline","loss","miss","concern","risk","bear","weak",
        "cut","crash","plunge","sink","tumble","warning","fear","down","below",
        "layoff","fire","downgrade","underperform","recession","tariff",
        "sanction","halt","probe","fine","penalty","slowdown","bankrupt",
    ] if w in t)
    if pos > neg: return "🟢", "חיובי", GRN
    if neg > pos: return "🔴", "שלילי", RED
    return "🟡", "ניטרלי", AMB

def _categorize(title: str) -> tuple:
    """Returns (icon, Hebrew tag, color) or ('','','') if generic."""
    t = title.lower()
    if any(w in t for w in ["ipo","initial public offering","goes public",
                              "debut","listing","direct listing","spac"]):
        return "🚀", "הנפקה (IPO)", AMB
    if any(w in t for w in ["earnings","quarterly","eps","revenue beat",
                              "revenue miss","q1 ","q2 ","q3 ","q4 ","net income"]):
        return "📊", "רווחים", CYAN
    if any(w in t for w in ["fed ","federal reserve","interest rate","inflation",
                              "cpi","gdp","fomc","powell","tariff","trade war","recession"]):
        return "🏦", "מאקרו", PUR
    if any(w in t for w in ["merger","acquisition","takeover","deal","buys ",
                              "acquires","buyout","acquire"]):
        return "🤝", "מיזוג/רכישה", GRN
    if any(w in t for w in ["crypto","bitcoin","ethereum","blockchain","btc","eth"]):
        return "₿", "קריפטו", AMB
    if any(w in t for w in ["oil","opec","crude","natural gas","energy sector"]):
        return "🛢️", "אנרגיה", RED
    if any(w in t for w in ["layoff","job cut","firing","workforce","redundan"]):
        return "👥", "כוח אדם", RED
    return "", "", ""

# ══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS BACKTEST SIMULATOR
# ══════════════════════════════════════════════════════════════════════════════
TRADEABLE = [
    ("AAPL","Apple"),    ("MSFT","Microsoft"),  ("GOOGL","Alphabet"),
    ("AMZN","Amazon"),   ("META","Meta"),        ("TSLA","Tesla"),
    ("NVDA","NVIDIA"),   ("AMD","AMD"),          ("MRVL","Marvell"),
    ("ARM","ARM"),       ("CRWD","CrowdStrike"), ("PLTR","Palantir"),
    ("DDOG","Datadog"),  ("NET","Cloudflare"),   ("AXON","Axon"),
    ("TTD","Trade Desk"),("NFLX","Netflix"),     ("PYPL","PayPal"),
    ("SQ","Block"),      ("SHOP","Shopify"),     ("SNOW","Snowflake"),
    ("INTC","Intel"),    ("CRM","Salesforce"),   ("ADBE","Adobe"),
    ("V","Visa"),        ("MA","Mastercard"),    ("JPM","JPMorgan"),
]

RISK_PROFILES = {
    "שמרני":   {"max_pos": 0.15, "rsi_buy": 28, "rsi_sell": 72, "stop_loss": 0.05},
    "מאוזן":   {"max_pos": 0.25, "rsi_buy": 33, "rsi_sell": 67, "stop_loss": 0.07},
    "אגרסיבי": {"max_pos": 0.40, "rsi_buy": 40, "rsi_sell": 60, "stop_loss": 0.10},
}

ANIM_SPEED = {
    "איטי": (3,   0.09),
    "רגיל": (15,  0.025),
    "מהיר": (80,  0.008),
}

STRATEGY_PROFILES = {
    "📊 RSI קלאסי": {
        "desc": "קנה כש-RSI נמוך (מכירת יתר) ומכור כש-RSI גבוה — אסטרטגיית ניגוד מגמה.",
        "mode": "rsi",
    },
    "🚀 מומנטום": {
        "desc": "עקוב אחר המגמה — קנה כשהמניה שוברת שיאים חדשים ומכור בחולשה.",
        "mode": "momentum",
    },
    "↩️ Mean Reversion": {
        "desc": "קנה כשהמניה רחוקה מאוד מהממוצע ומכור כשהיא חוזרת אליו.",
        "mode": "mean_reversion",
    },
}

MARKET_SCENARIOS = [
    {
        "id": "ai_boom",
        "name": "🤖 בום ה-AI 2023",
        "emoji": "🚀",
        "story": "NVDA זינקה 240%, AMD 127% — שנת הבינה המלאכותית הגדולה.",
        "detail": "האם האסטרטגיה שלך הייתה תופסת את הרכבת?",
        "years": (2023, 2024),
        "tickers": ["NVDA","AMD","ARM","MRVL","PLTR"],
        "risk": "אגרסיבי",
        "strategy": "🚀 מומנטום",
        "color": "#00b4d8",
    },
    {
        "id": "bear_2022",
        "name": "📉 שוק הדובים 2022",
        "emoji": "💥",
        "story": "הריבית עלתה בחדות — הטק קרס 50-80% תוך שנה.",
        "detail": "האם ה-AI היה מציל את התיק?",
        "years": (2022, 2023),
        "tickers": ["NVDA","AMD","TSLA","SHOP","SNOW"],
        "risk": "שמרני",
        "strategy": "↩️ Mean Reversion",
        "color": "#ef4444",
    },
    {
        "id": "covid",
        "name": "🦠 קריסה והתאוששות קוביד 2020",
        "emoji": "📈",
        "story": "קריסה של 35% תוך 5 שבועות ואז זינוק של 100%+ — הכי דרמטי בהיסטוריה.",
        "detail": "מה ה-AI היה עושה בזמן הפאניקה?",
        "years": (2020, 2021),
        "tickers": ["NVDA","AMZN","SHOP","TSLA","PYPL"],
        "risk": "מאוזן",
        "strategy": "↩️ Mean Reversion",
        "color": "#f59e0b",
    },
    {
        "id": "cloud_boom",
        "name": "☁️ בום הענן 2020-2021",
        "emoji": "☁️",
        "story": "עבודה מהבית הגדילה ביקוש לענן — SNOW, DDOG, NET זינקו 200%+.",
        "detail": "מניות הענן שאף אחד לא הכיר לפני 2020.",
        "years": (2020, 2022),
        "tickers": ["SNOW","DDOG","NET","CRWD","ZS"],
        "risk": "אגרסיבי",
        "strategy": "🚀 מומנטום",
        "color": "#a78bfa",
    },
    {
        "id": "ev_2020",
        "name": "⚡ מהפכת ה-EV 2020",
        "emoji": "⚡",
        "story": "טסלה קפצה 700% בשנת 2020 לבדה — אחד הזינוקים הגדולים בהיסטוריה.",
        "detail": "האם אפשר היה לתפוס את הגל כולו?",
        "years": (2020, 2021),
        "tickers": ["TSLA","NVDA","AMD","PLTR","AAPL"],
        "risk": "אגרסיבי",
        "strategy": "🚀 מומנטום",
        "color": "#22c55e",
    },
    {
        "id": "fintech",
        "name": "💳 פינטק 2020",
        "emoji": "💳",
        "story": "תשלומים דיגיטליים התפוצצו — PYPL, SQ, V זינקו עם המעבר לאון-ליין.",
        "detail": "אסטרטגיית RSI הייתה קונה בתחתית הקורונה.",
        "years": (2020, 2022),
        "tickers": ["PYPL","SQ","V","MA","SHOP"],
        "risk": "מאוזן",
        "strategy": "📊 RSI קלאסי",
        "color": "#00b4d8",
    },
]

@st.cache_data(ttl=3600, show_spinner=False)
def _dl(sym: str, start: str, end: str) -> pd.DataFrame:
    try:
        df = yf.download(sym, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[~df.index.duplicated(keep="last")]
        return df
    except Exception:
        return pd.DataFrame()

def _date_le(d1: str, d2: str) -> bool:
    try:
        return datetime.strptime(d1, "%d/%m/%Y") <= datetime.strptime(d2, "%d/%m/%Y")
    except Exception:
        return True

def _run_backtest(tickers: list, start_year: int, end_year: int,
                  budget: float, target_pct: float, risk_key: str,
                  strategy_mode: str = "rsi"):
    rp    = RISK_PROFILES[risk_key]
    start = f"{start_year}-01-01"
    end   = f"{end_year}-12-31"

    # Download data
    raw = {}
    for sym in tickers:
        df = _dl(sym, start, end)
        if not df.empty and "Close" in df.columns:
            raw[sym] = df

    if not raw:
        return None

    # Align closes
    closes = pd.DataFrame({s: df["Close"] for s, df in raw.items()})
    closes = closes.ffill().dropna(how="all")
    if closes.empty:
        return None

    # Pre-compute RSI(14), MA50, MA200
    rsi_d  = pd.DataFrame(index=closes.index)
    ma50_d = pd.DataFrame(index=closes.index)
    ma200_d = pd.DataFrame(index=closes.index)
    for sym in closes.columns:
        c  = closes[sym].ffill()
        d  = c.diff()
        g  = d.clip(lower=0).rolling(14).mean()
        lo = (-d.clip(upper=0)).rolling(14).mean()
        rsi_d[sym]  = 100 - 100 / (1 + g / lo)
        ma50_d[sym]  = c.rolling(50).mean()
        ma200_d[sym] = c.rolling(200).mean()

    # Buy-and-hold: equal weight at first valid price
    bh_shares = {}
    per_stock = budget / len(closes.columns)
    for sym in closes.columns:
        valid = closes[sym].dropna()
        if not valid.empty:
            bh_shares[sym] = per_stock / float(valid.iloc[0])

    # Simulation
    cash        = float(budget)
    positions   = {}          # sym -> {shares, entry_price, entry_date}
    daily_vals  = []          # [(datetime, float)]
    bh_vals     = []          # [float]
    trade_log   = []
    target_val  = budget * (1 + target_pct / 100)
    tgt_reached = False
    tgt_date    = None

    for i, dt in enumerate(closes.index):
        if i < 50:
            pv = cash + sum(
                positions[s]["shares"] * float(closes.at[dt, s])
                for s in positions
                if s in closes.columns and not pd.isna(closes.at[dt, s])
            )
            daily_vals.append((dt, pv))
            bh = sum(bh_shares.get(s,0) * float(closes.at[dt, s])
                     for s in closes.columns if not pd.isna(closes.at[dt, s]))
            bh_vals.append(bh or budget)
            continue

        # ── Exits ────────────────────────────────────────────────────────────
        for sym in list(positions.keys()):
            if sym not in closes.columns: continue
            price = closes.at[dt, sym]
            if pd.isna(price): continue
            price  = float(price)
            pos    = positions[sym]
            pnl    = (price - pos["entry_price"]) / pos["entry_price"]
            rsi_v  = float(rsi_d.at[dt, sym])  if (sym in rsi_d.columns  and not pd.isna(rsi_d.at[dt, sym]))  else None
            ma50_v = float(ma50_d.at[dt, sym])  if (sym in ma50_d.columns and not pd.isna(ma50_d.at[dt, sym]))  else None
            ma200_v= float(ma200_d.at[dt, sym]) if (sym in ma200_d.columns and not pd.isna(ma200_d.at[dt, sym])) else None

            reason = None
            if pnl <= -rp["stop_loss"]:
                reason = f"Stop Loss: {pnl*100:.1f}% 🛑"
            elif strategy_mode == "momentum":
                # Momentum: exit when price falls below MA50 or RSI drops under 40
                if ma50_v and price < ma50_v:
                    reason = f"ירידה מתחת ל-MA50 — יציאת מומנטום 📉"
                elif rsi_v is not None and rsi_v < 38:
                    reason = f"RSI={rsi_v:.0f} — חולשת מומנטום 📉"
            elif strategy_mode == "mean_reversion":
                # Mean Reversion: exit when RSI normalizes or price reaches MA200
                if rsi_v is not None and rsi_v > 62:
                    reason = f"RSI={rsi_v:.0f} — חזרה לממוצע, יציאה 📤"
                elif ma200_v and price >= ma200_v * 0.99:
                    reason = f"חזרה ל-MA200 (${ma200_v:.2f}) — יציאה ✅"
            else:  # rsi classic
                if rsi_v is not None and rsi_v > rp["rsi_sell"]:
                    reason = f"RSI={rsi_v:.0f} — אות מכירה 📉"

            if reason:
                proceeds   = pos["shares"] * price
                pnl_dollar = proceeds - pos["shares"] * pos["entry_price"]
                cash      += proceeds
                trade_log.append({
                    "date":        dt.strftime("%d/%m/%Y"),
                    "action":      "sell",
                    "sym":         sym,
                    "price":       price,
                    "shares":      pos["shares"],
                    "entry_price": pos["entry_price"],
                    "pnl_pct":     pnl * 100,
                    "pnl_dollar":  pnl_dollar,
                    "reason":      reason,
                })
                del positions[sym]

        # ── Entries ──────────────────────────────────────────────────────────
        pv_now = cash + sum(
            positions[s]["shares"] * float(closes.at[dt, s])
            for s in positions
            if s in closes.columns and not pd.isna(closes.at[dt, s])
        )
        # For momentum: compute recent high (20-day)
        if strategy_mode == "momentum" and i >= 20:
            high_20d = {s: float(closes[s].iloc[i-20:i].max())
                        for s in closes.columns if s in closes.columns}
        else:
            high_20d = {}

        for sym in closes.columns:
            if sym in positions: continue
            price = closes.at[dt, sym]
            if pd.isna(price): continue
            price  = float(price)
            rsi_v  = float(rsi_d.at[dt, sym])  if (sym in rsi_d.columns  and not pd.isna(rsi_d.at[dt, sym]))  else None
            ma50_v = float(ma50_d.at[dt, sym])  if (sym in ma50_d.columns and not pd.isna(ma50_d.at[dt, sym]))  else None
            ma200_v= float(ma200_d.at[dt, sym]) if (sym in ma200_d.columns and not pd.isna(ma200_d.at[dt, sym])) else None

            if rsi_v is None: continue

            # ── Buy signal by strategy mode ──────────────────────────────────
            should_buy = False
            buy_reason = ""

            if strategy_mode == "momentum":
                # Buy when RSI > 55, price above MA50, breaking 20-day high
                h20 = high_20d.get(sym)
                if (rsi_v > 55 and ma50_v and price > ma50_v
                        and h20 and price >= h20 * 0.99):
                    should_buy = True
                    buy_reason = f"פריצת שיא 20י׳, RSI={rsi_v:.0f} — מומנטום 🚀"

            elif strategy_mode == "mean_reversion":
                # Buy when RSI < 28 and price is >8% below MA200
                if (rsi_v < 28 and ma200_v and price < ma200_v * 0.92):
                    should_buy = True
                    buy_reason = f"RSI={rsi_v:.0f}, רחוק {((ma200_v-price)/ma200_v*100):.0f}% מ-MA200 ↩️"

            else:  # rsi classic
                if ma50_v is None: continue
                if rsi_v >= rp["rsi_buy"]: continue
                if price <= ma50_v: continue
                should_buy = True
                ma_note = "מעל MA50"
                if ma200_v:
                    ma_note += " ו-MA200" if price > ma200_v else ", מתחת ל-MA200"
                buy_reason = f"RSI={rsi_v:.0f}, {ma_note} 📈"

            if not should_buy: continue

            max_inv = pv_now * rp["max_pos"]
            if cash < max_inv * 0.25: continue
            invest = min(cash * 0.9, max_inv)
            shares = int(invest / price)
            if shares < 1: continue

            cash -= shares * price
            positions[sym] = {"shares": shares, "entry_price": price,
                               "entry_date": dt.strftime("%d/%m/%Y")}
            trade_log.append({
                "date":        dt.strftime("%d/%m/%Y"),
                "action":      "buy",
                "sym":         sym,
                "price":       price,
                "shares":      shares,
                "entry_price": price,
                "pnl_pct":     None,
                "pnl_dollar":  None,
                "reason":      buy_reason,
            })

        # ── Daily snapshot ────────────────────────────────────────────────────
        pv = cash + sum(
            positions[s]["shares"] * float(closes.at[dt, s])
            for s in positions
            if s in closes.columns and not pd.isna(closes.at[dt, s])
        )
        daily_vals.append((dt, pv))
        bh = sum(bh_shares.get(s,0) * float(closes.at[dt, s])
                 for s in closes.columns if not pd.isna(closes.at[dt, s]))
        bh_vals.append(bh or budget)

        if not tgt_reached and pv >= target_val:
            tgt_reached = True
            tgt_date    = dt.strftime("%d/%m/%Y")

    if not daily_vals:
        return None

    # Best / worst closed trade
    sells = [t for t in trade_log if t["action"] == "sell"]
    best  = max(sells, key=lambda t: t["pnl_dollar"], default=None) if sells else None
    worst = min(sells, key=lambda t: t["pnl_dollar"], default=None) if sells else None

    final_val = daily_vals[-1][1]
    final_bh  = bh_vals[-1]
    total_ret = (final_val - budget) / budget * 100
    bh_ret    = (final_bh  - budget) / budget * 100

    return {
        "daily_vals":    daily_vals,
        "bh_vals":       bh_vals,
        "trade_log":     trade_log,
        "tgt_reached":   tgt_reached,
        "tgt_date":      tgt_date,
        "final_val":     final_val,
        "final_bh":      final_bh,
        "total_ret":     total_ret,
        "bh_ret":        bh_ret,
        "n_buys":        sum(1 for t in trade_log if t["action"] == "buy"),
        "best_trade":    best,
        "worst_trade":   worst,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
html, body, .stApp {{
    background: {BG} !important;
    color: {TX} !important;
    font-family: 'Heebo', 'Segoe UI', sans-serif !important;
}}
.block-container {{ padding: 0 1.8rem 2rem !important; max-width: 1420px !important; }}

/* ── Gradient ambient light ── */
.stApp::after {{
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 15% 0%, {CYAN}09 0%, transparent 55%),
        radial-gradient(ellipse at 85% 100%, {PUR}07 0%, transparent 55%);
    pointer-events: none;
    z-index: 0;
}}

/* ── RTL ── */
p, div, span, li {{ direction: rtl; }}
input, textarea, select {{ direction: rtl !important; text-align: right !important; }}
label {{ color: {TX2} !important; font-size: .82rem !important; direction: rtl !important; }}

/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(160deg, {SURF2} 0%, #0b1a2e 100%) !important;
    color: {TX} !important;
    border: 1px solid {BDR} !important;
    border-radius: 10px !important;
    font-family: 'Heebo', sans-serif !important;
    font-weight: 600 !important;
    font-size: .86rem !important;
    transition: all .18s ease !important;
    direction: rtl !important;
    letter-spacing: .01em !important;
}}
.stButton > button:hover {{
    background: linear-gradient(160deg, {BDR} 0%, {BDR2} 100%) !important;
    border-color: {CYAN}88 !important;
    color: {CYAN} !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0,180,216,.14) !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {CYAN}2e 0%, {PUR}1a 100%) !important;
    border-color: {CYAN} !important;
    color: {CYAN} !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 10px {CYAN}28 !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, {CYAN}4a 0%, {PUR}2e 100%) !important;
    box-shadow: 0 4px 18px {CYAN}40 !important;
}}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    background: {SURF2} !important;
    color: {TX} !important;
    border: 1px solid {BDR} !important;
    border-radius: 10px !important;
    font-family: 'Heebo', sans-serif !important;
    font-size: .9rem !important;
    transition: border-color .18s, box-shadow .18s !important;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {{
    border-color: {CYAN} !important;
    box-shadow: 0 0 0 3px {CYAN}20 !important;
}}
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    background: {SURF2} !important;
    border: 1px solid {BDR} !important;
    border-radius: 10px !important;
    color: {TX} !important;
}}
.stDateInput > div > div > input {{
    background: {SURF2} !important;
    color: {TX} !important;
    border: 1px solid {BDR} !important;
    border-radius: 10px !important;
}}

/* ── Sliders ── */
.stSlider > div {{ direction: ltr; }}
.stSlider .st-bq {{ background: {CYAN} !important; }}

/* ── Expander ── */
details {{
    background: {SURF} !important;
    border: 1px solid {BDR} !important;
    border-radius: 10px !important;
    padding: 4px 8px !important;
}}
summary {{ color: {TX2} !important; }}

/* ── Spinner ── */
.stSpinner > div {{ border-top-color: {CYAN} !important; }}

/* ── Overflow (needed for absolute children) ── */
[data-testid="stVerticalBlock"],
[data-testid="column"],
[data-testid="stMarkdownContainer"] {{ overflow: visible !important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{
    background: linear-gradient({BDR2}, {CYAN}44);
    border-radius: 3px;
}}

/* ── Cards ── */
.scard {{
    background: linear-gradient(150deg, {SURF} 0%, #0b1b2f 100%);
    border: 1px solid {BDR};
    border-radius: 16px;
    padding: 16px;
    height: 100%;
    direction: rtl;
    transition: border-color .2s, box-shadow .2s, transform .18s;
    position: relative;
    overflow: hidden;
}}
.scard::after {{
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, {CYAN}22, transparent);
    transition: opacity .2s;
    opacity: 0;
}}
.scard:hover {{
    border-color: {BDR2};
    box-shadow: 0 8px 28px rgba(0,0,0,.5), 0 0 0 1px {CYAN}14;
    transform: translateY(-3px);
}}
.scard:hover::after {{
    opacity: 1;
}}

/* ── Section header ── */
.section-head {{
    font-size: 1.45rem;
    font-weight: 800;
    color: {TX};
    direction: rtl;
    padding: 4px 0 14px;
    margin-bottom: 18px;
    position: relative;
}}
.section-head::after {{
    content: '';
    position: absolute;
    bottom: 0; right: 0;
    width: 56px; height: 2px;
    background: linear-gradient(90deg, {CYAN}, {PUR});
    border-radius: 2px;
}}

/* ── Table header ── */
.tbl-head {{
    display: flex;
    align-items: center;
    padding: 10px 16px;
    background: {SURF3};
    border: 1px solid {BDR};
    border-radius: 10px 10px 0 0;
    direction: rtl;
    font-size: .76rem;
    color: {TX3};
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .04em;
}}
.tbl-row {{
    display: flex;
    align-items: center;
    padding: 11px 16px;
    border-left: 1px solid {BDR};
    border-right: 1px solid {BDR};
    border-bottom: 1px solid {BDR};
    direction: rtl;
    transition: background .12s;
    font-size: .88rem;
}}
.tbl-row:hover {{ background: {SURF2}; }}
.tbl-row:last-child {{ border-radius: 0 0 10px 10px; }}

/* ── Log entry ── */
.log-entry {{
    padding: 8px 12px;
    border-radius: 7px;
    margin-bottom: 6px;
    font-size: .82rem;
    line-height: 1.5;
    direction: rtl;
    background: {SURF2};
    border-right: 3px solid {BDR2};
}}

/* ── Summary card ── */
.sumcard {{
    background: linear-gradient(150deg, {SURF} 0%, #0b1b2f 100%);
    border: 1px solid {BDR};
    border-radius: 14px;
    padding: 18px;
    direction: rtl;
    text-align: center;
    transition: box-shadow .18s, transform .18s;
}}
.sumcard:hover {{
    box-shadow: 0 6px 22px rgba(0,180,216,.1);
    transform: translateY(-2px);
}}

/* ── Table header ── */
.tbl-head {{
    background: linear-gradient(180deg, {SURF3} 0%, #102030 100%);
}}

/* ── Mobile ── */
@media (max-width: 768px) {{
    .block-container {{ padding: 0 0.6rem 80px !important; }}
    .section-head {{ font-size: 1.15rem !important; }}
    .scard {{ padding: 12px !important; border-radius: 12px !important; }}
    .stButton > button {{ font-size: .8rem !important; }}
}}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _prefetch_quotes(tickers: list) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tickers)) as ex:
        results = list(ex.map(quote, tickers))
    return dict(zip(tickers, results))

def _check_alerts(watchlist: list) -> list:
    alerts = []
    for sym in watchlist:
        q = quote(sym)
        if not q:
            continue
        rsi = q.get("rsi", 50)
        if rsi < 35:
            alerts.append({"sym": sym, "type": "buy", "rsi": rsi,
                           "price": q.get("price", 0), "chg": q.get("chg", 0)})
        elif rsi > 65:
            alerts.append({"sym": sym, "type": "sell", "rsi": rsi,
                           "price": q.get("price", 0), "chg": q.get("chg", 0)})
    return alerts

# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
def _nav():
    p      = st.session_state["page"]
    mobile = st.session_state.get("mobile_mode", False)
    _uc    = _unread_count()

    # ── Header bar ────────────────────────────────────────────────────────────
    badge_html = (f"<span style='background:{RED};color:#fff;font-size:.62rem;"
                  f"border-radius:6px;padding:1px 6px;margin-right:4px;'>{_uc}</span>"
                  if _uc > 0 else "")
    st.markdown(f"""<div style="
        background:{SURF};
        border-bottom:1px solid {BDR2};
        padding:10px 20px 8px;margin-bottom:12px;
        display:flex;align-items:center;justify-content:space-between;direction:rtl;
    ">
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:28px;height:28px;border-radius:4px;
                border:1px solid {BDR2};display:flex;align-items:center;
                justify-content:center;font-size:.95rem;">📈</div>
            <div>
                <div style="font-size:.95rem;font-weight:800;letter-spacing:-.02em;color:{TX};">
                    מנתח מניות Pro
                </div>
                <div style="font-size:.58rem;color:{TX3};margin-top:-1px;letter-spacing:.03em;">
                    {datetime.now().strftime('%d/%m/%Y · %H:%M')}
                </div>
            </div>
        </div>
        <div style="font-size:.7rem;color:{TX3};direction:rtl;">
            {badge_html}{'התראות חדשות' if _uc > 0 else ''}
        </div>
    </div>""", unsafe_allow_html=True)

    if mobile:
        # ── Mobile navigation: selectbox + toggle ─────────────────────────────
        PAGE_MAP = {
            "🏠  ראשי":       "home",
            "💼  התיק שלי":   "portfolio",
            "👁️  רשימת מעקב": "watchlist",
            "📰  עדכוני שוק":  "news",
            "🤖  סוכנים":     "agents",
            "⚖️  השוואה":     "compare",
            "🎮  דמו":        "demo",
            "📚  למד":        "learn",
        }
        labels = list(PAGE_MAP.keys())
        current_label = next((k for k, v in PAGE_MAP.items() if v == p), labels[0])

        mc1, mc2 = st.columns([5.5, 1])
        with mc1:
            sel = st.selectbox("ניווט", labels,
                               index=labels.index(current_label),
                               key="mobile_nav_sel",
                               label_visibility="collapsed")
        with mc2:
            if st.button("🖥️", key="nb_mob", use_container_width=True,
                         help="החלף למצב מחשב"):
                st.session_state["mobile_mode"] = False
                st.rerun()

        if PAGE_MAP[sel] != p:
            st.session_state["page"] = PAGE_MAP[sel]
            st.rerun()

        if _uc > 0:
            st.markdown(
                f'<div style="background:{RED}18;border:1px solid {RED}44;'
                f'border-radius:8px;padding:7px 14px;font-size:.78rem;color:{RED};'
                f'direction:rtl;text-align:center;margin-bottom:6px;">'
                f'🔔 {_uc} התראות חדשות — עבור ל-"🤖 סוכנים"</div>',
                unsafe_allow_html=True)
    else:
        # ── Desktop navigation: button row ────────────────────────────────────
        _, b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,b11,b12,b13 = st.columns(
            [0.3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.3])
        with b1:
            if st.button("🏠 ראשי", key="nb_home", use_container_width=True,
                         type="primary" if p == "home" else "secondary"):
                st.session_state["page"] = "home"; st.rerun()
        with b2:
            if st.button("💼 תיק", key="nb_pf", use_container_width=True,
                         type="primary" if p == "portfolio" else "secondary"):
                st.session_state["page"] = "portfolio"; st.rerun()
        with b3:
            if st.button("👁️ מעקב", key="nb_wl", use_container_width=True,
                         type="primary" if p == "watchlist" else "secondary"):
                st.session_state["page"] = "watchlist"; st.rerun()
        with b4:
            if st.button("🏆 גורו", key="nb_guru", use_container_width=True,
                         type="primary" if p == "guru" else "secondary"):
                st.session_state["page"] = "guru"; st.rerun()
        with b5:
            if st.button("🔍 סורק", key="nb_sc", use_container_width=True,
                         type="primary" if p == "screener" else "secondary"):
                st.session_state["page"] = "screener"; st.rerun()
        with b6:
            if st.button("📅 דוחות", key="nb_earn", use_container_width=True,
                         type="primary" if p == "earnings" else "secondary"):
                st.session_state["page"] = "earnings"; st.rerun()
        with b7:
            if st.button("🔔 התראות", key="nb_al", use_container_width=True,
                         type="primary" if p == "alerts" else "secondary"):
                st.session_state["page"] = "alerts"; st.rerun()
        with b8:
            if st.button("⚖️ השוואה", key="nb_cmp", use_container_width=True,
                         type="primary" if p == "compare" else "secondary"):
                st.session_state["page"] = "compare"; st.rerun()
        with b9:
            if st.button("📰 חדשות", key="nb_news", use_container_width=True,
                         type="primary" if p == "news" else "secondary"):
                st.session_state["page"] = "news"; st.rerun()
        with b10:
            _ag_lbl = f"🤖 סוכנים 🔴{_uc}" if _uc > 0 else "🤖 סוכנים"
            if st.button(_ag_lbl, key="nb_agents", use_container_width=True,
                         type="primary" if p == "agents" else "secondary"):
                st.session_state["page"] = "agents"; st.rerun()
        with b11:
            if st.button("📚 למד", key="nb_learn", use_container_width=True,
                         type="primary" if p == "learn" else "secondary"):
                st.session_state["page"] = "learn"; st.rerun()
        with b12:
            if st.button("🇮🇱 ישראל", key="nb_il", use_container_width=True,
                         type="primary" if p == "israel" else "secondary"):
                st.session_state["page"] = "israel"; st.rerun()
        with b13:
            if st.button("📱", key="nb_mob", use_container_width=True,
                         help="החלף למצב נייד"):
                st.session_state["mobile_mode"] = True; st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS FOR STOCK DETAIL
# ══════════════════════════════════════════════════════════════════════════════
def _fmt_large(n):
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9:  return f"${n/1e9:.1f}B"
    if n >= 1e6:  return f"${n/1e6:.0f}M"
    return f"${n:,.0f}"

def _gen_summary(df: pd.DataFrame, info: dict, sym: str) -> tuple:
    """Returns (what_is, behavior, driver, mood) as Hebrew strings."""
    # 1. What the company does
    hot_entry = next((s for s in HOT if s["t"] == sym), None)
    if hot_entry:
        what_is = hot_entry["w"]
    else:
        name     = info.get("longName", sym)
        sector   = info.get("sector", "")
        industry = info.get("industry", "")
        what_is  = f"{name} היא חברה בתחום {sector}."
        if industry and industry != sector:
            what_is += f" תחום פעילות עיקרי: {industry}."

    # 2. Stock behavior
    close = df["Close"].dropna()
    cl    = float(close.iloc[-1])
    try:
        chg1m = (cl / float(close.iloc[-22]) - 1) * 100
        trend = "עלתה" if chg1m > 0 else "ירדה"
        behavior = f"בחודש האחרון המניה {trend} ב-{abs(chg1m):.1f}%."
    except Exception:
        behavior = ""
    ma50  = df["MA50"].iloc[-1]  if "MA50"  in df.columns and not pd.isna(df["MA50"].iloc[-1])  else None
    ma200 = df["MA200"].iloc[-1] if "MA200" in df.columns and not pd.isna(df["MA200"].iloc[-1]) else None
    if ma50 and ma200:
        if   cl > ma50 and cl > ma200: behavior += " המחיר מעל שני הממוצעים הנעים — תמונה טכנית חיובית."
        elif cl < ma50 and cl < ma200: behavior += " המחיר מתחת לשני הממוצעים — לחץ מכירות."
        else:                          behavior += " המחיר בין הממוצעים — מאבק על כיוון."

    # 3. Driver
    parts = []
    rv = info.get("revenueGrowth")
    eg = info.get("earningsGrowth")
    if rv: parts.append(f"צמיחת הכנסות של {rv*100:.0f}% בשנה האחרונה")
    if eg: parts.append(f"צמיחת רווח של {eg*100:.0f}%")
    tgt = info.get("targetMeanPrice")
    if tgt: parts.append(f"יעד מחיר ממוצע של האנליסטים: ${tgt:,.0f}")
    driver = (". ".join(parts[:2]) + ".") if parts else "אין מידע זמין על הגורמים המניעים."

    # 4. Market mood — factual data only, no buy/sell directives (those are in the scoring panel)
    rsi_v      = df["RSI"].iloc[-1] if "RSI" in df.columns and not pd.isna(df["RSI"].iloc[-1]) else None
    n_analysts = info.get("numberOfAnalystOpinions") or 0
    tgt_price  = info.get("targetMeanPrice")
    mood_parts = []
    if n_analysts > 0 and tgt_price:
        upside = (tgt_price / float(close.iloc[-1]) - 1) * 100
        arrow  = "↑" if upside >= 0 else "↓"
        mood_parts.append(f"{n_analysts} אנליסטים עוקבים · יעד ${tgt_price:,.0f} ({arrow}{abs(upside):.0f}% מהמחיר הנוכחי)")
    elif n_analysts > 0:
        mood_parts.append(f"{n_analysts} אנליסטים עוקבים אחרי המניה")
    if rsi_v:
        if   rsi_v < 30: mood_parts.append(f"RSI {rsi_v:.0f} — מכירת יתר, לחץ מכירות קיצוני")
        elif rsi_v > 70: mood_parts.append(f"RSI {rsi_v:.0f} — קניית יתר, מומנטום גבוה")
        else:            mood_parts.append(f"RSI {rsi_v:.0f} — אזור ניטרלי")
    mood = ". ".join(mood_parts) + "." if mood_parts else "אין מידע על סנטימנט השוק."
    return what_is, behavior, driver, mood


# ══════════════════════════════════════════════════════════════════════════════
# STOCK DETAIL PANEL (used on home page)
# ══════════════════════════════════════════════════════════════════════════════
def _stock_detail(sym: str):
    watchlist = load_json(WL_FILE)

    # ── Period selector ───────────────────────────────────────────────────────
    per_key = f"det_period_{sym}"
    if per_key not in st.session_state:
        st.session_state[per_key] = "6mo"

    st.markdown(f"""<div style="background:{SURF};border:2px solid {BDR2};
        border-radius:8px;padding:22px 26px;margin-top:6px;direction:rtl;">
    """, unsafe_allow_html=True)

    # Header row: title + action buttons
    hc1, hc2, hc3, hc4, _ = st.columns([1.8, 1.1, 1.1, 0.9, 2])
    with hc1:
        st.markdown(f"<div style='font-size:1.2rem;font-weight:800;color:{CYAN};"
                    f"padding-top:6px;'>📊 ניתוח — {sym}</div>",
                    unsafe_allow_html=True)
    with hc2:
        in_wl = sym in watchlist
        if st.button("✓ במעקב" if in_wl else "👁️ הוסף למעקב",
                     key=f"det_wl_{sym}", use_container_width=True,
                     type="secondary" if in_wl else "primary"):
            if not in_wl:
                watchlist.append(sym)
                save_json(WL_FILE, watchlist)
                st.rerun()
    with hc3:
        if st.button("💼 הוסף לתיק", key=f"det_pf_{sym}",
                     use_container_width=True):
            st.session_state["pf_prefill"] = sym
            st.session_state["page"] = "portfolio"
            st.rerun()
    with hc4:
        if st.button("✕ סגור", key=f"det_close_{sym}",
                     use_container_width=True):
            st.session_state["home_selected"] = None
            st.rerun()

    # ── Load data ─────────────────────────────────────────────────────────────
    period = st.session_state[per_key]
    with st.spinner(f"טוען נתונים עבור {sym}…"):
        df   = fetch_history(sym, period)
        info = fetch_info(sym)
        news = fetch_news(sym)
        cal  = fetch_calendar(sym)

    if df.empty:
        st.error(f"לא נמצאו נתונים עבור {sym}.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    cl      = float(df["Close"].iloc[-1])
    prev_cl = float(df["Close"].iloc[-2]) if len(df) > 1 else cl
    chg_pct = (cl - prev_cl) / prev_cl * 100
    chg_c   = GRN if chg_pct >= 0 else RED
    rsi_val = float(df["RSI"].iloc[-1]) if "RSI" in df.columns else float("nan")
    ma50    = float(df["MA50"].iloc[-1])  if "MA50"  in df.columns and not pd.isna(df["MA50"].iloc[-1])  else None
    ma200   = float(df["MA200"].iloc[-1]) if "MA200" in df.columns and not pd.isna(df["MA200"].iloc[-1]) else None

    if   rsi_val < 35: rsi_sig, rsi_c = "קנייה",  GRN
    elif rsi_val > 65: rsi_sig, rsi_c = "מכירה",  RED
    else:              rsi_sig, rsi_c = "המתנה",  AMB

    # ── Full scoring (computed here so metrics row shows final verdict) ──────
    score      = 0
    indicators = []

    # RSI
    if not np.isnan(rsi_val):
        if rsi_val < 30:
            d = +2; ic = "📉"; lbl = f"RSI = {rsi_val:.0f}"; col = GRN
            det = "מכירת יתר חריפה — לחץ מכירות קיצוני בדרך כלל מקדים היפוך מגמה. אזור כניסה אטרקטיבי."
        elif rsi_val < 40:
            d = +1; ic = "📉"; lbl = f"RSI = {rsi_val:.0f}"; col = GRN
            det = "RSI נמוך מסמן חולשה זמנית. עבור מניות צמיחה איכותיות, ירידה לאזור זה היא לעיתים הזדמנות כניסה."
        elif rsi_val > 70:
            d = -2; ic = "📈"; lbl = f"RSI = {rsi_val:.0f}"; col = RED
            det = "קניית יתר — מומנטום חזק אך סיכון לתיקון גבוה."
        elif rsi_val > 60:
            d = -1; ic = "📈"; lbl = f"RSI = {rsi_val:.0f}"; col = AMB
            det = "RSI גבוה מעיד על תנופה — סיכון לתנודתיות בטווח הקצר."
        else:
            d = 0; ic = "➡️"; lbl = f"RSI = {rsi_val:.0f}"; col = TX2
            det = "RSI באזור נייטרלי — אין אות ברור. מומלץ לעקוב אחר פריצה מהטווח."
        score += d; indicators.append((ic, "RSI", lbl, det, col, d))

    # MA50
    if ma50:
        gap50 = (cl - ma50) / ma50 * 100
        if cl > ma50:
            d = +1; col = GRN
            lbl = f"מחיר מעל MA50 (+{gap50:.1f}%)"
            det = f"המחיר {gap50:.1f}% מעל ממוצע 50 יום — מגמה עולה לטווח בינוני."
        else:
            d = -1; col = RED
            lbl = f"מחיר מתחת ל-MA50 ({gap50:.1f}%)"
            det = f"המחיר {abs(gap50):.1f}% מתחת לממוצע 50 יום — חולשה בינונית. עלייה מעל MA50 תהיה אות חיובי."
        score += d; indicators.append(("📊", "ממוצע נע 50", lbl, det, col, d))

    # MA200
    if ma200:
        gap200 = (cl - ma200) / ma200 * 100
        if cl > ma200:
            d = +1; col = GRN
            lbl = f"מחיר מעל MA200 (+{gap200:.1f}%)"
            det = f"המחיר מעל ממוצע 200 יום — מגמה עולה לטווח ארוך."
        else:
            d = -1; col = RED
            lbl = f"מחיר מתחת ל-MA200 ({gap200:.1f}%)"
            det = f"המחיר {abs(gap200):.1f}% מתחת לממוצע 200 יום — תמונה שלילית לטווח ארוך."
        score += d; indicators.append(("📉", "ממוצע נע 200", lbl, det, col, d))

    # Golden / Death Cross
    if ma50 and ma200:
        if ma50 > ma200:
            gap_x = (ma50 - ma200) / ma200 * 100
            d = +1; col = GRN
            lbl = f"Golden Cross: MA50 > MA200 (+{gap_x:.1f}%)"
            det = "ממוצע 50 יום מעל ממוצע 200 יום — צלב הזהב. מסמן מגמה עולה לטווח ארוך."
        else:
            gap_x = (ma200 - ma50) / ma200 * 100
            d = -1; col = RED
            lbl = f"Death Cross: MA50 < MA200 (-{gap_x:.1f}%)"
            det = "ממוצע 50 יום מתחת לממוצע 200 יום — צלב המוות. מסמן מגמה יורדת לטווח ארוך."
        score += d; indicators.append(("✂️", "Golden/Death Cross", lbl, det, col, d))

    # MACD
    if "MACD" in df.columns and "MACD_S" in df.columns:
        macd_v = float(df["MACD"].iloc[-1])
        macd_s = float(df["MACD_S"].iloc[-1])
        macd_h = macd_v - macd_s
        if macd_v > macd_s:
            d = +1; col = GRN
            lbl = f"MACD > Signal (+{macd_h:.2f})"
            det = "קו MACD מעל קו האות — מומנטום עולה."
        else:
            d = -1; col = RED
            lbl = f"MACD < Signal ({macd_h:.2f})"
            det = "קו MACD מתחת לקו האות — מומנטום יורד. ייתכן שהלחץ ימשך בטווח הקצר."
        score += d; indicators.append(("⚡", "MACD", lbl, det, col, d))

    # Bollinger Bands
    if "BB_L" in df.columns and "BB_U" in df.columns:
        bb_l = float(df["BB_L"].iloc[-1])
        bb_u = float(df["BB_U"].iloc[-1])
        bb_w = bb_u - bb_l if bb_u > bb_l else 1
        bb_pct = (cl - bb_l) / bb_w
        if bb_pct <= 0.10:
            d = +1; col = GRN
            lbl = f"ליד פס בולינגר תחתון ({bb_pct*100:.0f}% בטווח)"
            det = "המחיר ליד פס בולינגר התחתון — אות קנייה טכני. בדרך כלל מסמן מכירת יתר זמנית."
        elif bb_pct >= 0.90:
            d = -1; col = RED
            lbl = f"ליד פס בולינגר עליון ({bb_pct*100:.0f}% בטווח)"
            det = "המחיר ליד פס בולינגר העליון — מתיחות טכנית. סיכוי לתיקון לכיוון הממוצע."
        else:
            d = 0; col = TX2
            lbl = f"בולינגר: {bb_pct*100:.0f}% בתוך הטווח"
            det = f"המחיר ב-{bb_pct*100:.0f}% בין הפסים (0%=תחתון, 100%=עליון). אין אות קיצוני."
        score += d; indicators.append(("🎯", "בולינגר בנדס", lbl, det, col, d))

    # 52-week range
    w52_hi = info.get("fiftyTwoWeekHigh")
    w52_lo = info.get("fiftyTwoWeekLow")
    if w52_hi and w52_lo and w52_hi > w52_lo:
        w52_r   = w52_hi - w52_lo
        w52_pct = (cl - w52_lo) / w52_r * 100
        if w52_pct <= 15:
            d = +1; col = GRN
            lbl = f"קרוב לשפל 52 שבועות ({w52_pct:.0f}% מהטווח)"
            det = f"המחיר קרוב לשפל שנה (${w52_lo:.1f}) — אזור היסטורי של קנייה."
        elif w52_pct >= 90:
            d = -1; col = AMB
            lbl = f"קרוב לשיא 52 שבועות ({w52_pct:.0f}% מהטווח)"
            det = f"המחיר קרוב לשיא שנה (${w52_hi:.1f}) — עמידות היסטורית. לא בהכרח שלילי לחברות חזקות."
        else:
            d = 0; col = TX2
            lbl = f"טווח 52 שבועות: {w52_pct:.0f}%"
            det = f"המחיר ב-{w52_pct:.0f}% בין שפל שנה (${w52_lo:.1f}) לשיא (${w52_hi:.1f})."
        score += d; indicators.append(("📏", "טווח 52 שבועות", lbl, det, col, d))

    # Momentum 30d
    if len(df) >= 30:
        p30 = float(df["Close"].iloc[-30])
        mom30 = (cl - p30) / p30 * 100
        if mom30 > 20:
            d = -1; col = AMB
            lbl = f"מומנטום 30י׳: +{mom30:.1f}%"
            det = f"עלייה חדה של {mom30:.1f}% ב-30 יום — מתיחות גבוהה, סיכון לתיקון."
        elif mom30 > 5:
            d = +1; col = GRN
            lbl = f"מומנטום 30י׳: +{mom30:.1f}%"
            det = f"עלייה בריאה של {mom30:.1f}% ב-30 יום — מגמה חיובית ויציבה."
        elif mom30 < -20:
            d = +1; col = GRN
            lbl = f"מומנטום 30י׳: {mom30:.1f}%"
            det = f"ירידה חדה של {abs(mom30):.1f}% ב-30 יום — מכירת יתר. פוטנציאל התאוששות לאחר התייצבות."
        elif mom30 < -5:
            d = -1; col = RED
            lbl = f"מומנטום 30י׳: {mom30:.1f}%"
            det = f"ירידה של {abs(mom30):.1f}% ב-30 יום — חולשה. בדוק אם יש שינוי פונדמנטלי."
        else:
            d = 0; col = TX2
            lbl = f"מומנטום 30י׳: {mom30:+.1f}%"
            det = "תנועת מחיר מינורית ב-30 יום — ניטרלי."
        score += d; indicators.append(("🔄", "מומנטום 30 יום", lbl, det, col, d))

    # Analyst consensus
    rec_key   = (info.get("recommendationKey") or "").lower()
    n_analyst = info.get("numberOfAnalystOpinions") or 0
    tgt_price = info.get("targetMeanPrice")
    if rec_key in ("buy", "strong_buy"):
        upside = (tgt_price / cl - 1) * 100 if tgt_price else None
        d = +1; col = GRN
        lbl = f"אנליסטים: {rec_key.replace('_',' ').title()}"
        det = (f"{n_analyst} אנליסטים ממליצים קנייה" +
               (f" · יעד ${tgt_price:,.0f} (אפסייד {upside:.0f}%)" if upside else ""))
    elif rec_key in ("sell", "strong_sell", "underperform"):
        d = -1; col = RED
        lbl = f"אנליסטים: {rec_key.replace('_',' ').title()}"
        det = f"{n_analyst} אנליסטים ממליצים מכירה — זהירות."
    elif rec_key == "hold":
        d = 0; col = AMB
        lbl = "אנליסטים: החזקה"
        det = f"{n_analyst} אנליסטים ממליצים המתנה — אין קטליסט מיידי."
    else:
        d = 0; col = TX3
        lbl = "אנליסטים: אין נתון"; det = "לא נמצאו המלצות אנליסטים."
    score += d; indicators.append(("👨‍💼", "אנליסטים", lbl, det, col, d))

    # Revenue / Earnings growth
    rev_g = info.get("revenueGrowth")
    ear_g = info.get("earningsGrowth")
    if rev_g is not None:
        if rev_g > 0.20:
            d = +2; col = GRN
            lbl = f"צמיחת הכנסות {rev_g*100:.0f}%"
            det = f"צמיחה של {rev_g*100:.0f}% בהכנסות — מאפיין ליבה של מניות צמיחה."
        elif rev_g > 0.05:
            d = +1; col = GRN
            lbl = f"צמיחת הכנסות {rev_g*100:.0f}%"
            det = f"צמיחה מתונה של {rev_g*100:.0f}% — בריאה אך לא מרשימה לרף מניית צמיחה."
        elif rev_g < -0.05:
            d = -1; col = RED
            lbl = f"ירידת הכנסות {rev_g*100:.0f}%"
            det = "ירידה בהכנסות — דגל אדום. בדוק אם זמנית."
        else:
            d = 0; col = AMB
            lbl = f"הכנסות יציבות ({rev_g*100:.0f}%)"
            det = "צמיחה אפסית — לא מתאים לפרופיל מניית צמיחה."
        ear_str = f" · רווח: {ear_g*100:.0f}%" if ear_g else ""
        score += d; indicators.append(("💰", "פונדמנטלים", lbl + ear_str, det, col, d))

    # Gross margin
    margin = info.get("grossMargins")
    if margin and margin > 0.50:
        d = +1; score += d
        indicators.append(("📦", "שולי רווח גולמי",
                           f"מרווח גולמי {margin*100:.0f}%",
                           f"שולי רווח גולמי {margin*100:.0f}% — pricing power חזק. מצדיק מכפילים גבוהים.",
                           GRN, d))

    # Free Cash Flow
    fcf = info.get("freeCashflow")
    if fcf is not None:
        fcf_b = fcf / 1e9
        if fcf > 0:
            d = +1; col = GRN
            lbl = f"FCF חיובי: ${fcf_b:.1f}B"
            det = f"תזרים מזומנים חופשי חיובי של ${fcf_b:.1f}B — החברה מייצרת מזומן אמיתי."
        else:
            d = -1; col = RED
            lbl = f"FCF שלילי: ${fcf_b:.1f}B"
            det = f"תזרים מזומנים חופשי שלילי — שורפת מזומן. נורמלי לסטארטאפים, מדאיג לחברות בוגרות."
        score += d; indicators.append(("💵", "תזרים מזומנים (FCF)", lbl, det, col, d))

    # Debt-to-Equity
    de_raw = info.get("debtToEquity")
    if de_raw is not None:
        de_val = de_raw / 100
        if de_val < 0.5:
            d = +1; col = GRN
            lbl = f"חוב/הון נמוך ({de_val:.2f})"
            det = f"D/E = {de_val:.2f} — מינוף נמוך. החברה לא תלויה בחוב."
        elif de_val > 2.0:
            d = -1; col = RED
            lbl = f"חוב/הון גבוה ({de_val:.2f})"
            det = f"D/E = {de_val:.2f} — מינוף גבוה. בריבית גבוהה זה מגדיל סיכון."
        else:
            d = 0; col = AMB
            lbl = f"חוב/הון בינוני ({de_val:.2f})"
            det = f"D/E = {de_val:.2f} — מינוף מתון. נורמלי לחברות בוגרות."
        score += d; indicators.append(("🏦", "יחס חוב/הון (D/E)", lbl, det, col, d))

    # Volume trend
    if "Vol_ratio" in df.columns and not pd.isna(df["Vol_ratio"].iloc[-1]):
        vr = float(df["Vol_ratio"].iloc[-1])
        if vr > 1.5:
            if chg_pct > 0:
                d = +1; col = GRN
                lbl = f"נפח גבוה ({vr:.1f}x ממוצע) עם עלייה"
                det = f"נפח {(vr-1)*100:.0f}% מעל הממוצע לצד עלייה — מומנטום חיובי עם אישור נפח."
            else:
                d = -1; col = RED
                lbl = f"נפח גבוה ({vr:.1f}x ממוצע) עם ירידה"
                det = "נפח מסחר גבוה לצד ירידה — לחץ מכירות משמעותי."
            score += d; indicators.append(("📊", "נפח מסחר", lbl, det, col, d))

    # Earnings date
    earnings_dt = cal.get("earnings_date")
    if earnings_dt:
        days_to_earn = (pd.Timestamp(earnings_dt) - pd.Timestamp(datetime.now())).days
        if 0 <= days_to_earn <= 14:
            d = -1; score += d
            indicators.append(("📅", "דוח רווחים",
                f"דוח בעוד {days_to_earn} ימים ({pd.Timestamp(earnings_dt).strftime('%d/%m/%Y')})",
                "הדוח הרבעוני קרוב — תנודתיות גבוהה צפויה סביב פרסום.",
                AMB, d))

    # Map score → verdict
    if   score >=  6: rec_label, rec_color, rec_icon = "קנייה חזקה",  GRN, "🟢"
    elif score >=  3: rec_label, rec_color, rec_icon = "קנייה",       GRN, "🟩"
    elif score >= -2: rec_label, rec_color, rec_icon = "החזקה",       AMB, "🟡"
    elif score >= -4: rec_label, rec_color, rec_icon = "מכירה",       RED, "🔴"
    else:             rec_label, rec_color, rec_icon = "מכירה חזקה",  RED, "🔻"

    # ── Key metrics cards ─────────────────────────────────────────────────────
    mc_items = [
        ("מחיר",       f"${cl:,.2f}",          TX),
        ("שינוי יומי", f"{'+'if chg_pct>=0 else ''}{chg_pct:.2f}%", chg_c),
        ("RSI",        f"{rsi_val:.0f}" if not np.isnan(rsi_val) else "—", rsi_c),
        ("המלצה",      rec_label,         rec_color),
        ("MA 50",      f"${ma50:,.2f}"  if ma50  else "—", CYAN),
        ("MA 200",     f"${ma200:,.2f}" if ma200 else "—", AMB),
    ]
    if info.get("trailingPE"):
        mc_items.append(("מכפיל P/E", f"{info['trailingPE']:.1f}", TX2))
    if info.get("marketCap"):
        mc_items.append(("שווי שוק", _fmt_large(info["marketCap"]), TX2))
    if info.get("trailingEps"):
        mc_items.append(("EPS", f"${info['trailingEps']:.2f}", TX2))
    if info.get("dividendYield"):
        mc_items.append(("דיבידנד", f"{info['dividendYield']*100:.1f}%", TX2))
    if "Volatility30" in df.columns and not pd.isna(df["Volatility30"].iloc[-1]):
        vol30 = float(df["Volatility30"].iloc[-1])
        mc_items.append(("תנודתיות 30י׳", f"{vol30:.0f}%", AMB))
    if "Vol_ratio" in df.columns and not pd.isna(df["Vol_ratio"].iloc[-1]):
        vr = float(df["Vol_ratio"].iloc[-1])
        mc_items.append(("נפח (x ממוצע)", f"{vr:.1f}x", GRN if vr > 1.5 else TX2))
    earnings_dt = cal.get("earnings_date")
    if earnings_dt:
        days_to_earn = (pd.Timestamp(earnings_dt) - pd.Timestamp(datetime.now())).days
        if 0 <= days_to_earn <= 60:
            earn_c = RED if days_to_earn <= 14 else AMB
            mc_items.append(("דוח רווחים", f"עוד {days_to_earn} י׳", earn_c))

    mcols = st.columns(len(mc_items))
    for col, (lbl, val, vc) in zip(mcols, mc_items):
        is_rec = (lbl == "המלצה")
        border = f"1px solid {vc}88" if is_rec else f"1px solid {BDR}"
        shadow = f"0 0 12px {vc}22" if is_rec else "none"
        col.markdown(f"""<div style="background:{SURF2};border:{border};
            border-radius:6px;padding:10px 8px;text-align:center;direction:rtl;
            margin-bottom:4px;box-shadow:{shadow};transition:all .15s;">
            <div style="font-size:.68rem;color:{TX3};margin-bottom:4px;">{lbl}</div>
            <div style="font-size:.92rem;font-weight:{'800' if is_rec else '700'};color:{vc};">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── "מה המניה עושה?" summary ──────────────────────────────────────────────
    what_is, behavior, driver, mood = _gen_summary(df, info, sym)
    st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
        border-radius:6px;padding:16px 20px;margin-bottom:14px;direction:rtl;">
        <div style="font-size:.9rem;font-weight:800;margin-bottom:12px;color:{TX};">
            📋 מה המניה עושה?
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="border-right:3px solid {CYAN};padding:8px 12px;
                        background:{BG};border-radius:0 8px 8px 0;">
                <div style="font-size:.72rem;color:{CYAN};font-weight:700;
                            margin-bottom:4px;">🏢 מה החברה עושה?</div>
                <div style="font-size:.82rem;color:{TX};line-height:1.6;">{what_is}</div>
            </div>
            <div style="border-right:3px solid {AMB};padding:8px 12px;
                        background:{BG};border-radius:0 8px 8px 0;">
                <div style="font-size:.72rem;color:{AMB};font-weight:700;
                            margin-bottom:4px;">📈 מה המניה עושה לאחרונה?</div>
                <div style="font-size:.82rem;color:{TX};line-height:1.6;">{behavior}</div>
            </div>
            <div style="border-right:3px solid {GRN};padding:8px 12px;
                        background:{BG};border-radius:0 8px 8px 0;">
                <div style="font-size:.72rem;color:{GRN};font-weight:700;
                            margin-bottom:4px;">🔍 מה מניע אותה?</div>
                <div style="font-size:.82rem;color:{TX};line-height:1.6;">{driver}</div>
            </div>
            <div style="border-right:3px solid {PUR};padding:8px 12px;
                        background:{BG};border-radius:0 8px 8px 0;">
                <div style="font-size:.72rem;color:{PUR};font-weight:700;
                            margin-bottom:4px;">🌡️ סנטימנט השוק</div>
                <div style="font-size:.82rem;color:{TX};line-height:1.6;">{mood}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Period buttons ────────────────────────────────────────────────────────
    pb_cols = st.columns([3, 1, 1, 1, 1])
    pb_cols[0].markdown(f"<div style='color:{TX2};font-size:.82rem;"
                        f"padding-top:8px;direction:rtl;'>תקופה:</div>",
                        unsafe_allow_html=True)
    for col, (lbl, val) in zip(pb_cols[1:], [("1M","1mo"),("3M","3mo"),
                                               ("6M","6mo"),("1Y","1y")]):
        if col.button(lbl, key=f"per_{sym}_{val}", use_container_width=True,
                      type="primary" if period == val else "secondary"):
            st.session_state[per_key] = val
            fetch_history.clear()
            st.rerun()

    # ── Candlestick chart ─────────────────────────────────────────────────────
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.55, 0.25, 0.20],
        shared_xaxes=True,
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        name="מחיר",
        increasing_line_color=GRN, decreasing_line_color=RED,
        increasing_fillcolor="rgba(34,197,94,0.33)",
        decreasing_fillcolor="rgba(239,68,68,0.33)",
    ), row=1, col=1)

    # Bollinger Bands
    if "BB_U" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_U"], name="BB עליון",
            line=dict(color=TX3, width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_L"], name="BB תחתון",
            line=dict(color=TX3, width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(107,155,192,.05)"), row=1, col=1)
    if ma50:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA 50",
            line=dict(color=AMB, width=1.5)), row=1, col=1)
    if ma200:
        fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], name="MA 200",
            line=dict(color=PUR, width=1.5)), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_hrect(y0=65, y1=100, fillcolor="rgba(239,68,68,0.07)",
                      line_width=0, row=2, col=1)
        fig.add_hrect(y0=0, y1=35, fillcolor="rgba(34,197,94,0.07)",
                      line_width=0, row=2, col=1)
        fig.add_hline(y=65, line=dict(color=RED, dash="dot", width=1), row=2, col=1)
        fig.add_hline(y=35, line=dict(color=GRN, dash="dot", width=1), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
            line=dict(color=PUR, width=1.8)), row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        colors = [GRN if v >= 0 else RED for v in df["MACD_H"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_H"], name="MACD Hist",
            marker_color=colors, opacity=0.7), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
            line=dict(color=CYAN, width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_S"], name="Signal",
            line=dict(color=AMB, width=1.5)), row=3, col=1)

    fig.update_layout(
        **{**PB, "height": 560},
        xaxis_rangeslider_visible=False,
        yaxis_title="מחיר ($)",
        yaxis2_title="RSI",
        yaxis3_title="MACD",
    )
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # ── Fundamentals ─────────────────────────────────────────────────────────
    fund_items = []
    pairs = [
        ("הכנסות (TTM)",   info.get("totalRevenue"),       _fmt_large),
        ("שוליים נטו",     info.get("profitMargins"),      lambda v: f"{v*100:.1f}%"),
        ("צמיחת הכנסות",   info.get("revenueGrowth"),      lambda v: f"{v*100:.1f}%"),
        ("צמיחת רווח",     info.get("earningsGrowth"),     lambda v: f"{v*100:.1f}%"),
        ("P/S",            info.get("priceToSalesTrailing12Months"), lambda v: f"{v:.1f}x"),
        ("P/B",            info.get("priceToBook"),        lambda v: f"{v:.1f}x"),
        ("EBITDA",         info.get("ebitda"),             _fmt_large),
        ("מזומן",          info.get("totalCash"),          _fmt_large),
        ("חוב כולל",       info.get("totalDebt"),          _fmt_large),
        ("החזר הון (ROE)",  info.get("returnOnEquity"),    lambda v: f"{v*100:.1f}%"),
    ]
    for lbl, val, fmt in pairs:
        if val:
            try:   fund_items.append((lbl, fmt(val)))
            except: pass

    if fund_items:
        st.markdown(f"<div style='font-weight:700;color:{TX};font-size:.92rem;"
                    f"direction:rtl;margin:8px 0 10px;'>💰 נתונים פונדמנטליים</div>",
                    unsafe_allow_html=True)
        n = len(fund_items)
        fcols = st.columns(min(n, 5))
        for idx, (lbl, val) in enumerate(fund_items):
            fcols[idx % len(fcols)].markdown(
                f"""<div style="background:{SURF2};border:1px solid {BDR};
                    border-radius:9px;padding:9px 10px;text-align:center;
                    direction:rtl;margin-bottom:6px;">
                    <div style="font-size:.67rem;color:{TX3};margin-bottom:3px;">{lbl}</div>
                    <div style="font-size:.88rem;font-weight:700;color:{TX};">{val}</div>
                </div>""", unsafe_allow_html=True)

    # ── News ──────────────────────────────────────────────────────────────────
    if news:
        st.markdown(f"<div style='font-weight:700;color:{TX};font-size:.92rem;"
                    f"direction:rtl;margin:12px 0 10px;'>📰 חדשות אחרונות</div>",
                    unsafe_allow_html=True)
        for item in news[:4]:
            title     = item.get("title", "")
            link      = item.get("link", "#")
            publisher = item.get("publisher", "")
            pub_ts    = item.get("providerPublishTime", 0)
            if pub_ts:
                dt_str = datetime.fromtimestamp(pub_ts).strftime("%d/%m %H:%M")
            else:
                dt_str = ""
            if not title:
                continue
            st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
                border-right:3px solid {CYAN};border-radius:0 9px 9px 0;
                padding:10px 14px;margin-bottom:7px;direction:ltr;">
                <a href="{link}" target="_blank"
                   style="color:{TX};font-size:.83rem;font-weight:600;
                          text-decoration:none;line-height:1.5;">{title}</a>
                <div style="font-size:.7rem;color:{TX3};margin-top:4px;">
                    {publisher}{"&nbsp;·&nbsp;"+dt_str if dt_str else ""}
                </div>
            </div>""", unsafe_allow_html=True)

    # ── AI Recommendation display ─────────────────────────────────────────────
    # ── Build explanation paragraphs ──
    bullish = [(ic,lbl,det) for ic,grp,lbl,det,col,d in indicators if d > 0]
    bearish = [(ic,lbl,det) for ic,grp,lbl,det,col,d in indicators if d < 0]
    neutral = [(ic,lbl,det) for ic,grp,lbl,det,col,d in indicators if d == 0]

    def _ind_row(ic, lbl, det, c):
        return (f"<div style='display:flex;gap:10px;padding:9px 0;"
                f"border-bottom:1px solid {BDR};direction:rtl;'>"
                f"<span style='font-size:1rem;min-width:22px;'>{ic}</span>"
                f"<div><div style='font-size:.82rem;font-weight:700;color:{c};'>{lbl}</div>"
                f"<div style='font-size:.79rem;color:{TX2};line-height:1.55;margin-top:2px;'>{det}</div>"
                f"</div></div>")

    bull_html = "".join(_ind_row(ic,lbl,det, GRN) for ic,lbl,det in bullish) if bullish else ""
    bear_html = "".join(_ind_row(ic,lbl,det, RED) for ic,lbl,det in bearish) if bearish else ""
    neut_html = "".join(_ind_row(ic,lbl,det, TX2) for ic,lbl,det in neutral) if neutral else ""

    # Risk warning tailored to verdict
    if rec_label in ("קנייה חזקה", "קנייה"):
        risk_msg = ("⚠️ גם עם אותות חיוביים, מניות צמיחה טכנולוגיות תנודתיות מאוד. "
                    "שינוי בריבית, תוצאות רבעוניות מאכזבות, או תנודתיות שוק כללית עלולים לגרום "
                    "לירידות של 20-40% בטווח קצר. השקע רק סכום שאתה מוכן להפסיד.")
    elif rec_label == "החזקה":
        risk_msg = ("⚠️ אין קטליסט ברור לעלייה או ירידה בטווח הקרוב. "
                    "אם אתה מחזיק — עקוב אחר תוצאות הרבעון הקרוב ורמת ה-RSI. "
                    "כניסה חדשה בנקודה זו אינה מומלצת ללא תיקון.")
    else:
        risk_msg = ("⚠️ אותות שליליים מרובים — שקול הפחתת חשיפה. "
                    "אל תלחם במגמה. המתן לאישורים טכניים ברורים (פריצת MA50, RSI נמוך) "
                    "לפני כניסה מחדש.")

    # Score gauge bar
    _score_pct = max(0.0, min(100.0, (max(-10, min(10, score)) + 10) / 20 * 100))
    _score_bar = (
        f"<div style='margin:16px 0 12px;'>"
        f"<div style='position:relative;"
        f"background:linear-gradient(90deg,{RED}dd 0%,{AMB}99 42%,{AMB}99 58%,{GRN}dd 100%);"
        f"height:8px;border-radius:8px;'>"
        f"<div style='position:absolute;top:50%;left:{_score_pct:.1f}%;transform:translate(-50%,-50%);"
        f"width:18px;height:18px;border-radius:50%;"
        f"background:{rec_color};border:2.5px solid {BG};"
        f"box-shadow:0 0 10px {rec_color}99;'></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;font-size:.62rem;color:{TX3};margin-top:6px;'>"
        f"<span>מכירה חזקה (−10)</span>"
        f"<span style='color:{TX2};'>ניטרלי (0)</span>"
        f"<span>קנייה חזקה (+10)</span>"
        f"</div></div>"
    )

    st.html(f"""
    <div style="background:{BG};border:1px solid {rec_color}88;border-radius:8px;
        padding:20px 24px;margin-top:16px;direction:rtl;">

        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;
                    padding-bottom:16px;border-bottom:1px solid {BDR2};">
            <div style="font-size:.78rem;color:{TX2};font-weight:600;">המלצת מערכת:</div>
            <div style="font-size:1.8rem;font-weight:900;color:{rec_color};letter-spacing:1px;
                        text-shadow:0 0 20px {rec_color}55;">
                {rec_icon}&nbsp;{rec_label}
            </div>
            <div style="margin-right:auto;background:{SURF2};border-radius:8px;
                        padding:3px 14px;font-size:.78rem;color:{TX2};">
                ציון: <b style="color:{rec_color};">{score:+d}</b> · {len(indicators)} אינדיקטורים
            </div>
        </div>

        {_score_bar}

        {"<div style='margin-top:14px;'><div style='font-size:.78rem;font-weight:700;color:"+GRN+";margin-bottom:6px;'>✅ גורמים תומכים (" + str(len(bullish)) + ")</div>" + bull_html + "</div>" if bullish else ""}
        {"<div style='margin-top:12px;'><div style='font-size:.78rem;font-weight:700;color:"+RED+";margin-bottom:6px;'>❌ גורמים נגד (" + str(len(bearish)) + ") — <span style='font-weight:400;font-size:.72rem;opacity:.75;'>נלקחו בחשבון בציון</span></div>" + bear_html + "</div>" if bearish else ""}
        {"<div style='margin-top:12px;'><div style='font-size:.78rem;font-weight:700;color:"+TX3+";margin-bottom:6px;'>⬜ נייטרלי (" + str(len(neutral)) + ")</div>" + neut_html + "</div>" if neutral else ""}

        <div style="background:{SURF2};border-radius:6px;padding:12px 16px;
                    margin-top:16px;font-size:.79rem;color:{TX2};line-height:1.65;
                    border-right:3px solid {rec_color}66;">
            {risk_msg}
        </div>

        <div style="font-size:.68rem;color:{TX3};margin-top:10px;">
            ניתוח אוטומטי בלבד · אינו מהווה ייעוץ השקעות מוסמך · תאריך: {datetime.now().strftime('%d/%m/%Y')}
        </div>
    </div>
    """)

    # ── Bottom-line plain-language explanation ────────────────────────────────
    action_map = {
        "קנייה חזקה": (f"כן — רוב האינדיקטורים מצביעים על הזדמנות כניסה ל-{sym}", GRN),
        "קנייה":       (f"כן, אך בזהירות — יש יותר סיבות לאופטימיות מאשר לדאגה", GRN),
        "החזקה":       ("לא עכשיו — המתן לאות ברור יותר", AMB),
        "מכירה":       ("לא — שקול להפחית חשיפה", RED),
        "מכירה חזקה":  ("לא — מומלץ לצאת מהפוזיציה", RED),
    }
    action_str, action_color = action_map.get(rec_label, ("לא ברור", TX2))

    why_bullets = "".join(
        f"<li style='margin-bottom:7px;'>"
        f"<span style='font-weight:700;color:{GRN};'>{lbl}</span>"
        f" — <span style='color:{TX};'>{det}</span></li>"
        for ic, lbl, det in bullish
    )
    watch_bullets = "".join(
        f"<li style='margin-bottom:7px;'>"
        f"<span style='font-weight:700;color:{RED};'>{lbl}</span>"
        f" — <span style='color:{TX};'>{det}</span></li>"
        for ic, lbl, det in bearish
    )

    n_total = len(bullish) + len(bearish) + len(neutral)
    if rec_label in ("קנייה חזקה", "קנייה"):
        conclusion = (
            f"מתוך {n_total} אינדיקטורים שנבדקו, {len(bullish)} תומכים בקנייה "
            f"ו-{len(bearish)} מתנגדים. הכף נוטה לטובה — "
            f"אך תמיד כדאי לפזר סיכונים ולא לשים הכול על מניה אחת."
        )
    elif rec_label == "החזקה":
        conclusion = (
            f"האינדיקטורים מאוזנים ({len(bullish)} חיוביים, {len(bearish)} שליליים). "
            f"אם אתה כבר מחזיק — אין סיבה למכור. "
            f"אם אתה שוקל כניסה חדשה — המתן לתנאים בשלים יותר."
        )
    else:
        conclusion = (
            f"מתוך {n_total} אינדיקטורים שנבדקו, {len(bearish)} שליליים מול {len(bullish)} חיוביים. "
            f"הכף נוטה לזהירות — ייתכן שעדיף להמתין לשיפור בתנאים הטכניים."
        )

    why_section = (
        f"<div style='margin-bottom:16px;'>"
        f"<div style='font-size:.8rem;color:{TX3};font-weight:700;margin-bottom:8px;'>"
        f"למה? — הגורמים התומכים:</div>"
        f"<ul style='margin:0;padding-right:20px;font-size:.82rem;line-height:1.8;'>"
        f"{why_bullets}</ul></div>"
    ) if why_bullets else ""

    watch_section = (
        f"<div style='margin-bottom:16px;'>"
        f"<div style='font-size:.8rem;color:{TX3};font-weight:700;margin-bottom:8px;'>"
        f"⚠️ גורמי סיכון שנלקחו בחשבון בציון:</div>"
        f"<ul style='margin:0;padding-right:20px;font-size:.82rem;line-height:1.8;'>"
        f"{watch_bullets}</ul></div>"
    ) if watch_bullets else ""

    st.html(f"""
    <div style="background:{SURF};border:1px solid {BDR2};border-radius:8px;
        padding:20px 24px;margin-top:16px;direction:rtl;">

        <div style="font-size:1rem;font-weight:800;margin-bottom:16px;
                    border-bottom:1px solid {BDR2};padding-bottom:12px;color:{TX};">
            💬 השורה התחתונה — מה זה אומר לי?
        </div>

        <div style="margin-bottom:18px;background:{BG};border-radius:6px;
                    padding:14px 18px;border-right:4px solid {action_color};">
            <div style="font-size:.75rem;color:{TX3};font-weight:700;margin-bottom:6px;">
                האם לקנות את {sym} עכשיו?
            </div>
            <div style="font-size:1.15rem;font-weight:900;color:{action_color};line-height:1.5;
                        text-shadow:0 0 16px {action_color}44;">
                {action_str}
            </div>
        </div>

        {why_section}
        {watch_section}

        <div style="background:{SURF2};border-radius:6px;padding:14px 18px;
                    border-right:4px solid {CYAN};font-size:.84rem;color:{TX};line-height:1.8;">
            <span style="font-weight:700;color:{CYAN};">בשורה האמיתית:</span> {conclusion}
        </div>
    </div>
    """)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME — Hot Stocks Scanner
# ══════════════════════════════════════════════════════════════════════════════
def page_home():
    st_autorefresh(interval=60_000, key="home_refresh")   # every 60 s
    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:16px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            מניות חמות לצפייה
        </div>
        <div style="color:{TX2};font-size:.8rem;margin-top:3px;">
            ניתוח RSI ואות מסחר — מתעדכן כל דקה
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Search any ticker ─────────────────────────────────────────────────────
    sc1, sc2, sc3 = st.columns([2.5, 0.7, 3.8])
    with sc1:
        search_val = st.text_input(
            "", placeholder="🔍 חפש כל מניה לפי סמול — AAPL, TSLA, GOOGL...",
            label_visibility="collapsed", key="search_input"
        ).upper().strip()
    with sc2:
        do_search = st.button("חפש", key="search_btn", type="primary",
                              use_container_width=True)

    if do_search and search_val:
        st.session_state["search_ticker"] = search_val
        st.session_state["home_selected"] = None
        st.rerun()

    search_sym = st.session_state.get("search_ticker", "")
    if search_sym:
        hdr_c, clr_c = st.columns([6, 1])
        with hdr_c:
            st.markdown(
                f"<div style='direction:rtl;font-size:.85rem;color:{TX2};padding:4px 0;'>"
                f"מציג ניתוח עבור: <b style='color:{CYAN};'>{search_sym}</b></div>",
                unsafe_allow_html=True)
        with clr_c:
            if st.button("✕ נקה", key="clear_search", use_container_width=True):
                st.session_state["search_ticker"] = ""
                st.rerun()
        _stock_detail(search_sym)
        st.markdown(
            f"<div style='height:6px;border-bottom:2px solid {BDR};"
            f"margin-bottom:24px;margin-top:8px;'></div>",
            unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    selected  = st.session_state.get("home_selected")
    watchlist = load_json(WL_FILE)
    mobile    = st.session_state.get("mobile_mode", False)
    col_count = 2 if mobile else 5

    # ── Alerts banner ─────────────────────────────────────────────────────────
    if watchlist:
        alerts = _check_alerts(watchlist)
        if alerts:
            buy_alerts  = [a for a in alerts if a["type"] == "buy"]
            sell_alerts = [a for a in alerts if a["type"] == "sell"]
            parts = []
            if buy_alerts:
                syms = ", ".join(f"<b style='color:{GRN};'>{a['sym']}</b> (RSI {a['rsi']:.0f})"
                                 for a in buy_alerts)
                parts.append(f"📉 אות קנייה פוטנציאלי: {syms}")
            if sell_alerts:
                syms = ", ".join(f"<b style='color:{RED};'>{a['sym']}</b> (RSI {a['rsi']:.0f})"
                                 for a in sell_alerts)
                parts.append(f"📈 RSI גבוה — שים לב: {syms}")
            st.html(f"""
            <div style="background:#0a1e10;border:1px solid {GRN}55;border-radius:6px;
                padding:10px 16px;margin-bottom:16px;direction:rtl;font-size:.83rem;color:{TX};">
                🔔 <b style="color:{GRN};">התראות ממניות המעקב שלך:</b>
                {"&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)}
            </div>
            """)

    # ── Prefetch all HOT quotes in parallel ───────────────────────────────────
    with st.spinner("מעדכן נתוני שוק..."):
        hot_quotes = _prefetch_quotes([s["t"] for s in HOT])

    for row_start in range(0, len(HOT), col_count):
        cols = st.columns(col_count, gap="small")
        for i, col in enumerate(cols):
            if row_start + i >= len(HOT):
                break
            s = HOT[row_start + i]
            q = hot_quotes.get(s["t"], {})

            price_str = f"${q['price']:,.2f}"    if q else "—"
            chg_str   = (f"+{q['chg']:.1f}%" if q.get("chg",0)>=0
                         else f"{q['chg']:.1f}%") if q else "—"
            chg_c     = (GRN if q.get("chg",0)>=0 else RED) if q else TX3
            rsi_str   = f"{q['rsi']:.0f}"       if q else "—"
            sig       = q.get("sig","—")          if q else "—"
            sig_c     = q.get("sig_c", TX3)       if q else TX3
            is_sel    = (selected == s["t"])
            border    = f"border:2px solid {CYAN};" if is_sel else f"border:1px solid {BDR};"

            col.markdown(f"""<div class="scard" style="{border}border-top:3px solid {s['a']};">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;margin-bottom:7px;">
                    <div style="font-size:1.15rem;font-weight:900;color:{s['a']};
                                letter-spacing:-.01em;">
                        {s['t']}
                    </div>
                    <div style="font-size:.62rem;background:{s['a']}1e;color:{s['a']};
                                padding:3px 8px;border-radius:6px;white-space:nowrap;
                                border:1px solid {s['a']}33;">
                        {s['c']}
                    </div>
                </div>
                <div style="font-size:.73rem;color:{TX2};margin-bottom:10px;line-height:1.4;">
                    {s['n']}
                </div>
                <div style="font-size:1.55rem;font-weight:800;color:{TX};
                            margin-bottom:2px;letter-spacing:-.02em;">
                    {price_str}
                </div>
                <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:9px;">
                    <span style="color:{chg_c};font-weight:700;font-size:.88rem;">
                        {chg_str}
                    </span>
                    <span style="background:{sig_c}1e;color:{sig_c};font-size:.71rem;
                                 font-weight:700;padding:3px 10px;border-radius:6px;
                                 border:1px solid {sig_c}33;">
                        {sig}
                    </span>
                </div>
                <div style="font-size:.71rem;color:{TX3};
                            border-top:1px solid {BDR};padding-top:7px;margin-bottom:7px;">
                    RSI: <span style="color:{TX2};font-weight:600;">{rsi_str}</span>
                </div>
                <div style="font-size:.75rem;color:{TX2};line-height:1.55;margin-bottom:10px;">
                    {s['w']}
                </div>
            </div>""", unsafe_allow_html=True)

            # ── Action buttons under each card ────────────────────────────────
            b1, b2 = col.columns(2)
            with b1:
                if st.button("📊 ניתוח", key=f"h_ana_{s['t']}",
                             use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state["home_selected"] = (
                        None if is_sel else s["t"]
                    )
                    st.rerun()
            with b2:
                in_wl  = s["t"] in watchlist
                wl_lbl = "✓ מעקב" if in_wl else "👁️ מעקב"
                if st.button(wl_lbl, key=f"h_wl_{s['t']}",
                             use_container_width=True,
                             type="primary" if in_wl else "secondary"):
                    if not in_wl:
                        watchlist.append(s["t"])
                        save_json(WL_FILE, watchlist)
                        st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Detail panel (below all cards) ───────────────────────────────────────
    if selected:
        _stock_detail(selected)


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO ANALYTICS — P&L chart + sector pie
# ══════════════════════════════════════════════════════════════════════════════
def _portfolio_analytics(portfolio: list, pf_quotes: dict):
    if not portfolio:
        return

    st.markdown(f"""<div style="margin-top:28px;border-top:1px solid {BDR};
        padding-top:22px;direction:rtl;">
        <div style="font-size:1rem;font-weight:800;margin-bottom:16px;color:{TX};">
            ניתוח ביצועים
        </div></div>""", unsafe_allow_html=True)

    all_syms = list({h["sym"] for h in portfolio}) + ["SPY", "QQQ", "^TA35.TA"]

    with st.spinner("מחשב ביצועי תיק..."):
        hist: dict = {}
        def _fetch_sym(sym):
            try:    return sym, fetch_history(sym, "1y")
            except: return sym, pd.DataFrame()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for sym, df in ex.map(_fetch_sym, all_syms):
                if not df.empty:
                    hist[sym] = df

    # Build combined daily portfolio value
    portfolio_series: dict = {}
    for h in portfolio:
        sym      = h["sym"]
        shares   = h["shares"]
        buy_date = pd.Timestamp(h.get("buy_date", "2020-01-01"))
        if sym not in hist:
            continue
        df = hist[sym]
        df = df[df.index >= buy_date]
        for date, row in df.iterrows():
            d = date.date()
            portfolio_series[d] = portfolio_series.get(d, 0) + float(row["Close"]) * shares

    if not portfolio_series:
        return

    dates   = sorted(portfolio_series.keys())
    pf_vals = [portfolio_series[d] for d in dates]
    pf_pct  = [(v / pf_vals[0] - 1) * 100 for v in pf_vals]
    pf_color = GRN if pf_pct[-1] >= 0 else RED

    col_chart, col_pie = st.columns([2.2, 1])

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=pf_pct, name="התיק שלי",
            line=dict(color=pf_color, width=2.5),
            fill="tozeroy", fillcolor=f"rgba({'34,197,94' if pf_pct[-1]>=0 else '239,68,68'},0.07)",
        ))
        benchmarks = [("SPY","S&P 500",TX3,"dot"),
                      ("QQQ","נאסד\"ק",PUR,"dash"),
                      ("^TA35.TA","ת\"א 35",AMB,"dashdot")]
        for bsym, bname, bcol, bdash in benchmarks:
            bdf = hist.get(bsym)
            if bdf is not None and not bdf.empty:
                bdf2 = bdf[bdf.index >= pd.Timestamp(dates[0])]
                if not bdf2.empty:
                    bv   = bdf2["Close"].tolist()
                    bpct = [(v / bv[0] - 1) * 100 for v in bv]
                    fig.add_trace(go.Scatter(
                        x=[d.date() for d in bdf2.index], y=bpct,
                        name=bname, line=dict(color=bcol, width=1.5, dash=bdash),
                    ))
        fig.add_hline(y=0, line=dict(color=BDR2, dash="dot", width=1))
        fig.update_layout(
            **{**PB, "height": 290},
            yaxis_ticksuffix="%", yaxis_title="תשואה",
            title=dict(text="ביצועי תיק מול מדדים", font=dict(color=TX, size=13), x=0),
            xaxis_rangeslider_visible=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_pie:
        sector_map = {s["t"]: s.get("s", s.get("c", "אחר")) for s in DEEP_SCAN_UNIVERSE}
        for h in HOT:
            sector_map.setdefault(h["t"], h.get("c", "Tech"))
        sectors: dict = {}
        for h in portfolio:
            sym = h["sym"]
            q   = pf_quotes.get(sym, {})
            cur = float(q.get("price") or h["buy_price"]) * h["shares"]
            sec = sector_map.get(sym, sym)
            sectors[sec] = sectors.get(sec, 0) + cur
        colors = [CYAN, PUR, GRN, AMB, RED, "#60a5fa", "#f472b6", TX2]
        fig2 = go.Figure(go.Pie(
            labels=list(sectors.keys()), values=list(sectors.values()),
            hole=0.5, textinfo="percent",
            textfont=dict(color=TX, size=10),
            marker=dict(colors=colors[:len(sectors)], line=dict(color=BG, width=2)),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            **{**PB, "height": 290},
            showlegend=True,
            legend=dict(font=dict(size=9, color=TX2), orientation="v",
                        yanchor="middle", y=0.5, xanchor="left", x=1.02),
            title=dict(text="פילוח סקטוריאלי", font=dict(color=TX, size=13), x=0),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO — התיק שלי
# ══════════════════════════════════════════════════════════════════════════════
def page_portfolio():
    st_autorefresh(interval=30_000, key="pf_refresh_auto")   # every 30 s
    portfolio = load_json(PF_FILE)

    hdr1, hdr2 = st.columns([5, 1])
    with hdr1:
        st.markdown(f"""<div class="section-head">💼 התיק שלי</div>""",
                    unsafe_allow_html=True)
    with hdr2:
        if st.button("🔄 רענן", key="pf_refresh", use_container_width=True,
                     help="עדכן מחירים"):
            fast_price.clear()
            quote.clear()
            st.rerun()

    # ── CSV Import ────────────────────────────────────────────────────────────
    with st.expander("📥 ייבוא תיק מ-CSV / Excel"):
        st.markdown(f"""<div style="direction:rtl;color:{TX2};font-size:.8rem;margin-bottom:8px;">
            העלה קובץ עם עמודות: <b>Ticker, Shares, BuyPrice</b> (ותאריך אופציונלי).
            ייצוא מ-Interactive Brokers, מיטב, בנק הפועלים וכו' עובד ישירות.</div>""",
            unsafe_allow_html=True)
        uploaded = st.file_uploader("בחר קובץ CSV או Excel", type=["csv","xlsx","xls"],
                                    key="pf_upload", label_visibility="collapsed")
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df_up = pd.read_csv(uploaded)
                else:
                    df_up = pd.read_excel(uploaded)
                # Normalize column names
                df_up.columns = [c.strip().lower() for c in df_up.columns]
                col_map = {}
                for c in df_up.columns:
                    if c in ("ticker","symbol","sym","מניה","סמול"):  col_map["sym"] = c
                    if c in ("shares","quantity","כמות","מניות"):     col_map["shares"] = c
                    if c in ("buyprice","buy_price","price","מחיר","עלות"): col_map["price"] = c
                    if c in ("date","buydate","buy_date","תאריך"):    col_map["date"] = c

                if "sym" not in col_map or "shares" not in col_map:
                    st.error("לא נמצאו עמודות Ticker ו-Shares. ודא שהקובץ מכיל אותן.")
                else:
                    preview = df_up[[col_map[k] for k in col_map if k in col_map]].head(5)
                    st.dataframe(preview, use_container_width=True)
                    if st.button("ייבא לתיק ✓", key="pf_import_btn", type="primary"):
                        new_holdings = []
                        for _, row in df_up.iterrows():
                            sym    = str(row[col_map["sym"]]).upper().strip()
                            shares = float(row[col_map["shares"]])
                            price  = float(row[col_map.get("price", col_map["sym"])]) if "price" in col_map else 0.0
                            date   = str(row[col_map["date"]]) if "date" in col_map else datetime.now().strftime("%Y-%m-%d")
                            if sym and shares > 0:
                                new_holdings.append({"sym": sym, "shares": shares,
                                                     "buy_price": price, "buy_date": date[:10]})
                        existing = {h["sym"]: h for h in portfolio}
                        for h in new_holdings:
                            existing[h["sym"]] = h
                        save_json(PF_FILE, list(existing.values()))
                        st.success(f"ייובאו {len(new_holdings)} מניות לתיק!")
                        st.rerun()
            except Exception as e:
                st.error(f"שגיאה בקריאת הקובץ: {e}")

    # ── Add holding form ──────────────────────────────────────────────────────
    prefill = st.session_state.pop("pf_prefill", "")
    with st.expander("➕ הוסף מניה לתיק", expanded=(len(portfolio) == 0 or bool(prefill))):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 1.5, 0.8])
        with c1:
            new_sym = st.text_input("סמול (Ticker)", value=prefill, placeholder="NVDA",
                                    key="pf_sym").upper().strip()
        with c2:
            new_shares = st.number_input("מספר מניות", min_value=0.0001,
                                         value=1.0, step=1.0, key="pf_shares")
        with c3:
            new_bp = st.number_input("מחיר קנייה ($)", min_value=0.01,
                                     value=100.0, step=1.0, key="pf_bp")
        with c4:
            new_date = st.date_input("תאריך קנייה", key="pf_date")
        with c5:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("הוסף ✓", key="pf_add", use_container_width=True,
                         type="primary"):
                if new_sym:
                    portfolio.append({
                        "sym":      new_sym,
                        "shares":   float(new_shares),
                        "buy_price":float(new_bp),
                        "buy_date": str(new_date),
                    })
                    save_json(PF_FILE, portfolio)
                    st.rerun()

    if not portfolio:
        st.markdown(f"""<div style="text-align:center;padding:70px 0;
            color:{TX2};direction:rtl;">
            <div style="font-size:3.5rem;margin-bottom:14px;">📭</div>
            <div style="font-size:1rem;">התיק ריק. הוסף את המניה הראשונה שלך למעלה.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Prefetch all portfolio quotes in parallel ─────────────────────────────
    pf_syms = [h["sym"] for h in portfolio]
    with st.spinner("מעדכן מחירים..."):
        pf_quotes = _prefetch_quotes(pf_syms)

    # ── Compute P&L ──────────────────────────────────────────────────────────
    total_invested = 0.0
    total_current  = 0.0

    # Column headers
    hc = st.columns([1.2, 1.8, 1.1, 1.5, 1.5, 2.0, 0.6])
    for col, lbl in zip(hc, ["סמול","מחיר | שינוי יומי","כמות",
                               "עלות כוללת","שווי נוכחי","רווח / הפסד (כולל)",""]):
        col.markdown(f"<div style='color:{TX3};font-size:.74rem;font-weight:700;"
                     f"direction:rtl;padding-bottom:4px;border-bottom:1px solid {BDR};'>"
                     f"{lbl}</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    to_delete = None
    for i, h in enumerate(portfolio):
        sym    = h["sym"]
        shares = h["shares"]
        bp     = h["buy_price"]

        q     = pf_quotes.get(sym, {})
        price = q.get("price") if q else None
        # fallback to fast_price if quote returned empty
        if not price:
            price = fast_price(sym)
        day_chg = q.get("chg") if q else None  # daily % change

        invested = shares * bp
        total_invested += invested

        if price:
            cur_val  = shares * price
            pnl_usd  = cur_val - invested
            pnl_pct  = pnl_usd / invested * 100
            pnl_c    = GRN if pnl_usd >= 0 else RED
            total_current += cur_val
            curval_s = f"${cur_val:,.0f}"
            pnl_s    = (f"+${pnl_usd:,.0f}" if pnl_usd >= 0 else f"-${abs(pnl_usd):,.0f}")
            pnl_pct_s= f"{pnl_pct:+.1f}%"
            # Daily change badge
            if day_chg is not None:
                dchg_c   = GRN if day_chg >= 0 else RED
                dchg_arr = "▲" if day_chg >= 0 else "▼"
                price_s  = (f"<span style='font-weight:700;'>${price:,.2f}</span>"
                            f"&nbsp;<span style='font-size:.75rem;color:{dchg_c};"
                            f"font-weight:600;'>{dchg_arr} {abs(day_chg):.1f}%</span>")
            else:
                price_s = f"<span style='font-weight:700;'>${price:,.2f}</span>"
        else:
            pnl_c    = TX2
            price_s  = "<span style='color:#3a6080;'>טוען...</span>"
            curval_s = "..."
            pnl_s    = "..."
            pnl_pct_s= ""

        bg = f"background:{SURF}" if i % 2 == 0 else f"background:{SURF2}"
        rc = st.columns([1.2, 1.8, 1.1, 1.5, 1.5, 2.0, 0.6])
        with rc[0]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<b style='color:{CYAN};'>{sym}</b></div>",
                        unsafe_allow_html=True)
        with rc[1]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;color:{TX};'>"
                        f"{price_s}</div>", unsafe_allow_html=True)
        with rc[2]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;color:{TX2};'>"
                        f"{shares:g}</div>", unsafe_allow_html=True)
        with rc[3]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;color:{TX2};'>"
                        f"${invested:,.0f}</div>", unsafe_allow_html=True)
        with rc[4]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"{curval_s}</div>", unsafe_allow_html=True)
        with rc[5]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<span style='color:{pnl_c};font-weight:700;'>{pnl_s}</span>"
                        f"<span style='color:{pnl_c};font-size:.78rem;margin-right:6px;'>"
                        f"{pnl_pct_s}</span></div>", unsafe_allow_html=True)
        with rc[6]:
            if st.button("✕", key=f"pf_del_{i}", help="הסר מהתיק"):
                to_delete = i

    if to_delete is not None:
        portfolio.pop(to_delete)
        save_json(PF_FILE, portfolio)
        st.rerun()

    # ── Summary bar ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if total_current > 0:
        total_pnl     = total_current - total_invested
        total_pnl_pct = total_pnl / total_invested * 100 if total_invested else 0
        pnl_c         = GRN if total_pnl >= 0 else RED

        sc = st.columns(3)
        for col, lbl, val, vc in [
            (sc[0], "סך הושקע",        f"${total_invested:,.0f}",  TX),
            (sc[1], "שווי נוכחי",       f"${total_current:,.0f}",   CYAN),
            (sc[2], "רווח / הפסד כולל", f"{'+'if total_pnl>=0 else ''}${total_pnl:,.0f}  ({total_pnl_pct:+.1f}%)", pnl_c),
        ]:
            col.markdown(f"""<div class="sumcard">
                <div style="font-size:.78rem;color:{TX2};margin-bottom:6px;">{lbl}</div>
                <div style="font-size:1.35rem;font-weight:800;color:{vc};">{val}</div>
            </div>""", unsafe_allow_html=True)

        _portfolio_analytics(portfolio, pf_quotes)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WATCHLIST — מניות במעקב
# ══════════════════════════════════════════════════════════════════════════════
def page_watchlist():
    watchlist = load_json(WL_FILE)

    st.markdown(f"""<div class="section-head">👁️ מניות במעקב</div>""",
                unsafe_allow_html=True)

    # ── Add ticker ────────────────────────────────────────────────────────────
    ac1, ac2, _ = st.columns([1.5, 0.8, 4])
    with ac1:
        add_sym = st.text_input("", placeholder="הוסף סמול (AAPL, TSLA...)",
                                label_visibility="collapsed",
                                key="wl_input").upper().strip()
    with ac2:
        if st.button("➕ הוסף", key="wl_add", type="primary",
                     use_container_width=True):
            if not add_sym:
                st.warning("הזן סמול מניה")
            elif add_sym in (watchlist if isinstance(watchlist, list) else []):
                st.info(f"{add_sym} כבר ברשימה")
            else:
                wl = watchlist if isinstance(watchlist, list) else []
                wl.append(add_sym)
                ok = save_json(WL_FILE, wl)
                if ok:
                    st.rerun()
                else:
                    st.error("שגיאה בשמירה — נסה שוב")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if not watchlist:
        st.markdown(f"""<div style="text-align:center;padding:70px 0;
            color:{TX2};direction:rtl;">
            <div style="font-size:3.5rem;margin-bottom:14px;">🔍</div>
            <div>אין מניות ברשימת המעקב. הוסף את הראשונה למעלה.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Header ────────────────────────────────────────────────────────────────
    hc = st.columns([1, 1.6, 1.4, 1.4, 1.4, 0.6])
    for col, lbl in zip(hc, ["סמול","מחיר","שינוי יומי","RSI","אות מסחר",""]):
        col.markdown(f"<div style='color:{TX3};font-size:.74rem;font-weight:700;"
                     f"direction:rtl;padding-bottom:4px;border-bottom:1px solid {BDR};'>"
                     f"{lbl}</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    to_remove = None
    for i, sym in enumerate(watchlist):
        q  = quote(sym)
        bg = f"background:{SURF}" if i % 2 == 0 else f"background:{SURF2}"

        price_s = f"${q['price']:,.2f}"              if q else "—"
        chg_s   = (f"+{q['chg']:.1f}%" if q.get("chg",0) >= 0
                   else f"{q['chg']:.1f}%")          if q else "—"
        chg_c   = (GRN if q.get("chg", 0) >= 0 else RED) if q else TX2
        rsi_s   = f"{q['rsi']:.0f}"                 if q else "—"
        sig     = q.get("sig", "—")                  if q else "—"
        sig_c   = q.get("sig_c", TX3)                if q else TX3

        rc = st.columns([1, 1.6, 1.4, 1.4, 1.4, 0.6])
        with rc[0]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<b style='color:{CYAN};'>{sym}</b></div>",
                        unsafe_allow_html=True)
        with rc[1]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"{price_s}</div>", unsafe_allow_html=True)
        with rc[2]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<span style='color:{chg_c};font-weight:600;'>{chg_s}</span>"
                        f"</div>", unsafe_allow_html=True)
        with rc[3]:
            # RSI color
            rsi_val = q.get("rsi", 50) if q else 50
            rsi_c = GRN if rsi_val < 35 else RED if rsi_val > 65 else TX2
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<span style='color:{rsi_c};font-weight:600;'>{rsi_s}</span>"
                        f"</div>", unsafe_allow_html=True)
        with rc[4]:
            st.markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                        f"<span style='background:{sig_c}22;color:{sig_c};"
                        f"font-size:.76rem;font-weight:700;padding:4px 12px;"
                        f"border-radius:6px;'>{sig}</span></div>",
                        unsafe_allow_html=True)
        with rc[5]:
            if st.button("✕", key=f"wl_del_{i}", help="הסר מהרשימה"):
                to_remove = i

    if to_remove is not None:
        watchlist.pop(to_remove)
        save_json(WL_FILE, watchlist)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DEMO — סימולציית דמו
# ══════════════════════════════════════════════════════════════════════════════
# ── helpers ──────────────────────────────────────────────────────────────────
def _trade_line(t: dict) -> str:
    """One-line Hebrew trade description."""
    if t["action"] == "buy":
        return (f"{t['date']} — קניתי {t['sym']} ב-${t['price']:,.2f} | {t['reason']}")
    else:
        sign = "+" if (t.get("pnl_dollar") or 0) >= 0 else ""
        return (f"{t['date']} — מכרתי {t['sym']} ב-${t['price']:,.2f} | "
                f"{sign}${t.get('pnl_dollar',0):,.0f} ({t.get('pnl_pct',0):+.1f}%) | "
                f"{t['reason']}")

def _trade_color(t: dict) -> str:
    if t["action"] == "buy": return GRN
    return GRN if (t.get("pnl_dollar") or 0) >= 0 else RED

def _draw_portfolio_chart(dates, values, bh_vals, budget, target_val,
                          target_pct, tgt_date=None) -> go.Figure:
    fig = go.Figure()
    fig.add_hline(y=budget, line=dict(color=TX3, dash="dot", width=1))
    fig.add_hline(y=target_val,
                  line=dict(color=AMB, dash="dash", width=1.5),
                  annotation_text=f"יעד {target_pct:.0f}%",
                  annotation_font_color=AMB)
    fig.add_trace(go.Scatter(x=dates, y=bh_vals, name="קנה והחזק",
                             line=dict(color=TX3, width=1.5, dash="dot"),
                             fill="tozeroy", fillcolor="rgba(107,155,192,.03)"))
    fig.add_trace(go.Scatter(x=dates, y=values, name="AI",
                             line=dict(color=CYAN, width=2.5),
                             fill="tozeroy", fillcolor="rgba(0,180,216,.07)"))
    if tgt_date:
        try:
            td = datetime.strptime(tgt_date, "%d/%m/%Y")
            fig.add_trace(go.Scatter(x=[td], y=[target_val], mode="markers",
                name="יעד הושג",
                marker=dict(symbol="star", color=AMB, size=16,
                            line=dict(color=BG, width=1))))
        except Exception:
            pass
    fig.update_layout(**{**PB, "height": 360, "yaxis_title": "שווי תיק ($)"})
    return fig


# ── Setup screen ─────────────────────────────────────────────────────────────
def _demo_setup():
    S = st.session_state

    # ── Section 1: Scenario cards ─────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1rem;font-weight:800;color:{TX};direction:rtl;'
        f'margin-bottom:14px;">⚡ בחר תרחיש מוכן — לחץ להפעלה מיידית</div>',
        unsafe_allow_html=True)

    row1 = st.columns(3, gap="small")
    row2 = st.columns(3, gap="small")
    all_cols = row1 + row2

    for col, sc in zip(all_cols, MARKET_SCENARIOS):
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(150deg,{SURF},{sc["color"]}12);'
                f'border:1px solid {sc["color"]}44;border-top:3px solid {sc["color"]};'
                f'border-radius:8px;padding:14px 16px;direction:rtl;min-height:110px;">'
                f'<div style="font-size:1rem;font-weight:900;color:{sc["color"]};'
                f'margin-bottom:5px;">{sc["name"]}</div>'
                f'<div style="font-size:.73rem;color:{TX2};line-height:1.5;">{sc["story"]}</div>'
                f'<div style="font-size:.68rem;color:{TX3};margin-top:5px;">{sc["detail"]}</div>'
                f'</div>', unsafe_allow_html=True)
            if st.button(f'{sc["emoji"]} הפעל', key=f"sc_{sc['id']}",
                         use_container_width=True):
                S["demo2_tickers"]    = sc["tickers"]
                S["demo2_start_year"] = sc["years"][0]
                S["demo2_end_year"]   = sc["years"][1]
                S["demo2_risk"]       = sc["risk"]
                S["demo2_strategy"]   = sc["strategy"]
                S["demo2_budget"]     = S.get("demo2_budget", 10000.0)
                S["demo2_target_pct"] = S.get("demo2_target_pct", 50.0)
                S["demo2_speed"]      = S.get("demo2_speed", "רגיל")
                S["demo2_state"]      = "computing"
                st.rerun()

    # ── Section 2: Strategy selector ─────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:1rem;font-weight:800;color:{TX};direction:rtl;'
        f'margin-bottom:12px;">🧠 בחר אסטרטגיית מסחר</div>',
        unsafe_allow_html=True)

    strat_names = list(STRATEGY_PROFILES.keys())
    cur_strat   = S.get("demo2_strategy", strat_names[0])
    if cur_strat not in strat_names:
        cur_strat = strat_names[0]

    scols = st.columns(3, gap="small")
    for col, sname in zip(scols, strat_names):
        sp      = STRATEGY_PROFILES[sname]
        is_sel  = (sname == cur_strat)
        bdr_c   = CYAN if is_sel else BDR
        bg      = f"{CYAN}14" if is_sel else SURF
        with col:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {bdr_c};'
                f'border-radius:6px;padding:14px;direction:rtl;min-height:90px;">'
                f'<div style="font-size:.9rem;font-weight:800;color:{TX if is_sel else TX2};">'
                f'{sname}</div>'
                f'<div style="font-size:.72rem;color:{TX2};margin-top:6px;line-height:1.5;">'
                f'{sp["desc"]}</div>'
                f'</div>', unsafe_allow_html=True)
            if st.button("✓ בחר" if is_sel else "בחר", key=f"strat_{sname}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                S["demo2_strategy"] = sname
                st.rerun()

    # ── Section 3: Custom setup ───────────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    with st.expander("⚙️ הגדרות מתקדמות — תאריכים, מניות ותקציב"):
        c1, c2 = st.columns(2)
        with c1:
            budget = st.number_input("💰 תקציב התחלתי ($)",
                                      min_value=1000, max_value=10_000_000,
                                      value=int(S["demo2_budget"]), step=1000,
                                      key="d2_budget")
        with c2:
            target_pct = st.number_input("🎯 יעד רווח (%)",
                                          min_value=5, max_value=2000,
                                          value=int(S["demo2_target_pct"]), step=5,
                                          key="d2_target")
        c3, c4 = st.columns(2)
        with c3:
            years      = list(range(2010, 2025))
            start_year = st.selectbox("📅 שנת התחלה", years,
                                       index=years.index(S["demo2_start_year"]),
                                       key="d2_sy")
        with c4:
            eyears   = list(range(2011, 2026))
            end_year = st.selectbox("📅 שנת סיום", eyears,
                                     index=eyears.index(min(S["demo2_end_year"], 2025)),
                                     key="d2_ey")

        opts    = [f"{sym} — {name}" for sym, name in TRADEABLE]
        default = [f"{sym} — {name}" for sym, name in TRADEABLE
                   if sym in S["demo2_tickers"]]
        sel = st.multiselect("📋 מניות לסחור (עד 12)", opts,
                              default=default, max_selections=12, key="d2_tickers_sel")

        risk  = st.radio("⚖️ רמת סיכון", ["שמרני","מאוזן","אגרסיבי"],
                          index=["שמרני","מאוזן","אגרסיבי"].index(S["demo2_risk"]),
                          horizontal=True, key="d2_risk")
        speed = st.radio("⚡ מהירות אנימציה", ["איטי","רגיל","מהיר"],
                          index=["איטי","רגיל","מהיר"].index(S["demo2_speed"]),
                          horizontal=True, key="d2_speed")

        if st.button("🚀 הפעל סימולציה מותאמת אישית", type="primary", key="d2_go"):
            tickers = [o.split(" — ")[0] for o in sel]
            if not tickers:
                st.error("בחר לפחות מניה אחת.")
            elif start_year >= end_year:
                st.error("שנת ההתחלה חייבת להיות לפני שנת הסיום.")
            else:
                S["demo2_budget"]     = float(budget)
                S["demo2_target_pct"] = float(target_pct)
                S["demo2_start_year"] = start_year
                S["demo2_end_year"]   = end_year
                S["demo2_tickers"]    = tickers
                S["demo2_risk"]       = risk
                S["demo2_speed"]      = speed
                S["demo2_state"]      = "computing"
                st.rerun()


# ── Animation screen ──────────────────────────────────────────────────────────
def _demo_animate():
    S        = st.session_state
    r        = S["demo2_results"]
    frame    = S["demo2_frame"]
    speed    = S["demo2_speed"]
    budget   = S["demo2_budget"]
    tgt_val  = budget * (1 + S["demo2_target_pct"] / 100)
    total    = len(r["daily_vals"])
    steps, delay = ANIM_SPEED[speed]
    new_frame = min(frame + steps, total)

    # Controls
    cc1, cc2, cc3, _ = st.columns([1.1, 1.1, 1.1, 4])
    with cc1:
        if st.button("⏩ דלג לסוף", key="d2_skip", use_container_width=True):
            S["demo2_frame"] = total
            S["demo2_state"] = "complete"
            st.rerun()
    with cc2:
        if st.button("⏸️ השהה", key="d2_pause", use_container_width=True):
            S["demo2_frame"] = new_frame
            st.rerun()
            return
    with cc3:
        if st.button("⏹️ איפוס", key="d2_reset2", use_container_width=True):
            S["demo2_state"] = "setup"
            st.rerun()

    # Progress bar
    pct = new_frame / total * 100
    st.markdown(f"""<div style="background:{BDR};border-radius:4px;height:5px;margin:6px 0 14px;">
        <div style="background:{CYAN};width:{pct:.1f}%;height:100%;border-radius:4px;"></div>
    </div>""", unsafe_allow_html=True)

    # Current values
    dates  = [v[0] for v in r["daily_vals"][:new_frame]]
    values = [v[1] for v in r["daily_vals"][:new_frame]]
    bh     = r["bh_vals"][:new_frame]

    if not dates:
        S["demo2_frame"] = new_frame
        time.sleep(delay)
        st.rerun()
        return

    cur_val = values[-1]
    cur_dt  = dates[-1]
    ret_pct = (cur_val - budget) / budget * 100
    pnl_c   = GRN if ret_pct >= 0 else RED

    # Stats row
    sc = st.columns(4)
    for col, lbl, val, vc in [
        (sc[0], "שווי נוכחי",     f"${cur_val:,.0f}",                      CYAN),
        (sc[1], "תשואה",          f"{ret_pct:+.1f}%",                       pnl_c),
        (sc[2], "תאריך",          cur_dt.strftime("%d/%m/%Y"),               TX2),
        (sc[3], "יעד",            f"${tgt_val:,.0f} ({S['demo2_target_pct']:.0f}%)", AMB),
    ]:
        col.markdown(f"""<div class="sumcard">
            <div style="font-size:.7rem;color:{TX3};margin-bottom:3px;">{lbl}</div>
            <div style="font-size:.92rem;font-weight:700;color:{vc};">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Chart
    fig = _draw_portfolio_chart(dates, values, bh, budget, tgt_val,
                                S["demo2_target_pct"])
    st.plotly_chart(fig, use_container_width=True)

    # Live trade log (last 10 up to current date)
    cur_str = cur_dt.strftime("%d/%m/%Y")
    recent  = [t for t in r["trade_log"] if _date_le(t["date"], cur_str)][-10:]
    if recent:
        st.markdown(f"<div style='font-weight:700;color:{TX};font-size:.86rem;"
                    f"direction:rtl;margin-bottom:8px;'>📋 עסקאות אחרונות</div>",
                    unsafe_allow_html=True)
        for t in reversed(recent):
            bc = _trade_color(t)
            st.markdown(f"""<div style="border-right:3px solid {bc};background:{SURF2};
                border-radius:0 7px 7px 0;padding:8px 12px;margin-bottom:5px;
                font-size:.79rem;color:{TX};direction:rtl;">{_trade_line(t)}</div>""",
                unsafe_allow_html=True)

    # Advance
    S["demo2_frame"] = new_frame
    if new_frame < total:
        time.sleep(delay)
        st.rerun()
    else:
        S["demo2_state"] = "complete"
        st.rerun()


# ── Final report ──────────────────────────────────────────────────────────────
def _demo_report():
    S      = st.session_state
    r      = S["demo2_results"]
    budget = S["demo2_budget"]
    tp     = S["demo2_target_pct"]
    tgt    = budget * (1 + tp / 100)
    ret    = r["total_ret"]
    bh_r   = r["bh_ret"]

    # Grade
    if r["tgt_reached"] and ret > bh_r * 1.3:    grade, gc = "מצוין ⭐", GRN
    elif r["tgt_reached"]:                         grade, gc = "טוב 👍",   CYAN
    elif ret > 0 and ret > bh_r * 0.7:            grade, gc = "בינוני 👌", AMB
    else:                                          grade, gc = "גרוע 👎",  RED

    reached_c = GRN if r["tgt_reached"] else RED
    reached_s = "✅ כן — הגענו ליעד!" if r["tgt_reached"] else "❌ לא הגענו ליעד"

    # Header summary
    strat_lbl = S.get("demo2_strategy", "📊 RSI קלאסי")
    st.markdown(f"""<div style="background:{SURF};border:1px solid {BDR};
        border-radius:8px;padding:24px 28px;direction:rtl;margin-bottom:16px;">
        <div style="font-size:1.1rem;font-weight:800;color:{TX};margin-bottom:4px;">
            📊 דוח סיכום — {S['demo2_start_year']}–{S['demo2_end_year']}
        </div>
        <div style="font-size:.78rem;color:{TX2};margin-bottom:14px;">
            <span style="background:{CYAN}22;color:{CYAN};padding:2px 8px;border-radius:8px;
            border:1px solid {CYAN}44;">{strat_lbl}</span>
            &nbsp;· סיכון: {S['demo2_risk']} ·
            {', '.join(S['demo2_tickers'])}
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
            <div style="background:{SURF2};border-radius:6px;padding:14px;text-align:center;">
                <div style="font-size:.7rem;color:{TX3};margin-bottom:5px;">האם הגענו ליעד?</div>
                <div style="font-size:.95rem;font-weight:700;color:{reached_c};">{reached_s}</div>
                {"<div style='font-size:.74rem;color:"+TX2+";margin-top:4px;'>ב-"+r['tgt_date']+"</div>" if r['tgt_reached'] and r['tgt_date'] else ""}
            </div>
            <div style="background:{SURF2};border-radius:6px;padding:14px;text-align:center;">
                <div style="font-size:.7rem;color:{TX3};margin-bottom:5px;">תשואה כוללת</div>
                <div style="font-size:1.1rem;font-weight:800;color:{GRN if ret>=0 else RED};">{ret:+.1f}%</div>
                <div style="font-size:.74rem;color:{TX2};margin-top:3px;">קנה והחזק: {bh_r:+.1f}%</div>
            </div>
            <div style="background:{SURF2};border-radius:6px;padding:14px;text-align:center;">
                <div style="font-size:.7rem;color:{TX3};margin-bottom:5px;">עודף על קנה-והחזק</div>
                <div style="font-size:1.1rem;font-weight:800;color:{GRN if ret>bh_r else RED};">{ret-bh_r:+.1f}%</div>
            </div>
            <div style="background:{SURF2};border-radius:6px;padding:14px;text-align:center;">
                <div style="font-size:.7rem;color:{TX3};margin-bottom:5px;">ציון AI</div>
                <div style="font-size:1.1rem;font-weight:800;color:{gc};">{grade}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Full chart
    dates  = [v[0] for v in r["daily_vals"]]
    values = [v[1] for v in r["daily_vals"]]
    fig = _draw_portfolio_chart(dates, values, r["bh_vals"], budget, tgt,
                                tp, r.get("tgt_date"))
    st.plotly_chart(fig, use_container_width=True)

    # Stats
    sc = st.columns(4)
    for col, lbl, val, vc in [
        (sc[0], "שווי סופי AI",    f"${r['final_val']:,.0f}",  CYAN),
        (sc[1], "שווי סופי BH",    f"${r['final_bh']:,.0f}",   TX2),
        (sc[2], "עסקאות בוצעו",    str(r["n_buys"]),            TX),
        (sc[3], "רמת סיכון",       S["demo2_risk"],              AMB),
    ]:
        col.markdown(f"""<div class="sumcard">
            <div style="font-size:.7rem;color:{TX3};margin-bottom:4px;">{lbl}</div>
            <div style="font-size:1rem;font-weight:700;color:{vc};">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Best / worst trades
    bt, wt = r.get("best_trade"), r.get("worst_trade")
    if bt or wt:
        bc1, bc2 = st.columns(2)
        if bt:
            bc1.markdown(f"""<div style="background:{SURF};border:1px solid {GRN}55;
                border-radius:6px;padding:16px;direction:rtl;">
                <div style="font-size:.75rem;color:{GRN};font-weight:700;margin-bottom:8px;">
                    🏆 עסקה הטובה ביותר
                </div>
                <div style="font-size:1rem;font-weight:700;color:{TX};">{bt['sym']}</div>
                <div style="font-size:.82rem;color:{TX2};margin-top:4px;">
                    כניסה ב-${bt['entry_price']:,.2f} · יציאה ב-${bt['price']:,.2f}
                </div>
                <div style="font-size:1.1rem;font-weight:800;color:{GRN};margin-top:6px;">
                    +${bt['pnl_dollar']:,.0f} ({bt['pnl_pct']:+.1f}%)
                </div>
            </div>""", unsafe_allow_html=True)
        if wt:
            bc2.markdown(f"""<div style="background:{SURF};border:1px solid {RED}55;
                border-radius:6px;padding:16px;direction:rtl;">
                <div style="font-size:.75rem;color:{RED};font-weight:700;margin-bottom:8px;">
                    💔 עסקה הגרועה ביותר
                </div>
                <div style="font-size:1rem;font-weight:700;color:{TX};">{wt['sym']}</div>
                <div style="font-size:.82rem;color:{TX2};margin-top:4px;">
                    כניסה ב-${wt['entry_price']:,.2f} · יציאה ב-${wt['price']:,.2f}
                </div>
                <div style="font-size:1.1rem;font-weight:800;color:{RED};margin-top:6px;">
                    ${wt['pnl_dollar']:,.0f} ({wt['pnl_pct']:+.1f}%)
                </div>
            </div>""", unsafe_allow_html=True)

    # Full trade log
    st.markdown(f"<div style='font-weight:700;color:{TX};font-size:.9rem;"
                f"direction:rtl;margin:16px 0 10px;'>📋 יומן עסקאות מלא "
                f"({len(r['trade_log'])} פעולות)</div>", unsafe_allow_html=True)
    for t in r["trade_log"]:
        bc = _trade_color(t)
        st.markdown(f"""<div style="border-right:3px solid {bc};background:{SURF2};
            border-radius:0 7px 7px 0;padding:8px 12px;margin-bottom:5px;
            font-size:.79rem;color:{TX};direction:rtl;">{_trade_line(t)}</div>""",
            unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("🔄 סימולציה חדשה", type="primary", key="d2_new"):
        S["demo2_state"] = "setup"
        st.rerun()


# ── Main router for demo page ─────────────────────────────────────────────────
def page_demo():
    S = st.session_state
    st.markdown(f"""<div class="section-head">🎮 סימולטור מסחר אוטונומי</div>""",
                unsafe_allow_html=True)

    state = S.get("demo2_state", "setup")

    if state == "setup":
        _demo_setup()

    elif state == "computing":
        strat_key  = S.get("demo2_strategy", "📊 RSI קלאסי")
        strat_mode = STRATEGY_PROFILES.get(strat_key, {}).get("mode", "rsi")
        with st.spinner(f"⏳ מחשב סימולציה — אסטרטגיית {strat_key}…"):
            results = _run_backtest(
                S["demo2_tickers"], S["demo2_start_year"], S["demo2_end_year"],
                S["demo2_budget"],  S["demo2_target_pct"], S["demo2_risk"],
                strategy_mode=strat_mode,
            )
        if results is None or not results["daily_vals"]:
            st.error("לא ניתן לטעון נתונים לתקופה שנבחרה. נסה מניות אחרות או שנים אחרות.")
            S["demo2_state"] = "setup"
        else:
            S["demo2_results"] = results
            S["demo2_frame"]   = 0
            S["demo2_state"]   = "animating"
        st.rerun()

    elif state == "animating":
        _demo_animate()

    elif state == "complete":
        _demo_report()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMPARE — השוואת מניות
# ══════════════════════════════════════════════════════════════════════════════
def page_compare():
    st.markdown(f"""<div class="section-head">⚖️ השוואת מניות</div>""",
                unsafe_allow_html=True)

    COLORS = [CYAN, AMB, GRN, PUR]
    all_syms = [s["t"] for s in HOT]

    # ── Manual ticker input ───────────────────────────────────────────────────
    mc1, mc2, _ = st.columns([2.2, 0.8, 4])
    with mc1:
        manual = st.text_input("", placeholder="הוסף סמול ידנית — AAPL, MSFT...",
                               label_visibility="collapsed", key="cmp_manual").upper().strip()
    with mc2:
        if st.button("➕ הוסף", key="cmp_add", type="primary", use_container_width=True):
            if manual and manual not in st.session_state["compare_tickers"]:
                st.session_state["compare_tickers"] = (
                    st.session_state["compare_tickers"] + [manual])[:4]
                st.rerun()

    # ── Multiselect ───────────────────────────────────────────────────────────
    sel = st.multiselect(
        "בחר עד 4 מניות להשוואה:",
        all_syms,
        default=[t for t in st.session_state["compare_tickers"] if t in all_syms],
        max_selections=4, key="cmp_sel",
    )
    extra = [t for t in st.session_state["compare_tickers"] if t not in all_syms]
    compare_tickers = list(dict.fromkeys(sel + extra))[:4]
    st.session_state["compare_tickers"] = compare_tickers

    if len(compare_tickers) < 2:
        st.info("בחר לפחות 2 מניות להשוואה.")
        return

    # ── Period ────────────────────────────────────────────────────────────────
    period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y"}
    period_key = st.radio("תקופה:", list(period_map.keys()), index=2,
                           horizontal=True, key="cmp_period")
    period = period_map[period_key]

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("טוען נתוני השוואה..."):
        def _load(sym): return sym, fetch_history(sym, period)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            dfs = {sym: df for sym, df in ex.map(lambda s: _load(s), compare_tickers)
                   if not df.empty}

    if not dfs:
        st.error("לא ניתן לטעון נתונים.")
        return

    # ── Normalized price chart ────────────────────────────────────────────────
    fig1 = go.Figure()
    for i, (sym, df) in enumerate(dfs.items()):
        base = float(df["Close"].iloc[0])
        norm = (df["Close"] / base - 1) * 100
        fig1.add_trace(go.Scatter(x=df.index, y=norm, name=sym,
                                  line=dict(color=COLORS[i % 4], width=2.2)))
    fig1.add_hline(y=0, line=dict(color=TX3, dash="dot", width=1))
    fig1.update_layout(**{**PB, "height": 380,
                          "yaxis_title": f"תשואה % מתחילת {period_key}"})
    st.plotly_chart(fig1, use_container_width=True)

    # ── RSI comparison chart ──────────────────────────────────────────────────
    fig2 = go.Figure()
    for i, (sym, df) in enumerate(dfs.items()):
        if "RSI" in df.columns:
            fig2.add_trace(go.Scatter(x=df.index, y=df["RSI"], name=f"RSI {sym}",
                                      line=dict(color=COLORS[i % 4], width=1.8)))
    fig2.add_hrect(y0=65, y1=100, fillcolor="rgba(239,68,68,0.06)", line_width=0)
    fig2.add_hrect(y0=0, y1=35, fillcolor="rgba(34,197,94,0.06)", line_width=0)
    fig2.add_hline(y=65, line=dict(color=RED, dash="dot", width=1))
    fig2.add_hline(y=35, line=dict(color=GRN, dash="dot", width=1))
    fig2.update_layout(**{**PB, "height": 240, "yaxis_title": "RSI"})
    fig2.update_yaxes(range=[0, 100])
    st.plotly_chart(fig2, use_container_width=True)

    # ── Comparison table ──────────────────────────────────────────────────────
    st.markdown(f"<div style='font-weight:700;color:{TX};font-size:.92rem;"
                f"direction:rtl;margin:14px 0 10px;'>📊 טבלת השוואה</div>",
                unsafe_allow_html=True)

    with st.spinner("טוען נתוני יסוד..."):
        def _load_info(sym): return sym, fetch_info(sym)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            all_info = dict(ex.map(lambda s: _load_info(s), compare_tickers))

    hcols = st.columns([1.1, 1.1, 1.1, 1, 1, 1.2, 1.1, 1.1])
    for col, lbl in zip(hcols, ["מניה","מחיר","שינוי יומי",
                                  f"תשואה {period_key}","RSI",
                                  "שווי שוק","P/E","צמיחה"]):
        col.markdown(f"<div style='color:{TX3};font-size:.73rem;font-weight:700;"
                     f"direction:rtl;border-bottom:1px solid {BDR};padding-bottom:5px;'>"
                     f"{lbl}</div>", unsafe_allow_html=True)

    for i, (sym, df) in enumerate(dfs.items()):
        info  = all_info.get(sym, {})
        cl    = float(df["Close"].iloc[-1])
        prev  = float(df["Close"].iloc[-2]) if len(df) > 1 else cl
        chg   = (cl - prev) / prev * 100
        first = float(df["Close"].iloc[0])
        pret  = (cl / first - 1) * 100
        rsi   = (float(df["RSI"].iloc[-1])
                 if "RSI" in df.columns and not pd.isna(df["RSI"].iloc[-1]) else None)
        mc    = info.get("marketCap")
        pe    = info.get("trailingPE")
        revg  = info.get("revenueGrowth")

        chg_c  = GRN if chg >= 0  else RED
        ret_c  = GRN if pret >= 0 else RED
        rsi_c  = (GRN if rsi and rsi < 35 else RED if rsi and rsi > 65 else TX2)

        rc = st.columns([1.1, 1.1, 1.1, 1, 1, 1.2, 1.1, 1.1])
        bg = f"background:{SURF}" if i % 2 == 0 else f"background:{SURF2}"

        rc[0].markdown(f"<div style='{bg};padding:10px 4px;direction:rtl;'>"
                       f"<b style='color:{COLORS[i%4]};font-size:1rem;'>{sym}</b></div>",
                       unsafe_allow_html=True)
        rc[1].markdown(f"<div style='{bg};padding:10px 4px;'>${cl:,.2f}</div>",
                       unsafe_allow_html=True)
        rc[2].markdown(f"<div style='{bg};padding:10px 4px;'>"
                       f"<span style='color:{chg_c};font-weight:600;'>"
                       f"{'+' if chg>=0 else ''}{chg:.1f}%</span></div>",
                       unsafe_allow_html=True)
        rc[3].markdown(f"<div style='{bg};padding:10px 4px;'>"
                       f"<span style='color:{ret_c};font-weight:600;'>"
                       f"{'+' if pret>=0 else ''}{pret:.1f}%</span></div>",
                       unsafe_allow_html=True)
        rc[4].markdown(f"<div style='{bg};padding:10px 4px;'>"
                       f"<span style='color:{rsi_c};font-weight:600;'>"
                       f"{rsi:.0f if rsi else '—'}</span></div>",
                       unsafe_allow_html=True)
        rc[5].markdown(f"<div style='{bg};padding:10px 4px;color:{TX2};'>"
                       f"{_fmt_large(mc) if mc else '—'}</div>", unsafe_allow_html=True)
        rc[6].markdown(f"<div style='{bg};padding:10px 4px;color:{TX2};'>"
                       f"{f'{pe:.1f}x' if pe else '—'}</div>", unsafe_allow_html=True)
        rc[7].markdown(f"<div style='{bg};padding:10px 4px;'>"
                       f"<span style='color:{GRN if revg and revg>0 else RED};font-weight:600;'>"
                       f"{f'{revg*100:.0f}%' if revg else '—'}</span></div>",
                       unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: NEWS — עדכוני שוק
# ══════════════════════════════════════════════════════════════════════════════
def page_news():
    st_autorefresh(interval=900_000, key="news_refresh_auto")  # every 15 min
    portfolio = load_json(PF_FILE)
    watchlist = load_json(WL_FILE)
    pf_syms   = [h["sym"] for h in portfolio]
    wl_syms   = watchlist if isinstance(watchlist, list) else []
    user_syms = list(dict.fromkeys(pf_syms + wl_syms))

    # ── Header ────────────────────────────────────────────────────────────────
    h1, h2, h3 = st.columns([4, 2, 1])
    with h1:
        st.markdown(f'<div class="section-head">📰 עדכוני שוק</div>',
                    unsafe_allow_html=True)
    with h2:
        st.markdown(
            f"<div style='color:{TX3};font-size:.78rem;direction:rtl;padding-top:14px;'>"
            f"עודכן: {datetime.now().strftime('%d/%m/%Y · %H:%M')}</div>",
            unsafe_allow_html=True)
    with h3:
        if st.button("🔄 רענן", key="news_refresh", use_container_width=True):
            fetch_general_news.clear()
            fetch_market_overview.clear()
            fetch_news.clear()
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # MARKET OVERVIEW BAR
    # ════════════════════════════════════════════════════════════════════════
    with st.spinner("טוען נתוני שוק..."):
        overview = fetch_market_overview()

    if overview:
        tiles = list(overview.items())
        cols  = st.columns(len(tiles))
        for col, (name, d) in zip(cols, tiles):
            chg   = d["chg"]
            color = GRN if chg >= 0 else RED
            arrow = "▲" if chg >= 0 else "▼"
            price = d["price"]
            price_s = (f"${price:,.0f}" if price >= 1000
                       else f"${price:,.2f}" if price >= 1
                       else f"${price:.4f}")
            col.markdown(
                f'<div style="background:{SURF2};border:1px solid {BDR};'
                f'border-top:2px solid {color};border-radius:6px;padding:10px 8px;'
                f'text-align:center;direction:rtl;">'
                f'<div style="font-size:.65rem;color:{TX3};margin-bottom:3px;">{name}</div>'
                f'<div style="font-size:.88rem;font-weight:700;color:{TX};">{price_s}</div>'
                f'<div style="font-size:.72rem;color:{color};font-weight:600;">'
                f'{arrow} {abs(chg):.2f}%</div></div>',
                unsafe_allow_html=True)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — General market news
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{TX};direction:rtl;'
        f'padding:16px 0 12px;border-bottom:2px solid {BDR};margin-bottom:16px;">'
        f'🌍 חדשות שוק כלליות</div>', unsafe_allow_html=True)

    with st.spinner("טוען חדשות מ-RSS ו-Yahoo Finance..."):
        gen_news = fetch_general_news()

    if not gen_news:
        st.markdown(f"<div style='color:{TX2};direction:rtl;'>לא נמצאו חדשות כרגע.</div>",
                    unsafe_allow_html=True)
    else:
        # Filter tabs: All / by category
        CAT_OPTS = ["הכל", "🚀 הנפקות", "📊 רווחים", "🏦 מאקרו", "🤝 מיזוגים"]
        cat_filter = st.radio("סנן חדשות:", CAT_OPTS, horizontal=True, key="news_cat")

        def _cat_match(title):
            ci, _, _ = _categorize(title)
            return {
                "🚀 הנפקות":  ci == "🚀",
                "📊 רווחים":  ci == "📊",
                "🏦 מאקרו":   ci == "🏦",
                "🤝 מיזוגים": ci == "🤝",
            }.get(cat_filter, True)

        shown = [it for it in gen_news if cat_filter == "הכל" or _cat_match(it.get("title",""))]

        st.markdown(
            f"<div style='color:{TX3};font-size:.75rem;direction:rtl;margin-bottom:10px;'>"
            f"{len(shown)} כתבות · לחץ להרחבה</div>", unsafe_allow_html=True)

        for item in shown[:20]:
            title     = item.get("title", "")
            link      = item.get("link", "#")
            publisher = item.get("publisher", "")
            pub_ts    = item.get("providerPublishTime", 0)
            summary   = (item.get("summary") or item.get("description") or "")
            if not title:
                continue

            time_str       = _time_ago(pub_ts) if pub_ts else ""
            src_str        = f"{time_str} — {publisher}" if publisher else time_str
            si, sl, sc     = _sentiment(title)
            cat_i, cat_l, cat_c = _categorize(title)
            heb_title      = translate_to_hebrew(title)

            cat_badge = (
                f"<span style='background:{cat_c}22;color:{cat_c};font-size:.68rem;"
                f"font-weight:700;padding:1px 8px;border-radius:6px;margin-right:6px;'>"
                f"{cat_i} {cat_l}</span>"
            ) if cat_i else ""

            expander_lbl = f"{si} {heb_title}"
            with st.expander(expander_lbl):
                st.markdown(
                    f'<div style="direction:rtl;">'
                    f'<div style="display:flex;align-items:center;gap:6px;'
                    f'flex-wrap:wrap;margin-bottom:8px;">'
                    f'<span style="background:{sc}22;color:{sc};font-size:.72rem;'
                    f'font-weight:700;padding:2px 10px;border-radius:8px;">'
                    f'{si} {sl}</span>{cat_badge}'
                    f'<span style="font-size:.72rem;color:{TX3};">{src_str}</span></div>'
                    + (f'<div style="font-size:.83rem;color:{TX2};line-height:1.65;'
                       f'direction:ltr;margin-bottom:10px;">{summary}</div>' if summary else "")
                    + f'<a href="{link}" target="_blank" '
                      f'style="color:{CYAN};font-size:.78rem;">'
                      f'קרא את הכתבה המלאה ↗</a></div>',
                    unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — News for my stocks
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{TX};direction:rtl;'
        f'padding:16px 0 12px;border-bottom:2px solid {BDR};margin-bottom:16px;">'
        f'📊 חדשות על המניות שלי</div>', unsafe_allow_html=True)

    if not user_syms:
        st.markdown(
            f'<div style="background:{SURF};border:1px solid {BDR};border-radius:6px;'
            f'padding:24px;text-align:center;direction:rtl;color:{TX2};">'
            f'הוסף מניות לתיק או לרשימת המעקב כדי לראות חדשות רלוונטיות.</div>',
            unsafe_allow_html=True)
    else:
        today_ts = int(datetime.combine(datetime.now().date(),
                                        datetime.min.time()).timestamp())

        with st.spinner("טוען חדשות למניות..."):
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(8, len(user_syms))) as ex:
                stock_news = dict(zip(user_syms,
                                      ex.map(fetch_news, user_syms)))

        for sym in user_syms:
            items = stock_news.get(sym, []) or []
            if not items:
                continue

            today_items = [it for it in items
                           if it.get("providerPublishTime", 0) >= today_ts]
            pos_count   = sum(1 for it in today_items
                              if _sentiment(it.get("title", ""))[0] == "🟢")
            neg_count   = sum(1 for it in today_items
                              if _sentiment(it.get("title", ""))[0] == "🔴")
            mostly_neg  = neg_count > pos_count and neg_count > 0

            tag_icon  = "💼" if sym in pf_syms else "👁️"
            tag_lbl   = "תיק" if sym in pf_syms else "מעקב"
            tag_color = CYAN if sym in pf_syms else AMB
            bdr_col   = RED if mostly_neg else BDR2

            badge_neg = (
                f"<span style='background:{RED}22;color:{RED};font-size:.72rem;"
                f"font-weight:700;padding:3px 10px;border-radius:8px;'>"
                f"⚠️ חדשות שליליות</span>" if mostly_neg else "")

            counts_html = ""
            if pos_count:
                counts_html += (f"<span style='color:{GRN};font-weight:700;'>"
                                f"🟢 {pos_count}</span>&nbsp;")
            if neg_count:
                counts_html += (f"<span style='color:{RED};font-weight:700;'>"
                                f"🔴 {neg_count}</span>")
            if today_items:
                counts_html += f"&nbsp;<span style='color:{TX3};font-size:.72rem;'>היום</span>"

            st.markdown(
                f'<div style="background:{SURF};border:1px solid {bdr_col};'
                f'border-radius:6px;padding:16px;margin-bottom:14px;direction:rtl;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-size:1.1rem;font-weight:800;color:{CYAN};">{sym}</span>'
                f'<span style="background:{tag_color}22;color:{tag_color};font-size:.68rem;'
                f'font-weight:700;padding:2px 8px;border-radius:6px;">'
                f'{tag_icon} {tag_lbl}</span>{badge_neg}</div>'
                f'<div style="font-size:.78rem;">{counts_html}</div></div>',
                unsafe_allow_html=True)

            for it in items[:4]:
                t  = it.get("title", "")
                lk = it.get("link", "#")
                pb = it.get("publisher", "")
                ts = it.get("providerPublishTime", 0)
                if not t:
                    continue
                si, sl, sc = _sentiment(t)
                time_s = _time_ago(ts) if ts else ""
                pub_s  = f"&nbsp;·&nbsp;{pb}" if pb else ""
                st.markdown(
                    f'<div style="background:{SURF2};border-right:3px solid {sc};'
                    f'border-radius:0 8px 8px 0;padding:9px 14px;margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:flex-start;gap:8px;flex-wrap:wrap;">'
                    f'<a href="{lk}" target="_blank" style="color:{TX};font-size:.83rem;'
                    f'font-weight:600;text-decoration:none;line-height:1.5;'
                    f'direction:ltr;flex:1;">{t}</a>'
                    f'<span style="background:{sc}22;color:{sc};font-size:.68rem;'
                    f'font-weight:700;padding:2px 7px;border-radius:6px;white-space:nowrap;">'
                    f'{si} {sl}</span></div>'
                    f'<div style="font-size:.7rem;color:{TX3};margin-top:4px;">'
                    f'{time_s}{pub_s}</div></div>',
                    unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Upcoming events
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{TX};direction:rtl;'
        f'padding:16px 0 12px;border-bottom:2px solid {BDR};margin-bottom:16px;">'
        f'📅 אירועים קרובים</div>', unsafe_allow_html=True)

    if not user_syms:
        st.markdown(
            f'<div style="background:{SURF};border:1px solid {BDR};border-radius:6px;'
            f'padding:24px;text-align:center;direction:rtl;color:{TX2};">'
            f'הוסף מניות לתיק או לרשימת המעקב כדי לראות אירועים קרובים.</div>',
            unsafe_allow_html=True)
    else:
        def _fetch_events(sym):
            evts = []
            # Earnings
            cal = fetch_calendar(sym)
            ed  = cal.get("earnings_date")
            if ed:
                ed_ts = pd.Timestamp(ed)
                days  = (ed_ts - pd.Timestamp(datetime.now())).days
                if -7 <= days <= 90:
                    evts.append({
                        "sym": sym, "type": "earnings",
                        "icon": "📋", "label": "דוח רבעוני",
                        "date": ed_ts.strftime("%d/%m/%Y"), "days": days,
                    })
            # Ex-dividend date
            info   = fetch_info(sym)
            ex_div = info.get("exDividendDate")
            if ex_div:
                try:
                    ex_dt = datetime.fromtimestamp(int(ex_div))
                    days  = (ex_dt.date() - datetime.now().date()).days
                    if 0 <= days <= 90:
                        evts.append({
                            "sym": sym, "type": "dividend",
                            "icon": "💰", "label": "תשלום דיבידנד",
                            "date": ex_dt.strftime("%d/%m/%Y"), "days": days,
                        })
                except Exception:
                    pass
            return evts

        with st.spinner("טוען אירועים קרובים..."):
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(8, len(user_syms))) as ex:
                all_evts = []
                for evts in ex.map(_fetch_events, user_syms):
                    all_evts.extend(evts)
            all_evts.sort(key=lambda e: e["days"])

        if not all_evts:
            st.markdown(
                f'<div style="background:{SURF};border:1px solid {BDR};border-radius:6px;'
                f'padding:24px;text-align:center;direction:rtl;color:{TX2};">'
                f'לא נמצאו אירועים קרובים (90 יום) למניות שלך.</div>',
                unsafe_allow_html=True)
        else:
            for evt in all_evts:
                days    = evt["days"]
                is_warn = evt["type"] == "earnings" and 0 <= days <= 7
                bdr_c   = RED if is_warn else (AMB if days <= 14 else BDR)

                if days < 0:
                    days_s = f"לפני {abs(days)} ימים"; days_c = TX3
                elif days == 0:
                    days_s = "היום!"; days_c = RED
                elif days == 1:
                    days_s = "מחר"; days_c = RED
                else:
                    days_s = f"עוד {days} ימים"
                    days_c = AMB if days <= 7 else (CYAN if days <= 14 else TX2)

                warn_str = "⚠️ " if is_warn else ""
                tag_icon = "💼" if evt["sym"] in pf_syms else "👁️"

                st.markdown(
                    f'<div style="background:{SURF};border:1px solid {bdr_c};'
                    f'border-radius:6px;padding:14px 18px;margin-bottom:8px;direction:rtl;'
                    f'display:flex;justify-content:space-between;align-items:center;'
                    f'flex-wrap:wrap;gap:8px;">'
                    f'<div style="display:flex;align-items:center;gap:12px;">'
                    f'<span style="font-size:1.3rem;">{evt["icon"]}</span>'
                    f'<div>'
                    f'<div style="font-size:.88rem;font-weight:700;color:{TX};">'
                    f'{warn_str}{evt["sym"]} {tag_icon} — {evt["label"]}</div>'
                    f'<div style="font-size:.75rem;color:{TX3};margin-top:2px;">'
                    f'{evt["date"]}</div></div></div>'
                    f'<div style="background:{days_c}22;color:{days_c};font-size:.82rem;'
                    f'font-weight:700;padding:4px 14px;border-radius:8px;">'
                    f'{days_s}</div></div>',
                    unsafe_allow_html=True)

    st.markdown(
        f'<div style="text-align:center;color:{TX3};font-size:.72rem;'
        f'margin-top:28px;direction:rtl;padding-bottom:8px;">'
        f'🔄 הנתונים מתרעננים אוטומטית כל 15 דקות · '
        f'לרענון מידי לחץ על 🔄 רענן</div>',
        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AGENTS — מרכז סוכנים
# ══════════════════════════════════════════════════════════════════════════════
def page_agents():
    st_autorefresh(interval=15_000, key="agents_refresh_auto")

    AGENT_META = [
        ("monitor", "📡", "סוכן ניטור",
         "בודק ירידות, RSI ופריצות MA50 בתיק ובמעקב", 30),
        ("scanner", "🔍", "סוכן סריקה AI",
         f"סורק {len(DEEP_SCAN_UNIVERSE)}+ מניות עצמאית — מזהה נפח חריג, פריצות והתאוששות RSI", 30),
        ("news",    "📰", "סוכן חדשות",
         "מנתח סנטימנט חדשות ומדגיל עודף שלילי", 15),
    ]
    AGENT_FNS   = {"monitor": _run_monitor, "scanner": _run_deep_scanner, "news": _run_news_agent}
    AGENT_ICONS = {"monitor": "📡", "scanner": "🔍", "news": "📰"}

    # ── Header ────────────────────────────────────────────────────────────────
    hh1, hh2 = st.columns([5, 1])
    with hh1:
        st.markdown(f'<div class="section-head">🤖 מרכז סוכנים</div>',
                    unsafe_allow_html=True)
    with hh2:
        if st.button("🔄 רענן", key="ag_pg_refresh", use_container_width=True):
            st.rerun()

    # ── Agent status cards ────────────────────────────────────────────────────
    state = _load_agent_state()
    cols  = st.columns(3, gap="medium")

    for col, (name, icon, label, desc, interval) in zip(cols, AGENT_META):
        ag       = state.get(name, {"enabled": True, "status": "ממתין", "last_run": None})
        enabled  = ag.get("enabled", True)
        status   = ag.get("status", "ממתין")
        last_run = ag.get("last_run") or "טרם רץ"
        alive    = (t := _agent_threads.get(name)) is not None and t.is_alive()

        si, sc = (("⚫", TX3) if not enabled else
                  ("🟢", GRN) if status == "פעיל" else
                  ("🔴", RED) if status == "שגיאה" else ("🟡", AMB))
        if not enabled: status = "כבוי"
        bdr = CYAN if (enabled and alive) else BDR

        with col:
            st.markdown(
                f'<div style="background:linear-gradient(160deg,{SURF},#0b1b2f);'
                f'border:1px solid {bdr};border-top:3px solid {sc};'
                f'border-radius:8px;padding:18px;direction:rtl;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;margin-bottom:8px;">'
                f'<div style="font-size:1rem;font-weight:800;color:{TX};">{icon} {label}</div>'
                f'<div style="font-size:.78rem;font-weight:700;color:{sc};">{si} {status}</div>'
                f'</div>'
                f'<div style="font-size:.75rem;color:{TX2};margin-bottom:12px;line-height:1.5;">'
                f'{desc}</div>'
                f'<div style="font-size:.71rem;color:{TX3};margin-bottom:2px;">'
                f'🕐 ריצה אחרונה: {last_run}</div>'
                f'<div style="font-size:.71rem;color:{TX3};">'
                f'⏱️ תדירות: כל {interval} דקות</div></div>',
                unsafe_allow_html=True)

            bc1, bc2 = st.columns(2)
            with bc1:
                tog_lbl = "⏸ השבת" if enabled else "▶ הפעל"
                if st.button(tog_lbl, key=f"ag_tog_{name}", use_container_width=True):
                    ag["enabled"] = not enabled
                    ag["status"]  = "ממתין" if not enabled else "כבוי"
                    state[name]   = ag
                    _save_agent_state(state); _ensure_agents(); st.rerun()
            with bc2:
                if st.button("▶ הרץ עכשיו", key=f"ag_run_{name}", use_container_width=True):
                    with st.spinner(f"מריץ {label}..."):
                        try:
                            AGENT_FNS[name]()
                            state = _load_agent_state()
                            state[name]["status"]   = "ממתין"
                            state[name]["last_run"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            _save_agent_state(state)
                        except Exception as exc:
                            state = _load_agent_state()
                            state[name]["status"] = "שגיאה"
                            _save_agent_state(state)
                            _add_log(name, f"שגיאה ידנית: {str(exc)[:100]}")
                    st.rerun()

    # ── Scanner settings panel ────────────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    with st.expander("⚙️ הגדרות סוכן הסריקה AI"):
        state = _load_agent_state()
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            freq_opts   = {"כל 30 דקות": 30, "כל שעה": 60, "כל 3 שעות": 180}
            cur_freq    = state.get("scanner_interval", 30)
            cur_lbl     = next((k for k, v in freq_opts.items() if v == cur_freq), "כל 30 דקות")
            freq_sel    = st.selectbox("תדירות סריקה", list(freq_opts.keys()),
                                       index=list(freq_opts.keys()).index(cur_lbl),
                                       key="scanner_freq_sel")
        with sc2:
            conf_opts   = ["שווה מעקב", "בינוני", "גבוה"]
            cur_conf    = state.get("scanner_min_confidence", "שווה מעקב")
            conf_sel    = st.selectbox("רמת ביטחון מינימלית להתראה", conf_opts,
                                       index=conf_opts.index(cur_conf)
                                       if cur_conf in conf_opts else 0,
                                       key="scanner_conf_sel")
        with sc3:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("💾 שמור הגדרות", key="scanner_save", use_container_width=True):
                state["scanner_interval"]         = freq_opts[freq_sel]
                state["scanner_min_confidence"]   = conf_sel
                _save_agent_state(state)
                st.success("✅ הגדרות נשמרו")
        st.markdown(
            f'<div style="font-size:.74rem;color:{TX3};direction:rtl;margin-top:8px;">'
            f'הסוכן סורק {len(DEEP_SCAN_UNIVERSE)}+ מניות כולל small-cap ומניות לא מוכרות · '
            f'מחפש: נפח חריג, RSI מתאושש, פריצות התנגדות, צבירה מוסדית שקטה, קרוב לשפל שנתי</div>',
            unsafe_allow_html=True)

    # ── Notification centre ───────────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    uc = _unread_count()
    nc1, nc2, nc3 = st.columns([4, 1.5, 1.3])
    with nc1:
        badge = (f"&nbsp;<span style='background:{RED};color:#fff;font-size:.68rem;"
                 f"border-radius:6px;padding:1px 7px;'>{uc}</span>") if uc > 0 else ""
        st.markdown(
            f'<div class="section-head" style="font-size:1.1rem;">🔔 מרכז התראות{badge}</div>',
            unsafe_allow_html=True)
    with nc2:
        if st.button("✓ סמן הכל כנקרא", key="notif_read", use_container_width=True):
            _mark_all_read(); st.rerun()
    with nc3:
        if st.button("🗑️ נקה הכל", key="notif_clear", use_container_width=True):
            _clear_notifications(); st.rerun()

    # Filter row
    FILTER_OPTS = ["הכל", "🔥 חמות מאוד", "⚡ בינוני", "👀 שוות מעקב",
                   "📡 ניטור", "📰 חדשות"]
    fsel  = st.radio("סנן:", FILTER_OPTS, horizontal=True, key="notif_filter")
    notifs = _load_notifications()

    if fsel == "🔥 חמות מאוד":
        notifs = [n for n in notifs if n.get("confidence") == "גבוה"]
    elif fsel == "⚡ בינוני":
        notifs = [n for n in notifs if n.get("confidence") == "בינוני"]
    elif fsel == "👀 שוות מעקב":
        notifs = [n for n in notifs if n.get("confidence") == "שווה מעקב"]
    elif fsel == "📡 ניטור":
        notifs = [n for n in notifs if n.get("agent") == "monitor"]
    elif fsel == "📰 חדשות":
        notifs = [n for n in notifs if n.get("agent") == "news"]

    if not notifs:
        st.markdown(
            f'<div style="text-align:center;padding:48px 24px;color:{TX2};direction:rtl;">'
            f'<div style="font-size:2rem;margin-bottom:10px;">🎉</div>'
            f'<div>אין התראות כרגע</div>'
            f'<div style="font-size:.78rem;color:{TX3};margin-top:6px;">'
            f'הסוכן סורק אוטומטית כל 30 דקות</div></div>',
            unsafe_allow_html=True)
    else:
        for n in notifs[:80]:
            is_scanner  = n.get("agent") == "scanner" and n.get("confidence")
            level       = n.get("level", "info")
            lc          = RED if level == "danger" else AMB if level == "warning" else CYAN
            dot         = f"<span style='color:{CYAN};font-size:.9rem;'>●&nbsp;</span>" if not n.get("read") else ""
            ag_ic       = AGENT_ICONS.get(n.get("agent", ""), "🤖")

            if is_scanner:
                # Rich scanner notification card
                conf        = n.get("confidence", "")
                conf_icon   = n.get("conf_icon", "")
                risk        = n.get("risk", "")
                sym         = n.get("sym", "")
                entry       = n.get("entry")
                target1     = n.get("target1")
                target2     = n.get("target2")
                stop        = n.get("stop")
                desc        = n.get("desc", "")
                why_u       = n.get("why_unknown", "")
                all_reasons = n.get("all_reasons", "")
                vol_ratio   = n.get("vol_ratio", 0)
                rsi_val     = n.get("rsi", 0)
                score       = n.get("score", 0)

                conf_c      = (GRN if conf == "גבוה" else
                               AMB if conf == "בינוני" else CYAN)
                risk_c      = (RED if risk == "גבוה" else
                               AMB if risk == "בינוני" else GRN)

                targets_html = ""
                if entry:
                    targets_html = (
                        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;">'
                        f'<span style="background:{CYAN}18;color:{CYAN};border:1px solid {CYAN}33;'
                        f'border-radius:8px;padding:4px 10px;font-size:.72rem;font-weight:700;">'
                        f'כניסה: ${entry:.2f}</span>'
                        f'<span style="background:{GRN}18;color:{GRN};border:1px solid {GRN}33;'
                        f'border-radius:8px;padding:4px 10px;font-size:.72rem;font-weight:700;">'
                        f'יעד 1: ${target1:.2f}</span>'
                        f'<span style="background:{GRN}18;color:{GRN};border:1px solid {GRN}33;'
                        f'border-radius:8px;padding:4px 10px;font-size:.72rem;font-weight:700;">'
                        f'יעד 2: ${target2:.2f}</span>'
                        f'<span style="background:{RED}18;color:{RED};border:1px solid {RED}33;'
                        f'border-radius:8px;padding:4px 10px;font-size:.72rem;font-weight:700;">'
                        f'סטופ: ${stop:.2f}</span>'
                        f'</div>'
                    )

                why_html = ""
                if why_u:
                    why_html = (
                        f'<div style="background:{PUR}10;border:1px solid {PUR}33;'
                        f'border-radius:8px;padding:8px 12px;margin-top:8px;direction:rtl;">'
                        f'<span style="font-size:.71rem;font-weight:700;color:{PUR};">'
                        f'🔍 למה לא מוכרת?</span>'
                        f'<div style="font-size:.72rem;color:{TX2};margin-top:3px;line-height:1.5;">'
                        f'{why_u}</div></div>'
                    )

                reasons_html = ""
                if all_reasons:
                    parts = all_reasons.split(" · ")
                    reasons_html = (
                        f'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;">'
                        + "".join(
                            f'<span style="background:{SURF2};border:1px solid {BDR};'
                            f'color:{TX2};border-radius:6px;padding:3px 8px;font-size:.7rem;">'
                            f'{p}</span>'
                            for p in parts if p
                        )
                        + '</div>'
                    )

                st.markdown(
                    f'<div style="background:linear-gradient(160deg,{SURF},#0b1b2f);'
                    f'border:1px solid {lc}55;border-right:4px solid {lc};'
                    f'border-radius:0 14px 14px 0;padding:16px 18px;'
                    f'margin-bottom:12px;direction:rtl;">'

                    # Header row
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:flex-start;margin-bottom:8px;">'
                    f'<div style="font-size:.9rem;font-weight:800;color:{TX};">'
                    f'{dot}🔍 {n.get("title","")}</div>'
                    f'<div style="font-size:.68rem;color:{TX3};white-space:nowrap;'
                    f'margin-right:8px;">{n.get("time","")}</div></div>'

                    # Badges
                    f'<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:8px;">'
                    f'<span style="background:{conf_c}18;color:{conf_c};border:1px solid {conf_c}33;'
                    f'border-radius:6px;padding:3px 10px;font-size:.72rem;font-weight:700;">'
                    f'{conf_icon} ביטחון: {conf}</span>'
                    f'<span style="background:{risk_c}18;color:{risk_c};border:1px solid {risk_c}33;'
                    f'border-radius:6px;padding:3px 10px;font-size:.72rem;font-weight:700;">'
                    f'⚠️ סיכון: {risk}</span>'
                    + (f'<span style="background:{SURF2};color:{TX2};border:1px solid {BDR};'
                       f'border-radius:6px;padding:3px 10px;font-size:.71rem;">'
                       f'RSI {rsi_val:.0f} · נפח x{vol_ratio:.1f} · ציון {score}</span>'
                       if rsi_val else '')
                    + f'</div>'

                    # Company desc
                    + (f'<div style="font-size:.78rem;color:{TX2};margin-bottom:6px;'
                       f'line-height:1.5;">{desc}</div>' if desc else '')

                    # Reasons
                    + reasons_html + targets_html + why_html

                    + '</div>',
                    unsafe_allow_html=True)

                # "Analyze in depth" button
                if sym:
                    if st.button(f"🔬 נתח {sym} לעומק",
                                 key=f"notif_deep_{n.get('key','')[:20]}",
                                 type="primary"):
                        st.session_state["search_ticker"] = sym
                        st.session_state["page"] = "home"
                        st.rerun()
            else:
                # Standard notification card (monitor / news)
                body      = n.get("body", "")
                body_html = "".join(
                    f'<div style="font-size:.78rem;color:{TX2};line-height:1.6;">{line}</div>'
                    for line in body.split("\n") if line.strip()
                )
                st.markdown(
                    f'<div style="background:{SURF};border:1px solid {BDR};'
                    f'border-right:4px solid {lc};border-radius:0 10px 10px 0;'
                    f'padding:12px 16px;margin-bottom:8px;direction:rtl;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:flex-start;margin-bottom:4px;">'
                    f'<div style="font-size:.86rem;font-weight:700;color:{TX};">'
                    f'{dot}{ag_ic} {n.get("title","")}</div>'
                    f'<div style="font-size:.7rem;color:{TX3};white-space:nowrap;'
                    f'margin-right:8px;">{n.get("time","")}</div></div>'
                    f'{body_html}</div>',
                    unsafe_allow_html=True)

    # ── Activity log ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    with st.expander("📋 לוג פעילות סוכנים"):
        try:
            with open(AGENT_LOGS_FILE, encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
        if not logs:
            st.markdown(f"<div style='color:{TX2};direction:rtl;'>אין לוג עדיין.</div>",
                        unsafe_allow_html=True)
        else:
            for log in logs[:80]:
                ic = AGENT_ICONS.get(log.get("agent", ""), "🤖")
                st.markdown(
                    f'<div style="font-size:.78rem;direction:rtl;padding:4px 0;'
                    f'border-bottom:1px solid {BDR}44;">'
                    f'<span style="color:{TX3};">{log["time"]}</span>&nbsp;'
                    f'{ic}&nbsp;<span style="color:{TX};">{log["message"]}</span></div>',
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LEARN PAGE — glossary + strategies
# ══════════════════════════════════════════════════════════════════════════════
def page_learn():
    st.markdown(
        f'<h1 style="color:{CYAN};font-size:2rem;direction:rtl;text-align:right;margin-bottom:4px;">📚 למד</h1>'
        f'<p style="color:{TX2};direction:rtl;text-align:right;margin-bottom:18px;">מדריך מקיף לשוק ההון — מושגים, אסטרטגיות וטיפים מעשיים</p>',
        unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📖 מילון מונחים", "🟢 אסטרטגיות קנייה", "🔴 אסטרטגיות מכירה", "🧮 חישובון RSI"])

    # ── shared card style ────────────────────────────────────────────────────
    def _term_card(term_he, term_en, body, example="", color=CYAN):
        st.markdown(
            f'<div style="background:{SURF2};border:1px solid {color}44;border-radius:6px;'
            f'padding:14px 18px;margin-bottom:10px;direction:rtl;text-align:right;">'
            f'<span style="font-size:1.05rem;font-weight:700;color:{color};">{term_he}</span>'
            f'<span style="color:{TX3};font-size:.82rem;margin-right:8px;">· {term_en}</span><br>'
            f'<span style="color:{TX};font-size:.9rem;line-height:1.55;">{body}</span>'
            + (f'<div style="margin-top:8px;background:{SURF3};border-radius:8px;padding:7px 12px;'
               f'font-size:.82rem;color:{AMB};">💡 {example}</div>' if example else '')
            + '</div>',
            unsafe_allow_html=True)

    def _strategy_card(emoji, name, tagline, when, pros, cons, example, color=GRN):
        pros_html = "".join(f'<li>{p}</li>' for p in pros)
        cons_html = "".join(f'<li>{c}</li>' for c in cons)
        st.markdown(
            f'<div style="background:{SURF2};border:1px solid {color}55;border-radius:8px;'
            f'padding:18px 20px;margin-bottom:14px;direction:rtl;text-align:right;">'
            f'<div style="font-size:1.15rem;font-weight:700;color:{color};margin-bottom:4px;">'
            f'{emoji} {name}</div>'
            f'<div style="color:{TX2};font-size:.88rem;margin-bottom:10px;">{tagline}</div>'
            f'<div style="margin-bottom:8px;">'
            f'<span style="color:{CYAN};font-size:.82rem;font-weight:600;">⏰ מתי להשתמש: </span>'
            f'<span style="color:{TX};font-size:.85rem;">{when}</span></div>'
            f'<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;">'
            f'<div style="flex:1;min-width:160px;">'
            f'<div style="color:{GRN};font-size:.8rem;font-weight:600;margin-bottom:4px;">✅ יתרונות</div>'
            f'<ul style="color:{TX};font-size:.83rem;margin:0;padding-right:16px;line-height:1.6;">{pros_html}</ul>'
            f'</div>'
            f'<div style="flex:1;min-width:160px;">'
            f'<div style="color:{RED};font-size:.8rem;font-weight:600;margin-bottom:4px;">❌ חסרונות</div>'
            f'<ul style="color:{TX};font-size:.83rem;margin:0;padding-right:16px;line-height:1.6;">{cons_html}</ul>'
            f'</div></div>'
            f'<div style="background:{SURF3};border-radius:8px;padding:9px 14px;font-size:.83rem;">'
            f'<span style="color:{AMB};font-weight:600;">📌 דוגמה אמיתית: </span>'
            f'<span style="color:{TX};">{example}</span></div>'
            f'</div>',
            unsafe_allow_html=True)

    # ── TAB 1: GLOSSARY ─────────────────────────────────────────────────────
    with tab1:
        search = st.text_input("🔍 חיפוש מונח...", placeholder="לדוגמה: RSI, דיבידנד, P/E", key="learn_search")
        search_lower = search.strip().lower()

        GLOSSARY = {
            "📈 ניתוח טכני": [
                ("RSI", "Relative Strength Index",
                 "מדד עוצמה יחסית בטווח 0–100. RSI מתחת ל-30 → מניה יתמכרה (קניה פוטנציאלית). RSI מעל 70 → מניה יתקנה (מכירה פוטנציאלית).",
                 "NVDA ירדה ל-RSI 28 בנובמבר 2022 — מי שקנה שם ראה +180% בשנה.", CYAN),
                ("ממוצע נע — MA", "Moving Average",
                 "ממוצע מחיר המניה על פני תקופה (50 יום / 200 יום). כשהמחיר חוצה את ה-MA מלמטה למעלה — סימן חיובי. מלמעלה למטה — סימן שלילי.",
                 "MA50 > MA200 = 'צלב הזהב' (Golden Cross) — אות קנייה חזק.", CYAN),
                ("MACD", "Moving Average Convergence Divergence",
                 "מדד מומנטום המחשב הפרש בין ממוצעים נעים. כשקו ה-MACD חוצה את קו האות מלמטה — אות קנייה. מלמעלה — אות מכירה.",
                 "MACD חיובי ועולה = מומנטום חיובי חזק.", CYAN),
                ("בולינגר בנדס", "Bollinger Bands",
                 "שלושה קווים סביב המחיר: ממוצע נע + 2 סטיות תקן. כשהמחיר נוגע בפס התחתון — אזור קניה. בפס העליון — אזור מכירה.",
                 "מניה שנוגעת בפס התחתון חוזרת למרכז ב-70% מהמקרים.", PUR),
                ("תמיכה ועמידות", "Support & Resistance",
                 "תמיכה = רמת מחיר שבה הקונים מתגברים (הרצפה). עמידות = רמת מחיר שבה המוכרים מתגברים (התקרה). פריצה של עמידות הופכת אותה לתמיכה.",
                 "AAPL בדצמבר 2023 פרצה עמידה ב-$190 ועלתה ל-$220.", CYAN),
                ("פריצה", "Breakout",
                 "כשמחיר המניה שובר רמת עמידות חשובה עם נפח מסחר גבוה. זהו אות לכניסת קונים חדשים ומומנטום עולה.",
                 "אם מניה נסחרת ב-$50 ומגיעה ל-$50 כמה פעמים ופורצת — פריצה!", GRN),
                ("נפח מסחר", "Volume",
                 "כמות המניות שנסחרו ביום. עלייה עם נפח גבוה = חזק ואמין. עלייה עם נפח נמוך = חשוד. ירידה עם נפח גבוה = מוכרים חזקים בשוק.",
                 "ריילי של +5% עם נפח פי 3 מהרגיל = תנועה אמיתית.", AMB),
                ("נר יפני", "Candlestick",
                 "ייצוג גרפי של מחיר פתיחה, שיא, שפל וסגירה. נר ירוק = המחיר עלה. נר אדום = המחיר ירד. גוף גדול = מומנטום חזק.",
                 "נר 'דוג'י' (גוף קטן) = חוסר החלטיות בשוק.", CYAN),
                ("ממוצע נע 52 שבועות", "52-Week High/Low",
                 "השיא/שפל הגבוה ביותר של המניה ב-12 החודשים האחרונים. מניה שנסחרת ליד שפל 52 שבועות עשויה להיות בהזדמנות.",
                 "RXRX נסחרה ב-85% מתחת לשיא 52 שבועות — אות למחקר נוסף.", RED),
            ],
            "📊 ניתוח פונדמנטלי": [
                ("P/E", "Price-to-Earnings Ratio",
                 "יחס בין מחיר המניה לרווח למניה. P/E של 20 = משלמים $20 על כל $1 רווח שנתי. P/E נמוך = זול יחסית. P/E גבוה = יקר או ציפייה לצמיחה.",
                 "NVDA סחרה ב-P/E 100+ בשיא ה-AI — השוק ציפה לצמיחה עצומה.", AMB),
                ("EPS", "Earnings Per Share",
                 "הרווח נטו של החברה חלקי מספר המניות. EPS עולה = החברה מרוויחה יותר. EPS שלילי = הפסד.",
                 "AAPL דיווחה EPS של $6.11 ברבעון Q1 2024 — שיא חדש.", GRN),
                ("שווי שוק", "Market Capitalization",
                 "מחיר המניה × מספר המניות = הערכת שווי כוללת של החברה. Large Cap: מעל $10B. Mid Cap: $2B–$10B. Small Cap: מתחת ל-$2B.",
                 "Apple = שווי שוק $3.5 טריליון — החברה הגדולה בעולם.", CYAN),
                ("דיבידנד", "Dividend",
                 "חלק מהרווחים שהחברה מחלקת לבעלי המניות. מדיד ב-Yield (%) — כמה % ממחיר המניה מקבלים בשנה.",
                 "JNJ משלמת דיבידנד של ~3% בשנה — הכנסה פסיבית יציבה.", GRN),
                ("הכנסות", "Revenue",
                 "סך המכירות של החברה לפני הוצאות. הכנסות עולות = העסק צומח. חשוב לבדוק גם את שולי הרווח (Margin).",
                 "MSFT עברה $200B הכנסות שנתיות — ציון דרך היסטורי.", AMB),
                ("שולי רווח גולמי", "Gross Margin",
                 "אחוז הרווח לאחר עלות הייצור. שולי רווח גבוהים (>50%) = חברה עם יתרון תחרותי חזק.",
                 "AAPL ~43%, MSFT ~70%, חברות תוכנה לרוב מעל 60%.", GRN),
                ("חוב/הון", "Debt-to-Equity",
                 "יחס בין החוב של החברה להונה העצמי. יחס גבוה = ממונפת ומסוכנת יותר. יחס נמוך = יציבה פיננסית.",
                 "בנקים בד\"כ יש להם D/E גבוה — זה נורמלי בסקטור.", RED),
                ("תזרים מזומנים חופשי", "Free Cash Flow (FCF)",
                 "המזומן שנשאר לחברה אחרי כל ההשקעות. FCF חיובי = החברה מייצרת מזומן אמיתי. חשוב יותר מ-EPS לעיתים.",
                 "GOOGL ייצרה $60B+ FCF ב-2023 — חוזק אמיתי.", GRN),
            ],
            "📋 פקודות מסחר": [
                ("פקודת שוק", "Market Order",
                 "קנייה/מכירה מיידית במחיר הזמין כרגע. מהירה אבל לא מבטיחה מחיר מסוים. מתאימה לניירות עם נזילות גבוהה.",
                 "אם AAPL נסחרת ב-$190 — פקודת שוק תתבצע בסביבות $190.", CYAN),
                ("פקודת לימיט", "Limit Order",
                 "מגדיר מחיר מקסימום לקנייה (או מינימום למכירה). הפקודה תתבצע רק אם המחיר מגיע לרמה שהגדרת.",
                 "הגדרת לימיט קנייה ב-$185 על AAPL — תתבצע רק אם המחיר יורד לשם.", GRN),
                ("סטופ לוס", "Stop Loss",
                 "פקודה אוטומטית למכירה אם המחיר יורד לרמה מסוימת. מגן על ההפסד. חיוני לניהול סיכונים!",
                 "קנית ב-$100, סטופ ב-$92 = מגביל הפסד ל-8%.", RED),
                ("סטופ לימיט", "Stop-Limit Order",
                 "שילוב של Stop Loss ולימיט. כשהסטופ מופעל, נשלחת פקודת לימיט (לא שוק). יש סיכון שהפקודה לא תתבצע אם השוק נופל מהר.",
                 "Stop ב-$92, Limit ב-$90 — ימכור בין $90–92 בלבד.", AMB),
                ("טריילינג סטופ", "Trailing Stop",
                 "סטופ לוס שמתעדכן אוטומטית עם עליית המחיר. אם המניה עולה, הסטופ עולה אחריה. אם יורדת — הסטופ נשאר במקומו.",
                 "קנית ב-$100, טריילינג 10%. מניה עלתה ל-$130 → הסטופ עלה ל-$117.", GRN),
                ("Take Profit", "Take Profit / Target",
                 "מחיר יעד למכירה כשהרווח מגיע לרמה רצויה. חשוב לקבוע לפני הכניסה לעסקה, לא בזמן שהמניה עולה.",
                 "קנית ב-$50, Take Profit ב-$65 = יעד רווח 30%.", GRN),
            ],
            "📉 מדדים ומשמעות": [
                ("S&P 500", "S&P 500",
                 "מדד 500 החברות הגדולות בארה\"ב. נחשב לברומטר הכלכלה האמריקנית. תשואה היסטורית ממוצעת ~10% בשנה.",
                 "מי שהשקיע $10,000 לפני 30 שנה יש לו כיום ~$170,000.", GRN),
                ('נאסד"ק', "NASDAQ",
                 "מדד מוכוון לחברות טכנולוגיה. יותר תנודתי מה-S&P 500. כולל AAPL, MSFT, GOOGL, NVDA, AMZN.",
                 "נאסד\"ק ירד 33% ב-2022 ועלה 43% ב-2023 — תנודתי אבל רווחי.", CYAN),
                ("VIX", "Volatility Index / Fear Index",
                 "מדד הפחד של וול סטריט. VIX מתחת ל-15 = שוק רגוע. 15–25 = מתח בינוני. מעל 30 = פחד גבוה = הזדמנות לקנייה עבור אמיצים.",
                 "ב-COVID מרץ 2020 VIX הגיע ל-85 — שיא היסטורי.", RED),
                ("ביטא", "Beta",
                 "מדד תנודתיות המניה יחסית לשוק. ביטא 1 = זז כמו השוק. ביטא 2 = זז פי 2. ביטא 0.5 = פחות תנודתי.",
                 "מניות ביוטק בד\"כ ביטא 1.5–2.5 — גבוהות סיכון.", AMB),
                ("דאו ג'ונס", "Dow Jones Industrial Average",
                 "מדד 30 החברות התעשייתיות הגדולות בארה\"ב. הוותיק ביותר — נוסד 1896. פחות מייצג את הכלכלה המודרנית מה-S&P.",
                 "הדאו עבר 40,000 נקודות לראשונה בהיסטוריה ב-2024.", PUR),
            ],
            "🧠 פסיכולוגיה של השקעות": [
                ("FOMO", "Fear Of Missing Out",
                 "הפחד להחמיץ. גורם למשקיעים לקנות בשיא אחרי עלייה חדה. אחת הטעויות הנפוצות ביותר בשוק.",
                 "FOMO על ביטקוין ב-$65K בנובמבר 2021 — מי שנכנס שם הפסיד 70%.", RED),
                ("שוק שורי vs דובי", "Bull Market vs Bear Market",
                 "שוק שורי = עלייה של 20%+ מהשפל. שוק דובי = ירידה של 20%+ מהשיא. ממוצע שוק שורי: 3.8 שנים. שוק דובי: 1.4 שנים.",
                 "שוק דובי 2022 נמשך ~12 חודשים, ואחריו שוק שורי חזק 2023–2024.", GRN),
                ("הטיית עיגון", "Anchoring Bias",
                 "התקבעות למחיר קניה ולא למחיר שוק הנוכחי. 'אני מוכר רק כשיחזור ל-$100 שקניתי' — מחשבה שגויה.",
                 "המניה שווה מה שהשוק מוכן לשלם — לא מה ששילמת.", AMB),
                ("ממוצע עלות — DCA", "Dollar Cost Averaging",
                 "השקעה של סכום קבוע בכל חודש ללא תלות במחיר. מפחיתה את הסיכון של כניסה בשיא.",
                 "השקעת $500 בחודש ב-S&P 500 ב-2020–2024 הניבה תשואה מצוינת.", GRN),
                ("גיוון תיק", "Diversification",
                 "פיזור ההשקעות על פני מניות, סקטורים ואפילו מדינות שונות. מפחית סיכון ללא ויתור על תשואה.",
                 "תיק של 20 מניות מסקטורים שונים = סיכון נמוך ב-60% מהחזקה של מניה אחת.", GRN),
                ("הטיית אישוש", "Confirmation Bias",
                 "מחפשים מידע שמאשש את מה שכבר מאמינים. למשל: 'TSLA תגיע ל-$1000' — וסופרים רק את הכותרות החיוביות.",
                 "תמיד חפש גם את הצד השני — מה הדובים אומרים על המניה שלך.", RED),
            ],
        }

        for category, terms in GLOSSARY.items():
            filtered = [t for t in terms if
                        not search_lower or
                        search_lower in t[0].lower() or
                        search_lower in t[1].lower() or
                        search_lower in t[2].lower()]
            if not filtered:
                continue
            st.markdown(
                f'<div style="font-size:1rem;font-weight:700;color:{TX2};direction:rtl;'
                f'text-align:right;margin:16px 0 8px;">{category}</div>',
                unsafe_allow_html=True)
            for term in filtered:
                _term_card(*term)

    # ── TAB 2: BUY STRATEGIES ───────────────────────────────────────────────
    with tab2:
        st.markdown(
            f'<p style="color:{TX2};direction:rtl;text-align:right;font-size:.9rem;margin-bottom:16px;">'
            f'כל אסטרטגיה כוללת: מתי להשתמש, יתרונות וחסרונות ודוגמה אמיתית.</p>',
            unsafe_allow_html=True)

        _strategy_card(
            "🚀", "מומנטום — Momentum",
            "לרכוב על הגל — קנה מניות שכבר עולות ומצפה שימשיכו",
            "כשהמניה עולה מעל MA50, RSI בין 55–70, ונפח מסחר גבוה. בשוק שורי חזק.",
            ["עובד מצוין בשוק עולה", "קל לזהות אוטומטית", "פוטנציאל רווח מהיר"],
            ["מסוכן בשוק תנודתי", "קשה לתזמן יציאה", "FOMO עלול להכניס מאוחר מדי"],
            "NVDA עלתה מ-$300 ל-$500 ב-6 חודשים — כל RSI מעל 55 + MA50 היה כניסה. מי שנכנס אחרי כל פריצה הרוויח.",
            GRN)

        _strategy_card(
            "💎", "ערך — Value Investing",
            "לקנות שטרות של $100 ב-$70 — מניות שהשוק מתמחר בחסר",
            "כשה-P/E נמוך מממוצע הסקטור, FCF חיובי, חברה רווחית שנפלה בגלל חדשות רעות זמניות.",
            ["מבוסס על ניתוח אמיתי", "פחות תנודתי", "מוכיח לאורך עשורים (וורן באפט)"],
            ["דורש סבלנות ארוכת טווח", "המניה עלולה 'להיות זולה' שנים", "קשה לדעת מתי 'הזמן הנכון'"],
            "GOOGL ב-2022 ירדה ל-P/E 20 — זול מאוד לחברת טק. מי שקנה הכפיל בשנתיים.",
            AMB)

        _strategy_card(
            "🌱", "צמיחה — Growth Investing",
            "לקנות חברות שצומחות מהר גם אם יקרות כרגע — להשקיע בעתיד",
            "כשהכנסות גדלות 20%+ בשנה, שוק גדול לכיבוש, מוצר מנצח. P/E גבוה מקובל.",
            ["פוטנציאל תשואה עצום", "השקעה בחברות המובילות את העתיד", "מגוון מניות מעניינות"],
            ["תמחור גבוה = ירידה חדה בשוק דובי", "חברות רבות לא מגשימות הבטחה", "צריך לעקוב מקרוב"],
            "NVDA ב-2023: הכנסות גדלו 200%+ — מי שהחזיק ראה +238% בשנה.",
            PUR)

        _strategy_card(
            "📅", "ממוצע עלות — DCA",
            "להשקיע סכום קבוע כל חודש, ללא קשר למחיר הנוכחי",
            "תמיד — במיוחד למשקיעים לטווח ארוך שלא רוצים לתזמן את השוק.",
            ["מבטל את הסיכון של כניסה בשיא", "פשוט לביצוע", "מתאים לכולם"],
            ["לא מנצל הזדמנויות ספציפיות", "בשוק עולה קצת פחות יעיל מקנייה חד-פעמית", "משעמם 😄"],
            "השקעת $500 בחודש ב-S&P 500 מ-2019 עד 2024 = ~$35,000 הפכו ל-~$62,000.",
            CYAN)

        _strategy_card(
            "💥", "פריצה — Breakout",
            "לקנות כשהמניה פורצת רמת עמידות חשובה עם נפח גבוה",
            "כשמחיר בדיוק פרץ רמה שניסה לשבור כמה פעמים, עם נפח פי 1.5+ מהרגיל.",
            ["כניסה מוקדמת לתנועה גדולה", "Stop Loss ברור (מתחת לפריצה)", "פוטנציאל R:R מצוין"],
            ["פריצות כוזבות — False Breakout", "צריך להיות ליד המסך", "קשה לאוטומציה"],
            "META פרצה $350 בינואר 2024 עם נפח x2. תוך 3 חודשים הגיעה ל-$520.",
            GRN)

        _strategy_card(
            "↩️", "התאוששות RSI — RSI Recovery",
            "לקנות מניות טובות שנפלו יותר מדי (RSI מתחת ל-30)",
            "כשחברה בריאה פונדמנטלית נפלה 20-30%+ בגלל שוק כללי או חדשות זמניות, RSI מתחת ל-30.",
            ["קנייה בזול — הזדמנות ברורה", "Stop Loss ברור (שפל חדש)", "גם ה-RSI-system שלנו עוקב אחרי זה"],
            ["מניה יכולה להמשיך לרדת", "'מלכודת ערך' — הבעיה אמיתית", "צריך ניתוח פונדמנטלי"],
            "AAPL ב-RSI 28 בדצמבר 2022 — כניסה שם הניבה +50% תוך שנה.",
            CYAN)

        _strategy_card(
            "📉", "קנייה בירידה — Pullback",
            "לחכות שמניה חזקה תירד מעט ואז לקנות בטרנד עולה",
            "כשמניה בטרנד עולה ברור, יורדת 5-10% בחזרה לאזור MA20/MA50, ואז מראה סימני התייצבות.",
            ["כניסה בנקודה טובה יותר מפריצה", "הטרנד כבר הוכח", "Stop Loss ברור"],
            ["מה אם הירידה ממשיכה?", "קשה להבחין בין Pullback לשינוי טרנד", "דורש תזמון"],
            "NVDA עלתה, ירדה 8% ב-אוגוסט 2023, ואז המשיכה לשיא חדש — כניסה בירידה הניבה +60%.",
            AMB)

    # ── TAB 3: SELL STRATEGIES ──────────────────────────────────────────────
    with tab3:
        st.markdown(
            f'<p style="color:{TX2};direction:rtl;text-align:right;font-size:.9rem;margin-bottom:16px;">'
            f'מתי ואיך לצאת מהעסקה — הצד שרוב המשקיעים מזניחים.</p>',
            unsafe_allow_html=True)

        _strategy_card(
            "🛡️", "סטופ לוס — Stop Loss",
            "קו אדום שלא חוצים — מכירה אוטומטית כשההפסד מגיע לסף מוגדר",
            "תמיד — בכל עסקה. קבע לפני הכניסה ל-7-10% מתחת למחיר הקנייה.",
            ["מגן על ההון", "מוציא רגש מהמשוואה", "מאפשר שינה רגועה"],
            ["עלול למכור בשפל זמני", "בשוק תנודתי — יצאת ואז המניה עלתה", "צריך לקבוע נכון"],
            "קנית TSLA ב-$200. Stop ב-$186 (7%). TSLA ירדה ל-$170 — יצאת ב-$186 וחסכת ירידה נוספת.",
            RED)

        _strategy_card(
            "🎯", "מכירה ביעד — Take Profit",
            "מכור חלק מהפוזיציה כשמגיע ליעד רווח מוגדר מראש",
            "כשהמניה הגיעה ל-20-30% רווח, או לאזור עמידות חשוב. מכור 50% ותן לשאר לרוץ.",
            ["מבטיח רווחים", "מפחית לחץ פסיכולוגי", "אסטרטגיה ברורה"],
            ["עלול למכור מוקדם מדי", "מחמיץ עלייה נוספת", "קשה פסיכולוגית לראות שהיא ממשיכה"],
            "קנית NVDA ב-$300. יעד ב-$390 (30%). כשהגיעה — מכרת חצי. השאר המשיך ל-$500.",
            GRN)

        _strategy_card(
            "📈", "סטופ נגרר — Trailing Stop",
            "הסטופ 'נגרר' אחרי המחיר כשהוא עולה — מגן על הרווחים",
            "כשיש לך רווח יפה ואתה רוצה להמשיך להחזיק אבל לא לאבד הכל. קבע 10-15% מתחת לשיא.",
            ["מגן על רווחים", "לא מחמיץ עלייה", "אוטומטי ורגשי פחות"],
            ["שוק תנודתי יכול להפעיל מוקדם", "מורכב להגדרה אצל חלק מהברוקרים", ""],
            "NVDA עלתה מ-$300 ל-$500. Trailing 10% = Stop עולה ל-$450. כשירדה ל-$450 — יצאת ברווח של 50%.",
            AMB)

        _strategy_card(
            "📊", "יציאה לפי RSI — RSI Exit",
            "מכור כשה-RSI מגיע לאזור קניית יתר (מעל 70-75)",
            "כשהמניה עלתה חדות ו-RSI עבר 70. במיוחד אם עלתה 20%+ תוך זמן קצר.",
            ["מבוסס על מדד אובייקטיבי", "מזהה שיאים בזמן", "טוב לטווח קצר"],
            ["מניות חזקות יכולות להישאר ב-RSI 70+ זמן רב", "RSI 70 לבד לא מספיק", ""],
            "NVDA הגיעה ל-RSI 82 לפני ירידה של 15% — RSI גבוה היה אות מוקדם.",
            RED)

        _strategy_card(
            "📉", "יציאה לפי ממוצע נע — MA Cross",
            "מכור כשמחיר המניה יורד מתחת ל-MA50 או MA200",
            "כשמניה שהחזקת יורדת ושוברת את ה-MA50 עם נפח גבוה — טרנד השתנה.",
            ["מחכה לאישור הטרנד", "פחות FALSE signals מ-RSI בלבד", "ברור ואובייקטיבי"],
            ["כניסה מאוחרת — כבר ירדת 5-10%", "בשוק צדדי — יצאת ונכנסת הרבה", ""],
            "קנית TSLA. עברה מתחת MA50 בינואר 2022. מי שיצא שם חסך 40% נוספים של ירידה.",
            RED)

        _strategy_card(
            "⏰", "מכירה חלקית — Scaling Out",
            "מכור את הפוזיציה בשלבים — לא הכל בבת אחת",
            "כשאינך בטוח אם זה השיא. מכור שליש ב-+20%, שליש ב-+40%, שמור שליש לטווח ארוך.",
            ["מפחית אחרת רגשות", "לא מחמיץ עלייה נוספת", "גמיש"],
            ["מורכב לניהול", "עמלות יותר", "צריך ניהול אקטיבי"],
            "קנית RKLB ב-$10. מכרת 33% ב-$14, 33% ב-$18, שמרת 33% — ממוצע מכירה $14 + אפסייד ארוך.",
            PUR)

        # Tips box
        st.markdown(
            f'<div style="background:{SURF2};border:1px solid {GRN}44;border-radius:8px;'
            f'padding:18px 20px;margin-top:8px;direction:rtl;text-align:right;">'
            f'<div style="font-size:1rem;font-weight:700;color:{GRN};margin-bottom:10px;">💡 כללי הזהב של מכירה</div>'
            f'<ol style="color:{TX};font-size:.88rem;padding-right:20px;line-height:1.85;">'
            f'<li>תמיד קבע <strong>Stop Loss לפני הכניסה</strong> — לא תוך כדי.</li>'
            f'<li>אל תחכה שתחזור להפסד — <strong>הפסד קטן עדיף על הפסד גדול</strong>.</li>'
            f'<li>כשמניה עלתה 20-30% — <strong>מכור לפחות חצי</strong>.</li>'
            f'<li><strong>אל תסתכל על מחיר הקנייה</strong> — תחשוב: אם לא החזקת כרגע, האם היית קונה?</li>'
            f'<li><strong>רגשות הם האויב</strong> — Stop Loss אוטומטי עוזר.</li>'
            f'</ol></div>',
            unsafe_allow_html=True)

    # ── TAB 4: RSI CALCULATOR ───────────────────────────────────────────────
    with tab4:
        st.markdown(
            f'<p style="color:{TX2};direction:rtl;text-align:right;font-size:.9rem;margin-bottom:16px;">'
            f'הכנס סמל מניה או מחירי סגירה ידניים — קבל ניתוח RSI מיידי.</p>',
            unsafe_allow_html=True)

        def _rsi_from_series(closes, period=14):
            """Simple rolling RSI — same formula used throughout the app."""
            s = pd.Series(closes, dtype=float)
            d = s.diff()
            g  = d.clip(lower=0).rolling(period).mean()
            lo = (-d.clip(upper=0)).rolling(period).mean()
            rsi_series = 100 - 100 / (1 + g / lo)
            return rsi_series

        def _rsi_gauge_html(rsi_val):
            pct = max(0, min(100, rsi_val))
            if pct < 30:
                val_color = GRN
            elif pct < 70:
                val_color = AMB
            else:
                val_color = RED
            return (
                f'<div style="position:relative;height:28px;border-radius:8px;overflow:visible;'
                f'background:linear-gradient(to right,{GRN}88 0% 30%,{AMB}88 30% 70%,{RED}88 70% 100%);">'
                f'<div style="position:absolute;left:{pct}%;top:-5px;transform:translateX(-50%);'
                f'width:6px;height:38px;background:{val_color};border-radius:3px;'
                f'box-shadow:0 0 10px {val_color};"></div></div>'
                f'<div style="display:flex;justify-content:space-between;color:{TX3};font-size:.75rem;margin-top:4px;">'
                f'<span>0</span><span style="color:{GRN};">מכירת יתר 30</span>'
                f'<span style="color:{AMB};">ניטרלי</span>'
                f'<span style="color:{RED};">קניית יתר 70</span><span>100</span></div>'
            )

        def _rsi_interpretation(rsi_val):
            if rsi_val < 20:
                return (RED, "מכירת יתר קיצונית",
                        "RSI מתחת ל-20 הוא נדיר מאוד ומסמן פאניקה בשוק. היסטורית, אלה הן נקודות הכניסה הטובות ביותר לטווח הארוך — אם הפונדמנטלים של החברה תקינים.",
                        "🟢 קנייה חזקה / הצטברות")
            elif rsi_val < 30:
                return (GRN, "מכירת יתר",
                        "המניה נמכרה יתר על המידה. לרוב מצב זה מקדים התאוששות. בדוק שאין סיבה פונדמנטלית לירידה (דוח רע, תחרות) לפני כניסה.",
                        "🟢 קנייה / שקול כניסה")
            elif rsi_val < 45:
                return (TX2, "ניטרלי — נטייה שלילית",
                        "RSI באזור זה מראה חולשה מסוימת אך לא מכירת יתר. המניה יכולה להמשיך לרדת. המתן לאיתות חזק יותר.",
                        "🟡 המתן — אין אות ברור")
            elif rsi_val < 55:
                return (TX2, "ניטרלי",
                        "אזור הניטרלי הטהור. השוק לא נותן אות ברור לכאן או לכאן. בדוק גורמים נוספים כמו MA, נפח ופונדמנטלים.",
                        "🟡 ניטרלי — אין אות")
            elif rsi_val < 70:
                return (AMB, "ניטרלי — נטייה חיובית",
                        "המניה מראה כוח ומומנטום חיובי. אם אתה בפוזיציה, זה הזמן לשקול Trailing Stop. אם עדיין לא נכנסת, חכה לפולבק.",
                        "🟡 החזק — שקול Trailing Stop")
            elif rsi_val < 80:
                return (RED, "קניית יתר",
                        "המניה נסחרת גבוה מדי בטווח הקצר. שקול מכירה חלקית (Scaling Out) או הידוק ה-Stop Loss. מניות חזקות עלולות להישאר כאן זמן מה.",
                        "🔴 מכירה חלקית / הידק Stop Loss")
            else:
                return (RED, "קניית יתר קיצונית",
                        "RSI מעל 80 הוא אות מכירה חזק. מצב זה בד\"כ מקדים תיקון. אם יש לך רווח יפה — מכור לפחות חצי מהפוזיציה.",
                        "🔴 מכירה / הפחתת פוזיציה")

        mode = st.radio("מצב קלט", ["🔍 לפי סמל מניה", "✏️ מחירים ידניים"],
                        horizontal=True, key="rsi_mode")

        if mode == "🔍 לפי סמל מניה":
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                ticker_in = st.text_input("סמל מניה", placeholder="AAPL / NVDA / TSLA ...",
                                          key="rsi_ticker_in")
            with c2:
                rsi_period = st.number_input("תקופת RSI", min_value=5, max_value=30,
                                             value=14, key="rsi_period_auto")
            with c3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                calc_auto = st.button("🧮 חשב", type="primary", key="rsi_btn_auto",
                                      use_container_width=True)

            if calc_auto and ticker_in.strip():
                sym = ticker_in.strip().upper()
                with st.spinner(f"מוריד נתונים עבור {sym}..."):
                    try:
                        df = fetch_history(sym, "3mo")
                        if df is None or len(df) < rsi_period + 5:
                            st.error(f"לא נמצאו מספיק נתונים עבור {sym}")
                        else:
                            rsi_s = _rsi_from_series(df["Close"].tolist(), rsi_period)
                            last_rsi = float(rsi_s.dropna().iloc[-1])
                            rsi_hist = rsi_s.dropna().iloc[-14:].tolist()
                            closes   = df["Close"].iloc[-15:].tolist()
                            cur_price = float(df["Close"].iloc[-1])
                            prev_price = float(df["Close"].iloc[-2])
                            chg_pct = (cur_price - prev_price) / prev_price * 100
                            st.session_state["rsi_result"] = {
                                "sym": sym, "rsi": last_rsi, "period": rsi_period,
                                "rsi_hist": rsi_hist, "closes": closes,
                                "cur_price": cur_price, "chg_pct": chg_pct,
                                "mode": "auto",
                            }
                    except Exception as e:
                        st.error(f"שגיאה: {e}")

        else:
            st.markdown(
                f'<p style="color:{TX3};font-size:.82rem;direction:rtl;margin-bottom:6px;">'
                f'הכנס לפחות {14+5} מחירי סגירה יומיים, מופרדים בפסיקים (מהישן לחדש).</p>',
                unsafe_allow_html=True)
            prices_in = st.text_area("מחירי סגירה (מהישן לחדש)",
                                     placeholder="100.5, 101.2, 99.8, 102.1, ...",
                                     height=100, key="rsi_prices_in")
            c1, c2 = st.columns([1, 3])
            with c1:
                rsi_period = st.number_input("תקופת RSI", min_value=5, max_value=30,
                                             value=14, key="rsi_period_man")
            with c2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                calc_man = st.button("🧮 חשב RSI", type="primary", key="rsi_btn_man")
            if calc_man and prices_in.strip():
                try:
                    closes = [float(x.strip()) for x in prices_in.replace("\n", ",").split(",")
                              if x.strip()]
                    if len(closes) < rsi_period + 5:
                        st.error(f"דרוש לפחות {rsi_period + 5} מחירים (יש {len(closes)})")
                    else:
                        rsi_s    = _rsi_from_series(closes, rsi_period)
                        last_rsi = float(rsi_s.dropna().iloc[-1])
                        rsi_hist = rsi_s.dropna().iloc[-14:].tolist()
                        st.session_state["rsi_result"] = {
                            "sym": "ידני", "rsi": last_rsi, "period": rsi_period,
                            "rsi_hist": rsi_hist, "closes": closes[-15:],
                            "cur_price": closes[-1], "chg_pct": (closes[-1] - closes[-2]) / closes[-2] * 100,
                            "mode": "manual",
                        }
                except ValueError:
                    st.error("פורמט שגוי — הכנס מחירים מספריים מופרדים בפסיקים בלבד.")

        # ── Results display ─────────────────────────────────────────────────
        res = st.session_state.get("rsi_result")
        if res:
            rsi_val   = res["rsi"]
            col, zone_label, interp_text, action = _rsi_interpretation(rsi_val)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Big RSI number + zone badge
            _price_arrow = "▲" if res["chg_pct"] >= 0 else "▼"
            _price_color = GRN if res["chg_pct"] >= 0 else RED
            _price_html = (
                f'<div style="font-size:.88rem;color:{_price_color};">'
                f'{_price_arrow} ${res["cur_price"]:.2f} ({res["chg_pct"]:+.2f}%)</div>'
                if res["mode"] == "auto" else ""
            )
            st.markdown(
                f'<div style="background:{SURF2};border:1px solid {col}55;border-radius:8px;'
                f'padding:20px 24px;direction:rtl;text-align:right;">'
                f'<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px;">'
                f'<div style="font-size:3.2rem;font-weight:800;color:{col};line-height:1;">'
                f'{rsi_val:.1f}</div>'
                f'<div>'
                f'<div style="font-size:1.1rem;font-weight:700;color:{col};">{zone_label}</div>'
                f'<div style="font-size:.82rem;color:{TX2};">RSI({res["period"]}) · {res["sym"]}</div>'
                f'{_price_html}'
                f'</div>'
                f'<div style="margin-right:auto;background:{col}22;border:1px solid {col}55;'
                f'border-radius:8px;padding:6px 14px;font-size:.85rem;color:{col};font-weight:600;">'
                f'{action}</div>'
                f'</div>'
                + _rsi_gauge_html(rsi_val) +
                f'<div style="margin-top:16px;color:{TX};font-size:.88rem;line-height:1.6;">{interp_text}</div>'
                f'</div>',
                unsafe_allow_html=True)

            # RSI trend over last sessions
            if len(res["rsi_hist"]) >= 3:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.markdown(
                    f'<div style="color:{TX2};font-size:.82rem;font-weight:600;direction:rtl;'
                    f'text-align:right;margin-bottom:6px;">📊 RSI — 14 ימים אחרונים</div>',
                    unsafe_allow_html=True)
                cols_rsi = st.columns(len(res["rsi_hist"]))
                for i, rv in enumerate(res["rsi_hist"]):
                    if rv < 30:
                        rc = GRN
                    elif rv < 70:
                        rc = AMB
                    else:
                        rc = RED
                    is_last = (i == len(res["rsi_hist"]) - 1)
                    with cols_rsi[i]:
                        st.markdown(
                            f'<div style="text-align:center;background:{"" + rc + "22" if is_last else SURF3};'
                            f'border:1px solid {rc if is_last else BDR};border-radius:8px;padding:4px 2px;">'
                            f'<div style="font-size:{"1rem" if is_last else ".78rem"};font-weight:{"700" if is_last else "400"};color:{rc};">'
                            f'{rv:.0f}</div>'
                            f'<div style="font-size:.65rem;color:{TX3};">-{len(res["rsi_hist"])-1-i}d</div>'
                            f'</div>',
                            unsafe_allow_html=True)

            # Explanation of RSI
            with st.expander("❓ איך RSI מחושב?"):
                st.markdown(
                    f'<div style="direction:rtl;text-align:right;color:{TX};font-size:.88rem;line-height:1.7;">'
                    f'<strong style="color:{CYAN};">RSI = 100 − (100 ÷ (1 + RS))</strong><br><br>'
                    f'כאשר RS = ממוצע עליות {res["period"]} ימים ÷ ממוצע ירידות {res["period"]} ימים<br><br>'
                    f'<strong>דוגמה:</strong> אם ב-14 ימים הייתה עלייה ממוצעת של $0.80 וירידה ממוצעת של $0.40:<br>'
                    f'RS = 0.80 ÷ 0.40 = 2 → RSI = 100 − (100 ÷ 3) = <strong>66.7</strong><br><br>'
                    f'<strong style="color:{GRN};">RSI &lt; 30</strong> = מניה נמכרה יתר — הקונים חוזרים בד"כ<br>'
                    f'<strong style="color:{AMB};">RSI 30–70</strong> = אזור נורמלי — אין אות חד-משמעי<br>'
                    f'<strong style="color:{RED};">RSI &gt; 70</strong> = מניה נקנתה יתר — תיקון אפשרי</div>',
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LIVE TICKER BAR — shown on every page
# ══════════════════════════════════════════════════════════════════════════════
def _live_bar():
    """Compact live market ticker strip shown on all pages."""
    try:
        ov = fetch_market_overview()
    except Exception:
        return
    if not ov:
        return

    ORDER = ["S&P 500", 'נאסד"ק', "דאו", "VIX", "זהב", "נפט", "ביטקוין", "דולר/שקל"]
    items_html = ""
    for name in ORDER:
        d = ov.get(name)
        if not d:
            continue
        price = d["price"]
        chg   = d.get("chg", 0)
        c     = GRN if chg >= 0 else RED
        arrow = "▲" if chg >= 0 else "▼"
        # Format price nicely
        if name == "ביטקוין":
            p_str = f"${price:,.0f}"
        elif name == "דולר/שקל":
            p_str = f"₪{1/price:.4f}" if price else "—"
        elif price >= 1000:
            p_str = f"{price:,.0f}"
        else:
            p_str = f"{price:.2f}"

        items_html += (
            f'<span style="white-space:nowrap;margin:0 14px;">'
            f'<span style="color:{TX2};font-size:.72rem;">{name}</span>'
            f'&nbsp;<span style="color:{TX};font-weight:700;font-size:.78rem;">{p_str}</span>'
            f'&nbsp;<span style="color:{c};font-size:.72rem;">{arrow}{abs(chg):.2f}%</span>'
            f'</span><span style="color:{BDR2};font-size:.7rem;">|</span>'
        )

    now_str = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f'<div style="background:{SURF};border:1px solid {BDR};border-radius:6px;'
        f'padding:7px 16px;margin-bottom:14px;display:flex;align-items:center;'
        f'justify-content:space-between;overflow-x:auto;direction:ltr;">'
        f'<div style="display:flex;align-items:center;gap:0;flex-wrap:nowrap;">'
        f'<span style="color:{GRN};font-size:.7rem;font-weight:700;'
        f'margin-left:14px;white-space:nowrap;direction:rtl;">'
        f'🟢 LIVE&nbsp;{now_str}</span>'
        f'{items_html}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _guru_analysis(guru: dict, title: str) -> str:
    """Generate contextual analysis of a guru's news item."""
    t   = title.lower()
    name = guru["name"]
    fund = guru["fund"]

    # Detect action type
    if any(w in t for w in ["short", "bet against", "put option", "bearish"]):
        action = "שורט (הימור על ירידה)"
        action_reason = "הגורו מהמר שהמניה תרד — הוא קנה אופציות פוט או מכר בחסר"
    elif any(w in t for w in ["buy", "buys", "purchase", "long", "bullish", "adds", "increased"]):
        action = "קנייה / הגדלת פוזיציה"
        action_reason = "הגורו רכש מניות נוספות — הוא מאמין שהמחיר הנוכחי נמוך מהשווי האמיתי"
    elif any(w in t for w in ["sell", "sells", "sold", "reduce", "exit", "close"]):
        action = "מכירה / הקטנת פוזיציה"
        action_reason = "הגורו מוכר — ייתכן שהמחיר הגיע ליעד שלו, או שהתזה השתנתה"
    elif any(w in t for w in ["warning", "bubble", "crash", "recession", "inflation"]):
        action = "אזהרה / ניתוח מאקרו"
        action_reason = "הגורו מפרסם תחזית כלכלית — לא בהכרח מדובר בעסקה ספציפית"
    else:
        action = "עדכון / הצהרה"
        action_reason = "הגורו שיתף עמדה או מידע כללי על השוק"

    # Guru-specific philosophy
    philosophies = {
        "burry":   "מייקל ברי ידוע בזיהוי בועות שוק. הוא מחפש חברות מוערכות ביתר ומנסה להרוויח מהנפילה שלהן.",
        "buffett": "ורן באפט משקיע לטווח ארוך בחברות עם יתרון תחרותי (moat). הוא קונה כשאחרים מוכרים.",
        "musk":    "אילון מאסק פועל מתוך חזון טכנולוגי ארוך טווח. הצהרותיו משפיעות על השוק לעתים קרובות.",
        "ackman":  "ביל אקמן אקטיביסט — הוא קונה חלקים גדולים בחברות ולוחץ על שינויי ניהול להעלאת ערך.",
        "wood":    "קתי ווד מתמקדת בטכנולוגיה מפריעה. היא משקיעה ב-AI, ביו-טק, ורובוטיקה לטווח של 5 שנים+.",
        "dalio":   "ריי דליו מנהל תיק לפי עקרונות מאקרו. הוא מחלק סיכונים בין נכסים שונים ומגיב לציקלים כלכליים.",
        "druckenmiller": "סטנלי דרוקנמילר אחד מהמנהלים הטובים בהיסטוריה. הוא ממנף תחזיות מאקרו לעסקאות גדולות.",
        "icahn":   "קרל אייקן משקיע אקטיביסט — הוא לוחץ על חברות לחלק דיבידנדים, לבצע רכישות עצמיות, או למכור.",
        "tepper":  "דיוויד טפר ידוע בקניית נכסים במצוקה (distressed). הוא מנצל משברים לרכישה במחיר נמוך.",
        "tudor":   "פול טיודור ג'ונס מתמחה במסחר טכני ומאקרו. הוא מפורסם בניבוי קריסת 1987.",
        "soros":   "ג'ורג' סורוס מפורסם בהימורי מאקרו ענקיים, כגון הימור נגד הלירה הבריטית ב-1992.",
        "dimon":   "ג'יימי דיימון מנכ\"ל JPMorgan — הצהרותיו משקפות את דעת הממסד הפיננסי על כלכלת ארה\"ב.",
        "fink":    "לארי פינק מנהל את BlackRock, הקרן הגדולה בעולם. עמדותיו משפיעות על זרמי ההון הגלובליים.",
    }
    philosophy = philosophies.get(guru["id"], f"{name} מנהל את {fund}.")

    # Detect mentioned stocks/assets
    stocks_mentioned = []
    common = {"apple":"AAPL","nvidia":"NVDA","tesla":"TSLA","microsoft":"MSFT",
               "palantir":"PLTR","amazon":"AMZN","google":"GOOG","meta":"META",
               "berkshire":"BRK.B","jpmorgan":"JPM","bitcoin":"BTC","gold":"GLD"}
    for kw, sym in common.items():
        if kw in t:
            stocks_mentioned.append(sym)

    stock_line = ""
    if stocks_mentioned:
        stock_line = f"\n\n📌 **מניות/נכסים מוזכרים:** {', '.join(stocks_mentioned)}"

    return (f"**פעולה שזוהתה:** {action}\n\n"
            f"**מה זה אומר:** {action_reason}\n\n"
            f"**על {name}:** {philosophy}"
            f"{stock_line}")


@st.cache_data(ttl=3600, show_spinner=False)
def _translate_he(text: str) -> str:
    """Translate English text to Hebrew via Google Translate free endpoint."""
    if not text:
        return text
    try:
        import urllib.request as _ur
        url = (f"https://translate.googleapis.com/translate_a/single"
               f"?client=gtx&sl=en&tl=iw&dt=t&q={urllib.parse.quote(text)}")
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=5) as r:
            data = json.load(r)
        translated = "".join(seg[0] for seg in data[0] if seg[0])
        return translated if translated else text
    except Exception:
        return text


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: GURU TRACKER — גורו טראקר
# ══════════════════════════════════════════════════════════════════════════════
def page_guru():
    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:14px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            גורו טראקר
        </div>
        <div style="color:{TX2};font-size:.83rem;margin-top:4px;">
            עדכוני חדשות על המשקיעים הגדולים בעולם — מתעדכן כל 15 דקות
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Telegram status bar ───────────────────────────────────────────────────
    cfg = _telegram_cfg()
    tg_col, inp_col = st.columns([1, 3])
    with tg_col:
        if cfg.get("token"):
            st.markdown(f"<div style='color:{GRN};font-size:.82rem;padding-top:8px;direction:rtl;'>"
                        f"📱 Telegram מחובר ✅</div>", unsafe_allow_html=True)
        else:
            with st.expander("📱 חבר Telegram"):
                tc1, tc2, tc3 = st.columns([2, 2, 0.8])
                with tc1:
                    new_token = st.text_input("Bot Token", value="", placeholder="123456789:AAF...", key="tg_token")
                with tc2:
                    new_chat  = st.text_input("Chat ID",   value="", placeholder="123456789",       key="tg_chat")
                with tc3:
                    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                    if st.button("שמור", key="tg_save", type="primary", use_container_width=True):
                        save_json(TELEGRAM_FILE, {"token": new_token.strip(), "chat_id": new_chat.strip()})
                        _send_telegram("✅ <b>מנתח מניות</b>\nהתראות Telegram הופעלו! 🚀")
                        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Tabs: חדשות / פוזיציות ────────────────────────────────────────────────
    tab_news, tab_pos = st.tabs(["📰 חדשות", "🏛️ פוזיציות (13F SEC)"])

    # ════════════════════════ TAB: פוזיציות ════════════════════════════════════
    with tab_pos:
        st.markdown(f"""<div style="direction:rtl;color:{TX2};font-size:.82rem;
            margin-bottom:12px;">
            נתוני אחזקות מדוחות 13F לרשות ניירות ערך האמריקאית (SEC) — מתעדכן רבעונית
        </div>""", unsafe_allow_html=True)

        gurus_with_cik = [g for g in GURUS if g.get("cik")]
        pos_names = [f"{g['emoji']} {g['name']}" for g in gurus_with_cik]
        pg_col, _ = st.columns([2, 4])
        with pg_col:
            pos_sel = st.selectbox("בחר משקיע", pos_names,
                                   key="pos_sel", label_visibility="collapsed")

        sel_guru = next((g for g in gurus_with_cik
                         if f"{g['emoji']} {g['name']}" == pos_sel), None)
        if sel_guru:
            with st.spinner(f"מביא אחזקות {sel_guru['name']} מ-SEC..."):
                holdings = _fetch_13f(sel_guru["cik"])

            if not holdings:
                st.info("לא נמצאו נתונים עדכניים — ייתכן שהדיווח הרבעוני טרם הוגש.")
            else:
                date_str = holdings[0].get("date", "")
                total_val = sum(h["value_k"] for h in holdings)
                st.markdown(f"""<div style="direction:rtl;margin-bottom:10px;">
                    <span style="color:{TX2};font-size:.8rem;">
                    דיווח מתאריך: <b style="color:{CYAN};">{date_str}</b> &nbsp;|&nbsp;
                    סה"כ תיק מדווח: <b style="color:{GRN};">${total_val/1000:,.0f}M</b>
                    </span></div>""", unsafe_allow_html=True)

                for i, h in enumerate(holdings[:20]):
                    pct = h["value_k"] / total_val * 100 if total_val else 0
                    val_m = h["value_k"] / 1000
                    bar_w = int(pct * 3)
                    rank_c = GRN if i < 3 else (CYAN if i < 10 else TX2)
                    st.markdown(f"""
                    <div style="background:{SURF2};border:1px solid {BDR};
                         border-radius:8px;padding:10px 14px;margin-bottom:6px;
                         direction:ltr;">
                      <div style="display:flex;align-items:center;gap:10px;">
                        <span style="color:{rank_c};font-weight:800;font-size:.9rem;
                              min-width:24px;">#{i+1}</span>
                        <div style="flex:1;">
                          <div style="font-size:.85rem;font-weight:600;color:{TX};">
                            {h['name']}</div>
                          <div style="margin-top:4px;background:{SURF3};border-radius:3px;
                               height:4px;width:100%;">
                            <div style="background:{rank_c};height:4px;border-radius:3px;
                                 width:{min(bar_w,100)}%;"></div>
                          </div>
                        </div>
                        <div style="text-align:right;min-width:100px;">
                          <div style="color:{GRN};font-weight:700;font-size:.85rem;">
                            ${val_m:,.1f}M</div>
                          <div style="color:{TX3};font-size:.72rem;">{pct:.1f}%</div>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

    # ════════════════════════ TAB: חדשות ═══════════════════════════════════════
    with tab_news:
        # ── Guru selector ─────────────────────────────────────────────────────
        guru_names = [f"{g['emoji']} {g['name']}" for g in GURUS]
        sel_col, _ = st.columns([2, 4])
        with sel_col:
            sel = st.selectbox("בחר משקיע", ["📰 כל החדשות"] + guru_names,
                               key="guru_sel", label_visibility="collapsed")

        selected_ids = ([g["id"] for g in GURUS] if sel == "📰 כל החדשות"
                        else [g["id"] for g in GURUS if f"{g['emoji']} {g['name']}" == sel])

        # ── Fetch + translate news ─────────────────────────────────────────
        rc1, rc2 = st.columns([5, 1])
        with rc2:
            st.button("🔄 רענן", key="guru_refresh", use_container_width=True)

        with st.spinner("מביא ומתרגם חדשות..."):
            all_items = []
            for guru in [g for g in GURUS if g["id"] in selected_ids]:
                rss_url = (
                    f"https://news.google.com/rss/search"
                    f"?q={urllib.parse.quote(guru['q'])}"
                    f"&hl=en-US&gl=US&ceid=US:en&tbs=qdr:w"
                )
                try:
                    items = _parse_rss(rss_url, guru["name"], max_items=8)
                    for item in items:
                        item["_guru"] = guru
                    all_items.extend(items)
                except Exception:
                    pass

        all_items.sort(key=lambda x: x.get("providerPublishTime", 0), reverse=True)

        if not all_items:
            st.markdown(f"""<div style="text-align:center;padding:50px;color:{TX2};">
                <div style="font-size:2.5rem;">📭</div>
                <div style="margin-top:10px;">לא נמצאו חדשות כרגע — נסה ללחוץ רענן.</div>
            </div>""", unsafe_allow_html=True)
        else:
            for item in all_items[:25]:
                guru    = item["_guru"]
                title   = item.get("title", "")
                link    = item.get("link", "#")
                pub     = item.get("publisher", guru["name"])
                ts      = item.get("providerPublishTime", 0)
                ago     = _time_ago(ts) if ts else ""
                sent_icon, sent_label, sent_c = _sentiment(title)
                border_c = {"🟢": GRN, "🔴": RED}.get(sent_icon, BDR2)
                heb_title = _translate_he(title)

                st.markdown(f"""
                <div style="background:{SURF2};border:1px solid {BDR};
                     border-right:4px solid {border_c};border-radius:0 12px 12px 0;
                     padding:12px 16px;margin-bottom:8px;">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;
                              direction:rtl;flex-wrap:wrap;">
                    <span style="font-size:1.1rem;">{guru['emoji']}</span>
                    <span style="font-size:.75rem;font-weight:700;color:{CYAN};">{guru['name']}</span>
                    <span style="font-size:.7rem;color:{TX3};">·</span>
                    <span style="font-size:.7rem;color:{TX3};">{pub}</span>
                    <span style="font-size:.7rem;color:{TX3};">·</span>
                    <span style="font-size:.7rem;color:{TX3};">{ago}</span>
                    <span style="margin-right:auto;font-size:.7rem;
                          color:{sent_c};font-weight:600;">{sent_icon} {sent_label}</span>
                  </div>
                  <div style="direction:rtl;">
                    <a href="{link}" target="_blank"
                       style="color:{TX};font-size:.85rem;font-weight:600;
                              text-decoration:none;line-height:1.6;">{heb_title}</a>
                  </div>
                </div>""", unsafe_allow_html=True)

                item_key = f"analysis_{abs(hash(title)) % 999999}"
                with st.expander("🧠 ניתוח — למה הגורו עשה את זה?"):
                    st.markdown(_guru_analysis(guru, title))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ISRAEL — מניות ישראל
# ══════════════════════════════════════════════════════════════════════════════
def page_israel():
    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:14px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            🇮🇱 מניות ישראל
        </div>
        <div style="color:{TX2};font-size:.83rem;margin-top:4px;">
            מניות ישראליות — בורסת תל אביב ודואל-ליסטינג בנאסד"ק
        </div>
    </div>""", unsafe_allow_html=True)

    with st.spinner("סורק מניות ישראל..."):
        results = []
        def _fetch_il(stock):
            q = _agent_quote(stock["t"])
            if q:
                q["sym"]  = stock["t"]
                q["name"] = stock["n"]
                q["sec"]  = stock["s"]
            return q

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(_fetch_il, s): s for s in TASE_UNIVERSE}
            for fut in concurrent.futures.as_completed(futs):
                try:
                    r = fut.result()
                    if r and r.get("price"):
                        results.append(r)
                except Exception:
                    pass

    results.sort(key=lambda x: abs(x.get("chg", 0)), reverse=True)

    if not results:
        st.info("לא ניתן לטעון נתונים כרגע — נסה שוב בעוד מספר דקות.")
        return

    # Summary bar
    gainers = sum(1 for r in results if r.get("chg", 0) > 0)
    losers  = sum(1 for r in results if r.get("chg", 0) < 0)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
            border-radius:6px;padding:12px;text-align:center;direction:rtl;">
            <div style="color:{GRN};font-size:1.3rem;font-weight:800;">{gainers}</div>
            <div style="color:{TX2};font-size:.75rem;">עולות</div></div>""",
            unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
            border-radius:6px;padding:12px;text-align:center;direction:rtl;">
            <div style="color:{RED};font-size:1.3rem;font-weight:800;">{losers}</div>
            <div style="color:{TX2};font-size:.75rem;">יורדות</div></div>""",
            unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
            border-radius:6px;padding:12px;text-align:center;direction:rtl;">
            <div style="color:{CYAN};font-size:1.3rem;font-weight:800;">{len(results)}</div>
            <div style="color:{TX2};font-size:.75rem;">מניות</div></div>""",
            unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, r in enumerate(results):
        chg   = r.get("chg", 0)
        price = r.get("price", 0)
        rsi   = r.get("rsi", 50)
        c     = GRN if chg >= 0 else RED
        sym   = r["sym"]
        is_tase = sym.endswith(".TA")
        currency = "₪" if is_tase else "$"
        rsi_c = RED if rsi > 70 else (GRN if rsi < 30 else AMB)

        with cols[i % 3]:
            st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
                border-top:3px solid {c};border-radius:6px;padding:14px;
                margin-bottom:10px;direction:rtl;cursor:pointer;"
                onclick="void(0)">
                <div style="font-size:.7rem;color:{TX3};margin-bottom:2px;">{r.get('sec','')}</div>
                <div style="font-size:.85rem;font-weight:800;color:{TX};">{r['name']}</div>
                <div style="font-size:.7rem;color:{TX3};margin-bottom:8px;">{sym}</div>
                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                  <span style="font-size:1.15rem;font-weight:700;color:{TX};">
                    {currency}{price:,.2f}</span>
                  <span style="font-size:.85rem;font-weight:700;color:{c};">
                    {'▲' if chg>=0 else '▼'}{abs(chg):.2f}%</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:6px;">
                  <span style="font-size:.7rem;color:{TX3};">RSI</span>
                  <span style="font-size:.75rem;font-weight:700;color:{rsi_c};">{rsi:.0f}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("📊 נתח", key=f"il_{sym}", use_container_width=True):
                st.session_state["page"]       = "home"
                st.session_state["search_sym"] = sym
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SCREENER — סורק טכני
# ══════════════════════════════════════════════════════════════════════════════
def page_screener():
    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:14px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            סורק טכני
        </div>
        <div style="color:{TX2};font-size:.83rem;margin-top:4px;">
            סנן {len(DEEP_SCAN_UNIVERSE)} מניות לפי קריטריונים טכניים בזמן אמת
        </div>
    </div>""", unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        rsi_min, rsi_max = st.slider("טווח RSI", 0, 100, (0, 45), key="sc_rsi")
    with fc2:
        ma_filter = st.selectbox("מול MA50", ["הכל", "מעל MA50", "מתחת MA50"], key="sc_ma")
    with fc3:
        all_sectors = ["הכל"] + sorted({s.get("s", s.get("c", "אחר")) for s in DEEP_SCAN_UNIVERSE})
        sector_filter = st.selectbox("סקטור", all_sectors, key="sc_sec")
    with fc4:
        sort_by = st.selectbox("מיין לפי", ["RSI נמוך → גבוה", "RSI גבוה → נמוך", "שינוי יומי"], key="sc_sort")

    run_col, _ = st.columns([1, 4])
    with run_col:
        if st.button("🔍 הרץ סריקה", key="sc_run", type="primary", use_container_width=True):
            st.session_state["sc_results"] = None
            st.session_state["sc_running"] = True
            st.rerun()

    if not st.session_state.get("sc_running") and st.session_state.get("sc_results") is None:
        st.markdown(f"""<div style="text-align:center;padding:60px 0;color:{TX2};direction:rtl;">
            <div style="font-size:3rem;margin-bottom:12px;">🔍</div>
            <div style="font-size:.95rem;">הגדר פילטרים ולחץ "הרץ סריקה"</div>
        </div>""", unsafe_allow_html=True)
        return

    candidates = [s for s in DEEP_SCAN_UNIVERSE
                  if sector_filter == "הכל" or s.get("s", s.get("c", "")) == sector_filter]

    if st.session_state.get("sc_running"):
        with st.spinner(f"סורק {len(candidates)} מניות בזמן אמת..."):
            def _scan_one(stock):
                try:
                    q = _agent_quote(stock["t"])
                    if not q or q.get("rsi") is None:
                        return None
                    rsi   = q["rsi"]
                    price = q.get("price", 0)
                    ma50  = q.get("ma50")
                    if not (rsi_min <= rsi <= rsi_max):
                        return None
                    if ma_filter == "מעל MA50" and (not ma50 or price < ma50):
                        return None
                    if ma_filter == "מתחת MA50" and (not ma50 or price >= ma50):
                        return None
                    return {**stock, **q}
                except Exception:
                    return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=14) as ex:
                raw = list(ex.map(_scan_one, candidates))
            st.session_state["sc_results"] = [r for r in raw if r]
            st.session_state["sc_running"]  = False
            st.rerun()

    results = st.session_state.get("sc_results") or []
    if not results:
        st.warning("לא נמצאו מניות התואמות את הפילטרים. נסה להרחיב את הקריטריונים.")
        return

    if sort_by == "RSI נמוך → גבוה":
        results = sorted(results, key=lambda x: x.get("rsi", 99))
    elif sort_by == "RSI גבוה → נמוך":
        results = sorted(results, key=lambda x: x.get("rsi", 0), reverse=True)
    else:
        results = sorted(results, key=lambda x: x.get("chg", 0), reverse=True)

    st.markdown(f"""<div style="color:{GRN};font-size:.85rem;direction:rtl;margin-bottom:14px;">
        ✅ נמצאו <b>{len(results)}</b> מניות
    </div>""", unsafe_allow_html=True)

    cols = st.columns(3)
    for i, r in enumerate(results):
        with cols[i % 3]:
            rsi_v = r.get("rsi", 50)
            price = r.get("price", 0)
            chg   = r.get("chg", 0)
            ma50  = r.get("ma50")
            chg_c = GRN if chg >= 0 else RED
            rsi_c = GRN if rsi_v < 35 else AMB if rsi_v < 60 else RED
            above_ma = ma50 and price > ma50

            st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
                border-radius:8px;padding:16px;margin-bottom:12px;direction:rtl;
                border-top:3px solid {rsi_c};">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <div style="font-size:1.1rem;font-weight:800;color:{CYAN};">{r['t']}</div>
                        <div style="font-size:.75rem;color:{TX2};margin-top:2px;">{r.get('n','')}</div>
                        <div style="font-size:.66rem;color:{TX3};margin-top:4px;
                            background:{SURF};border-radius:6px;padding:2px 7px;display:inline-block;">
                            {r.get('s', r.get('c',''))}
                        </div>
                    </div>
                    <div style="text-align:left;">
                        <div style="font-size:1rem;font-weight:700;color:{TX};">${price:,.2f}</div>
                        <div style="font-size:.78rem;color:{chg_c};">{'▲' if chg>=0 else '▼'} {abs(chg):.1f}%</div>
                    </div>
                </div>
                <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
                    <div style="background:{rsi_c}22;border:1px solid {rsi_c}55;
                        border-radius:8px;padding:4px 10px;font-size:.76rem;">
                        <span style="color:{TX3};">RSI </span>
                        <span style="color:{rsi_c};font-weight:700;">{rsi_v:.0f}</span>
                    </div>
                    <div style="background:{''+GRN+'22;border:1px solid '+GRN+'44;color:'+GRN if above_ma else RED+'22;border:1px solid '+RED+'44;color:'+RED};
                        border-radius:8px;padding:4px 10px;font-size:.74rem;">
                        {'מעל MA50' if above_ma else 'מתחת MA50'}
                    </div>
                </div>
                {'<div style="margin-top:8px;font-size:.74rem;color:'+TX2+';line-height:1.5;">'+r.get("u","")[:90]+'</div>' if r.get("u") else ""}
            </div>""", unsafe_allow_html=True)

            if st.button(f"📊 נתח {r['t']}", key=f"sc_go_{r['t']}_{i}",
                         use_container_width=True):
                st.session_state["search_ticker"] = r["t"]
                st.session_state["page"] = "home"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EARNINGS CALENDAR — לוח שנה רווחים
# ══════════════════════════════════════════════════════════════════════════════
def page_earnings():
    portfolio  = load_json(PF_FILE)
    watchlist  = load_json(WL_FILE)
    pf_syms    = [h["sym"] for h in portfolio]
    all_syms   = list(dict.fromkeys(pf_syms + watchlist))

    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:14px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            לוח שנה — דוחות רווחים
        </div>
        <div style="color:{TX2};font-size:.83rem;margin-top:4px;">
            דוחות רבעוניים קרובים עבור התיק ורשימת המעקב שלך
        </div>
    </div>""", unsafe_allow_html=True)

    if not all_syms:
        st.info("הוסף מניות לתיק או לרשימת המעקב כדי לראות דוחות קרובים.")
        return

    with st.spinner("מביא תאריכי דוחות..."):
        upcoming = []
        def _get_earn(sym):
            try:
                cal = fetch_calendar(sym)
                dt  = cal.get("earnings_date")
                if dt:
                    days = (pd.Timestamp(dt) - pd.Timestamp(datetime.now())).days
                    return {"sym": sym, "date": dt, "days": days,
                            "in_pf": sym in pf_syms}
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            for r in ex.map(_get_earn, all_syms):
                if r and r["days"] >= -7:
                    upcoming.append(r)

    upcoming = sorted(upcoming, key=lambda x: x["days"])

    if not upcoming:
        st.markdown(f"""<div style="text-align:center;padding:50px;color:{TX2};">
            <div style="font-size:2.5rem;">📭</div>
            <div style="margin-top:10px;">לא נמצאו דוחות קרובים (עד 90 ימים)</div>
        </div>""", unsafe_allow_html=True)
        return

    for r in upcoming:
        sym    = r["sym"]
        days   = r["days"]
        dt_str = pd.Timestamp(r["date"]).strftime("%d/%m/%Y")
        if days < 0:
            label, bc = f"לפני {abs(days)} ימים", TX3
        elif days == 0:
            label, bc = "היום! 🔥", RED
        elif days <= 7:
            label, bc = f"בעוד {days} ימים", RED
        elif days <= 30:
            label, bc = f"בעוד {days} ימים", AMB
        else:
            label, bc = f"בעוד {days} ימים", TX2

        tag = f"<span style='background:{CYAN}22;color:{CYAN};border-radius:6px;padding:1px 7px;font-size:.68rem;margin-right:6px;'>תיק</span>" if r["in_pf"] else ""

        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
            border-radius:6px;padding:14px 18px;margin-bottom:8px;direction:rtl;
            display:flex;align-items:center;justify-content:space-between;
            border-right:4px solid {bc};">
            <div>
                {tag}
                <span style="font-size:1rem;font-weight:700;color:{CYAN};">{sym}</span>
                <span style="font-size:.8rem;color:{TX2};margin-right:10px;">{dt_str}</span>
            </div>
            <div style="font-size:.85rem;font-weight:700;color:{bc};">{label}</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PRICE ALERTS — התראות מחיר
# ══════════════════════════════════════════════════════════════════════════════
def page_alerts():
    watchlist = load_json(WL_FILE)
    portfolio = load_json(PF_FILE)
    pf_syms   = [h["sym"] for h in portfolio]
    all_syms  = list(dict.fromkeys(pf_syms + watchlist))
    alerts    = load_json(ALERTS_FILE) if os.path.exists(ALERTS_FILE) else {}
    if isinstance(alerts, list):
        alerts = {}

    st.markdown(f"""<div style="direction:rtl;padding-bottom:14px;border-bottom:1px solid {BDR2};margin-bottom:14px;">
        <div style="font-size:1.5rem;font-weight:800;color:{TX};letter-spacing:-.02em;">
            התראות מחיר
        </div>
        <div style="color:{TX2};font-size:.83rem;margin-top:4px;">
            קבל התראה כשמניה חוצה יעד מחיר
        </div>
    </div>""", unsafe_allow_html=True)

    if not all_syms:
        st.info("הוסף מניות לתיק או לרשימת המעקב כדי להגדיר התראות.")
        return

    changed = False
    for sym in all_syms:
        sym_alerts = alerts.get(sym, {})
        price_now  = fast_price(sym) or 0
        tag = "📂 תיק" if sym in pf_syms else "👁️ מעקב"

        with st.expander(f"{tag}  {sym}  —  ${price_now:,.2f} כרגע"):
            ac1, ac2, ac3 = st.columns([1, 1, 0.6])
            with ac1:
                above = st.number_input(
                    "התראה כש**מחיר עולה מעל** ($)",
                    value=float(sym_alerts.get("above") or 0),
                    min_value=0.0, step=1.0, key=f"al_above_{sym}")
            with ac2:
                below = st.number_input(
                    "התראה כש**מחיר יורד מתחת** ($)",
                    value=float(sym_alerts.get("below") or 0),
                    min_value=0.0, step=1.0, key=f"al_below_{sym}")
            with ac3:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("שמור ✓", key=f"al_save_{sym}", type="primary",
                             use_container_width=True):
                    alerts[sym] = {}
                    if above > 0:
                        alerts[sym]["above"] = above
                    if below > 0:
                        alerts[sym]["below"] = below
                    save_json(ALERTS_FILE, alerts)
                    st.success(f"התראות עבור {sym} נשמרו!")
                    changed = True

            # Show active alerts
            if sym_alerts:
                parts = []
                if sym_alerts.get("above"):
                    hit = price_now >= sym_alerts["above"]
                    c   = GRN if hit else TX3
                    parts.append(f"<span style='color:{c};'>↑ מעל ${sym_alerts['above']:,.0f}{'  ✅ הופעל!' if hit else ''}</span>")
                if sym_alerts.get("below"):
                    hit = price_now > 0 and price_now <= sym_alerts["below"]
                    c   = RED if hit else TX3
                    parts.append(f"<span style='color:{c};'>↓ מתחת ל-${sym_alerts['below']:,.0f}{'  🔴 הופעל!' if hit else ''}</span>")
                if parts:
                    st.markdown(f"<div style='font-size:.8rem;margin-top:6px;direction:rtl;'>"
                                f"התראות פעילות: {'  ·  '.join(parts)}</div>",
                                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
_ensure_agents()
_nav()
_live_bar()

_page = st.session_state["page"]
if   _page == "home":      page_home()
elif _page == "portfolio": page_portfolio()
elif _page == "watchlist": page_watchlist()
elif _page == "guru":      page_guru()
elif _page == "israel":    page_israel()
elif _page == "screener":  page_screener()
elif _page == "earnings":  page_earnings()
elif _page == "alerts":    page_alerts()
elif _page == "compare":   page_compare()
elif _page == "demo":      page_demo()
elif _page == "news":      page_news()
elif _page == "agents":    page_agents()
elif _page == "learn":     page_learn()

st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
st.caption("⚠️ אפליקציה זו מיועדת למטרות לימוד בלבד ואינה מהווה ייעוץ פיננסי.")
