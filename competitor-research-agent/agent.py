import os
import io
import time
import anthropic
import markdown as md
from datetime import datetime, timezone
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
DRIVE_FOLDER_ID = os.environ.get("DRIVE_RESEARCH_FOLDER_ID", "")

KEYWORDS = [
    "nail fungus", "nagelpilz", "fungal nail laser",
    "nagelpilz laser", "toenail fungus", "nail fungus treatment",
    "nagelpilz behandlung", "nail fungus device",
]

PRODUCT = "Levora Skin – Anti-Nagelpilz Laser-Device (~€49,90)"
NICHE = "Anti-Nagelpilz / Fußpflege / Health-Device"
TARGET_MARKET = "DACH (Deutschland, Österreich, Schweiz)"
AVATAR_TARGET = "Frauen und Männer 40–65+, DACH-Markt"


def get_drive_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def scrape_keyword(page, keyword):
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=ALL"
        f"&q={quote(keyword)}&search_type=keyword_unordered"
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception:
        pass

    for selector in [
        '[data-cookiebanner="accept_button"]',
        'button[title="Accept All"]',
        'button[title="Alle Cookies akzeptieren"]',
        'div[aria-label="Allow all cookies"] button',
    ]:
        try:
            page.click(selector, timeout=2000)
            break
        except Exception:
            pass

    time.sleep(3)

    for _ in range(5):
        page.evaluate("window.scrollBy(0, 1500)")
        time.sleep(1.2)

    return page.inner_text("body")[:8000]


def collect_raw_texts():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
        )
        page = context.new_page()

        for keyword in KEYWORDS:
            print(f"Scrape: '{keyword}'...")
            text = scrape_keyword(page, keyword)
            results[keyword] = text
            print(f"  {len(text)} Zeichen gesammelt")
            time.sleep(2)

        browser.close()
    return results


def run_claude(client, prompt, max_tokens=4000):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def analyze_competitor_intel(client, raw_texts):
    combined = ""
    for kw, text in raw_texts.items():
        combined += f"\n\n=== Keyword: '{kw}' ===\n{text}"

    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein Senior Performance Marketing Analyst spezialisiert auf Direct-Response E-Commerce im DACH-Markt.

Produkt: {PRODUCT}
Markt: {TARGET_MARKET}
Datum: {today}

Ich habe die Facebook Ad Library für folgende Keywords gescraped: {', '.join(raw_texts.keys())}

Rohdaten aus der Ad Library:
{combined[:20000]}

---

Erstelle einen strukturierten Competitor Intelligence Report auf Deutsch. Analysiere alle erkennbaren Werbeanzeigen (Markennamen, Ad-Texte, Headlines, CTAs).

# Teil 1: Competitor Intelligence Report – {today}

## 1.1 Identifizierte Marken & Wettbewerber
Tabelle: Brand | Markt | Produkt/Positionierung | Ad-Volumen/Laufzeit

## 1.2 Dominante Angles & Hooks
Für jeden Angle: Beschreibung + konkrete Zitate aus den Ads + warum es funktioniert

## 1.3 Zielgruppensprache & Wording
Häufige Begriffe nach Kategorie (Problem-Description, Emotionen, Versprechen, CTAs) als Tabelle

## 1.4 Funnel-Muster
Erkennbare Strukturen: Ad-Hook → Body Copy → CTA → Landingpage-Typ

## 1.5 Creative-Ansätze
UGC, Advertorial, Testimonial, Educational, Vorher/Nachher – mit Beispielen

## 1.6 Angebot & Preisstruktur
Erkennbare Preisniveaus, Bundles, Garantien, Scarcity-Taktiken

## 1.7 Proof & Glaubwürdigkeit
Welche Autoritätssignale nutzen Wettbewerber (Studien, Ärzte, Vorher/Nachher)?

## 1.8 Marktlücken & Chancen für Levora
Was machen Wettbewerber NICHT? Wo kann Levora differenzieren?

## 1.9 Top 5 sofort umsetzbare Empfehlungen für Levora Skin
Konkret, priorisiert, mit Begründung

## 1.10 Was vermeiden
Übersättigte Angles, riskante Claims, schwache Positionierungen"""

    return run_claude(client, prompt, max_tokens=4000)


def analyze_market_awareness(client):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein Market Research Strategist ausgebildet in Eugene Schwartz' "Breakthrough Advertising".

Deine Aufgabe: Führe eine umfassende Market Awareness und Demographic Intelligence Analysis durch für:
Produkt: {PRODUCT}
Nische: {NICHE}
Zielmarkt: {TARGET_MARKET}
Datum: {today}

Nutze dein Wissen über Social Media-Diskussionen (Reddit, TikTok, YouTube, Facebook), Suchverhalten (Google Trends), Marktdaten (Statista, Grand View Research) und Wettbewerber-Messaging im Nagelpilz/Health-Device-Bereich.

# Teil 2: Market Awareness & Zielgruppen-Analyse

## 2.1 Total Addressable Market (TAM)
- Gesamtmarktgröße (Nagelpilz-Behandlung / At-home Health Devices) in EUR/USD für DACH
- Wachstumsrate (CAGR) und Trend
- Betroffene Personen (ca. 12-15% der Bevölkerung leiden an Nagelpilz laut Studien)
- Bewertung der Opportunity für ein Laser-Device bei ~€49,90

## 2.2 Awareness Stage Breakdown (Schwartz-Framework)
Schätze die prozentuale Verteilung für den DACH-Nagelpilz-Markt:
- **Unaware** (X%): Begründung, typische Phrasen, Touchpoints
- **Problem Aware** (X%): Begründung, typische Phrasen, Touchpoints
- **Solution Aware** (X%): Begründung, typische Phrasen, Touchpoints
- **Product Aware** (X%): Begründung, typische Phrasen, Touchpoints
- **Most Aware** (X%): Begründung, typische Phrasen, Touchpoints

## 2.3 Verhaltens- & Sprachindikatoren
Realistische Beispiele was Menschen in jeder Awareness-Stage sagen oder suchen (DACH-Sprache)

## 2.4 Awareness-Trends
Aktuelle Shifts im DACH-Markt: wachsendes Suchvolumen? Neue Kanäle (TikTok)? Influencer-Coverage?

## 2.5 Finale Awareness-Einschätzung
"Die Mehrheit des DACH-Marktes befindet sich aktuell in der [X]-Stage."
Mit 2-3 Sätzen Begründung.

## 2.6 Werbe-Implikationen für Levora
- Welche Awareness-Stufe zuerst targeten?
- Ton, Proof-Level, emotionale Tiefe
- Konkreter Ad-Angle oder Headline-Idee

## 2.7 Demografische Zusammensetzung

**Geschlecht:**
| Segment | % | Strategische Implikation |
|---------|---|--------------------------|
| Frauen | X% | ... |
| Männer | X% | ... |

**Alter:**
| Altersgruppe | % | Verhalten | Implikation |
|-------------|---|-----------|-------------|
| 35–44 | X% | ... | ... |
| 45–54 | X% | ... | ... |
| 55–64 | X% | ... | ... |
| 65+ | X% | ... | ... |

**Geografie & Einkommen:** Top-Regionen in DACH, Einkommensniveaus

## 2.8 Top 3 Zielgruppen-Avatare für Levora

**Avatar #1 – [Name]**
Alter, Geschlecht, Einkommen, Psychografik, Awareness-Stage, Plattformen, resonierendes Messaging, konkreter Ad-Angle

**Avatar #2 – [Name]**
[gleiches Format]

**Avatar #3 – [Name]**
[gleiches Format]

## 2.9 "For Dummies" Executive Summary
- Dominante Awareness-Stufe: [X]
- Was das bedeutet (Klartext): Was wissen Kunden bereits? Was glauben sie?
- Actionable Takeaway: Ein Satz was als nächstes in der Messaging-Strategie zu tun ist
- Avatar-Verbindung: Wie mappt die Awareness-Stufe auf die Top-Avatare?"""

    return run_claude(client, prompt, max_tokens=4000)


def analyze_avatar_psychographics(client):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein erfahrener Direct-Response-Stratege und Konsumentenpsychologe.

Deine Aufgabe: Führe eine tiefe psychografische Analyse durch für:
Produkt: {PRODUCT}
Zielgruppe: {AVATAR_TARGET}
Datum: {today}

Basiere die Analyse auf deinem Wissen über öffentliche Diskussionen zu Nagelpilz auf Reddit (r/Nagelpflege, r/AskDocs, r/Dermatology), Facebook-Gruppen, YouTube-Kommentaren, Amazon-Rezensionen und deutschen Gesundheitsforen.
Verwende realistische, authentische Zitate (kennzeichne mit Plattform/Kontext). Keine Marketing-Phrasen.

# Teil 3: Psychografische Tiefenanalyse – Die innere Welt des Levora-Kunden

## 3.1 Identität & Kernüberzeugungen
**Wer ist dieser Kunde?**
- Selbstbild, Rolle im Leben, worauf er/sie stolz ist
- Lebensstil: Beruf, Familie, Hobbys, Werte
- Direkte Zitate (wie beschreiben sie sich selbst und ihr Leben)

**Weltanschauung & Überzeugungen:**
- Was "gut" und "schlecht" bedeutet
- Einstellung zu Gesundheit, Eigenverantwortung, Medizin
- Kern-Lebensphilosophie in 1-3 Sätzen

**Hoffnungen, Träume, Ziele:**
- Wie sieht ein idealer Tag aus?
- Was bedeutet "bessere Zukunft" für sie?
- Zitate die Sehnsucht oder Optimismus zeigen

## 3.2 Schmerzen, Frustrationen & Ängste
**Emotionale Pain Points:**
- Scham, Angst, Schuldgefühle, Unsicherheit rund um Nagelpilz
- Soziale Isolation (Sandalen, Schwimmbad, Intimität)
- Was sie nachts wachhält

**Externe Frustrationen:**
- Gescheiterte Behandlungen (Lacke, Cremes, Arztbesuche)
- Kosten, Zeitaufwand, Nebenwirkungen
- "Horror Stories" aus Foren – starke emotionale Zitate

**Warum sie glauben blockiert zu sein:**
- Externe Schuldzuweisungen (Pharma, Ärzte, "unheilbar")

## 3.3 Markt- & Lösungswahrnehmung
**Welche Lösungen haben sie bereits probiert?**
- Konkrete Marken, Methoden, Hausmittel
- Was hat sie dazu geführt (Empfehlung, Werbung, Arzt)?

**Was sie an bestehenden Lösungen mögen:**
- Emotionale Vorteile (Erleichterung, Kontrolle, Hoffnung)
- Funktionale Positives
- Verbatim-Zitate mit Zufriedenheit

**Was sie an bestehenden Lösungen NICHT mögen:**
- Enttäuschung, Verrat, Reue
- "Es hat einfach nicht funktioniert" – Zitate
- Skeptizismus: "Das ist alles nur Marketing"

## 3.4 Neugier & Vergessene Versuche
- Unkonventionelle oder vergessene Methoden die diskutiert werden
- Reaktionen darauf (Begeisterung, Unglaube)
- Historische oder verschwörungstheoretische Narrative rund um Nagelpilz-Behandlung

## 3.5 Externe Schuld & "Der Feind"
- Glauben sie das Problem ist heute schlimmer als früher? Warum?
- Klare Schuldige in ihrer Erzählung (Pharmaindustrie, Ärzte, Schuhe, öffentliche Bäder)
- Gruppen die "immun" erscheinen ("Die Japaner haben das nie wegen...")
- Emotionale Befriedigung dieser Überzeugungen

## 3.6 Sprache & Emotionale Trigger
**20-30 häufige Begriffe/Metaphern** (DACH-Sprache) zur Beschreibung des Problems

**Top 5-7 emotionale Hot Buttons:**
- Angst vor dem Altern / Verfall
- Wunsch nach Kontrolle
- Scham & soziale Peinlichkeit
- Vertrauen in natürliche/technische Lösungen
- etc.

## 3.7 Marketing-Anwendung

**Key Psychological Drivers (Top 5-7):**
Für jeden: Emotion | Überzeugung dahinter | Kunden-Zitat | Marketing-Implikation

**Top Belief Chains für Copy:**
Jede Kette: Oberflächen-Frustration → tiefere Überzeugung → emotionale Konsequenz → was Levora enthüllt/löst

**Marketing-Hypothesen (3-5):**
"Wenn wir [Kern-Wunsch/Angst] ansprechen mit [spezifischem Narrativ], dann [erwartete Reaktion], weil [emotionale Begründung aus Zitaten]."

**Konkreter Copy-Starter für Levora:**
Schreibe 3 Hook-Varianten (je 1-2 Sätze) die direkt aus dieser Analyse entstehen und sofort in Facebook-Ads testbar sind."""

    return run_claude(client, prompt, max_tokens=4500)


def combine_reports(client, competitor_intel, market_awareness, avatar_psycho):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein Senior Marketing Strategist. Erstelle einen knappen strategischen Synthese-Abschnitt der die drei folgenden Research-Teile verbindet.

Produkt: {PRODUCT} | Datum: {today}

Die drei Analyse-Teile wurden bereits erstellt. Erstelle NUR diesen abschließenden Synthese-Abschnitt (ca. 400-600 Wörter):

# Teil 4: Strategische Synthese & Action Plan

## 4.1 Die 3 wichtigsten Erkenntnisse (Cross-Report)
Verbinde die Insights aus Competitor Intel, Market Awareness und Psychografie zu den 3 übergeordneten strategischen Erkenntnissen für Levora.

## 4.2 Sofort-Action-Plan für Levora (nächste 30 Tage)
Konkrete, priorisierte Liste (1-5) mit:
- Was genau tun
- Welchen Kanal/Format nutzen
- Welchen Awareness-Level targeten
- Welchen Avatar ansprechen

## 4.3 Warnungen & Fallstricke
Was sollte Levora in den nächsten 30 Tagen NICHT tun (übersättigte Angles, Compliance-Risiken, schwache Positionierungen)

Halte es präzise und actionable. Kein Fluff."""

    return run_claude(client, prompt, max_tokens=1500)


def create_google_doc(drive_service, title, full_content):
    body_html = md.markdown(full_content, extensions=["tables", "fenced_code", "nl2br"])
    html = f"""<html><meta charset="utf-8">
<head><style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #222; max-width: 960px; margin: 40px auto; padding: 0 20px; }}
  h1 {{ font-size: 24pt; color: #1a1a2e; border-bottom: 3px solid #e63946; padding-bottom: 10px; margin-top: 40px; }}
  h2 {{ font-size: 17pt; color: #1a1a2e; margin-top: 32px; border-left: 4px solid #e63946; padding-left: 12px; }}
  h3 {{ font-size: 13pt; color: #333; margin-top: 20px; }}
  h4 {{ font-size: 12pt; color: #555; margin-top: 14px; font-style: italic; }}
  table {{ border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 10pt; }}
  th {{ background: #e63946; color: white; padding: 8px 12px; text-align: left; font-weight: bold; }}
  td {{ border: 1px solid #ddd; padding: 7px 11px; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  blockquote {{ border-left: 4px solid #e63946; margin: 12px 0; padding: 10px 18px; background: #fff5f5; font-style: italic; color: #333; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 10pt; }}
  hr {{ border: none; border-top: 2px solid #e63946; margin: 32px 0; }}
  ul, ol {{ padding-left: 24px; }}
  li {{ margin: 5px 0; }}
  strong {{ color: #1a1a2e; }}
  .section-divider {{ background: #1a1a2e; color: white; padding: 12px 20px; margin: 40px -20px 20px; font-size: 14pt; font-weight: bold; }}
</style></head>
<body>
<h1>{title}</h1>
<p style="color:#666; font-size:10pt;">Erstellt: {datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")} UTC | Produkt: {PRODUCT} | Markt: {TARGET_MARKET}</p>
<hr>
{body_html}
</body></html>"""

    metadata = {"name": title, "mimeType": "application/vnd.google-apps.document"}
    if DRIVE_FOLDER_ID:
        metadata["parents"] = [DRIVE_FOLDER_ID]

    media = MediaIoBaseUpload(io.BytesIO(html.encode("utf-8")), mimetype="text/html")
    f = drive_service.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    return f.get("webViewLink", "")


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_de = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    print(f"GOD TIER Research Agent gestartet – {today}")

    print("\n[1/5] Scraping Facebook Ad Library...")
    raw_texts = collect_raw_texts()
    total_chars = sum(len(t) for t in raw_texts.values())
    print(f"Gesamt: {total_chars} Zeichen aus {len(raw_texts)} Keywords")

    if total_chars < 500:
        print("Zu wenig Daten. Abbruch.")
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n[2/5] Competitor Intelligence Analyse...")
    competitor_intel = analyze_competitor_intel(client, raw_texts)
    print(f"  {len(competitor_intel)} Zeichen generiert")

    print("\n[3/5] Market Awareness & Demografische Analyse...")
    market_awareness = analyze_market_awareness(client)
    print(f"  {len(market_awareness)} Zeichen generiert")

    print("\n[4/5] Psychografische Avatar-Analyse...")
    avatar_psycho = analyze_avatar_psychographics(client)
    print(f"  {len(avatar_psycho)} Zeichen generiert")

    print("\n[5/5] Strategische Synthese...")
    synthesis = combine_reports(client, competitor_intel, market_awareness, avatar_psycho)
    print(f"  {len(synthesis)} Zeichen generiert")

    full_report = f"""{competitor_intel}

---

{market_awareness}

---

{avatar_psycho}

---

{synthesis}"""

    print("\nErstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"GOD TIER Research – Levora Skin – {today_de}"
    doc_url = create_google_doc(drive_service, title, full_report)

    total_chars_report = len(full_report)
    print(f"\nFertig! {total_chars_report} Zeichen Report")
    print(f"Doc: {doc_url}")


if __name__ == "__main__":
    main()
