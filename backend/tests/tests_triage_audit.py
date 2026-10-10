import json
from app.services.triage_service import triage_waste_image
from app.services.audit_service import audit_resolution_images

if __name__ == "__main__":
    image_path = "tests/dump.jpeg"
    result = triage_waste_image(image_path)
    print(f"[*] Triaging {image_path} via Groq Vision...")
    print(json.dumps(result, indent=2))

    image_before_path = "tests/dump.jpeg"
    image_after_path = "tests/cleaned.jpg"
    result = audit_resolution_images(image_before_path, image_after_path)
    print(f"[*] Auditing resolution images...")
    print(json.dumps(result, indent=2))

    image_before_path = "tests/dump.jpeg"
    image_after_path = "tests/fake_clean.jpg"
    result = audit_resolution_images(image_before_path, image_after_path)
    print(f"[*] Auditing Fake resolution images...")
    print(json.dumps(result, indent=2))