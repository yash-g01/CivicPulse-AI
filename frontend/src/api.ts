import type { CreateReportResponse, Ticket, Triage, TriageRejection } from "./types"

const API = "/api/v1"

export class TriageRejectionError extends Error {
  rejection: TriageRejection
  constructor(reason: string, rejection: TriageRejection) {
    super(reason)
    this.name = "TriageRejectionError"
    this.rejection = rejection
  }
}

function detailMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "string") return payload
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail
    if (typeof detail === "string") return detail
    if (detail && typeof detail === "object") {
      if ("message" in detail && typeof (detail as { message: unknown }).message === "string") {
        return (detail as { message: string }).message
      }
      if ("rejection_reason" in detail && typeof (detail as { rejection_reason: unknown }).rejection_reason === "string") {
        return (detail as { rejection_reason: string }).rejection_reason
      }
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "string") return item
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg)
          }
          return JSON.stringify(item)
        })
        .join(" ")
    }
  }
  return fallback
}

export async function checkTriage(imageOrImages: File | File[]): Promise<Triage> {
  const body = new FormData()
  if (Array.isArray(imageOrImages)) {
    imageOrImages.forEach((img) => body.append("images", img))
    if (imageOrImages.length > 0) {
      body.append("image", imageOrImages[0])
    }
  } else {
    body.append("image", imageOrImages)
  }

  const res = await fetch(`${API}/triage`, { method: "POST", body })
  const json: unknown = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(detailMessage(json, "Triage could not inspect the image."))
  }
  return json as Triage
}

export async function createReport(input: {
  image?: File
  images?: File[]
  lat: number
  lng: number
  userPhone: string
  userName?: string
  portalUrl?: string
}): Promise<CreateReportResponse> {
  const body = new FormData()
  if (input.images && input.images.length > 0) {
    input.images.forEach((img) => body.append("images", img))
    body.append("image", input.images[0])
  } else if (input.image) {
    body.append("image", input.image)
  }
  body.append("lat", String(input.lat))
  body.append("lng", String(input.lng))
  body.append("user_phone", input.userPhone)
  if (input.userName) body.append("user_name", input.userName)
  if (input.portalUrl) body.append("portal_url", input.portalUrl)

  const res = await fetch(`${API}/reports`, { method: "POST", body })
  const json: any = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = json?.detail
    const isNotGarbage =
      detail?.code === "NOT_GARBAGE" ||
      detail?.is_valid_waste === false ||
      (typeof detail === "string" &&
        (detail.toLowerCase().includes("rejected") ||
          detail.toLowerCase().includes("not depict actionable public waste") ||
          detail.toLowerCase().includes("not garbage")))

    if (isNotGarbage) {
      const reason =
        detail?.rejection_reason ||
        detail?.message ||
        (typeof detail === "string"
          ? detail.replace(/^Rejected:\s*/i, "")
          : "The uploaded photo does not depict actionable public waste or garbage.")

      throw new TriageRejectionError(reason, {
        isNotGarbage: true,
        reason,
        triage: detail?.triage,
      })
    }

    throw new Error(detailMessage(json, "Could not file this report."))
  }
  return json as CreateReportResponse
}

export async function getTicket(ticketId: string): Promise<Ticket> {
  const res = await fetch(`${API}/tickets/${ticketId}`)
  const json: unknown = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(detailMessage(json, "Ticket not found."))
  }
  return json as Ticket
}

export async function submitOtp(ticketId: string, otp: string): Promise<void> {
  const res = await fetch(`${API}/tickets/${ticketId}/submit-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ otp }),
  })
  const json: unknown = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(detailMessage(json, "Could not relay OTP."))
  }
}

export async function confirmLogin(ticketId: string): Promise<void> {
  const res = await fetch(`${API}/tickets/${ticketId}/confirm-login`, {
    method: "POST",
  })
  const json: unknown = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(detailMessage(json, "Could not confirm login."))
  }
}

export async function simulateResolution(ticketId: string, afterImage: File): Promise<Ticket> {
  const body = new FormData()
  body.append("after_image", afterImage)
  const res = await fetch(`${API}/tickets/${ticketId}/simulate-resolution`, {
    method: "POST",
    body,
  })
  const json: unknown = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(detailMessage(json, "Audit failed."))
  }
  return json as Ticket
}
