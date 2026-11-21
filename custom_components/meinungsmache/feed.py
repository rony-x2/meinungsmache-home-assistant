"""RSS-Feeds von meinungsmache.de lesen (ohne Home-Assistant-Abhängigkeiten, damit leicht testbar)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import html
import re
from xml.etree import ElementTree as ET

TEASER_LAENGE = 280
_TAG = re.compile(r"<[^>]+>")
_LEER = re.compile(r"\s+")
_EXKLUSIV = re.compile(r"^\s*exklusiv\b", re.IGNORECASE)
_BILD = re.compile(r"^https://meinungsmache\.de/gateway/articles/([a-z0-9][a-z0-9-]{0,200})/image$")
BILD_PFAD = "/api/meinungsmache/bild/{kennung}"


def bild_kennung(url: str | None) -> str | None:
    """Kennung eines Artikelbilds von meinungsmache.de, sonst None."""
    treffer = _BILD.match(url or "")
    return treffer.group(1) if treffer else None


class FeedFehler(Exception):
    """Der Feed ließ sich nicht lesen."""


@dataclass(frozen=True, slots=True)
class Artikel:
    """Ein Eintrag aus einem Feed."""

    guid: str
    titel: str
    link: str
    veroeffentlicht: datetime | None
    teaser: str
    bild: str | None
    autor: str | None
    exklusiv: bool

    @property
    def eigen(self) -> bool:
        """Eigene Artikel der Redaktion tragen im Feed eine Autorin oder einen Autor."""
        return self.autor is not None

    @property
    def bild_pfad(self) -> str | None:
        """Bild über Home Assistant ausgeliefert (siehe bild.py), sonst die Adresse aus dem Feed."""
        kennung = bild_kennung(self.bild)
        return BILD_PFAD.format(kennung=kennung) if kennung else self.bild

    def als_dict(self) -> dict:
        """Form für Attribute und Ereignisse (Zeit als ISO-Text, Bild als Pfad in Home Assistant)."""
        daten = asdict(self)
        daten["veroeffentlicht"] = self.veroeffentlicht.isoformat() if self.veroeffentlicht else None
        daten["eigen"] = self.eigen
        daten["bild"] = self.bild_pfad
        daten["bild_original"] = self.bild
        return daten


def _text(element: ET.Element, name: str) -> str:
    return (element.findtext(name) or "").strip()


def klartext(roh: str, laenge: int = TEASER_LAENGE) -> str:
    """HTML der Beschreibung in kurzen Klartext wandeln, an einer Wortgrenze gekürzt."""
    text = _LEER.sub(" ", html.unescape(_TAG.sub(" ", html.unescape(roh)))).strip()
    if len(text) <= laenge:
        return text
    gekuerzt = text[: laenge + 1].rsplit(" ", 1)[0].rstrip(" ,;:.–-")
    return gekuerzt + " …"


def _zeit(roh: str) -> datetime | None:
    if not roh:
        return None
    try:
        zeit = parsedate_to_datetime(roh)
    except (TypeError, ValueError):
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=UTC)


def lies_feed(xml_text: str | bytes) -> list[Artikel]:
    """Einträge eines RSS-2.0-Feeds, neueste zuerst."""
    try:
        wurzel = ET.fromstring(xml_text)
    except ET.ParseError as err:
        raise FeedFehler(f"Feed ist kein gültiges XML: {err}") from err
    kanal = wurzel.find("channel")
    if wurzel.tag != "rss" or kanal is None:
        raise FeedFehler("Feed ist kein RSS 2.0")

    artikel: list[Artikel] = []
    gesehen: set[str] = set()
    for eintrag in kanal.findall("item"):
        link = _text(eintrag, "link")
        guid = _text(eintrag, "guid") or link
        titel = _LEER.sub(" ", _text(eintrag, "title"))
        if not guid or not titel or guid in gesehen:
            continue
        gesehen.add(guid)
        anhang = eintrag.find("enclosure")
        bild = anhang.get("url") if anhang is not None and (anhang.get("type") or "").startswith("image/") else None
        autor = _text(eintrag, "author") or None
        exklusiv = bool(_EXKLUSIV.match(titel)) or "/article/exklusiv-" in link
        artikel.append(
            Artikel(
                guid=guid,
                titel=titel,
                link=link,
                veroeffentlicht=_zeit(_text(eintrag, "pubDate")),
                teaser=klartext(eintrag.findtext("description") or ""),
                bild=bild,
                autor=autor,
                exklusiv=exklusiv,
            )
        )
    alt = datetime.min.replace(tzinfo=UTC)
    artikel.sort(key=lambda a: a.veroeffentlicht or alt, reverse=True)
    return artikel
