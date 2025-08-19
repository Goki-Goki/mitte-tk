"""
streamlit_app.py
================

This Streamlit application presents available Padel match slots scraped from
Playtomic and allows users to register their interest for a particular slot.

The app reads data from a CSV file (``open_matches.csv``) which is expected to
contain records in the format defined by :class:`playtomic_scraper.OpenSlot`.
The user can filter the table by city and (optionally) level.  After selecting
a desired slot, the user can enter their email address and click **Join
Waitlist**; this will append their details to a second CSV file
(``waitlist.csv``).  In a production deployment you would instead push this
data into a database or CRM, but for the purpose of a quick prototype we use
simple files.

To run the app locally::

    streamlit run streamlit_app.py

To deploy on Streamlit Cloud, push this file along with ``open_matches.csv``
and ``waitlist.csv`` (which can be empty) to your Git repository and link
the repository in the Streamlit Cloud dashboard.
"""

import pandas as pd
import streamlit as st


@st.cache_data(ttl=300)
def load_matches():
    # CSV-URL aus Google Sheets „Veröffentlichen im Web“ (Tab OpenMatches)
    SHEET_CSV_URL = st.secrets.get("https://docs.google.com/spreadsheets/d/e/2PACX-1vRjtjgQ1kAlaeche7r78gtPzUkN3KZofTIkD47FWFaqIVHAR51Ehv72bgTguiHYu6PUe5sCsHrEF3XN/pub?output=csv", "")
    if not SHEET_CSV_URL:
        st.error("OPENMATCHES_CSV_URL fehlt in st.secrets")
        return pd.DataFrame(columns=[
            "city","club_name","court_name","start_time","end_time","level","free_slots"
        ])
    df = pd.read_csv(SHEET_CSV_URL)
    # Datumsfelder parsen
    for col in ("start_time","end_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def append_waitlist_entry(match_row: pd.Series, email: str) -> None:
    """Appends a waitlist entry to the CSV file.

    Args:
        match_row: A pandas Series representing the selected row.
        email: The user's email address.
    """
    entry = match_row.to_dict()
    entry["email"] = email
    # Append to the waitlist file.  Create the file with header if it
    # doesn't exist yet.
    try:
        waitlist_df = pd.read_csv(WAITLIST_FILE)
    except FileNotFoundError:
        waitlist_df = pd.DataFrame(columns=list(entry.keys()))
    waitlist_df = pd.concat([waitlist_df, pd.DataFrame([entry])], ignore_index=True)
    waitlist_df.to_csv(WAITLIST_FILE, index=False)


def main():
    st.set_page_config(page_title="Padel Matches", layout="centered")
    st.title("🎾 Open Padel Matches")

    df = load_matches()
    if df.empty:
        return

    # Convert time strings to datetime for filtering
    # If the CSV uses ISO 8601 strings (YYYY-MM-DD HH:MM), pandas can parse them directly.
    for col in ["start_time", "end_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    # Create helper columns for filtering
    df["start_datetime"] = df["start_time"]
    df["end_datetime"] = df["end_time"]

    # Sidebar filters
    st.sidebar.header("Filter")
    # City filter
    city_options = df["city"].dropna().unique().tolist()
    selected_city = st.sidebar.selectbox("City", options=city_options)
    # Level filter
    level_options = ["All"]
    if "level" in df.columns:
        unique_levels = df["level"].dropna().unique().tolist()
        if unique_levels:
            level_options += unique_levels
    selected_level = st.sidebar.selectbox("Level", options=level_options)
    # Date filter: desired date
    import datetime as dt
    selected_date = st.sidebar.date_input("Desired date", value=dt.date.today())
    # Time range filter
    start_time_input = st.sidebar.time_input("Start after", value=dt.time(0, 0))
    end_time_input = st.sidebar.time_input("End before", value=dt.time(23, 59))
    # Construct datetime range for comparison
    start_dt = dt.datetime.combine(selected_date, start_time_input)
    end_dt = dt.datetime.combine(selected_date, end_time_input)

    # Apply filters
    filtered_df = df[df["city"] == selected_city].copy()
    if selected_level != "All" and "level" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["level"] == selected_level]
    # Filter by date/time range
    filtered_df = filtered_df[
        (filtered_df["start_datetime"] >= start_dt) & (filtered_df["end_datetime"] <= end_dt)
    ]

    # Display the filtered table
    st.subheader(f"Available Matches in {selected_city}")
    st.write(
        "Select a match below to join the waitlist.\n"
        "Use the date and time filters in the sidebar to find matches within your preferred time window."
    )

    if filtered_df.empty:
        st.info("No matches available for the selected filters.")
        return

    # Reset index for display purposes
    display_df = filtered_df.reset_index(drop=True)
    st.dataframe(display_df)
    # Row selection via number input
    selected_index = st.number_input(
        "Enter the row number of the match you want to join (starting from 0):",
        min_value=0,
        max_value=len(display_df) - 1,
        step=1,
        format="%d",
    )

    with st.form(key="waitlist_form"):
        st.write("**Join Waitlist**")
        email = st.text_input("Your email address")
        submitted = st.form_submit_button("Join Waitlist")
        if submitted:
            # Basic validation
            if "@" not in email:
                st.error("Please enter a valid email address.")
            else:
                match_row = display_df.iloc[int(selected_index)]
                append_waitlist_entry(match_row, email)
                st.success(
                    f"You have been added to the waitlist for {match_row['club_name']} on "
                    f"{match_row['start_time']} - {match_row['end_time']}!"
                )


if __name__ == "__main__":
    main()
