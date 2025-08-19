import os
import urllib.parse
from datetime import datetime, timedelta, time

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# App-Konfiguration
# ------------------------------------------------------------
st.set_page_config(page_title="mitte — Open Matches", layout="wide")

# Farb-/Typo-Setup im Sinne des Mitte-CD (minimalistisch, schwarz/weiß, dezenter Akzent)
# Hinweis: Das ist ein visuelles Näherungs-Theme, kein offizielles Hex-Manual.
PRIMARY = "#0A0A0A"   # fast schwarz
TEXT    = "#111111"
MUTED   = "#6F6F6F"
BORDER  = "#EAEAEA"
BG      = "#FFFFFF"
CARDBG  = "#FFFFFF"
ACCENT  = "#00D07F"   # dezenter frischer Akzent (Buttons/Highlight)

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      :root {{
        --mp-primary: {PRIMARY};
        --mp-text: {TEXT};
        --mp-muted: {MUTED};
        --mp-border: {BORDER};
        --mp-bg: {BG};
        --mp-card: {CARDBG};
        --mp-accent: {ACCENT};
      }}

      html, body, [class*="css"]  {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                      'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji',
                      'Segoe UI Emoji', 'Segoe UI Symbol';
        color: var(--mp-text);
        background: var(--mp-bg);
      }}

      .block-container {{
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 980px;
        margin: auto;
      }}

      h1, h2, h3 {{
        letter-spacing: -0.02em;
      }}

      /* Karten */
      .mp-card {{
        border: 1px solid var(--mp-border);
        background: var(--mp-card);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 12px;
      }}

      .mp-meta {{
        color: var(--mp-muted);
        font-size: 0.95rem;
        margin-top: 4px;
        line-height: 1.35;
      }}

      /* Buttons als Links (Fallback, wenn st.link_button nicht verfügbar ist) */
      .mp-btn {{
        display: inline-block;
        width: 100%;
        text-align: center;
        background: var(--mp-primary);
        color: white !important;
        text-decoration: none !important;
        border-radius: 12px;
        padding: 12px 16px;
        font-weight: 600;
        transition: all .15s ease;
        border: 1px solid var(--mp-primary);
      }}
      .mp-btn:hover {{
        filter: brightness(1.04);
        transform: translateY(-1px);
      }}

      /* Streamlit Buttons global breiter + runde Ecken */
      .stButton>button, .stDownloadButton>button {{
        width: 100%;
        border-radius: 12px;
        padding: 12px 16px;
        background: var(--mp-primary);
        color: #fff;
        border: 1px solid var(--mp-primary);
        font-weight: 600;
      }}
      .stButton>button:hover {{
        filter: brightness(1.04);
        transform: translateY(-1px);
      }}

      /* Inputs etwas runder */
      .stSelectbox, .stMultiSelect, .stDateInput, .stSlider, .stTimeInput {{
        border-radius: 10px !important;
      }}

      /* Sidebar kompakter */
      section[data-testid="stSidebar"] .block-container {{
        padding-top: 0.5rem;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# Datenquelle
# ------------------------------------------------------------
OPENMATCHES_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRjtjgQ1kAlaeche7r78gtPzUkN3KZofTIkD47FWFaqIVHAR51Ehv72bgTguiHYu6PUe5sCsHrEF3XN/pub?output=csv"
)

@st.cache_data(ttl=300)
def load_matches() -> pd.DataFrame:
    try:
        df = pd.read_csv(OPENMATCHES_CSV_URL)
    except Exception as e:
        st.error(f"Fehler beim Laden der Match-Daten: {e}")
        return pd.DataFrame(columns=[
            "city","club_name","court_name","start_time","end_time","level","free_slots","match_url","booking_url"
        ])

    # Spalten vereinheitlichen (lowercase Map)
    lower = {c.lower().strip(): c for c in df.columns}
    def rename_if_exists(src, dst):
        if src in lower and lower[src] != dst:
            df.rename(columns={lower[src]: dst}, inplace=True)

    # Kernspalten erzwingen
    for col in ["city","club_name","court_name","start_time","end_time","level","free_slots"]:
        rename_if_exists(col, col)
        if col not in df.columns:
            df[col] = None

    # optionale Linkspalten
    rename_if_exists("match_url", "match_url")
    if "match_url" not in df.columns: df["match_url"] = None
    rename_if_exists("booking_url", "booking_url")
    if "booking_url" not in df.columns: df["booking_url"] = None

    # Zeiten parsen
    for col in ("start_time","end_time"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["level"] = df["level"].fillna("").astype(str)
    # free_slots robust nach int
    try:
        df["free_slots"] = pd.to_numeric(df["free_slots"], errors="coerce").fillna(0).astype(int)
    except Exception:
        df["free_slots"] = 0

    for col in ("city","club_name","court_name"):
        df[col] = df[col].fillna("").astype(str)

    return df

def build_signup_url(row: pd.Series) -> str:
    # 1) match_url  2) booking_url  3) Fallback Suche
    for key in ("match_url","booking_url"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    query = f"{row.get('club_name','')} {row.get('city','Hamburg')}".strip()
    q = urllib.parse.quote_plus(query)
    return f"https://playtomic.com/search?query={q}"

def hhmm(dt: pd.Timestamp) -> str:
    if pd.isna(dt): return ""
    return dt.strftime("%H:%M")

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown("## AB JETZT NUR NOCH BEI **MITTE**.")
st.caption("State-of-the-art playing conditions in an aesthetic environment — centrally in Hamburg.")

matches = load_matches()
if matches.empty or matches["start_time"].isna().all():
    st.info("Keine verwertbaren Matches gefunden.")
    st.stop()

# ------------------------------------------------------------
# Sidebar-Filter
# ------------------------------------------------------------
st.sidebar.header("🔍 Filter")

today = datetime.now().date()
selected_date = st.sidebar.date_input("Datum", value=today, min_value=today)

time_range = st.sidebar.slider(
    "Spielzeit (von/bis)",
    value=(time(16, 0), time(22, 0)),
    min_value=time(8, 0),
    max_value=time(22, 0),
    step=timedelta(minutes=30),
)

clubs = sorted([c for c in matches["club_name"].dropna().unique().tolist() if c])
levels = sorted([l for l in matches["level"].dropna().unique().tolist() if l])

selected_club = st.sidebar.multiselect("Club", clubs, default=clubs)
selected_level = st.sidebar.multiselect("Level", levels, default=levels)

# ------------------------------------------------------------
# Filter anwenden
# ------------------------------------------------------------
df = matches.copy()
df = df[
    (df["start_time"].dt.date == selected_date) &
    (df["start_time"].dt.time >= time_range[0]) &
    (df["end_time"].dt.time <= time_range[1])
]
if selected_club:
    df = df[df["club_name"].isin(selected_club)]
if selected_level:
    df = df[df["level"].isin(selected_level)]
df = df.sort_values(by=["start_time","club_name","court_name"])

# ------------------------------------------------------------
# Ergebnisse
# ------------------------------------------------------------
if df.empty:
    st.info("Keine offenen Matches für diese Auswahl.")
else:
    st.markdown(f"### Gefundene Matches am {selected_date} · {len(df)} Einträge")

    # Optionale Tabellenansicht
    with st.expander("📋 Tabellarische Ansicht"):
        tdf = df.copy()
        tdf["start"] = tdf["start_time"].dt.strftime("%H:%M")
        tdf["end"]   = tdf["end_time"].dt.strftime("%H:%M")
        tdf = tdf[["city","club_name","court_name","start","end","level","free_slots"]]
        st.dataframe(tdf, use_container_width=True)

    # Karten
    for idx, row in df.iterrows():
        signup_url = build_signup_url(row)
        with st.container():
            st.markdown(
                f"""
                <div class="mp-card">
                  <div style="display:flex; justify-content:space-between; gap:12px; align-items:center; flex-wrap:wrap;">
                    <div style="flex:1 1 360px;">
                      <div style="font-weight:700; font-size:1.05rem;">{row['club_name']} — {row['court_name']}</div>
                      <div class="mp-meta">
                        ⏰ {hhmm(row['start_time'])} – {hhmm(row['end_time'])}<br/>
                        🏷️ Level: {row['level'] or '—'} · 👥 Freie Plätze: {int(row['free_slots']) if pd.notna(row['free_slots']) else 0}
                      </div>
                    </div>
                    <div style="flex:0 0 240px; min-width:220px;">
                      <a class="mp-btn" href="{signup_url}" target="_blank" rel="noopener noreferrer">Jetzt anmelden</a>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

st.caption("© mitte | Boutique Padel · Datenquelle: Google Sheet (Demo).")
