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

    # Accept cookie banner if shown
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

    # Scroll to load more ads
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


def analyze_with_claude(raw_texts):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    combined = ""
    for kw, text in raw_texts.items():
        combined += f"\n\n=== Keyword: '{kw}' ===\n{text}"

    prompt = f"""Du bist ein Senior Performance Marketing Analyst spezialisiert auf Direct-Response E-Commerce.

Ich habe die Facebook Ad Library für folgende Keywords gescraped: {', '.join(raw_texts.keys())}

Hier ist der rohe Seitentext aus der Ad Library für jedes Keyword:

{combined[:25000]}

---

Extrahiere aus diesem Text alle erkennbaren Werbeanzeigen (Markennamen, Ad-Texte, Headlines, CTAs) und erstelle dann einen detaillierten Competitor Intelligence Report auf Deutsch.

# Competitor Intelligence Report – {datetime.now(timezone.utc).strftime("%d.%m.%Y")}

## 1. Identifizierte Marken & Wettbewerber
Liste alle erkennbaren Brands/Seiten die Ads schalten.

## 2. Dominante Angles & Hooks
Welche Probleme/Emotionen werden angesprochen? Konkrete Zitate aus den Ads.

## 3. Zielgruppensprache & Wording
Welche Begriffe, Formulierungen, Versprechen dominieren?

## 4. Funnel-Muster
Erkennbare Muster bei Headline → Body Copy → CTA.

## 5. Creative-Ansätze
Welche Storytelling-Ansätze werden genutzt (UGC, Vorher/Nachher, Testimonial, Educational)?

## 6. Top 5 Empfehlungen für Levora Skin
Konkrete, sofort umsetzbare Maßnahmen was Levora (Anti-Nagelpilz Laser-Device, ~€49,90, DACH-Markt) implementieren sollte.

## 7. Was vermeiden
Angles/Ansätze die übersättigt wirken oder schlechte Signale senden."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def create_google_doc(drive_service, title, content):
    body_html = md.markdown(content, extensions=["tables", "fenced_code", "nl2br"])
    html = f"""<html><meta charset="utf-8">
<head><style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #222; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
  h1 {{ font-size: 22pt; color: #1a1a2e; border-bottom: 3px solid #e63946; padding-bottom: 8px; }}
  h2 {{ font-size: 16pt; color: #1a1a2e; margin-top: 28px; border-left: 4px solid #e63946; padding-left: 10px; }}
  h3 {{ font-size: 13pt; color: #333; margin-top: 18px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th {{ background: #e63946; color: white; padding: 8px 12px; text-align: left; }}
  td {{ border: 1px solid #ddd; padding: 8px 12px; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  blockquote {{ border-left: 4px solid #e63946; margin: 10px 0; padding: 8px 16px; background: #fff5f5; font-style: italic; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 24px 0; }}
  ul, ol {{ padding-left: 24px; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #1a1a2e; }}
</style></head>
<body>
<h1>{title}</h1>
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
    print(f"Competitor Research Agent gestartet – {today}")

    raw_texts = collect_raw_texts()
    total_chars = sum(len(t) for t in raw_texts.values())
    print(f"\nGesamt: {total_chars} Zeichen aus {len(raw_texts)} Keywords gesammelt")

    if total_chars < 500:
        print("Zu wenig Daten gesammelt. Abbruch.")
        return

    print("Analysiere mit Claude...")
    report = analyze_with_claude(raw_texts)

    print("Erstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"Competitor Intel – {today}"
    doc_url = create_google_doc(drive_service, title, report)

    print(f"Fertig! Doc: {doc_url}")


if __name__ == "__main__":
    main()
