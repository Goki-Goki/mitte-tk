"""
playtomic_scraper.py
======================

This module contains a simple scraper that illustrates how one might collect
open match data from the public Playtomic website.  In the current
environment we cannot make outbound HTTP requests, but the code is written
so that it can be executed on your local machine or in an environment
where internet access is available.

The scraper targets the public club pages on playtomic.com – for example:

    https://playtomic.com/clubs/mitte-the-cabrio

On those pages Playtomic displays a grid of available court times.
Each court lists its available time slots in human‑readable form
(e.g. “2 options • Starting at 14:30 until 18:00”).  The function
``parse_club_page`` will parse this HTML and extract a list of available
slots.  You can then write these to a CSV or push them into another
system (e.g. Google Sheets via n8n).

Usage example::

    from playtomic_scraper import scrape_open_slots, write_to_csv, HAMBURG_CLUBS

    # Only scan the two Mitte Padel clubs in Hamburg.
    slots = scrape_open_slots(HAMBURG_CLUBS, city="Hamburg")
    write_to_csv(slots, "open_matches.csv")

Note: To respect the target website you should add appropriate delays
between requests and avoid overloading their servers.

"""

import csv
import datetime as dt
import re
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class OpenSlot:
    """Represents an available court slot for a club.

    Attributes:
        city: The city where the club is located.
        club_name: Name of the club (e.g. “mitte — The Cabrio”).
        court_name: Name/identifier of the court (e.g. “1 • Center Court”).
        start_time: Start time of the slot (ISO 8601 string).
        end_time: End time of the slot (ISO 8601 string).
        level: Optional player level if available (Playtomic does not
            expose this on the public club page, so leave blank for now).
        free_slots: Optional number of open positions; unknown on the
            public club page, so default to 4 (doubles) or 2 (singles).
    """

    city: str
    club_name: str
    court_name: str
    start_time: str
    end_time: str
    level: Optional[str] = None
    free_slots: Optional[int] = None


def _fetch_html(url: str) -> str:
    """Fetches the HTML content of a given URL.

    Args:
        url: The URL to fetch.

    Returns:
        The HTML content as a string.

    Raises:
        requests.RequestException: If the request fails.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def _parse_timeslot_text(text: str) -> Iterable[tuple[str, str]]:
    """Parses a timeslot descriptor into start/end time pairs.

    Playtomic expresses available slots for a court in a condensed form,
    for example "2 options • Starting at 14:30 until 18:00".  In other
    cases it might appear as "1 option • Starting at 15:00 until 15:00".
    This function finds all occurrences of start/end times in the string.

    Args:
        text: The raw text from the page.

    Yields:
        Tuples of (start_time, end_time) in HH:MM format.
    """
    # Regular expression to capture "Starting at HH:MM until HH:MM"
    pattern = re.compile(r"Starting\s+at\s+(\d{1,2}:\d{2})\s+until\s+(\d{1,2}:\d{2})")
    for match in pattern.finditer(text):
        yield match.group(1), match.group(2)


def parse_club_page(html: str, club_name: str, city: str) -> List[OpenSlot]:
    """Parses the Playtomic club page to extract available slots.

    Args:
        html: Raw HTML content of the club page.
        club_name: Name of the club (used for reporting).
        city: City where the club resides.

    Returns:
        A list of OpenSlot objects.
    """
    soup = BeautifulSoup(html, "html.parser")
    slots: List[OpenSlot] = []

    # Find court names (e.g. "1 • Center Court").  These appear as headings
    # preceding the available options.  We'll find all elements that
    # contain the bullet character "•" followed by the word "Court".
    court_elements = soup.find_all(string=re.compile(r"\u2022.*Court"))
    for element in court_elements:
        court_name = element.strip()
        # The next sibling may contain the availability text (e.g. "2 options…")
        parent = element.find_parent()
        if not parent:
            continue
        # Find text that mentions "option"/"options"
        text_block = parent.find_next(string=re.compile(r"options?•|option•|Starting"))
        if not text_block:
            continue
        for start_time, end_time in _parse_timeslot_text(text_block):
            # Playtomic pages do not include dates in these text blocks, so we
            # assume the date is "today" for demonstration.  In a production
            # scraper you would derive the date from the surrounding context
            # (e.g. by reading the page header for the current day) or iterate
            # through the date selector to collect multiple days.
            today = dt.date.today().isoformat()
            slots.append(
                OpenSlot(
                    city=city,
                    club_name=club_name,
                    court_name=court_name,
                    start_time=f"{today} {start_time}",
                    end_time=f"{today} {end_time}",
                    free_slots=None,
                )
            )

    return slots


def scrape_open_slots(clubs: Dict[str, str], city: str) -> List[OpenSlot]:
    """Scrapes open slots for a set of clubs.

    Args:
        clubs: A mapping of club names to URLs.
        city: The city name to assign to all results.

    Returns:
        A list of OpenSlot objects aggregated across all clubs.
    """
    all_slots: List[OpenSlot] = []
    for club_name, url in clubs.items():
        try:
            html = _fetch_html(url)
        except requests.RequestException as exc:
            print(f"Failed to fetch {club_name}: {exc}")
            continue
        slots = parse_club_page(html, club_name, city)
        all_slots.extend(slots)
    return all_slots


def write_to_csv(slots: Iterable[OpenSlot], filename: str) -> None:
    """Writes open slot records to a CSV file.

    Args:
        slots: An iterable of OpenSlot objects.
        filename: Destination CSV filename.
    """
    fieldnames = list(asdict(OpenSlot(
        city="",
        club_name="",
        court_name="",
        start_time="",
        end_time="",
    )).keys())

    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for slot in slots:
            writer.writerow(asdict(slot))

#
# Convenience definitions for common scraping scenarios.
#

# Public Playtomic URLs for the two Mitte Padel clubs located in Hamburg.
# These are used by default when running this module as a script.
HAMBURG_CLUBS: Dict[str, str] = {
    "mitte — The Cabrio": "https://playtomic.com/clubs/mitte-the-cabrio",
    "mitte — Dolce Vita": "https://playtomic.com/clubs/mitte-dolce-vita",
}


def main() -> None:
    """Scrapes the Hamburg Mitte Padel clubs and writes results to CSV.

    When executed as a script (``python playtomic_scraper.py``), this function
    will scrape only the two Mitte Padel clubs in Hamburg using
    :data:`HAMBURG_CLUBS` and write the results to ``open_matches.csv``.
    """
    print("Scraping Hamburg Mitte Padel clubs...")
    slots = scrape_open_slots(HAMBURG_CLUBS, city="Hamburg")
    write_to_csv(slots, "open_matches.csv")
    print(f"Wrote {len(slots)} slots to open_matches.csv")


if __name__ == "__main__":
    # Provide a simple CLI interface to run the scraper.
    main()


if __name__ == "__main__":
    # Example usage: scrape two Hamburg clubs and write results to CSV.
    hamburg_clubs = {
        "mitte — The Cabrio": "https://playtomic.com/clubs/mitte-the-cabrio",
        "mitte — Dolce Vita": "https://playtomic.com/clubs/mitte-dolce-vita",
    }
    slots = scrape_open_slots(hamburg_clubs, city="Hamburg")
    write_to_csv(slots, "open_matches.csv")
    print(f"Scraped {len(slots)} slots and wrote to open_matches.csv")