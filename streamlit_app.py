import os
import urllib.parse
from datetime import datetime, timedelta, time

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Mitte Padel – Open Matches", layout="wide")

# -------------------------------------------------------------------
# Konfiguration
# -------------------------------------------------------------------
# Öffentliche CSV-URL deines Google Sheets (Tab mit OpenMatches)
OPENMATCHES_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRjtjgQ1kAlaeche7r78gtPzUkN3KZofTIkD47FWFaqIVHAR51Ehv72bgTguiHYu6PUe5sCsHrEF3XN/pub?output=csv"
)

# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_matches() -> pd.DataFrame:
    """Lädt die Matchdaten aus dem veröffentlichten Google-Sheet (CSV)."""
    try:
        df = pd.read_csv(OPENMATCHES_CSV_URL)
    except Exception as e:
        st.error(f"Fehler beim Laden der Match-Daten: {e}")
        return pd.DataFrame(columns=[
            "city", "club_name", "court_name",
            "start_time", "end_time", "level", "free_slots", "match_url"
        ])

    # Spalten-Normalisierung (robust gegenüber leicht abweichenden Headern)
    colmap = {c.lower().strip(): c for c in df.columns}
    def has(col): return col in colmap

    # Erwartete Kernspalten
    expected = ["city", "club_name", "court_name", "start_time", "end_time", "level", "free_slots"]
    for c in expected:
        if not has(c):
            df[c] = None
        else:
            # Auf Standardnamen mappen (lowercase-Key -> echter Spaltenname)
            df.rename(columns={colmap[c]: c}, inplace=True)

    # optionale URL-Spalten
    if has("match_url") and colmap["match_url"] != "match_url":
        df.rename(columns={colmap["match_url"]: "match_url"}, inplace=True)
    elif "match_url" not in df.columns:
        df["match_url"] = None

    if has("booking_url") and colmap["booking_url"] != "booking_url":
        df.rename(columns={colmap["booking_url"]: "booking_url"}, inplace=True)
    elif "booking_url" not in df.columns:
        df["booking_url"] = None

    # Datumsfelder parsen
    for col in ("start_time", "end_time"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Level als String vereinheitlichen (keine NaNs)
    df["level"] = df["level"].fillna("").astype(str)

    # Freie Plätze als Zahl / robust gegen leere Werte
    try:
        df["free_slots"] = pd.to_numeric(df["free_slots"], errors="coerce").fillna(0).astype(int)
    except Exception:
        df["free_slots"] = 0

    # city/club/court Strings
    for c in ("city", "club_name", "court_name"):
        df[c] = df[c].fillna("").astype(str)

    return df


def build_signup_url(row: pd.Series) -> str:
    """
    Priorität:
    1) match_url
    2) booking_url
    3) Fallback: Playtomic-Suche mit Club + Stadt
    """
    for key in ("match_url", "booking_url"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Fallback: Suche
    query = f"{row.get('club_name','')} {row.get('city','Hamburg')}".strip()
    q = urllib.parse.quote_plus(query)
    # Allgemeine Suchseite (Playtomic kann den genauen Pfad variieren)
    return f"https://playtomic.com/search?query={q}"


def human_time(t: datetime) -> str:
    return t.strftime("%H:%M") if isinstance(t, (datetime,)) else ""


# -------------------------------------------------------------------
# UI – Header
# -------------------------------------------------------------------
st.title("🎾 Mitte Padel – Offene Matches in Hamburg")
st.write("Finde offene Matches in den Mitte-Clubs in Hamburg und melde dich direkt bei Playtomic an.")

matches = load_matches()
if matches.empty or matches["start_time"].isna().all():
    st.warning("Keine verwertbaren Matches gefunden (leere Daten oder ungültige Zeitstempel).")
    st.stop()

# -------------------------------------------------------------------
# Sidebar: Filter
# -------------------------------------------------------------------
st.sidebar.header("🔍 Filteroptionen")

today = datetime.now().date()
selected_date = st.sidebar.date_input("Datum", value=today, min_value=today)

# Zeit-Slider (08:00–22:00) mit 30-Minuten-Schritten
time_range = st.sidebar.slider(
    "Spielzeit auswählen (von/bis)",
    value=(time(hour=16, minute=0), time(hour=22, minute=0)),
    min_value=time(hour=8, minute=0),
    max_value=time(hour=22, minute=0),
    step=timedelta(minutes=30)
)

# dynamische Filterwerte
clubs = sorted([c for c in matches["club_name"].dropna().unique().tolist() if c])
levels = sorted([l for l in matches["level"].dropna().unique().tolist() if l])

# Default: alle vorselektiert
selected_club = st.sidebar.multiselect("Club auswählen", clubs, default=clubs)
selected_level = st.sidebar.multiselect("Spielniveau auswählen", levels, default=levels)

# -------------------------------------------------------------------
# Filter anwenden
# -------------------------------------------------------------------
# Sicherheitskopie (kein SettingWithCopy)
df = matches.copy()

# Datum/Zeit filtern
df = df[
    (df["start_time"].dt.date == selected_date) &
    (df["start_time"].dt.time >= time_range[0]) &
    (df["end_time"].dt.time <= time_range[1])
]

# Club / Level filtern (nur wenn Liste nicht leer)
if selected_club:
    df = df[df["club_name"].isin(selected_club)]
if selected_level:
    df = df[df["level"].isin(selected_level)]

df = df.sort_values(by=["start_time", "club_name", "court_name"])

# -------------------------------------------------------------------
# Ergebnisse
# -------------------------------------------------------------------
if df.empty:
    st.info("Keine offenen Matches für diese Auswahl.")
else:
    st.subheader(f"Gefundene Matches am {selected_date}  ·  {len(df)} Einträge")

    # Optional: kompakte Tabellenansicht zum Überblick
    with st.expander("📋 Tabellarische Ansicht einblenden", expanded=False):
        tdf = df.copy()
        # Anzeigeformat für Zeiten
        tdf["start"] = tdf["start_time"].dt.strftime("%H:%M")
        tdf["end"] = tdf["end_time"].dt.strftime("%H:%M")
        tdf = tdf[["city", "club_name", "court_name", "start", "end", "level", "free_slots"]]
        st.dataframe(tdf, use_container_width=True)

    # Kartenartige Darstellung
    for idx, row in df.iterrows():
        with st.container():
            st.markdown(
                f"### {row['club_name']} – {row['court_name']}\n"
                f"⏰ {human_time(row['start_time'])} – {human_time(row['end_time'])}  \n"
                f"🏷️ Level: {row['level'] or '—'}  \n"
                f"👥 Freie Plätze: {int(row['free_slots']) if pd.notna(row['free_slots']) else 0}"
            )
            signup_url = build_signup_url(row)

            # Bevorzugt: Link-Button (falls deine Streamlit-Version das Feature hat)
            try:
                st.link_button("Jetzt anmelden", signup_url, use_container_width=False)
            except Exception:
                # Fallback als normaler Link
                st.markdown(f"[Jetzt anmelden]({signup_url})", unsafe_allow_html=True)

            st.divider()

st.caption("⚡ Datenquelle: Google Sheet (OpenMatches Demo) · „Jetzt anmelden“ leitet zu Playtomic (Match/Club/Suche).")
