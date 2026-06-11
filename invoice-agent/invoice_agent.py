import os
import json
import requests
import base64
import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_RIGHT

SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
AZURE_TENANT_ID = os.environ["AZURE_TENANT_ID"]
AZURE_CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
AZURE_CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
FROM_EMAIL = os.environ.get("EMAIL_ADDRESS", "info@levora-skin.de")
PROCESSED_FILE = "invoice-agent/processed_orders.json"

COMPANY = {
    "name": "Malia Kosubek",
    "zusatz": "Einzelunternehmen",
    "strasse": "Bruchstraße 13",
    "plz_ort": "40235 Düsseldorf",
    "email": "info@levora-skin.de",
    "web": "www.levora-skin.de",
    "ust_id": "DE369648210",
    "steuernummer": "133/5173/6507",
    "iban": "BE45 9055 3079 2289",
    "bic": "TRWIBEB1XXX",
    "bank": "Wise",
}

PINK = HexColor("#D4667A")
LIGHT_PINK = HexColor("#FAF0F2")
DARK = HexColor("#2D2D2D")
GRAY = HexColor("#888888")
LIGHT_GRAY = HexColor("#F7F7F7")


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f)


def get_all_orders():
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    all_orders = []
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    params = {
        "status": "any",
        "limit": 250,
        "fields": "id,order_number,created_at,email,billing_address,line_items,total_price,subtotal_price,total_tax,currency",
    }
    while url:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        orders = r.json().get("orders", [])
        all_orders.extend(orders)
        link = r.headers.get("Link", "")
        url = None
        params = {}
        if 'rel="next"' in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
    return all_orders


def rechnungsnummer(order_number):
    year = datetime.now().year
    return f"RE-{year}-{str(order_number).zfill(5)}"


def create_invoice_pdf(order):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    body = ParagraphStyle("body", fontSize=9, textColor=DARK, leading=14, fontName="Helvetica")
    bold = ParagraphStyle("bold", fontSize=9, textColor=DARK, leading=14, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", fontSize=8, textColor=GRAY, leading=12, fontName="Helvetica")
    h1 = ParagraphStyle("h1", fontSize=20, textColor=PINK, fontName="Helvetica-Bold", spaceAfter=4)
    right = ParagraphStyle("right", fontSize=9, textColor=DARK, leading=14, fontName="Helvetica", alignment=TA_RIGHT)
    right_pink = ParagraphStyle("right_pink", fontSize=9, textColor=PINK, leading=14, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    story = []

    # Header
    header_data = [[
        Paragraph("<b>Levora Skin</b>", ParagraphStyle("", fontSize=16, textColor=PINK, fontName="Helvetica-Bold")),
        Paragraph(f"{COMPANY['name']}<br/>{COMPANY['zusatz']}<br/>{COMPANY['strasse']}<br/>{COMPANY['plz_ort']}<br/>{COMPANY['email']}<br/>{COMPANY['web']}", small),
    ]]
    ht = Table(header_data, colWidths=[9*cm, 7*cm])
    ht.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (1,0), (1,0), "RIGHT")]))
    story.append(ht)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PINK, spaceAfter=12, spaceBefore=8))

    # Empfänger & Rechnungsinfo
    addr = order.get("billing_address") or {}
    kunde_name = f"{addr.get('first_name','').strip()} {addr.get('last_name','').strip()}".strip() or order.get("email","Kunde")
    kunde_zeilen = [kunde_name]
    if addr.get("address1"): kunde_zeilen.append(addr["address1"])
    if addr.get("zip") or addr.get("city"): kunde_zeilen.append(f"{addr.get('zip','')} {addr.get('city','')}".strip())
    if addr.get("country"): kunde_zeilen.append(addr["country"])
    if order.get("email"): kunde_zeilen.append(order["email"])

    re_nr = rechnungsnummer(order["order_number"])
    re_datum = datetime.now().strftime("%d.%m.%Y")
    bestell_datum = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).strftime("%d.%m.%Y")

    info_data = [[
        Paragraph("<br/>".join(kunde_zeilen), body),
        Paragraph(f"<b>Rechnungsnummer:</b> {re_nr}<br/><b>Rechnungsdatum:</b> {re_datum}<br/><b>Bestelldatum:</b> {bestell_datum}<br/><b>Bestellnummer:</b> #{order['order_number']}", right),
    ]]
    it = Table(info_data, colWidths=[9*cm, 7*cm])
    it.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(it)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Rechnung", h1))
    story.append(Paragraph("Vielen Dank für deine Bestellung!", body))
    story.append(Spacer(1, 0.4*cm))

    # Positionen
    rows = [[
        Paragraph("<b>Pos.</b>", bold),
        Paragraph("<b>Beschreibung</b>", bold),
        Paragraph("<b>Menge</b>", bold),
        Paragraph("<b>Einzelpreis</b>", bold),
        Paragraph("<b>Gesamt</b>", bold),
    ]]
    for i, item in enumerate(order.get("line_items", []), 1):
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        rows.append([
            Paragraph(str(i), body),
            Paragraph(item.get("title", ""), body),
            Paragraph(str(qty), body),
            Paragraph(f"{price:.2f} €", body),
            Paragraph(f"{qty*price:.2f} €", body),
        ])

    pt = Table(rows, colWidths=[1*cm, 9*cm, 2*cm, 3*cm, 3*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PINK),
        ("TEXTCOLOR", (0,0), (-1,0), white),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
        ("PADDING", (0,0), (-1,-1), 6),
        ("ALIGN", (2,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.3*cm))

    # Summen – Netto berechnet aus Brutto
    total = float(order.get("total_price", 0))
    tax = float(order.get("total_tax", 0))
    netto = total - tax

    summen = [
        ["", "", Paragraph("Nettobetrag:", body), Paragraph(f"{netto:.2f} €", right)],
        ["", "", Paragraph("zzgl. 19% MwSt.:", body), Paragraph(f"{tax:.2f} €", right)],
        ["", "", Paragraph("<b>Gesamtbetrag:</b>", bold), Paragraph(f"<b>{total:.2f} €</b>", right_pink)],
    ]
    st = Table(summen, colWidths=[1*cm, 8*cm, 5*cm, 4*cm])
    st.setStyle(TableStyle([
        ("LINEABOVE", (2,2), (3,2), 1, PINK),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(st)
    story.append(Spacer(1, 0.5*cm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#DDDDDD"), spaceAfter=6))
    story.append(Paragraph(f"<b>Bankverbindung:</b> {COMPANY['name']} · IBAN: {COMPANY['iban']} · BIC: {COMPANY['bic']} · {COMPANY['bank']}", small))
    story.append(Paragraph(f"USt-IdNr.: {COMPANY['ust_id']} · Steuernummer: {COMPANY['steuernummer']}", small))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def get_ms_token():
    url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    r = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def send_invoice_to_me(ms_token, order_number, kunde_name, pdf_bytes):
    re_nr = rechnungsnummer(order_number)
    payload = {
        "message": {
            "subject": f"Rechnung {re_nr} – Bestellung #{order_number} ({kunde_name})",
            "body": {"contentType": "Text", "content": f"Automatisch erstellte Rechnung für Bestellung #{order_number} von {kunde_name}."},
            "toRecipients": [{"emailAddress": {"address": FROM_EMAIL}}],
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"{re_nr}.pdf",
                "contentType": "application/pdf",
                "contentBytes": base64.b64encode(pdf_bytes).decode(),
            }],
        },
        "saveToSentItems": True,
    }
    headers = {"Authorization": f"Bearer {ms_token}", "Content-Type": "application/json"}
    r = requests.post(f"https://graph.microsoft.com/v1.0/users/{FROM_EMAIL}/sendMail", headers=headers, json=payload)
    r.raise_for_status()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Rechnungs-Agent gestartet.")
    processed = load_processed()
    print(f"Bereits verarbeitet: {len(processed)} Bestellungen.")

    orders = get_all_orders()
    new_orders = [o for o in orders if str(o["id"]) not in processed]
    print(f"{len(new_orders)} neue Bestellung(en) zu verarbeiten.")

    if not new_orders:
        print("Fertig.")
        return

    ms_token = get_ms_token()

    for order in new_orders:
        order_number = order["order_number"]
        addr = order.get("billing_address") or {}
        kunde_name = f"{addr.get('first_name','').strip()} {addr.get('last_name','').strip()}".strip() or order.get("email", "Unbekannt")
        print(f"  Verarbeite #{order_number} – {kunde_name}...")
        try:
            pdf = create_invoice_pdf(order)
            send_invoice_to_me(ms_token, order_number, kunde_name, pdf)
            processed.add(str(order["id"]))
            print(f"  ✓ Rechnung gespeichert")
        except Exception as e:
            print(f"  ✗ Fehler: {e}")

    save_processed(processed)
    print("Fertig.")


if __name__ == "__main__":
    main()
