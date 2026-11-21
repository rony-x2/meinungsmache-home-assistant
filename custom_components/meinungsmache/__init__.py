"""Meinungsmache: Nachrichten von meinungsmache.de in Home Assistant."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import shutil

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .bild import BildAnsicht
from .const import DOMAIN, KARTE_URL
from .coordinator import MeinungsmacheConfigEntry, MeinungsmacheKoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.EVENT]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
HIER = Path(__file__).parent


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dashboard-Karte bereitstellen und Automations-Vorlagen ablegen."""
    await _karte_anmelden(hass)
    await hass.async_add_executor_job(_vorlagen_ablegen, Path(hass.config.path("blueprints", "automation", DOMAIN)))
    return True


async def _karte_anmelden(hass: HomeAssistant) -> None:
    if hass.http is None:  # etwa in Tests ohne Webserver
        return
    hass.http.register_view(BildAnsicht(hass))
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    ordner = KARTE_URL.rsplit("/", 1)[0]
    await hass.http.async_register_static_paths([StaticPathConfig(ordner, str(HIER / "frontend"), True)])
    # Prüfsumme statt Versionsnummer: der Browser hält die Datei lange vor und soll jede Änderung sehen
    inhalt = await hass.async_add_executor_job((HIER / "frontend" / "meinungsmache-card.js").read_bytes)
    add_extra_js_url(hass, f"{KARTE_URL}?v={hashlib.sha256(inhalt).hexdigest()[:10]}")


def _vorlagen_ablegen(ziel: Path) -> None:
    """Mitgelieferte Blueprints kopieren, ohne vorhandene (womöglich angepasste) zu überschreiben."""
    try:
        ziel.mkdir(parents=True, exist_ok=True)
        for quelle in sorted((HIER / "blueprints").glob("*.yaml")):
            datei = ziel / quelle.name
            if not datei.exists():
                shutil.copyfile(quelle, datei)
    except OSError as err:
        _LOGGER.warning("Automations-Vorlagen konnten nicht abgelegt werden: %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: MeinungsmacheConfigEntry) -> bool:
    """Feeds einrichten."""
    koordinator = MeinungsmacheKoordinator(hass, entry)
    await koordinator.async_config_entry_first_refresh()
    entry.runtime_data = koordinator
    _abgewaehlte_feeds_entfernen(hass, entry, koordinator.feeds)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _abgewaehlte_feeds_entfernen(hass: HomeAssistant, entry: MeinungsmacheConfigEntry, feeds: list[str]) -> None:
    geraete = dr.async_get(hass)
    for geraet in dr.async_entries_for_config_entry(geraete, entry.entry_id):
        slugs = {kennung.removeprefix(f"{entry.entry_id}_") for dom, kennung in geraet.identifiers if dom == DOMAIN}
        if slugs and not slugs & set(feeds):
            geraete.async_update_device(geraet.id, remove_config_entry_id=entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MeinungsmacheConfigEntry) -> bool:
    """Einrichtung entladen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MeinungsmacheConfigEntry) -> None:
    """Gemerkte Artikel beim Entfernen mitlöschen."""
    from homeassistant.helpers.storage import Store

    from .coordinator import SPEICHER_VERSION

    await Store(hass, SPEICHER_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
