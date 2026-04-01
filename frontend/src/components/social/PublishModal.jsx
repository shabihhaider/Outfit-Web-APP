import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiGlobe, FiUsers, FiLock, FiCheck } from 'react-icons/fi'
import { publishOutfit, getVibes } from '../../api/social.js'
// import { getActiveSeason } from '../../utils/seasons.js'

const VISIBILITY_OPTIONS = [
  { value: 'public',    label: 'Public',    Icon: FiGlobe,  desc: 'Anyone can see' },
  { value: 'followers', label: 'Followers', Icon: FiUsers,  desc: 'Followers only' },
  { value: 'private',   label: 'Private',   Icon: FiLock,   desc: 'Only you' },
]

export default function PublishModal({ open, onClose, savedOutfit, remixSourcePostId = null }) {
  const qc = useQueryClient()
  const [caption,    setCaption]    = useState('')
  const [visibility, setVisibility] = useState('public')
  const [selectedVibes, setSelectedVibes] = useState([])

  // const activeSeason = getActiveSeason()

  const { data: vibesData } = useQuery({
    queryKey: ['vibes'],
    queryFn:  getVibes,
    enabled:  open,
    staleTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: publishOutfit,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feed'] })
      qc.invalidateQueries({ queryKey: ['social-profile'] })
      onClose()
      setCaption('')
      setSelectedVibes([])
      setVisibility('public')
    },
  })

  function toggleVibe(slug) {
    setSelectedVibes(prev => {
      if (prev.includes(slug)) return prev.filter(s => s !== slug)
      if (prev.length >= 3)    return prev  // max 3
      return [...prev, slug]
    })
  }

  function handleSubmit() {
    if (!savedOutfit) return
    mutation.mutate({
      saved_outfit_id:     savedOutfit.id,
      caption:             caption.trim() || undefined,
      vibe_slugs:          selectedVibes,
      visibility,
      remix_source_post_id: remixSourcePostId || undefined,
    })
  }

  const allVibes = [
    ...(vibesData?.global      || []),
    ...(vibesData?.['south-asian'] || []),
  ]

  // Auto-suggest season vibe
  // const seasonVibe = activeSeason?.vibe
  // const seasonLabel = activeSeason?.label

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ type: 'spring', damping: 28, stiffness: 350 }}
            className="relative z-10 w-full max-w-lg bg-white dark:bg-brand-900 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-brand-100 dark:border-brand-800">
              <div>
                <h2 className="font-display text-xl font-bold text-brand-900 dark:text-brand-100">
                  {remixSourcePostId ? '🔀 Publish Remix' : 'Share Outfit'}
                </h2>
                {savedOutfit && (
                  <p className="text-sm text-brand-500 mt-0.5">{savedOutfit.name}</p>
                )}
              </div>
              <button onClick={onClose} className="p-2 rounded-lg text-brand-400 hover:text-brand-600 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors">
                <FiX size={18} />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 p-5 space-y-5">

              {/* Caption */}
              <div>
                <label className="label-xs mb-1.5 block">Caption</label>
                <textarea
                  value={caption}
                  onChange={e => setCaption(e.target.value)}
                  maxLength={300}
                  rows={3}
                  placeholder="Describe this look…"
                  className="w-full rounded-xl border border-brand-200 dark:border-brand-700 bg-brand-50 dark:bg-brand-800/40 px-3 py-2.5 text-sm text-brand-800 dark:text-brand-200 placeholder-brand-400 focus:outline-none focus:border-accent-400 resize-none"
                />
                <p className="text-right text-[10px] text-brand-400 mt-1">{caption.length}/300</p>
              </div>

              {/* Vibe tags */}
              <div>
                <label className="label-xs mb-1.5 block">Vibe Tags <span className="font-normal text-brand-400">(pick up to 3)</span></label>
                {allVibes.length > 0 && (
                  <div className="space-y-3">
                    {/* South Asian tags first */}
                    {(vibesData?.['south-asian'] || []).length > 0 && (
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-brand-400 mb-1.5">South Asian</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(vibesData?.['south-asian'] || []).map(v => (
                            <button
                              key={v.slug}
                              onClick={() => toggleVibe(v.slug)}
                              className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium border transition-all ${
                                selectedVibes.includes(v.slug)
                                  ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100'
                                  : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
                              } ${selectedVibes.length >= 3 && !selectedVibes.includes(v.slug) ? 'opacity-40 cursor-not-allowed' : ''}`}
                            >
                              {selectedVibes.includes(v.slug) && <FiCheck size={10} />}
                              {v.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-brand-400 mb-1.5">Global</p>
                      <div className="flex flex-wrap gap-1.5">
                        {(vibesData?.global || []).map(v => (
                          <button
                            key={v.slug}
                            onClick={() => toggleVibe(v.slug)}
                            className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium border transition-all ${
                              selectedVibes.includes(v.slug)
                                ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100'
                                : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
                            } ${selectedVibes.length >= 3 && !selectedVibes.includes(v.slug) ? 'opacity-40 cursor-not-allowed' : ''}`}
                          >
                            {selectedVibes.includes(v.slug) && <FiCheck size={10} />}
                            {v.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Visibility */}
              <div>
                <label className="label-xs mb-1.5 block">Visibility</label>
                <div className="grid grid-cols-3 gap-2">
                  {VISIBILITY_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setVisibility(opt.value)}
                      className={`flex flex-col items-center gap-1 p-3 rounded-xl border text-xs font-medium transition-all ${
                        visibility === opt.value
                          ? 'bg-brand-900 text-white border-brand-900 dark:bg-brand-100 dark:text-brand-900 dark:border-brand-100'
                          : 'border-brand-200 dark:border-brand-700 text-brand-600 dark:text-brand-400 hover:border-brand-400'
                      }`}
                    >
                      <opt.Icon size={15} />
                      <span>{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-5 border-t border-brand-100 dark:border-brand-800 flex gap-3">
              <button onClick={onClose} className="flex-1 btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={mutation.isPending}
                className="flex-1 btn-primary"
              >
                {mutation.isPending ? 'Publishing…' : 'Publish'}
              </button>
            </div>

            {mutation.isError && (
              <p className="px-5 pb-3 text-xs text-red-500 text-center">
                {mutation.error?.response?.data?.error || 'Failed to publish. Try again.'}
              </p>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
