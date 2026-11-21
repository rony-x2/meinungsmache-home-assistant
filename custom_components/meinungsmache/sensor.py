"""Sensoren je Feed: neuester Artikel (mit Liste für die Karte) und Zeitpunkt des neuesten Artikels."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_ANZAHL, FEEDS, STANDARD_ANZAHL
from .coordinator import MeinungsmacheConfigEntry, MeinungsmacheKoordinator
from .entity import MeinungsmacheEntitaet

PARALLEL_UPDATES = 0
MAX_ZUSTAND = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeinungsmacheConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Sensoren für alle gewählten Feeds anlegen."""
    koordinator = entry.runtime_data
    anzahl = int({**entry.data, **entry.options}.get(CONF_ANZAHL, STANDARD_ANZAHL))
    entitaeten: list[SensorEntity] = []
    for slug in koordinator.feeds:
        entitaeten.append(NeuesterArtikel(koordinator, slug, anzahl))
        entitaeten.append(ZuletztErschienen(koordinator, slug))
    async_add_entities(entitaeten)


class NeuesterArtikel(MeinungsmacheEntitaet, SensorEntity):
    """Titel des neuesten Artikels; die letzten Einträge stehen im Attribut ``eintraege``."""

    _attr_translation_key = "neuester_artikel"
    # Die Liste und der Anrisstext ändern sich mit jedem Artikel und würden die Datenbank nur füllen
    _unrecorded_attributes = frozenset({"eintraege", "teaser"})

    def __init__(self, koordinator: MeinungsmacheKoordinator, slug: str, anzahl: int) -> None:
        super().__init__(koordinator, slug, "neuester_artikel", "sensor")
        self._anzahl = anzahl

    @property
    def native_value(self) -> str | None:
        stand = self.stand
        if not stand or not stand.artikel:
            return None
        titel = stand.artikel[0].titel
        return titel if len(titel) <= MAX_ZUSTAND else titel[: MAX_ZUSTAND - 1] + "…"

    @property
    def entity_picture(self) -> str | None:
        stand = self.stand
        return stand.artikel[0].bild_pfad if stand and stand.artikel else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stand = self.stand
        attribute: dict[str, Any] = {"feed": self.slug, "feed_name": FEEDS[self.slug]}
        if not stand or not stand.artikel:
            return attribute
        neuester = stand.artikel[0].als_dict()
        neuester.pop("titel")
        neuester.pop("guid")
        attribute.update(neuester)
        attribute["eintraege"] = [
            {k: v for k, v in a.als_dict().items() if k != "guid"} for a in stand.artikel[: self._anzahl]
        ]
        if stand.fehler:
            attribute["letzter_fehler"] = stand.fehler
        return attribute


class ZuletztErschienen(MeinungsmacheEntitaet, SensorEntity):
    """Erscheinungszeitpunkt des neuesten Artikels."""

    _attr_translation_key = "zuletzt_erschienen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, koordinator: MeinungsmacheKoordinator, slug: str) -> None:
        super().__init__(koordinator, slug, "zuletzt_erschienen", "sensor")

    @property
    def native_value(self) -> datetime | None:
        stand = self.stand
        return stand.artikel[0].veroeffentlicht if stand and stand.artikel else None
