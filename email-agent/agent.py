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
