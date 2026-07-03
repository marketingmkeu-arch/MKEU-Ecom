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
BRAND = "Levora Skin"

COMPETITORS = {
    "Marien Apotheke": {
        "fb_search_terms": ["Marien Apotheke", "marienapotheke nagelpilz", "marienapotheke nail"],
        "website_urls": [
            "https://www.marienapotheke.de",
            "https://www.marienapotheke.de/nagelpilz",
        ],
        "fb_page_id": "marienapotheke",
    },
    "Heilbrunnen Apotheke": {
        "fb_search_terms": ["Heilbrunnen Apotheke", "heilbrunnen nagelpilz", "heilbrunnenapotheke"],
        "website_urls": [
            "https://www.heilbrunnen-apotheke.de",
            "https://www.heilbrunnen-apotheke.de/nagelpilz",
        ],
        "fb_page_id": "heilbrunnenapotheke",
    },
}


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


def safe_goto(page, url, timeout=30000):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return True
    except Exception as e:
        print(f"    Fehler beim Laden: {url} – {e}")
        return False


def accept_cookies(page):
    for selector in [
        '[data-cookiebanner="accept_button"]',
        'button[title="Accept All"]',
        'button[title="Alle Cookies akzeptieren"]',
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Accept all")',
        'button:has-text("Akzeptieren")',
        'button:has-text("Zustimmen")',
        'button:has-text("OK")',
        '[id*="cookie"] button',
        '[class*="cookie"] button',
    ]:
        try:
            page.click(selector, timeout=2000)
            time.sleep(0.5)
            return
        except Exception:
            pass


def scroll_page(page, steps=8, delay=1.2):
    for _ in range(steps):
        page.evaluate("window.scrollBy(0, 2000)")
        time.sleep(delay)


def extract_ad_links(page):
    """Extrahiert alle Ziel-URLs aus den Ads auf der aktuellen Seite."""
    links = set()
    try:
        # CTA Buttons mit Links
        for el in page.query_selector_all('a[href]'):
            href = el.get_attribute("href") or ""
            # Facebook redirect links auflösen
            if "l.facebook.com/l.php" in href or "facebook.com/ads" not in href:
                if href.startswith("http") and "facebook.com" not in href:
                    links.add(href.split("?fbclid")[0].split("&h=")[0])
            # Manchmal steckt die URL in data-attrs
        for el in page.query_selector_all('[data-ad-preview-url], [data-link-url]'):
            href = el.get_attribute("data-ad-preview-url") or el.get_attribute("data-link-url") or ""
            if href.startswith("http") and "facebook.com" not in href:
                links.add(href)
    except Exception:
        pass
    return list(links)[:10]


def scrape_fb_ads_for_brand(page, search_term):
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country=DE"
        f"&q={quote(search_term)}&search_type=keyword_unordered"
    )
    safe_goto(page, url, timeout=35000)
    accept_cookies(page)
    time.sleep(4)
    scroll_page(page, steps=10, delay=1.5)

    for sel in [
        'div[role="button"]:has-text("See more")',
        'span:has-text("See more")',
        'div[role="button"]:has-text("Mehr anzeigen")',
        'span:has-text("Mehr anzeigen")',
    ]:
        try:
            for btn in page.query_selector_all(sel)[:20]:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    raw = page.inner_text("body")[:15000]

    cards = []
    try:
        for card in page.query_selector_all('[data-testid="ad-card"], div[aria-label*="Ad by"], div[aria-label*="Werbung von"]')[:25]:
            try:
                t = card.inner_text()
                if len(t) > 50:
                    cards.append(t[:800])
            except Exception:
                pass
    except Exception:
        pass

    # Links aus den Ads extrahieren
    ad_links = extract_ad_links(page)

    result = raw
    if cards:
        result += "\n\n=== AD CARDS ===\n" + "\n---\n".join(cards[:15])
    if ad_links:
        result += "\n\n=== GEFUNDENE AD-LINKS (Ziel-URLs) ===\n" + "\n".join(ad_links)
    return result[:18000], ad_links


def scrape_fb_page_ads(page, page_id):
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country=DE"
        f"&view_all_page_id={page_id}"
    )
    safe_goto(page, url, timeout=35000)
    accept_cookies(page)
    time.sleep(4)
    scroll_page(page, steps=8, delay=1.5)

    for sel in ['div[role="button"]:has-text("See more")', 'span:has-text("Mehr anzeigen")']:
        try:
            for btn in page.query_selector_all(sel)[:20]:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    ad_links = extract_ad_links(page)
    text = page.inner_text("body")[:15000]
    if ad_links:
        text += "\n\n=== GEFUNDENE AD-LINKS (Ziel-URLs) ===\n" + "\n".join(ad_links)
    return text, ad_links


def scrape_website(page, url):
    if not safe_goto(page, url, timeout=30000):
        return ""
    accept_cookies(page)
    time.sleep(2)
    scroll_page(page, steps=6, delay=1.0)

    # Get all text
    raw = page.inner_text("body")[:12000]

    # Try to extract structured elements
    extras = []

    # Headlines
    try:
        for el in page.query_selector_all("h1, h2, h3")[:20]:
            t = el.inner_text().strip()
            if t:
                extras.append(f"[HEADLINE] {t}")
    except Exception:
        pass

    # Trust elements (Bewertungen, Siegel, Ärzte)
    try:
        for el in page.query_selector_all('[class*="trust"], [class*="review"], [class*="badge"], [class*="seal"], [class*="doctor"], [class*="award"], [class*="certificate"]')[:15]:
            t = el.inner_text().strip()
            if t and len(t) > 5:
                extras.append(f"[TRUST] {t[:200]}")
    except Exception:
        pass

    # CTAs
    try:
        for el in page.query_selector_all("button, a.btn, a.button, [class*='cta']")[:15]:
            t = el.inner_text().strip()
            if t and len(t) > 2:
                extras.append(f"[CTA] {t}")
    except Exception:
        pass

    # Prices
    try:
        for el in page.query_selector_all('[class*="price"], [class*="preis"]')[:10]:
            t = el.inner_text().strip()
            if t:
                extras.append(f"[PRICE] {t}")
    except Exception:
        pass

    result = raw
    if extras:
        result += "\n\n=== STRUKTURIERTE ELEMENTE ===\n" + "\n".join(extras[:50])
    return result[:14000]


def collect_all_data():
    data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        for brand_name, config in COMPETITORS.items():
            print(f"\n--- Scraping: {brand_name} ---")
            data[brand_name] = {"fb_ads": {}, "website": {}}

            all_ad_links = set()

            # Facebook Ad Library – Keyword Suche
            ctx_fb = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="de-DE",
            )
            page_fb = ctx_fb.new_page()

            for term in config["fb_search_terms"]:
                print(f"  FB Keyword: '{term}'...")
                result, links = scrape_fb_ads_for_brand(page_fb, term)
                data[brand_name]["fb_ads"][term] = result
                all_ad_links.update(links)
                print(f"    {len(result)} Zeichen, {len(links)} Links gefunden")
                time.sleep(3)

            # Facebook Page Ads
            print(f"  FB Page: '{config['fb_page_id']}'...")
            page_text, links = scrape_fb_page_ads(page_fb, config["fb_page_id"])
            data[brand_name]["fb_ads"]["__page__"] = page_text
            all_ad_links.update(links)
            print(f"    {len(page_text)} Zeichen, {len(links)} Links gefunden")

            page_fb.close()
            ctx_fb.close()

            # Website/Funnel Scraping – automatisch aus Ad-Links + Fallback
            ctx_web = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="de-DE",
            )
            page_web = ctx_web.new_page()

            # Zuerst die aus den Ads extrahierten Links scrapen
            scraped_links = list(all_ad_links)[:6]
            print(f"  Scrape {len(scraped_links)} Ad-Links (automatisch gefunden)...")
            for url in scraped_links:
                print(f"  → {url[:80]}...")
                result = scrape_website(page_web, url)
                data[brand_name]["website"][url] = result
                print(f"    {len(result)} Zeichen")
                time.sleep(2)

            # Fallback: hardcodierte URLs falls keine Links aus Ads gefunden
            if len(scraped_links) == 0:
                print(f"  Keine Ad-Links gefunden – nutze Fallback-URLs...")
                for url in config.get("website_urls", []):
                    print(f"  → {url}...")
                    result = scrape_website(page_web, url)
                    data[brand_name]["website"][url] = result
                    print(f"    {len(result)} Zeichen")
                    time.sleep(2)

            page_web.close()
            ctx_web.close()

        browser.close()

    return data


def run_claude(client, prompt, max_tokens=6000):
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def analyze_competitor(client, brand_name, brand_data, today):
    fb_combined = ""
    for term, text in brand_data["fb_ads"].items():
        label = "Facebook Page Ads" if term == "__page__" else f"FB Keyword '{term}'"
        fb_combined += f"\n\n=== {label} ===\n{text}"

    web_combined = ""
    for url, text in brand_data["website"].items():
        web_combined += f"\n\n=== WEBSITE: {url} ===\n{text}"

    prompt = f"""Du bist ein Senior Performance Marketing Analyst und Funnel-Experte (Direct Response, DACH E-Commerce).

Wir analysieren heute **{brand_name}** — einen direkten Konkurrenten von {BRAND} im Nagelpilz-Markt.
Datum: {today}

Du hast frische Rohdaten aus Facebook Ad Library und ihren Websites. Zerlege diesen Wettbewerber **von A bis Z**.

---

## FACEBOOK AD DATEN:
{fb_combined[:18000]}

## WEBSITE/LANDING PAGE DATEN:
{web_combined[:12000]}

---

# VOLLANALYSE: {brand_name.upper()}

## 1. CREATIVE BREAKDOWN — Jede erkennbare Anzeige

Für jede Anzeige die du erkennst:

**Anzeige #X:**
- **Hook (erste 3 Sekunden):** [exakter Text / was zu sehen ist]
- **Format:** UGC / Testimonial / Produktvideo / Infografik / Carousel / etc.
- **Avatar:** Wer wird angesprochen? (Alter, Geschlecht, Situation)
- **Desire:** Was ist das tiefste Verlangen das angesprochen wird?
- **Angle:** Der übergeordnete Blickwinkel (Scham, Gescheiterte Versuche, Soziale Peinlichkeit, Transformation, Wissenschaft, etc.)
- **Awareness Stage:** Unaware / Problem Aware / Solution Aware / Product Aware / Most Aware
- **Body Copy:** Wichtigste Aussagen
- **CTA:** Wohin wird geleitet? (Shop, Landing Page, Quiz, etc.)
- **Offer:** Was wird angeboten? Preis / Bundle / Garantie sichtbar?

---

## 2. AVATAR-ANALYSE — Welche Zielgruppen werden bespielt?

Beschreibe jeden erkennbaren Avatar detailliert:
- Demografisch (Alter, Geschlecht)
- Psychografisch (Situation, Schmerzpunkte, Verhalten)
- Wie verhält sich dieser Avatar mit Nagelpilz? (Beispiel: Frau lackiert Nägel um es zu verstecken / Mann ignoriert es einfach / Sportler schämt sich im Umkleidraum)
- Welche Sprache wird für diesen Avatar verwendet?
- Wird für jeden Avatar ein anderer Angle/Creative genutzt?

---

## 3. FUNNEL-KONGRUENZ ANALYSE

**3.1 Creative → Landing Page Match:**
Was verspricht das Creative? Was zeigt die Landing Page? Ist das kongruent?
Wo gibt es Brüche? (Anderer Ton, anderes Versprechen, anderes Design)

**3.2 Awareness-Level Match:**
Passt die Awareness-Stage im Creative zur Seite wo gelandet wird?
(Jemand der Problem Aware ist sollte nicht direkt auf eine Product Page)

**3.3 Offer-Kongruenz:**
Wird im Creative ein spezifisches Angebot gezeigt das auf der LP bestätigt wird?

**3.4 Funnel-Typ:**
Direkt zum Shop / Landing Page / Advertorial / Quiz-Funnel / VSL / anderes?

---

## 4. TRUST-BUILDING ANALYSE

Wie bauen sie Vertrauen auf? Bewerte jeden Trust-Mechanismus:

- **Ärzte & Experten:** Werden Ärzte, Dermatologen, Podologen gezeigt? Wie prominent? Authentisch oder gestellt?
- **Gütesiegel & Zertifikate:** Welche Siegel nutzen sie? (CE, TÜV, Apotheken-Siegel, etc.)
- **Social Proof:** Reviews, Sternebewertungen, Anzahl Kunden — wie präsentiert?
- **Personal Stories / Testimonials:** Wer erzählt die Geschichte? Glaubwürdigkeit?
- **Vorher/Nachher:** Wie werden Transformationen gezeigt?
- **Medienerwähnungen:** Presse, TV, Magazine?
- **Garantien:** Geld-zurück, Zufriedenheitsgarantie — wie kommuniziert?
- **Gesamtbewertung Trust-Strategie:** Was funktioniert, was wirkt billig?

---

## 5. OFFER ANALYSE

- **Hauptprodukt & Preis**
- **Bundle / Upsell Struktur** — was wird zusammen verkauft?
- **Garantien & Risk Reversal**
- **Scarcity / Urgency Mechanismen** (limitiert, Rabatt läuft ab, etc.)
- **Zahlungsoptionen** (Ratenzahlung, PayPal, etc.)
- **Versand & Lieferversprechen**
- **Gesamtbewertung Offer-Stärke**

---

## 6. ZIELGRUPPENSPRACHE & MESSAGING

- **Welche Worte und Phrasen nutzen sie?** (Exakte Zitate aus Ads und Website)
- **Tonalität:** Medizinisch/klinisch vs. emotional/persönlich vs. witzig/leicht?
- **Taboo-Themen:** Sprechen sie Scham direkt an? Wie?
- **Was vermeiden sie zu sagen?**
- **Deutsche vs. englische Begriffe** — was dominiert?

---

## 7. WAS MACHEN SIE GUT — Lerne davon für {BRAND}

Top 5-7 Dinge die {brand_name} besser macht als der Durchschnitt.
Für jedes: Was genau → Warum es funktioniert → Wie {BRAND} das übernehmen sollte

---

## 8. WAS MACHEN SIE SCHLECHT — Deine Chance

Top 5-7 Schwächen, Fehler oder verpasste Chancen.
Für jede: Was fehlt/falsch → Warum das ein Problem ist → Wie {BRAND} das besser machen kann

---

## 9. ZUSAMMENFASSUNG — Killer-Insights für {BRAND}

3-5 prägnante, actionable Erkenntnisse aus dieser Analyse.
Was muss {BRAND} sofort wissen um besser zu sein als {brand_name}?"""

    return run_claude(client, prompt, max_tokens=6000)


def create_synthesis(client, analyses, today):
    combined = ""
    for brand, analysis in analyses.items():
        combined += f"\n\n{'='*60}\nANALYSE: {brand}\n{'='*60}\n{analysis}"

    prompt = f"""Du bist Lead-Stratege für {BRAND} (Anti-Nagelpilz Laser-Device, ~€49,90, DACH).

Du hast heute tiefe Funnel-Analysen von zwei direkten Konkurrenten erhalten:
- Marien Apotheke
- Heilbrunnen Apotheke

Datum: {today}

{combined[:15000]}

---

# SYNTHESE & STRATEGISCHER ACTION PLAN FÜR {BRAND}

## 1. DIREKTVERGLEICH: Marien Apotheke vs. Heilbrunnen Apotheke

Tabelle: Kriterium | Marien Apotheke | Heilbrunnen Apotheke | {BRAND} Chance
Kriterien: Creative-Stärke / Avatar-Abdeckung / Funnel-Qualität / Trust / Offer / Zielgruppensprache / Awareness-Level

---

## 2. AVATAR-GAPS — Welche Zielgruppen werden von BEIDEN vernachlässigt?

Wer wird nicht oder schlecht angesprochen? Das sind {BRAND}'s sofortige Chancen.
Konkrete Avatar-Beschreibungen + warum niemand sie anspricht.

Denke dabei an typische Verhaltensweisen verschiedener Avatare:
- Frauen die Nägel lackieren um Pilz zu verstecken
- Männer die das Problem einfach ignorieren
- Senioren die es nicht sehen können
- Diabetiker die besonders gefährdet sind
- Sportler die sich im Umkleidraum schämen
- etc.

---

## 3. ANGLE-GAPS — Was sagt keiner der beiden?

Welche Angles, Hooks, Messaging-Ansätze werden von beiden Wettbewerbern nicht genutzt?
Das sind unbesetzte Positionen im Markt.

---

## 4. FUNNEL-BLUEPRINT FÜR {BRAND}

Basierend auf dem was gut und schlecht funktioniert bei den Wettbewerbern:
Was sollte {BRAND}'s optimaler Funnel aussehen?

- **Awareness-Level Entry Point** — wo sollen die meisten Ads ansetzen?
- **Funnel-Typ** — LP / Quiz / VSL / Direkt-Shop?
- **Creative-Format Priorität**
- **Trust-Elemente** die unbedingt rein müssen
- **Offer-Struktur Empfehlung**

---

## 5. TOP 5 SOFORT-AKTIONEN FÜR {BRAND}

Priorisiert nach Impact. Für jede:
- **Was genau tun**
- **Warum** (welches Finding begründet das)
- **Konkreter Hook-Text oder Messaging-Ansatz**
- **Welchen Avatar ansprechen**
- **KPI zum Messen**

---

## 6. CREATIVE-BRIEFING — Die eine Ad die jetzt getestet werden soll

Basierend auf den größten Gaps der Wettbewerber:

**Format:**
**Länge:**
**Avatar:**
**Awareness-Stage:**
**Hook (Sekunde 1-3):**
**Story-Arc:**
- Sek 1-5: ...
- Sek 5-15: ...
- Sek 15-30: ...
- Sek 30-60: ...
**CTA:**
**Landing Page Empfehlung:**
**Trust-Elemente die rein müssen:**
**Was {BRAND} NICHT machen sollte** (Fehler der Wettbewerber vermeiden)"""

    return run_claude(client, prompt, max_tokens=5000)


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
  .brand-section {{ background: #f0f4ff; border-left: 5px solid #1a1a2e; padding: 8px 14px; margin: 20px 0; }}
</style></head>
<body>
<h1>{title}</h1>
<p class="meta">Erstellt: {today_de} | {BRAND} | Competitor Deep-Dive: Marien Apotheke & Heilbrunnen Apotheke</p>
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
    print(f"Competitor Deep-Dive Agent gestartet – {today_de}")
    print(f"Ziele: Marien Apotheke & Heilbrunnen Apotheke")

    print("\n[1/4] Scraping: Facebook Ads + Websites beider Wettbewerber...")
    data = collect_all_data()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    analyses = {}
    step = 2
    for brand_name, brand_data in data.items():
        total = sum(len(t) for t in brand_data["fb_ads"].values()) + sum(len(t) for t in brand_data["website"].values())
        print(f"\n[{step}/4] Analysiere {brand_name} ({total} Zeichen Rohdaten)...")
        analysis = analyze_competitor(client, brand_name, brand_data, today_de)
        analyses[brand_name] = analysis
        print(f"  Analyse: {len(analysis)} Zeichen")
        step += 1

    print(f"\n[4/4] Synthese & Action Plan für {BRAND}...")
    synthesis = create_synthesis(client, analyses, today_de)
    print(f"  Synthese: {len(synthesis)} Zeichen")

    full_report = ""
    for brand_name, analysis in analyses.items():
        full_report += f"# DEEP-DIVE ANALYSE: {brand_name.upper()}\n\n{analysis}\n\n---\n\n"
    full_report += f"# SYNTHESE & ACTION PLAN FÜR {BRAND.upper()}\n\n{synthesis}"

    print("\nErstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"{today_de} – Competitor Deep-Dive: Marien & Heilbrunnen Apotheke"
    doc_url = create_google_doc(drive_service, title, full_report)

    print(f"\nFertig! {len(full_report)} Zeichen Gesamt-Report")
    print(f"Doc: {doc_url}")


if __name__ == "__main__":
    main()
