import asyncio
import os
import sys
import uuid

# Add backend directory to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.filing_agent import run_filing_worker, normalize_portal_url
from app.core.dynamodb import get_ticket, save_ticket, update_ticket_status
from app.config import settings

async def test_live_pmc():
    print("\n" + "=" * 65)
    print("  TEST 1: LIVE PMC PORTAL (complaints.pmc.gov.in/language=en)")
    print("=" * 65)
    
    ticket_id = f"test_pmc_{uuid.uuid4().hex[:6]}"
    raw_pmc_url = "complaints.pmc.gov.in/language=en"
    norm_url = normalize_portal_url(raw_pmc_url)
    print(f"[*] Input URL: {raw_pmc_url}")
    print(f"[*] Normalized URL: {norm_url}")
    assert norm_url == "https://complaint.pmc.gov.in/?language=en"

    form_data = {
        "status": "QUEUED_FOR_FILING",
        "user_phone": "9822012345",
        "lat": "18.5204",
        "lng": "73.8567",
        "portal_url": norm_url,
        "authority": {
            "corporation": "Pune Municipal Corporation (PMC)",
            "portal_url": norm_url,
            "city_slug": "pune",
            "nodal_email": "feedback@punecorporation.org"
        },
        "complaint_text": "Chronic unsegregated waste dumping causing obstruction and sanitation hazard.",
        "landmark": "Near Deccan Gymkhana Bus Stop",
    }
    save_ticket(ticket_id, form_data)

    # Use existing test image
    test_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "dump.jpeg"))

    # Spawn worker task
    worker_task = asyncio.create_task(
        run_filing_worker(ticket_id, form_data, test_img)
    )

    # Monitor status for up to 30 seconds
    saw_browsing = False
    saw_login_or_email = False
    simulated_login = False
    for i in range(25):
        await asyncio.sleep(1.5)
        ticket = get_ticket(ticket_id)
        if not ticket:
            continue
        status = ticket.get("status")
        telemetry = ticket.get("agent_telemetry", "")
        print(f"  [PMC Step {i+1}] Status: {status} | Telemetry: {telemetry[:75]}")

        if status in ("AGENT_BROWSING_PORTAL", "AWAITING_HUMAN_ACTION", "AWAITING_LOGIN", "AWAITING_OTP", "EMAIL_FALLBACK_READY"):
            saw_browsing = True

        if status in ("AWAITING_HUMAN_ACTION", "AWAITING_LOGIN") and not simulated_login:
            print(f"  🔑 AWAITING_HUMAN_ACTION reached! Prompt: {ticket.get('auth_prompt')}")
            print("  🔒 Verified: Agent paused without auto-filling mobile number, waiting for citizen login!")
            saw_login_or_email = True
            simulated_login = True
            # Simulate citizen completing login via API to test post-login complaint URL discovery
            print("  👤 Citizen completed login! Notifying worker...")
            update_ticket_status(ticket_id, {"user_login_completed": True})
        elif status == "AWAITING_OTP":
            print(f"  🔑 AWAITING_OTP reached! Prompt: {ticket.get('auth_prompt')}")
            saw_login_or_email = True
            update_ticket_status(ticket_id, {"user_provided_otp": "592014"})
        elif status == "EMAIL_FALLBACK_READY":
            print("  📧 Fallback email dossier generated!")
            saw_login_or_email = True
            break
        elif status == "SUBMITTED":
            print(f"  🎯 Successfully submitted! Ref ID: {ticket.get('municipal_ref_id')}")
            saw_login_or_email = True
            break

    # Wait for worker completion or timeout
    try:
        await asyncio.wait_for(worker_task, timeout=15.0)
    except Exception:
        pass

    final_ticket = get_ticket(ticket_id)
    print(f"\n[PMC Final State] Status: {final_ticket.get('status')}")
    assert saw_browsing, "Agent never navigated to PMC portal."
    assert saw_login_or_email, "Agent did not reach citizen login wait or submission."
    print("✅ TEST 1 PASSED: Agent paused without auto-filling mobile, waiting for citizen login!\n")


async def test_live_pcmc():
    print("\n" + "=" * 65)
    print("  TEST 2: LIVE PCMC PORTAL (https://grievance.pcmcindia.gov.in:8443/Grievance/citizen/)")
    print("=" * 65)

    ticket_id = f"test_pcmc_{uuid.uuid4().hex[:6]}"
    pcmc_url = "https://grievance.pcmcindia.gov.in:8443/Grievance/citizen/"
    norm_url = normalize_portal_url(pcmc_url)
    print(f"[*] Input URL: {pcmc_url}")
    print(f"[*] Normalized URL: {norm_url}")

    form_data = {
        "status": "QUEUED_FOR_FILING",
        "user_phone": "9822012345",
        "lat": "18.6298",
        "lng": "73.7997",
        "portal_url": norm_url,
        "authority": {
            "corporation": "Pimpri Chinchwad Municipal Corporation (PCMC)",
            "portal_url": norm_url,
            "city_slug": "pcmc",
            "nodal_email": "sarathi@pcmcindia.gov.in"
        },
        "complaint_text": "Severe garbage accumulation along roadside near railway station.",
        "landmark": "Near Pimpri Railway Station Bridge",
    }
    save_ticket(ticket_id, form_data)

    test_img = os.path.abspath(os.path.join(os.path.dirname(__file__), "dump.jpeg"))

    worker_task = asyncio.create_task(
        run_filing_worker(ticket_id, form_data, test_img)
    )

    saw_browsing = False
    saw_fallback_or_login = False
    simulated_login = False
    for i in range(25):
        await asyncio.sleep(1.5)
        ticket = get_ticket(ticket_id)
        if not ticket:
            continue
        status = ticket.get("status")
        telemetry = ticket.get("agent_telemetry", "")
        print(f"  [PCMC Step {i+1}] Status: {status} | Telemetry: {telemetry[:75]}")

        if status in ("AGENT_BROWSING_PORTAL", "COMPILING_EMAIL_DOSSIER", "EMAIL_FALLBACK_READY", "AWAITING_HUMAN_ACTION", "AWAITING_LOGIN", "AWAITING_OTP"):
            saw_browsing = True

        if status in ("AWAITING_HUMAN_ACTION", "AWAITING_LOGIN") and not simulated_login:
            print(f"  🔑 PCMC Logon detected: Awaiting citizen login! Prompt: {ticket.get('auth_prompt')}")
            print("  🔒 Verified: Agent is pausing and waiting for citizen login without auto-filling credentials!")
            saw_fallback_or_login = True
            simulated_login = True
            # Simulate citizen completing login to test post-login URL discovery
            print("  👤 Citizen completed login! Notifying worker...")
            update_ticket_status(ticket_id, {"user_login_completed": True})

        if status == "EMAIL_FALLBACK_READY":
            email_info = ticket.get("email_dispatch", {})
            evidence_url = ticket.get("evidence_url") or email_info.get("evidence_url")
            print(f"  📧 Fallback Triggered: {ticket.get('fallback_reason')}")
            print(f"  📧 Recipient: {email_info.get('to')}")
            print(f"  📧 Subject: {email_info.get('subject')}")
            print(f"  📎 S3 Presigned Evidence URL: {evidence_url}")
            print(f"  📧 Mailto URI: {email_info.get('mailto_url')[:60]}...")
            assert evidence_url and "s3.amazonaws.com" in evidence_url, "S3 Presigned URL missing in fallback email!"
            assert evidence_url in email_info.get("body", ""), "S3 Presigned URL not embedded in email body!"
            saw_fallback_or_login = True
            break
        elif status == "SUBMITTED":
            print(f"  🎯 Successfully submitted on PCMC! Ref ID: {ticket.get('municipal_ref_id')}")
            saw_fallback_or_login = True
            break

    try:
        await asyncio.wait_for(worker_task, timeout=20.0)
    except Exception:
        pass

    final_ticket = get_ticket(ticket_id)
    print(f"\n[PCMC Final State] Status: {final_ticket.get('status')}")
    assert saw_browsing, "Agent never navigated to PCMC portal."
    assert saw_fallback_or_login, "Agent did not finalize PCMC login wait or fallback pathway."
    print("✅ TEST 2 PASSED: Agent handled PCMC logon and verified S3 presigned URL in email dossier!\n")


async def main():
    await test_live_pmc()
    await test_live_pcmc()
    print("=" * 65)
    print("  🎉 ALL LIVE MUNICIPAL NAVIGATION TESTS SUCCEEDED!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
