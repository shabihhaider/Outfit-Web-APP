import { useState, useRef, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiBookmark, FiCheck, FiShare2, FiInfo, FiX, FiUser } from 'react-icons/fi'
import { saveOutfit } from '../../api/outfits.js'
import OutfitItems from './OutfitItems.jsx'
import WhyThisOutfit from './WhyThisOutfit.jsx'
import FeedbackButtons from './FeedbackButtons.jsx'
import ConfidenceBadge from '../ui/ConfidenceBadge.jsx'
import ScoreInfoTooltip from '../ui/ScoreInfoTooltip.jsx'
import { scoreToPercent } from '../../utils/formatters.js'
import ShareButton from '../ui/ShareButton.jsx'
import OutfitTryOnModal from '../tryon/OutfitTryOnModal.jsx'

export default function OutfitCard({ outfit, occasion }) {
  const [saved, setSaved] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [showNameModal, setShowNameModal] = useState(false)
  const [outfitName, setOutfitName] = useState('')
  const [saveError, setSaveError] = useState('')
  const [tryOnOpen, setTryOnOpen] = useState(false)
  const inputRef = useRef(null)
  const queryClient = useQueryClient()

  useEffect(() => {
    if (showNameModal && inputRef.current) inputRef.current.focus()
  }, [showNameModal])

  const saveMutation = useMutation({
    mutationFn: (name) => {
      const items = outfit.items?.map(i => i.id) ?? []
      return saveOutfit({
        name,
        occasion,
        item_ids: items,
        final_score: outfit.final_score,
        confidence: outfit.confidence,
      })
    },
    onSuccess: () => {
      setSaved(true)
      setShowNameModal(false)
      setSaveError('')
      queryClient.invalidateQueries({ queryKey: ['saved'] })
    },
    onError: (err) => {
      const msg = err?.response?.data?.error ?? err?.message ?? 'Failed to save outfit.'
      setSaveError(msg)
    },
  })

  function handleSaveClick() {
    const cats = outfit.items?.map(i => i.category).join(' + ') ?? 'outfit'
    setOutfitName(`${occasion.charAt(0).toUpperCase() + occasion.slice(1)} ${cats}`)
    setSaveError('')
    setShowNameModal(true)
  }

  function handleConfirmSave() {
    const name = outfitName.trim() || `${occasion} outfit`
    saveMutation.mutate(name)
  }

  const pct = scoreToPercent(outfit.final_score)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="card group overflow-hidden border-brand-100/60 dark:border-brand-800/40 hover:shadow-card-hover"
    >
      {/* Visual Accent */}
      <div className={`h-1 w-full bg-gradient-to-r transition-all duration-500 ${
        pct >= 70 ? 'from-emerald-400 to-emerald-600' : 
        pct >= 50 ? 'from-accent-400 to-accent-600' : 
        'from-red-400 to-red-600'
      }`} />

      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <ConfidenceBadge level={outfit.confidence} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-brand-400 dark:text-brand-500">
                Compatibility
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="data-value text-4xl leading-none">{pct}%</span>
              <ScoreInfoTooltip />
              <span className={`font-display text-lg font-medium italic ${pct >= 75 ? 'text-emerald-500' : pct >= 55 ? 'text-emerald-500/70' : pct >= 40 ? 'text-amber-500' : 'text-red-400'}`}>
                {pct >= 75 ? 'Great Match' : pct >= 55 ? 'Good Match' : pct >= 40 ? 'Fair Match' : 'Weak Match'}
              </span>
            </div>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={handleSaveClick}
              disabled={saved || saveMutation.isPending}
              className={`h-11 px-5 rounded-2xl transition-all duration-300 flex items-center gap-2 font-medium text-sm shadow-sm ${
                saved
                  ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-800/40'
                  : 'btn-accent hover:shadow-md'
              }`}
            >
              {saved ? <><FiCheck size={16} /> Saved</> : <><FiBookmark size={16} /> Save</>}
            </button>
          </div>
        </div>

        {/* Featured Items Section */}
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-brand-50/30 dark:bg-brand-900/10 rounded-3xl -z-10" />
          <div className="p-4">
            <OutfitItems items={outfit.items} />
          </div>
        </div>

        {/* Analysis Summary */}
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-y-2">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs font-bold uppercase tracking-widest text-brand-500 dark:text-brand-400 flex items-center gap-1.5 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
            >
              <FiInfo size={14} className={showDetails ? 'text-accent-500' : ''} />
              {showDetails ? 'Close Analysis' : 'View Analysis'}
            </button>
            <div className="flex gap-2 sm:gap-4">
              <div className="flex flex-col items-end">
                <span className="text-[9px] font-bold uppercase tracking-tighter text-brand-300">Style</span>
                <span className="text-xs font-mono font-bold text-brand-600 dark:text-brand-300">
                  {scoreToPercent(outfit.model2_score)}%
                </span>
              </div>
              {outfit.cohesion_score != null && (
                <div className="flex flex-col items-end">
                  <span className="text-[9px] font-bold uppercase tracking-tighter text-brand-300">Cohesion</span>
                  <span className="text-xs font-mono font-bold text-brand-600 dark:text-brand-300">
                    {scoreToPercent(outfit.cohesion_score)}%
                  </span>
                </div>
              )}
              <div className="flex flex-col items-end">
                <span className="text-[9px] font-bold uppercase tracking-tighter text-brand-300">Weather</span>
                <span className="text-xs font-mono font-bold text-brand-600 dark:text-brand-300">
                  {scoreToPercent(outfit.weather_score)}%
                </span>
              </div>
            </div>
          </div>

          <AnimatePresence>
            {showDetails && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-2 pb-4 border-t border-brand-100/60 dark:border-brand-800/40">
                  <WhyThisOutfit outfit={outfit} defaultOpen={true} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Actions */}
        <div className="mt-6 pt-5 border-t border-brand-100/60 dark:border-brand-800/40 flex items-center justify-between">
          <FeedbackButtons historyId={outfit.history_id} />
          <div className="flex items-center gap-3">
             <button
               onClick={() => setTryOnOpen(true)}
               className="h-9 px-3.5 rounded-xl text-xs font-medium text-brand-500 dark:text-brand-400 border border-brand-200/60 dark:border-brand-700/40 hover:bg-accent-50 dark:hover:bg-accent-900/15 hover:text-accent-600 dark:hover:text-accent-400 hover:border-accent-200 dark:hover:border-accent-700 transition-all flex items-center gap-1.5"
               title="Virtual Try-On"
             >
               <FiUser size={13} /> Try On
             </button>
             <ShareButton outfit={outfit} items={outfit.items} rounded />
          </div>
        </div>
      </div>

      {/* Save Name Modal */}
      <AnimatePresence>
        {showNameModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
            onClick={(e) => { if (e.target === e.currentTarget) setShowNameModal(false) }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 12 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="card-glass w-full max-w-sm p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-display text-lg font-bold text-brand-900 dark:text-brand-100">Name this look</h3>
                <button onClick={() => { setShowNameModal(false); setSaveError('') }} className="w-8 h-8 rounded-lg flex items-center justify-center text-brand-400 hover:text-brand-700 dark:hover:text-brand-200 hover:bg-brand-100 dark:hover:bg-brand-800 transition-all">
                  <FiX size={16} />
                </button>
              </div>
              <input
                ref={inputRef}
                type="text"
                value={outfitName}
                onChange={e => { setOutfitName(e.target.value); setSaveError('') }}
                onKeyDown={e => e.key === 'Enter' && handleConfirmSave()}
                placeholder="e.g. Monday Office Look"
                maxLength={60}
                className="w-full px-4 py-3 rounded-2xl border border-brand-200 dark:border-brand-700 bg-white dark:bg-brand-900 text-brand-900 dark:text-brand-100 text-sm placeholder:text-brand-300 dark:placeholder:text-brand-600 focus:outline-none focus:ring-2 focus:ring-accent-400 mb-2"
              />
              {saveError && (
                <p className="text-xs text-red-500 dark:text-red-400 mb-3 px-1">{saveError}</p>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowNameModal(false); setSaveError('') }}
                  className="flex-1 h-10 rounded-2xl btn-secondary text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmSave}
                  disabled={saveMutation.isPending}
                  className="flex-1 h-10 rounded-2xl btn-primary text-sm font-medium disabled:opacity-50"
                >
                  {saveMutation.isPending ? 'Saving…' : 'Save Look'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <OutfitTryOnModal
        open={tryOnOpen}
        onClose={() => setTryOnOpen(false)}
        items={outfit.items}
        occasion={occasion}
      />
    </motion.div>
  )
}
