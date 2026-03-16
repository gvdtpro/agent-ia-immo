import os
import logging
from datetime import datetime, timedelta, timezone
from notion_client import Client

logger = logging.getLogger(__name__)

# IDs des bases Notion créées
ACHETEURS_DB = "6e1b31167aa64f519880943a194c4c66"
VENDEURS_DB  = "12c1fed387f24932a3808289b3d3e986"

_notion = None

def get_notion():
    global _notion
    if not _notion:
        _notion = Client(auth=os.environ["NOTION_TOKEN"])
    return _notion


def query_acheteurs(filtre: dict = None) -> list:
    kwargs = {"database_id": ACHETEURS_DB}
    if filtre:
        kwargs["filter"] = filtre
    kwargs["sorts"] = [{"timestamp": "created_time", "direction": "descending"}]
    res = get_notion().databases.query(**kwargs)
    return res["results"]


def get_rdv_du_jour() -> list:
    """Acheteurs avec un RDV aujourd'hui."""
    today = datetime.now().strftime("%Y-%m-%d")
    return query_acheteurs({
        "and": [
            {"property": "Statut", "select": {"equals": "RDV confirmé"}},
            {"property": "Date RDV", "date": {"equals": today}}
        ]
    })


def get_a_valider() -> list:
    """Nouveaux prospects ajoutés manuellement, pas encore traités."""
    return query_acheteurs({
        "property": "Statut",
        "select": {"equals": "Ajouté manuellement"}
    })


def get_relances_du_jour() -> list:
    """Acheteurs en attente de relance auto."""
    return query_acheteurs({
        "property": "Statut",
        "select": {"equals": "Relance auto"}
    })


def get_nouveaux_leads(heures: int = 24) -> list:
    """Prospects dont la Date premier contact est dans les dernières X heures."""
    depuis = (datetime.now(timezone.utc) - timedelta(hours=heures)).strftime("%Y-%m-%d")
    return query_acheteurs({
        "property": "Date premier contact",
        "date": {"on_or_after": depuis}
    })


def get_leads_chauds() -> list:
    """Acheteurs avec statut Chaud."""
    return query_acheteurs({
        "property": "Statut",
        "select": {"equals": "Chaud"}
    })


def prop(page: dict, name: str) -> str:
    """Extrait la valeur d'une propriété Notion de façon sécurisée."""
    try:
        p = page["properties"][name]
        t = p["type"]
        if t == "title":
            return p["title"][0]["plain_text"] if p["title"] else "—"
        if t == "rich_text":
            return p["rich_text"][0]["plain_text"] if p["rich_text"] else "—"
        if t == "select":
            return p["select"]["name"] if p["select"] else "—"
        if t == "number":
            v = p["number"]
            return f"{v:,}€".replace(",", " ") if v else "—"
        if t == "phone_number":
            return p["phone_number"] or "—"
        if t == "email":
            return p["email"] or "—"
    except (KeyError, IndexError, TypeError):
        return "—"
    return "—"
