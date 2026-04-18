import { useEffect, useRef, useState } from 'react'
import { useIsFetching } from '@tanstack/react-query'
import LoadingSpinner from './LoadingSpinner.jsx'

const SESSION_KEY = 'outfitai-warmup-shown'

export default function InitialWarmupOverlay() {
  // Show at most once per browser session — never again after first dismiss.
  const alreadyShown = typeof sessionStorage !== 'undefined'
    ? sessionStorage.getItem(SESSION_KEY) === '1'
    : true

  const [visible, setVisible] = useState(false)
  const dismissedRef = useRef(alreadyShown)
  const isFetching = useIsFetching()

  function dismiss() {
    if (dismissedRef.current) return
    dismissedRef.current = true
    sessionStorage.setItem(SESSION_KEY, '1')
    setVisible(false)
  }

  // Show after 600 ms on first mount if session has not seen it yet.
  // Hard cap at 20 s regardless of fetch state.
  useEffect(() => {
    if (dismissedRef.current) return

    const showTimer = setTimeout(() => setVisible(true), 600)
    const hardCap   = setTimeout(dismiss, 20000)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(hardCap)
    }
  }, []) // intentionally empty — runs exactly once per mount

  // Dismiss 350 ms after all queries have settled, once the overlay is visible.
  useEffect(() => {
    if (!visible || isFetching > 0) return
    const t = setTimeout(dismiss, 350)
    return () => clearTimeout(t)
  }, [visible, isFetching])

  if (!visible) return null

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Application warming up"
      className="fixed inset-0 z-[70] bg-brand-950/70 backdrop-blur-sm flex items-center justify-center px-6"
    >
      <div className="w-full max-w-md rounded-2xl border border-brand-700/60 bg-brand-900/95 px-6 py-5 shadow-xl">
        <p className="text-xs uppercase tracking-[0.2em] text-brand-400 mb-2">OutfitAI</p>
        <LoadingSpinner size="sm" label="Warming up the AI service…" className="justify-start text-brand-100" />
        <p className="text-sm text-brand-300 mt-3">
          This can take a few seconds after idle. We&apos;re loading your wardrobe and recommendations.
        </p>
      </div>
    </div>
  )
}
