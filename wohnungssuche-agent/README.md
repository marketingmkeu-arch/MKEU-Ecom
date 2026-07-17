# Wohnungssuche-Agent (Kleinanzeigen, Düsseldorf)

Einfaches Tool zur Suche nach **Eigentumswohnungen zum Kauf** auf
kleinanzeigen.de in ausgewählten Düsseldorfer Stadtteilen. Es sammelt Treffer,
entfernt Duplikate, markiert bereits gesehene Anzeigen und sortiert neue,
passende Angebote nach oben – ohne Nachrichten zu verschicken und ohne
Schutzmaßnahmen von Kleinanzeigen zu umgehen.

## Suchkriterien

- Kategorie: Eigentumswohnungen, Angebotsart: Kaufen
- Ort: Düsseldorf, max. 300.000 €
- Stadtteile: Bilk, Unterbilk, Friedrichstadt, Pempelfort, Stadtmitte,
  Golzheim, Oberkassel, Flehe, Flingern-Nord
- Ausgeschlossen: Miete, Garagen, Stellplätze, Grundstücke,
  Gewerbeimmobilien, Häuser, Ferienwohnungen, Teilverkäufe, reine
  Kapitalanlagen mit laufender Langzeitvermietung
- Priorisiert (in dieser Reihenfolge): privat **und** provisionsfrei →
  privat → provisionsfrei → bezugsfrei → Balkon/Loggia/Terrasse →
  neueste Anzeige zuerst

## Wichtige Einschränkung: automatischer Abruf

Kleinanzeigen schützt seine Suchseiten aktiv gegen automatisierte Zugriffe.
Ein Testabruf während der Entwicklung dieses Tools wurde bereits mit
`HTTP 403` blockiert. Das Tool versucht `fetch` trotzdem als **einzelnen,
höflichen Probeversuch** – bricht aber sofort ab, sobald eine Blockade,
ein Captcha oder ein `robots.txt`-Verbot erkannt wird. Es gibt keine
Wiederholungsversuche, keine Proxys und keine Captcha-Umgehung.

**Der zuverlässige Weg ist der manuelle Import** (siehe unten). Das Tool
öffnet dafür die korrekt gefilterten Suchseiten in deinem eigenen Browser.

## Installation

```bash
cd wohnungssuche-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Nutzung

### 1. Gefilterte Suchlinks öffnen

```bash
python agent.py urls --open
```

Öffnet für jeden Stadtteil eine bereits passend gefilterte Kleinanzeigen-Seite
(Eigentumswohnung, Kaufen, Düsseldorf, max. 300.000 €, Stadtteil als
Suchbegriff). Mit `--privat` werden zusätzlich Varianten mit dem
Kleinanzeigen-eigenen "nur privat"-Filter angezeigt/geöffnet.

Ohne `--open` werden die Links nur ausgegeben, z. B. um sie manuell in einen
Browser-Tab zu kopieren.

### 2. Automatischen Abruf versuchen (optional)

```bash
python agent.py fetch
```

Versucht die Suchergebnisse direkt herunterzuladen. Schlägt das fehl
(wahrscheinlich), einfach mit Schritt 3 weitermachen.

### 3. Manueller Import (empfohlener Weg)

1. Öffne die Links aus Schritt 1 in deinem Browser (dort bist du normal
   unterwegs, keine Automatisierung, keine Captcha-Umgehung nötig).
2. Für jede Stadtteil-Seite mit Ergebnissen: Seite speichern
   (`Strg+S` / `Cmd+S` → "Webseite, komplett") in den Ordner
   `wohnungssuche-agent/imports/`. Der Dateiname darf den Stadtteilnamen
   enthalten, muss aber nicht (er wird zusätzlich aus dem Anzeigentext
   erkannt).
3. Import einlesen:

   ```bash
   python agent.py import
   ```

### 4. Bericht erzeugen

```bash
python agent.py report
```

Zeigt eine sortierte Übersicht in der Konsole und schreibt zusätzlich
`data/bericht.md`. Jede Anzeige zeigt Titel, Kaufpreis, Stadtteil,
Wohnfläche, Zimmerzahl, privat/gewerblich, provisionsfrei/-pflichtig,
bezugsfrei/vermietet, Balkon/Loggia/Terrasse und den Link zur Anzeige.
Fehlende Angaben werden ausdrücklich als "nicht angegeben" markiert.

Beim erneuten Ausführen von `report` werden Anzeigen aus vorherigen Läufen
als `[bereits gesehen]` markiert, neue als `[NEU]` hervorgehoben.

## Datenablage

- `data/listings.json` – alle bisher gefundenen Anzeigen (dedupliziert nach
  Kleinanzeigen-Anzeigen-ID)
- `data/seen.json` – IDs bereits angezeigter Anzeigen
- `data/bericht.md` – zuletzt erzeugter Bericht

Diese Dateien enthalten persönliche Suchdaten und sind über `.gitignore`
von Commits ausgeschlossen.

## Grenzen dieser einfachen Version

- Die Extraktion von Preis, Fläche, Zimmerzahl, Anbietertyp usw. basiert auf
  Text-Mustern in der Kleinanzeigen-Seite. Ändert Kleinanzeigen sein
  Seitenlayout grundlegend, muss die Erkennung in `agent.py` angepasst
  werden.
- Die Stadtteil-Zuordnung erfolgt über den Suchbegriff bzw. über den Text der
  Anzeige – keine Umkreissuche auf PLZ-Basis.
- Kein automatischer Versand von Nachrichten, keine Anmeldung, keine
  Umgehung von Sicherheitsmechanismen.
