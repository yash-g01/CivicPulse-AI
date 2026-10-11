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

from typing import Optional, List

router = APIRouter()

class OtpPayload(BaseModel):
    otp: str

@router.post("/triage")
async def check_image_triage(
    image: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None)
):
    upload_list: List[UploadFile] = []
    if images:
        upload_list.extend(images)
    if image and image not in upload_list:
        upload_list.append(image)
    if not upload_list:
        raise HTTPException(status_code=400, detail="At least one image is required for triage.")

    ticket_id = str(uuid.uuid4())[:8]
    os.makedirs("/tmp/civicpulse", exist_ok=True)

    triage_data = None
    for idx, img in enumerate(upload_list[:3]):
        img_bytes = await img.read()
        local_path = f"/tmp/civicpulse/triage_{ticket_id}_{idx}_{img.filename or 'upload.jpg'}"
        with open(local_path, "wb") as f:
            f.write(img_bytes)

        cur_triage = await asyncio.to_thread(triage_waste_image, local_path)
        if cur_triage.get("is_valid_waste"):
            triage_data = cur_triage
            break
        elif triage_data is None:
            triage_data = cur_triage

    return triage_data or {"is_valid_waste": False, "rejection_reason": "No image could be triaged."}


@router.post("/reports")
async def create_waste_report(
    background_tasks: BackgroundTasks,
    image: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None),
    lat: float = Form(...),
    lng: float = Form(...),
    user_phone: str = Form(...),
    user_name: Optional[str] = Form(None),
    portal_url: Optional[str] = Form(None)
):
    upload_list: List[UploadFile] = []
    if images:
        upload_list.extend(images)
    if image and image not in upload_list:
        upload_list.append(image)
    if not upload_list:
        raise HTTPException(status_code=400, detail="At least one evidence photo is required.")

    start_total = time.time()
    ticket_id = str(uuid.uuid4())[:8]
    os.makedirs("/tmp/civicpulse", exist_ok=True)

    primary_img = upload_list[0]
    primary_bytes = await primary_img.read()
    primary_local_path = f"/tmp/civicpulse/{ticket_id}_{primary_img.filename or 'before.jpg'}"
    with open(primary_local_path, "wb") as f:
        f.write(primary_bytes)

    primary_s3_key = f"evidence/{ticket_id}_before.jpg"

    # Save additional images and prepare S3 keys
    all_s3_keys = [primary_s3_key]
    all_image_bytes = [(primary_s3_key, primary_bytes)]
    all_local_paths = [primary_local_path]

    for idx, additional_img in enumerate(upload_list[1:], start=1):
        add_bytes = await additional_img.read()
        add_key = f"evidence/{ticket_id}_before_{idx}.jpg"
        all_s3_keys.append(add_key)
        all_image_bytes.append((add_key, add_bytes))
        add_path = f"/tmp/civicpulse/{ticket_id}_{idx}_{additional_img.filename or 'before.jpg'}"
        with open(add_path, "wb") as f:
            f.write(add_bytes)
        all_local_paths.append(add_path)

    print(f"\n⚡ [{ticket_id}] Starting Concurrent Intake Processing ({len(upload_list)} images attached)...")

    # Upload all images to S3
    def _upload_all_images():
        for k, b in all_image_bytes:
            upload_image_bytes(k, b)

    try:
        triage_task = asyncio.to_thread(triage_waste_image, primary_local_path)
        geo_task = asyncio.to_thread(resolve_authority, lat, lng)
        s3_task = asyncio.to_thread(_upload_all_images)

        triage_data, authority, _ = await asyncio.gather(
            triage_task, geo_task, s3_task
        )
    except Exception as e:
        print(f"[{ticket_id}] Intake failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing pipeline failed: {str(e)}")

    # If primary image was rejected, but user uploaded multiple images, test secondary image before rejecting
    if not triage_data.get("is_valid_waste") and len(upload_list) > 1:
        for idx in range(1, min(len(upload_list), 3)):
            add_path = f"/tmp/civicpulse/{ticket_id}_{idx}_{upload_list[idx].filename or 'before.jpg'}"
            sec_triage = await asyncio.to_thread(triage_waste_image, add_path)
            if sec_triage.get("is_valid_waste"):
                triage_data = sec_triage
                break

    if not triage_data.get("is_valid_waste"):
        rejection = triage_data.get("rejection_reason") or "Image does not depict actionable public waste."
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NOT_GARBAGE",
                "message": rejection,
                "is_valid_waste": False,
                "rejection_reason": rejection,
                "triage": triage_data,
            }
        )

    if portal_url:
        authority["portal_url"] = portal_url

    from app.core.s3 import generate_presigned_view_url
    evidence_urls = [generate_presigned_view_url(k) for k in all_s3_keys]
    evidence_url = evidence_urls[0]

    record = {
        "status": "QUEUED_FOR_FILING",
        "user_phone": user_phone,
        "user_name": user_name or "",
        "lat": str(lat),
        "lng": str(lng),
        "authority": authority,
        "portal_url": portal_url or authority.get("portal_url"),
        "triage": triage_data,
        "before_s3_key": primary_s3_key,
        "before_s3_keys": all_s3_keys,
        "evidence_url": evidence_url,
        "evidence_urls": evidence_urls,
        "complaint_text": triage_data.get("complaint_text", ""),
        "landmark": triage_data.get("landmark_context", ""),
        "created_at": str(time.time()),
        "filed_fields": {
            "complainant_name": user_name or "Concerned Citizen",
            "mobile_number": user_phone or "On file",
            "category": (triage_data.get("waste_categories") or ["Solid Waste Management"])[0] if triage_data.get("waste_categories") else "Solid Waste Management",
            "landmark": triage_data.get("landmark_context") or "Roadside civic accumulation",
            "description": triage_data.get("complaint_text") or "Solid waste accumulation detected and reported.",
            "evidence_count": len(all_s3_keys),
            "evidence_files": [f"Evidence Photo {i+1}" for i in range(len(all_s3_keys))],
            "portal_name": authority.get("corporation", "Municipal Corporation"),
            "portal_url": portal_url or authority.get("portal_url", ""),
        },
    }
    await asyncio.to_thread(save_ticket, ticket_id, record)

    background_tasks.add_task(
        run_filing_worker,
        ticket_id=ticket_id,
        form_data=record,
        local_image_path=all_local_paths if len(all_local_paths) > 1 else primary_local_path
    )

    elapsed = (time.time() - start_total) * 1000
    print(f"✅ [{ticket_id}] Intake Complete in {elapsed:.0f}ms -> Browser worker dispatched in background.\n")

    return {
        "ticket_id": ticket_id,
        "status": "QUEUED_FOR_FILING",
        "triage": triage_data,
        "authority": authority,
        "evidence_url": evidence_url,
        "evidence_urls": evidence_urls,
        "user_name": user_name or "",
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