import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Mitte Padel – Open Matches", layout="wide")

# -------------------
# Konfiguration
# -------------------
OPENMATCHES_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRjtjgQ1kAlaeche7r78gtPzUkN3KZofTIkD47FWFaqIVHAR51Ehv72bgTguiHYu6PUe5sCsHrEF3XN/pub?output=csv"
WAITLIST_FILE = "waitlist.csv"

# -------------------
# Daten laden
# -------------------
@st.cache_data(ttl=300)
def load_matches():
    try:
        df = pd.read_csv(OPENMATCHES_CSV_URL)
    except Exception as e:
        st.error(f"Fehler beim Laden der Match-Daten: {e}")
        return pd.DataFrame()

    # Datumsfelder parsen
    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    if "end_time" in df.columns:
        df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce")

    return df

# -------------------
# Warteliste speichern
# -------------------
def add_to_waitlist(row, email):
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "city": row.get("city", ""),
        "club_name": row.get("club_name", ""),
        "court_name": row.get("court_name", ""),
        "start_time": row.get("start_time", ""),
        "end_time": row.get("end_time", ""),
        "level": row.get("level", ""),
        "free_slots": row.get("free_slots", ""),
        "email": email
    }
    if os.path.exists(WAITLIST_FILE):
        df = pd.read_csv(WAITLIST_FILE)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    else:
        df = pd.DataFrame([new_entry])
    df.to_csv(WAITLIST_FILE, index=False)

# -------------------
# Streamlit UI
# -------------------
st.title("🎾 Mitte Padel – Offene Matches in Hamburg")
st.write("Finde offene Matches in den Mitte-Clubs und trage dich bei Bedarf in die Warteliste ein.")

matches = load_matches()
if matches.empty:
    st.warning("Keine Matches gefunden.")
    st.stop()

# Filter-Optionen
st.sidebar.header("Filter")
today = datetime.now().date()
selected_date = st.sidebar.date_input("Datum auswählen", value=today, min_value=today)
selected_time = st.sidebar.time_input("Frühester Startzeitpunkt", value=datetime.now().time())

# Filter anwenden
filtered = matches[
    (matches["start_time"].dt.date == selected_date) &
    (matches["start_time"].dt.time >= selected_time)
]

if filtered.empty:
    st.info("Keine offenen Matches für diese Auswahl.")
else:
    st.subheader(f"Gefundene Matches am {selected_date}")
    for idx, row in filtered.iterrows():
        with st.container():
            st.markdown(
                f"**{row['club_name']} – {row['court_name']}**  "
                f"⏰ {row['start_time'].strftime('%H:%M')} – {row['end_time'].strftime('%H:%M')}  "
                f"🏷️ Level: {row['level']}  "
                f"👥 Freie Plätze: {row['free_slots']}"
            )

            with st.expander("Auf Warteliste setzen"):
                email = st.text_input(f"Deine E-Mail für Match {idx}", key=f"email_{idx}")
                if st.button(f"Jetzt eintragen ({row['club_name']} {row['start_time'].strftime('%H:%M')})", key=f"btn_{idx}"):
                    if email:
                        add_to_waitlist(row, email)
                        st.success("Du wurdest erfolgreich auf die Warteliste gesetzt! ✅")
                    else:
                        st.error("Bitte E-Mail eingeben, um dich einzutragen.")

    st.caption("⚡ Datenquelle: Google Sheet (OpenMatches Demo)")
