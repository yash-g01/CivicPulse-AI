import { useEffect, useState } from "react"
import { Capture } from "./components/Capture"
import { CaseFile } from "./components/CaseFile"

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

  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-3 bg-stamp md:block" />
      <div className="mx-auto max-w-5xl px-5 py-6 sm:px-8 sm:py-10">
        <nav className="mb-10 flex items-center justify-between">
          <button type="button" onClick={goHome} className="flex items-center gap-2.5">
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
          <p className="hidden text-right text-xs text-dust sm:block">
            Photograph. Route. File.
            <span className="block">Catch the fake cleanup.</span>
          </p>
        </nav>

        {ticketId ? (
          <CaseFile ticketId={ticketId} previewUrl={previewUrl} onHome={goHome} />
        ) : (
          <Capture onFiled={(id, preview) => openTicket(id, preview)} onLookup={(id) => openTicket(id)} />
        )}

        <footer className="mt-16 border-t border-rule pt-4 text-[11px] uppercase tracking-[0.16em] text-dust">
          CivicPulse · citizen filing, not a municipal portal
        </footer>
      </div>
    </div>
  )
}
