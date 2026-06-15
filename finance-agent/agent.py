import os
import json
import requests
import base64
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "1316660256925670")
PAYPAL_CLIENT_ID = os.environ["PAYPAL_CLIENT_ID"]
PAYPAL_CLIENT_SECRET = os.environ["PAYPAL_CLIENT_SECRET"]
PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "live")  # "live" or "sandbox"
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]

COGS_SINGLE_EUR = 6.11    # NailMed einzeln
COGS_BUNDLE_EUR = 12.19   # Bundle: NailMed x2 + Keratinpfeile + NagelPatch
FEES_RATE = 0.03          # eigene PayPal/Stripe Gebühren
VAT_RATE = 0.19           # deutsche MwSt — im Shopify Brutto-Umsatz enthalten
EXTERNAL_BUDGET_EUR = 500.0  # monatliches externes Budget (netto, MwSt-frei)

SHEET_TITLE = "💰 Levora Finance Tracking"
PAYPAL_BASE = "https://api-m.paypal.com" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com"

HEADERS = [
    "Datum", "Umsatz Brutto (€)", "MwSt 19% (€)", "Umsatz Netto (€)",
    "COGS (€)", "Payment Fees (€)", "Meta Ad Spend (€)", "Reingewinn (€)",
    "Marge %", "ROAS (netto)", "Break-Even ROAS",
    "PayPal Available (€)", "PayPal Holds (€)", "PayPal Gesamt (€)",
    "Externes Budget Rest (€)", "Cash für Ads (€)",
    "Budget Konservativ/Tag (€)", "Budget Aggressiv/Tag (€)",
    "Bestellungen", "Ø COGS/Order (€)",
]


# ── Google Services ───────────────────────────────────────────────────────────

def _google_creds():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    creds.refresh(Request())
    return creds


def get_sheets_service():
    return build("sheets", "v4", credentials=_google_creds())


def get_drive_service():
    return build("drive", "v3", credentials=_google_creds())


def find_or_create_spreadsheet(drive, sheets):
    """Finds existing sheet by title or creates a new one. Returns spreadsheet_id."""
    results = drive.files().list(
        q=f"name='{SHEET_TITLE}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        fields="files(id, name, webViewLink)",
        pageSize=1,
    ).execute()

    files = results.get("files", [])
    if files:
        sid = files[0]["id"]
        print(f"Sheet gefunden: {files[0]['webViewLink']}")
        return sid

    # Create new spreadsheet
    body = {
        "properties": {"title": SHEET_TITLE, "locale": "de_DE"},
        "sheets": [{"properties": {"title": "Finance Log", "index": 0}}],
    }
    new_sheet = sheets.spreadsheets().create(body=body, fields="spreadsheetId,spreadsheetUrl").execute()
    sid = new_sheet["spreadsheetId"]
    print(f"Neues Sheet erstellt: {new_sheet['spreadsheetUrl']}")

    # Write header row
    sheets.spreadsheets().values().update(
        spreadsheetId=sid,
        range="'Finance Log'!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    # Format header row
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.12, "green": 0.12, "blue": 0.12},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
            }
        }, {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        }]},
    ).execute()

    return sid


# ── Currency ──────────────────────────────────────────────────────────────────

def get_eur_usd_rate():
    try:
        r = requests.get("https://api.frankfurter.app/latest?from=USD&to=EUR", timeout=10)
        return r.json()["rates"]["EUR"]
    except Exception:
        return 0.92


# ── PayPal ────────────────────────────────────────────────────────────────────

def get_paypal_token():
    credentials = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        data="grant_type=client_credentials",
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_paypal_balances(token):
    """Returns (available_eur, pending_eur) tuple."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Available balance
    r = requests.get(
        f"{PAYPAL_BASE}/v1/reporting/balances",
        headers=headers,
        params={"currency_code": "EUR", "as_of_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()

    available = 0.0
    for bal in data.get("balances", []):
        if bal.get("currency_code") == "EUR":
            available = float(bal.get("available_balance", {}).get("value", 0))
            break

    # Pending/held: sum transactions with PENDING status in last 30 days
    pending = get_paypal_pending_amount(token, headers)
    return round(available, 2), round(pending, 2)


def get_paypal_pending_amount(token, headers):
    """Sums all pending/held PayPal transactions (last 30 days)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    pending_total = 0.0
    page = 1

    while True:
        params = {
            "start_date": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "transaction_status": "P",  # P = Pending
            "fields": "transaction_info",
            "page_size": 500,
            "page": page,
        }
        r = requests.get(
            f"{PAYPAL_BASE}/v1/reporting/transactions",
            headers=headers,
            params=params,
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        transactions = data.get("transaction_details", [])
        for txn in transactions:
            info = txn.get("transaction_info", {})
            if info.get("transaction_amount", {}).get("currency_code") == "EUR":
                val = float(info["transaction_amount"].get("value", 0))
                if val > 0:
                    pending_total += val
        if page >= data.get("total_pages", 1):
            break
        page += 1

    return round(pending_total, 2)


# ── Shopify ───────────────────────────────────────────────────────────────────

def get_shopify_month_revenue(year, month):
    start = f"{year}-{month:02d}-01T00:00:00+00:00"
    if month == 12:
        end_y, end_m = year + 1, 1
    else:
        end_y, end_m = year, month + 1
    end = f"{end_y}-{end_m:02d}-01T00:00:00+00:00"

    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    orders, page_info = [], None
    while True:
        params = {
            "status": "any",
            "financial_status": "paid",
            "created_at_min": start,
            "created_at_max": end,
            "limit": 250,
            "fields": "id,total_price,line_items",
        }
        if page_info:
            params["page_info"] = page_info
        r = requests.get(url, headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN}, params=params)
        r.raise_for_status()
        batch = r.json().get("orders", [])
        orders.extend(batch)
        link = r.headers.get("Link", "")
        if 'rel="next"' not in link:
            break
        page_info = link.split("page_info=")[1].split(">")[0]

    revenue = round(sum(float(o["total_price"]) for o in orders), 2)
    cogs = round(_calculate_cogs(orders), 2)
    return revenue, len(orders), cogs


def _is_bundle(line_item):
    title = (line_item.get("title") or "").lower()
    variant = (line_item.get("variant_title") or "").lower()
    for kw in ["2er", "duo", "bundle", "2x", "doppel", "zwei", "2-pack", "keratinpfeile", "nagelpatch"]:
        if kw in title or kw in variant:
            return True
    return False


def _calculate_cogs(orders):
    total = 0.0
    for order in orders:
        items = order.get("line_items", [])
        has_bundle_items = any(_is_bundle(i) for i in items)
        if has_bundle_items:
            total += COGS_BUNDLE_EUR
        else:
            for item in items:
                total += COGS_SINGLE_EUR * item.get("quantity", 1)
    return total


# ── Meta ──────────────────────────────────────────────────────────────────────

def get_meta_month_spend(year, month):
    if month == 12:
        end_y, end_m = year + 1, 1
    else:
        end_y, end_m = year, month + 1
    since = f"{year}-{month:02d}-01"
    until = (datetime(end_y, end_m, 1) - timedelta(days=1)).strftime("%Y-%m-%d")

    url = f"https://graph.facebook.com/v19.0/act_{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "fields": "spend",
        "time_range": json.dumps({"since": since, "until": until}),
        "level": "account",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])
    return round(float(data[0].get("spend", 0)), 2) if data else 0.0


def get_meta_today_spend():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://graph.facebook.com/v19.0/act_{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "fields": "spend",
        "time_range": json.dumps({"since": today, "until": today}),
        "level": "account",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])
    return round(float(data[0].get("spend", 0)), 2) if data else 0.0


# ── Sheet Log ─────────────────────────────────────────────────────────────────

def append_log_row(sheets, spreadsheet_id, data: dict):
    now = datetime.now(timezone.utc)

    pp_available = data["pp_available"]
    pp_pending = data["pp_pending"]
    pp_total = round(pp_available + pp_pending, 2)

    revenue_brutto = data["revenue"]
    adspend = data["adspend"]
    cogs = data["cogs"]
    orders = data["orders"]

    vat_amount = round(revenue_brutto * VAT_RATE / (1 + VAT_RATE), 2)
    revenue_netto = round(revenue_brutto - vat_amount, 2)
    fees = round(revenue_netto * FEES_RATE, 2)
    net_profit = round(revenue_netto - adspend - cogs - fees, 2)
    margin_pct = round(net_profit / revenue_netto * 100, 1) if revenue_netto else 0.0
    roas = round(revenue_netto / adspend, 2) if adspend > 0 else 0.0
    cogs_rate = cogs / revenue_netto if revenue_netto else 0.0
    break_even_roas = round(1 / (1 - cogs_rate - FEES_RATE), 2) if (cogs_rate + FEES_RATE) < 1 else 0.0
    cogs_per_order_avg = round(cogs / orders, 2) if orders else COGS_SINGLE_EUR

    daily_orders_avg = max(orders / now.day, 1)
    cogs_7day_reserve = round(daily_orders_avg * cogs_per_order_avg * 7, 2)
    vat_reserve = vat_amount

    next_month = datetime(now.year, now.month + 1 if now.month < 12 else 1, 1, tzinfo=timezone.utc)
    days_left = (next_month - now).days
    days_in_month = now.day + days_left
    external_remaining = round(EXTERNAL_BUDGET_EUR * (days_left / days_in_month), 2)

    reinvestable_profit = max(net_profit, 0.0)
    total_inflows = round(pp_available + reinvestable_profit + external_remaining, 2)
    cash_for_ads = round(total_inflows - vat_reserve - cogs_7day_reserve, 2)
    daily_conservative = round(max(cash_for_ads * 0.50 / 7, 0), 2)
    daily_aggressive = round(max(cash_for_ads * 0.75 / 7, 0), 2)

    row = [
        now.strftime("%d.%m.%Y"),
        revenue_brutto,
        vat_amount,
        revenue_netto,
        cogs,
        fees,
        adspend,
        net_profit,
        margin_pct,
        roas,
        break_even_roas,
        pp_available,
        pp_pending,
        pp_total,
        external_remaining,
        cash_for_ads,
        daily_conservative,
        daily_aggressive,
        orders,
        cogs_per_order_avg,
    ]

    sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="'Finance Log'!A:T",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()

    print(f"Zeile angehängt: {now.strftime('%d.%m.%Y')} | Netto €{revenue_netto} | Gewinn €{net_profit} | Cash für Ads €{cash_for_ads}")
    print(f"Sheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    print(f"Finance Agent gestartet — {now.strftime('%d.%m.%Y %H:%M')} UTC")

    # PayPal
    print("Fetching PayPal balances...")
    try:
        pp_token = get_paypal_token()
        pp_available, pp_pending = get_paypal_balances(pp_token)
    except Exception as e:
        print(f"PayPal Fehler: {e} — setze auf 0")
        pp_available, pp_pending = 0.0, 0.0
    print(f"PayPal: Verfügbar €{pp_available} | Pending €{pp_pending}")

    # Shopify
    print("Fetching Shopify revenue...")
    revenue, orders, cogs = get_shopify_month_revenue(now.year, now.month)
    print(f"Shopify: €{revenue} | {orders} Bestellungen | COGS: €{cogs}")

    # Meta
    print("Fetching Meta ad spend...")
    adspend = get_meta_month_spend(now.year, now.month)
    print(f"Meta: €{adspend} gesamt diesen Monat")

    # Google Sheets — find or create, then append row
    sheets = get_sheets_service()
    drive = get_drive_service()
    spreadsheet_id = find_or_create_spreadsheet(drive, sheets)
    append_log_row(sheets, spreadsheet_id, {
        "pp_available": pp_available,
        "pp_pending": pp_pending,
        "revenue": revenue,
        "cogs": cogs,
        "adspend": adspend,
        "orders": orders,
    })


if __name__ == "__main__":
    main()
