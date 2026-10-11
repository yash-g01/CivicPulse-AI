import {
  ArrowRight,
  Check,
  Copy,
  ExternalLink,
  FileText,
  Mail,
  MapPin,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  User,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { getAllTickets, getFullApiUrl } from "../api"
import { isInFlight, statusCopy } from "../status"
import type { Ticket, TicketStatus } from "../types"

type Props = {
  onSelectTicket: (ticketId: string) => void
  onNewFiling: () => void
}

type FilterTab = "ALL" | "SUBMITTED" | "GHOST_AUDIT" | "VERIFIED_CLEAN" | "EMAIL" | "IN_FLIGHT"

export function CasesList({ onSelectTicket, onNewFiling }: Props) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState<FilterTab>("ALL")
  const [copiedId, setCopiedId] = useState<string | null>(null)

  async function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)
    try {
      const data = await getAllTickets()
      setTickets(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases.")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  function copyText(text: string, id: string) {
    void navigator.clipboard.writeText(text)
    setCopiedId(id)
    window.setTimeout(() => setCopiedId(null), 1800)
  }

  // KPI Metrics
  const stats = useMemo(() => {
    let portal = 0
    let ghost = 0
    let clean = 0
    let email = 0
    let inFlight = 0

    tickets.forEach((t) => {
      const s = t.status || ""
      if (s === "REOPENED_AUDIT_FAILED" || t.audit?.fraud_detected) ghost++
      else if (s === "CONFIRMED_CLEAN") clean++
      else if (s === "SUBMITTED") portal++
      else if (s === "EMAIL_FALLBACK_READY" || s === "COMPILING_EMAIL_DOSSIER") email++
      else if (isInFlight(s as TicketStatus)) inFlight++
    })

    return { total: tickets.length, portal, ghost, clean, email, inFlight }
  }, [tickets])

  // Filtered Tickets
  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return tickets.filter((t) => {
      const tid = (t.ticket_id || "").toLowerCase()
      const ref = (t.municipal_ref_id || t.filed_fields?.reference_token || "").toLowerCase()
      const name = (t.user_name || t.filed_fields?.complainant_name || "").toLowerCase()
      const landmark = (t.landmark || t.triage?.landmark_context || "").toLowerCase()
      const desc = (t.complaint_text || t.triage?.complaint_text || "").toLowerCase()
      const corp = (t.authority?.corporation || "").toLowerCase()

      const matchesSearch =
        !q ||
        tid.includes(q) ||
        ref.includes(q) ||
        name.includes(q) ||
        landmark.includes(q) ||
        desc.includes(q) ||
        corp.includes(q)

      if (!matchesSearch) return false

      const s = t.status || ""
      const isGhost = s === "REOPENED_AUDIT_FAILED" || Boolean(t.audit?.fraud_detected)
      const isClean = s === "CONFIRMED_CLEAN"
      const isEmail = s === "EMAIL_FALLBACK_READY" || s === "COMPILING_EMAIL_DOSSIER"
      const isPortal = s === "SUBMITTED"
      const isInf = isInFlight(s as TicketStatus)

      if (activeTab === "GHOST_AUDIT") return isGhost
      if (activeTab === "VERIFIED_CLEAN") return isClean
      if (activeTab === "EMAIL") return isEmail
      if (activeTab === "SUBMITTED") return isPortal
      if (activeTab === "IN_FLIGHT") return isInf
      return true
    })
  }, [tickets, searchQuery, activeTab])

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <div>
          <button
            type="button"
            onClick={onNewFiling}
            className="text-xs font-semibold uppercase tracking-[0.18em] text-dust hover:text-ink transition cursor-pointer"
          >
            ← New intake desk
          </button>
          <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Municipal Docket · Filed Cases
          </h1>
          <p className="mt-1 text-sm text-dust max-w-xl">
            Live registry of autonomous portal filings, statutory email dossiers, and ghost-resolution forensic audits.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/mock-pmc-portal"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-full border border-rule bg-paper px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-dust hover:text-ink hover:border-ink/30 transition shadow-xs"
          >
            Mock Portal <ExternalLink size={13} />
          </a>
          <button
            type="button"
            onClick={() => load(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-paper hover:bg-ink/80 transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Sync"}
          </button>
        </div>
      </div>

      {/* KPI Stats Counters */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <button
          type="button"
          onClick={() => setActiveTab("ALL")}
          className={`rounded-2xl border p-4 text-left transition cursor-pointer ${activeTab === "ALL"
              ? "border-ink bg-ink text-paper shadow-sm"
              : "border-rule bg-paper hover:border-ink/30"
            }`}
        >
          <p
            className={`text-[10px] font-bold uppercase tracking-[0.18em] ${activeTab === "ALL" ? "text-paper/80" : "text-dust"
              }`}
          >
            Total Cases
          </p>
          <p
            className={`mt-1 font-display text-2xl font-bold ${activeTab === "ALL" ? "text-paper" : "text-ink"
              }`}
          >
            {stats.total}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("SUBMITTED")}
          className={`rounded-2xl border p-4 text-left transition cursor-pointer ${activeTab === "SUBMITTED"
              ? "border-moss bg-moss text-paper shadow-sm"
              : "border-rule bg-paper hover:border-moss/40"
            }`}
        >
          <p
            className={`text-[10px] font-bold uppercase tracking-[0.18em] ${activeTab === "SUBMITTED" ? "text-paper/80" : "text-moss"
              }`}
          >
            Filed on Portal
          </p>
          <p
            className={`mt-1 font-display text-2xl font-bold ${activeTab === "SUBMITTED" ? "text-paper" : "text-moss"
              }`}
          >
            {stats.portal}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("GHOST_AUDIT")}
          className={`rounded-2xl border p-4 text-left transition cursor-pointer ${activeTab === "GHOST_AUDIT"
              ? "border-stamp bg-stamp text-paper shadow-sm"
              : "border-rule bg-paper hover:border-stamp/40"
            }`}
        >
          <p
            className={`text-[10px] font-bold uppercase tracking-[0.18em] ${activeTab === "GHOST_AUDIT" ? "text-paper/80" : "text-stamp"
              }`}
          >
            Ghost-Resolved ⚠️
          </p>
          <p
            className={`mt-1 font-display text-2xl font-bold ${activeTab === "GHOST_AUDIT" ? "text-paper" : "text-stamp"
              }`}
          >
            {stats.ghost}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("VERIFIED_CLEAN")}
          className={`rounded-2xl border p-4 text-left transition cursor-pointer ${activeTab === "VERIFIED_CLEAN"
              ? "border-moss bg-moss text-paper shadow-sm"
              : "border-rule bg-paper hover:border-moss/40"
            }`}
        >
          <p
            className={`text-[10px] font-bold uppercase tracking-[0.18em] ${activeTab === "VERIFIED_CLEAN" ? "text-paper/80" : "text-moss"
              }`}
          >
            Verified Clean ✓
          </p>
          <p
            className={`mt-1 font-display text-2xl font-bold ${activeTab === "VERIFIED_CLEAN" ? "text-paper" : "text-moss"
              }`}
          >
            {stats.clean}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("EMAIL")}
          className={`rounded-2xl border p-4 text-left transition cursor-pointer ${activeTab === "EMAIL"
              ? "border-gold bg-ink text-paper shadow-sm"
              : "border-rule bg-paper hover:border-gold/40"
            }`}
        >
          <p
            className={`text-[10px] font-bold uppercase tracking-[0.18em] ${activeTab === "EMAIL" ? "text-gold" : "text-dust"
              }`}
          >
            Statutory Mail
          </p>
          <p
            className={`mt-1 font-display text-2xl font-bold ${activeTab === "EMAIL" ? "text-paper" : "text-ink"
              }`}
          >
            {stats.email}
          </p>
        </button>
      </div>

      {/* Search & Filter Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-dust pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by token, ticket ID, complainant, landmark…"
            className="w-full rounded-full border border-rule bg-paper py-2.5 pl-10 pr-4 text-xs font-medium placeholder:text-dust/70 focus:border-ink focus:outline-hidden transition shadow-2xs"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-bold uppercase text-dust hover:text-ink cursor-pointer"
            >
              Clear
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            type="button"
            onClick={() => setActiveTab("ALL")}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition cursor-pointer ${activeTab === "ALL" ? "bg-ink text-paper" : "bg-paper-deep text-dust hover:text-ink"
              }`}
          >
            All ({stats.total})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("SUBMITTED")}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition cursor-pointer ${activeTab === "SUBMITTED" ? "bg-moss text-paper" : "bg-paper-deep text-dust hover:text-ink"
              }`}
          >
            Portal Filed ({stats.portal})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("GHOST_AUDIT")}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition cursor-pointer ${activeTab === "GHOST_AUDIT" ? "bg-stamp text-paper" : "bg-stamp/10 text-stamp hover:bg-stamp/20"
              }`}
          >
            Ghost-Resolved ⚠️ ({stats.ghost})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("VERIFIED_CLEAN")}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition cursor-pointer ${activeTab === "VERIFIED_CLEAN" ? "bg-moss text-paper" : "bg-moss/10 text-moss hover:bg-moss/20"
              }`}
          >
            Verified Clean ✓ ({stats.clean})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("EMAIL")}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition cursor-pointer ${activeTab === "EMAIL" ? "bg-ink text-paper" : "bg-paper-deep text-dust hover:text-ink"
              }`}
          >
            Emailed ({stats.email})
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-stamp/30 bg-stamp/10 p-4 text-xs font-semibold text-stamp-deep">
          {error}
        </div>
      )}

      {/* Loading Skeletons */}
      {loading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="animate-pulse rounded-[24px] border border-rule bg-paper p-5 space-y-4">
              <div className="h-4 w-1/3 rounded bg-paper-deep" />
              <div className="h-6 w-2/3 rounded bg-paper-deep" />
              <div className="h-24 rounded-xl bg-paper-deep" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filtered.length === 0 && (
        <div className="rounded-[28px] border border-dashed border-rule bg-paper-deep/60 p-12 text-center">
          <FileText size={32} className="mx-auto text-dust" />
          <h3 className="mt-3 font-display text-xl font-semibold text-ink">No cases found</h3>
          <p className="mt-1 text-xs text-dust">
            {searchQuery
              ? `No filings matching "${searchQuery}". Try searching by another keyword.`
              : "No filed or emailed cases under this filter category."}
          </p>
          <button
            type="button"
            onClick={onNewFiling}
            className="mt-5 inline-flex items-center gap-2 rounded-full bg-stamp px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.16em] text-paper hover:bg-stamp/90 transition cursor-pointer"
          >
            Create New Filing
          </button>
        </div>
      )}

      {/* Case Cards Grid */}
      {!loading && filtered.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2">
          {filtered.map((ticket) => {
            const tid = ticket.ticket_id || ticket.PK?.replace("TICKET#", "") || "UNKNOWN"
            const token =
              ticket.municipal_ref_id ||
              ticket.filed_fields?.reference_token ||
              `PMC-SW-2026-${tid.toUpperCase()}`
            const meta = statusCopy(ticket.status)
            const isGhost = ticket.status === "REOPENED_AUDIT_FAILED" || Boolean(ticket.audit?.fraud_detected)
            const isClean = ticket.status === "CONFIRMED_CLEAN"
            const isEmail = ticket.status === "EMAIL_FALLBACK_READY" || ticket.status === "COMPILING_EMAIL_DOSSIER"

            const toneBorder = isGhost
              ? "border-stamp/40 hover:border-stamp shadow-stamp/5"
              : isClean
                ? "border-moss/40 hover:border-moss shadow-moss/5"
                : isEmail
                  ? "border-gold/30 hover:border-gold/60"
                  : "border-rule hover:border-ink/30"

            const dateStr = ticket.created_at
              ? new Date(
                typeof ticket.created_at === "number" || !isNaN(Number(ticket.created_at))
                  ? Number(ticket.created_at) * (Number(ticket.created_at) < 1e11 ? 1000 : 1)
                  : ticket.created_at,
              ).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
              : "Recent"

            const beforeThumb = getFullApiUrl(ticket.evidence_url || `/api/v1/evidence/${tid}/before`)
            const afterThumb = ticket.after_url
              ? getFullApiUrl(ticket.after_url)
              : (ticket.after_s3_key ? getFullApiUrl(`/api/v1/evidence/${tid}/after`) : undefined)

            return (
              <article
                key={tid}
                className={`flex flex-col justify-between overflow-hidden rounded-[26px] border bg-paper p-5 transition-all shadow-xs hover:shadow-md ${toneBorder}`}
              >
                <div>
                  {/* Card Header: Token & Status Badge */}
                  <div className="flex items-start justify-between gap-3 border-b border-rule/60 pb-3.5">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-dust">
                        Reference Token
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-base font-bold tracking-tight text-ink sm:text-lg">
                          {token}
                        </span>
                        <button
                          type="button"
                          onClick={() => copyText(token, tid)}
                          title="Copy reference token"
                          className="inline-flex h-6 w-6 items-center justify-center rounded-md border border-rule bg-paper-deep text-dust hover:text-ink transition cursor-pointer"
                        >
                          {copiedId === tid ? <Check size={12} className="text-moss" /> : <Copy size={12} />}
                        </button>
                      </div>
                    </div>

                    <div
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${isGhost
                        ? "bg-stamp/15 text-stamp-deep"
                        : isClean
                          ? "bg-moss/15 text-moss"
                          : isEmail
                            ? "bg-ink/10 text-ink"
                            : "bg-paper-deep text-dust"
                        }`}
                    >
                      {isInFlight(ticket.status) && (
                        <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
                      )}
                      {isGhost ? <ShieldAlert size={12} /> : isClean ? <ShieldCheck size={12} /> : null}
                      {meta.label}
                    </div>
                  </div>

                  {/* Evidence Thumbnails (Before & After if available) */}
                  <div className="mt-4 flex gap-3">
                    <figure className="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl border border-rule bg-paper-deep">
                      <img
                        src={beforeThumb}
                        alt="Citizen complaint evidence"
                        className="h-full w-full object-cover"
                        onError={(e) => {
                          ; (e.target as HTMLImageElement).src = getFullApiUrl("/api/v1/mock/sample-image/dump")
                        }}
                      />
                      <figcaption className="absolute bottom-0 inset-x-0 bg-ink/75 py-0.5 text-center text-[9px] font-bold uppercase tracking-wider text-paper">
                        Report Photo
                      </figcaption>
                    </figure>

                    {afterThumb && (
                      <figure className="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl border border-rule bg-paper-deep">
                        <img
                          src={afterThumb}
                          alt="Field resolution claim"
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            ; (e.target as HTMLImageElement).src = getFullApiUrl(
                              isGhost ? "/api/v1/mock/sample-image/fake_clean" : "/api/v1/mock/sample-image/cleaned"
                            )
                          }}
                        />
                        <figcaption
                          className={`absolute bottom-0 inset-x-0 py-0.5 text-center text-[9px] font-bold uppercase tracking-wider text-paper ${isGhost ? "bg-stamp" : "bg-moss"
                            }`}
                        >
                          {isGhost ? "Ghost Claim" : "Clean Claim"}
                        </figcaption>
                      </figure>
                    )}

                    <div className="flex-1 min-w-0 space-y-1.5 text-xs">
                      <p className="font-semibold text-ink line-clamp-1">
                        {ticket.authority?.corporation || "Pune Municipal Corporation (PMC)"}
                      </p>
                      <p className="text-dust line-clamp-1 flex items-center gap-1">
                        <MapPin size={12} className="shrink-0" />
                        {ticket.landmark || ticket.triage?.landmark_context || "Pune Municipal Area"}
                      </p>
                      <p className="text-dust line-clamp-1 flex items-center gap-1.5">
                        <User size={12} className="shrink-0" />
                        <span className="font-medium text-ink/90">{ticket.user_name || "Concerned Citizen"}</span>
                        <span className="text-[10px] text-dust/70">· Citizen on record</span>
                      </p>
                      <p className="text-[10px] text-dust pt-1">{dateStr}</p>
                    </div>
                  </div>

                  {/* Ghost-Resolution Alert Banner */}
                  {isGhost && (
                    <div className="mt-4 rounded-xl border border-stamp/20 bg-stamp/10 p-3 text-xs">
                      <p className="flex items-center gap-1.5 font-bold text-stamp-deep">
                        <ShieldAlert size={14} className="shrink-0" />
                        Ghost-Resolution Fraud Flagged
                      </p>
                      <p className="mt-1 text-[11px] leading-relaxed text-ink/80 line-clamp-2">
                        {ticket.audit?.discrepancy_notes ||
                          "Field contractor submitted resolution photo from a mismatching scene. Case reopened."}
                      </p>
                    </div>
                  )}

                  {/* Verified Clean Banner */}
                  {isClean && (
                    <div className="mt-4 rounded-xl border border-moss/20 bg-moss/10 p-3 text-xs">
                      <p className="flex items-center gap-1.5 font-bold text-moss">
                        <ShieldCheck size={14} className="shrink-0" />
                        Cleanup Verified by Vision AI
                      </p>
                      <p className="mt-1 text-[11px] leading-relaxed text-ink/80 line-clamp-2">
                        {ticket.audit?.discrepancy_notes ||
                          "Municipal landmarks verified and the civic pile was confirmed removed."}
                      </p>
                    </div>
                  )}

                  {/* Statutory Mail Callout */}
                  {isEmail && ticket.email_dispatch && (
                    <div className="mt-4 rounded-xl border border-gold/40 bg-paper-deep p-3 text-xs">
                      <p className="flex items-center gap-1.5 font-bold text-ink">
                        <Mail size={14} className="shrink-0 text-dust" />
                        Statutory Email Dossier Compiled
                      </p>
                      <p className="mt-1 text-[11px] text-dust line-clamp-1">
                        To: {ticket.email_dispatch.to || ticket.authority?.nodal_email || "Municipal Commissioner"}
                      </p>
                    </div>
                  )}
                </div>

                {/* Footer Action Buttons */}
                <div className="mt-5 flex items-center justify-between border-t border-rule/60 pt-3.5">
                  <span className="font-mono text-[10px] uppercase text-dust">
                    ID: #{tid}
                  </span>

                  <div className="flex items-center gap-2">
                    <a
                      href={`/mock-pmc-portal#track`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-full border border-rule px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-dust hover:text-ink hover:border-ink/30 transition cursor-pointer"
                    >
                      Audit on Portal ↗
                    </a>
                    <button
                      type="button"
                      onClick={() => onSelectTicket(tid)}
                      className="inline-flex items-center gap-1 rounded-full bg-ink px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-paper hover:bg-ink/80 transition cursor-pointer"
                    >
                      Case File <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
