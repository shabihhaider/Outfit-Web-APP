import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FiEdit2, FiTrash2, FiStar, FiUser } from 'react-icons/fi'
import { patchItem } from '../../api/wardrobe.js'
import ConfirmDialog from '../ui/ConfirmDialog.jsx'
import TryOnModal from '../tryon/TryOnModal.jsx'

const CAT_EMOJI = {
  top: '👕', bottom: '👖', outwear: '🧥', shoes: '👟', dress: '👗', jumpsuit: '🧘'
}

const CATEGORIES = ['top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
const FORMALITIES = ['casual', 'formal', 'both']

export default function WardrobeCard({ item, onDelete }) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [tryOnOpen, setTryOnOpen] = useState(false)
  const [category, setCategory] = useState(item.category)
  const [formality, setFormality] = useState(item.formality)

  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (data) => patchItem(item.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] })
      setIsEditing(false)
    }
  })

  const imageUrl = item.image_url
    ? `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}${item.image_url}`
    : null

  function handleSave() {
    mutation.mutate({ category, formality })
  }

  return (
    <>
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="card overflow-hidden group"
      >
        {/* Image */}
        <div className="relative aspect-square bg-brand-100/60 dark:bg-brand-800/40 overflow-hidden">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={`${item.category} item`}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              onError={e => { e.target.style.display = 'none' }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-5xl opacity-60">
              {CAT_EMOJI[item.category] || '👔'}
            </div>
          )}

          {/* Overlay gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Action buttons — always visible on touch, hover-only on desktop */}
          <div className="absolute top-2 right-2 flex gap-1.5 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all duration-200 sm:translate-y-1 sm:group-hover:translate-y-0">
            <button
              onClick={() => setIsEditing(true)}
              className="bg-white/90 dark:bg-brand-800/90 backdrop-blur-sm hover:bg-white dark:hover:bg-brand-700 text-brand-600 dark:text-brand-300 rounded-lg p-2 shadow-sm transition-colors"
              title="Edit item"
            >
              <FiEdit2 size={13} />
            </button>
            <button
              onClick={() => setConfirmOpen(true)}
              className="bg-white/90 dark:bg-brand-800/90 backdrop-blur-sm hover:bg-red-50 dark:hover:bg-red-900/40 text-red-500 rounded-lg p-2 shadow-sm transition-colors"
              title="Delete item"
            >
              <FiTrash2 size={13} />
            </button>
          </div>
        </div>

        {/* Edit Panel */}
        {isEditing && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="p-3 bg-brand-50/80 dark:bg-brand-800/40 border-b border-brand-100/60 dark:border-brand-700/40"
          >
            <div className="mb-3">
              <p className="label-xs mb-1.5">Category</p>
              <div className="flex flex-wrap gap-1">
                {CATEGORIES.map(c => (
                  <button
                    key={c}
                    onClick={() => setCategory(c)}
                    className={`px-2 py-1 rounded-full text-[10px] font-medium transition-all ${
                      category === c
                        ? 'bg-brand-900 text-white dark:bg-brand-100 dark:text-brand-900 shadow-sm'
                        : 'bg-white dark:bg-brand-800 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-700 hover:border-brand-400'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
            <div className="mb-3">
              <p className="label-xs mb-1.5">Formality</p>
              <div className="flex gap-1">
                {FORMALITIES.map(f => (
                  <button
                    key={f}
                    onClick={() => setFormality(f)}
                    className={`flex-1 px-2 py-1 rounded-full text-[10px] font-medium transition-all ${
                      formality === f
                        ? 'bg-brand-900 text-white dark:bg-brand-100 dark:text-brand-900 shadow-sm'
                        : 'bg-white dark:bg-brand-800 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-700 hover:border-brand-400'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={handleSave} disabled={mutation.isPending} className="flex-1 btn-primary text-[11px] py-1.5">
                {mutation.isPending ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => { setIsEditing(false); setCategory(item.category); setFormality(item.formality); }}
                className="flex-1 btn-secondary text-[11px] py-1.5"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}

        {/* Info */}
        <div className="p-3">
          <div className="flex items-center gap-1.5 flex-wrap mb-2">
            <span className={`badge-${item.category}`}>{item.category}</span>
            <span className={`badge-${item.formality}`}>{item.formality}</span>
          </div>

          {item.model_confidence != null && (
            <div className="text-xs text-brand-400 dark:text-brand-500 mb-2">
              AI confidence: <span className="data-value text-xs">{Math.round(item.model_confidence * 100)}%</span>
            </div>
          )}

          <button
            onClick={() => navigate('/recommendations', { state: { anchorItemId: item.id } })}
            className="w-full text-xs text-accent-600 dark:text-accent-400 font-medium py-2 border border-accent-200/60 dark:border-accent-700/40 rounded-lg hover:bg-accent-50/50 dark:hover:bg-accent-900/15 transition-all flex items-center justify-center gap-1.5 mb-2"
          >
            <FiStar size={12} /> Build outfit
          </button>
          <button
            onClick={() => setTryOnOpen(true)}
            className="w-full text-xs text-brand-500 dark:text-brand-400 font-medium py-2 border border-brand-200/60 dark:border-brand-700/40 rounded-lg hover:bg-brand-50/60 dark:hover:bg-brand-800/40 transition-all flex items-center justify-center gap-1.5"
          >
            <FiUser size={12} /> Virtual Try-On
          </button>
        </div>
      </motion.div>

      <ConfirmDialog
        open={confirmOpen}
        title="Delete item"
        message="Are you sure you want to remove this item from your wardrobe? This cannot be undone."
        danger
        onConfirm={() => { setConfirmOpen(false); onDelete(item.id) }}
        onCancel={() => setConfirmOpen(false)}
      />

      <TryOnModal
        open={tryOnOpen}
        onClose={() => setTryOnOpen(false)}
        item={item}
      />
    </>
  )
}
