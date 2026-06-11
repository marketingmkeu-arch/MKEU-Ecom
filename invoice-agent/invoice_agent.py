import os
import json
import requests
import re
from datetime import datetime, timezone, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import io
import base64

# --- Konfiguration ---
SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
AZURE_TENANT_ID = os.environ["AZURE_TENANT_ID"]
AZURE_CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
AZURE_CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
FROM_EMAIL = os.environ.get("EMAIL_ADDRESS", "info@levora-skin.de")

# --- Firmendaten ---
COMPANY = {
    "name": "Malia Kosubek",
    "zusatz": "Einzelunternehmen",
    "strasse": "Bruchstraße 13",
    "plz_ort": "40235 Düsseldorf",
    "land": "Deutschland",
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


def get_recent_orders():
    since = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {
        "status": "any",
        "created_at_min": since,
        "limit": 50,
        "fields": "id,order_number,created_at,email,billing_address,line_items,total_price,subtotal_price,total_tax,currency,financial_status,tags",
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    orders = r.json().get("orders", [])
    # Nur Bestellungen die noch kein "invoice_sent" Tag haben
    return [o for o in orders if "invoice_sent" not in (o.get("tags") or "")]


def tag_order_invoiced(order_id):
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders/{order_id}.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return
    existing_tags = r.json().get("order", {}).get("tags", "")
    new_tags = f"{existing_tags},invoice_sent".strip(",")
    requests.put(url, headers=headers, json={"order": {"id": order_id, "tags": new_tags}})


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

    story = []

    # Header
    header_data = [
        [Paragraph("<b>Levora Skin</b>", ParagraphStyle("", fontSize=16, textColor=PINK, fontName="Helvetica-Bold")),
         Paragraph(f"{COMPANY['name']}<br/>{COMPANY['zusatz']}<br/>{COMPANY['strasse']}<br/>{COMPANY['plz_ort']}<br/>{COMPANY['email']}<br/>{COMPANY['web']}", small)],
    ]
    header_table = Table(header_data, colWidths=[9*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PINK, spaceAfter=12, spaceBefore=8))

    # Empfänger & Rechnungsinfos
    addr = order.get("billing_address") or {}
    kunde_name = f"{addr.get('first_name', '')} {addr.get('last_name', '')}".strip() or order.get("email", "")
    kunde_adresse = f"{addr.get('address1', '')}<br/>{addr.get('zip', '')} {addr.get('city', '')}<br/>{addr.get('country', '')}"

    re_nr = rechnungsnummer(order["order_number"])
    re_datum = datetime.now().strftime("%d.%m.%Y")
    bestell_datum = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).strftime("%d.%m.%Y")

    info_data = [
        [Paragraph(f"{kunde_name}<br/>{kunde_adresse}", body),
         Paragraph(f"<b>Rechnungsnummer:</b> {re_nr}<br/><b>Rechnungsdatum:</b> {re_datum}<br/><b>Bestelldatum:</b> {bestell_datum}<br/><b>Bestellnummer:</b> #{order['order_number']}", right)],
    ]
    info_table = Table(info_data, colWidths=[9*cm, 7*cm])
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Rechnung", h1))
    story.append(Paragraph(f"Vielen Dank für deine Bestellung! Anbei findest du deine Rechnung.", body))
    story.append(Spacer(1, 0.4*cm))

    # Positionen
    pos_header = [
        Paragraph("<b>Pos.</b>", bold),
        Paragraph("<b>Beschreibung</b>", bold),
        Paragraph("<b>Menge</b>", bold),
        Paragraph("<b>Einzelpreis</b>", bold),
        Paragraph("<b>Gesamt</b>", bold),
    ]
    pos_rows = [pos_header]

    for i, item in enumerate(order.get("line_items", []), 1):
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        total = qty * price
        pos_rows.append([
            Paragraph(str(i), body),
            Paragraph(item.get("title", ""), body),
            Paragraph(str(qty), body),
            Paragraph(f"{price:.2f} €", body),
            Paragraph(f"{total:.2f} €", body),
        ])

    pos_table = Table(pos_rows, colWidths=[1*cm, 9*cm, 2*cm, 3*cm, 3*cm])
    pos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PINK),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(pos_table)
    story.append(Spacer(1, 0.3*cm))

    # Summen
    subtotal = float(order.get("subtotal_price", 0))
    tax = float(order.get("total_tax", 0))
    total = float(order.get("total_price", 0))
    netto = total / 1.19

    summen_data = [
        ["", "", Paragraph("Nettobetrag:", body), Paragraph(f"{netto:.2f} €", right)],
        ["", "", Paragraph("zzgl. 19% MwSt.:", body), Paragraph(f"{tax:.2f} €", right)],
        ["", "", Paragraph("<b>Gesamtbetrag:</b>", bold), Paragraph(f"<b>{total:.2f} €</b>", ParagraphStyle("", fontSize=9, textColor=PINK, fontName="Helvetica-Bold", alignment=TA_RIGHT))],
    ]
    summen_table = Table(summen_data, colWidths=[1*cm, 8*cm, 5*cm, 4*cm])
    summen_table.setStyle(TableStyle([
        ("LINEABOVE", (2, 2), (3, 2), 1, PINK),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summen_table)
    story.append(Spacer(1, 0.5*cm))

    # Zahlungsinfos
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#DDDDDD"), spaceAfter=8))
    story.append(Paragraph("<b>Bankverbindung:</b>", bold))
    story.append(Paragraph(f"Kontoinhaber: {COMPANY['name']} | IBAN: {COMPANY['iban']} | BIC: {COMPANY['bic']} | Bank: {COMPANY['bank']}", small))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"USt-IdNr.: {COMPANY['ust_id']} | Steuernummer: {COMPANY['steuernummer']}", small))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Kleinunternehmerregelung gemäß §19 UStG – Kein Ausweis von Umsatzsteuer.", small))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def get_ms_token():
    url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def send_invoice_email(token, to_email, to_name, order_number, pdf_bytes):
    re_nr = rechnungsnummer(order_number)
    subject = f"Deine Rechnung von Levora Skin – {re_nr}"
    body_text = f"""Hallo {to_name or ''},

vielen Dank für deine Bestellung bei Levora Skin! 🌸

Im Anhang findest du deine Rechnung ({re_nr}) als PDF.

Bei Fragen stehen wir dir jederzeit unter info@levora-skin.de zur Verfügung.

Liebe Grüße,
Dein Levora Skin Team
www.levora-skin.de"""

    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": [{"emailAddress": {"address": to_email, "name": to_name or ""}}],
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": f"{re_nr}.pdf",
                "contentType": "application/pdf",
                "contentBytes": pdf_b64,
            }],
        },
        "saveToSentItems": True,
    }

    url = f"https://graph.microsoft.com/v1.0/users/{FROM_EMAIL}/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Rechnungs-Agent gestartet.")
    orders = get_recent_orders()
    print(f"{len(orders)} neue Bestellung(en) gefunden.")

    if not orders:
        print("Fertig.")
        return

    ms_token = get_ms_token()

    for order in orders:
        order_number = order["order_number"]
        to_email = order.get("email", "")
        addr = order.get("billing_address") or {}
        to_name = f"{addr.get('first_name', '')} {addr.get('last_name', '')}".strip()

        if not to_email:
            print(f"  ⚠ Bestellung #{order_number}: keine E-Mail-Adresse, übersprungen.")
            continue

        print(f"  Verarbeite Bestellung #{order_number} für {to_email}...")
        try:
            pdf = create_invoice_pdf(order)
            send_invoice_email(ms_token, to_email, to_name, order_number, pdf)
            tag_order_invoiced(order["id"])
            print(f"  ✓ Rechnung gesendet an {to_email}")
        except Exception as e:
            print(f"  ✗ Fehler: {e}")

    print("Fertig.")


if __name__ == "__main__":
    main()
