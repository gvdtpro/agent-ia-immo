from datetime import datetime
import crm_notion as nc

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS  = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def build_briefing() -> str:
    now  = datetime.now()
    jour = JOURS[now.weekday()]
    date = f"{now.day} {MOIS[now.month - 1]} {now.year}"

    rdv       = nc.get_rdv_du_jour()
    a_valider = nc.get_a_valider()
    relances  = nc.get_relances_du_jour()
    chauds    = nc.get_leads_chauds()
    nouveaux  = nc.get_nouveaux_leads()

    lignes = [f"📋 *BRIEFING DU {jour.upper()} {date.upper()}*", ""]

    # ── PLANNING DU JOUR ──────────────────────────
    lignes.append("🗓 *PLANNING DU JOUR*")
    if rdv:
        for p in rdv:
            heure = nc.prop(p, 'Heure RDV')
            heure_str = f" à *{heure}*" if heure != "—" else ""
            lignes.append(f"• {nc.prop(p, 'Acheteur')}{heure_str} — {nc.prop(p, 'Critères')} _(budget {nc.prop(p, 'Budget')})_")
    else:
        lignes.append("• Aucun RDV confirmé pour aujourd'hui")
    lignes.append("")

    # ── RÉPONSES À VALIDER ────────────────────────
    lignes.append("⚠️ *RÉPONSES À VALIDER*")
    if a_valider:
        for p in a_valider:
            lignes.append(f"• {nc.prop(p, 'Acheteur')} — reçu {nc.prop(p, 'Dernier échange')}")
    else:
        lignes.append("• Aucune réponse en attente ✅")
    lignes.append("")

    # ── RELANCES DU JOUR ──────────────────────────
    lignes.append("🔄 *RELANCES DU JOUR*")
    if relances:
        for p in relances:
            lignes.append(f"• {nc.prop(p, 'Acheteur')} — {nc.prop(p, 'Critères')} _(dernier contact : {nc.prop(p, 'Dernier échange')})_")
    else:
        lignes.append("• Aucune relance prévue aujourd'hui")
    lignes.append("")

    # ── LEADS CHAUDS ──────────────────────────────
    if chauds:
        lignes.append("🔴 *LEADS CHAUDS — PRIORITÉ*")
        for p in chauds:
            lignes.append(f"• {nc.prop(p, 'Acheteur')} — budget {nc.prop(p, 'Budget')}")
        lignes.append("")

    # ── NOUVEAUX LEADS ────────────────────────────
    lignes.append("🆕 *NOUVEAUX LEADS*")
    if nouveaux:
        lignes.append(f"• *{len(nouveaux)} nouvelle(s) demande(s)*")
        for p in nouveaux:
            lignes.append(f"  — {nc.prop(p, 'Acheteur')} : {nc.prop(p, 'Critères')}")
    else:
        lignes.append("• Aucun nouveau lead")

    lignes.append("")
    lignes.append("_Généré automatiquement — Agent IA Immo_ 🤖")

    return "\n".join(lignes)
