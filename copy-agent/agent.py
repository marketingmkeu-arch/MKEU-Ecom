import os
import re
import time
import anthropic
import requests
from playwright.sync_api import sync_playwright

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "marketingmkeu-arch/MKEU-Ecom")
ISSUE_NUMBER = int(os.environ["ISSUE_NUMBER"])
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")

# YouTube channels to scrape for copywriting knowledge
CREATOR_CHANNELS = {
    "Anthony Camacho": "https://www.youtube.com/@AnthonyCamacho/videos",
    "Sebastian Szalinski": "https://www.youtube.com/@SebastianSzalinski/videos",
    "Carl Weische": "https://www.youtube.com/@CarlWeische/videos",
}

BREAKTHROUGH_ADVERTISING_CONTEXT = """
## Breakthrough Advertising (Eugene Schwartz) — Kern-Prinzipien

**Die 5 Awareness-Stages:**
1. Unaware — kennen ihr Problem nicht → beginne mit Story/Emotion
2. Problem Aware — kennen Problem, keine Lösung → zeige dass Lösung existiert
3. Solution Aware — kennen Lösungskategorien → positioniere dein Produkt
4. Product Aware — kennen dein Produkt, noch nicht überzeugt → Proof, Differenzierung
5. Most Aware — wollen kaufen, brauchen Anlass → Offer, Urgency, Preis

**Die 3 Copy-Elemente:**
- **Mass Desire** — schreibe nicht über das Produkt, schreibe über das größte existierende Verlangen der Zielgruppe
- **Claim** — der stärkste Anspruch den du beweisen kannst
- **Proof** — alles was den Claim glaubwürdig macht

**Hook-Mechanismen nach Schwartz:**
- Identify the desire → amplify it → channel it into your product
- Der Hook muss das EXISTING desire der Zielgruppe ansprechen, nie ein neues erzeugen
- Headlines müssen: das Versprechen enthalten ODER Neugier wecken ODER beides

**Häufige Copy-Fehler:**
- Über Features reden statt über den Transformation
- Zu früh zum Produkt gehen (Awareness-Stage ignorieren)
- Proof fehlt oder ist schwach
- CTA kommt zu früh oder zu spät
- Kein klares Hauptversprechen (too many promises = no promise)
"""


def scrape_youtube_channel(page, channel_url, channel_name, max_videos=8):
    """Scrape recent video titles and snippets from a YouTube channel."""
    print(f"  Scrape {channel_name}...")
    try:
        page.goto(channel_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(3)

        # Accept cookies
        for sel in ['button[aria-label="Accept all"]', 'button:has-text("Accept all")', 'button:has-text("Alle akzeptieren")']:
            try:
                page.click(sel, timeout=2000)
                break
            except Exception:
                pass

        time.sleep(2)

        # Get video titles
        titles = []
        for sel in ["yt-formatted-string#video-title", "#video-title", "a#video-title"]:
            try:
                els = page.query_selector_all(sel)
                for el in els[:max_videos]:
                    try:
                        t = el.inner_text().strip()
                        if t and len(t) > 5:
                            titles.append(t)
                    except Exception:
                        pass
                if titles:
                    break
            except Exception:
                pass

        # Get raw page text for context
        raw = page.inner_text("body")[:4000]

        return {
            "titles": titles[:max_videos],
            "raw": raw,
        }
    except Exception as e:
        print(f"    Fehler: {e}")
        return {"titles": [], "raw": ""}


def get_youtube_insights():
    """Scrape all creator channels for recent video topics and themes."""
    insights = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-DE",
        )
        page = ctx.new_page()

        for name, url in CREATOR_CHANNELS.items():
            insights[name] = scrape_youtube_channel(page, url, name)
            time.sleep(2)

        browser.close()
    return insights


def format_creator_insights(insights):
    """Format scraped YouTube data into prompt context."""
    lines = []
    for creator, data in insights.items():
        lines.append(f"\n### {creator} — Aktuelle Video-Themen:")
        if data["titles"]:
            for t in data["titles"]:
                lines.append(f"- {t}")
        else:
            lines.append("(keine Titel gefunden)")
    return "\n".join(lines)


def analyze_copy(copy_text, title, creator_insights_text):
    """Run full copywriting analysis with Claude."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = f"""Du bist ein Elite-Copywriter und Copy-Analyst. Deine Ausbildung basiert auf:

1. **Eugene Schwartz — Breakthrough Advertising** (das Standardwerk der Direct-Response)
2. **Anthony Camacho** — Direct-Response Facebook Ads, Hooks, VSL-Struktur
3. **Sebastian Szalinski** — DACH Direct-Response, E-Commerce, Conversion-Copy
4. **Carl Weische** — Performance-Marketing DACH, Ad-Copy, Funnel-Texte

{BREAKTHROUGH_ADVERTISING_CONTEXT}

## Aktuelle Inhalte dieser Creator (frisch gescraped):
{creator_insights_text}

---

Deine Aufgabe: Analysiere die eingereichte Copy präzise, tief und actionable.
Denke wie ein erfahrener Direct-Response Texter — nicht wie ein allgemeiner Marketing-Berater.
Jede Kritik muss konkret sein: zeige das Problem UND liefere eine verbesserte Version."""

    user_prompt = f"""Analysiere diese Copy für Levora Skin (Anti-Nagelpilz Laser-Device, ~€49,90, DACH-Markt):

**Titel/Kontext:** {title}

**Copy:**
---
{copy_text}
---

Erstelle eine vollständige Copy-Analyse nach folgendem Format:

## 🎯 Schnell-Bewertung
| Kriterium | Bewertung (1-10) | Kommentar |
|-----------|------------------|-----------|
| Hook-Stärke | X/10 | ... |
| Awareness-Stage-Match | X/10 | ... |
| Emotionale Tiefe | X/10 | ... |
| Proof & Glaubwürdigkeit | X/10 | ... |
| CTA-Klarheit | X/10 | ... |
| Gesamteindruck | X/10 | ... |

## 📊 Awareness-Stage Analyse
Welche Stage wird angesprochen? Passt das zur Zielgruppe?
Was fehlt um die richtige Stage optimal anzusprechen?

## 💪 Was gut funktioniert (mit Begründung)
Liste die Stärken — warum funktionieren sie nach Schwartz/Direct-Response-Prinzipien?

## ⚠️ Was verbessert werden muss
Für jeden Schwachpunkt:
- **Problem:** Was genau ist schwach und warum
- **Fix:** Konkrete verbesserte Version (rewrite)

## 🔥 Hook-Alternativen (5 Varianten)
5 alternative Hooks/Einstiege die stärker wären.
Für jeden: Hook-Text + Warum er funktioniert (welches Desire/Emotion er anspricht)

## ✍️ Verbesserter Rewrite
Vollständiger Rewrite der Copy — verbessert nach allen Kriterien.
Markiere die wichtigsten Änderungen mit einer kurzen Erklärung in Klammern.

## 💡 Empfehlungen nach Creator-Stil
- **Anthony Camacho würde sagen:** ...
- **Sebastian Szalinski würde sagen:** ...
- **Carl Weische würde sagen:** ...

## 🚀 Next Steps
Was sind die 3 wichtigsten konkreten Maßnahmen um diese Copy zu verbessern?"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def post_github_comment(comment_body):
    """Post analysis as a comment on the GitHub issue."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {"body": comment_body}
    r = requests.post(url, json=data, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json().get("html_url", "")


def add_label_done(label="copy-reviewed"):
    """Add a label to mark the issue as reviewed."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{ISSUE_NUMBER}/labels"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Ensure label exists
    requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/labels",
        json={"name": label, "color": "0075ca"},
        headers=headers,
        timeout=10,
    )
    requests.post(url, json={"labels": [label]}, headers=headers, timeout=10)


def main():
    print(f"Copy Review Agent gestartet — Issue #{ISSUE_NUMBER}: {ISSUE_TITLE}")

    if not ISSUE_BODY or len(ISSUE_BODY.strip()) < 20:
        post_github_comment("❌ Kein Copy-Text gefunden. Bitte schreibe die Copy in den Issue-Body.")
        return

    print("\n[1/3] YouTube-Channels der Creators scrapen...")
    insights = get_youtube_insights()
    creator_insights_text = format_creator_insights(insights)
    total_titles = sum(len(d["titles"]) for d in insights.values())
    print(f"  {total_titles} Video-Titel gesammelt")

    print("\n[2/3] Copy analysieren mit Claude...")
    analysis = analyze_copy(ISSUE_BODY, ISSUE_TITLE, creator_insights_text)
    print(f"  {len(analysis)} Zeichen Analyse")

    print("\n[3/3] Analyse als GitHub-Kommentar posten...")
    comment = f"""## 🤖 Copy Review by Levora Copy Agent

> **Analysiert:** {ISSUE_TITLE}
> **Framework:** Breakthrough Advertising (Schwartz) + Anthony Camacho + Sebastian Szalinski + Carl Weische

---

{analysis}

---
*Copy Agent | Levora Skin | {__import__('datetime').datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC*"""

    comment_url = post_github_comment(comment)
    add_label_done()
    print(f"Fertig! Kommentar: {comment_url}")


if __name__ == "__main__":
    main()
