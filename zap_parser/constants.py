"""Fixed ZAP URLs, query defaults, and amenity code → label map."""

BH_VIEWPORT = (
    "-43.820222649902334,-19.770017419143223|-44.05711535009765,-20.067946236292432"
)
BH_ONDE = (
    ",Minas Gerais,Belo Horizonte,,,,,city,BR>Minas Gerais>NULL>Belo Horizonte,-19.919052,-43.938669,"
)

TRANSACAO_ALUGUEL = "aluguel"
TRANSACAO_VENDA = "venda"

BASE_QUERY: dict[str, str] = {
    "transacao": "aluguel",
    "tipos": (
        "apartamento_residencial,casa_residencial,studio_residencial,kitnet_residencial,"
        "condominio_residencial,casa-vila_residencial,cobertura_residencial,flat_residencial,"
        "loft_residencial,lote-terreno_residencial,sobrado_residencial,granja_residencial"
    ),
    "ordem": "MOST_RECENT",
}

MAX_PAGES = 50

ZAP_AMENITY_LABELS: dict[str, str] = {
    "INTERNET_ACCESS": "Internet",
    "GRASS": "Gramado",
    "CABLE_TV": "TV a cabo",
    "GATED_COMMUNITY": "Condomínio fechado",
    "HEATING": "Aquecimento",
    "KITCHEN": "Cozinha",
    "SERVICE_AREA": "Área de serviço",
    "ELEVATOR": "Elevador",
    "WATCHMAN": "Vigia",
    "GARAGE": "Garagem",
    "GARDEN": "Jardim",
    "FURNISHED": "Mobiliado",
    "SAFETY_CIRCUIT": "Circuito de segurança",
    "PETS_ALLOWED": "Aceita pets",
    "CONCIERGE_24H": "Portaria 24h",
    "INTERCOM": "Interfone",
    "POOL": "Piscina",
    "GYM": "Academia",
    "LAUNDRY": "Lavanderia",
    "ELECTRONIC_GATE": "Portão eletrônico",
    "DISABLED_ACCESS": "Acesso para deficientes",
    "SAUNA": "Sauna",
    "BALCONY": "Varanda",
    "CLOSET": "Closet",
    "AMERICAN_KITCHEN": "Cozinha americana",
    "SUITE": "Suíte",
    "PLAYGROUND": "Playground",
    "SPORTS_COURT": "Quadra poliesportiva",
    "BARBECUE_GRILL": "Churrasqueira",
    "PARTY_ROOM": "Salão de festas",
    "AIR_CONDITIONING": "Ar-condicionado",
}

# Nominatim policy: identifiable User-Agent
NOMINATIM_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
