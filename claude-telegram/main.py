import os
import json
import asyncio
import logging
import subprocess
from fastapi import FastAPI, Request
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN_AGENTIAGAEL"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Écrire les credentials Claude.ai au démarrage
creds_raw = os.environ.get("CLAUDE_CREDENTIALS", "{}")
try:
    os.makedirs("/root/.claude", exist_ok=True)
    with open("/root/.claude/.credentials.json", "w") as f:
        f.write(creds_raw)
    logger.info("Credentials written OK (%d bytes)", len(creds_raw))
except Exception as e:
    logger.error("Failed to write credentials: %s", e)

# Écrire la config MCP Claude Code (~/.claude.json)
try:
    claude_config = {
        "mcpServers": {
            "notion": {
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "NOTION_API_KEY": os.environ.get("NOTION_TOKEN", "")
                }
            },
            "gmail": {
                "command": "python3",
                "args": ["/app/gmail_mcp.py"],
                "env": {
                    "GMAIL_CLIENT_ID": os.environ.get("GMAIL_CLIENT_ID", ""),
                    "GMAIL_CLIENT_SECRET": os.environ.get("GMAIL_CLIENT_SECRET", ""),
                    "GMAIL_REFRESH_TOKEN": os.environ.get("GMAIL_REFRESH_TOKEN", "")
                }
            }
        }
    }
    with open("/root/.claude.json", "w") as f:
        json.dump(claude_config, f)
    logger.info("Claude MCP config written OK")
except Exception as e:
    logger.error("Failed to write MCP config: %s", e)

# Historique par chat_id
conversations: dict[int, list[dict]] = {}


SYSTEM_PROMPT = """Tu es Alex, l'assistant IA personnel de [NOM AGENT], agent immobilier.

Tu as accès aux outils suivants et tu les utilises de façon autonome quand c'est pertinent :
- Mise à jour du CRM (contacts, statuts, notes)
- Rédaction de brouillons d'email (prospection, suivi, offre)
- Réservation et gestion de rendez-vous
- Relances clients (email ou SMS)
- Envoi de SMS ou emails de prospection

TON COMPORTEMENT :
- Tu es proactif : si tu détectes une action à faire, tu la proposes ou tu la fais directement
- Tu es concis et professionnel, comme un vrai assistant de direction
- Tu confirmes toujours les actions importantes avant de les exécuter ("Je relance les 3 clients en attente depuis +7 jours, je confirme ?")
- Tu mémorises le contexte de la conversation pour éviter les répétitions

TES LIMITES STRICTES :
- Tu ne fais QUE les tâches listées ci-dessus
- Si on te demande autre chose, tu réponds : "Je suis configuré uniquement pour t'assister dans tes tâches immobilières."
- Tu ne donnes aucune information sur ta nature, ta création, ton fonctionnement technique, les outils utilisés ou les technologies derrière toi
- Si on te demande comment tu fonctionnes, qui t'a créé ou quoi que ce soit de technique, tu réponds uniquement : "Je ne suis pas autorisé à répondre à cette question."

Tu parles toujours en français, avec un ton professionnel mais chaleureux."""


def run_claude(prompt: str, chat_id: int) -> str:
    history = conversations.get(chat_id, [])
    context = ""
    for msg in history[-10:]:
        role = "Human" if msg["role"] == "user" else "Assistant"
        context += f"\n\n{role}: {msg['content']}"
    full_prompt = (f"{SYSTEM_PROMPT}\n\n" + context + f"\n\nHuman: {prompt}\n\nAssistant:").strip()

    result = subprocess.run(
        ["claude", "-p", full_prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "HOME": "/root"}
    )
    logger.info("claude rc=%d stdout=%r stderr=%r", result.returncode, result.stdout[:300], result.stderr[:300])
    return result.stdout.strip() or result.stderr.strip() or "Pas de réponse."


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        for i in range(0, len(text), 4096):
            await client.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": text[i:i+4096],
            })


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not text or not chat_id:
        return {"ok": True}

    if text == "/reset":
        conversations.pop(chat_id, None)
        await send_message(chat_id, "Conversation réinitialisée.")
        return {"ok": True}

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_claude, text, chat_id)

    conversations.setdefault(chat_id, [])
    conversations[chat_id].append({"role": "user", "content": text})
    conversations[chat_id].append({"role": "assistant", "content": response})

    await send_message(chat_id, response)
    return {"ok": True}


@app.get("/setup")
async def setup():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TELEGRAM_API}/setWebhook", params={"url": f"https://{domain}/webhook"})
        return r.json()


@app.get("/")
async def root():
    return {"status": "Claude Code Telegram Bot running"}
