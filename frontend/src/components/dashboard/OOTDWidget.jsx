import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { FiSave, FiRefreshCw, FiSun, FiThermometer } from 'react-icons/fi'
import { getOOTD } from '../../api/recommendations.js'
import { saveOutfit } from '../../api/outfits.js'
import { scoreToPercent } from '../../utils/formatters.js'
import ConfidenceBadge from '../ui/ConfidenceBadge.jsx'
import { resolveUrl } from '../../utils/resolveUrl.js'

export default function OOTDWidget() {
  const [saved, setSaved] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ootd'],
    queryFn: () => getOOTD(),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const outfit = data?.outfit
      if (!outfit) return Promise.reject(new Error('No outfit to save'))
      const items = outfit.items?.map(i => i.id) ?? []
      const cats = outfit.items?.map(i => i.category).join('+') ?? 'outfit'
      const name = `OOTD ${outfit.occasion} ${cats} ${Date.now()}`
      return saveOutfit({
        name,
        occasion: outfit.occasion,
        item_ids: items,
        final_score: outfit.final_score,
        confidence: outfit.confidence,
      })
    },
    onSuccess: () => {
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['saved'] })
      toast.success('Outfit saved to your collection!')
    },
    onError: () => toast.error('Could not save outfit. Try again.'),
  })

  const outfit = data?.outfit

  if (isLoading) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="skeleton h-6 w-32 rounded-lg" />
          <div className="skeleton h-5 w-16 rounded-lg ml-auto" />
        </div>
        <div className="flex gap-3 mb-4">
          {[1,2,3].map(i => <div key={i} className="skeleton w-20 h-20 rounded-xl" />)}
        </div>
        <div className="skeleton h-2 w-full rounded-lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6">
        <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200 mb-2">Today&apos;s Pick</h2>
        <p className="text-sm text-brand-400 dark:text-brand-500">Could not load today&apos;s outfit.</p>
      </div>
    )
  }

  if (!outfit) {
    return (
      <div className="card p-6">
        <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200 mb-2">Today&apos;s Pick</h2>
        <p className="text-sm text-brand-500 dark:text-brand-400">{data?.reason || 'Upload more items to get daily outfit suggestions.'}</p>
      </div>
    )
  }

  const pct = scoreToPercent(outfit.final_score)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="card p-6 relative overflow-hidden"
    >
      {/* Subtle accent line */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-accent-400 via-accent-500 to-accent-600" />

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-100/80 dark:bg-accent-900/25 flex items-center justify-center">
              <FiSun className="text-accent-500" size={16} />
            </div>
            <h2 className="font-display text-2xl font-semibold text-brand-800 dark:text-brand-200">Today&apos;s Pick</h2>
          </div>
          <p className="text-xs text-brand-400 dark:text-brand-500 mt-1 ml-[42px] flex items-center gap-1.5">
            <span className="capitalize">{outfit.occasion}</span>
            <span className="text-brand-300 dark:text-brand-600">/</span>
            <FiThermometer size={11} />
            <span>{outfit.temperature_used}°C</span>
            {outfit.is_fresh && (
              <span className="ml-1 px-1.5 py-0.5 bg-emerald-100/80 dark:bg-emerald-900/25 text-emerald-700 dark:text-emerald-400 text-[10px] rounded-full font-semibold">Fresh</span>
            )}
          </p>
        </div>
        <div className="text-right">
          <span className="data-value text-2xl">{pct}%</span>
          <div className="mt-1">
            <ConfidenceBadge level={outfit.confidence} />
          </div>
        </div>
      </div>

      {/* Items */}
      <AnimatePresence mode="wait">
        <motion.div
          key={outfit.items?.map(i => i.id).join('-')}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="flex gap-3 mb-5 overflow-x-auto pb-1"
        >
          {outfit.items.map((item, idx) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.08 }}
              className="flex-shrink-0"
            >
              <div className="w-20 h-20 rounded-xl overflow-hidden bg-brand-100/60 dark:bg-brand-800/40 border border-brand-100/60 dark:border-brand-700/40 shadow-sm">
                {item.image_url && (
                  <img src={resolveUrl(item.image_url)} alt={item.category} loading="lazy" decoding="async" className="w-full h-full object-cover" />
                )}
              </div>
              <p className="text-[11px] text-brand-500 dark:text-brand-400 text-center mt-1.5 capitalize">{item.category}</p>
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>

      {/* Score breakdown */}
      <div className="mb-5">
        <div className="h-1.5 bg-brand-100/80 dark:bg-brand-800/60 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
            className={`h-full rounded-full ${
              pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-accent-500' : 'bg-red-500'
            }`}
          />
        </div>
        <div className="flex justify-between text-[11px] text-brand-400 dark:text-brand-500 mt-1.5 font-mono">
          <span>Model {scoreToPercent(outfit.model2_score)}%</span>
          <span>Color {scoreToPercent(outfit.color_score)}%</span>
          <span>Weather {scoreToPercent(outfit.weather_score)}%</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saved || saveMutation.isPending}
          className={`text-sm font-medium px-4 py-2.5 rounded-xl transition-all flex-1 flex items-center justify-center gap-2 ${
            saved
              ? 'bg-emerald-50/80 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-700/40'
              : 'btn-accent'
          }`}
        >
          <FiSave size={14} />
          {saved ? 'Saved' : 'Save outfit'}
        </button>
        <button
          onClick={() => { setSaved(false); refetch() }}
          className="text-sm font-medium px-4 py-2.5 rounded-xl btn-secondary flex items-center justify-center gap-2"
        >
          <FiRefreshCw size={14} />
          Different
        </button>
      </div>
    </motion.div>
  )
}
