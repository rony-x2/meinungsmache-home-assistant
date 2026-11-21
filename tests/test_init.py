"""Einrichtung, Entitäten, Ereignisse."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meinungsmache.const import EREIGNIS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import JETZT, feeds_bereitstellen


@pytest.mark.freeze_time(JETZT)
async def test_einrichtung_und_neue_artikel(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    ereignisse = async_capture_events(hass, EREIGNIS)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert eintrag.state is ConfigEntryState.LOADED

    sensor = hass.states.get("sensor.meinungsmache_all_neuester_artikel")
    assert sensor.state == "Testartikel eins"
    assert len(sensor.attributes["eintraege"]) == 3
    assert sensor.attributes["link"].endswith("/testartikel-eins")
    assert sensor.attributes["entity_picture"] == "/api/meinungsmache/bild/testartikel-eins"
    assert sensor.attributes["bild_original"].endswith("/testartikel-eins/image")
    assert hass.states.get("sensor.meinungsmache_donald_trump_zuletzt_erschienen").state == "2026-11-21T11:54:23+00:00"
    event = hass.states.get("event.meinungsmache_all_neuer_artikel")
    assert event.state == "unknown"
    assert ereignisse == []  # erster Abruf: nur merken

    # Ein exklusiver Artikel erscheint in beiden Feeds
    feeds_bereitstellen(aioclient_mock, all="all_neu.xml", donald_trump="donald-trump_neu.xml")
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(ereignisse) == 1
    daten = ereignisse[0].data
    assert daten["titel"] == "EXKLUSIV: Ein Interview"
    assert daten["feeds"] == ["all", "donald-trump"] and daten["frueher"] == []
    assert daten["exklusiv"] is True and daten["autor"] == "Mara"
    assert hass.states.get("sensor.meinungsmache_all_neuester_artikel").state == "EXKLUSIV: Ein Interview"
    for slug in ("all", "donald_trump"):
        event = hass.states.get(f"event.meinungsmache_{slug}_neuer_artikel")
        assert event.attributes["event_type"] == "exklusiv"
        assert event.attributes["titel"] == "EXKLUSIV: Ein Interview"

    # Nichts Neues: keine weiteren Ereignisse
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(ereignisse) == 1


@pytest.mark.freeze_time(JETZT)
async def test_spaeter_in_weiterem_feed(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    ereignisse = async_capture_events(hass, EREIGNIS)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()

    feeds_bereitstellen(aioclient_mock, all="all_neu.xml", donald_trump="donald-trump.xml")
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    feeds_bereitstellen(aioclient_mock, all="all_neu.xml", donald_trump="donald-trump_neu.xml")
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert [(e.data["feeds"], e.data["frueher"]) for e in ereignisse] == [(["all"], []), (["donald-trump"], ["all"])]


@pytest.mark.freeze_time(JETZT)
async def test_ein_feed_faellt_aus(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.clear_requests()
    aioclient_mock.get("https://meinungsmache.de/rss/all", status=503)
    aioclient_mock.get("https://meinungsmache.de/rss/donald-trump", status=503)
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("sensor.meinungsmache_all_neuester_artikel").state == "unavailable"
    assert hass.states.get("event.meinungsmache_all_neuer_artikel").state == "unknown"


async def test_erster_abruf_scheitert(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get("https://meinungsmache.de/rss/all", status=500)
    aioclient_mock.get("https://meinungsmache.de/rss/donald-trump", status=500)
    await hass.config_entries.async_setup(eintrag.entry_id)
    assert eintrag.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time(JETZT)
async def test_abgewaehlter_feed_verschwindet(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    geraete = dr.async_get(hass)
    assert len(dr.async_entries_for_config_entry(geraete, eintrag.entry_id)) == 2

    hass.config_entries.async_update_entry(eintrag, options={**eintrag.options, "feeds": ["all"]})
    await hass.config_entries.async_reload(eintrag.entry_id)
    await hass.async_block_till_done()
    assert [g.name for g in dr.async_entries_for_config_entry(geraete, eintrag.entry_id)] == [
        "Meinungsmache Alle Artikel"
    ]
    assert hass.states.get("sensor.meinungsmache_donald_trump_neuester_artikel") is None


@pytest.mark.freeze_time(JETZT)
async def test_vorlagen_und_diagnose(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    from pathlib import Path

    from custom_components.meinungsmache.diagnostics import async_get_config_entry_diagnostics

    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    ordner = Path(hass.config.path("blueprints", "automation", "meinungsmache"))
    assert sorted(p.name for p in ordner.glob("*.yaml")) == ["benachrichtigung.yaml", "neuer_artikel.yaml"]

    diagnose = await async_get_config_entry_diagnostics(hass, eintrag)
    assert diagnose["feeds"]["all"]["artikel"] == 4
    assert diagnose["feeds"]["donald-trump"]["fehler"] is None


@pytest.mark.freeze_time(JETZT)
async def test_bilder_ueber_home_assistant(
    hass: HomeAssistant, eintrag: MockConfigEntry, aioclient_mock: AiohttpClientMocker, hass_client_no_auth
) -> None:
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    feeds_bereitstellen(aioclient_mock, all="all.xml", donald_trump="donald-trump.xml")
    aioclient_mock.get(
        "https://meinungsmache.de/gateway/articles/testartikel-eins/image",
        content=b"BILD",
        headers={"Content-Type": "image/avif"},
    )
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()

    antwort = await client.get("/api/meinungsmache/bild/testartikel-eins")
    assert antwort.status == 200
    assert antwort.headers["Content-Type"] == "image/avif"
    assert await antwort.read() == b"BILD"
    await client.get("/api/meinungsmache/bild/testartikel-eins")
    assert aioclient_mock.call_count == 3  # zwei Feeds, das Bild nur einmal

    assert (await client.get("/api/meinungsmache/bild/fremdes-bild")).status == 404
