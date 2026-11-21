"""Abruf der gewählten Feeds und Erkennung neuer Artikel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEEDS,
    CONF_INTERVALL,
    DOMAIN,
    EREIGNIS,
    FEED_URL,
    FEEDS,
    GEMERKT_MAX,
    STANDARD_FEEDS,
    STANDARD_INTERVALL,
)
from .feed import Artikel, FeedFehler, lies_feed

_LOGGER = logging.getLogger(__name__)

# Artikel, die älter sind, gelten nie als neu (etwa wenn ein alter Eintrag wieder im Feed auftaucht)
NEU_HOECHSTENS = timedelta(days=2)
NEU_NACH_START = timedelta(hours=1)
ZEITLIMIT = aiohttp.ClientTimeout(total=30)
SPEICHER_VERSION = 1

type MeinungsmacheConfigEntry = ConfigEntry[MeinungsmacheKoordinator]


@dataclass(slots=True)
class FeedStand:
    """Stand eines Feeds nach dem letzten Abruf."""

    artikel: list[Artikel] = field(default_factory=list)
    neu: list[Artikel] = field(default_factory=list)  # nur im jeweiligen Lauf gefüllt, älteste zuerst
    abgerufen: datetime | None = None
    fehler: str | None = None


class MeinungsmacheKoordinator(DataUpdateCoordinator[dict[str, FeedStand]]):
    """Ruft alle gewählten Feeds gemeinsam ab."""

    config_entry: MeinungsmacheConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MeinungsmacheConfigEntry) -> None:
        optionen = {**entry.data, **entry.options}
        self.feeds: list[str] = [f for f in optionen.get(CONF_FEEDS, STANDARD_FEEDS) if f in FEEDS]
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=optionen.get(CONF_INTERVALL, STANDARD_INTERVALL)),
        )
        self._sitzung = async_get_clientsession(hass)
        self._speicher: Store[dict[str, list[str]]] = Store(hass, SPEICHER_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._gemerkt: dict[str, list[str]] = {}

    async def _async_setup(self) -> None:
        self._gemerkt = await self._speicher.async_load() or {}

    async def _hole(self, slug: str) -> list[Artikel]:
        url = FEED_URL.format(slug=slug)
        try:
            async with self._sitzung.get(url, timeout=ZEITLIMIT, headers={"Accept": "application/rss+xml"}) as antwort:
                antwort.raise_for_status()
                roh = await antwort.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FeedFehler(f"{url}: {err}") from err
        return await self.hass.async_add_executor_job(lies_feed, roh)

    async def _async_update_data(self) -> dict[str, FeedStand]:
        ergebnisse = await asyncio.gather(*(self._hole(slug) for slug in self.feeds), return_exceptions=True)
        alt = self.data or {}
        vorher = {slug: set(guids) for slug, guids in self._gemerkt.items()}
        jetzt = dt_util.utcnow()
        # Nach einem Neustart nur melden, was eben erst erschienen ist, statt alles Verpasste auf einmal
        hoechstens = NEU_HOECHSTENS if self.data is not None else NEU_NACH_START
        stand: dict[str, FeedStand] = {}
        fehler = 0
        geaendert = False

        for slug, ergebnis in zip(self.feeds, ergebnisse, strict=True):
            if isinstance(ergebnis, BaseException):
                if not isinstance(ergebnis, FeedFehler):
                    raise ergebnis
                fehler += 1
                _LOGGER.debug("Feed %s nicht abrufbar: %s", slug, ergebnis)
                letzter = alt.get(slug, FeedStand())
                stand[slug] = FeedStand(artikel=letzter.artikel, abgerufen=letzter.abgerufen, fehler=str(ergebnis))
                continue

            bekannt = self._gemerkt.get(slug)
            neu: list[Artikel] = []
            if bekannt is not None:  # beim allerersten Abruf eines Feeds nichts melden
                bekannte = set(bekannt)
                neu = [
                    a
                    for a in ergebnis
                    if a.guid not in bekannte and (a.veroeffentlicht is None or jetzt - a.veroeffentlicht <= hoechstens)
                ]
                neu.reverse()
            guids = [a.guid for a in ergebnis]
            if bekannt is None or not set(guids) <= set(bekannt):
                aktuell = set(guids)
                zusammen = guids + [g for g in (bekannt or []) if g not in aktuell]
                self._gemerkt[slug] = zusammen[:GEMERKT_MAX]
                geaendert = True
            stand[slug] = FeedStand(artikel=ergebnis, neu=neu, abgerufen=jetzt)

        if self.feeds and fehler == len(self.feeds):
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="abruf_fehlgeschlagen",
            )
        if geaendert:
            self._speicher.async_delay_save(lambda: self._gemerkt, 10)

        self._melden(stand, vorher)
        return stand

    def _melden(self, stand: dict[str, FeedStand], vorher: dict[str, set[str]]) -> None:
        """Ein Ereignis je neuem Artikel, auch wenn er in mehreren Feeds zugleich erscheint.

        ``feeds`` nennt die Feeds, in denen er jetzt neu ist; ``frueher`` die, in denen er schon
        gemeldet war (taucht er etwas später in einem weiteren Feed auf). So lassen sich doppelte
        Benachrichtigungen vermeiden.
        """
        neu: dict[str, tuple[Artikel, list[str]]] = {}
        for slug, feed_stand in stand.items():
            for artikel in feed_stand.neu:
                neu.setdefault(artikel.guid, (artikel, []))[1].append(slug)
        alt = datetime.min.replace(tzinfo=dt_util.UTC)
        for artikel, feeds in sorted(neu.values(), key=lambda e: e[0].veroeffentlicht or alt):
            frueher = [slug for slug in self.feeds if slug not in feeds and artikel.guid in vorher.get(slug, ())]
            self.hass.bus.async_fire(
                EREIGNIS,
                {
                    "feed": feeds[0],
                    "feed_name": FEEDS[feeds[0]],
                    "feeds": feeds,
                    "frueher": frueher,
                    **artikel.als_dict(),
                },
            )
