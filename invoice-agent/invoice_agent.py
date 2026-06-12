import os
import json
import requests
import io
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_RIGHT

SHOPIFY_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")
GOOGLE_CREDENTIALS = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "1WbR_p1bKJ5_H2HAGy_dvYfcPj9JTOT_R")
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


def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        GOOGLE_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds)


def upload_to_drive(drive_service, filename, pdf_bytes):
    file_metadata = {"name": filename, "parents": [DRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()


def get_orders_with_status(status):
    all_orders = []
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    params = {
        "status": status,
        "limit": 250,
        "fields": "id,order_number,created_at,email,billing_address,line_items,total_price,total_tax",
    }
    while url:
        r = requests.get(url, headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN}, params=params)
        r.raise_for_status()
        all_orders.extend(r.json().get("orders", []))
        link = r.headers.get("Link", "")
        url = None
        params = {}
        if 'rel="next"' in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
    return all_orders


def get_all_orders():
    seen = set()
    all_orders = []
    for status in ("open", "closed", "cancelled"):
        try:
            for o in get_orders_with_status(status):
                if o["id"] not in seen:
                    seen.add(o["id"])
                    all_orders.append(o)
        except Exception as e:
            print(f"  Warnung: Status '{status}' nicht abrufbar: {e}")
    return all_orders


def rechnungsnummer(order_number):
    return f"RE-{datetime.now().year}-{str(order_number).zfill(5)}"


def pdf_filename(order_number):
    return f"Levora-Skin_#{order_number}.pdf"


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
    right_pink = ParagraphStyle("rp", fontSize=9, textColor=PINK, leading=14, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    story = []

    ht = Table([[
        Paragraph("<b>Levora Skin</b>", ParagraphStyle("", fontSize=16, textColor=PINK, fontName="Helvetica-Bold")),
        Paragraph(f"{COMPANY['name']}<br/>{COMPANY['zusatz']}<br/>{COMPANY['strasse']}<br/>{COMPANY['plz_ort']}<br/>{COMPANY['email']}<br/>{COMPANY['web']}", small),
    ]], colWidths=[9*cm, 7*cm])
    ht.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(1,0),(1,0),"RIGHT")]))
    story.append(ht)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PINK, spaceAfter=12, spaceBefore=8))

    addr = order.get("billing_address") or {}
    kunde_name = f"{(addr.get('first_name') or '').strip()} {(addr.get('last_name') or '').strip()}".strip() or order.get("email","Kunde")
    zeilen = [kunde_name]
    if addr.get("address1"): zeilen.append(addr["address1"])
    if addr.get("zip") or addr.get("city"): zeilen.append(f"{addr.get('zip','')} {addr.get('city','')}".strip())
    if addr.get("country"): zeilen.append(addr["country"])
    if order.get("email"): zeilen.append(order["email"])

    re_nr = rechnungsnummer(order["order_number"])
    re_datum = datetime.now().strftime("%d.%m.%Y")
    bestell_datum = datetime.fromisoformat(order["created_at"].replace("Z","+00:00")).strftime("%d.%m.%Y")

    it = Table([[
        Paragraph("<br/>".join(zeilen), body),
        Paragraph(f"<b>Rechnungsnummer:</b> {re_nr}<br/><b>Rechnungsdatum:</b> {re_datum}<br/><b>Bestelldatum:</b> {bestell_datum}<br/><b>Bestellnummer:</b> #{order['order_number']}", right),
    ]], colWidths=[9*cm, 7*cm])
    it.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(it)
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Rechnung", h1))
    story.append(Paragraph("Vielen Dank für deine Bestellung!", body))
    story.append(Spacer(1, 0.4*cm))

    rows = [[Paragraph(f"<b>{h}</b>", bold) for h in ["Pos.", "Beschreibung", "Menge", "Einzelpreis", "Gesamt"]]]
    for i, item in enumerate(order.get("line_items", []), 1):
        qty = item.get("quantity", 1)
        price = float(item.get("price", 0))
        rows.append([Paragraph(str(i), body), Paragraph(item.get("title",""), body),
                     Paragraph(str(qty), body), Paragraph(f"{price:.2f} €", body),
                     Paragraph(f"{qty*price:.2f} €", body)])

    pt = Table(rows, colWidths=[1*cm, 9*cm, 2*cm, 3*cm, 3*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),PINK), ("TEXTCOLOR",(0,0),(-1,0),white),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,LIGHT_GRAY]),
        ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
        ("PADDING",(0,0),(-1,-1),6), ("ALIGN",(2,0),(-1,-1),"RIGHT"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.3*cm))

    total = float(order.get("total_price", 0))
    tax = float(order.get("total_tax", 0))
    if tax == 0 and total > 0:
        tax = round(total / 1.19 * 0.19, 2)
    netto = round(total - tax, 2)
    st = Table([
        ["","", Paragraph("Nettobetrag:", body), Paragraph(f"{netto:.2f} €", right)],
        ["","", Paragraph("zzgl. 19% MwSt.:", body), Paragraph(f"{tax:.2f} €", right)],
        ["","", Paragraph("<b>Gesamtbetrag:</b>", bold), Paragraph(f"<b>{total:.2f} €</b>", right_pink)],
    ], colWidths=[1*cm, 8*cm, 5*cm, 4*cm])
    st.setStyle(TableStyle([("LINEABOVE",(2,2),(3,2),1,PINK),("PADDING",(0,0),(-1,-1),4)]))
    story.append(st)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#DDDDDD"), spaceAfter=6))
    story.append(Paragraph(f"<b>Bankverbindung:</b> {COMPANY['name']} · IBAN: {COMPANY['iban']} · BIC: {COMPANY['bic']} · {COMPANY['bank']}", small))
    story.append(Paragraph(f"USt-IdNr.: {COMPANY['ust_id']} · Steuernummer: {COMPANY['steuernummer']}", small))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Rechnungs-Agent gestartet.")
    processed = load_processed()
    print(f"Bereits verarbeitet: {len(processed)}")

    orders = get_all_orders()
    new_orders = [o for o in orders if str(o["id"]) not in processed]
    print(f"{len(new_orders)} neue Bestellung(en) zu verarbeiten.")

    if not new_orders:
        print("Fertig.")
        return

    drive_service = get_drive_service()

    for order in new_orders:
        try:
            pdf = create_invoice_pdf(order)
            filename = pdf_filename(order["order_number"])
            upload_to_drive(drive_service, filename, pdf)
            processed.add(str(order["id"]))
            print(f"  ✓ Hochgeladen: {filename}")
        except Exception as e:
            print(f"  ✗ Fehler bei #{order['order_number']}: {e}")

    save_processed(processed)
    print("Fertig.")


if __name__ == "__main__":
    main()
