import { useEffect, useState } from "react"
import { Capture } from "./components/Capture"
import { CaseFile } from "./components/CaseFile"
import { HowItWorks } from "./components/HowItWorks"

function pathToTicket(pathname: string): string | null {
  const match = pathname.match(/^\/t\/([^/]+)\/?$/)
  return match?.[1] ?? null
}

export default function App() {
  const [ticketId, setTicketId] = useState<string | null>(() => pathToTicket(window.location.pathname))
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    const onPop = () => setTicketId(pathToTicket(window.location.pathname))
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [])

  function goHome() {
    window.history.pushState({}, "", "/")
    setTicketId(null)
    setPreviewUrl(null)
  }

  function openTicket(id: string, preview?: string) {
    window.history.pushState({}, "", `/t/${id}`)
    setTicketId(id)
    setPreviewUrl(preview || null)
  }

  function scrollToHowItWorks(e: React.MouseEvent) {
    if (ticketId) {
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
        <nav className="mb-10 flex items-center justify-between">
          <button type="button" onClick={goHome} className="flex items-center gap-2.5 cursor-pointer">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-stamp font-display text-lg text-paper">
              ●
            </span>
            <span className="text-left">
              <span className="block font-display text-xl leading-none">CivicPulse</span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-dust">
                Waste action desk
              </span>
            </span>
          </button>

          <div className="flex items-center gap-5 sm:gap-6">
            <button
              type="button"
              onClick={scrollToHowItWorks}
              className="text-xs font-semibold uppercase tracking-[0.16em] text-dust hover:text-stamp transition cursor-pointer"
            >
              How it works
            </button>
            <p className="hidden text-right text-xs text-dust sm:block">
              Photograph. Route. File.
              <span className="block">Catch the fake cleanup.</span>
            </p>
          </div>
        </nav>

        {ticketId ? (
          <CaseFile ticketId={ticketId} previewUrl={previewUrl} onHome={goHome} />
        ) : (
          <>
            <Capture onFiled={(id, preview) => openTicket(id, preview)} onLookup={(id) => openTicket(id)} />
            <HowItWorks />
          </>
        )}

        <footer className="mt-16 border-t border-rule pt-5 pb-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] uppercase tracking-[0.16em] text-dust">
          <span>CivicPulse · citizen filing, not a municipal portal</span>
          <div className="flex items-center gap-4">
            <button type="button" onClick={scrollToHowItWorks} className="hover:text-ink transition cursor-pointer">
              How it works
            </button>
            <button type="button" onClick={goHome} className="hover:text-ink transition cursor-pointer">
              New Filing
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}
