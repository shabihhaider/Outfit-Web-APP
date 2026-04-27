import { useState, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiUser } from 'react-icons/fi'
import TryOnModal from './TryOnModal.jsx'
import { resolveUrl } from '../../utils/resolveUrl.js'
import { wardrobeItemAlt } from '../../utils/wardrobeItemAlt.js'

// Categories that FASHN VTON supports (shoes cannot be virtually tried on)
const VTO_SUPPORTED = new Set(['top', 'outwear', 'bottom', 'dress', 'jumpsuit'])

// Hero priority — most visually impactful garments first
const HERO_PRIORITY = ['dress', 'jumpsuit', 'top', 'outwear', 'bottom']

function pickHero(items) {
  if (!items?.length) return null
  for (const cat of HERO_PRIORITY) {
    const found = items.find(i => i.category === cat)
    if (found) return found
  }
  return items[0]
}

export default function OutfitTryOnModal({ open, onClose, items, occasion }) {
  const [selectedItem, setSelectedItem] = useState(null)
  const [tryOnOpen, setTryOnOpen] = useState(false)

  // Filter to items that VTO can actually process (shoes are not supported)
  const tryableItems = useMemo(
    () => (items ?? []).filter(i => i.id && i.image_url && VTO_SUPPORTED.has(i.category)),
    [items]
  )

  // Auto-select hero when modal opens
  const hero = useMemo(() => pickHero(tryableItems), [tryableItems])
  const active = selectedItem ?? hero

  if (!open || tryableItems.length === 0) return null

  // If TryOnModal is open, render only that
  if (tryOnOpen && active) {
    return (
      <TryOnModal
        open
        onClose={() => { setTryOnOpen(false); onClose() }}
        item={active}
      />
    )
  }

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-brand-950/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="card w-full max-w-md shadow-modal"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-display text-xl font-semibold text-brand-900 dark:text-brand-100">
                  Try On Outfit
                </h2>
                <p className="text-xs text-brand-500 dark:text-brand-400 mt-0.5">
                  Select which piece to virtually try on
                  {occasion && <span className="ml-1 capitalize">· {occasion}</span>}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-brand-500 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors"
              >
                <FiX size={18} />
              </button>
            </div>

            {/* Item selector grid */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              {tryableItems.map((item) => {
                const isActive = active?.id === item.id
                const imgUrl = resolveUrl(item.image_url)

                return (
                  <button
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`group relative aspect-square rounded-2xl overflow-hidden border-2 transition-all duration-200 ${
                      isActive
                        ? 'border-accent-500 shadow-lg shadow-accent-500/20 ring-2 ring-accent-500/30 scale-[1.02]'
                        : 'border-brand-200/60 dark:border-brand-700/40 hover:border-accent-300 dark:hover:border-accent-600'
                    }`}
                  >
                    <img
                      src={imgUrl}
                      alt={wardrobeItemAlt(item)}
                      className="w-full h-full object-cover"
                    />

                    {/* Category label */}
                    <div className={`absolute bottom-0 inset-x-0 py-1.5 text-center transition-all ${
                      isActive
                        ? 'bg-accent-500 text-white'
                        : 'bg-black/50 text-white/80 backdrop-blur-sm'
                    }`}>
                      <span className="text-[10px] font-bold uppercase tracking-wider">
                        {item.category}
                      </span>
                    </div>

                    {/* Selected checkmark */}
                    {isActive && (
                      <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-accent-500 flex items-center justify-center shadow-md">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Info banner */}
            <div className="mb-5 p-3 rounded-xl bg-brand-50/60 dark:bg-brand-800/40 border border-brand-100/60 dark:border-brand-700/30">
              <p className="text-xs text-brand-500 dark:text-brand-400 leading-relaxed">
                AI will place the selected <span className="font-semibold text-brand-700 dark:text-brand-300">{active?.category}</span> on
                your photo using neural fitting technology. First try takes a few seconds; cached results are instant.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 btn-secondary">
                Cancel
              </button>
              <button
                onClick={() => setTryOnOpen(true)}
                className="flex-1 btn-primary flex items-center justify-center gap-2"
              >
                <FiUser size={14} />
                Try This On
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  )
}
