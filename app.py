import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="מנתח מניות", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Palette ────────────────────────────────────────────────────────────────────
BG    = "#060d1a";  SURF  = "#0c1828";  SURF2 = "#112035";  SURF3 = "#162843"
BDR   = "#1b3050";  BDR2  = "#24446e"
CYAN  = "#00b4d8";  CDIM  = "rgba(0,180,216,.12)"
GRN   = "#22c55e";  GDIM  = "rgba(34,197,94,.10)"
RED   = "#ef4444";  RDIM  = "rgba(239,68,68,.10)"
AMB   = "#f59e0b";  ADIM  = "rgba(245,158,11,.10)"
PUR   = "#a78bfa";  PDIM  = "rgba(167,139,250,.08)"
TX    = "#e8f4fd";  TX2   = "#6b9bc0";  TX3 = "#3a6080"

PB = dict(
    plot_bgcolor=SURF, paper_bgcolor=SURF,
    font=dict(color=TX, family="Heebo, sans-serif", size=11),
    xaxis=dict(gridcolor=BDR, zerolinecolor=BDR, tickfont=dict(color=TX2)),
    yaxis=dict(gridcolor=BDR, zerolinecolor=BDR, tickfont=dict(color=TX2)),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=8, r=8, t=36, b=8),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=SURF2, bordercolor=BDR, font=dict(color=TX, size=11)),
)

GROWTH = [
    {"t":"MRVL", "n":"Marvell Technology",  "c":"מוליכים למחצה", "d":"שבבי AI לתשתיות ענן",     "a":CYAN},
    {"t":"NVDA", "n":"NVIDIA",              "c":"מוליכים למחצה", "d":"מנהיגה עולמית בשבבי AI",  "a":CYAN},
    {"t":"AMD",  "n":"AMD",                 "c":"מוליכים למחצה", "d":"שבבים למחשוב ו-AI",        "a":CYAN},
    {"t":"ARM",  "n":"ARM Holdings",        "c":"מוליכים למחצה", "d":"ארכיטקטורת שבבים מובילה", "a":CYAN},
    {"t":"CRWD", "n":"CrowdStrike",         "c":"סייבר",         "d":"אבטחת סייבר מבוססת AI",   "a":RED},
    {"t":"PLTR", "n":"Palantir",            "c":"AI · ענן",      "d":"ניתוח נתונים ו-AI",        "a":PUR},
    {"t":"DDOG", "n":"Datadog",             "c":"AI · ענן",      "d":"ניטור ואובזרבביליות",      "a":PUR},
    {"t":"NET",  "n":"Cloudflare",          "c":"AI · ענן",      "d":"תשתית אינטרנט ואבטחה",    "a":PUR},
    {"t":"AXON", "n":"Axon Enterprise",     "c":"סייבר",         "d":"טכנולוגיות AI לביטחון",   "a":RED},
    {"t":"TTD",  "n":"The Trade Desk",      "c":"AI · ענן",      "d":"פרסום דיגיטלי מבוסס AI",  "a":PUR},
]

# ── CSS ────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');
html,body,[class*="css"],*{{font-family:'Heebo',sans-serif!important;box-sizing:border-box}}
.stApp{{background:{BG}!important;color:{TX};direction:rtl}}
.main .block-container{{padding:0 2rem 4rem;max-width:1440px}}
[data-testid="collapsedControl"],section[data-testid="stSidebar"]{{display:none!important}}
p,span,label,div,h1,h2,h3,h4,h5,h6{{color:{TX};direction:rtl;text-align:right}}
h1{{font-weight:800!important}}h2{{font-weight:700!important}}h3{{font-weight:600!important}}

/* search */
.sw .stTextInput>div>div{{background:{SURF}!important;border:2px solid {CYAN}!important;
  border-radius:16px!important;box-shadow:0 0 0 5px {CDIM},0 8px 40px rgba(0,0,0,.6)!important}}
.sw .stTextInput input{{background:transparent!important;color:{TX}!important;
  font-size:1.5rem!important;font-weight:800!important;padding:22px 28px!important;
  text-align:center!important;direction:ltr!important;letter-spacing:4px!important;caret-color:{CYAN}!important}}
.sw .stTextInput input::placeholder{{color:{TX3}!important;font-size:.9rem!important;
  font-weight:400!important;letter-spacing:.5px!important;direction:rtl!important}}
.sw label{{display:none!important}}

/* selectbox */
.stSelectbox>div>div{{background:{SURF}!important;border:1px solid {BDR}!important;
  border-radius:10px!important;color:{TX}!important}}
.stSelectbox>div>div:hover{{border-color:{CYAN}!important}}
.stSelectbox svg{{fill:{TX2}!important}}

/* tabs */
.stTabs [data-baseweb="tab-list"]{{background:{SURF};border-bottom:1px solid {BDR};
  border-radius:14px 14px 0 0;padding:0 16px;gap:4px}}
.stTabs [data-baseweb="tab"]{{background:transparent;color:{TX2}!important;
  font-size:.95rem!important;font-weight:600!important;padding:14px 22px!important;
  border-bottom:2px solid transparent!important;border-radius:0!important;transition:color .2s!important}}
.stTabs [data-baseweb="tab"]:hover{{color:{TX}!important;background:{CDIM}!important}}
.stTabs [aria-selected="true"]{{color:{TX}!important;border-bottom:2px solid {CYAN}!important;background:transparent!important}}
.stTabs [data-baseweb="tab-panel"]{{background:{SURF};border:1px solid {BDR};border-top:none;
  border-radius:0 0 14px 14px;padding:24px 20px}}

/* expander */
.streamlit-expanderHeader{{background:{SURF}!important;color:{TX}!important;
  border:1px solid {BDR}!important;border-radius:10px!important;
  font-weight:600!important;padding:12px 16px!important}}
.streamlit-expanderHeader:hover{{border-color:{BDR2}!important}}
.streamlit-expanderContent{{background:{SURF}!important;border:1px solid {BDR}!important;
  border-top:none!important;border-radius:0 0 10px 10px!important;padding:16px!important}}

/* number input */
.stNumberInput input{{background:{SURF}!important;border:1px solid {BDR}!important;
  border-radius:8px!important;color:{TX}!important;direction:ltr!important;
  text-align:right!important;font-size:.95rem!important;padding:8px 12px!important}}
.stNumberInput input:focus{{border-color:{CYAN}!important;box-shadow:0 0 0 2px {CDIM}!important}}
.stNumberInput label{{color:{TX}!important;font-weight:600!important}}
div[data-baseweb="input"]{{background:{SURF}!important;border-color:{BDR}!important}}

/* gs buttons */
.gsb button{{background:{SURF2}!important;border:1px solid {BDR}!important;
  border-radius:8px!important;color:{TX}!important;font-weight:700!important;
  font-size:.95rem!important;letter-spacing:1px!important;padding:10px!important;transition:all .2s!important}}
.gsb button:hover{{border-color:{CYAN}!important;background:{CDIM}!important;color:{CYAN}!important}}

/* misc */
hr{{border:none;border-top:1px solid {BDR}!important;margin:.75rem 0!important}}
.stCaption{{color:{TX3}!important;font-size:.73rem!important}}
.stMarkdown{{text-align:right!important}}
.stSpinner>div{{border-top-color:{CYAN}!important}}
.stInfo{{background:rgba(0,180,216,.06)!important;border:1px solid rgba(0,180,216,.2)!important;border-radius:10px!important}}
.stError{{background:{RDIM}!important;border:1px solid rgba(239,68,68,.25)!important;border-radius:10px!important}}
[data-testid="column"]{{padding:0 6px!important}}
.stMarkdown p{{margin:0}}
</style>""", unsafe_allow_html=True)


# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_history(sym, period):
    df = yf.Ticker(sym).history(period=period)
    return _ind(df) if not df.empty else df

@st.cache_data(ttl=3600)
def fetch_bt(sym):
    df = yf.Ticker(sym).history(start="2017-01-01")
    return _ind(df) if not df.empty else df

@st.cache_data(ttl=300)
def fetch_info(sym): return yf.Ticker(sym).info

@st.cache_data(ttl=3600)
def fetch_fin(sym):  return yf.Ticker(sym).financials

def _ind(df):
    df = df.copy()
    d = df["Close"].diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    df["RSI"]     = 100 - 100/(1+g/l)
    df["MA50"]    = df["Close"].rolling(50).mean()
    df["MA200"]   = df["Close"].rolling(200).mean()
    ma = df["Close"].rolling(20).mean()
    sd = df["Close"].rolling(20).std()
    df["BBU"] = ma + 2*sd;  df["BBL"] = ma - 2*sd
    return df


# ── Analysis ───────────────────────────────────────────────────────────────────
def get_rec(df, info):
    r = df.iloc[-1]
    c, rsi, m50, m200 = r["Close"], r["RSI"], r["MA50"], r["MA200"]
    score, sigs = 0, []
    if not np.isnan(rsi):
        if   rsi < 30: score+=2; sigs.append((True,  f"RSI {rsi:.1f} — מכירת יתר"))
        elif rsi > 70: score-=2; sigs.append((False, f"RSI {rsi:.1f} — קניית יתר"))
        else:                    sigs.append((None,  f"RSI {rsi:.1f} — נייטרלי"))
    if not np.isnan(m50):
        if c>m50:  score+=1; sigs.append((True,  f"מחיר מעל MA50  (${m50:.0f})"))
        else:      score-=1; sigs.append((False, f"מחיר מתחת MA50  (${m50:.0f})"))
    if not np.isnan(m200):
        if c>m200: score+=1; sigs.append((True,  f"מחיר מעל MA200 (${m200:.0f})"))
        else:      score-=1; sigs.append((False, f"מחיר מתחת MA200 (${m200:.0f})"))
    if not (np.isnan(m50) or np.isnan(m200)):
        if m50>m200: score+=1; sigs.append((True,  "צלב זהב — MA50 > MA200"))
        else:        score-=1; sigs.append((False, "צלב מוות — MA50 < MA200"))
    if score>=2:    return "קנה",  GRN, sigs, score
    elif score<=-2: return "מכור", RED, sigs, score
    else:           return "המתן", AMB, sigs, score


def gen_explain(df, info, label, score):
    r    = df.iloc[-1]
    c    = r["Close"]; rsi = r["RSI"]; m50 = r["MA50"]; m200 = r["MA200"]
    lc   = {"קנה":GRN,"מכור":RED,"המתן":AMB}[label]
    pct  = max(5, min(95, (score+5)/10*100))
    stg  = "חזק מאוד" if abs(score)>=4 else "חזק" if abs(score)>=3 else "מתון"

    # score bar
    bar = f"""
    <div style="background:{SURF2};border:1px solid {BDR};border-radius:14px;
                padding:20px 22px;margin-bottom:16px;direction:rtl;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div style="font-size:.78rem;color:{TX2};font-weight:500;">חוזק האות: <strong style="color:{lc}">{stg}</strong></div>
        <div style="font-size:2rem;font-weight:900;color:{lc};letter-spacing:2px;">{label}</div>
      </div>
      <div style="position:relative;height:8px;border-radius:4px;
                  background:linear-gradient(90deg,{RED} 0%,{AMB} 50%,{GRN} 100%);">
        <div style="position:absolute;top:-4px;left:{pct:.1f}%;width:16px;height:16px;
                    background:{lc};border-radius:50%;transform:translateX(-50%);
                    box-shadow:0 0 10px {lc}99;border:2px solid {BG};"></div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:6px;">
        <div style="color:{RED};font-size:.68rem;font-weight:600;">◄ דובי</div>
        <div style="color:{TX3};font-size:.68rem;">נייטרלי</div>
        <div style="color:{GRN};font-size:.68rem;font-weight:600;">שורי ►</div>
      </div>
    </div>"""

    def eblock(icon, title, body, accent=CYAN):
        return f"""
        <div style="background:{SURF2};border:1px solid {BDR};border-top:3px solid {accent};
                    border-radius:0 0 12px 12px;padding:18px;height:100%;
                    direction:rtl;text-align:right;">
          <div style="font-size:.7rem;font-weight:700;color:{TX2};text-transform:uppercase;
                      letter-spacing:.08em;margin-bottom:10px;">{icon} {title}</div>
          <div style="color:{TX};font-size:.86rem;line-height:1.75;">{body}</div>
        </div>"""

    # RSI
    if not np.isnan(rsi):
        if rsi < 30:
            rb = (f"מדד ה-RSI עומד על <strong>{rsi:.1f}</strong>, מתחת לסף 30 של <strong>מכירת יתר</strong>. "
                  f"המוכרים דחפו את המחיר מטה בחוזקה — לעתים קרובות מעבר למה שמוצדק. "
                  f"ירידה לרמה זו מסמנת הזדמנות כניסה פוטנציאלית, אם כי אין ערובה שהמחיר "
                  f"לא ימשיך לרדת לפני ההתאוששות.")
            ra = GRN
        elif rsi > 70:
            rb = (f"מדד ה-RSI עומד על <strong>{rsi:.1f}</strong>, מעל לסף 70 של <strong>קניית יתר</strong>. "
                  f"הקונים דחפו את המחיר מעלה בעוצמה. מצב זה מקדים לעתים תיקון כלפי מטה, "
                  f"אם כי מניות צמיחה חזקות יכולות להישאר בקניית יתר לתקופות ממושכות.")
            ra = RED
        else:
            mood = "מעט גבוהה" if rsi>50 else "מעט נמוכה"
            rb = (f"מדד ה-RSI עומד על <strong>{rsi:.1f}</strong> — באזור הנייטרלי (30–70), "
                  f"{mood} מהמרכז. אין אות ברור של קניית יתר או מכירת יתר, "
                  f"מה שמרמז על מאזן יחסי בין קונים ומוכרים.")
            ra = TX2
    else:
        rb, ra = "אין מספיק נתונים לחישוב RSI.", TX3
    rsi_h = eblock("📊", "ניתוח RSI", rb, ra)

    # MA
    if not (np.isnan(m50) or np.isnan(m200)):
        ab50 = c>m50; ab200 = c>m200
        cross = "צלב זהב" if m50>m200 else "צלב מוות"
        cc = GRN if m50>m200 else RED
        cdesc = "אות שורי חזק, מגמת עלייה ארוכת טווח" if m50>m200 else "אות דובי, מגמת ירידה בטווח הארוך"
        if ab50 and ab200:
            pos = f"המחיר (${c:.2f}) נסחר <strong>מעל שני הממוצעים</strong> — MA50 (${m50:.0f}) וMA200 (${m200:.0f}). תמונה טכנית חיובית המאשרת מגמה עולה."
        elif not ab50 and not ab200:
            pos = f"המחיר (${c:.2f}) נסחר <strong>מתחת לשני הממוצעים</strong> — MA50 (${m50:.0f}) וMA200 (${m200:.0f}). תמונה שלילית המצביעה על לחץ מכירות."
        elif ab50:
            pos = f"המחיר (${c:.2f}) <strong>מעל MA50</strong> (${m50:.0f}) אך <strong>מתחת ל-MA200</strong> (${m200:.0f}). מגמה קצרה חיובית, ארוכה עדיין שלילית."
        else:
            pos = f"המחיר (${c:.2f}) <strong>מתחת ל-MA50</strong> (${m50:.0f}) אך <strong>מעל MA200</strong> (${m200:.0f}). חולשה קצרת טווח בתוך מגמה ארוכה חיובית."
        mb = f"{pos}<br><br><strong style='color:{cc}'>{cross}:</strong> {cdesc}."
        ma_a = GRN if (ab50 and ab200 and m50>m200) else RED if (not ab50 and not ab200 and m50<m200) else BDR
    else:
        mb, ma_a = "אין מספיק נתונים לחישוב ממוצעים נעים.", TX3
    ma_h = eblock("📈", "ממוצעים נעים", mb, ma_a)

    # Fundamentals
    pe=info.get("trailingPE"); fpe=info.get("forwardPE")
    rg=info.get("revenueGrowth"); eg=info.get("earningsGrowth")
    lines=[]
    if pe:
        desc = "ציפיות צמיחה גבוהות — סיכון אם הצמיחה לא תתממש" if pe>60 \
               else "הערכת שווי סבירה עבור מניית צמיחה" if pe>25 \
               else "מכפיל נמוך — עשוי להצביע על הזדמנות"
        lines.append(f"<strong>מכפיל רווח {pe:.0f}x</strong> — {desc}")
    if fpe and pe and fpe<pe:
        lines.append(f"מכפיל עתידי ({fpe:.0f}x) נמוך מהנוכחי — האנליסטים צופים שיפור ברווחיות")
    if rg:
        gc = GRN if rg>.15 else AMB if rg>0 else RED
        lines.append(f"<strong style='color:{gc}'>צמיחת הכנסות: {rg*100:.1f}%</strong>")
    if eg:
        gc = GRN if eg>.15 else AMB if eg>0 else RED
        lines.append(f"<strong style='color:{gc}'>צמיחת רווח: {eg*100:.1f}%</strong>")
    fb = "<br>".join(f"• {l}" for l in lines) if lines else "נתונים פונדמנטליים אינם זמינים."
    fund_h = eblock("🏦", "נתונים פונדמנטליים", fb)

    # Risk
    risks = {
        "קנה":  ("המלצת קנייה — אזהרת סיכון",
                  f"מניות צמיחה בתחומי AI ומוליכים למחצה הן תנודתיות מאוד. "
                  f"ירידה בשוק, דו\"ח מאכזב או שינוי ריביות יכולים לבטל את האות תוך ימים. "
                  f"מומלץ להגדיר <strong>Stop-Loss</strong> ולפזר את ההשקעה על פני מספר פוזיציות."),
        "מכור": ("המלצת מכירה — אזהרת סיכון",
                  f"מניות עם קניית יתר יכולות להמשיך לעלות, במיוחד עם קטליזטור עסקי חזק. "
                  f"שקול <strong>הקטנת פוזיציה חלקית</strong> במקום מכירה מלאה."),
        "המתן": ("המתנה — אזהרת סיכון",
                  f"מצב נייטרלי אינו אומר שאין סיכון. עקוב אחר נפחי מסחר, חדשות הענף "
                  f"ואינדיקטורים מקרו-כלכליים לפני נקיטת עמדה."),
    }
    rt, rb2 = risks[label]
    risk_h = f"""
    <div style="background:{ADIM};border:1px solid rgba(245,158,11,.3);
                border-right:4px solid {AMB};border-radius:10px;
                padding:16px 20px;direction:rtl;text-align:right;margin-top:4px;">
      <div style="color:{AMB};font-size:.72rem;font-weight:700;
                  text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">⚠️ {rt}</div>
      <div style="color:{TX};font-size:.86rem;line-height:1.7;">{rb2}</div>
    </div>"""

    return bar, rsi_h, ma_h, fund_h, risk_h


def hold_str(days: int) -> str:
    if days <= 0:  return "—"
    if days < 7:   return f"{days} ימים"
    if days < 30:  return f"~{days//7} שבועות"
    if days < 365: return f"~{days//30} חודשים"
    return f"~{days//365} שנים"


def run_bt_v2(df: pd.DataFrame, initial: float, freq: str = "daily") -> dict:
    """Backtest with frequency control + 0.1% transaction costs tracked in parallel."""
    cash_c, sh_c, pos_c   = initial, 0., False   # with costs
    cash_nc, sh_nc, pos_nc = initial, 0., False  # without costs
    port_c, port_nc, bh   = [], [], []
    trades, holding_days  = [], []
    buy_date = None
    prev_period = None
    bh_sh = initial / df["Close"].iloc[0]

    for dt, row in df.iterrows():
        cl, rsi = row["Close"], row["RSI"]
        bh.append(bh_sh * cl)

        check = False
        if freq == "daily":
            check = True
        elif freq == "weekly":
            wk = (dt.year, dt.isocalendar()[1])
            if wk != prev_period:
                prev_period = wk;  check = True
        elif freq == "monthly":
            mo = (dt.year, dt.month)
            if mo != prev_period:
                prev_period = mo;  check = True

        if check and not np.isnan(rsi):
            # ── with-cost portfolio ──
            if rsi < 30 and not pos_c and cash_c > 0:
                cost = cash_c * 0.001
                sh_c = (cash_c - cost) / cl;  cash_c = 0;  pos_c = True
                buy_date = dt
                trades.append({"type":"buy",  "date":dt, "price":cl, "cost":cost})
            elif rsi > 70 and pos_c and sh_c > 0:
                gross = sh_c * cl;  cost = gross * 0.001
                cash_c = gross - cost;  sh_c = 0;  pos_c = False
                if buy_date:
                    holding_days.append((dt - buy_date).days);  buy_date = None
                trades.append({"type":"sell", "date":dt, "price":cl, "cost":cost})
            # ── no-cost mirror ──
            if rsi < 30 and not pos_nc and cash_nc > 0:
                sh_nc = cash_nc / cl;  cash_nc = 0;  pos_nc = True
            elif rsi > 70 and pos_nc and sh_nc > 0:
                cash_nc = sh_nc * cl;  sh_nc = 0;  pos_nc = False

        port_c.append(cash_c  + sh_c  * cl)
        port_nc.append(cash_nc + sh_nc * cl)

    s        = pd.Series(port_c, index=df.index)
    max_dd   = ((s - s.cummax()) / s.cummax()).min() * 100
    n_buys   = sum(1 for t in trades if t["type"]=="buy")
    n_sells  = sum(1 for t in trades if t["type"]=="sell")
    tot_cost = sum(t["cost"] for t in trades)

    return dict(
        port=port_c, port_nc=port_nc, bh=bh,
        buys= [(t["date"], t["price"]) for t in trades if t["type"]=="buy"],
        sells=[(t["date"], t["price"]) for t in trades if t["type"]=="sell"],
        fs=port_c[-1],  fs_nc=port_nc[-1],  fb=bh[-1],
        rs =(port_c[-1]  - initial)/initial*100,
        rs_nc=(port_nc[-1]- initial)/initial*100,
        rb =(bh[-1]      - initial)/initial*100,
        dd=max_dd,
        nb=n_buys, ns=n_sells, n_trades=n_buys+n_sells,
        tot_cost=tot_cost,
        cost_impact=port_nc[-1]-port_c[-1],
        avg_hold=int(np.mean(holding_days)) if holding_days else 0,
    )


def gen_freq_summary(res: dict, sym: str) -> tuple:
    d, w, m = res["daily"], res["weekly"], res["monthly"]
    bh_ret  = d["rb"]

    # Score each frequency
    rets = {k: res[k]["rs"] for k in res}
    dds  = {k: res[k]["dd"] for k in res}   # negative; max = least bad
    ntrs = {k: res[k]["n_trades"] for k in res}

    scores = {k: 0 for k in res}
    best_r = max(rets, key=rets.get);   scores[best_r] += 3
    best_d = max(dds,  key=dds.get);   scores[best_d] += 2   # closest to 0
    best_n = min(ntrs, key=ntrs.get);  scores[best_n] += 1   # fewest trades
    best   = max(scores, key=scores.get)

    fc = {"daily":CYAN, "weekly":GRN, "monthly":AMB}

    lines = [
        (CYAN, f"📊 <strong>מסחר יומי:</strong> הניב <strong>{d['rs']:.1f}%</strong> לאחר עמלות "
               f"(ללא עמלות: {d['rs_nc']:.1f}%). בוצעו {d['n_trades']} עסקאות, "
               f"עמלות כוללות <strong>${d['tot_cost']:.0f}</strong>. "
               f"ממוצע זמן החזקה: {hold_str(d['avg_hold'])}."),
        (GRN,  f"📅 <strong>מסחר שבועי:</strong> הניב <strong>{w['rs']:.1f}%</strong> לאחר עמלות "
               f"(ללא עמלות: {w['rs_nc']:.1f}%). בוצעו {w['n_trades']} עסקאות, "
               f"עמלות כוללות <strong>${w['tot_cost']:.0f}</strong>. "
               f"ממוצע זמן החזקה: {hold_str(w['avg_hold'])}."),
        (AMB,  f"📆 <strong>מסחר חודשי:</strong> הניב <strong>{m['rs']:.1f}%</strong> לאחר עמלות "
               f"(ללא עמלות: {m['rs_nc']:.1f}%). בוצעו {m['n_trades']} עסקאות, "
               f"עמלות כוללות <strong>${m['tot_cost']:.0f}</strong>. "
               f"ממוצע זמן החזקה: {hold_str(m['avg_hold'])}."),
        (TX2,  f"📌 <strong>קנה והחזק:</strong> הניב <strong>{bh_ret:.1f}%</strong> "
               f"ללא עסקאות, ללא עמלות, ללא מעקב."),
    ]

    fn = {"daily":"יומי","weekly":"שבועי","monthly":"חודשי"}
    if best == "daily":
        rec = (f"עבור {sym}, <strong>המסחר היומי</strong> השיג את התשואה הגבוהה ביותר ({d['rs']:.1f}%), "
               f"אך דרש {d['n_trades']} עסקאות ועמלות של ${d['tot_cost']:.0f}. "
               f"גישה זו מתאימה למשקיעים פעילים המוכנים לעקוב אחר הפוזיציה מדי יום.")
    elif best == "weekly":
        rec = (f"עבור {sym}, <strong>המסחר השבועי</strong> הציג את האיזון האופטימלי — "
               f"תשואה של {w['rs']:.1f}% עם {w['n_trades']} עסקאות בלבד. "
               f"גישה זו מתאימה למשקיע שרוצה להיות פעיל מבלי לנטר כל יום.")
    else:
        rec = (f"עבור {sym}, <strong>המסחר החודשי</strong> הוכח כגישה היעילה ביותר — "
               f"תשואה של {m['rs']:.1f}% עם {m['n_trades']} עסקאות ועמלות נמוכות של ${m['tot_cost']:.0f} בלבד. "
               f"גישה זו מתאימה למשקיע פסיבי שרוצה לנצל אות RSI ללא ניהול צמוד.")

    any_beat_bh = any(res[k]["rs"] > bh_ret for k in res)
    if not any_beat_bh:
        rec += (f" <strong>חשוב לציין:</strong> במקרה זה, אסטרטגיית קנה-והחזק ({bh_ret:.1f}%) "
                f"ניצחה את כל האסטרטגיות הפעילות — {sym} עלתה ברציפות מ-2017, "
                f"ולכן כניסות ויציאות הפחיתו את התשואה.")

    return lines, rec, best, fc[best]


# ── UI helpers ─────────────────────────────────────────────────────────────────
def fl(n):
    if n is None: return "—"
    try: n=float(n)
    except: return "—"
    if n>=1e12: return f"${n/1e12:.2f}T"
    if n>=1e9:  return f"${n/1e9:.2f}B"
    if n>=1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def fp(n):
    if n is None: return "—"
    try: return f"{float(n)*100:.1f}%"
    except: return "—"

def mcard(label, val, sub="", vc=None):
    vc = vc or TX
    sh = f'<div style="color:{TX2};font-size:.75rem;margin-top:3px;">{sub}</div>' if sub else ""
    return f"""<div style="background:{SURF};border:1px solid {BDR};border-radius:12px;
                   padding:16px 18px;text-align:right;height:100%;">
      <div style="color:{TX2};font-size:.68rem;font-weight:700;text-transform:uppercase;
                  letter-spacing:.09em;margin-bottom:6px;">{label}</div>
      <div style="color:{vc};font-size:1.35rem;font-weight:700;line-height:1.15;">{val}</div>{sh}
    </div>"""

def shead(text, icon=""):
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;
                     margin:4px 0 18px;direction:rtl;">
      <div style="width:3px;height:22px;background:linear-gradient({CYAN},{PUR});
                  border-radius:2px;flex-shrink:0;"></div>
      <span style="font-size:1rem;font-weight:700;color:{TX};">{(icon+' ') if icon else ''}{text}</span>
    </div>""", unsafe_allow_html=True)

def select_t(t): st.session_state["si"] = t


# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════
inject_css()

st.markdown(f"""<div style="padding:36px 0 10px;text-align:center;">
  <div style="font-size:2rem;font-weight:900;color:{TX};letter-spacing:-.5px;">📈 מנתח מניות</div>
  <div style="color:{TX2};font-size:.88rem;margin-top:6px;">
    ניתוח טכני ופונדמנטלי בזמן אמת · AI · מוליכים למחצה · סייבר · ענן
  </div>
</div>""", unsafe_allow_html=True)

_, sc, _ = st.columns([1,2,1])
with sc:
    st.markdown('<div class="sw">', unsafe_allow_html=True)
    sym_in = st.text_input("s", value="", key="si",
                            placeholder="הקלד סימול מניה ולחץ Enter  (לדוגמה: MRVL, NVDA, CRWD)",
                            label_visibility="hidden")
    st.markdown("</div>", unsafe_allow_html=True)

_, pc, _ = st.columns([1,1,1])
with pc:
    period = st.selectbox("p", ["1mo","3mo","6mo","1y","2y","5y"], index=3,
                           format_func=lambda x:{"1mo":"חודש","3mo":"3 חודשים","6mo":"6 חודשים",
                                                  "1y":"שנה","2y":"שנתיים","5y":"5 שנים"}[x],
                           label_visibility="collapsed")

sym = sym_in.upper().strip()

# ── Landing ────────────────────────────────────────────────────────────────────
if not sym:
    st.markdown(f"""<div style="text-align:center;padding:36px 0 20px;">
      <div style="font-size:2.4rem;margin-bottom:12px;">🔍</div>
      <div style="color:{TX};font-size:1.05rem;font-weight:600;margin-bottom:6px;">חפש מניית צמיחה כדי להתחיל</div>
      <div style="color:{TX2};font-size:.86rem;">ניתוח טכני מלא · המלצה עם הסבר מפורט · בדיקת אחור מ-2017</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="text-align:center;margin-bottom:16px;">
      <span style="background:{SURF};border:1px solid {BDR};border-radius:20px;
                   padding:5px 16px;font-size:.78rem;color:{TX2};">
        ✨ מניות צמיחה מובילות — לחץ כדי לנתח
      </span>
    </div>""", unsafe_allow_html=True)

    for ri in range(0, len(GROWTH), 5):
        row = GROWTH[ri:ri+5]
        cols = st.columns(len(row))
        for col, s in zip(cols, row):
            with col:
                st.markdown(f"""<div style="background:{SURF};border:1px solid {BDR};
                  border-top:3px solid {s['a']};border-radius:0 0 12px 12px;
                  padding:14px 12px 10px;text-align:center;margin-bottom:4px;">
                  <div style="font-size:1.2rem;font-weight:900;color:{TX};letter-spacing:1px;">{s['t']}</div>
                  <div style="font-size:.65rem;font-weight:700;color:{s['a']};margin-top:3px;
                              text-transform:uppercase;letter-spacing:.06em;">{s['c']}</div>
                  <div style="font-size:.72rem;color:{TX2};margin-top:5px;line-height:1.35;
                              direction:rtl;">{s['d']}</div>
                </div>""", unsafe_allow_html=True)
                st.markdown('<div class="gsb">', unsafe_allow_html=True)
                st.button("נתח ←", key=f"l_{s['t']}", on_click=select_t,
                          args=(s['t'],), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ── Fetch ──────────────────────────────────────────────────────────────────────
with st.spinner(f"טוען נתונים עבור {sym}…"):
    df   = fetch_history(sym, period)
    info = fetch_info(sym)

if df.empty:
    st.error(f"לא נמצאו נתונים עבור **{sym}**. בדוק את הסימול ונסה שנית.")
    st.stop()

co  = info.get("longName") or sym
cl  = df["Close"].iloc[-1]
pv  = df["Close"].iloc[-2]
ch  = cl-pv; chp = ch/pv*100
chc = GRN if ch>=0 else RED
arr = "▲" if ch>=0 else "▼"

# ── Stock header ───────────────────────────────────────────────────────────────
st.markdown(f"""<div style="background:linear-gradient(135deg,{SURF} 0%,{SURF2} 100%);
  border:1px solid {BDR};border-radius:14px;padding:22px 26px;margin:16px 0;
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
  <div>
    <div style="font-size:1.5rem;font-weight:800;color:{TX};">{co}</div>
    <div style="color:{TX2};font-size:.83rem;margin-top:3px;">
      {info.get('sector','')}{(' · '+info.get('industry','')) if info.get('industry') else ''}
    </div>
  </div>
  <div style="text-align:left;">
    <div style="font-size:2.4rem;font-weight:900;color:{TX};line-height:1;">${cl:.2f}</div>
    <div style="color:{chc};font-size:.95rem;font-weight:700;text-align:left;margin-top:2px;">
      {arr} {abs(ch):.2f} &nbsp;({abs(chp):.2f}%)
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── 4 metrics ──────────────────────────────────────────────────────────────────
m1,m2,m3,m4 = st.columns(4)
rsi_now = df["RSI"].iloc[-1]
for col, label, val, vc in [
    (m1, "שווי שוק",       fl(info.get("marketCap")),     TX),
    (m2, "שיא 52 שבועות",  f"${df['Close'].max():.2f}",  TX),
    (m3, "שפל 52 שבועות",  f"${df['Close'].min():.2f}",  TX),
    (m4, "מכפיל רווח",     f"{info.get('trailingPE'):.1f}x" if info.get("trailingPE") else "—", TX),
]:
    col.markdown(mcard(label, val, vc=vc), unsafe_allow_html=True)

# ── Quick-switch ───────────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
with st.expander("✨ החלף מניה — מניות צמיחה מוצעות"):
    sw = st.columns(len(GROWTH))
    for col, s in zip(sw, GROWTH):
        with col:
            active = s["t"] == sym
            st.markdown(f"""<div style="text-align:center;font-size:.62rem;
              color:{'#7dcfef' if active else TX2};margin-bottom:2px;">
              {'● ' if active else ''}{s['n']}</div>""", unsafe_allow_html=True)
            st.markdown('<div class="gsb">', unsafe_allow_html=True)
            st.button(s["t"], key=f"sw_{s['t']}", on_click=select_t,
                      args=(s["t"],), use_container_width=True, disabled=active)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
t1, t2, t3 = st.tabs(["📊  ניתוח טכני", "🏦  פונדמנטלי", "🔬  בדיקת אחור"])

# ══════════════════════════════════════════════════════════════════════════════
with t1:
    label, lc, sigs, score = get_rec(df, info)

    # ── Chart: 3 panels (price + volume + RSI) ─────────────────────────────────
    shead("גרף מחיר")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[.60, .14, .26], vertical_spacing=.03)

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="מחיר", increasing_line_color=GRN, decreasing_line_color=RED,
        increasing_fillcolor=GRN, decreasing_fillcolor=RED,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"],  name="MA 50",
                              line=dict(color=CYAN, width=1.6)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], name="MA 200",
                              line=dict(color=AMB, width=1.6)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=pd.concat([df.index.to_series(), df.index.to_series()[::-1]]),
        y=pd.concat([df["BBU"], df["BBL"][::-1]]),
        fill="toself", fillcolor="rgba(167,139,250,.05)",
        line=dict(color="rgba(0,0,0,0)"), name="בולינגר",
    ), row=1, col=1)

    # Volume
    vol_colors = [GRN if df["Close"].iloc[i] >= df["Open"].iloc[i] else RED
                  for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="נפח",
                          marker_color=vol_colors, marker_opacity=.5,
                          showlegend=False), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                              line=dict(color=PUR, width=1.5),
                              fill="tozeroy", fillcolor=PDIM), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color=RED,  line_width=1, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color=GRN,  line_width=1, row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor=PDIM, line_width=0, row=3, col=1)

    fig.update_layout(**{**PB, "height": 620, "xaxis_rangeslider_visible": False,
                          "yaxis2": dict(title="נפח", gridcolor=BDR, tickfont=dict(color=TX2), showgrid=False),
                          "yaxis3": dict(title="RSI", range=[0,100], gridcolor=BDR, tickfont=dict(color=TX2))})
    st.plotly_chart(fig, use_container_width=True)

    # ── Recommendation row ─────────────────────────────────────────────────────
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    shead("המלצה וסיגנלים")

    rc1, rc2 = st.columns([2, 3])
    with rc1:
        bar_h, rsi_h, ma_h, fund_h, risk_h = gen_explain(df, info, label, score)
        st.markdown(bar_h, unsafe_allow_html=True)

    with rc2:
        buls = ""
        for pos, txt in sigs:
            dot = f"<span style='color:{GRN}'>●</span>" if pos is True \
                  else f"<span style='color:{RED}'>●</span>" if pos is False \
                  else f"<span style='color:{TX2}'>●</span>"
            buls += f"""<div style="display:flex;align-items:center;gap:8px;
              padding:8px 12px;border-bottom:1px solid {BDR};direction:rtl;">
              {dot}
              <span style="font-size:.85rem;color:{TX};">{txt}</span>
            </div>"""
        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
          border-radius:12px;overflow:hidden;">{buls}</div>""", unsafe_allow_html=True)

    # ── Detailed explanation ───────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    shead("הסבר מפורט")

    # Summary
    lco = {"קנה":GRN,"מכור":RED,"המתן":AMB}[label]
    why = ("האינדיקטורים הטכניים מצביעים על הזדמנות כניסה פוטנציאלית: RSI נמוך ו/או מחיר מעל הממוצעים הנעים."
           if label=="קנה" else
           "מספר אינדיקטורים מצביעים על עייפות בעלייה ועל לחץ מכירות אפשרי."
           if label=="מכור" else
           "הסיגנלים הטכניים מעורבים — חלקם חיוביים וחלקם שליליים. עדיף להמתין לאישור כיוון ברור.")
    st.markdown(f"""<div style="background:rgba({
        '34,197,94' if label=='קנה' else '239,68,68' if label=='מכור' else '245,158,11'
    },.07);border:1px solid {lco}33;border-radius:12px;
    padding:18px 22px;margin-bottom:16px;direction:rtl;">
      <div style="font-size:.95rem;font-weight:700;color:{lco};margin-bottom:6px;">
        {'📥 מדוע כדאי לשקול קנייה?' if label=='קנה' else '📤 מדוע כדאי לשקול מכירה?' if label=='מכור' else '⏸️ מדוע כדאי להמתין?'}
      </div>
      <div style="color:{TX};font-size:.88rem;line-height:1.7;">{why}</div>
    </div>""", unsafe_allow_html=True)

    e1, e2, e3 = st.columns(3)
    with e1: st.markdown(rsi_h,  unsafe_allow_html=True)
    with e2: st.markdown(ma_h,   unsafe_allow_html=True)
    with e3: st.markdown(fund_h, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(risk_h, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
with t2:
    shead("נתונים פיננסיים")
    fa, fb_, fc = st.columns(3)

    with fa:
        st.markdown(f"<div style='color:{TX2};font-size:.78rem;font-weight:700;margin-bottom:10px;'>הערכת שווי</div>", unsafe_allow_html=True)
        pe=info.get("trailingPE"); fpe=info.get("forwardPE")
        pb_=info.get("priceToBook"); ps=info.get("priceToSalesTrailing12Months")
        for lbl, v in [("מכפיל רווח",f"{pe:.2f}" if pe else "—"),
                        ("מכפיל רווח עתידי",f"{fpe:.2f}" if fpe else "—"),
                        ("מחיר / ספר",f"{pb_:.2f}" if pb_ else "—"),
                        ("מחיר / מכירות",f"{ps:.2f}" if ps else "—")]:
            st.markdown(mcard(lbl,v)+"<div style='height:8px'></div>", unsafe_allow_html=True)

    with fb_:
        st.markdown(f"<div style='color:{TX2};font-size:.78rem;font-weight:700;margin-bottom:10px;'>תוצאות עסקיות</div>", unsafe_allow_html=True)
        rev=info.get("totalRevenue"); ni=info.get("netIncomeToCommon")
        eb=info.get("ebitda"); mg=info.get("profitMargins")
        for lbl, v, vc in [("הכנסות",fl(rev),TX),
                             ("רווח נקי",fl(ni), GRN if ni and ni>0 else RED if ni else TX),
                             ("EBITDA",fl(eb),TX),
                             ("שולי רווח",fp(mg), GRN if mg and mg>0 else TX)]:
            st.markdown(mcard(lbl,v,vc=vc)+"<div style='height:8px'></div>", unsafe_allow_html=True)

    with fc:
        st.markdown(f"<div style='color:{TX2};font-size:.78rem;font-weight:700;margin-bottom:10px;'>צמיחה ודיבידנד</div>", unsafe_allow_html=True)
        dy=info.get("dividendYield"); eps=info.get("trailingEps")
        rg=info.get("revenueGrowth"); eg=info.get("earningsGrowth")
        for lbl, v, vc in [("תשואת דיבידנד",fp(dy) if dy else "—",TX),
                             ("רווח למניה (EPS)",f"${eps:.2f}" if eps else "—",TX),
                             ("צמיחת הכנסות",fp(rg), GRN if rg and rg>0 else RED if rg else TX),
                             ("צמיחת רווח",fp(eg), GRN if eg and eg>0 else RED if eg else TX)]:
            st.markdown(mcard(lbl,v,vc=vc)+"<div style='height:8px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    shead("הכנסות ורווח שנתי")
    try:
        fin = fetch_fin(sym)
        if fin is not None and not fin.empty:
            rr = fin.loc["Total Revenue"] if "Total Revenue" in fin.index else None
            ir = fin.loc["Net Income"]    if "Net Income"    in fin.index else None
            if rr is not None:
                yrs = [str(d.year) for d in rr.index]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=yrs, y=rr.values/1e9, name="הכנסות ($B)",
                                       marker_color=CYAN, marker_opacity=.8))
                if ir is not None:
                    fig2.add_trace(go.Bar(x=yrs, y=ir.values/1e9, name="רווח נקי ($B)",
                                           marker_color=GRN, marker_opacity=.8))
                fig2.update_layout(**{**PB,"height":300,"barmode":"group","yaxis_title":"מיליארד $"})
                st.plotly_chart(fig2, use_container_width=True)
            else: st.info("נתונים שנתיים אינם זמינים.")
        else: st.info("נתונים שנתיים אינם זמינים.")
    except: st.info("לא ניתן לטעון נתונים שנתיים.")


# ══════════════════════════════════════════════════════════════════════════════
with t3:
    # ── Header card ────────────────────────────────────────────────────────────
    st.markdown(f"""<div style="background:{CDIM};border:1px solid rgba(0,180,216,.25);
      border-radius:10px;padding:14px 20px;margin-bottom:20px;direction:rtl;">
      <div style="font-weight:800;color:{TX};font-size:1rem;margin-bottom:6px;">
        🔬 בדיקת אחור — השוואת תדירויות מסחר
      </div>
      <div style="color:{TX2};font-size:.84rem;line-height:1.6;">
        <strong style="color:{CYAN}">אסטרטגיה:</strong> קנה כאשר RSI &lt; 30 · מכור כאשר RSI &gt; 70
        &nbsp;|&nbsp; <strong style="color:{CYAN}">תקופה:</strong> ינואר 2017 – היום
        &nbsp;|&nbsp; <strong style="color:{AMB}">עמלות:</strong> 0.1% לכל עסקה
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Settings ───────────────────────────────────────────────────────────────
    bc, _ = st.columns([1, 2])
    with bc:
        initial = st.number_input("סכום השקעה התחלתי ($)",
                                   min_value=100, max_value=10_000_000,
                                   value=10_000, step=1000)

    with st.spinner("מריץ סימולציה לשלוש תדירויות…"):
        bt_df = fetch_bt(sym)

    if bt_df.empty:
        st.error("לא ניתן לטעון נתוני עבר.")
    else:
        amt = float(initial)
        all_bt = {
            "daily":   run_bt_v2(bt_df, amt, "daily"),
            "weekly":  run_bt_v2(bt_df, amt, "weekly"),
            "monthly": run_bt_v2(bt_df, amt, "monthly"),
        }
        lines_sum, rec_text, best_freq, best_color = gen_freq_summary(all_bt, sym)

        # ── Comparison chart ───────────────────────────────────────────────────
        shead("גרף השוואה — כל התדירויות")
        fig3 = go.Figure()

        # Buy & Hold (background reference)
        fig3.add_trace(go.Scatter(
            x=bt_df.index, y=all_bt["daily"]["bh"], name="קנה והחזק",
            line=dict(color=TX2, width=1.5, dash="dot"),
            fill="tozeroy", fillcolor="rgba(107,155,192,.03)",
        ))
        # 3 strategy lines
        for freq, color, name, dash in [
            ("monthly", AMB,  "מסחר חודשי",  "solid"),
            ("weekly",  GRN,  "מסחר שבועי",  "solid"),
            ("daily",   CYAN, "מסחר יומי",   "solid"),
        ]:
            fig3.add_trace(go.Scatter(
                x=bt_df.index, y=all_bt[freq]["port"], name=name,
                line=dict(color=color, width=2.2 if freq==best_freq else 1.5, dash=dash),
            ))

        # Buy/sell markers for best frequency only
        bf = all_bt[best_freq]
        if bf["buys"]:
            bx, by = zip(*bf["buys"])
            fig3.add_trace(go.Scatter(
                x=list(bx), y=list(by), mode="markers",
                name=f"קנייה ({{'daily':'יומי','weekly':'שבועי','monthly':'חודשי'}}[best_freq])",
                marker=dict(symbol="triangle-up", color=GRN, size=8,
                            line=dict(color=BG, width=1)),
            ))
        if bf["sells"]:
            sx, sy = zip(*bf["sells"])
            fig3.add_trace(go.Scatter(
                x=list(sx), y=list(sy), mode="markers",
                name=f"מכירה",
                marker=dict(symbol="triangle-down", color=RED, size=8,
                            line=dict(color=BG, width=1)),
            ))

        fig3.update_layout(**{**PB, "height": 420, "yaxis_title": "שווי תיק ($)"})
        st.plotly_chart(fig3, use_container_width=True)

        # ── 3 comparison cards ─────────────────────────────────────────────────
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        shead("השוואת תדירויות")

        freq_meta = [
            ("daily",   CYAN, "📊 מסחר יומי",   "בדיקת אות כל יום מסחר"),
            ("weekly",  GRN,  "📅 מסחר שבועי",  "בדיקת אות כל יום שני"),
            ("monthly", AMB,  "📆 מסחר חודשי",  "בדיקת אות ראשון בחודש"),
        ]
        cc1, cc2, cc3 = st.columns(3)
        for col, (freq, color, title, subtitle) in zip([cc1,cc2,cc3], freq_meta):
            bt  = all_bt[freq]
            is_best = (freq == best_freq)
            rc  = GRN if bt["rs"] >= 0 else RED

            best_badge = (f'<div style="background:{color};color:{BG};font-size:.7rem;'
                          f'font-weight:800;text-align:center;padding:5px 0;letter-spacing:.5px;">'
                          f'⭐ ביצועים מיטביים</div>') if is_best else ""

            def row(lbl, val, vc=TX):
                return (f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:center;padding:8px 14px;border-bottom:1px solid {BDR};'
                        f'direction:rtl;">'
                        f'<span style="color:{TX2};font-size:.78rem;">{lbl}</span>'
                        f'<span style="color:{vc};font-size:.84rem;font-weight:700;">{val}</span>'
                        f'</div>')

            rows_html = "".join([
                row("תשואה (עם עמלות)",    f"{bt['rs']:+.1f}%",          GRN if bt['rs']>=0 else RED),
                row("תשואה (ללא עמלות)",   f"{bt['rs_nc']:+.1f}%",       TX2),
                row("השפעת עמלות",          f"-${bt['cost_impact']:.0f}", RED),
                row("עמלות ששולמו",         f"${bt['tot_cost']:.0f}",     TX2),
                row("עסקאות (קנייה/מכירה)", f"{bt['nb']} / {bt['ns']}",  TX),
                row("ממוצע זמן החזקה",      hold_str(bt['avg_hold']),     TX),
                row("מקסימום ירידה",         f"{bt['dd']:.1f}%",           RED),
            ])

            col.markdown(f"""<div style="background:{SURF};
              border:1px solid {'color' if is_best else BDR};
              border:1px solid {color if is_best else BDR};
              border-radius:12px;overflow:hidden;height:100%;">
              {best_badge}
              <div style="padding:14px 16px 10px;border-bottom:1px solid {BDR};
                          text-align:center;direction:rtl;">
                <div style="font-size:1.25rem;font-weight:900;color:{color};">{title}</div>
                <div style="font-size:.72rem;color:{TX2};margin-top:3px;">{subtitle}</div>
              </div>
              {rows_html}
            </div>""", unsafe_allow_html=True)

        # ── Buy & Hold reference card ──────────────────────────────────────────
        bh_ret = all_bt["daily"]["rb"]
        bh_is_best = bh_ret > max(all_bt[k]["rs"] for k in all_bt)
        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
          border-radius:10px;padding:12px 18px;margin-top:10px;
          display:flex;justify-content:space-between;align-items:center;
          flex-wrap:wrap;gap:8px;direction:rtl;">
          <div style="color:{TX2};font-size:.82rem;font-weight:600;">
            📌 קנה והחזק (ייחוס) &nbsp;·&nbsp; 0 עסקאות &nbsp;·&nbsp; $0 עמלות
          </div>
          <div style="color:{GRN if bh_ret>=0 else RED};font-size:1.1rem;font-weight:800;">
            {bh_ret:+.1f}%
            {'&nbsp; <span style="background:{GRN};color:{BG};font-size:.65rem;font-weight:800;border-radius:4px;padding:2px 6px;">ניצח הכל</span>'.format(GRN=GRN,BG=BG) if bh_is_best else ''}
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Hebrew AI Summary ──────────────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        shead("ניתוח וסיכום המערכת")

        lines_html = ""
        for lc, text in lines_sum:
            lines_html += f"""<div style="border-right:3px solid {lc};padding:9px 14px;
              margin-bottom:8px;direction:rtl;text-align:right;background:{BG}22;
              border-radius:0 6px 6px 0;">
              <div style="color:{TX};font-size:.87rem;line-height:1.65;">{text}</div>
            </div>"""

        st.markdown(f"""<div style="background:{SURF2};border:1px solid {BDR};
          border-radius:14px;padding:22px;direction:rtl;text-align:right;">
          <div style="font-size:.95rem;font-weight:700;color:{TX};margin-bottom:16px;">
            🤖 ניתוח ממוצע האסטרטגיות עבור {sym}
          </div>
          {lines_html}
          <div style="background:{CDIM};border:1px solid {best_color}44;
                      border-right:4px solid {best_color};
                      border-radius:10px;padding:16px 18px;margin-top:8px;">
            <div style="color:{best_color};font-weight:700;font-size:.82rem;
                        margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em;">
              💡 המלצת המערכת
            </div>
            <div style="color:{TX};font-size:.88rem;line-height:1.75;">{rec_text}</div>
          </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
st.caption("⚠️ אפליקציה זו מיועדת למטרות מידע בלבד ואינה מהווה ייעוץ פיננסי. כל ההשקעות כרוכות בסיכון.")
