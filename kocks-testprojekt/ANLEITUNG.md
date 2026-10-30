# Testprojekt – Anleitung

Nicht-offizieller Nachbau einer Webseite, nur zu Test- und Demozwecken.

## Öffnen
`index.html` per Doppelklick im Browser öffnen. Ein Server ist nicht nötig.

## Was liegt wo?
| Datei        | Wofür                                                          |
|--------------|----------------------------------------------------------------|
| `content.js` | **Alle Texte**, Links, Bildpfade. Hier änderst du fast alles.   |
| `style.css`  | Farben & Schrift ganz oben (`:root`), danach das Layout.        |
| `script.js`  | Baut die Seite aus `content.js` – normalerweise nicht anfassen. |
| `bilder/`    | Eigene Bilder hier ablegen.                                     |

## Häufige Änderungen
- **Wort/Text ändern:** in `content.js` den Text zwischen `"..."` ändern.
- **Textpassage streichen:** Zeile löschen oder Text leer lassen `""`.
- **Ganzen Abschnitt ausblenden:** `anzeigen: false` setzen.
- **News-Karte entfernen/hinzufügen:** einen `{ ... },`-Block löschen bzw. kopieren.
- **Bild einsetzen:** Datei nach `bilder/` legen, z. B. `bild: "bilder/news-1.jpg"`.
- **Farbe ändern:** in `style.css` oben z. B. `--gold: #b89d5f;` anpassen.

Seite plötzlich leer? Meist fehlt in `content.js` ein Komma oder ein Anführungszeichen.
