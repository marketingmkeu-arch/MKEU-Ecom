/* =====================================================================
   ALLE TEXTE DER SEITE – HIER ANPASSEN
   ---------------------------------------------------------------------
   So funktioniert's:
   • Text ändern:      Einfach den Text zwischen den Anführungszeichen "..." ändern.
   • Text entfernen:   Die ganze Zeile löschen (oder den Text leer lassen: "").
   • Abschnitt aus:    Bei einem Abschnitt  anzeigen: false  setzen.
   • Eintrag entfernen (z. B. eine News-Karte): den ganzen { ... }-Block
                       inkl. Komma löschen.
   • Bilder:           Bild in den Ordner "bilder" legen und den Dateinamen
                       eintragen, z. B.  bild: "bilder/news-1.jpg"
                       Leer lassen ("") = es wird ein Platzhalter angezeigt.
   • Kleine HTML-Tags sind erlaubt, z. B. <sup>®</sup> oder <br> (Zeilenumbruch).

   Achtung: Jeder Text muss in "..." stehen und nach jedem Eintrag
   kommt ein Komma. Wenn die Seite danach leer ist, fehlt meistens
   ein Komma oder ein Anführungszeichen.
   ===================================================================== */

window.SEITE = {

  /* ---------- Allgemein ---------- */
  seitenTitel: "KOCKS – Testprojekt",

  logo: {
    text: "KOCKS",
    bild: ""            // z. B. "bilder/logo.svg" – leer = Text-Logo mit Platzhalter-Symbol
  },

  /* ---------- Menü (öffnet sich über das ☰-Symbol oben rechts) ---------- */
  menue: [
    { titel: "Products", links: ["Bar &amp; Wire rod Mills", "Tube Mills", "Profile &amp; Surface", "Process &amp; Automation"] },
    { titel: "Service", links: [] },
    { titel: "References", links: ["RSB<sup>®</sup>", "SRB<sup>®</sup> &amp; EXB", "KOCKS Locations"] },
    { titel: "Company", links: ["About Us", "History", "Careers", "News", "Contact", "Netiquette", "Legal details", "Data protection notice"] }
  ],

  /* ---------- Startbereich (großes blaues Feld oben) ---------- */
  hero: {
    anzeigen: true,
    bild: "",           // Hintergrundbild, z. B. "bilder/hero.jpg"
    marke: "KOCKS ROLLED<sup>®</sup>",
    zeile1: "WE MAKE YOUR",
    zeile2: "PRODUCT",
    zeile2Gold: "GOLD",
    text: "We know from our long-term customer relationships that KOCKS rolled<sup>®</sup> steel stands for an extraordinary quality.",
    reiter: ["Bar &amp; Wire rod Mills", "Tube Mills", "Profile &amp; Surface", "Process &amp; Automation"]
  },

  /* ---------- Zahlen ---------- */
  zahlen: {
    anzeigen: true,
    eintraege: [
      { zahl: "62,500,000", einheit: "TONS" },
      { zahl: "255", einheit: "BLOCKS" }
    ]
  },

  /* ---------- "It's more than just a machine" mit Video ---------- */
  intro: {
    anzeigen: true,
    ueberschrift: "IT’S MORE THAN<br>JUST A MACHINE.",
    videoBild: "",      // Vorschaubild des Videos
    videoLink: "",      // z. B. YouTube-Link – leer = Play-Button ohne Funktion
    videoUntertitel: "IT’S MORE THAN JUST A MACHINE",
    lead: "The “more” is a promise of invisible added value.",
    absaetze: [
      "Around the world, our 3-roll blocks set the benchmark for precision and reliability. Yet the machine is only the visible result. Behind it stand passion and dedication, a unique fusion of people who care, a values-driven culture, and technologies that anticipate what’s next. Through ingenious mechanical engineering, combined with targeted digitalization and automation, we believe in creating premium rolling solutions together with our customers. KOCKS is THE specialist with a 100% focus on 3-roll technology, and THE trusted partner on the journey to producing the highest-quality long products.",
      "KOCKS rolled<sup>®</sup> – We make your product gold."
    ]
  },

  /* ---------- Blaues Banner (Magazin) ---------- */
  banner: {
    anzeigen: true,
    titelGold: "IT´S MORE",
    titelWeiss: "THAN<br>JUST A MACHINE.",
    textGold: "Commitment, longevity, inventiveness, flexibility, reliability, sustainability.",
    text: "Immerse yourself. In the KOCKS News we demonstrate our special quality.",
    bild: ""            // Magazin-Bild rechts
  },

  /* ---------- News ---------- */
  news: {
    anzeigen: true,
    ueberschrift: "NEWS",
    linkText: "Read more",
    // farbe: "blau" oder "gold"
    eintraege: [
      { datum: "OCT 27, 2026", titel: "4D EAGLE S 50 IN OPERATION AT BADISCHE STAHLWERKE", farbe: "blau", bild: "", link: "#" },
      { datum: "OCT 7, 2026",  titel: "MASTEEL DECIDES FOR THE 4D EAGLE S LASER GAUGE",   farbe: "gold", bild: "", link: "#" },
      { datum: "JUL 29, 2026", titel: "STEELTEC INTEGRATES THE 4D EAGLE S LASER SYSTEM",   farbe: "blau", bild: "", link: "#" }
    ]
  },

  /* ---------- Experts & People ---------- */
  experten: {
    anzeigen: true,
    kategorie: "EXPERTS &amp; PEOPLE",
    ueberschrift: "WE MAKE THE<br>DIFFERENCE",
    linkText: "Read more",
    eintraege: [
      { kategorie: "KNOW-HOW FOR TOMORROW", titel: "KOCKS SERVICE – IT'S MORE THAN JUST SPARE PARTS.", farbe: "blau", bild: "", link: "#" },
      { kategorie: "WORKING @ KOCKS",       titel: "PERSONALITY IS MORE IMPORTANT THAN MERE GRADES.", farbe: "gold", bild: "", link: "#" }
    ]
  },

  /* ---------- Kontakt ---------- */
  kontakt: {
    anzeigen: true,
    ueberschrift: "CONTACT US",
    text: "Customer satisfaction is our highest priority. If you have any questions about our products or services, please feel free to contact us by e-mail or give us a call. We look forward to hearing from you!",
    linkText: "Contact",
    link: "#",
    bild: ""
  },

  /* ---------- Know-how (dunkelblauer Abschnitt) ---------- */
  knowhow: {
    anzeigen: true,
    kategorie: "KNOW-HOW FOR TOMORROW",
    ueberschrift: "KOCKS STANDS FOR PREMIUM PROCESSES AND PRODUCTS",
    bild: "",
    absaetze: [
      "Since 1946, our 3-roll technology has been setting quality standards in the production of high-quality bar, wire rod and tube.",
      "Our customers confirm our pursuit of perfection with the words: „The KOCKS process is essential for the final quality of the rolled product“."
    ]
  },

  /* ---------- Footer (unten) ---------- */
  footer: {
    anzeigen: true,
    // Die Link-Spalten kommen aus "menue" oben.
    newsButton: "KOCKS NEWS",
    auszeichnungBild: "",    // z. B. Siegel/Award – leer = Platzhalter
    zeigeLinkedin: true
  },

  /* ---------- Schwebende Buttons rechts (E-Mail / Telefon / LinkedIn) ---------- */
  seitenButtons: {
    anzeigen: true,
    email: "mailto:test@example.com",
    telefon: "tel:+490000000000",
    linkedin: "#"
  },

  /* ---------- TESTPROJEKT-HINWEIS (ganz unten) ---------- */
  hinweis: {
    anzeigen: true,
    titel: "Testprojekt",
    text: "Dies ist ein nicht-offizieller Nachbau zu Test- und Demonstrationszwecken. Keine Verbindung zum Original-Unternehmen, kein echtes Angebot. Alle Bilder sind Platzhalter."
  }
};
