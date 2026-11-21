"""Event-Entitäten: lösen bei jedem neuen Artikel eines Feeds aus (Grundlage für Automationen)."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EREIGNISTYPEN, FEEDS, TYP_ARTIKEL, TYP_EIGEN, TYP_EXKLUSIV
from .coordinator import MeinungsmacheConfigEntry, MeinungsmacheKoordinator
from .entity import MeinungsmacheEntitaet
from .feed import Artikel

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeinungsmacheConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Eine Event-Entität je Feed."""
    koordinator = entry.runtime_data
    async_add_entities(NeuerArtikel(koordinator, slug) for slug in koordinator.feeds)


def ereignistyp(artikel: Artikel) -> str:
    """Exklusiv vor eigenem Artikel vor gewöhnlichem Artikel."""
    if artikel.exklusiv:
        return TYP_EXKLUSIV
    if artikel.eigen:
        return TYP_EIGEN
    return TYP_ARTIKEL


class NeuerArtikel(MeinungsmacheEntitaet, EventEntity):
    """Löst je neuem Artikel einmal aus; Typ und Artikeldaten stehen in den Attributen."""

    _attr_translation_key = "neuer_artikel"
    _attr_event_types = EREIGNISTYPEN

    def __init__(self, koordinator: MeinungsmacheKoordinator, slug: str) -> None:
        super().__init__(koordinator, slug, "neuer_artikel", "event")

    @property
    def available(self) -> bool:
        # Ein Event soll nicht „nicht verfügbar“ werden, nur weil ein Abruf ausfiel
        return self.stand is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        stand = self.stand
        if stand is None or not stand.neu:
            self.async_write_ha_state()
            return
        for artikel in stand.neu:
            daten = {k: v for k, v in artikel.als_dict().items() if k != "guid"}
            self._trigger_event(ereignistyp(artikel), {"feed": self.slug, "feed_name": FEEDS[self.slug], **daten})
            self.async_write_ha_state()
