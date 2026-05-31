"""Fixed ZAP URLs, query defaults, and amenity code → label map."""

from __future__ import annotations

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

# GraphQL field selection (includeFields query param)
_API_LISTING_FIELDS = (
    "expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,"
    "amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,"
    "floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,"
    "legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,"
    "externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,"
    "bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,"
    "priceSuggestion,condominiumName,modality,enhancedDevelopment"
)
_API_ACCOUNT_FIELDS = (
    "config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,"
    "createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser"
)
_API_CHILDREN_FIELDS = (
    "id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos"
)


def _api_listings_inner_bundle() -> str:
    return (
        f"listing({_API_LISTING_FIELDS}),"
        f"account({_API_ACCOUNT_FIELDS}),"
        f"medias,accountLink,link,"
        f"children({_API_CHILDREN_FIELDS})"
    )


def _api_listings_search_block(name: str) -> str:
    return f"{name}(search(result(listings({_api_listings_inner_bundle()})),totalCount))"


#https://glue-api.zapimoveis.com.br/v4/listings?categoryPage=RESULT&business=RENTAL&parentId=null&listingType=USED&images=webp&user=934d5980-0fdf-40de-adc3-879b1ebd14ae&portal=ZAP&__zt=mtc:deduplication2023&addressCity=Belo+Horizonte&addressZone=&addressStreet=&addressLocationId=BR>Minas+Gerais>NULL>Belo+Horizonte&addressState=Minas+Gerais&addressNeighborhood=&addressPointLat=-19.919052&addressPointLon=-43.938669&addressType=city&page=3&size=30&from=60&includeFields=expansion(search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)),fullUriFragments,nearby(search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)),page,search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount),topoFixo(search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount))&__id=search

def _join_query_params(params: dict[str, str]) -> str:
    return "&".join(f"{key}={value}" for key, value in params.items())


    """Build glue-api listings URL; pass e.g. page=1, size=30, from=0, business=SALE, user=…"""
def build_api_listings_url(transacao: str, **overrides: str) -> str:
    # --- glue-api /v4/listings query (defaults; override via build_api_listings_url) ---
    API_LISTINGS_BASE = "https://glue-api.zapimoveis.com.br/v4/listings"
    API_LISTINGS_QUERY: dict[str, str] = {
        "categoryPage": "RESULT",
        "business": "RENTAL" if transacao == TRANSACAO_ALUGUEL else "SALE",
        "sort": "MOST_RECENT",
        "parentId": "null",
        "listingType": "USED",
        "images": "webp",
        "user": "934d5980-0fdf-40de-adc3-879b1ebd14ae",
        "portal": "ZAP",
        "__zt": "mtc:deduplication2023",
        "viewport": "maxX,maxY|minX,minY",
        "page": "3",
        "size": "30",
        "from": "60",
        "includeFields": "nearby(search(result(listings(listing(h2Tag,expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)),page,search(result(listings(listing(h2Tag,expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount),topoFixo(search(result(listings(listing(h2Tag,expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount))",
        #"addressCity": "Belo+Horizonte",
        #"addressZone": "",
        #"addressStreet": "",
        #"addressLocationId": "BR>Minas+Gerais>NULL>Belo+Horizonte",
        #"addressState": "Minas+Gerais",
        #"addressNeighborhood": "",
        #"addressPointLat": "-19.919052",
        #"addressPointLon": "-43.938669",
        #"addressType": "city",
        "__id": "search",
    }
    #https://glue-api.zapimoveis.com.br/v4/listings?categoryPage=RESULT&business=RENTAL&sort=MOST_RECENT&parentId=null&listingType=USED&images=webp&user=934d5980-0fdf-40de-adc3-879b1ebd14ae&portal=ZAP&__zt=mtc:deduplication2023&viewport=-43.87875917944335,-19.83890073050035|-43.99857882055663,-19.999162659634596&page=2&size=30&from=30&includeFields=fullUriFragments,page,search(result(listings(listing(h2Tag,expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)&__id=search
    params = {**API_LISTINGS_QUERY, **overrides}
    return f"{API_LISTINGS_BASE}?{_join_query_params(params)}"


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
