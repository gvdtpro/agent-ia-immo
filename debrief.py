"""
Session de debrief quotidien — le bot pose les questions RDV par RDV
et met à jour Notion en temps réel.
"""
import re
import crm_notion as nc
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Sessions actives { chat_id: { rdvs, index, step, statut_choisi, prochain_rdv } }
_sessions: dict = {}


def start_debrief(chat_id: int) -> tuple:
    """Démarre une session. Retourne (message, keyboard)."""
    rdvs = nc.get_rdv_du_jour()
    if not rdvs:
        return "Aucun RDV aujourd'hui à débriefer ✅", None

    _sessions[chat_id] = {"rdvs": rdvs, "index": 0, "step": "statut"}
    return _format_question(chat_id)


def is_active(chat_id: int) -> bool:
    return chat_id in _sessions


def handle_callback(chat_id: int, data: str) -> tuple:
    """Bouton inline pressé. Retourne (message, keyboard, is_done)."""
    if chat_id not in _sessions:
        return "Pas de debrief en cours.", None, True

    session = _sessions[chat_id]
    if session["step"] == "statut":
        session["statut_choisi"] = data
        session["step"] = "prochain_rdv"
        return "📅 Prochain RDV prévu ? _(tape une date ex: 25/03, ou 'non')_", None, False

    return "", None, False


def handle_text(chat_id: int, text: str) -> tuple:
    """Réponse texte libre. Retourne (message, keyboard, is_done)."""
    if chat_id not in _sessions:
        return None, None, True  # pas notre affaire

    session = _sessions[chat_id]
    step = session["step"]

    if step == "statut":
        # L'utilisateur a tapé du texte au lieu d'appuyer sur un bouton
        return "Utilise les boutons ☝️", None, False

    if step == "prochain_rdv":
        session["prochain_rdv"] = None if _is_non(text) else text
        session["step"] = "notes"
        return "📝 Notes ? _(ou 'non' pour passer)_", None, False

    if step == "notes":
        notes = None if _is_non(text) else text
        page_id = session["rdvs"][session["index"]]["id"]
        nc.update_acheteur(
            page_id=page_id,
            statut=session.get("statut_choisi"),
            prochain_rdv=session.get("prochain_rdv"),
            notes=notes,
        )
        return _next_rdv(chat_id)

    return None, None, True


# ── Helpers ──────────────────────────────────────────────────────────

def _format_question(chat_id: int) -> tuple:
    session = _sessions[chat_id]
    page = session["rdvs"][session["index"]]
    total = len(session["rdvs"])
    idx = session["index"] + 1

    nom = nc.prop(page, "Acheteur")
    type_rdv = nc.prop(page, "Type RDV")
    heure = nc.prop(page, "Heure RDV")

    sous_titre = " · ".join(x for x in [type_rdv, heure] if x != "—")
    msg = f"🌙 *DEBRIEF {idx}/{total} — {nom}*"
    if sous_titre:
        msg += f"\n_{sous_titre}_"
    msg += "\n\nComment ça s'est passé ?"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔴 Chaud",    callback_data="Chaud"),
        InlineKeyboardButton("🟡 Tiède",    callback_data="Relance auto"),
        InlineKeyboardButton("🔵 Pas intéressé", callback_data="Froid"),
    ]])
    return msg, keyboard


def _next_rdv(chat_id: int) -> tuple:
    session = _sessions[chat_id]
    session["index"] += 1

    if session["index"] >= len(session["rdvs"]):
        del _sessions[chat_id]
        return "✅ *Debrief terminé — CRM mis à jour !*", None, True

    session["step"] = "statut"
    msg, keyboard = _format_question(chat_id)
    return msg, keyboard, False


def _is_non(text: str) -> bool:
    return text.strip().lower() in ["non", "no", "-", "rien", "skip"]


def _parse_date(text: str):
    """Convertit DD/MM ou DD/MM/YYYY → YYYY-MM-DD, sinon None."""
    text = text.strip()
    m = re.match(r'^(\d{1,2})/(\d{1,2})$', text)
    if m:
        return f"2026-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None
