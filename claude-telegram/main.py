import os
import json
import asyncio
import logging
from fastapi import FastAPI, Request
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN_AGENTIAGAEL"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Extraire le token OAuth depuis CLAUDE_CREDENTIALS
creds_raw = os.environ.get("CLAUDE_CREDENTIALS", "{}")
creds = json.loads(creds_raw)
OAUTH_TOKEN = creds.get("claudeAiOauth", {}).get("accessToken", "")
if OAUTH_TOKEN:
    logger.info("OAuth token loaded OK")
else:
    logger.warning("OAuth token not found in CLAUDE_CREDENTIALS")

# Historique par chat_id
conversations: dict[int, list[dict]] = {}


async def call_claude(prompt: str, history: list[dict]) -> str:
    messages = history[-20:] + [{"role": "user", "content": prompt}]
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Authorization": f"Bearer {OAUTH_TOKEN}",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 4096,
                "messages": messages,
            }
        )
        data = r.json()
        logger.info("API response status=%d", r.status_code)
        if r.status_code == 200:
            return data["content"][0]["text"]
        else:
            logger.error("API error: %s", data)
            return f"Erreur API: {data.get('error', {}).get('message', str(data))}"


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

    history = conversations.get(chat_id, [])
    response = await call_claude(text, history)

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
