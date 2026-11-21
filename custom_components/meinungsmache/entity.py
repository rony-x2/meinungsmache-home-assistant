"""Gemeinsame Grundlage der Entitäten: ein Gerät je Feed."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASIS_URL, DOMAIN, FEEDS, NAME
from .coordinator import FeedStand, MeinungsmacheKoordinator


class MeinungsmacheEntitaet(CoordinatorEntity[MeinungsmacheKoordinator]):
    """Entität eines Feeds."""

    _attr_has_entity_name = True
    _attr_attribution = "Daten von meinungsmache.de"

    def __init__(self, koordinator: MeinungsmacheKoordinator, slug: str, schluessel: str, plattform: str) -> None:
        super().__init__(koordinator)
        self.slug = slug
        eintrag = koordinator.config_entry.entry_id
        self._attr_unique_id = f"{eintrag}_{slug}_{schluessel}"
        # Feste Entitäts-IDs, unabhängig von der Sprache der Oberfläche (für Karte und Vorlagen)
        self.entity_id = f"{plattform}.{DOMAIN}_{slug.replace('-', '_')}_{schluessel}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{eintrag}_{slug}")},
            name=f"{NAME} {FEEDS[slug]}",
            manufacturer="meinungsmache.de",
            model="RSS-Feed",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=BASIS_URL,
        )

    @property
    def stand(self) -> FeedStand | None:
        """Stand dieses Feeds."""
        return (self.coordinator.data or {}).get(self.slug)

    @property
    def available(self) -> bool:
        stand = self.stand
        return super().available and stand is not None and bool(stand.artikel or stand.abgerufen)
