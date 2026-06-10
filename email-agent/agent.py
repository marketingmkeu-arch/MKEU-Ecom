import os
import json
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

SYSTEM_PROMPT = """Du bist Yvonne, der freundliche E-Mail-Support-Agent von Levora Skin.
Du antwortest auf Kundenanfragen professionell, empathisch und auf Deutsch.
Levora Skin ist eine Hautpflegemarke. Halte Antworten kurz und hilfreich.
Falls du eine Frage nicht beantworten kannst (z.B. spezifische Bestelldetails),
weise den Kunden freundlich darauf hin, dass ein Mitarbeiter sich meldet.
Beginne nie mit "Sehr geehrte/r", sondern mit "Hallo [Name]," wenn der Name bekannt ist."""


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
        "$select": "id,subject,from,body,receivedDateTime",
        "$top": 10,
        "$orderby": "receivedDateTime asc",
    }
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get("value", [])


def generate_reply(email):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    sender = email["from"]["emailAddress"].get("name", "Kunde")
    subject = email.get("subject", "")
    body = email.get("body", {}).get("content", "")

    # Strip HTML tags simply
    import re
    body_text = re.sub(r"<[^>]+>", " ", body).strip()
    body_text = re.sub(r"\s+", " ", body_text)[:2000]

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Bitte antworte auf diese Kundenanfrage:\n\nVon: {sender}\nBetreff: {subject}\n\nNachricht:\n{body_text}",
            }
        ],
    )
    return message.content[0].text


def send_reply(token, email_id, to_address, to_name, subject, reply_text):
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

    if DRAFT_MODE:
        url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/messages"
        r = requests.post(url, headers=headers, json=payload["message"])
    else:
        url = f"{GRAPH_URL}/users/{EMAIL_ADDRESS}/sendMail"
        r = requests.post(url, headers=headers, json=payload)

    r.raise_for_status()
    return r.status_code


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
        print(f"Verarbeite: '{subject}' von {sender['address']}")

        try:
            reply = generate_reply(email)
            send_reply(token, email_id, sender["address"], sender.get("name", ""), subject, reply)
            mark_as_read(token, email_id)
            mode = "Entwurf gespeichert" if DRAFT_MODE else "Antwort gesendet"
            print(f"  ✓ {mode}")
        except Exception as e:
            print(f"  ✗ Fehler: {e}")

    print("Fertig.")


if __name__ == "__main__":
    main()
