import httpx
import re
from typing import Dict, Any
from app.core.dynamodb import get_authority_cache, save_authority_cache
from app.services.discovery_agent import discover_authority_via_web

LOCAL_DIRECTORY = {
    "pune": {
        "corporation": "Pune Municipal Corporation (PMC)",
        "portal_url": "https://complaint.pmc.gov.in/",
        "nodal_email": "feedback@punecorporation.org",
        "requires_otp": True,
        "jurisdiction": "PMC Urban Local Body",
    },
    "pcmc": {
        "corporation": "Pimpri Chinchwad Municipal Corporation (PCMC)",
        "portal_url": "https://grievance.pcmcindia.gov.in:8443/Grievance/citizen/",
        "nodal_email": "sarathi@pcmcindia.gov.in",
        "requires_otp": True,
        "jurisdiction": "PCMC Urban Local Body",
    },
    "mumbai": {
        "corporation": "Brihanmumbai Municipal Corporation (BMC)",
        "portal_url": "https://marg.mcgm.gov.in/MARG/welcomePage.html",
        "nodal_email": "feedback@mcgm.gov.in",
        "requires_otp": False,
        "jurisdiction": "BMC Greater Mumbai",
    },
}

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())

def _fast_bbox_match(lat: float, lng: float) -> str | None:
    """Instant sub-millisecond coordinate bounding-box resolution for demo metros."""
    # PCMC (Pimpri-Chinchwad, Nigdi, Bhosari, Akurdi, Ravet, Wakad - Northwest)
    if 18.58 <= lat <= 18.75 and 73.72 <= lng <= 73.90:
        return "pcmc"
    # PMC (Pune Central, Shivaji Nagar, Kothrud, Hadapsar, Camp, Katraj, Viman Nagar, Kharadi, Wagholi)
    if 18.40 <= lat <= 18.66 and 73.70 <= lng <= 74.08:
        return "pune"
    if 18.90 <= lat <= 19.30 and 72.75 <= lng <= 73.05:
        return "mumbai"
    if 12.80 <= lat <= 13.15 and 77.45 <= lng <= 77.75:
        return "bengaluru"
    return None

def resolve_authority(lat: float, lng: float) -> Dict[str, Any]:
    # 1. Instant Bounding Box Check (0.1ms - skips OSM entirely)
    fast_city = _fast_bbox_match(lat, lng)
    if fast_city and fast_city in LOCAL_DIRECTORY:
        auth = dict(LOCAL_DIRECTORY[fast_city])
        auth["city_slug"] = fast_city
        auth["ward_detected"] = "Metro Central Ward"
        auth["is_cached"] = True
        return auth

    # 2. Reverse Geocode via Nominatim (Only if outside indexed metro boxes)
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
    headers = {"User-Agent": "CivicPulse-AI/1.0 (env-hackathon; contact@civicpulse.org)"}

    try:
        with httpx.Client(timeout=2.5) as client:
            resp = client.get(url, headers=headers).json()
    except Exception as e:
        print(f"[Nominatim Warning] Timeout/Error ({e}), defaulting to Pune")
        resp = {}

    address = resp.get("address", {})
    suburb = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("residential")
        or "Central Ward"
    )
    city = (
        address.get("city")
        or address.get("town")
        or address.get("state_district")
        or address.get("county")
        or "Pune"
    )
    state = address.get("state") or "Maharashtra"
    city_slug = _slugify(city)
    if any(k in (city + " " + suburb).lower() for k in ["pimpri", "chinchwad", "pcmc"]):
        city_slug = "pcmc"

    # 3. DynamoDB Cache Check (< 50ms)
    cached = get_authority_cache(city_slug)
    if cached:
        cached["ward_detected"] = suburb
        cached["is_cached"] = True
        return cached

    # 4. Local Directory Check
    if city_slug in LOCAL_DIRECTORY:
        auth = dict(LOCAL_DIRECTORY[city_slug])
        auth["city_slug"] = city_slug
        auth["ward_detected"] = suburb
        auth["is_cached"] = False
        save_authority_cache(city_slug, auth)
        return auth

    # 5. Live Search Fallback (Only for unindexed locations)
    print(f"[*] City '{city}' not indexed. Spawning Groq Web Discovery Agent...")
    auth = discover_authority_via_web(city=city, state=state)
    auth["city_slug"] = city_slug
    auth["ward_detected"] = suburb
    auth["is_cached"] = False
    save_authority_cache(city_slug, auth)
    return auth