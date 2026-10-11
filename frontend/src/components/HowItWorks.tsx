import {
  ArrowRight,
  Bot,
  Camera,
  CheckCircle2,
  ChevronDown,
  Eye,
  FileCheck2,
  FileText,
  MapPin,
  Scale,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react"
import { useState } from "react"

interface Step {
  id: string
  number: string
  title: string
  tagline: string
  icon: typeof Camera
  badge: string
  summary: string
  deepDive: {
    technology: string
    action: string
    citizenImpact: string
  }
  metric: string
}

const STEPS: Step[] = [
  {
    id: "triage",
    number: "01",
    title: "Multimodal AI Triage",
    tagline: "Instant scene verification & categorization in <500ms",
    icon: Camera,
    badge: "Groq Vision · Llama 3.2 Vision",
    summary:
      "Citizen snaps one or multiple photos from any camera or gallery. High-speed vision models instantly scan the scene for municipal solid waste, classify waste streams (plastics, construction debris, organic refuse), score severity from 1 to 5, and filter out non-garbage images.",
    deepDive: {
      technology: "Sub-second multimodal visual inference with custom prompt tuning",
      action: "Extracts landmark context, detects accumulation volume, and checks authentic civic dumping",
      citizenImpact: "Zero manual form-filling — the camera reads the grievance for you",
    },
    metric: "< 480ms triage latency",
  },
  {
    id: "routing",
    number: "02",
    title: "Statutory ULB Geo-Routing",
    tagline: "Pinpoint jurisdiction & nodal sanitation officers",
    icon: MapPin,
    badge: "Automated Municipal Boundary Engine",
    summary:
      "Geographic coordinates resolve the precise Urban Local Body (ULB) — whether Pune Municipal Corporation (PMC), BMC Mumbai, BBMP Bengaluru, or regional councils — finding the local ward and official grievance gateway.",
    deepDive: {
      technology: "Automated municipal GIS resolver with cached ward boundary mapping",
      action: "Maps lat/long to ward officer jurisdictions and active municipal portal endpoints",
      citizenImpact: "No guessing which ward office or department handles your locality",
    },
    metric: "100% boundary accuracy",
  },
  {
    id: "filing",
    number: "03",
    title: "Autonomous Playwright Filing",
    tagline: "AI browser agent drives government portals directly",
    icon: Bot,
    badge: "Playwright Headed Browser Automation",
    summary:
      "An autonomous AI agent opens a dedicated browser session, navigates the government grievance gateway, overcomes multilingual barriers, adapts to form layout changes without fragile CSS selectors, and uploads all photographic evidence.",
    deepDive: {
      technology: "Semantic DOM snapshot extractor + real-time LLM browser steering",
      action: "Automates multi-step form entry, selects departments, and relays SMS OTP via human-in-the-loop sheet",
      citizenImpact: "Bypasses confusing municipal UIs; returns an official municipal tracking token (PMC-SW-XXXX)",
    },
    metric: "Instant reference ID extraction",
  },
  {
    id: "statutory",
    number: "04",
    title: "Statutory Legal Escalation",
    tagline: "SWM Rules 2016 legal notice if portals stall",
    icon: Scale,
    badge: "Statutory Compliance · SWM Rules 2016",
    summary:
      "If a municipal portal is down, offline, or requires pre-registered municipal employee credentials, the discovery agent scrapes executive directories for direct nodal emails and drafts a formal legal grievance invoking Section 13 of the Solid Waste Management Rules, 2016.",
    deepDive: {
      technology: "Live discovery crawler + legal mailto: intent compiler",
      action: "Pre-fills citizen identity, precise coordinates, and presigned AWS S3 photographic evidence links",
      citizenImpact: "Holds municipal commissioners legally accountable with zero friction",
    },
    metric: "Zero dropped complaints",
  },
  {
    id: "auditor",
    number: "05",
    title: "Ghost-Resolution Auditor",
    tagline: "AI forensic inspection catches fake cleanups",
    icon: ShieldCheck,
    badge: "Dual-Scene Forensic Computer Vision",
    summary:
      "Contractors often close public complaints with recycled photos or angled shots hiding remaining waste. When a case is marked 'Resolved', CivicPulse performs a forensic 'Before vs After' inspection to verify genuine clearance and flag fraudulent closures.",
    deepDive: {
      technology: "Cross-scene visual reasoning comparing background landmarks, surface clearing, and lighting",
      action: "Computes cleanup confidence, detects scene mismatches, and logs discrepancy notes",
      citizenImpact: "Stops the notorious 'closed on paper, trash still there' municipal loophole",
    },
    metric: "Dual-image fraud detection",
  },
]

const FAQS = [
  {
    q: "Do I need to download a government app or create a portal account?",
    a: "No. CivicPulse acts as your autonomous civic agent. You simply take or upload photos from your phone browser. Our backend agent drives the municipal gateway directly.",
  },
  {
    q: "How does the agent handle SMS OTP verification on government portals?",
    a: "When a portal sends a verification code to your phone, CivicPulse displays a lightweight bottom sheet asking for the OTP. Once entered, the agent enters it into the portal and completes the filing.",
  },
  {
    q: "What happens if the municipal portal is down or requires citizen login?",
    a: "CivicPulse has an automatic statutory fallback: our discovery agent searches official executive rosters for the nodal sanitation officer's email and drafts a formal grievance letter citing Section 13 of the Solid Waste Management Rules, 2016, pre-filled with your photo evidence.",
  },
  {
    q: "How does the Ghost-Resolution Auditor catch fake cleanups?",
    a: "When municipal contractors upload an 'after' photo claiming clearance, our vision auditor compares both images. It analyzes fixed architectural landmarks, fence lines, and curb geometry to verify that the debris was genuinely removed rather than covered up or photographed from a misleading angle.",
  },
  {
    q: "Can I upload multiple photos from different angles?",
    a: "Yes! You can attach multiple photos directly from your phone camera or gallery. CivicPulse uploads all photos to secure cloud storage and embeds them into the municipal filing and statutory email dossiers.",
  },
]

export function HowItWorks() {
  const [activeStepId, setActiveStepId] = useState<string>("triage")
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  const activeStep = STEPS.find((s) => s.id === activeStepId) || STEPS[0]
  const IconComponent = activeStep.icon

  return (
    <section id="how-it-works" className="mt-20 border-t border-rule pt-16 scroll-mt-12">
      {/* SECTION HEADER */}
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-stamp/30 bg-stamp/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-stamp">
            <Sparkles size={12} />
            <span>Architecture & Workflow</span>
          </div>
          <h2 className="mt-3 font-display text-3xl sm:text-4xl font-semibold tracking-tight text-ink">
            How CivicPulse works.
            <span className="block italic text-stamp-deep">From roadside pile to verified removal.</span>
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-dust">
            Government grievance apps fail because citizens give up on clunky forms and contractors submit fake cleanup photos. CivicPulse replaces bureaucracy with autonomous AI agents.
          </p>
        </div>

        <div className="hidden lg:flex items-center gap-2 rounded-2xl border border-rule bg-paper-deep/40 px-4 py-2.5 text-xs text-dust">
          <Zap size={15} className="text-stamp" />
          <span>Full cycle: Capture → Portal → Legal → Audit</span>
        </div>
      </div>

      {/* STEP PROGRESS PILLS */}
      <div className="mt-10 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {STEPS.map((step) => {
          const StepIcon = step.icon
          const isActive = step.id === activeStepId
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => setActiveStepId(step.id)}
              className={`group flex flex-col items-start rounded-2xl border p-3.5 text-left transition-all duration-200 cursor-pointer ${
                isActive
                  ? "border-stamp bg-paper ring-2 ring-stamp/20 shadow-md scale-[1.02]"
                  : "border-rule bg-paper-deep/30 hover:border-ink/50 hover:bg-paper-deep/60 opacity-85 hover:opacity-100 hover:scale-[1.01]"
              }`}
            >
              <div className="flex w-full items-center justify-between pb-2">
                <span
                  className={`font-mono text-xs font-bold transition-colors ${
                    isActive ? "text-stamp" : "text-dust group-hover:text-ink"
                  }`}
                >
                  {step.number}
                </span>
                <span
                  className={`grid h-7 w-7 place-items-center rounded-lg transition-all duration-200 ${
                    isActive
                      ? "bg-stamp text-paper shadow-sm scale-110"
                      : "bg-paper-deep text-dust group-hover:text-ink group-hover:scale-105"
                  }`}
                >
                  <StepIcon size={14} />
                </span>
              </div>
              <span className="font-display text-sm font-semibold text-ink line-clamp-1">{step.title}</span>
              <span className="mt-0.5 text-[10px] text-dust line-clamp-1">{step.metric}</span>
              {isActive && (
                <div className="mt-2 h-0.5 w-full bg-stamp rounded-full animate-scale-in" />
              )}
            </button>
          )
        })}
      </div>

      {/* ACTIVE STEP DEEP-DIVE CARD WITH ANIMATED TRANSITIONS */}
      <div className="mt-6 overflow-hidden rounded-[28px] border-2 border-rule bg-paper/90 shadow-[0_20px_50px_-25px_rgba(27,23,18,0.35)] backdrop-blur-sm transition-all duration-300">
        <div
          key={`header-${activeStepId}`}
          className="border-b border-rule/60 bg-paper-deep/40 px-6 py-4 flex flex-wrap items-center justify-between gap-3 animate-step-enter"
        >
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-stamp text-paper shadow-sm transition-transform duration-300 hover:scale-110">
              <IconComponent size={20} />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-stamp uppercase tracking-wider">
                  Step {activeStep.number}
                </span>
                <span className="text-rule">·</span>
                <span className="rounded-full bg-paper px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-dust border border-rule">
                  {activeStep.badge}
                </span>
              </div>
              <h3 className="font-display text-xl font-bold text-ink">{activeStep.title}</h3>
            </div>
          </div>
          <span className="font-mono text-xs font-semibold text-stamp bg-stamp/10 rounded-full px-3 py-1">
            {activeStep.metric}
          </span>
        </div>

        <div
          key={`body-${activeStepId}`}
          className="p-6 sm:p-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-start"
        >
          <div>
            <p className="font-display text-lg font-medium text-stamp-deep leading-snug animate-stagger-1">
              "{activeStep.tagline}"
            </p>
            <p className="mt-3 text-sm leading-relaxed text-dust sm:text-[15px] animate-stagger-2">
              {activeStep.summary}
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 animate-stagger-3">
              <div className="rounded-2xl border border-rule/70 bg-paper-deep/30 p-4 transition-all duration-200 hover:border-stamp/40 hover:bg-paper-deep/50 hover:shadow-sm">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-dust">
                  <Bot size={14} className="text-stamp" />
                  <span>Agent Action</span>
                </div>
                <p className="mt-1.5 text-xs text-ink leading-relaxed">
                  {activeStep.deepDive.action}
                </p>
              </div>

              <div className="rounded-2xl border border-rule/70 bg-paper-deep/30 p-4 transition-all duration-200 hover:border-moss/40 hover:bg-paper-deep/50 hover:shadow-sm">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-dust">
                  <CheckCircle2 size={14} className="text-moss" />
                  <span>Citizen Benefit</span>
                </div>
                <p className="mt-1.5 text-xs text-ink leading-relaxed">
                  {activeStep.deepDive.citizenImpact}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-rule bg-paper-deep/60 p-5 flex flex-col justify-between animate-stagger-4 transition-all duration-200 hover:border-ink/40">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">
                Engine Details
              </span>
              <p className="mt-1 text-xs font-mono font-medium text-ink bg-paper px-3 py-2 rounded-xl border border-rule shadow-inner">
                {activeStep.deepDive.technology}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-rule/60 flex items-center justify-between text-xs">
              <span className="text-dust">Explore next step:</span>
              <button
                type="button"
                onClick={() => {
                  const currIdx = STEPS.findIndex((s) => s.id === activeStepId)
                  const nextIdx = (currIdx + 1) % STEPS.length
                  setActiveStepId(STEPS[nextIdx].id)
                }}
                className="inline-flex items-center gap-1 font-semibold text-stamp hover:text-stamp-deep transition-all duration-200 hover:translate-x-1 cursor-pointer"
              >
                <span>{STEPS[(STEPS.findIndex((s) => s.id === activeStepId) + 1) % STEPS.length].title}</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 3 CORE PILLARS / COMPARISON GRID */}
      <div className="mt-12 grid gap-5 sm:grid-cols-3">
        <div className="rounded-2xl border border-rule bg-paper/70 p-5 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:shadow-lg hover:border-stamp/40">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-stamp/10 text-stamp transition-transform duration-300 hover:scale-110">
            <Zap size={18} />
          </div>
          <h4 className="mt-3 font-display text-base font-bold text-ink">Zero App Fatigue</h4>
          <p className="mt-1.5 text-xs leading-relaxed text-dust">
            No downloading government portals or filling 14-field municipal forms. Snap photos in your mobile browser and the agent drives the website for you.
          </p>
        </div>

        <div className="rounded-2xl border border-rule bg-paper/70 p-5 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:shadow-lg hover:border-moss/40">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-moss/10 text-moss transition-transform duration-300 hover:scale-110">
            <Eye size={18} />
          </div>
          <h4 className="mt-3 font-display text-base font-bold text-ink">Anti-Fraud Vision Audit</h4>
          <p className="mt-1.5 text-xs leading-relaxed text-dust">
            Contractors cannot falsely claim completion. Our dual-image computer vision compares before/after geometry to confirm waste was truly removed.
          </p>
        </div>

        <div className="rounded-2xl border border-rule bg-paper/70 p-5 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:shadow-lg hover:border-ink/40">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-ink/10 text-ink transition-transform duration-300 hover:scale-110">
            <FileCheck2 size={18} />
          </div>
          <h4 className="mt-3 font-display text-base font-bold text-ink">Statutory Legal Guarantee</h4>
          <p className="mt-1.5 text-xs leading-relaxed text-dust">
            If portals crash, CivicPulse automatically generates formal legal complaint notices under Solid Waste Management Rules 2016 to municipal commissioners.
          </p>
        </div>
      </div>

      {/* FREQUENTLY ASKED QUESTIONS ACCORDION */}
      <div className="mt-14 rounded-[28px] border border-rule bg-paper/60 p-6 sm:p-8">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-dust">
          <FileText size={13} className="text-stamp" />
          <span>Frequently Asked Questions</span>
        </div>
        <h3 className="mt-2 font-display text-2xl font-semibold text-ink">
          Everything you need to know.
        </h3>

        <div className="mt-6 divide-y divide-rule/60">
          {FAQS.map((faq, idx) => {
            const isOpen = openFaq === idx
            return (
              <div key={faq.q} className="py-4">
                <button
                  type="button"
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  className="flex w-full items-center justify-between gap-4 text-left font-display text-sm sm:text-base font-semibold text-ink transition-colors duration-200 hover:text-stamp cursor-pointer"
                >
                  <span>{faq.q}</span>
                  <span
                    className={`grid h-6 w-6 shrink-0 place-items-center rounded-full bg-paper-deep text-dust transition-all duration-300 ${
                      isOpen ? "rotate-180 bg-stamp/10 text-stamp" : ""
                    }`}
                  >
                    <ChevronDown size={14} />
                  </span>
                </button>
                {isOpen && (
                  <p className="mt-2.5 text-xs sm:text-sm leading-relaxed text-dust animate-accordion-open">
                    {faq.a}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
