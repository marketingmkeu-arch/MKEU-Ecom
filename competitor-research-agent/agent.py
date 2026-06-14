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

FB_KEYWORDS = [
    "nail fungus", "nagelpilz", "nagelpilz laser", "fungal nail laser",
    "toenail fungus", "nail fungus treatment", "nagelpilz behandlung",
    "nail fungus device", "onychomycosis", "nail fungus cure",
    "toenail fungus before after", "nail fungus testimonial",
    "Canesten", "Loceryl", "Excilor",
]

YOUTUBE_QUERIES = [
    "nail fungus treatment ad 2024",
    "toenail fungus before after transformation",
    "nagelpilz laser erfahrung",
    "nail fungus laser device review",
    "how i got rid of toenail fungus",
    "nail fungus success story",
    "toenail fungus ugc ad",
]

REDDIT_SEARCHES = [
    "https://www.reddit.com/search/?q=nail+fungus+treatment&sort=new&t=week",
    "https://www.reddit.com/search/?q=toenail+fungus+cure&sort=new&t=week",
    "https://www.reddit.com/search/?q=nagelpilz+behandlung&sort=new&t=week",
    "https://www.reddit.com/r/Dermatology/search/?q=nail+fungus&sort=new&t=month",
    "https://www.reddit.com/r/AskDocs/search/?q=toenail+fungus&sort=new&t=month",
]

FORUM_URLS = [
    "https://www.onmeda.de/forum/suche?q=nagelpilz",
    "https://www.quora.com/search?q=toenail+fungus+treatment+review",
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


def safe_goto(page, url, timeout=25000):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception:
        pass


def accept_cookies(page):
    for selector in [
        '[data-cookiebanner="accept_button"]',
        'button[title="Accept All"]',
        'button[title="Alle Cookies akzeptieren"]',
        'div[aria-label="Allow all cookies"] button',
        'button[data-testid="cookie-policy-manage-dialog-accept-button"]',
        'button:has-text("Accept")',
        'button:has-text("Akzeptieren")',
    ]:
        try:
            page.click(selector, timeout=2000)
            return
        except Exception:
            pass


def scroll_page(page, steps=6, delay=1.2):
    for _ in range(steps):
        page.evaluate("window.scrollBy(0, 2000)")
        time.sleep(delay)


def scrape_fb_ads(page, keyword):
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=ALL"
        f"&q={quote(keyword)}&search_type=keyword_unordered"
    )
    safe_goto(page, url, timeout=30000)
    accept_cookies(page)
    time.sleep(3)
    scroll_page(page, steps=8, delay=1.5)

    # Expand "See more" buttons
    for sel in ['div[role="button"]:has-text("See more")', 'span:has-text("See more")', 'div[role="button"]:has-text("Mehr anzeigen")']:
        try:
            for btn in page.query_selector_all(sel)[:15]:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    raw = page.inner_text("body")[:10000]

    # Try structured ad cards
    cards = []
    try:
        for card in page.query_selector_all('[data-testid="ad-card"], div[aria-label*="Ad by"]')[:20]:
            try:
                t = card.inner_text()
                if len(t) > 50:
                    cards.append(t[:600])
            except Exception:
                pass
    except Exception:
        pass

    result = raw
    if cards:
        result += "\n\n=== AD DETAILS ===\n" + "\n---\n".join(cards[:12])
    return result[:12000]


def scrape_youtube(page, query):
    safe_goto(page, f"https://www.youtube.com/results?search_query={quote(query)}")
    time.sleep(3)
    scroll_page(page, steps=3, delay=1.2)

    raw = page.inner_text("body")[:5000]

    titles = []
    try:
        for el in page.query_selector_all("yt-formatted-string#video-title")[:15]:
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
        result += "\n\n=== VIDEO TITLES ===\n" + "\n".join(titles)
    return result[:7000]


def scrape_reddit(page, url):
    safe_goto(page, url)
    accept_cookies(page)
    time.sleep(3)
    scroll_page(page, steps=4, delay=1.0)
    return page.inner_text("body")[:8000]


def scrape_forum(page, url):
    safe_goto(page, url)
    accept_cookies(page)
    time.sleep(2)
    scroll_page(page, steps=3, delay=1.0)
    return page.inner_text("body")[:6000]


def collect_all_data():
    data = {"fb_ads": {}, "youtube": {}, "reddit": {}, "forums": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # --- Facebook Ad Library ---
        ctx_fb = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        page_fb = ctx_fb.new_page()
        for kw in FB_KEYWORDS:
            print(f"  FB: '{kw}'...")
            data["fb_ads"][kw] = scrape_fb_ads(page_fb, kw)
            print(f"    {len(data['fb_ads'][kw])} Zeichen")
            time.sleep(2)
        page_fb.close()
        ctx_fb.close()

        # --- YouTube ---
        ctx_yt = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page_yt = ctx_yt.new_page()
        for q in YOUTUBE_QUERIES:
            print(f"  YouTube: '{q}'...")
            data["youtube"][q] = scrape_youtube(page_yt, q)
            print(f"    {len(data['youtube'][q])} Zeichen")
            time.sleep(2)
        page_yt.close()
        ctx_yt.close()

        # --- Reddit ---
        ctx_rd = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page_rd = ctx_rd.new_page()
        for url in REDDIT_SEARCHES:
            label = url.split("q=")[1].split("&")[0] if "q=" in url else url
            print(f"  Reddit: '{label}'...")
            data["reddit"][label] = scrape_reddit(page_rd, url)
            print(f"    {len(data['reddit'][label])} Zeichen")
            time.sleep(2)
        page_rd.close()
        ctx_rd.close()

        # --- Foren ---
        ctx_fo = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        page_fo = ctx_fo.new_page()
        for url in FORUM_URLS:
            label = url.split("//")[1].split("/")[0]
            print(f"  Forum: '{label}'...")
            data["forums"][label] = scrape_forum(page_fo, url)
            print(f"    {len(data['forums'][label])} Zeichen")
            time.sleep(2)
        page_fo.close()
        ctx_fo.close()

        browser.close()

    return data


def run_claude(client, prompt, max_tokens=5000):
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
        fb_combined += f"\n\n=== FB ADS – '{kw}' ===\n{text}"

    yt_combined = ""
    for q, text in data["youtube"].items():
        yt_combined += f"\n\n=== YOUTUBE – '{q}' ===\n{text}"

    prompt = f"""Du bist ein Senior Performance Marketing Analyst (Direct-Response E-Commerce, DACH + Global).

Produkt: {PRODUCT} | Datum: {today}

Du hast heute frische Rohdaten aus Facebook Ad Library und YouTube gescraped.
Deine Aufgabe: Extrahiere ALLE neuen Erkenntnisse die du in diesen Daten siehst.
Suche aktiv nach Dingen die neu oder ungewöhnlich sind — nicht nur die offensichtlichen Muster.

### FACEBOOK AD LIBRARY:
{fb_combined[:20000]}

### YOUTUBE:
{yt_combined[:8000]}

---

# TEIL 1: COMPETITOR INTELLIGENCE – {today}

## 1.1 Alle aktiven Wettbewerber (Global + DACH)
Tabelle: Brand | Markt | Produkt/Positionierung | Ad-Format | Besonderheit
Mindestens 10 Brands wenn erkennbar.

## 1.2 Heutige Video-Hooks & Ad-Einstiege (die ersten 3 Sekunden)
Jeder erkennbare Hook — exakt zitiert oder sinngemäß rekonstruiert.
Für jeden Hook: Marke | Hook-Text | Psychologischer Mechanismus | Awareness-Stage
Mindestens 12-15 verschiedene Hooks.

## 1.3 Vollständige Ad-Copy Analyse
Für jede erkennbare Anzeige: Headline → Body Copy → CTA → Funnel-Typ → Awareness-Stage

## 1.4 Dominante Angles (nach Häufigkeit, mit Zitaten)
Ranking der Angles von am häufigsten zu am seltensten.
Konkrete Beispiel-Zitate für jeden Angle.

## 1.5 Zielgruppensprache – Wortfeld-Tabelle
| Kategorie | Deutsch | Englisch | Häufigkeit |
Problem-Beschreibung / Emotionen / Versprechen / Medizinische Begriffe / CTAs

## 1.6 Funnel-Strukturen & Creative-Formate
Welche Funnel-Typen sind erkennbar? UGC / Advertorial / VSL / Quiz / Direkt-Shop?

## 1.7 Neue oder ungewöhnliche Findings heute
Was ist heute aufgetaucht das du bisher nicht oder selten gesehen hast?
(Neuer Competitor, neuer Angle, neues Format, unerwartetes Messaging)

## 1.8 Preise, Offer-Stacks & Garantien der Wettbewerber

## 1.9 Proof & Glaubwürdigkeitssignale

## 1.10 Marktlücken & Chancen für Levora
Was macht NIEMAND? Wo ist Differenzierung möglich?

## 1.11 TOP 7 SOFORT-EMPFEHLUNGEN FÜR LEVORA
Priorisiert, konkret, mit Begründung aus den heutigen Daten.

## 1.12 Was Levora NICHT tun sollte"""

    return run_claude(client, prompt, max_tokens=5000)


def analyze_community_voice(client, data):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    reddit_combined = ""
    for label, text in data["reddit"].items():
        reddit_combined += f"\n\n=== REDDIT – '{label}' ===\n{text}"

    forum_combined = ""
    for label, text in data["forums"].items():
        forum_combined += f"\n\n=== FORUM – '{label}' ===\n{text}"

    prompt = f"""Du bist ein Consumer Insights Analyst spezialisiert auf Direct-Response Marketing.

Produkt: {PRODUCT} | Datum: {today}

Du hast heute frische Daten aus Reddit und Gesundheitsforen gescraped — das sind echte, ungefilterte Stimmen von Menschen mit Nagelpilz.

### REDDIT DATEN:
{reddit_combined[:15000]}

### FORUM DATEN:
{forum_combined[:8000]}

---

Extrahiere und analysiere die echte Stimme des Kunden. Das ist Gold für Levora's Messaging.

# TEIL 2: COMMUNITY VOICE & CUSTOMER INTELLIGENCE – {today}

## 2.1 Echte Zitate aus Reddit & Foren (mindestens 20)
Gruppiert nach Thema. Exakt zitiert (mit Quellenhinweis: Reddit / Forum / Quora).
Suche besonders nach:
- Emotionale Ausbrüche / Frustration
- Gescheiterte Behandlungen ("Ich habe alles probiert...")
- Scham-Momente (Schwimmbad, Sandalen, Arzt, Partner)
- Überraschende Erkenntnisse oder Meinungen
- Skepsis gegenüber Produkten / Ads
- Positive Erfahrungen und was dabei geholfen hat

## 2.2 Häufigste Diskussionsthemen heute
Was beschäftigt die Community aktuell? Ranking nach Häufigkeit.

## 2.3 Sprache & Wording der Community (DACH + Global)
Wie beschreiben echte Menschen ihr Problem?
- 25-30 echte Begriffe/Phrasen die sie nutzen
- Emotionale Metaphern ("Ich schäme mich", "Es kommt immer wieder")
- Was sie von Produkten erwarten (in ihren Worten)

## 2.4 Aktuelle Skepsis & Einwände
Was glauben sie NICHT? Was würden sie sofort ablehnen?
Diese Einwände muss Levora's Messaging adressieren.

## 2.5 Was funktioniert laut Community (Erfolgsstories)
Welche Lösungen werden positiv erwähnt? Was hat geholfen?
Zitate + Kontext.

## 2.6 Neue Erkenntnisse heute aus der Community
Was ist heute in den Daten aufgetaucht das neu oder überraschend ist?

## 2.7 Copy-Gold für Levora
Formulierungen, Phrasen, Metaphern aus der Community die Levora direkt in Ads verwenden sollte.
Mit Begründung warum sie funktionieren.

## 2.8 Belief Chains aus echten Community-Daten
Basierend auf den heutigen Zitaten:
Oberflächen-Problem → tiefere Überzeugung → emotionale Konsequenz → Levora-Lösung"""

    return run_claude(client, prompt, max_tokens=4500)


def analyze_market_and_avatars(client):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist Market Research Strategist (Schwartz "Breakthrough Advertising") und Consumer Psychologist.

Produkt: {PRODUCT} | Zielmarkt: {TARGET_MARKET} | Datum: {today}

Erstelle heute eine tiefe Analyse. Nutze dein gesamtes Wissen über den Nagelpilz-Markt:
Reddit/Forum-Diskussionen, YouTube-Comments, Amazon-Rezensionen, Google Trends, Statista, Wettbewerber-Messaging.

Wichtig: Suche heute nach NEUEN Erkenntnissen und vertiefe bestehende Hypothesen.
Frage dich aktiv: Was weißt du heute das du gestern noch nicht wusstest?

# TEIL 3: MARKT-INTELLIGENZ & AVATAR-PSYCHOGRAFIE – {today}

## 3.1 TAM & Marktdynamik (DACH + Global)
- Globaler Antifungal-Markt: Größe, CAGR, Trend
- DACH spezifisch: Betroffene (~12 Mio.), Kaufbereitschaft für Device
- Warum JETZT ein gutes Fenster für Levora ist

## 3.2 Awareness Stage Breakdown – DACH Nagelpilz-Laser-Markt
Für jede Stage: %-Schätzung | Warum | Typische Aussagen auf Deutsch | Touchpoints
Unaware / Problem Aware / Solution Aware / Product Aware / Most Aware

## 3.3 Awareness-Trends & Neue Signale
Was verändert sich gerade im Markt?
- Suchvolumen-Shifts
- TikTok/Social-Trends
- Saisonalität (Sommer nahend)
- Generationsshift (wird Nagelpilz ein jüngeres Thema?)
- Neue Technologien die Awareness verschieben

## 3.4 Tiefe Demografische Analyse

Tabelle: Segment | % | Kernanliegen | Kauf-Trigger | Best Channel | Messaging-Ansatz
Trenne: Frauen 40-55 / Frauen 55-70+ / Männer 45-65 / Diabetiker / Sportler / Senioren

Komorbiditäten als Targeting-Signal:
Wie nutzt man Diabetes, Durchblutungsstörungen, Immunschwäche für Meta-Targeting?

## 3.5 Psychografische Tiefenanalyse – Die 3 Kern-Avatare

Für jeden Avatar:
- Name & Kurzbezeichnung
- Alter, Geschlecht, Lebenssituation, Einkommen
- Awareness-Stage
- Ihre Nagelpilz-Geschichte (Erstvorkommen → Versuche → aktueller Stand)
- Die 3 tiefsten emotionalen Schmerzpunkte (mit authentischen Zitaten)
- Was sie von "dem perfekten Produkt" erwarten (in ihren Worten)
- Welche Plattformen / Content sie konsumieren
- Der Hook der sie sofort anspricht (konkreter Ad-Text)

**Avatar #1 – [Name]**
**Avatar #2 – [Name]**
**Avatar #3 – [Name]**

## 3.6 Villains & externe Schuld im Kundenkopf
Wen oder was machen sie verantwortlich? (Pharma, Ärzte, Schwimmbäder, Schuhe)
Wie nutzt Levora das in Storytelling?

## 3.7 Sprache & Emotionale Hot Buttons
Top 7 emotionale Trigger + wie Levora sie anspricht

## 3.8 8 sofort testbare Ad-Hooks für Levora
Basierend auf heutiger Analyse:
- 2x Scham/Sozial (Deutsch)
- 2x Frustration/Gescheiterte Versuche (Deutsch)
- 2x Curiosity-Gap/Insider (Deutsch/Englisch)
- 2x Transformation/Versprechen
Für jeden: exakter Text + Avatar + Awareness-Stage

## 3.9 "For Dummies" Executive Summary
- Dominante Awareness-Stufe: [X]
- Was das konkret bedeutet (Klartext)
- Der eine Satz der alles zusammenfasst für die Messaging-Strategie"""

    return run_claude(client, prompt, max_tokens=5000)


def create_action_plan(client, competitor_intel, community_voice, market_analysis):
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    prompt = f"""Du bist Lead-Stratege für Levora Skin. Du hast heute drei Research-Reports erhalten:
1. Competitor Intelligence (FB Ad Library + YouTube)
2. Community Voice (Reddit + Foren — echte Kundenstimmen)
3. Markt-Intelligenz & Avatar-Psychografie

Produkt: {PRODUCT} | Datum: {today}

Erstelle den strategischen Action-Plan der DIREKT aus den heutigen Daten kommt.
Keine generischen Marketing-Ratschläge. Jede Empfehlung muss auf einem konkreten heutigen Finding basieren.

# TEIL 4: ACTION PLAN & NEXT STEPS FÜR LEVORA – {today}

## 4.1 Top 3 Erkenntnisse des Tages
Was ist heute das Wichtigste? Was hat sich bestätigt, vertieft, oder neu gezeigt?
Jede Erkenntnis: Was → Warum wichtig → Konkrete Implikation für Levora

## 4.2 DIESE WOCHE UMSETZEN (Top Priorität)
Für jede Aktion:
- **Was genau tun** (so konkret wie möglich)
- **Warum** (welches Finding von heute begründet das)
- **Kanal & Format**
- **Welchen Avatar ansprechen**
- **Konkreter Hook-Text oder Messaging-Ansatz**
- **KPI zum Messen**

## 4.3 NÄCHSTE WOCHE VORBEREITEN
3-4 Aktionen mit gleicher Struktur

## 4.4 Creative-Briefing für heute (Video-Ad)
**Format:** UGC / Testimonial / Hook-Video (Empfehlung begründen)
**Länge:** X Sekunden
**Hook (Sekunde 1-3):** [exakter Text / was zu sehen ist]
**Story-Arc:**
- Sek 1-5: ...
- Sek 5-15: ...
- Sek 15-30: ...
**CTA:** ...
**Do's:** ...
**Don'ts:** ...
**Referenz-Ads** aus dem heutigen Research

## 4.5 Langfristige Chance (Nächste 3 Monate)
Was zeigt der Research als strukturellen Trend?
Wie baut Levora systematisch Marktführerschaft im DACH-Laser-Device-Segment auf?

## 4.6 Warnungen & Was Levora NICHT tun sollte
Übersättigte Angles, Compliance-Risiken, Fehler die Wettbewerber machen die Levora vermeiden sollte"""

    return run_claude(client, prompt, max_tokens=3500)


def create_google_doc(drive_service, title, full_content):
    today_de = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    body_html = md.markdown(full_content, extensions=["tables", "fenced_code", "nl2br"])
    html = f"""<html><meta charset="utf-8">
<head><style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.65; color: #222; max-width: 980px; margin: 40px auto; padding: 0 24px; }}
  h1 {{ font-size: 26pt; color: #1a1a2e; border-bottom: 4px solid #e63946; padding-bottom: 12px; margin-top: 0; }}
  h2 {{ font-size: 17pt; color: #1a1a2e; margin-top: 36px; background: #fff8f8; border-left: 5px solid #e63946; padding: 8px 14px; }}
  h3 {{ font-size: 13pt; color: #1a1a2e; margin-top: 22px; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
  h4 {{ font-size: 12pt; color: #e63946; margin-top: 16px; font-weight: bold; }}
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
  p {{ margin: 8px 0; }}
  .meta {{ color: #888; font-size: 9pt; margin-bottom: 30px; }}
</style></head>
<body>
<h1>{title}</h1>
<p class="meta">Erstellt: {today_de} | {PRODUCT} | {TARGET_MARKET}</p>
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
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    today_de = now.strftime("%d.%m.%Y")
    print(f"GOD TIER Research Agent gestartet – {today}")

    print("\n[1/5] Scraping: FB Ad Library + YouTube + Reddit + Foren...")
    data = collect_all_data()

    total_fb = sum(len(t) for t in data["fb_ads"].values())
    total_yt = sum(len(t) for t in data["youtube"].values())
    total_rd = sum(len(t) for t in data["reddit"].values())
    total_fo = sum(len(t) for t in data["forums"].values())
    print(f"  FB: {total_fb} | YouTube: {total_yt} | Reddit: {total_rd} | Foren: {total_fo} Zeichen")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n[2/5] Competitor Intelligence (Hooks, Scripts, Angles)...")
    competitor_intel = analyze_competitor_intel(client, data)
    print(f"  {len(competitor_intel)} Zeichen")

    print("\n[3/5] Community Voice (Reddit + Foren — echte Kundenstimmen)...")
    community_voice = analyze_community_voice(client, data)
    print(f"  {len(community_voice)} Zeichen")

    print("\n[4/5] Markt-Intelligenz & Avatar-Psychografie...")
    market_analysis = analyze_market_and_avatars(client)
    print(f"  {len(market_analysis)} Zeichen")

    print("\n[5/5] Action Plan & Next Steps...")
    action_plan = create_action_plan(client, competitor_intel, community_voice, market_analysis)
    print(f"  {len(action_plan)} Zeichen")

    full_report = f"""{competitor_intel}

---

{community_voice}

---

{market_analysis}

---

{action_plan}"""

    print("\nErstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"{today_de} Marktresearch"
    doc_url = create_google_doc(drive_service, title, full_report)

    print(f"\nFertig! {len(full_report)} Zeichen Gesamt-Report")
    print(f"Doc: {doc_url}")


if __name__ == "__main__":
    main()
