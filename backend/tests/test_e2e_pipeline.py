import os
import sys
import time
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_end_to_end():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        print("\n=======================================================")
        print("  CIVICPULSE AI: END-TO-END PIPELINE VERIFICATION")
        print("=======================================================\n")

        # 1. Test Mock PMC Portal endpoint
        print("[1/5] Testing GET /mock-pmc-portal...")
        res = await client.get("/mock-pmc-portal")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert "Pune Municipal Corporation" in res.text
        print("      ✅ Mock portal successfully serving grievance form.")

        # 2. Test Waste Intake Report
        print("\n[2/5] Testing POST /api/v1/reports (Intake & Triage)...")
        sample_image_path = "tests/dump.jpeg"
        with open(sample_image_path, "rb") as f:
            image_data = f.read()

        files = {"image": ("dump.jpeg", image_data, "image/jpeg")}
        data = {
            "lat": "18.5204",
            "lng": "73.8567",
            "user_phone": "9822012345"
        }

        start_time = time.time()
        res = await client.post("/api/v1/reports", files=files, data=data)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        intake_resp = res.json()
        ticket_id = intake_resp["ticket_id"]
        print(f"      ✅ Report accepted! Ticket ID: {ticket_id}")
        print(f"      📍 Authority: {intake_resp['authority']['corporation']}")
        print(f"      🗑️ Triage Severity: {intake_resp['triage']['severity']}/5")
        print(f"      ⏱️ Processing Time: {intake_resp['processing_time_ms']}ms")

        # 3. Test Polling & OTP Relay
        print(f"\n[3/5] Polling ticket {ticket_id} for AWAITING_OTP state...")
        await_otp_reached = False
        for _ in range(15):
            await asyncio.sleep(1.5)
            ticket_res = await client.get(f"/api/v1/tickets/{ticket_id}")
            if ticket_res.status_code == 200:
                t_data = ticket_res.json()
                status = t_data.get("status")
                print(f"      Current Status: {status}")
                if status in ("AWAITING_OTP", "AWAITING_HUMAN_ACTION", "AWAITING_LOGIN"):
                    await_otp_reached = True
                    break
                elif status == "SUBMITTED":
                    break

        if await_otp_reached:
            print("\n      🔑 Ticket reached AWAITING_OTP! Submitting OTP via API...")
            otp_res = await client.post(
                f"/api/v1/tickets/{ticket_id}/submit-otp",
                json={"otp": "592014"}
            )
            assert otp_res.status_code == 200
            print("      ✅ OTP submitted successfully!")

        # 4. Wait for SUBMITTED state
        print("\n[4/5] Waiting for Playwright worker to complete form and extract token...")
        final_token = None
        for _ in range(20):
            await asyncio.sleep(2)
            ticket_res = await client.get(f"/api/v1/tickets/{ticket_id}")
            if ticket_res.status_code == 200:
                t_data = ticket_res.json()
                if t_data.get("status") == "SUBMITTED":
                    final_token = t_data.get("municipal_ref_id")
                    print(f"      🎯 Grievance Form Submitted! Reference Token: {final_token}")
                    break

        assert final_token, "Filing worker failed to finalize ticket status."

        # 5. Test Ghost-Resolution Auditor Simulation
        print("\n[5/5] Testing POST /api/v1/tickets/{id}/simulate-resolution (Ghost Auditor)...")
        # Test clean photo
        with open("tests/cleaned.jpg", "rb") as f:
            clean_bytes = f.read()
        res_clean = await client.post(
            f"/api/v1/tickets/{ticket_id}/simulate-resolution",
            files={"after_image": ("cleaned.jpg", clean_bytes, "image/jpeg")}
        )
        assert res_clean.status_code == 200
        clean_json = res_clean.json()
        print(f"      Verified Clean: Status = {clean_json['status']}")
        print(f"      Auditor Verdict: debris_cleared={clean_json['audit'].get('debris_cleared')}, fraud_detected={clean_json['audit'].get('fraud_detected')}")

        # Test fake clean photo
        with open("tests/fake_clean.jpg", "rb") as f:
            fake_bytes = f.read()
        res_fake = await client.post(
            f"/api/v1/tickets/{ticket_id}/simulate-resolution",
            files={"after_image": ("fake_clean.jpg", fake_bytes, "image/jpeg")}
        )
        assert res_fake.status_code == 200
        fake_json = res_fake.json()
        print(f"\n      Simulated Fake Clean: Status = {fake_json['status']}")
        print(f"      Auditor Verdict: fraud_detected={fake_json['audit'].get('fraud_detected')}")
        print(f"      Discrepancy Notes: {fake_json['audit'].get('discrepancy_notes')[:120]}...")

        print("\n=======================================================")
        print("  🎉 ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
