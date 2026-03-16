import os
import logging
from fastapi import FastAPI, Request
from telegram import Bot, Update
from config_manager import get_client_config
from claude_client import get_claude_response
from briefing import build_briefing
from debrief import start_debrief, is_active, handle_callback, handle_text as debrief_handle_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "Agent IA Immo — opérationnel"}


@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    """Point d'entrée pour tous les bots Telegram. Chaque client a son propre token."""
    try:
        data = await request.json()
        bot = Bot(token=token)
        update = Update.de_json(data, bot)

        # ── CALLBACK QUERY (boutons inline) ────────────────
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            chat_id = query.message.chat_id
            msg, keyboard, done = handle_callback(chat_id, query.data)
            if msg:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown",
                                       reply_markup=keyboard)
            return {"ok": True}

        if not update.message or not update.message.text:
            return {"ok": True}

        user_message = update.message.text
        chat_id = update.message.chat_id
        user_name = update.message.from_user.first_name or "le prospect"

        logger.info(f"[{token[:10]}...] Message de {user_name}: {user_message[:50]}")

        # ── COMMANDE /debrief ───────────────────────────────
        if user_message.strip().lower() == "/debrief":
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            try:
                msg, keyboard = start_debrief(chat_id)
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown",
                                       reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Erreur debrief: {e}")
                await bot.send_message(chat_id=chat_id, text="Erreur lors du démarrage du debrief.")
            return {"ok": True}

        # ── SESSION DEBRIEF EN COURS ─────────────────────────
        if is_active(chat_id):
            msg, keyboard, done = debrief_handle_text(chat_id, user_message)
            if msg is not None:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown",
                                       reply_markup=keyboard)
                return {"ok": True}

        # ── COMMANDE /journee — 0% Claude ──────────────────
        if user_message.strip().lower() in ["/journee", "/journée"]:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            try:
                briefing = build_briefing()
                await bot.send_message(
                    chat_id=chat_id,
                    text=briefing,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Erreur briefing: {e}")
                await bot.send_message(chat_id=chat_id, text="Erreur lors de la génération du briefing.")
            return {"ok": True}

        # ── Charge la config du client (avec cache 30 min) ──
        client_config = get_client_config(token)
        if not client_config:
            await bot.send_message(chat_id=chat_id, text="Ce bot n'est pas configuré.")
            return {"ok": True}

        # Indicateur de saisie pendant que Claude génère
        await bot.send_chat_action(chat_id=chat_id, action="typing")

        # Appel Claude API
        response = await get_claude_response(
            user_message=user_message,
            user_name=user_name,
            client_config=client_config
        )

        await bot.send_message(chat_id=chat_id, text=response)
        logger.info(f"[{token[:10]}...] Réponse envoyée à {user_name}")

    except Exception as e:
        logger.error(f"Erreur webhook: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="Tape / pour voir les commandes disponibles."
            )
        except Exception:
            pass

    return {"ok": True}


@app.get("/setup/{token}")
async def setup_webhook(token: str, request: Request):
    """Enregistre le webhook Telegram pour un bot donné."""
    base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if not base_url:
        return {"error": "RAILWAY_PUBLIC_DOMAIN non défini"}

    webhook_url = f"https://{base_url}/webhook/{token}"
    bot = Bot(token=token)
    await bot.set_webhook(url=webhook_url)
    await bot.set_my_commands([
        ("journee",  "📋 Briefing du jour"),
        ("debrief",  "🌙 Debrief & mise à jour CRM"),
    ])
    return {"status": "webhook enregistré", "url": webhook_url}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
