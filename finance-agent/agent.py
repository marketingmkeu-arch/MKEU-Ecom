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
SPREADSHEET_ID = "16ht9M4uxDZrRi2uWg2ohzZJbQUEkEPHG9tLAFrofzB4"

COGS_SINGLE_EUR = 6.11    # NailMed einzeln
COGS_BUNDLE_EUR = 12.19   # Bundle: NailMed x2 + Keratinpfeile + NagelPatch
FEES_RATE = 0.03          # eigene PayPal/Stripe Gebühren
VAT_RATE = 0.19           # deutsche MwSt — im Shopify Brutto-Umsatz enthalten
EXTERNAL_BUDGET_EUR = 500.0  # monatliches externes Budget (netto, MwSt-frei)
MONTHS_DE = ["JANUAR","FEBRUAR","MÄRZ","APRIL","MAI","JUNI",
             "JULI","AUGUST","SEPTEMBER","OKTOBER","NOVEMBER","DEZEMBER"]

TAB_NAME = "💰 FINANCE DASHBOARD"
PAYPAL_BASE = "https://api-m.paypal.com" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com"


# ── Google Sheets ─────────────────────────────────────────────────────────────

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


def ensure_tab_exists(service):
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = [s["properties"]["title"] for s in meta["sheets"]]
    if TAB_NAME not in sheets:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": TAB_NAME}}}]},
        ).execute()
        print(f"Tab '{TAB_NAME}' erstellt.")
    else:
        print(f"Tab '{TAB_NAME}' existiert bereits.")


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


# ── Sheet Builder ─────────────────────────────────────────────────────────────

def rgb(r, g, b):
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def get_sheet_id(service):
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for s in meta["sheets"]:
        if s["properties"]["title"] == TAB_NAME:
            return s["properties"]["sheetId"]
    return None


def col_idx(letter):
    return ord(letter.upper()) - ord("A")


def build_cell_format_requests(sheet_id):
    """Returns formatting batchUpdate requests for the dashboard."""
    requests_list = []

    def header_row(row, text_color, bg_color):
        return {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row, "endRowIndex": row + 1,
                           "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg_color,
                        "textFormat": {"bold": True, "fontSize": 11,
                                       "foregroundColor": text_color},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"top": 6, "bottom": 6, "left": 10},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)",
            }
        }

    def value_row(start_row, end_row):
        return {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row, "endRowIndex": end_row,
                           "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": rgb(250, 250, 250),
                        "textFormat": {"fontSize": 10},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"top": 4, "bottom": 4, "left": 10},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)",
            }
        }

    # Section headers
    dark_bg = rgb(30, 30, 30)
    white = rgb(255, 255, 255)
    blue_bg = rgb(25, 103, 210)
    green_bg = rgb(11, 128, 67)
    orange_bg = rgb(230, 120, 20)
    purple_bg = rgb(100, 50, 200)

    requests_list.append(header_row(0, white, dark_bg))    # Title
    requests_list.append(header_row(2, white, blue_bg))    # PayPal       rows 3-9
    requests_list.append(value_row(3, 9))
    requests_list.append(header_row(9, white, green_bg))   # P&L          rows 10-21
    requests_list.append(value_row(10, 22))
    requests_list.append(header_row(22, white, orange_bg)) # Cash Flow    rows 23-33
    requests_list.append(value_row(23, 34))
    requests_list.append(header_row(34, white, purple_bg)) # Ad Budget    rows 35-41
    requests_list.append(value_row(35, 41))

    # Column widths
    requests_list.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 280},
            "fields": "pixelSize",
        }
    })
    requests_list.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 180},
            "fields": "pixelSize",
        }
    })
    requests_list.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 4},
            "properties": {"pixelSize": 160},
            "fields": "pixelSize",
        }
    })

    return requests_list


def write_dashboard(service, data: dict):
    sheet_id = get_sheet_id(service)
    now = datetime.now(timezone.utc)
    month_name = MONTHS_DE[now.month - 1]

    pp_available = data["pp_available"]
    pp_pending = data["pp_pending"]
    pp_total = round(pp_available + pp_pending, 2)

    revenue_brutto = data["revenue"]   # Shopify Umsatz inkl. 19% MwSt
    adspend = data["adspend"]
    cogs = data["cogs"]
    orders = data["orders"]
    today_spend = data["today_spend"]

    # MwSt herausrechnen — Brutto enthält MwSt, Netto ist die echte Einnahme
    vat_amount = round(revenue_brutto * VAT_RATE / (1 + VAT_RATE), 2)  # = Brutto * 19/119
    revenue_netto = round(revenue_brutto - vat_amount, 2)

    # P&L auf Netto-Basis
    fees = round(revenue_netto * FEES_RATE, 2)
    net_profit = round(revenue_netto - adspend - cogs - fees, 2)
    margin_pct = round(net_profit / revenue_netto * 100, 1) if revenue_netto else 0.0
    roas = round(revenue_netto / adspend, 2) if adspend > 0 else 0.0

    # Break-even ROAS auf Netto-Basis
    cogs_rate = cogs / revenue_netto if revenue_netto else 0.0
    break_even_roas = round(1 / (1 - cogs_rate - FEES_RATE), 2) if (cogs_rate + FEES_RATE) < 1 else 0.0

    # Tages-Durchschnitte
    daily_orders_avg = max(orders / now.day, 1)
    cogs_per_order_avg = cogs / orders if orders else COGS_SINGLE_EUR
    daily_profit_avg = round(net_profit / now.day, 2) if net_profit > 0 else 0.0

    # Verbleibende Tage im Monat
    next_month = datetime(now.year, now.month + 1 if now.month < 12 else 1, 1, tzinfo=timezone.utc)
    days_left = (next_month - now).days
    days_in_month = now.day + days_left

    # Hochrechnung Gewinn bis Monatsende (linear, basierend auf bisherigem Schnitt)
    profit_projected_rest = round(daily_profit_avg * days_left, 2)

    # COGS Reserve für 7 Tage (laufende Lieferantenzahlungen)
    cogs_7day_reserve = round(daily_orders_avg * cogs_per_order_avg * 7, 2)

    # MwSt Reserve: noch nicht abgeführte MwSt (läuft monatlich / quartalsweise)
    # Konservativ: volle monatliche MwSt reservieren
    vat_reserve = vat_amount

    # Externes Budget anteilig nach verbleibenden Tagen
    external_remaining = round(EXTERNAL_BUDGET_EUR * (days_left / days_in_month), 2)

    # ── Verfügbares Cash für Ads ──
    # PayPal Available (bereits eingegangen, aber MwSt-Anteil muss reserviert bleiben)
    # + Reinvestierbarer Gewinn (bereits realisiert, MwSt raus, Kosten raus)
    # + Externes Budget (Rest Monat)
    # − MwSt Reserve (läuft ans Finanzamt)
    # − COGS Reserve 7 Tage (Lieferant)
    reinvestable_profit = max(net_profit, 0.0)
    total_inflows = round(pp_available + reinvestable_profit + external_remaining, 2)
    total_reserves = round(vat_reserve + cogs_7day_reserve, 2)
    cash_for_ads = round(total_inflows - total_reserves, 2)

    daily_ad_budget_conservative = round(max(cash_for_ads * 0.50 / 7, 0), 2)
    daily_ad_budget_aggressive = round(max(cash_for_ads * 0.75 / 7, 0), 2)

    values = [
        # Row 1: Title
        ["💰 FINANCE DASHBOARD", f"Stand: {now.strftime('%d.%m.%Y %H:%M')} UTC", "", ""],
        ["", "", "", ""],

        # Row 3: PayPal Header
        ["🏦 PAYPAL STATUS", "Betrag (€)", "Info", ""],
        ["Verfügbares Guthaben", f"€{pp_available:,.2f}", "Sofort verwendbar", ""],
        ["Ausstehend / Holds (21 Tage)", f"€{pp_pending:,.2f}", "Noch nicht freigegeben", ""],
        ["Gesamt PayPal Balance", f"€{pp_total:,.2f}", "", ""],
        ["", "", "", ""],
        ["Hold-Freigabe (nächste 7 Tage)", "—", "Manuell eintragen ↓", ""],
        ["Hold-Freigabe (nächste 14 Tage)", "—", "Manuell eintragen ↓", ""],

        # Row 10: Monthly P&L Header (Netto)
        [f"📊 MONATLICHE P&L — {month_name} {now.year}", "Betrag (€)", "Details", ""],
        ["Umsatz BRUTTO (Shopify, inkl. 19% MwSt)", f"€{revenue_brutto:,.2f}", f"{orders} Bestellungen", ""],
        ["− MwSt 19% (ans Finanzamt)", f"−€{vat_amount:,.2f}", "= Brutto × 19/119", ""],
        ["= Umsatz NETTO", f"€{revenue_netto:,.2f}", "Deine echte Einnahme", ""],
        ["− Meta Ad Spend", f"−€{adspend:,.2f}", f"ROAS (netto): {roas:.2f}x", ""],
        ["− COGS (exakt)", f"−€{cogs:,.2f}", f"Single €{COGS_SINGLE_EUR} / Bundle €{COGS_BUNDLE_EUR}", ""],
        ["− Payment Fees (3%)", f"−€{fees:,.2f}", "PayPal/Stripe Gebühren", ""],
        ["= Reingewinn", f"€{net_profit:,.2f}", f"Marge: {margin_pct}%", ""],
        ["", "", "", ""],
        ["Ø Gewinn pro Tag (Ist)", f"€{daily_profit_avg:,.2f}", f"Basis: {now.day} Tage", ""],
        ["Hochrechnung Gewinn (Rest Monat)", f"€{profit_projected_rest:,.2f}",
         f"~{days_left} Tage verbleibend", ""],
        ["Ad Spend Heute", f"€{today_spend:,.2f}", now.strftime("%d.%m.%Y"), ""],

        # Row 22: Cash Flow Header
        ["💸 CASH FLOW & VERFÜGBARKEIT", "Betrag (€)", "Herkunft / Hinweis", ""],
        ["(+) PayPal Available", f"€{pp_available:,.2f}", "Bereits eingegangen", ""],
        ["(+) Reinvestierbarer Gewinn (Ist)", f"€{reinvestable_profit:,.2f}",
         "Netto-Gewinn diesen Monat", ""],
        [f"(+) Externes Budget (Rest ~{days_left}d)", f"€{external_remaining:,.2f}",
         f"von €{EXTERNAL_BUDGET_EUR:.0f}/Monat fix", ""],
        ["= Total Zuflüsse", f"€{total_inflows:,.2f}", "", ""],
        ["", "", "", ""],
        ["(−) MwSt Reserve", f"−€{vat_reserve:,.2f}", "Finanzamt — nicht anfassen!", ""],
        ["(−) COGS Reserve (7 Tage)", f"−€{cogs_7day_reserve:,.2f}",
         f"{daily_orders_avg:.0f} Orders/Tag × €{cogs_per_order_avg:.2f}", ""],
        ["= Netto Cash für Ads", f"€{cash_for_ads:,.2f}", "Sicher verwendbar", ""],
        ["", "", "", ""],
        ["⚠️ Hold Release (manuell)", "—", "Wann kommen Holds frei?", ""],
        ["Sonstiges / Puffer (manuell)", "—", "z.B. Chargebacks", ""],

        # Row 34: Ad Budget Header
        ["🎯 AD BUDGET RECHNER", "Tagesbudget (€)", "Wochenbudget (€)", "Empfehlung"],
        ["Konservativ (50% des Cash)", f"€{daily_ad_budget_conservative:,.2f}",
         f"€{daily_ad_budget_conservative*7:,.2f}", "Sicher / Stabil"],
        ["Aggressiv (75% des Cash)", f"€{daily_ad_budget_aggressive:,.2f}",
         f"€{daily_ad_budget_aggressive*7:,.2f}", "Wachstum"],
        ["Aktuelles Tages-Budget (Meta)", f"€{today_spend:,.2f}", "—", "Ist-Zustand"],
        ["", "", "", ""],
        ["Break-Even ROAS (netto)", f"{break_even_roas}x", "Unter diesem Wert = Verlust", ""],
        ["Aktueller ROAS (netto)", f"{roas}x", "Meta diesen Monat",
         "✅ Profitabel" if roas >= break_even_roas else "⚠️ Unter Break-Even"],
    ]

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{TAB_NAME}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    # Apply formatting
    format_requests = build_cell_format_requests(sheet_id)
    if format_requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": format_requests},
        ).execute()

    print(f"Dashboard aktualisiert: {now.strftime('%d.%m.%Y %H:%M')} UTC")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    print(f"Finance Dashboard Agent gestartet — {now.strftime('%d.%m.%Y %H:%M')} UTC")

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
    today_spend = get_meta_today_spend()
    print(f"Meta: €{adspend} gesamt | €{today_spend} heute")

    # Write to Sheets
    service = get_sheets_service()
    ensure_tab_exists(service)
    write_dashboard(service, {
        "pp_available": pp_available,
        "pp_pending": pp_pending,
        "revenue": revenue,
        "cogs": cogs,
        "adspend": adspend,
        "today_spend": today_spend,
        "orders": orders,
    })


if __name__ == "__main__":
    main()
