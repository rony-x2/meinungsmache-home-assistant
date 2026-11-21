"""Artikelbilder über Home Assistant ausliefern.

meinungsmache.de liefert die Bilder teils mit ``Cross-Origin-Resource-Policy: same-origin``; im Dashboard
fehlen sie dann. Home Assistant holt sie deshalb selbst und reicht sie weiter. Nebenbei lädt der Browser
nichts direkt von meinungsmache.de, und die Companion-App erreicht die Bilder auch von unterwegs.
Ausgeliefert werden nur Bilder von Artikeln, die gerade in einem eingerichteten Feed stehen.
"""

from __future__ import annotations

from collections import OrderedDict
from http import HTTPStatus
import logging

import aiohttp
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .feed import bild_kennung

_LOGGER = logging.getLogger(__name__)

QUELLE = "https://meinungsmache.de/gateway/articles/{kennung}/image"
MAX_BILDER = 80
MAX_GROESSE = 3 * 1024 * 1024
ERLAUBT = ("image/avif", "image/webp", "image/jpeg", "image/png", "image/gif")


def bekannte_bilder(hass: HomeAssistant) -> set[str]:
    """Kennungen aller Bilder in den aktuellen Feeds."""
    kennungen: set[str] = set()
    for eintrag in hass.config_entries.async_loaded_entries(DOMAIN):
        for stand in (eintrag.runtime_data.data or {}).values():
            kennungen.update(k for a in stand.artikel if (k := bild_kennung(a.bild)))
    return kennungen


class BildAnsicht(HomeAssistantView):
    """GET /api/meinungsmache/bild/<kennung>."""

    url = "/api/meinungsmache/bild/{kennung}"
    name = "api:meinungsmache:bild"
    requires_auth = False  # <img> sendet keine Anmeldung; ausgeliefert wird nur, was ohnehin öffentlich ist

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._speicher: OrderedDict[str, tuple[bytes, str]] = OrderedDict()

    async def get(self, request: web.Request, kennung: str) -> web.Response:
        if kennung not in bekannte_bilder(self._hass):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        if (treffer := self._speicher.get(kennung)) is None:
            treffer = await self._holen(kennung)
            if treffer is None:
                return web.Response(status=HTTPStatus.BAD_GATEWAY)
            self._speicher[kennung] = treffer
            while len(self._speicher) > MAX_BILDER:
                self._speicher.popitem(last=False)
        else:
            self._speicher.move_to_end(kennung)
        inhalt, art = treffer
        return web.Response(
            body=inhalt,
            content_type=art,
            headers={"Cache-Control": "public, max-age=604800, immutable", "X-Content-Type-Options": "nosniff"},
        )

    async def _holen(self, kennung: str) -> tuple[bytes, str] | None:
        try:
            async with async_get_clientsession(self._hass).get(
                QUELLE.format(kennung=kennung), timeout=aiohttp.ClientTimeout(total=20)
            ) as antwort:
                antwort.raise_for_status()
                art = (antwort.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                laenge = antwort.headers.get("Content-Length", "")
                if art not in ERLAUBT or (laenge.isdigit() and int(laenge) > MAX_GROESSE):
                    return None
                inhalt = await antwort.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Bild %s nicht abrufbar: %s", kennung, err)
            return None
        return (inhalt, art) if len(inhalt) <= MAX_GROESSE else None
