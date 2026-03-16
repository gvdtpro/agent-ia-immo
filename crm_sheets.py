import os
import json
import logging
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SHEET_ID    = "1685i6kn1d6yy1PAGX2KBy3SPeF3ziug5SAE561vodk0"
SCOPES      = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

_client = None

def get_client():
    global _client
    if not _client:
        creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client


def get_sheet(tab: str):
    return get_client().open_by_key(SHEET_ID).worksheet(tab)


def get_all_acheteurs() -> list[dict]:
    """Retourne tous les acheteurs sous forme de liste de dicts."""
    sheet = get_sheet("Acheteurs")
    return sheet.get_all_records()


def get_rdv_du_jour() -> list[dict]:
    return [r for r in get_all_acheteurs() if r.get("Statut", "") == "🔴 Chaud"]


def get_a_valider() -> list[dict]:
    return [r for r in get_all_acheteurs() if r.get("Statut", "") == "Ajouté manuellement"]


def get_relances_du_jour() -> list[dict]:
    return [r for r in get_all_acheteurs() if "Relance" in r.get("Statut", "") or r.get("Statut", "") == "🟡 Tiède"]


def get_leads_chauds() -> list[dict]:
    return [r for r in get_all_acheteurs() if "Chaud" in r.get("Statut", "")]


def get_nouveaux_leads() -> list[dict]:
    """Prospects dont le statut est 'Ajouté manuellement' — considérés comme nouveaux."""
    return [r for r in get_all_acheteurs() if "Ajouté" in r.get("Statut", "")]
