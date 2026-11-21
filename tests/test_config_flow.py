"""Einrichtung über die Oberfläche."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meinungsmache.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import fixture


async def test_einrichten(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    for slug in ("all", "wirtschaft"):
        aioclient_mock.get(f"https://meinungsmache.de/rss/{slug}", text=fixture("all.xml"))
    ergebnis = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert ergebnis["type"] is FlowResultType.FORM

    ergebnis = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {"feeds": [], "intervall": 15, "anzahl": 10}
    )
    assert ergebnis["errors"] == {"feeds": "kein_feed"}

    ergebnis = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {"feeds": ["wirtschaft", "all"], "intervall": 30.0, "anzahl": 5.0}
    )
    assert ergebnis["type"] is FlowResultType.CREATE_ENTRY
    assert ergebnis["options"] == {"feeds": ["all", "wirtschaft"], "intervall": 30, "anzahl": 5}
    await hass.async_block_till_done()


async def test_nicht_erreichbar(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get("https://meinungsmache.de/rss/all", status=502)
    ergebnis = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    ergebnis = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {"feeds": ["all"], "intervall": 15, "anzahl": 10}
    )
    assert ergebnis["errors"] == {"base": "nicht_erreichbar"}


async def test_nur_einmal(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, options={"feeds": ["all"]}).add_to_hass(hass)
    ergebnis = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert ergebnis["type"] is FlowResultType.ABORT
    assert ergebnis["reason"] == "single_instance_allowed"


async def test_optionen(hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    for slug in ("all", "donald-trump", "usa"):
        aioclient_mock.get(f"https://meinungsmache.de/rss/{slug}", text=fixture("all.xml"))
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    ergebnis = await hass.config_entries.options.async_init(eintrag.entry_id)
    assert ergebnis["type"] is FlowResultType.FORM
    ergebnis = await hass.config_entries.options.async_configure(
        ergebnis["flow_id"], {"feeds": ["usa", "all"], "intervall": 20, "anzahl": 8}
    )
    assert ergebnis["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert eintrag.options == {"feeds": ["all", "usa"], "intervall": 20, "anzahl": 8}
    assert hass.states.get("sensor.meinungsmache_usa_neuester_artikel") is not None
