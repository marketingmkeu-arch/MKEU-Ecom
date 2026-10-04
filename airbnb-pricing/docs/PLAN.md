# Projektplan: Dynamic Pricing Concordiastraße 15

Arbeitsreihenfolge wie vereinbart: 1. Ziel verstehen → 2. Datenquellen → 3. Datenqualität →
4. Architektur → 5. Implementierungsplan → 6. Datenerfassung und Implementierung.

## 1. Projekt und Ziel

- **Objekt:** ca. 60 m², 2 Zimmer (1 Schlafzimmer), Balkon, Kücheninsel, frisch renoviert, möbliert;
  Unterbilk, ca. 500 m bis Medienhafen/Bilk, ca. 1,5 km bis Altstadt/Königsallee, ca. 5,8 km bis
  Messe/Merkur Spiel-Arena (Luftlinie, Koordinaten manuell geokodiert).
- **Ziel:** Für jeden der nächsten 365 Tage einen nachvollziehbaren Übernachtungspreis empfehlen;
  das System soll sich regelmäßig automatisch mit neuen Markt-, Event- und Buchungsdaten aktualisieren.
- **Zielgruppe der Wohnung:** Messe- und Geschäftsreisende (Mo–Do), Städtereisende/Paare und kleine
  Gruppen (Fr–So), Event-Besucher (Konzerte, Karneval).
- **Wichtigste Nebenbedingung (neu erkannt):** Düsseldorfer Wohnraumschutzsatzung – ohne Genehmigung
  **max. 90 Nächte pro Kalenderjahr** und Pflicht zur Wohnraum-ID. Das verschiebt das Optimierungsziel von
  „Auslastung“ zu „Erlös pro verbrauchter Nacht“. → **Offene Frage an den Eigentümer: Liegt eine
  Zweckentfremdungsgenehmigung vor?**

## 2. Verfügbare Datenquellen

Vollständige Bewertung: [DATENQUELLEN.md](DATENQUELLEN.md). Kurzfassung:

| Bedarf | Beste legale Quelle | Status |
|---|---|---|
| Comp Set (Listings, Ausstattung) | manuelle Recherche → CSV; später AirDNA/PriceLabs | Vorlage bereit, **nicht erhoben** |
| Angebotene Preise je Datum | wöchentliche manuelle Snapshots; PriceLabs/AirDNA | Vorlage bereit, **nicht erhoben** |
| Realisierte Preise / Auslastung | eigene Buchungsdaten (Channel Manager); AirDNA (modelliert) | **nicht verfügbar** |
| Historische Tages-ADR/Auslastung | AirDNA / PriceLabs (kostenpflichtig) | **nicht verfügbar** |
| Marktaggregate Viertel | guestfavorites, airbtics, AirROI (Snippets) | genutzt, Konfidenz niedrig |
| Saison (amtlich) | IT.NRW Beherbergungsstatistik (GENESIS 45412) | zu integrieren (Phase B) |
| Messen | Messe Düsseldorf, Koelnmesse | 12 Monate erfasst |
| Events | visitduesseldorf, Venues, Ticketing | erfasst, z. T. unbestätigt |
| Feiertage / Ferien | Kalenderregel / Schulministerium NRW | erfasst |

## 3. Datenqualität

| Datenbereich | Klasse | Bewertung |
|---|---|---|
| Messetermine 10/2026–10/2027 | 1/2 | gut; REHACARE 2027 ohne Termin; Japan-Tag widersprüchlich (22. vs. 29.05.) |
| Besucherzahlen | 2 | nur für MEDICA, CARAVAN SALON, ProWein, A+A, glasstec belegt |
| Viertel-ADR | 2 | niedrig: Snippets, unbekannte Methodik, verschiedene Stichtage |
| Auslastung | 2 | widersprüchlich (58 % vs. 35,9 %) → **keine belastbaren Daten** |
| Wochentags-, Saison-, Event-Faktoren | 4 | Priors, kalibrierbar |
| Comp-Preise, Gebühren, Rabatte | – | **keine belastbaren Daten verfügbar** |
| Historische Event-Wirkung | – | **keine belastbaren Daten verfügbar** |

## 4. Architektur

```
airbnb-pricing/
├── config/pricing.toml           alle Parameter, je markiert als Datenableitung oder ANNAHME
├── data/
│   ├── raw/                      Rohdaten (versioniert, mit Quelle/Konfidenz je Zeile)
│   │   ├── events/events.csv
│   │   ├── calendar/school_holidays_nrw.csv
│   │   ├── market/market_aggregates.csv
│   │   ├── comps/comp_listings.csv, price_snapshots.csv   (Vorlagen)
│   │   └── historical/market_daily.csv                    (Vorlage für AirDNA-/PriceLabs-Export)
│   └── processed/pricing.db      SQLite: raw_* Spiegel + calc_* Ergebnisse je Lauf (nicht versioniert)
├── src/dynpricing/
│   ├── calendar_data.py          Feiertage NRW (Osterformel), Schulferien, lange Wochenenden
│   ├── event_calendar.py         Events, Distanzen, Nachtgewichte, Überlagerung
│   ├── market_data.py            Marktaggregate, Anker-ADR
│   ├── competitor_analysis.py    Comp-Score, Radien 0,5/1/2/3/5 km, Snapshot-Mediane, Verfügbarkeit
│   ├── historical_data.py        Faktor-Schätzung, Event-Uplift-Messung
│   ├── demand_model.py           Nachfrageindex je Nacht (erklärbare Komponenten)
│   ├── pricing_engine.py         Basis, Preisgrenzen, Tagespreis, Lead Time, Pace, Mindestaufenthalt, 90-Nächte-Limit
│   ├── validation.py             Backtest
│   ├── reporting.py              CSV-Kalender, strategy.json, Markdown-Report
│   ├── db.py                     SQLite
│   ├── pipeline.py / cli.py      Orchestrierung
├── output/                       pricing_calendar_12m.csv, strategy.json, (backtest.json)
├── reports/pricing_report.md
└── tests/
```

Prinzipien: nur Standardbibliothek (reproduzierbar, keine Abhängigkeiten); Rohdaten getrennt von
Ergebnissen; jede Zahl im Report trägt Datenklasse und Quelle; jede Tagesempfehlung hat eine Begründung.

## 5. Implementierungsplan

### Phase A – erledigt in diesem Schritt
- [x] Recherche Datenquellen, Regulierung, Messe-/Eventkalender 12 Monate
- [x] Modulares Gerüst, SQLite, Konfiguration
- [x] Nachfrage- und Pricing-Modell mit Priors, Basis-Kalibrierung auf Markt-ADR
- [x] Lead-Time-Logik ohne automatische Last-Minute-Rabatte bei Verknappung
- [x] 90-Nächte-Priorisierung mit Schattenpreis
- [x] 12-Monats-Kalender, Strategie-JSON, Report
- [x] Werkzeuge für Event-Uplift-Messung und Backtest (warten auf Daten)
- [x] Tests (26)

### Phase B – Datenerfassung (empfohlen als Nächstes; benötigt Eigentümer)
1. **Sofort (MEDICA ist am 16.–19.11.2026, in 6 Wochen):** 15–25 Comps manuell erfassen
   (`comp_listings.csv`) und für ein Messedatum, einen Normal-Dienstag und ein Normal-Wochenende die
   angebotenen Preise erfassen (`price_snapshots.csv`). Danach wöchentlich wiederholen.
2. Regulierungsstatus klären (Wohnraum-ID / Genehmigung) → `regulation.annual_night_cap`.
3. Datenanbieter wählen (PriceLabs oder AirDNA) und Tagesdaten der letzten 24 Monate exportieren
   → `historical/market_daily.csv`. Damit: Faktoren kalibrieren, Event-Uplifts messen, Backtest
   (MEDICA 2025, boot 2026, ProWein 2026, CARAVAN SALON 2025).
4. IT.NRW-Monatsdaten (GENESIS 45412, Düsseldorf) als Saison-Gegencheck einbinden.

### Phase C – Automatisierung
1. GitHub-Workflow (bereits angelegt, `airbnb-pricing.yml`): wöchentlich Tests + Neuberechnung + Commit.
2. Connector für Snapshot-/Anbieter-Export (CSV-Import aus dem Datenanbieter, kein Scraping).
3. Eigene Buchungen über Channel Manager (z. B. Smoobu/Hostaway-API) → Pace-Faktor und Lead-Time-Kalibrierung.
4. Optional: Preis-Push in den Channel Manager (erst nach mehreren Wochen Schattenbetrieb).

### Phase D – Modellverbesserung (wenn ≥ 12 Monate Tagesdaten vorliegen)
- Regression (log-ADR ~ Monat + Wochentag + Event-Features + Ferien) statt fester Priors.
- Nachfrage-/Preiselastizität aus eigenen Buchungen (Buchungswahrscheinlichkeit je Preis und Vorlauf).
- Optimierung des 90-Nächte-Kontingents unter Unsicherheit (Erwartungserlös statt statischem Preisrang).
