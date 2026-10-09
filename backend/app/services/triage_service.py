import os
import sys
import json
from google import genai
import base64


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def triage_waste_image(image_path: str) -> dict:
    prompt = """
    You are an environmental inspector and civic AI triage agent. Inspect this uploaded image.
    You must output ONLY raw valid JSON with no markdown wrapping and no backticks.

    Evaluation requirements:
    1. is_valid_waste: true if image shows roadside garbage, illegal dumping, overflowing public dumpsters, debris, or open burning. false if it is a meme, selfie, indoor room, or clean road.
    2. rejection_reason: null if valid; brief explanation string if invalid.
    3. waste_categories: array from ["plastic", "organic_food", "construction_debris", "dry_leaves", "e_waste", "biomedical"].
    4. severity: integer from 1 to 5 (1 = stray litter, 3 = overflowing bin obstructing path, 5 = massive illegal dumping/active fire/biohazard).
    5. landmark_context: key visual anchors (e.g., "adjacent to blue electrical transformer and boundary wall").
    6. complaint_text: a professional, formal 2-sentence complaint ready for official municipal portal submission citing health and obstruction risks.

    Schema:
    {
      "is_valid_waste": true,
      "rejection_reason": null,
      "waste_categories": ["plastic", "organic_food"],
      "severity": 4,
      "landmark_context": "near utility pole and brick wall",
      "complaint_text": "Chronic accumulation of unsegregated solid waste obstructing pedestrian passage. Poses immediate risk of vector-borne contamination."
    }
    """

    # Load image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "data": image_b64,
                "mime_type": "image/jpeg"
            }
        ]
    )
    raw_text = interaction.output_text

    if not raw_text:
        raise ValueError("No output received from Gemini model.")

    return json.loads(raw_text.strip().removeprefix("```json").removesuffix("```").strip())  # Parse the JSON output from the model

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.triage_service <path_to_image>")
        sys.exit(1)

    print(f"[*] Triaging {sys.argv[1]} via Gemini 3.8 Flash...")
    res = triage_waste_image(sys.argv[1])
    print(json.dumps(res, indent=2))