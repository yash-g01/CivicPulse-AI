import { ExternalLink, Mail, UserCheck } from "lucide-react"
import { useEffect, useState } from "react"
import { confirmLogin, getTicket, submitOtp } from "../api"
import { formatCategories, isInFlight, severityWords, statusCopy } from "../status"
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
              Citizen: <strong>{ticket?.user_name || "Concerned Citizen"}</strong> · Contact: {ticket?.user_phone || "On file"}
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
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold">Agent</p>
            <p className="mt-2 font-mono text-[13px] leading-relaxed text-paper/90">
              {ticket?.agent_telemetry || ticket?.agent_summary || "Waiting for the filing worker…"}
            </p>
            {ticket?.municipal_ref_id && (
              <p className="mt-3 font-display text-2xl text-gold">{ticket.municipal_ref_id}</p>
            )}
          </article>
        </div>
      </div>

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
