export type TicketStatus =
  | "QUEUED_FOR_FILING"
  | "AGENT_BROWSING_PORTAL"
  | "AWAITING_HUMAN_ACTION"
  | "AWAITING_OTP"
  | "RELAYING_OTP"
  | "SUBMITTED"
  | "COMPILING_EMAIL_DOSSIER"
  | "EMAIL_FALLBACK_READY"
  | "CONFIRMED_CLEAN"
  | "REOPENED_AUDIT_FAILED"
  | string

export type Authority = {
  corporation?: string
  portal_url?: string
  nodal_email?: string
  requires_otp?: boolean
  jurisdiction?: string
  city_slug?: string
  ward_detected?: string
  is_cached?: boolean
}

export type Triage = {
  is_valid_waste?: boolean
  rejection_reason?: string | null
  waste_categories?: string[]
  severity?: number
  landmark_context?: string
  complaint_text?: string
}

export type TriageRejection = {
  isNotGarbage: boolean
  reason: string
  triage?: Triage
}

export type Audit = {
  is_same_scene?: boolean
  debris_cleared?: boolean
  fraud_detected?: boolean
  confidence?: number
  discrepancy_notes?: string
}

export type EmailDispatch = {
  subject?: string
  body?: string
  mailto_url?: string
  to?: string
  recipient?: string
  evidence_url?: string
}

export type FiledFields = {
  complainant_name?: string
  mobile_number?: string
  category?: string
  landmark?: string
  description?: string
  evidence_files?: string[]
  evidence_count?: number
  portal_name?: string
  portal_url?: string
  reference_token?: string
  filed_at?: string
  [key: string]: any
}

export type Ticket = {
  PK?: string
  ticket_id?: string
  status: TicketStatus
  user_phone?: string
  user_name?: string
  lat?: string | number
  lng?: string | number
  authority?: Authority
  portal_url?: string
  triage?: Triage
  before_s3_key?: string
  before_s3_keys?: string[]
  after_s3_key?: string
  after_url?: string
  token_id?: string
  evidence_url?: string
  evidence_urls?: string[]
  complaint_text?: string
  landmark?: string
  created_at?: string | number
  agent_telemetry?: string
  agent_summary?: string
  auth_prompt?: string
  requires_login?: boolean
  municipal_ref_id?: string
  filed_fields?: FiledFields
  email_dispatch?: EmailDispatch
  fallback_reason?: string
  audit?: Audit
}

export type CreateReportResponse = {
  ticket_id: string
  status: TicketStatus
  triage: Triage
  authority: Authority
  evidence_url?: string
  evidence_urls?: string[]
  user_name?: string
  processing_time_ms?: number
}
