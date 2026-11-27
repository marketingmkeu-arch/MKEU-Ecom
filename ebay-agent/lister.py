"""eBay-Lister: stellt Inserate aus ebay-agent/queue/*.json über die eBay Trading API ein.

Batch-Datei (ebay-agent/queue/<name>.json):
{
  "mode": "check" | "verify" | "live",
  "listings": [
    {
      "sku": "PKM-151-DISPLAY-JP",
      "type": "sealed" | "single",
      "title": "max. 80 Zeichen",
      "price": 129.99,
      "quantity": 1,
      "condition": "NM",                       # nur Einzelkarten: NM / EX / VG / PO
      "specifics": {"Spiel": "Pokémon TCG", "Edition": "151", "Sprache": "Japanisch"},
      "intro": "Ein Satz.",
      "bullets": ["…", "…"],
      "images": ["ebay-agent/queue/<name>/1.jpg"],
      "best_offer": {"auto_accept": 120, "min": 110},   # optional
      "manufacturer": "The Pokémon Company"               # optional, Schlüssel in config.json → manufacturers
    }
  ]
}

check  = nur Zugang testen (GetUser)
revise = bestehende Inserate ändern: {"mode": "revise", "revisions": [{"item_id": "…", "images": [...], "price": 12, "quantity": 2, "title": "…"}]}
verify = alles prüfen und Gebühren anzeigen, nichts wird eingestellt (VerifyAddFixedPriceItem)
live   = Bilder hochladen und Inserate einstellen (AddFixedPriceItem)
"""
import html
import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
QUEUE, DONE, RESULTS = ROOT / "queue", ROOT / "done", ROOT / "results"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
API = "https://api.ebay.com/ws/api.dll"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}
COMPAT = "1349"


def env(name):
    return (os.environ.get(name) or "").strip().strip('"').strip("'").strip()


TOKEN = env("EBAY_AUTH_TOKEN")
# Neue Tokens beginnen mit "v^" und gehen meist in den IAF-Header, alte (AgAAAA…) in den Request-Body.
# Klappt eine Variante nicht (Fehler 931), wird automatisch die andere probiert.
OAUTH = TOKEN.startswith("v^")
_SWITCHED = False


def x(s):
    return html.escape(str(s), quote=False)


def headers(call):
    h = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": COMPAT,
        "X-EBAY-API-DEV-NAME": env("EBAY_DEV_ID"),
        "X-EBAY-API-APP-NAME": env("EBAY_APP_ID"),
        "X-EBAY-API-CERT-NAME": env("EBAY_CERT_ID"),
        "X-EBAY-API-CALL-NAME": call,
        "X-EBAY-API-SITEID": CFG["site_id"],
    }
    if OAUTH:
        h["X-EBAY-API-IAF-TOKEN"] = TOKEN
    return h


def creds():
    return "" if OAUTH else f"<RequesterCredentials><eBayAuthToken>{x(TOKEN)}</eBayAuthToken></RequesterCredentials>"


def parse(resp):
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        hdr = {k: v for k, v in resp.headers.items() if k.lower().startswith(("x-ebay", "content-type", "www-auth"))}
        raise RuntimeError(f"eBay-Antwort nicht lesbar: HTTP {resp.status_code}, Header {hdr}, Inhalt {resp.text[:400]!r}")
    errors = []
    for e in root.findall("e:Errors", NS):
        errors.append({
            "severity": e.findtext("e:SeverityCode", "", NS),
            "code": e.findtext("e:ErrorCode", "", NS),
            "message": e.findtext("e:LongMessage", "", NS) or e.findtext("e:ShortMessage", "", NS),
        })
    return root, root.findtext("e:Ack", "", NS), errors


def call(name, body):
    xml = f'<?xml version="1.0" encoding="utf-8"?><{name}Request xmlns="urn:ebay:apis:eBLBaseComponents">{creds()}<ErrorLanguage>de_DE</ErrorLanguage><WarningLevel>High</WarningLevel>{body}</{name}Request>'
    r = requests.post(API, data=xml.encode("utf-8"), headers={**headers(name), "Content-Type": "text/xml"}, timeout=120)
    root, ack, errors = parse(r)
    global OAUTH, _SWITCHED
    if not _SWITCHED and any(e["code"] in ("931", "21916984") for e in errors):
        _SWITCHED, OAUTH = True, not OAUTH
        return call(name, body)
    return root, ack, errors


def _picture_url(root, errors, how):
    url = root.findtext("e:SiteHostedPictureDetails/e:FullURL", "", NS) if root is not None else ""
    if not url:
        raise RuntimeError(f"{how}: " + ("; ".join(e["message"] for e in errors) or "keine Bild-URL zurückbekommen"))
    return url


MEDIA = "https://apim.ebay.com/commerce/media/v1_beta"


def upload_picture(path):
    """Lädt ein Bild über eBays Media API hoch. Klappt das nicht, bekommt eBay den öffentlichen GitHub-Link,
    den es beim Einstellen selbst kopiert. Gibt (URL, Weg) zurück."""
    p = REPO / path
    problems = []
    try:
        r = requests.post(f"{MEDIA}/image/create_image_from_file", headers={"Authorization": f"Bearer {TOKEN}"},
                          files={"image": (p.name, p.read_bytes(), "image/jpeg")}, timeout=180)
        if r.status_code in (200, 201):
            loc = r.headers.get("Location", "")
            data = r.json() if r.content else {}
            url = data.get("imageUrl")
            if not url and loc:
                g = requests.get(loc, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
                url = g.json().get("imageUrl") if g.ok else None
            if url:
                return url, "eBay Media API"
        problems.append(f"Media API: HTTP {r.status_code} {r.text[:300]!r}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"Media API: {e}")
    sha, repo = os.environ.get("GITHUB_SHA"), os.environ.get("GITHUB_REPOSITORY")
    if sha and repo:
        return f"https://raw.githubusercontent.com/{repo}/{sha}/{path}", "GitHub-Link (" + "; ".join(problems) + ")"
    raise RuntimeError(f"Bild {path}: " + " | ".join(problems))


def description(L):
    bullets = "".join(f"<li>{x(b)}</li>" for b in L.get("bullets", []) if b)
    return (f"<h2>{x(L['title'])}</h2>"
            + (f"<p>{x(L['intro'])}</p>" if L.get("intro") else "")
            + (f"<ul>{bullets}</ul>" if bullets else "")
            + CFG["footer_html"])


def item_xml(L, picture_urls):
    kind = "single" if L.get("type") == "single" else "sealed"
    ship = CFG["shipping"][kind]
    title = L["title"].strip()
    if len(title) > 80:
        raise ValueError(f"Titel zu lang ({len(title)} Zeichen): {title}")
    parts = [
        f"<Title>{x(title)}</Title>",
        f"<Description><![CDATA[{description(L)}]]></Description>",
        f"<PrimaryCategory><CategoryID>{x(L.get('category') or CFG['categories'][kind])}</CategoryID></PrimaryCategory>",
        f"<StartPrice currencyID=\"EUR\">{float(L['price']):.2f}</StartPrice>",
        f"<Quantity>{int(L.get('quantity', 1))}</Quantity>",
        "<ListingDuration>GTC</ListingDuration><ListingType>FixedPriceItem</ListingType>",
        f"<Country>{CFG['country']}</Country><Currency>EUR</Currency>",
        f"<Location>{x(CFG['location'])}</Location><PostalCode>{x(CFG['postal_code'])}</PostalCode>",
        f"<ConditionID>{CFG['condition_ids'][kind]}</ConditionID>",
        f"<DispatchTimeMax>{CFG['dispatch_days']}</DispatchTimeMax>",
    ]
    if L.get("sku"):
        parts.append(f"<SKU>{x(L['sku'])}</SKU>")
    if kind == "single":
        cc = CFG["card_condition"].get(L.get("condition") or "NM", CFG["card_condition"]["NM"])
        parts.append(f"<ConditionDescriptors><ConditionDescriptor><Name>40001</Name><Value>{cc}</Value></ConditionDescriptor></ConditionDescriptors>")
    specs = "".join(
        f"<NameValueList><Name>{x(k)}</Name><Value>{x(v)}</Value></NameValueList>"
        for k, v in (L.get("specifics") or {}).items() if str(v).strip())
    if specs:
        parts.append(f"<ItemSpecifics>{specs}</ItemSpecifics>")
    if picture_urls:
        parts.append("<PictureDetails>" + "".join(f"<PictureURL>{x(u)}</PictureURL>" for u in picture_urls) + "</PictureDetails>")
    parts.append(
        "<ShippingDetails><ShippingType>Flat</ShippingType>"
        f"<ShippingServiceOptions><ShippingServicePriority>1</ShippingServicePriority><ShippingService>{ship['service']}</ShippingService>"
        f"<ShippingServiceCost currencyID=\"EUR\">{ship['cost']}</ShippingServiceCost></ShippingServiceOptions>"
        f"<InternationalShippingServiceOption><ShippingServicePriority>1</ShippingServicePriority><ShippingService>{ship['intl_service']}</ShippingService>"
        f"<ShippingServiceCost currencyID=\"EUR\">{ship['intl_cost']}</ShippingServiceCost><ShipToLocation>Worldwide</ShipToLocation></InternationalShippingServiceOption>"
        "</ShippingDetails><ShipToLocations>Worldwide</ShipToLocations>")
    rp = CFG["returns"]
    parts.append(
        "<ReturnPolicy><ReturnsAcceptedOption>ReturnsAccepted</ReturnsAcceptedOption>"
        f"<ReturnsWithinOption>{rp['days']}</ReturnsWithinOption><RefundOption>MoneyBack</RefundOption>"
        f"<ShippingCostPaidByOption>{rp['paid_by']}</ShippingCostPaidByOption></ReturnPolicy>"
        if rp.get("accepted") else "<ReturnPolicy><ReturnsAcceptedOption>ReturnsNotAccepted</ReturnsAcceptedOption></ReturnPolicy>")
    bo = L.get("best_offer")
    if bo is None and CFG.get("best_offer_default"):
        bo = {}
    if bo is not None and bo is not False:
        parts.append("<BestOfferDetails><BestOfferEnabled>true</BestOfferEnabled></BestOfferDetails>")
        lp = []
        if bo.get("auto_accept"):
            lp.append(f"<BestOfferAutoAcceptPrice currencyID=\"EUR\">{float(bo['auto_accept']):.2f}</BestOfferAutoAcceptPrice>")
        if bo.get("min"):
            lp.append(f"<MinimumBestOfferPrice currencyID=\"EUR\">{float(bo['min']):.2f}</MinimumBestOfferPrice>")
        if lp:
            parts.append("<ListingDetails>" + "".join(lp) + "</ListingDetails>")
    m = CFG.get("manufacturers", {}).get(L.get("manufacturer") or "")
    if m:
        parts.append("<Regulatory><Manufacturer>" + "".join(f"<{k}>{x(v)}</{k}>" for k, v in m.items() if v) + "</Manufacturer></Regulatory>")
    return "<Item>" + "".join(parts) + "</Item>"


def fees(root):
    out = {}
    for f in root.findall("e:Fees/e:Fee", NS):
        v = f.find("e:Fee", NS)
        if v is not None and float(v.text or 0) > 0:
            out[f.findtext("e:Name", "", NS)] = float(v.text)
    return out


def run_check():
    root, ack, errors = call("GetUser", "")
    return {
        "ack": ack,
        "user": root.findtext("e:User/e:UserID", "", NS),
        "site": root.findtext("e:User/e:Site", "", NS),
        "business_type": root.findtext("e:User/e:SellerInfo/e:SellerBusinessType", "", NS),
        "store": root.findtext("e:User/e:SellerInfo/e:StoreOwner", "", NS),
        "errors": errors,
        "diagnose": {
            "token_uebergabe": "IAF-Header" if OAUTH else "eBayAuthToken im Body",
            "token_laenge": len(TOKEN),
            "token_beginnt_mit": TOKEN[:6],
            "app_id_endung": env("EBAY_APP_ID")[-4:],
            "app_id_ist_sandbox": "-SBX-" in env("EBAY_APP_ID"),
            "app_id_ist_production": "-PRD-" in env("EBAY_APP_ID"),
            "dev_id_format_ok": bool(__import__("re").fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", env("EBAY_DEV_ID"))),
            "dev_id_laenge": len(env("EBAY_DEV_ID")),
            "cert_id_beginnt_mit_PRD": env("EBAY_CERT_ID").startswith("PRD-"),
            "cert_id_laenge": len(env("EBAY_CERT_ID")),
            "app_id_laenge": len(env("EBAY_APP_ID")),
            "app_und_cert_vertauscht": env("EBAY_CERT_ID").count("-PRD-") > 0 or env("EBAY_APP_ID").startswith("PRD-"),
            "secrets_vorhanden": {n: bool(env(n)) for n in ("EBAY_APP_ID", "EBAY_DEV_ID", "EBAY_CERT_ID", "EBAY_AUTH_TOKEN")},
        },
    }


def run_shipping_list():
    root, ack, errors = call("GeteBayDetails", "<DetailName>ShippingServiceDetails</DetailName>")
    out = []
    for d in root.findall("e:ShippingServiceDetails", NS):
        if d.findtext("e:ValidForSellingFlow", "", NS) != "true":
            continue
        out.append({
            "code": d.findtext("e:ShippingService", "", NS),
            "name": d.findtext("e:Description", "", NS),
            "international": d.findtext("e:InternationalService", "false", NS) == "true",
            "carrier": d.findtext("e:ShippingCarrier", "", NS),
            "tracking": d.findtext("e:ShippingCategory", "", NS),
        })
    return {"ack": ack, "errors": errors, "services": out}


LOG = ROOT / "inserate.csv"


def log_listing(L, res):
    """Hängt jedes Live-Inserat an ebay-agent/inserate.csv an (zum Mitzählen der Gratis-Inserate)."""
    import csv
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(["datum", "item_id", "link", "titel", "preis", "menge", "gebuehr_eur"])
        w.writerow([datetime.now(timezone.utc).date().isoformat(), res["item_id"], res["url"], L.get("title"),
                    f"{float(L['price']):.2f}", L.get("quantity", 1), f"{sum(res.get('fees', {}).values()):.2f}"])


def run_revise(R):
    """Ändert ein bestehendes Inserat. R: {"item_id", optional "images", "price", "quantity", "title"}."""
    res = {"item_id": R.get("item_id"), "aenderung": [k for k in ("images", "price", "quantity", "title") if k in R]}
    try:
        parts = [f"<ItemID>{x(R['item_id'])}</ItemID>"]
        if "title" in R:
            parts.append(f"<Title>{x(R['title'])}</Title>")
        if "price" in R:
            parts.append(f"<StartPrice currencyID=\"EUR\">{float(R['price']):.2f}</StartPrice>")
        if "quantity" in R:
            parts.append(f"<Quantity>{int(R['quantity'])}</Quantity>")
        if "images" in R:
            up = [upload_picture(p) for p in R["images"]]
            res["pictures"] = [{"url": u, "weg": w} for u, w in up]
            parts.append("<PictureDetails>" + "".join(f"<PictureURL>{x(u)}</PictureURL>" for u, _ in up) + "</PictureDetails>")
        root, ack, errors = call("ReviseFixedPriceItem", "<Item>" + "".join(parts) + "</Item>")
        res.update({"ack": ack, "errors": errors, "url": f"https://www.ebay.de/itm/{R['item_id']}"})
    except Exception as e:  # noqa: BLE001
        res.update({"ack": "Failure", "errors": [{"severity": "Error", "code": "local", "message": str(e)}]})
    return res


def run_listing(L, mode):
    res = {"sku": L.get("sku"), "title": L.get("title"), "price": L.get("price")}
    try:
        up = [upload_picture(p) for p in L.get("images", [])]
        pics = [u for u, _ in up]
        res["pictures"] = [{"url": u, "weg": w} for u, w in up]
        callname = "AddFixedPriceItem" if mode == "live" else "VerifyAddFixedPriceItem"
        root, ack, errors = call(callname, item_xml(L, pics))
        res.update({"ack": ack, "errors": errors, "fees": fees(root)})
        item_id = root.findtext("e:ItemID", "", NS)
        if mode == "live" and item_id:
            res["item_id"] = item_id
            res["url"] = f"https://www.ebay.de/itm/{item_id}"
            log_listing(L, res)
    except Exception as e:  # noqa: BLE001
        res.update({"ack": "Failure", "errors": [{"severity": "Error", "code": "local", "message": str(e)}]})
    return res


def main():
    batches = sorted(QUEUE.glob("*.json"))
    if not batches:
        print("Keine Batches in der Warteschlange.")
        return
    RESULTS.mkdir(exist_ok=True)
    DONE.mkdir(exist_ok=True)
    call("GetUser", "")  # legt fest, wie das Token übergeben wird, bevor Bilder hochgeladen werden
    failed = False
    for b in batches:
        data = json.loads(b.read_text(encoding="utf-8"))
        mode = data.get("mode", "verify")
        print(f"== {b.name} ({mode})")
        out = {"batch": b.stem, "mode": mode, "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if mode == "revise":
            out["revisions"] = []
            for R in data.get("revisions", []):
                r = run_revise(R)
                out["revisions"].append(r)
                print(f"- {r['ack']:8} {r.get('url')}")
                failed |= r["ack"] not in ("Success", "Warning")
        elif mode == "shipping":
            out["shipping"] = run_shipping_list()
            print(f"{len(out['shipping']['services'])} Versandarten")
        elif mode == "check":
            out["check"] = run_check()
            print(json.dumps(out["check"], ensure_ascii=False, indent=1))
            failed |= out["check"]["ack"] not in ("Success", "Warning")
        else:
            out["listings"] = []
            for L in data.get("listings", []):
                r = run_listing(L, mode)
                out["listings"].append(r)
                print(f"- {r['ack']:8} {r.get('title')}  {r.get('url', '')}")
                for e in r.get("errors", []):
                    print(f"    {e['severity']} {e['code']}: {e['message']}")
                failed |= r["ack"] not in ("Success", "Warning")
        (RESULTS / f"{b.stem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.move(str(b), str(DONE / b.name))
        img_dir = QUEUE / b.stem
        if img_dir.is_dir():
            shutil.move(str(img_dir), str(DONE / b.stem))
    if failed:
        print("Mindestens ein Eintrag ist fehlgeschlagen, Details in ebay-agent/results/.")


if __name__ == "__main__":
    sys.exit(main())
