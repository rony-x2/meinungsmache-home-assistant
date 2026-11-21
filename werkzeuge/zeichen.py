#!/usr/bin/env python3
"""Zeichen der Integration (Zeitungsseite auf der Kennfarbe von meinungsmache.de) als PNG für brand/ rendern."""

import asyncio
from pathlib import Path

FARBE = "#C5A46D"
LINIE = "#1b1f27"
SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    f'<rect width="24" height="24" rx="5.5" fill="{FARBE}"/>'
    f'<g fill="none" stroke="{LINIE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6 5.5h12v13H6z"/><path d="M8.6 8.4h3.3v3.1H8.6zM14 8.6h1.6M14 11.3h1.6M8.6 14.6h6.9"/></g></svg>'
)
ZIEL = Path(__file__).resolve().parent.parent / "custom_components" / "meinungsmache" / "brand"


async def main() -> None:
    from playwright.async_api import async_playwright

    ZIEL.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, px in (("icon.png", 256), ("icon@2x.png", 512)):
            seite = await b.new_page(viewport={"width": px, "height": px})
            svg = SVG.replace("<svg ", f'<svg width="{px}" height="{px}" ', 1)
            await seite.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await seite.screenshot(path=str(ZIEL / name), omit_background=True)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
