"""Konstanten der Integration Meinungsmache."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "meinungsmache"
NAME: Final = "Meinungsmache"
BASIS_URL: Final = "https://meinungsmache.de"
FEED_URL: Final = BASIS_URL + "/rss/{slug}"

CONF_FEEDS: Final = "feeds"
CONF_INTERVALL: Final = "intervall"
CONF_ANZAHL: Final = "anzahl"

STANDARD_FEEDS: Final = ["all"]
STANDARD_INTERVALL: Final = 15  # Minuten; der Feed wird serverseitig 5 Minuten zwischengespeichert
MIN_INTERVALL: Final = 5
MAX_INTERVALL: Final = 240
STANDARD_ANZAHL: Final = 10
MAX_ANZAHL: Final = 30

# Ereignis auf dem Bus, je neuem Artikel und Feed einmal
EREIGNIS: Final = "meinungsmache_neuer_artikel"

# Ereignistypen der Event-Entitäten
TYP_ARTIKEL: Final = "artikel"
TYP_EIGEN: Final = "eigener_artikel"
TYP_EXKLUSIV: Final = "exklusiv"
EREIGNISTYPEN: Final = [TYP_ARTIKEL, TYP_EIGEN, TYP_EXKLUSIV]

# Wie viele bereits gesehene Artikel je Feed gemerkt werden
GEMERKT_MAX: Final = 400

KARTE_URL: Final = "/meinungsmache_static/meinungsmache-card.js"

# Alle Feeds von meinungsmache.de: Kennung -> Anzeigename (Reihenfolge wie auf der Seite)
FEEDS: Final[dict[str, str]] = {
    "all": "Alle Artikel",
    "frontpage": "Startseite",
    "politik": "Politik",
    "gesellschaft": "Gesellschaft",
    "meinungen": "Meinungen",
    "good-news": "Good News",
    "international": "International",
    "wirtschaft": "Wirtschaft",
    "umwelt": "Umwelt",
    "sport": "Sport",
    "medien": "Medien",
    "migration": "Migration",
    "afd": "AfD",
    "cdu": "CDU",
    "spd": "SPD",
    "die-linke": "Die Linke",
    "friedrich-merz": "Friedrich Merz",
    "donald-trump": "Donald Trump",
    "europaeische-union": "Europäische Union",
    "frankreich": "Frankreich",
    "grossbritannien": "Großbritannien",
    "china": "China",
    "gaza": "Gaza",
    "iran": "Iran",
    "russland": "Russland",
    "sudan": "Sudan",
    "ukraine": "Ukraine",
    "usa": "USA",
}
