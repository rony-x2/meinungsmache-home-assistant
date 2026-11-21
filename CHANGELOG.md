# Änderungen

## 0.1.0 – 2026-11-21

Erste Fassung.

- Einrichtung über die Oberfläche: 28 Feeds von meinungsmache.de zur Wahl, Abrufabstand, Anzahl der Einträge; nachträglich änderbar
- Je Feed ein Gerät: Sensor „Neuester Artikel“ (mit Liste für die Karte), Zeitsensor „Zuletzt erschienen“, Event-Entität „Neuer Artikel“ (Arten: Artikel, eigener Artikel, exklusiv)
- Ereignis `meinungsmache_neuer_artikel`, einmal je Artikel über alle Feeds
- Dashboard-Karte `custom:meinungsmache-card` mit Reitern für mehrere Feeds und Editor
- Artikelbilder werden über Home Assistant ausgeliefert
- Automations-Vorlagen: Benachrichtigung an die Companion-App, eigene Aktionen; Filter nach Feed, Art und Stichwörtern
- Eigene Markenbilder im Ordner `brand/` (ab Home Assistant 2026.3)
