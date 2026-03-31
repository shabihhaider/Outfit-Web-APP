import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiZap } from 'react-icons/fi'
import { getMyStyleDNA } from '../../api/social.js'

const TONE_LABELS = {
  neutral: '⚪ Neutral',
  dark:    '🖤 Dark',
  bright:  '🌈 Bright',
  earthy:  '🟤 Earthy',
  rich:    '🔴 Rich',
}

export default function StyleDNACard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['style-dna'],
    queryFn:  getMyStyleDNA,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 bg-brand-100 dark:bg-brand-800 rounded w-24 mb-3" />
        <div className="h-8 bg-brand-100 dark:bg-brand-800 rounded w-48 mb-2" />
        <div className="h-3 bg-brand-100 dark:bg-brand-800 rounded w-full" />
      </div>
    )
  }

  if (isError || !data) return null

  const { persona_name, vibe_slug, tagline, dominant_tones, formality_mix, category_mix, total_items } = data

  if (total_items < 3) {
    return (
      <div className="card p-5">
        <p className="label-xs mb-2">Style DNA</p>
        <p className="text-sm text-brand-500 dark:text-brand-400">
          Add at least 3 wardrobe items to unlock your Style DNA.
        </p>
      </div>
    )
  }

  const topCategory = Object.entries(category_mix).sort((a, b) => b[1] - a[1])[0]?.[0]
  const topFormality = Object.entries(formality_mix).sort((a, b) => b[1] - a[1])[0]?.[0]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-5 overflow-hidden relative"
    >
      {/* Background accent */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-accent-100/40 dark:from-accent-900/20 to-transparent rounded-bl-full -z-0" />

      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <FiZap size={13} className="text-accent-500" />
          <p className="label-xs">Style DNA</p>
        </div>

        <h3 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 mb-1">
          {persona_name}
        </h3>
        <p className="text-sm text-brand-500 dark:text-brand-400 italic mb-4">
          "{tagline}"
        </p>

        {/* Tone pills */}
        {dominant_tones.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {dominant_tones.map(tone => (
              <span
                key={tone}
                className="text-[11px] px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-800 text-brand-600 dark:text-brand-400"
              >
                {TONE_LABELS[tone] || tone}
              </span>
            ))}
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-lg font-bold text-brand-900 dark:text-brand-100">{total_items}</p>
            <p className="text-[10px] text-brand-400 uppercase tracking-wide">Items</p>
          </div>
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 capitalize">{topCategory}</p>
            <p className="text-[10px] text-brand-400 uppercase tracking-wide">Main Cat</p>
          </div>
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 capitalize">{topFormality}</p>
            <p className="text-[10px] text-brand-400 uppercase tracking-wide">Formality</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
