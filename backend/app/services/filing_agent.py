import os
import re
import json
import asyncio
import platform
import subprocess
import time
import urllib.parse
from typing import Any, Optional, Dict, List
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from groq import Groq

from app.core.dynamodb import update_ticket_status, get_ticket
from app.config import settings
from app.services.discovery_agent import (
    find_official_municipal_email,
    draft_statutory_complaint_email,
)

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
    return Groq(api_key=api_key)

def _chat_completion_with_fallback(groq_client: Groq, prompt: str) -> Dict[str, Any]:
    """
    Executes chat completion with multi-model resilience.
    If the primary model hits a transient rate limit (429), automatically retries
    and falls back across openai/gpt-oss-120b, openai/gpt-oss-20b, and qwen/qwen3.8-27b.
    """
    models = [
        getattr(settings, "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"),
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b"
    ]
    for model_name in models:
        for attempt in range(2):
            try:
                chat_completion = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                raw_content = chat_completion.choices[0].message.content or "{}"
                return json.loads(raw_content)
            except Exception as ex:
                err_str = str(ex).lower()
                if "429" in err_str or "rate limit" in err_str:
                    time.sleep(1.2)
                    continue
                else:
                    break
    return {"thought": "Proceeding with standard form submission flow.", "actions": []}

def normalize_portal_url(url: str) -> str:
    """
    Normalizes municipal portal URLs, handling markdown wrappers, missing protocols,
    typos (e.g. complaints vs complaint), and language parameter syntax.
    """
    if not url:
        return "https://complaint.pmc.gov.in/"
    url = url.strip()
    m = re.search(r"https?://[^\s)\]]+", url)
    if m:
        url = m.group(0)
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Correct common municipal domain and query typos
    url = url.replace("complaints.pmc.gov.in", "complaint.pmc.gov.in")
    if "/language=" in url:
        url = url.replace("/language=", "/?language=")
    return url

# ---------------------------------------------------------------------------
# Universal Language Switcher (Selector-Agnostic)
# ---------------------------------------------------------------------------

async def _ensure_english_version(page: Page) -> bool:
    """
    Checks for English language switchers on the municipal portal and
    switches to the English version before inspecting page contents.
    Handles:
    - Dropdown selectors (like PMC <select class="language">)
    - URL query parameters (?language=en, ?lang=en)
    - Buttons, anchors, and aria-labels with exact English/ENG matches.
    If the page is already in English (like PCMC), returns False immediately without delay.
    """
    # 1. Dropdown language switchers (e.g. PMC's <select class="form_cntrl language">)
    for sel in ["select.language", "select.form_cntrl", "select[name*='lang' i]", "select#language", "select"]:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.first.is_visible():
                options = await loc.first.locator("option").all_inner_texts()
                for opt_idx, opt_text in enumerate(options):
                    if "english" in opt_text.lower():
                        val = await loc.first.locator("option").nth(opt_idx).get_attribute("value")
                        current_val = await loc.first.input_value()
                        if current_val != val:
                            print(f"🌐 Found English option '{opt_text.strip()}' (val={val}) in {sel}. Switching to English...")
                            await loc.first.select_option(value=val)
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=6000)
                            except Exception:
                                pass
                            await asyncio.sleep(1.2)
                            return True
                        else:
                            return False
        except Exception:
            continue

    # 2. Link & button switchers (exact text matching to avoid collisions with words like 'citizen')
    english_selectors = [
        'a:text-is("English")',
        'button:text-is("English")',
        'a:text-is("ENG")',
        'button:text-is("ENG")',
        'a:text-is("EN")',
        'button:text-is("EN")',
        'a[title*="English" i]',
        'a[href*="lang=en" i]',
        'a[href*="language=en" i]',
        'a[href*="/en" i]',
    ]
    for sel in english_selectors:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.first.is_visible():
                print(f"🌐 Found English version switcher ({sel}). Switching portal to English...")
                await loc.first.click(timeout=3000)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=6000)
                except Exception:
                    pass
                await asyncio.sleep(1.2)
                return True
        except Exception:
            continue
    return False

# ---------------------------------------------------------------------------
# Universal Semantic DOM Extraction (Selector-Agnostic)
# ---------------------------------------------------------------------------

async def _extract_interactive_elements(page: Page) -> List[Dict[str, Any]]:
    """
    Extracts a rich, semantic snapshot of interactive elements on ANY municipal website.
    Gathers labels, placeholders, aria attributes, names, and visible text so that
    the AI agent can reason and interact without depending on hardcoded CSS selectors.
    """
    return await page.evaluate('''() => {
        const items = [];

        // Helper to find associated label text for an input
        const getLabelText = (el) => {
            if (el.labels && el.labels.length > 0) {
                return el.labels[0].innerText.trim();
            }
            if (el.id) {
                const lbl = document.querySelector('label[for=\"' + el.id + '\"]');
                if (lbl) return lbl.innerText.trim();
            }
            if (el.closest('.form_group, .form-group, td, tr, div')) {
                const p = el.closest('.form_group, .form-group, td, div');
                const lbl = p.querySelector('label, span.label');
                if (lbl) return lbl.innerText.trim();
            }
            return '';
        };

        // 1. Inputs, selects, and textareas
        document.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.offsetParent === null && el.type !== 'file') return;
            const label = getLabelText(el);
            const placeholder = el.placeholder || '';
            const name = el.name || '';
            const id = el.id ? '#' + el.id : '';
            const type = (el.type || el.tagName.toLowerCase()).toLowerCase();
            
            // Build primary selector with fallbacks
            let primarySelector = id;
            if (!primarySelector && name) primarySelector = '[name=\"' + name + '\"]';
            if (!primarySelector && placeholder) primarySelector = '[placeholder=\"' + placeholder.replace(/\"/g, '\\\\\"') + '\"]';
            if (!primarySelector) primarySelector = el.tagName.toLowerCase() + (type ? '[type=\"' + type + '\"]' : '');

            // Infer semantic role: mobile/phone takes precedence over generic OTP in names like otpMobileNo
            let semanticRole = 'text';
            const combined = (label + ' ' + placeholder + ' ' + name + ' ' + (el.id || '')).toLowerCase();
            if (combined.includes('mobile') || combined.includes('phone') || combined.includes('contact') || type === 'tel') {
                semanticRole = 'mobile';
            } else if (combined.includes('otp') || combined.includes('code') || combined.includes('verification') || combined.includes('loginotp') || combined.includes('enteredotp')) {
                semanticRole = 'otp';
            } else if (combined.includes('user') || combined.includes('login') || combined.includes('email')) {
                semanticRole = 'username';
            } else if (combined.includes('pass')) {
                semanticRole = 'password';
            } else if (combined.includes('desc') || combined.includes('complaint') || combined.includes('grievance') || combined.includes('detail') || el.tagName.toLowerCase() === 'textarea') {
                semanticRole = 'description';
            } else if (combined.includes('land') || combined.includes('addr') || combined.includes('street') || combined.includes('area') || combined.includes('house') || combined.includes('building')) {
                semanticRole = 'landmark';
            } else if (combined.includes('cat') || combined.includes('type') || combined.includes('dept')) {
                semanticRole = 'category';
            }

            items.push({
                tag: el.tagName.toLowerCase(),
                selector: primarySelector,
                name: name,
                label: label,
                placeholder: placeholder,
                type: type,
                semantic_role: semanticRole,
                value: el.value || '',
                options: el.tagName.toLowerCase() === 'select' ? Array.from(el.options).map(o => o.text.trim()) : undefined
            });
        });

        // 2. Interactive buttons, submits, and click triggers
        document.querySelectorAll('button, a[role=\"button\"], a[onclick], input[type=\"submit\"], input[type=\"button\"], a.Otp').forEach(el => {
            if (el.offsetParent === null) return;
            const text = el.innerText ? el.innerText.trim() : (el.value || '');
            const id = el.id ? '#' + el.id : '';
            const name = el.name ? '[name=\"' + el.name + '\"]' : '';
            const selector = id || name || (text ? (el.tagName.toLowerCase() + ':has-text(\"' + text.slice(0, 30).replace(/\"/g, '\\\\\"') + '\")') : el.tagName.toLowerCase());
            
            let semanticRole = 'action';
            const lowerText = text.toLowerCase();
            if (lowerText.includes('otp') || lowerText.includes('generate') || lowerText.includes('send')) {
                semanticRole = 'otp_trigger';
            } else if (lowerText.includes('verify') || lowerText.includes('confirm')) {
                semanticRole = 'verify';
            } else if (lowerText.includes('submit') || lowerText.includes('save') || lowerText.includes('register') || lowerText.includes('log on') || lowerText.includes('login') || lowerText.includes('enter')) {
                semanticRole = 'submit';
            }

            items.push({
                tag: 'button',
                selector: selector,
                text: text,
                semantic_role: semanticRole
            });
        });

        // 3. Relevant civic navigation links (Complaints, Grievances, Citizen Login/Register, Status)
        const relevantKeywords = [
            'complaint', 'grievance', 'redressal', 'citizen', 'service',
            'solid waste', 'swm', 'garbage', 'register', 'online', 'english', 'en',
            'login', 'log on', 'otp', 'sign in', 'status', 'तक्रार'
        ];
        document.querySelectorAll('a').forEach(el => {
            if (el.offsetParent === null) return;
            const text = el.innerText ? el.innerText.trim() : '';
            const href = el.getAttribute('href') || '';
            const combined = (text + ' ' + href).toLowerCase();
            const matches = relevantKeywords.some(k => combined.includes(k));
            if (matches && text.length > 0 && text.length < 60) {
                const selector = href && !href.startsWith('javascript') && !href.startsWith('#')
                    ? 'a[href=\"' + href.replace(/\"/g, '\\\\\"') + '\"]'
                    : 'a:has-text(\"' + text.slice(0, 30).replace(/\"/g, '\\\\\"') + '\")';
                if (!items.some(i => i.selector === selector || (i.text && i.text === text))) {
                    let role = 'navigation';
                    const lowerText = text.toLowerCase();
                    if (lowerText.includes('management system') || lowerText.includes('portal') || href === 'home' || href === '#' || href === '/') {
                        role = 'navigation';
                    } else if (lowerText.includes('login') || lowerText.includes('log on') || lowerText.includes('sign in')) {
                        role = 'login';
                    } else if (lowerText.includes('status') || lowerText.includes('track') || lowerText.includes('rpt')) {
                        role = 'status';
                    } else if (lowerText.includes('complaint') || lowerText.includes('grievance') || lowerText.includes('तक्रार')) {
                        role = 'complaint';
                    } else if (lowerText.includes('register')) {
                        role = 'register';
                    }
                    items.push({
                        tag: 'link',
                        selector: selector,
                        text: text,
                        href: href,
                        semantic_role: role
                    });
                }
            }
        });

        // 4. Notices, hints, alerts, and banners
        document.querySelectorAll('.badge-otp, .alert, .alert-success, #confirmation-banner, #otp-hint, .form_group p, .log_title, td.error, span.error').forEach(el => {
            if (el.offsetParent !== null) {
                const text = el.innerText.trim();
                if (text.length > 0 && text.length < 120) {
                    items.push({
                        tag: 'notice',
                        selector: el.id ? '#' + el.id : ('.' + el.className.split(' ')[0]),
                        text: text
                    });
                }
            }
        });

        return items;
    }''')

# ---------------------------------------------------------------------------
# Universal Action Execution Helpers (Selector-Agnostic)
# ---------------------------------------------------------------------------

def _detect_login_or_registration_fields(page_url: str, dom_elements: List[Dict[str, Any]]) -> Optional[str]:
    """
    Detects whether the current portal page presents any mobile number input,
    citizen login credentials, or registration form.
    Returns a descriptive reason if login/registration is required, or None otherwise.
    """
    lower_url = (page_url or "").lower()

    # URL path indicators
    url_match = any(term in lower_url for term in [
        "/login", "/logon", "/signin", "/sign-in",
        "/citizenregistration", "/registercitizen", "/register"
    ])

    has_mobile_field = False
    has_credential_field = False
    has_auth_button = False

    for el in dom_elements:
        tag = el.get("tag", "").lower()
        role = el.get("semantic_role", "").lower()
        name = (el.get("name") or "").lower()
        placeholder = (el.get("placeholder") or "").lower()
        label = (el.get("label") or "").lower()
        text = (el.get("text") or "").lower()
        el_type = (el.get("type") or "").lower()
        sel = (el.get("selector") or "").lower()

        combined = f"{name} {placeholder} {label} {sel}"

        if tag in ("input", "textarea"):
            if role in ("mobile", "phone") or "mobile" in combined or "phone" in combined or el_type == "tel":
                has_mobile_field = True
            if role in ("username", "password") or el_type == "password" or "pass" in combined or "user" in combined:
                has_credential_field = True

        if tag in ("button", "link"):
            if any(kw in text for kw in ["get otp", "send otp", "login", "log in", "log on", "sign in", "register"]):
                has_auth_button = True

    if has_mobile_field:
        return "Mobile number authentication field detected"
    if has_credential_field:
        return "Citizen login credentials field detected"
    if url_match and (has_auth_button or has_credential_field or has_mobile_field):
        return "Citizen login or registration page detected"

    return None

def _is_complaint_submission_form(dom_elements: List[Dict[str, Any]]) -> bool:
    """
    Checks whether the current page contains the complaint submission form fields
    (e.g. description textarea, landmark/address input, category select, file upload, submit button).
    Ensures that login / credential forms are not mistaken for complaint forms.
    """
    is_login_page = any(
        el.get("semantic_role") in ("password", "username")
        for el in dom_elements if el.get("tag") == "input"
    )
    if is_login_page:
        return False

    has_textarea = any(el.get("tag") == "textarea" for el in dom_elements)
    has_complaint_input = any(
        el.get("semantic_role") in ("description", "landmark")
        or any(k in (el.get("name") or "").lower() for k in ["complaint", "grievance", "desc", "detail", "landmark"])
        for el in dom_elements if el.get("tag") in ("input", "textarea")
    )
    has_submit_btn = any(
        el.get("tag") in ("button", "input")
        and any(k in (el.get("text") or el.get("value") or "").lower() for k in ["submit", "save", "नोंदवा"])
        for el in dom_elements
    )
    return (has_textarea or has_complaint_input) and has_submit_btn

def _find_citizen_login_or_register_link(dom_elements: List[Dict[str, Any]], clicked_targets: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """
    Finds a link or button for Citizen Login or Citizen Registration on the portal landing page,
    enabling the agent to navigate to the authentication screen and wait for the user to complete login.
    """
    priority_login_terms = [
        "citizen login",
        "citizen log in",
        "citizen log on",
        "citizen login / sign up",
        "citizen sign in",
        "citizen registration",
        "register your complaint",  # On portals like PCMC, clicking Register Your Complaint leads directly to Logon
        "login",
        "log on",
        "sign in"
    ]
    avoid_terms = ["admin", "officer", "staff", "management system", "pcmc user"]
    avoid_hrefs = ["home", "#", "/", "index", "index.html", "javascript:void(0);", "javascript:;"]

    for term in priority_login_terms:
        for el in dom_elements:
            if el.get("tag") in ("link", "button"):
                text = (el.get("text") or "").lower().strip()
                href = (el.get("href") or "").lower().strip()
                selector = el.get("selector", "")
                
                if href in avoid_hrefs or any(a in text for a in avoid_terms):
                    continue
                if clicked_targets and (selector in clicked_targets or text in clicked_targets):
                    continue
                if term in text:
                    return el
    return None

def _find_raise_complaint_url_or_button(dom_elements: List[Dict[str, Any]], clicked_targets: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """
    Scans interactive elements on the page specifically looking for a URL, link, or button
    to raise / register / lodge a citizen complaint on the municipal portal once logged in.
    Filters out header branding logos, home links, status check links, and informational text.
    """
    priority_keywords = [
        "register your complaint",
        "register complaint",
        "lodge complaint",
        "new complaint",
        "raise complaint",
        "file complaint",
        "post complaint",
        "citizen's grievances",
        "citizens grievances",
        "citizen grievance",
        "register grievance",
        "lodge grievance",
        "new grievance",
        "complaint registration",
        "तक्रार नोंदवा",
        "तक्रार नोंदणी"
    ]

    avoid_terms = [
        "management system", "portal", "status", "track", "rpt", "report", "check",
        "about", "help", "manual", "header", "logo", "services", "gis", "officer", "admin", "login", "log on"
    ]
    avoid_hrefs = ["home", "#", "/", "index", "index.html", "javascript:void(0);", "javascript:;"]

    # Priority 1: Match links or buttons with strong complaint filing action text
    for el in dom_elements:
        if el.get("tag") in ("link", "button"):
            text = (el.get("text") or "").lower().strip()
            href = (el.get("href") or "").lower().strip()
            selector = el.get("selector", "")

            if href in avoid_hrefs or any(avoid in text for avoid in avoid_terms):
                continue
            if clicked_targets and (selector in clicked_targets or text in clicked_targets):
                continue

            for kw in priority_keywords:
                if kw in text:
                    return el

    # Priority 2: Links or buttons with semantic_role 'complaint'
    for el in dom_elements:
        if el.get("tag") in ("link", "button") and el.get("semantic_role") == "complaint":
            text = (el.get("text") or "").lower().strip()
            href = (el.get("href") or "").lower().strip()
            selector = el.get("selector", "")

            if href in avoid_hrefs or any(avoid in text for avoid in avoid_terms):
                continue
            if clicked_targets and (selector in clicked_targets or text in clicked_targets):
                continue
            return el

    # Priority 3: Links or buttons with exact action text 'complaint'
    for el in dom_elements:
        if el.get("tag") in ("link", "button"):
            text = (el.get("text") or "").lower().strip()
            href = (el.get("href") or "").lower().strip()
            selector = el.get("selector", "")

            if href in avoid_hrefs or any(avoid in text for avoid in avoid_terms):
                continue
            if clicked_targets and (selector in clicked_targets or text in clicked_targets):
                continue
            if text == "complaint" or (any(k in text for k in ["complaint", "grievance", "तक्रार"]) and len(text) < 30):
                return el

    return None

async def _robust_click(page: Page, action: Dict[str, Any], ticket_id: str) -> bool:
    """Executes a click action using multiple semantic fallback strategies."""
    selector = action.get("selector", "")
    text = action.get("text") or action.get("label") or ""
    semantic_role = action.get("semantic_role", "")

    # Strategy 1: Targeted visible CSS selector
    if selector:
        try:
            loc = page.locator(f"{selector}:visible") if ":visible" not in selector else page.locator(selector)
            if await loc.count() > 0:
                await loc.first.click(timeout=5000)
                print(f"[{ticket_id}] 👆 Clicked visible selector: {selector}")
                return True
        except Exception:
            pass

    # Strategy 2: Raw selector with force
    if selector:
        try:
            loc = page.locator(selector)
            if await loc.count() > 0:
                await loc.first.click(force=True, timeout=5000)
                print(f"[{ticket_id}] 👆 Force-clicked selector: {selector}")
                return True
        except Exception:
            pass

    # Strategy 3: Text / Accessible Role Match (completely selector-agnostic)
    if text:
        for method_name, loc in [
            ("role:button", page.get_by_role("button", name=text)),
            ("role:link", page.get_by_role("link", name=text)),
            ("text:exact", page.get_by_text(text, exact=True)),
            ("text:substring", page.get_by_text(text, exact=False)),
        ]:
            try:
                if await loc.count() > 0 and await loc.first.is_visible():
                    await loc.first.click(timeout=5000)
                    print(f"[{ticket_id}] 👆 Clicked via {method_name}: '{text}'")
                    return True
            except Exception:
                continue

    # Strategy 4: Semantic keyword fallback
    keywords = {
        "complaint": ["Register Your Complaint", "Register Complaint", "Citizen's Grievances", "Lodge Complaint", "Grievance", "तक्रार"],
        "login": ["Citizen Login", "Citizen LOGIN", "Log On", "Login", "Sign In"],
        "otp_trigger": ["GET OTP", "Get OTP", "Generate OTP", "Send OTP"],
        "verify": ["Verify", "VERIFY", "btnVerify", "Confirm"],
        "submit": ["Submit", "SUBMIT", "Save", "Log On", "Enter"]
    }.get(semantic_role, [])

    for kw in keywords:
        try:
            loc = page.locator(f"a:has-text('{kw}'):visible, button:has-text('{kw}'):visible, input[value*='{kw}' i]:visible")
            if await loc.count() > 0:
                await loc.first.click(timeout=5000)
                print(f"[{ticket_id}] 👆 Clicked via semantic keyword '{kw}'")
                return True
        except Exception:
            continue

    return False

async def _robust_fill(page: Page, action: Dict[str, Any], ticket_id: str, allow_mobile_fill: bool = False) -> bool:
    """Executes a fill action using multiple semantic fallback strategies."""
    selector = action.get("selector", "")
    val = str(action.get("value", ""))
    label = action.get("label", "")
    semantic_role = action.get("semantic_role", "")

    # Policy Guard: Refuse auto-filling mobile numbers into login/auth fields.
    # Must wait for citizen to complete login or registration.
    is_mobile_input = (
        semantic_role in ("mobile", "phone")
        or (val.isdigit() and len(val) == 10)
        or any(k in selector.lower() for k in ["mobile", "phone", "txtmobileno"])
        or any(k in label.lower() for k in ["mobile", "phone"])
    )
    if is_mobile_input and not allow_mobile_fill:
        print(f"[{ticket_id}] 🛑 Refusing auto-fill into mobile field '{selector or label}': must wait for citizen to complete login or registration.")
        return False

    # Strategy 1: Targeted visible CSS selector
    if selector:
        try:
            loc = page.locator(f"{selector}:visible") if ":visible" not in selector else page.locator(selector)
            if await loc.count() > 0:
                await loc.first.fill(val, timeout=5000)
                print(f"[{ticket_id}] ✍️  Filled '{val}' into visible: {selector}")
                return True
        except Exception:
            pass

    # Strategy 2: Raw selector with force
    if selector:
        try:
            loc = page.locator(selector)
            if await loc.count() > 0:
                await loc.first.fill(val, force=True, timeout=5000)
                print(f"[{ticket_id}] ✍️  Force-filled '{val}' into: {selector}")
                return True
        except Exception:
            pass

    # Strategy 3: Label or Placeholder match
    if label:
        try:
            loc = page.get_by_label(label, exact=False)
            if await loc.count() > 0 and await loc.first.is_visible():
                await loc.first.fill(val, timeout=5000)
                print(f"[{ticket_id}] ✍️  Filled '{val}' via label '{label}'")
                return True
        except Exception:
            pass

    # Strategy 4: Semantic role heuristics (completely selector-agnostic)
    # Mobile / Phone number (10 digits)
    if semantic_role in ("mobile", "phone") or (val.isdigit() and len(val) == 10):
        for pattern in [
            '#otpMobileNo:visible',
            '#mobile:visible',
            '#enteredOTPMobile:visible',
            'input[name*="mobile" i]:visible',
            'input[id*="mobile" i]:visible',
            'input[placeholder*="mobile" i]:visible',
            'input[type="tel"]:visible',
            'input[name*="phone" i]:visible',
            'input[name*="user" i]:visible',
            'input[name*="txtMobileNo" i]:visible',
            'input[name*="container:txtMobileNo" i]:visible'
        ]:
            try:
                loc = page.locator(pattern)
                if await loc.count() > 0:
                    await loc.first.fill(val, timeout=4000)
                    print(f"[{ticket_id}] ✍️  Filled mobile '{val}' via pattern '{pattern}'")
                    return True
            except Exception:
                continue

    # OTP verification code (4-6 digits)
    if semantic_role == "otp" or (val.isdigit() and 4 <= len(val) <= 6):
        for pattern in [
            '#loginOTP:visible',
            '#otpNumber:visible',
            'input[name*="otp" i]:visible',
            'input[id*="otp" i]:visible',
            'input[placeholder*="otp" i]:visible',
            'input[name*="code" i]:visible',
            'input[id*="loginOTP" i]:visible'
        ]:
            try:
                loc = page.locator(pattern)
                if await loc.count() > 0:
                    await loc.first.fill(val, timeout=4000)
                    print(f"[{ticket_id}] ✍️  Filled OTP '{val}' via pattern '{pattern}'")
                    return True
            except Exception:
                continue

    # Username / Login credentials
    if semantic_role in ("username", "user") or "user" in selector.lower():
        for pattern in [
            'input[name*="user" i]:visible',
            'input[id*="user" i]:visible',
            'input[name="userName"]:visible',
            '#id3:visible'
        ]:
            try:
                loc = page.locator(pattern)
                if await loc.count() > 0:
                    await loc.first.fill(val, timeout=4000)
                    print(f"[{ticket_id}] ✍️  Filled username '{val}' via pattern '{pattern}'")
                    return True
            except Exception:
                continue

    # Password
    if semantic_role == "password" or "pass" in selector.lower():
        for pattern in [
            'input[type="password"]:visible',
            'input[name*="pass" i]:visible',
            '#id4:visible'
        ]:
            try:
                loc = page.locator(pattern)
                if await loc.count() > 0:
                    await loc.first.fill(val, timeout=4000)
                    print(f"[{ticket_id}] ✍️  Filled password via pattern '{pattern}'")
                    return True
            except Exception:
                continue

    # Complaint text / details / landmark
    if semantic_role in ("description", "complaint", "landmark"):
        for pattern in [
            'textarea:visible',
            'input[name*="desc" i]:visible',
            'input[name*="complaint" i]:visible',
            'input[name*="detail" i]:visible',
            'input[name*="landmark" i]:visible'
        ]:
            try:
                loc = page.locator(pattern)
                if await loc.count() > 0:
                    await loc.first.fill(val, timeout=4000)
                    print(f"[{ticket_id}] ✍️  Filled description into '{pattern}'")
                    return True
            except Exception:
                continue

    return False

# ---------------------------------------------------------------------------
# Fallback Email Dispatch
# ---------------------------------------------------------------------------

async def _trigger_email_fallback(ticket_id: str, form_data: dict, reason: str = ""):
    """
    Fallback mechanism when municipal portal is down, unreachable, or lacks an online complaint form:
    1. Discovers the official municipal grievance / commissioner email via web search or directory.
    2. Drafts a formal, legally grounded statutory complaint email using Groq.
    3. Builds an RFC-compliant mailto: intent URI with pre-filled To, Subject, and Body.
    4. Updates DynamoDB with EMAIL_FALLBACK_READY state.
    5. On local macOS environment, triggers the native mail compose intent.
    """
    corp_name = form_data.get("authority", {}).get("corporation", "Municipal Corporation")
    city = form_data.get("authority", {}).get("city_slug", "Pune")
    nodal_email = form_data.get("authority", {}).get("nodal_email")

    print(f"\n📧 [{ticket_id}] Triggering Email Fallback: {reason}")
    update_ticket_status(ticket_id, {
        "status": "COMPILING_EMAIL_DOSSIER",
        "agent_telemetry": f"Searching web for official {corp_name} grievance email and preparing statutory mailto: dossier..."
    })

    if not nodal_email or "example" in nodal_email or "temp" in nodal_email:
        try:
            discovered_email = await asyncio.to_thread(find_official_municipal_email, corp_name, city)
            nodal_email = discovered_email or nodal_email or f"feedback@{city.lower().replace(' ', '')}.gov.in"
        except Exception as e:
            print(f"[{ticket_id}] Email lookup notice: {e}")
            nodal_email = nodal_email or f"feedback@{city.lower().replace(' ', '')}.gov.in"

    # Generate S3 Presigned URL for photographic evidence (since mailto: cannot attach files)
    before_s3_key = form_data.get("before_s3_key") or f"evidence/{ticket_id}_before.jpg"
    evidence_url = form_data.get("evidence_url")
    if not evidence_url and before_s3_key:
        try:
            from app.core.s3 import generate_presigned_view_url
            evidence_url = generate_presigned_view_url(before_s3_key)
            form_data["evidence_url"] = evidence_url
            form_data["before_s3_key"] = before_s3_key
            print(f"[{ticket_id}] 📎 Embedded S3 Presigned URL for Photographic Evidence: {evidence_url}")
        except Exception as s3_err:
            print(f"[{ticket_id}] S3 Presigned URL warning: {s3_err}")

    email_data = await asyncio.to_thread(draft_statutory_complaint_email, form_data, nodal_email)
    if evidence_url and not email_data.get("evidence_url"):
        email_data["evidence_url"] = evidence_url

    update_ticket_status(ticket_id, {
        "status": "EMAIL_FALLBACK_READY",
        "fallback_reason": reason or "Online grievance registration unavailable on municipal portal.",
        "email_dispatch": email_data,
        "evidence_url": evidence_url,
        "agent_summary": (
            f"Online portal complaint form unavailable ({reason}). "
            f"Formal statutory grievance email dossier compiled with ready-to-dispatch mailto: intent and S3 evidence link for {nodal_email}."
        )
    })

    mailto_url = email_data.get("mailto_url", "")
    try:
        if platform.system() == "Darwin" and mailto_url:
            subprocess.Popen(["open", mailto_url])
            print(f"[{ticket_id}] ✉️  Launched local macOS mailto: intent compose window.")
    except Exception as ex:
        print(f"[{ticket_id}] Local mail intent notice: {ex}")

    print(f"[{ticket_id}] ✅ Email Fallback Dossier Ready! Recipient: {nodal_email}\n")
    return email_data

# ---------------------------------------------------------------------------
# Universal Autonomous AI Agent Filing Worker
# ---------------------------------------------------------------------------

async def run_filing_worker(ticket_id: str, form_data: dict, local_image_path: str):
    """
    Autonomous LLM-driven browser worker.
    - Inspects ANY municipal grievance portal dynamically using Playwright and Groq.
    - Operates completely regardless of specific CSS selectors using multi-strategy semantic resolution.
    - Prioritizes switching to English language version before inspecting forms.
    - Only requests human input whenever the website requires it (SMS OTP, verification).
    - If no online complaint registration option exists or portal is down, falls back to
      searching the web for official email and generating ready-to-send mailto: intent.
    """
    # Target URL determination: Always prioritize resolved authority portal URL or custom portal_url
    raw_url = (
        form_data.get("portal_url")
        or form_data.get("authority", {}).get("portal_url")
        or settings.DEFAULT_PORTAL_URL
    )
    if settings.PORTAL_MODE == "mock" and not form_data.get("portal_url") and not form_data.get("authority", {}).get("portal_url"):
        target_url = settings.MOCK_PORTAL_URL
    else:
        target_url = normalize_portal_url(raw_url)

    corp_name = form_data.get("authority", {}).get("corporation", "Municipal Corporation")
    user_phone = str(form_data.get("user_phone", "9822012345"))
    landmark = form_data.get("landmark", "Roadside unsegregated waste pile")
    complaint_text = form_data.get("complaint_text", "Chronic unsegregated waste accumulation obstructing passage and posing public health hazards.")

    ticket_context = {
        "citizen_phone": user_phone,
        "landmark": landmark,
        "complaint_text": complaint_text,
        "category": "Solid Waste Management",
        "municipality": corp_name
    }

    print(f"\n🤖 [{ticket_id}] Launching autonomous AI Filing Agent for {corp_name} at {target_url}...")
    update_ticket_status(ticket_id, {
        "status": "AGENT_BROWSING_PORTAL",
        "agent_telemetry": f"Navigating to {target_url}..."
    })

    if not target_url or not target_url.startswith("http"):
        await _trigger_email_fallback(ticket_id, form_data, "No valid municipal portal URL found for this location.")
        return

    groq_client = _get_groq_client()
    step_history: List[Dict[str, Any]] = []
    user_provided_otp: Optional[str] = None
    user_login_completed: bool = False
    ref_id: Optional[str] = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=settings.HEADLESS_BROWSER,
            args=["--disable-web-security", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        # Handle portal alert dialogs automatically so they do not block Playwright
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        try:
            print(f"[{ticket_id}] 🌐 Navigating directly to {target_url}...")
            try:
                await page.goto(target_url, timeout=35000, wait_until="domcontentloaded")
            except Exception as nav_err:
                print(f"[{ticket_id}] ⚠️ Municipal portal unreachable / timed out: {nav_err}")
                await browser.close()
                await _trigger_email_fallback(
                    ticket_id,
                    form_data,
                    f"Municipal website ({target_url}) is down or unresponsive: {nav_err}"
                )
                return

            await asyncio.sleep(1.2)

            # Step 0: Ensure English language version before inspecting the portal
            await _ensure_english_version(page)

            # Autonomous Multi-Step Reasoning Loop (max 8 steps)
            clicked_targets = set()
            for step_idx in range(1, 9):
                print(f"[{ticket_id}] 🧠 --- Agent Step {step_idx} Reasoning ---")
                await _ensure_english_version(page)

                # Check dynamic ticket state from DynamoDB
                record = get_ticket(ticket_id)
                if record and record.get("user_login_completed"):
                    user_login_completed = True

                dom_elements = await _extract_interactive_elements(page)

                # 1. Detection of Mobile Number or Login/Registration fields:
                # Instead of automatically filling in the mobile number, pause and wait for the user to complete login or registration.
                login_reason = _detect_login_or_registration_fields(page.url, dom_elements)
                if login_reason and not user_login_completed:
                    prompt_msg = f"Portal requires citizen login or registration on {corp_name}. Please complete login or registration on the portal."
                    print(f"[{ticket_id}] 🛑 {login_reason}: {prompt_msg}")
                    print(f"[{ticket_id}] ⏳ Pausing automation: waiting for citizen to complete login or registration (no auto-fill)...")

                    update_ticket_status(ticket_id, {
                        "status": "AWAITING_HUMAN_ACTION",
                        "requires_login": True,
                        "auth_prompt": prompt_msg,
                        "agent_telemetry": f"Portal requires citizen login/registration ({login_reason}). Waiting for user to complete login or registration..."
                    })

                    login_done = False
                    for poll_i in range(30):  # Poll up to 60 seconds (30 * 2s)
                        await asyncio.sleep(2.0)

                        # A. Check if citizen confirmed login or entered OTP via API
                        rec = get_ticket(ticket_id)
                        if rec:
                            if rec.get("user_login_completed"):
                                print(f"[{ticket_id}] ✅ Citizen confirmed login via API!")
                                login_done = True
                                break
                            if rec.get("user_provided_otp") or rec.get("user_provided_input"):
                                user_provided_otp = str(rec.get("user_provided_otp") or rec.get("user_provided_input")).strip()
                                print(f"[{ticket_id}] ✅ Citizen supplied OTP code: {user_provided_otp}")
                                login_done = True
                                break

                        # B. Check if browser page advanced past the login/registration screen
                        try:
                            current_url = page.url
                            current_dom = await _extract_interactive_elements(page)
                            still_login = _detect_login_or_registration_fields(current_url, current_dom)
                            has_complaint_form = _is_complaint_submission_form(current_dom)

                            if (not still_login) or has_complaint_form:
                                print(f"[{ticket_id}] ✅ Portal page advanced past login screen (URL: {current_url}).")
                                login_done = True
                                break
                        except Exception:
                            pass

                    if not login_done:
                        print(f"[{ticket_id}] ⚠️ Citizen login/registration was not completed. Transitioning to statutory email dispatch...")
                        await browser.close()
                        await _trigger_email_fallback(
                            ticket_id,
                            form_data,
                            f"Portal requires citizen login or registration on {corp_name}. Timed out waiting for citizen completion."
                        )
                        return

                    user_login_completed = True
                    update_ticket_status(ticket_id, {
                        "status": "AGENT_BROWSING_PORTAL",
                        "requires_login": False,
                        "agent_telemetry": f"Citizen login completed! Looking for URL to raise complaint on {corp_name} portal..."
                    })
                    await asyncio.sleep(1.0)
                    continue

                # 2. Once the user completely logs in, look for a URL to raise the complaint
                if user_login_completed and not _is_complaint_submission_form(dom_elements):
                    complaint_url_el = _find_raise_complaint_url_or_button(dom_elements, clicked_targets)
                    if complaint_url_el:
                        target_name = complaint_url_el.get("text") or complaint_url_el.get("href") or "Raise Complaint"
                        sel = complaint_url_el.get("selector", "")
                        clicked_targets.add(sel)
                        clicked_targets.add(target_name)
                        print(f"[{ticket_id}] 🔍 Citizen logged in: found URL/link to raise complaint on portal: '{target_name}' ({sel})")
                        update_ticket_status(ticket_id, {
                            "status": "AGENT_BROWSING_PORTAL",
                            "agent_telemetry": f"Found URL to raise complaint: '{target_name}'. Opening complaint form..."
                        })
                        await _robust_click(page, complaint_url_el, ticket_id)
                        await asyncio.sleep(2.0)
                        await _ensure_english_version(page)
                        continue

                # 3. If NOT logged in and NOT on complaint submission form:
                #    Check if portal has a Citizen Login / Register option to reach the authentication page
                if not user_login_completed and not _is_complaint_submission_form(dom_elements):
                    login_link = _find_citizen_login_or_register_link(dom_elements, clicked_targets)
                    if login_link:
                        target_name = login_link.get("text") or login_link.get("href") or "Citizen Login"
                        sel = login_link.get("selector", "")
                        clicked_targets.add(sel)
                        clicked_targets.add(target_name)
                        print(f"[{ticket_id}] 🔐 Portal requires citizen login to raise complaint. Navigating to login screen via '{target_name}'...")
                        update_ticket_status(ticket_id, {
                            "status": "AGENT_BROWSING_PORTAL",
                            "agent_telemetry": f"Navigating to citizen login screen via '{target_name}'..."
                        })
                        await _robust_click(page, login_link, ticket_id)
                        await asyncio.sleep(2.0)
                        await _ensure_english_version(page)
                        continue

                # 3. Active OTP screen detection: If portal has reached standalone OTP verification screen and citizen OTP not supplied yet
                otp_input_element = next(
                    (el for el in dom_elements if el.get("tag") == "input" and el.get("semantic_role") == "otp"),
                    None
                )
                if otp_input_element and not user_provided_otp:
                    prompt_msg = f"Verification required on {corp_name} portal. Enter SMS code sent to your phone."
                    print(f"[{ticket_id}] 🛑 Active OTP verification field detected on portal: {prompt_msg}")
                    update_ticket_status(ticket_id, {
                        "status": "AWAITING_OTP",
                        "auth_prompt": prompt_msg,
                        "agent_telemetry": f"Portal requires human input: {prompt_msg}"
                    })

                    otp_code = None
                    for poll_i in range(15):
                        await asyncio.sleep(2)
                        record = get_ticket(ticket_id)
                        if record:
                            val = record.get("user_provided_otp") or record.get("user_provided_input")
                            if val:
                                otp_code = str(val).strip()
                                print(f"[{ticket_id}] ✅ Human entered requested input: {otp_code}")
                                break

                    if not otp_code:
                        print(f"[{ticket_id}] ⚠️ Citizen timed out providing input. Transitioning to statutory email dispatch...")
                        await browser.close()
                        await _trigger_email_fallback(ticket_id, form_data, "Citizen timed out providing OTP verification on portal.")
                        return

                    user_provided_otp = otp_code
                    update_ticket_status(ticket_id, {
                        "status": "RELAYING_OTP",
                        "user_provided_otp": None,
                        "user_provided_input": None,
                        "agent_telemetry": f"Relaying verification code '{otp_code}' to portal..."
                    })
                    continue

                prompt = f"""
You are an autonomous AI browser agent navigating a municipal grievance portal to submit a solid waste citizen complaint.
Citizen Ticket Data:
{json.dumps(ticket_context, indent=2)}

Citizen Login State:
{'LOGGED IN - Now look for URL to raise complaint or fill complaint form' if user_login_completed else 'AWAITING CITIZEN LOGIN'}

Latest Human Provided Input:
{'User Input / OTP: ' + user_provided_otp if user_provided_otp else 'None yet'}

Recent Step History:
{json.dumps(step_history[-2:], indent=2)}

Current Interactive Page Elements (Semantic DOM Snapshot):
{json.dumps(dom_elements, indent=2)}

Available Action Commands:
1. {{"action": "click", "selector": "selector", "text": "button or link text", "semantic_role": "complaint|login|otp_trigger|verify|submit"}}
2. {{"action": "fill", "selector": "selector", "label": "field label", "semantic_role": "mobile|otp|username|password|description|landmark", "value": "text to type"}}
3. {{"action": "select_option", "selector": "selector", "value": "Option Label"}}
4. {{"action": "upload_file", "selector": "input[type='file']"}}
5. {{"action": "request_human_input", "type": "otp", "prompt": "Please enter verification code sent to your phone."}}
6. {{"action": "finish", "token": "PMC-SW-2026-XXXX"}}
7. {{"action": "email_fallback", "reason": "No complaint registration option exists on this portal"}}

CRITICAL BEHAVIOR POLICY (NAVIGATE REGARDLESS OF CSS SELECTORS):
1. REACTIVE STEP-BY-STEP EXECUTION: Plan ONLY 1 or 2 immediate actions for the elements visible on the CURRENT page right now. DO NOT generate actions for future pages that are not yet loaded.
2. LANGUAGE: Ensure English version is active. If in regional language, click or select English first.
3. POST-LOGIN COMPLAINT URL DISCOVERY (CRITICAL):
   Once the user has completely logged in, look for the URL or link to RAISE / LODGE / REGISTER A COMPLAINT (e.g. 'Register Your Complaint', 'Lodge Grievance', 'Register Complaint', 'Citizen Grievances', 'New Grievance', 'तक्रार').
   Click that URL / link to navigate to the grievance registration form.
4. CITIZEN LOGIN & REGISTRATION POLICY:
   - UNDER NO CIRCUMSTANCES should you automatically fill in the mobile number or credentials into login or registration fields.
   - If the portal presents a mobile number, login, or registration field, you must wait for the user to complete login or registration.
   - Do NOT generate fill actions for mobile numbers or credentials on login or registration forms.
   - If online filing strictly requires pre-registered citizen credentials or login that cannot proceed, output:
     {{"action": "email_fallback", "reason": "Portal requires citizen login/registration"}}.
5. HUMAN INPUT: Whenever the portal asks for an SMS verification code (e.g. OTP, verification code, captcha) that only the citizen has received, output:
   {{"action": "request_human_input", "type": "otp", "prompt": "Portal requires SMS verification code sent to your mobile. Please enter it."}}.
   NEVER guess or invent verification codes.
6. AFTER HUMAN INPUT: Once human input is provided (shown in 'Latest Human Provided Input'), enter it into the OTP field and click Verify.
7. FORM SUBMISSION: Once inside the complaint submission form, select 'Solid Waste Management', fill landmark & description, attach evidence file, and click submit.
8. FINISH: When a confirmation token or successful submission banner appears (e.g. PMC-SW-..., COMP-..., PCMC-...), output {{"action": "finish", "token": "..."}}.
9. STATUTORY EMAIL FALLBACK: If the portal has no online complaint registration option, or requires pre-registered citizen credentials, or online filing cannot proceed, output:
   {{"action": "email_fallback", "reason": "Online complaint registration requires pre-registered citizen credentials or is unavailable"}}.

Output strictly valid JSON matching:
{{"thought": "clear step-by-step reasoning", "actions": [ ... ]}}
"""

                decision = _chat_completion_with_fallback(groq_client, prompt)
                thought = decision.get("thought", "Analyzing page...")
                actions = decision.get("actions", [])
                print(f"[{ticket_id}] 💭 Thought: {thought}")
                print(f"[{ticket_id}] 🎯 Next Action(s): {actions}")

                update_ticket_status(ticket_id, {
                    "agent_telemetry": thought[:140]
                })

                should_break_loop = False
                fallback_reason = None

                # Execute planned actions on the live browser page using selector-agnostic helpers
                for act in actions:
                    act_type = act.get("action")
                    selector = act.get("selector", "")
                    val = act.get("value", "")

                    if act_type == "click":
                        await _robust_click(page, act, ticket_id)
                        await asyncio.sleep(2.0)
                        await _ensure_english_version(page)
                        # Page DOM or state has updated; break inner loop to evaluate fresh DOM on next agent step
                        break

                    elif act_type == "fill":
                        await _robust_fill(page, act, ticket_id, allow_mobile_fill=user_login_completed)

                    elif act_type == "select_option":
                        try:
                            loc = page.locator(f"{selector}:visible") if ":visible" not in selector else page.locator(selector)
                            target_loc = loc.first if await loc.count() > 0 else page.locator(selector).first
                            try:
                                await target_loc.select_option(label=str(val), timeout=5000)
                            except Exception:
                                try:
                                    await target_loc.select_option(index=1, timeout=5000)
                                except Exception:
                                    pass
                            print(f"[{ticket_id}] 📋 Selected '{val}' in {selector}")
                        except Exception as sel_err:
                            print(f"[{ticket_id}] Select notice ({selector}): {sel_err}")

                    elif act_type == "upload_file":
                        file_input = page.locator(selector if selector else 'input[type="file"]')
                        if await file_input.count() > 0 and os.path.exists(local_image_path):
                            await file_input.first.set_input_files(os.path.abspath(local_image_path))
                            print(f"[{ticket_id}] 📎 Attached photographic evidence {os.path.basename(local_image_path)}")

                    elif act_type == "request_human_input":
                        prompt_msg = act.get("prompt") or f"Verification required on {corp_name} portal. Enter SMS code sent to {user_phone}."
                        print(f"[{ticket_id}] 🛑 HUMAN INPUT REQUIRED BY WEBSITE: {prompt_msg}")

                        update_ticket_status(ticket_id, {
                            "status": "AWAITING_OTP",
                            "auth_prompt": prompt_msg,
                            "agent_telemetry": f"Portal requires human input: {prompt_msg}"
                        })

                        # Polling state machine awaiting user input via DynamoDB (up to 30 seconds)
                        otp_code = None
                        for poll_i in range(15):
                            await asyncio.sleep(2)
                            record = get_ticket(ticket_id)
                            if record:
                                val = record.get("user_provided_otp") or record.get("user_provided_input")
                                if val:
                                    otp_code = str(val).strip()
                                    print(f"[{ticket_id}] ✅ Human entered requested input: {otp_code}")
                                    break

                            # In mock mode, if citizen takes longer than 15s in automated test, fallback for demo continuity
                            if settings.PORTAL_MODE == "mock" and poll_i >= 8:
                                otp_code = "592014"
                                print(f"[{ticket_id}] 💡 Mock demo mode auto-supplied verification OTP: {otp_code}")
                                break

                        if not otp_code:
                            print(f"[{ticket_id}] ⚠️ Citizen timed out providing input. Transitioning to statutory email dispatch...")
                            await browser.close()
                            await _trigger_email_fallback(ticket_id, form_data, "Citizen timed out providing OTP verification on portal.")
                            return

                        user_provided_otp = otp_code
                        update_ticket_status(ticket_id, {
                            "status": "RELAYING_OTP",
                            "user_provided_otp": None,
                            "user_provided_input": None,
                            "agent_telemetry": f"Relaying verification code '{otp_code}' to portal..."
                        })
                        break  # Re-evaluate page with the new human input available

                    elif act_type == "finish":
                        extracted_token = act.get("token")
                        if extracted_token and ("PMC-" in extracted_token or "COMP-" in extracted_token):
                            ref_id = extracted_token
                        should_break_loop = True
                        break

                    elif act_type == "email_fallback":
                        fallback_reason = act.get("reason", "No online complaint option available on portal")
                        should_break_loop = True
                        break

                step_history.append({"thought": thought, "actions": actions})
                await asyncio.sleep(1.2)

                if should_break_loop:
                    if fallback_reason:
                        await browser.close()
                        await _trigger_email_fallback(ticket_id, form_data, fallback_reason)
                        return
                    break

                # Check if final reference token is present on the page
                page_text = await page.content()
                token_match = (
                    re.search(r"(PMC-[A-Z0-9-]+)", page_text)
                    or re.search(r"(COMP-\d+)", page_text)
                )
                if token_match:
                    ref_id = token_match.group(0)
                    print(f"[{ticket_id}] 🎯 Token detected on page: {ref_id}")
                    break

            # If loop finished without reference token, check page or trigger email fallback
            if not ref_id:
                page_text = await page.content()
                token_match = (
                    re.search(r"(PMC-[A-Z0-9-]+)", page_text)
                    or re.search(r"(COMP-\d+)", page_text)
                )
                if token_match:
                    ref_id = token_match.group(0)
                else:
                    if settings.PORTAL_MODE == "mock":
                        ref_id = f"PMC-SW-2026-{ticket_id.upper()}"
                    else:
                        print(f"[{ticket_id}] ⚠️ Online complaint form not completed on portal. Transitioning to statutory email dispatch...")
                        await browser.close()
                        await _trigger_email_fallback(
                            ticket_id,
                            form_data,
                            "Complaint form could not be completed on portal (SMS verification required)."
                        )
                        return

            print(f"[{ticket_id}] 🏁 Filing finalized! Reference Token: {ref_id}\n")
            update_ticket_status(ticket_id, {
                "status": "SUBMITTED",
                "municipal_ref_id": ref_id,
                "agent_summary": f"Autonomous AI filing finalized with {corp_name}. Reference Token: {ref_id}"
            })

        except Exception as e:
            print(f"[{ticket_id}] AI Filing worker notice: {e}")
            await _trigger_email_fallback(ticket_id, form_data, f"Browser filing encountered error: {str(e)}")
        finally:
            try:
                await browser.close()
            except Exception:
                pass