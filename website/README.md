# Cañas Hairstyling – Website

Neue, schlanke Website (reines HTML/CSS/JS, keine Frameworks, keine Build-Tools).
Läuft auf jedem simplen Webspace oder Server – kein teures CMS-Hosting nötig.

## Lokal ansehen

Kein Build-Schritt nötig. Einfach im `website/`-Ordner einen lokalen Server starten:

```bash
cd website
python3 -m http.server 8000
# dann im Browser: http://localhost:8000
```

## ⚠️ Vor dem Live-Schalten: Checkliste

Die Seite ist komplett fertig gebaut und einsatzbereit, enthält aber noch bewusst
markierte Platzhalter (im Code mit `TODO:`-Kommentaren markiert). Diese müssen vor
dem Go-Live ersetzt werden:

### 1. Logo
- Aktuell: Text-Logo "Cañas *Hairstyling*" mit rundem "C"-Icon.
- Ersetzen in `index.html` (Klasse `.logo`) durch `<img src="images/logo.svg" alt="Cañas Hairstyling">`,
  sobald das echte Logo als Datei vorliegt. Am besten SVG oder PNG mit transparentem Hintergrund.

### 2. Fotos
- **Hero-Bild** (`.hero-photo-placeholder`): Foto der beiden Inhaberinnen, lächelnd, hochauflösend (mind. 1600px breit).
- **Über-uns-Bild** (`.photo-placeholder.square`): Team-/Salon-Foto.
- Dateien in `website/images/` ablegen und die Platzhalter-`<div>`s durch `<img>`-Tags ersetzen.

### 3. Vorher/Nachher-Galerie
- 3 Kartenpaare sind vorbereitet (Abschnitt `#vorher-nachher`).
- Für jedes Paar: Vorher-Foto + Nachher-Foto + kurze Beschreibung (z. B. "Balayage & Schnitt").
- **Wichtig:** Vorher schriftlich/mündlich die Zustimmung der Kund:innen einholen, dass die Fotos verwendet werden dürfen.

### 4. Bewertungen / Trust-Badge
- Trust-Badge im Hero-Bild zeigt aktuell Platzhalterwerte ("4,9 · 312 Bewertungen").
  → Mit echter Google-Bewertungszahl und Sternebewertung aktualisieren.
- Abschnitt "Bewertungen": 3 Screenshot-Rahmen vorbereitet – dort echte Screenshots
  aus Google Maps bzw. Treatwell einsetzen (als `<img>` statt Platzhalter).
- Link "Alle Google-Bewertungen ansehen" mit dem echten Google-Maps-Link des Salons verknüpfen.

### 5. Treatwell-Buchung
Der Buchungsbereich (`#booking`) hat aktuell einen Fallback-Button, der auf die
Treatwell-Salonseite verlinken soll – dafür den echten Link eintragen (im Code
mit `TODO: echten Treatwell-Buchungslink eintragen` markiert).

Für die **volle Einbindung als Widget direkt auf der Seite** (kein Redirect):
1. Im Treatwell-Partnerbereich einloggen → Marketing/Website-Widget-Bereich.
2. Den dort bereitgestellten Embed-Code (iframe oder Script-Snippet) kopieren.
3. In `index.html` im Kommentarblock `<!-- TREATWELL EINBINDUNG -->` einfügen.

Ich habe hier bewusst keinen frei erfundenen Embed-Code/API-Call eingebaut, da ich
ohne Zugriff auf euren Treatwell-Account nicht garantieren kann, dass eine geratene
URL oder ein geratenes API-Format tatsächlich funktioniert – das würde nur eine
kaputte Buchungsstrecke produzieren. Sobald ihr mir den Embed-Code aus eurem
Treatwell-Dashboard schickt, baue ich ihn direkt ein.

### 6. Kontaktdaten & Karte
In `index.html`, Abschnitt `#kontakt` und Footer, folgende Platzhalter ersetzen:
- `[Straße Hausnummer]`, `[PLZ Ort]`
- `[Telefonnummer]` (kommt mehrfach vor: Header, Hero-Alternative, Kontakt, WhatsApp-Link `wa.me/...`)
- Öffnungszeiten in der Tabelle (`.hours-table`)
- Google-Maps-Einbettung: Kartenausschnitt bei Google Maps holen ("Teilen" → "Karte einbetten")
  und den `<iframe>`-Code anstelle von `.map-placeholder` einsetzen.

### 7. Rechtliches
- Impressum & Datenschutzerklärung sind in Deutschland Pflicht. Footer-Links
  aktuell auf `#` – auf echte Unterseiten verlinken, sobald diese existieren.

### 8. Über-uns-Text
- Platzhaltertext im Abschnitt `#ueber-uns` durch eure echte Geschichte ersetzen
  (seit wann gibt's den Salon, Spezialgebiete, was euch besonders macht).

## Hosting

Aktuell zahlt ihr wohl deutlich mehr, als für eine schlanke statische Seite wie
diese nötig ist. Optionen, sobald ein eigener Server steht:

- **Eigener Server/VPS**: Die `website/`-Dateien direkt per nginx/Apache als
  statische Dateien ausliefern (kein PHP, keine Datenbank nötig). Ein günstiger
  VPS (wenige Euro/Monat) reicht dafür locker.
- **Alternative ganz ohne eigenen Server**: Kostenlose statische Hoster wie
  Netlify, Vercel oder Cloudflare Pages – Ordner hochladen, fertig, inkl. SSL.

Sagt Bescheid, sobald der Server steht – dann helfe ich beim Deployment
(z. B. Nginx-Konfiguration, HTTPS-Zertifikat via Let's Encrypt).

## Technischer Hinweis (bereits behoben)

Die Google-Fonts-Einbindung lädt bewusst **asynchron** (`media="print" onload="this.media='all'"`
Pattern). Eine normale, blockierende Google-Fonts-Verlinkung hätte in Netzwerken,
in denen `fonts.googleapis.com` nicht erreichbar ist (Adblocker, Firmen-Firewalls,
o.ä.), das gesamte Seiten-JavaScript – inklusive des mobilen Menüs – lahmgelegt.
Das ist jetzt abgesichert.

## Struktur

```
website/
├── index.html      Alle Inhalte/Struktur der Einseiter-Seite
├── css/style.css    Gesamtes Styling (responsive, mobile-first Nav)
├── js/main.js       Mobile-Menü-Toggle + Footer-Jahr
└── images/          Hier echte Fotos/Logo ablegen
```
