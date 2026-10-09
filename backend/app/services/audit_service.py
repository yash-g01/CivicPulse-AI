import os
import sys
import json
import base64
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def audit_resolution_images(before_path: str, after_path: str) -> dict:
    prompt = """
    You are an environmental accountability auditor inspecting a municipal cleanup claim.
    You are provided two images:
    Image 1: Initial complaint showing the uncollected waste ("Before").
    Image 2: Cleanup evidence submitted by municipal workers to claim resolution ("After").

    Inspect carefully:
    1. is_same_scene: Does Image 2 photograph the exact same physical location as Image 1? Check landmarks, boundary walls, trees, curb alignments, and utilities.
    2. debris_cleared: Has the pile in Image 1 actually been removed in Image 2?
    3. fraud_detected: True if the worker photographed a completely different clean location, an irrelevant angle, or if debris is still present.
    4. confidence: Float score between 0.0 and 1.0.
    5. discrepancy_notes: Concise analysis explaining the verification result.

    Output ONLY raw valid JSON:
    {
      "is_same_scene": boolean,
      "debris_cleared": boolean,
      "fraud_detected": boolean,
      "confidence": float,
      "discrepancy_notes": string
    }
    """

    # Load image
    with open(before_path, "rb") as f:
        image_bytes = f.read()
    image_before_b64 = base64.b64encode(image_bytes).decode("utf-8")

    with open(after_path, "rb") as f:
        image_bytes = f.read()
    image_after_b64 = base64.b64encode(image_bytes).decode("utf-8")

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[{"type": "text", "text": "Image 1 (Before cleanup) :."},
            {
                "type": "image",
                "data": image_before_b64,
                "mime_type": "image/jpeg"
            },
            {"type": "text", "text": "Image 2: (After cleanup) :"},
            {
                "type": "image",
                "data": image_after_b64,
                "mime_type": "image/jpeg"
            },
            {"type": "text", "text": prompt},
        ]
    )
    raw_text = interaction.output_text

    if not raw_text:
        raise ValueError("No output received from Gemini model.")

    return json.loads(raw_text.strip().removeprefix("```json").removesuffix("```").strip())  # Parse the JSON output from the model

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m app.services.audit_service <before_image> <after_image>")
        sys.exit(1)

    print("[*] Running Ghost-Resolution Audit via Gemini 3.8 Flash...")
    res = audit_resolution_images(sys.argv[1], sys.argv[2])
    print(json.dumps(res, indent=2))