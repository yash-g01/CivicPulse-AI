from fastapi import APIRouter
from fastapi.responses import HTMLResponse

mock_router = APIRouter()

MOCK_PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pune Municipal Corporation (PMC) - Citizen Grievance Redressal Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: #f1f5f9; color: #1e293b; padding: 24px 16px; }
    .container { max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #e2e8f0; }
    .header { background: #1e3a8a; color: #ffffff; padding: 20px 24px; display: flex; align-items: center; gap: 16px; }
    .header-badge { width: 44px; height: 44px; border-radius: 8px; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }
    .header h1 { font-size: 18px; font-weight: 700; line-height: 1.3; }
    .header p { font-size: 13px; color: #bfdbfe; margin-top: 2px; }
    .form-body { padding: 24px; display: flex; flex-direction: column; gap: 20px; }
    .section-title { font-size: 14px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }
    .form-group { display: flex; flex-direction: column; gap: 6px; }
    label { font-size: 13px; font-weight: 600; color: #334155; }
    input, select, textarea { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; }
    input:focus, select:focus, textarea:focus { border-color: #2563eb; outline: none; }
    .input-row { display: flex; gap: 10px; align-items: center; }
    button { padding: 10px 16px; font-size: 14px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: all 0.2s; border: none; white-space: nowrap; }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-success { background: #16a34a; color: #ffffff; width: 100%; padding: 12px; font-size: 15px; margin-top: 8px; }
    .btn-success:hover { background: #15803d; }
    .badge-otp { background: #eff6ff; color: #1d4ed8; border: 1px dashed #93c5fd; padding: 8px 12px; border-radius: 6px; font-size: 13px; display: inline-block; margin-top: 6px; }
    .alert-success { background: #f0fdf4; border: 1px solid #86efac; color: #166534; padding: 16px; border-radius: 8px; text-align: center; font-size: 15px; }
    .alert-success strong { font-size: 17px; display: block; margin-top: 4px; color: #14532d; }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-badge">PMC</div>
      <div>
        <h1>Pune Municipal Corporation</h1>
        <p>Public Grievance Redressal Gateway (Solid Waste & Health Dept)</p>
      </div>
    </div>

    <div class="form-body">
      <!-- Step 1: Citizen Mobile Verification -->
      <div>
        <div class="section-title">Step 1: Citizen Authentication</div>
        <div class="form-group">
          <label for="mobile">Mobile Number</label>
          <div class="input-row">
            <input type="tel" id="mobile" name="mobile" placeholder="Enter 10-digit mobile number" value="9822012345" />
            <button type="button" id="btn-send-otp" class="btn-primary" onclick="sendOtp()">Send OTP</button>
          </div>
          <div id="otp-hint" class="badge-otp hidden">
            SMS sent! Code: <strong id="hint-code">592014</strong>
          </div>
        </div>

        <div id="otp-section" class="form-group" style="margin-top: 14px;">
          <label for="otp-input">Enter OTP</label>
          <div class="input-row">
            <input type="text" id="otp-input" name="otp" placeholder="6-digit verification code" />
            <button type="button" id="btn-verify-otp" class="btn-primary" onclick="verifyOtp()">Verify OTP</button>
          </div>
          <div id="otp-verified-msg" class="badge-otp hidden" style="background:#f0fdf4; color:#166534; border-color:#86efac;">
            Mobile Verified
          </div>
        </div>
      </div>

      <!-- Step 2: Grievance Details Form -->
      <div id="complaint-section" class="hidden">
        <div class="section-title">Step 2: Grievance Details</div>
        
        <div class="form-group">
          <label for="citizen-name">Citizen / Complainant Name</label>
          <input type="text" id="citizen-name" name="citizen_name" placeholder="Full name of complainant" />
        </div>

        <div class="form-group">
          <label for="department">Department</label>
          <select id="department" name="department">
            <option value="Solid Waste Management" selected>Solid Waste Management (SWM)</option>
            <option value="Health & Sanitation">Health & Sanitation</option>
            <option value="Roads & Footpaths">Roads & Footpaths</option>
          </select>
        </div>

        <div class="form-group">
          <label for="landmark">Location / Landmark</label>
          <input type="text" id="landmark" name="landmark" placeholder="Street name, landmark, ward number" />
        </div>

        <div class="form-group">
          <label for="description">Grievance Description</label>
          <textarea id="description" name="description" rows="3" placeholder="Provide detailed description of civic accumulation..."></textarea>
        </div>

        <div class="form-group">
          <label for="evidence-file">Attach Photographic Evidence (Multiple)</label>
          <input type="file" id="evidence-file" name="evidence" accept="image/*" multiple />
        </div>

        <button type="button" id="btn-submit" class="btn-success" onclick="submitGrievance()">Register Complaint</button>
      </div>

      <!-- Step 3: Confirmation Banner -->
      <div id="confirmation-banner" class="alert-success hidden">
        Citizen Grievance Registered Successfully!
        <strong id="ref-token">PMC-SW-2026-89102</strong>
      </div>
    </div>
  </div>

  <script>
    function sendOtp() {
      document.getElementById('otp-hint').classList.remove('hidden');
      document.getElementById('otp-section').classList.remove('hidden');
      document.getElementById('otp-input').focus();
    }

    function verifyOtp() {
      const otpVal = document.getElementById('otp-input').value.trim();
      if (otpVal.length >= 4) {
        document.getElementById('otp-verified-msg').classList.remove('hidden');
        document.getElementById('complaint-section').classList.remove('hidden');
      } else {
        alert('Please enter a valid OTP code.');
      }
    }

    function submitGrievance() {
      const randNum = Math.floor(10000 + Math.random() * 90000);
      const token = 'PMC-SW-2026-' + randNum;
      document.getElementById('ref-token').innerText = token;
      document.getElementById('confirmation-banner').classList.remove('hidden');
      document.getElementById('btn-submit').disabled = true;
      document.getElementById('btn-submit').innerText = 'Submitted';
    }
  </script>
</body>
</html>
"""

@mock_router.get("/mock-pmc-portal", response_class=HTMLResponse)
async def get_mock_portal():
    return HTMLResponse(content=MOCK_PORTAL_HTML, status_code=200)
