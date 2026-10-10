import os
import re
import json
import urllib.parse
from typing import Dict, Any, Optional
from ddgs import DDGS
from groq import Groq
from app.config import settings

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
    return Groq(api_key=api_key)

def _search_ddgs(query: str, max_results: int = 4) -> str:
    """Fetches web snippets using the ddgs library without an API key."""
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
    2. Passes snippets to Groq for ultra-fast structured JSON extraction.
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
    3. nodal_email: Official municipal grievance or commissioner email address.
    4. requires_otp: Whether citizen phone OTP/login is required to register complaints (boolean).
    5. jurisdiction: Formal urban administrative division.

    Output strictly raw valid JSON matching this schema:
    {{
      "corporation": string,
      "portal_url": string,
      "nodal_email": string,
      "requires_otp": boolean,
      "jurisdiction": string
    }}
    """

    raw_text = ""
    try:
        groq_client = _get_groq_client()
        chat_completion = groq_client.chat.completions.create(
            model=getattr(settings, "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw_text = chat_completion.choices[0].message.content or ""
    except Exception as e:
        print(f"[Discovery Agent Notice] Groq extraction note: {e}")

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

    portal_url = data.get("portal_url", f"https://{city.lower()}.gov.in").strip()
    # Clean any markdown links or parentheses
    portal_url = re.sub(r"[\[\]\(\)]", "", portal_url)

    nodal_email = data.get("nodal_email", f"feedback@{city.lower()}.gov.in").strip()

    return {
        "corporation": data.get("corporation", f"{city.title()} Municipal Corporation"),
        "portal_url": portal_url,
        "nodal_email": nodal_email,
        "requires_otp": bool(data.get("requires_otp", True)),
        "jurisdiction": data.get("jurisdiction", f"{city.title()} Urban Body"),
    }

def find_official_municipal_email(corporation: str, city: str, state: str = "") -> str:
    """
    Searches the web to find the official grievance / commissioner email
    for the specified municipal corporation.
    """
    search_query = f"{corporation} {city} municipal corporation grievance email commissioner email nodal officer contact"
    snippets = _search_ddgs(search_query, max_results=4)

    prompt = f"""
    Given the following search results for {corporation} in {city}, identify the official municipal
    email address for filing citizen grievances or contacting the Municipal Commissioner / Health Officer.
    
    Search snippets:
    {snippets}
    
    Output strictly raw JSON:
    {{"email": "official_email_address"}}
    If no specific email is found in the snippets, predict the most likely official domain email (e.g. commissioner@{city.lower().replace(' ', '')}.gov.in).
    """

    try:
        groq_client = _get_groq_client()
        res = groq_client.chat.completions.create(
            model=getattr(settings, "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        parsed = json.loads(res.choices[0].message.content or "{}")
        email = parsed.get("email", "").strip()
        if "@" in email:
            return email
    except Exception as e:
        print(f"[Email Discovery Notice] {e}")

    return f"commissioner@{city.lower().replace(' ', '')}.gov.in"

def draft_statutory_complaint_email(ticket_data: Dict[str, Any], recipient_email: str) -> Dict[str, str]:
    """
    Uses Groq to draft a formal, high-impact statutory civic complaint email
    and generates an RFC 6068 mailto: intent URI.
    Since mailto: does not support file attachments, embeds an AWS S3 presigned
    URL directly in the body for authorities to view the visual evidence.
    """
    corp_name = ticket_data.get("authority", {}).get("corporation") or "The Municipal Commissioner"
    landmark = ticket_data.get("landmark") or ticket_data.get("triage", {}).get("landmark_context") or "Public corridor"
    complaint_summary = ticket_data.get("complaint_text") or ticket_data.get("triage", {}).get("complaint_text") or "Accumulated unsegregated public waste"
    lat = ticket_data.get("lat", "")
    lng = ticket_data.get("lng", "")
    phone = ticket_data.get("user_phone", "")
    categories = ticket_data.get("triage", {}).get("waste_categories", [])
    severity = ticket_data.get("triage", {}).get("severity", 4)

    # Generate or fetch S3 presigned URL for the photographic evidence
    evidence_url = ticket_data.get("evidence_url", "")
    if not evidence_url and ticket_data.get("before_s3_key"):
        try:
            from app.core.s3 import generate_presigned_view_url
            evidence_url = generate_presigned_view_url(ticket_data["before_s3_key"])
        except Exception as ex:
            print(f"[Presigned URL Notice] {ex}")
    if not evidence_url and ticket_data.get("ticket_id"):
        try:
            from app.core.s3 import generate_presigned_view_url
            evidence_url = generate_presigned_view_url(f"evidence/{ticket_data['ticket_id']}_before.jpg")
        except Exception as ex:
            print(f"[Presigned URL Notice] {ex}")

    prompt = f"""
You are a public interest legal and civic advocacy expert.
Draft a formal, polite, yet legally authoritative statutory civic grievance email addressed to {corp_name}.
Context:
- Location Landmark: {landmark}
- GPS Coordinates: Latitude {lat}, Longitude {lng}
- Identified Waste: {', '.join(categories) if categories else 'Mixed solid refuse'}
- Severity Level: {severity}/5
- Public Health Hazard: {complaint_summary}
- Photographic Evidence (AWS S3 Presigned URL): {evidence_url if evidence_url else 'Available upon request'}
- Citizen Contact: {phone}
- Legal Citation: Solid Waste Management (SWM) Rules, 2016 and statutory public health provisions under Municipal Corporation Act.

Draft:
1. Subject line: High-priority, concise, specifying landmark and urgent action needed.
2. Body: Formal, respectful, detailing location coordinates, exact landmark features, public health hazards (pest breeding, sanitation breach), and requesting immediate field clearance and sanitary compliance report.
CRITICAL: Since the mailto: intent cannot attach files, you MUST explicitly include the Photographic Evidence AWS S3 Presigned URL ({evidence_url}) directly in the email body as verifiable visual evidence for the municipal officers.
End with citizen contact details.

Output strictly valid JSON:
{{
  "subject": "Clear subject line",
  "body": "Complete email body"
}}
"""

    subject = f"[STATUTORY GRIEVANCE] Urgent Public Waste Removal: {landmark}"
    evidence_line = (
        f"- Photographic Evidence (AWS S3 URL): {evidence_url}\n"
        f"  (Note: Visual evidence shared via secure S3 URL as mailto: intent does not support file attachments)\n"
    ) if evidence_url else ""
    body = (
        f"To,\nThe Municipal Commissioner / Competent Authority\n{corp_name}\n\n"
        f"SUBJECT: Urgent Statutory Grievance under Solid Waste Management Rules, 2016\n\n"
        f"Dear Sir/Madam,\n\n"
        f"I am writing to officially report an acute public health and sanitation hazard resulting from chronic "
        f"unsegregated waste accumulation at the following location:\n\n"
        f"- Landmark: {landmark}\n"
        f"- GPS Coordinates: Latitude {lat}, Longitude {lng}\n"
        f"{evidence_line}"
        f"- Hazard Description: {complaint_summary}\n\n"
        f"Note: Photographic proof is hosted at the secure S3 URL above for municipal inspection (mailto: intent cannot attach files).\n\n"
        f"Under the Solid Waste Management Rules, 2016, the Municipal Corporation is legally mandated to ensure "
        f"regular clearance of public areas and prevent open contamination.\n\n"
        f"Kindly dispatch the zonal sanitation team immediately and provide a resolution confirmation.\n\n"
        f"Citizen Contact: {phone}\n"
        f"Generated via CivicPulse AI Engine"
    )

    try:
        groq_client = _get_groq_client()
        for model_name in [getattr(settings, "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"), "openai/gpt-oss-20b"]:
            try:
                res = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                parsed = json.loads(res.choices[0].message.content or "{}")
                if parsed.get("subject") and parsed.get("body"):
                    subject = parsed["subject"]
                    body = parsed["body"]
                    # Ensure evidence URL is present in the LLM drafted body
                    if evidence_url and evidence_url not in body:
                        body += (
                            f"\n\nPhotographic Evidence (AWS S3 Presigned URL):\n{evidence_url}\n"
                            f"(Note: Visual evidence shared via secure AWS S3 bucket as mailto: intent does not allow file attachments)"
                        )
                    break
            except Exception as model_err:
                if "429" in str(model_err):
                    continue
                break
    except Exception as e:
        print(f"[Email Drafting Notice] {e}")

    # Construct standard mailto: URI with percent encoding
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body)
    mailto_url = f"mailto:{recipient_email}?subject={encoded_subject}&body={encoded_body}"

    return {
        "to": recipient_email,
        "subject": subject,
        "body": body,
        "mailto_url": mailto_url,
        "evidence_url": evidence_url,
    }

if __name__ == "__main__":
    import sys
    test_city = sys.argv[1] if len(sys.argv) > 1 else "Lucknow"
    test_state = sys.argv[2] if len(sys.argv) > 2 else "Uttar Pradesh"
    print(f"[*] Discovering authority for {test_city}, {test_state} via ddgs + Groq...")
    res = discover_authority_via_web(test_city, test_state)
    print(json.dumps(res, indent=2))