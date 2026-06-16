import os
import json
import requests
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1316660256925670")
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
SPREADSHEET_ID = "16ht9M4uxDZrRi2uWg2ohzZJbQUEkEPHG9tLAFrofzB4"

COGS_1_USD = 7.74
COGS_2_EUR = 12.17
FEES_RATE = 0.03

MONTHS_DE = ["JANUAR","FEBRUAR","MÄRZ","APRIL","MAI","JUNI",
             "JULI","AUGUST","SEPTEMBER","OKTOBER","NOVEMBER","DEZEMBER"]


def get_sheets_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


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
    if not r.ok:
        print(f"Meta API Fehler {r.status_code}: {r.text}")
    r.raise_for_status()
    data = r.json().get("data", [])
    if data:
        return round(float(data[0].get("spend", 0)), 2)
    return 0.0


def write_to_sheet(service, date_iso, revenue, cogs, adspend_fb, fees, order_count):
    d = datetime.fromisoformat(date_iso)
    tab_name = f"{MONTHS_DE[d.month - 1]} {d.year}"
    date_str = d.strftime("%d.%m.%Y")

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{tab_name}'!A:A",
        valueRenderOption="FORMATTED_VALUE",
    ).execute()

    col_a = result.get("values", [])
    print(f"Tab: {tab_name} | Suche: {date_str} | {len(col_a)} Zeilen")
    print(f"Erste 5 Werte: {[r[0] if r else '' for r in col_a[:5]]}")

    for i, row in enumerate(col_a):
        if row and row[0] == date_str:
            row_num = i + 1
            updates = [
                {"range": f"'{tab_name}'!B{row_num}", "values": [[revenue]]},
                {"range": f"'{tab_name}'!C{row_num}", "values": [[cogs]]},
                {"range": f"'{tab_name}'!D{row_num}", "values": [[adspend_fb]]},
                {"range": f"'{tab_name}'!G{row_num}", "values": [[fees]]},
                {"range": f"'{tab_name}'!L{row_num}", "values": [[order_count]]},
            ]
            body = {"valueInputOption": "RAW", "data": updates}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body=body
            ).execute()
            print(f"Erfolgreich eingetragen in Zeile {row_num}")
            return

    print(f"Datum nicht gefunden: {date_str}")


def main():
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    date_iso = yesterday.strftime("%Y-%m-%d")

    print(f"Leon (P&L Agent) gestartet für {date_iso}")

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

    service = get_sheets_service()
    write_to_sheet(service, date_iso, revenue, cogs, adspend_fb, fees, order_count)


if __name__ == "__main__":
    main()
