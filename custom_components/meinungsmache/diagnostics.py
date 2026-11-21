"""Diagnosedaten (ohne persönliche Angaben; die Feeds sind öffentlich)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import MeinungsmacheConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: MeinungsmacheConfigEntry) -> dict[str, Any]:
    """Stand der Feeds für Fehlermeldungen."""
    koordinator = entry.runtime_data
    return {
        "optionen": dict(entry.options),
        "letzter_abruf_erfolgreich": koordinator.last_update_success,
        "feeds": {
            slug: {
                "artikel": len(stand.artikel),
                "neuester": stand.artikel[0].titel if stand.artikel else None,
                "abgerufen": stand.abgerufen.isoformat() if stand.abgerufen else None,
                "fehler": stand.fehler,
            }
            for slug, stand in (koordinator.data or {}).items()
        },
    }
