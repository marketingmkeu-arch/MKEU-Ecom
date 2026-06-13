import os
import io
import json
import requests
import anthropic
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
DRIVE_FOLDER_ID = os.environ.get("DRIVE_RESEARCH_FOLDER_ID", "")

KEYWORDS = [
    "nail fungus", "nagelpilz", "fungal nail", "nail fungus laser",
    "nagelpilz laser", "onychomycosis", "nail fungus treatment",
    "nagelpilz behandlung", "anti-fungal nail", "toenail fungus",
    "nail fungus device", "nagelpilz gerät",
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


def search_ad_library(keyword):
    url = "https://graph.facebook.com/v19.0/ads_archive"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "search_terms": keyword,
        "ad_active_status": "ACTIVE",
        "fields": "id,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,ad_creative_link_titles,ad_delivery_start_time,page_name,ad_snapshot_url",
        "limit": 30,
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        print(f"  Fehler bei '{keyword}': {r.text[:200]}")
        return []
    return r.json().get("data", [])


def collect_ads():
    all_ads = {}
    for keyword in KEYWORDS:
        print(f"Suche: '{keyword}'...")
        ads = search_ad_library(keyword)
        for ad in ads:
            ad_id = ad.get("id")
            if ad_id and ad_id not in all_ads:
                all_ads[ad_id] = ad
        print(f"  {len(ads)} Ads gefunden")
    return list(all_ads.values())


def format_ads_for_analysis(ads):
    by_page = {}
    for ad in ads:
        page = ad.get("page_name", "Unbekannt")
        if page not in by_page:
            by_page[page] = []
        by_page[page].append(ad)

    lines = []
    for page, page_ads in list(by_page.items())[:40]:
        lines.append(f"\n### Marke: {page} ({len(page_ads)} Ads aktiv)")
        for ad in page_ads[:3]:
            bodies = ad.get("ad_creative_bodies") or []
            titles = ad.get("ad_creative_link_titles") or []
            descs = ad.get("ad_creative_link_descriptions") or []
            captions = ad.get("ad_creative_link_captions") or []
            start = ad.get("ad_delivery_start_time", "")
            if titles:
                lines.append(f"  Headline: {titles[0][:200]}")
            if bodies:
                lines.append(f"  Copy: {bodies[0][:400]}")
            if descs:
                lines.append(f"  Beschreibung: {descs[0][:200]}")
            if captions:
                lines.append(f"  Caption: {captions[0][:100]}")
            if start:
                lines.append(f"  Läuft seit: {start[:10]}")
            lines.append("")

    return "\n".join(lines)


def analyze_with_claude(ads_text, total_ads, total_pages):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Du bist ein Senior Performance Marketing Analyst spezialisiert auf Direct-Response E-Commerce.

Ich habe {total_ads} aktive Facebook/Instagram Ads von {total_pages} verschiedenen Marken aus der Meta Ad Library gesammelt. Alle bewerben Produkte rund um Nagelpilz-Behandlung (Laser-Geräte, Cremes, Behandlungen etc.) weltweit.

Hier sind die gesammelten Ads:

{ads_text}

---

Erstelle jetzt einen detaillierten Competitor Intelligence Report auf Deutsch. Sei extrem konkret und zitiere echte Beispiele aus den Ads.

# Competitor Intelligence Report – {{datum}}

## 1. Marktüberblick
Wer schaltet wie viel, wer ist am aggressivsten aktiv, Marktdynamik.

## 2. Dominante Angles & Hooks
Welche Probleme/Emotionen werden angesprochen? Liste die Top-Angles mit konkreten Zitaten aus den Ads.

## 3. Zielgruppensprache & Wording
Welche Begriffe, Formulierungen, Versprechen dominieren? Was resoniert offensichtlich?

## 4. Funnel-Muster
Erkennbare Muster bei Headline → Body Copy → CTA. Wie wird der Kaufimpuls aufgebaut?

## 5. Creative-Ansätze
Welche Formate und Storytelling-Ansätze werden genutzt (UGC, Vorher/Nachher, Testimonial, Educational, etc.)?

## 6. Top 5 Empfehlungen für Levora Skin
Konkrete, sofort umsetzbare Maßnahmen was Levora (Anti-Nagelpilz Laser-Device, ~€49,90, DACH-Markt) von den Wettbewerbern lernen und implementieren sollte.

## 7. Was vermeiden
Angles/Ansätze die übersättigt wirken oder schlechte Signale senden."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def create_google_doc(drive_service, title, content):
    html = f"""<html><meta charset="utf-8"><body>
<h1>{title}</h1>
<div style="font-family: Arial, sans-serif; line-height: 1.6; white-space: pre-wrap;">{content}</div>
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

    ads = collect_ads()
    print(f"\nGesamt: {len(ads)} unique Ads gesammelt")

    if not ads:
        print("Keine Ads gefunden. Abbruch.")
        return

    pages = set(ad.get("page_name") for ad in ads)
    print(f"Von {len(pages)} verschiedenen Marken/Seiten")

    ads_text = format_ads_for_analysis(ads)
    print(f"\nAnalysiere mit Claude...")
    report = analyze_with_claude(ads_text, len(ads), len(pages))

    print("Erstelle Google Doc...")
    drive_service = get_drive_service()
    title = f"Competitor Intel – {today}"
    doc_url = create_google_doc(drive_service, title, report)

    print(f"Fertig!")
    print(f"Doc: {doc_url}")


if __name__ == "__main__":
    main()
