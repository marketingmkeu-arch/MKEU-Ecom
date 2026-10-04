# Datenquellen – Bewertung und Status

Stand der Recherche: 04.10.2026. Datenklassen: **1** = direkt beobachtet · **2** = externer Anbieter ·
**3** = abgeleitete Schätzung · **4** = Modellannahme.

> Einschränkung dieser Recherche: Aus der Ausführungsumgebung waren nur Websuchen möglich. Direkte
> Seitenabrufe (insideairbnb.com, airbtics.com, guestfavorites.com, messen.de, messe-duesseldorf.de,
> opendata.duesseldorf.de, it.nrw) wurden vom Netzwerk-Proxy blockiert. Alle Werte aus diesen Quellen
> stammen daher aus Such-Snippets und müssen vor wichtigen Entscheidungen auf der Originalseite geprüft
> werden.

## A. Kurzzeitvermietungs-Marktdaten

| Quelle | URL / API | Daten | Aktualisierung | Historie | Zuverlässigkeit | Kosten | Einschränkungen | Status |
|---|---|---|---|---|---|---|---|---|
| **Airbnb** | – | Listings, Kalender, Preise | – | – | – | – | **Keine öffentliche Markt-API.** Die Partner-API ist nur für eigene Listings (Channel Manager). Automatisiertes Auslesen der Website verstößt gegen die AGB → wird **nicht** gemacht. | nicht nutzbar |
| **Inside Airbnb** | insideairbnb.com/get-the-data | Listing-Snapshots, Kalender, Reviews (CC BY 4.0) | quartalsweise | ab ca. 2015 | gut (dokumentierte Methodik) | kostenlos | **Düsseldorf laut Recherche nicht abgedeckt** (Seite selbst im Container blockiert; vor Ausschluss manuell prüfen). | prüfen |
| **AirDNA** | airdna.co (MarketMinder, API) | Tages-ADR, Auslastung, RevPAR, Pacing, Comp Sets je Listing | täglich/wöchentlich | ab ca. 2014 | hoch, Industriestandard; geschätzte Belegung | kostenpflichtig (Preis vor Kauf prüfen; nicht recherchiert) | AGB-konforme Exporte; Belegung modelliert, nicht gemessen | **empfohlen für Phase 3/11** |
| **PriceLabs Market Dashboard** | pricelabs.co | Marktpreise und Auslastung, Pacing nach Lead Time, Nachbar-Listings | täglich | ca. 1–2 Jahre | hoch | kostenpflichtig, vergleichsweise günstig (Preis nicht recherchiert) | Anbieter für Dynamic Pricing; Daten nur über die Oberfläche bzw. CSV-Export | empfohlen (günstig) |
| **Key Data Dashboard** | keydatadashboard.com | Ist-Buchungsdaten von Property Managern (realisierte ADR) | täglich | mehrjährig | hoch (echte Buchungen), dünn in DE | Abo | Abdeckung Düsseldorf unklar | prüfen |
| **AirROI** | airroi.com | ADR, Auslastung, Saisonmuster, API | laufend | TTM | mittel | Free-Tier + API | Werte in USD; Methodik nur teilweise offen | Snippet genutzt |
| **airbtics** | airbtics.com | ADR, Auslastung, Umsatz je Stadt/Viertel | laufend | 12 Monate | mittel | Free/Abo | Median-Definition | Snippet genutzt |
| **guestfavorites** | guestfavorites.com | ADR/Auslastung je Viertel | monatlich | unklar | niedrig–mittel | kostenlos | Methodik unbekannt | Snippet genutzt (Anker-ADR) |

**Folgerung:** Für belastbare historische Tagesdaten (Phase 3 und 11) ist ein lizenzierter Anbieter nötig
(AirDNA oder PriceLabs). Kostenlose Quellen liefern nur Jahres- bzw. Viertelsaggregate.

## B. Comp Set / angebotene Preise

| Weg | Daten | Rechtlich | Aufwand | Empfehlung |
|---|---|---|---|---|
| Manuelle Recherche auf Airbnb/Booking (Mensch im Browser) | 15–30 Listings: Größe, Ausstattung, Preis für feste Testdaten | zulässig (normale Nutzung) | ca. 2 h Ersterfassung, 30 min/Woche Snapshots | **sofort umsetzbar** → `data/raw/comps/*.csv` |
| AirDNA/PriceLabs Comp Set | Listing-Kalender, Preise, Belegung | lizenziert | gering | mittelfristig |
| Eigenes Airbnb-Konto (Channel-Manager-API, z. B. Smoobu, Hostaway) | eigene Buchungen, Pace, realisierte Preise | zulässig | gering | **wichtigste Quelle für realisierte Preise** |

Alle Snapshot-Preise sind **angebotene** Preise. Ein angebotener Preis wird nie als gezahlt behandelt.

## C. Nachfrage, Statistik, Kalender

| Quelle | URL | Daten | Aktualisierung | Historie | Zuverlässigkeit | Kosten | Nutzung |
|---|---|---|---|---|---|---|---|
| IT.NRW Beherbergungsstatistik | it.nrw / webshop.it.nrw.de, GENESIS-Datenbank landesdatenbank.nrw.de (Tabelle 45412) | Monatliche Gäste und Übernachtungen je Gemeinde (Betriebe ≥10 Betten) | monatlich, ca. 2 Monate Verzug | ab 1990er | hoch (amtlich) | kostenlos, GENESIS-API mit Registrierung | Saisonindikator (Monatsfaktoren); keine Preise, keine Airbnb-Abdeckung |
| Destatis GENESIS | www-genesis.destatis.de | Bundesvergleich Beherbergung | monatlich | lang | hoch | kostenlos | Plausibilisierung |
| Open Data Düsseldorf | opendata.duesseldorf.de | Veranstaltungen, Tourismus (Datensätze prüfen) | unregelmäßig | variabel | mittel | kostenlos | Eventkalender ergänzen |
| Messe Düsseldorf | messe-duesseldorf.de (Messekalender) | Messetermine, Abschlussberichte mit Besucherzahlen | laufend | Archiv | **hoch** | kostenlos | Event-Kalender (Tier, Besucher) |
| Koelnmesse | koelnmesse.com/current-dates | Messetermine Köln | laufend | – | hoch | kostenlos | Überlaufeffekte |
| visitduesseldorf.de | Veranstaltungskalender | Feste, Karneval, Konzerte | laufend | – | mittel–hoch | kostenlos | Event-Kalender |
| Ticketing-Seiten (Eventim, Ticketmaster), Venues (Merkur Spiel-Arena, PSD Bank Dome) | – | Konzerttermine | laufend | – | mittel | kostenlos | Konzerte (manuell) |
| Schulferien | Schulministerium NRW (schulministerium.nrw), KMK | Ferientermine | jährlich | – | hoch | kostenlos | Kalenderfaktor |
| Feiertage | gesetzlich (Feiertagsgesetz NW) | – | – | – | hoch | – | im Code berechnet (Osterformel) |

## D. Regulierung (preisrelevant)

- **Wohnraumschutzsatzung Düsseldorf / Wohnraumstärkungsgesetz NRW:** Kurzzeitvermietung von Wohnraum
  ist ohne Genehmigung **max. 90 Tage pro Kalenderjahr** zulässig; vorher ist eine **Wohnraum-ID**
  zu beantragen und in jedem Inserat anzugeben; ein Buchungskalender ist zu führen. Darüber hinaus ist
  eine Zweckentfremdungsgenehmigung nötig (Gebühr 500–2.500 EUR), Verstöße bis 500.000 EUR Bußgeld.
  Quellen: land.nrw (Pressemitteilung Wohnraum-ID), bauportal.nrw (Satzung Düsseldorf 10.03.2022).
  → Im Modell: `regulation.annual_night_cap`. **Bitte den eigenen Status prüfen** (Genehmigung ja/nein).

## E. In diesem Lauf verwendete Datenpunkte

- `data/raw/market/market_aggregates.csv` – jede Zeile mit Anbieter, URL, Abrufdatum, Datenklasse, Konfidenz
- `data/raw/events/events.csv` – jedes Event mit Quelle, Quellentyp und Konfidenz
- `data/raw/calendar/school_holidays_nrw.csv`
