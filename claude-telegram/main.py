import os
import json
import asyncio
import logging
import time
from fastapi import FastAPI, Request
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN_AGENTIAGAEL"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
HOME = "/home/appuser"
MCP_CONFIG_PATH = f"{HOME}/.claude.json"
NOTION_CACHE_TTL = 300  # 5 minutes

# Écrire les credentials Claude.ai au démarrage
creds_raw = os.environ.get("CLAUDE_CREDENTIALS", "{}")
try:
    os.makedirs(f"{HOME}/.claude", exist_ok=True)
    with open(f"{HOME}/.claude/.credentials.json", "w") as f:
        f.write(creds_raw)
    logger.info("Credentials written OK (%d bytes)", len(creds_raw))
except Exception as e:
    logger.error("Failed to write credentials: %s", e)

# Écrire la config MCP Claude Code
try:
    claude_config = {
        "mcpServers": {
            "notion": {
                "command": "notion-mcp-server",
                "args": [],
                "env": {"NOTION_API_KEY": os.environ.get("NOTION_TOKEN", "")}
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
    with open(MCP_CONFIG_PATH, "w") as f:
        json.dump(claude_config, f)
    logger.info("Claude MCP config written OK")
except Exception as e:
    logger.error("Failed to write MCP config: %s", e)

# Historique par chat_id
conversations: dict[int, list[dict]] = {}

# Déduplication : message_ids déjà traités
processed_ids: set[int] = set()

# Cache Notion par chat_id : {chat_id: {"data": str, "ts": float}}
notion_cache: dict[int, dict] = {}

SYSTEM_PROMPT = """Tu es Alex, l'assistant IA personnel de [NOM AGENT], agent immobilier.

Tu as accès aux outils suivants et tu les utilises de façon autonome quand c'est pertinent :
- Mise à jour du CRM (contacts, statuts, notes)
- Rédaction de brouillons d'email (prospection, suivi, offre)
- Réservation et gestion de rendez-vous
- Relances clients (email ou SMS)
- Envoi de SMS ou emails de prospection

SOURCES DE DONNÉES :
- Toutes les informations clients (nom, coordonnées, statut, historique, biens recherchés, rendez-vous, notes) sont dans Notion. Tu dois toujours consulter Notion en priorité avant de répondre à toute question sur un client.
- Les emails (envoyés, reçus, brouillons) sont dans Gmail uniquement.
- Tu ne dois jamais inventer d'informations client. Si tu ne trouves pas dans Notion, tu le dis clairement.

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

NOTION_KEYWORDS = {"client", "contact", "crm", "rendez-vous", "rdv", "agenda", "acheteur",
                   "vendeur", "bien", "propriété", "note", "statut", "cherche", "budget",
                   "relance", "suivi", "historique", "dossier", "prospect"}
GMAIL_KEYWORDS  = {"mail", "email", "message", "envoyer", "envoie", "brouillon",
                   "inbox", "réception", "reçu", "envoyé"}

def needs_notion(text: str) -> bool:
    return bool(set(text.lower().split()) & NOTION_KEYWORDS)

def needs_gmail(text: str) -> bool:
    return bool(set(text.lower().split()) & GMAIL_KEYWORDS)

def needs_tools(text: str) -> bool:
    return needs_notion(text) or needs_gmail(text)

def get_cached_notion(chat_id: int) -> str | None:
    entry = notion_cache.get(chat_id)
    if entry and (time.time() - entry["ts"]) < NOTION_CACHE_TTL:
        age = int(time.time() - entry["ts"])
        logger.info("Notion cache HIT for chat_id=%d (age=%ds)", chat_id, age)
        return entry["data"]
    return None

def set_notion_cache(chat_id: int, data: str):
    notion_cache[chat_id] = {"data": data, "ts": time.time()}


async def run_claude(prompt: str, chat_id: int) -> str:
    history = conversations.get(chat_id, [])
    context = ""
    for msg in history[-6:]:
        role = "Human" if msg["role"] == "user" else "Assistant"
        context += f"\n\n{role}: {msg['content']}"
    full_prompt = (context + f"\n\nHuman: {prompt}\n\nAssistant:").strip() if context else prompt

    use_notion = needs_notion(prompt)
    use_gmail  = needs_gmail(prompt)
    use_mcp    = use_notion or use_gmail

    # Cache Notion : si données fraîches dispo et pas besoin de Gmail, injecter en contexte
    cached = get_cached_notion(chat_id) if use_notion and not use_gmail else None
    if cached:
        system = SYSTEM_PROMPT + f"\n\nDONNÉES NOTION (récupérées il y a moins de 5 min) :\n{cached}"
        use_mcp = use_gmail  # Notion pas besoin via MCP si cache dispo
        logger.info("Notion injected from cache, MCP=%s", use_mcp)
    else:
        system = SYSTEM_PROMPT

    cmd = [
        "claude", "-p", full_prompt,
        "--output-format", "text",
        "--dangerously-skip-permissions",
        "--model", "claude-haiku-4-5-20251001",
        "--system-prompt", system,
    ]
    if use_mcp:
        cmd += ["--mcp-config", MCP_CONFIG_PATH]
        logger.info("MCP enabled (notion=%s gmail=%s)", use_notion and not cached, use_gmail)
    else:
        logger.info("Fast path (no MCP)")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "HOME": HOME}
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        return "Délai d'attente dépassé, réessaie."

    out = stdout.decode().strip()
    err = stderr.decode().strip()
    logger.info("claude rc=%d out=%r", proc.returncode, out[:200])

    # Mettre en cache si Notion était impliqué
    if use_notion and out:
        set_notion_cache(chat_id, out)

    return out or err or "Pas de réponse."


async def edit_message(chat_id: int, message_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4096],
        })
        # Si la réponse dépasse 4096 chars, envoyer le reste en nouveaux messages
        for i in range(4096, len(text), 4096):
            await client.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": text[i:i+4096],
            })


async def send_message(chat_id: int, text: str) -> int | None:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
        })
        return r.json().get("result", {}).get("message_id")


async def process_message(chat_id: int, text: str):
    # Envoyer "⏳" immédiatement — l'utilisateur voit que ça travaille
    thinking_id = await send_message(chat_id, "⏳ Analyse en cours...")

    response = await run_claude(text, chat_id)

    conversations.setdefault(chat_id, [])
    conversations[chat_id].append({"role": "user", "content": text})
    conversations[chat_id].append({"role": "assistant", "content": response})

    # Éditer le message "⏳" avec la vraie réponse
    if thinking_id:
        await edit_message(chat_id, thinking_id, response)
    else:
        await send_message(chat_id, response)


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    message_id = message.get("message_id")

    if not text or not chat_id:
        return {"ok": True}

    if message_id in processed_ids:
        logger.info("Duplicate message_id=%d ignored", message_id)
        return {"ok": True}
    processed_ids.add(message_id)
    if len(processed_ids) > 1000:
        processed_ids.clear()

    if text == "/reset":
        conversations.pop(chat_id, None)
        notion_cache.pop(chat_id, None)
        await send_message(chat_id, "Conversation réinitialisée.")
        return {"ok": True}

    asyncio.create_task(process_message(chat_id, text))
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
