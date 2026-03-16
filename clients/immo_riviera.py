from clients.base import ClientConfig, Property

config = ClientConfig(
    token_env_var="TELEGRAM_TOKEN_IMMO_RIVIERA",
    agency_name="Riviera Prestige Immobilier",
    agent_name="Alexandre Fontaine",
    city="Nice",
    phone="04 93 45 67 89",
    email="contact@riviera-prestige.fr",
    availability="Lun-Sam 9h-20h, dimanche sur RDV",
    properties=[
        Property(
            type="Appartement T4",
            surface=95,
            location="Nice Cimiez",
            price=620000,
            status="Disponible",
            details="Vue mer, terrasse 20m², parking, gardien, standing"
        ),
        Property(
            type="Villa",
            surface=220,
            location="Villefranche-sur-Mer",
            price=1850000,
            status="Disponible",
            details="Piscine, vue panoramique mer, 5 chambres, garage, jardin 800m²"
        ),
        Property(
            type="Appartement T2",
            surface=52,
            location="Nice Promenade des Anglais",
            price=390000,
            status="Disponible",
            details="Vue mer partielle, 2ème étage, balcon, résidence sécurisée"
        ),
        Property(
            type="Penthouse T5",
            surface=180,
            location="Cannes Croisette",
            price=3200000,
            status="Disponible",
            details="Rooftop privatif 80m², vue 360°, domotique, 2 parkings, cave"
        ),
        Property(
            type="Appartement T3",
            surface=74,
            location="Antibes Juan-les-Pins",
            price=480000,
            status="Sous compromis",
            details="200m de la plage, terrasse, cave, résidence avec piscine"
        ),
    ],
    custom_instructions="""
- Clientèle haut de gamme, adopte un ton élégant et discret
- Mettre en avant le style de vie et le prestige, pas seulement les m²
- Pour les biens > 1M€, proposer une visite privée avec champagne
- Préciser que des visites en visioconférence sont possibles pour les clients étrangers
- Ne jamais mentionner les prix des concurrents
"""
)
