# Dynamic Pricing – Concordiastraße 15, Düsseldorf

Datengetriebenes, nachvollziehbares Pricing-System für eine 60-m²-Ferienwohnung (2 Zimmer, Balkon) in
Unterbilk. Erzeugt für jeden der nächsten 365 Tage einen empfohlenen Übernachtungspreis mit Begründung.

- **Ergebnis:** [`reports/pricing_report.md`](reports/pricing_report.md) ·
  [`output/pricing_calendar_12m.csv`](output/pricing_calendar_12m.csv) · [`output/strategy.json`](output/strategy.json)
- **Plan & Architektur:** [`docs/PLAN.md`](docs/PLAN.md)
- **Datenquellen:** [`docs/DATENQUELLEN.md`](docs/DATENQUELLEN.md)
- **Modell:** [`docs/MODELL.md`](docs/MODELL.md)

## Ausführen

```bash
cd airbnb-pricing
PYTHONPATH=src python3 -m dynpricing.cli run              # Stichtag = heute
PYTHONPATH=src python3 -m dynpricing.cli run --as-of 2026-10-04
python3 -m pytest -q tests
```

Python ≥ 3.11, keine Laufzeitabhängigkeiten.

## Daten aktualisieren

| Datei | Inhalt | Wer/Wie |
|---|---|---|
| `data/raw/events/events.csv` | Messen und Events mit Tier, Quelle, Konfidenz | manuell, z. B. quartalsweise |
| `data/raw/comps/comp_listings.csv` | Vergleichsobjekte | manuell recherchiert oder Anbieter-Export |
| `data/raw/comps/price_snapshots.csv` | angebotene Preise je Aufenthaltsdatum | wöchentlich |
| `data/raw/historical/market_daily.csv` | historische Tages-ADR/Auslastung | Export AirDNA / PriceLabs |
| `data/raw/market/market_aggregates.csv` | Marktaggregate | bei neuen Anbieterdaten |
| `config/pricing.toml` | alle Parameter und Annahmen | bei Kalibrierung |

Der nächste Lauf nutzt neue Daten automatisch: Comps fließen in den Tagespreis ein, historische Daten
ersetzen die Wochentags- und Saisonannahmen, und ein Backtest wird geschrieben.

## Grundsätze

- Keine erfundenen Daten. Fehlende Daten werden als „keine belastbaren Daten verfügbar“ ausgewiesen.
- Datenklassen: 1 beobachtet · 2 externer Anbieter · 3 abgeleitete Schätzung · 4 Modellannahme.
- Angebotene Preise werden nie als realisierte Preise behandelt.
- Kein Scraping von Airbnb und kein Umgehen von Zugriffsbeschränkungen.
