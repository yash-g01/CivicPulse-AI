import { ShieldCheck, X } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"

type Props = {
  prompt: string
  onClose?: () => void
  onSubmit: (otp: string) => Promise<void>
}

export function OtpSheet({ prompt, onClose, onSubmit }: Props) {
  const [digits, setDigits] = useState(["", "", "", "", "", ""])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const refs = useRef<Array<HTMLInputElement | null>>([])

  useEffect(() => {
    refs.current[0]?.focus()
  }, [])

  function setAt(index: number, value: string) {
    const char = value.replace(/\D/g, "").slice(-1)
    const next = [...digits]
    next[index] = char
    setDigits(next)
    if (char && index < 5) refs.current[index + 1]?.focus()
  }

  function onKey(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus()
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const otp = digits.join("")
    if (otp.length < 4) {
      setError("Enter the SMS code from the corporation.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      await onSubmit(otp)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send OTP.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/45 p-4 sm:items-center">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-[28px] border border-gold bg-paper p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stamp">Human in the loop</p>
            <h2 className="mt-1 font-display text-3xl">SMS code</h2>
          </div>
          {onClose && (
            <button type="button" onClick={onClose} className="rounded-full p-1 text-dust hover:text-ink">
              <X size={18} />
            </button>
          )}
        </div>
        <p className="mt-3 text-sm leading-relaxed text-dust">{prompt}</p>

        <div className="mt-5 flex justify-between gap-2">
          {digits.map((digit, index) => (
            <input
              key={index}
              ref={(node) => {
                refs.current[index] = node
              }}
              value={digit}
              inputMode="numeric"
              maxLength={1}
              onChange={(e) => setAt(index, e.target.value)}
              onKeyDown={(e) => onKey(index, e)}
              className="h-14 w-11 rounded-xl border border-rule bg-paper-deep text-center font-display text-2xl outline-none focus:border-stamp"
            />
          ))}
        </div>

        {error && <p className="mt-3 text-sm text-stamp-deep">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-ink py-3 text-sm font-semibold text-paper disabled:opacity-60"
        >
          <ShieldCheck size={16} />
          {busy ? "Relaying…" : "Hand the code to the agent"}
        </button>
      </form>
    </div>
  )
}
