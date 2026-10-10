import httpx
import re
from typing import Dict, Any
from app.core.dynamodb import get_authority_cache, save_authority_cache
from app.services.discovery_agent import discover_authority_via_web

# Pre-seeded directory for instant sub-5ms resolution of common test cities
LOCAL_DIRECTORY = {
    "pune": {
        "corporation": "Pune Municipal Corporation (PMC)",
        "portal_url": "[https://complaint.pmc.gov.in/](https://complaint.pmc.gov.in/)",
        "nodal_email": "feedback@punecorporation.org",
        "requires_otp": True,
        "jurisdiction": "PMC Urban Local Body",
    },
    "mumbai": {
        "corporation": "Brihanmumbai Municipal Corporation (BMC)",
        "portal_url": "[https://portal.mcgm.gov.in/](https://portal.mcgm.gov.in/)",
        "nodal_email": "feedback@mcgm.gov.in",
        "requires_otp": False,
        "jurisdiction": "BMC Greater Mumbai",
    },
    "bengaluru": {
        "corporation": "Bruhat Bengaluru Mahanagara Palike (BBMP)",
        "portal_url": "[https://bbmpeaas.karnataka.gov.in/sahaaya/](https://bbmpeaas.karnataka.gov.in/sahaaya/)",
        "nodal_email": "comm@bbmp.gov.in",
        "requires_otp": True,
        "jurisdiction": "BBMP Solid Waste Division",
    },
}

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())

def resolve_authority(lat: float, lng: float) -> Dict[str, Any]:
    """
    Resolves GPS coordinates into municipal authority details:
    1. Reverse geocodes coordinates via OpenStreetMap Nominatim.
    2. Checks DynamoDB cache for an existing resolution (< 50ms).
    3. Checks pre-seeded local dictionary.
    4. Surfs the live web via Gemini Google Search agent, parses the portal/email,
       and caches to DynamoDB.
    """
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
    headers = {"User-Agent": "CivicPulse-AI/1.0 (env-hackathon; contact@civicpulse.org)"}

    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(url, headers=headers).json()
    except Exception as e:
        print(f"[Nominatim Error] Geocoding request failed: {e}")
        resp = {}

    address = resp.get("address", {})
    city = (
        address.get("city")
        or address.get("town")
        or address.get("state_district")
        or address.get("county")
        or "Pune"
    )
    state = address.get("state") or "Maharashtra"
    suburb = address.get("suburb") or address.get("neighbourhood") or "Ward Area"
    city_slug = _slugify(city)

    # 1. DynamoDB Cache Check (< 50ms)
    cached = get_authority_cache(city_slug)
    if cached:
        cached["ward_detected"] = suburb
        cached["state"] = state
        cached["is_cached"] = True
        return cached

    # 2. Local Pre-seeded Directory Check
    if city_slug in LOCAL_DIRECTORY:
        authority = dict(LOCAL_DIRECTORY[city_slug])
        authority["city_slug"] = city_slug
        authority["state"] = state
        authority["ward_detected"] = suburb
        authority["is_cached"] = False
        save_authority_cache(city_slug, authority)
        return authority

    # 3. Dynamic Web-Surfing Agent (Live Google Search)
    print(f"[*] City '{city}' not indexed. Spawning Gemini Web Discovery Agent for {city}, {state}...")
    authority = discover_authority_via_web(city=city, state=state)
    authority["city_slug"] = city_slug
    authority["state"] = state
    authority["ward_detected"] = suburb
    authority["is_cached"] = False

    # 4. Cache into DynamoDB so future reports for this city resolve instantly
    save_authority_cache(city_slug, authority)
    print(f"[✓] Discovered and cached {authority['corporation']}: {authority['portal_url']}")

    return authority