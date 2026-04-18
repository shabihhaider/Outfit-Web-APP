import { useEffect, useState } from 'react'
import { useIsFetching } from '@tanstack/react-query'
import LoadingSpinner from './LoadingSpinner.jsx'

export default function InitialWarmupOverlay() {
  const isFetching = useIsFetching()
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (dismissed || isFetching === 0) return

    const showTimer = setTimeout(() => {
      setVisible(true)
    }, 600)

    const autoDismissTimer = setTimeout(() => {
      setDismissed(true)
      setVisible(false)
    }, 20000)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(autoDismissTimer)
    }
  }, [dismissed, isFetching])

  useEffect(() => {
    if (!visible || dismissed || isFetching > 0) return

    const hideTimer = setTimeout(() => {
      setDismissed(true)
      setVisible(false)
    }, 350)

    return () => clearTimeout(hideTimer)
  }, [visible, dismissed, isFetching])

  if (!visible || dismissed) return null

  return (
    <div className="fixed inset-0 z-[70] bg-brand-950/70 backdrop-blur-sm flex items-center justify-center px-6">
      <div className="w-full max-w-md rounded-2xl border border-brand-700/60 bg-brand-900/95 px-6 py-5 shadow-xl">
        <p className="text-xs uppercase tracking-[0.2em] text-brand-400 mb-2">OutfitAI</p>
        <LoadingSpinner size="sm" label="Warming up the AI service..." className="justify-start text-brand-100" />
        <p className="text-sm text-brand-300 mt-3">This can take a few seconds after idle. We&apos;re loading your wardrobe and recommendations.</p>
      </div>
    </div>
  )
}
