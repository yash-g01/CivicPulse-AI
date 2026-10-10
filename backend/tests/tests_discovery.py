import time
from app.services.geo_router import resolve_authority

if __name__ == "__main__":
    print("[*] Testing Live Web-Surfing Authority Discovery...\n")

    test_locations = [
        {"city": "Jaipur", "lat": 26.9124, "lng": 75.7873},
        {"city": "Lucknow", "lat": 26.8467, "lng": 80.9462},
        {"city": "Indore", "lat": 22.7196, "lng": 75.8577},
    ]

    for loc in test_locations:
        print(f"--- Resolving Coordinates for {loc['city']} ({loc['lat']}, {loc['lng']}) ---")
        start = time.time()
        auth = resolve_authority(loc["lat"], loc["lng"])
        elapsed = (time.time() - start) * 1000

        print(f"Time Taken: {elapsed:.1f}ms (is_cached: {auth.get('is_cached')})")
        print(f"Corporation : {auth.get('corporation')}")
        print(f"Portal URL  : {auth.get('portal_url')}")
        print(f"Nodal Email : {auth.get('nodal_email')}")
        print(f"Requires OTP: {auth.get('requires_otp')}\n")