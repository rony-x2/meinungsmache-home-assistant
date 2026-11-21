"""Lesen der Feeds."""

from datetime import UTC, datetime

import pytest

from custom_components.meinungsmache.feed import FeedFehler, klartext, lies_feed

from .conftest import fixture


def test_lies_feed() -> None:
    artikel = lies_feed(fixture("all_neu.xml"))
    assert [a.titel for a in artikel][:2] == ["EXKLUSIV: Ein Interview", "Testartikel eins"]
    exklusiv, eins = artikel[0], artikel[1]
    assert exklusiv.exklusiv and exklusiv.eigen and exklusiv.autor == "Mara"
    assert not eins.exklusiv and not eins.eigen
    assert eins.teaser == "Ein kurzer Anrisstext & mehr."
    assert eins.veroeffentlicht == datetime(2026, 11, 21, 17, 0, 1, tzinfo=UTC)
    assert eins.bild == "https://meinungsmache.de/gateway/articles/testartikel-eins/image"
    assert eins.als_dict()["bild"] == "/api/meinungsmache/bild/testartikel-eins"
    assert artikel[-1].bild is None
    assert len(artikel[3].teaser) <= 282 and artikel[3].teaser.endswith(" …")


def test_klartext_kuerzt_an_wortgrenze() -> None:
    assert klartext("<p>eins zwei drei vier</p>", 12) == "eins zwei …"
    assert klartext("<p>kurz</p>") == "kurz"


@pytest.mark.parametrize("inhalt", ["kein xml", "<feed></feed>"])
def test_ungueltige_feeds(inhalt: str) -> None:
    with pytest.raises(FeedFehler):
        lies_feed(inhalt)
