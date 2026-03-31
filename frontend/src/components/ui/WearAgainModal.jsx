import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiArrowRight, FiRotateCcw, FiCalendar, FiBookmark, FiAlertCircle } from 'react-icons/fi'
import { scoreOutfit } from '../../api/recommendations.js'
import { scoreToPercent } from '../../utils/formatters.js'
import ConfidenceBadge from './ConfidenceBadge.jsx'
import LoadingSpinner from './LoadingSpinner.jsx'

export default function WearAgainModal({ outfit, open, onClose, onSave, onCalendar }) {
  const itemIds = outfit ? (outfit.item_ids_parsed || outfit.items?.map(i => i.id) || []) : []

  const scoreQuery = useQuery({
    queryKey: ['rescore', itemIds],
    queryFn: () => scoreOutfit({
      item_ids: itemIds,
      occasion: outfit?.occasion || 'casual',
      temp_celsius: 25,
    }),
    enabled: open && itemIds.length >= 2,
  })

  const originalPct = scoreToPercent(outfit?.final_score)
  const newData = scoreQuery.data
  const newPct = newData?.valid ? scoreToPercent(newData.final_score) : null
  const delta = newPct !== null ? newPct - originalPct : null

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/40 backdrop-blur-md"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="card-glass p-8 w-full max-w-md shadow-elevated border-brand-100/60 dark:border-brand-800/40"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-8">
               <div className="flex items-center gap-3">
                 <div className="w-10 h-10 rounded-2xl bg-brand-900 dark:bg-brand-100 flex items-center justify-center text-brand-100 dark:text-brand-900">
                    <FiRotateCcw size={18} />
                 </div>
                 <h3 className="font-display text-2xl font-bold text-brand-900 dark:text-brand-100 tracking-tight italic">Reclaim Style</h3>
               </div>
               <button onClick={onClose} className="p-2 rounded-xl text-brand-400 hover:bg-brand-100/40 dark:hover:bg-brand-800/40 transition-all hover:rotate-90">
                 <FiX size={20} />
               </button>
            </div>

            {scoreQuery.isLoading && (
              <div className="flex flex-col items-center gap-4 py-12 justify-center">
                <LoadingSpinner size="lg" />
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-400">Synchronizing Analysis</p>
              </div>
            )}

            {scoreQuery.isError && (
              <div className="py-10 text-center">
                 <FiAlertCircle className="mx-auto text-red-400 mb-3" size={32} />
                 <p className="text-sm font-medium text-brand-600 dark:text-brand-400">Scoring pipeline interrupted.</p>
              </div>
            )}

            {newData && (
              <>
                <div className="bg-brand-50/40 dark:bg-brand-900/10 rounded-[24px] p-6 border border-brand-100/40 dark:border-brand-800/40 mb-8">
                   <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-brand-400 mb-2">Historical</p>
                        <p className="data-value text-3xl opacity-60">{originalPct}%</p>
                      </div>
                      <div className="w-10 h-10 rounded-full bg-white dark:bg-brand-800 border border-brand-100 dark:border-brand-700 flex items-center justify-center shadow-sm">
                        <FiArrowRight className="text-accent-500" size={18} />
                      </div>
                      <div className="flex-1 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-widest text-brand-400 mb-2">Projected</p>
                        <p className="data-value text-3xl text-brand-900 dark:text-brand-100">
                           {newData.valid ? `${newPct}%` : '--'}
                        </p>
                      </div>
                   </div>
                   
                   {delta !== null && newData.valid && (
                      <div className="mt-4 flex justify-center">
                        <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-colors ${
                          delta > 0 
                            ? 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:border-emerald-800/40 dark:text-emerald-400' 
                            : delta < 0 
                              ? 'bg-red-50 border-red-100 text-red-500 dark:bg-red-900/20 dark:border-red-800/40 dark:text-red-400' 
                              : 'bg-brand-50 border-brand-100 text-brand-500'
                        }`}>
                          {delta > 0 ? '\u2191' : delta < 0 ? '\u2193' : '\u2022'} {Math.abs(delta)}% Variance
                        </span>
                      </div>
                   )}
                </div>

                <div className="space-y-4 mb-8">
                   <div className="flex justify-center">
                      <ConfidenceBadge level={newData.confidence} />
                   </div>
                   <p className="text-sm text-brand-500 dark:text-brand-400 text-center leading-relaxed font-medium italic">
                      {!newData.valid && 'Structural inconsistencies detected. Composition requires manual recalibration.'}
                      {newData.valid && delta > 0 && 'Atmospheric alignment has improved. This ensemble is highly recommended for current conditions.'}
                      {newData.valid && delta === 0 && 'The composition maintains its integrity under contemporary stylistic parameters.'}
                      {newData.valid && delta < 0 && 'Climatic variance has slightly reduced compatibility. Still a sophisticated choice.'}
                   </p>
                </div>

                {newData.rule_violations?.length > 0 && (
                  <div className="p-4 bg-red-50/40 dark:bg-red-900/10 border border-red-100/60 dark:border-red-800/40 rounded-2xl mb-8 space-y-2">
                    {newData.rule_violations.map((v, i) => (
                      <div key={i} className="flex items-start gap-2.5">
                        <FiAlertCircle className="text-red-500 mt-0.5" size={14} />
                        <p className="text-[11px] font-bold uppercase tracking-tight text-red-700 dark:text-red-400 leading-tight">{v}</p>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <button 
                    onClick={() => { onSave?.(outfit); onClose(); }} 
                    disabled={!newData.valid}
                    className="h-12 rounded-2xl btn-secondary flex items-center justify-center gap-2 font-bold text-[10px] uppercase tracking-widest disabled:opacity-40"
                  >
                    <FiBookmark size={16} /> Archive Look
                  </button>
                  <button 
                    onClick={() => { onCalendar?.(outfit); onClose(); }} 
                    disabled={!newData.valid}
                    className="h-12 rounded-2xl btn-primary flex items-center justify-center gap-2 font-bold text-[10px] uppercase tracking-widest disabled:opacity-40"
                  >
                    <FiCalendar size={16} /> Plan In Scatola
                  </button>
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
