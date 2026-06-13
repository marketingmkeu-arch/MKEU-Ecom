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

PRODUCT = "Levora Skin – Anti-Nagelpilz Laser-Device (~€49,90)"
NICHE = "Anti-Nagelpilz / Fußpflege / Health-Device"
TARGET_MARKET = "DACH (Deutschland, Österreich, Schweiz) + global"
AVATAR_TARGET = "Frauen und Männer 40–65+, DACH-Markt"

FB_KEYWORDS = [
    "nail fungus", "nagelpilz", "fungal nail laser",
    "nagelpilz laser", "toenail fungus", "nail fungus treatment",
    "nagelpilz behandlung", "nail fungus device",
    "onychomycosis", "fungal nail", "nail fungus cure",
    "toenail fungus treatment", "nail laser device",
]

YOUTUBE_QUERIES = [
    "nail fungus treatment ad",
    "toenail fungus before after",
    "nagelpilz laser behandlung",
    "nail fungus laser device review",
    "fungal nail cure testimonial",
    "nail fungus facebook ad",
]


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


def scrape_fb_ads_deep(page, keyword):
    """Scrape FB Ad Library and try to extract individual ad details."""
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=ALL"
        f"&q={quote(keyword)}&search_type=keyword_unordered"
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass

    for selector in [
        '[data-cookiebanner="accept_button"]',
        'button[title="Accept All"]',
        'button[title="Alle Cookies akzeptieren"]',
        'div[aria-label="Allow all cookies"] button',
        'button[data-testid="cookie-policy-manage-dialog-accept-button"]',
    ]:
        try:
            page.click(selector, timeout=2000)
            break
        except Exception:
            pass

    time.sleep(3)

    # Scroll aggressively to load many ads
    for _ in range(8):
        page.evaluate("window.scrollBy(0, 2000)")
        time.sleep(1.5)

    # Try to click "See more" / "Mehr anzeigen" buttons to expand ad text
    for see_more_sel in [
        'div[role="button"]:has-text("See more")',
        'div[role="button"]:has-text("Mehr anzeigen")',
        'span:has-text("See more")',
    ]:
        try:
            buttons = page.query_selector_all(see_more_sel)
            for btn in buttons[:15]:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    # Get full page text including expanded ad copies
    raw = page.inner_text("body")

    # Also try to get structured ad data via aria labels
    structured = []
    try:
        ad_cards = page.query_selector_all('[data-testid="ad-card"], div[class*="ad_card"], div[aria-label*="Ad by"]')
        for card in ad_cards[:20]:
            try:
                text = card.inner_text()
                if len(text) > 50:
                    structured.append(text[:600])
            except Exception:
                pass
    except Exception:
        pass

    combined = raw[:10000]
    if structured:
        combined += "\n\n=== STRUKTURIERTE AD-DETAILS ===\n" + "\n---\n".join(structured[:10])

    return combined[:12000]


def scrape_youtube_for_scripts(page, query):
    """Scrape YouTube search results for video titles, descriptions, and comments."""
    url = f"https://www.youtube.com/results?search_query={quote(query)}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
    except Exception:
        return ""

    time.sleep(3)
    for _ in range(3):
        page.evaluate("window.scrollBy(0, 1500)")
        time.sleep(1)

    # Get titles and descriptions from search results
    raw = page.inner_text("body")[:6000]

    # Try to get video titles specifically
    titles = []
    try:
        title_els = page.query_selector_all("yt-formatted-string#video-title, h3.title-and-badge a")
        for el in title_els[:15]:
            try:
                t = el.inner_text().strip()
                if t:
                    titles.append(t)
            except Exception:
                pass
    except Exception:
        pass

    result = raw
    if titles:
        result += "\n\n=== VIDEO TITLES ===\n" + "\n".join(titles[:15])

    return result[:7000]


def scrape_youtube_video_comments(page, video_url):
    """Get comments and description from a specific YouTube video."""
    try:
        page.goto(video_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(4)
        # Scroll to load comments
        for _ in range(4):
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(1.5)
        return page.inner_text("body")[:8000]
    except Exception:
        return ""


def collect_all_data():
    results = {"fb_ads": {}, "youtube": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # FB Ad Library scraping
        context_fb = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
        )
        page_fb = context_fb.new_page()

        for keyword in FB_KEYWORDS:
            print(f"  FB Ad Library: '{keyword}'...")
            text = scrape_fb_ads_deep(page_fb, keyword)
            results["fb_ads"][keyword] = text
            print(f"    {len(text)} Zeichen")
            time.sleep(2)

        page_fb.close()
        context_fb.close()

        # YouTube scraping
        context_yt = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page_yt = context_yt.new_page()

        for query in YOUTUBE_QUERIES:
            print(f"  YouTube: '{query}'...")
            text = scrape_youtube_for_scripts(page_yt, query)
            results["youtube"][query] = text
            print(f"    {len(text)} Zeichen")
            time.sleep(2)

        page_yt.close()
        context_yt.close()
        browser.close()

    return results


def run_claude(client, prompt, max_tokens=4500):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def analyze_competitor_intel(client, data):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    fb_combined = ""
    for kw, text in data["fb_ads"].items():
        fb_combined += f"\n\n=== FB ADS – Keyword: '{kw}' ===\n{text}"

    yt_combined = ""
    for query, text in data["youtube"].items():
        yt_combined += f"\n\n=== YOUTUBE – Query: '{query}' ===\n{text}"

    prompt = f"""Du bist ein Senior Performance Marketing Analyst (Direct-Response E-Commerce, DACH + Global).

Produkt: {PRODUCT}
Datum: {today}

Du hast folgende Rohdaten aus Facebook Ad Library und YouTube gescraped:

### FACEBOOK AD LIBRARY DATEN (Keywords: {', '.join(data['fb_ads'].keys())}):
{fb_combined[:18000]}

### YOUTUBE DATEN:
{yt_combined[:8000]}

---

Analysiere alle erkennbaren Werbeanzeigen, Video-Hooks, Skripte und Messaging-Muster.
Extrahiere so viele konkrete Textbeispiele wie möglich (Headlines, Hooks, Body Copy, CTAs, Video-Einstiege).

# TEIL 1: COMPETITOR INTELLIGENCE REPORT – {today}

## 1.1 Identifizierte Wettbewerber (Global + DACH)
Erstelle eine detaillierte Tabelle:
| Brand | Land/Markt | Produkt | Ad-Format | Laufzeit | Kanal | Besonderheit |
Mindestens 10 Marken wenn erkennbar. Trenne DACH-Wettbewerber von internationalen.

## 1.2 Video-Hooks & Ad-Einstiege (die ersten 3 Sekunden)
Das ist der kritischste Teil. Liste jeden erkennbaren Video-Hook / Ad-Opener:
- Exaktes Zitat oder sinngemäße Rekonstruktion
- Welche Marke / welcher Kanal
- Warum funktioniert dieser Hook psychologisch? (Neugier, Scham, Versprechen, Schock)
- Awareness-Stage die er anspricht

**Mindestens 15 verschiedene Hook-Variationen wenn möglich.**

## 1.3 Vollständige Ad-Skripte & Copy-Analyse
Für jede erkennbare Anzeige:
- **Headline / Hook** (erster Satz/Bild)
- **Body Copy** (Hauptversprechen, Story, Proof)
- **CTA** (was sollen sie tun)
- **Funnel-Typ** (direkt zu Shop / Advertorial / Lead)
- **Awareness-Stage**

## 1.4 Dominante Angles nach Häufigkeit (Ranking)
Sortiere von am häufigsten zu am seltensten:
1. [Angle-Name]: X% der Ads – Beschreibung – konkrete Beispiel-Zitate
2. ...

## 1.5 ZG-Spezifisches Wording & Emotionale Trigger
Erstelle eine strukturierte Wortliste:

| Kategorie | Deutsch | Englisch | Häufigkeit |
|-----------|---------|----------|------------|
| Problem-Beschreibung | "verfärbte Nägel", "Pilz unter dem Nagel" | "discolored nails", "nail fungus" | hoch |
| Emotionen | "Scham", "peinlich", "verstecken" | "embarrassing", "hiding" | sehr hoch |
| Versprechen | "sichtbare Ergebnisse in 2 Wochen" | "visible results" | mittel |
| CTAs | "Jetzt testen", "Mehr erfahren" | "Try now", "Shop now" | - |

## 1.6 Funnel-Strukturen
Für jeden erkennbaren Funnel-Typ:
- Ad-Typ → Landing Page → Offer → Upsell
- Beispiel-Marke
- Besonderheiten (Advertorial-Stil, VSL, Quiz-Funnel)

## 1.7 Creative-Formate & Storytelling
| Format | Beschreibung | Marken die es nutzen | Warum es funktioniert |
Trenne: UGC-Testimonial / Vorher-Nachher / Educational-Content / Experten-Hook / Problem-Agitation-Solution / Curiosity-Gap-Advertorial

## 1.8 Preise, Angebote & Offer-Stacks
Was sind erkennbare Preisniveaus, Bundles, Garantien, Scarcity-Taktiken der Wettbewerber?

## 1.9 Proof & Glaubwürdigkeitssignale
Was nutzen Wettbewerber um Vertrauen aufzubauen?
- Studien & Statistiken (konkrete Zitate)
- Arzt-Endorsements
- Vorher/Nachher Bildbeweise
- Testimonial-Typen

## 1.10 Marktlücken & Chancen für Levora
Was macht NIEMAND in diesem Markt? Wo ist Differenzierung möglich?
Konkret nach Kanal, Format, Angle, Zielgruppe.

## 1.11 TOP 7 SOFORT-UMSETZBARE EMPFEHLUNGEN FÜR LEVORA
Priorisiert nach Hebel-Wirkung:
1. **[Was genau]** – Begründung (basierend auf Wettbewerber-Insight X) – Format/Kanal – erwartete Wirkung
2. ...

## 1.12 Was Levora NICHT tun sollte
Übersättigte Angles, riskante Health Claims, schwache Differenzierungen die bereits alle machen."""

    return run_claude(client, prompt, max_tokens=5000)


def analyze_market_awareness(client):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein Market Research Strategist ausgebildet in Eugene Schwartz' "Breakthrough Advertising".

Produkt: {PRODUCT}
Zielmarkt: {TARGET_MARKET}
Datum: {today}

Nutze dein gesamtes Wissen über:
- Reddit-Diskussionen (r/Nagelpilz, r/AskDocs, r/Dermatology, r/diabetes, r/eldercare)
- TikTok/YouTube Kommentare zu Nagelpilz-Content
- Google Trends Daten zu "nagelpilz", "nail fungus treatment"
- Statista / Grand View Research Marktdaten (Antifungal-Markt wächst auf ~$15Mrd bis 2030)
- Konkurrenten-Messaging das du über die Ad Library weißt

Erstelle einen vollständigen, tiefen Analyse-Report:

# TEIL 2: MARKET AWARENESS & ZIELGRUPPEN-INTELLIGENZ

## 2.1 Total Addressable Market (TAM) – DACH & Global
**Global:**
- Antifungal-Markt global: Größe, CAGR, Quellen
- At-home Health Devices Segment
- Nail Fungus spezifisch

**DACH:**
- Betroffene Personen (ca. 12-15% der Bevölkerung = ~12 Mio. in DACH)
- Kaufkraft & Zahlungsbereitschaft für Device-Lösung (~€49,90)
- Opportunity-Assessment: Warum ist das ein attraktives Fenster JETZT?

## 2.2 Awareness Stage Breakdown – DACH Nagelpilz-Markt

Für jede Stage:
- Prozentuale Schätzung
- Warum (Verhaltensdaten, Suchmuster, Diskussionsstil)
- Typische Aussagen/Suchanfragen dieser Menschen (Deutsch UND Englisch)
- Wo sie zu finden sind (Kanal, Community, Touchpoint)
- Wie man sie anspricht

**Unaware (~X%)**
**Problem Aware (~X%)**
**Solution Aware (~X%)**
**Product Aware (~X%)**
**Most Aware (~X%)**

## 2.3 Verhaltens- & Sprachindikatoren nach Stage
Liste 5-8 realistische Aussagen/Suchanfragen pro Stage.
Bleib authentisch – wie würden diese Menschen WIRKLICH sprechen (Umgangssprache, Foren-Tonalität)?

## 2.4 Awareness-Trends 2024-2026
- Wächst das Suchvolumen? Wohin?
- Neue Kanäle: TikTok "NailFungus" Hashtag-Wachstum
- Influencer-Coverage: Zunahme von UGC zu Nagelpilz?
- Saisonalität: Wann suchen Menschen mehr (Frühjahr vor Sommer?)
- Generationsshift: Wird das Thema jünger?

## 2.5 Finale Awareness-Einschätzung
**"Die Mehrheit des DACH-Marktes für Nagelpilz-Laser-Devices befindet sich aktuell in der [X]-Stage."**
Begründung in 3-4 Sätzen. Was bedeutet das konkret für Levora's Advertising-Strategie?

## 2.6 Demografische Tiefenanalyse

**Geschlecht:**
| Segment | % | Kernanliegen | Kanal-Präferenz | Messaging-Ansatz |
|---------|---|--------------|-----------------|------------------|
| Frauen 40-55 | X% | ... | ... | ... |
| Frauen 55-70+ | X% | ... | ... | ... |
| Männer 45-65 | X% | ... | ... | ... |
| Männer 30-45 | X% | ... | ... | ... |

**Alter-Breakdown:**
| Altersgruppe | % | Kaufverhalten | Pain Point Fokus | Best Channel |
|-------------|---|---------------|------------------|--------------|
| 35-44 | X% | ... | ... | ... |
| 45-54 | X% | ... | ... | ... |
| 55-64 | X% | ... | ... | ... |
| 65+ | X% | ... | ... | ... |

**Geografische Prioritäten in DACH:**
Welche Bundesländer/Regionen? Städtisch vs. ländlich?

**Komorbiditäten als Targeting-Signal:**
Nagelpilz korreliert stark mit: Diabetes, Durchblutungsstörungen, Immunschwäche, Sportlerfuß.
Wie nutzt man das für Meta-Targeting?

## 2.7 Top 3 Zielgruppen-Avatare für Levora

Für jeden Avatar sehr konkret:

**Avatar #1 – [Name] – [Kurzbezeichnung]**
- Alter, Geschlecht, Wohnort, Einkommen, Lebenssituation
- Awareness-Stage
- Wichtigste Plattformen & Content-Konsum
- Was sie bereits probiert haben (und warum es scheiterte)
- Ihr größter emotionaler Pain Point (in ihren eigenen Worten)
- Welcher Levora-Hook würde sie sofort ansprechen
- Konkretes Ad-Beispiel (Hook → Promise → CTA) für diesen Avatar

**Avatar #2 – [Name] – [Kurzbezeichnung]**
[gleiches Format]

**Avatar #3 – [Name] – [Kurzbezeichnung]**
[gleiches Format]

## 2.8 "For Dummies" Executive Summary

- **Dominante Awareness-Stufe:** [X]
- **Was das bedeutet (Klartext):** Was wissen diese Menschen bereits? Was glauben sie?
- **Der größte Fehler den Levora machen könnte:** ...
- **Actionable Takeaway:** Ein präziser Satz was als erstes in der Messaging-Strategie zu tun ist
- **Avatar-Connection:** Welcher Avatar ist das beste Einstiegs-Segment und warum?
- **Wichtigste Metrik zum Tracken:** ..."""

    return run_claude(client, prompt, max_tokens=5000)


def analyze_avatar_psychographics(client):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist ein erfahrener Direct-Response-Stratege und Konsumentenpsychologe.

Produkt: {PRODUCT}
Zielgruppe: {AVATAR_TARGET}, speziell mit chronischem Nagelpilz (6+ Monate, multiple Behandlungsversuche)
Datum: {today}

Basiere die Analyse auf realen Diskussionsmustern aus:
- Reddit: r/AskDocs, r/Dermatology, r/diabetes, r/eldercare, r/malegrooming (auf Deutsch & Englisch)
- Deutschen Gesundheitsforen (onmeda.de, Apotheke.de-Kommentare)
- Amazon-Rezensionen zu Nagelpilz-Produkten (Canesten, Anti-Pilz-Lacke, Scholl)
- Facebook-Gruppen zu Fußgesundheit/Diabetes
- YouTube-Kommentare zu Nagelpilz-Videos

Erstelle verbatim-ähnliche Zitate die realistisch klingen (kennzeichne: "[Realistisches Zitat, Typ: Reddit/Forum/Amazon]").

# TEIL 3: PSYCHOGRAFISCHE TIEFENANALYSE – DER LEVORA-KUNDE

## 3.1 Wer ist diese Person? (Identität & Selbstbild)

**Selbstbeschreibung & Stolz:**
Wie beschreiben sich diese Menschen? Wofür sind sie stolz?
Zitate die zeigen wie sie ihr Leben sehen.

**Weltanschauung zu Gesundheit:**
- Einstellung zu Ärzten, Medikamenten, alternativen Heilmethoden, Technik
- Was "echte Behandlung" vs. "Abzocke" bedeutet
- Eigenverantwortung vs. systemisches Versagen

**Kern-Lebensphilosophie in 2-3 Sätzen.**

## 3.2 Die Nagelpilz-Geschichte (Customer Journey bis Levora)

**Typischer Verlauf:**
1. Erstes Bemerken (wie lange ignoriert?)
2. Erster Arztbesuch (was passierte?)
3. Erste Behandlung (welche? Ergebnis?)
4. Frustration & weitere Versuche
5. Aktueller Stand (warum noch nicht gelöst?)

**Zitate zu jeder Phase** aus Foren/Reddit.

**Warum sie noch keine Lösung haben:**
- Was haben sie alles probiert (Canesten, Loceryl, Hausmittel, Arzt, Laser beim Podologen)?
- Warum hat nichts dauerhaft geholfen?
- Welche Ausreden/Rationalisierungen nutzen sie?

## 3.3 Emotionale Pain Points (tief, nicht oberflächlich)

**Die 5 tiefsten Scham- und Angst-Punkte:**

1. **[Pain Point]**: Beschreibung + 3 authentische Zitate
2. **[Pain Point]**: Beschreibung + 3 authentische Zitate
3. **[Pain Point]**: Beschreibung + 3 authentische Zitate
4. **[Pain Point]**: Beschreibung + 3 authentische Zitate
5. **[Pain Point]**: Beschreibung + 3 authentische Zitate

**Konkrete Lebenssituationen die schmerzen:**
- Am Schwimmbad / Wellness / Sauna
- Intimität mit Partner
- Arztbesuche (andere Erkrankungen – Scham bei Untersuchung)
- Sommer / Sandalen-Saison
- Pediküre / Fußpflege beim Profi

## 3.4 Was sie über Lösungen denken

**Bisherige Erfahrungen (was sie probiert haben):**
| Lösung | Warum versucht | Was passierte | Zitat |
|--------|----------------|---------------|-------|
| Canesten Lack | Arzt empfohlen | 3 Monate, dann Rückfall | "..." |
| Loceryl | Apotheke | zu teuer, Geduld verloren | "..." |
| Hausmittel (Essig, Teebaum) | Youtube-Tipps | kurzfristig besser, dann wieder schlimmer | "..." |
| Laser beim Podologen | teuer | zu teuer (€300+), mehrere Sessions | "..." |

**Ihre Skepsis gegenüber At-Home Devices:**
Konkrete Einwände die aufkommen. Wie man sie entkräftet.

**Was sie von "dem perfekten Produkt" erwarten:**
In ihren eigenen Worten.

## 3.5 Villains & Externe Schuld

**Wer oder was ist schuld?**
- "Die Pharmaindustrie will keine Heilung" – wie verbreitet ist das?
- "Ärzte nehmen das nicht ernst" – konkrete Zitate
- "Öffentliche Schwimmbäder / Fitnessstudios" als Ursache
- Schuhe / Strümpfe / Berufsbedingt

**Conspiratorial Beliefs im Markt:**
Gibt es "vergessene Heilmittel" oder Verschwörungsnarrative rund um Nagelpilz?

## 3.6 ZG-Sprache & Emotionale Trigger (DACH-spezifisch)

**25-30 häufige Begriffe/Phrasen** die diese Menschen nutzen:
Trenne: Problem-Sprache / Emotions-Sprache / Lösungs-Sprache / Skepsis-Sprache

**Top 7 Emotionale Hot Buttons:**
Für jeden: Name | Emotion | Überzeugung dahinter | Marketing-Implikation

## 3.7 Marketing-Anwendung (direkt für Levora)

**Key Psychological Drivers (Top 6):**
| Driver | Emotion | Überzeugung | Kunden-Zitat | Copy-Implikation für Levora |

**Top 5 Belief Chains für Levora-Copy:**
Jede Kette:
→ Oberflächen-Problem (was sie sagen)
→ Tiefere Überzeugung (was sie wirklich denken)
→ Emotionale Konsequenz (was sie fühlen)
→ Was Levora enthüllt/löst

**Marketing-Hypothesen (5 testbare Thesen):**
"Wenn wir [Kern-Wunsch/Angst] ansprechen mit [spezifischem Narrativ / Hook], dann [erwartete Reaktion vom Kunden], weil [emotionale Begründung]."

## 3.8 Konkrete Ad-Hooks für Levora (sofort testbar)

Basierend auf der Psychografie, schreibe 8 verschiedene Hook-Variationen:

**Hook-Typ A: Scham/Sozial** (2 Varianten auf Deutsch, 1 auf Englisch)
**Hook-Typ B: Frustration/Gescheiterte Versuche** (2 Varianten)
**Hook-Typ C: Curiosity-Gap/Insider-Wissen** (2 Varianten)
**Hook-Typ D: Transformation/Versprechen** (1 Variante)

Für jeden Hook: Wort-für-Wort Text + Avatar der angesprochen wird + Awareness-Stage"""

    return run_claude(client, prompt, max_tokens=5500)


def create_next_steps(client, competitor_intel, market_awareness, avatar_psycho):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist der Lead-Stratege für Levora Skin. Du hast heute drei tiefe Research-Reports erhalten:
1. Competitor Intelligence (FB Ad Library + YouTube)
2. Market Awareness Analyse (Schwartz-Framework, TAM, Avatare)
3. Psychografische Tiefenanalyse (Emotionen, Sprache, Belief Chains)

Produkt: {PRODUCT} | Datum: {today}

Erstelle jetzt den finalen strategischen Action-Plan:

# TEIL 4: LEVORA NEXT STEPS & STRATEGISCHER ACTION PLAN – {today}

## 4.1 Die 3 wichtigsten Erkenntnisse des Tages
(Cross-Report, was ist die EINE Sache die sich heute besonders klar gezeigt hat?)

1. **[Erkenntnis]**: Warum wichtig → Was das für Levora konkret bedeutet
2. **[Erkenntnis]**: Warum wichtig → Was das für Levora konkret bedeutet
3. **[Erkenntnis]**: Warum wichtig → Was das für Levora konkret bedeutet

## 4.2 SOFORT (Diese Woche – Top Priorität)
Für jede Aktion:
- **Was genau tun?** (so konkret wie möglich)
- **Warum?** (welcher Research-Insight begründet das)
- **Kanal / Format**
- **Welchen Avatar ansprechen?**
- **Welchen Hook / Angle nutzen?** (konkreter Text wenn möglich)
- **KPI zum Tracken**

Aktion 1: ...
Aktion 2: ...
Aktion 3: ...

## 4.3 NÄCHSTE WOCHE (Mittelfristig)
3-4 Aktionen die vorbereitet werden müssen:
(gleiche Struktur wie 4.2)

## 4.4 NÄCHSTEN MONAT (Strategisch)
2-3 größere strategische Initiativen:
- Neues Creative-Format testen
- Neue Zielgruppe erschließen
- Funnel-Struktur anpassen

## 4.5 Creative-Briefing (Für Video/Bild-Ads)
Schreibe ein kurzes Briefing für einen Videographer/Editor:

**Für die Woche priorisiertes Creative:**
- Format: (UGC / Testimonial / Explainer / Hook-Video)
- Länge: X Sekunden
- Hook (Erste 3 Sekunden): [exakter Text / Bild]
- Story-Arc: Was passiert in Sekunde 1-5 / 5-15 / 15-30?
- CTA: Was sollen sie tun?
- Do's: ...
- Don'ts: ...
- Referenz-Ads aus dem Research die als Inspiration dienen

## 4.6 WARNSIGNALE & Was Levora NICHT tun sollte
- Übersättigte Angles die bereits alle machen (konkret benennen)
- Compliance-Risiken bei Health Claims
- Schwache Positionierungen die Geld verbrennen

## 4.7 Langfristige Marktchance (6-12 Monate)
Was sieht der Research als strukturellen Trend für Levora?
Wie kann Levora die Marktführerschaft im DACH-Laser-Device-Segment aufbauen?"""

    return run_claude(client, prompt, max_tokens=3500)


def create_google_doc(drive_service, title, full_content):
    today_de = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    body_html = md.markdown(full_content, extensions=["tables", "fenced_code", "nl2br"])
    html = f"""<html><meta charset="utf-8">
<head><style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.65; color: #222; max-width: 980px; margin: 40px auto; padding: 0 24px; }}
  h1 {{ font-size: 26pt; color: #1a1a2e; border-bottom: 4px solid #e63946; padding-bottom: 12px; margin-top: 0; }}
  h2 {{ font-size: 17pt; color: #1a1a2e; margin-top: 36px; border-left: 5px solid #e63946; padding-left: 14px; background: #fff8f8; padding: 8px 14px; }}
  h3 {{ font-size: 13pt; color: #1a1a2e; margin-top: 22px; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
  h4 {{ font-size: 12pt; color: #e63946; margin-top: 16px; font-style: normal; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 10pt; }}
  th {{ background: #1a1a2e; color: white; padding: 9px 13px; text-align: left; font-weight: bold; }}
  td {{ border: 1px solid #ddd; padding: 8px 12px; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  blockquote {{ border-left: 5px solid #e63946; margin: 14px 0; padding: 12px 20px; background: #fff5f5; font-style: italic; color: #444; border-radius: 0 4px 4px 0; }}
  code {{ background: #f0f0f0; padding: 2px 7px; border-radius: 3px; font-size: 10pt; font-family: monospace; }}
  hr {{ border: none; border-top: 3px solid #e63946; margin: 40px 0; }}
  ul, ol {{ padding-left: 26px; }}
  li {{ margin: 6px 0; }}
  strong {{ color: #1a1a2e; }}
  .meta {{ color: #888; font-size: 9pt; margin-bottom: 30px; }}
  p {{ margin: 8px 0; }}
</style></head>
<body>
<h1>{title}</h1>
<p class="meta">Erstellt: {today_de} | {PRODUCT} | {TARGET_MARKET} | GOD TIER Daily Research</p>
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

    print("\n[1/5] Scraping Facebook Ad Library + YouTube...")
    data = collect_all_data()

    total_fb = sum(len(t) for t in data["fb_ads"].values())
    total_yt = sum(len(t) for t in data["youtube"].values())
    print(f"  FB Ads: {total_fb} Zeichen | YouTube: {total_yt} Zeichen")

    if total_fb < 500:
        print("Zu wenig FB-Daten. Fahre trotzdem fort mit YouTube-Daten.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n[2/5] Competitor Intelligence (Ad-Skripte, Hooks, Angles)...")
    competitor_intel = analyze_competitor_intel(client, data)
    print(f"  {len(competitor_intel)} Zeichen")

    print("\n[3/5] Market Awareness & Zielgruppen-Analyse...")
    market_awareness = analyze_market_awareness(client)
    print(f"  {len(market_awareness)} Zeichen")

    print("\n[4/5] Psychografische Avatar-Analyse...")
    avatar_psycho = analyze_avatar_psychographics(client)
    print(f"  {len(avatar_psycho)} Zeichen")

    print("\n[5/5] Next Steps & Action Plan...")
    next_steps = create_next_steps(client, competitor_intel, market_awareness, avatar_psycho)
    print(f"  {len(next_steps)} Zeichen")

    full_report = f"""{competitor_intel}

---

{market_awareness}

---

{avatar_psycho}

---

{next_steps}"""

    print("\nErstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"GOD TIER Research – Levora – {today_de}"
    doc_url = create_google_doc(drive_service, title, full_report)

    print(f"\nFertig! {len(full_report)} Zeichen Gesamt-Report")
    print(f"Doc: {doc_url}")


if __name__ == "__main__":
    main()
