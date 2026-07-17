"""Wohnungssuche-Agent: Eigentumswohnungen in Duesseldorf auf Kleinanzeigen finden.

Kleinanzeigen blockiert automatisierte Zugriffe zuverlaessig (Bot-Schutz, 403).
Dieses Tool umgeht das nicht. Es baut die korrekt gefilterten Suchlinks,
versucht optional einen einzelnen hoeflichen Abruf und faellt ansonsten auf
manuellen Import gespeicherter Seiten zurueck (siehe README.md).
"""

import argparse
import json
import re
import time
import webbrowser
from datetime import date, timedelta, datetime
from pathlib import Path
from urllib import robotparser

import requests
from bs4 import BeautifulSoup

STADTTEILE = {
    "Bilk": "bilk",
    "Unterbilk": "unterbilk",
    "Friedrichstadt": "friedrichstadt",
    "Pempelfort": "pempelfort",
    "Stadtmitte": "stadtmitte",
    "Golzheim": "golzheim",
    "Oberkassel": "oberkassel",
    "Flehe": "flehe",
    "Flingern-Nord": "flingern-nord",
}

MAX_PREIS = 300_000
# c196 = Kategorie "Wohnung kaufen" (Eigentumswohnungen), l2068 = Ort Duesseldorf.
# Empirisch bestaetigt ueber kleinanzeigen.de Suchergebnisse (Juli 2026).
CATEGORY_LOCATION = "k0c196l2068"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = BASE_DIR / "imports"
LISTINGS_FILE = DATA_DIR / "listings.json"
SEEN_FILE = DATA_DIR / "seen.json"
BERICHT_FILE = DATA_DIR / "bericht.md"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Wohnungssuche-Tool/1.0; manuelle Nutzung)"
}

# Nur eindeutige Ausschluesse. Bewusst kein generisches "haus"-Muster, da
# Eigentumswohnungs-Anzeigen haeufig Woerter wie "Hausgeld" oder "im Haus"
# enthalten und sonst faelschlich ausgeschlossen wuerden.
EXCLUDE_PATTERNS = [
    r"\bgarage\b",
    r"\bstellplatz\b",
    r"\btiefgaragenstellplatz\b",
    r"\bgrundstück\b",
    r"\bbauplatz\b",
    r"\bgewerbeeinheit\b",
    r"\bgewerbefläche\b",
    r"\bbürofläche\b",
    r"\bladenlokal\b",
    r"\bferienwohnung\b",
    r"\bferienimmobilie\b",
    r"\bteilverkauf\b",
    r"\beinfamilienhaus\b",
    r"\bmehrfamilienhaus\b",
    r"\breihenhaus\b",
    r"\bdoppelhaush",
    r"\bstadthaus\b",
    r"\bvilla\b",
    r"\bmietwohnung\b",
    r"\bzu vermieten\b",
]


def build_url(stadtteil_slug):
    return (
        f"https://www.kleinanzeigen.de/s-wohnung-kaufen/duesseldorf/"
        f"{stadtteil_slug}/preis:0:{MAX_PREIS}/{CATEGORY_LOCATION}"
    )


def build_urls():
    return {name: build_url(slug) for name, slug in STADTTEILE.items()}


def privat_url(url):
    return url.replace(f"/{CATEGORY_LOCATION}", f"/privat/{CATEGORY_LOCATION}")


def extract_ad_id(url):
    match = re.search(r"/(\d{6,})-\d+-\d+", url)
    if match:
        return match.group(1)
    match = re.search(r"(\d{6,})", url)
    return match.group(1) if match else None


def extract_price(text):
    match = re.search(r"(\d{1,3}(?:\.\d{3})*)\s?€", text)
    if not match:
        return None
    return int(match.group(1).replace(".", ""))


def extract_qm(text):
    match = re.search(r"(\d+(?:[.,]\d+)?)\s?m²", text)
    return float(match.group(1).replace(",", ".")) if match else None


def extract_zimmer(text):
    match = re.search(r"(\d+(?:[.,]\d+)?)\s?Zimmer", text, re.IGNORECASE)
    return float(match.group(1).replace(",", ".")) if match else None


def detect_anbieter(text):
    t = text.lower()
    if "gewerblicher anbieter" in t or "gewerblich" in t:
        return "gewerblich"
    if "privater anbieter" in t or re.search(r"\bprivat\b", t):
        return "privat"
    return "nicht angegeben"


def detect_provisionsfrei(text):
    t = text.lower()
    if any(k in t for k in ("provisionsfrei", "ohne käuferprovision", "keine provision", "courtagefrei")):
        return True
    if any(k in t for k in ("käuferprovision", "provision", "courtage")):
        return False
    return None


def detect_bezugsfrei(text):
    t = text.lower()
    if any(k in t for k in ("bezugsfrei", "unvermietet", "frei ab")):
        return True
    if any(k in t for k in ("vermietet", "kapitalanlage")):
        return False
    return None


def detect_balkon(text):
    t = text.lower()
    if any(k in t for k in ("balkon", "loggia", "terrasse")):
        return True
    return None


def detect_datum(text):
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    if re.search(r"\bheute\b", text, re.IGNORECASE):
        return date.today().isoformat()
    if re.search(r"\bgestern\b", text, re.IGNORECASE):
        return (date.today() - timedelta(days=1)).isoformat()
    return None


def is_kapitalanlage_ausschluss(text):
    t = text.lower()
    if "kapitalanlage" not in t:
        return False
    if any(k in t for k in ("bezugsfrei", "unvermietet")):
        return False
    return "vermietet" in t


def is_relevant(text, stadtteil_name):
    t = text.lower()
    if stadtteil_name.lower() not in t:
        return False
    if any(re.search(p, t) for p in EXCLUDE_PATTERNS):
        return False
    if is_kapitalanlage_ausschluss(t):
        return False
    price = extract_price(text)
    if price is not None and price > MAX_PREIS:
        return False
    return True


def build_listing(url, text, title, stadtteil_name, quelle):
    return {
        "id": extract_ad_id(url),
        "titel": title,
        "kaufpreis": extract_price(text),
        "stadtteil": stadtteil_name,
        "wohnflaeche_qm": extract_qm(text),
        "zimmer": extract_zimmer(text),
        "anbieter": detect_anbieter(text),
        "provisionsfrei": detect_provisionsfrei(text),
        "bezugsfrei": detect_bezugsfrei(text),
        "balkon": detect_balkon(text),
        "url": url,
        "datum": detect_datum(text),
        "quelle": quelle,
    }


def parse_search_html(html, stadtteil_name, quelle):
    soup = BeautifulSoup(html, "lxml")
    listings = []
    seen_ids = set()
    for link in soup.find_all("a", href=re.compile(r"/s-anzeige/")):
        href = link.get("href")
        if not href:
            continue
        url = href if href.startswith("http") else "https://www.kleinanzeigen.de" + href
        ad_id = extract_ad_id(url)
        if not ad_id or ad_id in seen_ids:
            continue
        container = link.find_parent("article") or link.find_parent("li") or link
        text = container.get_text(" ", strip=True)
        if not is_relevant(text, stadtteil_name):
            continue
        title = link.get_text(" ", strip=True) or text[:80]
        seen_ids.add(ad_id)
        listings.append(build_listing(url, text, title, stadtteil_name, quelle))
    return listings


def parse_imported_html(html, filename):
    soup = BeautifulSoup(html, "lxml")
    listings = []
    seen_ids = set()
    for link in soup.find_all("a", href=re.compile(r"/s-anzeige/")):
        href = link.get("href")
        if not href:
            continue
        url = href if href.startswith("http") else "https://www.kleinanzeigen.de" + href
        ad_id = extract_ad_id(url)
        if not ad_id or ad_id in seen_ids:
            continue
        container = link.find_parent("article") or link.find_parent("li") or link
        text = container.get_text(" ", strip=True)

        matched_stadtteil = None
        for name in STADTTEILE:
            if name.lower() in text.lower():
                matched_stadtteil = name
                break
        if not matched_stadtteil:
            normalized_filename = filename.lower().replace("-", "").replace("_", "")
            for name in STADTTEILE:
                if name.lower().replace("-", "") in normalized_filename:
                    matched_stadtteil = name
                    break
        if not matched_stadtteil:
            continue
        if not is_relevant(text, matched_stadtteil):
            continue

        title = link.get_text(" ", strip=True) or text[:80]
        seen_ids.add(ad_id)
        listings.append(build_listing(url, text, title, matched_stadtteil, "manuell"))
    return listings


def robots_allowed(url):
    rp = robotparser.RobotFileParser()
    rp.set_url("https://www.kleinanzeigen.de/robots.txt")
    try:
        rp.read()
    except Exception:
        return True
    return rp.can_fetch("*", url)


def fetch_url(url):
    if not robots_allowed(url):
        return None, "robots.txt verbietet das Abrufen dieser Seite."
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f"Netzwerkfehler: {e}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code} – automatischer Abruf blockiert oder nicht moeglich."
    lowered = resp.text.lower()
    if any(k in lowered for k in ("captcha", "datadome", "unusual traffic", "access denied")):
        return None, "Schutzmassnahme/Captcha erkannt – automatischer Abruf wird abgebrochen."
    return resp.text, None


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_listings(new_listings):
    store = load_json(LISTINGS_FILE, {})
    now = datetime.now().isoformat(timespec="seconds")
    added = 0
    for listing in new_listings:
        key = listing["id"]
        if key is None:
            continue
        if key in store:
            for field, value in listing.items():
                if value is not None:
                    store[key][field] = value
            store[key]["zuletzt_gesehen"] = now
        else:
            listing["zuerst_gesehen"] = now
            listing["zuletzt_gesehen"] = now
            store[key] = listing
            added += 1
    save_json(LISTINGS_FILE, store)
    return added, len(new_listings)


def sort_key(listing):
    privat = listing.get("anbieter") == "privat"
    provisionsfrei = listing.get("provisionsfrei") is True
    bezugsfrei = listing.get("bezugsfrei") is True
    balkon = listing.get("balkon") is True
    datum = listing.get("datum") or ""
    return (
        not (privat and provisionsfrei),
        not privat,
        not provisionsfrei,
        not bezugsfrei,
        not balkon,
        "".join(reversed(datum)) if datum else "",
    )


def fmt_price(value):
    return f"{value:,.0f} €".replace(",", ".") if value is not None else "nicht angegeben"


def fmt_qm(value):
    return f"{value:g} m²" if value is not None else "nicht angegeben"


def fmt_zimmer(value):
    return f"{value:g} Zimmer" if value is not None else "nicht angegeben"


def fmt_bool(value, true_label, false_label):
    if value is True:
        return true_label
    if value is False:
        return false_label
    return "nicht angegeben"


def cmd_urls(args):
    for name, url in build_urls().items():
        print(f"{name}: {url}")
        if args.privat:
            print(f"  nur privat: {privat_url(url)}")
    if args.open:
        for url in build_urls().values():
            webbrowser.open(url)
            if args.privat:
                webbrowser.open(privat_url(url))


def cmd_fetch(args):
    urls = build_urls()
    names = list(urls.keys())
    print(f"Teste automatischen Abruf mit '{names[0]}' als Probe ...")
    html, err = fetch_url(urls[names[0]])
    if err:
        print(f"Automatischer Abruf nicht moeglich: {err}")
        print("Kleinanzeigen blockiert vermutlich automatisierte Zugriffe (Bot-Schutz).")
        print("Weiter mit manuellem Import: 'python agent.py urls --open' und danach")
        print("die relevanten Seiten speichern und mit 'python agent.py import' einlesen.")
        return
    total_added = 0
    all_listings = parse_search_html(html, names[0], "automatisch")
    added, found = merge_listings(all_listings)
    total_added += added
    print(f"  {names[0]}: {found} passende Anzeigen gefunden, {added} neu gespeichert.")
    for name in names[1:]:
        time.sleep(2)
        html, err = fetch_url(urls[name])
        if err:
            print(f"  {name}: automatischer Abruf abgebrochen ({err}).")
            continue
        listings = parse_search_html(html, name, "automatisch")
        added, found = merge_listings(listings)
        total_added += added
        print(f"  {name}: {found} passende Anzeigen gefunden, {added} neu gespeichert.")
    print(f"Fertig. {total_added} neue Anzeigen im Datenbestand.")


def cmd_import(args):
    folder = Path(args.pfad) if args.pfad else IMPORTS_DIR
    html_files = sorted(list(folder.glob("*.html")) + list(folder.glob("*.htm")))
    if not html_files:
        print(f"Keine HTML-Dateien in {folder} gefunden.")
        print("Speichere zuerst gefilterte Kleinanzeigen-Seiten dort ab (siehe README.md).")
        return
    total_added = 0
    for path in html_files:
        html = path.read_text(encoding="utf-8", errors="ignore")
        listings = parse_imported_html(html, path.name)
        added, found = merge_listings(listings)
        total_added += added
        print(f"{path.name}: {found} passende Anzeigen erkannt, {added} neu gespeichert.")
    print(f"Fertig. {total_added} neue Anzeigen aus manuellem Import gespeichert.")


def render_console(listings):
    print(f"\n{len(listings)} passende Anzeigen (sortiert nach Prioritaet):\n")
    for i, listing in enumerate(listings, 1):
        marker = "[NEU]" if listing.get("neu") else "[bereits gesehen]"
        print(f"{i}. {marker} {listing.get('titel', 'nicht angegeben')}")
        print(f"   Kaufpreis:      {fmt_price(listing.get('kaufpreis'))}")
        print(f"   Stadtteil:      {listing.get('stadtteil', 'nicht angegeben')}")
        print(f"   Wohnflaeche:    {fmt_qm(listing.get('wohnflaeche_qm'))}")
        print(f"   Zimmer:         {fmt_zimmer(listing.get('zimmer'))}")
        print(f"   Anbieter:       {listing.get('anbieter', 'nicht angegeben')}")
        print(f"   Provision:      {fmt_bool(listing.get('provisionsfrei'), 'provisionsfrei', 'provisionspflichtig')}")
        print(f"   Vermietung:     {fmt_bool(listing.get('bezugsfrei'), 'bezugsfrei', 'vermietet')}")
        print(f"   Balkon/Terrasse:{fmt_bool(listing.get('balkon'), 'vorhanden', 'nicht angegeben')}")
        print(f"   Link:           {listing.get('url')}")
        print()


def render_markdown(listings):
    lines = [
        "# Wohnungssuche Duesseldorf – Bericht",
        "",
        f"Stand: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| # | Status | Titel | Kaufpreis | Stadtteil | Wohnflaeche | Zimmer | Anbieter | Provision | Vermietung | Balkon | Link |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, listing in enumerate(listings, 1):
        status = "NEU" if listing.get("neu") else "gesehen"
        lines.append(
            "| {i} | {status} | {titel} | {preis} | {stadtteil} | {qm} | {zimmer} | {anbieter} | {provision} | {vermietung} | {balkon} | [Anzeige]({url}) |".format(
                i=i,
                status=status,
                titel=(listing.get("titel") or "nicht angegeben").replace("|", "/"),
                preis=fmt_price(listing.get("kaufpreis")),
                stadtteil=listing.get("stadtteil", "nicht angegeben"),
                qm=fmt_qm(listing.get("wohnflaeche_qm")),
                zimmer=fmt_zimmer(listing.get("zimmer")),
                anbieter=listing.get("anbieter", "nicht angegeben"),
                provision=fmt_bool(listing.get("provisionsfrei"), "provisionsfrei", "provisionspflichtig"),
                vermietung=fmt_bool(listing.get("bezugsfrei"), "bezugsfrei", "vermietet"),
                balkon=fmt_bool(listing.get("balkon"), "vorhanden", "nicht angegeben"),
                url=listing.get("url"),
            )
        )
    DATA_DIR.mkdir(exist_ok=True)
    BERICHT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_report(args):
    store = load_json(LISTINGS_FILE, {})
    if not store:
        print("Keine Anzeigen im Datenbestand. Zuerst 'fetch' oder 'import' ausfuehren.")
        return
    seen_ids = set(load_json(SEEN_FILE, []))
    listings = list(store.values())
    for listing in listings:
        listing["neu"] = listing["id"] not in seen_ids
    listings.sort(key=sort_key)
    render_console(listings)
    render_markdown(listings)
    save_json(SEEN_FILE, sorted(store.keys()))
    neu_count = sum(1 for listing in listings if listing["neu"])
    print(f"{neu_count} davon neu seit dem letzten Bericht.")
    print(f"Bericht gespeichert unter {BERICHT_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Wohnungssuche-Agent fuer Kleinanzeigen (Duesseldorf).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_urls = sub.add_parser("urls", help="Gefilterte Suchlinks anzeigen/oeffnen.")
    p_urls.add_argument("--open", action="store_true", help="Links im Standardbrowser oeffnen.")
    p_urls.add_argument("--privat", action="store_true", help="Zusaetzlich Nur-privat-Links anzeigen.")
    p_urls.set_defaults(func=cmd_urls)

    p_fetch = sub.add_parser("fetch", help="Best-effort automatischer Abruf (bricht bei Schutzmassnahmen ab).")
    p_fetch.set_defaults(func=cmd_fetch)

    p_import = sub.add_parser("import", help="Manuell gespeicherte HTML-Seiten aus imports/ einlesen.")
    p_import.add_argument("--pfad", help="Ordner mit HTML-Dateien (Standard: imports/).")
    p_import.set_defaults(func=cmd_import)

    p_report = sub.add_parser("report", help="Sortierte Uebersicht anzeigen und Bericht schreiben.")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
