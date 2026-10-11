import { useEffect, useState } from "react"
import { Capture } from "./components/Capture"
import { CaseFile } from "./components/CaseFile"
import { CasesList } from "./components/CasesList"
import { HowItWorks } from "./components/HowItWorks"
import { ExternalLink, FileText, PlusCircle } from "lucide-react"

type RouteState = {
  view: "home" | "cases" | "ticket"
  ticketId: string | null
}

function parseRoute(pathname: string): RouteState {
  const match = pathname.match(/^\/t\/([^/]+)\/?$/)
  if (match) return { view: "ticket", ticketId: match[1] }
  if (pathname === "/cases" || pathname === "/cases/") return { view: "cases", ticketId: null }
  return { view: "home", ticketId: null }
}

export default function App() {
  const [route, setRoute] = useState<RouteState>(() => parseRoute(window.location.pathname))
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    const onPop = () => setRoute(parseRoute(window.location.pathname))
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [])

  function goHome() {
    window.history.pushState({}, "", "/")
    setRoute({ view: "home", ticketId: null })
    setPreviewUrl(null)
  }

  function goToCases() {
    window.history.pushState({}, "", "/cases")
    setRoute({ view: "cases", ticketId: null })
  }

  function openTicket(id: string, preview?: string) {
    window.history.pushState({}, "", `/t/${id}`)
    setRoute({ view: "ticket", ticketId: id })
    setPreviewUrl(preview || null)
  }

  function scrollToHowItWorks(e: React.MouseEvent) {
    if (route.view !== "home") {
      goHome()
      setTimeout(() => {
        document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })
      }, 100)
    } else {
      e.preventDefault()
      document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })
    }
  }

  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-3 bg-stamp md:block" />
      <div className="mx-auto max-w-5xl px-5 py-6 sm:px-8 sm:py-10">
        <nav className="mb-10 flex flex-wrap items-center justify-between gap-4 border-b border-rule/60 pb-5">
          <button type="button" onClick={goHome} className="flex items-center gap-2.5 cursor-pointer">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-stamp font-display text-lg text-paper shadow-xs">
              ●
            </span>
            <span className="text-left">
              <span className="block font-display text-xl leading-none">CivicPulse</span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-dust">
                Waste action desk
              </span>
            </span>
          </button>

          <div className="flex items-center gap-3 sm:gap-4">
            <button
              type="button"
              onClick={goHome}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] transition cursor-pointer ${
                route.view === "home"
                  ? "bg-ink text-paper"
                  : "text-dust hover:text-ink hover:bg-paper-deep"
              }`}
            >
              <PlusCircle size={13} />
              New Intake
            </button>

            <button
              type="button"
              onClick={scrollToHowItWorks}
              className="hidden sm:inline-block text-xs font-semibold uppercase tracking-[0.14em] text-dust hover:text-stamp transition cursor-pointer px-2 py-1"
            >
              How it works
            </button>

            <button
              type="button"
              onClick={goToCases}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] transition cursor-pointer ${
                route.view === "cases"
                  ? "bg-ink text-paper"
                  : "text-dust hover:text-ink hover:bg-paper-deep"
              }`}
            >
              <FileText size={13} />
              Filed Cases
            </button>

            <a
              href="/mock-pmc-portal"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full border border-rule bg-paper px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-dust hover:text-ink hover:border-ink/40 transition shadow-2xs"
            >
              Mock Portal <ExternalLink size={12} />
            </a>
          </div>
        </nav>

        {route.view === "ticket" && route.ticketId ? (
          <CaseFile ticketId={route.ticketId} previewUrl={previewUrl} onHome={goHome} />
        ) : route.view === "cases" ? (
          <CasesList onSelectTicket={(id) => openTicket(id)} onNewFiling={goHome} />
        ) : (
          <>
            <Capture onFiled={(id, preview) => openTicket(id, preview)} onLookup={(id) => openTicket(id)} />
            <HowItWorks />
          </>
        )}

        <footer className="mt-16 border-t border-rule pt-5 pb-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] uppercase tracking-[0.16em] text-dust">
          <span>CivicPulse · citizen filing, not a municipal portal</span>
          <div className="flex items-center gap-4">
            <button type="button" onClick={goToCases} className="hover:text-ink transition cursor-pointer">
              All Cases
            </button>
            <button type="button" onClick={scrollToHowItWorks} className="hover:text-ink transition cursor-pointer">
              How it works
            </button>
            <button type="button" onClick={goHome} className="hover:text-ink transition cursor-pointer">
              New Filing
            </button>
            <a href="/mock-pmc-portal" target="_blank" rel="noreferrer" className="hover:text-ink transition">
              Mock PMC Portal ↗
            </a>
          </div>
        </footer>
      </div>
    </div>
  )
}
