# Pricing-Modell

## 1. Nachfrageindex je Nacht

```
D = Saison[Monat] × Wochentag × (1 + Feiertag + Schulferien) × (1 + Event-Uplift)
```

- **1.0** = normaler Dienstag ohne Event in einem Durchschnittsmonat.
- **Event-Uplift**: je Event `Tier-Uplift × Nachtgewicht`. Nachtgewicht: Anreisenacht vor Messebeginn 0,8,
  volle Messenächte 1,0, Nacht des letzten Messetags 0,3 (pro Event überschreibbar, z. B. Konzert: nur
  die Konzertnacht; Marathon: nur die Nacht davor). Wochentagsfilter (z. B. Weihnachtsmarkt nur Fr/Sa).
- **Überlagerung** mehrerer Events: stärkstes Event voll, das zweite × 0,5, das dritte × 0,25 … – statt
  Multiplikation, damit gestapelte Events nicht explodieren.
- Bei Tier-S/A-Messen wird der Wochentagsabschlag (So–Mi < 1) neutralisiert, weil Messegäste genau dann
  übernachten.
- **Tiers statt Pauschalaufschlag:** Die Einstufung nutzt Besucherzahl, Internationalität
  (Übernachtungsquote), Fach- vs. Publikumsmesse und Dauer. Die Uplifts sind Priors, bis
  `historical_data.estimate_event_uplift` die Wirkung aus Tagesdaten misst
  (Event-ADR ÷ ADR derselben Wochentage ±4 Wochen ohne Event).

Nachfragestufen: niedrig < 0,93 ≤ normal < 1,08 ≤ erhöht < 1,30 ≤ hoch < 1,70 ≤ Spitze.

## 2. Basispreis

```
Anker-ADR       = Σ ADR(Viertel) × Gewicht              (Unterbilk 0,5 · Bilk 0,3 · Friedrichstadt 0,2)
angepasst       = Anker × Größenanpassung × Qualitätsaufschlag
Basis           = angepasst ÷ (Σ D² / Σ D)
```

Warum durch den nachfragegewichteten Index teilen? Die Markt-ADR ist ein Durchschnitt über **gebuchte**
Nächte, und gebuchte Nächte liegen überproportional an Wochenenden und Messetagen. Gewichtet man jeden
Tag mit seinem Index (Proxy für die Buchungswahrscheinlichkeit), erhält man den Preis eines Normaltages,
bei dem die erwartete ADR des Modells genau der Markt-ADR entspricht. Ein Test prüft diese Eigenschaft.

## 3. Tagespreis

```
statisch  = clamp(Basis × D, Minimum, Maximum)
            + Untergrenzen: Tier S volle Messenacht ≥ Event Price, Tier A ≥ High-Demand Price
            + optional: Mischung mit Comp-Median (angeboten) × Positionierung, Gewicht 40 %, ab 5 Comps
empfohlen = clamp(statisch × Lead-Time-Faktor × Pace-Faktor, Minimum, Maximum)
```

Preisgrenzen (Multiplikator auf die Basis): Minimum 0,78 (mind. 79 EUR) · Target 1,05 · High-Demand 1,35 ·
Event 1,70 · Maximum 3,0.

## 4. Lead Time

Die Tabelle in `config/pricing.toml` hat je Vorlauf-Bucket drei Spalten:

- **low** (Nachfrage niedrig): stärkere Last-Minute-Abschläge
- **normal**: moderate Abschläge ab 14 Tagen, leichte Aufschläge über 60 Tage
- **high** (Nachfrage hoch/Spitze **oder** verfügbare Comps < 25 %): **kein Rabatt**, kurzfristig +4 bis +8 %

Damit gibt es keinen automatischen Last-Minute-Rabatt: Bei Messe-Verknappung steigt der Preis.

## 5. Pace / Auslastung

Wenn eigene Buchungsdaten vorliegen: `pace_ratio = gebuchte Nächte ÷ erwartete gebuchte Nächte` für den
Zielzeitraum (Erwartungskurve aus eigener Historie oder AirDNA-Pacing). > 1,1 → +6 %, < 0,9 → −5 %,
begrenzt auf ±10 %. Ohne Daten neutral (1,0).

## 6. 90-Nächte-Limit

Ohne Genehmigung sind nur 90 Nächte pro Kalenderjahr erlaubt. Das ändert das Ziel: Statt Auslastung
zählt der Erlös je verbrauchter Nacht. Das Modell sortiert die Nächte jedes Kalenderjahres nach
statischem Preis und gibt die besten `ceil((90 − genutzt) ÷ Verkaufsquote)` frei. Der niedrigste
freigegebene Preis ist der **Schattenpreis**: Unterhalb davon lohnt sich der Verkauf einer Nacht nicht,
weil sie später teurer verkauft werden könnte.

## 7. Mindestaufenthalt

Standard 2 · Wochenende 2 · Tier-S-Messe 3 · niedrige Nachfrage 1 (Lückenfüller).

## 8. Kalibrierung (sobald Daten vorliegen)

| Parameter | Kalibrierung mit | Funktion |
|---|---|---|
| Wochentag, Saison | Tages-ADR Nicht-Event-Tage | `historical_data.estimate_factors` (überschreibt die Priors automatisch) |
| Event-Tiers | Tages-ADR um Events | `historical_data.estimate_event_uplift` |
| Basis / Positionierung | Comp-Snapshots | `competitor_analysis.comp_days` + Mischung |
| Lead Time | eigene Buchungen (Buchungsdatum, Check-in, Preis) | Phase B (geplant) |
| Gesamtmodell | Backtest | `validation.backtest` (MAPE, Bias Normal- vs. Eventtage, Rangkorrelation) |
