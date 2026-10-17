# 00b – Projektparameter (Nutzerangaben)

Stand: 2026-10-17 · Quelle: Nutzerangaben im Chat. Personenbezogene Daten aus dem Buchungs-Screenshot (Name, Telefon) werden bewusst nicht gespeichert.

| Parameter | Wert | Konsequenz für die Modellierung |
|---|---|---|
| Reisezeitraum | 01.11.–16.11.2026 | harte Grenze für Abholung/Lieferung |
| Unterkunft (Routenstart) | 美豪酒店（上海陆家嘴八佰伴店）· Mehood Hotel, Lujiazui Babaiban, Pudong | Adresse/Koordinaten noch **nicht verifiziert** (amap.com nötig) |
| Hotelbuchung | 01.11.–13.11.2026 (12 Nächte), Stand Buchungsmaske, Zahlung nicht bestätigt | **Lücke 13.–16.11.** – Unterkunft für die letzten Nächte offen; Lieferadresse nach 13.11. ungeklärt |
| Steuerstatus | Kleinunternehmer (§ 19 UStG) | Kein Vorsteuerabzug → **Einfuhrumsatzsteuer (19 %) ist echter Kostenbestandteil**; Verkäufe ohne USt-Ausweis; Umsatzgrenzen beobachten |
| Budget | **4.000 € reine Warenkosten** (Nutzer hat Skill-Default überschrieben) | Fracht/Gepäck, Zoll, EUSt, Gebühren, Reserve kommen **zusätzlich** – Gesamtcash-Bedarf wird separat ausgewiesen |
| Transport | Zusatzgepäck im Flug | Gewerbliche Ware ist **nicht** von der Reisefreimenge gedeckt → Anmeldung am roten Ausgang. Bei Warenwert über der Grenze für mündliche Anmeldung (vermutlich 1.000 €, Art. 137 UZK-DA – **auf zoll.de zu verifizieren**) schriftliche Zollanmeldung, ggf. EORI und Zollagent am Ankunftsflughafen nötig |
| Verkaufsplattform | offen | Gebühren werden szenarisch (eBay / Cardmarket) modelliert |
| Abflug-/Ankunftsflughafen, Gepäckgrenzen | offen | nötig für Gepäckkosten und Zollstelle |

## Abgeleitete Vorab-Hinweise (noch ohne Quellenprüfung)
- 4.000 € Warenwert in Koffern übersteigt mit hoher Wahrscheinlichkeit die Grenze für vereinfachte mündliche Anmeldung → Zollabfertigung vorab planen (EORI beantragen dauert einige Tage).
- Volumen: Booster-Displays sind sperrig; Anzahl/Gewicht der Zusatzgepäckstücke wird in Stage 3 berechnet.
