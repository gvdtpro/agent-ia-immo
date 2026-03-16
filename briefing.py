from datetime import datetime
import crm_notion as nc

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS  = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def build_briefing() -> str:
    """
    Génère le briefing quotidien sans appel Claude.
    Retourne une chaîne formatée pour Telegram (Markdown).
    """
    now = datetime.now()
    jour = JOURS[now.weekday()]
    date = f"{now.day} {MOIS[now.month - 1]} {now.year}"

    rdv        = nc.get_rdv_du_jour()
    a_valider  = nc.get_a_valider()
    relances   = nc.get_relances_du_jour()
    nouveaux   = nc.get_nouveaux_leads(heures=24)
    chauds     = nc.get_leads_chauds()

    lignes = [
        f"📋 *BRIEFING DU {jour.upper()} {date.upper()}*",
        ""
    ]

    # ── PLANNING DU JOUR ──────────────────────────
    lignes.append("🗓 *PLANNING DU JOUR*")
    if rdv:
        for p in rdv:
            nom     = nc.prop(p, "Acheteur")
            budget  = nc.prop(p, "Budget")
            critere = nc.prop(p, "Critères")
            lignes.append(f"• {nom} — {critere} _(budget {budget})_")
    else:
        lignes.append("• Aucun RDV confirmé pour aujourd'hui")
    lignes.append("")

    # ── RÉPONSES À VALIDER ────────────────────────
    lignes.append("⚠️ *RÉPONSES À VALIDER*")
    if a_valider:
        for p in a_valider:
            nom     = nc.prop(p, "Acheteur")
            dernier = nc.prop(p, "Dernier échange")
            lignes.append(f"• {nom} — reçu {dernier}")
    else:
        lignes.append("• Aucune réponse en attente ✅")
    lignes.append("")

    # ── RELANCES DU JOUR ──────────────────────────
    lignes.append("🔄 *RELANCES DU JOUR*")
    if relances:
        for p in relances:
            nom     = nc.prop(p, "Acheteur")
            dernier = nc.prop(p, "Dernier échange")
            critere = nc.prop(p, "Critères")
            lignes.append(f"• {nom} — {critere} _(dernier contact : {dernier})_")
    else:
        lignes.append("• Aucune relance prévue aujourd'hui")
    lignes.append("")

    # ── LEADS CHAUDS ──────────────────────────────
    if chauds:
        lignes.append("🔴 *LEADS CHAUDS — À TRAITER EN PRIORITÉ*")
        for p in chauds:
            nom    = nc.prop(p, "Acheteur")
            budget = nc.prop(p, "Budget")
            lignes.append(f"• {nom} — budget {budget}")
        lignes.append("")

    # ── NOUVEAUX LEADS ────────────────────────────
    lignes.append("🆕 *NOUVEAUX LEADS (24H)*")
    if nouveaux:
        lignes.append(f"• *{len(nouveaux)} nouvelle(s) demande(s)* reçue(s)")
        for p in nouveaux:
            nom     = nc.prop(p, "Acheteur")
            critere = nc.prop(p, "Critères")
            lignes.append(f"  — {nom} : {critere}")
    else:
        lignes.append("• Aucun nouveau lead depuis hier")

    lignes.append("")
    lignes.append("_Généré automatiquement — Agent IA Immo_ 🤖")

    return "\n".join(lignes)
