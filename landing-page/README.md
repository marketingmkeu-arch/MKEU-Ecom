# MedNail Landing Page – Bearbeitungsanleitung

## Dateien
```
landing-page/
├── index.html      ← Die Landing Page (hier alles bearbeiten)
├── style.css       ← Alle Styles (Farben, Abstände, Schriften)
├── images/         ← Deine Bilder hier ablegen
│   └── (lege hier .jpg / .png / .webp Dateien ab)
└── README.md       ← Diese Anleitung
```

## Schnell-Anleitung

### Text ändern
Öffne `index.html` und suche den Text, den du ändern willst. Jede Section ist mit einem Kommentar markiert:
```html
<!-- ══════ SECTION: Hero ══════ -->
```

### Bild einfügen
Lege dein Bild in den `images/` Ordner und ersetze einen Platzhalter:
```html
<!-- VORHER (Platzhalter): -->
<div class="img-placeholder">Produktbild hier einfügen</div>

<!-- NACHHER (dein Bild): -->
<img src="images/dein-bild.jpg" alt="Beschreibung">
```

### Neue Bild-Section hinzufügen
Kopiere diesen Block und füge ihn an der gewünschten Stelle in `index.html` ein:

```html
<!-- ══════ SECTION: Neue Bild-Section ══════ -->
<section class="section">
  <div class="wrap">
    <img src="images/dein-bild.jpg" alt="Beschreibung" class="full-image">
  </div>
</section>
```

Für ein Bild mit Text daneben:
```html
<section class="section">
  <div class="wrap">
    <div class="image-text-row">
      <img src="images/dein-bild.jpg" alt="Beschreibung">
      <div>
        <h2>Deine Überschrift</h2>
        <p>Dein Text hier.</p>
      </div>
    </div>
  </div>
</section>
```

Für eine Bild-Galerie:
```html
<section class="section">
  <div class="wrap">
    <div class="image-grid cols-3">
      <img src="images/bild-1.jpg" alt="Bild 1">
      <img src="images/bild-2.jpg" alt="Bild 2">
      <img src="images/bild-3.jpg" alt="Bild 3">
    </div>
  </div>
</section>
```

### Farben ändern
Öffne `style.css` und ändere die Werte ganz oben bei `:root`:
```css
:root {
  --green: #00A86B;    /* ← CTA-Buttons, Akzentfarbe */
  --navy: #0C1F3B;     /* ← Dunkle Hintergründe */
  --blue: #2B7DE9;     /* ← Blau-Akzent */
}
```

### Section-Reihenfolge ändern
Schneide einen ganzen `<!-- ══════ SECTION: ... ══════ -->` Block aus und füge ihn an der neuen Position ein.

### Section löschen
Lösche alles von `<!-- ══════ SECTION: Name ══════ -->` bis zum nächsten `<!-- ══════ SECTION: ... ══════ -->`.
