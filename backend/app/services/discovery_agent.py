import os
import re
import json
from typing import Dict, Any
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def discover_authority_via_web(city: str, state: str) -> Dict[str, Any]:
    """
    Surfs Google Search via Gemini to discover the official municipal
    corporation grievance portal and nodal authority email.
    """
    prompt = f"""
    Search Google and find the official Urban Local Body (Municipal Corporation, Nagar Nigam, or Municipality)
    responsible for public grievances and solid waste management in {city}, {state}, India.

    Find:
    1. Exact official name of the municipal body (e.g. "Lucknow Municipal Corporation", "Indore Municipal Corporation").
    2. Official citizen grievance/complaint redressal portal URL (must be the active official portal, e.g., ending in .gov.in or official municipal domain).
    3. Official nodal email address for public grievances, commissioner, or solid waste management.
    4. Whether citizen registration or phone OTP is typically required on this portal (boolean).
    5. Formal jurisdiction label.

    Output strictly raw valid JSON without markdown wrapping or backticks:
    {{
      "corporation": string,
      "portal_url": string,
      "nodal_email": string,
      "requires_otp": boolean,
      "jurisdiction": string
    }}
    """

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=[{"type": "text", "text": prompt}],
        tools=[{"type": "google_search"}]
    )
    raw_text = interaction.output_text or ""

    # Clean potential markdown wrapping
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```[a-zA-Z]*\n?", "", clean_text)
        clean_text = re.sub(r"\n?```$", "", clean_text).strip()

    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError:
        # Emergency structured fallback if the model response failed JSON formatting
        data = {
            "corporation": f"{city.title()} Municipal Corporation",
            "portal_url": f"https://{city.lower().replace(' ', '')}.gov.in",
            "nodal_email": f"commissioner@{city.lower().replace(' ', '')}.gov.in",
            "requires_otp": True,
            "jurisdiction": f"{city.title()} Urban Body"
        }

    return {
        "corporation": data.get("corporation", f"{city.title()} Municipal Corporation"),
        "portal_url": data.get("portal_url", ""),
        "nodal_email": data.get("nodal_email", ""),
        "requires_otp": bool(data.get("requires_otp", True)),
        "jurisdiction": data.get("jurisdiction", f"{city.title()} Municipality"),
    }