import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiChevronDown } from 'react-icons/fi'
import { buildWhyText, scoreToPercent } from '../../utils/formatters.js'

export default function WhyThisOutfit({ outfit, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const lines = buildWhyText(outfit)

  return (
    <div className="border-t border-brand-100/60 dark:border-brand-800/40 pt-3 mt-3">
      <button
        onClick={() => setOpen(o => !o)}
        className="label-xs flex items-center gap-2 hover:text-brand-600 dark:hover:text-brand-300 transition-colors w-full"
      >
        <FiChevronDown
          size={12}
          className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
        <span>Why this outfit?</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2">
              {lines.map((line, i) => (
                <div key={i} className="text-sm text-brand-600 dark:text-brand-400 flex items-start gap-2 p-2.5 bg-brand-50/60 dark:bg-brand-800/30 rounded-xl">
                  {line}
                </div>
              ))}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
                <ScoreBar label="Style" value={outfit.model2_score} weight="45%" />
                <ScoreBar label="Color" value={outfit.color_score} weight="25%" />
                <ScoreBar label="Cohesion" value={outfit.cohesion_score} weight="15%" />
                <ScoreBar label="Weather" value={outfit.weather_score} weight="15%" />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ScoreBar({ label, value, weight }) {
  const pct = scoreToPercent(value)
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-accent-500' : 'bg-red-500'
  return (
    <div>
      <div className="flex justify-between text-[11px] text-brand-500 dark:text-brand-400 mb-1">
        <span>{label}</span>
        <span className="font-mono font-semibold">{pct}%</span>
      </div>
      <div className="h-1.5 bg-brand-200/60 dark:bg-brand-700/40 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      {weight && (
        <div className="text-[9px] text-brand-300 dark:text-brand-600 mt-0.5 text-right">{weight} weight</div>
      )}
    </div>
  )
}
