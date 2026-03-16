import os
import logging
import anthropic
from clients.base import ClientConfig

logger = logging.getLogger(__name__)

# Client Anthropic partagé (réutilise la connexion HTTP)
_client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"  # Rapide + pas cher (~$0.001/message)
MAX_TOKENS = 300                      # Réponses courtes pour Telegram


async def get_claude_response(
    user_message: str,
    user_name: str,
    client_config: ClientConfig
) -> str:
    """
    Appelle l'API Claude avec le system prompt du client
    et retourne la réponse texte.
    """
    try:
        response = await _client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=client_config.build_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": f"[Prospect : {user_name}]\n{user_message}"
                }
            ]
        )

        answer = response.content[0].text
        logger.info(
            f"Tokens utilisés — input: {response.usage.input_tokens}, "
            f"output: {response.usage.output_tokens}"
        )
        return answer

    except anthropic.AuthenticationError:
        logger.error("Clé API Anthropic invalide ou crédit insuffisant")
        return "Je suis momentanément indisponible. Contactez-nous directement."

    except Exception as e:
        logger.error(f"Erreur Claude API: {e}")
        return "Une erreur est survenue. Veuillez réessayer dans quelques instants."
