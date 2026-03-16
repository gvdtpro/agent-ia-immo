from clients.base import ClientConfig, Property

config = ClientConfig(
    token_env_var="TELEGRAM_TOKEN_DEMO",
    agency_name="Martin Immobilier",
    agent_name="Sophie Martin",
    city="Lyon",
    phone="04 78 12 34 56",
    email="contact@martin-immo.fr",
    availability="Lun-Ven 9h-19h, Sam 10h-17h",
    properties=[
        Property(
            type="Appartement T3",
            surface=68,
            location="Lyon 6e",
            price=320000,
            status="Disponible",
            details="Balcon, double vitrage, cave, proche métro Foch"
        ),
        Property(
            type="Appartement T2",
            surface=45,
            location="Lyon 3e",
            price=210000,
            status="Disponible",
            details="Lumineux, refait à neuf, parking inclus"
        ),
        Property(
            type="Maison",
            surface=140,
            location="Caluire-et-Cuire",
            price=580000,
            status="Disponible",
            details="Jardin 300m², garage double, 4 chambres, proche écoles"
        ),
        Property(
            type="Studio",
            surface=28,
            location="Lyon 7e",
            price=135000,
            status="Sous compromis",
            details="Idéal investissement locatif, proche Jean Macé"
        ),
    ],
    custom_instructions="""
- Mets en avant la qualité de vie dans le quartier Foch pour le T3
- Pour les familles, recommande en priorité la maison de Caluire
- Ne pas mentionner les agences concurrentes
"""
)
