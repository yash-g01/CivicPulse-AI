import uuid
import os
import time
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.triage_service import triage_waste_image
from app.services.audit_service import audit_resolution_images
from app.services.geo_router import resolve_authority
from app.services.filing_agent import run_filing_worker
from app.core.dynamodb import get_ticket, save_ticket, update_ticket_status
from app.core.s3 import upload_image_bytes, get_image_bytes

from typing import Optional

router = APIRouter()

class OtpPayload(BaseModel):
    otp: str

@router.post("/reports")
async def create_waste_report(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    user_phone: str = Form(...),
    portal_url: Optional[str] = Form(None)
):
    start_total = time.time()
    ticket_id = str(uuid.uuid4())[:8]
    image_bytes = await image.read()

    os.makedirs("/tmp/civicpulse", exist_ok=True)
    local_path = f"/tmp/civicpulse/{ticket_id}_before.jpg"
    with open(local_path, "wb") as f:
        f.write(image_bytes)

    s3_key = f"evidence/{ticket_id}_before.jpg"

    print(f"\n⚡ [{ticket_id}] Starting Concurrent Intake Processing...")

    # Execute Triage, Geo-routing, and S3 upload in parallel non-blocking threads
    try:
        triage_task = asyncio.to_thread(triage_waste_image, local_path)
        geo_task = asyncio.to_thread(resolve_authority, lat, lng)
        s3_task = asyncio.to_thread(upload_image_bytes, s3_key, image_bytes)

        triage_data, authority, _ = await asyncio.gather(
            triage_task, geo_task, s3_task
        )
    except Exception as e:
        print(f"[{ticket_id}] Intake failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing pipeline failed: {str(e)}")

    if not triage_data.get("is_valid_waste"):
        rejection = triage_data.get("rejection_reason") or "Image does not depict actionable public waste."
        raise HTTPException(status_code=400, detail=f"Rejected: {rejection}")

    # If caller explicitly provided a target municipal portal URL, prioritize it
    if portal_url:
        authority["portal_url"] = portal_url

    # Initialize DynamoDB Ticket
    from app.core.s3 import generate_presigned_view_url
    evidence_url = generate_presigned_view_url(s3_key)

    record = {
        "status": "QUEUED_FOR_FILING",
        "user_phone": user_phone,
        "lat": str(lat),
        "lng": str(lng),
        "authority": authority,
        "portal_url": portal_url or authority.get("portal_url"),
        "triage": triage_data,
        "before_s3_key": s3_key,
        "evidence_url": evidence_url,
        "complaint_text": triage_data.get("complaint_text", ""),
        "landmark": triage_data.get("landmark_context", ""),
        "created_at": str(time.time()),
    }
    await asyncio.to_thread(save_ticket, ticket_id, record)

    # Launch Playwright / browser-use worker in the background
    background_tasks.add_task(
        run_filing_worker,
        ticket_id=ticket_id,
        form_data=record,
        local_image_path=local_path
    )

    elapsed = (time.time() - start_total) * 1000
    print(f"✅ [{ticket_id}] Intake Complete in {elapsed:.0f}ms -> Browser worker dispatched in background.\n")

    return {
        "ticket_id": ticket_id,
        "status": "QUEUED_FOR_FILING",
        "triage": triage_data,
        "authority": authority,
        "evidence_url": evidence_url,
        "processing_time_ms": round(elapsed, 1),
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    ticket = await asyncio.to_thread(get_ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/tickets/{ticket_id}/submit-otp")
async def submit_ticket_otp(ticket_id: str, payload: OtpPayload):
    ticket = await asyncio.to_thread(get_ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    otp = payload.otp.strip()
    await asyncio.to_thread(update_ticket_status, ticket_id, {
        "user_provided_otp": otp,
        "status": "RELAYING_OTP"
    })
    print(f"[{ticket_id}] 🔑 User submitted OTP: {otp}")
    return {
        "ticket_id": ticket_id,
        "status": "RELAYING_OTP",
        "message": "OTP received and relayed to autonomous worker"
    }


@router.post("/tickets/{ticket_id}/confirm-login")
async def confirm_ticket_login(ticket_id: str):
    ticket = await asyncio.to_thread(get_ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await asyncio.to_thread(update_ticket_status, ticket_id, {
        "user_login_completed": True,
        "status": "AGENT_BROWSING_PORTAL"
    })
    print(f"[{ticket_id}] 👤 User confirmed login/registration completion.")
    return {
        "ticket_id": ticket_id,
        "status": "LOGIN_CONFIRMED",
        "message": "Login confirmed, autonomous worker continuing filing."
    }


@router.post("/tickets/{ticket_id}/simulate-resolution")
async def simulate_resolution(
    ticket_id: str,
    after_image: UploadFile = File(...)
):
    ticket = await asyncio.to_thread(get_ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    after_bytes = await after_image.read()
    os.makedirs("/tmp/civicpulse", exist_ok=True)
    after_path = f"/tmp/civicpulse/{ticket_id}_after.jpg"
    with open(after_path, "wb") as f:
        f.write(after_bytes)

    # Fetch initial complaint evidence photo
    before_path = f"/tmp/civicpulse/{ticket_id}_before.jpg"
    if not os.path.exists(before_path):
        before_s3_key = ticket.get("before_s3_key")
        if before_s3_key:
            try:
                before_bytes = await asyncio.to_thread(get_image_bytes, before_s3_key)
                with open(before_path, "wb") as f:
                    f.write(before_bytes)
            except Exception as ex:
                print(f"[{ticket_id}] Could not fetch before image from S3: {ex}")

    if not os.path.exists(before_path):
        raise HTTPException(status_code=400, detail="Original complaint image unavailable for audit comparison")

    # Upload after image to S3
    after_s3_key = f"evidence/{ticket_id}_after.jpg"
    await asyncio.to_thread(upload_image_bytes, after_s3_key, after_bytes)

    # Perform forensic AI audit
    audit_data = await asyncio.to_thread(audit_resolution_images, before_path, after_path)

    # Determine status transition
    if audit_data.get("fraud_detected"):
        new_status = "REOPENED_AUDIT_FAILED"
    elif audit_data.get("debris_cleared") and audit_data.get("is_same_scene"):
        new_status = "CONFIRMED_CLEAN"
    else:
        new_status = "REOPENED_AUDIT_FAILED"

    await asyncio.to_thread(update_ticket_status, ticket_id, {
        "status": new_status,
        "after_s3_key": after_s3_key,
        "audit": audit_data
    })

    return {
        "ticket_id": ticket_id,
        "status": new_status,
        "audit": audit_data
    }