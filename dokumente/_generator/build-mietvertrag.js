const {
  Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle,
  Table, TableRow, TableCell, WidthType, ShadingType, Header, Footer,
  PageNumber, LevelFormat, PageBreak, VerticalAlign
} = require("docx");

const FONT = "Calibri";
const CW = 9638; // content width in DXA (A4 minus 2cm margins)
const children = [];
const A = (...xs) => xs.forEach(x => children.push(x));

function runs(list, o = {}) {
  return new Paragraph({
    spacing: { before: o.before ?? 0, after: o.after ?? 90, line: o.line ?? 264 },
    alignment: o.align,
    indent: o.indent,
    keepNext: o.keepNext,
    children: list.map(r =>
      typeof r === "string"
        ? new TextRun({ text: r, size: o.size ?? 20, font: FONT })
        : new TextRun({ font: FONT, size: o.size ?? 20, ...r })
    ),
  });
}
const p  = (t, o = {}) => runs([t], o);
const b  = (t, o = {}) => runs([{ text: t, bold: true }], o);
const sp = (h = 90) => new Paragraph({ spacing: { after: h }, children: [] });

function title(t) {
  return runs([{ text: t, bold: true, size: 32 }], { align: AlignmentType.CENTER, after: 60 });
}
function subtitle(t) {
  return runs([{ text: t, size: 20, color: "555555" }], { align: AlignmentType.CENTER, after: 240 });
}
function sec(t) {
  return new Paragraph({
    spacing: { before: 320, after: 130 }, keepNext: true,
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 4, color: "2F5496" } },
    children: [new TextRun({ text: t, bold: true, size: 23, color: "2F5496", font: FONT })],
  });
}
function sub(t) {
  return runs([{ text: t, bold: true }], { before: 170, after: 60, keepNext: true });
}
const box = (t) => p("☐ " + t, { indent: { left: 170 }, after: 70 });
const li  = (t) => p("– " + t, { indent: { left: 340, hanging: 170 }, after: 50 });
const u   = (n) => "_".repeat(n);

function note(t) {
  return new Paragraph({
    spacing: { before: 70, after: 150 },
    indent: { left: 170 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, space: 10, color: "BFBFBF" } },
    children: [new TextRun({ text: t, italics: true, size: 17, color: "595959", font: FONT })],
  });
}

function cell(content, width, o = {}) {
  const kids = Array.isArray(content) ? content : [p(content || "", { after: 30, size: o.size ?? 19, bold: o.bold })];
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: "auto" } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: kids,
  });
}
function table(colWidths, rows) {
  return new Table({
    width: { size: colWidths.reduce((a, c) => a + c, 0), type: WidthType.DXA },
    columnWidths: colWidths,
    borders: {
      top:    { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
      left:   { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
      right:  { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
      insideVertical:   { style: BorderStyle.SINGLE, size: 4, color: "AFAFAF" },
    },
    rows,
  });
}
// two-column form table: label | empty fill cell
function form(pairs, labelW = 3200) {
  const valW = CW - labelW;
  return table([labelW, valW], pairs.map(([label, prefill]) =>
    new TableRow({ children: [
      cell(label, labelW, { shade: "F2F2F2", bold: false }),
      cell(prefill || "", valW),
    ]})
  ));
}

/* ============================ TITEL ============================ */
A(
  title("Mietvertrag über möblierten Wohnraum"),
  subtitle("Formularvertrag zum Ausfüllen – Stand: " + "August 2026"),
);

A(sec("Vertragsparteien"));
A(b("Vermieter / Vermieterin", { after: 80 }));
A(form([
  ["Name, Vorname / Firma", ""],
  ["Straße, Hausnummer", ""],
  ["PLZ, Ort", ""],
  ["Telefon", ""],
  ["E-Mail", ""],
  ["ggf. vertreten durch (Verwaltung)", ""],
]));
A(p("– nachfolgend „Vermieter“ –", { align: AlignmentType.RIGHT, before: 80, after: 160, size: 19 }));

A(b("Mieter / Mieterin 1", { after: 80 }));
A(form([
  ["Name, Vorname", ""],
  ["Geburtsdatum / Geburtsort", ""],
  ["Derzeitige Anschrift", ""],
  ["Telefon", ""],
  ["E-Mail", ""],
  ["Ausweis-/Passnummer (freiwillig)", ""],
  ["Arbeitgeber / Tätigkeit (freiwillig)", ""],
]));
A(sp(140));
A(b("Mieter / Mieterin 2 (falls vorhanden)", { after: 80 }));
A(form([
  ["Name, Vorname", ""],
  ["Geburtsdatum / Geburtsort", ""],
  ["Derzeitige Anschrift", ""],
  ["Telefon", ""],
  ["E-Mail", ""],
]));
A(p("– nachfolgend „Mieter“ –", { align: AlignmentType.RIGHT, before: 80, after: 160, size: 19 }));
A(p("wird folgender Mietvertrag geschlossen:", { after: 100 }));

/* ============================ § 1 ============================ */
A(sec("§ 1  Mietsache"));
A(p("(1) Vermietet wird zu Wohnzwecken die nachfolgend bezeichnete möblierte Wohnung:"));
A(form([
  ["Straße, Hausnummer", ""],
  ["PLZ, Ort", ""],
  ["Lage im Gebäude", "Geschoss: ______   Wohnungs-Nr.: ______   Lage: ☐ links  ☐ rechts  ☐ Mitte"],
  ["Wohnfläche ca.", "____________ m²"],
]));
A(note("Die Wohnfläche ist nach der Wohnflächenverordnung (WoFlV) zu ermitteln. Weicht die tatsächliche Fläche um mehr als 10 % nach unten ab, liegt nach der Rechtsprechung des BGH ein Mietmangel vor. Tragen Sie die Fläche daher nur ein, wenn sie belastbar ermittelt wurde – andernfalls die Zeile streichen."));

A(p("(2) Die Wohnung besteht aus:", { before: 120 }));
A(form([
  ["Zimmer", "________ Wohn-/Schlafzimmer"],
  ["Küche", "☐ separate Küche   ☐ Kochnische   ☐ Wohnküche"],
  ["Sanitär", "________ Bad (☐ Wanne ☐ Dusche)   ________ separates WC"],
  ["Weitere Räume", "☐ Diele/Flur   ☐ Abstellraum   ☐ Speisekammer   ☐ ______________"],
  ["Freiflächen", "☐ Balkon   ☐ Loggia   ☐ Terrasse   ☐ Gartenanteil   ☐ keine"],
], 2400));

A(p("(3) Mitvermietet werden ferner:", { before: 120 }));
A(form([
  ["Kellerraum", "Nr. ______________"],
  ["Dachbodenanteil / Speicher", "Nr. ______________"],
  ["Stellplatz / Garage", "☐ ja, Nr. ____________   ☐ nein   (Entgelt siehe § 5)"],
  ["Fahrradabstellplatz", "☐ ja   ☐ nein"],
  ["Sonstiges", ""],
], 2900));

A(p("(4) Zur Mitbenutzung mit anderen Hausbewohnern stehen zur Verfügung:", { before: 120 }));
A(p("☐ Waschküche  ☐ Trockenraum  ☐ Fahrradkeller  ☐ Hof  ☐ Garten  ☐ Müllplatz  ☐ Aufzug  ☐ ______________________", { indent: { left: 170 } }));

A(p("(5) Dem Mieter werden bei Übergabe folgende Schlüssel ausgehändigt:", { before: 120 }));
A(form([
  ["Haustür / Hauseingang", "________ Stück"],
  ["Wohnungstür", "________ Stück"],
  ["Briefkasten", "________ Stück"],
  ["Keller / Nebenräume", "________ Stück"],
  ["Sonstige (Garage, Schranke, Chip)", "________ Stück"],
], 3600));
A(p("Der Mieter darf zusätzliche Schlüssel nur mit vorheriger Zustimmung des Vermieters anfertigen lassen. Bei Beendigung des Mietverhältnisses sind sämtliche Schlüssel – auch selbst beschaffte – an den Vermieter herauszugeben. Den Verlust eines Schlüssels hat der Mieter unverzüglich anzuzeigen.", { before: 100 }));

/* ============================ § 2 ============================ */
A(sec("§ 2  Möblierung und Inventar"));
A(p("(1) Die Wohnung wird möbliert vermietet. Die überlassenen Einrichtungsgegenstände, Geräte und Ausstattungen ergeben sich abschließend aus der Inventarliste (Anlage 1), die wesentlicher Bestandteil dieses Vertrages ist. Die Inventarliste weist Anzahl, Zustand und Zeitwert der Gegenstände zum Zeitpunkt der Übergabe aus und wird von beiden Vertragsparteien unterzeichnet."));
A(p("(2) Der Mieter hat die überlassenen Gegenstände pfleglich und schonend zu behandeln. Für Schäden, die über die vertragsgemäße Abnutzung hinausgehen und die der Mieter, seine Haushaltsangehörigen, Untermieter, Besucher oder von ihm beauftragte Personen zu vertreten haben, haftet der Mieter nach den gesetzlichen Vorschriften."));
A(p("(3) Die vertragsgemäße Abnutzung des Inventars ist mit der Miete abgegolten; hierfür schuldet der Mieter keinen Ersatz."));
A(p("(4) Der Vermieter hält das Inventar auf eigene Kosten in gebrauchsfähigem Zustand. Wird ein Gegenstand ohne Verschulden des Mieters unbrauchbar, ersetzt der Vermieter ihn innerhalb angemessener Frist durch einen gleichwertigen Gegenstand oder setzt ihn instand. § 12 dieses Vertrages (Kleinreparaturen) bleibt unberührt."));
A(p("(5) Der Mieter darf Inventargegenstände ohne vorherige Zustimmung des Vermieters weder aus der Wohnung entfernen noch veräußern, verpfänden, austauschen oder umgestalten."));
A(p("(6) Der Mieter ist berechtigt, eigene Einrichtungsgegenstände in die Wohnung einzubringen, soweit dadurch die Mietsache nicht beschädigt wird. Bei Vertragsende sind sie vollständig zu entfernen."));
A(p("(7) Folgende Räume, Schränke oder Flächen sind von der Nutzung ausgenommen und bleiben dem Vermieter zur Einlagerung eigener Sachen vorbehalten:"));
A(p(u(100), { indent: { left: 170 } }));
A(note("Ohne diese Vereinbarung darf der Vermieter keine eigenen Sachen in der Wohnung lagern. Wird kein Raum ausgenommen, streichen Sie Absatz 7."));

/* ============================ § 3 ============================ */
A(sec("§ 3  Mietzweck und Zahl der Bewohner"));
A(p("(1) Die Wohnung wird ausschließlich zu Wohnzwecken vermietet."));
A(p("(2) Die Wohnung ist für die Nutzung durch ________ erwachsene Person(en) und ________ Kind(er) bestimmt. Die vorübergehende Aufnahme von Besuch bleibt hiervon unberührt."));
A(p("(3) Eine gewerbliche oder freiberufliche Nutzung der Wohnung, die nach außen in Erscheinung tritt oder Publikums- bzw. Mitarbeiterverkehr auslöst, bedarf der vorherigen schriftlichen Zustimmung des Vermieters. Eine rein bürogebundene Tätigkeit ohne Außenwirkung (z. B. Homeoffice) ist gestattet."));
A(p("(4) Eine Nutzung als Ferienwohnung, zur tage- oder wochenweisen Weitervermietung (z. B. über Online-Vermittlungsportale) oder als Betriebsunterkunft ist ausgeschlossen."));

/* ============================ § 4 ============================ */
A(sec("§ 4  Mietzeit, Beginn und Vertragsart"));
A(p("(1) Das Mietverhältnis beginnt am ________________________ .", { after: 130 }));
A(p("(2) Vertragsart – es gilt ausschließlich die angekreuzte Variante:", { after: 120 }));

A(sub("Variante A – Unbefristetes Mietverhältnis (Regelfall)"));
A(box("Das Mietverhältnis läuft auf unbestimmte Zeit. Es endet durch Kündigung nach § 21 dieses Vertrages."));

A(sub("Variante B – Zeitmietvertrag nach § 575 BGB"));
A(box("Das Mietverhältnis ist befristet bis zum ________________________ und endet zu diesem Zeitpunkt, ohne dass es einer Kündigung bedarf."));
A(p("Der Vermieter beabsichtigt nach Ablauf der Mietzeit (Befristungsgrund gemäß § 575 Abs. 1 BGB – bitte konkret beschreiben):", { indent: { left: 170 }, before: 80 }));
A(box("die Räume als Wohnung für sich, seine Familienangehörigen oder Angehörige seines Haushalts zu nutzen;"));
A(box("die Räume zulässigerweise zu beseitigen oder so wesentlich zu verändern oder instand zu setzen, dass die Maßnahmen durch eine Fortsetzung des Mietverhältnisses erheblich erschwert würden;"));
A(box("die Räume an einen zur Dienstleistung Verpflichteten zu vermieten."));
A(p("Konkretisierung des Befristungsgrundes: " + u(70), { indent: { left: 170 } }));
A(p(u(105), { indent: { left: 170 } }));
A(note("Achtung: Der Befristungsgrund muss dem Mieter bei Vertragsschluss schriftlich und konkret mitgeteilt werden. Fehlt er oder ist er nur formelhaft, gilt das Mietverhältnis kraft Gesetzes als auf unbestimmte Zeit geschlossen (§ 575 Abs. 1 S. 2 BGB). Eine Befristung „einfach so“ ist im Wohnraummietrecht nicht möglich."));

A(sub("Variante C – Wohnraum zum vorübergehenden Gebrauch (§ 549 Abs. 2 Nr. 1 BGB)"));
A(box("Die Wohnung wird nur zum vorübergehenden Gebrauch vermietet vom ______________ bis ______________ ."));
A(p("Anlass des vorübergehenden Gebrauchs: " + u(58), { indent: { left: 170 } }));
A(note("Diese Variante ist nur zulässig, wenn der Aufenthalt seiner Natur nach von vornherein vorübergehend ist (z. B. befristete Projektentsendung, Kur, Messe, Praktikum, Interimswohnung während eines Umbaus). Der bloße Umstand, dass die Wohnung möbliert ist, genügt NICHT. Bei zulässiger Vereinbarung gelten die Vorschriften über Mieterhöhungen, Kündigungsschutz und Sozialklausel nicht."));

A(sub("Variante D – Möblierter Wohnraum in der vom Vermieter selbst bewohnten Wohnung (§ 549 Abs. 2 Nr. 2 BGB)"));
A(box("Der vermietete möblierte Wohnraum ist Teil der vom Vermieter selbst bewohnten Wohnung und nicht zum dauernden Gebrauch für eine Familie oder eine gemeinsam mit einer dauerhaft angelegten Haushaltsführung lebende Person überlassen."));
A(note("In diesem Fall gelten die §§ 557–561 (Mieterhöhung), 573–573d Abs. 1, 575, 575a Abs. 1, 577, 577a BGB nicht. Die Kündigung ist dann nach § 573c Abs. 3 BGB spätestens am 15. eines Monats zum Ablauf desselben Monats möglich."));

A(p("(3) Wird in Absatz 2 keine Variante angekreuzt, gilt Variante A (unbefristetes Mietverhältnis).", { before: 130 }));

/* ============================ § 5 ============================ */
A(sec("§ 5  Miete"));
A(p("(1) Die monatliche Miete setzt sich wie folgt zusammen:", { after: 120 }));
{
  const L = 6438, R = 3200;
  const row = (label, val, o = {}) => new TableRow({ children: [
    cell([p(label, { after: 30, size: 19, bold: o.bold })], L, { shade: o.shade }),
    cell([p(val, { after: 30, size: 19, bold: o.bold, align: AlignmentType.RIGHT })], R, { shade: o.shade }),
  ]});
  A(table([L, R], [
    row("a) Nettokaltmiete für die unmöblierte Wohnung", "____________ EUR"),
    row("b) Möblierungszuschlag (Entgelt für die Überlassung des Inventars)", "____________ EUR"),
    row("c) Zwischensumme Nettomiete (a + b)", "____________ EUR", { shade: "F7F7F7", bold: true }),
    row("d) Vorauszahlung auf kalte Betriebskosten (§ 7)", "____________ EUR"),
    row("e) Vorauszahlung auf Heiz- und Warmwasserkosten (§ 7)", "____________ EUR"),
    row("f) Entgelt für Stellplatz / Garage", "____________ EUR"),
    row("g) Sonstiges: ______________________________________", "____________ EUR"),
    row("Gesamtmiete monatlich (c + d + e + f + g)", "____________ EUR", { shade: "E8EEF7", bold: true }),
  ]));
}
A(p("(2) Der Möblierungszuschlag nach Absatz 1 lit. b wird gesondert ausgewiesen. Er entgilt ausschließlich die Überlassung und Instandhaltung der in Anlage 1 aufgeführten Einrichtungsgegenstände.", { before: 130 }));
A(note("Der gesonderte Ausweis ist wichtig: Die ortsübliche Vergleichsmiete und – in Gebieten mit angespanntem Wohnungsmarkt – die Mietpreisbremse (§§ 556d ff. BGB) knüpfen an die Nettokaltmiete ohne Möblierung an. Möblierte Wohnungen sind von der Mietpreisbremse nicht ausgenommen. Ohne getrennten Ausweis lässt sich die zulässige Höhe nicht darlegen."));

A(sub("Angaben zur Mietpreisbremse (nur in Gebieten mit angespanntem Wohnungsmarkt)"));
A(box("Die Wohnung liegt nicht in einem Gebiet mit angespanntem Wohnungsmarkt; die §§ 556d ff. BGB finden keine Anwendung."));
A(box("Die Wohnung liegt in einem solchen Gebiet. Der Vermieter erteilt hiermit vor Vertragsschluss unaufgefordert Auskunft nach § 556g Abs. 1a BGB:"));
A(form([
  ["Vormiete (Miete des vorherigen Mietverhältnisses)", "____________ EUR   ☐ keine Vormiete"],
  ["Ausnahmetatbestand", "☐ § 556e Abs. 1 (Vormiete)  ☐ § 556e Abs. 2 (Modernisierung)  ☐ § 556f (Neubau/umfassende Sanierung)  ☐ keiner"],
  ["Modernisierung in den letzten 3 Jahren", "☐ ja, am ______________   ☐ nein"],
  ["Erstmalige Nutzung/Vermietung nach dem 01.10.2014", "☐ ja   ☐ nein"],
], 4200));
A(note("Die Auskunft muss vor Vertragsschluss in Textform erteilt werden. Wird sie unterlassen, kann sich der Vermieter auf den Ausnahmetatbestand zunächst nicht berufen."));

/* ============================ § 6 ============================ */
A(sec("§ 6  Zahlung der Miete"));
A(p("(1) Die Gesamtmiete ist monatlich im Voraus, spätestens am dritten Werktag des Monats, kostenfrei auf folgendes Konto des Vermieters zu zahlen:"));
A(form([
  ["Kontoinhaber", ""],
  ["IBAN", ""],
  ["BIC / Kreditinstitut", ""],
  ["Verwendungszweck", ""],
], 2800));
A(p("(2) Für die Rechtzeitigkeit der Zahlung genügt es, wenn der Mieter den Zahlungsauftrag bei ausreichender Kontodeckung rechtzeitig erteilt; Verzögerungen im Zahlungsverkehr gehen nicht zu seinen Lasten.", { before: 120 }));
A(p("(3) Beginnt oder endet das Mietverhältnis im Laufe eines Monats, ist die Miete anteilig (1/30 je Tag) zu zahlen."));
A(p("(4) Bei Zahlungsverzug schuldet der Mieter Verzugszinsen nach § 288 BGB. Weitergehende Ansprüche des Vermieters bleiben unberührt."));
A(p("(5) Der Mieter kann gegen Mietforderungen nur mit unbestrittenen oder rechtskräftig festgestellten Forderungen aufrechnen oder ein Zurückbehaltungsrecht ausüben. Er hat dies dem Vermieter mindestens einen Monat vor Fälligkeit der Miete in Textform anzuzeigen (§ 556b Abs. 2 BGB). Das Recht zur Minderung nach § 536 BGB bleibt unberührt."));
A(box("Der Mieter erteilt dem Vermieter ein SEPA-Lastschriftmandat (gesondertes Formular)."));

/* ============================ § 7 ============================ */
A(sec("§ 7  Betriebs-, Heiz- und Warmwasserkosten"));
A(sub("Variante A – Vorauszahlung mit jährlicher Abrechnung (empfohlen)"));
A(box("Der Mieter trägt neben der Nettomiete die Betriebskosten im Sinne des § 556 BGB in Verbindung mit § 2 der Betriebskostenverordnung (BetrKV). Er leistet hierauf die in § 5 Abs. 1 lit. d und e vereinbarten monatlichen Vorauszahlungen."));
A(p("Umgelegt werden insbesondere:", { before: 90, indent: { left: 170 } }));
[
  "laufende öffentliche Lasten des Grundstücks (Grundsteuer)",
  "Kosten der Wasserversorgung und der Entwässerung",
  "Kosten des Betriebs der zentralen Heizungsanlage sowie der zentralen Warmwasserversorgung",
  "Kosten des Betriebs des Personen- oder Lastenaufzugs",
  "Kosten der Straßenreinigung und Müllbeseitigung",
  "Kosten der Gebäudereinigung und Ungezieferbekämpfung",
  "Kosten der Gartenpflege",
  "Kosten der Beleuchtung der Gemeinschaftsflächen",
  "Kosten der Schornsteinreinigung",
  "Kosten der Sach- und Haftpflichtversicherung des Gebäudes",
  "Kosten für den Hauswart",
  "Kosten des Betriebs der Gemeinschafts-Antennenanlage bzw. der Verteilanlage (soweit umlagefähig)",
  "Kosten des Betriebs der Einrichtungen für die Wäschepflege",
  "sonstige Betriebskosten im Sinne des § 2 Nr. 17 BetrKV, und zwar: ____________________________________",
].forEach(t => A(li(t)));
A(note("§ 2 Nr. 17 BetrKV („sonstige Betriebskosten“) ist nur wirksam, wenn die einzelnen Kostenarten konkret benannt werden – etwa Wartung von Rauchwarnmeldern, Dachrinnenreinigung, Wartung der Lüftungsanlage. Eine pauschale Bezugnahme reicht nicht."));
A(p("Nicht umlagefähig sind insbesondere Instandhaltungs- und Instandsetzungskosten, Verwaltungskosten sowie Kosten der Mietausfallwagniss-Absicherung.", { indent: { left: 170 } }));

A(sub("Variante B – Betriebskostenpauschale"));
A(box("Sämtliche Betriebskosten sind mit einer monatlichen Pauschale von ____________ EUR abgegolten. Eine Abrechnung findet nicht statt. Der Vermieter kann die Pauschale bei Kostensteigerungen nach § 560 Abs. 1 BGB anpassen."));

A(sub("Variante C – Inklusivmiete"));
A(box("Sämtliche Betriebskosten einschließlich Heizung und Warmwasser sind in der Miete enthalten (Warmmiete)."));
A(note("Vorsicht: Eine Inklusivmiete für Heizung und Warmwasser verstößt in aller Regel gegen die Heizkostenverordnung, die eine überwiegend verbrauchsabhängige Abrechnung zwingend vorschreibt. Zulässig ist sie im Wesentlichen nur in den Ausnahmefällen des § 2 und § 11 HeizkostenV (u. a. Gebäude mit nicht mehr als zwei Wohnungen, von denen eine der Vermieter selbst bewohnt). Prüfen Sie das vor dem Ankreuzen."));

A(sub("Gemeinsame Regelungen"));
A(p("(1) Der Abrechnungszeitraum ist das Kalenderjahr, sofern nicht Folgendes vereinbart ist: vom ____________ bis ____________ ."));
A(p("(2) Über die Vorauszahlungen ist jährlich abzurechnen. Die Abrechnung ist dem Mieter spätestens zwölf Monate nach Ende des Abrechnungszeitraums mitzuteilen (§ 556 Abs. 3 BGB); danach sind Nachforderungen ausgeschlossen, es sei denn, der Vermieter hat die Verspätung nicht zu vertreten."));
A(p("(3) Umlagemaßstab für die verbrauchsunabhängigen Kosten ist, soweit nicht zwingend anderes gilt:"));
A(p("☐ Wohnfläche   ☐ Anzahl der Wohneinheiten   ☐ Personenzahl   ☐ ______________________", { indent: { left: 170 } }));
A(p("(4) Die Kosten für Heizung und Warmwasser werden nach Maßgabe der Heizkostenverordnung abgerechnet, davon ______ % (mindestens 50 %, höchstens 70 %) nach erfasstem Verbrauch und der Rest nach Wohnfläche."));
A(p("(5) Die Aufteilung der Kohlendioxidkosten für Brennstofflieferungen erfolgt nach dem Kohlendioxidkostenaufteilungsgesetz (CO2KostAufG). Der auf den Vermieter entfallende Anteil wird nicht auf den Mieter umgelegt."));
A(p("(6) Vermieter und Mieter können die Höhe der Vorauszahlungen nach einer Abrechnung durch Erklärung in Textform auf eine angemessene Höhe anpassen (§ 560 Abs. 4 BGB)."));
A(p("(7) Werden nach Vertragsschluss neue Betriebskosten eingeführt oder entstehen sie erstmals, ist der Vermieter berechtigt, diese nach § 560 Abs. 1 BGB anteilig umzulegen."));
A(p("(8) Der Mieter kann nach Zugang der Abrechnung Einsicht in die Abrechnungsunterlagen nehmen; auf Wunsch werden ihm Kopien gegen Erstattung der Kosten überlassen."));

/* ============================ § 8 ============================ */
A(sec("§ 8  Mietanpassung"));
A(p("Es gilt ausschließlich die angekreuzte Variante:", { after: 110 }));
A(sub("Variante A – Gesetzliche Regelung"));
A(box("Mieterhöhungen richten sich nach den §§ 558 ff. BGB (Anpassung an die ortsübliche Vergleichsmiete unter Beachtung von Wartefrist und Kappungsgrenze) sowie nach § 559 BGB (Modernisierung)."));
A(sub("Variante B – Staffelmiete (§ 557a BGB)"));
A(box("Die Nettomiete nach § 5 Abs. 1 lit. c erhöht sich wie folgt:"));
{
  const c1 = 3213, c2 = 3213, c3 = 3212;
  const r = (a, bb, cc, head) => new TableRow({ children: [
    cell([p(a, { after: 30, size: 19, bold: head })], c1, { shade: head ? "F2F2F2" : undefined }),
    cell([p(bb, { after: 30, size: 19, bold: head })], c2, { shade: head ? "F2F2F2" : undefined }),
    cell([p(cc, { after: 30, size: 19, bold: head })], c3, { shade: head ? "F2F2F2" : undefined }),
  ]});
  A(table([c1, c2, c3], [
    r("Staffel", "gültig ab", "Nettomiete monatlich", true),
    r("1.", "____________________", "____________ EUR"),
    r("2.", "____________________", "____________ EUR"),
    r("3.", "____________________", "____________ EUR"),
    r("4.", "____________________", "____________ EUR"),
  ]));
}
A(note("Bei der Staffelmiete muss jede Staffel als Betrag (nicht als Prozentsatz) ausgewiesen sein, und die Miete muss jeweils mindestens ein Jahr unverändert bleiben. Während der Laufzeit sind Erhöhungen nach §§ 558, 559 BGB ausgeschlossen. Das Kündigungsrecht des Mieters darf höchstens für vier Jahre ausgeschlossen werden."));
A(sub("Variante C – Indexmiete (§ 557b BGB)"));
A(box("Die Nettomiete ändert sich entsprechend der Entwicklung des vom Statistischen Bundesamt ermittelten Verbraucherpreisindex für Deutschland. Die Miete muss jeweils mindestens ein Jahr unverändert bleiben. Die Änderung ist in Textform geltend zu machen und wird mit Beginn des übernächsten Monats nach Zugang der Erklärung wirksam."));
A(note("Bei Verträgen nach § 549 Abs. 2 BGB (Varianten C und D in § 4) gelten die §§ 557–561 BGB nicht; die Miete kann dort nur durch Vereinbarung geändert werden."));

/* ============================ § 9 ============================ */
A(sec("§ 9  Mietsicherheit (Kaution)"));
A(p("(1) Der Mieter leistet eine Mietsicherheit in Höhe von ____________ EUR."));
A(note("Höchstens das Dreifache der Monatsmiete ohne die als Pauschale oder Vorauszahlung ausgewiesenen Betriebskosten (§ 551 Abs. 1 BGB), also höchstens das Dreifache des Betrages aus § 5 Abs. 1 lit. c. Eine höhere Vereinbarung ist insoweit unwirksam."));
A(p("(2) Der Mieter ist berechtigt, die Sicherheit in drei gleichen monatlichen Teilzahlungen zu leisten. Die erste Teilzahlung ist zu Beginn des Mietverhältnisses fällig, die weiteren mit den unmittelbar folgenden Mietzahlungen."));
A(p("(3) Art der Sicherheit:"));
A(box("Barkaution / Überweisung auf ein Kautionskonto"));
A(box("Verpfändetes Sparkonto des Mieters"));
A(box("Selbstschuldnerische Bürgschaft eines Kreditinstituts oder einer Kautionsversicherung (Bürgschaftsurkunde als Anlage)"));
A(p("(4) Der Vermieter hat eine Barkaution getrennt von seinem eigenen Vermögen bei einem Kreditinstitut zu dem für Spareinlagen mit dreimonatiger Kündigungsfrist üblichen Zinssatz anzulegen. Die Erträge stehen dem Mieter zu und erhöhen die Sicherheit."));
A(p("(5) Der Vermieter darf während des laufenden Mietverhältnisses nicht auf die Sicherheit zugreifen, es sei denn wegen rechtskräftig festgestellter oder unbestrittener Forderungen."));
A(p("(6) Die Sicherheit ist nach Beendigung des Mietverhältnisses und Rückgabe der Mietsache abzurechnen und zurückzuzahlen, sobald dem Vermieter eine angemessene Überlegungs- und Prüffrist zur Verfügung gestanden hat. Ein angemessener Teilbetrag darf bis zur Erteilung der noch ausstehenden Betriebskostenabrechnung einbehalten werden."));

/* ============================ § 10 ============================ */
A(sec("§ 10  Übergabe und Zustand der Mietsache"));
A(p("(1) Die Wohnung wird dem Mieter am ________________________ übergeben."));
A(p("(2) Über den Zustand der Wohnung und des Inventars sowie über die Zählerstände wird bei Übergabe ein gemeinsames Protokoll erstellt (Anlage 2). Beide Parteien erhalten eine unterzeichnete Ausfertigung."));
A(p("(3) Die Wohnung wird übergeben:"));
A(p("☐ frisch renoviert   ☐ renoviert   ☐ gebrauchsfähig, nicht renoviert", { indent: { left: 170 } }));
A(p("(4) Mängel, die bei Übergabe erkennbar sind, werden im Protokoll festgehalten. Im Protokoll nicht aufgeführte Mängel hat der Mieter unverzüglich nach Entdeckung anzuzeigen (§ 536c BGB)."));
A(p("(5) Die Wohnung ist mit Rauchwarnmeldern ausgestattet: ☐ ja, Anzahl ________   ☐ nein. Die Wartung obliegt: ☐ dem Vermieter   ☐ dem Mieter. Der Mieter darf die Geräte weder entfernen noch außer Betrieb setzen und hat die Funktionsprüfung bzw. Wartung zu dulden."));

/* ============================ § 11 ============================ */
A(sec("§ 11  Obhuts- und Sorgfaltspflichten des Mieters"));
A(p("(1) Der Mieter hat die Mietsache und das Inventar schonend und pfleglich zu behandeln sowie ordnungsgemäß zu reinigen und zu lüften."));
A(p("(2) Der Mieter hat die Räume ausreichend zu beheizen und zu belüften, um Feuchtigkeits- und Frostschäden vorzubeugen. Bei längerer Abwesenheit während der Heizperiode sind geeignete Vorkehrungen gegen Frostschäden zu treffen."));
A(p("(3) Mängel und Schäden an der Mietsache sowie deren drohender Eintritt sind dem Vermieter unverzüglich anzuzeigen (§ 536c BGB). Unterlässt der Mieter die Anzeige schuldhaft, haftet er für den daraus entstehenden Schaden."));
A(p("(4) Bei längerer Abwesenheit (mehr als ____ Wochen) hat der Mieter dem Vermieter eine erreichbare Person zu benennen, die Zugang zur Wohnung gewähren kann."));
A(p("(5) Für Beschädigungen der Mietsache und des Inventars haftet der Mieter, soweit sie von ihm, seinen Haushaltsangehörigen, Besuchern, Untermietern oder von ihm beauftragten Personen schuldhaft verursacht wurden. Für Schäden, die auf vertragsgemäßem Gebrauch beruhen, haftet er nicht."));

/* ============================ § 12 ============================ */
A(sec("§ 12  Kleinreparaturen"));
A(p("(1) Der Mieter trägt die Kosten kleinerer Instandhaltungen an denjenigen Teilen der Mietsache, die seinem häufigen und unmittelbaren Zugriff ausgesetzt sind, insbesondere an Installationsgegenständen für Elektrizität, Wasser und Gas, an Heiz- und Kocheinrichtungen, an Fenster- und Türverschlüssen sowie an Verschlussvorrichtungen von Fensterläden."));
A(p("(2) Die Kostentragung ist begrenzt auf ____________ EUR (empfohlen: höchstens 100–120 EUR) je Einzelfall und insgesamt auf ______ % (höchstens 8 %) der Jahresnettomiete nach § 5 Abs. 1 lit. c innerhalb eines Kalenderjahres."));
A(p("(3) Übersteigen die Kosten einer einzelnen Reparatur den Betrag nach Absatz 2, trägt der Vermieter die Kosten in voller Höhe; eine anteilige Beteiligung des Mieters findet nicht statt."));
A(p("(4) Der Mieter ist nicht verpflichtet, Reparaturen selbst zu beauftragen oder auszuführen."));
A(note("Fehlt eine der beiden Höchstgrenzen oder fällt sie zu hoch aus, ist die gesamte Klausel nach der Rechtsprechung unwirksam – dann trägt der Vermieter alle Kosten. Setzen Sie die Beträge daher konservativ an."));

/* ============================ § 13 ============================ */
A(sec("§ 13  Schönheitsreparaturen"));
A(sub("Variante A – Vermieter trägt die Schönheitsreparaturen (bei möblierter Vermietung empfohlen)"));
A(box("Die Schönheitsreparaturen verbleiben beim Vermieter. Der Mieter schuldet weder laufende Schönheitsreparaturen noch eine Endrenovierung."));
A(sub("Variante B – Übertragung auf den Mieter"));
A(box("Der Mieter übernimmt die Schönheitsreparaturen. Sie umfassen das Streichen bzw. Tapezieren der Wände und Decken, das Streichen der Heizkörper einschließlich Heizrohre, der Innentüren sowie der Fenster und Außentüren von innen. Die Arbeiten sind fachgerecht in neutralen Farbtönen auszuführen, wenn und soweit ein Renovierungsbedarf tatsächlich besteht."));
A(note("Variante B ist nur wirksam, wenn die Wohnung dem Mieter renoviert übergeben wird oder er einen angemessenen Ausgleich erhält (BGH). Starre Fristenpläne, Endrenovierungsklauseln, Farbwahlvorgaben für die Mietzeit und Quotenabgeltungsklauseln sind unwirksam. Bei einer möbliert überlassenen Wohnung ist Variante A der sichere Weg."));

/* ============================ § 14 ============================ */
A(sec("§ 14  Bauliche Veränderungen und Einrichtungen des Mieters"));
A(p("(1) Bauliche Veränderungen der Mietsache, insbesondere Um- und Einbauten, das Verlegen von Bodenbelägen sowie Eingriffe in Leitungen, bedürfen der vorherigen Zustimmung des Vermieters in Textform."));
A(p("(2) Der Mieter darf in üblichem Umfang dübeln und bohren, soweit dies zur vertragsgemäßen Nutzung erforderlich ist. Bohrlöcher sind bei Auszug fachgerecht zu verschließen."));
A(p("(3) Vom Mieter angebrachte Einrichtungen darf er bei Beendigung des Mietverhältnisses wegnehmen (§ 539 Abs. 2 BGB); er hat den ursprünglichen Zustand fachgerecht wiederherzustellen. Der Vermieter kann die Wegnahme durch angemessene Entschädigung abwenden."));
A(p("(4) Ansprüche des Mieters auf Zustimmung zu Maßnahmen der Barrierereduzierung, des Einbruchsschutzes oder zum Betrieb einer Lademöglichkeit für Elektrofahrzeuge nach § 554 BGB bleiben unberührt."));
A(p("(5) Der Mieter hat Erhaltungsmaßnahmen sowie Modernisierungsmaßnahmen nach Maßgabe der §§ 555a bis 555f BGB zu dulden. Der Vermieter kündigt sie fristgerecht an."));

/* ============================ § 15 ============================ */
A(sec("§ 15  Betreten der Mietsache durch den Vermieter"));
A(p("(1) Der Vermieter oder von ihm beauftragte Personen dürfen die Wohnung nur aus konkretem sachlichem Anlass, nach vorheriger Ankündigung von in der Regel mindestens 24 Stunden und zu zumutbaren Tageszeiten betreten."));
A(p("(2) Bei Gefahr im Verzug (z. B. Wasserrohrbruch, Brand) darf die Wohnung ohne Ankündigung betreten werden."));
A(p("(3) Bei beabsichtigtem Verkauf oder nach Kündigung hat der Mieter Besichtigungen nach vorheriger Terminabstimmung in zumutbarem Umfang zu ermöglichen."));
A(p("(4) Der Vermieter besitzt ☐ keinen Zweitschlüssel   ☐ einen Zweitschlüssel, der nur in den Fällen des Absatzes 2 oder mit Einverständnis des Mieters verwendet werden darf."));

/* ============================ § 16 ============================ */
A(sec("§ 16  Untervermietung und Aufnahme Dritter"));
A(p("(1) Der Mieter darf den Gebrauch der Mietsache ohne Erlaubnis des Vermieters nicht einem Dritten überlassen (§ 540 BGB)."));
A(p("(2) Entsteht nach Vertragsschluss ein berechtigtes Interesse, einen Teil der Wohnung unterzuvermieten, kann der Mieter die Erlaubnis nach § 553 BGB verlangen. Der Vermieter darf sie verweigern, wenn in der Person des Dritten ein wichtiger Grund vorliegt, der Wohnraum übermäßig belegt würde oder ihm die Überlassung aus sonstigen Gründen nicht zugemutet werden kann. Der Vermieter kann die Erlaubnis von einer angemessenen Erhöhung der Miete abhängig machen."));
A(p("(3) Die Aufnahme des Ehegatten, des eingetragenen Lebenspartners sowie der Kinder des Mieters bedarf keiner Erlaubnis."));
A(p("(4) Die vollständige oder tage- bzw. wochenweise Überlassung der Wohnung an wechselnde Personen, insbesondere über Vermittlungsportale, ist ohne ausdrückliche schriftliche Zustimmung des Vermieters untersagt. Öffentlich-rechtliche Zweckentfremdungsverbote bleiben unberührt."));
A(p("(5) Bei erlaubter Untervermietung haftet der Mieter für ein Verschulden des Untermieters wie für eigenes Verschulden."));

/* ============================ § 17 ============================ */
A(sec("§ 17  Tierhaltung"));
A(p("(1) Die Haltung von Kleintieren, die keine Gefahr oder Belästigung für Mitbewohner darstellen und keine Schäden verursachen können (z. B. Ziervögel, Zierfische, Hamster), ist ohne Zustimmung gestattet."));
A(p("(2) Die Haltung sonstiger Tiere, insbesondere von Hunden und Katzen, bedarf der vorherigen Zustimmung des Vermieters. Der Vermieter entscheidet nach billigem Ermessen unter Abwägung der beiderseitigen Interessen; die Zustimmung darf nicht willkürlich verweigert werden. Sie kann bei erheblicher Störung widerrufen werden."));
A(p("(3) Vereinbart wird bereits jetzt: ☐ Tierhaltung nicht beantragt   ☐ Haltung von ______________________ wird gestattet."));
A(note("Ein generelles, ausnahmsloses Verbot der Hunde- und Katzenhaltung in Formularverträgen ist nach der Rechtsprechung des BGH unwirksam. Der Zustimmungsvorbehalt mit Einzelfallabwägung ist der zulässige Weg."));

/* ============================ § 18 ============================ */
A(sec("§ 18  Hausordnung und Rücksichtnahme"));
A(p("(1) Der Mieter hat auf die Mitbewohner Rücksicht zu nehmen. Die Ruhezeiten gelten täglich von 22:00 bis 07:00 Uhr sowie an Sonn- und Feiertagen ganztägig; im Übrigen ist Zimmerlautstärke einzuhalten, soweit dies zumutbar ist."));
A(p("(2) Die als Anlage 3 beigefügte Hausordnung ist Bestandteil dieses Vertrages: ☐ ja   ☐ es besteht keine Hausordnung."));
A(p("(3) Abfälle sind getrennt in die dafür vorgesehenen Behälter zu entsorgen. Flure, Treppenhäuser, Zugänge und Rettungswege sind freizuhalten."));
A(p("(4) Zur Reinigung der Gemeinschaftsflächen bzw. zum Winterdienst ist verpflichtet: ☐ der Vermieter bzw. ein beauftragter Dienstleister   ☐ der Mieter nach beigefügtem Plan."));

/* ============================ § 19 ============================ */
A(sec("§ 19  Rauchen"));
A(p("☐ Das Rauchen ist in der Wohnung und in den Gemeinschaftsflächen untersagt.", { indent: { left: 170 } }));
A(p("☐ Das Rauchen ist in der Wohnung gestattet; über die üblichen Gebrauchsspuren hinausgehende Verunreinigungen hat der Mieter zu beseitigen.", { indent: { left: 170 } }));

/* ============================ § 20 ============================ */
A(sec("§ 20  Versicherungen"));
A(p("(1) Der Vermieter unterhält die Gebäudeversicherung. Die umlagefähigen Kosten werden nach § 7 abgerechnet."));
A(p("(2) Dem Mieter wird dringend empfohlen, eine Hausrat- sowie eine Privathaftpflichtversicherung zu unterhalten. Der Hausrat des Mieters ist über die Gebäudeversicherung nicht abgedeckt."));
A(p("(3) ☐ Der Mieter verpflichtet sich, während der Mietzeit eine Privathaftpflichtversicherung zu unterhalten und deren Bestehen auf Verlangen nachzuweisen."));

/* ============================ § 21 ============================ */
A(sec("§ 21  Beendigung des Mietverhältnisses und Kündigung"));
A(p("(1) Die Kündigung bedarf der Schriftform (§ 568 Abs. 1 BGB). Eine Kündigung per E-Mail, SMS oder Messenger ist unwirksam."));
A(p("(2) Bei einem unbefristeten Mietverhältnis (§ 4 Variante A) kann der Mieter spätestens am dritten Werktag eines Kalendermonats zum Ablauf des übernächsten Monats kündigen. Für den Vermieter verlängert sich diese Frist nach fünf und nach acht Jahren seit Überlassung des Wohnraums um jeweils drei Monate (§ 573c Abs. 1 BGB). Die Kündigung durch den Vermieter setzt ein berechtigtes Interesse nach § 573 BGB voraus und ist zu begründen."));
A(p("(3) Bei möbliertem Wohnraum im Sinne des § 4 Variante D kann das Mietverhältnis spätestens am fünfzehnten eines Monats zum Ablauf dieses Monats gekündigt werden (§ 573c Abs. 3 BGB); eines berechtigten Interesses bedarf es nicht."));
A(p("(4) Das Recht zur außerordentlichen fristlosen Kündigung aus wichtigem Grund (§§ 543, 569 BGB) sowie zur außerordentlichen befristeten Kündigung (§ 573d BGB) bleibt für beide Parteien unberührt."));
A(p("(5) Ein Ausschluss des ordentlichen Kündigungsrechts wird vereinbart:"));
A(box("nein"));
A(box("ja, beiderseitiger Kündigungsverzicht bis zum ________________________ (höchstens vier Jahre ab Vertragsschluss)."));
A(p("(6) Setzt der Mieter den Gebrauch der Mietsache nach Ablauf der Mietzeit fort, gilt das Mietverhältnis nicht als verlängert; § 545 BGB wird abbedungen."));
A(p("(7) Die Parteien können das Mietverhältnis jederzeit einvernehmlich in Schriftform aufheben."));

/* ============================ § 22 ============================ */
A(sec("§ 22  Rückgabe der Mietsache"));
A(p("(1) Bei Beendigung des Mietverhältnisses ist die Wohnung geräumt, besenrein gereinigt und in vertragsgemäßem Zustand zurückzugeben."));
A(p("(2) Sämtliches Inventar gemäß Anlage 1 ist vollständig, gereinigt und am ursprünglichen Aufstellungsort zu übergeben. Fehlende oder über die vertragsgemäße Abnutzung hinaus beschädigte Gegenstände sind zum Zeitwert zu ersetzen."));
A(p("(3) Sämtliche Schlüssel sind zurückzugeben. Für nicht zurückgegebene Schlüssel haftet der Mieter nach den gesetzlichen Vorschriften; die Kosten eines erforderlichen Schließanlagenaustauschs trägt er nur, soweit ein solcher tatsächlich vorgenommen wird und die Schließanlage konkret gefährdet ist."));
A(p("(4) Über die Rückgabe wird ein gemeinsames Protokoll einschließlich der Zählerstände erstellt."));
A(p("(5) Der Mieter teilt dem Vermieter seine neue Anschrift für Zwecke der Betriebskostenabrechnung und der Kautionsabrechnung mit."));

/* ============================ § 23 ============================ */
A(sec("§ 23  Mehrere Mieter"));
A(p("(1) Mehrere Mieter haften für alle Verpflichtungen aus diesem Vertrag als Gesamtschuldner."));
A(p("(2) Die Mieter bevollmächtigen sich gegenseitig – widerruflich – zur Entgegennahme von Erklärungen des Vermieters mit Ausnahme von Kündigungen und Mieterhöhungsverlangen. Erklärungen des Vermieters gegenüber einem Mieter wirken insoweit auch für und gegen die übrigen Mieter."));
A(p("(3) Eine Kündigung des Mietverhältnisses muss von allen Mietern erklärt und gegenüber allen Mietern ausgesprochen werden. Der Austausch oder das Ausscheiden einzelner Mieter bedarf einer schriftlichen Vereinbarung aller Beteiligten."));

/* ============================ § 24 ============================ */
A(sec("§ 24  Wohnungsgeberbestätigung"));
A(p("Der Vermieter bestätigt dem Mieter den Einzug innerhalb von zwei Wochen nach dem Einzug schriftlich oder elektronisch (§ 19 Bundesmeldegesetz). Entsprechendes gilt für den Auszug, soweit der Mieter aus einer Wohnung auszieht und keine neue Wohnung im Inland bezieht. Eine Anmeldung bei der Meldebehörde ohne tatsächlichen Bezug der Wohnung ist unzulässig."));

/* ============================ § 25 ============================ */
A(sec("§ 25  Energieausweis"));
A(p("Dem Mieter wurde der Energieausweis nach § 80 Gebäudeenergiegesetz (GEG) spätestens bei Vertragsschluss vorgelegt bzw. in Kopie übergeben:"));
A(form([
  ["Vorlage erfolgt", "☐ ja, am ______________   ☐ nicht erforderlich (Ausnahme nach GEG)"],
  ["Art des Ausweises", "☐ Bedarfsausweis   ☐ Verbrauchsausweis"],
  ["Energiekennwert", "____________ kWh/(m²·a)"],
  ["Wesentlicher Energieträger der Heizung", ""],
  ["Baujahr des Gebäudes", ""],
  ["Energieeffizienzklasse", ""],
], 3500));

/* ============================ § 26 ============================ */
A(sec("§ 26  Datenschutz"));
A(p("Der Vermieter verarbeitet personenbezogene Daten des Mieters ausschließlich zur Begründung, Durchführung und Beendigung dieses Mietverhältnisses sowie zur Erfüllung gesetzlicher Pflichten (Art. 6 Abs. 1 lit. b und c DSGVO). Die Daten werden nach Ablauf der gesetzlichen Aufbewahrungsfristen gelöscht. Die Informationen nach Art. 13 DSGVO sind als Anlage 4 beigefügt. Dem Mieter stehen die Rechte auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Beschwerde bei einer Aufsichtsbehörde zu."));

/* ============================ § 27 ============================ */
A(sec("§ 27  Sonstige Vereinbarungen"));
for (let i = 0; i < 7; i++) A(p(u(112), { after: 200 }));

/* ============================ § 28 ============================ */
A(sec("§ 28  Schlussbestimmungen"));
A(p("(1) Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen dieses Vertrages bedürfen der Schriftform."));
A(p("(2) Wird der Vertrag für längere Zeit als ein Jahr nicht in schriftlicher Form geschlossen, so gilt er für unbestimmte Zeit (§ 550 BGB)."));
A(p("(3) Sollte eine Bestimmung dieses Vertrages ganz oder teilweise unwirksam sein oder werden, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt. An die Stelle der unwirksamen Bestimmung tritt die gesetzliche Regelung."));
A(p("(4) Die Vertragsparteien bestätigen, dass sie diesen Vertrag einschließlich sämtlicher Anlagen gelesen und verstanden haben und je eine unterzeichnete Ausfertigung erhalten."));
A(p("(5) Folgende Anlagen sind Bestandteil dieses Vertrages:"));
[
  "Anlage 1 – Inventarliste (Möblierungsverzeichnis)",
  "Anlage 2 – Übergabe-/Rückgabeprotokoll",
  "Anlage 3 – Hausordnung",
  "Anlage 4 – Datenschutzinformationen nach Art. 13 DSGVO",
  "Anlage 5 – Energieausweis (Kopie)",
  "Anlage 6 – ______________________________________",
].forEach(t => A(p("☐ " + t, { indent: { left: 170 }, after: 50 })));

/* ============================ UNTERSCHRIFTEN ============================ */
A(sec("Unterschriften"));
A(p("Ort, Datum: ________________________________________", { before: 200, after: 400 }));
{
  const c = 4819;
  const sigRow = (l, r) => new TableRow({ children: [
    cell([p(l, { after: 0, size: 18 })], c),
    cell([p(r, { after: 0, size: 18 })], c),
  ]});
  const gap = () => new TableRow({ children: [
    cell([sp(420)], c), cell([sp(420)], c),
  ]});
  A(new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [c, c],
    borders: {
      top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
      left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
      insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
    },
    rows: [
      gap(),
      sigRow("_____________________________________", "_____________________________________"),
      sigRow("Vermieter / Vermieterin", "Mieter / Mieterin 1"),
      gap(),
      sigRow("_____________________________________", "_____________________________________"),
      sigRow("ggf. weiterer Vermieter", "Mieter / Mieterin 2"),
    ],
  }));
}

/* ============================ ANLAGE 1 ============================ */
A(new Paragraph({ children: [new PageBreak()] }));
A(title("Anlage 1 – Inventarliste"));
A(subtitle("Verzeichnis der mitvermieteten Einrichtungsgegenstände"));
A(p("Zur Wohnung: ________________________________________________________________________", { after: 60 }));
A(p("Mieter: ______________________________________   Übergabedatum: ______________________", { after: 200 }));
A(p("Zustandsschlüssel: 1 = neuwertig · 2 = gut · 3 = gebraucht, gebrauchsfähig · 4 = stark gebraucht", { size: 18, after: 140 }));
{
  const w = [1500, 3300, 800, 1900, 2138];
  const hdr = new TableRow({ tableHeader: true, children:
    ["Raum", "Gegenstand / Marke / Modell", "Anzahl", "Zustand (1–4) / Mängel", "Zeitwert in EUR"]
      .map((t, i) => cell([p(t, { after: 20, size: 18, bold: true })], w[i], { shade: "E8EEF7" }))
  });
  const empty = () => new TableRow({ children: w.map(x => cell([p("", { after: 90, size: 18 })], x)) });
  const rows = [hdr];
  const roomRow = (name) => new TableRow({ children: [
    cell([p(name, { after: 20, size: 18, bold: true })], w[0], { shade: "F2F2F2" }),
    ...w.slice(1).map(x => cell([p("", { after: 90, size: 18 })], x)),
  ]});
  ["Wohnzimmer", "Schlafzimmer", "Küche", "Bad", "Flur / Diele", "Balkon / Keller", "Sonstiges"].forEach(r => {
    rows.push(roomRow(r));
    for (let i = 0; i < 3; i++) rows.push(empty());
  });
  A(table(w, rows));
}
A(p("Summe Zeitwert Inventar: ____________________ EUR", { before: 180, bold: true }));
A(p("Die Vertragsparteien bestätigen die Vollständigkeit und Richtigkeit dieser Inventarliste. Sie ist Bestandteil des Mietvertrages.", { before: 140, size: 18 }));
A(p("", { after: 320 }));
A(p("____________________________________                    ____________________________________"));
A(p("Vermieter / Vermieterin                                             Mieter / Mieterin", { size: 18 }));

/* ============================ ANLAGE 2 ============================ */
A(new Paragraph({ children: [new PageBreak()] }));
A(title("Anlage 2 – Übergabe-/Rückgabeprotokoll"));
A(subtitle("Zutreffendes bitte ankreuzen:  ☐ Übergabe an den Mieter   ☐ Rückgabe an den Vermieter"));
A(form([
  ["Wohnung (Anschrift)", ""],
  ["Datum / Uhrzeit", ""],
  ["Anwesend", ""],
], 3000));
A(sub("Zählerstände"));
{
  const w = [3200, 3200, 3238];
  const r = (a, bb, cc, head) => new TableRow({ children: [
    cell([p(a, { after: 30, size: 19, bold: head })], w[0], { shade: head ? "E8EEF7" : undefined }),
    cell([p(bb, { after: 30, size: 19, bold: head })], w[1], { shade: head ? "E8EEF7" : undefined }),
    cell([p(cc, { after: 30, size: 19, bold: head })], w[2], { shade: head ? "E8EEF7" : undefined }),
  ]});
  A(table(w, [
    r("Zähler", "Zählernummer", "Zählerstand", true),
    r("Strom", "", ""), r("Gas", "", ""), r("Wasser (kalt)", "", ""),
    r("Wasser (warm)", "", ""), r("Heizung / Wärmemengenzähler", "", ""),
  ]));
}
A(sub("Zustand der Räume"));
{
  const w = [2100, 5300, 2238];
  const r = (a, bb, cc, head) => new TableRow({ children: [
    cell([p(a, { after: head ? 20 : 90, size: 18, bold: head })], w[0], { shade: head ? "E8EEF7" : undefined }),
    cell([p(bb, { after: head ? 20 : 90, size: 18, bold: head })], w[1], { shade: head ? "E8EEF7" : undefined }),
    cell([p(cc, { after: head ? 20 : 90, size: 18, bold: head })], w[2], { shade: head ? "E8EEF7" : undefined }),
  ]});
  const rows = [r("Raum", "Festgestellte Mängel / Bemerkungen", "Zu beseitigen bis", true)];
  ["Wohnzimmer", "Schlafzimmer", "Küche", "Bad / WC", "Flur / Diele", "Balkon / Terrasse", "Keller / Nebenräume", "Fenster / Türen", "Böden / Wände / Decken", "Elektro / Sanitär / Heizung"]
    .forEach(x => rows.push(r(x, "", "")));
  A(table(w, rows));
}
A(sub("Schlüsselübergabe"));
A(p("Haustür ______ Stück · Wohnungstür ______ Stück · Briefkasten ______ Stück · Keller ______ Stück · Sonstige ______ Stück"));
A(sub("Inventar"));
A(p("☐ Das Inventar gemäß Anlage 1 wurde vollständig und im dort beschriebenen Zustand übergeben / zurückgegeben."));
A(p("☐ Abweichungen: ______________________________________________________________________"));
A(p("", { after: 320 }));
A(p("____________________________________                    ____________________________________"));
A(p("Vermieter / Vermieterin                                             Mieter / Mieterin", { size: 18 }));

/* ============================ ANLAGE 3 ============================ */
A(new Paragraph({ children: [new PageBreak()] }));
A(title("Anlage 3 – Hausordnung"));
A(subtitle("Muster – bei Bedarf anpassen oder streichen"));
[
  ["Ruhezeiten", "Täglich von 22:00 bis 07:00 Uhr sowie sonn- und feiertags ganztägig ist Ruhe zu halten. Musizieren und laute Haushaltsgeräte sind außerhalb dieser Zeiten in zumutbarem Umfang gestattet."],
  ["Treppenhaus und Zugänge", "Flure, Treppen und Hauseingänge sind freizuhalten; sie dienen als Rettungswege. Das Abstellen von Gegenständen, Fahrrädern oder Kinderwagen ist nur an den dafür vorgesehenen Plätzen zulässig."],
  ["Reinigung", "Die Reinigung der Gemeinschaftsflächen erfolgt: ☐ durch einen beauftragten Dienstleister   ☐ turnusmäßig durch die Bewohner nach Aushang."],
  ["Abfall", "Abfälle sind getrennt in die dafür bereitgestellten Behälter zu entsorgen. Sperrmüll ist eigenständig zu entsorgen."],
  ["Lüften und Heizen", "Die Räume sind regelmäßig durch Stoßlüften zu belüften und ausreichend zu beheizen, um Feuchtigkeitsschäden zu vermeiden. Dauerkippstellung der Fenster ist zu vermeiden."],
  ["Waschküche / Trockenraum", "Die Nutzung richtet sich nach dem Aushang. Nach Benutzung sind die Räume und Geräte gereinigt zu hinterlassen."],
  ["Grillen", "☐ Grillen auf Balkon und Terrasse ist untersagt.   ☐ Elektrogrills sind gestattet."],
  ["Sicherheit", "Haus- und Kellertüren sind zwischen 22:00 und 06:00 Uhr geschlossen zu halten. Rauchwarnmelder dürfen nicht entfernt oder abgedeckt werden."],
  ["Winterdienst", "Räum- und Streupflicht auf den Gehwegen: ☐ Vermieter / Dienstleister   ☐ Bewohner nach Plan."],
].forEach(([h, t]) => { A(sub(h)); A(p(t)); });

/* ============================ ANLAGE 4 ============================ */
A(new Paragraph({ children: [new PageBreak()] }));
A(title("Anlage 4 – Datenschutzinformationen"));
A(subtitle("Information nach Art. 13 DSGVO"));
A(sub("1. Verantwortlicher"));
A(p("Verantwortlich für die Verarbeitung ist der in diesem Mietvertrag genannte Vermieter mit der dort angegebenen Anschrift und den dort genannten Kontaktdaten."));
A(sub("2. Zwecke und Rechtsgrundlagen"));
A(p("Die Verarbeitung Ihrer personenbezogenen Daten erfolgt zur Anbahnung, Begründung, Durchführung und Beendigung des Mietverhältnisses (Art. 6 Abs. 1 lit. b DSGVO), zur Erfüllung rechtlicher Verpflichtungen wie melde-, steuer- und handelsrechtlicher Aufbewahrungspflichten (Art. 6 Abs. 1 lit. c DSGVO) sowie – soweit einschlägig – zur Wahrung berechtigter Interessen, etwa der Geltendmachung von Forderungen (Art. 6 Abs. 1 lit. f DSGVO)."));
A(sub("3. Kategorien verarbeiteter Daten"));
A(p("Stammdaten (Name, Geburtsdatum, Anschrift), Kontaktdaten, Vertrags- und Abrechnungsdaten, Zahlungsdaten sowie – soweit vom Mieter freiwillig übermittelt – Bonitäts- und Beschäftigungsangaben."));
A(sub("4. Empfänger"));
A(p("Eine Weitergabe erfolgt nur, soweit dies zur Vertragsdurchführung oder zur Erfüllung rechtlicher Pflichten erforderlich ist, insbesondere an Hausverwaltung, Messdienstleister und Abrechnungsunternehmen, Handwerksbetriebe, Versorgungsunternehmen, Steuerberater sowie Behörden und Gerichte."));
A(sub("5. Speicherdauer"));
A(p("Die Daten werden für die Dauer des Mietverhältnisses und darüber hinaus bis zum Ablauf der gesetzlichen Aufbewahrungs- und Verjährungsfristen gespeichert und anschließend gelöscht."));
A(sub("6. Ihre Rechte"));
A(p("Sie haben das Recht auf Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) sowie ein Widerspruchsrecht (Art. 21 DSGVO). Ferner steht Ihnen ein Beschwerderecht bei einer Datenschutz-Aufsichtsbehörde zu."));
A(sub("7. Bereitstellungspflicht"));
A(p("Die Bereitstellung der zur Vertragsdurchführung erforderlichen Daten ist für den Abschluss des Mietvertrages notwendig. Ohne diese Daten kann der Vertrag nicht geschlossen oder durchgeführt werden."));

/* ============================ AUSFÜLLHINWEISE ============================ */
A(new Paragraph({ children: [new PageBreak()] }));
A(title("Ausfüllhinweise"));
A(subtitle("Diese Seite ist nicht Bestandteil des Mietvertrages – bitte vor der Unterzeichnung entfernen."));
const hint = (h, t) => { A(sub(h)); A(p(t)); };
hint("1. Möbliert heißt nicht rechtlos",
  "Ein möblierter Mietvertrag ist ein ganz normaler Wohnraummietvertrag. Kündigungsschutz, Mietpreisbremse und Betriebskostenrecht gelten in vollem Umfang. Die Sonderregeln des § 549 Abs. 2 BGB greifen nur in den dort genannten engen Ausnahmefällen (§ 4 Varianten C und D).");
hint("2. Möblierungszuschlag getrennt ausweisen",
  "Tragen Sie in § 5 die Nettokaltmiete für die unmöblierte Wohnung und den Möblierungszuschlag getrennt ein. In der Praxis wird der Zuschlag häufig aus dem Zeitwert des Inventars abgeleitet (verbreitet: monatlich rund 1–2 % des Zeitwerts, zuzüglich eines angemessenen Instandhaltungs- und Verzinsungsanteils). Halten Sie die Berechnung schriftlich fest, damit Sie sie im Streitfall belegen können.");
hint("3. Inventarliste sorgfältig führen",
  "Die Inventarliste (Anlage 1) ist bei möblierter Vermietung Ihr wichtigstes Beweismittel. Notieren Sie Marke, Modell, Zustand und Zeitwert jedes Gegenstandes und ergänzen Sie datierte Fotos. Beide Seiten unterschreiben die Liste bei Übergabe und bei Rückgabe.");
hint("4. Befristung nur mit Grund",
  "Eine Befristung ohne den gesetzlich vorgeschriebenen und konkret benannten Grund (§ 575 BGB) führt dazu, dass der Vertrag als unbefristet gilt. Wenn Sie sich nicht sicher sind, wählen Sie Variante A und arbeiten Sie stattdessen mit einem befristeten Kündigungsverzicht (§ 21 Abs. 5).");
hint("5. Kaution und Höchstgrenzen",
  "Die Kaution darf höchstens drei Nettomonatsmieten ohne Betriebskosten betragen. Prüfen Sie außerdem die Höchstgrenzen bei den Kleinreparaturen (§ 12) – zu hohe Beträge machen die gesamte Klausel unwirksam.");
hint("6. Vor Vertragsschluss zu erledigen",
  "Energieausweis vorlegen (§ 25), bei Mietpreisbremse die Auskunft nach § 556g Abs. 1a BGB in Textform erteilen (§ 5), Inventarliste und Übergabeprotokoll vorbereiten, Datenschutzinformationen aushändigen. Nach dem Einzug: Wohnungsgeberbestätigung innerhalb von zwei Wochen ausstellen (§ 24).");
hint("7. Streichen statt stehen lassen",
  "Nicht gewählte Varianten und nicht benötigte Absätze sollten gestrichen (durchgestrichen und von beiden Seiten abgezeichnet) oder gelöscht werden. Beide Parteien erhalten je eine vollständig unterzeichnete Ausfertigung inklusive aller Anlagen.");
hint("Rechtlicher Hinweis",
  "Dieses Formular ist eine allgemeine Vorlage und ersetzt keine Rechtsberatung im Einzelfall. Landesrechtliche Besonderheiten (z. B. Zweckentfremdungsverbote, Rauchwarnmelderpflichten, Winterdienstsatzungen), kommunale Mietspiegel sowie die aktuelle Rechtsprechung können abweichende Regelungen erfordern. Lassen Sie den ausgefüllten Vertrag im Zweifel von einer Rechtsanwältin oder einem Rechtsanwalt für Mietrecht oder einem Eigentümerverband prüfen.");

/* ============================ DOKUMENT ============================ */
const doc = new Document({
  creator: "Vermieter",
  title: "Mietvertrag über möblierten Wohnraum",
  description: "Formularvertrag zum Ausfüllen",
  styles: {
    default: {
      document: { run: { font: FONT, size: 20 }, paragraph: { spacing: { line: 264 } } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1134, bottom: 1134, left: 1134, right: 1134, header: 567, footer: 567 },
      },
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, space: 4, color: "BFBFBF" } },
          children: [new TextRun({ text: "Mietvertrag über möblierten Wohnraum", size: 16, color: "808080", font: FONT })],
        }),
      ]}),
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: ["Seite ", PageNumber.CURRENT, " von ", PageNumber.TOTAL_PAGES], size: 16, color: "808080", font: FONT })],
        }),
      ]}),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  require("fs").writeFileSync(process.argv[2] || "Mietvertrag.docx", buf);
  console.log("OK ->", process.argv[2]);
});
