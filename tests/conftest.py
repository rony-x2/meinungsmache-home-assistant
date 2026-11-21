"""Gemeinsame Hilfen für die Tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meinungsmache.const import CONF_ANZAHL, CONF_FEEDS, CONF_INTERVALL, DOMAIN
from homeassistant.core import HomeAssistant

FIXTURES = Path(__file__).parent / "fixtures"
JETZT = "2026-11-21 19:00:00+00:00"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def feeds_bereitstellen(aioclient_mock: AiohttpClientMocker, **feeds: str) -> None:
    """feeds: slug (mit _ statt -) -> Dateiname."""
    aioclient_mock.clear_requests()
    for slug, datei in feeds.items():
        aioclient_mock.get(f"https://meinungsmache.de/rss/{slug.replace('_', '-')}", text=fixture(datei))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def eintrag(hass: HomeAssistant) -> MockConfigEntry:
    e = MockConfigEntry(
        domain=DOMAIN,
        title="Meinungsmache",
        data={},
        options={CONF_FEEDS: ["all", "donald-trump"], CONF_INTERVALL: 15, CONF_ANZAHL: 3},
    )
    e.add_to_hass(hass)
    return e
