import { useState } from 'react'
import { FiInfo } from 'react-icons/fi'

/**
 * Small ⓘ icon that shows a tooltip explaining the outfit match score.
 * Works on desktop (hover) and mobile (tap to toggle).
 */
/**
 * placement: "up" (default) — tooltip appears above the icon
 *            "down"         — tooltip appears below (use when card is near top of viewport)
 */
export default function ScoreInfoTooltip({ placement = 'up' }) {
  const [open, setOpen] = useState(false)

  const above = placement === 'up'
  const tooltipPos = above
    ? 'bottom-full left-1/2 -translate-x-1/2 mb-2'
    : 'top-full left-0 mt-2'
  const arrowClass = above
    ? 'absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-brand-900 dark:border-t-brand-100'
    : 'absolute bottom-full left-4 border-4 border-transparent border-b-brand-900 dark:border-b-brand-100'

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-label="What does this score mean?"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        onBlur={() => setOpen(false)}
        className="group flex items-center justify-center w-5 h-5 rounded-full text-brand-300 hover:text-accent-500 dark:text-brand-600 dark:hover:text-accent-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-400"
      >
        <FiInfo size={13} />
      </button>

      {open && (
        <div
          role="tooltip"
          className={`absolute ${tooltipPos} w-60 z-50 bg-brand-900 dark:bg-brand-100 text-white dark:text-brand-900 text-[11px] rounded-xl shadow-xl px-3.5 py-3 pointer-events-none`}
        >
          <p className="font-semibold mb-1.5">Match Score</p>
          <p className="text-brand-300 dark:text-brand-600 mb-2">Combines 4 factors:</p>
          <ul className="space-y-0.5 text-brand-200 dark:text-brand-700">
            <li><span className="font-medium text-white dark:text-brand-900">Style</span> — how well pieces pair together</li>
            <li><span className="font-medium text-white dark:text-brand-900">Color</span> — color harmony between items</li>
            <li><span className="font-medium text-white dark:text-brand-900">Weather</span> — suitability for today&apos;s temperature</li>
            <li><span className="font-medium text-white dark:text-brand-900">Cohesion</span> — formality &amp; occasion consistency</li>
          </ul>
          <div className="mt-2 pt-2 border-t border-brand-700 dark:border-brand-300 text-brand-400 dark:text-brand-500">
            85%+ great · 70–84% good · &lt;70% fair
          </div>
          <div className={arrowClass} />
        </div>
      )}
    </span>
  )
}
