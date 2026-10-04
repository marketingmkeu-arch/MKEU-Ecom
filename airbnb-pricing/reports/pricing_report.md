# Pricing-Report Concordiastraße 15, Düsseldorf

_Automatisch erzeugt am 2026-10-04 durch `dynpricing`. Kalenderzeitraum: 2026-10-04 bis 2027-10-03._

> **Hinweis zur Datenlage:** Für diese Version liegen keine Preise einzelner Vergleichs-Listings, keine historischen Tagesdaten und keine eigenen Buchungsdaten vor. Basispreis und Faktoren beruhen auf Marktaggregaten externer Anbieter (nur aus Such-Snippets gelesen) und auf markierten Modellannahmen. Die Zahlen sind ein begründeter Startpunkt, aber keine Marktmessung.

## 1. Executive Summary

- **Realistischer Normalpreis (Basis, Di ohne Event):** ca. **118 EUR**
- **Normaler Wochentag (Mo–Do, Median):** 119 EUR · **Normales Wochenende (Fr/Sa, Median):** 139 EUR
- **Minimum Price:** 92 EUR · **Maximum Price:** 354 EUR
- **Stärkste Nachfragetreiber im Zeitraum:** MEDICA + COMPAMED 2026 (Ø 259 EUR, bis 259 EUR); glasstec 2026 (Ø 189 EUR, bis 189 EUR); ProWein 2027 (Ø 189 EUR, bis 189 EUR)
- **Regulierung:** Ohne Zweckentfremdungsgenehmigung sind in Düsseldorf höchstens **90 Nächte pro Kalenderjahr** Kurzzeitvermietung erlaubt (Wohnraum-ID nötig). Die Strategie sollte deshalb die wertvollsten Nächte priorisieren (Messen, Wochenenden, Oktober) – siehe Abschnitt 7.

## 2. Marktanalyse

Externe Marktaggregate (Datenklasse 2, Anbieter; **nicht verifiziert**, Methodik der Anbieter unbekannt):

| Anbieter | Gebiet | Kennzahl | Wert | Einheit | Zeitraum |
|---|---|---|---|---|---|
| guestfavorites | Unterbilk | adr | 139.0 | EUR | Seitenstand Juli 2026 |
| guestfavorites | Unterbilk | occupancy | 0.58 | ratio | Seitenstand Juli 2026 |
| guestfavorites | Friedrichstadt | adr | 147.0 | EUR | Seitenstand Juli 2026 |
| guestfavorites | Friedrichstadt | occupancy | 0.53 | ratio | Seitenstand Juli 2026 |
| guestfavorites | Bilk | adr | 109.0 | EUR | Seitenstand Februar 2026 |
| guestfavorites | Bilk | occupancy | 0.57 | ratio | Seitenstand Februar 2026 |
| guestfavorites | Altstadt | adr | 173.0 | EUR | Seitenstand Juli 2026 |
| guestfavorites | Altstadt | occupancy | 0.49 | ratio | Seitenstand Juli 2026 |
| guestfavorites | Derendorf | adr | 137.0 | EUR | Seitenstand Juni 2026 |
| guestfavorites | Pempelfort | adr | 122.0 | EUR | Seitenstand Februar 2026 |
| guestfavorites | Golzheim | adr | 159.0 | EUR | Seitenstand Januar 2026 |
| airbtics | Düsseldorf (Stadt) | adr | 109.0 | EUR | 2025 |
| airbtics | Düsseldorf (Stadt) | occupancy | 0.58 | ratio | 2025 |
| airroi | Düsseldorf (Stadt) | adr | 168.0 | USD | TTM Stand 2026 |
| airroi | Düsseldorf (Stadt) | occupancy | 0.359 | ratio | TTM Stand 2026 |
| airroi | Düsseldorf (Stadt) | booking_lead_time | 71.0 | days | TTM Stand 2026 |

Einordnung: Die Wohnung liegt in Unterbilk (Nähe Medienhafen, Bilk, Friedrichstadt). Die ADR-Werte der Nachbarviertel liegen zwischen ca. 109 EUR (Bilk) und 147 EUR (Friedrichstadt); die Altstadt liegt mit 173 EUR deutlich höher. Die Auslastungswerte der Anbieter widersprechen sich (airbtics: Median 58 %, AirROI: Ø 35,9 %) – vermutlich wegen unterschiedlicher Definitionen von "aktiven" Listings. Für Auslastungsaussagen gilt daher: **keine belastbaren Daten verfügbar**.

## 3. Comparable Listings

**Keine belastbaren Daten verfügbar.** Es wurden keine Listing-Daten erhoben: Airbnb bietet keine öffentliche API für Marktdaten, und automatisiertes Auslesen der Website verstößt gegen die Nutzungsbedingungen. Das Comp Set wird daher über `data/raw/comps/comp_listings.csv` (manuell recherchierte Listings) oder über einen lizenzierten Anbieter (AirDNA, PriceLabs, Key Data) befüllt. Das Bewertungsschema (Lage 30, Größe 20, Schlafzimmer 15, gesamte Wohnung 15, Ausstattung 20 Punkte; ≥75 = vergleichbar, 55–74 = eingeschränkt) ist implementiert.

## 4. Historische Entwicklung

**Keine belastbaren Daten verfügbar.** Öffentlich zugängliche historische Tagesdaten (ADR, Auslastung) für Düsseldorfer Kurzzeitvermietungen gibt es nicht. Inside Airbnb deckt Düsseldorf nach aktuellem Rechercheergebnis nicht ab. IT.NRW veröffentlicht monatliche Gäste- und Übernachtungszahlen (Hotellerie, Betriebe ≥10 Betten) – geeignet als Saisonindikator, nicht als Preisquelle. Sobald ein Export (z. B. AirDNA) in `data/raw/historical/market_daily.csv` liegt, schätzt `historical_data.estimate_factors` Wochentags- und Monatsfaktoren automatisch neu.

## 5. Saisonabhängigkeit

Saisonfaktoren sind **Modellannahmen** (Prior). Qualitativ gestützt durch AirROI: Peak im Oktober, Tief im Juli. Messen sind separat modelliert.

| Monat | Saisonfaktor | Normaltage von | bis | Max. inkl. Events |
|---|---|---|---|---|
| Januar | 0.88 | 99 | 119 | 149 |
| Februar | 0.92 | 99 | 129 | 189 |
| März | 1.0 | 99 | 139 | 199 |
| April | 1.02 | 109 | 139 | 179 |
| Mai | 1.05 | 109 | 139 | 179 |
| Juni | 1.03 | 109 | 139 | 189 |
| Juli | 0.92 | 99 | 119 | 189 |
| August | 0.92 | 99 | 119 | 159 |
| September | 1.05 | 109 | 139 | 179 |
| Oktober | 1.08 | 109 | 149 | 189 |
| November | 1.0 | 99 | 139 | 259 |
| Dezember | 0.95 | 99 | 109 | 179 |

## 6. Messe- und Eventanalyse

Events bekommen **keinen pauschalen Aufschlag**: Die Tier-Einstufung berücksichtigt Besucherzahl, Internationalität (Übernachtungsquote), Fach- vs. Publikumsmesse, Dauer und Wochentage. Beispiel: Der CARAVAN SALON hat zwar die meisten Besucher (269.000 im Jahr 2025), viele übernachten aber im eigenen Reisemobil oder kommen als Tagesgäste – deshalb nur Tier B. MEDICA (ca. 80.000 Fachbesucher, ca. 75 % international) sorgt dagegen erfahrungsgemäß für die stärkste Hotelverknappung – Tier S.

Die historische Preiswirkung je Event: **keine belastbaren Daten verfügbar** – die Tier-Uplifts ({'S': 1.2, 'A': 0.55, 'B': 0.25, 'C': 0.12, 'D': 0.05}) sind Priors. `historical_data.estimate_event_uplift` misst die tatsächliche Wirkung (Event-ADR vs. gleiche Wochentage ±4 Wochen ohne Event), sobald Tagesdaten vorliegen.

| Event | Start | Ende | Tier | Besucher | Distanz km | Preis min | Ø | max | Datenqualität |
|---|---|---|---|---|---|---|---|---|---|
| MEDICA + COMPAMED 2026 | 2026-11-16 | 2026-11-19 | S | 80000 | 5.8 | 259 | 259 | 259 | high |
| glasstec 2026 | 2026-10-20 | 2026-10-23 | A | 32023 | 5.8 | 189 | 189 | 189 | medium |
| ProWein 2027 | 2027-03-07 | 2027-03-09 | A | 31000 | 5.8 | 179 | 189 | 189 | high |
| GIFA / METEC / THERMPROCESS / NEWCAST 2027 | 2027-06-21 | 2027-06-25 | A |  | 5.8 | 189 | 189 | 189 | medium |
| Die Toten Hosen (Stadion) | 2027-07-10 | 2027-07-10 | A |  | 5.9 | 189 | 189 | 189 | medium |
| Silvester | 2026-12-31 | 2026-12-31 | A |  | 1.5 | 179 | 179 | 179 | high |
| Straßenkarneval (Weiberfastnacht bis Rosenmontag) | 2027-02-04 | 2027-02-08 | A |  | 1.5 | 169 | 179 | 189 | high |
| BEAUTY DÜSSELDORF + TOP HAIR 2027 | 2027-04-09 | 2027-04-11 | B |  | 5.8 | 169 | 179 | 179 | medium |
| Japan-Tag Düsseldorf/NRW 2027 | 2027-05-22 | 2027-05-22 | B |  | 1.5 | 179 | 179 | 179 | low |
| Die Toten Hosen (Stadion) | 2027-07-03 | 2027-07-04 | A |  | 5.9 | 169 | 179 | 189 | medium |
| Uniper Düsseldorf Marathon | 2027-04-18 | 2027-04-18 | C |  | 1.5 | 159 | 159 | 159 | medium |
| Die Ärzte (Konzert) | 2027-04-24 | 2027-04-24 | C |  | 6.2 | 159 | 159 | 159 | low |
| Rheinkirmes 2027 | 2027-07-16 | 2027-07-25 | B |  | 2.1 | 149 | 159 | 169 | medium |
| Sabaton (Konzert) | 2027-04-23 | 2027-04-23 | C |  | 6.2 | 149 | 149 | 149 | medium |
| CARAVAN SALON 2027 | 2027-08-27 | 2027-09-05 | B | 269000 | 5.8 | 119 | 149 | 179 | high |
| Düsseldorfer Weihnachtsmarkt 2026 | 2026-11-19 | 2026-12-30 | C |  | 1.7 | 109 | 139 | 149 | medium |
| Disney on Ice | 2027-03-05 | 2027-03-07 | D |  | 6.2 | 139 | 139 | 139 | low |
| IDS 2027 (Köln) | 2027-03-16 | 2027-03-20 | C |  | 33.2 | 129 | 139 | 149 | medium |
| Karnevalsauftakt 11.11. | 2026-11-11 | 2026-11-11 | C |  | 1.5 | 129 | 129 | 129 | high |
| boot Düsseldorf 2027 | 2027-01-23 | 2027-01-31 | B |  | 5.8 | 119 | 129 | 149 | high |
| VALVE WORLD EXPO 2026 | 2026-12-01 | 2026-12-03 | C |  | 5.8 | 119 | 119 | 119 | medium |
| EuroCIS 2027 | 2027-02-16 | 2027-02-18 | C |  | 5.8 | 119 | 119 | 119 | medium |
| gamescom 2027 (Köln) | 2027-08-25 | 2027-08-29 | C |  | 33.2 | 119 | 119 | 119 | medium |

## 7. Pricing Strategy

### Preisgrenzen

| Stufe | EUR |
|---|---|
| Minimum Price | 92 |
| Normal/Base Price | 118 |
| Target Price | 124 |
| High-Demand Price | 159 |
| Event Price | 201 |
| Maximum Price | 354 |

### Herleitung Basispreis

1. Anker-ADR Nachbarviertel: Unterbilk: 139 EUR × 0.50 + Friedrichstadt: 147 EUR × 0.20 + Bilk: 109 EUR × 0.30 = **131.6 EUR**
2. × Größenanpassung 0.95 × Qualitätsaufschlag 1.05 = 131.27 EUR (Annahmen)
3. ÷ nachfragegewichteter Ø-Index 1.1126 (die Markt-ADR enthält Wochenend- und Messenächte überproportional) = **Basis 117.98 EUR**

### Lead-Time-Strategie

Last-Minute-Rabatte gibt es **nur** bei normaler oder niedriger Nachfrage. Bei hoher Nachfrage, Spitzennachfrage oder knapper Konkurrenz (verfügbare Comps < 25%) steigt der kurzfristige Preis stattdessen.

| Vorlauf | niedrige Nachfrage | normal | hoch / knapp |
|---|---|---|---|
| Same Day | -18% | -12% | +8% |
| 1–3 Tage | -14% | -8% | +6% |
| 4–7 Tage | -10% | -5% | +4% |
| 8–14 Tage | -6% | -2% | +2% |
| 15–30 Tage | -3% | +0% | +0% |
| 31–60 Tage | +0% | +0% | +0% |
| 61–90 Tage | +0% | +2% | +5% |
| 90+ Tage | +0% | +4% | +10% |

**Langfristige Buchungen:** Mehr als 60 Tage im Voraus werden Preise leicht über dem Zielpreis angesetzt (Puffer für Messen, die erst später bekannt werden). Liegt die Buchungs-Pace unter der Erwartung, reduziert die Pace-Komponente den Preis schrittweise (max. −10 %).

### Mindestaufenthalt und Rabatte

- Standard 2 Nächte, Wochenende 2, Tier-S-Messen 3, Tage mit niedriger Nachfrage 1 (Lückenfüller).
- Preise gelten für bis zu 2 Gäste. Zusatzgast-Gebühr und Reinigungsgebühr: **keine belastbaren Daten verfügbar** (keine Comp-Erhebung) – nach der ersten Comp-Erhebung am Median des Comp Sets ausrichten.
- Wochenrabatt: 10% · Monatsrabatt: 30% (Heuristik, keine Marktbeobachtung; mit Comp-Daten überprüfen). Hinweis: Längere Aufenthalte verbrauchen das 90-Nächte-Kontingent schnell – rechtlich prüfen, ab welcher Dauer eine Vermietung nicht mehr als Kurzzeitvermietung zählt.

### 90-Nächte-Limit

Bei 90 genehmigungsfreien Nächten pro Jahr und einer angenommenen Verkaufsquote von 60% gibt das Modell je Kalenderjahr die wertvollsten Nächte frei (Spalte `Quota Recommendation`). Schattenpreis = niedrigster Preis, zu dem noch freigegeben wird: {2026: 99, 2027: 119}. Gibt es eine Genehmigung, `annual_night_cap = 0` setzen.

## 8. 12-Monats-Pricing-Kalender

Vollständiger Tageskalender: `output/pricing_calendar_12m.csv`. Auszug: die nächsten 21 Tage und die Tage mit den höchsten Preisen.

| Datum | Wochentag | Base Price | Recommended Price | Event | Event Impact | Demand Level |
|---|---|---|---|---|---|---|
| 2026-10-04 | Sonntag | 119 | 99 |  |  | normal |
| 2026-10-05 | Montag | 119 | 109 |  |  | normal |
| 2026-10-06 | Dienstag | 119 | 109 |  |  | normal |
| 2026-10-07 | Mittwoch | 119 | 109 |  |  | normal |
| 2026-10-08 | Donnerstag | 119 | 119 |  |  | erhöht |
| 2026-10-09 | Freitag | 119 | 139 |  |  | erhöht |
| 2026-10-10 | Samstag | 119 | 139 |  |  | erhöht |
| 2026-10-11 | Sonntag | 119 | 109 |  |  | normal |
| 2026-10-12 | Montag | 119 | 119 |  |  | normal |
| 2026-10-13 | Dienstag | 119 | 119 |  |  | normal |
| 2026-10-14 | Mittwoch | 119 | 119 |  |  | normal |
| 2026-10-15 | Donnerstag | 119 | 129 |  |  | erhöht |
| 2026-10-16 | Freitag | 119 | 139 |  |  | erhöht |
| 2026-10-17 | Samstag | 119 | 139 |  |  | erhöht |
| 2026-10-18 | Sonntag | 119 | 99 |  |  | niedrig |
| 2026-10-19 | Montag | 119 | 179 | glasstec 2026 | +44% (Tier A) | hoch |
| 2026-10-20 | Dienstag | 119 | 189 | glasstec 2026 | +55% (Tier A) | hoch |
| 2026-10-21 | Mittwoch | 119 | 189 | glasstec 2026 | +55% (Tier A) | hoch |
| 2026-10-22 | Donnerstag | 119 | 189 | glasstec 2026 | +55% (Tier A) | hoch |
| 2026-10-23 | Freitag | 119 | 159 | glasstec 2026 | +16% (Tier A) | hoch |
| 2026-10-24 | Samstag | 119 | 139 |  |  | erhöht |

**Top 15 Preistage:**

| Datum | Wochentag | Base Price | Recommended Price | Event | Event Impact | Demand Level | Begründung |
|---|---|---|---|---|---|---|---|
| 2026-11-16 | Montag | 119 | 259 | MEDICA + COMPAMED 2026 | +120% (Tier S) | Spitze | Saison 1.00; Wochentag 1.00; Event: MEDICA + COMPAMED 2026 (+120%); Nachfrageindex 2.20 |
| 2026-11-17 | Dienstag | 119 | 259 | MEDICA + COMPAMED 2026 | +120% (Tier S) | Spitze | Saison 1.00; Wochentag 1.00; Event: MEDICA + COMPAMED 2026 (+120%); Nachfrageindex 2.20 |
| 2026-11-18 | Mittwoch | 119 | 259 | MEDICA + COMPAMED 2026 | +120% (Tier S) | Spitze | Saison 1.00; Wochentag 1.00; Event: MEDICA + COMPAMED 2026 (+120%); Nachfrageindex 2.20 |
| 2026-11-15 | Sonntag | 119 | 229 | MEDICA + COMPAMED 2026 | +96% (Tier S) | Spitze | Saison 1.00; Wochentag 1.00; Event: MEDICA + COMPAMED 2026 (+96%); Nachfrageindex 1.96 |
| 2027-03-06 | Samstag | 119 | 219 | ProWein 2027 + Disney on Ice | +47% (Tier A) | hoch | Saison 1.00; Wochentag 1.15; Event: ProWein 2027 + Disney on Ice (+47%); Nachfrageindex 1.68; Vorlauf 153 T (+10%, Modus high) |
| 2027-02-05 | Freitag | 119 | 209 | Straßenkarneval (Weiberfastnacht bis Rosenmontag) | +55% (Tier A) | hoch | Saison 0.92; Wochentag 1.12; Event: Straßenkarneval (Weiberfastnacht bis Rosenmontag) (+55%); Nachfrageindex 1.60; Vorlauf 124 T (+10%, Modus high) |
| 2027-02-06 | Samstag | 119 | 209 | Straßenkarneval (Weiberfastnacht bis Rosenmontag) | +55% (Tier A) | hoch | Saison 0.92; Wochentag 1.15; Event: Straßenkarneval (Weiberfastnacht bis Rosenmontag) (+55%); Nachfrageindex 1.64; Vorlauf 125 T (+10%, Modus high) |
| 2027-03-07 | Sonntag | 119 | 209 | ProWein 2027 + Disney on Ice | +58% (Tier A) | hoch | Saison 1.00; Wochentag 1.00; Event: ProWein 2027 + Disney on Ice (+58%); Nachfrageindex 1.57; Vorlauf 154 T (+10%, Modus high) |
| 2027-06-21 | Montag | 119 | 209 | GIFA / METEC / THERMPROCESS / NEWCAST 2027 | +55% (Tier A) | hoch | Saison 1.03; Wochentag 1.00; Event: GIFA / METEC / THERMPROCESS / NEWCAST 2027 (+55%); Nachfrageindex 1.60; Vorlauf 260 T (+10%, Modus high) |
| 2027-06-22 | Dienstag | 119 | 209 | GIFA / METEC / THERMPROCESS / NEWCAST 2027 | +55% (Tier A) | hoch | Saison 1.03; Wochentag 1.00; Event: GIFA / METEC / THERMPROCESS / NEWCAST 2027 (+55%); Nachfrageindex 1.60; Vorlauf 261 T (+10%, Modus high) |
| 2027-06-23 | Mittwoch | 119 | 209 | GIFA / METEC / THERMPROCESS / NEWCAST 2027 | +55% (Tier A) | hoch | Saison 1.03; Wochentag 1.00; Event: GIFA / METEC / THERMPROCESS / NEWCAST 2027 (+55%); Nachfrageindex 1.60; Vorlauf 262 T (+10%, Modus high) |
| 2027-06-24 | Donnerstag | 119 | 209 | GIFA / METEC / THERMPROCESS / NEWCAST 2027 | +55% (Tier A) | hoch | Saison 1.03; Wochentag 1.00; Event: GIFA / METEC / THERMPROCESS / NEWCAST 2027 (+55%); Nachfrageindex 1.60; Vorlauf 263 T (+10%, Modus high) |
| 2027-07-03 | Samstag | 119 | 209 | Die Toten Hosen (Stadion) | +55% (Tier A) | hoch | Saison 0.92; Wochentag 1.15; Event: Die Toten Hosen (Stadion) (+55%); Nachfrageindex 1.64; Vorlauf 272 T (+10%, Modus high) |
| 2027-07-10 | Samstag | 119 | 209 | Die Toten Hosen (Stadion) | +55% (Tier A) | hoch | Saison 0.92; Wochentag 1.15; Event: Die Toten Hosen (Stadion) (+55%); Nachfrageindex 1.64; Vorlauf 279 T (+10%, Modus high) |
| 2027-03-08 | Montag | 119 | 199 | ProWein 2027 | +55% (Tier A) | hoch | Saison 1.00; Wochentag 1.00; Event: ProWein 2027 (+55%); Nachfrageindex 1.55; Vorlauf 155 T (+10%, Modus high) |

## 9. Datenqualität

| Aussage | Datenklasse | Belastbarkeit |
|---|---|---|
| Messetermine (MEDICA, boot, ProWein, CARAVAN SALON, EuroCIS, glasstec) | 1/2 – offizielle Seiten via Suche | hoch |
| Feiertage NRW, Schulferien NRW | 1 – Kalenderregel / Kultusministerium via Sekundärquelle | hoch |
| Konzert- und Festtermine | 2 – Sekundärquellen | mittel bis niedrig (Japan-Tag widersprüchlich) |
| Viertel-ADR / Auslastung | 2 – externe Anbieter, nur Snippets | niedrig |
| Basispreis | 3 – abgeleitete Schätzung | mittel/niedrig |
| Wochentags-, Saison-, Event-Faktoren | 4 – Modellannahmen | niedrig bis zur Kalibrierung |
| Comp-Set-Preise, Gebühren, Rabatte der Konkurrenz | – | keine belastbaren Daten verfügbar |
| Realisierte Buchungspreise | – | keine belastbaren Daten verfügbar |
| Historische Event-Wirkung | – | keine belastbaren Daten verfügbar |

Validierung (Phase 11): **nicht durchführbar – keine historischen Tagesdaten.** Das Backtest-Modul (`validation.py`) ist bereit und vergleicht Modellpreise mit Markt-ADR (MAPE, Bias an Normal- vs. Eventtagen, Rangkorrelation).

Nächste Schritte zur Erhöhung der Belastbarkeit: siehe `docs/PLAN.md`, Abschnitt Implementierungsplan.
