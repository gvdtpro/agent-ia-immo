from dataclasses import dataclass, field
from typing import List


@dataclass
class Property:
    type: str        # "Appartement T3", "Maison", "Studio"
    surface: int     # m²
    location: str    # "Paris 15e", "Lyon 6e"
    price: int       # €
    status: str      # "Disponible", "Sous compromis", "Vendu"
    details: str     # "Balcon, parking, lumineux"


@dataclass
class ClientConfig:
    # Identification
    token_env_var: str      # Nom de la variable d'env contenant le token Telegram
    agency_name: str
    agent_name: str
    city: str
    phone: str
    email: str

    # Disponibilités
    availability: str       # "Lun-Ven 9h-19h, Sam 10h-17h"

    # Catalogue de biens
    properties: List[Property] = field(default_factory=list)

    # Instructions personnalisées (optionnel)
    custom_instructions: str = ""

    def build_system_prompt(self) -> str:
        props_text = "\n".join([
            f"• {p.type} {p.surface}m² — {p.location} — {p.price:,}€ ({p.status}) | {p.details}"
            for p in self.properties
        ]) or "Aucun bien disponible pour le moment."

        return f"""Tu es l'assistant IA de {self.agency_name}, agence immobilière à {self.city}.
Tu réponds aux prospects qui contactent l'agence via Telegram.

CONTACT AGENCE :
- Agent : {self.agent_name}
- Téléphone : {self.phone}
- Email : {self.email}
- Disponibilités RDV : {self.availability}

BIENS DISPONIBLES :
{props_text}

RÈGLES DE RÉPONSE :
- Toujours en français, ton professionnel et chaleureux
- Réponses courtes (2-3 phrases max) adaptées à Telegram
- Si le prospect demande un bien disponible → propose une visite
- Si le prospect demande un bien non disponible → oriente vers un bien similaire
- Pour questions hors catalogue → propose de contacter {self.agent_name} directement
- Ne jamais inventer d'informations sur les biens
- Si le prospect souhaite un RDV → donne les disponibilités et le contact

{self.custom_instructions}"""
