from datetime import datetime
import crm_sheets as crm

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS  = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def build_briefing() -> str:
    now  = datetime.now()
    jour = JOURS[now.weekday()]
    date = f"{now.day} {MOIS[now.month - 1]} {now.year}"

    rdv       = crm.get_rdv_du_jour()
    a_valider = crm.get_a_valider()
    relances  = crm.get_relances_du_jour()
    chauds    = crm.get_leads_chauds()
    nouveaux  = crm.get_nouveaux_leads()

    lignes = [f"📋 *BRIEFING DU {jour.upper()} {date.upper()}*", ""]

    # ── PLANNING DU JOUR ──────────────────────────
    lignes.append("🗓 *PLANNING DU JOUR*")
    if rdv:
        for r in rdv:
            lignes.append(f"• {r.get('Nom','')} {r.get('Prénom','')} — {r.get('Secteur souhaité','')} _(budget {r.get('Budget max (€)','?')}€)_")
    else:
        lignes.append("• Aucun RDV confirmé pour aujourd'hui")
    lignes.append("")

    # ── RÉPONSES À VALIDER ────────────────────────
    lignes.append("⚠️ *RÉPONSES À VALIDER*")
    if a_valider:
        for r in a_valider:
            lignes.append(f"• {r.get('Nom','')} {r.get('Prénom','')} — {r.get('Dernier contact','—')}")
    else:
        lignes.append("• Aucune réponse en attente ✅")
    lignes.append("")

    # ── RELANCES DU JOUR ──────────────────────────
    lignes.append("🔄 *RELANCES DU JOUR*")
    if relances:
        for r in relances:
            lignes.append(f"• {r.get('Nom','')} {r.get('Prénom','')} — {r.get('Type de bien','')} {r.get('Secteur souhaité','')} _(dernier contact : {r.get('Dernier contact','—')})_")
    else:
        lignes.append("• Aucune relance prévue aujourd'hui")
    lignes.append("")

    # ── LEADS CHAUDS ──────────────────────────────
    if chauds:
        lignes.append("🔴 *LEADS CHAUDS — PRIORITÉ*")
        for r in chauds:
            lignes.append(f"• {r.get('Nom','')} {r.get('Prénom','')} — budget {r.get('Budget max (€)','?')}€")
        lignes.append("")

    # ── NOUVEAUX LEADS ────────────────────────────
    lignes.append("🆕 *NOUVEAUX LEADS*")
    if nouveaux:
        lignes.append(f"• *{len(nouveaux)} nouvelle(s) demande(s)*")
        for r in nouveaux:
            lignes.append(f"  — {r.get('Nom','')} {r.get('Prénom','')} : {r.get('Type de bien','')} {r.get('Secteur souhaité','')}")
    else:
        lignes.append("• Aucun nouveau lead")

    lignes.append("")
    lignes.append("_Généré automatiquement — Agent IA Immo_ 🤖")

    return "\n".join(lignes)
