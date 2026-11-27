---
name: ebay-inserate
description: eBay-Inserate für Sammelkarten (TCG Sealed-Produkte und Einzelkarten) aus Fotos und Preis erstellen und über die eBay-Pipeline in ebay-agent/ einstellen. Verwenden, sobald der Nutzer Produktfotos schickt, einen Preis nennt oder etwas bei eBay inserieren, ändern oder hochladen will.
---

# eBay-Inserate erstellen

Der Nutzer schickt Produktfotos und einen Preis. Du erkennst das Produkt, schreibst das Inserat und
stellst es über die Pipeline in `ebay-agent/` ein. Die Pipeline läuft als GitHub Action
(`.github/workflows/ebay-lister.yml`) und startet bei jedem Push in `ebay-agent/queue/`.
Die eBay-Schlüssel liegen als GitHub Secrets (`APP_ID_EBAY_API`, `DEV_ID_EBAY_API`, `CERT_ID_EBAY_API`,
`TOKEN_EBAY_API`, Token gültig bis Mai 2028). Niemals nach Schlüsseln im Chat fragen.

Antworte auf Deutsch, kurz und ohne Fachjargon.

## Feste Regeln des Verkäufers

- Konto `dala_9976`, eBay.de, **Privatverkäufer**. Kein Kleinunternehmer-Satz, **keine Rücknahme** im Inserat.
- **Sealed** (Displays, Booster, ETB, Boxen …): DHL Paket 6,19 €, weltweit 20 €. Zustand Neu (1000).
- **Einzelkarten**: Einschreiben 4,00 €, weltweit 20 €. Zustand „Near Mint oder besser“, außer der Nutzer sagt etwas anderes.
- Versand weltweit, nicht nur EU. Preisvorschlag immer an.
- Mehrere Stück: Jeder weitere Artikel kostet die vollen Versandkosten (so gewollt). Käufer sollen sich für Kombiversand melden, das steht im Fußtext.
- Das alles steht in `ebay-agent/config.json`. Ändert der Nutzer eine Regel dauerhaft, dort anpassen.
- Gratis-Inserate: Stand 26.11.2026 waren es 303 bis 1.12.2026. Live-Inserate stehen in `ebay-agent/inserate.csv`.
  Nach jedem Stapel sagen, wie viele noch übrig sind (Startwert minus neue Zeilen seit 26.11.).

## Ablauf

1. **Produkt erkennen** aus den Fotos: Spiel, Produkt bzw. Kartenname, Set, **Sprache** (z. B. 宝可梦 = vereinfachtes Chinesisch,
   寶可夢 = traditionelles Chinesisch, japanische Schrift = Japanisch), Sealed oder Einzelkarte.
   Bei Unsicherheit kurz nachfragen statt raten. Nichts erfinden (keine Packungsinhalte, die nicht auf der Box stehen).
2. **Fotos**: Nur echte Fotos des Nutzers verwenden. Stockfotos oder Screenshots nicht verwenden, wenn sie
   eine andere Version zeigen könnten, und das dem Nutzer sagen. Jedes Foto mit Pillow aufbereiten:
   `ImageOps.exif_transpose`, falls nötig drehen, bis die Schrift aufrecht steht (einmal per Vorschau prüfen),
   auf max. 1600 px verkleinern, als JPEG **ohne EXIF** speichern (entfernt Standortdaten).
   Hochgeladene Bilder liegen unter `/root/.claude/uploads/...`.
3. **Inserat schreiben**:
   - Titel max. 80 Zeichen, Suchbegriffe zuerst: Spiel, Produkt/Karte, Set, Sprache, am Ende „Neu OVP“ (Sealed) bzw. Zustand (Karte).
   - `specifics`: Spiel, Edition (Set), Hersteller, Sprache, Produktart, Herstellungsjahr; bei Karten zusätzlich Kartenname, Kartennummer, Seltenheit.
   - `intro` ein Satz, `bullets` 2–4 kurze Fakten.
   - SKU aus Spiel-Kürzel und Produkt, z. B. `PKM-30TH-DISPLAY-CN`.
4. **Probelauf**: Ordner `ebay-agent/queue/<NNNN-kurzname>/` mit den Fotos (`1.jpg`, `2.jpg` …) und
   Datei `ebay-agent/queue/<NNNN-kurzname>.json` mit `"mode": "verify"` anlegen (Format siehe Kopf von `ebay-agent/lister.py`).
   `NNNN` = höchste bisherige Nummer in `queue/`, `done/` und `results/` plus 1. Mehrere Produkte dürfen in eine Datei.
   Commit, `git pull --no-rebase` und Push auf den eigenen Branch.
5. **Ergebnis abwarten**: In einer Hintergrund-Schleife `git fetch` ausführen, bis `ebay-agent/results/<NNNN-kurzname>.json` da ist.
   Die Action verschiebt den Stapel nach `ebay-agent/done/`. `Warning` = in Ordnung, `Failure` = Fehler lesen und beheben.
   Gebühren aus dem Probelauf berücksichtigen die Gratis-Aktion **nicht**, also nicht als echte Kosten melden.
6. **Direkt live stellen**: Der Nutzer hat am 27.11.2026 festgelegt, dass Inserate nach einem erfolgreichen
   Probelauf (`Success` oder `Warning`) **ohne weitere Rückfrage** live gehen. Nur nachfragen, wenn etwas unklar ist
   (Produkt, Sprache, Zustand, Echtheit, Preis fehlt) oder der Probelauf fehlschlägt.
   Fotos, die nach Fälschung oder KI-Bild aussehen (Kauderwelsch-Text, falsches Copyright, falsches Logo), nie einstellen, sondern nachfragen.
   Wünscht der Nutzer einen weißen Hintergrund: Karte anhand ihrer vier Ecken perspektivisch geraderücken (OpenCV),
   mit abgerundeten Ecken auf Weiß setzen, die Karte selbst nicht verändern. **Nur das weiße Bild** verwenden, kein Originalfoto dazu (Nutzerwunsch 27.11.2026).
7. **Live-Stapel**: Neue Datei `queue/<NNNN+1-kurzname>-live.json`, gleicher Inhalt, `"mode": "live"`.
   Die Bildpfade zeigen auf `ebay-agent/done/<Probelauf-Ordner>/…`. Ergebnis abwarten und dem Nutzer
   die Links `https://www.ebay.de/itm/<ItemID>` schicken, dazu die Zahl der restlichen Gratis-Inserate.

## Technische Hinweise

- Fotos gehen als öffentlicher GitHub-Link an eBay (das Repo ist öffentlich). eBays Media API verweigert dem Token den Zugriff, das ist normal.
- Bestehendes Inserat ändern (Fotos, Preis, Menge, Titel): Batch `{ "mode": "revise", "revisions": [{"item_id": "…", "price": 12}] }`. Item-IDs stehen in `ebay-agent/inserate.csv`.
- Zugang testen: Batch `{ "mode": "check" }`. Versandarten nachschlagen: `{ "mode": "shipping" }`.
- Die Action pusht Ergebnisse mit `[skip ci]` zurück. Vor jedem eigenen Push `git pull --no-rebase`.
- `ebay-agent/queue/.gitkeep` muss bleiben, sonst verschwindet der Ordner.
