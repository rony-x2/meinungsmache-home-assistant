#!/usr/bin/env python3
"""
bauen.py – baut die Projektseite „Meinungsmache für Home Assistant“ nach seite/dist/.

  python3 seite/bauen.py           Seite, Karte, Zeichen und Vorschaubild schreiben

Die Vorführung zeigt die echte Karte aus custom_components/meinungsmache/frontend. Die Artikel dafür
liest das Bauskript aus der Schnittstelle von „Rede mit Meinungsmache“ (stand.php); seite.js holt sie
beim Aufruf aktuell nach. Ohne Netz baut die Seite mit leerer Vorführung.
"""

import asyncio
from datetime import date, datetime
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import sys
import urllib.request
from zoneinfo import ZoneInfo

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
ZIEL = HIER / "dist"
KARTE = WURZEL / "custom_components" / "meinungsmache" / "frontend" / "meinungsmache-card.js"
SEITE = "https://poc.deutschkaemer.info/meinungsmache-home-assistant/"
STAND_URL = "https://poc.deutschkaemer.info/meinungsmache/stand.php"
GITHUB = "https://github.com/rony-x2/meinungsmache-home-assistant"
V_CSS, V_JS = 1, 1
BESCHREIBUNG = (
    "Die Nachrichten von meinungsmache.de in Home Assistant: Feeds wählen, neueste Artikel auf dem Dashboard "
    "und Automationen bei exklusiven Artikeln oder Themen."
)
BEFEHL_ZEILEN = (
    "cd /config && mkdir -p custom_components && \\\n"
    f"  curl -fsSL {GITHUB}/archive/refs/heads/main.tar.gz | \\\n"
    "  tar xz --strip-components=2 -C custom_components \\\n"
    "  meinungsmache-home-assistant-main/custom_components/meinungsmache && \\\n"
    "  ha core restart"
)
BEFEHL = re.sub(r"\s*\\\n\s*", " ", BEFEHL_ZEILEN)

FARBE, LINIE = "#C5A46D", "#1b1f27"
ZEITUNG = '<path d="M6 5.5h12v13H6z"/><path d="M8.6 8.4h3.3v3.1H8.6zM14 8.6h1.6M14 11.3h1.6M8.6 14.6h6.9"/>'

IKONEN = {
    "menue": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "schliessen": '<path d="M6 6l12 12M18 6L6 18"/>',
    "code": '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 4.5l-3 15"/>',
    "haken": '<circle cx="12" cy="12" r="9"/><path d="M8 12.4l2.8 2.8L16.2 9.6"/>',
    "karte": '<rect x="3.5" y="4" width="17" height="16" rx="2.5"/><path d="M7 8.5h10M7 12h10M7 15.5h6"/>',
    "blitz": '<path d="M13 3L5.5 13.5H11L10 21l7.5-10.5H12z"/>',
    "glocke": '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 1.5H5z"/><path d="M10 20.5a2.2 2.2 0 0 0 4 0"/>',
    "rss": '<path d="M5 11a8 8 0 0 1 8 8M5 5a14 14 0 0 1 14 14"/><circle cx="6" cy="18" r="1.4"/>',
    "haus": '<path d="M4 11.5L12 4.5l8 7"/><path d="M6 10v9.5h12V10"/><path d="M10 19.5v-5h4v5"/>',
    "paket": '<path d="M12 3.5l8 4.5v8l-8 4.5-8-4.5V8z"/><path d="M4 8l8 4.5L20 8M12 12.5v8.5"/>',
    "konsole": '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15h4.5"/>',
    "regler": '<path d="M5 7h9M18 7h1M5 17h3M12 17h7"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    "pfeil": '<path d="M7 17L17 7M9 7h8v8"/>',
}

# Beispiele für Automationen: Vorlage, Feeds, Art, Stichwörter
FAELLE = [
    ("blitz", "Exklusiver Artikel erschienen", "Alle Artikel", "Nur exklusive", "–"),
    ("glocke", "Meldung zu Trump", "Donald Trump, USA", "Alle", "– (oder „Alle Artikel“ mit „Trump“)"),
    ("karte", "Meldung zur Wirtschaft", "Wirtschaft", "Alle", "–"),
    ("rss", "Neuer Artikel generell", "Alle Artikel", "Alle", "–"),
]

h = lambda s: html.escape(str(s), quote=True)  # noqa: E731


def ikon(name: str, klasse: str = "ikon") -> str:
    return (
        f'<svg class="{klasse}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{IKONEN[name]}</svg>'
    )


def zeichen(klasse: str = "projektzeichen kachelzeichen", eckig: bool = False) -> str:
    """Projektzeichen: Zeitungsseite auf der Kennfarbe von meinungsmache.de (wie brand/icon.png)."""
    return (
        f'<svg class="{klasse}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        f'<rect width="24" height="24" rx="{0 if eckig else 5.5}" fill="{FARBE}"/>'
        f'<g fill="none" stroke="{LINIE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{ZEITUNG}</g></svg>"
    )


def feeds() -> dict[str, str]:
    """Feeds aus const.py der Integration (eine Quelle für beide)."""
    text = (WURZEL / "custom_components" / "meinungsmache" / "const.py").read_text(encoding="utf-8")
    block = text.split("FEEDS: Final[dict[str, str]] = {", 1)[1].split("}", 1)[0]
    return dict(re.findall(r'"([a-z-]+)": "([^"]+)"', block))


def berlin_iso(zeit: str) -> str:
    """„2026-11-21 18:00“ (deutsche Zeit, wie stand.php sie liefert) als ISO-Zeit mit Versatz."""
    return datetime.strptime(zeit[:16], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Berlin")).isoformat()


def demo_daten() -> tuple[list[dict], str]:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(STAND_URL, headers={"Accept": "application/json"}), timeout=20
        ) as r:
            stand = json.load(r)
    except OSError as err:
        print("Hinweis: kein Stand für die Vorführung:", err, file=sys.stderr)
        return [], ""
    eintraege = []
    for a in stand.get("neueste", []):
        eigen = a.get("art") == "eigen"
        eintraege.append(
            {
                "titel": a["titel"],
                "link": a["url"],
                "veroeffentlicht": berlin_iso(a["zeit"]),
                "autor": a.get("von") if eigen else None,
                "eigen": eigen,
                "exklusiv": bool(re.match(r"\s*exklusiv\b", a["titel"], re.I)),
            }
        )
    return eintraege, stand.get("letzter_abruf") or stand.get("bis") or ""


def stand_text(zeit: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})", zeit or "")
    return f"{m[3]}.{m[2]}.{m[1]}, {m[4]} Uhr" if m else "beim Bauen"


def art_text(a: dict) -> str:
    return (
        "Exklusiv · Alle Artikel"
        if a["exklusiv"]
        else (f"{a['autor']} · Alle Artikel" if a["eigen"] else "Meldung · Alle Artikel")
    )


def faelle_html() -> str:
    teile = []
    for name, titel, feed, art, stich in FAELLE:
        teile.append(f"""        <article class="kachel fall-ha">
          <h3 class="mit-logo">{ikon(name, "ikon logo")}{h(titel)}</h3>
          <dl>
            <div><dt>Feeds</dt><dd>{h(feed)}</dd></div>
            <div><dt>Art</dt><dd>{h(art)}</dd></div>
            <div><dt>Stichwörter</dt><dd>{h(stich)}</dd></div>
          </dl>
        </article>""")
    return "\n".join(teile)


def import_link(datei: str) -> str:
    quelle = f"{GITHUB}/blob/main/custom_components/meinungsmache/blueprints/{datei}"
    return "https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=" + urllib.request.quote(
        quelle, safe=""
    )


def schema() -> str:
    person = {
        "@type": "Person",
        "@id": "https://deutschkaemer.info/#person",
        "name": "Dennis Deutschkämer",
        "url": "https://deutschkaemer.info",
    }
    quelle = {
        "@type": "NewsMediaOrganization",
        "@id": "https://meinungsmache.de/#organisation",
        "name": "Meinungsmache",
        "url": "https://meinungsmache.de",
    }
    software = {
        "@type": "SoftwareApplication",
        "@id": SEITE + "#integration",
        "name": "Meinungsmache für Home Assistant",
        "description": BESCHREIBUNG,
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "Home Assistant",
        "isAccessibleForFree": True,
        "inLanguage": ["de", "en"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "softwareVersion": version(),
        "downloadUrl": GITHUB,
        "license": "https://opensource.org/license/mit",
        "author": {"@id": person["@id"]},
        "about": {"@id": quelle["@id"]},
    }
    quelltext = {
        "@type": "SoftwareSourceCode",
        "@id": SEITE + "#quelltext",
        "name": "meinungsmache-home-assistant",
        "codeRepository": GITHUB,
        "programmingLanguage": ["Python", "JavaScript"],
        "license": "https://opensource.org/license/mit",
        "author": {"@id": person["@id"]},
        "targetProduct": {"@id": software["@id"]},
    }
    seite = {
        "@type": "WebPage",
        "@id": SEITE + "#seite",
        "url": SEITE,
        "name": "Meinungsmache für Home Assistant",
        "description": BESCHREIBUNG,
        "inLanguage": "de",
        "dateModified": date.today().isoformat(),
        "isPartOf": {
            "@type": "WebSite",
            "@id": "https://poc.deutschkaemer.info/#website",
            "name": "Proof of Concepts – Dennis Deutschkämer",
            "url": "https://poc.deutschkaemer.info/",
            "author": {"@id": person["@id"]},
        },
        "about": {"@id": quelle["@id"]},
        "mainEntity": {"@id": software["@id"]},
        "author": {"@id": person["@id"]},
        "primaryImageOfPage": SEITE + "og.png",
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Proof of Concepts",
                    "item": "https://poc.deutschkaemer.info/",
                },
                {"@type": "ListItem", "position": 2, "name": "Meinungsmache für Home Assistant", "item": SEITE},
            ],
        },
    }
    graph = {"@context": "https://schema.org", "@graph": [seite, software, quelltext, quelle, person]}
    roh = json.dumps(graph, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return '  <script type="application/ld+json">\n' + roh + "\n  </script>"


def version() -> str:
    return json.loads((WURZEL / "custom_components" / "meinungsmache" / "manifest.json").read_text())["version"]


async def bilder() -> None:
    """Zeichen in den üblichen Größen und das Vorschaubild für geteilte Links."""
    from playwright.async_api import async_playwright

    (ZIEL / "favicon.svg").write_text(
        zeichen("", False).replace(' class=""', ' xmlns="http://www.w3.org/2000/svg"') + "\n"
    )
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, px, eckig in (
            ("favicon-32.png", 32, False),
            ("icon-192.png", 192, False),
            ("icon-512.png", 512, False),
            ("apple-touch-icon.png", 180, True),
        ):
            pg = await b.new_page(viewport={"width": px, "height": px})
            svg = zeichen("", eckig).replace("<svg ", f'<svg width="{px}" height="{px}" ', 1)
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await pg.screenshot(path=str(ZIEL / name), omit_background=True)
            await pg.close()
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        await pg.set_content(vorschau_html())
        await pg.screenshot(path=str(ZIEL / "og.png"))
        await b.close()


def vorschau_html() -> str:
    zeilen = "".join(
        f'<div class="z"><b>{h(t)}</b><span>{h(m)}</span></div>'
        for t, m in (
            ("EXKLUSIV: Interview mit …", "Exklusiv · vor 5 Minuten"),
            ("Neue Meldung zur Wirtschaft", "Meldung · vor 2 Stunden"),
            ("Bericht aus Leipzig", "Eigener Artikel · gestern"),
        )
    )
    return f"""<html><head><style>
body {{ margin:0; width:1200px; height:630px; background:#0f1115; color:#e8eaf0; font-family: system-ui, sans-serif;
  display:grid; grid-template-columns: 1.1fr 1fr; align-items:center; gap:48px; padding:0 72px; box-sizing:border-box; }}
.k {{ font-size:22px; letter-spacing:.12em; text-transform:uppercase; color:{FARBE}; margin:0 0 18px; }}
h1 {{ font-size:62px; line-height:1.05; margin:0 0 22px; }}
p {{ font-size:26px; line-height:1.4; color:#aab0bd; margin:0; }}
.karte {{ background:#1a1d24; border:1px solid #2a2f3a; border-radius:20px; padding:22px; }}
.kopf {{ display:flex; align-items:center; gap:12px; font-size:24px; margin-bottom:10px; }}
.kopf svg {{ width:40px; height:40px; }}
.z {{ border-top:1px solid #2a2f3a; padding:14px 0; display:flex; flex-direction:column; gap:4px; }}
.z b {{ font-size:22px; }} .z span {{ font-size:17px; color:#aab0bd; }}
.zeichen svg {{ width:88px; height:88px; margin-bottom:22px; }}
</style></head><body>
<div><div class="zeichen">{zeichen("")}</div><p class="k">Proof of Concept · Home Assistant</p>
<h1>Meinungsmache für Home Assistant</h1><p>Feeds wählen, neueste Artikel aufs Dashboard, Automationen bei exklusiven Artikeln oder Themen.</p></div>
<div class="karte"><div class="kopf">{zeichen("")}<b>Meinungsmache</b></div>{zeilen}</div>
</body></html>"""


def main() -> None:
    ZIEL.mkdir(exist_ok=True)
    eintraege, stand = demo_daten()
    erster = eintraege[0] if eintraege else {"titel": "", "exklusiv": False, "eigen": False}
    karte = KARTE.read_bytes()
    ersetzen = {
        "SEITE": SEITE,
        "GITHUB": GITHUB,
        "BESCHREIBUNG": h(BESCHREIBUNG),
        "SCHEMA": schema(),
        "BEFEHL": h(BEFEHL),
        "BEFEHL_ZEILEN": h(BEFEHL_ZEILEN),
        "ZEICHEN": zeichen(),
        "ZEICHEN_KLEIN": zeichen("m-svg"),
        "ERSTER_TITEL": h(erster["titel"]),
        "ERSTER_UNTER": h(art_text(erster)) if eintraege else "",
        "STAND": h(stand_text(stand)),
        "DEMO_DATEN": json.dumps(eintraege, ensure_ascii=False).replace("</", "<\\/"),
        "FAELLE": faelle_html(),
        "FEEDS": "\n".join(f"        <li><span>{h(n)}</span><code>{h(s)}</code></li>" for s, n in feeds().items()),
        "IMPORT_BENACHRICHTIGUNG": h(import_link("benachrichtigung.yaml")),
        "IMPORT_AKTIONEN": h(import_link("neuer_artikel.yaml")),
        "V_CSS": str(V_CSS),
        "V_JS": str(V_JS),
        "V_KARTE": hashlib.sha256(karte).hexdigest()[:10],
    }
    text = (HIER / "vorlage.html").read_text(encoding="utf-8")
    for k, v in ersetzen.items():
        text = text.replace("{{" + k + "}}", v)
    text = re.sub(r"\{\{ikon:([^:}]+)(?::([^}]+))?\}\}", lambda m: ikon(m[1], m[2] or "ikon"), text)
    assert "{{" not in text, re.findall(r"\{\{[^}]*\}\}", text)
    assert "—" not in text, "Geviertstrich gefunden"
    (ZIEL / "index.html").write_text(text, encoding="utf-8")
    for datei in ("seite.css", "seite.js"):
        shutil.copyfile(HIER / datei, ZIEL / datei)
    shutil.copyfile(KARTE, ZIEL / "meinungsmache-card.js")
    if "--ohne-bilder" not in sys.argv:
        asyncio.run(bilder())
    print("geschrieben:", ZIEL, len(eintraege), "Artikel für die Vorführung")


if __name__ == "__main__":
    main()
