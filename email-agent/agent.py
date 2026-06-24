import os
import re
import requests
import anthropic
from datetime import datetime, timezone

TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DRAFT_MODE = os.environ.get("DRAFT_MODE", "true").lower() == "true"
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "levora-skin.myshopify.com")

GRAPH_URL = "https://graph.microsoft.com/v1.0"

# ── Widerruf-Templates ────────────────────────────────────────────────────────

WIDERRUF_TEMPLATE_1 = """Hallo {vorname},

dein Widerruf ist bei uns eingegangen – du erhältst in Kürze eine separate Bestätigung.

Ich bin Yvonne vom Levora-Kundenservice. Ich schreibe dir, weil dein Paket laut unserer Versandinfo noch gar nicht bei dir angekommen sein kann – es ist noch auf dem Weg zu dir.

Das bedeutet: Du hast das Gerät noch nicht in der Hand gehabt. Und trotzdem hast du dich entschieden, es zurückzuschicken.

Das passiert – ich mache dir da keine Vorwürfe. Aber ich wäre wirklich neugierig:

❓ Was hat dich zum Widerruf bewogen?
   ☐ Ich bin unsicher, ob das Gerät wirklich hilft
   ☐ Ich habe den Preis nochmal überdacht
   ☐ Ich habe anderswo eine Alternative gefunden
   ☐ Es war ein Versehen beim Bestellen
   ☐ Mir fehlte vor dem Kauf eine wichtige Information
   ☐ Die Lieferzeit war mir zu lang
   ☐ Sonstiges: ________________________

❓ Gab es eine Frage, die du vor dem Kauf hattest und die unbeantwortet blieb?
   ________________________________________________

Wenn du magst, beantworte ich dir diese Frage jetzt noch – ganz ohne Druck. Manchmal ist es einfach das eine Argument, das gefehlt hat.

Antworte einfach auf diese E-Mail. Ich melde mich persönlich.

Herzliche Grüße,
Yvonne
Kundensupport | Levora Skin"""

WIDERRUF_TEMPLATE_2 = """Hallo {vorname},

wir haben deinen Widerruf erhalten und bearbeiten ihn – eine Bestätigung geht dir separat zu.

Dein Paket müsste in den letzten Tagen bei dir angekommen sein. Und direkt danach kam der Widerruf – das sagt mir, dass beim Auspacken oder beim ersten Eindruck irgendetwas nicht gestimmt hat.

Ich würde das gerne verstehen:

❓ Wie weit bist du mit dem Gerät gekommen?
   ☐ Ich habe es ausgepackt, aber noch nicht benutzt
   ☐ Ich habe es einmal ausprobiert
   ☐ Ich habe es 2–3 Mal benutzt

❓ Was hat dich am meisten gestört?
   ☐ Das Gerät sah anders aus als erwartet
   ☐ Die Handhabung war unklar
   ☐ Die Anleitung hat nicht gereicht
   ☐ Es hat sich nicht so angefühlt wie erhofft
   ☐ Ich hatte ein technisches Problem
   ☐ Sonstiges: ________________________

❓ Wusstest du, dass sichtbare Veränderungen am Nagel erst nach 6–8 Wochen regelmäßiger Anwendung eintreten?
   ☐ Ja, das war mir klar
   ☐ Nein – das wusste ich nicht

Falls du magst, erkläre ich dir kurz, was in den ersten Wochen im Nagel passiert – vielleicht hilft das, die Entscheidung nochmal zu überdenken. Keine Verpflichtung.

Herzliche Grüße,
Yvonne
Kundensupport | Levora Skin"""

WIDERRUF_TEMPLATE_3 = """Hallo {vorname},

dein Widerruf ist angekommen – wir kümmern uns darum, eine Bestätigung folgt in Kürze.

Du hast das Gerät jetzt schon eine Weile bei dir. Das bedeutet, du hattest Zeit, es auszuprobieren – und trotzdem bist du zum Schluss gekommen, es zurückzuschicken.

Das nehme ich ernst. Ich möchte verstehen, was passiert ist:

❓ Wie regelmäßig hast du das Gerät benutzt?
   ☐ Täglich oder fast täglich
   ☐ Ein paar Mal pro Woche
   ☐ Nur gelegentlich
   ☐ Kaum – ich bin nicht richtig in die Routine gekommen

❓ Was war der ausschlaggebende Grund für den Widerruf?
   ☐ Ich habe noch keine sichtbare Veränderung am Nagel bemerkt
   ☐ Die Anwendung war mir auf Dauer zu aufwendig
   ☐ Ich hatte ein technisches Problem mit dem Gerät
   ☐ Ich habe eine andere Lösung gefunden
   ☐ Sonstiges: ________________________

Ich frage, weil Nagelpilz tief im Nagelbett sitzt – sichtbare Ergebnisse brauchen bei den meisten Menschen 8–12 Wochen konsequenter Anwendung. Das ist keine Ausrede, sondern einfach Biologie.

Falls du das Gefühl hattest, dass nichts passiert: Vielleicht war die Anwendungsfrequenz noch nicht ganz optimal. Das kann ich dir in zwei Sätzen erklären – wenn du magst.

Antworte einfach kurz auf diese Mail. Ich schaue mir deinen Fall persönlich an.

Herzliche Grüße,
Yvonne
Kundensupport | Levora Skin"""

# ── Shopify ───────────────────────────────────────────────────────────────────

def _shopify_get(params):
    if not SHOPIFY_TOKEN:
        return None
    url = f"https://{SHOPIFY_SHOP}/admin/api/2024-04/orders.json"
    fields = "id,created_at,fulfillment_status,fulfillments,customer"
    try:
        r = requests.get(
            url,
            headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN},
            params={**params, "status": "any", "limit": 1, "fields": fields},
            timeout=10,
        )
        r.raise_for_status()
        orders = r.json().get("orders", [])
        return orders[0] if orders else None
    except Exception as e:
        print(f"  Shopify-Fehler: {e}")
        return None


def get_shopify_order_by_number(order_number):
    num = order_number.strip().lstrip("#")
    order = _shopify_get({"name": f"#{num}"})
    if order:
        print(f"  Order #{num} via Bestellnummer gefunden")
    return order


def get_shopify_order_by_email(customer_email):
    order = _shopify_get({"email": customer_email})
    if order:
        print(f"  Order via Kunden-Email gefunden")
    return order


def find_shopify_order(sender_email, body_text):
    """Try order number from body first, then fall back to sender email."""
    match = re.search(r"#\s*(\d{3,6})", body_text)
    if match:
        order = get_shopify_order_by_number(match.group(1))
        if order:
            return order
    return get_shopify_order_by_email(sender_email)


def get_customer_first_name(order, fallback_name):
    """First name from Shopify customer data — never from sender display name."""
    if order:
        customer = order.get("customer") or {}
        first_name = customer.get("first_name", "").strip()
        if first_name:
            return first_name
    # Last resort: parse the email body for a name (not sender display name)
    return fallback_name or "du"


def get_widerruf_context(order):
    """Return (days_since_order, template) based on order data."""
    if not order:
        return None, None

    created_at = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - created_at).days

    fulfillment_status = order.get("fulfillment_status") or "unfulfilled"
    # Check if any fulfillment was actually shipped
    shipped = fulfillment_status in ("fulfilled", "partial")

    if not shipped or days < 2:
        return days, WIDERRUF_TEMPLATE_1
    elif days < 20:
        return days, WIDERRUF_TEMPLATE_2
    else:
        return days, WIDERRUF_TEMPLATE_3


# ── Email detection ───────────────────────────────────────────────────────────

WIDERRUF_KEYWORDS = [
    "widerruf", "widerrufen", "widerrufs", "stornieren", "stornierung",
    "zurückschicken", "rückgabe", "rücksendung", "zurückgeben",
    "cancellation", "cancel", "return", "retour",
]

def is_widerruf(subject, body_text):
    text = (subject + " " + body_text).lower()
    return any(kw in text for kw in WIDERRUF_KEYWORDS)


def extract_first_name(sender_name):
    """Try to extract first name from sender display name."""
    if not sender_name:
        return "du"
    parts = sender_name.strip().split()
    return parts[0] if parts else sender_name


# ── Microsoft Graph ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist Yvonne vom Kundensupport bei Levora Skin – einer deutschen Hautpflegemarke.
Du schreibst immer persönlich, warmherzig und lösungsorientiert. Duze die Kunden.
Schreibe kurze, klare E-Mails. Kein "Sehr geehrte/r" – stattdessen "Hallo [Name]," wenn der Name bekannt ist.
Unterschreibe immer mit:
  Herzliche Grüße,
  Yvonne
  Kundensupport | Levora Skin

---

WICHTIGE REGELN:

1. PAKET-ANFRAGEN (erste Nachricht – Kunde fragt wo sein Paket ist):
Antworte: Vielen Dank für deine Nachricht! Ich habe gerade in unserem System nachgeschaut und laut DHL sollte dein Paket eigentlich schon unterwegs sein. Das klingt für mich etwas ungewöhnlich – ich werde morgen umgehend mit DHL telefonieren und die Sache in Erfahrung bringen. Ich melde mich dann sofort bei dir!
Füge hinzu: Falls dein Paket in den nächsten 4–5 Tagen nicht ankommen sollte, melde dich bitte kurz bei mir – dann schicke ich dir umgehend kostenlos ein neues Paket zu. Und sollte das ursprüngliche Paket doch noch ankommen, kannst du einfach beide behalten. 😊

2. PAKET-ANFRAGEN (Folgenachricht – Paket ist nach 4-5 Tagen immer noch nicht da):
Erkenne diese Situation daran, dass der Kunde schreibt sein Paket sei immer noch nicht angekommen / er meldet sich nochmal wegen seinem Paket.
Antworte: Das tut mir wirklich sehr leid zu hören! Ich werde dir umgehend ein neues Paket fertig machen – es wird noch heute unser Versandlager verlassen. Du erhältst die Tracking-Informationen sobald es versendet wurde.

3. WIDERRUF / STORNIERUNG:
Wird separat mit einem vorgefertigten Template behandelt – du musst hier NICHTS generieren.
Gib stattdessen exakt zurück: "WIDERRUF"

4. ESKALATION – NICHT ANTWORTEN:
Bei folgenden Themen KEINE Antwort generieren – gib stattdessen exakt diesen Text zurück: "ESCALATE"
- Drohungen mit PayPal-Käuferschutz, Chargeback oder rechtlichen Schritten
- Sehr aggressive oder beleidigende Nachrichten
- Komplexe rechtliche Fragen

5. ALLE ANDEREN ANFRAGEN:
Antworte freundlich und hilfsbereit im Stil von Yvonne. Falls du etwas nicht weißt, schreibe dass du dich darum kümmerst und dich schnellstmöglich meldest.
"""


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def get_unread_emails(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/mailFolders/inbox/messages"
    params = {
        "$filter": "isRead eq false",
        "$select": "id,subject,from,body,receivedDateTime,conversationId",
        "$top": 10,
        "$orderby": "receivedDateTime asc",
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get("value", [])


def get_conversation_history(token, conversation_id, current_email_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages"
    params = {
        "$filter": f"conversationId eq '{conversation_id}'",
        "$select": "id,subject,from,body,receivedDateTime,sender",
        "$orderby": "receivedDateTime asc",
        "$top": 10,
    }
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return []
    messages = r.json().get("value", [])
    return [m for m in messages if m["id"] != current_email_id]


def generate_reply(email, history):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    sender = email["from"]["emailAddress"].get("name", "")
    subject = email.get("subject", "")
    body = email.get("body", {}).get("content", "")
    body_text = re.sub(r"<[^>]+>", " ", body).strip()
    body_text = re.sub(r"\s+", " ", body_text)[:2000]

    context = ""
    if history:
        context = "\n\nVorherige E-Mails in diesem Thread (älteste zuerst):\n"
        for h in history[-3:]:
            h_sender = h["from"]["emailAddress"].get("address", "")
            h_body = re.sub(r"<[^>]+>", " ", h.get("body", {}).get("content", "")).strip()
            h_body = re.sub(r"\s+", " ", h_body)[:500]
            context += f"Von: {h_sender}\n{h_body}\n---\n"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Bitte antworte auf diese Kundenanfrage:{context}\n\nNeue E-Mail von: {sender}\nBetreff: {subject}\n\nNachricht:\n{body_text}",
            }
        ],
    )
    return message.content[0].text


def save_draft(token, to_address, to_name, subject, reply_text):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    payload = {
        "subject": subject,
        "body": {"contentType": "Text", "content": reply_text},
        "toRecipients": [{"emailAddress": {"address": to_address, "name": to_name}}],
    }
    r = requests.post(f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages", headers=headers, json=payload)
    r.raise_for_status()


def send_reply(token, to_address, to_name, subject, reply_text):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": reply_text},
            "toRecipients": [{"emailAddress": {"address": to_address, "name": to_name}}],
        },
        "saveToSentItems": True,
    }
    r = requests.post(f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/sendMail", headers=headers, json=payload)
    r.raise_for_status()


def mark_as_read(token, email_id):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.patch(f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages/{email_id}", headers=headers, json={"isRead": True})
    r.raise_for_status()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Email Agent gestartet. Draft-Modus: {DRAFT_MODE}")
    token = get_access_token()
    emails = get_unread_emails(token)
    print(f"{len(emails)} ungelesene E-Mail(s) gefunden.")

    for email in emails:
        email_id = email["id"]
        subject = email.get("subject", "(kein Betreff)")
        sender = email["from"]["emailAddress"]
        sender_email = sender["address"]
        sender_name = sender.get("name", "")
        conversation_id = email.get("conversationId", "")
        body = email.get("body", {}).get("content", "")
        body_text = re.sub(r"<[^>]+>", " ", body).strip()
        body_text = re.sub(r"\s+", " ", body_text)[:2000]

        print(f"Verarbeite: '{subject}' von {sender_email}")

        try:
            # ── Widerruf-Erkennung ──────────────────────────────────────────
            if is_widerruf(subject, body_text):
                print(f"  → Widerruf erkannt – Shopify-Lookup...")
                order = find_shopify_order(sender_email, body_text)
                days, template = get_widerruf_context(order)

                if template:
                    vorname = get_customer_first_name(order, None)
                    reply = template.format(vorname=vorname)
                    stage = "noch unterwegs" if template == WIDERRUF_TEMPLATE_1 else ("frisch erhalten" if template == WIDERRUF_TEMPLATE_2 else "längere Nutzung")
                    print(f"  → Template: {stage} | {days} Tage | Vorname: {vorname}")
                else:
                    vorname = get_customer_first_name(order, None)
                    reply = WIDERRUF_TEMPLATE_1.format(vorname=vorname)
                    print(f"  → Kein Order gefunden, Template 1 als Fallback")

                if DRAFT_MODE:
                    save_draft(token, sender_email, sender_name, subject, reply)
                    print(f"  ✓ Widerruf-Entwurf gespeichert")
                else:
                    send_reply(token, sender_email, sender_name, subject, reply)
                    mark_as_read(token, email_id)
                    print(f"  ✓ Widerruf-Antwort gesendet")
                continue

            # ── Normaler Claude-Flow ────────────────────────────────────────
            history = get_conversation_history(token, conversation_id, email_id) if conversation_id else []
            reply = generate_reply(email, history)

            if reply.strip() == "ESCALATE":
                print(f"  ⚠ Eskalation – wird übersprungen")
                mark_as_read(token, email_id)
                continue

            if reply.strip() == "WIDERRUF":
                order = find_shopify_order(sender_email, body_text)
                days, template = get_widerruf_context(order)
                vorname = get_customer_first_name(order, None)
                reply = (template or WIDERRUF_TEMPLATE_1).format(vorname=vorname)

            if DRAFT_MODE:
                save_draft(token, sender_email, sender_name, subject, reply)
                print(f"  ✓ Entwurf gespeichert")
            else:
                send_reply(token, sender_email, sender_name, subject, reply)
                mark_as_read(token, email_id)
                print(f"  ✓ Antwort gesendet")

        except Exception as e:
            print(f"  ✗ Fehler: {e}")

    print("Fertig.")


if __name__ == "__main__":
    main()


TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DRAFT_MODE = os.environ.get("DRAFT_MODE", "true").lower() == "true"

GRAPH_URL = "https://graph.microsoft.com/v1.0"

SYSTEM_PROMPT = """Du bist Yvonne vom Kundensupport bei Levora Skin – einer deutschen Hautpflegemarke.
Du schreibst immer persönlich, warmherzig und lösungsorientiert. Duze die Kunden.
Schreibe kurze, klare E-Mails. Kein "Sehr geehrte/r" – stattdessen "Hallo [Name]," wenn der Name bekannt ist.
Unterschreibe immer mit:
  Liebe Grüße,
  Yvonne
  Levora Skin Kundensupport

---

WICHTIGE REGELN:

1. PAKET-ANFRAGEN (erste Nachricht – Kunde fragt wo sein Paket ist):
Antworte: Vielen Dank für deine Nachricht! Ich habe gerade in unserem System nachgeschaut und laut DHL sollte dein Paket eigentlich schon unterwegs sein. Das klingt für mich etwas ungewöhnlich – ich werde morgen umgehend mit DHL telefonieren und die Sache in Erfahrung bringen. Ich melde mich dann sofort bei dir!
Füge hinzu: Falls dein Paket in den nächsten 4–5 Tagen nicht ankommen sollte, melde dich bitte kurz bei mir – dann schicke ich dir umgehend kostenlos ein neues Paket zu. Und sollte das ursprüngliche Paket doch noch ankommen, kannst du einfach beide behalten. 😊

2. PAKET-ANFRAGEN (Folgenachricht – Paket ist nach 4-5 Tagen immer noch nicht da):
Erkenne diese Situation daran, dass der Kunde schreibt sein Paket sei immer noch nicht angekommen / er meldet sich nochmal wegen seinem Paket.
Antworte: Das tut mir wirklich sehr leid zu hören! Ich werde dir umgehend ein neues Paket fertig machen – es wird noch heute unser Versandlager verlassen. Du erhältst die Tracking-Informationen sobald es versendet wurde.

3. STORNIERUNGSANFRAGEN:
Frage zuerst freundlich nach dem Grund. Erkläre gleichzeitig, dass du kurz im System prüfen musst, ob das Paket das Versandlager bereits verlassen hat, um weitere Details klären zu können.

4. ESKALATION – NICHT ANTWORTEN:
Bei folgenden Themen KEINE Antwort generieren – gib stattdessen exakt diesen Text zurück: "ESCALATE"
- Drohungen mit PayPal-Käuferschutz, Chargeback oder rechtlichen Schritten
- Sehr aggressive oder beleidigende Nachrichten
- Komplexe rechtliche Fragen

5. ALLE ANDEREN ANFRAGEN:
Antworte freundlich und hilfsbereit im Stil von Yvonne. Falls du etwas nicht weißt, schreibe dass du dich darum kümmerst und dich schnellstmöglich meldest.
"""


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def get_unread_emails(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/mailFolders/inbox/messages"
    params = {
        "$filter": "isRead eq false",
        "$select": "id,subject,from,body,receivedDateTime,conversationId",
        "$top": 10,
        "$orderby": "receivedDateTime asc",
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get("value", [])


def get_conversation_history(token, conversation_id, current_email_id):
    """Fetch previous emails in the same conversation to detect follow-ups."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages"
    params = {
        "$filter": f"conversationId eq '{conversation_id}'",
        "$select": "id,subject,from,body,receivedDateTime,sender",
        "$orderby": "receivedDateTime asc",
        "$top": 10,
    }
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return []
    messages = r.json().get("value", [])
    return [m for m in messages if m["id"] != current_email_id]


def generate_reply(email, history):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    sender = email["from"]["emailAddress"].get("name", "")
    subject = email.get("subject", "")
    body = email.get("body", {}).get("content", "")
    body_text = re.sub(r"<[^>]+>", " ", body).strip()
    body_text = re.sub(r"\s+", " ", body_text)[:2000]

    context = ""
    if history:
        context = "\n\nVorherige E-Mails in diesem Thread (älteste zuerst):\n"
        for h in history[-3:]:
            h_sender = h["from"]["emailAddress"].get("address", "")
            h_body = re.sub(r"<[^>]+>", " ", h.get("body", {}).get("content", "")).strip()
            h_body = re.sub(r"\s+", " ", h_body)[:500]
            context += f"Von: {h_sender}\n{h_body}\n---\n"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Bitte antworte auf diese Kundenanfrage:{context}\n\nNeue E-Mail von: {sender}\nBetreff: {subject}\n\nNachricht:\n{body_text}",
            }
        ],
    )
    return message.content[0].text


def save_draft(token, to_address, to_name, subject, reply_text):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    payload = {
        "subject": subject,
        "body": {"contentType": "Text", "content": reply_text},
        "toRecipients": [{"emailAddress": {"address": to_address, "name": to_name}}],
    }
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages"
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()


def send_reply(token, to_address, to_name, subject, reply_text):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": reply_text},
            "toRecipients": [{"emailAddress": {"address": to_address, "name": to_name}}],
        },
        "saveToSentItems": True,
    }
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/sendMail"
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()


def mark_as_read(token, email_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages/{email_id}"
    r = requests.patch(url, headers=headers, json={"isRead": True})
    r.raise_for_status()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Email Agent gestartet. Draft-Modus: {DRAFT_MODE}")
    token = get_access_token()
    emails = get_unread_emails(token)
    print(f"{len(emails)} ungelesene E-Mail(s) gefunden.")

    for email in emails:
        email_id = email["id"]
        subject = email.get("subject", "(kein Betreff)")
        sender = email["from"]["emailAddress"]
        conversation_id = email.get("conversationId", "")
        print(f"Verarbeite: '{subject}' von {sender['address']}")

        try:
            history = get_conversation_history(token, conversation_id, email_id) if conversation_id else []
            reply = generate_reply(email, history)

            if reply.strip() == "ESCALATE":
                print(f"  ⚠ Eskalation – wird übersprungen (muss manuell bearbeitet werden)")
                mark_as_read(token, email_id)
                continue

            if DRAFT_MODE:
                save_draft(token, sender["address"], sender.get("name", ""), subject, reply)
                print(f"  ✓ Entwurf gespeichert")
            else:
                send_reply(token, sender["address"], sender.get("name", ""), subject, reply)
                mark_as_read(token, email_id)
                print(f"  ✓ Antwort gesendet")

        except Exception as e:
            print(f"  ✗ Fehler: {e}")

    print("Fertig.")


if __name__ == "__main__":
    main()
