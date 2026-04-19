import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiZap, FiTarget, FiSun, FiMoon, FiCoffee, FiActivity, FiGlobe, FiHexagon, FiArrowRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import { getMyStyleDNA } from '../../api/social.js'

const PERSONA_ICONS = {
  'The Old Money':       FiGlobe,
  'The Power Dresser':   FiTarget,
  'Statement Maker':    FiZap,
  'Mughal Luxe':        FiHexagon,
  'The Elegant':        FiMoon,
  'The Classicist':     FiCoffee,
  'The Minimalist':     FiSun,
  'The Dark Academic':  FiMoon,
  'Street Explorer':    FiActivity,
  'The Boho Soul':      FiSun,
  'The Smart Casual':   FiCoffee,
  'The Cottagecore':    FiSun,
  'The Gorpcore':      FiActivity,
  'Urban Navigator':    FiTarget,
  'The Sneakerhead':    FiZap,
  'The Purist':         FiSun,
  'The Collector':      FiHexagon,
  'Versatile Classic':  FiGlobe,
  'Y2K Revivalist':     FiZap,
  'The Desi Chic':      FiSun,
  'Modern Mughal':      FiHexagon,
  'East-West Fusion':   FiGlobe,
  'The Lawn Chic':      FiSun,
}

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
<div className="relative z-10">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center justify-center w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900/30">
            <FiZap size={11} className="text-accent-700 dark:text-accent-400" />
          </div>
          <p className="label-xs text-brand-500 dark:text-brand-400">Style DNA</p>
        </div>

        <div className="flex items-center gap-3 mb-1">
          {(() => {
            const Icon = PERSONA_ICONS[persona_name] || FiZap
            return <Icon size={24} className="text-brand-900 dark:text-brand-100" />
          })()}
          <h3 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100">
            {persona_name}
          </h3>
        </div>
        <p className="text-sm text-brand-500 dark:text-brand-400 italic mb-4">
          &ldquo;{tagline}&rdquo;
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
        <div className="grid grid-cols-3 gap-2 text-center mb-4">
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-lg font-bold text-brand-900 dark:text-brand-100">{total_items}</p>
            <p className="text-[10px] text-brand-500 uppercase tracking-wide">Items</p>
          </div>
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 capitalize">{topCategory}</p>
            <p className="text-[10px] text-brand-500 uppercase tracking-wide">Main Cat</p>
          </div>
          <div className="bg-brand-50 dark:bg-brand-800/40 rounded-lg p-2">
            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 capitalize">{topFormality}</p>
            <p className="text-[10px] text-brand-500 uppercase tracking-wide">Formality</p>
          </div>
        </div>

        {/* CTA */}
        <Link
          to="/recommendations"
          className="flex items-center justify-center gap-1.5 w-full h-9 rounded-xl btn-accent text-sm font-medium"
        >
          Build outfits for your style <FiArrowRight size={14} />
        </Link>
      </div>
    </motion.div>
  )
}
