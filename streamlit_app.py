import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# -------------------
# App-Konfiguration
# -------------------
st.set_page_config(page_title="Mitte Padel – Open Matches", layout="wide")

# Mobile-Optimierung: Buttons in voller Breite
st.markdown(
    """
    <style>
    .stButton>button {
        width: 100% !important;
        border-radius: 8px;
        padding: 0.75em 1em;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 900px;
        margin: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------
# Datenquelle
# -------------------
OPENMATCHES_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRjtjgQ1kAlaeche7r78gtPzUkN3KZofTIkD47FWFaqIVHAR51Ehv72bgTguiHYu6PUe5sCsHrEF3XN/pub?output=csv"

@st.cache_data(ttl=300)
def load_matches():
    try:
        df = pd.read_csv(OPENMATCHES_CSV_URL)
    except Exception as e:
        st.error(f"Fehler beim Laden der Match-Daten: {e}")
        return pd.DataFrame()

    # Zeitfelder parsen
    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    if "end_time" in df.columns:
        df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")

    return df

# -------------------
# App UI
# -------------------
st.title("🎾 Mitte Padel – Offene Matches")
st.write("Finde offene Matches in den Mitte-Clubs in Hamburg und melde dich direkt an.")

matches = load_matches()
if matches.empty:
    st.warning("Keine Matches gefunden.")
    st.stop()

# -------------------
# Sidebar: Filter
# -------------------
st.sidebar.header("🔍 Filteroptionen")

today = datetime.now().date()
selected_date = st.sidebar.date_input("Datum", value=today, min_value=today)

# Zeit-Slider (08:00 – 22:00)
time_range = st.sidebar.slider(
    "Spielzeit auswählen",
    value=(datetime.strptime("16:00", "%H:%M").time(), datetime.strptime("22:00", "%H:%M").time()),
    min_value=datetime.strptime("08:00", "%H:%M").time(),
    max_value=datetime.strptime("22:00", "%H:%M").time(),
    step=timedelta(minutes=30)
)

# Dynamische Filterwerte
clubs = sorted(matches["club_name"].dropna().unique().tolist())
levels = sorted(matches["level"].dropna().unique().tolist())

selected_club = st.sidebar.multiselect("Club auswählen", clubs, default=clubs)
selected_level = st.sidebar.multiselect("Spielniveau auswählen", levels, default=levels)

# -------------------
# Filter anwenden
# -------------------
df = matches[
    (matches["start_time"].dt.date == selected_date) &
    (matches["start_time"].dt.time >= time_range[0]) &
    (matches["end_time"].dt.time <= time_range[1]) &
    (matches["club_name"].isin(selected_club)) &
    (matches["level"].isin(selected_level))
]

# -------------------
# Ergebnisse anzeigen
# -------------------
if df.empty:
    st.info("Keine offenen Matches für diese Auswahl.")
else:
    st.subheader(f"Gefundene Matches am {selected_date}  ·  {len(df)} Einträge")

    for idx, row in df.iterrows():
        with st.container():
            st.markdown(
                f"""
                ### {row['club_name']} – {row['court_name']}
                ⏰ {row['start_time'].strftime('%H:%M')} – {row['end_time'].strftime('%H:%M')}  
                🏷️ Level: {row['level']}  
                👥 Freie Plätze: {row['free_slots']}
                """,
                unsafe_allow_html=True
            )

            # Direkt zu Playtomic verlinken
            if "match_url" in row and pd.notna(row["match_url"]):
                st.markdown(
                    f"[👉 Jetzt anmelden]({row['match_url']})",
                    unsafe_allow_html=True
                )
            else:
                st.button("👉 Jetzt anmelden", key=f"btn_{idx}")

st.caption("⚡ Datenquelle: Google Sheet (OpenMatches Demo)")
