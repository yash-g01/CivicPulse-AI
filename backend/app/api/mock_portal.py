import os
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse
from app.core.dynamodb import list_all_tickets, find_ticket_by_token, update_ticket_status, get_ticket
from app.core.s3 import upload_image_bytes, get_image_bytes, generate_presigned_view_url
from app.services.audit_service import audit_resolution_images

mock_router = APIRouter()

MOCK_PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pune Municipal Corporation (PMC) - Citizen Grievance Redressal Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: #f1f5f9; color: #1e293b; padding: 24px 16px; min-height: 100vh; }
    .container { max-width: 820px; margin: 0 auto; background: #ffffff; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.07); overflow: hidden; border: 1px solid #e2e8f0; }
    
    /* Header */
    .header { background: #1e3a8a; color: #ffffff; padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; }
    .header-left { display: flex; align-items: center; gap: 16px; }
    .header-badge { width: 44px; height: 44px; border-radius: 8px; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }
    .header h1 { font-size: 18px; font-weight: 700; line-height: 1.3; }
    .header p { font-size: 13px; color: #bfdbfe; margin-top: 2px; }
    .header-portal-tag { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); font-size: 11px; padding: 4px 8px; border-radius: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Navigation Tabs */
    .nav-tabs { display: flex; background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 0 16px; gap: 8px; }
    .nav-tab { padding: 14px 20px; font-size: 14px; font-weight: 600; color: #64748b; background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 8px; }
    .nav-tab:hover { color: #1e3a8a; }
    .nav-tab.active { color: #1e3a8a; border-bottom-color: #2563eb; background: #ffffff; }

    /* Body */
    .form-body { padding: 24px; display: flex; flex-direction: column; gap: 20px; }
    .section-title { font-size: 14px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }
    .form-group { display: flex; flex-direction: column; gap: 6px; }
    label { font-size: 13px; font-weight: 600; color: #334155; }
    input, select, textarea { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; }
    input:focus, select:focus, textarea:focus { border-color: #2563eb; outline: none; }
    .input-row { display: flex; gap: 10px; align-items: center; }
    
    /* Buttons */
    button { padding: 10px 16px; font-size: 14px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: all 0.2s; border: none; white-space: nowrap; }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-success { background: #16a34a; color: #ffffff; width: 100%; padding: 12px; font-size: 15px; margin-top: 8px; }
    .btn-success:hover { background: #15803d; }
    .btn-danger { background: #dc2626; color: #ffffff; }
    .btn-danger:hover { background: #b91c1c; }
    .btn-secondary { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; }
    .btn-secondary:hover { background: #e2e8f0; }

    /* Badges & Alerts */
    .badge-otp { background: #eff6ff; color: #1d4ed8; border: 1px dashed #93c5fd; padding: 8px 12px; border-radius: 6px; font-size: 13px; display: inline-block; margin-top: 6px; }
    .alert-success { background: #f0fdf4; border: 1px solid #86efac; color: #166534; padding: 16px; border-radius: 8px; text-align: center; font-size: 15px; }
    .alert-success strong { font-size: 17px; display: block; margin-top: 4px; color: #14532d; }
    .alert-fraud { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; padding: 16px; border-radius: 8px; font-size: 14px; line-height: 1.5; }
    .alert-fraud strong { font-size: 16px; display: block; margin-bottom: 4px; color: #7f1d1d; }
    .alert-verified { background: #ecfdf5; border: 1px solid #6ee7b7; color: #065f46; padding: 16px; border-radius: 8px; font-size: 14px; line-height: 1.5; }
    .alert-verified strong { font-size: 16px; display: block; margin-bottom: 4px; color: #047857; }

    /* Track Status Styles */
    .search-box { display: flex; gap: 10px; }
    .search-box input { font-family: monospace; font-size: 15px; font-weight: 600; letter-spacing: 0.5px; }
    .quick-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 8px; }
    .chip { background: #e2e8f0; color: #334155; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 100px; cursor: pointer; border: 1px solid transparent; transition: all 0.2s; }
    .chip:hover { background: #cbd5e1; border-color: #94a3b8; }

    /* Docket Table */
    .docket-container { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-top: 10px; }
    .docket-header { background: #f8fafc; padding: 10px 14px; font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
    .docket-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .docket-table th { background: #f1f5f9; padding: 10px 12px; text-align: left; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; }
    .docket-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    .docket-table tr:hover { background: #f8fafc; cursor: pointer; }
    .docket-table tr.selected { background: #eff6ff; }
    
    .status-pill { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 100px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; }
    .pill-submitted { background: #e0f2fe; color: #0369a1; }
    .pill-reopened { background: #fee2e2; color: #b91c1c; }
    .pill-clean { background: #dcfce7; color: #15803d; }
    .pill-email { background: #f3e8ff; color: #7e22ce; }
    .pill-inflight { background: #fef3c7; color: #b45309; }

    /* Detail Card */
    .detail-card { border: 1px solid #cbd5e1; border-radius: 10px; padding: 20px; background: #ffffff; margin-top: 16px; }
    .detail-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 14px; }
    .detail-token { font-family: monospace; font-size: 20px; font-weight: 800; color: #1e3a8a; }
    .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 13px; }
    .detail-field dt { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }
    .detail-field dd { font-weight: 600; color: #1e293b; }

    /* Evidence Box */
    .evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 16px; }
    .evidence-box { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc; text-align: center; }
    .evidence-box img { width: 100%; height: 180px; object-fit: cover; display: block; }
    .evidence-label { padding: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; background: #f1f5f9; color: #475569; }

    /* Resolution Bay */
    .resolution-bay { margin-top: 20px; border: 2px dashed #93c5fd; background: #eff6ff; border-radius: 10px; padding: 18px; }
    .resolution-title { font-size: 14px; font-weight: 700; color: #1e3a8a; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
    .quick-test-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; margin-bottom: 12px; }
    .btn-quick { font-size: 12px; padding: 6px 12px; border-radius: 6px; font-weight: 600; }

    .hidden { display: none !important; }
    .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-left">
        <div class="header-badge">PMC</div>
        <div>
          <h1>Pune Municipal Corporation</h1>
          <p>Public Grievance Redressal Gateway (Solid Waste & Health Dept)</p>
        </div>
      </div>
      <div class="header-portal-tag">Official Redressal Portal</div>
    </div>

    <!-- Navigation Tabs -->
    <div class="nav-tabs">
      <button type="button" id="tab-register" class="nav-tab active" onclick="switchTab('register')">
        📝 Register Grievance
      </button>
      <button type="button" id="tab-track" class="nav-tab" onclick="switchTab('track')">
        🔍 Track Status & Field Resolution
      </button>
    </div>

    <!-- Tab 1: Grievance Registration Form -->
    <div id="section-register" class="form-body">
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
        <p style="margin-top: 10px; font-size: 13px;">
          <a href="javascript:void(0)" onclick="trackNewlyFiledToken()" style="color: #15803d; font-weight: 700; text-decoration: underline;">Track this ticket in Field Redressal Desk →</a>
        </p>
      </div>
    </div>

    <!-- Tab 2: Track Status & Field Resolution (NEW!) -->
    <div id="section-track" class="form-body hidden">
      <!-- Search Bar -->
      <div>
        <div class="section-title">Track Grievance Status by Token Number</div>
        <div class="search-box">
          <input type="text" id="token-search-input" placeholder="Enter Token (e.g. PMC-SW-2026-89102 or ticket ID)" value="PMC-SW-2026-89102" />
          <button type="button" id="btn-search-token" class="btn-primary" onclick="searchToken()">Search Ticket</button>
        </div>
        <div class="quick-chips">
          <span style="font-size: 11px; font-weight: 600; color: #64748b;">Quick search:</span>
          <span class="chip" onclick="quickFillToken('PMC-SW-2026-89102')">PMC-SW-2026-89102</span>
          <span class="chip" onclick="quickFillToken('028972bd')">Ticket #028972bd</span>
          <span class="chip" onclick="quickFillToken('5644b9e2')">Ticket #5644b9e2</span>
        </div>
      </div>

      <!-- Docket Table (List of Tokens) -->
      <div>
        <div class="section-title" style="display:flex; justify-content:space-between; align-items:center;">
          <span>Municipal Grievance Registry & Tokens</span>
          <button type="button" class="btn-secondary" style="font-size:11px; padding:4px 8px;" onclick="loadDocketTokens()">↻ Refresh</button>
        </div>
        <div class="docket-container">
          <div class="docket-header">
            <span>Recent Filed Grievances</span>
            <span id="docket-count" style="font-size: 11px; color: #64748b;">Loading tokens...</span>
          </div>
          <div style="max-height: 220px; overflow-y: auto;">
            <table class="docket-table">
              <thead>
                <tr>
                  <th>Token Number</th>
                  <th>Complainant / Contact</th>
                  <th>Landmark</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="docket-table-body">
                <tr><td colspan="5" style="text-align: center; color: #64748b; padding: 18px;">Loading registered municipal tokens...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Selected Grievance Inspection Card -->
      <div id="token-detail-card" class="detail-card hidden">
        <div class="detail-header">
          <div>
            <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Municipal Reference Token</div>
            <div id="card-token" class="detail-token">PMC-SW-2026-89102</div>
            <div id="card-date" style="font-size: 12px; color: #64748b; margin-top: 2px;">Filed: 11 Oct 2026</div>
          </div>
          <div id="card-status-badge" class="status-pill pill-submitted">SUBMITTED</div>
        </div>

        <div class="detail-grid">
          <div class="detail-field">
            <dt>Complainant Name</dt>
            <dd id="card-complainant">—</dd>
          </div>
          <div class="detail-field">
            <dt>Registered Mobile</dt>
            <dd id="card-mobile">—</dd>
          </div>
          <div class="detail-field">
            <dt>Ward / Landmark</dt>
            <dd id="card-landmark">—</dd>
          </div>
          <div class="detail-field">
            <dt>Grievance Category</dt>
            <dd id="card-category">Solid Waste Management (SWM)</dd>
          </div>
        </div>

        <div style="margin-top: 14px;">
          <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Citizen Complaint Text</div>
          <p id="card-description" style="font-size: 13px; color: #334155; margin-top: 3px; line-height: 1.4; background: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;"></p>
        </div>

        <!-- Evidence Photos (Before & After) -->
        <div class="evidence-grid">
          <div class="evidence-box">
            <img id="card-img-before" src="/api/v1/mock/sample-image/dump" alt="Citizen Report" />
            <div class="evidence-label">Citizen Complaint Evidence (Before)</div>
          </div>
          <div class="evidence-box">
            <img id="card-img-after" src="/api/v1/mock/sample-image/cleaned" alt="Worker Resolution" />
            <div id="card-img-after-label" class="evidence-label">Field Resolution Evidence (After)</div>
          </div>
        </div>

        <!-- Audit Verdict Banner -->
        <div id="audit-banner-box" style="margin-top: 16px;"></div>

        <!-- Municipal Field Redressal Bay (Upload Resolution Evidence) -->
        <div class="resolution-bay">
          <div class="resolution-title">
            <span>🛡️ Municipal Field Officer Redressal Bay</span>
          </div>
          <p style="font-size: 13px; color: #1e3a8a; line-height: 1.4;">
            Sanitary Inspectors & Contractors must upload photographic evidence of problem resolution before closing this ticket.
            The CivicPulse AI audit engine will cross-examine this photo against the original scene.
          </p>

          <div style="margin-top: 12px;">
            <label style="font-size: 12px; font-weight: 700; color: #1e3a8a;">Quick 1-Click Verification Test:</label>
            <div class="quick-test-actions">
              <button type="button" class="btn-quick" style="background: #16a34a; color: #fff;" onclick="useSampleResolution('clean')">
                ✨ Use Genuine Clean Evidence
              </button>
              <button type="button" class="btn-quick" style="background: #dc2626; color: #fff;" onclick="useSampleResolution('fake')">
                🚨 Use Ghost-Resolution Evidence (Fake/Mismatch)
              </button>
            </div>
          </div>

          <div class="form-group" style="margin-top: 8px;">
            <label for="resolution-file">Or Upload Custom After-Cleanup Photo</label>
            <input type="file" id="resolution-file" accept="image/*" onchange="previewCustomResolution(event)" />
          </div>

          <div id="custom-preview-container" class="hidden" style="margin-top: 10px; text-align: center;">
            <img id="custom-preview-img" style="max-height: 140px; border-radius: 6px; border: 1px solid #cbd5e1;" />
          </div>

          <button type="button" id="btn-submit-resolution" class="btn-success" style="margin-top: 12px;" onclick="submitFieldResolution()">
            Upload Resolution Evidence & Run Forensic Audit
          </button>
          
          <div id="resolution-progress" class="hidden" style="margin-top: 10px; text-align: center; color: #1d4ed8; font-size: 13px; font-weight: 600;">
            <span class="spinner"></span> Auditing resolution evidence via Groq Vision against original citizen scene...
          </div>
        </div>

        <!-- Link to CivicPulse Frontend -->
        <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 12px; color: #64748b;">Updates DynamoDB & triggers frontend verification:</span>
          <a id="btn-open-frontend" href="http://localhost:5173" target="_blank" class="btn-primary" style="font-size: 12px; text-decoration: none; padding: 6px 14px;">
            Open Case in CivicPulse Citizen App ↗
          </a>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentTicket = null;
    let selectedSampleType = null;
    let customFileBlob = null;

    function switchTab(tab) {
      document.getElementById('tab-register').classList.toggle('active', tab === 'register');
      document.getElementById('tab-track').classList.toggle('active', tab === 'track');
      document.getElementById('section-register').classList.toggle('hidden', tab !== 'register');
      document.getElementById('section-track').classList.toggle('hidden', tab !== 'track');

      if (tab === 'track') {
        loadDocketTokens();
      }
    }

    function sendOtp() {
      document.getElementById('otp-hint').classList.remove('hidden');
      document.getElementById('otp-section').classList.remove('hidden');
      document.getElementById('otp-input').focus();
    }

    function verifyOtp() {
      const otpVal = document.getElementById('otp-input').value.trim();
      if (otpVal.length >= 4) {
        document.getElementById('otp-verified-msg').classList.remove('hidden');
        document.getElementById('otp-section').classList.add('hidden');
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

    function trackNewlyFiledToken() {
      const token = document.getElementById('ref-token').innerText;
      switchTab('track');
      document.getElementById('token-search-input').value = token;
      searchToken();
    }

    function quickFillToken(token) {
      document.getElementById('token-search-input').value = token;
      searchToken();
    }

    async function loadDocketTokens() {
      const tableBody = document.getElementById('docket-table-body');
      const countEl = document.getElementById('docket-count');
      try {
        const res = await fetch('/api/v1/mock/tokens');
        if (!res.ok) throw new Error('Could not fetch tokens');
        const data = await res.json();
        
        countEl.innerText = `${data.length} tickets recorded`;
        if (data.length === 0) {
          tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#64748b; padding:16px;">No municipal tickets found.</td></tr>';
          return;
        }

        let html = '';
        data.slice(0, 15).forEach(t => {
          const token = t.token_id || t.municipal_ref_id || ('PMC-SW-2026-' + (t.ticket_id || '').toUpperCase());
          const complainant = t.complainant_name || 'Concerned Citizen';
          const landmark = t.landmark || 'Pune Municipal Area';
          const status = t.status || 'SUBMITTED';

          let pillClass = 'pill-submitted';
          let statusText = status;
          if (status === 'REOPENED_AUDIT_FAILED') {
            pillClass = 'pill-reopened';
            statusText = '⚠️ Ghost Resolution';
          } else if (status === 'CONFIRMED_CLEAN') {
            pillClass = 'pill-clean';
            statusText = '✅ Verified Clean';
          } else if (status === 'EMAIL_FALLBACK_READY') {
            pillClass = 'pill-email';
            statusText = 'Statutory Mail';
          }

          html += `
            <tr onclick="loadTicketDetail('${token}', '${t.ticket_id}')">
              <td><strong style="font-family:monospace; color:#1e3a8a;">${token}</strong></td>
              <td>${complainant}</td>
              <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${landmark}</td>
              <td><span class="status-pill ${pillClass}">${statusText}</span></td>
              <td><button type="button" class="btn-primary" style="font-size:11px; padding:4px 8px;">Inspect & Redress →</button></td>
            </tr>
          `;
        });
        tableBody.innerHTML = html;

        // Auto-load first ticket if none selected
        if (!currentTicket && data.length > 0) {
          loadTicketDetail(data[0].token_id || data[0].municipal_ref_id, data[0].ticket_id);
        }
      } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#dc2626; padding:16px;">Error loading docket: ${err.message}</td></tr>`;
      }
    }

    async function searchToken() {
      const q = document.getElementById('token-search-input').value.trim();
      if (!q) {
        alert('Please enter a reference token or ticket ID.');
        return;
      }
      await loadTicketDetail(q, q);
    }

    async function loadTicketDetail(token, fallbackId) {
      const card = document.getElementById('token-detail-card');
      const searchInput = document.getElementById('token-search-input');
      searchInput.value = token;

      try {
        const res = await fetch(`/api/v1/mock/tokens/${encodeURIComponent(token)}`);
        if (!res.ok) {
          // If not found by token, try fallback ID
          const res2 = await fetch(`/api/v1/tickets/${encodeURIComponent(fallbackId || token)}`);
          if (!res2.ok) throw new Error('Ticket not found in municipal records');
          currentTicket = await res2.json();
        } else {
          currentTicket = await res.json();
        }

        renderTicketDetail(currentTicket);
        card.classList.remove('hidden');
        card.scrollIntoView({ behavior: 'smooth' });
      } catch (err) {
        alert('Grievance not found: ' + err.message);
      }
    }

    function renderTicketDetail(t) {
      const tid = t.ticket_id || (t.PK ? t.PK.replace('TICKET#', '') : 'UNKNOWN');
      const token = t.municipal_ref_id || t.token_id || (t.filed_fields && t.filed_fields.reference_token) || ('PMC-SW-2026-' + tid.toUpperCase());

      document.getElementById('card-token').innerText = token;
      document.getElementById('card-complainant').innerText = t.user_name || (t.filed_fields && t.filed_fields.complainant_name) || 'Concerned Citizen';
      const rawMobile = String(t.user_phone || (t.filed_fields && t.filed_fields.mobile_number) || 'Protected');
      document.getElementById('card-mobile').innerText = rawMobile.includes('••') ? rawMobile : (rawMobile.length >= 4 ? '••••••' + rawMobile.slice(-4) : 'Protected');
      document.getElementById('card-landmark').innerText = t.landmark || (t.triage && t.triage.landmark_context) || 'Roadside civic accumulation';
      document.getElementById('card-category').innerText = (t.triage && t.triage.waste_categories && t.triage.waste_categories[0]) ? t.triage.waste_categories[0].replace(/_/g, ' ') : 'Solid Waste Management (SWM)';
      document.getElementById('card-description').innerText = t.complaint_text || (t.triage && t.triage.complaint_text) || 'Chronic unsegregated waste accumulation reported.';

      // Format date
      if (t.created_at) {
        let ts = Number(t.created_at);
        if (ts < 1e11) ts = ts * 1000;
        document.getElementById('card-date').innerText = 'Filed: ' + new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
      }

      // Status Badge
      const statusBadge = document.getElementById('card-status-badge');
      const status = t.status || 'SUBMITTED';
      statusBadge.className = 'status-pill';
      if (status === 'REOPENED_AUDIT_FAILED') {
        statusBadge.classList.add('pill-reopened');
        statusBadge.innerText = '🚨 REOPENED (GHOST RESOLUTION)';
      } else if (status === 'CONFIRMED_CLEAN') {
        statusBadge.classList.add('pill-clean');
        statusBadge.innerText = '✅ CONFIRMED CLEAN';
      } else if (status === 'EMAIL_FALLBACK_READY') {
        statusBadge.classList.add('pill-email');
        statusBadge.innerText = 'STATUTORY EMAIL READY';
      } else {
        statusBadge.classList.add('pill-submitted');
        statusBadge.innerText = status;
      }

      // Evidence Before image
      const beforeImg = document.getElementById('card-img-before');
      beforeImg.src = t.evidence_url || `/api/v1/evidence/${tid}/before`;

      // Evidence After image
      const afterImg = document.getElementById('card-img-after');
      const afterLabel = document.getElementById('card-img-after-label');
      if (t.after_url || t.after_s3_key) {
        afterImg.src = t.after_url || `/api/v1/evidence/${tid}/after`;
        afterLabel.innerText = 'Field Resolution Evidence (Audited)';
      } else {
        afterImg.src = '/api/v1/mock/sample-image/cleaned';
        afterLabel.innerText = 'Sample Reference (Awaiting Field Upload)';
      }

      // Render Audit Verdict if audited
      renderAuditVerdict(t.audit, status);

      // Frontend link
      document.getElementById('btn-open-frontend').href = `https://localhost:5173/t/${tid}`;
    }

    function renderAuditVerdict(audit, status) {
      const box = document.getElementById('audit-banner-box');
      if (!audit && status !== 'REOPENED_AUDIT_FAILED' && status !== 'CONFIRMED_CLEAN') {
        box.innerHTML = '';
        return;
      }

      const isFraud = (audit && (audit.fraud_detected || !audit.debris_cleared)) || status === 'REOPENED_AUDIT_FAILED';
      if (isFraud) {
        const notes = audit ? audit.discrepancy_notes : 'The resolution photo depicts a completely different location or debris is still present.';
        const conf = audit && audit.confidence ? Math.round(audit.confidence * 100) : 96;
        box.innerHTML = `
          <div class="alert-fraud">
            <strong>🛑 GHOST-RESOLUTION FRAUD DETECTED (MUNICIPAL TICKET REOPENED)</strong>
            <div>${notes}</div>
            <div style="margin-top: 6px; font-size: 12px; font-weight: 700; opacity: 0.85;">
              Same Scene: ❌ No &nbsp;|&nbsp; Debris Cleared: ❌ No &nbsp;|&nbsp; Audit Confidence: ${conf}%
            </div>
          </div>
        `;
      } else {
        const notes = audit ? audit.discrepancy_notes : 'Landmarks match and the waste pile has been verified cleared.';
        const conf = audit && audit.confidence ? Math.round(audit.confidence * 100) : 92;
        box.innerHTML = `
          <div class="alert-verified">
            <strong>✅ AUTHENTIC RESOLUTION VERIFIED (CLEANUP CONFIRMED)</strong>
            <div>${notes}</div>
            <div style="margin-top: 6px; font-size: 12px; font-weight: 700; opacity: 0.85;">
              Same Scene: ✓ Yes &nbsp;|&nbsp; Debris Cleared: ✓ Yes &nbsp;|&nbsp; Audit Confidence: ${conf}%
            </div>
          </div>
        `;
      }
    }

    function useSampleResolution(type) {
      selectedSampleType = type;
      customFileBlob = null;
      document.getElementById('resolution-file').value = '';
      document.getElementById('custom-preview-container').classList.add('hidden');

      const afterImg = document.getElementById('card-img-after');
      afterImg.src = type === 'clean' ? '/api/v1/mock/sample-image/cleaned' : '/api/v1/mock/sample-image/fake_clean';
      document.getElementById('card-img-after-label').innerText = type === 'clean' ? 'Selected: Genuine Clean Site Evidence' : 'Selected: Ghost Resolution Fake Evidence';
    }

    function previewCustomResolution(event) {
      const file = event.target.files[0];
      if (!file) return;
      selectedSampleType = null;
      customFileBlob = file;

      const url = URL.createObjectURL(file);
      document.getElementById('custom-preview-img').src = url;
      document.getElementById('custom-preview-container').classList.remove('hidden');

      document.getElementById('card-img-after').src = url;
      document.getElementById('card-img-after-label').innerText = 'Uploaded: Custom Field Evidence';
    }

    async function submitFieldResolution() {
      if (!currentTicket) {
        alert('Please select a ticket first.');
        return;
      }

      const tid = currentTicket.ticket_id || (currentTicket.PK ? currentTicket.PK.replace('TICKET#', '') : '');
      const btn = document.getElementById('btn-submit-resolution');
      const progress = document.getElementById('resolution-progress');

      btn.disabled = true;
      progress.classList.remove('hidden');

      try {
        const formData = new FormData();
        if (customFileBlob) {
          formData.append('after_image', customFileBlob);
        } else if (selectedSampleType) {
          formData.append('sample_type', selectedSampleType);
        } else {
          // Default to fake or clean if none chosen
          formData.append('sample_type', 'fake');
        }

        const res = await fetch(`/api/v1/mock/tokens/${encodeURIComponent(tid)}/resolve`, {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Resolution upload failed.');
        }

        const result = await res.json();
        currentTicket = result;
        renderTicketDetail(currentTicket);
        loadDocketTokens(); // Refresh table status

        // Scroll up to audit banner
        document.getElementById('audit-banner-box').scrollIntoView({ behavior: 'smooth' });
      } catch (err) {
        alert('Audit error: ' + err.message);
      } finally {
        btn.disabled = false;
        progress.classList.add('hidden');
      }
    }

    // Initial Load
    window.addEventListener('DOMContentLoaded', () => {
      // Check URL hash
      if (window.location.hash === '#track') {
        switchTab('track');
      }
    });
  </script>
</body>
</html>
"""

@mock_router.get("/mock-pmc-portal", response_class=HTMLResponse)
async def get_mock_portal():
    return HTMLResponse(content=MOCK_PORTAL_HTML, status_code=200)


def _mask_mobile(phone: Optional[str]) -> str:
    if not phone:
        return "Protected"
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) >= 4:
        return f"••••••{digits[-4:]}"
    return "••••••••••"

@mock_router.get("/api/v1/mock/tokens")
async def get_mock_tokens():
    """Returns a list of filed tickets formatted for the mock portal docket with masked citizen mobile."""
    tickets = await asyncio.to_thread(list_all_tickets)
    results = []
    for t in tickets:
        tid = t.get("ticket_id") or t.get("PK", "").replace("TICKET#", "")
        if not tid:
            continue
        token_id = t.get("municipal_ref_id") or t.get("filed_fields", {}).get("reference_token") or f"PMC-SW-2026-{tid.upper()}"
        results.append({
            "token_id": token_id,
            "ticket_id": tid,
            "municipal_ref_id": t.get("municipal_ref_id"),
            "complainant_name": t.get("user_name") or t.get("filed_fields", {}).get("complainant_name") or "Concerned Citizen",
            "mobile": _mask_mobile(t.get("user_phone")),
            "landmark": t.get("landmark") or t.get("triage", {}).get("landmark_context") or "Pune Municipal Area",
            "status": t.get("status") or "SUBMITTED",
            "created_at": t.get("created_at"),
            "evidence_url": t.get("evidence_url") or f"/api/v1/evidence/{tid}/before",
            "after_url": t.get("after_url"),
            "audit": t.get("audit")
        })
    return results


@mock_router.get("/api/v1/mock/tokens/{token_query}")
async def get_mock_token_detail(token_query: str):
    """Searches for a single ticket by token or ID for the mock portal inspector with masked citizen contact."""
    ticket = await asyncio.to_thread(find_ticket_by_token, token_query)
    if not ticket:
        ticket = await asyncio.to_thread(get_ticket, token_query)
    if not ticket:
        raise HTTPException(status_code=404, detail="Token or ticket not found.")

    sanitized = dict(ticket)
    tid = sanitized.get("ticket_id") or sanitized.get("PK", "").replace("TICKET#", "")
    sanitized["ticket_id"] = tid
    if sanitized.get("user_phone"):
        sanitized["user_phone"] = _mask_mobile(sanitized.get("user_phone"))
    if isinstance(sanitized.get("filed_fields"), dict):
        ff = dict(sanitized["filed_fields"])
        if ff.get("mobile_number"):
            ff["mobile_number"] = _mask_mobile(ff.get("mobile_number"))
        sanitized["filed_fields"] = ff
    if not sanitized.get("evidence_url"):
        sanitized["evidence_url"] = f"/api/v1/evidence/{tid}/before"
    return sanitized


@mock_router.post("/api/v1/mock/tokens/{token_query}/resolve")
async def resolve_mock_token(
    token_query: str,
    after_image: Optional[UploadFile] = File(None),
    sample_type: Optional[str] = Form(None)
):
    """
    Submits problem resolution evidence for a municipal token.
    Runs Groq Vision forensic audit to detect ghost-resolution,
    and updates DynamoDB ticket so the frontend displays the verified or flagged status.
    """
    ticket = await asyncio.to_thread(find_ticket_by_token, token_query)
    if not ticket:
        ticket = await asyncio.to_thread(get_ticket, token_query)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Token '{token_query}' not found.")

    actual_ticket_id = ticket.get("ticket_id") or ticket.get("PK", "").replace("TICKET#", "")
    os.makedirs("/tmp/civicpulse", exist_ok=True)
    after_path = f"/tmp/civicpulse/{actual_ticket_id}_after.jpg"

    # Read image from file upload or sample fixture
    if after_image:
        content = await after_image.read()
        filename = after_image.filename or "after.jpg"
        after_path = f"/tmp/civicpulse/{actual_ticket_id}_{filename}"
        with open(after_path, "wb") as f:
            f.write(content)
        after_bytes = content
    elif sample_type == "clean":
        sample_file = "tests/cleaned.jpg" if os.path.exists("tests/cleaned.jpg") else "backend/tests/cleaned.jpg"
        with open(sample_file, "rb") as f:
            after_bytes = f.read()
        after_path = f"/tmp/civicpulse/{actual_ticket_id}_cleaned.jpg"
        with open(after_path, "wb") as f:
            f.write(after_bytes)
    else:  # fake / ghost sample
        sample_file = "tests/fake_clean.jpg" if os.path.exists("tests/fake_clean.jpg") else "backend/tests/fake_clean.jpg"
        with open(sample_file, "rb") as f:
            after_bytes = f.read()
        after_path = f"/tmp/civicpulse/{actual_ticket_id}_fake_clean.jpg"
        with open(after_path, "wb") as f:
            f.write(after_bytes)

    # Fetch initial complaint evidence photo
    before_path = f"/tmp/civicpulse/{actual_ticket_id}_before.jpg"
    if not os.path.exists(before_path):
        before_s3_key = ticket.get("before_s3_key")
        if before_s3_key:
            try:
                before_bytes = await asyncio.to_thread(get_image_bytes, before_s3_key)
                with open(before_path, "wb") as f:
                    f.write(before_bytes)
            except Exception as ex:
                print(f"[{actual_ticket_id}] Could not fetch before image from S3: {ex}")

    # Fallback to test fixture if local before image is missing
    if not os.path.exists(before_path):
        for candidate in ["tests/dump.jpeg", "backend/tests/dump.jpeg"]:
            if os.path.exists(candidate):
                import shutil
                shutil.copy(candidate, before_path)
                break

    if not os.path.exists(before_path):
        raise HTTPException(status_code=400, detail="Original complaint image unavailable for audit comparison.")

    # Upload after image to S3 (non-blocking on failure)
    after_s3_key = f"evidence/{actual_ticket_id}_after.jpg"
    try:
        await asyncio.to_thread(upload_image_bytes, after_s3_key, after_bytes)
    except Exception as s3_err:
        print(f"[{actual_ticket_id}] S3 after upload notice: {s3_err}")

    after_url = ""
    try:
        after_url = generate_presigned_view_url(after_s3_key)
    except Exception:
        pass
    if not after_url:
        after_url = f"/api/v1/evidence/{actual_ticket_id}/after"

    # Run AI forensic audit
    audit_data = await asyncio.to_thread(audit_resolution_images, before_path, after_path)

    # Determine status transition
    is_fraud = audit_data.get("fraud_detected") or not audit_data.get("debris_cleared")
    if is_fraud:
        new_status = "REOPENED_AUDIT_FAILED"
        summary_msg = f"⚠️ Ghost-resolution detected on mock portal: {audit_data.get('discrepancy_notes')}"
    elif audit_data.get("debris_cleared") and audit_data.get("is_same_scene"):
        new_status = "CONFIRMED_CLEAN"
        summary_msg = f"✅ Genuine cleanup verified on mock portal: {audit_data.get('discrepancy_notes')}"
    else:
        new_status = "REOPENED_AUDIT_FAILED"
        summary_msg = f"⚠️ Evidence inconclusive: {audit_data.get('discrepancy_notes')}"

    updates = {
        "status": new_status,
        "after_s3_key": after_s3_key,
        "after_url": after_url,
        "audit": audit_data,
        "agent_summary": summary_msg,
        "agent_telemetry": f"Mock portal resolution submitted. Audit result: {new_status}."
    }
    await asyncio.to_thread(update_ticket_status, actual_ticket_id, updates)

    updated_ticket = await asyncio.to_thread(get_ticket, actual_ticket_id)
    return updated_ticket or {
        "ticket_id": actual_ticket_id,
        "status": new_status,
        "audit": audit_data,
        "after_url": after_url
    }


@mock_router.get("/api/v1/mock/sample-image/{sample_name}")
async def get_mock_sample_image(sample_name: str):
    """Serves sample image files for mock portal quick test actions."""
    name = sample_name.lower().strip()
    mapping = {
        "cleaned": ["tests/cleaned.jpg", "backend/tests/cleaned.jpg"],
        "fake_clean": ["tests/fake_clean.jpg", "backend/tests/fake_clean.jpg"],
        "dump": ["tests/dump.jpeg", "backend/tests/dump.jpeg"],
    }
    for candidate in mapping.get(name, []):
        if os.path.exists(candidate):
            with open(candidate, "rb") as f:
                return Response(content=f.read(), media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Sample image not found.")
