from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

doc = SimpleDocTemplate(
    "Levora_Email_Agent_Handbuch.pdf",
    pagesize=A4,
    rightMargin=2.5*cm,
    leftMargin=2.5*cm,
    topMargin=2.5*cm,
    bottomMargin=2.5*cm,
)

PINK = HexColor("#D4667A")
LIGHT_PINK = HexColor("#FAF0F2")
DARK = HexColor("#2D2D2D")
GRAY = HexColor("#666666")
LIGHT_GRAY = HexColor("#F5F5F5")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("Title", fontSize=24, textColor=PINK, spaceAfter=6, fontName="Helvetica-Bold", alignment=TA_LEFT)
subtitle_style = ParagraphStyle("Subtitle", fontSize=13, textColor=GRAY, spaceAfter=20, fontName="Helvetica")
h2_style = ParagraphStyle("H2", fontSize=14, textColor=PINK, spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold")
h3_style = ParagraphStyle("H3", fontSize=11, textColor=DARK, spaceBefore=10, spaceAfter=5, fontName="Helvetica-Bold")
body_style = ParagraphStyle("Body", fontSize=10, textColor=DARK, spaceAfter=6, fontName="Helvetica", leading=16)
quote_style = ParagraphStyle("Quote", fontSize=10, textColor=DARK, spaceAfter=4, fontName="Helvetica-Oblique", leading=15,
                              leftIndent=15, rightIndent=15, backColor=LIGHT_PINK, borderPadding=(8, 10, 8, 10))
label_style = ParagraphStyle("Label", fontSize=9, textColor=white, fontName="Helvetica-Bold")
small_style = ParagraphStyle("Small", fontSize=9, textColor=GRAY, fontName="Helvetica", spaceAfter=4)
warning_style = ParagraphStyle("Warning", fontSize=10, textColor=HexColor("#8B4513"), fontName="Helvetica",
                                 backColor=HexColor("#FFF3CD"), leading=15, leftIndent=10, rightIndent=10,
                                 borderPadding=(6, 8, 6, 8), spaceAfter=8)

story = []

story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("Levora Skin", title_style))
story.append(Paragraph("Automatischer E-Mail-Support-Agent", subtitle_style))
story.append(Paragraph("Handbuch & Antwort-Leitfaden — Yvonne (KI-Kundensupport)", small_style))
story.append(HRFlowable(width="100%", thickness=2, color=PINK, spaceAfter=20))

story.append(Paragraph("Übersicht", h2_style))
story.append(Paragraph(
    "Der E-Mail-Agent antwortet automatisch auf eingehende Kundenanfragen bei <b>info@levora-skin.de</b>. "
    "Er agiert als <b>Yvonne vom Kundensupport</b> – freundlich, persönlich und lösungsorientiert. "
    "Der Agent prüft das Postfach alle 15 Minuten, erkennt den Anfragetyp und antwortet entsprechend dem Leitfaden.",
    body_style
))
story.append(Paragraph(
    "Im aktuellen Setup speichert der Agent zunächst nur <b>Entwürfe</b>. "
    "Sobald die Antwortqualität bestätigt ist, kann er auf vollautomatischen Versand umgestellt werden.",
    body_style
))

story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("Sprache & Tonalität", h2_style))
data = [
    ["Merkmal", "Beschreibung"],
    ["Anrede", "Immer \"du\" – kein \"Sie\""],
    ["Einstieg", "\"Hallo [Name],\" – kein \"Sehr geehrte/r\""],
    ["Ton", "Warm, empathisch, persönlich"],
    ["Länge", "Kurz und klar – keine langen Textwände"],
    ["Abschluss", "\"Liebe Grüße, Yvonne – Levora Skin Kundensupport\""],
]
t = Table(data, colWidths=[5*cm, 11*cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PINK),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
    ("PADDING", (0, 0), (-1, -1), 7),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))
story.append(t)

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("Fall 1: Paket-Anfrage – Erste Nachricht", h2_style))
story.append(Paragraph(
    "<b>Erkennungsmuster:</b> Kunde fragt erstmalig nach seinem Paket (\"Wo ist mein Paket?\", \"Meine Bestellung ist noch nicht angekommen\", etc.)",
    body_style
))
story.append(Paragraph("Standardantwort:", h3_style))
story.append(Paragraph(
    "Hallo [Name],<br/><br/>"
    "vielen Dank für deine Nachricht! Ich habe gerade in unserem System nachgeschaut und laut DHL sollte dein Paket eigentlich schon unterwegs sein. "
    "Das klingt für mich ehrlich gesagt etwas ungewöhnlich – ich werde morgen umgehend mit DHL telefonieren und die Sache in Erfahrung bringen. "
    "Ich melde mich dann sofort bei dir!<br/><br/>"
    "Falls dein Paket in den nächsten 4–5 Tagen nicht ankommen sollte, melde dich bitte kurz bei mir – "
    "dann schicke ich dir umgehend kostenlos ein neues Paket zu. Und sollte das ursprüngliche Paket doch noch ankommen, "
    "kannst du einfach beide behalten. 😊<br/><br/>"
    "Liebe Grüße,<br/>Yvonne<br/>Levora Skin Kundensupport",
    quote_style
))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("Fall 2: Paket-Anfrage – Folgenachricht (nach 4–5 Tagen)", h2_style))
story.append(Paragraph(
    "<b>Erkennungsmuster:</b> Kunde schreibt erneut, dass das Paket immer noch nicht angekommen ist "
    "(Kontext: vorherige E-Mail im gleichen Thread vorhanden).",
    body_style
))
story.append(Paragraph("Standardantwort:", h3_style))
story.append(Paragraph(
    "Hallo [Name],<br/><br/>"
    "das tut mir wirklich sehr leid zu hören! Ich werde dir umgehend ein neues Paket fertig machen – "
    "es wird noch heute unser Versandlager verlassen. Du erhältst die Tracking-Informationen, "
    "sobald es versendet wurde.<br/><br/>"
    "Liebe Grüße,<br/>Yvonne<br/>Levora Skin Kundensupport",
    quote_style
))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("Fall 3: Stornierungsanfrage", h2_style))
story.append(Paragraph(
    "<b>Erkennungsmuster:</b> Kunde möchte seine Bestellung stornieren.",
    body_style
))
story.append(Paragraph("Vorgehensweise:", h3_style))
story.append(Paragraph("1. Freundlich nach dem Grund fragen.", body_style))
story.append(Paragraph("2. Gleichzeitig mitteilen, dass geprüft werden muss, ob das Paket das Versandlager bereits verlassen hat.", body_style))
story.append(Paragraph("Beispielantwort:", h3_style))
story.append(Paragraph(
    "Hallo [Name],<br/><br/>"
    "vielen Dank für deine Nachricht! Ich würde mich kurz bei dir melden und fragen, ob du mir den Grund für die Stornierung mitteilen magst – "
    "vielleicht können wir dir auch anderweitig helfen.<br/><br/>"
    "Ich schaue gleichzeitig kurz in unserem System nach, ob dein Paket das Versandlager bereits verlassen hat, "
    "damit ich dir alle weiteren Details nennen kann. Ich melde mich umgehend bei dir!<br/><br/>"
    "Liebe Grüße,<br/>Yvonne<br/>Levora Skin Kundensupport",
    quote_style
))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("Eskalation – Keine automatische Antwort", h2_style))
story.append(Paragraph(
    "Bei folgenden Anfragetypen antwortet der Agent NICHT automatisch. "
    "Die E-Mail wird als gelesen markiert und muss manuell bearbeitet werden:",
    body_style
))
esc_data = [
    ["Anfragetyp", "Beispiel", "Bearbeitung"],
    ["PayPal-Käuferschutz / Chargeback", "\"Ich eröffne einen Käuferschutzfall\"", "Founder persönlich"],
    ["Rechtliche Drohungen", "\"Ich gehe zum Anwalt\"", "Founder persönlich"],
    ["Aggressive / beleidigende Nachrichten", "Beleidigungen, Drohungen", "Founder persönlich"],
]
t2 = Table(esc_data, colWidths=[5.5*cm, 6*cm, 4.5*cm])
t2.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#8B0000")),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#FFF0F0")]),
    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
    ("PADDING", (0, 0), (-1, -1), 7),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))
story.append(t2)

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("Alle anderen Anfragen", h2_style))
story.append(Paragraph(
    "Der Agent antwortet freundlich im Stil von Yvonne. Falls er eine Frage nicht vollständig beantworten kann, "
    "schreibt er, dass er sich darum kümmert und sich schnellstmöglich meldet. "
    "Die restlichen Kundenflows werden durch die automatisierten E-Mail-Sequenzen abgedeckt.",
    body_style
))

story.append(Spacer(1, 0.4*cm))
story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#DDDDDD"), spaceAfter=10))
story.append(Paragraph("Technische Konfiguration", h2_style))
tech_data = [
    ["Parameter", "Wert"],
    ["Postfach", "info@levora-skin.de"],
    ["Ausführung", "Alle 15 Minuten (GitHub Actions)"],
    ["KI-Modell", "Claude Sonnet (Anthropic)"],
    ["Draft-Modus", "Aktiv – speichert Entwürfe statt direkt zu senden"],
    ["Thread-Erkennung", "Automatisch via Conversation-ID (Folge-E-Mails werden erkannt)"],
]
t3 = Table(tech_data, colWidths=[6*cm, 10*cm])
t3.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), PINK),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_GRAY]),
    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
    ("PADDING", (0, 0), (-1, -1), 7),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))
story.append(t3)

story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    f"Stand: Juni 2026  ·  Levora Skin  ·  Internes Dokument",
    small_style
))

doc.build(story)
print("PDF erstellt: Levora_Email_Agent_Handbuch.pdf")
