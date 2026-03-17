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
    # Vérifier que le fichier est lisible par claude
    parsed = json.loads(creds_raw)
    logger.info("Token type: %s", list(parsed.keys()))
except Exception as e:
    logger.error("Failed to write credentials: %s", e)

# Historique par chat_id
conversations: dict[int, list[dict]] = {}


def run_claude(prompt: str, chat_id: int) -> str:
    history = conversations.get(chat_id, [])
    context = ""
    for msg in history[-10:]:
        role = "Human" if msg["role"] == "user" else "Assistant"
        context += f"\n\n{role}: {msg['content']}"
    full_prompt = (context + f"\n\nHuman: {prompt}\n\nAssistant:").strip() if context else prompt

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
