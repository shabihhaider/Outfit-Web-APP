import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { FiX, FiCheck, FiTrash2, FiSun, FiBriefcase, FiHeart } from 'react-icons/fi'
import { getSaved } from '../../api/outfits.js'
import { getItems } from '../../api/wardrobe.js'
import { createPlan, updatePlan, deletePlan } from '../../api/calendar.js'
import ConfirmDialog from '../ui/ConfirmDialog.jsx'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const OCCASIONS = [
  { val: 'casual', label: 'Casual', Icon: FiSun },
  { val: 'formal', label: 'Formal', Icon: FiBriefcase },
  { val: 'wedding', label: 'Wedding', Icon: FiHeart },
]

function formatDateDisplay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-PK', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

export default function PlanModal({ open, date, existingPlan, monthStr, onClose }) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState('saved')
  const [selectedOutfitId, setSelectedOutfitId] = useState(null)
  const [selectedItems, setSelectedItems] = useState([])
  const [occasion, setOccasion] = useState('')
  const [notes, setNotes] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [error, setError] = useState(null)

  const { data: savedData } = useQuery({
    queryKey: ['saved'],
    queryFn: getSaved,
    enabled: open,
  })

  const { data: wardrobeData } = useQuery({
    queryKey: ['wardrobe'],
    queryFn: getItems,
    enabled: open && mode === 'manual',
  })

  const savedOutfits = savedData?.saved ?? []
  const wardrobeItems = wardrobeData?.items ?? []

  useEffect(() => {
    if (open) {
      setError(null)
      if (existingPlan) {
        setOccasion(existingPlan.occasion || '')
        setNotes(existingPlan.notes || '')
        if (existingPlan.saved_outfit_id) {
          setMode('saved')
          setSelectedOutfitId(existingPlan.saved_outfit_id)
          setSelectedItems([])
        } else {
          setMode('manual')
          setSelectedOutfitId(null)
          setSelectedItems(existingPlan.item_ids || [])
        }
      } else {
        setMode('saved')
        setSelectedOutfitId(null)
        setSelectedItems([])
        setOccasion('')
        setNotes('')
      }
    }
  }, [open, date, existingPlan])

  const createMutation = useMutation({
    mutationFn: (payload) => createPlan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', monthStr] })
      toast.success('Outfit planned!')
      onClose()
    },
    onError: (err) => setError(err.response?.data?.error || 'Failed to create plan.'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updatePlan(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', monthStr] })
      toast.success('Plan updated!')
      onClose()
    },
    onError: (err) => setError(err.response?.data?.error || 'Failed to update plan.'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deletePlan(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', monthStr] })
      setShowDeleteConfirm(false)
      toast.success('Plan removed.')
      onClose()
    },
  })

  function handleSave() {
    setError(null)
    const payload = {
      plan_date: date,
      occasion: occasion || null,
      notes: notes.trim() || null,
    }

    if (mode === 'saved' && selectedOutfitId) {
      payload.saved_outfit_id = selectedOutfitId
    } else if (mode === 'manual' && selectedItems.length > 0) {
      payload.item_ids = selectedItems
    } else {
      setError('Select a saved outfit or pick items manually.')
      return
    }

    if (existingPlan) {
      updateMutation.mutate({ id: existingPlan.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function toggleItem(itemId) {
    setSelectedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    )
  }

  if (!open) return null

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-950/40 backdrop-blur-sm"
            onClick={onClose}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 12 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="card p-6 w-full max-w-lg shadow-modal max-h-[90vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="font-display text-2xl font-semibold text-brand-900 dark:text-brand-100">
                    {existingPlan ? 'Edit Plan' : 'Plan Outfit'}
                  </h3>
                  <p className="text-sm text-brand-500 dark:text-brand-400">{formatDateDisplay(date)}</p>
                </div>
                <button onClick={onClose} className="p-1.5 rounded-lg text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-800 transition-colors">
                  <FiX size={18} />
                </button>
              </div>

              {/* Occasion */}
              <div className="mb-5">
                <label className="label-xs mb-2 block">Occasion</label>
                <div className="flex gap-2">
                  {OCCASIONS.map(o => (
                    <button
                      key={o.val}
                      onClick={() => setOccasion(occasion === o.val ? '' : o.val)}
                      className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all border-2 flex items-center justify-center gap-1.5 ${
                        occasion === o.val
                          ? 'bg-accent-50/80 dark:bg-accent-900/15 border-accent-300/60 dark:border-accent-600/40 text-accent-800 dark:text-accent-300'
                          : 'border-brand-200/60 dark:border-brand-700/40 text-brand-600 dark:text-brand-400 hover:border-brand-400 dark:hover:border-brand-500'
                      }`}
                    >
                      <o.Icon size={14} />
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Mode tabs */}
              <div className="flex gap-1 mb-5 bg-brand-100/40 dark:bg-brand-800/30 rounded-xl p-1">
                <button
                  onClick={() => setMode('saved')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                    mode === 'saved' ? 'bg-white dark:bg-brand-800 shadow-sm text-brand-900 dark:text-brand-100' : 'text-brand-500 dark:text-brand-400'
                  }`}
                >
                  From Saved
                </button>
                <button
                  onClick={() => setMode('manual')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                    mode === 'manual' ? 'bg-white dark:bg-brand-800 shadow-sm text-brand-900 dark:text-brand-100' : 'text-brand-500 dark:text-brand-400'
                  }`}
                >
                  Pick Items
                </button>
              </div>

              {/* Saved outfits */}
              {mode === 'saved' && (
                <div className="space-y-2 mb-5 max-h-48 overflow-y-auto">
                  {savedOutfits.length === 0 ? (
                    <p className="text-sm text-brand-400 dark:text-brand-500 text-center py-4">No saved outfits yet.</p>
                  ) : (
                    savedOutfits.map(outfit => (
                      <button
                        key={outfit.id}
                        onClick={() => setSelectedOutfitId(outfit.id === selectedOutfitId ? null : outfit.id)}
                        className={`w-full text-left p-3 rounded-xl border-2 transition-all flex items-center gap-3 ${
                          selectedOutfitId === outfit.id
                            ? 'border-accent-400/60 dark:border-accent-600/40 bg-accent-50/50 dark:bg-accent-900/10'
                            : 'border-brand-100/60 dark:border-brand-800/40 hover:bg-brand-50/60 dark:hover:bg-brand-800/20'
                        }`}
                      >
                        <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                          selectedOutfitId === outfit.id
                            ? 'border-accent-500 bg-accent-500'
                            : 'border-brand-300 dark:border-brand-600'
                        }`}>
                          {selectedOutfitId === outfit.id && <FiCheck size={10} className="text-white" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-brand-800 dark:text-brand-200 truncate">{outfit.name}</p>
                          <p className="text-xs text-brand-400 dark:text-brand-500 capitalize">
                            {outfit.occasion} &middot; {Math.round((outfit.final_score || 0) * 100)}%
                          </p>
                        </div>
                        <div className="flex gap-0.5 flex-shrink-0">
                          {outfit.items?.slice(0, 3).map((item, j) => (
                            <div key={j} className="w-8 h-8 rounded-lg overflow-hidden bg-brand-100 dark:bg-brand-800">
                              {item.image_url && <img src={`${API_URL}${item.image_url}`} alt="" className="w-full h-full object-cover" />}
                            </div>
                          ))}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}

              {/* Manual picker */}
              {mode === 'manual' && (
                <div className="mb-5">
                  <p className="text-xs text-brand-500 dark:text-brand-400 mb-2">
                    Selected: {selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''}
                  </p>
                  <div className="grid grid-cols-4 gap-2 max-h-48 overflow-y-auto">
                    {wardrobeItems.map(item => {
                      const selected = selectedItems.includes(item.id)
                      return (
                        <button
                          key={item.id}
                          onClick={() => toggleItem(item.id)}
                          className={`relative rounded-xl overflow-hidden border-2 transition-all aspect-square ${
                            selected
                              ? 'border-accent-500/80 ring-1 ring-accent-200/60 dark:ring-accent-700/40'
                              : 'border-brand-100/60 dark:border-brand-800/40 hover:border-brand-300 dark:hover:border-brand-600'
                          }`}
                        >
                          {item.image_url && <img src={`${API_URL}${item.image_url}`} alt={item.category} className="w-full h-full object-cover" />}
                          {selected && (
                            <div className="absolute top-1 right-1 w-5 h-5 bg-accent-500 rounded-full flex items-center justify-center shadow-sm">
                              <FiCheck size={12} className="text-white" />
                            </div>
                          )}
                          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent text-white text-[10px] py-1 text-center capitalize">
                            {item.category}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Notes */}
              <div className="mb-5">
                <label className="label-xs mb-1.5 block">Notes (optional)</label>
                <input
                  type="text"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  maxLength={200}
                  placeholder="e.g. Job interview, Dinner party..."
                  className="input-field w-full rounded-xl"
                />
              </div>

              {error && (
                <div className="p-3 mb-4 bg-red-50/80 dark:bg-red-900/15 border border-red-200/60 dark:border-red-800/40 rounded-xl text-sm text-red-700 dark:text-red-300">
                  {error}
                </div>
              )}

              <div className="flex gap-2">
                <button onClick={onClose} className="btn-secondary text-sm flex-1 rounded-xl">Cancel</button>
                {existingPlan && (
                  <button onClick={() => setShowDeleteConfirm(true)} className="btn-danger text-sm px-4 flex items-center gap-1 rounded-xl">
                    <FiTrash2 size={14} />
                  </button>
                )}
                <button onClick={handleSave} disabled={isPending} className="btn-primary text-sm flex-1 rounded-xl">
                  {isPending ? 'Saving...' : existingPlan ? 'Update' : 'Save Plan'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={showDeleteConfirm}
        title="Delete Plan"
        message="Remove this outfit plan from your calendar?"
        danger
        onConfirm={() => deleteMutation.mutate(existingPlan?.id)}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  )
}
