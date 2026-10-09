import json
from app.services.triage_service import triage_waste_image

if __name__ == "__main__":
    image_path = "tests/dump.jpeg"
    result = triage_waste_image(image_path)
    print(f"[*] Triaging {image_path} via Gemini 3.8 Flash...")
    print(json.dumps(result, indent=2))