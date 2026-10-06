"""PDF-Preisliste zum Teilen (z. B. per WhatsApp). Benötigt reportlab.

Aufruf (nach `dynpricing.cli run`): python3 scripts/export_pdf.py [Jahr]
"""

import csv
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "output"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

if (FONT_DIR / "DejaVuSans.ttf").exists():
    pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DVB", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    REG, BOLD = "DV", "DVB"
else:
    REG, BOLD = "Helvetica", "Helvetica-Bold"

H1 = ParagraphStyle("h1", fontName=BOLD, fontSize=15, leading=19, spaceAfter=4)
H2 = ParagraphStyle("h2", fontName=BOLD, fontSize=11, leading=14, spaceBefore=8, spaceAfter=3)
TXT = ParagraphStyle("t", fontName=REG, fontSize=8.5, leading=11)
CELL = ParagraphStyle("c", fontName=REG, fontSize=7.8, leading=9.5)


def label(a: date, b: date) -> str:
    s = f"{WD[a.weekday()]} {a:%d.%m.}"
    return s if a == b else f"{s} – {WD[b.weekday()]} {b:%d.%m.}"


def basis_short(text: str) -> str:
    if text.startswith("belegt"):
        return "belegt (" + text.split("Median ")[1].split(" (")[0] + ")"
    return "Annahme" if text.startswith("Annahme") else "abgeleitet"


def payout_ratio() -> float:
    import tomllib
    cfg = tomllib.loads((OUT.parent / "config" / "pricing.toml").read_text(encoding="utf-8"))
    return cfg.get("fees", {}).get("payout_ratio", 1.0)


def main(year: int) -> Path:
    ratio = payout_ratio()
    rows = list(csv.DictReader(open(OUT / f"airbnb_eingabe_{year}.csv", encoding="utf-8")))
    data = [["Nächte", "Nachtpreis\neintragen", "Gast zahlt\npro Nacht*", "Sie bekommen\npro Nacht**", "Min.", "Event / Grund", "Datenbasis"]]
    styles = []
    prev_end = None
    for r in rows:
        a, b = date.fromisoformat(r["von"]), date.fromisoformat(r["bis"])
        if prev_end and (a - prev_end).days > 1:
            gap_a = date.fromordinal(prev_end.toordinal() + 1)
            gap_b = date.fromordinal(a.toordinal() - 1)
            data.append([label(gap_a, gap_b), "gesperrt", "", "", "", "gebucht / Urlaub", ""])
            styles.append(("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor("#E5E5E5")))
        prev_end = b
        data.append([label(a, b), f"{r['Airbnb-Nachtpreis']} €", f"~{r['Gastpreis/Nacht']} €",
                     f"~{float(r['Gastpreis/Nacht']) * ratio:.0f} €", r["Mindestnächte"],
                     Paragraph(r["Event"] or "–", CELL), Paragraph(basis_short(r["Datenbasis"]), CELL)])
        if r["Event"]:
            styles.append(("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor("#FFF4D6")))

    path = OUT / f"Preisliste_Airbnb_{year}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=f"Preisliste Airbnb {year}")
    story = [
        Paragraph(f"Airbnb-Preisliste Concordiastraße 15 – {year}", H1),
        Paragraph(f"Stand {date.today():%d.%m.%Y}. Nachtpreis = in Airbnb einzutragen (ohne Reinigung).", TXT),
        Paragraph("Einstellungen", H2),
        Paragraph("• Reinigungsgebühr <b>35 €</b> (einmal pro Buchung) &nbsp; • Max. <b>2 Gäste</b> &nbsp; • Mindestaufenthalt So–Do 1, Fr/Sa 2, MEDICA 15.–18.11.: 3 &nbsp; "
                  "• <b>Smart Pricing aus</b><br/>"
                  "• Wochenrabatt <b>10 %</b> &nbsp; • Monats-, Last-Minute-, Frühbucherrabatt <b>aus</b> &nbsp; "
                  "• Aktion für neue Inserate abschalten, falls möglich<br/>"
                  "• Sperren: <b>30.10.–14.11.</b> (Urlaub; nur als Gesamtzeitraum per Sonderangebot ~1.510 €) und "
                  "<b>ab 01.01.2027</b> (Langzeitmieter-Suche)", TXT),
        Paragraph("Preise", H2),
    ]
    t = Table(data, colWidths=[36 * mm, 19 * mm, 19 * mm, 22 * mm, 9 * mm, 52 * mm, 29 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BOLD), ("FONTNAME", (0, 1), (-1, -1), REG),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE7F0")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (4, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ] + styles))
    story += [t, Spacer(1, 4),
              Paragraph("* Gast zahlt ≈ Nachtpreis + anteilige Reinigung (35 € einmal pro Buchung, verteilt auf 2–3 Nächte). "
                        f"** Nach Airbnb-Servicegebühr ({(1 - ratio) * 100:.2f} % auf Nachtpreise + Reinigung, belegt durch Buchung 05.10.). "
                        "Gelb = Event/Messe. "
                        "„belegt“ = durch Vergleichspreise geprüft; „Annahme“ = Aufschlag ohne Vergleichsdaten. "
                        "Di 06.10.: falls bis 05.10. abends nicht gebucht → 119 €.", TXT)]
    doc.build(story)
    return path


if __name__ == "__main__":
    print(main(int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year))
