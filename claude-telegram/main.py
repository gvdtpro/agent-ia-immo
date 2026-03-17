import subprocess
import os
import asyncio
import logging
from fastapi import FastAPI, Request
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN_AGENTIAGAEL"]

# Écrire les credentials Claude.ai au démarrage
creds = os.environ.get("CLAUDE_CREDENTIALS", "")
if creds:
    os.makedirs("/root/.claude", exist_ok=True)
    with open("/root/.claude/.credentials.json", "w") as f:
        f.write(creds)
    logger.info("Claude credentials written OK (%d bytes)", len(creds))
else:
    logger.warning("CLAUDE_CREDENTIALS env var is empty!")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Historique par chat_id (en mémoire, reset au redémarrage)
conversations: dict[int, list[dict]] = {}


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        # Telegram limite à 4096 chars par message
        for i in range(0, len(text), 4096):
            await client.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": text[i:i+4096],
                "parse_mode": "Markdown"
            })


def run_claude(prompt: str, chat_id: int) -> str:
    # Construire l'historique comme contexte
    history = conversations.get(chat_id, [])
    context = ""
    for msg in history[-10:]:  # 10 derniers messages max
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        context += f"{role}: {msg['content']}\n"

    full_prompt = f"{context}Utilisateur: {prompt}\nAssistant:" if context else prompt

    result = subprocess.run(
        ["claude", "-p", full_prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ}
    )
    logger.info("claude returncode=%d stdout=%r stderr=%r", result.returncode, result.stdout[:200], result.stderr[:200])
    return result.stdout.strip() or result.stderr.strip() or "Pas de réponse."


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not text or not chat_id:
        return {"ok": True}

    # Commande /reset
    if text == "/reset":
        conversations.pop(chat_id, None)
        await send_message(chat_id, "Conversation réinitialisée.")
        return {"ok": True}

    # Appel Claude Code
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_claude, text, chat_id)

    # Sauvegarder dans l'historique
    if chat_id not in conversations:
        conversations[chat_id] = []
    conversations[chat_id].append({"role": "user", "content": text})
    conversations[chat_id].append({"role": "assistant", "content": response})

    await send_message(chat_id, response)
    return {"ok": True}


@app.get("/setup")
async def setup():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TELEGRAM_API}/setWebhook",
            params={"url": f"https://{domain}/webhook"}
        )
        return r.json()


@app.get("/")
async def root():
    return {"status": "Claude Code Telegram Bot running"}
