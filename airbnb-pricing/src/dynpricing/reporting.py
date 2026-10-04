"""Ausgaben: Pricing-Kalender (CSV), Strategie (JSON) und Report (Markdown)."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .historical_data import MONTH_KEYS
from .pipeline import RunResult, median_price
from datetime import date

from .pricing_engine import DayPrice, german_weekday, round_price
from .revenue import airbnb_nightly_price, all_forecasts, compare_windows, payout

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
             "September", "Oktober", "November", "Dezember"]

CALENDAR_COLUMNS = [
    "Datum", "Wochentag", "Base Price", "Recommended Price", "Event", "Event Impact",
    "Demand Level", "Begründung", "Demand Index", "Min Nights", "Price Band",
    "Lead-Time Factor", "Quota Priority", "Quota Recommendation", "Airbnb Nightly Price",
]


def _r(result: RunResult, p: float) -> int:
    return round_price(p, result.cfg["output"].get("round_to_nine", False), floor=result.bands.minimum)


def calendar_rows(result: RunResult) -> list[dict]:
    rows = []
    for p in result.prices:
        d = p.demand
        rows.append({
            "Datum": d.day.isoformat(),
            "Wochentag": german_weekday(d.day),
            "Base Price": _r(result, p.base),
            "Recommended Price": p.recommended,
            "Event": d.event.names,
            "Event Impact": f"{d.event.uplift:+.0%} (Tier {d.event.max_tier})" if d.event.max_tier else "",
            "Demand Level": d.level,
            "Begründung": "; ".join(p.reasons),
            "Demand Index": f"{d.index:.3f}",
            "Min Nights": p.min_nights,
            "Price Band": p.band,
            "Lead-Time Factor": f"{p.lead_time_factor:.2f}",
            "Quota Priority": p.quota_priority or "",
            "Quota Recommendation": p.quota_recommendation,
            "Airbnb Nightly Price": airbnb_nightly_price(p, result.cfg),
        })
    return rows


def write_calendar_csv(result: RunResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CALENDAR_COLUMNS)
        w.writeheader()
        w.writerows(calendar_rows(result))


def _is_plain(p: DayPrice) -> bool:
    d = p.demand
    return not d.event.max_tier and not d.holiday_label


def event_price_table(result: RunResult) -> list[dict]:
    by_event: dict[str, list[DayPrice]] = defaultdict(list)
    for p in result.prices:
        contribs = p.demand.event.contributions
        # Preis nur dem dominanten Event zuordnen; nur volle Eventnächte (ohne An-/Abreise)
        if contribs and contribs[0][1] >= result.cfg["events"]["tier_uplift"][contribs[0][0].impact_tier] * 0.99:
            by_event[contribs[0][0].event_id].append(p)
    rows = []
    for ev in result.events:
        ps = by_event.get(ev.event_id)
        if not ps:
            continue
        static = [p.static_price for p in ps]
        rows.append({
            "event": ev.name,
            "start": ev.start.isoformat(),
            "end": ev.end.isoformat(),
            "tier": ev.impact_tier,
            "visitors": ev.expected_visitors,
            "distance_km": round(ev.distance_km(result.cfg["property"]["lat"], result.cfg["property"]["lon"]), 1),
            "price_min": _r(result, min(static)),
            "price_avg": _r(result, statistics.mean(static)),
            "price_max": _r(result, max(static)),
            "confidence": ev.confidence,
        })
    return sorted(rows, key=lambda r: r["price_avg"], reverse=True)


def strategy(result: RunResult) -> dict:
    prices, cfg, bands = result.prices, result.cfg, result.bands
    weekday_normal = median_price(prices, lambda p: _is_plain(p) and p.demand.day.weekday() in (0, 1, 2, 3))
    weekend_normal = median_price(prices, lambda p: _is_plain(p) and p.demand.day.weekday() in (4, 5))
    seasonal = {}
    for m in range(1, 13):
        plain = [p.static_price for p in prices if p.demand.day.month == m and _is_plain(p)]
        allp = [p.static_price for p in prices if p.demand.day.month == m]
        if allp:
            seasonal[MONTHS_DE[m - 1]] = {
                "normal_min": _r(result, min(plain)) if plain else None,
                "normal_max": _r(result, max(plain)) if plain else None,
                "inkl_events_max": _r(result, max(allp)),
                "saisonfaktor": cfg["season"][MONTH_KEYS[m - 1]],
            }
    los = cfg["length_of_stay"]
    cap = cfg["regulation"].get("annual_night_cap", 0)
    cap_los = los.get("night_cap", {}) if cap else {}
    released = defaultdict(int)
    for p in prices:
        if p.quota_recommendation == "freigeben":
            released[p.demand.day.year] += 1
    return {
        "as_of": result.as_of.isoformat(),
        # Preisgrenzen ungerundet auf 9er-Endung, damit die Stufen unterscheidbar bleiben
        "basispreis": round(bands.base),
        "preisgrenzen": {k: round(v) for k, v in bands.as_dict().items()},
        "normaler_wochentagspreis_mo_do": _r(result, weekday_normal) if weekday_normal else None,
        "normaler_wochenendpreis_fr_sa": _r(result, weekend_normal) if weekend_normal else None,
        "saisonale_preisbereiche": seasonal,
        "messe_und_eventpreise": event_price_table(result),
        "mindestaufenthalt": {
            "standard": los["default_min_nights"], "wochenende": los["weekend_min_nights"],
            "events": los["event_min_nights"], "niedrige_nachfrage": los["low_demand_min_nights"],
        },
        "wochenrabatt": cap_los.get("weekly_discount", los["weekly_discount"]),
        "monatsrabatt": cap_los.get("monthly_discount", los["monthly_discount"]),
        "max_aufenthalt": cap_los.get("max_nights"),
        "freigegebene_naechte_je_jahr": dict(released),
        "lead_time_tabelle": cfg["lead_time"]["buckets"],
        "nacht_limit": cfg["regulation"].get("annual_night_cap", 0),
        "schattenpreis_je_jahr": result.shadow_prices,
        "basisherleitung": {
            "anker_adr": round(result.derivation.anchor_adr, 2),
            "anker_schritte": result.derivation.anchor_steps,
            "angepasste_anker_adr": round(result.derivation.adjusted_anchor, 2),
            "nachfragegewichteter_index": round(result.derivation.demand_weighted_index, 4),
            "basis": round(result.derivation.base, 2),
            "marktbasis": round(result.derivation.market_base, 2),
            "comp_basis": round(result.derivation.comp_base, 2) if result.derivation.comp_base else None,
            "comp_listings": result.derivation.comp_n,
            "comp_gewicht": result.derivation.comp_weight,
            "startrabatt_faktor": result.derivation.launch_factor,
        },
    }


def write_strategy_json(result: RunResult, path: Path) -> dict:
    s = strategy(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


def _md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def write_report(result: RunResult, s: dict, path: Path) -> None:
    cfg, b = result.cfg, s["preisgrenzen"]
    d = s["basisherleitung"]
    cap = s["nacht_limit"]
    comps_ok = [c for c in result.comps if c.comp_class == "vergleichbar"]
    lines: list[str] = []
    add = lines.append

    add(f"# Pricing-Report {cfg['property']['name']}, Düsseldorf")
    add("")
    add(f"_Automatisch erzeugt am {result.as_of.isoformat()} durch `dynpricing`. Kalenderzeitraum: "
        f"{result.prices[0].demand.day} bis {result.prices[-1].demand.day}._")
    add("")
    add("> **Hinweis zur Datenlage:** Für diese Version liegen keine Preise einzelner Vergleichs-Listings, "
        "keine historischen Tagesdaten und keine eigenen Buchungsdaten vor. Basispreis und Faktoren beruhen "
        "auf Marktaggregaten externer Anbieter (nur aus Such-Snippets gelesen) und auf markierten "
        "Modellannahmen. Die Zahlen sind ein begründeter Startpunkt, aber keine Marktmessung.")
    add("")

    add("## 1. Executive Summary")
    add("")
    add("> Alle Preise sind **Gastpreise pro Nacht inkl. aller Gebühren** (so zeigt Airbnb die Konkurrenz an). "
        "Den eigenen Preis in Airbnb so einstellen, dass die Gastansicht diesen Wert zeigt.")
    add("")
    add(f"- **Realistischer Normalpreis (Basis, Di ohne Event):** ca. **{s['basispreis']} EUR**")
    add(f"- **Normaler Wochentag (Mo–Do, Median):** {s['normaler_wochentagspreis_mo_do']} EUR · "
        f"**Normales Wochenende (Fr/Sa, Median):** {s['normaler_wochenendpreis_fr_sa']} EUR")
    add(f"- **Minimum Price:** {b['Minimum Price']} EUR · **Maximum Price:** {b['Maximum Price']} EUR")
    top = s["messe_und_eventpreise"][:3]
    if top:
        add("- **Stärkste Nachfragetreiber im Zeitraum:** " + "; ".join(
            f"{e['event']} (Ø {e['price_avg']} EUR, bis {e['price_max']} EUR)" for e in top))
    if cap:
        add(f"- **Regulierung:** Ohne Zweckentfremdungsgenehmigung sind in Düsseldorf höchstens **{cap} Nächte "
            "pro Kalenderjahr** Kurzzeitvermietung erlaubt (Wohnraum-ID nötig). Die Strategie sollte deshalb "
            "die wertvollsten Nächte priorisieren (Messen, Wochenenden, Oktober) und keine Nacht unter dem "
            f"Schattenpreis ({s['schattenpreis_je_jahr']} EUR) verkaufen – siehe Abschnitt 7.")
    add("")

    add("## 2. Marktanalyse")
    add("")
    add("Externe Marktaggregate (Datenklasse 2, Anbieter; **nicht verifiziert**, Methodik der Anbieter unbekannt):")
    add("")
    add(_md_table(
        ["Anbieter", "Gebiet", "Kennzahl", "Wert", "Einheit", "Zeitraum"],
        [[m.provider, m.geography, m.metric, m.value, m.unit, m.period] for m in result.metrics],
    ))
    add("")
    add("Einordnung: Die Wohnung liegt in Unterbilk (Nähe Medienhafen, Bilk, Friedrichstadt). Die ADR-Werte "
        "der Nachbarviertel liegen zwischen ca. 109 EUR (Bilk) und 147 EUR (Friedrichstadt); die Altstadt "
        "liegt mit 173 EUR deutlich höher. Die Auslastungswerte der Anbieter widersprechen sich "
        "(airbtics: Median 58 %, AirROI: Ø 35,9 %) – vermutlich wegen unterschiedlicher Definitionen von "
        "\"aktiven\" Listings. Für Auslastungsaussagen gilt daher: **keine belastbaren Daten verfügbar**.")
    add("")

    add("## 3. Comparable Listings")
    add("")
    if result.comps:
        cb = result.comp_base
        add(_md_table(
            ["Listing", "Viertel", "Distanz km", "Bewertung", "Score", "Klasse", "Normaltag-Äquivalent EUR"],
            [[c.listing_id, c.neighbourhood, round(c.distance_km, 2) if c.distance_km is not None else "unbekannt",
              f"{c.rating} ({c.reviews_count:.0f})" if c.rating else "–", c.score, c.comp_class,
              round(cb.normalized[c.listing_id]) if cb and c.listing_id in cb.normalized else "–"]
             for c in result.comps],
        ))
        add("")
        add("Datenklasse 1 (direkt beobachtet): **angebotene** Preise aus Airbnb-Suchen, keine gezahlten Preise. "
            "„Normaltag-Äquivalent“ = angebotener Preis ÷ Nachfrageindex des Aufenthaltstags. Ohne Koordinaten "
            "gilt ein Listing höchstens als eingeschränkt vergleichbar.")
        if cb:
            add("")
            add(f"Median-Normaltag über {cb.n_listings} Listings ({cb.n_observations} Beobachtungen): "
                f"**{cb.value:.0f} EUR**. Einschränkungen: wenige Listings, nur ein Reisedatum, Lage und Größe "
                "teils unbekannt, „Gesamtpreis“ enthält je nach Listing Reinigung/Gebühren, mehrere Preise "
                "waren bereits rabattiert.")
    else:
        add("**Keine belastbaren Daten verfügbar.** Es wurden keine Listing-Daten erhoben: Airbnb bietet keine "
            "öffentliche API für Marktdaten, und automatisiertes Auslesen der Website verstößt gegen die "
            "Nutzungsbedingungen. Das Comp Set wird daher über `data/raw/comps/comp_listings.csv` "
            "(manuell recherchierte Listings) oder über einen lizenzierten Anbieter (AirDNA, PriceLabs, "
            "Key Data) befüllt. Das Bewertungsschema (Lage 30, Größe 20, Schlafzimmer 15, gesamte Wohnung 15, "
            "Ausstattung 20 Punkte; ≥75 = vergleichbar, 55–74 = eingeschränkt) ist implementiert.")
    add("")

    add("## 4. Historische Entwicklung")
    add("")
    if result.history:
        add(f"{len(result.history)} historische Tagesbeobachtungen geladen.")
    else:
        add("**Keine belastbaren Daten verfügbar.** Öffentlich zugängliche historische Tagesdaten (ADR, "
            "Auslastung) für Düsseldorfer Kurzzeitvermietungen gibt es nicht. Inside Airbnb deckt Düsseldorf "
            "nach aktuellem Rechercheergebnis nicht ab. IT.NRW veröffentlicht monatliche Gäste- und "
            "Übernachtungszahlen (Hotellerie, Betriebe ≥10 Betten) – geeignet als Saisonindikator, nicht als Preisquelle. "
            "Sobald ein Export (z. B. AirDNA) in `data/raw/historical/market_daily.csv` liegt, schätzt "
            "`historical_data.estimate_factors` Wochentags- und Monatsfaktoren automatisch neu.")
    add("")

    add("## 5. Saisonabhängigkeit")
    add("")
    add("Saisonfaktoren sind **Modellannahmen** (Prior). Qualitativ gestützt durch AirROI: Peak im Oktober, "
        "Tief im Juli. Messen sind separat modelliert.")
    add("")
    add(_md_table(
        ["Monat", "Saisonfaktor", "Normaltage von", "bis", "Max. inkl. Events"],
        [[m, v["saisonfaktor"], v["normal_min"], v["normal_max"], v["inkl_events_max"]]
         for m, v in s["saisonale_preisbereiche"].items()],
    ))
    add("")

    add("## 6. Messe- und Eventanalyse")
    add("")
    add("Events bekommen **keinen pauschalen Aufschlag**: Die Tier-Einstufung berücksichtigt Besucherzahl, "
        "Internationalität (Übernachtungsquote), Fach- vs. Publikumsmesse, Dauer und Wochentage. Beispiel: "
        "Der CARAVAN SALON hat zwar die meisten Besucher (269.000 im Jahr 2025), viele übernachten aber im "
        "eigenen Reisemobil oder kommen als Tagesgäste – deshalb nur Tier B. MEDICA (ca. 80.000 Fachbesucher, "
        "ca. 75 % international) sorgt dagegen erfahrungsgemäß für die stärkste Hotelverknappung – Tier S.")
    add("")
    add("Die historische Preiswirkung je Event: **keine belastbaren Daten verfügbar** – die Tier-Uplifts "
        f"({cfg['events']['tier_uplift']}) sind Priors. `historical_data.estimate_event_uplift` misst die tatsächliche "
        "Wirkung (Event-ADR vs. gleiche Wochentage ±4 Wochen ohne Event), sobald Tagesdaten vorliegen.")
    add("")
    add(_md_table(
        ["Event", "Start", "Ende", "Tier", "Besucher", "Distanz km", "Preis min", "Ø", "max", "Datenqualität"],
        [[e["event"], e["start"], e["end"], e["tier"], e["visitors"], e["distance_km"], e["price_min"],
          e["price_avg"], e["price_max"], e["confidence"]] for e in s["messe_und_eventpreise"]],
    ))
    add("")

    add("## 7. Pricing Strategy")
    add("")
    add("### Preisgrenzen")
    add("")
    add(_md_table(["Stufe", "EUR"], [[k, v] for k, v in b.items()]))
    add("")
    add("### Herleitung Basispreis")
    add("")
    add(f"1. Anker-ADR Nachbarviertel: {' + '.join(d['anker_schritte'])} = **{d['anker_adr']} EUR**")
    add(f"2. × Größenanpassung {cfg['market_anchor']['unit_size_adjustment']} × Qualitätsaufschlag "
        f"{cfg['market_anchor']['quality_premium']} = {d['angepasste_anker_adr']} EUR (Annahmen)")
    add(f"3. ÷ nachfragegewichteter Ø-Index {d['nachfragegewichteter_index']} (die Markt-ADR enthält "
        f"Wochenend- und Messenächte überproportional) = Marktbasis {d['marktbasis']} EUR")
    if d["comp_basis"]:
        add(f"4. Mischung mit beobachteter Comp-Basis {d['comp_basis']} EUR × Positionierung "
            f"{cfg['competition']['position_vs_median']} (Gewicht {d['comp_gewicht']:.0%} bei {d['comp_listings']} Listings)")
    add(f"= **Basis {d['basis']} EUR**")
    if d["startrabatt_faktor"] != 1.0:
        add("")
        add(f"Startrabatt: Solange das Listing neu ist (bis ca. {cfg['launch']['until_reviews']} Bewertungen), werden "
            f"Tage mit niedriger bis erhöhter Nachfrage um {1 - d['startrabatt_faktor']:.0%} günstiger angeboten. "
            "Messe- und Spitzentage sind ausgenommen. Danach `launch.active = false` setzen.")
    add("")
    add("### Lead-Time-Strategie")
    add("")
    add("Last-Minute-Rabatte gibt es **nur** bei normaler oder niedriger Nachfrage. Bei hoher Nachfrage, "
        "Spitzennachfrage oder knapper Konkurrenz (verfügbare Comps < "
        f"{cfg['lead_time']['scarcity_availability_threshold']:.0%}) steigt der kurzfristige Preis stattdessen.")
    add("")
    labels = ["Same Day", "1–3 Tage", "4–7 Tage", "8–14 Tage", "15–30 Tage", "31–60 Tage", "61–90 Tage", "90+ Tage"]
    add(_md_table(
        ["Vorlauf", "niedrige Nachfrage", "normal", "hoch / knapp"],
        [[lab, f"{bk['low'] - 1:+.0%}", f"{bk['normal'] - 1:+.0%}", f"{bk['high'] - 1:+.0%}"]
         for lab, bk in zip(labels, s["lead_time_tabelle"])],
    ))
    add("")
    add("**Langfristige Buchungen:** Mehr als 60 Tage im Voraus werden Preise leicht über dem Zielpreis angesetzt "
        "(Puffer für Messen, die erst später bekannt werden). Liegt die Buchungs-Pace unter der Erwartung, "
        "reduziert die Pace-Komponente den Preis schrittweise (max. −10 %).")
    add("")
    add("### Mindestaufenthalt und Rabatte")
    add("")
    m = s["mindestaufenthalt"]
    add(f"- Standard {m['standard']} Nächte, Wochenende {m['wochenende']}, Tier-S-Messen {m['events']['S']}, "
        f"Tage mit niedriger Nachfrage {m['niedrige_nachfrage']} (Lückenfüller).")
    add("- Preise gelten für bis zu 2 Gäste. Zusatzgast-Gebühr und Reinigungsgebühr: **keine belastbaren "
        "Daten verfügbar** (keine Comp-Erhebung) – nach der ersten Comp-Erhebung am Median des Comp Sets ausrichten.")
    if cap:
        add(f"- Wochenrabatt: {s['wochenrabatt']:.0%} · **kein Monatsrabatt** · maximaler Aufenthalt "
            f"{s['max_aufenthalt']} Nächte. Grund: Ein rabattierter Langaufenthalt verbraucht das 90-Nächte-"
            "Kontingent zu niedrigen Preisen (z. B. 30 Nächte mit 30 % Rabatt = ein Drittel des Jahreskontingents). "
            "Längere Anfragen nur annehmen, wenn der Nachtpreis über dem Schattenpreis liegt.")
    else:
        add(f"- Wochenrabatt: {s['wochenrabatt']:.0%} · Monatsrabatt: {s['monatsrabatt']:.0%} "
            "(Heuristik, keine Marktbeobachtung; mit Comp-Daten überprüfen).")
    add("")
    if cap:
        reg = cfg["regulation"]
        add("### 90-Nächte-Limit (ohne Zweckentfremdungsgenehmigung)")
        add("")
        add(f"Erlaubt sind {cap} Nächte pro Kalenderjahr (Wohnraum-ID im Inserat, Buchungskalender führen). "
            "Ziel ist deshalb nicht maximale Auslastung, sondern **maximaler Erlös pro verbrauchter Nacht**.")
        add("")
        add(f"- Bei einer angenommenen Verkaufsquote von {reg['assumed_sell_through']:.0%} werden je Jahr die "
            f"wertvollsten Nächte freigegeben: {s['freigegebene_naechte_je_jahr']} (Spalte `Quota Recommendation`).")
        if s["schattenpreis_je_jahr"]:
            add(f"- **Schattenpreis** je Jahr: {s['schattenpreis_je_jahr']} EUR. Alle anderen Nächte bleiben buchbar, "
                "aber nie unter diesem Preis – eine billig verkaufte Nacht fehlt später bei einer Messe.")
        else:
            add("- Im aktuellen Zeitraum reicht das Kontingent für alle freigegebenen Nächte; kein Schattenpreis nötig.")
        add("- Genutzte Nächte laufend in `regulation.nights_already_used` eintragen; der nächste Lauf verteilt "
            "das Restkontingent neu.")
        add("- Hartes Limit beachten: Bei 90 gebuchten Nächten im Kalenderjahr den Kalender für den Rest des Jahres schließen.")
        add("")

    rev = revenue_summary(result)
    add("### Umsatz- und Auszahlungsprognose")
    add("")
    add("Erwartungswert-Rechnung: Buchungswahrscheinlichkeit je Nacht nach Nachfragestufe "
        f"({cfg['revenue']['booking_probability']}, ANNAHME) × Gastpreis, begrenzt auf das 90-Nächte-Kontingent "
        f"je Kalenderjahr und die Vermietungsfenster {cfg['regulation'].get('rental_windows')}. "
        f"Auszahlung = Gastpreis × {rev['payout_ratio']} (aus den ersten echten Buchungen abgeleitet).")
    add("")
    add(_md_table(["Szenario", "Nächte je Jahr", "Gastumsatz EUR", "Auszahlung EUR"],
                  [[k, v["naechte_je_jahr"], v["brutto_gast"], v["auszahlung"]] for k, v in rev["szenarien"].items()]))
    add("")
    add("Vergleich der Vermietungsfenster 2027 (realistisches Szenario):")
    add("")
    add(_md_table(["Fenster", "erwartete Nächte", "Ø Gastpreis", "Auszahlung EUR"],
                  [[k, v["naechte"], v["adr"], v["auszahlung"]] for k, v in rev["vergleich_2027"].items()]))
    add("")

    add("## 8. 12-Monats-Pricing-Kalender")
    add("")
    add("Vollständiger Tageskalender: `output/pricing_calendar_12m.csv`. Auszug: die nächsten 21 Tage und die "
        "Tage mit den höchsten Preisen.")
    add("")
    rows = calendar_rows(result)
    head = ["Datum", "Wochentag", "Base Price", "Recommended Price", "Event", "Event Impact", "Demand Level"]
    add(_md_table(head, [[r[h] for h in head] for r in rows[:21]]))
    add("")
    add("**Top 15 Preistage:**")
    add("")
    top_rows = sorted(rows, key=lambda r: r["Recommended Price"], reverse=True)[:15]
    add(_md_table(head + ["Begründung"], [[r[h] for h in head + ["Begründung"]] for r in top_rows]))
    add("")

    add("## 9. Datenqualität")
    add("")
    add(_md_table(
        ["Aussage", "Datenklasse", "Belastbarkeit"],
        [
            ["Messetermine (MEDICA, boot, ProWein, CARAVAN SALON, EuroCIS, glasstec)", "1/2 – offizielle Seiten via Suche", "hoch"],
            ["Feiertage NRW, Schulferien NRW", "1 – Kalenderregel / Kultusministerium via Sekundärquelle", "hoch"],
            ["Konzert- und Festtermine", "2 – Sekundärquellen", "mittel bis niedrig (Japan-Tag widersprüchlich)"],
            ["Viertel-ADR / Auslastung", "2 – externe Anbieter, nur Snippets", "niedrig"],
            ["Basispreis", "3 – abgeleitete Schätzung", "mittel/niedrig"],
            ["Wochentags-, Saison-, Event-Faktoren", "4 – Modellannahmen", "niedrig bis zur Kalibrierung"],
            ["Comp-Set-Preise, Gebühren, Rabatte der Konkurrenz", "–", "keine belastbaren Daten verfügbar"],
            ["Realisierte Buchungspreise", "–", "keine belastbaren Daten verfügbar"],
            ["Historische Event-Wirkung", "–", "keine belastbaren Daten verfügbar"],
        ],
    ))
    add("")
    add("Validierung (Phase 11): " + (
        "siehe `output/backtest.json`." if result.history else
        "**nicht durchführbar – keine historischen Tagesdaten.** Das Backtest-Modul (`validation.py`) ist bereit "
        "und vergleicht Modellpreise mit Markt-ADR (MAPE, Bias an Normal- vs. Eventtagen, Rangkorrelation)."))
    add("")
    add("Nächste Schritte zur Erhöhung der Belastbarkeit: siehe `docs/PLAN.md`, Abschnitt Implementierungsplan.")
    add("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


PLAN_COLUMNS = ["Datum", "Wochentag", "Gastpreis/Nacht (inkl. allem)", "Airbnb-Nachtpreis eintragen",
                "Mindestnächte", "Event", "Nachfrage", "Datenbasis", "Status", "Begründung"]


def data_basis(result: RunResult, p: DayPrice) -> str:
    """Wie belastbar ist der Preis dieses Tages?"""
    med = (result.observed_dates or {}).get(p.demand.day)
    if med is not None:
        return f"belegt: Vergleichs-Median {med:.0f} € (inkl. allem)"
    if p.demand.event.max_tier in ("S", "A", "B"):
        return "Annahme: Event-Aufschlag ohne Vergleichspreise"
    return "abgeleitet: Vergleichspreise normaler Tage + eigene Buchungen"


def plan_rows(result: RunResult, start: date, end: date) -> list[dict]:
    rows = []
    for p in result.prices:
        d = p.demand
        if not start <= d.day <= end:
            continue
        rows.append({
            "Datum": d.day.isoformat(),
            "Wochentag": german_weekday(d.day),
            "Gastpreis/Nacht (inkl. allem)": p.recommended,
            "Airbnb-Nachtpreis eintragen": airbnb_nightly_price(p, result.cfg),
            "Mindestnächte": p.min_nights,
            "Event": d.event.names,
            "Nachfrage": d.level,
            "Datenbasis": data_basis(result, p),
            "Status": p.quota_recommendation,
            "Begründung": "; ".join(r for r in p.reasons if not r.startswith("Vorlauf")),
        })
    return rows


def write_plan_csv(rows: list[dict], path: Path) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PLAN_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return rows


def price_ranges(rows: list[dict]) -> list[dict]:
    """Aufeinanderfolgende Tage mit gleichem Airbnb-Preis und Mindestaufenthalt zusammenfassen."""
    ranges: list[dict] = []
    for r in rows:
        if r["Status"] in ("gebucht", "geschlossen", "blockiert"):
            continue
        key = (r["Airbnb-Nachtpreis eintragen"], r["Mindestnächte"], r["Event"], r["Datenbasis"])
        if ranges and ranges[-1]["_key"] == key and date.fromisoformat(ranges[-1]["bis"]).toordinal() + 1 == date.fromisoformat(r["Datum"]).toordinal():
            ranges[-1]["bis"] = r["Datum"]
            ranges[-1]["Nächte"] += 1
        else:
            ranges.append({"_key": key, "von": r["Datum"], "bis": r["Datum"], "Nächte": 1,
                           "Airbnb-Nachtpreis": r["Airbnb-Nachtpreis eintragen"],
                           "Gastpreis/Nacht": r["Gastpreis/Nacht (inkl. allem)"],
                           "Mindestnächte": r["Mindestnächte"], "Event": r["Event"], "Datenbasis": r["Datenbasis"]})
    for r in ranges:
        r.pop("_key")
    return ranges


def write_ranges_csv(rows: list[dict], path: Path) -> list[dict]:
    ranges = price_ranges(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["von", "bis", "Nächte", "Airbnb-Nachtpreis", "Gastpreis/Nacht", "Mindestnächte", "Event", "Datenbasis"])
        w.writeheader()
        w.writerows(ranges)
    return ranges


def revenue_summary(result: RunResult) -> dict:
    cfg = result.cfg
    booked = result.bookings or {}
    out = {"payout_ratio": cfg["fees"]["payout_ratio"], "szenarien": {},
           "bereits_gebucht": {"naechte": len(booked), "auszahlung": round(sum(booked.values()))}}
    blocks = []
    for a, b in cfg.get("availability", {}).get("blocked_nights", []):
        sel = [p for p in result.prices if date.fromisoformat(a) <= p.demand.day <= date.fromisoformat(b)]
        if sel:
            total = sum(p.static_price for p in sel)
            disc = cfg["availability"].get("block_offer_discount", 0.0)
            blocks.append({"von": a, "bis_einschl_nacht": b, "naechte": len(sel), "summe_tagespreise": round(total),
                           "angebot_gesamt": round(total * (1 - disc)), "angebot_pro_nacht": round(total * (1 - disc) / len(sel))})
    out["blockzeitraeume"] = blocks
    for f in all_forecasts(result.prices, cfg):
        out["szenarien"][f.scenario] = {
            "naechte": round(f.nights, 1),
            "naechte_je_jahr": {str(k): round(v, 1) for k, v in f.nights_by_year.items()},
            "limit_bindend": {str(k): v for k, v in f.cap_binding.items()},
            "brutto_gast": round(f.gross),
            "auszahlung": round(payout(f.gross, cfg)),
            "monate": {m: {"naechte": round(v.nights, 1), "brutto": round(v.gross), "auszahlung": round(payout(v.gross, cfg))}
                       for m, v in f.by_month.items()},
        }
    alt = compare_windows(result.prices, cfg, {
        "2027 Sommer (Jun-Sep)": (date(2027, 6, 1), date(2027, 9, 30)),
        "2027 Frühjahr (Jan-Mai)": (date(2027, 1, 1), date(2027, 5, 31)),
        "2027 beste Nächte ganzjährig (bis 03.10.)": (date(2027, 1, 1), date(2027, 12, 31)),
    })
    out["vergleich_2027"] = {k: {"naechte": round(f.nights, 1), "brutto_gast": round(f.gross),
                                 "auszahlung": round(payout(f.gross, cfg)),
                                 "adr": round(f.gross / f.nights) if f.nights else None}
                             for k, f in alt.items()}
    return out
