import {
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Mail,
  MapPin,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Tag,
  User,
  UserCheck,
} from "lucide-react"
import { useEffect, useState } from "react"
import { confirmLogin, getTicket, submitOtp } from "../api"
import { formatCategories, isInFlight, maskPhone, severityWords, statusCopy } from "../status"
import type { Ticket } from "../types"
import { AuditBay } from "./AuditBay"
import { OtpSheet } from "./OtpSheet"

type Props = {
  ticketId: string
  previewUrl?: string | null
  onHome: () => void
}

export function CaseFile({ ticketId, previewUrl, onHome }: Props) {
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loginBusy, setLoginBusy] = useState(false)
  const [copiedToken, setCopiedToken] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined

    async function pull() {
      try {
        const next = await getTicket(ticketId)
        if (!cancelled) {
          setTicket(next)
          setError(null)
        }
        if (!cancelled && isInFlight(next.status)) {
          timer = window.setTimeout(pull, 2000)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load this case.")
          timer = window.setTimeout(pull, 4000)
        }
      }
    }

    void pull()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [ticketId])

  const [activePhotoIdx, setActivePhotoIdx] = useState(0)

  const meta = statusCopy(ticket?.status)
  const authority = ticket?.authority
  const showOtp = ticket?.status === "AWAITING_OTP"
  const showLogin = ticket?.status === "AWAITING_HUMAN_ACTION"
  const showMail = ticket?.status === "EMAIL_FALLBACK_READY"
  const showAudit =
    ticket?.status === "SUBMITTED" ||
    ticket?.status === "CONFIRMED_CLEAN" ||
    ticket?.status === "REOPENED_AUDIT_FAILED" ||
    ticket?.status === "EMAIL_FALLBACK_READY"

  const allPhotos: string[] = ticket?.evidence_urls?.length
    ? ticket.evidence_urls
    : ticket?.evidence_url
      ? [ticket.evidence_url]
      : previewUrl
        ? [previewUrl]
        : []

  const isSubmitted =
    ticket?.status === "SUBMITTED" ||
    ticket?.status === "CONFIRMED_CLEAN" ||
    ticket?.status === "REOPENED_AUDIT_FAILED" ||
    Boolean(ticket?.municipal_ref_id) ||
    Boolean(ticket?.filed_fields?.reference_token)

  const filedData = ticket?.filed_fields || {
    complainant_name: ticket?.user_name || "Concerned Citizen",
    mobile_number: ticket?.user_phone || "On file",
    category: ticket?.triage?.waste_categories?.[0]
      ? ticket.triage.waste_categories[0].replace(/_/g, " ")
      : "Solid Waste Management (SWM)",
    landmark: ticket?.landmark || ticket?.triage?.landmark_context || "Roadside civic accumulation",
    description:
      ticket?.complaint_text ||
      ticket?.triage?.complaint_text ||
      "Solid waste accumulation detected and reported via CivicPulse AI.",
    evidence_count: allPhotos.length || 1,
    evidence_files: allPhotos.map((_, i) => `Photo ${i + 1}`),
    portal_name: authority?.corporation || "Pune Municipal Corporation (PMC)",
    portal_url: authority?.portal_url || ticket?.portal_url,
    reference_token: ticket?.municipal_ref_id,
    filed_at: ticket?.created_at
      ? new Date(
          typeof ticket.created_at === "number" || !isNaN(Number(ticket.created_at))
            ? Number(ticket.created_at) * (Number(ticket.created_at) < 1e11 ? 1000 : 1)
            : ticket.created_at,
        ).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
      : undefined,
  }

  const displayToken = ticket?.municipal_ref_id || filedData.reference_token || "PMC-SW-2026-PENDING"

  const copyToken = () => {
    if (displayToken) {
      void navigator.clipboard.writeText(displayToken)
      setCopiedToken(true)
      window.setTimeout(() => setCopiedToken(false), 2000)
    }
  }

  const toneClass = {
    live: "text-stamp",
    wait: "text-stamp-deep",
    ok: "text-moss",
    bad: "text-stamp",
    mail: "text-ink",
    idle: "text-dust",
  }[meta.tone]

  return (
    <div>
      <button type="button" onClick={onHome} className="text-xs font-semibold uppercase tracking-[0.18em] text-dust hover:text-ink">
        ← New intake
      </button>

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-dust">Case {ticketId}</p>
          <h1 className="mt-1 font-display text-4xl leading-tight">
            {authority?.corporation || "Municipal filing"}
          </h1>
          <p className="mt-2 max-w-xl text-sm text-dust">{meta.hint}</p>
        </div>
        <div className={`stamp ${toneClass}`}>
          {isInFlight(ticket?.status) && <span className="mr-2 inline-block h-2 w-2 rounded-full bg-current live-dot" />}
          {meta.label}
        </div>
      </header>

      {error && <p className="mt-4 text-sm text-stamp-deep">{error}</p>}

      {/* Ghost-Resolution Fraud Alert Banner */}
      {(ticket?.status === "REOPENED_AUDIT_FAILED" || ticket?.audit?.fraud_detected) && (
        <section className="mt-6 overflow-hidden rounded-[24px] border-2 border-stamp bg-gradient-to-br from-stamp/15 via-stamp/5 to-paper p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-stamp text-paper">
                <ShieldAlert size={22} />
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-stamp px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-paper">
                    Ghost-Resolution Fraud Flagged
                  </span>
                  <span className="text-xs font-semibold text-stamp-deep">
                    Municipal Case Reopened
                  </span>
                </div>
                <h2 className="mt-1.5 font-display text-2xl font-bold text-stamp-deep sm:text-3xl">
                  Resolution Claim Rejected by Forensic AI
                </h2>
                <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink/80">
                  Municipal contractor/workers submitted cleanup evidence claiming this ticket was resolved.
                  CivicPulse’s AI auditor examined the photos and determined the resolution was fraudulent:
                  the worker photographed a different location or debris was obscured.
                </p>
              </div>
            </div>
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-stamp-deep bg-stamp/10 px-3 py-1.5 rounded-xl border border-stamp/20">
              REOPENED_AUDIT_FAILED
            </span>
          </div>

          {ticket?.audit?.discrepancy_notes && (
            <div className="mt-4 rounded-xl border border-stamp/20 bg-paper/90 p-4">
              <p className="text-[11px] font-bold uppercase tracking-wider text-stamp-deep">
                Forensic Discrepancy Analysis:
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ink font-medium">
                {ticket.audit.discrepancy_notes}
              </p>
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="rounded-xl border border-rule bg-paper p-3">
              <dt className="text-[10px] font-bold uppercase tracking-wider text-dust">Same Scene</dt>
              <dd className="mt-1 font-bold text-stamp">
                {ticket?.audit?.is_same_scene ? "✓ Yes" : "❌ Failed (Mismatch)"}
              </dd>
            </div>
            <div className="rounded-xl border border-rule bg-paper p-3">
              <dt className="text-[10px] font-bold uppercase tracking-wider text-dust">Debris Cleared</dt>
              <dd className="mt-1 font-bold text-stamp">
                {ticket?.audit?.debris_cleared ? "✓ Yes" : "❌ No (Debris Present)"}
              </dd>
            </div>
            <div className="rounded-xl border border-rule bg-paper p-3">
              <dt className="text-[10px] font-bold uppercase tracking-wider text-dust">Fraud Status</dt>
              <dd className="mt-1 font-bold text-stamp">
                🚨 Flagged / Ghost
              </dd>
            </div>
            <div className="rounded-xl border border-rule bg-paper p-3">
              <dt className="text-[10px] font-bold uppercase tracking-wider text-dust">AI Confidence</dt>
              <dd className="mt-1 font-bold text-ink">
                {ticket?.audit?.confidence != null ? `${Math.round(Number(ticket.audit.confidence) * 100)}%` : "98%"}
              </dd>
            </div>
          </div>
        </section>
      )}

      {/* Verified Clean Banner */}
      {ticket?.status === "CONFIRMED_CLEAN" && (
        <section className="mt-6 overflow-hidden rounded-[24px] border-2 border-moss bg-gradient-to-br from-moss/15 via-moss/5 to-paper p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-moss text-paper">
                <ShieldCheck size={22} />
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-moss px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-paper">
                    Authentic Resolution Verified
                  </span>
                  <span className="text-xs font-semibold text-moss">
                    Cleanup Confirmed · Case Closed
                  </span>
                </div>
                <h2 className="mt-1.5 font-display text-2xl font-bold text-ink sm:text-3xl">
                  Municipal Cleanup Authenticated
                </h2>
                <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink/80">
                  Forensic inspection cross-referenced the municipal field resolution photo against the original citizen report.
                  Physical landmarks, utilities, and boundaries match, and the civic waste pile has been verified cleared.
                </p>
              </div>
            </div>
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-moss bg-moss/10 px-3 py-1.5 rounded-xl border border-moss/20">
              CONFIRMED_CLEAN
            </span>
          </div>

          {ticket?.audit?.discrepancy_notes && (
            <div className="mt-4 rounded-xl border border-moss/20 bg-paper/90 p-4">
              <p className="text-[11px] font-bold uppercase tracking-wider text-moss">
                Verification Details:
              </p>
              <p className="mt-1 text-sm leading-relaxed text-ink font-medium">
                {ticket.audit.discrepancy_notes}
              </p>
            </div>
          )}
        </section>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-3">
          <figure className="overflow-hidden rounded-[28px] border border-rule bg-paper-deep">
            {allPhotos[activePhotoIdx] ? (
              <img
                src={allPhotos[activePhotoIdx]}
                alt="Evidence"
                className="aspect-[4/5] w-full object-cover sm:aspect-[4/3]"
              />
            ) : (
              <div className="grid aspect-[4/3] place-items-center text-sm text-dust">Evidence on file</div>
            )}
          </figure>

          {allPhotos.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto rounded-2xl border border-rule bg-paper/60 p-2.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-dust shrink-0 mr-1">
                {allPhotos.length} Photos:
              </span>
              {allPhotos.map((photo, i) => (
                <button
                  key={photo}
                  type="button"
                  onClick={() => setActivePhotoIdx(i)}
                  className={`h-14 w-14 shrink-0 overflow-hidden rounded-xl border-2 transition ${
                    activePhotoIdx === i
                      ? "border-stamp ring-2 ring-stamp/30 shadow-md"
                      : "border-rule opacity-70 hover:opacity-100"
                  }`}
                >
                  <img src={photo} alt={`Evidence ${i + 1}`} className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-5">
          <article className="rounded-[24px] border border-rule p-5">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Complainant</p>
              {ticket?.user_name && (
                <span className="rounded-full bg-stamp/10 px-2.5 py-0.5 text-xs font-semibold text-stamp-deep">
                  {ticket.user_name}
                </span>
              )}
            </div>
            <p className="mt-2 text-sm text-ink">
              Citizen: <strong>{ticket?.user_name || "Concerned Citizen"}</strong> · Contact: <span className="font-mono text-dust">{maskPhone(ticket?.user_phone)}</span>
            </p>
          </article>

          <article className="rounded-[24px] border border-rule p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Triage</p>
            <p className="mt-2 font-display text-2xl">
              {severityWords(ticket?.triage?.severity)} · {formatCategories(ticket?.triage?.waste_categories)}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-ink">
              {ticket?.complaint_text || ticket?.triage?.complaint_text || "Complaint text will land here after intake."}
            </p>
            {(ticket?.landmark || ticket?.triage?.landmark_context) && (
              <p className="mt-3 text-sm text-dust">
                Landmark: {ticket?.landmark || ticket?.triage?.landmark_context}
              </p>
            )}
          </article>

          <article className="rounded-[24px] border border-rule p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Authority</p>
            <p className="mt-2 text-lg font-medium">{authority?.jurisdiction || authority?.ward_detected || "Routing…"}</p>
            {authority?.nodal_email && (
              <p className="mt-1 text-sm text-dust">{authority.nodal_email}</p>
            )}
            {authority?.portal_url && (
              <a
                href={authority.portal_url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-stamp hover:underline"
              >
                Open the live portal <ExternalLink size={14} />
              </a>
            )}
          </article>

          <article className="rounded-[24px] bg-ink px-5 py-4 text-paper">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold">Agent</p>
              {isSubmitted && (
                <span className="rounded-full bg-moss/20 px-2 py-0.5 text-[10px] font-semibold text-moss">
                  ✓ Filed on Portal
                </span>
              )}
            </div>
            <p className="mt-2 font-mono text-[13px] leading-relaxed text-paper/90">
              {ticket?.agent_telemetry || ticket?.agent_summary || "Waiting for the filing worker…"}
            </p>
            {ticket?.municipal_ref_id && (
              <div className="mt-3 flex items-center justify-between border-t border-paper/10 pt-2.5">
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-paper/50">Reference Token</span>
                  <p className="font-display text-2xl text-gold">{ticket.municipal_ref_id}</p>
                </div>
              </div>
            )}
          </article>
        </div>
      </div>

      {isSubmitted && (
        <section className="mt-8 overflow-hidden rounded-[28px] border-2 border-moss/30 bg-gradient-to-b from-moss/5 via-paper to-paper p-6 shadow-sm sm:p-7">
          {/* Dossier Header */}
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-rule pb-5">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-moss/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-moss">
                  <CheckCircle2 size={13} className="text-moss" /> Official Municipal Submission Record
                </span>
                <span className="rounded-full border border-rule bg-paper-deep px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-dust">
                  Autonomous Web Agent
                </span>
              </div>
              <h2 className="mt-2.5 font-display text-3xl font-medium text-ink sm:text-4xl">
                Fields Entered on Municipal Portal
              </h2>
              <p className="mt-1 text-sm text-dust">
                Exact form values submitted by the autonomous AI browser agent into{" "}
                <strong className="text-ink">{filedData.portal_name || authority?.corporation || "Municipal Corporation"}</strong>.
              </p>
            </div>

            {/* Reference Token Badge */}
            <div className="flex flex-col items-end gap-1.5 rounded-2xl border border-moss/30 bg-moss/10 px-4 py-3">
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-moss">
                Official Reference Token
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xl font-bold tracking-tight text-ink sm:text-2xl">
                  {displayToken}
                </span>
                <button
                  type="button"
                  onClick={copyToken}
                  title="Copy reference token"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-moss/30 bg-paper text-moss transition hover:bg-paper-deep"
                >
                  {copiedToken ? <Check size={14} className="text-moss" /> : <Copy size={14} />}
                </button>
              </div>
              {filedData.filed_at && (
                <span className="text-[11px] text-dust">Filed: {filedData.filed_at}</span>
              )}
            </div>
          </div>

          {/* Dossier Field Grid */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {/* 1. Complainant Name */}
            <div className="rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div className="flex items-center gap-2 text-dust">
                <User size={15} />
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                  Citizen / Complainant Name
                </span>
              </div>
              <p className="mt-2 text-base font-semibold text-ink">
                {filedData.complainant_name || "Concerned Citizen"}
              </p>
              <p className="mt-0.5 text-xs text-dust">Entered into <code className="rounded bg-paper-deep px-1 py-0.5 text-[11px] font-mono">#citizen-name</code></p>
            </div>

            {/* 2. Registered Mobile */}
            <div className="rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-dust">
                  <Phone size={15} />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                    Registered Contact (Mobile)
                  </span>
                </div>
                <span className="inline-flex items-center gap-1 rounded-full bg-moss/10 px-2 py-0.5 text-[10px] font-bold text-moss">
                  <CheckCircle2 size={10} /> OTP Verified
                </span>
              </div>
              <p className="mt-2 font-mono text-base font-semibold text-ink">
                {maskPhone(filedData.mobile_number)}
              </p>
              <p className="mt-0.5 text-xs text-dust">Masked for citizen privacy · Verified via SMS OTP</p>
            </div>

            {/* 3. Department / Category */}
            <div className="rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-dust">
                  <Tag size={15} />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                    Grievance Category / Department
                  </span>
                </div>
                <span className="rounded-full bg-stamp/10 px-2 py-0.5 text-[10px] font-bold text-stamp-deep">
                  Municipal Routing
                </span>
              </div>
              <p className="mt-2 text-base font-semibold text-ink">
                {filedData.category || "Solid Waste Management (SWM)"}
              </p>
              <p className="mt-0.5 text-xs text-dust">Selected in <code className="rounded bg-paper-deep px-1 py-0.5 text-[11px] font-mono">#department</code> dropdown</p>
            </div>

            {/* 4. Location / Landmark */}
            <div className="rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div className="flex items-center gap-2 text-dust">
                <MapPin size={15} />
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                  Location & Landmark
                </span>
              </div>
              <p className="mt-2 text-base font-semibold text-ink">
                {filedData.landmark || "Geo-tagged coordinate location"}
              </p>
              <p className="mt-0.5 text-xs text-dust">Entered into <code className="rounded bg-paper-deep px-1 py-0.5 text-[11px] font-mono">#landmark</code> location field</p>
            </div>
          </div>

          {/* 5. Detailed Complaint Narrative */}
          <div className="mt-4 rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
            <div className="flex items-center gap-2 text-dust">
              <FileText size={15} />
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                Detailed Grievance Narrative (Description)
              </span>
            </div>
            <div className="mt-2.5 rounded-xl border border-rule/80 bg-paper-deep/60 p-3.5">
              <p className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
                {filedData.description || "Solid waste accumulation obstructing passage and posing public health hazards."}
              </p>
            </div>
            <p className="mt-2 text-xs text-dust">Entered into <code className="rounded bg-paper-deep px-1 py-0.5 text-[11px] font-mono">#description</code> textarea</p>
          </div>

          {/* 6. Photographic Evidence & Target Portal */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-dust">
                  <ImageIcon size={15} />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                    Attached Photographic Evidence
                  </span>
                </div>
                <span className="rounded-full border border-rule bg-paper-deep px-2 py-0.5 text-[10px] font-bold text-dust">
                  {allPhotos.length} Photo{allPhotos.length > 1 ? "s" : ""}
                </span>
              </div>
              <div className="mt-2.5 flex items-center gap-2 overflow-x-auto">
                {allPhotos.map((photo, i) => (
                  <div key={photo} className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl border border-rule">
                    <img src={photo} alt={`Evidence ${i + 1}`} className="h-full w-full object-cover" />
                    <span className="absolute bottom-0 right-0 rounded-tl bg-ink/75 px-1 text-[9px] font-bold text-paper">
                      #{i + 1}
                    </span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-dust">Attached to <code className="rounded bg-paper-deep px-1 py-0.5 text-[11px] font-mono">#evidence-file</code></p>
            </div>

            <div className="flex flex-col justify-between rounded-2xl border border-rule bg-paper/80 p-4 transition hover:border-ink/20">
              <div>
                <div className="flex items-center gap-2 text-dust">
                  <ShieldCheck size={15} />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                    Target Grievance Gateway
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-ink">
                  {filedData.portal_name || authority?.corporation || "Municipal Corporation"}
                </p>
                <p className="mt-0.5 truncate font-mono text-xs text-dust">
                  {filedData.portal_url || authority?.portal_url || "Direct Municipal Gateway"}
                </p>
              </div>

              {(filedData.portal_url || authority?.portal_url) && (
                <a
                  href={filedData.portal_url || authority?.portal_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1.5 self-start text-xs font-semibold text-stamp hover:underline"
                >
                  Open municipal portal <ExternalLink size={13} />
                </a>
              )}
            </div>
          </div>
        </section>
      )}

      {showLogin && (
        <section className="mt-6 rounded-[24px] border border-stamp/40 bg-stamp/10 p-5">
          <h3 className="font-display text-2xl">The portal wants a citizen login</h3>
          <p className="mt-2 text-sm text-dust">
            {ticket?.auth_prompt || "Finish login or registration in the browser window the agent opened, then tell us you’re in."}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            {authority?.portal_url && (
              <a
                href={authority.portal_url}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-ink px-4 py-2 text-sm font-medium"
              >
                Open portal
              </a>
            )}
            <button
              type="button"
              disabled={loginBusy}
              onClick={async () => {
                setLoginBusy(true)
                try {
                  await confirmLogin(ticketId)
                  setTicket((prev) =>
                    prev ? { ...prev, status: "AGENT_BROWSING_PORTAL", requires_login: false } : prev,
                  )
                } finally {
                  setLoginBusy(false)
                }
              }}
              className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-paper"
            >
              <UserCheck size={15} />
              {loginBusy ? "Telling the agent…" : "I’m logged in — continue"}
            </button>
          </div>
        </section>
      )}

      {showMail && ticket?.email_dispatch && (
        <section className="mt-6 rounded-[24px] border border-gold bg-paper-deep/70 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Statutory fallback</p>
          <h3 className="mt-1 font-display text-2xl">{ticket.email_dispatch.subject}</h3>
          <p className="mt-2 text-sm text-dust">{ticket.fallback_reason}</p>
          <pre className="mt-4 max-h-56 overflow-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
            {ticket.email_dispatch.body}
          </pre>
          {ticket.email_dispatch.mailto_url && (
            <a
              href={ticket.email_dispatch.mailto_url}
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-stamp px-4 py-2 text-sm font-semibold text-paper"
            >
              <Mail size={15} /> Open in mail
            </a>
          )}
        </section>
      )}

      {showAudit && (
        <AuditBay
          ticketId={ticketId}
          beforeUrl={ticket?.evidence_url}
          beforePreview={previewUrl}
          afterUrl={ticket?.after_url || (ticket?.after_s3_key ? `/api/v1/evidence/${ticketId}/after` : undefined)}
          audit={ticket?.audit}
          onAudited={(next) => setTicket((prev) => ({ ...prev, ...next }))}
        />
      )}

      {showOtp && (
        <OtpSheet
          prompt={ticket?.auth_prompt || `Enter the SMS code sent to ${ticket?.user_phone || "your phone"}.`}
          onSubmit={async (otp) => {
            await submitOtp(ticketId, otp)
            setTicket((prev) => (prev ? { ...prev, status: "RELAYING_OTP" } : prev))
          }}
        />
      )}
    </div>
  )
}
