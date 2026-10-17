# 00 – Domain-Allowlist (Stage 0 · STOP-GATE)

Stand: 2026-10-17 · Status: **WARTET AUF FREIGABE** · Noch keine Website wurde aufgerufen.

Diese Liste ist Berechtigungsplanung, keine Vertrauensaussage und kein Nachweis, dass eine Seite für automatisierten Zugriff erreichbar ist. Es werden keine Logins, Käufe, Zahlungen, Registrierungen oder Händlerkontakte durchgeführt. CAPTCHAs, Paywalls, Geoblocks und Anti-Bot-Maßnahmen werden nicht umgangen. Ein blockierter Zugriff wird als `BLOCKED` protokolliert.

Benötigte Berechtigung je Host: nur lesender HTTPS-GET (WebFetch/WebSearch). Kein POST, kein Login, keine Cookies/Sessions.

## Priorität A – für Stage 1 und Rechts-Gate unverzichtbar

| Host | Rolle | Login nötig? | Hinweis |
|---|---|---|---|
| `www.pokemon.cn` (+ `pokemon.cn`) | Offizielle SKU-/Release-Daten der vereinfacht-chinesischen TCG-Produkte, offizielle Stores | nein | Primärquelle für Produktkatalog |
| `www.pokemon.com` | Globaler Abgleich, Release-Ankündigungen | nein | |
| `www.pokemon.co.jp` | Abgrenzung japanische vs. chinesische Editionen (151, Terastal) | nein | |
| `www.ebay.de` | **Verkaufte/abgeschlossene** Angebote DE | nein (Filter „Verkaufte Artikel“ ohne Login, kann aber blockiert sein) | einzige halbwegs öffentliche Sold-Daten-Quelle |
| `www.cardmarket.com` | EU-TCG-Marktpreise (Trend/Ø), Angebotslage | teils (Detail-Historie) | Anti-Bot-Schutz wahrscheinlich |
| `www.zoll.de` | Einfuhrabgaben, Reiseverkehr vs. gewerblich, EORI | nein | |
| `auskunft.ezt-online.de` | EZT – Zolltarifnummer und Zollsatz | nein | |
| `ec.europa.eu` / `taxation-customs.ec.europa.eu` | TARIC, Zollwert | nein | TARIC-Abfrage läuft über `ec.europa.eu/taxation_customs/dds2/taric/` |
| `eur-lex.europa.eu` | Unionsmarken-VO (Erschöpfung Art. 15), GPSR, EuGH-Urteile | nein | Pflicht für Marken-/Parallelimport-Gate |
| `www.gesetze-im-internet.de` | MarkenG § 24, UStG, VerpackG, SpielzeugV | nein | |
| `www.ecb.europa.eu` | EUR/CNY-Referenzkurs mit Datum | nein | |

## Priorität B – China-Marktplätze (hohe Wahrscheinlichkeit `BLOCKED`)

| Host | Rolle | Login nötig? | Hinweis |
|---|---|---|---|
| `www.tmall.com`, `*.tmall.com` | Offizielle Flagship-Stores, Double-11-Preise | meist ja für Preise | Anti-Bot, Geo-Restriktionen |
| `www.taobao.com`, `*.taobao.com` | Händler-Angebotspreise | meist ja | |
| `www.1688.com` | Großhandelsfindung | ja | Fälschungsrisiko hoch |
| `www.goofish.com`, `2.taobao.com` | Xianyu-Zweitmarkt | ja | sehr hohes Authentizitätsrisiko, nur Preisindikator |
| `www.jd.com`, `item.jd.com` | Alternative Händlerpreise | teils | |
| `www.pinduoduo.com` / `mobile.yangkeduo.com` | Preisuntergrenze, nur Indikator | ja (App-zentriert) | zusätzliche Prüfung |

Realistische Erwartung: Diese Seiten liefern ohne Login/Browser oft nichts. Alternative: Sie öffnen Seiten selbst in einer freigegebenen Browser-Session (Claude in Chrome/Desktop-Browser) – Zugangsdaten **nie** im Chat.

## Priorität C – Shanghai-Läden und Route (Stage 2/3)

| Host | Rolle | Login nötig? |
|---|---|---|
| `www.dianping.com` | Ladenfindung, Öffnungszeiten, Bewertungen | häufig ja / Anti-Bot |
| `www.amap.com`, `ditu.amap.com` | Geokodierung, ÖPNV-Routen (GCJ-02-Koordinaten) | nein |
| `map.baidu.com` | Backup-Geokodierung (BD-09-Koordinaten) | nein |
| `maps.apple.com` | Teilbare Kartenlinks | nein |

## Priorität D – Compliance-Ergänzung und Nachfrage-Ergänzung

| Host | Rolle | Login nötig? |
|---|---|---|
| `www.verpackungsregister.org` | LUCID-Pflicht VerpackG | nein |
| `www.stiftung-ear.de` | ElektroG – nur falls Elektronik-Merch | nein |
| `www.bundesbank.de` | FX-Gegenprüfung | nein |
| `www.kleinanzeigen.de` | DE-**Angebots**preise (keine Verkaufsdaten) | nein |
| `www.ebay.com` | Internationale Vergleichswerte | nein |
| `home.alibabagroup.com` | Double-11-Zeitplan (im Skill bereits zitiert) | nein |

## Freigabe – Ihre Optionen

1. **Minimal (empfohlen zum Start):** nur Priorität A → Produktkatalog, DE-Nachfrage und Rechts-/Zoll-Gate.
2. **A + C + D:** zusätzlich Läden/Route und Compliance.
3. **Alles inkl. B:** mit dem Hinweis, dass China-Marktplätze sehr wahrscheinlich blockieren.

Weiterleitungen, CDNs und Subdomains (z. B. `m.`-Varianten, `img.alicdn.com`) werden erst bei Bedarf einzeln mit Begründung angefragt.
