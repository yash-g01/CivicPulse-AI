import {
  AlertOctagon,
  Camera,
  CheckCircle2,
  Image as ImageIcon,
  Loader2,
  MapPin,
  Phone,
  Plus,
  Search,
  User,
  X,
} from "lucide-react"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { checkTriage, createReport, TriageRejectionError } from "../api"
import type { Triage } from "../types"

const PLACES = [
  { name: "Pune", lat: 18.5204, lng: 73.8567 },
  { name: "Mumbai", lat: 19.076, lng: 72.8777 },
  { name: "Bengaluru", lat: 12.9716, lng: 77.5946 },
]

type Props = {
  onFiled: (ticketId: string, previewUrl: string) => void
  onLookup: (ticketId: string) => void
}

/**
 * Mobile-friendly image compressor and format normalizer.
 * Resizes 12MP+ camera photos to max 1600px and outputs a fast ~250KB JPEG.
 */
async function prepareImageForUpload(rawFile: File): Promise<{ file: File; previewUrl: string }> {
  if (!rawFile.type.startsWith("image/")) {
    return { file: rawFile, previewUrl: URL.createObjectURL(rawFile) }
  }

  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        try {
          const maxDim = 1600
          let { width, height } = img
          if (width > maxDim || height > maxDim) {
            if (width > height) {
              height = Math.round((height * maxDim) / width)
              width = maxDim
            } else {
              width = Math.round((width * maxDim) / height)
              height = maxDim
            }
          }

          const canvas = document.createElement("canvas")
          canvas.width = width
          canvas.height = height
          const ctx = canvas.getContext("2d")
          if (!ctx) {
            return resolve({ file: rawFile, previewUrl: URL.createObjectURL(rawFile) })
          }

          ctx.drawImage(img, 0, 0, width, height)
          canvas.toBlob(
            (blob) => {
              if (!blob) {
                return resolve({ file: rawFile, previewUrl: URL.createObjectURL(rawFile) })
              }
              const cleanName = (rawFile.name || "evidence.jpg").replace(/\.[^/.]+$/, "") + ".jpg"
              const optimizedFile = new File([blob], cleanName, { type: "image/jpeg" })
              resolve({ file: optimizedFile, previewUrl: URL.createObjectURL(optimizedFile) })
            },
            "image/jpeg",
            0.82,
          )
        } catch {
          resolve({ file: rawFile, previewUrl: URL.createObjectURL(rawFile) })
        }
      }
      img.onerror = () => {
        resolve({ file: rawFile, previewUrl: URL.createObjectURL(rawFile) })
      }
      img.src = e.target?.result as string
    }
    reader.onerror = () => {
      resolve({ file: rawFile, previewUrl: URL.createObjectURL(rawFile) })
    }
    reader.readAsDataURL(rawFile)
  })
}

export function Capture({ onFiled, onLookup }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const addMoreInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const addCameraInputRef = useRef<HTMLInputElement>(null)
  const [showAddModal, setShowAddModal] = useState(false)

  // Multiple files & previews
  const [files, setFiles] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [activeIdx, setActiveIdx] = useState(0)

  // Citizen info
  const [name, setName] = useState(() => localStorage.getItem("cp_name") || "")
  const [phone, setPhone] = useState(() => localStorage.getItem("cp_phone") || "")

  // Location info (Default to Pune coordinates)
  const [lat, setLat] = useState(() => localStorage.getItem("cp_lat") || "18.5204")
  const [lng, setLng] = useState(() => localStorage.getItem("cp_lng") || "73.8567")
  const [geoHint, setGeoHint] = useState("Pinned to Pune (default). Tap below to switch city.")

  const [lookup, setLookup] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Triage state
  const [triageChecking, setTriageChecking] = useState(false)
  const [triageResult, setTriageResult] = useState<Triage | null>(null)
  const [isNotGarbage, setIsNotGarbage] = useState(false)
  const [rejectionReason, setRejectionReason] = useState<string | null>(null)

  useEffect(() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(5))
        setLng(pos.coords.longitude.toFixed(5))
        setGeoHint("Pin from this device.")
      },
      () => {
        setGeoHint("Location blocked on HTTP. Using selected city pin.")
      },
      { timeout: 5000, enableHighAccuracy: true },
    )
  }, [])

  async function handleFilesSelected(newRawFiles: FileList | File[] | null, append = false) {
    if (!newRawFiles || newRawFiles.length === 0) return
    setError(null)
    setIsNotGarbage(false)
    setRejectionReason(null)
    setTriageResult(null)

    const rawArray = Array.from(newRawFiles)
    // Process and optimize all images in parallel
    const optimizedResults = await Promise.all(rawArray.map((f) => prepareImageForUpload(f)))

    const nextFiles = append
      ? [...files, ...optimizedResults.map((r) => r.file)]
      : optimizedResults.map((r) => r.file)
    const nextPreviews = append
      ? [...previews, ...optimizedResults.map((r) => r.previewUrl)]
      : optimizedResults.map((r) => r.previewUrl)

    setFiles(nextFiles)
    setPreviews(nextPreviews)
    if (!append) {
      setActiveIdx(0)
    }

    // Run instant pre-flight triage check via triage_service on the primary and attached images
    setTriageChecking(true)
    try {
      const triage = await checkTriage(nextFiles)
      setTriageResult(triage)
      if (triage.is_valid_waste === false) {
        setIsNotGarbage(true)
        setRejectionReason(
          triage.rejection_reason ||
            "The triage service confirmed that this uploaded picture does not depict garbage, trash, or municipal waste.",
        )
      } else {
        setIsNotGarbage(false)
        setRejectionReason(null)
      }
    } catch (err) {
      console.warn("Pre-flight triage check notice:", err)
    } finally {
      setTriageChecking(false)
    }
  }

  function removePhoto(indexToRemove: number) {
    const nextFiles = files.filter((_, idx) => idx !== indexToRemove)
    const nextPreviews = previews.filter((_, idx) => idx !== indexToRemove)
    setFiles(nextFiles)
    setPreviews(nextPreviews)
    if (activeIdx >= nextPreviews.length) {
      setActiveIdx(Math.max(0, nextPreviews.length - 1))
    }
    if (nextFiles.length === 0) {
      setIsNotGarbage(false)
      setRejectionReason(null)
      setTriageResult(null)
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (files.length === 0) {
      setError("Please add at least one photo of the dump.")
      return
    }

    if (isNotGarbage) {
      setError("The triage service confirmed this photo is not garbage. Please replace the photo before filing.")
      return
    }

    const latitude = Number(lat)
    const longitude = Number(lng)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      setError("Need a latitude and longitude to route the complaint.")
      return
    }

    const digits = phone.replace(/\D/g, "")
    if (digits.length < 10) {
      setError("Enter the mobile number that will receive the portal OTP.")
      return
    }

    const trimmedName = name.trim()
    localStorage.setItem("cp_name", trimmedName)
    localStorage.setItem("cp_phone", digits)
    localStorage.setItem("cp_lat", String(latitude))
    localStorage.setItem("cp_lng", String(longitude))

    setBusy(true)
    try {
      const result = await createReport({
        images: files,
        image: files[0],
        lat: latitude,
        lng: longitude,
        userPhone: digits,
        userName: trimmedName,
      })
      onFiled(result.ticket_id, previews[0] || "")
    } catch (err) {
      if (err instanceof TriageRejectionError) {
        setIsNotGarbage(true)
        setRejectionReason(err.rejection.reason)
        if (err.rejection.triage) {
          setTriageResult(err.rejection.triage)
        }
        setError(null)
      } else {
        setError(err instanceof Error ? err.message : "Filing failed.")
      }
    } finally {
      setBusy(false)
    }
  }

  const activePreview = previews[activeIdx] || previews[0] || null

  return (
    <form onSubmit={onSubmit} className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
      <section>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-stamp">Field intake</p>
        <h1 className="mt-2 font-display text-[2.2rem] sm:text-[2.55rem] leading-[1.05] font-semibold tracking-tight text-ink sm:text-5xl">
          Photograph the pile.
          <span className="block italic text-stamp-deep">We take it to the corporation.</span>
        </h1>
        <p className="mt-3 max-w-xl text-[14px] sm:text-[15px] leading-relaxed text-dust">
          CivicPulse reads the scene, finds the urban local body, and drives their grievance portal.
          Upload multiple photos from different angles for a stronger case file.
        </p>

        {/* EVIDENCE PHOTO DROPZONE & PREVIEW (SUPPORTS MULTIPLE IMAGES) */}
        <div className="relative mt-6 sm:mt-8 flex min-h-[280px] w-full flex-col items-center justify-center overflow-hidden rounded-[28px] border-2 border-dashed border-rule bg-paper-deep/60 text-dust transition hover:border-stamp">
          {activePreview ? (
            <div className="relative h-full min-h-[300px] max-h-[440px] w-full">
              <img
                src={activePreview}
                alt="Selected waste evidence"
                className={`h-full min-h-[300px] max-h-[440px] w-full object-cover transition ${
                  isNotGarbage ? "brightness-[0.75] contrast-[1.05]" : ""
                }`}
              />

              {/* Photo count pill */}
              <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-ink/80 px-3 py-1 text-xs font-semibold text-paper shadow-md backdrop-blur">
                <span>Photo {activeIdx + 1} of {files.length}</span>
              </div>

              {/* Quick action buttons on preview */}
              <div className="absolute bottom-3 right-3 z-20 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => addCameraInputRef.current?.click()}
                  title="Click photo using camera"
                  className="inline-flex items-center gap-1.5 rounded-full bg-stamp hover:bg-stamp-deep text-paper px-3 py-1.5 text-xs font-semibold shadow-lg backdrop-blur transition active:scale-95"
                >
                  <Camera size={13} />
                  <span>Camera</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddModal(true)}
                  title="Add more photos"
                  className="inline-flex items-center gap-1.5 rounded-full bg-ink/85 hover:bg-ink text-paper px-3 py-1.5 text-xs font-semibold shadow-lg backdrop-blur transition active:scale-95"
                >
                  <Plus size={13} />
                  <span>Add</span>
                </button>
              </div>

              {/* Watermark stamp overlay if triage confirmed it is NOT garbage */}
              {isNotGarbage && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-stamp/20 p-6 text-center backdrop-blur-[1px] animate-scale-in">
                  <div className="stamp border-stamp bg-paper px-6 py-3 font-bold text-stamp shadow-2xl animate-stamp-slam">
                    <span className="block text-[10px] tracking-[0.22em] uppercase text-stamp">Triage Verdict</span>
                    <span className="block font-display text-xl tracking-normal text-stamp-deep">✕ Not Municipal Garbage</span>
                  </div>
                  <p className="mt-3 rounded-full bg-ink/80 px-3.5 py-1 text-xs font-semibold text-paper shadow-md animate-stagger-2">
                    Tap to replace with a photo of garbage
                  </p>
                </div>
              )}

              {/* Live scanning badge & scanning laser line overlay */}
              {triageChecking && (
                <>
                  <div className="pointer-events-none absolute inset-x-0 z-20 h-1 bg-gradient-to-r from-transparent via-stamp to-transparent shadow-[0_0_14px_rgba(185,58,34,0.95)] animate-scan-laser" />
                  <div className="pointer-events-none absolute inset-0 z-10 bg-gradient-to-b from-stamp/10 via-transparent to-stamp/10 animate-pulse" />
                  <div className="absolute top-3 right-3 z-30 flex items-center gap-2 rounded-full border border-rule bg-paper/95 px-3 py-1.5 text-xs font-semibold text-ink shadow-md backdrop-blur animate-scale-in">
                    <Loader2 size={13} className="animate-spin text-stamp" />
                    <span>Triage inspecting scene…</span>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="relative flex w-full flex-col items-center justify-center px-6 py-12 text-center">
              <span className="grid h-14 w-14 place-items-center rounded-full bg-stamp text-paper shadow-md">
                <Camera size={24} />
              </span>
              <span className="mt-3 font-display text-2xl text-ink">Drop evidence here</span>
              <span className="mt-1 max-w-xs text-sm text-dust">
                Upload one or multiple photos. Camera or gallery. Street-level, with a landmark in frame.
              </span>

              {/* Direct mobile action buttons */}
              <div className="relative z-30 mt-5 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-full bg-stamp px-4 py-2.5 text-xs font-semibold text-paper shadow transition hover:bg-stamp-deep active:scale-95"
                >
                  <Camera size={14} /> Open Camera
                </button>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-full border border-ink bg-paper px-4 py-2.5 text-xs font-semibold text-ink transition hover:bg-paper-deep active:scale-95"
                >
                  <ImageIcon size={14} /> Select Photos (Multiple)
                </button>
              </div>

              {/* Full-bleed file input overlay for desktop drag-and-drop or general tap */}
              <input
                type="file"
                accept="image/*"
                multiple
                className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                onChange={(e) => {
                  void handleFilesSelected(e.target.files, false)
                  e.target.value = ""
                }}
              />
            </div>
          )}
        </div>

        {/* THUMBNAIL FILMSTRIP FOR MULTIPLE PHOTOS */}
        {previews.length > 0 && (
          <div className="mt-4 rounded-2xl border border-rule bg-paper/60 p-3">
            <div className="flex items-center justify-between pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-dust">
              <span>Attached Evidence ({previews.length} {previews.length === 1 ? "photo" : "photos"})</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => addCameraInputRef.current?.click()}
                  className="inline-flex items-center gap-1 rounded-md bg-stamp/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-stamp transition hover:bg-stamp hover:text-paper"
                  title="Click photo using camera"
                >
                  <Camera size={11} /> + Camera
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddModal(true)}
                  className="inline-flex items-center gap-1 rounded-md bg-paper-deep px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-dust transition hover:text-ink"
                  title="Add more photos"
                >
                  <Plus size={11} /> + Add
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2.5 overflow-x-auto pb-1">
              {previews.map((prev, idx) => (
                <div
                  key={prev}
                  className={`group relative shrink-0 rounded-xl overflow-hidden border-2 transition-all duration-200 cursor-pointer ${
                    activeIdx === idx
                      ? "border-stamp ring-2 ring-stamp/30 shadow-md scale-105"
                      : "border-rule hover:border-ink opacity-80 hover:opacity-100 hover:scale-[1.02]"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setActiveIdx(idx)}
                    className="block h-16 w-16 cursor-pointer overflow-hidden bg-paper-deep"
                  >
                    <img src={prev} alt={`Thumbnail ${idx + 1}`} className="h-full w-full object-cover" />
                  </button>

                  <span className="absolute bottom-1 left-1 rounded bg-ink/75 px-1 py-0.2 text-[9px] font-bold text-paper">
                    #{idx + 1}
                  </span>

                  {/* Remove button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      removePhoto(idx)
                    }}
                    title="Remove photo"
                    className="absolute top-1 right-1 grid h-5 w-5 place-items-center rounded-full bg-stamp text-paper shadow hover:bg-stamp-deep transition"
                  >
                    <X size={11} />
                  </button>
                </div>
              ))}

              {/* Take Photo with Camera */}
              <button
                type="button"
                onClick={() => addCameraInputRef.current?.click()}
                className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-xl border-2 border-dashed border-stamp bg-stamp/10 text-stamp transition hover:bg-stamp hover:text-paper active:scale-95 shadow-sm"
                title="Click photo using camera"
              >
                <Camera size={18} />
                <span className="text-[9px] font-semibold uppercase mt-0.5">Camera</span>
              </button>

              {/* Add more photo button (opens chooser modal or library) */}
              <button
                type="button"
                onClick={() => setShowAddModal(true)}
                className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-xl border-2 border-dashed border-rule bg-paper-deep/70 text-dust transition hover:border-stamp hover:text-stamp active:scale-95 shadow-sm"
                title="Add another photo"
              >
                <Plus size={18} />
                <span className="text-[9px] font-semibold uppercase mt-0.5">Add</span>
              </button>
            </div>
          </div>
        )}

        {/* Hidden inputs specifically wired to direct Camera vs Library actions */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            void handleFilesSelected(e.target.files, previews.length > 0)
            e.target.value = ""
          }}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            void handleFilesSelected(e.target.files, false)
            e.target.value = ""
          }}
        />
        {/* Dedicated camera capture that appends to existing files */}
        <input
          ref={addCameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            void handleFilesSelected(e.target.files, true)
            e.target.value = ""
          }}
        />
        {/* Dedicated gallery / file picker that appends to existing files */}
        <input
          ref={addMoreInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            void handleFilesSelected(e.target.files, true)
            e.target.value = ""
          }}
        />

        {/* MODAL / SHEET: ADD PHOTO CHOOSER (CAMERA OR GALLERY) */}
        {showAddModal && (
          <div
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-ink/60 p-4 backdrop-blur-sm animate-fadeIn"
            onClick={() => setShowAddModal(false)}
          >
            <div
              className="w-full max-w-sm rounded-3xl border border-rule bg-paper p-5 sm:p-6 shadow-2xl animate-scaleUp"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between pb-3 border-b border-rule/60">
                <div>
                  <h3 className="font-display text-lg font-semibold text-ink">Add Evidence Photo</h3>
                  <p className="text-xs text-dust">Choose how to attach additional evidence</p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="grid h-8 w-8 place-items-center rounded-full bg-paper-deep text-dust hover:text-ink transition"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="mt-4 grid gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false)
                    addCameraInputRef.current?.click()
                  }}
                  className="flex items-center gap-3.5 rounded-2xl border-2 border-stamp/20 bg-stamp/5 p-4 text-left transition hover:border-stamp hover:bg-stamp/10 active:scale-98"
                >
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-stamp text-paper shadow-sm">
                    <Camera size={22} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-ink">Take Photo using Camera</div>
                    <div className="text-xs text-dust">Click another angle live on your phone</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false)
                    addMoreInputRef.current?.click()
                  }}
                  className="flex items-center gap-3.5 rounded-2xl border-2 border-rule bg-paper-deep/50 p-4 text-left transition hover:border-ink hover:bg-paper-deep active:scale-98"
                >
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-rule bg-paper text-ink shadow-sm">
                    <ImageIcon size={22} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-ink">Choose from Photo Library</div>
                    <div className="text-xs text-dust">Select one or multiple saved photos</div>
                  </div>
                </button>
              </div>

              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="mt-4 w-full rounded-full border border-rule py-2.5 text-xs font-semibold text-dust hover:text-ink transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* PROMINENT NOT-GARBAGE MESSAGE BANNER */}
        {isNotGarbage && (
          <div
            role="alert"
            className="mt-5 rounded-[24px] border-2 border-stamp/40 bg-stamp/10 p-5 shadow-sm text-ink animate-fadeIn"
          >
            <div className="flex items-start gap-3.5">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-stamp text-paper shadow-sm">
                <AlertOctagon size={22} />
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-display text-lg font-bold text-stamp-deep">
                    Not a picture of garbage
                  </h3>
                  <span className="stamp border-stamp bg-paper px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-stamp">
                    Triage Rejected
                  </span>
                </div>

                <p className="mt-1.5 text-sm font-semibold text-stamp-deep leading-relaxed">
                  {rejectionReason || "The triage service confirmed that this uploaded picture does not depict public waste or garbage."}
                </p>

                <p className="mt-2 text-xs leading-relaxed text-dust">
                  CivicPulse only routes genuine municipal solid waste, roadside dumping, or sanitation hazards to local municipal corporations. Please upload a clear photo of accumulated waste.
                </p>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => addCameraInputRef.current?.click()}
                    className="inline-flex items-center gap-1.5 rounded-full bg-stamp px-4 py-2 text-xs font-semibold text-paper transition hover:bg-stamp-deep shadow-sm"
                  >
                    <Camera size={14} /> Open Camera
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddModal(true)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-ink bg-paper px-4 py-2 text-xs font-semibold text-ink transition hover:bg-paper-deep shadow-sm"
                  >
                    <Plus size={14} /> Add from Gallery
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* POSITIVE TRIAGE VERIFIED BADGE */}
        {!isNotGarbage && !triageChecking && triageResult?.is_valid_waste && (
          <div className="mt-4 flex items-center justify-between rounded-2xl border border-moss/40 bg-moss-soft/60 px-4 py-3 text-xs text-moss">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="shrink-0 text-moss" />
              <span>
                <strong>Triage Verified:</strong> Civic waste detected (
                {triageResult.waste_categories?.map((c) => c.replace(/_/g, " ")).join(", ") || "municipal waste"}
                ) · Severity {triageResult.severity || 4}/5
              </span>
            </div>
            <span className="hidden font-mono text-[10px] uppercase sm:inline text-moss/80 font-bold">Actionable</span>
          </div>
        )}
      </section>

      <aside className="rounded-[28px] border border-rule bg-paper/80 p-5 sm:p-6 shadow-[0_20px_50px_-28px_rgba(27,23,18,0.45)]">
        {/* CITIZEN NAME INPUT FIELD (FOR STATUTORY COMPLAINT EMAIL & FORM PRE-FILL) */}
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">
            Your Full Name
          </label>
          <div className="mt-2 flex items-center gap-2 rounded-2xl border border-rule bg-paper px-3 focus-within:border-stamp transition">
            <User size={16} className="text-stamp shrink-0" />
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                localStorage.setItem("cp_name", e.target.value)
              }}
              placeholder="e.g. Rajesh Sharma"
              className="h-12 w-full bg-transparent text-base sm:text-sm outline-none"
            />
          </div>
          <p className="mt-1 text-[11px] text-dust">
            Pre-fills your name in official municipal complaint letters and portal forms.
          </p>
        </div>

        {/* MOBILE FOR OTP */}
        <div className="mt-5">
          <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">
            Mobile for OTP
          </label>
          <div className="mt-2 flex items-center gap-2 rounded-2xl border border-rule bg-paper px-3 focus-within:border-stamp transition">
            <Phone size={16} className="text-stamp shrink-0" />
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              inputMode="tel"
              placeholder="10-digit number"
              className="h-12 w-full bg-transparent text-base sm:text-sm outline-none"
            />
          </div>
        </div>

        {/* COORDINATES */}
        <label className="mt-5 block text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">
          Coordinates
        </label>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <input
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="Latitude"
            className="h-12 rounded-2xl border border-rule bg-paper px-3 text-base sm:text-sm outline-none focus:border-stamp transition"
          />
          <input
            value={lng}
            onChange={(e) => setLng(e.target.value)}
            placeholder="Longitude"
            className="h-12 rounded-2xl border border-rule bg-paper px-3 text-base sm:text-sm outline-none focus:border-stamp transition"
          />
        </div>
        <p className="mt-2 flex items-center gap-1.5 text-xs text-dust">
          <MapPin size={12} className="shrink-0" /> {geoHint}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {PLACES.map((place) => {
            const isSelected = Math.abs(Number(lat) - place.lat) < 0.05 && Math.abs(Number(lng) - place.lng) < 0.05
            return (
              <button
                key={place.name}
                type="button"
                onClick={() => {
                  setLat(String(place.lat))
                  setLng(String(place.lng))
                  setGeoHint(`Pinned to ${place.name}.`)
                }}
                className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all duration-200 cursor-pointer active:scale-95 ${
                  isSelected
                    ? "bg-ink text-paper shadow-md scale-105"
                    : "border border-rule text-ink hover:border-ink hover:bg-paper-deep/60"
                }`}
              >
                {place.name}
              </button>
            )
          })}
        </div>

        {/* NOT-GARBAGE NOTICE IN SIDEBAR */}
        {isNotGarbage && (
          <div className="mt-4 rounded-2xl border border-stamp/40 bg-stamp/10 p-3.5 text-xs text-stamp-deep animate-scale-in">
            <p className="flex items-center gap-1.5 font-semibold">
              <AlertOctagon size={14} /> Submission blocked
            </p>
            <p className="mt-1 leading-normal">
              The triage service confirmed this photo is not garbage. Please replace the photo before filing.
            </p>
          </div>
        )}

        {error && (
          <p className="mt-4 rounded-2xl bg-stamp/10 px-3 py-2 text-sm text-stamp-deep animate-scale-in">{error}</p>
        )}

        <button
          type="submit"
          disabled={busy || triageChecking || isNotGarbage}
          className={`mt-6 w-full rounded-full py-3.5 text-sm font-semibold tracking-wide transition-all duration-200 active:scale-[0.98] cursor-pointer ${
            isNotGarbage
              ? "bg-rule/70 text-dust cursor-not-allowed border border-rule"
              : "bg-stamp text-paper hover:bg-stamp-deep hover:shadow-xl hover:scale-[1.01] disabled:opacity-60 disabled:hover:scale-100"
          }`}
        >
          {isNotGarbage
            ? "Cannot file · Not a picture of garbage"
            : triageChecking
              ? "Verifying image triage…"
              : busy
                ? "Reading the scene…"
                : files.length > 1
                  ? `File this dump (${files.length} photos)`
                  : "File this dump"}
        </button>

        <div className="mt-8 border-t border-rule pt-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-dust">Open a case</p>
          <div className="mt-2 flex gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-2xl border border-rule bg-paper px-3">
              <Search size={15} className="text-dust shrink-0" />
              <input
                value={lookup}
                onChange={(e) => setLookup(e.target.value)}
                placeholder="Ticket id"
                className="h-11 w-full bg-transparent text-base sm:text-sm outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => lookup.trim() && onLookup(lookup.trim())}
              className="rounded-2xl border border-ink px-4 text-sm font-medium hover:bg-paper-deep transition"
            >
              Open
            </button>
          </div>
        </div>
      </aside>
    </form>
  )
}
