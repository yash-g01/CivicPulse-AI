import os
import re
import json
from typing import Dict, Any
from ddgs import DDGS

from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _search_ddgs(query: str, max_results: int = 4) -> str:
    """Fetches web snippets using the new ddgs library without an API key."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                href = r.get("href", "")
                body = r.get("body", "")
                results.append(f"Title: {title}\nURL: {href}\nSnippet: {body}\n")
        return "\n---\n".join(results)
    except Exception as e:
        print(f"[DDGS Notice] Search fallback triggered: {e}")
        return ""

def discover_authority_via_web(city: str, state: str) -> Dict[str, Any]:
    """
    Discovers the official municipal grievance portal and email:
    1. Fetches web snippets via DDGS.
    2. Passes snippets to Gemini for structured JSON extraction.
    3. Falls back gracefully if external search is throttled.
    """
    search_query = f"{city} {state} municipal corporation solid waste complaint grievance portal official website"
    web_context = _search_ddgs(search_query)

    prompt = f"""
    You are an Indian civic administration intelligence agent.
    Identify the official Urban Local Body (Municipal Corporation / Nagar Nigam / Municipality)
    responsible for solid waste management and citizen grievances in {city}, {state}, India.

    {"Here are live web search results for reference:" if web_context else ""}
    {web_context}

    Extract and verify:
    1. corporation: Formal name (e.g. "Indore Municipal Corporation", "Lucknow Municipal Corporation").
    2. portal_url: Official grievance redressal web portal URL (prefer active .gov.in, .org, or official civic domain).
    3. nodal_email: Nodal grievance or commissioner email address.
    4. requires_otp: Whether citizen phone OTP/login is required to register complaints (boolean).
    5. jurisdiction: Formal urban administrative division.

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
        input=[{"type": "text", "text": prompt}]
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
        data = {
            "corporation": f"{city.title()} Municipal Corporation",
            "portal_url": f"https://{city.lower().replace(' ', '')}.gov.in",
            "nodal_email": f"commissioner@{city.lower().replace(' ', '')}.gov.in",
            "requires_otp": True,
            "jurisdiction": f"{city.title()} Urban Body"
        }

    return {
        "corporation": data.get("corporation", f"{city.title()} Municipal Corporation"),
        "portal_url": data.get("portal_url", f"https://{city.lower()}.gov.in"),
        "nodal_email": data.get("nodal_email", f"feedback@{city.lower()}.gov.in"),
        "requires_otp": bool(data.get("requires_otp", True)),
        "jurisdiction": data.get("jurisdiction", f"{city.title()} Urban Body"),
    }

if __name__ == "__main__":
    import sys
    test_city = sys.argv[1] if len(sys.argv) > 1 else "Lucknow"
    test_state = sys.argv[2] if len(sys.argv) > 2 else "Uttar Pradesh"
    print(f"[*] Discovering authority for {test_city}, {test_state} via ddgs + Gemini...")
    res = discover_authority_via_web(test_city, test_state)
    print(json.dumps(res, indent=2))