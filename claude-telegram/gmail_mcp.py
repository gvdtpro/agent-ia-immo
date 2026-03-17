"""Gmail MCP Server — opérations email via Google API"""
import os
import json
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gmail")

def get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.modify"]
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def list_emails(max_results: int = 10, query: str = "") -> str:
    """Liste les derniers emails de la boîte de réception."""
    service = get_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, q=query or "in:inbox"
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return "Aucun email trouvé."
    output = []
    for msg in messages:
        m = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        output.append(f"[{headers.get('Date','')}] De: {headers.get('From','')} — {headers.get('Subject','(sans objet)')}")
    return "\n".join(output)


@mcp.tool()
def read_email(message_id: str) -> str:
    """Lit le contenu complet d'un email par son ID."""
    service = get_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = ""
    if "parts" in msg["payload"]:
        for part in msg["payload"]["parts"]:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
    elif "body" in msg["payload"] and msg["payload"]["body"].get("data"):
        body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")
    return f"De: {headers.get('From')}\nÀ: {headers.get('To')}\nDate: {headers.get('Date')}\nSujet: {headers.get('Subject')}\n\n{body}"


@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> str:
    """Crée un brouillon d'email."""
    service = get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return f"Brouillon créé (ID: {draft['id']}) pour {to} — Sujet: {subject}"


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Envoie un email directement."""
    service = get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email envoyé (ID: {sent['id']}) à {to}"


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> str:
    """Recherche des emails avec une requête Gmail (ex: 'from:client@email.com subject:relance')."""
    return list_emails(max_results=max_results, query=query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
