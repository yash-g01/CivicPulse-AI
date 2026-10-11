import type { TicketStatus } from "./types"

export const IN_FLIGHT: TicketStatus[] = [
  "QUEUED_FOR_FILING",
  "AGENT_BROWSING_PORTAL",
  "AWAITING_HUMAN_ACTION",
  "AWAITING_OTP",
  "RELAYING_OTP",
  "COMPILING_EMAIL_DOSSIER",
]

export function isInFlight(status: TicketStatus | undefined): boolean {
  return Boolean(status && IN_FLIGHT.includes(status))
}

export function statusCopy(status: TicketStatus | undefined): {
  label: string
  tone: "live" | "wait" | "ok" | "bad" | "mail" | "idle"
  hint: string
} {
  switch (status) {
    case "QUEUED_FOR_FILING":
      return { label: "Queued", tone: "live", hint: "Handing the file to the filing agent." }
    case "AGENT_BROWSING_PORTAL":
      return { label: "On the portal", tone: "live", hint: "The agent is reading the municipal form." }
    case "AWAITING_HUMAN_ACTION":
      return { label: "Your turn", tone: "wait", hint: "The portal needs a citizen login before filing can continue." }
    case "AWAITING_OTP":
      return { label: "OTP needed", tone: "wait", hint: "Type the SMS code sent to the phone on this report." }
    case "RELAYING_OTP":
      return { label: "Relaying OTP", tone: "live", hint: "Code received. Typing it into the portal." }
    case "SUBMITTED":
      return { label: "Filed", tone: "ok", hint: "A municipal reference token is on the record." }
    case "COMPILING_EMAIL_DOSSIER":
      return { label: "Drafting mail", tone: "mail", hint: "Portal filing stalled. Compiling a statutory email instead." }
    case "EMAIL_FALLBACK_READY":
      return { label: "Send the letter", tone: "mail", hint: "Open your mail client with a ready-to-send grievance." }
    case "CONFIRMED_CLEAN":
      return { label: "Cleanup verified", tone: "ok", hint: "Before and after photos match the same scene, debris gone." }
    case "REOPENED_AUDIT_FAILED":
      return { label: "Ghost cleanup", tone: "bad", hint: "The after photo does not prove this dump was cleared." }
    default:
      return { label: status || "Unknown", tone: "idle", hint: "Waiting for the next update." }
  }
}

export function formatCategories(list?: string[]): string {
  if (!list?.length) return "Unclassified waste"
  return list
    .map((item) => item.replace(/_/g, " "))
    .join(" · ")
}

export function severityWords(n?: number): string {
  const score = Number(n) || 0
  if (score >= 5) return "Severe"
  if (score >= 4) return "High"
  if (score >= 3) return "Notable"
  if (score >= 2) return "Mild"
  return "Low"
}
