import time
import importlib
import os
import logging
from clients.base import ClientConfig

logger = logging.getLogger(__name__)

# Cache en mémoire : {token: {"config": ClientConfig, "time": float}}
_cache: dict = {}
CACHE_TTL = 1800  # 30 minutes


def get_client_config(token: str) -> ClientConfig | None:
    """
    Retourne la config client associée au token Telegram.
    Utilise un cache de 30 min pour éviter les appels répétés.
    """
    now = time.time()

    # Cache valide → on retourne directement
    if token in _cache:
        if now - _cache[token]["time"] < CACHE_TTL:
            return _cache[token]["config"]

    # Sinon on charge depuis les fichiers clients/
    config = _load_config_for_token(token)
    if config:
        _cache[token] = {"config": config, "time": now}
        logger.info(f"Config chargée et mise en cache pour token {token[:10]}...")

    return config


def _load_config_for_token(token: str) -> ClientConfig | None:
    """
    Parcourt tous les modules dans clients/ et retourne
    celui dont le token correspond.
    """
    clients_dir = os.path.join(os.path.dirname(__file__), "clients")

    for filename in os.listdir(clients_dir):
        if filename.startswith("_") or not filename.endswith(".py"):
            continue

        module_name = filename[:-3]
        try:
            module = importlib.import_module(f"clients.{module_name}")
            if hasattr(module, "config"):
                client_token = os.environ.get(module.config.token_env_var, "")
                if client_token == token:
                    return module.config
        except Exception as e:
            logger.error(f"Erreur chargement client {module_name}: {e}")

    logger.warning(f"Aucun client trouvé pour le token {token[:10]}...")
    return None


def invalidate_cache(token: str = None):
    """Vide le cache pour forcer un rechargement. Utile après modif config."""
    global _cache
    if token:
        _cache.pop(token, None)
    else:
        _cache.clear()
    logger.info("Cache config invalidé")
