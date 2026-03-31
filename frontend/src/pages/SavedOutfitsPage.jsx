import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { FiTrash2, FiStar, FiChevronRight, FiGrid, FiList, FiShare2 } from 'react-icons/fi'
import { getSaved, deleteSaved } from '../api/outfits.js'
import PageWrapper from '../components/layout/PageWrapper.jsx'
import OutfitItems from '../components/recommendations/OutfitItems.jsx'
import LoadingSpinner from '../components/ui/LoadingSpinner.jsx'
import ErrorMessage from '../components/ui/ErrorMessage.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import PublishModal from '../components/social/PublishModal.jsx'
import { formatDate } from '../utils/formatters.js'
import { useNavigate } from 'react-router-dom'

export default function SavedOutfitsPage() {
  const [deleteTarget,  setDeleteTarget]  = useState(null)
  const [publishTarget, setPublishTarget] = useState(null)
  const [viewMode,      setViewMode]      = useState('grid')
  const queryClient = useQueryClient()
  const navigate    = useNavigate()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['saved'],
    queryFn: getSaved,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSaved,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved'] })
      setDeleteTarget(null)
    },
  })

  const outfits = data?.saved ?? data?.saved_outfits ?? data?.outfits ?? []

  return (
    <>
      <PageWrapper>
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6"
        >
          <div>
            <p className="label-xs mb-1">Curation Gallery</p>
            <h1 className="font-display text-3xl sm:text-4xl lg:text-6xl font-bold text-brand-900 dark:text-brand-100 tracking-tight leading-tight">
              Saved Archives
            </h1>
            <p className="text-brand-500 dark:text-brand-400 mt-3 text-lg font-medium italic">
              {isLoading ? 'Cataloging collection...' : `Discovering ${outfits.length} high-fidelity compositions.`}
            </p>
          </div>
          
          <div className="flex bg-brand-50/60 dark:bg-brand-900/20 p-1 rounded-2xl border border-brand-100 dark:border-brand-800">
            <button 
              onClick={() => setViewMode('grid')}
              className={`p-2.5 rounded-xl transition-all ${viewMode === 'grid' ? 'bg-white dark:bg-brand-800 shadow-sm text-brand-900 dark:text-brand-100' : 'text-brand-400 hover:text-brand-600'}`}
            >
              <FiGrid size={20} />
            </button>
            <button 
              onClick={() => setViewMode('list')}
              className={`p-2.5 rounded-xl transition-all ${viewMode === 'list' ? 'bg-white dark:bg-brand-800 shadow-sm text-brand-900 dark:text-brand-100' : 'text-brand-400 hover:text-brand-600'}`}
            >
              <FiList size={20} />
            </button>
          </div>
        </motion.div>

        {isLoading && <LoadingSpinner className="py-32" size="lg" />}
        {error && <ErrorMessage message="The gallery could not be synchronized." onRetry={refetch} />}

        {!isLoading && !error && outfits.length === 0 && (
          <EmptyState
            icon="🗃️"
            title="Archival Vault Empty"
            description="Preserve your preferred recommendations to build your personal style archive."
            action={{ label: 'Generate Looks', icon: FiStar, onClick: () => navigate('/recommendations') }}
          />
        )}

        {!isLoading && outfits.length > 0 && (
          <div className={viewMode === 'grid' 
            ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8" 
            : "max-w-4xl mx-auto space-y-6"
          }>
            <AnimatePresence>
              {outfits.map((outfit, idx) => (
                <motion.div
                  key={outfit.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.5, delay: idx * 0.05 }}
                  className="card-glass group overflow-hidden border-brand-100/60 dark:border-brand-800/40 hover:shadow-card-hover flex flex-col p-6 h-full"
                >
                  <div className="flex items-start justify-between mb-6">
                    <div className="space-y-1">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-brand-400 dark:text-brand-500">
                        {formatDate(outfit.created_at ?? outfit.saved_at)}
                      </p>
                      <h3 className="font-display text-xl font-bold text-brand-900 dark:text-brand-100 group-hover:text-accent-600 transition-colors truncate max-w-[180px]">
                        {outfit.name || 'Untitled Look'}
                      </h3>
                    </div>
                    <button
                      onClick={() => setDeleteTarget(outfit.id)}
                      className="w-10 h-10 rounded-xl bg-red-50/50 dark:bg-red-900/10 text-red-500 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-sm hover:bg-red-500 hover:text-white"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </div>

                  <div className="flex-1 mb-8 overflow-hidden rounded-2xl bg-brand-50/40 dark:bg-brand-900/10 p-4 border border-brand-100/40 dark:border-brand-800/40 group-hover:bg-white dark:group-hover:bg-brand-800/40 transition-colors">
                    <OutfitItems items={outfit.items ?? []} />
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-brand-100/60 dark:border-brand-800/40">
                    <div className="flex items-center gap-2">
                       <span className="badge-casual px-3 py-1 bg-brand-100 dark:bg-brand-800 text-[10px] uppercase font-bold tracking-widest">
                         {outfit.occasion}
                       </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPublishTarget(outfit)}
                        className="flex items-center gap-1.5 text-xs text-brand-500 hover:text-accent-600 dark:hover:text-accent-400 font-medium px-2.5 py-1.5 rounded-lg hover:bg-accent-50 dark:hover:bg-accent-900/15 transition-all"
                        title="Share to Feed"
                      >
                        <FiShare2 size={13} />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </PageWrapper>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Archival Deletion"
        message="Are you certain you wish to purge this composition from your permanent archive?"
        danger
        onConfirm={() => deleteMutation.mutate(deleteTarget)}
        onCancel={() => setDeleteTarget(null)}
      />

      <PublishModal
        open={!!publishTarget}
        onClose={() => setPublishTarget(null)}
        savedOutfit={publishTarget}
      />
    </>
  )
}
