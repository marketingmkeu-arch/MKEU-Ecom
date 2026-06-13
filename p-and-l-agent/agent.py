import os
import json
import requests
from datetime import datetime, timedelta, timezone

SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1316660256925670")
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
SHEET_SECRET = "levora-sheet-2026"

COGS_1_USD = 7.74
COGS_2_EUR = 12.17
FEES_RATE = 0.03


def get_eur_usd_rate():
    try:
        r = requests.get("https://api.frankfurter.app/latest?from=USD&to=EUR", timeout=10)
        return r.json()["rates"]["EUR"]
    except Exception:
        return 0.92


def get_shopify_orders(date_str):
    start = f"{date_str}T00:00:00+00:00"
    end = f"{date_str}T23:59:59+00:00"
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    params = {
        "status": "any",
        "created_at_min": start,
        "created_at_max": end,
        "limit": 250,
        "fields": "id,total_price,line_items",
    }
    r = requests.get(url, headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN}, params=params)
    r.raise_for_status()
    return r.json().get("orders", [])


def is_bundle(line_item):
    title = (line_item.get("title") or "").lower()
    variant = (line_item.get("variant_title") or "").lower()
    for kw in ["2er", "duo", "bundle", "2x", "doppel", "zwei", "2-pack"]:
        if kw in title or kw in variant:
            return True
    return False


def calculate_cogs(orders, eur_rate):
    total = 0.0
    for order in orders:
        for item in order.get("line_items", []):
            qty = item.get("quantity", 1)
            if is_bundle(item):
                total += COGS_2_EUR * qty
            else:
                total += COGS_1_USD * eur_rate * qty
    return round(total, 2)


def get_meta_adspend(date_str):
    url = f"https://graph.facebook.com/v19.0/act_{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "fields": "spend",
        "time_range": json.dumps({"since": date_str, "until": date_str}),
        "level": "account",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])
    if data:
        return round(float(data[0].get("spend", 0)), 2)
    return 0.0


def post_to_sheet(date_iso, revenue, cogs, adspend_fb, fees, order_count):
    payload = {
        "secret": SHEET_SECRET,
        "date": date_iso,
        "revenue": revenue,
        "cogs": cogs,
        "adspend_fb": adspend_fb,
        "fees": fees,
        "order_count": order_count,
    }
    r = requests.post(SHEET_WEBHOOK_URL, json=payload, timeout=15)
    return r.text


def main():
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    date_iso = yesterday.strftime("%Y-%m-%d")

    print(f"P&L Agent gestartet für {date_iso}")

    eur_rate = get_eur_usd_rate()
    print(f"USD→EUR Rate: {eur_rate}")

    orders = get_shopify_orders(date_iso)
    revenue = round(sum(float(o["total_price"]) for o in orders), 2)
    order_count = len(orders)
    cogs = calculate_cogs(orders, eur_rate)
    fees = round(revenue * FEES_RATE, 2)
    print(f"Shopify: {order_count} Orders | Revenue: €{revenue} | COGS: €{cogs} | Fees: €{fees}")

    adspend_fb = get_meta_adspend(date_iso)
    print(f"Meta Adspend: €{adspend_fb}")

    profit = round(revenue - cogs - adspend_fb - fees, 2)
    roas = round(revenue / adspend_fb, 2) if adspend_fb > 0 else 0
    print(f"Profit: €{profit} | ROAS: {roas}")

    result = post_to_sheet(date_iso, revenue, cogs, adspend_fb, fees, order_count)
    print(f"Sheet Antwort: {result}")


if __name__ == "__main__":
    main()
