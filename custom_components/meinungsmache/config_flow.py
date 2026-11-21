"""Einrichtung über die Oberfläche: Feeds wählen, Abrufabstand und Anzahl der Einträge."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ANZAHL,
    CONF_FEEDS,
    CONF_INTERVALL,
    DOMAIN,
    FEED_URL,
    FEEDS,
    MAX_ANZAHL,
    MAX_INTERVALL,
    MIN_INTERVALL,
    NAME,
    STANDARD_ANZAHL,
    STANDARD_FEEDS,
    STANDARD_INTERVALL,
)
from .feed import FeedFehler, lies_feed


def _schema(werte: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_FEEDS, default=werte.get(CONF_FEEDS, STANDARD_FEEDS)): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=slug, label=name) for slug, name in FEEDS.items()],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_INTERVALL, default=werte.get(CONF_INTERVALL, STANDARD_INTERVALL)): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_INTERVALL,
                    max=MAX_INTERVALL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(CONF_ANZAHL, default=werte.get(CONF_ANZAHL, STANDARD_ANZAHL)): NumberSelector(
                NumberSelectorConfig(min=1, max=MAX_ANZAHL, step=1, mode=NumberSelectorMode.BOX)
            ),
        }
    )


def _bereinigt(eingabe: dict[str, Any]) -> dict[str, Any]:
    feeds = [slug for slug in FEEDS if slug in eingabe[CONF_FEEDS]]  # Reihenfolge wie auf der Seite
    return {CONF_FEEDS: feeds, CONF_INTERVALL: int(eingabe[CONF_INTERVALL]), CONF_ANZAHL: int(eingabe[CONF_ANZAHL])}


class MeinungsmacheConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung von Meinungsmache."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            werte = _bereinigt(user_input)
            if not werte[CONF_FEEDS]:
                fehler[CONF_FEEDS] = "kein_feed"
            else:
                fehler = await self._erreichbar(werte[CONF_FEEDS][0])
            if not fehler:
                return self.async_create_entry(title=NAME, data={}, options=werte)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=fehler,
            description_placeholders={"seite": "https://meinungsmache.de"},
        )

    async def _erreichbar(self, slug: str) -> dict[str, str]:
        """Einmal abrufen, damit Netzprobleme schon bei der Einrichtung auffallen."""
        try:
            async with async_get_clientsession(self.hass).get(
                FEED_URL.format(slug=slug), timeout=aiohttp.ClientTimeout(total=20)
            ) as antwort:
                antwort.raise_for_status()
                roh = await antwort.read()
            await self.hass.async_add_executor_job(lies_feed, roh)
        except (aiohttp.ClientError, TimeoutError):
            return {"base": "nicht_erreichbar"}
        except FeedFehler:
            return {"base": "ungueltiger_feed"}
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeinungsmacheOptionsFlow:
        return MeinungsmacheOptionsFlow()


class MeinungsmacheOptionsFlow(OptionsFlowWithReload):
    """Feeds und Einstellungen nachträglich ändern."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            werte = _bereinigt(user_input)
            if not werte[CONF_FEEDS]:
                fehler[CONF_FEEDS] = "kein_feed"
            else:
                return self.async_create_entry(data=werte)
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or {**self.config_entry.data, **self.config_entry.options}),
            errors=fehler,
        )
