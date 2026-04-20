import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiArrowRight, FiRefreshCw, FiAlertCircle } from 'react-icons/fi'
import { remixPost } from '../../api/social.js'
import PublishModal from './PublishModal.jsx'
import { resolveUrl } from '../../utils/resolveUrl.js'

export default function RemixResultModal({ open, onClose, post }) {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [result,        setResult]        = useState(null)
  const [publishOpen,   setPublishOpen]   = useState(false)
  const [selectedItems, setSelectedItems] = useState({})  // category → item_id

  const remixMutation = useMutation({
    mutationFn: () => remixPost(post?.id),
    onSuccess: (data) => {
      setResult(data)
      // Default selection: pick first candidate per match
      const defaults = {}
      data.matches?.forEach(m => {
        if (m.candidates?.length > 0) {
          defaults[m.source_category] = m.candidates[0].item_id
        }
      })
      setSelectedItems(defaults)
    },
  })

  // Fire remix on open
  const handleOpen = () => {
    if (!result && post) {
      remixMutation.mutate()
    }
  }

  function handleClose() {
    setResult(null)
    setSelectedItems({})
    onClose()
  }

  function handleOpenInEditor() {
    const itemIds = Object.values(selectedItems).filter(Boolean)
    navigate('/editor', { state: { remixItemIds: itemIds, remixSourcePostId: post?.id } })
    handleClose()
  }

  return (
    <>
      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
              onClick={handleClose}
              onAnimationStart={handleOpen}
            />
            <motion.div
              initial={{ opacity: 0, y: 40, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.97 }}
              transition={{ type: 'spring', damping: 28, stiffness: 350 }}
              className="relative z-10 w-full max-w-2xl bg-white dark:bg-brand-900 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-brand-100 dark:border-brand-800">
                <div>
                  <h2 className="font-display text-xl font-bold text-brand-900 dark:text-brand-100 flex items-center gap-2">
                    <FiRefreshCw size={18} className="text-accent-700" />
                    Remix This Look
                  </h2>
                  <p className="text-sm text-brand-500 mt-0.5">
                    Matching from your wardrobe…
                  </p>
                </div>
                <button onClick={handleClose} className="p-2 rounded-lg text-brand-500 hover:text-brand-600 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors">
                  <FiX size={18} />
                </button>
              </div>

              <div className="overflow-y-auto flex-1 p-5">
                {/* Loading */}
                {remixMutation.isPending && (
                  <div className="py-16 text-center text-brand-500">
                    <div className="w-10 h-10 border-2 border-brand-200 border-t-accent-500 rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-sm">Finding your closest matches…</p>
                  </div>
                )}

                {/* Error */}
                {remixMutation.isError && (
                  <div className="py-12 text-center">
                    <FiAlertCircle size={32} className="mx-auto text-red-400 mb-3" />
                    <p className="text-sm text-brand-500">
                      {remixMutation.error?.response?.data?.error || 'Could not compute remix. Add more items to your wardrobe.'}
                    </p>
                  </div>
                )}

                {/* Results */}
                {result && (
                  <div className="space-y-4">
                    {/* Coverage indicator */}
                    <div className={`flex items-center gap-2 p-3 rounded-xl text-sm font-medium ${
                      result.can_remix
                        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                        : 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                    }`}>
                      <span>{result.can_remix ? '✅' : '⚠️'}</span>
                      <span>
                        {Math.round(result.coverage * 100)}% matched
                        {result.missing_categories.length > 0 && ` — missing: ${result.missing_categories.join(', ')}`}
                      </span>
                    </div>

                    {/* Match rows */}
                    {result.matches.map(match => (
                      <div key={match.source_category} className="border border-brand-100 dark:border-brand-800 rounded-xl overflow-hidden">
                        <div className="bg-brand-50 dark:bg-brand-800/40 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-500">
                          {match.source_category}
                        </div>
                        <div className="p-3 flex items-center gap-3">
                          {/* Source item */}
                          <div className="flex-shrink-0 text-center">
                            <p className="text-[10px] text-brand-500 mb-1">Original</p>
                            <div className="w-16 h-16 rounded-lg bg-brand-100 dark:bg-brand-800 overflow-hidden">
                              {match.source_item?.image_url ? (
                                <img
                                  src={resolveUrl(match.source_item.image_url)}
                                  className="w-full h-full object-cover"
                                  alt=""
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-2xl opacity-30">👗</div>
                              )}
                            </div>
                          </div>

                          <FiArrowRight size={16} className="text-brand-400 dark:text-brand-300 flex-shrink-0" />

                          {/* Candidate options */}
                          {match.candidates.length === 0 ? (
                            <div className="flex-1 text-xs text-brand-500 italic">
                              No {match.source_category} in your wardrobe
                            </div>
                          ) : (
                            <div className="flex gap-2 flex-wrap">
                              {match.candidates.map(c => (
                                <button
                                  key={c.item_id}
                                  onClick={() => setSelectedItems(prev => ({
                                    ...prev,
                                    [match.source_category]: c.item_id,
                                  }))}
                                  className={`relative flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                                    selectedItems[match.source_category] === c.item_id
                                      ? 'border-accent-500 shadow-md shadow-accent-200'
                                      : 'border-transparent hover:border-brand-300'
                                  }`}
                                >
                                  <img
                                    src={resolveUrl(c.image_url)}
                                    className="w-full h-full object-cover"
                                    alt=""
                                    onError={e => { e.target.style.display = 'none' }}
                                  />
                                  <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[8px] text-center py-0.5">
                                    {Math.round(c.final_score * 100)}%
                                  </div>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              {result && (
                <div className="p-5 border-t border-brand-100 dark:border-brand-800 flex gap-3">
                  <button
                    onClick={() => setPublishOpen(true)}
                    disabled={!result.can_remix}
                    className="flex-1 btn-secondary disabled:opacity-40"
                  >
                    Publish Remix
                  </button>
                  <button
                    onClick={handleOpenInEditor}
                    disabled={!result.can_remix}
                    className="flex-1 btn-primary disabled:opacity-40 flex items-center justify-center gap-2"
                  >
                    Open in Editor <FiArrowRight size={14} />
                  </button>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Publish remix modal */}
      {publishOpen && post && (
        <PublishModal
          open={publishOpen}
          onClose={() => setPublishOpen(false)}
          savedOutfit={post.outfit ? { id: post.outfit.id, name: post.outfit.name } : null}
          remixSourcePostId={post.id}
        />
      )}
    </>
  )
}
