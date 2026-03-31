import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getUpcomingSeasons, getActiveSeason } from '../../utils/seasons.js'

export default function EidPlannerWidget() {
  const navigate  = useNavigate()
  const upcoming  = getUpcomingSeasons(30)
  const active    = getActiveSeason()

  // Show if an Eid season is active or coming within 30 days
  const eidSeason = active?.key?.startsWith('eid')
    ? { ...active, daysUntil: 0 }
    : upcoming.find(s => s.key?.startsWith('eid'))

  if (!eidSeason) return null

  const isActive = eidSeason.daysUntil === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-5 border-l-4 border-accent-400"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{eidSeason.emoji}</span>
            <p className="label-xs">{eidSeason.label}</p>
          </div>

          {isActive ? (
            <p className="text-sm font-semibold text-brand-800 dark:text-brand-200">
              It's {eidSeason.label}! Have you planned your look?
            </p>
          ) : (
            <p className="text-sm font-semibold text-brand-800 dark:text-brand-200">
              {eidSeason.label} in <span className="text-accent-600">{eidSeason.daysUntil} days</span>
            </p>
          )}

          <p className="text-xs text-brand-500 dark:text-brand-400 mt-1">
            Plan your Chaand Raat, Eid morning, and family visit looks.
          </p>
        </div>

        <button
          onClick={() => navigate('/calendar')}
          className="flex-shrink-0 btn-primary text-xs py-1.5 px-3"
        >
          Plan Now
        </button>
      </div>
    </motion.div>
  )
}
