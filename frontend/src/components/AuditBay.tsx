import { ShieldAlert, ShieldCheck, Upload } from "lucide-react"
import { useState, type ChangeEvent } from "react"
import { simulateResolution, getFullApiUrl } from "../api"
import type { Audit, Ticket } from "../types"

type Props = {
  ticketId: string
  beforeUrl?: string
  beforePreview?: string | null
  afterUrl?: string
  audit?: Audit
  onAudited: (ticket: Ticket) => void
}

export function AuditBay({ ticketId, beforeUrl, beforePreview, afterUrl, audit, onAudited }: Props) {
  const [afterPreview, setAfterPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resolvedBefore = beforePreview || (beforeUrl ? getFullApiUrl(beforeUrl) : null)
  const resolvedAfter = afterPreview || (afterUrl ? getFullApiUrl(afterUrl) : null)

  async function onAfter(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setAfterPreview(URL.createObjectURL(file))
    setBusy(true)
    setError(null)
    try {
      const result = await simulateResolution(ticketId, file)
      onAudited(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed.")
    } finally {
      setBusy(false)
    }
  }

  const fraud = audit?.fraud_detected || (audit && !audit.debris_cleared)
  const clean = audit && audit.debris_cleared && audit.is_same_scene && !audit.fraud_detected

  return (
    <section className="mt-8 rounded-[28px] border border-rule p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Ghost-resolution check</p>
      <h3 className="mt-1 font-display text-2xl">Did they actually clear it?</h3>
      <p className="mt-2 max-w-2xl text-sm text-dust">
        Upload the worker’s “after” photo. We compare landmarks and whether the pile is gone.
      </p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <figure className="overflow-hidden rounded-2xl border border-rule bg-paper-deep">
          {resolvedBefore ? (
            <img src={resolvedBefore} alt="Original complaint" className="h-56 w-full object-cover" />
          ) : (
            <div className="grid h-56 place-items-center text-sm text-dust">Original evidence</div>
          )}
          <figcaption className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-dust">
            Citizen report
          </figcaption>
        </figure>

        <label className="relative overflow-hidden rounded-2xl border border-dashed border-rule bg-paper-deep">
          {resolvedAfter ? (
            <img src={resolvedAfter} alt="Claimed cleanup" className="h-56 w-full object-cover" />
          ) : (
            <div className="grid h-56 place-items-center px-4 text-center text-sm text-dust">
              <span className="flex flex-col items-center gap-2">
                <Upload size={18} />
                {busy ? "Comparing scenes…" : "Drop the cleanup claim"}
              </span>
            </div>
          )}
          <figcaption className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-dust">
            Worker claim {afterUrl && !afterPreview ? "(Audited)" : ""}
          </figcaption>
          <input type="file" accept="image/*" className="absolute inset-0 cursor-pointer opacity-0" onChange={onAfter} />
        </label>
      </div>

      {error && <p className="mt-3 text-sm text-stamp-deep">{error}</p>}

      {audit && (
        <div
          className={`mt-5 rounded-2xl px-4 py-4 ${
            fraud
              ? "bg-stamp/10 text-stamp-deep"
              : clean
                ? "bg-moss-soft text-moss"
                : "bg-paper-deep text-ink"
          }`}
        >
          <p className="flex items-center gap-2 text-sm font-semibold">
            {fraud ? <ShieldAlert size={16} /> : <ShieldCheck size={16} />}
            {fraud ? "This does not look like a real cleanup." : "Cleanup holds up against the original scene."}
          </p>
          <p className="mt-2 text-sm leading-relaxed opacity-90">{audit.discrepancy_notes}</p>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div>
              <dt className="uppercase tracking-wider opacity-70">Same scene</dt>
              <dd className="font-semibold">{audit.is_same_scene ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider opacity-70">Debris gone</dt>
              <dd className="font-semibold">{audit.debris_cleared ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="uppercase tracking-wider opacity-70">Confidence</dt>
              <dd className="font-semibold">
                {audit.confidence != null ? `${Math.round(Number(audit.confidence) * 100)}%` : "—"}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  )
}
